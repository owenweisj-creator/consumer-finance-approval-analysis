-- 目的：生成报告和 Excel 使用的最终结果集。

USE consumer_finance_analysis;

-- 1. 报告核心表：本期 vs 上期
SELECT *
FROM `v_申请审批月度`
ORDER BY `月份` DESC
LIMIT 2;

-- 2. 渠道贡献表
SELECT *
FROM `v_渠道归因`
ORDER BY `总效应`;

-- 3. 渠道风险表
SELECT
    c.`渠道类型`,
    c.`进件量`,
    c.`审批通过率`,
    r.`DPD30率`
FROM (
    SELECT `渠道类型`, `进件量`, `审批通过率`
    FROM `v_渠道月度`
    WHERE `月份` = '2026-09'
) c
LEFT JOIN `v_还款风险` r ON c.`渠道类型` = r.`渠道类型`
ORDER BY c.`进件量` DESC;

-- 4. 结论摘要（手工填写前先核对数字）
SELECT
    (SELECT `审批通过率` FROM `v_申请审批月度` WHERE `月份` = '2026-08') AS 上期通过率,
    (SELECT `审批通过率` FROM `v_申请审批月度` WHERE `月份` = '2026-09') AS 本期通过率,
    (SELECT ROUND(SUM(`结构效应`), 4) FROM `v_渠道归因`) AS 结构效应,
    (SELECT ROUND(SUM(`比率效应`), 4) FROM `v_渠道归因`) AS 比率效应,
    (SELECT ROUND(SUM(`总效应`), 4) FROM `v_渠道归因`) AS 总效应;

