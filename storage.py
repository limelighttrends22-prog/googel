"""Single-instance, principal-scoped SQLite reports. Not an agency tenancy system."""

import csv
import io
import json
import os
import sqlite3
import time
import uuid
from pathlib import Path


class ReportStore:
    def __init__(self, path=None):
        self.path = Path(
            path
            or (
                os.getenv("GOOGLE_ADS_MCP_REPORT_DB")
                or str(
                    Path.home()
                    / ".google-ads-command-center"
                    / "reports.sqlite3"
                )
            )
        )
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.path.is_symlink():
            raise ValueError("Report database must not be a symbolic link.")
        with self.connect() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS reports (id TEXT PRIMARY KEY, owner TEXT NOT NULL, customer TEXT NOT NULL, created REAL NOT NULL, body TEXT NOT NULL)"
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS owner_reports ON reports(owner, created)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, owner TEXT NOT NULL, report_id TEXT NOT NULL, kind TEXT NOT NULL, created REAL NOT NULL)"
            )
        if os.name != "nt":
            self.path.chmod(0o600)

    def connect(self):
        return sqlite3.connect(self.path, timeout=5)

    def save(self, owner, report):
        body = json.dumps(report, ensure_ascii=False, allow_nan=False)
        if len(body.encode()) > 5_000_000:
            raise ValueError("Report exceeds 5 MB; narrow the reporting scope.")
        rid = str(uuid.uuid4())
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            count = db.execute(
                "SELECT count(*) FROM reports WHERE owner=?", (owner,)
            ).fetchone()[0]
            if count >= 100:
                raise ValueError(
                    "100-report limit reached for this principal; delete old reports."
                )
            db.execute(
                "INSERT INTO reports VALUES (?,?,?,?,?)",
                (
                    rid,
                    owner,
                    report["provenance"]["customer_id"],
                    time.time(),
                    body,
                ),
            )
            db.execute(
                "INSERT INTO events(owner,report_id,kind,created) VALUES (?,?,?,?)",
                (owner, rid, "saved", time.time()),
            )
        return rid

    def list(self, owner):
        with self.connect() as db:
            return [
                dict(zip(("id", "customer_id", "created_at_epoch"), row))
                for row in db.execute(
                    "SELECT id,customer,created FROM reports WHERE owner=? ORDER BY created DESC LIMIT 100",
                    (owner,),
                )
            ]

    def get(self, owner, rid):
        with self.connect() as db:
            row = db.execute(
                "SELECT body FROM reports WHERE owner=? AND id=?", (owner, rid)
            ).fetchone()
        if row is None:
            raise ValueError("Report not found for the current principal.")
        return json.loads(row[0])

    def delete(self, owner, rid):
        with self.connect() as db:
            changed = db.execute(
                "DELETE FROM reports WHERE owner=? AND id=?", (owner, rid)
            ).rowcount
            if changed:
                db.execute(
                    "INSERT INTO events(owner,report_id,kind,created) VALUES (?,?,?,?)",
                    (owner, rid, "deleted", time.time()),
                )
        return bool(changed)


def export(report, format):
    if format == "json":
        return json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False)
    if format == "markdown":
        meta = report["provenance"]
        lines = [
            "# Google Ads account audit",
            "",
            f"Account: {meta['customer_id']}; currency: {meta['currency']}",
            f"Period: {meta['period']['start']} to {meta['period']['end']}",
            f"Retrieved: {meta['retrieved_at']}",
            "",
            "## Metrics",
            "",
            "```json",
            json.dumps(report["overview"], indent=2),
            "```",
            "",
            "## Recommendations",
        ]
        for r in report["recommendations"]:
            lines.extend(["", f"### {r['priority']}: {r['finding']}"])
            for key in (
                "evidence",
                "diagnosis",
                "recommended_action",
                "expected_impact",
                "confidence",
                "risk",
                "validation_plan",
                "rollback_plan",
                "ranking",
            ):
                lines.extend(
                    [
                        "",
                        f"**{key.replace('_',' ').title()}**",
                        "```json",
                        json.dumps(r[key], ensure_ascii=False, indent=2),
                        "```",
                    ]
                )
        lines.extend(["", "## Limits", "", *report["warnings"]])
        return "\n".join(lines)
    if format == "csv":
        output = io.StringIO(newline="")
        columns = [
            "id",
            "priority",
            "finding",
            "evidence",
            "diagnosis",
            "recommended_action",
            "expected_impact",
            "confidence",
            "risk",
            "validation_plan",
            "rollback_plan",
            "ranking",
        ]
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        for row in report["recommendations"]:
            values = {
                key: (
                    json.dumps(row[key], ensure_ascii=False)
                    if isinstance(row[key], (dict, list))
                    else str(row[key])
                )
                for key in columns
            }
            # Prevent spreadsheet formula injection when exported data includes query text.
            values = {
                key: (
                    "'" + value
                    if value.lstrip().startswith(("=", "+", "-", "@"))
                    else value
                )
                for key, value in values.items()
            }
            writer.writerow(values)
        return output.getvalue()
    raise ValueError("Supported formats: json, markdown, csv.")
