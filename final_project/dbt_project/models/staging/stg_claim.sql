{{
  config(
    materialized='view'
  )
}}
with source as (
  select * from {{ source('raw', 'raw_claim') }}
)
select
  id,
  type,
  status,
  policy_number,
  submit_date::timestamptz   as submit_date,
  payment_date::timestamptz as payment_date,
  admission_date::date      as admission_date,
  total_billed_amount::numeric         as total_billed_amount,
  total_base_payable_amount::numeric   as total_base_payable_amount
from source
