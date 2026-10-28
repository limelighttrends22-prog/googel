"""All fixtures in this module are synthetic; no advertising credentials used."""

import asyncio
import json
import math
import os
from datetime import date
from unittest.mock import MagicMock, patch
import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError
from pydantic import ValidationError
from ads_mcp.intelligence import engine, reports, auction
from ads_mcp.intelligence.models import Period, AuditOptions, AlertRule
from ads_mcp.intelligence.storage import ReportStore, export
from ads_mcp.query import build_query, execute
from ads_mcp.security import (
    customer_id,
    check_customer_scope,
    validate_configuration,
    principal,
)

PERIOD = Period(start="2026-09-01", end="2026-09-14")
INFO = {
    "customer.id": 1234567890,
    "customer.descriptive_name": "SYNTHETIC TEST ACCOUNT",
    "customer.currency_code": "INR",
    "customer.time_zone": "Asia/Kolkata",
    "customer.manager": False,
}
ROW = {
    "campaign.id": 1,
    "campaign.name": "SYNTHETIC TEST CAMPAIGN",
    "campaign.status": "ENABLED",
    "campaign.advertising_channel_type": "SEARCH",
    "campaign.bidding_strategy_type": "MAXIMIZE_CONVERSIONS",
    "metrics.cost_micros": 3600000000,
    "metrics.clicks": 100,
    "metrics.impressions": 1000,
    "metrics.conversions": 4,
    "metrics.conversions_value": 10000,
}


def test_weighted_metrics_and_nulls():
    m = engine.aggregate([ROW, ROW])
    assert m["cost"] == 7200 and m["ctr"] == 0.1 and m["cpa"] == 900
    assert engine.aggregate([])["cpa"] is None
    assert (
        engine.compare(engine.aggregate([]), engine.aggregate([]))["cost"][
            "relative_change"
        ]
        is None
    )


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1])
def test_invalid_metrics_rejected(value):
    with pytest.raises(ValueError):
        engine.aggregate([{"metrics.clicks": value}])


def test_fractional_conversions():
    row = {**ROW, "metrics.conversions": 0.5}
    assert engine.aggregate([row])["cpa"] == 7200


@pytest.mark.parametrize(
    "start,end", [("2026-02-01", "2026-01-01"), ("2020-01-01", "2026-01-01")]
)
def test_invalid_periods(start, end):
    with pytest.raises(ValidationError):
        Period(start=start, end=end)


def test_previous_period_equal_length():
    assert PERIOD.previous().days == PERIOD.days
    assert PERIOD.previous().end < PERIOD.start


@pytest.mark.parametrize(
    "value",
    ["", "abc1234567890", "customers/1234567890", "１２３４５６７８９０", True],
)
def test_invalid_customer_ids(value):
    with pytest.raises(ValueError):
        customer_id(value)


def test_ids_and_allowlist(monkeypatch):
    assert customer_id("123-456-7890") == "1234567890"
    monkeypatch.setenv("GOOGLE_ADS_MCP_ALLOWED_CUSTOMERS", "1234567890")
    with pytest.raises(PermissionError):
        check_customer_scope("9998887777")


@pytest.mark.parametrize(
    "fields,resource,conditions,order,limit",
    [
        ([], "campaign", None, None, None),
        (["campaign.id;DROP"], "campaign", None, None, None),
        (["campaign.id"], "campaign WHERE 1=1", None, None, None),
        (
            ["campaign.id"],
            "campaign",
            ["campaign.name = 'x'; SELECT *"],
            None,
            None,
        ),
        (["campaign.id"], "campaign", None, ["campaign.id DESC;"], None),
        (["campaign.id"], "campaign", None, None, 0),
        (["campaign.id"], "campaign", None, None, 10001),
        (["campaign.id"], "campaign", None, None, True),
    ],
)
def test_query_validation(fields, resource, conditions, order, limit):
    with pytest.raises(ValueError):
        build_query(fields, resource, conditions, order, limit)


def test_query_bound():
    assert "LIMIT 10000" in build_query(["campaign.id"], "campaign")


def test_paging_timeout_and_exact_cap():
    service = MagicMock()
    service.search.return_value = [object(), object(), object()]
    with patch(
        "ads_mcp.utils.get_googleads_service", return_value=service
    ), patch("ads_mcp.utils.format_output_row", return_value=ROW):
        assert (
            len(execute("1234567890", ["campaign.id"], "campaign", limit=2))
            == 2
        )
    assert service.search.call_args.kwargs["timeout"] == 30
    assert service.search.call_args.kwargs["retry"] is not None
    service.search_stream.assert_not_called()


