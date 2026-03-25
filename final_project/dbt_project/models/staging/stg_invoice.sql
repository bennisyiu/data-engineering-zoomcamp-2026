{{
  config(
    materialized='view'
  )
}}
with source as (
  select * from {{ source('raw', 'raw_invoice') }}
),
valid_policies as (
  select distinct policy_number from {{ source('raw', 'raw_policy') }}
)
select
  i.id,
  i.invoice_type,
  i.policy_number,
  i.coverage_start_date::timestamptz as coverage_start_date,
  i.coverage_end_date::timestamptz   as coverage_end_date,
  i.due_date::timestamptz           as due_date,
  i.status,
  i.pre_levy_amount::numeric        as pre_levy_amount,
  i.total_amount::numeric           as total_amount,
  i.refund_date::date               as refund_date,
  i.charge_date::timestamptz        as charge_date
from source i
inner join valid_policies v on i.policy_number = v.policy_number
