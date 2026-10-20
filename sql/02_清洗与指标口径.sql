-- 目的：确认清洗规则，并把核心指标口径固化成可复用的查询。

USE consumer_finance_analysis;

-- 1. 关键字段缺失率
SELECT
    ROUND(SUM(status IS NULL OR status = '') / COUNT(*), 4) AS 状态缺失率,
    ROUND(SUM(channel_type IS NULL OR channel_type = '') / COUNT(*), 4) AS 渠道缺失率,
    ROUND(SUM(approved_amount IS NULL) / COUNT(*), 4) AS 审批金额缺失率,
    ROUND(SUM(decision_date IS NULL) / COUNT(*), 4) AS 日期缺失率
FROM `v_申请明细`;

-- 2. 主键重复检查（应为 0）
SELECT COUNT(*) - COUNT(DISTINCT previous_id) AS 申请主键重复数
FROM `v_申请明细`;

-- 3. 还款表关键字段缺失率
SELECT
    ROUND(SUM(due_date IS NULL) / COUNT(*), 4) AS 应还日期缺失率,
    ROUND(SUM(amount_due IS NULL) / COUNT(*), 4) AS 应还金额缺失率,
    ROUND(SUM(late_days IS NULL) / COUNT(*), 4) AS 逾期天数缺失率
FROM `v_还款明细`;

-- 4. 2026-09 核心指标（本期）
SELECT
    `月份`,
    `进件量`,
    `审批通过量`,
    `实际用信量`,
    `审批通过率`,
    `用信率`,
    `审批金额`,
    `件均`
FROM `v_申请审批月度`
WHERE `月份` = '2026-09';

-- 5. 最近两个月对比
SELECT *
FROM `v_申请审批月度`
ORDER BY `月份` DESC
LIMIT 2;

-- 6. 指标口径速查（注释版）
-- 进件量 = 全部申请笔数
-- 审批通过率 =（Approved + Unused offer）/ 进件量
-- 用信率 = Approved /（Approved + Unused offer）
-- 审批金额 = Approved 合同的 approved_amount 合计（万元）
-- 件均 = 审批金额 / Approved 笔数

