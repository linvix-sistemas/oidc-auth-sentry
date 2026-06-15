# Changelog

All notable changes to this project are documented here.
This project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.1] - 2026-06-15
### Added
- Configurable display-name claim chain via the `auth-oidc.name-claims` option
  (comma-separated, ordered fallback). Defaults to standard OIDC claims
  (`name,preferred_username,email`).

### Changed
- Replaced the hardcoded Cognito-specific `cognito:username` claim in the
  display-name resolution with the configurable, OIDC-standard claim chain.

## [0.1.0] - 2026-06-15
### Added
- Generic OpenID Connect SSO provider for self-hosted Sentry, adapted from the
  built-in Google provider.
- Issuer (`iss`) and audience (`aud`) validation on the `id_token`.
- Optional email-domain restriction.
- `sentry.apps` entry point for automatic provider registration.
- GitHub Actions CI (lint + test matrix) and tag-triggered release to PyPI via
  trusted publishing.
