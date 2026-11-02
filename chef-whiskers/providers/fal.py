"""fal.ai provider: one FAL_KEY pays for both the reference image and the clips.

Defaults, each overridable in .env:
  FAL_IMAGE_MODEL  fal-ai/flux-pro/v1.1-ultra          text-to-image, asked for 9:16 PNG
  FAL_VIDEO_MODEL  fal-ai/vidu/q2/reference-to-video   keeps the cat consistent from the
                                                       reference image without making it
                                                       the first frame of every clip
  FAL_IMAGE_ARGS / FAL_VIDEO_ARGS  optional JSON merged into every request,
                                   e.g. FAL_VIDEO_ARGS={"resolution": "1080p"}

Another model works by changing the model ID if it takes the same fields: ``prompt``
and ``aspect_ratio``, plus ``reference_image_urls`` and ``duration`` for video. Check the
model's API page on fal.ai and use the *_ARGS variables for anything extra.
"""

from __future__ import annotations

import json
import math
import os
import time
from pathlib import Path
from typing import Any, Optional

import fal_client
import httpx
from fal_client.auth import MissingCredentialsError

from .base import (
    Provider,
    ProviderConfigError,
    ProviderError,
    TransientProviderError,
    download,
    with_retries,
)

DEFAULT_IMAGE_MODEL = "fal-ai/flux-pro/v1.1-ultra"
DEFAULT_VIDEO_MODEL = "fal-ai/vidu/q2/reference-to-video"
POLL_INTERVAL = 3.0  # seconds between status checks
JOB_TIMEOUT = 20 * 60  # give up on (and cancel) a job that has not finished after this long
MAX_POLL_ERRORS = 10  # consecutive network errors tolerated while polling one job


class FalRequestError(ProviderError):
    """fal rejected a request; ``status`` is the HTTP status code."""

    def __init__(self, message: str, status: int):
        super().__init__(message)
        self.status = status


class FalProvider(Provider):
    name = "fal"

    def __init__(self) -> None:
        self.require_env("FAL_KEY")  # fal_client reads it from the environment itself
        self.image_model = _model("FAL_IMAGE_MODEL", DEFAULT_IMAGE_MODEL)
        self.video_model = _model("FAL_VIDEO_MODEL", DEFAULT_VIDEO_MODEL)
        self.image_args = _json_env("FAL_IMAGE_ARGS")
        self.video_args = _json_env("FAL_VIDEO_ARGS")
        self._uploads: dict[tuple[Path, int, int], str] = {}

    @classmethod
    def describe(cls) -> str:
        key = os.environ.get("FAL_KEY", "").strip()
        key_state = "set" if key and not key.startswith("your-") else "MISSING (add it to .env)"
        return (
            f"image {_model('FAL_IMAGE_MODEL', DEFAULT_IMAGE_MODEL)}, "
            f"video {_model('FAL_VIDEO_MODEL', DEFAULT_VIDEO_MODEL)}, FAL_KEY {key_state}"
        )

    def generate_image(self, prompt: str) -> bytes:
        args = {"prompt": prompt, "aspect_ratio": "9:16", "num_images": 1, "output_format": "png", **self.image_args}
        result = self._run(self.image_model, args)
        return download(_file_url(result, "images", self.image_model))

    def generate_video(self, prompt: str, ref_image: Path, *, duration: float = 5.0, scene: Optional[str] = None) -> bytes:
        args: dict[str, Any] = {
            "prompt": prompt,
            "reference_image_urls": [self._upload(ref_image)],
            "aspect_ratio": "9:16",
            "duration": str(max(1, math.ceil(duration))),
            **self.video_args,
        }
        try:
            result = self._run(self.video_model, args)
        except FalRequestError as exc:
            # Models differ in which clip lengths they accept. If this one rejects the
            # length, use its default: the pipeline trims or extends the clip anyway.
            if exc.status != 422 or "duration" not in str(exc).lower() or "duration" in self.video_args:
                raise
            print(f"    fal: {self.video_model} rejected duration {args['duration']}; using the model's default length")
            args.pop("duration")
            result = self._run(self.video_model, args)
        return download(_file_url(result, "video", self.video_model))

    # ---------------------------------------------------------------- internals

    def _upload(self, path: Path) -> str:
        """Upload the reference image to fal's CDN once per run and reuse the URL."""
        stat = path.stat()
        key = (path.resolve(), stat.st_mtime_ns, stat.st_size)
        if key not in self._uploads:
            print(f"    fal: uploading {path.name}")
            self._uploads[key] = with_retries(
                lambda: _call(lambda: fal_client.upload_file(path), "upload"),
                what="uploading the reference image to fal",
            )
        return self._uploads[key]

    def _run(self, model: str, args: dict[str, Any]) -> dict[str, Any]:
        """Submit a job, poll it to completion and return its result.

        Network errors while polling keep polling the same job instead of submitting
        a new one, so a dropped connection does not mean paying twice.
        """
        handle = _call(lambda: fal_client.submit(model, arguments=args), model)
        deadline = time.monotonic() + JOB_TIMEOUT
        state, errors = "", 0
        while True:
            try:
                status = _call(handle.status, model)
                errors = 0
            except TransientProviderError:
                errors += 1
                if errors > MAX_POLL_ERRORS:
                    raise
                status = None
            if isinstance(status, fal_client.Completed):
                break
            new_state = {fal_client.Queued: "queued", fal_client.InProgress: "generating"}.get(type(status), state)
            if new_state != state:
                print(f"    fal: {new_state} ({model}, request {handle.request_id})")
                state = new_state
            if time.monotonic() > deadline:
                try:
                    handle.cancel()
                except Exception:
                    pass
                raise TransientProviderError(
                    f"{model} did not finish within {JOB_TIMEOUT // 60} minutes (request {handle.request_id})"
                )
            time.sleep(POLL_INTERVAL)
        return _call(handle.get, model)


