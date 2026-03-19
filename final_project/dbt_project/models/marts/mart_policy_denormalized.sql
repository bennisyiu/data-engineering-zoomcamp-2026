{{
  config(
    materialized='table'
  )
}}
with policy as (
  select
    policy_number,
    user_id,
    product,
    issue_date,
    effective_date,
    insured_gender,
    insured_date_of_birth,
    is_outlier_user
  from {{ ref('stg_policy') }}
),
invoice_agg as (
  select
    policy_number,
    count(*)::int as invoice_count,
    round(sum(pre_levy_amount)::numeric, 2) as total_pre_levy_amount,
    round(sum(total_amount)::numeric, 2) as total_amount_paid
  from {{ ref('stg_invoice') }}
  where status = 'paid'
  group by policy_number
),
claim_agg as (
  select
    policy_number,
    count(*)::int as claim_count,
    round(sum(total_billed_amount)::numeric, 2) as total_billed_amount,
    round(sum(total_base_payable_amount)::numeric, 2) as total_payable_amount
  from {{ ref('stg_claim') }}
  group by policy_number
)
select
  p.policy_number,
  p.user_id,
  p.product,
  p.issue_date,
  p.effective_date,
  p.insured_gender,
  p.insured_date_of_birth,
  p.is_outlier_user,
  coalesce(i.invoice_count, 0) as invoice_count,
  i.total_pre_levy_amount,
  i.total_amount_paid,
  coalesce(c.claim_count, 0) as claim_count,
  c.total_billed_amount,
  c.total_payable_amount
from policy p
left join invoice_agg i on p.policy_number = i.policy_number
left join claim_agg c on p.policy_number = c.policy_number
