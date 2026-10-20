"""生成 Power BI 工程（PBIP）：语义模型 + 4 页中文报表定义。

产物：
    powerbi/消费金融审批分析.pbip
    powerbi/消费金融审批分析.SemanticModel/
    powerbi/消费金融审批分析.Report/

报表采用 PBIR 目录结构（definition/pages/...），与 Power BI Desktop 2025 之后
保存的 .pbip 工程一致，可直接双击 .pbip 打开。
"""

from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PBI = ROOT / "powerbi"
MODEL_SRC = PBI / "Model"

PROJECT_NAME = "消费金融审批分析"
PBIP = PBI / f"{PROJECT_NAME}.pbip"
SM_DIR = PBI / f"{PROJECT_NAME}.SemanticModel"
RP_DIR = PBI / f"{PROJECT_NAME}.Report"

NAVY = "#173B57"
ACCENT = "#0E7C86"
WARN = "#B42318"
MUTED = "#5A6B7B"
PAGE_BG = "#F5F7FA"
CARD_BG = "#FFFFFF"
BORDER = "#E3E9EF"

SCHEMA_VISUAL = (
    "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/"
    "visualContainer/2.13.0/schema.json"
)


# ---------------------------------------------------------------- 基础表达式


def lit(value: str) -> dict:
    return {"expr": {"Literal": {"Value": value}}}


def num(value: float | int) -> dict:
    text = f"{value}D" if isinstance(value, float) else f"{value}D"
    return lit(text)


def text(value: str) -> dict:
    return lit("'" + value.replace("'", "''") + "'")


def boolean(value: bool) -> dict:
    return lit("true" if value else "false")


def color(value: str) -> dict:
    return {"solid": {"color": text(value)}}


def column_field(entity: str, prop: str, active: bool = True) -> dict:
    return {
        "field": {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}},
        "queryRef": f"{entity}.{prop}",
        "nativeQueryRef": prop,
        "active": active,
    }


def measure_field(entity: str, prop: str, display: str | None = None) -> dict:
    return {
        "field": {"Measure": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}},
        "queryRef": f"{entity}.{prop}",
        "nativeQueryRef": display or prop,
    }


def container_objects(
    title: str | None = None,
    *,
    title_size: int = 12,
    background: str | None = CARD_BG,
    border: bool = True,
    header: bool = False,
) -> dict:
    objects: dict = {}
    if title is not None:
        objects["title"] = [
            {
                "properties": {
                    "show": boolean(True),
                    "text": text(title),
                    "fontSize": num(title_size),
                    "fontColor": color(NAVY),
                }
            }
        ]
    if background is not None:
        objects["background"] = [
            {"properties": {"show": boolean(True), "color": color(background), "transparency": num(0)}}
        ]
    if border:
        objects["border"] = [
            {"properties": {"show": boolean(True), "color": color(BORDER), "radius": num(8)}}
        ]
    if not header:
        objects["visualHeader"] = [{"properties": {"show": boolean(False)}}]
    return objects


def visual(
    name: str,
    visual_type: str,
    position: dict,
    *,
    query_state: dict | None = None,
    objects: dict | None = None,
    container: dict | None = None,
    sort: dict | None = None,
) -> dict:
    body: dict = {"visualType": visual_type}
    if query_state is not None:
        query: dict = {"queryState": query_state}
        if sort is not None:
            query["sortDefinition"] = sort
        body["query"] = query
    if objects:
        body["objects"] = objects
    if container:
        body["visualContainerObjects"] = container
    body["drillFilterOtherVisuals"] = True
    return {
        "$schema": SCHEMA_VISUAL,
        "name": name,
        "position": position,
        "visual": body,
    }


def pos(x: float, y: float, w: float, h: float, z: int, tab: int) -> dict:
    return {"x": x, "y": y, "z": z, "height": h, "width": w, "tabOrder": tab}


# ---------------------------------------------------------------- 视觉元素


def text_block(
    name: str,
    x: float,
    y: float,
    w: float,
    h: float,
    paragraphs: list[dict],
    *,
    z: int = 0,
    tab: int = 0,
) -> dict:
    return visual(
        name,
        "textbox",
        pos(x, y, w, h, z, tab),
        objects={"general": [{"properties": {"paragraphs": paragraphs}}]},
        container={"background": [{"properties": {"show": boolean(False)}}],
                   "visualHeader": [{"properties": {"show": boolean(False)}}]},
    )


