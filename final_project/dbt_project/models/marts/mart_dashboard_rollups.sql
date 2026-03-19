{{
  config(
    materialized='table'
  )
}}
with daily as (
  select * from {{ ref('mart_dashboard_daily') }}
),
agg_d as (
  select
    'D' as time_grain,
    day_date as period_start,
    premium_received,
    policies_issued,
    claims_paid,
    claim_count,
    loss_ratio,
    avg_premium_per_policy,
    avg_claim_amount
  from daily
),
agg_w as (
  select
    'W' as time_grain,
    (date_trunc('week', day_date))::date as period_start,
    round(sum(premium_received)::numeric, 2) as premium_received,
    sum(policies_issued)::int as policies_issued,
    round(sum(claims_paid)::numeric, 2) as claims_paid,
    sum(claim_count)::int as claim_count,
    case when sum(premium_received) > 0 then round((sum(claims_paid) / sum(premium_received))::numeric, 4) else null end as loss_ratio,
    case when sum(policies_issued) > 0 then round((sum(premium_received) / sum(policies_issued))::numeric, 2) else null end as avg_premium_per_policy,
    case when sum(claim_count) > 0 then round((sum(claims_paid) / sum(claim_count))::numeric, 2) else null end as avg_claim_amount
  from daily
  group by date_trunc('week', day_date)
),
agg_m as (
  select
    'M' as time_grain,
    (date_trunc('month', day_date))::date as period_start,
    round(sum(premium_received)::numeric, 2) as premium_received,
    sum(policies_issued)::int as policies_issued,
    round(sum(claims_paid)::numeric, 2) as claims_paid,
    sum(claim_count)::int as claim_count,
    case when sum(premium_received) > 0 then round((sum(claims_paid) / sum(premium_received))::numeric, 4) else null end as loss_ratio,
    case when sum(policies_issued) > 0 then round((sum(premium_received) / sum(policies_issued))::numeric, 2) else null end as avg_premium_per_policy,
    case when sum(claim_count) > 0 then round((sum(claims_paid) / sum(claim_count))::numeric, 2) else null end as avg_claim_amount
  from daily
  group by date_trunc('month', day_date)
),
agg_q as (
  select
    'Q' as time_grain,
    (date_trunc('quarter', day_date))::date as period_start,
    round(sum(premium_received)::numeric, 2) as premium_received,
    sum(policies_issued)::int as policies_issued,
    round(sum(claims_paid)::numeric, 2) as claims_paid,
    sum(claim_count)::int as claim_count,
    case when sum(premium_received) > 0 then round((sum(claims_paid) / sum(premium_received))::numeric, 4) else null end as loss_ratio,
    case when sum(policies_issued) > 0 then round((sum(premium_received) / sum(policies_issued))::numeric, 2) else null end as avg_premium_per_policy,
    case when sum(claim_count) > 0 then round((sum(claims_paid) / sum(claim_count))::numeric, 2) else null end as avg_claim_amount
  from daily
  group by date_trunc('quarter', day_date)
),
agg_y as (
  select
    'Y' as time_grain,
    (date_trunc('year', day_date))::date as period_start,
    round(sum(premium_received)::numeric, 2) as premium_received,
    sum(policies_issued)::int as policies_issued,
    round(sum(claims_paid)::numeric, 2) as claims_paid,
    sum(claim_count)::int as claim_count,
    case when sum(premium_received) > 0 then round((sum(claims_paid) / sum(premium_received))::numeric, 4) else null end as loss_ratio,
    case when sum(policies_issued) > 0 then round((sum(premium_received) / sum(policies_issued))::numeric, 2) else null end as avg_premium_per_policy,
    case when sum(claim_count) > 0 then round((sum(claims_paid) / sum(claim_count))::numeric, 2) else null end as avg_claim_amount
  from daily
  group by date_trunc('year', day_date)
),
base as (
  select * from agg_d
  union all select * from agg_w
  union all select * from agg_m
  union all select * from agg_q
  union all select * from agg_y
),
prior_year as (
  select
    time_grain,
    (period_start + interval '1 year')::date as period_current,
    period_start as period_start_ly,
    premium_received as premium_received_ly,
    policies_issued as policies_issued_ly,
    claims_paid as claims_paid_ly,
    claim_count as claim_count_ly,
    loss_ratio as loss_ratio_ly,
    avg_premium_per_policy as avg_premium_per_policy_ly,
    avg_claim_amount as avg_claim_amount_ly
  from base
  where time_grain in ('M', 'Q', 'Y')
)
select
  b.time_grain,
  b.period_start,
  b.premium_received,
  b.policies_issued,
  b.claims_paid,
  b.claim_count,
  b.loss_ratio,
  b.avg_premium_per_policy,
  b.avg_claim_amount,
  py.period_start_ly,
  py.premium_received_ly,
  py.policies_issued_ly,
  py.claims_paid_ly,
  py.claim_count_ly,
  py.loss_ratio_ly,
  py.avg_premium_per_policy_ly,
  py.avg_claim_amount_ly
from base b
left join prior_year py on b.time_grain = py.time_grain and b.period_start = py.period_current
order by b.time_grain, b.period_start