def _model(var: str, default: str) -> str:
    return os.environ.get(var, "").strip() or default


def _json_env(var: str) -> dict[str, Any]:
    raw = os.environ.get(var, "").strip()
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProviderConfigError(f"{var} in .env is not valid JSON: {exc.msg}. Example: {var}={{\"resolution\": \"1080p\"}}") from exc
    if not isinstance(value, dict):
        raise ProviderConfigError(f"{var} must be a JSON object, like {{\"resolution\": \"1080p\"}}.")
    return value


def _file_url(result: Any, field: str, model: str) -> str:
    """Pull the output URL from {"video": {"url": ...}} or {"images": [{"url": ...}]}."""
    value = result.get(field) if isinstance(result, dict) else None
    if isinstance(value, list):
        value = value[0] if value else None
    url = value.get("url") if isinstance(value, dict) else None
    if not url:
        keys = ", ".join(result) if isinstance(result, dict) else type(result).__name__
        raise ProviderError(f"{model} returned no {field} URL (response fields: {keys}).")
    return url


def _call(fn, model: str):
    """Run a fal_client call, turning its exceptions into the pipeline's error types."""
    try:
        return fn()
    except MissingCredentialsError as exc:
        raise ProviderConfigError("FAL_KEY is not set. Add it to .env (see .env.example).") from exc
    except fal_client.FalClientHTTPError as exc:
        code = exc.status_code
        message = f"fal {model}: HTTP {code}: {_detail(exc.message)}"
        if code in (401, 403):
            raise ProviderError(f"{message}. Check FAL_KEY in .env and your fal account balance.") from exc
        if code in (408, 409, 425, 429) or code >= 500:
            raise TransientProviderError(message, retry_after=_retry_after(exc.response_headers)) from exc
        raise FalRequestError(message, code) from exc
    except fal_client.FalClientTimeoutError as exc:
        raise TransientProviderError(f"fal {model}: {exc}") from exc
    except (httpx.TransportError, TimeoutError, ConnectionError) as exc:
        raise TransientProviderError(f"network error talking to fal ({type(exc).__name__}: {exc})") from exc


def _detail(detail: Any) -> str:
    """Make fal's error detail readable; validation errors arrive as a list of dicts."""
    if isinstance(detail, list):
        parts = []
        for item in detail:
            if isinstance(item, dict):
                loc = ".".join(str(p) for p in item.get("loc", []) if p != "body")
                parts.append(f"{loc}: {item.get('msg', item)}" if loc else str(item.get("msg", item)))
            else:
                parts.append(str(item))
        return "; ".join(parts)
    return str(detail)


def _retry_after(headers: dict[str, str]) -> float | None:
    for key, value in (headers or {}).items():
        if key.lower() == "retry-after":
            try:
                return min(float(value), 300.0)
            except ValueError:
                return None
    return None
