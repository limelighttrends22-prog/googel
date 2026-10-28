# Actual validation results

Build date: 2026-10-28. Execution environment: Linux, Python 3.12.14.
All account/campaign/query/auction fixtures are synthetic. No private advertiser
credentials were supplied, requested in chat or used.

| Check | Actual result |
|---|---|
| Original unmodified upstream regressions | 64 passed, 3 skipped (optional Redis/Firestore packages absent); smoke/LLM excluded from baseline |
| Final combined unit, regression, security and stdio smoke suite | **129 passed, 3 skipped** in the recorded run |
| Skips | One Redis-store mock test; two Firestore-store mock tests because optional backend packages were not installed |
| MCP registration | 20 tools and 4 resources; tool JSON schemas validated; real in-process MCP calls for audit/glossary; stdio subprocess tool/resource discovery compared with regenerated golden snapshots |
| HTTP application | Actual local ASGI requests: anonymous `/mcp` → 401, synthetic invalid token → 401; OAuth discovery → 200; PKCE S256 and issuer-response support enabled |
| Input and failure handling | Invalid IDs, clauses, date bounds, nonfinite/negative metrics, excessive rows, malformed percentages, duplicate auction rows and insufficient evidence exercised |
| Analysis | Weighted metrics, undefined ratios, fractional conversions, comparison periods, lag/tracking guards, exact phrase classification, duplicate keywords, segments, anomalies and scenario formulas exercised |
| Saved reports | Owner separation, quota, deletion, export consistency/formula escaping, stable identity over token rotation and empty-path fallback exercised |
| Read-only safety | No mutation/execute tool registered; preview retains exact current/proposed state and returns execution unavailable; remote ADC fallback blocked |
| Syntax | `python -m compileall -q ads_mcp` passed |
| Formatting | Black check passed for all 51 Python source/test files |
| Installed dependency consistency | `python -m pip check`: no broken requirements |
| Dependency advisory query | `pip-audit` against the 80-package runtime lock: no known vulnerabilities returned at build time; not a security certification or future guarantee |
| Installation | Editable install plus clean wheel install into a separate virtual environment succeeded; installed wheel registered 20 tools and answered a real stdio glossary tool call; both environments passed pip check |

The archive and Python distribution build checks are recorded in
`PACKAGING_VALIDATION.json`; raw final test output and dependency audit output
are in `validation/`. Timing is observed for this environment, not a product
performance benchmark. The pinned dependency inventory includes licenses/notices
where installed distributions supply them; missing license files are explicitly
marked in THIRD_PARTY_NOTICES.md for upstream review.

## Intentional upstream test updates

The untouched archive's regression suite was run first. Tests in the improved
project retain coverage but update changed contracts: bounded Search paging
instead of unbounded SearchStream, RPC deadlines/retry options, strict malformed-ID
rejection, nullable array defaults, redacted error messages, loopback bind and
safer OAuth startup settings. Smoke goldens were regenerated for 20 tools. The
original reference generator now imports its own package correctly. These changes
are documented; no failing test was merely disabled to claim success.

## Precisely unverified

- Live Google Ads credentials, actual query field compatibility/eligibility,
  authorized manager routing and reconciliation against the UI.
- Real Google consent, refresh/revocation and ChatGPT tool invocation through a
  deployed public HTTPS endpoint. Synthetic HTTP tests do not prove this flow.
- Windows installation/runtime, Docker build/run, TLS proxy and cloud deployment.
  Windows/Linux GitHub Actions checks are supplied but not executed here.
- Redis/Firestore optional backends and multi-instance deployment.
- Browser tag execution, event deduplication, qualified leads, offline sales,
  attribution correctness, causal uplift or business impact forecasting.
- Upstream optional LLM tool-selection tests: require a separate model service/key
  and are excluded from the offline suite. No model quality benchmark is claimed.
- Production traffic, load/soak tests, penetration testing and formal legal/license
  review. Dependency-advisory results can change after this build.

No live advertising write was attempted. No such endpoint is implemented.
