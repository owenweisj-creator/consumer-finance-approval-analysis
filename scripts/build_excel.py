from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import xlsxwriter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.db import query_df

NAVY = "#173B57"
TEAL = "#0E7C86"
LIGHT = "#E6F3F4"
GRAY = "#6B7280"


def write_table(workbook, ws, df: pd.DataFrame, start_row: int, start_col: int = 0, formats: dict | None = None, widths: dict | None = None) -> int:
    header = workbook.add_format({"bold": True, "font_color": "#FFFFFF", "bg_color": NAVY, "align": "center", "valign": "vcenter", "font_name": "Microsoft YaHei"})
    text = workbook.add_format({"font_name": "Microsoft YaHei", "font_size": 10})
    for j, col in enumerate(df.columns):
        ws.write(start_row, start_col + j, str(col), header)
        if widths and col in widths:
            ws.set_column(start_col + j, start_col + j, widths[col])
    for i, (_, row) in enumerate(df.iterrows(), start=start_row + 1):
        for j, col in enumerate(df.columns):
            value = row[col]
            fmt = (formats or {}).get(col, text)
            if pd.isna(value):
                ws.write_blank(i, start_col + j, None, fmt)
            elif isinstance(value, (int, float)):
                ws.write_number(i, start_col + j, float(value), fmt)
            else:
                ws.write(i, start_col + j, str(value), fmt)
    return start_row + len(df) + 2


