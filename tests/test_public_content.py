from __future__ import annotations

import base64
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _decode(value: str) -> str:
    return base64.b64decode(value).decode("utf-8")


FORBIDDEN_TERMS = [
    _decode("6Z2i6K+V"),
    _decode("5bim5pWZ"),
    _decode("5L2g55qE5Yqo5omL"),
    _decode("6Z2i6K+V6L+96Zeu"),
    _decode("566A5Y6G"),
    _decode("NSDliIbpkp/orrLop6M="),
    _decode("6K6y6Kej56i/"),
]

PRIVATE_PATHS = [
    _decode("ZG9jcy9pbnRlcnZpZXcv"),
    _decode("ZG9jcy9sZWFybmluZy8="),
    _decode("c2NyaXB0cy9idWlsZF9yZXN1bWUucHk="),
    _decode("c2NyaXB0cy9pbXBvcnRfcmlza19mcm9tX2R1Y2tkYi5weQ=="),
]


def tracked_files() -> list[Path]:
    output = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True)
    return [ROOT / line for line in output.splitlines() if line.strip()]


def test_public_repo_has_no_private_material():
    files = tracked_files()
    names = {path.relative_to(ROOT).as_posix() for path in files}
    assert "docs/codex_log.md" in names
    for private in PRIVATE_PATHS:
        if private.endswith(".py"):
            assert private not in names
        else:
            assert not any(name.startswith(private) for name in names)


def test_public_text_is_clean():
    for path in tracked_files():
        if path.suffix.lower() not in {".md", ".py", ".ipynb", ".sql", ".toml", ".txt", ".yml"}:
            continue
        if path.name == "test_public_content.py":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for word in FORBIDDEN_TERMS:
            assert word not in text, f"forbidden term found in {path.relative_to(ROOT)}"


def test_readme_links_project():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "https://github.com/owenweisj-creator/consumer-finance-approval-analysis" in readme
