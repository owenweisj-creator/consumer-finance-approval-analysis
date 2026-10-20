from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import pymysql

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db import DB_CONFIG, connection, query_df

ANCHOR = "2026-09-30"
DEFAULT_SOURCE = Path(__file__).resolve().parents[1] / "data" / "raw"


def q(name: str) -> str:
    return f"`{name}`"


def create_staging(cursor, table: str, columns: list[str]) -> None:
    cursor.execute(f"DROP TABLE IF EXISTS {q(table)}")
    body = ", ".join(f"{q(column)} TEXT" for column in columns)
    cursor.execute(f"CREATE TABLE {q(table)} ({body}) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4")


def load_csv(cursor, table: str, path: Path) -> None:
    sql = (
        f"LOAD DATA LOCAL INFILE '{path.as_posix()}' INTO TABLE {q(table)} "
        "CHARACTER SET utf8mb4 "
        "FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '\"' "
        "LINES TERMINATED BY '\\n' IGNORE 1 LINES"
    )
    cursor.execute(sql)


def main() -> None:
    parser = argparse.ArgumentParser(description="把 Home Credit 两张源表装入 MySQL。")
    parser.add_argument("--source-dir", default=str(DEFAULT_SOURCE))
    parser.add_argument("--reload", action="store_true", help="删除并重建 staging 与结果表。")
    parser.add_argument("--reuse-staging", action="store_true", help="复用已装载的 staging 表，不重新 LOAD DATA。")
    parser.add_argument("--fast", action="store_true", help="用 CTAS 建结果表，再补索引，速度更快。")
    args = parser.parse_args()
    source = Path(args.source_dir)
    previous_csv = source / "previous_application.csv"
    installments_csv = source / "installments_payments.csv"
    if not previous_csv.exists() or not installments_csv.exists():
        raise FileNotFoundError(f"源文件不存在：{previous_csv} 或 {installments_csv}")

    admin = pymysql.connect(**DB_CONFIG, autocommit=True)
    with admin.cursor() as cursor:
        cursor.execute("SET GLOBAL local_infile=1")
        cursor.execute("SHOW VARIABLES LIKE 'local_infile'")
        print("local_infile:", cursor.fetchone())
    admin.close()

    previous_columns = pd.read_csv(previous_csv, nrows=0).columns.tolist()
    installments_columns = pd.read_csv(installments_csv, nrows=0).columns.tolist()

    with connection(local_infile=True) as conn:
        with conn.cursor() as cursor:
            if args.reload:
                for table in ["applications", "repayments"]:
                    cursor.execute(f"DROP TABLE IF EXISTS {q(table)}")
            if not args.reuse_staging:
                create_staging(cursor, "stg_previous_application", previous_columns)
                create_staging(cursor, "stg_installments_payments", installments_columns)
                conn.commit()

                print("装载 previous_application.csv ...")
                load_csv(cursor, "stg_previous_application", previous_csv)
                conn.commit()
                print("装载 installments_payments.csv ...")
                load_csv(cursor, "stg_installments_payments", installments_csv)
                conn.commit()
            else:
                cursor.execute("SELECT COUNT(*) AS n FROM stg_previous_application")
                print("复用 staging previous_application:", cursor.fetchone())
                cursor.execute("SELECT COUNT(*) AS n FROM stg_installments_payments")
                print("复用 staging installments_payments:", cursor.fetchone())

            if args.fast:
                _fast_build(cursor)
                conn.commit()
                _create_views(cursor)
                conn.commit()
                _verify(cursor)
                return

            cursor.execute(
                f"""
                CREATE TABLE IF NOT EXISTS applications (
                    previous_id BIGINT PRIMARY KEY,
                    customer_id BIGINT NOT NULL,
                    contract_type VARCHAR(50),
                    status VARCHAR(50),
                    applied_amount DECIMAL(18,2),
                    approved_amount DECIMAL(18,2),
                    annuity DECIMAL(18,2),
                    goods_price DECIMAL(18,2),
                    term_months INT,
                    channel_type VARCHAR(100),
                    product_type VARCHAR(50),
                    portfolio VARCHAR(50),
                    goods_category VARCHAR(100),
                    loan_purpose VARCHAR(100),
                    yield_group VARCHAR(20),
                    days_decision INT,
                    decision_date DATE,
                    KEY idx_decision_date (decision_date),
                    KEY idx_channel (channel_type),
                    KEY idx_status (status)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                COMMENT='历史申请与审批明细（金额万元，日期为模拟业务日历）'
                """
            )
            cursor.execute("TRUNCATE TABLE applications")
            cursor.execute(
                f"""
                INSERT INTO applications
                SELECT
                    CAST(SK_ID_PREV AS UNSIGNED),
                    CAST(SK_ID_CURR AS UNSIGNED),
                    NULLIF(TRIM(NAME_CONTRACT_TYPE), ''),
                    NULLIF(TRIM(NAME_CONTRACT_STATUS), ''),
                    CAST(NULLIF(TRIM(AMT_APPLICATION), '') AS DECIMAL(18,2)) / 10000,
                    CAST(NULLIF(TRIM(AMT_CREDIT), '') AS DECIMAL(18,2)) / 10000,
                    CAST(NULLIF(TRIM(AMT_ANNUITY), '') AS DECIMAL(18,2)) / 10000,
                    CAST(NULLIF(TRIM(AMT_GOODS_PRICE), '') AS DECIMAL(18,2)) / 10000,
                    CAST(CAST(NULLIF(TRIM(CNT_PAYMENT), '') AS DECIMAL(10,2)) AS SIGNED),
                    NULLIF(TRIM(CHANNEL_TYPE), ''),
                    NULLIF(TRIM(NAME_PRODUCT_TYPE), ''),
                    NULLIF(TRIM(NAME_PORTFOLIO), ''),
                    NULLIF(TRIM(NAME_GOODS_CATEGORY), ''),
                    NULLIF(TRIM(NAME_CASH_LOAN_PURPOSE), ''),
                    NULLIF(TRIM(NAME_YIELD_GROUP), ''),
                    CAST(NULLIF(TRIM(DAYS_DECISION), '') AS SIGNED),
                    DATE_ADD('{ANCHOR}', INTERVAL CAST(NULLIF(TRIM(DAYS_DECISION), '') AS SIGNED) DAY)
                FROM stg_previous_application
                """
            )
            conn.commit()

            cursor.execute(
                f"""
                CREATE TABLE IF NOT EXISTS repayments (
                    previous_id BIGINT NOT NULL,
                    customer_id BIGINT NOT NULL,
                    installment_number INT,
                    due_date DATE,
                    paid_date DATE NULL,
                    amount_due DECIMAL(18,2),
                    amount_paid DECIMAL(18,2),
                    late_days INT NULL,
                    dpd30_flag TINYINT NOT NULL DEFAULT 0,
                    KEY idx_previous (previous_id),
                    KEY idx_customer (customer_id),
                    KEY idx_due_date (due_date)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                COMMENT='分期还款明细（金额万元，日期为模拟业务日历）'
                """
            )
            cursor.execute("TRUNCATE TABLE repayments")
            cursor.execute(
                f"""
                INSERT INTO repayments
                SELECT
                    previous_id, customer_id, installment_number, due_date, paid_date,
                    amount_due, amount_paid, late_days,
                    CASE WHEN late_days >= 30 THEN 1 ELSE 0 END
                FROM (
                    SELECT
                        CAST(SK_ID_PREV AS UNSIGNED) AS previous_id,
                        CAST(SK_ID_CURR AS UNSIGNED) AS customer_id,
                        CAST(NULLIF(TRIM(NUM_INSTALMENT_NUMBER), '') AS SIGNED) AS installment_number,
                        DATE_ADD('{ANCHOR}', INTERVAL CAST(NULLIF(TRIM(DAYS_INSTALMENT), '') AS SIGNED) DAY) AS due_date,
                        CASE
                            WHEN NULLIF(TRIM(DAYS_ENTRY_PAYMENT), '') IS NULL THEN NULL
                            ELSE DATE_ADD('{ANCHOR}', INTERVAL CAST(NULLIF(TRIM(DAYS_ENTRY_PAYMENT), '') AS SIGNED) DAY)
                        END AS paid_date,
                        CAST(NULLIF(TRIM(AMT_INSTALMENT), '') AS DECIMAL(18,2)) / 10000 AS amount_due,
                        CAST(NULLIF(TRIM(AMT_PAYMENT), '') AS DECIMAL(18,2)) / 10000 AS amount_paid,
                        CASE
                            WHEN NULLIF(TRIM(DAYS_ENTRY_PAYMENT), '') IS NULL
                                 AND CAST(NULLIF(TRIM(DAYS_INSTALMENT), '') AS SIGNED) < 0
                                THEN -CAST(NULLIF(TRIM(DAYS_INSTALMENT), '') AS SIGNED)
                            WHEN NULLIF(TRIM(DAYS_ENTRY_PAYMENT), '') IS NULL THEN NULL
                            ELSE CAST(NULLIF(TRIM(DAYS_ENTRY_PAYMENT), '') AS SIGNED)
                                 - CAST(NULLIF(TRIM(DAYS_INSTALMENT), '') AS SIGNED)
                        END AS late_days
                    FROM stg_installments_payments
                ) AS base
                """
            )
            conn.commit()
            _create_views(cursor)
            conn.commit()
            _verify(cursor)


