# Security Policy

## Report vulnerabilities privately

Do not post credentials, HMAC keys, API endpoints containing tokens, or
unredacted server configuration in public issues or pull requests.
Use GitHub's **Report a vulnerability** / private vulnerability reporting
feature if it is enabled for this repository. If it is not enabled, contact
the maintainer through a private channel without disclosing secrets publicly.

## Historical credential exposure (2026-09-06)

See [issue #45](https://github.com/Joker7822/LOTO7_AI_AGENT/issues/45)
and [SECURITY_AND_OOS_AUDIT.md](SECURITY_AND_OOS_AUDIT.md). The former external
database integration is retired; no live database sync or rotation-verification
workflow is retained. Previously exposed credentials remain compromised until
revoked by the authorized external administrator. Removing the integration
does not revoke credentials, erase Git history, or prove incident remediation.

The owner must disable the former endpoint and database access, revoke exposed
credentials, and remove unused GitHub Actions secrets. Do not close the
historical security incident until external revocation is verified.

## Dependency hygiene

Dependabot checks Python requirements and GitHub Actions weekly. Review its
PRs and ensure CI succeeds before merging. Automated dependency update PRs
do not constitute a full software supply-chain audit.

## Lottery integrity

Do not manually overwrite frozen Production predictions, historical
evaluation evidence, or registered future-out-of-sample ledgers. Any
methodology change must be documented and evaluated prospectively, without
using already-seen draw outcomes as evidence of a future predictive edge.
