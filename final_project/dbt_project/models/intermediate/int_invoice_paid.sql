{{
  config(
    materialized='view'
  )
}}
select *
from {{ ref('stg_invoice') }}
where status = 'paid'
