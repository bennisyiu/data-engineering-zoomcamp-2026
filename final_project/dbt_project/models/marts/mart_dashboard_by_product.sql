{{
  config(
    materialized='table'
  )
}}
with monthly_premium_by_product as (
  select
    (date_trunc('month', inv.charge_date))::date as month_start,
    rnk.product,
    count(distinct inv.policy_number)::int as policies_with_payment,
    round(sum(inv.pre_levy_amount)::numeric, 2) as premium_received
  from {{ ref('int_invoice_paid') }} inv
  join {{ ref('int_policy_ranked') }} rnk on inv.policy_number = rnk.policy_number
  where not rnk.is_outlier_user and inv.charge_date is not null
  group by date_trunc('month', inv.charge_date), rnk.product
),
monthly_policies_by_product as (
  select
    (date_trunc('month', p.effective_date))::date as month_start,
    p.product,
    count(*)::int as policies_issued
  from {{ ref('stg_policy') }} p
  join {{ ref('int_policy_ranked') }} rnk on p.policy_number = rnk.policy_number
  where not rnk.is_outlier_user
  group by date_trunc('month', p.effective_date), p.product
),
monthly_claims_by_product as (
  select
    (date_trunc('month', c.payment_date))::date as month_start,
    rnk.product,
    count(*)::int as claim_count,
    round(sum(c.total_base_payable_amount)::numeric, 2) as claims_paid
  from {{ ref('stg_claim') }} c
  join {{ ref('int_policy_ranked') }} rnk on c.policy_number = rnk.policy_number
  where c.status = 'paid' and c.payment_date is not null
  group by date_trunc('month', c.payment_date), rnk.product
),
all_period_product as (
  select month_start, product from monthly_premium_by_product
  union
  select month_start, product from monthly_policies_by_product
  union
  select month_start, product from monthly_claims_by_product
),
current_metrics as (
  select
    a.month_start,
    a.product,
    coalesce(pr.premium_received, 0) as premium_received,
    coalesce(pi.policies_issued, 0) as policies_issued,
    coalesce(c.claims_paid, 0) as claims_paid,
    coalesce(c.claim_count, 0)::int as claim_count,
    case when coalesce(pr.premium_received, 0) > 0 then round((coalesce(c.claims_paid, 0) / pr.premium_received)::numeric, 4) else null end as loss_ratio,
    case when coalesce(pr.policies_with_payment, 0) > 0 and coalesce(pr.premium_received, 0) > 0 then round((pr.premium_received / pr.policies_with_payment)::numeric, 2) else null end as avg_premium_per_policy,
    case when coalesce(c.claim_count, 0) > 0 and coalesce(c.claims_paid, 0) > 0 then round((c.claims_paid / c.claim_count)::numeric, 2) else null end as avg_claim_amount
  from all_period_product a
  left join monthly_premium_by_product pr on a.month_start = pr.month_start and a.product = pr.product
  left join monthly_policies_by_product pi on a.month_start = pi.month_start and a.product = pi.product
  left join monthly_claims_by_product c on a.month_start = c.month_start and a.product = c.product
),
with_ly as (
  select
    cur.month_start,
    cur.product,
    cur.premium_received,
    cur.policies_issued,
    cur.claims_paid,
    cur.claim_count,
    cur.loss_ratio,
    cur.avg_premium_per_policy,
    cur.avg_claim_amount,
    (cur.month_start - interval '1 year')::date as month_start_ly,
    ly.premium_received as premium_received_ly,
    ly.policies_issued as policies_issued_ly,
    ly.claims_paid as claims_paid_ly,
    ly.claim_count as claim_count_ly,
    ly.loss_ratio as loss_ratio_ly,
    ly.avg_premium_per_policy as avg_premium_per_policy_ly,
    ly.avg_claim_amount as avg_claim_amount_ly
  from current_metrics cur
  left join current_metrics ly on ly.month_start = (cur.month_start - interval '1 year')::date and ly.product = cur.product
)
select
  month_start,
  product,
  premium_received,
  policies_issued,
  claims_paid,
  claim_count,
  loss_ratio,
  avg_premium_per_policy,
  avg_claim_amount,
  month_start_ly,
  premium_received_ly,
  policies_issued_ly,
  claims_paid_ly,
  claim_count_ly,
  loss_ratio_ly,
  avg_premium_per_policy_ly,
  avg_claim_amount_ly
from with_ly
order by month_start, product