def _fast_build(cursor) -> None:
    """先 CTAS 建表，再补索引；比带索引逐行 INSERT 快很多。"""
    cursor.execute("SET SESSION unique_checks=0")
    cursor.execute("SET SESSION foreign_key_checks=0")
    try:
        cursor.execute("SET SESSION sql_log_bin=0")
    except Exception:
        pass

    cursor.execute("DROP TABLE IF EXISTS applications")
    cursor.execute(
        f"""
        CREATE TABLE applications AS
        SELECT
            CAST(SK_ID_PREV AS UNSIGNED) AS previous_id,
            CAST(SK_ID_CURR AS UNSIGNED) AS customer_id,
            NULLIF(TRIM(NAME_CONTRACT_TYPE), '') AS contract_type,
            NULLIF(TRIM(NAME_CONTRACT_STATUS), '') AS status,
            CAST(NULLIF(TRIM(AMT_APPLICATION), '') AS DECIMAL(18,2)) / 10000 AS applied_amount,
            CAST(NULLIF(TRIM(AMT_CREDIT), '') AS DECIMAL(18,2)) / 10000 AS approved_amount,
            CAST(NULLIF(TRIM(AMT_ANNUITY), '') AS DECIMAL(18,2)) / 10000 AS annuity,
            CAST(NULLIF(TRIM(AMT_GOODS_PRICE), '') AS DECIMAL(18,2)) / 10000 AS goods_price,
            CAST(CAST(NULLIF(TRIM(CNT_PAYMENT), '') AS DECIMAL(10,2)) AS SIGNED) AS term_months,
            NULLIF(TRIM(CHANNEL_TYPE), '') AS channel_type,
            NULLIF(TRIM(NAME_PRODUCT_TYPE), '') AS product_type,
            NULLIF(TRIM(NAME_PORTFOLIO), '') AS portfolio,
            NULLIF(TRIM(NAME_GOODS_CATEGORY), '') AS goods_category,
            NULLIF(TRIM(NAME_CASH_LOAN_PURPOSE), '') AS loan_purpose,
            NULLIF(TRIM(NAME_YIELD_GROUP), '') AS yield_group,
            CAST(CAST(NULLIF(TRIM(DAYS_DECISION), '') AS DECIMAL(20,4)) AS SIGNED) AS days_decision,
            DATE_ADD('{ANCHOR}', INTERVAL CAST(CAST(NULLIF(TRIM(DAYS_DECISION), '') AS DECIMAL(20,4)) AS SIGNED) DAY) AS decision_date
        FROM stg_previous_application
        """
    )
    cursor.execute("ALTER TABLE applications ADD PRIMARY KEY (previous_id)")
    cursor.execute("ALTER TABLE applications ADD INDEX idx_decision_date (decision_date)")
    cursor.execute("ALTER TABLE applications ADD INDEX idx_channel (channel_type(100))")
    cursor.execute("ALTER TABLE applications ADD INDEX idx_status (status(50))")
    cursor.execute(
        "ALTER TABLE applications COMMENT='历史申请与审批明细（金额万元，日期为模拟业务日历）'"
    )

    cursor.execute("DROP TABLE IF EXISTS repayments")
    cursor.execute(
        f"""
        CREATE TABLE repayments AS
        SELECT
            previous_id, customer_id, installment_number, due_date, paid_date,
            amount_due, amount_paid, late_days,
            CASE WHEN late_days >= 30 THEN 1 ELSE 0 END AS dpd30_flag
        FROM (
            SELECT
                CAST(SK_ID_PREV AS UNSIGNED) AS previous_id,
                CAST(SK_ID_CURR AS UNSIGNED) AS customer_id,
                CAST(CAST(NULLIF(TRIM(NUM_INSTALMENT_NUMBER), '') AS DECIMAL(20,4)) AS SIGNED) AS installment_number,
                DATE_ADD('{ANCHOR}', INTERVAL CAST(CAST(NULLIF(TRIM(DAYS_INSTALMENT), '') AS DECIMAL(20,4)) AS SIGNED) DAY) AS due_date,
                CASE
                    WHEN NULLIF(TRIM(DAYS_ENTRY_PAYMENT), '') IS NULL THEN NULL
                    ELSE DATE_ADD('{ANCHOR}', INTERVAL CAST(CAST(NULLIF(TRIM(DAYS_ENTRY_PAYMENT), '') AS DECIMAL(20,4)) AS SIGNED) DAY)
                END AS paid_date,
                CAST(NULLIF(TRIM(AMT_INSTALMENT), '') AS DECIMAL(18,2)) / 10000 AS amount_due,
                CAST(NULLIF(TRIM(AMT_PAYMENT), '') AS DECIMAL(18,2)) / 10000 AS amount_paid,
                CASE
                    WHEN NULLIF(TRIM(DAYS_ENTRY_PAYMENT), '') IS NULL
                         AND CAST(CAST(NULLIF(TRIM(DAYS_INSTALMENT), '') AS DECIMAL(20,4)) AS SIGNED) < 0
                        THEN -CAST(CAST(NULLIF(TRIM(DAYS_INSTALMENT), '') AS DECIMAL(20,4)) AS SIGNED)
                    WHEN NULLIF(TRIM(DAYS_ENTRY_PAYMENT), '') IS NULL THEN NULL
                    ELSE CAST(CAST(NULLIF(TRIM(DAYS_ENTRY_PAYMENT), '') AS DECIMAL(20,4)) AS SIGNED)
                         - CAST(CAST(NULLIF(TRIM(DAYS_INSTALMENT), '') AS DECIMAL(20,4)) AS SIGNED)
                END AS late_days
            FROM stg_installments_payments
        ) AS base
        """
    )
    cursor.execute("ALTER TABLE repayments ADD INDEX idx_previous (previous_id)")
    cursor.execute("ALTER TABLE repayments ADD INDEX idx_customer (customer_id)")
    cursor.execute("ALTER TABLE repayments ADD INDEX idx_due_date (due_date)")
    cursor.execute(
        "ALTER TABLE repayments COMMENT='分期还款明细（金额万元，日期为模拟业务日历）'"
    )