def para(runs: list[tuple[str, dict]], *, align: str = "left", space_after: int = 0) -> dict:
    return {
        "textRuns": [{"value": value, "textStyle": style} for value, style in runs],
        "horizontalTextAlignment": align,
        "spaceAfter": f"{space_after}pt" if space_after else "0pt",
    }


def run_style(
    size: int,
    *,
    bold: bool = False,
    color_hex: str = NAVY,
    family: str = "微软雅黑",
) -> dict:
    style = {"fontSize": f"{size}pt", "fontFamily": family, "color": color_hex}
    if bold:
        style["fontWeight"] = "bold"
    return style


def page_title(page_title: str, subtitle: str) -> list[dict]:
    return [
        text_block(
            "title",
            16,
            10,
            900,
            36,
            [para([(page_title, run_style(20, bold=True, color_hex=NAVY))])],
            z=100,
            tab=0,
        ),
        text_block(
            "subtitle",
            16,
            52,
            1100,
            24,
            [para([(subtitle, run_style(10, color_hex=MUTED))])],
            z=100,
            tab=1,
        ),
    ]


def kpi_card(
    name: str,
    title: str,
    entity: str,
    measure: str,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    z: int = 200,
    tab: int = 2,
) -> dict:
    return visual(
        name,
        "cardVisual",
        pos(x, y, w, h, z, tab),
        query_state={"Data": {"projections": [measure_field(entity, measure)]}},
        container=container_objects(title, title_size=11),
    )


def combo_chart(name: str, x: float, y: float, w: float, h: float) -> dict:
    return visual(
        name,
        "lineStackedColumnComboChart",
        pos(x, y, w, h, 300, 10),
        query_state={
            "Category": {"projections": [column_field("月度经营", "月份")]},
            "Y": {"projections": [measure_field("月度经营", "进件量合计", "进件量")]},
            "Y2": {"projections": [measure_field("月度经营", "整体审批通过率")]},
        },
        container=container_objects("月度进件量与审批通过率", title_size=13),
    )


def bar_chart(
    name: str,
    title: str,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    measures: list[tuple[str, str]],
    sort_measure: str,
    colors: list[str] | None = None,
    horizontal: bool = True,
    z: int = 300,
    tab: int = 10,
) -> dict:
    projections = [measure_field("渠道归因", m, m) for m in measures]
    return visual(
        name,
        "clusteredBarChart" if horizontal else "clusteredColumnChart",
        pos(x, y, w, h, z, tab),
        query_state={
            "Category": {"projections": [column_field("渠道归因", "渠道类型")]},
            "Y": {"projections": projections},
        },
        container=container_objects(title, title_size=13),
        sort={
            "sort": [
                {
                    "field": {
                        "Measure": {
                            "Expression": {"SourceRef": {"Entity": "渠道归因"}},
                            "Property": sort_measure,
                        }
                    },
                    "direction": "Descending",
                }
            ]
        },
    )


def table_visual(
    name: str,
    title: str,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    items: list[tuple[str, str, str, str]],
    z: int = 300,
    tab: int = 20,
) -> dict:
    """表格视觉：items 为 (类型, 实体, 字段, 显示名)，类型取 col 或 meas。"""
    projections = []
    for kind, entity, prop, display in items:
        if kind == "meas":
            projection = measure_field(entity, prop, display)
        else:
            projection = column_field(entity, prop)
            projection.pop("active", None)
        if display:
            projection["displayName"] = display
        projections.append(projection)
    return visual(
        name,
        "tableEx",
        pos(x, y, w, h, z, tab),
        query_state={"Values": {"projections": projections}},
        container=container_objects(title, title_size=13),
    )


def month_slicer(name: str, x: float, y: float, w: float, h: float) -> dict:
    return visual(
        name,
        "slicer",
        pos(x, y, w, h, 300, 5),
        query_state={"Values": {"projections": [column_field("月度经营", "月份")]}},
        objects={
            "data": [{"properties": {"mode": text("Dropdown")}}],
            "general": [{"properties": {"selfFilterEnabled": boolean(True)}}],
        },
        container=container_objects(None, title_size=11),
    )


# ---------------------------------------------------------------- 页面定义


