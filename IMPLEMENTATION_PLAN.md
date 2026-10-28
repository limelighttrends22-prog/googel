# Implementation plan based on the supplied archive

Original: Apache-2.0 Google LLC project, package 0.0.5; Python >=3.10;
FastMCP 4, MCP 2, Google Ads SDK with v25 imports. Three mounted tools,
four documentation resources, ADC for stdio, GoogleProvider OAuth for HTTP,
optional encrypted client storage. No mutation tool exists.

1. Preserve upstream source, license, authors and tests in a separate copy.
2. Bound/validate GAQL and API calls; redact query/error logging; require a
   remote user token rather than falling back to server ADC. Fail startup
   for incomplete OAuth or unsafe remote configuration.
3. Add typed read-only account audits, search-term/keyword and segment
   analysis, conversion inventory, Search impression-share diagnosis,
   honest Auction Insights export analysis, explicit elasticity scenarios.
4. Return evidence envelopes, comparable periods, sample/lag safeguards,
   transparent recommendation ranking and all ten recommendation fields.
5. Add principal-scoped SQLite saved reports/inbox, JSON/Markdown/CSV exports,
   threshold evaluation, configuration doctor and glossary. No live writes;
   change previews are guidance, never executable approval tokens.
6. Test pure math, edge cases, live adapters with mocks, MCP schemas and
   transport, authorization, storage separation and packaging. Preserve and
   run upstream regression tests; explain intentional contract changes.
7. Document Windows/OAuth/ChatGPT setup, commercial boundaries, licenses,
   operational costs, unsupported features and real test results.
