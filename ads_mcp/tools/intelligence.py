"""Business-facing tools. Live Google Ads access is strictly read-only."""

from typing import Literal
from fastmcp import FastMCP
from mcp.types import ToolAnnotations
from ads_mcp.intelligence.models import Period, AuditOptions, AlertRule
from ads_mcp.intelligence import reports, engine, auction
from ads_mcp.intelligence.storage import ReportStore, export
from ads_mcp.security import principal, check_customer_scope

intelligence_mcp = FastMCP("intelligence", mask_error_details=True)
READ = ToolAnnotations(
    readOnlyHint=True, destructiveHint=False, openWorldHint=True
)
LOCAL_WRITE = ToolAnnotations(
    readOnlyHint=False, destructiveHint=False, openWorldHint=False
)


@intelligence_mcp.tool(annotations=READ)
def audit_account(
    customer_id: str,
    period: Period,
    login_customer_id: str | None = None,
    campaign_ids: list[str] | None = None,
) -> dict:
    """Audit a live advertiser account: comparable periods, campaigns, daily anomalies, Search share and ranked evidence. Costs use the account currency. No ad changes."""
    return reports.account_audit(
        customer_id, period, login_customer_id, campaign_ids
    )


@intelligence_mcp.tool(annotations=READ)
def analyze_search_terms(
    customer_id: str,
    period: Period,
    options: AuditOptions,
    login_customer_id: str | None = None,
    campaign_ids: list[str] | None = None,
) -> dict:
    """Review actual visible search queries, brand phrases, relevance cues and exposure. Supply target CPA, known tracking state and conversion lag. Never pauses entities."""
    return reports.search_terms(
        customer_id, period, options, login_customer_id, campaign_ids
    )


@intelligence_mcp.tool(annotations=READ)
def analyze_keywords(
    customer_id: str,
    period: Period,
    options: AuditOptions,
    login_customer_id: str | None = None,
    campaign_ids: list[str] | None = None,
) -> dict:
    """Review live keyword costs, conversions and exact text/match-type duplication. Duplicate keywords do not prove internal competition or higher CPC."""
    return reports.search_terms(
        customer_id,
        period,
        options,
        login_customer_id,
        campaign_ids,
        keywords=True,
    )


@intelligence_mcp.tool(annotations=READ)
def analyze_segments(
    customer_id: str,
    period: Period,
    dimension: Literal[
        "device",
        "campaign_device",
        "day_of_week",
        "hour",
        "region",
        "city",
        "ad_group",
    ],
    login_customer_id: str | None = None,
    campaign_ids: list[str] | None = None,
) -> dict:
    """Compare live device, campaign/device, time, geography or ad-group metrics. Geo IDs retain location_type; low-sample flags and causal limitations are explicit."""
    return reports.segments(
        customer_id, period, dimension, login_customer_id, campaign_ids
    )


@intelligence_mcp.tool(annotations=READ)
def inspect_conversion_health(
    customer_id: str, period: Period, login_customer_id: str | None = None
) -> dict:
    """Read conversion-action configuration and reported outcomes. Flags are review cues; cannot verify browser tags, deduplication or CRM lead quality."""
    return reports.conversion_health(customer_id, period, login_customer_id)


@intelligence_mcp.tool(annotations=READ)
def analyze_auction_export(
    csv_text: str,
    period: Period,
    scope: str,
    previous_csv_text: str | None = None,
    previous_period: Period | None = None,
) -> dict:
    """Analyze real English Auction Insights CSV (<=1 MB), preserving percentage bounds. Strip title/date preambles; include Display URL domain and rate columns. This is user-supplied evidence, not live competitor API data. Optional equal-length prior period must have identical filters/dimensions."""
    current = auction.parse_export(csv_text, period, scope)
    if bool(previous_csv_text) != bool(previous_period):
        raise ValueError(
            "Supply both previous CSV and previous period, or neither."
        )
    if previous_csv_text:
        previous = auction.parse_export(
            previous_csv_text, previous_period, scope
        )
        current["comparison"] = auction.compare_exports(current, previous)
        current["previous_period"] = previous["period"]
    return current


@intelligence_mcp.tool(annotations=READ)
def model_budget_scenarios(
    customer_id: str,
    period: Period,
    incremental_spend: float,
    cpc_multipliers: list[float],
    cvr_multipliers: list[float],
    tracking_verified: bool = False,
    conversion_lag_days: int = 7,
    login_customer_id: str | None = None,
    campaign_ids: list[str] | None = None,
) -> dict:
    """Sensitivity model using live historical economics and three explicit CPC/CVR multipliers, ordered conservative/base/optimistic. Not a forecast. Requires mature primary conversions and confirmed tracking. Incremental spend is total for the period, not a daily budget."""
    from datetime import date, timedelta

    if not 0 <= conversion_lag_days <= 90:
        raise ValueError("Conversion lag must be 0–90 days.")
    report = reports.account_audit(
        customer_id, period, login_customer_id, campaign_ids
    )
    mature = period.end < date.fromisoformat(
        report["provenance"]["today_in_account_timezone"]
    ) - timedelta(days=conversion_lag_days)
    if not tracking_verified or not mature:
        return {
            "status": "insufficient_evidence",
            "reason": "Confirm tracking and use a period ending before the conversion-lag cutoff.",
            "provenance": report["provenance"],
        }
    output = engine.scenarios(
        report["overview"], incremental_spend, cpc_multipliers, cvr_multipliers
    )
    return {
        **output,
        "provenance": report["provenance"],
        "baseline": report["overview"],
    }