def page_overview() -> dict:
    visuals = page_title(
        "消费金融审批通过率专项｜经营总览",
        "数据窗口 2025-04 至 2026-09｜金额单位：万元（归一化）｜观察基准日 2026-09-30",
    )
    cards = [
        ("kpi_apps", "进件量（笔，2026-09）", "当月指标", "当月进件量"),
        ("kpi_pass", "审批通过率（2026-09）", "当月指标", "当月审批通过率"),
        ("kpi_use", "用信率（2026-09）", "当月指标", "当月用信率"),
        ("kpi_amt", "审批金额（万元，2026-09）", "当月指标", "当月审批金额"),
        ("kpi_avg", "件均（万元，2026-09）", "当月指标", "当月件均"),
    ]
    for index, (name, title, entity, measure) in enumerate(cards):
        visuals.append(
            kpi_card(name, title, entity, measure, 16 + index * 248, 84, 236, 108, tab=2 + index)
        )
    visuals.append(combo_chart("combo_trend", 16, 204, 800, 496))
    visuals.append(month_slicer("slicer_month", 828, 204, 436, 132))
    visuals.append(
        text_block(
            "note_overview",
            828,
            348,
            436,
            352,
            [
                para([("口径与要点", run_style(12, bold=True, color_hex=NAVY))], space_after=6),
                para([("审批通过率 =（Approved + Unused offer）/ 全部进件。", run_style(10, color_hex=MUTED))], space_after=4),
                para([("2026-09：进件 36,012 笔，通过率 22.90%，环比 -6.52 个百分点。", run_style(10, color_hex=MUTED))], space_after=4),
                para([("同期进件量环比 +26.2%，属“量升率降”，需拆解渠道结构。", run_style(10, color_hex=MUTED))], space_after=4),
                para([("用信率 97.88%，审批后客户用信意愿稳定。", run_style(10, color_hex=MUTED))], space_after=4),
                para([("金额为归一化万元，仅用于结构与趋势比较。", run_style(10, color_hex=MUTED))]),
            ],
            z=300,
            tab=12,
        )
    )
    return {"name": "PageOverview", "displayName": "经营总览", "visuals": visuals}


def page_attribution() -> dict:
    visuals = page_title(
        "渠道归因｜结构效应与比率效应",
        "对比期 2026-08（基期）与 2026-09（当期）｜效应单位：个百分点（pp）",
    )
    cards = [
        ("eff_structure", "结构效应（pp）", "渠道归因", "结构效应合计"),
        ("eff_rate", "比率效应（pp）", "渠道归因", "比率效应合计"),
        ("eff_total", "总效应（pp）", "渠道归因", "总效应合计"),
    ]
    for index, (name, title, entity, measure) in enumerate(cards):
        visuals.append(
            kpi_card(name, title, entity, measure, 16 + index * 420, 84, 404, 108, tab=2 + index)
        )
    visuals.append(
        bar_chart(
            "bar_total_effect",
            "各渠道总效应（pp）",
            16,
            204,
            608,
            300,
            measures=["总效应合计"],
            sort_measure="总效应合计",
            colors=[ACCENT],
            z=300,
            tab=10,
        )
    )
    visuals.append(
        bar_chart(
            "bar_effect_split",
            "结构效应与比率效应对比（pp）",
            640,
            204,
            624,
            300,
            measures=["结构效应合计", "比率效应合计"],
            sort_measure="结构效应合计",
            colors=[NAVY, "#C8A24A"],
            z=300,
            tab=11,
        )
    )
    visuals.append(
        text_block(
            "note_attr",
            16,
            516,
            400,
            184,
            [
                para([("结论", run_style(12, bold=True, color_hex=NAVY))], space_after=6),
                para([("结构效应 -5.39pp、比率效应 -1.13pp，下降主要来自渠道结构变化，而非同一渠道审批标准整体收紧。", run_style(10, color_hex=MUTED))], space_after=4),
                para([("需重点跟踪 Country-wide 与 Stone 两个高通过率渠道的占比变化。", run_style(10, color_hex=MUTED))]),
            ],
            z=300,
            tab=12,
        )
    )
    visuals.append(
        table_visual(
            "table_attr",
            "渠道归因明细",
            428,
            516,
            836,
            184,
            items=[
                ("col", "渠道归因", "渠道类型", "渠道类型"),
                ("meas", "渠道归因", "基期结构占比", "基期占比"),
                ("meas", "渠道归因", "当期结构占比", "当期占比"),
                ("meas", "渠道归因", "基期渠道通过率", "基期通过率"),
                ("meas", "渠道归因", "当期渠道通过率", "当期通过率"),
                ("meas", "渠道归因", "结构效应合计", "结构效应(pp)"),
                ("meas", "渠道归因", "比率效应合计", "比率效应(pp)"),
                ("meas", "渠道归因", "总效应合计", "总效应(pp)"),
            ],
            z=300,
            tab=13,
        )
    )
    return {"name": "PageAttribution", "displayName": "渠道归因", "visuals": visuals}


