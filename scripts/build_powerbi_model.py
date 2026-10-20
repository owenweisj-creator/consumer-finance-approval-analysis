from __future__ import annotations

import subprocess
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PBI = ROOT / "powerbi"
MODEL = PBI / "Model"
PBI_TOOLS = Path(r"E:\ai数据分析工作\_archive\pbi-tools-full\app\pbi-tools.exe")


TABLES = {
    "月度经营": {
        "csv": "月度经营.csv",
        "columns": [
            ("月份", "string", "月份", "none"),
            ("月份序号", "int64", "月份序号", "none"),
            ("进件量", "int64", "进件量", "sum"),
            ("审批通过量", "int64", "审批通过量", "sum"),
            ("实际用信量", "int64", "实际用信量", "sum"),
            ("月度通过率", "double", "审批通过率", "none"),
            ("月度用信率", "double", "用信率", "none"),
            ("审批金额", "double", "审批金额", "sum"),
            ("月度件均", "double", "件均", "none"),
        ],
        "measures": [
            ("进件量合计", "SUM('月度经营'[进件量])", "#,0", "核心指标"),
            ("审批通过量合计", "SUM('月度经营'[审批通过量])", "#,0", "核心指标"),
            ("整体审批通过率", "DIVIDE(SUM('月度经营'[审批通过量]), SUM('月度经营'[进件量]))", "0.00%", "核心指标"),
            ("整体用信率", "DIVIDE(SUM('月度经营'[实际用信量]), SUM('月度经营'[审批通过量]))", "0.00%", "核心指标"),
            ("审批金额合计", "SUM('月度经营'[审批金额])", "#,0.00", "核心指标"),
            ("整体件均", "DIVIDE([审批金额合计], SUM('月度经营'[实际用信量]))", "#,0.00", "核心指标"),
            (
                "最新月进件量",
                "VAR 最新月 = CALCULATE(MAX('月度经营'[月份]), REMOVEFILTERS('月度经营')) "
                "RETURN CALCULATE([进件量合计], REMOVEFILTERS('月度经营'), '月度经营'[月份] = 最新月)",
                "#,0",
                "最新月",
            ),
            (
                "最新月审批通过率",
                "VAR 最新月 = CALCULATE(MAX('月度经营'[月份]), REMOVEFILTERS('月度经营')) "
                "RETURN CALCULATE([整体审批通过率], REMOVEFILTERS('月度经营'), '月度经营'[月份] = 最新月)",
                "0.00%",
                "最新月",
            ),
            (
                "最新月用信率",
                "VAR 最新月 = CALCULATE(MAX('月度经营'[月份]), REMOVEFILTERS('月度经营')) "
                "RETURN CALCULATE([整体用信率], REMOVEFILTERS('月度经营'), '月度经营'[月份] = 最新月)",
                "0.00%",
                "最新月",
            ),
            (
                "最新月审批金额",
                "VAR 最新月 = CALCULATE(MAX('月度经营'[月份]), REMOVEFILTERS('月度经营')) "
                "RETURN CALCULATE([审批金额合计], REMOVEFILTERS('月度经营'), '月度经营'[月份] = 最新月)",
                "#,0.00",
                "最新月",
            ),
            (
                "最新月件均",
                "VAR 最新月 = CALCULATE(MAX('月度经营'[月份]), REMOVEFILTERS('月度经营')) "
                "RETURN CALCULATE([整体件均], REMOVEFILTERS('月度经营'), '月度经营'[月份] = 最新月)",
                "#,0.00",
                "最新月",
            ),
        ],
    },
    "渠道归因": {
        "csv": "渠道归因.csv",
        "columns": [
            ("渠道类型", "string", "渠道类型", "none"),
            ("基期占比", "double", "基期占比", "none"),
            ("当期占比", "double", "当期占比", "none"),
            ("基期通过率", "double", "基期通过率", "none"),
            ("当期通过率", "double", "当期通过率", "none"),
            ("结构效应(pp)", "double", "结构效应(pp)", "none"),
            ("比率效应(pp)", "double", "比率效应(pp)", "none"),
            ("总效应(pp)", "double", "总效应(pp)", "none"),
        ],
        "measures": [
            ("结构效应合计", "SUM('渠道归因'[结构效应(pp)])", "0.00", "归因"),
            ("比率效应合计", "SUM('渠道归因'[比率效应(pp)])", "0.00", "归因"),
            ("总效应合计", "SUM('渠道归因'[总效应(pp)])", "0.00", "归因"),
            ("基期结构占比", "AVERAGE('渠道归因'[基期占比])", "0.00%", "归因"),
            ("当期结构占比", "AVERAGE('渠道归因'[当期占比])", "0.00%", "归因"),
            ("基期渠道通过率", "AVERAGE('渠道归因'[基期通过率])", "0.00%", "归因"),
            ("当期渠道通过率", "AVERAGE('渠道归因'[当期通过率])", "0.00%", "归因"),
        ],
    },
    "渠道表现": {
        "csv": "渠道表现.csv",
        "columns": [
            ("渠道类型", "string", "渠道类型", "none"),
            ("进件量", "int64", "进件量", "sum"),
            ("审批通过率", "double", "审批通过率", "none"),
            ("审批金额", "double", "审批金额", "sum"),
            ("DPD30率", "double", "DPD30率", "none"),
        ],
        "measures": [
            ("渠道进件量", "SUM('渠道表现'[进件量])", "#,0", "渠道"),
            ("渠道通过率", "AVERAGE('渠道表现'[审批通过率])", "0.00%", "渠道"),
            ("渠道DPD30", "AVERAGE('渠道表现'[DPD30率])", "0.00%", "渠道"),
            ("渠道审批金额", "SUM('渠道表现'[审批金额])", "#,0.00", "渠道"),
            (
                "整体DPD30",
                "DIVIDE(SUMX('渠道表现', '渠道表现'[DPD30率] * '渠道表现'[进件量]), SUM('渠道表现'[进件量]))",
                "0.00%",
                "渠道",
            ),
            (
                "加权通过率",
                "DIVIDE(SUMX('渠道表现', '渠道表现'[审批通过率] * '渠道表现'[进件量]), SUM('渠道表现'[进件量]))",
                "0.00%",
                "渠道",
            ),
        ],
    },
    "指标口径": {
        "csv": "指标口径.csv",
        "columns": [
            ("指标", "string", "指标", "none"),
            ("口径", "string", "口径", "none"),
        ],
        "measures": [],
    },
}


