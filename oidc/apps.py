from __future__ import annotations

from django.apps import AppConfig


class Config(AppConfig):
    name = "oidc"

    def ready(self) -> None:
        from sentry.auth import register

        from .provider import OIDCProvider

        register(OIDCProvider)
