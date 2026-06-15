from django.apps import AppConfig


class Config(AppConfig):
    name = "oidc"

    def ready(self) -> None:
        from sentry import auth, options

        from .provider import OIDCProvider

        auth.register(OIDCProvider)

        flags = options.FLAG_ALLOW_EMPTY | options.FLAG_PRIORITIZE_DISK
        options.register("auth-oidc.client-id", flags=flags)
        options.register("auth-oidc.client-secret", flags=flags)
        options.register("auth-oidc.authorize-url", flags=flags)
        options.register("auth-oidc.token-url", flags=flags)
        options.register("auth-oidc.issuer", flags=flags)
        options.register("auth-oidc.name-claims", flags=flags)
