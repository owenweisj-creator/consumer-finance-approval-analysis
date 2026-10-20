from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.db import query_df


def main() -> None:
    checks = {
        "申请行数": int(query_df("SELECT COUNT(*) AS n FROM `v_申请明细`").iloc[0, 0]),
        "还款行数": int(query_df("SELECT COUNT(*) AS n FROM `v_还款明细`").iloc[0, 0]),
        "最近两月": query_df("SELECT * FROM `v_申请审批月度` ORDER BY `月份` DESC LIMIT 2").to_dict(orient="records"),
        "归因合计": query_df(
            """
            SELECT ROUND(SUM(`结构效应`),4) AS 结构效应,
                   ROUND(SUM(`比率效应`),4) AS 比率效应,
                   ROUND(SUM(`总效应`),4) AS 总效应
            FROM `v_渠道归因`
            """
        ).to_dict(orient="records"),
        "渠道风险": query_df("SELECT * FROM `v_还款风险` ORDER BY `有还款记录合同数` DESC").to_dict(orient="records"),
    }
    print(json.dumps(checks, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
