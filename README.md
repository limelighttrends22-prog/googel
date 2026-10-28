# Google Ads AI Command Center

**Understand. Diagnose. Prioritize. Improve.**

An explainable, read-only Google Ads intelligence backend for MCP clients.
Built by modifying the supplied Google Ads MCP 0.0.5 project, preserving its
Apache-2.0 license and core discovery/search/metadata capabilities. This is
an independently modified foundation for evaluation, not a claim of complete
SaaS readiness or Google endorsement.

Start with [Windows setup](docs/WINDOWS_SETUP.md),
[ChatGPT connection](docs/CHATGPT_CONNECTION.md), and the
[actual validation results](docs/VALIDATION.md).

## What works

| Capability | Implementation | Evidence boundary |
|---|---|---|
| Original MCP functions | Customer discovery, bounded GAQL, metadata, four reference resources | SDK-backed reads; API credentials required |
| Account audit | Spend, impressions, clicks, CTR, CPC, conversions, CPA, value, ROAS, campaign rows, equal-length previous period, daily changes | Account currency and timezone; null for undefined ratios |
| Recommendation engine | Ten required fields; reproducible heuristic ranking | Verified observations separated from hypotheses; no invented lift |
| Query/keyword review | Review exposure, relevance phrases, user-defined brand split, keyword text/match duplication | Lag/tracking/sample guards; no automatic pause or fake intent model |
| Segments | Device, campaign/device, city/region IDs, weekdays, hour, ad groups | Descriptive; geography semantics retained; no causality claims |
| Conversion review | Action inventory, primary/secondary configuration, action metrics, duplicate-name cues | Cannot prove tag firing, deduplication or lead quality |
| Search participation | Budget/rank lost impression share; current budget/bidding configuration | Current budget is not historical utilization; bounded share values retained |
| Competitor review | Real English Auction Insights CSV import and prior-period comparison | Explicitly user-supplied; restricted API competitor fields not queried |
| Budget scenarios | Three explicit CPC/CVR sensitivities based on live historical economics | Mature data + tracking confirmation; not a forecast or bid simulator |
| Saved audits | Private SQLite snapshots, ranked inbox, JSON/Markdown/CSV text exports, deletion | Single instance; principal-scoped, not full agency tenancy |
| Alerts | Threshold rules evaluated against one saved report | On demand; no scheduler or notifications |
| Safe change review | Exact live campaign status plus proposed manual change worksheet | No execute endpoint; no advertising mutations available |
| Onboarding | Environment doctor and eight plain-language metric explanations | No secret values returned |

**20 MCP tools: 3 preserved, 17 added.** See [tool reference](docs/TOOLS.md).
The MCP client's model handles natural-language questions; this backend does
not embed or bill an independent AI model.

## Quick local evaluation (Python 3.12)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
Copy-Item .env.example .env
.\.venv\Scripts\ads-command-center.exe doctor
```

`doctor` inspects configuration without sending Google Ads requests. With
OAuth variables empty, `serve` uses local stdio and Google Application Default
Credentials. With complete, validated OAuth configuration it serves
authenticated Streamable HTTP; the local default bind is loopback. This server
never starts unauthenticated HTTP through its provided entrypoints.

As of October 28, 2026, new Google Ads API access is configured on the **Google
Cloud project**. Developer tokens were sunset September 9, 2026; the optional
legacy header is retained for compatibility. Follow the live official links in
[setup](docs/WINDOWS_SETUP.md), not old token-onboarding instructions.

## Evaluation and project map

- `ads_mcp/intelligence/`: pure calculations, typed contracts, live adapters,
  Auction Insights CSV parser, private snapshot storage/export.
- `ads_mcp/tools/intelligence.py`: business-facing MCP entrypoints.
- `ads_mcp/query.py`, `security.py`: bounds, timeout/retry and access safeguards.
- `tests/`: preserved/adapted upstream regressions plus intelligence/security
  tests. Test data is synthetic and explicitly labelled.
- `docs/`: architecture, setup, security, commercial requirements and actual results.
- `requirements.lock.txt`: pinned runtime closure; `requirements-dev.lock.txt`:
  evaluated development environment. Locks were resolved on Linux/Python 3.12;
  Windows installation commands are documented but not executed here.
- `LICENSE`, `NOTICE`, `THIRD_PARTY_NOTICES.md`, `THIRD_PARTY_LICENSES/`:
  attribution and dependency license inventory.

No real account data, credentials, OAuth token store, report database or virtual
environment is distributed. No live Google Ads request, OAuth consent login,
ChatGPT connection, container launch, or Windows execution was validated without
user-provided infrastructure and authorization. See the validation report for
what was actually exercised locally.
