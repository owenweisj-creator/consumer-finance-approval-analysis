# 消费金融审批通过率下降专项分析

用 MySQL + Pandas 对消费金融申请审批数据做专项诊断：2026-09 审批通过率从 29.4% 降至 22.9%，本项目的目标是判断下降来自渠道结构变化，还是同一渠道审批变严，并进一步验证风险表现。

项目周期：2026-09-01 启动，2026-10-20 发布 v1.0。

## 业务问题

1. 审批通过率下降是渠道结构变化，还是同一渠道审批变严？
2. 哪些渠道对整体通过率变化贡献最大？
3. 通过率下降是否对应更好的风险表现？

## 数据与口径

- 数据：Home Credit 公开消费金融数据集，使用 `previous_application` 与 `installments_payments` 两张表。
- 时间：`DAYS_*` 为相对当前申请日的负数，项目映射到以 2026-09-30 为锚点的业务日历。
- 金额：统一除以 10,000，单位为万元（归一化）。
- 审批通过率 =（Approved + Unused offer）/ 全部进件。
- 用信率 = Approved /（Approved + Unused offer）。
- DPD30：单期最大逾期天数 ≥ 30，仅用于获批客户的风险验证。

## 分析方法

- 月度趋势与审批漏斗：观察进件、通过、用信和金额变化。
- 渠道归因：把整体通过率变化拆成结构效应与比率效应。
- 风险验证：将渠道审批通过率与获批客户 DPD30 交叉比较，并说明选择偏差。
- 工具链：MySQL 8.0 + DBeaver 取数与聚合，Pandas/NumPy 复算与交叉验证，Matplotlib 画图。

## 关键发现

- 2026-09 进件量 36,012 笔（环比 +26.2%），审批通过率 22.90%（环比 -6.5pp）。
- 结构效应 -5.39pp、比率效应 -1.13pp、总效应 -6.52pp。
- 审批金额 188,681 万元（环比 +32.1%），件均 23.38 万元（+30.5%）；金额增长主要靠件均和期限，不靠件数。
- 低通过率渠道并不必然对应更低 DPD30；风险验证只能覆盖获批客户，存在选择偏差。

## 项目结构

```text
notebooks/        # 6 个分析 Notebook
sql/              # 6 个可在 DBeaver 运行的 SQL
src/              # MySQL 连接、指标函数、图表样式
scripts/          # 数据下载、装载、报告与 Excel 生成
data/             # 本地数据，gitignore
outputs/figures/  # 分析图表
outputs/report/   # 专项报告
outputs/excel/    # Excel 汇总
docs/             # AI 协作记录
```

## 快速开始

### 1. 下载数据

```powershell
.\.venv\Scripts\python.exe scripts/download_data.py
```

数据会下载到 `data/raw/`，并生成 `data/raw/manifest.json`。

### 2. 配置 MySQL

复制 `.env.example` 为 `.env`，填写本地连接信息：

```text
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password_here
MYSQL_DATABASE=consumer_finance_analysis
MYSQL_CHARSET=utf8mb4
```

### 3. 装载数据

```powershell
.\.venv\Scripts\python.exe scripts/load_mysql.py --reload --fast
```

### 4. 执行 Notebook

```powershell
.\.venv\Scripts\python.exe -m jupyter lab
```

按 `01` 到 `06` 的顺序执行，复现趋势、渠道归因和风险验证结果。

### 5. 生成报告与 Excel

```powershell
.\.venv\Scripts\python.exe scripts/build_report.py
.\.venv\Scripts\python.exe scripts/build_excel.py
```

## 局限

- 公开数据、模拟业务日历，结论用于方法展示，不代表真实公司经营。
- 金额为归一化万元，不能解释为真实人民币规模。
- 风险验证只看获批客户，存在选择偏差，不能做因果推断。
- 缺少渠道投放、拒绝原因和审批规则变更等业务事件数据。

## AI 协作记录

开发过程中的 AI 辅助 SQL/Pandas 草稿、排错与验证记录见 [docs/codex_log.md](docs/codex_log.md)。业务口径、分析结论和最终验收由项目负责人负责。

## 项目链接

https://github.com/owenweisj-creator/consumer-finance-approval-analysis
