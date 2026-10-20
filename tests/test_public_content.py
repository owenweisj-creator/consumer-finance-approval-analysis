from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN = [
    "面" + "试",
    "带" + "教",
    "你的" + "动手",
    "面" + "试追问",
    "简" + "历",
    "5 分钟" + "讲解",
    "讲解" + "稿",
]


def tracked_files() -> list[Path]:
    output = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True)
    return [ROOT / line for line in output.splitlines() if line.strip()]


def test_public_repo_has_no_career_material():
    files = tracked_files()
    names = {path.relative_to(ROOT).as_posix() for path in files}
    assert "docs/codex_log.md" in names
    assert not any(name.startswith("docs/interview/") for name in names)
    assert not any(name.startswith("docs/learning/") for name in names)
    assert "scripts/build_resume.py" not in names
    assert "scripts/import_risk_from_duckdb.py" not in names


def test_public_text_has_no_forbidden_terms():
    for path in tracked_files():
        if path.suffix.lower() not in {".md", ".py", ".ipynb", ".sql", ".toml", ".txt", ".yml"}:
            continue
        if path.name == "test_public_content.py":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for word in FORBIDDEN:
            assert word not in text, f"{word} found in {path.relative_to(ROOT)}"


def test_readme_links_project():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "https://github.com/owenweisj-creator/consumer-finance-approval-analysis" in readme
