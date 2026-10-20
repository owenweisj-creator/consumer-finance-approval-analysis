-- 目的：验证审批通过率下降是否对应更好的风险表现。

USE consumer_finance_analysis;

-- 1. 各渠道审批通过率与 DPD30
SELECT
    c.`渠道类型`,
    c.`进件量`,
    c.`审批通过率`,
    r.`有还款记录合同数`,
    r.`DPD30率`
FROM (
    SELECT
        `渠道类型`,
        `进件量`,
        `审批通过率`
    FROM `v_渠道月度`
    WHERE `月份` = '2026-09'
) c
LEFT JOIN `v_还款风险` r ON c.`渠道类型` = r.`渠道类型`
ORDER BY c.`进件量` DESC;

-- 2. 审批通过率最低的渠道，风险是否最低？
SELECT
    c.`渠道类型`,
    c.`审批通过率`,
    r.`DPD30率`
FROM (
    SELECT `渠道类型`, `审批通过率`
    FROM `v_渠道月度`
    WHERE `月份` = '2026-09'
) c
LEFT JOIN `v_还款风险` r ON c.`渠道类型` = r.`渠道类型`
ORDER BY c.`审批通过率`
LIMIT 5;

-- 3. Vintage 累计 DPD30
SELECT
    `放款cohort`,
    `账龄月`,
    `贷款数`,
    `累计DPD30率`
FROM `v_账龄迁徙`
WHERE `账龄月` IN (0, 3, 6, 12)
ORDER BY `放款cohort`, `账龄月`;

-- 4. 风险验证的边界
-- 这里只能说明“获批客户”的风险表现，
-- 不能说明被拒绝客户如果放款会表现如何；
-- 存在选择偏差，不能把审批通过率与 DPD30 直接做因果解释。

