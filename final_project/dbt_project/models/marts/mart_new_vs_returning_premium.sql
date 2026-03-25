{{
  config(
    materialized='table'
  )
}}
with premium_per_policy as (
  select
    inv.policy_number,
    rnk.is_new_policy,
    sum(inv.pre_levy_amount) as total_net_premium
  from {{ ref('int_invoice_paid') }} inv
  join {{ ref('int_policy_ranked') }} rnk on inv.policy_number = rnk.policy_number
  where not rnk.is_outlier_user
  group by inv.policy_number, rnk.is_new_policy
)
select
  case when is_new_policy then 'new' else 'returning' end as policy_type,
  count(*)::int as policy_count,
  round(avg(total_net_premium)::numeric, 2) as avg_net_premium,
  round(sum(total_net_premium)::numeric, 2) as total_net_premium
from premium_per_policy
group by is_new_policy
order by is_new_policy desc
