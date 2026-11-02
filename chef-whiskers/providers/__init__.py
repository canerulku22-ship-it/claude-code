"""Registry of image/video providers. Pick one with --provider or VIDEO_PROVIDER in .env.

To add a provider: write providers/<name>.py with a ``Provider`` subclass and add
one line to ``PROVIDERS`` below. Modules load only when selected, so a provider's
SDK is needed only by people who use it.
"""

from __future__ import annotations

import importlib
from typing import Type

from .base import (
    Provider,
    ProviderConfigError,
    ProviderError,
    TransientProviderError,
    with_retries,
)

# name -> "module:ClassName" inside this package
PROVIDERS: dict[str, str] = {
    "placeholder": "placeholder:PlaceholderProvider",
}

__all__ = [
    "PROVIDERS",
    "Provider",
    "ProviderConfigError",
    "ProviderError",
    "TransientProviderError",
    "available_providers",
    "get_provider",
    "get_provider_class",
    "with_retries",
]


def available_providers() -> list[str]:
    return sorted(PROVIDERS)


def get_provider_class(name: str) -> Type[Provider]:
    """Look up a provider class by name without instantiating it (no keys needed)."""
    if not name:
        raise ProviderConfigError(
            "No provider selected. Set VIDEO_PROVIDER in .env or pass --provider. "
            f"Available: {', '.join(available_providers())}."
        )
    target = PROVIDERS.get(name.lower())
    if target is None:
        raise ProviderConfigError(
            f"Unknown provider '{name}'. Available: {', '.join(available_providers())}. "
            "To add one, see 'Plugging in a provider' in README.md."
        )
    module_name, class_name = target.split(":")
    try:
        module = importlib.import_module(f".{module_name}", __name__)
    except ImportError as exc:
        raise ProviderConfigError(
            f"Provider '{name}' needs a package that is not installed ({exc}). "
            "Run: pip install -r requirements.txt"
        ) from exc
    return getattr(module, class_name)


def get_provider(name: str) -> Provider:
    """Instantiate the provider called ``name``. This is where API keys get checked."""
    return get_provider_class(name)()
