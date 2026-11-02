"""The interface every image/video provider implements, plus shared error and retry helpers."""

from __future__ import annotations

import os
import random
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable, Optional, TypeVar

T = TypeVar("T")


class ProviderError(RuntimeError):
    """A request failed and retrying will not help: bad key, rejected prompt, invalid input."""


class ProviderConfigError(ProviderError):
    """The provider is not configured, for example its API key is missing from .env."""


class TransientProviderError(ProviderError):
    """A temporary failure worth retrying: rate limit, timeout, 5xx, dropped connection.

    Set ``retry_after`` (seconds) when the API says how long to wait.
    """

    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after


class Provider(ABC):
    """Swappable backend for the two AI calls the pipeline makes.

    To plug in a provider, subclass this in ``providers/<name>.py``, implement both
    methods, and register the class in ``providers/__init__.py``. Raise
    ``TransientProviderError`` for errors worth retrying and ``ProviderError`` for
    the rest; ``with_retries`` handles the backoff.
    """

    #: Name used with --provider / VIDEO_PROVIDER.
    name: str = "base"
    #: Longest prompt the API accepts, if it has a limit (checked before calling it).
    max_prompt_chars: Optional[int] = None
    #: True for offline test providers: their output goes to output/test/ so it
    #: never mixes with, or gets reused as, real generations.
    is_test_provider: bool = False

    @abstractmethod
    def generate_image(self, prompt: str) -> bytes:
        """Generate one image for ``prompt`` and return its bytes.

        Ask for a vertical 9:16 image. PNG is preferred; other formats are converted.
        """

    @abstractmethod
    def generate_video(self, prompt: str, ref_image: Path, *, duration: float = 5.0) -> bytes:
        """Generate a short clip for ``prompt`` and return the MP4 bytes.

        ``ref_image`` is the character reference (output/character_ref.png). Send it
        as the model's character/subject reference if it has one, so the cat stays
        consistent without every clip starting on the same frame; fall back to using
        it as the start frame only if that is all the API offers.

        ``duration`` is the shot length in seconds. Request the shortest length the
        model supports that is at least this long, in 9:16. The pipeline trims longer
        clips and holds the last frame of shorter ones.
        """

    @classmethod
    def describe(cls) -> str:
        """One line for --dry-run: models and config status. Must not call any API."""
        return ""

    @staticmethod
    def require_env(var: str) -> str:
        """Return the environment variable ``var`` or raise a clear configuration error."""
        value = os.environ.get(var, "").strip()
        if not value:
            raise ProviderConfigError(
                f"{var} is not set. Copy .env.example to .env and put your key there "
                "(never in the code)."
            )
        if value.startswith("your-"):
            raise ProviderConfigError(
                f"{var} still has the placeholder value from .env.example. "
                "Replace it with your real key in .env."
            )
        return value


def is_retryable(exc: BaseException) -> bool:
    """Whether ``exc`` is a temporary failure that is worth another attempt."""
    if isinstance(exc, TransientProviderError):
        return True
    if isinstance(exc, ProviderError):
        return False
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code in (408, 409, 425, 429) or exc.code >= 500
    return isinstance(exc, (urllib.error.URLError, TimeoutError, ConnectionError))


def describe(exc: BaseException) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        return f"HTTP {exc.code} {exc.reason}"
    return str(exc) or type(exc).__name__


def with_retries(
    fn: Callable[[], T],
    *,
    what: str,
    attempts: int = 4,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
    sleep: Callable[[float], None] = time.sleep,
    log: Callable[[str], None] = print,
) -> T:
    """Call ``fn``, retrying temporary failures with exponential backoff and jitter.

    Errors that are not temporary are raised immediately as ``ProviderError`` with
    ``what`` in the message, so the user sees which step failed.
    """
    attempts = max(1, attempts)
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as exc:
            if not is_retryable(exc):
                if isinstance(exc, urllib.error.HTTPError) and exc.code in (401, 403):
                    raise ProviderError(
                        f"{what} failed: {describe(exc)}. Check the API key in .env and that "
                        "your account has access and credits."
                    ) from exc
                if isinstance(exc, (ProviderError, urllib.error.URLError)):
                    raise ProviderError(f"{what} failed: {describe(exc)}") from exc
                raise
            if attempt == attempts:
                raise ProviderError(
                    f"{what} failed after {attempts} attempts. Last error: {describe(exc)}"
                ) from exc
            retry_after = getattr(exc, "retry_after", None)
            if retry_after:
                delay = float(retry_after)
            else:
                delay = min(max_delay, base_delay * 2 ** (attempt - 1)) * random.uniform(0.8, 1.2)
            log(f"  ! {what}: {describe(exc)}. Retrying in {delay:.1f}s (attempt {attempt + 1}/{attempts})")
            sleep(delay)
    raise AssertionError("unreachable")


def download(url: str, *, timeout: float = 300, attempts: int = 3) -> bytes:
    """Fetch a generated file, retrying network errors without regenerating (and re-paying for) it."""

    def fetch() -> bytes:
        request = urllib.request.Request(url, headers={"User-Agent": "chef-whiskers"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()

    return with_retries(fetch, what=f"downloading {url}", attempts=attempts)