def main() -> None:
    out = ROOT / "outputs" / "excel"
    out.mkdir(parents=True, exist_ok=True)
    path = out / "审批通过率专项分析.xlsx"

    kpi = query_df("SELECT * FROM `v_申请审批月度` ORDER BY `月份` DESC LIMIT 2")
    cur, prev = kpi.iloc[0], kpi.iloc[1]
    trend = query_df("SELECT * FROM `v_申请审批月度` WHERE `月份` >= '2025-10' ORDER BY `月份`")
    channel = query_df("SELECT * FROM `v_渠道月度` WHERE `月份` = %s ORDER BY `进件量` DESC", [cur["月份"]])
    decomp = query_df("SELECT * FROM `v_渠道归因` ORDER BY `总效应`")
    risk = query_df("SELECT * FROM `v_还款风险`")
    risk_merged = channel.merge(risk, on="渠道类型", how="left")

    wb = xlsxwriter.Workbook(str(path))
    wb.set_properties({"title": "审批通过率下降专项分析", "author": "魏嗣杰"})
    title = wb.add_format({"bold": True, "font_size": 20, "font_color": NAVY, "font_name": "Microsoft YaHei"})
    sub = wb.add_format({"font_size": 10, "font_color": GRAY, "font_name": "Microsoft YaHei"})
    section = wb.add_format({"bold": True, "font_size": 12, "font_color": NAVY, "bottom": 1, "bottom_color": TEAL, "font_name": "Microsoft YaHei"})
    pct_fmt = wb.add_format({"num_format": "0.00%", "font_name": "Microsoft YaHei", "font_size": 10})
    pp_fmt = wb.add_format({"num_format": "+0.00%;-0.00%", "font_name": "Microsoft YaHei", "font_size": 10})
    num_fmt = wb.add_format({"num_format": "#,##0", "font_name": "Microsoft YaHei", "font_size": 10})
    money_fmt = wb.add_format({"num_format": "#,##0.00", "font_name": "Microsoft YaHei", "font_size": 10})

    # 结论摘要
    ws = wb.add_worksheet("结论摘要")
    ws.hide_gridlines(2)
    ws.set_column("A:A", 3)
    ws.set_column("B:B", 24)
    ws.set_column("C:C", 90)
    ws.write("B2", "审批通过率下降专项分析", title)
    ws.write("B4", "分析问题", section)
    ws.write("C4", "2026-09 审批通过率为什么从 29.4% 降到 22.9%？是渠道结构还是审批变严？", sub)
    ws.write("B5", "核心结论", section)
    ws.write("C5", "结构效应约 -5.39pp、比率效应约 -1.13pp，总效应 -6.52pp；低通过率渠道占比上升是主因。", sub)
    ws.write("B6", "金额变化", section)
    ws.write("C6", f"审批金额 {cur['审批金额']:,.2f} 万元，环比 {(cur['审批金额']/prev['审批金额']-1):.1%}；增长主要靠件均，不靠件数。", sub)
    ws.write("B7", "风险验证", section)
    ws.write("C7", "低通过率渠道并不必然低 DPD30；只能看获批客户，存在选择偏差，不能做因果解释。", sub)
    ws.write("B8", "数据说明", section)
    ws.write("C8", "Home Credit 公开数据；金额万元（归一化）；日期为模拟业务日历。", sub)

    # 月度趋势
    ws = wb.add_worksheet("月度趋势")
    ws.hide_gridlines(2)
    ws.write("A1", "月度经营趋势", title)
    display = trend.rename(columns={"月份": "月份"}).copy()
    for col in ["审批通过率", "用信率"]:
        display[col] = display[col] * 100
    end = write_table(
        wb,
        ws,
        display,
        3,
        formats={"进件量": num_fmt, "审批通过量": num_fmt, "实际用信量": num_fmt, "审批金额": money_fmt, "件均": money_fmt, "审批通过率": money_fmt, "用信率": money_fmt},
        widths={"月份": 10, "进件量": 11, "审批通过量": 12, "实际用信量": 12, "审批通过率": 12, "用信率": 10, "审批金额": 14, "件均": 10},
    )
    chart = wb.add_chart({"type": "column"})
    chart.add_series({"name": "进件量", "categories": ["月度趋势", 4, 0, end - 2, 0], "values": ["月度趋势", 4, 1, end - 2, 1], "fill": {"color": TEAL}})
    line = wb.add_chart({"type": "line"})
    line.add_series({"name": "审批通过率(%)", "categories": ["月度趋势", 4, 0, end - 2, 0], "values": ["月度趋势", 4, 4, end - 2, 4], "y2_axis": True, "line": {"color": "#D97706", "width": 2}})
    chart.combine(line)
    chart.set_title({"name": "进件量与审批通过率"})
    chart.set_size({"width": 760, "height": 340})
    ws.insert_chart("K3", chart)

    # 渠道贡献
    ws = wb.add_worksheet("渠道贡献")
    ws.hide_gridlines(2)
    ws.write("A1", "渠道对通过率变化的贡献", title)
    d = decomp.copy()
    for col in ["基期占比", "当期占比", "基期通过率", "当期通过率", "结构效应", "比率效应", "总效应"]:
        d[col] = d[col] * 100
    write_table(
        wb,
        ws,
        d,
        3,
        formats={c: money_fmt for c in d.columns if c != "渠道类型"},
        widths={"渠道类型": 26, **{c: 12 for c in d.columns if c != "渠道类型"}},
    )

    # 风险验证
    ws = wb.add_worksheet("风险验证")
    ws.hide_gridlines(2)
    ws.write("A1", "审批通过率与 DPD30", title)
    r = risk_merged[["渠道类型", "进件量", "审批通过率", "DPD30率"]].copy()
    r["审批通过率"] = r["审批通过率"] * 100
    r["DPD30率"] = r["DPD30率"] * 100
    write_table(wb, ws, r, 3, formats={"进件量": num_fmt, "审批通过率": money_fmt, "DPD30率": money_fmt}, widths={"渠道类型": 26, "进件量": 12, "审批通过率": 14, "DPD30率": 12})

    # 口径
    ws = wb.add_worksheet("口径说明")
    ws.hide_gridlines(2)
    ws.write("A1", "指标口径", title)
    metrics = pd.DataFrame(
        [
            ("进件量", "全部申请笔数"),
            ("审批通过率", "（Approved + Unused offer）/ 进件量"),
            ("用信率", "Approved /（Approved + Unused offer）"),
            ("审批金额", "Approved 合同金额合计，万元"),
            ("件均", "审批金额 / Approved 笔数"),
            ("结构效应", "渠道占比变化 × 基期渠道与整体通过率差"),
            ("比率效应", "当期渠道占比 × 渠道通过率变化"),
            ("DPD30", "单期最大逾期天数 ≥ 30；仅获批客户，存在选择偏差"),
        ],
        columns=["指标", "口径"],
    )
    write_table(wb, ws, metrics, 3, widths={"指标": 18, "口径": 70})

    wb.close()
    print(path)


if __name__ == "__main__":
    main()
