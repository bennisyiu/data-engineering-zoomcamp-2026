# Analytics Dashboard

## Tableau Public

**Live Dashboard:** [Insurance Policy, Claims & Invoice Analytics](https://public.tableau.com/shared/65BQGNBFS?:display_count=n&:origin=viz_share_link)

The workbook contains **4 dashboards** presented as a Tableau Story:

| Story Point | Dashboard | What it shows |
|------------|-----------|---------------|
| 1 | **Performance Dashboard** | KPIs, monthly premium vs claims trend, product breakdown, loss ratio, new vs returning, policies issued |
| 2 | **Executive Summary** | Quarterly & annual performance table with YoY % growth |
| 3 | **Claims Analysis** | Billed vs payable, coverage ratio, claim rate & frequency, out-of-pocket, top costliest policies, profitability by product |
| 4 | **Customer & Policy Profile** | Age distribution, premium & loss ratio by age group, revenue per invoice, product x gender heatmap |

## Data Sources

The dashboard reads from the `marts` schema (exported as CSVs for Tableau Public):

| CSV | Source table |
|-----|-------------|
| `mart_dashboard_monthly` | Monthly premium, claims, loss ratio |
| `mart_dashboard_by_product` | Monthly metrics by product with YoY |
| `mart_dashboard_rollups` | D/W/M/Q/Y aggregations with YoY |
| `mart_new_vs_returning_premium` | New vs returning policy counts and premium |
| `mart_policy_denormalized` | Policy-level detail with invoice + claim aggregates |

dbt models are designed so the dashboard uses pre-computed metrics without heavy calculated fields. Workbook structure and step-by-step build notes are in [`notes/tableau_dashboard.md`](../notes/tableau_dashboard.md).
