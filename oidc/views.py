from __future__ import annotations

import logging
from typing import Any

import orjson
from django.http import HttpRequest
from django.http.response import HttpResponseBase
from sentry.auth.helper import AuthHelper
from sentry.auth.view import AuthView
from sentry.utils.signing import urlsafe_b64decode

from .constants import (
    ERR_INVALID_AUDIENCE,
    ERR_INVALID_DOMAIN,
    ERR_INVALID_ISSUER,
    ERR_INVALID_RESPONSE,
    get_issuer,
)

logger = logging.getLogger("sentry.auth.oidc")


class FetchUser(AuthView):
    """
    Adapted from the Google provider's FetchUser.

    Like Google, we decode the `id_token` JWT returned by the token endpoint
    instead of making a separate userinfo call -- Cognito (and any compliant
    OIDC provider) returns the identity claims directly in the id_token.

    Differences vs Google:
      * No reliance on the Google-specific `hd` (hosted domain) claim. Domain
        restriction, if any, is derived from the email address.
      * We validate the `iss` (issuer) and `aud` (audience/client_id) claims,
        which OIDC requires and Google's implementation skipped.
    """

    def __init__(
        self,
        client_id: str,
        domains: list[str] | None,
        version: str | None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self.client_id = client_id
        self.domains = domains
        self.version = version
        super().__init__(*args, **kwargs)

    def dispatch(self, request: HttpRequest, pipeline: AuthHelper) -> HttpResponseBase:
        data: dict[str, Any] | None = pipeline.fetch_state("data")
        assert data is not None

        try:
            id_token = data["id_token"]
        except KeyError:
            logger.exception("Missing id_token in OAuth response: %s", data)
            return pipeline.error(ERR_INVALID_RESPONSE)

        try:
            _, payload_b, _ = map(urlsafe_b64decode, id_token.split(".", 2))
        except Exception as exc:
            logger.exception("Unable to decode id_token: %s", exc)
            return pipeline.error(ERR_INVALID_RESPONSE)

        try:
            payload: dict[str, Any] = orjson.loads(payload_b)
        except Exception as exc:
            logger.exception("Unable to decode id_token payload: %s", exc)
            return pipeline.error(ERR_INVALID_RESPONSE)

        # --- OIDC validation that Google's provider did not do -------------
        # Note: signature verification is intentionally omitted here to mirror
        # the upstream Google provider, which trusts the id_token because it
        # was just retrieved over TLS directly from the token endpoint in the
        # immediately preceding step. If you want full JWKS signature checks,
        # fetch jwks_uri from discovery and verify before trusting claims.
        issuer = get_issuer()
        if issuer and payload.get("iss") != issuer:
            logger.error("id_token issuer mismatch: %s", payload.get("iss"))
            return pipeline.error(ERR_INVALID_ISSUER % (payload.get("iss"),))

        aud = payload.get("aud")
        # `aud` may be a string or a list per the OIDC spec.
        aud_values = aud if isinstance(aud, list) else [aud]
        if self.client_id not in aud_values:
            logger.error("id_token audience mismatch: %s", aud)
            return pipeline.error(ERR_INVALID_AUDIENCE)
        # -------------------------------------------------------------------

        if not payload.get("email"):
            logger.error("Missing email in id_token payload: %s", id_token)
            return pipeline.error(ERR_INVALID_RESPONSE)

        # Optional restriction by email domain. Unlike Google we have no `hd`
        # claim, so we derive the domain from the email address itself.
        if self.domains:
            domain = extract_domain(payload["email"])
            if domain not in self.domains:
                return pipeline.error(ERR_INVALID_DOMAIN % (domain,))

        pipeline.bind_state("user", payload)

        return pipeline.next_step()


def extract_domain(email: str) -> str:
    return email.rsplit("@", 1)[-1]
