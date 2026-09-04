"""Railway cron entrypoint: initialize, ingest, transform, test, and exit."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from sqlalchemy.engine import make_url


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DBT_PROJECT = PROJECT_ROOT / "dbt_project"


def run(*command: str, cwd: Path = PROJECT_ROOT, env: dict[str, str]) -> None:
    print(f"+ {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=cwd, env=env, check=True)


def add_postgres_variables(env: dict[str, str], database_url: str) -> None:
    url = make_url(database_url.replace("postgres://", "postgresql://", 1))
    env.update(
        {
            "DATABASE_URL": database_url,
            "POSTGRES_HOST": url.host or "",
            "POSTGRES_PORT": str(url.port or 5432),
            "POSTGRES_USER": url.username or "",
            "POSTGRES_PASSWORD": url.password or "",
            "POSTGRES_DB": url.database or "insurance_dwh",
        }
    )


def main() -> None:
    env = dict(os.environ)
    admin_url = env.get("ADMIN_DATABASE_URL") or env.get("DATABASE_URL")
    if not admin_url:
        raise RuntimeError("Set ADMIN_DATABASE_URL or DATABASE_URL")

    run(
        sys.executable,
        "infra/railway/bootstrap_database.py",
        env=env,
    )

    pipeline_url = env.get("PIPELINE_DATABASE_URL") or admin_url
    add_postgres_variables(env, pipeline_url)

    if env.get("SEED_BUCKET_ON_START", "false").lower() in {"1", "true", "yes"}:
        run(sys.executable, "scripts/upload_to_s3.py", env=env)

    run(sys.executable, "scripts/extract_load.py", env=env)
    profiles_path = DBT_PROJECT / "profiles.yml"
    if not profiles_path.exists():
        shutil.copy2(DBT_PROJECT / "profiles.yml.example", profiles_path)
    if (DBT_PROJECT / "packages.yml").exists():
        run("dbt", "deps", cwd=DBT_PROJECT, env=env)
    run(
        "dbt",
        "build",
        "--profiles-dir",
        str(DBT_PROJECT),
        cwd=DBT_PROJECT,
        env=env,
    )
    print("Railway ELT pipeline completed successfully.", flush=True)


if __name__ == "__main__":
    main()
