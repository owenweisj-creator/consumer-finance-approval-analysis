"""校验 PBIP 工程：JSON 可解析、引用字段存在、页面/视觉数量完整。"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PBI = ROOT / "powerbi"
PROJECT = "消费金融审批分析"
SM = PBI / f"{PROJECT}.SemanticModel" / "definition"
RP = PBI / f"{PROJECT}.Report" / "definition"


def load_model() -> dict[str, dict[str, set[str]]]:
    tables: dict[str, dict[str, set[str]]] = {}
    for path in sorted((SM / "tables").glob("*.tmdl")):
        columns: set[str] = set()
        measures: set[str] = set()
        table = path.stem
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line.startswith("table "):
                table = line[len("table "):].strip()
            elif line.startswith("column "):
                columns.add(line[len("column "):].strip().strip("'"))
            elif line.startswith("measure "):
                match = re.match(r"measure '([^']+)'", line) or re.match(r"measure (\S+) =", line)
                if match:
                    measures.add(match.group(1))
        tables[table] = {"columns": columns, "measures": measures}
    return tables


def main() -> int:
    problems: list[str] = []
    tables = load_model()
    if not tables:
        problems.append("语义模型为空")
    for table, spec in tables.items():
        conflict = spec["columns"] & spec["measures"]
        if conflict:
            problems.append(f"{table} 中列与度量值同名：{'、'.join(sorted(conflict))}")

    pages_file = RP / "pages" / "pages.json"
    if not pages_file.exists():
        problems.append("缺少 pages.json")
        pages: list[str] = []
    else:
        pages = json.loads(pages_file.read_text(encoding="utf-8"))["pageOrder"]

    visual_count = 0
    for page in pages:
        page_dir = RP / "pages" / page
        if not (page_dir / "page.json").exists():
            problems.append(f"{page} 缺少 page.json")
        for visual_file in sorted((page_dir / "visuals").glob("*/visual.json")):
            visual_count += 1
            payload = json.loads(visual_file.read_text(encoding="utf-8"))
            query = payload.get("visual", {}).get("query", {}).get("queryState", {})
            for role, spec in query.items():
                for projection in spec.get("projections", []):
                    field = projection["field"]
                    kind = "Measure" if "Measure" in field else "Column"
                    expr = field[kind]
                    entity = expr["Expression"]["SourceRef"]["Entity"]
                    prop = expr["Property"]
                    bucket = "measures" if kind == "Measure" else "columns"
                    if entity not in tables:
                        problems.append(f"{visual_file.parent.name}: 表 {entity} 不存在")
                    elif prop not in tables[entity][bucket]:
                        problems.append(f"{visual_file.parent.name}: {kind} {entity}.{prop} 不存在")
                    if projection.get("queryRef") != f"{entity}.{prop}":
                        problems.append(f"{visual_file.parent.name}: queryRef 与实际字段不一致")

    if len(pages) != 4:
        problems.append(f"页面数量为 {len(pages)}，期望 4")
    for path in RP.rglob("*.json"):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            problems.append(f"{path.name} JSON 解析失败: {exc}")

    print(f"表 {len(tables)} 张｜页面 {len(pages)} 个｜视觉 {visual_count} 个")
    if problems:
        print("发现问题：")
        for item in problems:
            print(" -", item)
        return 1
    print("校验通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
