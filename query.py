"""Bounded read operations. No mutation service is exposed as an MCP tool."""

import re
from google.api_core.retry import Retry, if_exception_type
from google.api_core.exceptions import ServiceUnavailable, ResourceExhausted
from google.ads.googleads.errors import GoogleAdsException
from fastmcp.exceptions import ToolError
from ads_mcp import utils

MAX_ROWS = 10000
RETRY = Retry(
    predicate=if_exception_type(ServiceUnavailable, ResourceExhausted),
    initial=0.5,
    maximum=4,
    multiplier=2,
    timeout=15,
)
IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*$")


def identifier(value):
    if not IDENTIFIER.fullmatch(value):
        raise ValueError(
            "Use an exact resource or fully qualified field identifier."
        )
    return value


def build_query(fields, resource, conditions=None, orderings=None, limit=None):
    identifier(resource)
    if not fields or len(fields) > 100:
        raise ValueError("Select 1–100 fields.")
    for field in fields:
        identifier(field)
    limit = MAX_ROWS if limit is None else limit
    if (
        isinstance(limit, bool)
        or not isinstance(limit, int)
        or not 1 <= limit <= MAX_ROWS
    ):
        raise ValueError("Limit must be an integer between 1 and 10000.")
    conditions = conditions or []
    orderings = orderings or []
    if len(conditions) > 50 or len(orderings) > 20:
        raise ValueError("Too many query clauses.")
    for condition in conditions:
        if (
            not isinstance(condition, str)
            or len(condition) > 2000
            or re.search(
                r";|--|/\*|\*/|\b(?:SELECT|FROM|LIMIT|PARAMETERS|ORDER\s+BY)\b|[\x00-\x1f]",
                condition,
                re.I,
            )
        ):
            raise ValueError("Condition contains unsupported query syntax.")
    for order in orderings:
        if not re.fullmatch(
            r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*(?: (?:ASC|DESC))?", order
        ):
            raise ValueError(
                "Ordering must be a field optionally followed by ASC or DESC."
            )
    query = f"SELECT {','.join(fields)} FROM {resource}"
    if conditions:
        query += f" WHERE {' AND '.join(conditions)}"
    if orderings:
        query += f" ORDER BY {','.join(orderings)}"
    return (
        query + f" LIMIT {limit} PARAMETERS omit_unselected_resource_names=true"
    )


def execute(
    customer_id,
    fields,
    resource,
    conditions=None,
    orderings=None,
    limit=None,
    login_customer_id=None,
):
    cid = utils.clean_customer_id(customer_id)
    query = build_query(fields, resource, conditions, orderings, limit)
    service = utils.get_googleads_service(
        "GoogleAdsService", login_customer_id=login_customer_id
    )
    try:
        # Search pager handles all pages, including transient retries per page.
        pager = service.search(
            customer_id=cid, query=query, timeout=30, retry=RETRY
        )
        result = []
        for row in pager:
            result.append(utils.format_output_row(row, fields))
            if len(result) >= (limit or MAX_ROWS):
                break
        return result
    except GoogleAdsException as exc:
        # Error messages may echo user queries, URLs or PII. Keep only request ID
        # and enum code, never the upstream free-form message or credentials.
        codes = [
            str(error.error_code).split(":")[0].strip()
            for error in exc.failure.errors
        ]
        raise ToolError(
            f"Google Ads rejected the read request. Request ID: {exc.request_id}. Codes: {', '.join(codes)}. Check field compatibility, permissions and date filters."
        ) from None
    except (ServiceUnavailable, ResourceExhausted):
        raise ToolError(
            "Google Ads temporarily unavailable or quota exhausted; bounded read retries completed. Retry later."
        ) from None
