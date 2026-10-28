"""Deterministic diagnostics; every conclusion retains its input evidence."""

import math
import re
from collections import defaultdict
from statistics import mean, pstdev
from .models import AuditOptions


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def finite(value):
    number = float(value or 0)
    if not math.isfinite(number) or number < 0:
        raise ValueError("Metrics must be finite and non-negative.")
    return number


def aggregate(rows):
    totals = {
        k: 0.0
        for k in (
            "cost",
            "impressions",
            "clicks",
            "conversions",
            "conversion_value",
        )
    }
    for row in rows:
        for key, field in (
            ("cost", "cost_micros"),
            ("impressions", "impressions"),
            ("clicks", "clicks"),
            ("conversions", "conversions"),
            ("conversion_value", "conversions_value"),
        ):
            totals[key] += finite(row.get(f"metrics.{field}")) / (
                1_000_000 if key == "cost" else 1
            )
    totals.update(
        ctr=ratio(totals["clicks"], totals["impressions"]),
        average_cpc=ratio(totals["cost"], totals["clicks"]),
        conversion_rate=ratio(totals["conversions"], totals["clicks"]),
        cpa=ratio(totals["cost"], totals["conversions"]),
        roas=ratio(totals["conversion_value"], totals["cost"]),
    )
    return totals


def compare(current, previous):
    return {
        key: {
            "current": current[key],
            "previous": previous[key],
            "absolute_change": (
                None
                if current[key] is None or previous[key] is None
                else current[key] - previous[key]
            ),
            "relative_change": (
                None
                if current[key] is None or not previous[key]
                else (current[key] - previous[key]) / previous[key]
            ),
        }
        for key in current
    }


def rec(
    code,
    finding,
    evidence,
    action,
    priority="P2",
    confidence="medium",
    diagnosis=None,
    risk=None,
    impact=None,
    validation=None,
    rollback=None,
    effort=2,
):
    # Transparent triage score; no invented currency impact.
    urgency = {"P0": 4, "P1": 3, "P2": 2, "P3": 1}[priority]
    quality = {"high": 3, "medium": 2, "low": 1}[confidence]
    business_value = 3 if priority in ("P0", "P1") else 2
    risk_level = 1 if code in ("tracking", "conversion_inventory") else 2
    return dict(
        id=code,
        finding=finding,
        evidence=evidence,
        diagnosis=diagnosis
        or {
            "hypothesis": "Observed association needs validation.",
            "alternatives": [
                "Conversion delay",
                "Traffic mix",
                "Measurement changes",
            ],
        },
        recommended_action=action,
        priority=priority,
        expected_impact=impact
        or {
            "estimate": "Qualitative: improve decision quality; no guaranteed savings.",
            "assumptions": "Validate measurement and traffic quality first.",
        },
        confidence=confidence,
        risk=risk or "Restricting traffic can remove future qualified leads.",
        validation_plan=validation
        or "Verify tracking; compare matched weekdays after the conversion lag with qualified outcomes.",
        rollback_plan=rollback
        or "Record original settings; restore them manually if the controlled test harms qualified outcomes.",
        ranking={
            "score": urgency * 4
            + quality * 3
            + business_value * 2
            - risk_level
            - effort,
            "urgency": urgency,
            "evidence_quality": quality,
            "business_value": business_value,
            "risk": risk_level,
            "effort": effort,
        },
    )


def account_recommendations(current, previous, campaigns):
    output = []
    if current["clicks"] >= 30 and current["conversions"] == 0:
        output.append(
            rec(
                "tracking",
                "Clicks have no recorded primary conversions.",
                current,
                "Test a form/call conversion end to end and review primary conversion actions before changing bids.",
                "P0",
                "high",
                diagnosis={
                    "hypothesis": "Missing conversion signals or unproductive traffic.",
                    "alternatives": [
                        "Long conversion delay",
                        "No genuine leads yet",
                        "Conversions recorded as secondary",
                    ],
                },
                risk="Test conversions can contaminate reporting if not identified.",
                rollback="Remove test events through supported adjustment workflows; restore documented conversion settings if needed.",
            )
        )
    if (
        previous["conversions"] >= 20
        and current["conversion_rate"] is not None
        and previous["conversion_rate"]
        and current["conversion_rate"] < previous["conversion_rate"] * 0.7
    ):
        output.append(
            rec(
                "cvr_drop",
                "Recorded conversion rate fell more than 30% between the supplied periods.",
                compare(current, previous),
                "Compare conversion actions, landing pages and traffic mix; exclude immature conversion days before testing a change.",
                "P1",
                "medium",
            )
        )
    for row in campaigns:
        budget = row.get("metrics.search_budget_lost_impression_share")
        rank = row.get("metrics.search_rank_lost_impression_share")
        if budget is not None and finite(budget) >= 0.15:
            output.append(
                rec(
                    f"budget:{row.get('campaign.id')}",
                    "Search eligible impressions were lost to budget.",
                    row,
                    f"For campaign {row.get('campaign.id')}, verify qualified CPA/ROAS, then test a small budget increase only if profitable.",
                    "P2",
                    "medium",
                    diagnosis={
                        "hypothesis": "Budget limits eligible Search participation.",
                        "alternatives": [
                            "Rank may also constrain reach",
                            "More spend may buy lower-quality traffic",
                        ],
                    },
                )
            )
        if rank is not None and finite(rank) >= 0.3:
            output.append(
                rec(
                    f"rank:{row.get('campaign.id')}",
                    "Search eligible impressions were lost to ad rank.",
                    row,
                    f"Review ads, landing-page relevance and bid economics in campaign {row.get('campaign.id')} before increasing budget.",
                    "P2",
                    "medium",
                )
            )
    return sorted(output, key=lambda x: -x["ranking"]["score"])