def test_api_error_is_redacted():
    from google.ads.googleads.errors import GoogleAdsException

    failure = MagicMock()
    err = MagicMock()
    err.message = "SECRET-QUERY-PII"
    err.error_code = "query_error: INVALID_FIELD_NAME"
    failure.errors = [err]
    service = MagicMock()
    service.search.side_effect = GoogleAdsException(
        MagicMock(), MagicMock(), failure, "request-123"
    )
    with patch("ads_mcp.utils.get_googleads_service", return_value=service):
        with pytest.raises(ToolError) as ex:
            execute("1234567890", ["campaign.id"], "campaign")
    assert "SECRET" not in str(ex.value) and "request-123" in str(ex.value)


def test_tracking_recommendation_has_ten_fields():
    row = {**ROW, "metrics.conversions": 0}
    rec = engine.account_recommendations(
        engine.aggregate([row]), engine.aggregate([]), []
    )[0]
    assert rec["priority"] == "P0"
    assert (
        set(
            (
                "finding",
                "evidence",
                "diagnosis",
                "recommended_action",
                "priority",
                "expected_impact",
                "confidence",
                "risk",
                "validation_plan",
                "rollback_plan",
            )
        )
        <= rec.keys()
    )


def test_zero_conversions_do_not_trigger_without_threshold():
    row = {
        **ROW,
        "search_term_view.search_term": "toothpaste manufacturer",
        "metrics.conversions": 0,
        "metrics.clicks": 2,
    }
    assert not engine.term_analysis([row], AuditOptions(target_cpa=900), True)[
        "recommendations"
    ]


def test_immature_and_unverified_terms_only_review():
    row = {
        **ROW,
        "search_term_view.search_term": "free jobs",
        "metrics.conversions": 0,
    }
    result = engine.term_analysis(
        [row], AuditOptions(target_cpa=900, irrelevant_terms=["jobs"]), False
    )
    assert result["recommendations"][0]["priority"] == "P3"
    assert (
        result["review_exposure"] == 3600
        and result["review_exposure_is_not_waste"]
    )
    assert "pause" in result["recommendations"][0]["recommended_action"]


def test_brand_boundary_and_unclassified():
    assert not engine.token_match("shell toothpaste", ["hell"])
    assert engine.token_match("HCP toothpaste", ["hcp"])
    result = engine.term_analysis(
        [{**ROW, "search_term_view.search_term": "hcp"}], AuditOptions(), True
    )
    assert result["brand_split"]["unclassified"]["cost"] == 3600


def test_keyword_overlap_not_causal():
    rows = [
        {
            **ROW,
            "ad_group.id": x,
            "ad_group_criterion.keyword.text": " Toothpaste   Manufacturer ",
            "ad_group_criterion.keyword.match_type": "EXACT",
        }
        for x in (1, 2)
    ]
    output = engine.keyword_overlap(rows)
    assert len(output) == 1 and "does not prove" in output[0]["interpretation"]


def test_segments_no_invented_crm():
    result = engine.segment_analysis(
        [{**ROW, "segments.device": "MOBILE"}], ["segments.device"]
    )
    assert result["segments"][0]["metrics"]["cpa"] == 900
    assert "No CRM" in result["interpretation"]


def test_anomaly_uses_past_only():
    rows = [
        {
            **ROW,
            "segments.date": f"2026-09-{i:02d}",
            "metrics.cost_micros": (100 + i % 2) * 1000000,
        }
        for i in range(1, 9)
    ]
    rows[-1]["metrics.cost_micros"] = 1000000000
    assert engine.daily_anomalies(rows)[0]["date"] == "2026-09-08"


def test_budget_scenario_formula():
    base = engine.aggregate([{**ROW, "metrics.conversions": 20}])
    result = engine.scenarios(base, 3600, [1.2, 1, 0.8], [0.8, 1, 1.2])
    assert result["scenarios"][1]["estimated_incremental_conversions"] == 20
    assert result["status"] == "illustrative_sensitivity_not_forecast"


@pytest.mark.parametrize(
    "budget,cpc,cvr",
    [
        (float("nan"), [1] * 3, [1] * 3),
        (10, [1], [1] * 3),
        (0, [1] * 3, [1] * 3),
        (10, [0, 1, 1], [1] * 3),
    ],
)
def test_scenario_validation(budget, cpc, cvr):
    with pytest.raises(ValueError):
        engine.scenarios(engine.aggregate([ROW]), budget, cpc, cvr)


def test_scenario_low_sample():
    assert (
        engine.scenarios(engine.aggregate([ROW]), 100, [1] * 3, [1] * 3)[
            "status"
        ]
        == "insufficient_evidence"
    )


CSV = "Display URL domain,Impression share,Overlap rate\nexample.test,<10%,42.5%\nYou,30%,--\n"


