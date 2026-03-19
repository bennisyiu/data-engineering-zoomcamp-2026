-- Q1a: Average net premium (pre_levy_amount) for new vs returning policies.
-- New = user's first policy by effective_date; returning = 2nd+ policy.
-- Excludes users with >200 policies (outlier/test accounts).
-- Uses raw schema; same logic as dbt mart_new_vs_returning_premium.

WITH user_policy_count AS (
  SELECT user_id, COUNT(*) AS policy_count
  FROM raw.raw_policy
  GROUP BY user_id
),
policy_ranked AS (
  SELECT
    p.policy_number,
    p.user_id,
    ROW_NUMBER() OVER (PARTITION BY p.user_id ORDER BY p.effective_date, p.policy_number) AS policy_rank,
    (pc.policy_count > 200) AS is_outlier_user
  FROM raw.raw_policy p
  JOIN user_policy_count pc ON p.user_id = pc.user_id
),
premium_per_policy AS (
  SELECT
    inv.policy_number,
    (rnk.policy_rank = 1) AS is_new_policy,
    SUM(inv.pre_levy_amount::numeric) AS total_net_premium
  FROM raw.raw_invoice inv
  JOIN policy_ranked rnk ON inv.policy_number = rnk.policy_number
  WHERE inv.status = 'paid'
    AND NOT rnk.is_outlier_user
  GROUP BY inv.policy_number, rnk.policy_rank
)
SELECT
  CASE WHEN is_new_policy THEN 'new' ELSE 'returning' END AS policy_type,
  COUNT(*)::int AS policy_count,
  ROUND(AVG(total_net_premium)::numeric, 2) AS avg_net_premium,
  ROUND(SUM(total_net_premium)::numeric, 2) AS total_net_premium
FROM premium_per_policy
GROUP BY is_new_policy
ORDER BY is_new_policy DESC;
