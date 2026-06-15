from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sentry import options
from sentry.auth.provider import MigratingIdentityId
from sentry.auth.providers.oauth2 import OAuth2Callback, OAuth2Login, OAuth2Provider
from sentry.auth.view import AuthView

from .constants import (
    DATA_VERSION,
    PROVIDER_NAME,
    SCOPE,
    get_access_token_url,
    get_authorize_url,
)
from .views import FetchUser


class OIDCLogin(OAuth2Login):
    scope = SCOPE

    def __init__(self, client_id: str, domains: list[str] | None = None) -> None:
        self.domains = domains
        super().__init__(authorize_url=get_authorize_url(), client_id=client_id, scope=SCOPE)

    def get_authorize_params(self, state: str, redirect_uri: str) -> dict[str, str | None]:
        params = super().get_authorize_params(state, redirect_uri)
        # Google forced `approval_prompt`/`access_type=offline` here; those are
        # Google-specific. For generic OIDC we ask for a refresh token via the
        # standard `prompt`/`access_type` only if your IdP honors them. Cognito
        # issues refresh tokens automatically when the `openid` scope is granted
        # and the app client allows the refresh token grant, so we leave the
        # base params untouched.
        return params


class OIDCProvider(OAuth2Provider):
    name = PROVIDER_NAME
    key = "oidc"

    def __init__(
        self,
        domain: str | None = None,
        domains: list[str] | None = None,
        version: str | None = None,
        **config: Any,
    ) -> None:
        if domain:
            if domains:
                domains.append(domain)
            else:
                domains = [domain]
        self.domains = domains
        version = DATA_VERSION if domains is None else None
        self.version = version
        super().__init__(**config)

    def get_client_id(self) -> str:
        return options.get("auth-oidc.client-id")

    def get_client_secret(self) -> str:
        return options.get("auth-oidc.client-secret")

    def get_auth_pipeline(self) -> list[AuthView]:
        return [
            OIDCLogin(domains=self.domains, client_id=self.get_client_id()),
            OAuth2Callback(
                access_token_url=get_access_token_url(),
                client_id=self.get_client_id(),
                client_secret=self.get_client_secret(),
            ),
            FetchUser(
                client_id=self.get_client_id(),
                domains=self.domains,
                version=self.version,
            ),
        ]

    def get_refresh_token_url(self) -> str:
        return get_access_token_url()

    def build_config(self, state: Mapping[str, Any]) -> dict[str, Any]:
        # `state` won't carry a Google-style `domain`; persist whatever domain
        # restriction (if any) was configured on this provider.
        return {"domains": self.domains or [], "version": DATA_VERSION}

    def build_identity(self, state: Mapping[str, Any]) -> Mapping[str, Any]:
        # Cognito id_token claims look like:
        #   {
        #     "sub": "a1b2c3d4-...",          # stable, unique user id
        #     "iss": "https://cognito-idp.<region>.amazonaws.com/<pool>",
        #     "aud": "<app client id>",
        #     "email": "user@example.com",
        #     "email_verified": true,
        #     "cognito:username": "...",
        #     "name": "Full Name",            # present if the attribute is set
        #     ...
        #   }
        data = state["data"]
        user_data = state["user"]

        # Mirror Google's migration strategy: use the stable `sub` as the id,
        # keeping email as the legacy id so existing accounts are matched.
        user_id = MigratingIdentityId(id=user_data["sub"], legacy_id=user_data["email"])

        # Prefer a real display name; fall back to email if the IdP doesn't
        # send one.
        name = user_data.get("name") or user_data.get("cognito:username") or user_data["email"]

        return {
            "id": user_id,
            "email": user_data["email"],
            "name": name,
            "data": self.get_oauth_data(data),
            "email_verified": user_data.get("email_verified", False),
        }