def test_auction_preserves_bounds_and_provenance():
    result = auction.parse_export(
        CSV, PERIOD, "SYNTHETIC account Search campaigns"
    )
    assert result["rows"][0]["metrics"]["impression_share"] == {
        "value": 0.1,
        "relation": "<",
    }
    assert "not_independently_verified" in result["source"]


@pytest.mark.parametrize("value", ["101%", "NaN", "0.5", "-5%"])
def test_auction_invalid_percent(value):
    with pytest.raises(ValueError):
        auction.percentage(value)


def test_auction_comparison_does_not_subtract_bounds():
    current = auction.parse_export(CSV, PERIOD, "same filters")
    previous = auction.parse_export(
        CSV.replace("42.5%", "40%"), PERIOD.previous(), "same filters"
    )
    result = auction.compare_exports(current, previous)
    example = next(
        r for r in result["changes"] if r["domain"] == "example.test"
    )
    assert (
        example["metrics"]["impression_share"]["percentage_point_change"]
        is None
    )
    assert example["metrics"]["overlap_rate"][
        "percentage_point_change"
    ] == pytest.approx(2.5)


def test_auction_duplicate_rows_rejected():
    current = auction.parse_export(
        CSV + "example.test,20%,50%\n", PERIOD, "same"
    )
    prior = auction.parse_export(CSV, PERIOD.previous(), "same")
    with pytest.raises(ValueError):
        auction.compare_exports(current, prior)


def mock_read(cid, fields, resource, conditions=None, login=None, order=None):
    if fields[0] == "customer.id":
        return [INFO]
    if "metrics.search_impression_share" in fields:
        return [
            {
                "campaign.id": 1,
                "metrics.search_budget_lost_impression_share": 0.2,
            }
        ]
    if "campaign_budget.amount_micros" in fields:
        return []
    return [ROW]


def test_live_adapter_mocked_account_and_dates():
    with patch.object(reports, "read", side_effect=mock_read):
        result = reports.account_audit("1234567890", PERIOD)
    assert result["provenance"]["currency"] == "INR"
    assert result["overview"]["cost"] == 3600
    assert result["previous_period"]["end"] == "2026-08-31"
    assert result["recommendations"][0]["evidence"]["campaign.id"] == 1


def test_read_cap_never_silent():
    with patch.object(reports, "execute", return_value=[ROW] * 10000):
        with pytest.raises(ToolError):
            reports.read("1234567890", ["campaign.id"], "campaign")


def test_future_range_rejected():
    with pytest.raises(ValueError):
        reports.provenance(
            "1234567890", Period(start="2099-01-01", end="2099-01-02"), INFO
        )


def test_saved_reports_isolated_and_deleted(tmp_path):
    with patch.object(reports, "read", side_effect=mock_read):
        report = reports.account_audit("1234567890", PERIOD)
    store = ReportStore(tmp_path / "reports.db")
    rid = store.save("alice", report)
    assert store.list("bob") == []
    with pytest.raises(ValueError):
        store.get("bob", rid)
    assert not store.delete("bob", rid)
    assert store.get("alice", rid) == report
    assert store.delete("alice", rid)
    with pytest.raises(ValueError):
        store.get("alice", rid)


def test_saved_report_quota(tmp_path):
    store = ReportStore(tmp_path / "reports.db")
    report = {"provenance": {"customer_id": "1234567890"}}
    for _ in range(100):
        store.save("alice", report)
    with pytest.raises(ValueError):
        store.save("alice", report)


def test_exports_preserve_evidence_and_escape_formulas():
    with patch.object(reports, "read", side_effect=mock_read):
        report = reports.account_audit("1234567890", PERIOD)
    report["recommendations"][0][
        "finding"
    ] = '=HYPERLINK("https://example.test")'
    assert "'=HYPERLINK" in export(report, "csv")
    assert "Rollback Plan" in export(report, "markdown")
    assert json.loads(export(report, "json")) == report


@pytest.mark.parametrize(
    "env",
    [
        {"GOOGLE_ADS_MCP_OAUTH_CLIENT_ID": "only-half"},
        {"GOOGLE_ADS_MCP_STORAGE_DISABLE_ENCRYPTION": "true"},
        {
            "GOOGLE_ADS_MCP_OAUTH_CLIENT_ID": "id",
            "GOOGLE_ADS_MCP_OAUTH_CLIENT_SECRET": "secret",
        },
    ],
)
def test_unsafe_config_rejected(env):
    with patch.dict(os.environ, env, clear=True), pytest.raises(ValueError):
        validate_configuration()