def page_risk() -> dict:
    visuals = page_title(
        "风险验证｜审批通过率与 DPD30",
        "DPD30 仅统计获批且已放款客户，存在选择偏差｜观察期 2026-09 放款 cohort",
    )
    risk_cards = [
        ("risk_pass", "加权审批通过率", "渠道表现", "加权通过率"),
        ("risk_dpd", "加权 DPD30", "渠道表现", "整体DPD30"),
        ("risk_amt", "审批金额（万元）", "渠道表现", "渠道审批金额"),
    ]
    for index, (name, title, entity, measure) in enumerate(risk_cards):
        visuals.append(
            kpi_card(name, title, entity, measure, 16 + index * 420, 84, 404, 108, tab=2 + index)
        )
    visuals.append(
        visual(
            "bar_dpd",
            "clusteredBarChart",
            pos(16, 204, 608, 300, 300, 10),
            query_state={
                "Category": {"projections": [column_field("渠道表现", "渠道类型")]},
                "Y": {"projections": [measure_field("渠道表现", "渠道DPD30", "DPD30 率")]},
            },
            container=container_objects("各渠道 DPD30 率", title_size=13),
            sort={
                "sort": [
                    {
                        "field": {
                            "Measure": {
                                "Expression": {"SourceRef": {"Entity": "渠道表现"}},
                                "Property": "渠道DPD30",
                            }
                        },
                        "direction": "Descending",
                    }
                ]
            },
        )
    )
    visuals.append(
        table_visual(
            "table_risk",
            "渠道风险矩阵",
            640,
            204,
            624,
            300,
            items=[
                ("col", "渠道表现", "渠道类型", "渠道类型"),
                ("meas", "渠道表现", "渠道进件量", "进件量"),
                ("meas", "渠道表现", "渠道通过率", "审批通过率"),
                ("meas", "渠道表现", "渠道DPD30", "DPD30 率"),
                ("meas", "渠道表现", "渠道审批金额", "审批金额（万元）"),
            ],
            z=300,
            tab=11,
        )
    )
    visuals.append(
        text_block(
            "note_risk",
            16,
            516,
            1248,
            184,
            [
                para([("风险结论", run_style(12, bold=True, color_hex=NAVY))], space_after=6),
                para([("1. Contact center 通过率最低（4.33%）且 DPD30 最高（4.80%），是风险最集中的入口。", run_style(10, color_hex=MUTED))], space_after=4),
                para([("2. Country-wide、Stone、Regional / Local 通过率约 87%~88%，DPD30 集中在 1.9%~3.0%，属于“高通过、可控风险”渠道。", run_style(10, color_hex=MUTED))], space_after=4),
                para([("3. 通过率下降主要来自高通过率渠道占比下降，暂未观察到“放松审批换规模”的迹象；但 DPD30 只覆盖获批客户，不能直接外推至全部进件。", run_style(10, color_hex=MUTED))]),
            ],
            z=300,
            tab=12,
        )
    )
    return {"name": "PageRisk", "displayName": "风险验证", "visuals": visuals}


def page_dictionary() -> dict:
    visuals = page_title(
        "指标口径与数据说明",
        "口径与 sql/02_清洗与指标口径.sql、notebooks/02 完全一致",
    )
    visuals.append(
        table_visual(
            "table_dict",
            "指标口径表",
            16,
            84,
            828,
            616,
            items=[
                ("col", "指标口径", "指标", "指标"),
                ("col", "指标口径", "口径", "口径"),
            ],
            z=300,
            tab=2,
        )
    )
    visuals.append(
        text_block(
            "note_source",
            856,
            84,
            408,
            616,
            [
                para([("数据来源", run_style(12, bold=True, color_hex=NAVY))], space_after=6),
                para([("Home Credit 公开数据集 previous_application 与 installments_payments，经 MySQL 装载并按业务日历映射为 2025-04 至 2026-09。", run_style(10, color_hex=MUTED))], space_after=8),
                para([("模型结构", run_style(12, bold=True, color_hex=NAVY))], space_after=6),
                para([("5 张汇总表：月度经营（18 行）、当月指标（1 行）、渠道归因（7 行）、渠道表现（7 行）、指标口径（8 行），由 scripts/build_powerbi_data.py 从 MySQL 视图导出。", run_style(10, color_hex=MUTED))], space_after=8),
                para([("使用限制", run_style(12, bold=True, color_hex=NAVY))], space_after=6),
                para([("金额为归一化万元；业务日期为映射后的模拟时间；数据不含获客成本与利润，不做 CAC / ROI 结论。", run_style(10, color_hex=MUTED))], space_after=8),
                para([("刷新方式", run_style(12, bold=True, color_hex=NAVY))], space_after=6),
                para([("重新导出 CSV 后，在 Power BI 中点击“刷新”即可更新全部图表与卡片。", run_style(10, color_hex=MUTED))]),
            ],
            z=300,
            tab=3,
        )
    )
    return {"name": "PageDictionary", "displayName": "指标口径", "visuals": visuals}


