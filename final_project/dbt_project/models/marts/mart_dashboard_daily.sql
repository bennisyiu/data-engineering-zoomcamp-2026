{{
  config(
    materialized='table'
  )
}}
with daily_premium as (
  select
    inv.charge_date::date as day_date,
    count(distinct inv.policy_number)::int as policies_with_payment,
    round(sum(inv.pre_levy_amount)::numeric, 2) as premium_received
  from {{ ref('int_invoice_paid') }} inv
  join {{ ref('int_policy_ranked') }} rnk on inv.policy_number = rnk.policy_number
  where not rnk.is_outlier_user and inv.charge_date is not null
  group by inv.charge_date::date
),
daily_policies_issued as (
  select
    p.effective_date::date as day_date,
    count(*)::int as policies_issued
  from {{ ref('stg_policy') }} p
  join {{ ref('int_policy_ranked') }} rnk on p.policy_number = rnk.policy_number
  where not rnk.is_outlier_user
  group by p.effective_date::date
),
daily_claims as (
  select
    payment_date::date as day_date,
    count(*)::int as claim_count,
    round(sum(total_base_payable_amount)::numeric, 2) as claims_paid
  from {{ ref('stg_claim') }}
  where status = 'paid' and payment_date is not null
  group by payment_date::date
),
all_dates as (
  select day_date from daily_premium
  union
  select day_date from daily_policies_issued
  union
  select day_date from daily_claims
)
select
  d.day_date,
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
from all_dates d
left join daily_premium pr on d.day_date = pr.day_date
left join daily_policies_issued pi on d.day_date = pi.day_date
left join daily_claims c on d.day_date = c.day_date
order by d.day_date
