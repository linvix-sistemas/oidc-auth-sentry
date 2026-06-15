from sentry import options

# ---------------------------------------------------------------------------
# Adapted from sentry/auth/providers/google/constants.py
#
# Google hardcodes its OAuth2 endpoints. For a generic OIDC provider (e.g. AWS
# Cognito) we read them from Sentry options so the same code works against any
# issuer. Populate these from your IdP's discovery document:
#   https://<issuer>/.well-known/openid-configuration
#
# For a Cognito User Pool the issuer is:
#   https://cognito-idp.<region>.amazonaws.com/<user_pool_id>
# and the OAuth endpoints live under your Hosted UI domain:
#   https://<your-domain>.auth.<region>.amazoncognito.com
# ---------------------------------------------------------------------------


def get_authorize_url() -> str:
    # Cognito: https://<domain>/oauth2/authorize
    return options.get("auth-oidc.authorize-url")


def get_access_token_url() -> str:
    # Cognito: https://<domain>/oauth2/token
    return options.get("auth-oidc.token-url")


def get_issuer() -> str:
    # Cognito: https://cognito-idp.<region>.amazonaws.com/<user_pool_id>
    # Used to validate the `iss` claim on the id_token.
    return options.get("auth-oidc.issuer")


# Ordered list of id_token claims tried when building the user's display
# name -- the first present, non-empty claim wins, with email as the final
# fallback. Defaults to standard OIDC claims. Override via the
# `auth-oidc.name-claims` option (comma-separated) if your IdP uses a
# non-standard claim. AWS Cognito, for example, emits `cognito:username`
# instead of the standard `preferred_username`:
#   sentry config set auth-oidc.name-claims "name,cognito:username,email"
DEFAULT_NAME_CLAIMS = ["name", "preferred_username", "email"]


def get_name_claims() -> list[str]:
    raw = options.get("auth-oidc.name-claims")
    if not raw:
        return list(DEFAULT_NAME_CLAIMS)
    claims = [c.strip() for c in raw.split(",")]
    return [c for c in claims if c] or list(DEFAULT_NAME_CLAIMS)


# Human-readable provider name shown in the Sentry SSO UI.
PROVIDER_NAME = "OIDC"

# OIDC requires the `openid` scope; `email`/`profile` give us identity claims.
SCOPE = "openid email profile"

ERR_INVALID_DOMAIN = (
    "The domain for your account (%s) is not allowed to authenticate with this provider."
)

ERR_INVALID_RESPONSE = (
    "Unable to fetch user information from the OIDC provider. Please check the log."
)

ERR_INVALID_ISSUER = "The id_token was issued by an unexpected issuer (%s)."

ERR_INVALID_AUDIENCE = "The id_token audience does not match this client."

DATA_VERSION = "1"
