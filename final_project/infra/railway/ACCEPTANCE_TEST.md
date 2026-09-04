# Railway acceptance test

Run this checklist before permanently deleting the original AWS resources.
The Railway project is `insurance-dwh-portfolio`.

## 1. Confirm the safe baseline

In the Railway project canvas, confirm:

- `Postgres` is **Online**.
- `streamlit` is **Online** or sleeping until requested.
- `elt-pipeline` and `database-backup` are **Ready** with future schedules.
- Airflow, ZooKeeper, Kafka, the producer, and Flink show **Completed** while
  their `DEMO_MODE` variable is `false`.
- PostgreSQL has no public TCP proxy.

## 2. Test Streamlit and OpenRouter

1. Open https://streamlit-production-43ac.up.railway.app.
2. Allow several seconds for a serverless cold start.
3. Submit: `How many policies are there?`
4. Confirm the app displays generated read-only SQL and a result.
   The current mart result is 696 policies: 78 new and 618 returning.
5. Also try:
   - `Compare new and returning customers by policy count and average net premium.`
   - `Which products have the highest loss ratio in the latest month?`
6. Confirm no database or OpenRouter error appears.

## 3. Test Tableau

1. Open the [Tableau Public story](https://public.tableau.com/shared/65BQGNBFS?:display_count=n&:origin=viz_share_link).
2. Open each of the four dashboards.
3. Exercise at least one filter and confirm the charts update.

## 4. Test the ELT and dbt job

1. Open `elt-pipeline` in Railway.
2. Restart or redeploy the latest successful deployment to run it immediately.
3. Follow the deployment logs.
4. Confirm the logs report:
   - 6,583 policy rows;
   - 9,646 invoice rows;
   - 791 claim rows;
   - `PASS=29`, `ERROR=0`; and
   - `Railway ELT pipeline completed successfully`.
5. Confirm the service returns to **Ready** for its Sunday 03:00 UTC schedule.

## 5. Test the backup job

1. Open `database-backup`.
2. Restart the latest successful deployment.
3. Confirm its log reports an upload under
   `s3://.../backups/insurance_dwh-<timestamp>.dump`.
4. Confirm the service returns to **Ready** for its monthly schedule.

## 6. Test Airflow on demand

1. On both `airflow-webserver` and `airflow-scheduler`, change
   `DEMO_MODE` from `false` to `true` and deploy.
2. Wait until both deployments show **Success**.
3. Open https://airflow-webserver-production-be4b.up.railway.app.
4. Sign in as `admin` using the private `AIRFLOW_ADMIN_PASSWORD` shown only in
   the webserver's Railway Variables tab.
5. Confirm the `insurance_elt_pipeline` DAG is visible.
6. Open `/health` on the same domain and confirm the metadatabase and scheduler
   are healthy.
7. Optionally trigger the DAG and confirm its ingestion, dbt run, and dbt test
   tasks finish.
8. Set `DEMO_MODE=false` on both services and deploy again. Confirm both show
   **Completed**.

## 7. Test Kafka and PyFlink on demand

Start the services in dependency order:

1. Set `DEMO_MODE=true` on `zookeeper` and deploy. Wait for its log to show it
   listening on port `2181`.
2. Set `DEMO_MODE=true` on `kafka` and deploy. Wait for
   `KafkaServer id=1 started` and port `29092`.
3. Set `DEMO_MODE=true` on `flink-streaming` and `event-producer`, then deploy
   both.
4. Confirm producer logs show `Sent 1`, `Sent 2`, and later events.
5. Confirm Flink logs show `Executing Flink job` with the Railway-private Kafka
   and PostgreSQL hosts and no exception.
6. In the PostgreSQL data/query interface, run:

   ```sql
   SELECT COUNT(*) AS event_count, MAX(received_at) AS latest_event
   FROM raw_streaming.stream_policy_events;
   ```

7. Confirm `event_count` increases while the producer is running.
8. Set `DEMO_MODE=false` on the producer, Flink, Kafka, and ZooKeeper, then
   deploy. Confirm all four show **Completed**.

## 8. Final cost and security check

- Leave only PostgreSQL continuously online.
- Leave Streamlit serverless.
- Leave the ELT and backup services on their schedules.
- Confirm every heavy demo service has `DEMO_MODE=false`.
- Confirm PostgreSQL remains private with no TCP proxy.
- Check Railway usage after 24–48 hours and keep the soft alert near US$4.

When every required check passes, approve permanent AWS retirement.
