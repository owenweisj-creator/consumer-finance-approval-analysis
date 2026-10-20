import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_six_sql_files_exist():
    files = sorted((ROOT / "sql").glob("*.sql"))
    assert len(files) == 6


def test_six_notebooks_exist_and_are_valid_json():
    files = sorted((ROOT / "notebooks").glob("*.ipynb"))
    assert len(files) == 6
    for path in files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["nbformat"] == 4
        assert payload["cells"]

