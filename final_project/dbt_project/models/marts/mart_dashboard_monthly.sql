{{
  config(
    materialized='table'
  )
}}
with monthly_premium as (
  select
    date_trunc('month', inv.charge_date)::date as month_start,
    count(distinct inv.policy_number)::int as policies_with_payment,
    round(sum(inv.pre_levy_amount)::numeric, 2) as premium_received
  from {{ ref('int_invoice_paid') }} inv
  join {{ ref('int_policy_ranked') }} rnk on inv.policy_number = rnk.policy_number
  where not rnk.is_outlier_user
  group by date_trunc('month', inv.charge_date)
),
monthly_policies_issued as (
  select
    date_trunc('month', p.effective_date)::date as month_start,
    count(*)::int as policies_issued
  from {{ ref('stg_policy') }} p
  join {{ ref('int_policy_ranked') }} rnk on p.policy_number = rnk.policy_number
  where not rnk.is_outlier_user
  group by date_trunc('month', p.effective_date)
),
monthly_claims as (
  select
    date_trunc('month', payment_date)::date as month_start,
    count(*)::int as claim_count,
    round(sum(total_base_payable_amount)::numeric, 2) as claims_paid
  from {{ ref('stg_claim') }}
  where status = 'paid' and payment_date is not null
  group by date_trunc('month', payment_date)
),
months as (
  select distinct month_start from monthly_premium
  union
  select distinct month_start from monthly_policies_issued
  union
  select distinct month_start from monthly_claims
)
select
  m.month_start,
  coalesce(pr.premium_received, 0) as premium_received,
  coalesce(pi.policies_issued, 0) as policies_issued,
  coalesce(c.claims_paid, 0) as claims_paid,
  coalesce(c.claim_count, 0)::int as claim_count,
  case
    when coalesce(pr.premium_received, 0) > 0
    then round((coalesce(c.claims_paid, 0) / pr.premium_received)::numeric, 4)
    else null
  end as loss_ratio,
  case
    when coalesce(pr.policies_with_payment, 0) > 0 and coalesce(pr.premium_received, 0) > 0
    then round((pr.premium_received / pr.policies_with_payment)::numeric, 2)
    else null
  end as avg_premium_per_policy,
  case
    when coalesce(c.claim_count, 0) > 0 and coalesce(c.claims_paid, 0) > 0
    then round((c.claims_paid / c.claim_count)::numeric, 2)
    else null
  end as avg_claim_amount
from months m
left join monthly_premium pr on m.month_start = pr.month_start
left join monthly_policies_issued pi on m.month_start = pi.month_start
left join monthly_claims c on m.month_start = c.month_start
order by m.month_start