@intelligence_mcp.tool(annotations=LOCAL_WRITE)
def save_account_audit(
    customer_id: str,
    period: Period,
    login_customer_id: str | None = None,
    campaign_ids: list[str] | None = None,
) -> dict:
    """Run live read-only audit and explicitly save a private report snapshot on this server. Changes only local report storage, never Google Ads. Maximum 100 reports per principal."""
    owner = principal()
    report = reports.account_audit(
        customer_id, period, login_customer_id, campaign_ids
    )
    rid = ReportStore().save(owner, report)
    return {
        "report_id": rid,
        "customer_id": report["provenance"]["customer_id"],
        "recommendation_count": len(report["recommendations"]),
        "retention": "Until explicitly deleted; configure infrastructure retention/backups.",
        "isolation": "Hash of validated Google subject and OAuth audience; stable across refresh. Local stdio uses one local principal.",
    }


@intelligence_mcp.tool(annotations=READ)
def list_saved_audits() -> dict:
    """List snapshots belonging to the current validated Google principal (or local stdio principal). No cross-principal access."""
    rows = ReportStore().list(principal())
    return {"reports": [r for r in rows if _allowed(r["customer_id"])]}


def _allowed(cid):
    try:
        check_customer_scope(cid)
        return True
    except PermissionError:
        return False


def _saved(rid):
    report = ReportStore().get(principal(), rid)
    check_customer_scope(report["provenance"]["customer_id"])
    return report


@intelligence_mcp.tool(annotations=READ)
def get_saved_audit(report_id: str) -> dict:
    """Read a principal-scoped historical snapshot; retrieval does not refresh live account data."""
    return _saved(report_id)


@intelligence_mcp.tool(annotations=READ)
def recommendation_inbox(
    report_id: str, priority: Literal["all", "P0", "P1", "P2", "P3"] = "all"
) -> dict:
    """Return reproducible, ranked recommendations from one saved audit, with evidence, risks, validation and rollback guidance."""
    report = _saved(report_id)
    return {
        "provenance": report["provenance"],
        "recommendations": [
            r
            for r in report["recommendations"]
            if priority == "all" or r["priority"] == priority
        ],
    }


@intelligence_mcp.tool(annotations=READ)
def export_saved_audit(
    report_id: str, format: Literal["json", "markdown", "csv"] = "json"
) -> dict:
    """Return complete JSON/Markdown audit or CSV recommendation inbox as text. No arbitrary server filesystem writes. CSV escapes spreadsheet formulas."""
    return {"format": format, "content": export(_saved(report_id), format)}


@intelligence_mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False, destructiveHint=True, openWorldHint=False
    )
)
def delete_saved_audit(report_id: str) -> dict:
    """Delete only a private local report snapshot for the current principal. Does not delete ads or change advertising settings. Backups may retain copies."""
    _saved(report_id)
    return {"deleted": ReportStore().delete(principal(), report_id)}


@intelligence_mcp.tool(annotations=READ)
def evaluate_alert_rules(report_id: str, rules: list[AlertRule]) -> dict:
    """Evaluate supplied threshold rules against a saved audit. Runs only when invoked; no scheduler, notifications or background monitoring."""
    if not 1 <= len(rules) <= 30:
        raise ValueError("Supply 1–30 alert rules.")
    report = _saved(report_id)
    results = []
    for rule in rules:
        value = report["overview"][rule.metric]
        results.append(
            {
                "rule": rule.model_dump(),
                "value": value,
                "triggered": (
                    None
                    if value is None
                    else (
                        value > rule.threshold
                        if rule.operator == "gt"
                        else value < rule.threshold
                    )
                ),
                "status": "undefined_metric" if value is None else "evaluated",
            }
        )
    return {
        "provenance": report["provenance"],
        "rules": results,
        "scheduled": False,
    }


