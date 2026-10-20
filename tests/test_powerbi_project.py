from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PBI = ROOT / "powerbi"


def test_pbip_project_is_consistent():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_powerbi_project.py")],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_pbip_entry_point_exists():
    entry = PBI / "消费金融审批分析.pbip"
    assert entry.exists()
    payload = json.loads(entry.read_text(encoding="utf-8"))
    report = payload["artifacts"][0]["report"]["path"]
    assert (PBI / report).is_dir()


def test_report_has_four_chinese_pages():
    pages_file = PBI / "消费金融审批分析.Report" / "definition" / "pages" / "pages.json"
    payload = json.loads(pages_file.read_text(encoding="utf-8"))
    assert len(payload["pageOrder"]) == 4
    names = []
    for page in payload["pageOrder"]:
        page_json = PBI / "消费金融审批分析.Report" / "definition" / "pages" / page / "page.json"
        names.append(json.loads(page_json.read_text(encoding="utf-8"))["displayName"])
    assert names == ["经营总览", "渠道归因", "风险验证", "指标口径"]


def test_summary_data_tables_are_committed():
    for name, rows in {"月度经营": 18, "当月指标": 1, "渠道归因": 7, "渠道表现": 7, "指标口径": 8}.items():
        path = PBI / "data" / f"{name}.csv"
        assert path.exists()
        assert len(path.read_text(encoding="utf-8").strip().splitlines()) == rows + 1
