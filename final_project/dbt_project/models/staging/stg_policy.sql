{{
  config(
    materialized='view'
  )
}}
with source as (
  select * from {{ source('raw', 'raw_policy') }}
),
policy_counts as (
  select
    user_id,
    count(*) as policy_count
  from source
  group by user_id
)
select
  s.id,
  s.policy_number,
  s.user_id,
  s.application_id,
  s.product,
  s.issue_date::timestamptz     as issue_date,
  s.effective_date::timestamptz as effective_date,
  s.insured_gender,
  s.insured_date_of_birth::date as insured_date_of_birth,
  coalesce(pc.policy_count > 200, false) as is_outlier_user
from source s
left join policy_counts pc on s.user_id = pc.user_id
