from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.db import query_df


def main() -> None:
    out = ROOT / "powerbi" / "data"
    out.mkdir(parents=True, exist_ok=True)

    monthly = query_df(
        """
        SELECT `月份`, `进件量`, `审批通过量`, `实际用信量`, `审批通过率`,
               `用信率`, `审批金额`, `件均`
        FROM `v_申请审批月度`
        WHERE `月份` >= '2025-04'
        ORDER BY `月份`
        """
    )
    monthly["月份序号"] = monthly["月份"].str.replace("-", "", regex=False).astype(int)
    monthly = monthly[
        ["月份", "月份序号", "进件量", "审批通过量", "实际用信量", "审批通过率", "用信率", "审批金额", "件均"]
    ]
    monthly.to_csv(out / "月度经营.csv", index=False, encoding="utf-8")

    decomp = query_df("SELECT * FROM `v_渠道归因` ORDER BY `总效应`")
    decomp["结构效应(pp)"] = decomp["结构效应"] * 100
    decomp["比率效应(pp)"] = decomp["比率效应"] * 100
    decomp["总效应(pp)"] = decomp["总效应"] * 100
    decomp = decomp[
        [
            "渠道类型",
            "基期占比",
            "当期占比",
            "基期通过率",
            "当期通过率",
            "结构效应(pp)",
            "比率效应(pp)",
            "总效应(pp)",
        ]
    ]
    decomp.to_csv(out / "渠道归因.csv", index=False, encoding="utf-8")

    latest = query_df("SELECT max(`月份`) AS m FROM `v_申请审批月度`").iloc[0, 0]
    channel = query_df(
        """
        SELECT `渠道类型`, `进件量`, `审批通过率`, `审批金额`
        FROM `v_渠道月度`
        WHERE `月份` = %s
        ORDER BY `进件量` DESC
        """,
        [latest],
    )
    risk = query_df("SELECT `渠道类型`, `DPD30率` FROM `v_还款风险`")
    channel = channel.merge(risk, on="渠道类型", how="left").fillna({"DPD30率": 0})
    channel.to_csv(out / "渠道表现.csv", index=False, encoding="utf-8")

    metrics = pd.DataFrame(
        [
            ("进件量", "统计期内全部申请笔数"),
            ("审批通过率", "（Approved + Unused offer）/ 进件量"),
            ("用信率", "Approved /（Approved + Unused offer）"),
            ("审批金额", "Approved 合同金额合计，万元（归一化）"),
            ("件均", "审批金额 / Approved 笔数"),
            ("结构效应", "渠道占比变化 × 基期渠道与整体通过率差"),
            ("比率效应", "当期渠道占比 × 渠道通过率变化"),
            ("DPD30", "单期最大逾期天数 ≥ 30；仅获批客户，存在选择偏差"),
        ],
        columns=["指标", "口径"],
    )
    metrics.to_csv(out / "指标口径.csv", index=False, encoding="utf-8")

    print("月度经营", len(monthly))
    print("渠道归因", len(decomp))
    print("渠道表现", len(channel))
    print("指标口径", len(metrics))


if __name__ == "__main__":
    main()
