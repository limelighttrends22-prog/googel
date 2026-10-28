"""Live read adapters with explicit reporting provenance and failure boundaries."""

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from fastmcp.exceptions import ToolError
from ads_mcp.query import execute
from ads_mcp.security import check_customer_scope
from .models import Period, AuditOptions
from .engine import (
    aggregate,
    compare,
    account_recommendations,
    daily_anomalies,
    term_analysis,
    segment_analysis,
    keyword_overlap,
)

METRICS = [
    "metrics.impressions",
    "metrics.clicks",
    "metrics.cost_micros",
    "metrics.conversions",
    "metrics.conversions_value",
]
CAMPAIGN = [
    "campaign.id",
    "campaign.name",
    "campaign.status",
    "campaign.advertising_channel_type",
    "campaign.bidding_strategy_type",
]
CAP = 10000


def read(cid, fields, resource, conditions=None, login=None, order=None):
    rows = execute(cid, fields, resource, conditions, order, CAP, login)
    if len(rows) == CAP:
        raise ToolError(
            "Report reached the 10,000-row safety cap. Narrow the date range or campaign scope; partial data is not analyzed as a complete report."
        )
    return rows


def customer(cid, login=None):
    cid = check_customer_scope(cid)
    rows = read(
        cid,
        [
            "customer.id",
            "customer.descriptive_name",
            "customer.currency_code",
            "customer.time_zone",
            "customer.manager",
        ],
        "customer",
        login=login,
    )
    if len(rows) != 1:
        raise ToolError(
            "Expected one customer; confirm authorized advertiser ID and manager routing."
        )
    if rows[0].get("customer.manager"):
        raise ToolError(
            "Select an advertiser account; manager IDs route access but have no comparable advertiser metrics."
        )
    return rows[0]


def provenance(cid, period, info, login=None, extra=None):
    today = datetime.now(ZoneInfo(info["customer.time_zone"])).date()
    if period.end > today:
        raise ValueError(
            "Report end date is in the future in the account timezone."
        )
    return {
        "customer_id": check_customer_scope(cid),
        "login_customer_id": login,
        "period": period.model_dump(mode="json"),
        "currency": info["customer.currency_code"],
        "account_timezone": info["customer.time_zone"],
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "source": "Google Ads API v25 live reads",
        "filters": [period.condition()] + (extra or []),
        "completeness": "complete within requested resource and API visibility; privacy-suppressed rows may be absent",
        "freshness": "Retrieval time is not conversion finalization time; late conversions can revise this report.",
        "units": "cost/CPC/CPA in account currency; CTR/CVR/share as fractions; ROAS as a multiple; null means undefined",
        "today_in_account_timezone": today.isoformat(),
    }


def campaign_filter(campaign_ids):
    if not campaign_ids:
        return []
    if len(campaign_ids) > 100 or any(
        not str(v).isascii() or not str(v).isdigit() for v in campaign_ids
    ):
        raise ValueError("Use up to 100 numeric campaign IDs.")
    return ["campaign.id IN (" + ",".join(str(v) for v in campaign_ids) + ")"]


def account_audit(cid, period: Period, login=None, campaign_ids=None):
    info = customer(cid, login)
    filters = campaign_filter(campaign_ids)
    meta = provenance(cid, period, info, login, filters)
    prior = period.previous()
    fields = CAMPAIGN + METRICS
    current_rows = read(
        cid, fields, "campaign", [period.condition()] + filters, login
    )
    previous_rows = read(
        cid, fields, "campaign", [prior.condition()] + filters, login
    )
    daily = read(
        cid,
        ["segments.date"] + METRICS,
        "campaign",
        [period.condition()] + filters,
        login,
        ["segments.date ASC"],
    )
    current, previous = aggregate(current_rows), aggregate(previous_rows)
    warnings = []
    share_rows = []
    try:
        share_rows = read(
            cid,
            [
                "campaign.id",
                "campaign.name",
                "metrics.search_impression_share",
                "metrics.search_budget_lost_impression_share",
                "metrics.search_rank_lost_impression_share",
            ],
            "campaign",
            [period.condition(), "campaign.advertising_channel_type = 'SEARCH'"]
            + filters,
            login,
        )
    except ToolError:
        warnings.append(
            "Optional Search impression-share read unavailable; no budget/rank diagnosis made from it."
        )
    budget_rows = []
    try:
        budget_rows = read(
            cid,
            [
                "campaign.id",
                "campaign.name",
                "campaign.bidding_strategy_type",
                "campaign.campaign_budget",
                "campaign_budget.amount_micros",
                "campaign_budget.explicitly_shared",
            ],
            "campaign",
            filters,
            login,
        )
    except ToolError:
        warnings.append(
            "Current budget configuration unavailable; no budget amount inferred."
        )
    recommendations = account_recommendations(current, previous, share_rows)
    if not current_rows:
        warnings.append(
            "No rows returned: no eligible activity, permissions, date scope or filters may explain this; not proof of broken tracking."
        )
    return {
        "schema_version": "1.0",
        "report_type": "account_audit",
        "provenance": meta,
        "account": info,
        "overview": current,
        "previous_period": prior.model_dump(mode="json"),
        "comparison": compare(current, previous),
        "campaigns": [
            {"entity": row, "metrics": aggregate([row])} for row in current_rows
        ],
        "current_budget_configuration": budget_rows,
        "budget_note": "Configuration retrieved now, not historical daily budgets. Shared budgets must not be added once per campaign. No exact historical utilization computed.",
        "bidding_review": [
            {
                "campaign_id": r.get("campaign.id"),
                "strategy": r.get("campaign.bidding_strategy_type"),
                "period_conversions": aggregate([r])["conversions"],
                "next_step": "Confirm strategy objective, primary goals and qualified economics; conversion count alone does not establish a universal eligibility threshold.",
            }
            for r in current_rows
        ],
        "search_impression_share": share_rows,
        "share_note": "Google share metrics can use bounded sentinel values (e.g. 0.0999 for below 10%); raw values are preserved and are not precise measurements at the bounds.",
        "daily": daily,
        "anomalies": daily_anomalies(daily),
        "recommendations": recommendations,
        "warnings": warnings
        + [
            "Conversion count reflects configured primary actions, not verified qualified leads or sales.",
            "Historical comparisons are descriptive; changes in budget, weekdays and attribution can confound them.",
            "No exact budget-utilization percentage: daily budgets can be shared, change over time and permit daily overdelivery.",
        ],
        "execution": "read_only_no_live_mutations",
    }


