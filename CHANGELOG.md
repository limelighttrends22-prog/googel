# 0.1.0 — 2026-10-28

Independent modified distribution based on supplied upstream google-ads-mcp 0.0.5.

- Added 17 business-facing MCP tools alongside the original three.
- Added deterministic metrics, comparisons, ten-field ranked recommendations,
  search/keyword review, segment and conversion review, Search share diagnosis,
  current budgets/bidding context and explicit CPC/CVR sensitivity modelling.
- Added real English Auction Insights CSV import/comparison with preserved rate
  bounds and an explicit public-API competitor-access limitation.
- Added validated-Google-identity-scoped SQLite audit snapshots, recommendation
  inbox, JSON/Markdown/CSV export, threshold evaluation and private deletion.
- Added exact live campaign-status preview with manual rollback guidance; no
  advertising execution or approval-token endpoint was added.
- Hardened OAuth startup, redirects, ADC separation, query inputs, report limits,
  request deadlines, redacted API errors and child-server error masking.
- Removed Docker vendor-authentication downgrade; corrected reference updater
  import, unbounded reference fetches and duplicate continuation risk in the
  original metadata interceptor's exception handling.
- Added dotenv CLI/doctor, current project-based Google Ads onboarding, Windows
  and ChatGPT guides, pinned runtime/dev dependencies, license inventory, real
  tests and documented production gaps.

Intentional compatibility changes: malformed IDs now fail rather than arbitrary
character stripping; raw search has a 10,000-row maximum and uses Search paging;
conditions/orderings default to null; HTTP binds loopback by default and requires
complete secure OAuth configuration. Python import package `ads_mcp` and original
CLI command alias remain available. API v25 is retained explicitly.
