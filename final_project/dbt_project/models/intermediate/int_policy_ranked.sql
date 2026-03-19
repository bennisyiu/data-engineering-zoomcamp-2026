{{
  config(
    materialized='view'
  )
}}
with policy_ranked as (
  select
    id,
    policy_number,
    user_id,
    application_id,
    product,
    issue_date,
    effective_date,
    insured_gender,
    insured_date_of_birth,
    is_outlier_user,
    row_number() over (partition by user_id order by effective_date, policy_number) as policy_rank
  from {{ ref('stg_policy') }}
)
select
  *,
  (policy_rank = 1) as is_new_policy
from policy_ranked