# ---------------------------------------------------------------- 工程落盘


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def logical_id(kind: str) -> str:
    """固定 logicalId，避免每次生成都产生无意义 diff。"""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"consumer-finance-approval/{kind}"))


def build_semantic_model() -> None:
    if SM_DIR.exists():
        shutil.rmtree(SM_DIR)
    definition = SM_DIR / "definition"
    (definition / "tables").mkdir(parents=True, exist_ok=True)
    shutil.copy2(MODEL_SRC / "database.tmdl", definition / "database.tmdl")
    shutil.copy2(MODEL_SRC / "model.tmdl", definition / "model.tmdl")
    for item in sorted((MODEL_SRC / "tables").glob("*.tmdl")):
        shutil.copy2(item, definition / "tables" / item.name)

    write_json(
        SM_DIR / ".platform",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
            "metadata": {"type": "SemanticModel", "displayName": PROJECT_NAME},
            "config": {"version": "2.0", "logicalId": logical_id("SemanticModel")},
        },
    )
    write_json(SM_DIR / "definition.pbism", {"version": "4.0", "settings": {}})


def build_report(pages: list[dict]) -> None:
    if RP_DIR.exists():
        shutil.rmtree(RP_DIR)
    definition = RP_DIR / "definition"
    write_json(
        RP_DIR / ".platform",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
            "metadata": {"type": "Report", "displayName": PROJECT_NAME},
            "config": {"version": "2.0", "logicalId": logical_id("Report")},
        },
    )
    write_json(
        RP_DIR / "definition.pbir",
        {
            "version": "4.0",
            "datasetReference": {"byPath": {"path": f"../{SM_DIR.name}"}},
        },
    )
    write_json(
        definition / "version.json",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
            "version": "2.0.0",
        },
    )
    write_json(
        definition / "report.json",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.3.0/schema.json",
            "themeCollection": {
                "baseTheme": {
                    "name": "Fluent2-CY26SU08",
                    "reportVersionAtImport": {"visual": "2.12.0", "report": "3.4.0", "page": "2.3.1"},
                    "type": "SharedResources",
                }
            },
            "objects": {
                "section": [{"properties": {"verticalAlignment": text("Top")}}],
                "outspacePane": [{"properties": {"visible": boolean(False)}}],
            },
            "settings": {
                "useStylableVisualContainerHeader": True,
                "exportDataMode": "AllowSummarized",
                "defaultDrillFilterOtherVisuals": True,
                "allowChangeFilterTypes": True,
                "useEnhancedTooltips": True,
                "defaultDisplayUnitsToNone": True,
            },
        },
    )
    write_json(
        definition / "pages" / "pages.json",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json",
            "pageOrder": [page["name"] for page in pages],
            "activePageName": pages[0]["name"],
            "landingPageName": pages[0]["name"],
        },
    )
    for page in pages:
        page_dir = definition / "pages" / page["name"]
        write_json(
            page_dir / "page.json",
            {
                "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
                "name": page["name"],
                "displayName": page["displayName"],
                "displayOption": "FitToPage",
                "height": 720,
                "width": 1280,
                "objects": {
                    "background": [{"properties": {"color": color(PAGE_BG), "transparency": num(0)}}]
                },
            },
        )
        for item in page["visuals"]:
            write_json(page_dir / "visuals" / item["name"] / "visual.json", item)


def main() -> None:
    if not (MODEL_SRC / "database.tmdl").exists():
        raise SystemExit("未找到 powerbi/Model，请先运行 scripts/build_powerbi_model.py")
    pages = [page_overview(), page_attribution(), page_risk(), page_dictionary()]
    build_semantic_model()
    build_report(pages)
    write_json(
        PBIP,
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
            "version": "1.0",
            "artifacts": [{"report": {"path": RP_DIR.name}}],
            "settings": {"enableAutoRecovery": True},
        },
    )
    total = sum(len(page["visuals"]) for page in pages)
    print(f"已生成 {PBIP}")
    print(f"页面 {len(pages)} 个，视觉元素 {total} 个")


if __name__ == "__main__":
    main()
