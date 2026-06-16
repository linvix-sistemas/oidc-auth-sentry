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


def split_csv(raw: str | None) -> list[str]:
    # Parse a comma-separated option value into a clean list, dropping blanks
    # and surrounding whitespace. Empty/unset -> empty list.
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def get_name_claims() -> list[str]:
    return split_csv(options.get("auth-oidc.name-claims")) or list(DEFAULT_NAME_CLAIMS)


# Human-readable provider name shown in the Sentry SSO UI. Defaults to "OIDC";
# override via `auth-oidc.provider-name` to rebrand the SSO button/label, e.g.:
#   sentry config set auth-oidc.provider-name "Linvix ID"
PROVIDER_NAME = "OIDC"


def get_provider_name() -> str:
    return options.get("auth-oidc.provider-name") or PROVIDER_NAME


# Name of the id_token claim that carries the user's group memberships, and the
# set of groups allowed to authenticate. An empty `auth-oidc.allowed-groups`
# (the default) imposes no group restriction. The standard OIDC claim is
# `groups`; AWS Cognito emits `cognito:groups`:
#   sentry config set auth-oidc.groups-claim "cognito:groups"
#   sentry config set auth-oidc.allowed-groups "sentry-admins,sentry-users"
DEFAULT_GROUPS_CLAIM = "groups"


def get_groups_claim() -> str:
    return options.get("auth-oidc.groups-claim") or DEFAULT_GROUPS_CLAIM


def get_allowed_groups() -> list[str]:
    return split_csv(options.get("auth-oidc.allowed-groups"))


# Email domains allowed to authenticate. An empty `auth-oidc.allowed-domains`
# (the default) imposes no domain restriction:
#   sentry config set auth-oidc.allowed-domains "example.com,example.org"
def get_allowed_domains() -> list[str]:
    return split_csv(options.get("auth-oidc.allowed-domains"))

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

ERR_NOT_IN_GROUP = (
    "Your account is not a member of a group allowed to authenticate with this provider."
)

DATA_VERSION = "1"
