# Tableau Dashboard Summary (Personal Reference)

> Gitignored — reference for the dashboard build.

---

## 1. Workbook structure

**One workbook**, 3–4 sheets:

| Sheet                           | Purpose                                                                                              | Primary data source                                            |
| ------------------------------- | ---------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| **Summary table**               | grid style: metrics as rows, columns = Last 7 days, Last 30 days, WTD, MTD, vs same period last year | `marts.mart_dashboard_rollups`                                 |
| **Summary trends**              | Line charts for spikes/plummets: premium, policies, claims, loss ratio over time                     | `marts.mart_dashboard_daily` or `marts.mart_dashboard_rollups` |
| **By product table**            | Premium, policies, claims, loss by product; optional vs last year                                    | `marts.mart_dashboard_by_product`                              |
| **By product chart** (optional) | Bar or line by product (e.g. premium by product, trend by product)                                   | `marts.mart_dashboard_by_product`                              |

---

## 2. Metrics (all pre-built in dbt)

| #   | Metric                 | Definition                                                                    | In marts as              |
| --- | ---------------------- | ----------------------------------------------------------------------------- | ------------------------ |
| 1   | Premium received       | Sum of `pre_levy_amount` from paid invoices (excl. outlier user)              | `premium_received`       |
| 2   | Policies issued        | Count of policies by `effective_date` (excl. outlier user)                    | `policies_issued`        |
| 3   | Claims paid            | Sum of `total_base_payable_amount` where claim status = paid                  | `claims_paid`            |
| 4   | Claim count            | Number of claims paid in the period                                           | `claim_count`            |
| 5   | Loss ratio             | `claims_paid / premium_received`                                              | `loss_ratio`             |
| 6   | Avg premium per policy | `premium_received / policies_with_payment` (or per policies_issued at rollup) | `avg_premium_per_policy` |
| 7   | Avg claim amount       | `claims_paid / claim_count`                                                   | `avg_claim_amount`       |

---

## 3. Marts to use in Tableau

| Mart                          | Schema | Purpose                                                                                                                                                                      |
| ----------------------------- | ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **mart_dashboard_daily**      | marts  | One row per day. Use for: Last 7 days, Last 30 days, trend line charts.                                                                                                      |
| **mart_dashboard_rollups**    | marts  | One row per (time_grain, period_start). `time_grain`: D, W, M, Q, Y. Use for: WTD, MTD, quarterly; filter by grain. Same-period-last-year columns (`*_ly`) only for M, Q, Y. |
| **mart_dashboard_monthly**    | marts  | One row per month. Alternative to rollups when you only need monthly.                                                                                                        |
| **mart_dashboard_by_product** | marts  | One row per (month, product). Use for: product breakdown table/charts; `*_ly` = same month last year.                                                                        |

---

## 4. Time grains and “vs last year”

Current period: D, W, M, Q from rollups (or daily). Same period last year: `*_ly` only for M, Q, Y in rollups and in by_product — no daily or weekly last year in the marts.

---

## 5. Chart types

Line charts for premium, policies, claims, loss ratio (X = period_start or day_date). Loss ratio on secondary axis or its own line. By product: bar for a selected month or line over time for 1–2 products. A reference line at average or a threshold (e.g. loss ratio > 0.8) is used to spot anomalies.

---

## 6. Connection

PostgreSQL, database `insurance_dwh`, schema `marts`. Tables: mart_dashboard_daily, mart_dashboard_rollups, mart_dashboard_monthly, mart_dashboard_by_product. Server is localhost for local development or the EC2 host when deployed. The rollups and _ly columns provide period-over-period metrics so that complex calculated fields are not required.
