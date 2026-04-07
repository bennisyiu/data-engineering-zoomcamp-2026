"""
Text-to-SQL demo: natural language → SQL against dbt marts (read-only).
Uses OpenRouter (OpenAI-compatible API). Loads secrets from final_project root .env.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from sqlalchemy import create_engine, text

# final_project/streamlit_app/app.py → repo root for this capstone is parent.parent
REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
# Override with OPENROUTER_MODEL in .env; confirm slug at https://openrouter.ai/models
DEFAULT_MODEL = "qwen/qwen3.5-flash-02-23"
_MODEL_TYPO = "qwen/qwen3.5-flash-02-23s"

# Matches final_project dbt marts (six models; no mart_exec_summary)
MARTS_SCHEMA_DOC = """
All tables live in schema `marts`. Use qualified names: marts.<table>.

-- mart_new_vs_returning_premium: new vs returning policies (excl. outlier user)
-- policy_type (text): 'new' | 'returning'
-- policy_count (int), avg_net_premium (numeric), total_net_premium (numeric)

-- mart_policy_denormalized: one row per policy
-- policy_number, user_id, product, issue_date, effective_date, insured_gender,
-- insured_date_of_birth, is_outlier_user (bool),
-- invoice_count, total_pre_levy_amount, total_amount_paid,
-- claim_count, total_billed_amount, total_payable_amount

-- mart_dashboard_daily: one row per calendar day (excl. outlier user)
-- day_date, premium_received, policies_issued, claims_paid, claim_count,
-- loss_ratio, avg_premium_per_policy, avg_claim_amount

-- mart_dashboard_monthly: one row per month
-- month_start, premium_received, policies_issued, claims_paid, claim_count,
-- loss_ratio, avg_premium_per_policy, avg_claim_amount

-- mart_dashboard_rollups: by time_grain + period_start
-- time_grain: 'D'|'W'|'M'|'Q'|'Y'; period_start; premium_received, policies_issued,
-- claims_paid, claim_count, loss_ratio, avg_premium_per_policy, avg_claim_amount;
-- columns ending in _ly = same period last year (M/Q/Y only): period_start_ly,
-- premium_received_ly, policies_issued_ly, claims_paid_ly, claim_count_ly,
-- loss_ratio_ly, avg_premium_per_policy_ly, avg_claim_amount_ly

