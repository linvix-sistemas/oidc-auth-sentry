from django.apps import AppConfig


class Config(AppConfig):
    name = "oidc"

    def ready(self) -> None:
        from sentry import auth, options

        from .constants import get_provider_name
        from .provider import OIDCProvider

        flags = options.FLAG_ALLOW_EMPTY | options.FLAG_PRIORITIZE_DISK
        options.register("auth-oidc.client-id", flags=flags)
        options.register("auth-oidc.client-secret", flags=flags)
        options.register("auth-oidc.authorize-url", flags=flags)
        options.register("auth-oidc.token-url", flags=flags)
        options.register("auth-oidc.issuer", flags=flags)
        options.register("auth-oidc.name-claims", flags=flags)
        options.register("auth-oidc.provider-name", flags=flags)
        options.register("auth-oidc.groups-claim", flags=flags)
        options.register("auth-oidc.allowed-groups", flags=flags)
        options.register("auth-oidc.allowed-domains", flags=flags)

        # Resolve the (optionally rebranded) display name once at boot, after
        # its option is registered, so both the provider picker and the
        # configured provider show it.
        OIDCProvider.name = get_provider_name()

        auth.register(OIDCProvider)
