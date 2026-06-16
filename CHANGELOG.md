# Changelog

All notable changes to this project are documented here.
This project adheres to [Semantic Versioning](https://semver.org/).

## [0.2.1] - 2026-06-16
### Fixed
- Documentation: corrected the identity-mapping table (display-name fallback is
  `name → preferred_username → email`) and removed stale text describing the
  old, inert domain-restriction behavior.
- CI: fixed `ruff format` violation in `oidc/constants.py` (missing blank line).

### Changed
- Documentation: consolidated the optional `auth-oidc.*` settings into a single
  reference table and added a troubleshooting row for domain/group denials.

## [0.2.0] - 2026-06-16
### Added
- Customizable provider display name via the `auth-oidc.provider-name` option
  (default `OIDC`), e.g. to rebrand the SSO label to `Custom SSO`.
- Optional access control by group membership via `auth-oidc.groups-claim`
  (default `groups`; Cognito uses `cognito:groups`) and `auth-oidc.allowed-groups`
  (comma-separated; empty = no restriction).
- Optional access control by email domain via `auth-oidc.allowed-domains`
  (comma-separated; empty = no restriction). Exposes configuration for the
  previously inert domain-restriction logic.

### Changed
- Access control (domains) now reads from options at login time instead of the
  unused per-provider `domain`/`domains` config. Removed the orphaned
  `__init__` plumbing from the provider; `build_config` persists only the data
  version marker.

## [0.1.2] - 2026-06-15
### Fixed
- Register the `auth-oidc.*` options with Sentry's option manager in
  `AppConfig.ready()`. Without registration, reading any of them raised
  `UnknownOption` (HTTP 500 when configuring the provider) and produced
  "Unknown config option found" warnings at boot. Mirrors the built-in Google
  provider's approach.

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
