"""Honest analysis of user-supplied English Auction Insights CSV exports."""

import csv
import io
import re
from .models import Period

COLUMNS = {
    "impression share": "impression_share",
    "overlap rate": "overlap_rate",
    "position above rate": "position_above_rate",
    "outranking share": "outranking_share",
    "top of page rate": "top_of_page_rate",
    "abs. top of page rate": "absolute_top_of_page_rate",
}
DEFINITIONS = {
    "impression_share": "Share of estimated eligible impressions. Eligibility can differ by advertiser; shares do not sum to 100%.",
    "overlap_rate": "How often the other participant showed when your ad also showed.",
    "position_above_rate": "How often the other participant appeared above you when both ads showed.",
    "outranking_share": "How often your ad ranked higher, or showed while theirs did not, under the report's auction definition.",
    "top_of_page_rate": "Fraction of the participant's impressions above organic results; this is not impression share.",
    "absolute_top_of_page_rate": "Fraction of the participant's impressions in the first ad position.",
}


def percentage(text):
    text = text.strip()
    if text in ("", "--", "—", "N/A"):
        return {"value": None, "relation": "missing"}
    match = re.fullmatch(r"([<>]?)\s*(\d+(?:\.\d+)?)%", text)
    if not match or float(match[2]) > 100:
        raise ValueError(
            "Auction rates must be percentages such as 42.5%, <10%, >90%, or --."
        )
    return {"value": float(match[2]) / 100, "relation": match[1] or "="}


def parse_export(csv_text, period: Period, scope):
    if len(csv_text.encode()) > 1_000_000:
        raise ValueError("CSV must be <=1 MB.")
    if not scope.strip() or len(scope) > 500:
        raise ValueError(
            "Supply the exact account/campaign/device/date-filter description (1–500 characters)."
        )
    reader = csv.DictReader(io.StringIO(csv_text.lstrip("\ufeff")))
    if not reader.fieldnames:
        raise ValueError("CSV header missing.")
    names = {name.strip().casefold(): name for name in reader.fieldnames}
    domain_key = names.get("display url domain") or names.get("domain")
    if not domain_key:
        raise ValueError(
            "Expected an English CSV header with Display URL domain or Domain; remove title/date preamble rows."
        )
    available = [key for key in COLUMNS if key in names]
    if not available:
        raise ValueError("No recognized auction percentage columns.")
    rows = []
    for i, row in enumerate(reader):
        if i >= 1000:
            raise ValueError("Maximum 1,000 auction rows.")
        if None in row or any(value is None for value in row.values()):
            raise ValueError("Malformed CSV row.")
        domain = row[domain_key].strip()
        if not domain or len(domain) > 253:
            raise ValueError("Missing or oversized domain.")
        rows.append(
            {
                "domain": domain,
                "metrics": {
                    COLUMNS[key]: percentage(row[names[key]])
                    for key in available
                },
                "dimensions": {
                    key: value
                    for key, value in row.items()
                    if key not in [domain_key] + [names[k] for k in available]
                },
            }
        )
    if not rows:
        raise ValueError("CSV contains no participants.")
    return {
        "source": "user_supplied_export_not_independently_verified",
        "period": period.model_dump(mode="json"),
        "scope": scope,
        "rows": rows,
        "definitions": DEFINITIONS,
        "limitations": [
            "Public Google Ads API auction_insight_* fields are restricted; this tool does not claim live competitor access.",
            "CSV period, filters and provenance are assertions supplied by the user.",
            "Bounded rates (<10%, >90%) are not exact values and must not be used as exact differences.",
            "Do not average participant rates across dates, devices or campaigns without the correct denominators.",
            "No exact competitor spend, bids, strategy or causality can be inferred.",
        ],
    }


def compare_exports(current, previous):
    # Refuse mixed dimension joins and ambiguous repeated domains.
    if current["scope"] != previous["scope"]:
        raise ValueError(
            "Scope labels must match exactly before period comparison."
        )
    current_period, prior_period = Period(**current["period"]), Period(
        **previous["period"]
    )
    if (
        current_period.days != prior_period.days
        or prior_period.end >= current_period.start
    ):
        raise ValueError(
            "Compare equal-length non-overlapping periods, earlier period first."
        )

    def index(report):
        result = {}
        for row in report["rows"]:
            key = (
                row["domain"].casefold(),
                tuple(sorted(row["dimensions"].items())),
            )
            if key in result:
                raise ValueError(
                    "Duplicate domain/dimension rows; supply a report with unique participant segments."
                )
            result[key] = row
        return result

    before, after = index(previous), index(current)
    changes = []
    for key in before.keys() & after.keys():
        metrics = {}
        for name in (
            before[key]["metrics"].keys() & after[key]["metrics"].keys()
        ):
            a, b = after[key]["metrics"][name], before[key]["metrics"][name]
            metrics[name] = {
                "current": a,
                "previous": b,
                "percentage_point_change": (
                    100 * (a["value"] - b["value"])
                    if a["relation"] == b["relation"] == "="
                    else None
                ),
            }
        changes.append(
            {
                "domain": after[key]["domain"],
                "dimensions": after[key]["dimensions"],
                "metrics": metrics,
            }
        )
    return {
        "changes": changes,
        "newly_observed": [after[k] for k in after.keys() - before.keys()],
        "no_longer_observed": [before[k] for k in before.keys() - after.keys()],
        "interpretation": "Observed participation changes can reflect eligibility, traffic mix or reporting thresholds; they do not prove a competitor launched/stopped advertising.",
    }