def oauth_env(tmp_path):
    return {
        "GOOGLE_ADS_MCP_OAUTH_CLIENT_ID": "synthetic-id",
        "GOOGLE_ADS_MCP_OAUTH_CLIENT_SECRET": "synthetic-secret",
        "GOOGLE_ADS_MCP_BASE_URL": "https://mcp.example.test",
        "GOOGLE_ADS_MCP_JWT_SIGNING_KEY": "synthetic-test-key-not-real-"
        + "x" * 32,
        "GOOGLE_ADS_MCP_STORAGE_TYPE": "filetree",
        "GOOGLE_ADS_MCP_STORAGE_PATH": str(tmp_path / "oauth"),
        "GOOGLE_ADS_MCP_ALLOWED_REDIRECT_URIS": "https://chatgpt.com/connector/oauth/synthetic-test",
    }


def test_valid_oauth_configuration_without_legacy_developer_token(tmp_path):
    with patch.dict(os.environ, oauth_env(tmp_path), clear=True):
        validate_configuration()


def test_no_remote_adc_fallback():
    from ads_mcp.utils import _create_credentials

    with patch.dict(
        os.environ, {"GOOGLE_ADS_MCP_OAUTH_CLIENT_ID": "remote"}, clear=True
    ), patch(
        "fastmcp.server.dependencies.get_access_token", return_value=None
    ), patch(
        "google.auth.default"
    ) as adc:
        with pytest.raises(PermissionError):
            _create_credentials()
        with pytest.raises(PermissionError):
            principal()
        adc.assert_not_called()


def test_principal_never_persists_token():
    token = MagicMock()
    token.token = "synthetic-secret-token"
    token.claims = {"sub": "synthetic-user", "aud": "synthetic-app"}
    with patch(
        "fastmcp.server.dependencies.get_access_token", return_value=token
    ):
        owner = principal()
    assert "synthetic" not in owner and owner.startswith("oauth:")


def test_mcp_registration_schemas_and_real_tool_invocation():
    from ads_mcp.server import mcp

    async def run():
        async with Client(mcp) as client:
            tools = await client.list_tools()
            assert len(tools) == 20
            assert not any(
                "execute" in t.name or "mutate" in t.name for t in tools
            )
            for tool in tools:
                import jsonschema

                jsonschema.Draft202012Validator.check_schema(tool.input_schema)
            glossary = await client.call_tool(
                "intelligence_explain_metric", {"metric": "cpa"}
            )
            assert "Illustrative" in str(glossary)
            with patch.object(reports, "read", side_effect=mock_read):
                result = await client.call_tool(
                    "intelligence_audit_account",
                    {
                        "customer_id": "1234567890",
                        "period": PERIOD.model_dump(mode="json"),
                    },
                )
            assert "3600" in str(result)
            with pytest.raises(Exception):
                await client.call_tool(
                    "intelligence_audit_account",
                    {
                        "customer_id": "abc",
                        "period": {"start": "invalid", "end": "2026-01-01"},
                    },
                )

    asyncio.run(run())


def test_preview_never_executes_and_retains_exact_values():
    from ads_mcp.tools.intelligence import preview_campaign_change

    with patch.object(
        reports,
        "read",
        return_value=[
            {
                "campaign.id": 1,
                "campaign.name": "SYNTHETIC",
                "campaign.status": "ENABLED",
            }
        ],
    ):
        result = preview_campaign_change(
            "1234567890", "1", "PAUSED", "Review poor qualified outcomes"
        )
    assert (
        result["previous_value"] == "ENABLED"
        and result["proposed_value"] == "PAUSED"
    )
    assert not result["execution_available"] and not result["executable"]


def test_invalid_alert_threshold():
    with pytest.raises(ValidationError):
        AlertRule(metric="cpa", operator="gt", threshold=float("nan"))


def test_principal_stable_across_token_refresh():
    from types import SimpleNamespace

    first = SimpleNamespace(
        token="synthetic-token-one", claims={"sub": "user-one", "aud": "app"}
    )
    second = SimpleNamespace(
        token="synthetic-token-two", claims={"sub": "user-one", "aud": "app"}
    )
    third = SimpleNamespace(
        token="synthetic-token-three", claims={"sub": "user-two", "aud": "app"}
    )
    with patch(
        "fastmcp.server.dependencies.get_access_token", return_value=first
    ):
        a = principal()
    with patch(
        "fastmcp.server.dependencies.get_access_token", return_value=second
    ):
        b = principal()
    with patch(
        "fastmcp.server.dependencies.get_access_token", return_value=third
    ):
        c = principal()
    assert a == b and a != c


def test_empty_report_db_environment_uses_home_default(monkeypatch, tmp_path):
    monkeypatch.setenv("GOOGLE_ADS_MCP_REPORT_DB", "")
    with patch("pathlib.Path.home", return_value=tmp_path):
        store = ReportStore()
    assert store.path.name == "reports.sqlite3"
