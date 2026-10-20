-- 目的：把整体通过率变化拆成结构效应和比率效应。

USE consumer_finance_analysis;

-- 1. 渠道贡献明细
SELECT
    `渠道类型`,
    `基期占比`,
    `当期占比`,
    `基期通过率`,
    `当期通过率`,
    `结构效应`,
    `比率效应`,
    `总效应`
FROM `v_渠道归因`
ORDER BY `总效应`;

-- 2. 合计效应（应为 结构 -0.0539、比率 -0.0113、总 -0.0652）
SELECT
    ROUND(SUM(`结构效应`), 4) AS 结构效应合计,
    ROUND(SUM(`比率效应`), 4) AS 比率效应合计,
    ROUND(SUM(`总效应`), 4) AS 总效应合计
FROM `v_渠道归因`;

-- 3. 负向贡献最大的 3 个渠道
SELECT
    `渠道类型`,
    `结构效应`,
    `比率效应`,
    `总效应`
FROM `v_渠道归因`
ORDER BY `总效应`
LIMIT 3;

-- 4. 单个渠道手算示例：Credit and cash offices
WITH cur AS (
    SELECT
        SUM(`进件量`) AS 当期进件,
        SUM(`审批通过量`) AS 当期通过
    FROM `v_渠道月度`
    WHERE `月份` = '2026-09'
),
prev AS (
    SELECT
        SUM(`进件量`) AS 基期进件,
        SUM(`审批通过量`) AS 基期通过
    FROM `v_渠道月度`
    WHERE `月份` = '2026-08'
),
detail AS (
    SELECT '2026-09' AS 月份, `进件量`, `审批通过量`, `审批通过率`
    FROM `v_渠道月度`
    WHERE `月份` = '2026-09' AND `渠道类型` = 'Credit and cash offices'
    UNION ALL
    SELECT '2026-08', `进件量`, `审批通过量`, `审批通过率`
    FROM `v_渠道月度`
    WHERE `月份` = '2026-08' AND `渠道类型` = 'Credit and cash offices'
)
SELECT
    d.*,
    ROUND(d.`进件量` / CASE WHEN d.`月份` = '2026-09' THEN cur.当期进件 ELSE prev.基期进件 END, 4) AS 渠道占比
FROM detail d
CROSS JOIN cur
CROSS JOIN prev
ORDER BY d.`月份`;

