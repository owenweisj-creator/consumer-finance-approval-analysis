from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.db import DB_CONFIG, connection

SUMMARY_NAMES = [
    "v_申请审批月度",
    "v_渠道月度",
    "v_渠道归因",
    "v_还款风险",
    "v_账龄迁徙",
]


def drop_object(cursor, name: str) -> None:
    cursor.execute(
        "SELECT TABLE_TYPE FROM information_schema.tables WHERE table_schema=%s AND table_name=%s",
        (DB_CONFIG["database"], name),
    )
    row = cursor.fetchone()
    if not row:
        return
    kind = "VIEW" if row["TABLE_TYPE"] == "VIEW" else "TABLE"
    cursor.execute(f"DROP {kind} IF EXISTS `{name}`")


def main() -> None:
    with connection() as conn:
        with conn.cursor() as cursor:
            for name in SUMMARY_NAMES:
                drop_object(cursor, name)
            conn.commit()

            print("生成 v_申请审批月度 ...")
            cursor.execute(
                """
                CREATE TABLE `v_申请审批月度` AS
                SELECT
                    DATE_FORMAT(decision_date, '%Y-%m') AS `月份`,
                    COUNT(*) AS `进件量`,
                    SUM(status IN ('Approved', 'Unused offer')) AS `审批通过量`,
                    SUM(status = 'Approved') AS `实际用信量`,
                    SUM(status = 'Refused') AS `拒绝量`,
                    SUM(status = 'Canceled') AS `取消量`,
                    SUM(status = 'Unused offer') AS `未使用额度量`,
                    ROUND(SUM(status IN ('Approved', 'Unused offer')) / NULLIF(COUNT(*), 0), 4) AS `审批通过率`,
                    ROUND(SUM(status = 'Approved') / NULLIF(SUM(status IN ('Approved', 'Unused offer')), 0), 4) AS `用信率`,
                    ROUND(SUM(CASE WHEN status = 'Approved' THEN approved_amount ELSE 0 END), 2) AS `审批金额`,
                    ROUND(SUM(CASE WHEN status = 'Approved' THEN approved_amount ELSE 0 END) / NULLIF(SUM(status = 'Approved'), 0), 2) AS `件均`
                FROM applications_new
                GROUP BY 1
                """
            )
            cursor.execute("ALTER TABLE `v_申请审批月度` ADD INDEX idx_month (`月份`)")
            conn.commit()

            print("生成 v_渠道月度 ...")
            cursor.execute(
                """
                CREATE TABLE `v_渠道月度` AS
                SELECT
                    DATE_FORMAT(decision_date, '%Y-%m') AS `月份`,
                    COALESCE(channel_type, '未知渠道') AS `渠道类型`,
                    COUNT(*) AS `进件量`,
                    SUM(status IN ('Approved', 'Unused offer')) AS `审批通过量`,
                    SUM(status = 'Approved') AS `实际用信量`,
                    ROUND(SUM(status IN ('Approved', 'Unused offer')) / NULLIF(COUNT(*), 0), 4) AS `审批通过率`,
                    ROUND(SUM(status = 'Approved') / NULLIF(SUM(status IN ('Approved', 'Unused offer')), 0), 4) AS `用信率`,
                    ROUND(SUM(CASE WHEN status = 'Approved' THEN approved_amount ELSE 0 END), 2) AS `审批金额`,
                    ROUND(SUM(CASE WHEN status = 'Approved' THEN approved_amount ELSE 0 END) / NULLIF(SUM(status = 'Approved'), 0), 2) AS `件均`
                FROM applications_new
                GROUP BY 1, 2
                """
            )
            cursor.execute("ALTER TABLE `v_渠道月度` ADD INDEX idx_month_channel (`月份`, `渠道类型`(100))")
            conn.commit()

            print("生成 v_渠道归因 ...")
            cursor.execute(
                """
                CREATE TABLE `v_渠道归因` AS
                WITH bounds AS (
                    SELECT MAX(`月份`) AS `当期`, (
                        SELECT MAX(`月份`) FROM `v_申请审批月度`
                        WHERE `月份` < (SELECT MAX(`月份`) FROM `v_申请审批月度`)
                    ) AS `基期`
                    FROM `v_申请审批月度`
                ),
                cur AS (
                    SELECT `渠道类型`, `进件量`, `审批通过量`, `审批通过率`
                    FROM `v_渠道月度` CROSS JOIN bounds WHERE `月份` = bounds.`当期`
                ),
                prev AS (
                    SELECT `渠道类型`, `进件量`, `审批通过量`, `审批通过率`
                    FROM `v_渠道月度` CROSS JOIN bounds WHERE `月份` = bounds.`基期`
                ),
                totals AS (
                    SELECT
                        (SELECT SUM(`进件量`) FROM cur) AS `当期进件`,
                        (SELECT SUM(`审批通过量`) FROM cur) AS `当期通过`,
                        (SELECT SUM(`进件量`) FROM prev) AS `基期进件`,
                        (SELECT SUM(`审批通过量`) FROM prev) AS `基期通过`
                )
                SELECT
                    COALESCE(c.`渠道类型`, p.`渠道类型`) AS `渠道类型`,
                    ROUND(COALESCE(p.`进件量`, 0) / NULLIF(t.`基期进件`, 0), 4) AS `基期占比`,
                    ROUND(COALESCE(c.`进件量`, 0) / NULLIF(t.`当期进件`, 0), 4) AS `当期占比`,
                    ROUND(COALESCE(p.`审批通过率`, 0), 4) AS `基期通过率`,
                    ROUND(COALESCE(c.`审批通过率`, 0), 4) AS `当期通过率`,
                    ROUND(
                        (COALESCE(c.`进件量`, 0) / NULLIF(t.`当期进件`, 0) - COALESCE(p.`进件量`, 0) / NULLIF(t.`基期进件`, 0))
                        * (COALESCE(p.`审批通过率`, 0) - t.`基期通过` / NULLIF(t.`基期进件`, 0)), 6
                    ) AS `结构效应`,
                    ROUND(
                        (COALESCE(c.`进件量`, 0) / NULLIF(t.`当期进件`, 0))
                        * (COALESCE(c.`审批通过率`, 0) - COALESCE(p.`审批通过率`, 0)), 6
                    ) AS `比率效应`,
                    ROUND(
                        (COALESCE(c.`进件量`, 0) / NULLIF(t.`当期进件`, 0) - COALESCE(p.`进件量`, 0) / NULLIF(t.`基期进件`, 0))
                        * (COALESCE(p.`审批通过率`, 0) - t.`基期通过` / NULLIF(t.`基期进件`, 0))
                        + (COALESCE(c.`进件量`, 0) / NULLIF(t.`当期进件`, 0))
                        * (COALESCE(c.`审批通过率`, 0) - COALESCE(p.`审批通过率`, 0)), 6
                    ) AS `总效应`
                FROM cur c
                LEFT JOIN prev p ON c.`渠道类型` = p.`渠道类型`
                CROSS JOIN totals t
                UNION ALL
                SELECT
                    p.`渠道类型`, ROUND(p.`进件量` / NULLIF(t.`基期进件`, 0), 4), 0,
                    ROUND(p.`审批通过率`, 4), 0,
                    ROUND((0 - p.`进件量` / NULLIF(t.`基期进件`, 0))
                          * (p.`审批通过率` - t.`基期通过` / NULLIF(t.`基期进件`, 0)), 6),
                    0,
                    ROUND((0 - p.`进件量` / NULLIF(t.`基期进件`, 0))
                          * (p.`审批通过率` - t.`基期通过` / NULLIF(t.`基期进件`, 0)), 6)
                FROM prev p
                CROSS JOIN totals t
                WHERE NOT EXISTS (SELECT 1 FROM cur c WHERE c.`渠道类型` = p.`渠道类型`)
                """
            )
            conn.commit()

            print("生成 v_还款风险 ...")
            cursor.execute(
                """
                CREATE TABLE `v_还款风险` AS
                WITH loan_risk AS (
                    SELECT previous_id, MAX(dpd30_flag) AS dpd30
                    FROM repayments_new
                    GROUP BY previous_id
                )
                SELECT
                    COALESCE(a.channel_type, '未知渠道') AS `渠道类型`,
                    COUNT(*) AS `有还款记录合同数`,
                    SUM(r.dpd30) AS `DPD30合同数`,
                    ROUND(AVG(r.dpd30), 4) AS `DPD30率`
                FROM applications_new a
                JOIN loan_risk r ON a.previous_id = r.previous_id
                WHERE a.status = 'Approved'
                GROUP BY 1
                """
            )
            conn.commit()

            print("生成 v_账龄迁徙 ...")
            cursor.execute(
                """
                CREATE TABLE `v_账龄迁徙` AS
                WITH first_due AS (
                    SELECT previous_id, MIN(due_date) AS first_due_date,
                           DATE_FORMAT(MIN(due_date), '%Y-%m-01') AS cohort_month
                    FROM repayments_new
                    GROUP BY previous_id
                ),
                loan_mob AS (
                    SELECT r.previous_id, f.cohort_month,
                           TIMESTAMPDIFF(MONTH, f.cohort_month, DATE_FORMAT(r.due_date, '%Y-%m-01')) AS mob,
                           MAX(r.dpd30_flag) AS dpd30
                    FROM repayments_new r
                    JOIN first_due f ON r.previous_id = f.previous_id
                    GROUP BY 1, 2, 3
                ),
                cumulative AS (
                    SELECT *, MAX(dpd30) OVER (PARTITION BY previous_id ORDER BY mob) AS cum_dpd30
                    FROM loan_mob
                )
                SELECT
                    cohort_month AS `放款cohort`,
                    mob AS `账龄月`,
                    COUNT(*) AS `贷款数`,
                    ROUND(AVG(cum_dpd30), 4) AS `累计DPD30率`
                FROM cumulative
                WHERE mob BETWEEN 0 AND 24
                GROUP BY 1, 2
                """
            )
            conn.commit()
            print("汇总表生成完成")


if __name__ == "__main__":
    main()