def search_terms(
    cid,
    period,
    options: AuditOptions,
    login=None,
    campaign_ids=None,
    keywords=False,
):
    info = customer(cid, login)
    filters = campaign_filter(campaign_ids)
    meta = provenance(cid, period, info, login, filters)
    resource = "keyword_view" if keywords else "search_term_view"
    extra = (
        [
            "ad_group_criterion.criterion_id",
            "ad_group_criterion.keyword.text",
            "ad_group_criterion.keyword.match_type",
        ]
        if keywords
        else ["search_term_view.search_term", "search_term_view.status"]
    )
    fields = (
        ["campaign.id", "campaign.name", "ad_group.id", "ad_group.name"]
        + extra
        + METRICS
    )
    rows = read(
        cid,
        fields,
        resource,
        [period.condition()] + filters,
        login,
        ["metrics.cost_micros DESC"],
    )
    today = datetime.now(ZoneInfo(info["customer.time_zone"])).date()
    mature = period.end < today - timedelta(days=options.conversion_lag_days)
    output = term_analysis(rows, options, mature)
    return {
        "schema_version": "1.0",
        "report_type": resource,
        "provenance": meta,
        "options": options.model_dump(),
        "analysis": output,
        "rows": rows,
        "overlap": keyword_overlap(rows) if keywords else [],
        "limitations": [
            "Search term visibility is privacy-limited and may exclude substantial spend.",
            "Word/phrase matching is a transparent heuristic, not a semantic intent classifier.",
            "Conversion lag is user supplied, not measured from this report.",
            "Zero conversions never triggers automatic pausing.",
        ],
    }


DIMENSIONS = {
    "device": ("campaign", ["segments.device"]),
    "campaign_device": (
        "campaign",
        ["campaign.id", "campaign.name", "segments.device"],
    ),
    "day_of_week": ("campaign", ["segments.day_of_week"]),
    "hour": ("campaign", ["segments.hour"]),
    "region": (
        "geographic_view",
        [
            "geographic_view.country_criterion_id",
            "geographic_view.location_type",
            "segments.geo_target_region",
        ],
    ),
    "city": (
        "geographic_view",
        [
            "geographic_view.country_criterion_id",
            "geographic_view.location_type",
            "segments.geo_target_city",
        ],
    ),
    "ad_group": ("ad_group", ["campaign.id", "ad_group.id", "ad_group.name"]),
}


def segments(cid, period, dimension, login=None, campaign_ids=None):
    if dimension not in DIMENSIONS:
        raise ValueError("Unsupported dimension.")
    info = customer(cid, login)
    filters = campaign_filter(campaign_ids)
    meta = provenance(cid, period, info, login, filters)
    resource, dims = DIMENSIONS[dimension]
    rows = read(
        cid, dims + METRICS, resource, [period.condition()] + filters, login
    )
    return {
        "report_type": "segments",
        "provenance": meta,
        "dimension": dimension,
        "analysis": segment_analysis(rows, dims),
        "rows": rows,
        "geo_note": "Geographic IDs are returned as IDs; location_type distinguishes physical presence and area of interest. Resolve IDs via geo_target_constant metadata/search. Campaign targeting is a separate configuration.",
    }


def conversion_health(cid, period, login=None):
    info = customer(cid, login)
    meta = provenance(cid, period, info, login)
    inventory = read(
        cid,
        [
            "conversion_action.id",
            "conversion_action.name",
            "conversion_action.status",
            "conversion_action.type",
            "conversion_action.category",
            "conversion_action.primary_for_goal",
            "conversion_action.counting_type",
        ],
        "conversion_action",
        login=login,
    )
    metrics = read(
        cid,
        [
            "segments.conversion_action",
            "segments.conversion_action_name",
            "segments.conversion_action_category",
            "metrics.conversions",
            "metrics.all_conversions",
            "metrics.conversions_value",
        ],
        "customer",
        [period.condition()],
        login,
    )
    names = {}
    for row in inventory:
        names.setdefault(
            str(row.get("conversion_action.name", "")).casefold(), []
        ).append(row.get("conversion_action.id"))
    duplicate_names = {name: ids for name, ids in names.items() if len(ids) > 1}
    return {
        "report_type": "conversion_health",
        "provenance": meta,
        "inventory": inventory,
        "metrics_by_action": metrics,
        "review_flags": {
            "duplicate_names": duplicate_names,
            "no_visible_active_primary_actions": not any(
                r.get("conversion_action.status") == "ENABLED"
                and r.get("conversion_action.primary_for_goal")
                for r in inventory
            ),
        },
        "limitations": [
            "Duplicate names are a review cue, not proof that events are duplicated.",
            "Cross-account conversion actions may be owned by a manager and not appear in this advertiser inventory.",
            "No tag execution, consent diagnostics, event deduplication, CRM or offline sale reconciliation is performed.",
            "Review campaign-level goals too; primary_for_goal alone does not prove campaign optimization inclusion.",
        ],
    }
