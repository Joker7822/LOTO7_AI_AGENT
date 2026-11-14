# Security Policy

## Report vulnerabilities privately

Do not post credentials, HMAC keys, API endpoints containing tokens, or
unredacted server configuration in public issues or pull requests.
Use GitHub's **Report a vulnerability** / private vulnerability reporting
feature if it is enabled for this repository. If it is not enabled, contact
the maintainer through a private channel without disclosing secrets publicly.

## Known credential exposure (2026-09-06)

See [issue #45](https://github.com/Joker7822/LOTO7_AI_AGENT/issues/45)
and [SECURITY_AND_OOS_AUDIT.md](SECURITY_AND_OOS_AUDIT.md). Previously
committed Sakura database and HMAC credentials must be treated as exposed.
Deleting the configuration file, rewriting Git history, or adding a CI guard
**does not revoke leaked secrets**.

A maintainer with authorization over Sakura and GitHub Actions must:

1. Rotate the Sakura database password and HMAC key to independent, random
   values and update the corresponding server/GitHub Actions settings.
2. Verify that the new credentials work and the old credentials have been
   disabled, using a private, audited operational process.
3. Run the repository's credential-rotation verification workflow and confirm
   its live database transaction and generation check.
4. Confirm production sync actually succeeds rather than merely taking the
   documented fail-closed skip path.
5. Record the completion status without publishing credential material.

Until this is independently verified, **do not describe the incident as
remediated**. The application intentionally blocks unverified network syncs.
Only the server/account owners can complete rotation; a pull request cannot.

## Dependency hygiene

Dependabot checks Python requirements and GitHub Actions weekly. Review its
PRs and ensure CI succeeds before merging. Automated dependency update PRs
do not constitute a full software supply-chain audit.

## Lottery integrity

Do not manually overwrite frozen Production predictions, historical
evaluation evidence, or registered future-out-of-sample ledgers. Any
methodology change must be documented and evaluated prospectively, without
using already-seen draw outcomes as evidence of a future predictive edge.