def _create_views(cursor) -> None:
    cursor.execute("CREATE OR REPLACE VIEW `v_申请明细` AS SELECT * FROM applications")
    cursor.execute("CREATE OR REPLACE VIEW `v_还款明细` AS SELECT * FROM repayments")
    cursor.execute(
        """
        CREATE OR REPLACE VIEW `v_申请审批月度` AS
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
        FROM applications
        GROUP BY 1
        """
    )
    cursor.execute(
        """
        CREATE OR REPLACE VIEW `v_渠道月度` AS
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
        FROM applications
        GROUP BY 1, 2
        """
    )
    cursor.execute(
        """
        CREATE OR REPLACE VIEW `v_渠道归因` AS
        WITH bounds AS (
            SELECT MAX(`月份`) AS `当期`, (
                SELECT MAX(`月份`) FROM `v_申请审批月度`
                WHERE `月份` < (SELECT MAX(`月份`) FROM `v_申请审批月度`)
            ) AS `基期`
            FROM `v_申请审批月度`
        ),
        cur AS (
            SELECT `渠道类型`, `进件量`, `审批通过量`, `审批通过率`
            FROM `v_渠道月度`, bounds WHERE `月份` = bounds.`当期`
        ),
        prev AS (
            SELECT `渠道类型`, `进件量`, `审批通过量`, `审批通过率`
            FROM `v_渠道月度`, bounds WHERE `月份` = bounds.`基期`
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
    cursor.execute(
        """
        CREATE OR REPLACE VIEW `v_还款风险` AS
        WITH loan_risk AS (
            SELECT previous_id, MAX(dpd30_flag) AS dpd30
            FROM repayments
            GROUP BY previous_id
        )
        SELECT
            COALESCE(a.channel_type, '未知渠道') AS `渠道类型`,
            COUNT(*) AS `有还款记录合同数`,
            SUM(r.dpd30) AS `DPD30合同数`,
            ROUND(AVG(r.dpd30), 4) AS `DPD30率`
        FROM applications a
        JOIN loan_risk r ON a.previous_id = r.previous_id
        WHERE a.status = 'Approved'
        GROUP BY 1
        """
    )
    cursor.execute(
        """
        CREATE OR REPLACE VIEW `v_账龄迁徙` AS
        WITH first_due AS (
            SELECT previous_id, MIN(due_date) AS first_due_date,
                   DATE_FORMAT(MIN(due_date), '%Y-%m-01') AS cohort_month
            FROM repayments
            GROUP BY previous_id
        ),
        loan_mob AS (
            SELECT r.previous_id, f.cohort_month,
                   TIMESTAMPDIFF(MONTH, f.cohort_month, DATE_FORMAT(r.due_date, '%Y-%m-01')) AS mob,
                   MAX(r.dpd30_flag) AS dpd30
            FROM repayments r
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


def _verify(cursor) -> None:
    cursor.execute("SELECT COUNT(*) AS n FROM applications")
    applications = cursor.fetchone()["n"]
    cursor.execute("SELECT COUNT(*) AS n FROM repayments")
    repayments = cursor.fetchone()["n"]
    cursor.execute(
        """
        SELECT `月份`, `进件量`, `审批通过率`, `用信率`, `审批金额`
        FROM `v_申请审批月度` ORDER BY `月份` DESC LIMIT 1
        """
    )
    latest = cursor.fetchone()
    cursor.execute(
        """
        SELECT ROUND(SUM(`结构效应`), 4) AS mix,
               ROUND(SUM(`比率效应`), 4) AS rate,
               ROUND(SUM(`总效应`), 4) AS total
        FROM `v_渠道归因`
        """
    )
    effects = cursor.fetchone()
    print(
        json.dumps(
            {
                "applications": applications,
                "repayments": repayments,
                "latest_month": latest,
                "decomposition": effects,
            },
            ensure_ascii=False,
            default=str,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
