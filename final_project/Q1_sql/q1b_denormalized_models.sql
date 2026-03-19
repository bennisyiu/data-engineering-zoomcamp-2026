-- Q1b: Denormalized model — one row per policy with policy attributes and
-- aggregated paid-invoice and claim metrics. Uses raw schema; same logic as
-- dbt mart_policy_denormalized. Orphan invoices (no matching policy) excluded.

WITH valid_invoice AS (
  SELECT inv.*
  FROM raw.raw_invoice inv
  WHERE EXISTS (SELECT 1 FROM raw.raw_policy p WHERE p.policy_number = inv.policy_number)
),
invoice_agg AS (
  SELECT
    policy_number,
    COUNT(*)::int AS invoice_count,
    ROUND(SUM(pre_levy_amount::numeric), 2) AS total_pre_levy_amount,
    ROUND(SUM(total_amount::numeric), 2) AS total_amount_paid
  FROM valid_invoice
  WHERE status = 'paid'
  GROUP BY policy_number
),
claim_agg AS (
  SELECT
    policy_number,
    COUNT(*)::int AS claim_count,
    ROUND(SUM(total_billed_amount::numeric), 2) AS total_billed_amount,
    ROUND(SUM(total_base_payable_amount::numeric), 2) AS total_payable_amount
  FROM raw.raw_claim
  GROUP BY policy_number
)
SELECT
  p.policy_number,
  p.user_id,
  p.product,
  p.issue_date,
  p.effective_date,
  p.insured_gender,
  p.insured_date_of_birth,
  COALESCE(i.invoice_count, 0) AS invoice_count,
  i.total_pre_levy_amount,
  i.total_amount_paid,
  COALESCE(c.claim_count, 0) AS claim_count,
  c.total_billed_amount,
  c.total_payable_amount
FROM raw.raw_policy p
LEFT JOIN invoice_agg i ON p.policy_number = i.policy_number
LEFT JOIN claim_agg c ON p.policy_number = c.policy_number
ORDER BY p.policy_number;
