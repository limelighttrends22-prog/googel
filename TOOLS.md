# Tool reference

Default namespace prefixes below are actual advertised tool names. Change
`ads_mcp/tools_config.yaml` or set `GOOGLE_ADS_MCP_TOOLS_CONFIG` to an explicit
configuration file to disable categories/tools or change prefixes.
All live advertising access is read-only. Local snapshot changes are explicit.

| Tool | Inputs / result |
|---|---|
| `customers_list_accessible_customers` | Directly accessible customer IDs; not recursive manager enumeration |
| `metadata_get_resource_metadata` | `resource_name`, optional manager routing → selectable/filterable/sortable fields |
| `search_search` | customer, fields, resource, optional conditions/orderings/limit/manager → bounded raw rows |
| `intelligence_audit_account` | customer, period, optional manager/campaign IDs → overview, prior period, campaigns, daily rows, budget/rank cues, ranked recommendations |
| `intelligence_analyze_search_terms` | customer, period, options, optional manager/campaign IDs → visible query review, opportunities, brand split |
| `intelligence_analyze_keywords` | same → keyword review and duplicate text/match-type evidence |
| `intelligence_analyze_segments` | customer, period, dimension, optional manager/campaign IDs → grouped metrics and low-click flags |
| `intelligence_inspect_conversion_health` | customer, period, optional manager → action inventory, action metrics and review flags |
| `intelligence_analyze_auction_export` | CSV text, period, exact scope, optional previous CSV + period → bounded rates and changes |
| `intelligence_model_budget_scenarios` | customer, period, incremental spend, three CPC multipliers, three CVR multipliers, tracking confirmation, lag, optional manager/campaign IDs → sensitivity scenarios or insufficient evidence |
| `intelligence_save_account_audit` | same scope as audit → fresh audit persisted; returns report ID; local write |
| `intelligence_list_saved_audits` | no arguments → private snapshot IDs |
| `intelligence_get_saved_audit` | report ID → complete historical report |
| `intelligence_recommendation_inbox` | report ID, optional priority → ranked snapshot recommendations |
| `intelligence_export_saved_audit` | report ID, format json/markdown/csv → export text; CSV contains recommendations |
| `intelligence_delete_saved_audit` | report ID → delete result; destructive local write |
| `intelligence_evaluate_alert_rules` | report ID + 1–30 typed rules → triggered/false/undefined; no background execution |
| `intelligence_preview_campaign_change` | customer, campaign ID, proposed status, reason, optional manager → exact old/new values and manual review worksheet; never executes |
| `intelligence_explain_metric` | ctr/cpc/cpa/roas/impression_share/conversion_lag/conversion_rate/ad_rank → meaning, illustrative example, relevance, next step |
| `intelligence_onboarding_check` | no arguments → redacted configuration and dependency versions; no credential test |

## Common contracts

Customer IDs: 10 ASCII digits or `123-456-7890`. Campaign IDs: numeric strings.
Period: `{"start":"2026-09-01","end":"2026-09-30"}` (illustrative), ordered,
at most 366 days, not ending in the future for the account timezone. `login_customer_id`
is optional manager routing; never treat a manager as an advertiser.

Raw search defaults to 10,000 rows; reaching its selected limit can mean partial
data. Curated reports reject cap-hit datasets instead of analysing incomplete
totals. Narrow dates/campaigns when needed. SearchStream was replaced with a bounded
Search pager; tool names and raw row shape remain compatible. Conditions/orderings
now accept arrays or null. Malformed IDs and unsafe query clauses are rejected.
Live API field compatibility is authoritative: call metadata, then choose compatible
fields; selectable fields are not a guarantee that every combination is valid.

Audit overview covers campaign types returned by Google, including Search,
Shopping and Performance Max. Specialized PMax asset/audience reports are not
implemented. Campaign metrics do not make all Search metrics applicable to PMax.

`AuditOptions`:

```json
{
  "target_cpa": 900,
  "conversion_lag_days": 7,
  "tracking_verified": false,
  "min_clicks": 30,
  "brand_terms": ["HCP Wellness", "HCP"],
  "irrelevant_terms": ["jobs", "free course"]
}
```

These are illustrative business inputs, not measured recommendations for an
account. Non-converting terms require minimum clicks and at least 2× target CPA
spend for cost-based review. Irrelevance phrases create review cues even with
small samples. Unverified tracking or an immature period lowers actionability.
The tool never pauses a term, and review exposure is not guaranteed wasted spend.
Maturity requires the period to end **before** today's date minus the supplied
conversion-lag days. The lag is a caller assumption, not measured attribution data.

## Scenarios

Provide ordered CPC multipliers such as `[1.2,1.0,0.8]` and CVR multipliers such
as `[0.8,1.0,1.2]` only when defensible for your business. These numbers are an
illustration, not default claims about how Google auctions will respond.
The tool requires verified tracking, mature dates, >=30 clicks, >=10 primary
conversions, positive historical CPC/CVR and explicit assumptions. It does not
ensure your chosen multipliers really are conservative/optimistic; inspect them.
Incremental spend is total for that same length of time, in the account currency.
No causal, saturation or demand model is implied.

## Auction exports

Export an English Google Ads Auction Insights table, then remove title/date
preamble rows. First row must be the real CSV header. Header examples:
`Display URL domain,Impression share,Overlap rate,Position above rate,Outranking share,Top of page rate,Abs. top of page rate`.
Percentage examples: `42.5%`, `<10%`, `>90%`, `--`. Max 1 MB and 1,000 participants.
Copy exact date/filter scope separately; this metadata is user asserted, not API
verified. Never average rates without the correct denominators. A clearly
synthetic example is provided in `examples/auction-insights-synthetic.csv`.

## Recommendations and alerts

Every recommendation has finding, evidence, diagnosis/alternatives, recommended
action, P0–P3 priority, expected impact/assumptions, confidence, risk, validation
and rollback. Rank score = 4×urgency + 3×evidence quality + 2×business value − risk
− effort. Components are included. This is transparent triage, not validated
financial utility or an independent causal model. Global report provenance
provides dates, currency, account, query filters and retrieval time for the
recommendation evidence rows. Do not report an inner row without its envelope.

Alert rule example: `{"metric":"cpa","operator":"gt","threshold":1200}`.
This is a caller-supplied threshold, not a proposed business target. Undefined
CPA/ROAS returns `triggered: null`, not a misleading pass/fail.

## No live write protocol

No pause/update-budget/negative-keyword/execute tool exists. The status preview
shows a proposed manual operation and requires specific human approval before
any external implementation. It never claims success or returns an executable
approval token. A future write service must independently authenticate the
approver, bind approval to exact state/diff/account/expiry, check stale values,
perform API validation, enforce idempotency, audit outcomes, verify resulting
state and provide rollback. None of that is claimed as implemented here.