def col_line(name: str, data_type: str, source: str, summarize: str) -> str:
    formatted = f"'{name}'" if "(" in name or ")" in name else name
    return (
        f"\tcolumn {formatted}\n"
        f"\t\tdataType: {data_type}\n"
        f"\t\tsummarizeBy: {summarize}\n"
        f"\t\tsourceColumn: {source}\n"
    )


def table_tmdl(name: str, spec: dict) -> str:
    lines = [f"table {name}", ""]
    for col, dtype, source, summarize in spec["columns"]:
        lines.append(col_line(col, dtype, source, summarize))
    for measure, expr, fmt, folder in spec["measures"]:
        lines.append(f"\tmeasure '{measure}' = {expr}")
        lines.append(f"\t\tformatString: {fmt}")
        lines.append(f"\t\tdisplayFolder: {folder}")
        lines.append("")
    csv_path = (PBI / "data" / spec["csv"]).as_posix()
    changes = ", ".join(
        f'{{"{source}", {"Int64.Type" if dtype == "int64" else "type number" if dtype == "double" else "type text"}}}'
        for _, dtype, source, _ in spec["columns"]
    )
    lines.extend(
        [
            f"\tpartition '{name}' = m",
            "\t\tmode: import",
            "\t\tsource =",
            "\t\t\tlet",
            f'\t\t\t    Source = Csv.Document(File.Contents("{csv_path}"),[Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),',
            '\t\t\t    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),',
            f'\t\t\t    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{{{changes}}})',
            "\t\t\tin",
            '\t\t\t    #"Changed Type"',
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    MODEL.mkdir(parents=True, exist_ok=True)
    (MODEL / "tables").mkdir(exist_ok=True)
    (PBI / ".pbixproj.json").write_text(
        json.dumps(
            {
                "version": "1.0",
                "created": datetime.now().astimezone().isoformat(),
                "lastModified": datetime.now().astimezone().isoformat(),
                "settings": {"model": {"serializationMode": "Tmdl"}},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (MODEL / "database.tmdl").write_text("database ConsumerFinance\n\tcompatibilityLevel: 1606\n", encoding="utf-8")
    (MODEL / "model.tmdl").write_text(
        "model Model\n"
        "\tculture: zh-CN\n"
        "\tdefaultPowerBIDataSourceVersion: powerBI_V3\n",
        encoding="utf-8",
    )
    for name, spec in TABLES.items():
        (MODEL / "tables" / f"{name}.tmdl").write_text(table_tmdl(name, spec), encoding="utf-8")
    result = subprocess.run([str(PBI_TOOLS), "generate-bim", str(PBI)], capture_output=True, text=True)
    print(result.stdout)
    print(result.stderr)
    print("exit", result.returncode)


if __name__ == "__main__":
    main()