-- mart_dashboard_by_product: one row per month + product
-- month_start, product, premium_received, policies_issued, claims_paid, claim_count,
-- loss_ratio, avg_premium_per_policy, avg_claim_amount,
-- month_start_ly, premium_received_ly, policies_issued_ly, claims_paid_ly,
-- claim_count_ly, loss_ratio_ly, avg_premium_per_policy_ly, avg_claim_amount_ly
"""


def get_engine():
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    db = os.getenv("POSTGRES_DB", "insurance_dwh")
    if not user or not password:
        raise ValueError("Set POSTGRES_USER and POSTGRES_PASSWORD in final_project/.env")
    u, p = quote_plus(user), quote_plus(password)
    return create_engine(f"postgresql://{u}:{p}@{host}:{port}/{db}")


def validate_readonly_sql(sql: str) -> tuple[bool, str]:
    s = sql.strip()
    if not s:
        return False, "Empty SQL"
    if ";" in s.rstrip().rstrip(";"):
        return False, "Only one SQL statement allowed (no semicolon chains)"
    s = s.rstrip().rstrip(";").strip()
    upper = s.upper()
    if not (upper.startswith("SELECT") or upper.startswith("WITH")):
        return False, "Only SELECT (or WITH … SELECT) queries are allowed"
    forbidden = re.compile(
        r"\b(INSERT|UPDATE|DELETE|DROP|TRUNCATE|ALTER|CREATE|GRANT|REVOKE|COPY|CALL|EXECUTE)\b",
        re.I,
    )
    if forbidden.search(s):
        return False, "Query contains forbidden keywords"
    return True, ""


def ensure_limit(sql: str, max_rows: int = 200) -> str:
    s = sql.strip().rstrip(";").strip()
    if re.search(r"\blimit\s+\d+\s*$", s, re.I):
        return s
    return f"{s} LIMIT {max_rows}"


def extract_sql_from_response(content: str) -> str:
    """Take first ```sql ... ``` block or fall back to stripped text."""
    m = re.search(r"```(?:sql)?\s*([\s\S]*?)```", content, re.I)
    if m:
        return m.group(1).strip()
    return content.strip()


def generate_sql(question: str, client: OpenAI, model: str) -> str:
    system = (
        "You are a careful PostgreSQL analyst. Generate a single read-only query. "
        "Rules:\n"
        "- Use only the marts schema described below.\n"
        "- Return exactly one SQL statement, no explanation outside a markdown sql fence.\n"
        "- Prefer explicit column lists or aggregates; include LIMIT 200 if not already present.\n"
        "- Use ISO dates where filtering dates.\n\n"
        f"Schema:\n{MARTS_SCHEMA_DOC}"
    )
    referer = os.getenv(
        "OPENROUTER_SITE_URL",
        "https://github.com/DataTalksClub/data-engineering-zoomcamp",
    )
    title = os.getenv("OPENROUTER_APP_NAME", "DE Zoomcamp Insurance Text-to-SQL")
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": question},
        ],
        temperature=0.1,
        extra_headers={
            "HTTP-Referer": referer,
            "X-Title": title,
        },
    )
    return extract_sql_from_response(resp.choices[0].message.content or "")


def main():
    st.set_page_config(page_title="Insurance Text-to-SQL", layout="wide")
    st.title("Insurance warehouse — Text-to-SQL (marts)")
    st.caption(
        "Ask in plain English. The app generates SQL, validates it as read-only, "
        "and runs it against PostgreSQL **marts** only (final_project dbt models)."
    )

    api_key = os.getenv("OPENROUTER_API_KEY")
    model = (os.getenv("OPENROUTER_MODEL") or DEFAULT_MODEL).strip()
    if model == _MODEL_TYPO:
        model = DEFAULT_MODEL
    if not api_key:
        st.error(
            "Set `OPENROUTER_API_KEY` in `final_project/.env` (see `infra/.env.example`) "
            "and restart Streamlit."
        )
        st.stop()

    with st.sidebar:
        st.subheader("Model")
        st.code(model, language="text")
        st.subheader("Postgres")
        st.text(
            f"{os.getenv('POSTGRES_HOST', 'localhost')}:{os.getenv('POSTGRES_PORT', '5432')} / "
            f"{os.getenv('POSTGRES_DB', 'insurance_dwh')}"
        )
        with st.expander("Marts schema (for reviewers)"):
            st.markdown(f"```\n{MARTS_SCHEMA_DOC}\n```")

    default_q = (
        "What is the average total net premium for returning vs new customers "
        "in mart_new_vs_returning_premium?"
    )
    question = st.text_area("Your question", value=default_q, height=100)
    run = st.button("Generate SQL & run", type="primary")

    if not run:
        return

    client = OpenAI(api_key=api_key, base_url=OPENROUTER_BASE)
    with st.spinner("Calling OpenRouter…"):
        try:
            raw_sql = generate_sql(question, client, model)
        except Exception as e:
            msg = str(e).lower()
            st.error(f"OpenRouter error: {e}")
            if "banned" in msg:
                st.info(
                    "This provider may be blocked for your OpenRouter account/region. Try a different "
                    "family in `.env`, e.g. `OPENROUTER_MODEL=qwen/qwen3.5-flash-02-23`, "
                    "`google/gemini-2.0-flash-001`, or `deepseek/deepseek-chat` — then restart Streamlit. "
                    "See https://openrouter.ai/models"
                )
            elif "403" in str(e):
                st.info(
                    "403 often means the model is unavailable for your key. Pick another slug at "
                    "https://openrouter.ai/models."
                )
            elif "not a valid model" in msg or ("400" in str(e) and "model" in msg):
                st.info(
                    "Use an exact model slug from [openrouter.ai/models](https://openrouter.ai/models). "
                    "Typo: `qwen/qwen3.5-flash-02-23s` → `qwen/qwen3.5-flash-02-23` (no trailing **s**). "
                    "Fix `final_project/.env` and recreate the `streamlit` container."
                )
            return

    st.subheader("Generated SQL")
    st.code(raw_sql, language="sql")

    ok, err = validate_readonly_sql(raw_sql)
    if not ok:
        st.error(f"Blocked: {err}")
        return

    sql = ensure_limit(raw_sql)
    if sql != raw_sql.rstrip().rstrip(";").strip():
        st.info("Appended a row limit for safety.")

    try:
        engine = get_engine()
        with engine.connect() as conn:
            df = pd.read_sql(text(sql), conn)
    except Exception as e:
        st.error(f"Database error: {e}")
        low = str(e).lower()
        if "connection refused" in low or "could not connect to server" in low:
            st.info(
                "**Nothing is accepting Postgres on this host/port.** Typical fixes:\n\n"
                "- **Streamlit in Docker (`streamlit` service):** the app should use "
                "`POSTGRES_HOST=warehouse` (set in `docker-compose.yml`). Check that the "
                "`warehouse` container is healthy: `docker compose --env-file ../.env ps` "
                "from `final_project/infra`.\n\n"
                "- **Streamlit on your laptop (`streamlit run`):** start the stack so "
                "`warehouse` publishes **5432**, and use `POSTGRES_HOST=localhost` in "
                "`final_project/.env`.\n\n"
                "- **Warehouse only reachable on EC2’s public IP:** use that IP as "
                "`POSTGRES_HOST` and open **5432** in the security group for your IP.\n\n"
                "- **Port clash on 5432:** change the host mapping in "
                "`infra/docker-compose.yml` or stop the conflicting service."
            )
        return

    st.subheader("Results")
    st.dataframe(df, use_container_width=True)
    st.caption(f"{len(df)} row(s)")


if __name__ == "__main__":
    main()