@intelligence_mcp.tool(annotations=READ)
def preview_campaign_change(
    customer_id: str,
    campaign_id: str,
    proposed_status: Literal["ENABLED", "PAUSED"],
    reason: str,
    login_customer_id: str | None = None,
) -> dict:
    """Read exact current campaign status and prepare a manual change-review worksheet. This does NOT approve or execute a change, and no execute endpoint exists."""
    if not 1 <= len(reason.strip()) <= 1000:
        raise ValueError("Supply a specific reason (1–1000 characters).")
    filters = reports.campaign_filter([campaign_id])
    rows = reports.read(
        customer_id,
        ["campaign.id", "campaign.name", "campaign.status"],
        "campaign",
        filters,
        login_customer_id,
    )
    if len(rows) != 1:
        raise ValueError("Campaign not found or not accessible.")
    return {
        "account": check_customer_scope(customer_id),
        "entity": rows[0],
        "previous_value": rows[0]["campaign.status"],
        "proposed_value": proposed_status,
        "reason": reason,
        "risk": "Pausing stops delivery; enabling can restart spend under existing budget and bidding.",
        "validation_plan": "Confirm the exact advertiser/campaign and review qualified outcomes after conversion lag.",
        "rollback_plan": f"Manually restore campaign status to {rows[0]['campaign.status']} if appropriate; lost time and spend cannot be reversed.",
        "requires_specific_human_approval_before_manual_change": True,
        "executable": False,
        "execution_available": False,
    }


GLOSSARY = {
    "ctr": (
        "Clicks divided by impressions.",
        "Illustrative: 50 clicks / 1,000 impressions = 5%.",
        "Shows how often people click; does not measure lead quality.",
        "Compare relevant traffic and conversion quality before rewriting ads.",
    ),
    "cpc": (
        "Spend divided by clicks.",
        "Illustrative: ₹3,600 / 100 clicks = ₹36 per click.",
        "Connects traffic price to conversion economics.",
        "Check CPA and qualified leads before seeking cheaper clicks.",
    ),
    "cpa": (
        "Spend divided by recorded primary conversions.",
        "Illustrative: ₹3,600 / 4 conversions = ₹900 CPA.",
        "A recorded conversion may be a form, call or sale depending on settings.",
        "Verify conversion definitions and compare with your profitable acquisition target.",
    ),
    "roas": (
        "Recorded conversion value divided by spend.",
        "Illustrative: ₹10,000 value / ₹2,000 spend = 5×.",
        "Revenue return is not profit and assigned values may not be sales.",
        "Validate values, margins and attribution.",
    ),
    "impression_share": (
        "Impressions divided by estimated eligible impressions.",
        "Illustrative: 400 / 1,000 eligible impressions = 40%.",
        "Budget and rank can limit eligible visibility; this is not total market share.",
        "Separate lost share from budget and rank before changing spend.",
    ),
    "conversion_lag": (
        "Time between an ad interaction and a later reported conversion.",
        "Illustrative: a Monday click may convert on Friday.",
        "Recent periods can look worse before outcomes arrive.",
        "Exclude a business-appropriate lag window and rerun the report.",
    ),
    "conversion_rate": (
        "Recorded primary conversions divided by clicks in these tools.",
        "Illustrative: 4 conversions / 100 clicks = 4%.",
        "Includes your selected conversion definitions; multiple actions may exceed 100%.",
        "Validate goals and mature conversion periods.",
    ),
    "ad_rank": (
        "Auction assessment involving bid, ad/landing-page quality, thresholds and context.",
        "Illustrative only: 30% lost Search impression share to rank is a visibility constraint, not a required bid increase.",
        "Increasing budget alone may not solve rank constraints.",
        "Review relevance, experience and bid economics together.",
    ),
}


@intelligence_mcp.tool(annotations=READ)
def explain_metric(
    metric: Literal[
        "ctr",
        "cpc",
        "cpa",
        "roas",
        "impression_share",
        "conversion_lag",
        "conversion_rate",
        "ad_rank",
    ],
) -> dict:
    """Plain-English definition, clearly illustrative numbers, business meaning and next step."""
    return dict(
        zip(
            (
                "meaning",
                "illustrative_example",
                "business_relevance",
                "next_step",
            ),
            GLOSSARY[metric],
        )
    )


@intelligence_mcp.tool(annotations=READ)
def onboarding_check() -> dict:
    """Safe setup status: reports presence of configuration, never credential values. Does not validate live credentials or call Google."""
    import os
    from importlib.metadata import version

    return {
        "mode": (
            "oauth_http"
            if os.getenv("GOOGLE_ADS_MCP_OAUTH_CLIENT_ID")
            else "local_stdio_adc"
        ),
        "legacy_developer_token_configured": bool(
            os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN")
        ),
        "api_access_requirement": "Google Cloud project must have the appropriate Google Ads API access level; legacy developer tokens are optional/ignored following the September 2026 sunset",
        "customer_allowlist_configured": bool(
            os.getenv("GOOGLE_ADS_MCP_ALLOWED_CUSTOMERS")
        ),
        "versions": {p: version(p) for p in ("fastmcp", "mcp", "google-ads")},
        "live_authentication_verified": False,
        "live_ad_mutations_available": False,
        "next_step": "Configure credentials outside chat, call customers_list_accessible_customers, select an advertiser, then intelligence_audit_account with explicit dates.",
    }
