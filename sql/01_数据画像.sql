-- 目的：先看清数据规模、时间范围、状态分布和渠道分布。
-- 在 DBeaver 中连接 consumer_finance_analysis 后逐段执行。

USE consumer_finance_analysis;

-- 1. 两张核心表的行数
SELECT 'applications' AS 表名, COUNT(*) AS 行数 FROM `v_申请明细`
UNION ALL
SELECT 'repayments' AS 表名, COUNT(*) AS 行数 FROM `v_还款明细`;

-- 2. 业务日期范围
SELECT
    MIN(decision_date) AS 最早申请日,
    MAX(decision_date) AS 最晚申请日,
    COUNT(DISTINCT DATE_FORMAT(decision_date, '%Y-%m')) AS 覆盖月份数
FROM `v_申请明细`;

-- 3. 审批状态分布
SELECT
    status AS 审批状态,
    COUNT(*) AS 笔数,
    ROUND(COUNT(*) / SUM(COUNT(*)) OVER (), 4) AS 占比
FROM `v_申请明细`
GROUP BY status
ORDER BY 笔数 DESC;

-- 4. 渠道分布
SELECT
    COALESCE(channel_type, '未知渠道') AS 渠道类型,
    COUNT(*) AS 进件量,
    ROUND(COUNT(*) / SUM(COUNT(*)) OVER (), 4) AS 进件占比,
    ROUND(SUM(status IN ('Approved', 'Unused offer')) / COUNT(*), 4) AS 审批通过率
FROM `v_申请明细`
GROUP BY 1
ORDER BY 进件量 DESC;

-- 5. 产品类型分布
SELECT
    COALESCE(product_type, '未知产品') AS 产品类型,
    COUNT(*) AS 进件量,
    ROUND(SUM(status IN ('Approved', 'Unused offer')) / COUNT(*), 4) AS 审批通过率
FROM `v_申请明细`
GROUP BY 1
ORDER BY 进件量 DESC;

-- 6. 随机看 10 行，建立对字段的直觉
SELECT *
FROM `v_申请明细`
ORDER BY RAND()
LIMIT 10;