def token_match(text, terms):
    return any(
        re.search(
            r"(?<!\w)" + re.escape(term.strip().casefold()) + r"(?!\w)",
            text.casefold(),
        )
        for term in terms
    )


def term_analysis(rows, options: AuditOptions, mature: bool):
    findings, opportunities = [], []
    review_cost = 0.0
    brand = {"brand": [], "non_brand": [], "unclassified": []}
    for row in rows:
        query = str(
            row.get(
                "search_term_view.search_term",
                row.get("ad_group_criterion.keyword.text", ""),
            )
        )
        m = aggregate([row])
        label = (
            (
                "brand"
                if token_match(query, options.brand_terms)
                else "non_brand"
            )
            if options.brand_terms
            else "unclassified"
        )
        brand[label].append(row)
        irrelevant = token_match(query, options.irrelevant_terms)
        enough = (
            m["clicks"] >= options.min_clicks
            and options.target_cpa is not None
            and m["cost"] >= options.target_cpa * 2
        )
        if irrelevant or (m["conversions"] == 0 and enough):
            actionable = mature and options.tracking_verified
            review_cost += m["cost"]
            findings.append(
                rec(
                    f"term:{len(findings)+1}",
                    f"Review query/keyword: {query}",
                    {
                        "row": row,
                        "metrics": m,
                        "brand_classification": label,
                        "mature_period": mature,
                        "tracking_verified": options.tracking_verified,
                        "threshold": {
                            "min_clicks": options.min_clicks,
                            "spend_multiple_of_target_cpa": 2,
                        },
                    },
                    f"Review relevance of '{query}' in campaign {row.get('campaign.id')}, ad group {row.get('ad_group.id')}; "
                    + (
                        "prepare a narrowly matched negative only after business review."
                        if irrelevant and actionable
                        else "validate tracking, lag and intent before any exclusion or pause."
                    ),
                    "P2" if actionable else "P3",
                    "medium" if actionable else "low",
                    impact={
                        "estimate": "Review exposure only, not recoverable or guaranteed wasted spend.",
                        "observed_review_cost": m["cost"],
                        "assumptions": "Historical spend is sunk; future savings and lost conversions are unknown.",
                    },
                )
            )
        if (
            options.target_cpa
            and m["conversions"] >= 5
            and m["cpa"] <= options.target_cpa
        ):
            opportunities.append(
                {
                    "query": query,
                    "evidence": row,
                    "metrics": m,
                    "next_step": "Check existing keyword coverage, then test a separate exact/phrase keyword with a capped budget; no guaranteed incrementality.",
                }
            )
    return {
        "recommendations": findings,
        "opportunities": opportunities,
        "review_exposure": review_cost,
        "review_exposure_is_not_waste": True,
        "brand_split": {k: aggregate(v) for k, v in brand.items()},
        "classification_method": "User-provided literal phrases with word boundaries; non-brand only relative to supplied terms, not verified intent.",
    }


def keyword_overlap(rows):
    groups = defaultdict(list)
    for row in rows:
        text = re.sub(
            r"\s+",
            " ",
            str(row.get("ad_group_criterion.keyword.text", "")).casefold(),
        ).strip()
        if text:
            groups[
                (text, row.get("ad_group_criterion.keyword.match_type"))
            ].append(row)
    return [
        {
            "keyword": key[0],
            "match_type": key[1],
            "rows": value,
            "interpretation": "Duplicate text and match type across entities; this does not prove simultaneous eligibility, self-bidding or higher CPC.",
        }
        for key, value in groups.items()
        if len({(r.get("campaign.id"), r.get("ad_group.id")) for r in value})
        > 1
    ]


