# Security model and pre-connection checklist

## Enforced by this build

- Provided entrypoints allow stdio/ADC locally or OAuth-authenticated HTTP.
  Partial OAuth settings fail closed; HTTP does not fall back to server ADC.
- Canonical HTTPS OAuth origin, stable signing key, persistent encrypted OAuth
  storage and exact HTTPS MCP redirect allowlist are required in HTTP mode.
- FastMCP GoogleProvider validates upstream identity/audience/scopes and uses
  authorization code/PKCE, consent and refresh. Vendor issuer-response protection
  remains enabled. No source patches disable authentication safeguards.
- IDs, field/resource names, query clauses, periods, sample options, scenarios,
  CSV imports and local report sizes/counts are bounded and validated.
- Advertising methods are read-only; there is no mutation endpoint. Explicit
  save/delete operations only affect server-local report data.
- Principal IDs hash Google's validated subject and OAuth audience. Callers cannot
  choose them through tool parameters. Snapshot SQL is parameterized. Report IDs
  alone do not grant access. Current deployment customer allowlists are enforced
  again when reading cached reports.
- Application queries and raw upstream API error messages are not logged by the
  query adapter; clients receive error codes/request IDs. HTTP access logs are
  disabled in the provided server entrypoint. Child servers mask unexpected error
  details; framework validation errors remain available for invalid schemas.
- Secrets, ADC credentials, OAuth state, SQLite files and real report data are
  excluded from the deliverable and ignored in Git.
- CSV exports escape spreadsheet formula prefixes. Tool descriptions distinguish
  real API evidence, user-supplied exports, hypotheses and illustrative numbers.

## Operator checklist before real accounts

- [ ] Use a dedicated approved Cloud project and Google user with read-only Ads
  permissions where practical. Never share credentials in a prompt.
- [ ] Review requested Google scopes and consent. `adwords` is broad; no separate
  read-only Ads OAuth scope is available. Do not deploy other mutation code with
  these credentials assuming the scope itself prevents writes.
- [ ] Configure TLS, exact public origin and exact Google/MCP callback allowlists.
- [ ] Store secrets outside source with stable signing/encryption keys. Restrict
  secret-manager and file ACL access; keep encrypted backups and key recovery.
- [ ] Restrict intended advertisers with `GOOGLE_ADS_MCP_ALLOWED_CUSTOMERS`.
- [ ] Verify anonymous/invalid tokens fail and a different Google identity cannot
  list, read or delete another identity's reports. Test refresh and revocation.
- [ ] Secure the report database and OAuth directory. OAuth values are encrypted
  by the configured wrapper, but **report bodies are plaintext SQLite**. Use
  encrypted disks and restrictive Windows ACLs; chmod only applies on POSIX.
- [ ] Set retention, cleanup and backup/deletion policies. No automatic retention
  job exists. Deleted reports may remain in SQLite free pages, backups or the
  minimal event table; deletion is not cryptographic erasure.
- [ ] Verify account currency/timezone, conversion goals, lag, tracking and API
  totals before using recommendations. Do not paste sensitive search queries
  into unrelated services.
- [ ] Enforce ingress request/concurrency/rate/body limits, egress policy and
  spend monitoring for your deployment. The application bounds work per call
  but does not implement a public SaaS abuse-prevention gateway.
- [ ] Review dependencies, licenses, security advisories and v25 sunset dates.
  Run live tests on test accounts before admitting production advertisers.

## Remaining security work for a commercial service

Independent review/penetration testing, organization membership, role grants,
client delegation, billing-level quotas, global rate limiting, secret rotation,
GDPR/DPDP/data agreements as applicable, retention/revocation policies, alerting,
secure operational access and incident handling are operator/product work.
SQLite history is not an immutable security audit log. A cached report is private
to its original Google identity but does not re-check current advertiser access
on every read. Local stdio trusts the OS user and is not a network-user boundary.
Do not serve multiple agencies under one shared ADC identity.

Treat search terms, campaign names and imported CSV cells as untrusted data, not
instructions for the host model. No report text can authorize an ad change.
No security certification, penetration test or zero-vulnerability guarantee is
claimed. See VALIDATION.md for the exact offline checks performed.
