# Architecture and inspection findings

## Original project

The entire supplied archive was enumerated and its source, configuration,
documentation and test files read before modification. It contained Python
package 0.0.5 with FastMCP 4 / MCP 2, v25 SDK references, Apache-2.0 licensing,
three read tools and four remote reference resources. OAuth used FastMCP's
GoogleProvider; local stdio used ADC. Persistent OAuth stores were already
supported, including encryption wrappers.

The original backend was useful as a general query wrapper. Missing product
capabilities were analysis, prioritization, saved audits, report exports, alert
evaluation, business explanations and change-review worksheets. Specific issues:

- Search streamed unrestricted results into memory, logged complete GAQL, used
  mutable list defaults, lacked request deadlines, and returned upstream error
  strings that could echo sensitive query content.
- IDs were produced by stripping arbitrary characters, accepting malformed input.
  Resource metadata interpolated unvalidated names into queries.
- Remote credential handling could fall back to deployment ADC when no request
  token was found. Incomplete OAuth settings silently selected local mode.
- OAuth redirects were unrestricted by default; the shipped Dockerfile changed
  installed vendor code to disable issuer-response protection.
- HTTP bound to all interfaces by default; documentation requests had no timeout.
- The reference-refresh command used an invalid top-level `import utils`.
- No project-specific feature matrix, honest competitor access boundary, realistic
  commercial requirements or October 2026 API onboarding correction was provided.

The untouched source ZIP was preserved separately during development. The final
ZIP contains the new project, not a second full copy of the original archive.
Upstream author/license headers and adapted regression coverage are retained.

## Request path

MCP client → FastMCP parent → configured namespace subserver → typed tool →
report adapter → bounded GAQL reader → authorized Google Ads API v25.
Returned rows feed pure deterministic analysis; the response includes reporting
provenance, metrics, limitations and recommendations. No mutation service is
registered. The client model supplies language understanding; all diagnostic
math is reproducible Python, not an unverifiable model-generated score.

`cli.py` loads an explicit dotenv file before importing server configuration.
`security.py` validates remote origins, paired OAuth credentials, persistent
storage, redirect restrictions and deployment customer allowlists.
`GoogleProvider` handles validated OAuth identities, token refresh and encrypted
OAuth state. Local ADC is never a fallback in OAuth mode. HTTP startup refuses
a transport/authentication mismatch caused by changing environment after import.

`query.py` validates identifiers/clauses, limits rows/fields/conditions, uses the
SDK Search pager, a 30-second RPC timeout and bounded retries for transport-level
unavailable/quota exceptions. GoogleAdsException errors return request ID and
codes without upstream message text; application query contents are not logged.
There is no retry of advertising mutations because none exist. Not every Ads
quota failure is retryable: API-level quota errors are returned for the caller
to handle later. The raw search tool returns up to its documented cap; curated
reports refuse analysis when the cap is hit.

`intelligence/engine.py` has pure weighted calculations, relative/absolute
period changes, literal term classification, duplicate-keyword review, trailing
observed-day anomalies, descriptive segmentation, recommendation ranking and
explicit CPC/CVR scenario equations. Source rows are retained. Null ratios are
undefined, not zero. CTR/CVR/share values are fractions; money is account
currency converted from micros; ROAS is a multiple.

`intelligence/reports.py` owns live reporting queries, account currency/timezone,
fixed periods and previous periods, resource scopes and partial-failure warnings.
Optional Search-share/budget reads can fail with an explicit warning while core
campaign/account data still returns. Conversion inventory identifies configuration
review cues; it does not inspect browser tags or CRM records.

`intelligence/auction.py` imports English Auction Insights CSV exports, preserving
less-than/greater-than bounds and raw dimensions. Comparison requires equal-length,
non-overlapping periods and unique domain/dimension rows. Competitor fields are
not public API data; public campaign Search impression-share diagnostics provide
the strongest live alternative. No competitor budget/strategy inference exists.

`intelligence/storage.py` keeps SQLite report bodies and minimal save/delete event
records. Owners are hashes of Google's validated subject + audience; callers
cannot supply an owner/tenant ID. SQL is parameterized. Snapshots have a 5 MB cap,
100 reports per owner and explicit deletion. Database files are not encrypted by
this module; enforce filesystem encryption/ACLs/backups separately. Event records
are operational history, not a tamper-evident compliance ledger.

## Deliberate boundaries

One installation with multiple authorized users/accounts is supported. Reports
are separated by validated Google identity, but no agency organization, role,
client delegation, subscription, global usage billing or scheduler is implemented.
A saved report retains information originally read by that user; reading a cached
snapshot is not a fresh Google Ads account-permission check. Retention/revocation
policies for a commercial service need additional enforcement.

The API is pinned to v25 to preserve the original integration while improving
its analysis. Latest-version documentation resources remain references, so inspect
v25-compatible fields before sending raw queries. New versions need compatibility
and sunset review, not a blind string substitution. Live field/query eligibility
has not been verified against a real advertiser in this build.