def segment_analysis(rows, dimensions, min_clicks=30):
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(str(row.get(d, "UNKNOWN")) for d in dimensions)].append(
            row
        )
    overall = aggregate(rows)
    result = []
    for key, values in groups.items():
        m = aggregate(values)
        result.append(
            {
                "segment": dict(zip(dimensions, key)),
                "metrics": m,
                "sufficient_clicks": m["clicks"] >= min_clicks,
                "cpa_relative_to_report": (
                    ratio(m["cpa"], overall["cpa"])
                    if m["cpa"] is not None and overall["cpa"]
                    else None
                ),
            }
        )
    return {
        "segments": sorted(result, key=lambda x: -x["metrics"]["cost"]),
        "overall": overall,
        "interpretation": "Descriptive correlation, not causal lift. Geographic rows describe the selected report definition, not necessarily targeting. No CRM or qualified-lead data is connected.",
    }


def daily_anomalies(rows):
    # Trailing seven observations only, not future observations; missing dates are not filled.
    groups = defaultdict(list)
    for row in rows:
        groups[str(row.get("segments.date"))].append(row)
    daily = [(day, aggregate(value)) for day, value in sorted(groups.items())]
    output = []
    for i in range(7, len(daily)):
        history = [m["cost"] for _, m in daily[i - 7 : i]]
        avg, sd = mean(history), pstdev(history)
        actual = daily[i][1]["cost"]
        if (
            sd > 0
            and abs(actual - avg) > 3 * sd
            and abs(actual - avg) > max(1, avg * 0.3)
        ):
            output.append(
                {
                    "date": daily[i][0],
                    "cost": actual,
                    "baseline_cost": avg,
                    "z_score": (actual - avg) / sd,
                    "method": "Trailing seven observed days, >3 population standard deviations and >30% shift.",
                    "limitation": "Exploratory; weekday mix, missing dates, low counts and multiple testing can explain flags.",
                }
            )
    return output


def scenarios(baseline, incremental_budget, cpc_multipliers, cvr_multipliers):
    if len(cpc_multipliers) != 3 or len(cvr_multipliers) != 3:
        raise ValueError("Supply exactly three CPC and CVR multipliers.")
    if not 0 < finite(incremental_budget) <= 1e9:
        raise ValueError(
            "Incremental spend must be positive and <= 1 billion currency units."
        )
    if any(
        not 0.1 <= finite(v) <= 10 for v in cpc_multipliers + cvr_multipliers
    ):
        raise ValueError("Multipliers must be between 0.1 and 10.")
    if (
        baseline["clicks"] < 30
        or baseline["conversions"] < 10
        or not baseline["average_cpc"]
        or not baseline["conversion_rate"]
    ):
        return {
            "status": "insufficient_evidence",
            "reason": "At least 30 clicks, 10 conversions, positive CPC and conversion rate required; validate conversion maturity and quality.",
        }
    result = []
    for label, cpc_m, cvr_m in zip(
        ("conservative", "base", "optimistic"), cpc_multipliers, cvr_multipliers
    ):
        cpc = baseline["average_cpc"] * cpc_m
        rate = baseline["conversion_rate"] * cvr_m
        clicks = incremental_budget / cpc
        conversions = clicks * rate
        value_per_conversion = ratio(
            baseline["conversion_value"], baseline["conversions"]
        )
        result.append(
            dict(
                label=label,
                incremental_spend=incremental_budget,
                assumed_cpc=cpc,
                assumed_conversions_per_click=rate,
                estimated_incremental_clicks=clicks,
                estimated_incremental_conversions=conversions,
                estimated_incremental_value=conversions * value_per_conversion,
                assumed_cpc_multiplier=cpc_m,
                assumed_cvr_multiplier=cvr_m,
            )
        )
    return {
        "status": "illustrative_sensitivity_not_forecast",
        "scenarios": result,
        "confidence": "low",
        "formula": "incremental clicks = incremental spend / assumed CPC; conversions = clicks × assumed conversions per click; value = conversions × historical value per conversion",
        "assumptions": [
            "All incremental spend can be delivered",
            "User-supplied CPC/CVR multipliers describe marginal traffic",
            "Historical value per conversion persists",
            "No demand, auction, saturation or causal lift model",
            "Conversion count may exceed clicks for accounts counting multiple actions",
        ],
        "limitations": "Not an API bid simulator, forecast, promise, or justification for an automatic budget change.",
    }
