# Streamlit — Text-to-SQL on `marts`

Optional demo for **DE Zoomcamp `final_project`**: natural-language questions → LLM-generated SQL → read-only execution against PostgreSQL **`marts`** (same tables built by dbt in this repo).

**Reviewers:** use the public URL your instructor provides (e.g. `http://<Elastic-IP>:8501`). You do **not** need an OpenRouter API key; only the server operator configures that in `.env`.

## Deploy with Docker Compose (recommended for EC2)

The **`streamlit`** service in [`infra/docker-compose.yml`](../infra/docker-compose.yml) builds from [`infra/Dockerfile.streamlit`](../infra/Dockerfile.streamlit), listens on **`0.0.0.0:8501`**, and connects to the **`warehouse`** container on the Compose network (you do **not** set `POSTGRES_HOST=localhost` for this service — Compose sets `warehouse` for you).

1. On the EC2 instance, in **`final_project/.env`**, set:
   - **`POSTGRES_HOST=warehouse`** (needed for Airflow + EL scripts inside Docker).
   - **`OPENROUTER_API_KEY`** (required for the LLM). Optionally `OPENROUTER_MODEL`, etc.
   - Warehouse credentials (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`) matching the `warehouse` service.

2. **Security group:** allow inbound **TCP 8501** (same Elastic IP as Airflow — e.g. `http://52.221.114.40:8501`).

3. From **`final_project/infra`**:

   ```bash
   docker compose --env-file ../.env build streamlit
   docker compose --env-file ../.env up -d
   ```

4. Confirm the container is up: `docker compose --env-file ../.env ps`

More context: [`infra/INFRA.md`](../infra/INFRA.md).

---

## Run on your laptop (without the Streamlit container)

Use this when you want to hack the app locally and talk to Postgres on **`localhost:5432`** (e.g. Compose published the warehouse port).

### Prerequisites

- Warehouse populated (`dbt run` or the Airflow DAG).
- **`final_project/.env`** with `POSTGRES_HOST=localhost` (or your host) and OpenRouter variables. Copy from [`infra/.env.example`](../infra/.env.example).

### Commands

```bash
cd final_project
pip install -r requirements.txt
cd streamlit_app
streamlit run app.py
```

Browser: **http://localhost:8501**

---

## Environment variables

| Variable | Purpose |
|----------|---------|
| `OPENROUTER_API_KEY` | Required for LLM calls. |
| `OPENROUTER_MODEL` | Optional. Default in code: `qwen/qwen3.5-flash-02-23`. |
| `OPENROUTER_SITE_URL` | Optional. HTTP-Referer for OpenRouter. |
| `OPENROUTER_APP_NAME` | Optional. App title for OpenRouter. |
| `POSTGRES_HOST` | **Docker Streamlit service:** set automatically to `warehouse`. **Local `streamlit run`:** `localhost` if warehouse publishes 5432 on the host. |
| `POSTGRES_PORT` | Default `5432`. |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Same as warehouse. |

---

## Safety

- Only **SELECT** / **WITH … SELECT** runs; other statements are rejected.
- Queries get **LIMIT 200** if the model omits a limit.

## Example prompts

| Prompt idea | Typical table |
|-------------|----------------|
| Compare new vs returning policy counts and average net premium | `mart_new_vs_returning_premium` |
| Top days by premium received | `mart_dashboard_daily` |
| Premium and loss ratio by product for the latest month | `mart_dashboard_by_product` |
| Policies with the most claims and payable amounts | `mart_policy_denormalized` |
| Recent weekly rollups for premium and policies | `mart_dashboard_rollups` |

## Troubleshooting

- **403 / banned provider on OpenRouter:** Set `OPENROUTER_MODEL` to a model allowed in your region; see [openrouter.ai/models](https://openrouter.ai/models).
- **Windows (local run):** Use `python -m streamlit run app.py` if `streamlit` is not on PATH.
- **Connection refused inside Docker:** Ensure the **`streamlit`** service is running and **`warehouse`** is healthy; use `docker compose logs streamlit`.
- **Check OpenRouter vars inside the container (on the machine where Docker runs):**
  ```bash
  cd infra
  docker compose exec streamlit sh -c 'test -n "$OPENROUTER_API_KEY" && echo OPENROUTER_API_KEY=is_set || echo OPENROUTER_API_KEY=EMPTY'
  docker compose exec streamlit printenv OPENROUTER_MODEL
  ```
  Do not paste the key into chats or screenshots. If `EMPTY`, confirm `final_project/.env` exists on that host and contains `OPENROUTER_API_KEY=...`, then `docker compose up -d streamlit --force-recreate`.
- **Elastic IP URL fails:** The stack must be running **on that EC2 instance** (not only on your laptop). Open **8501** in the instance security group.
