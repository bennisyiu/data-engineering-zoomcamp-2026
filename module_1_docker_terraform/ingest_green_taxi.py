#!/usr/bin/env python
# coding: utf-8
import pandas as pd
import click
from sqlalchemy import create_engine

@click.command()
@click.option('--pg-user', default='root', help='PostgreSQL user')
@click.option('--pg-pass', default='root', help='PostgreSQL password')
@click.option('--pg-host', default='localhost', help='PostgreSQL host')
@click.option('--pg-port', default=5432, type=int, help='PostgreSQL port')
@click.option('--pg-db', default='ny_taxi', help='PostgreSQL database name')
@click.option('--target-table', default='green_taxi_trips', help='Target table name')
def run(pg_user, pg_pass, pg_host, pg_port, pg_db, target_table):
    """Ingest green taxi data (parquet) into PostgreSQL database"""
    
    # Hardcoded green taxi November 2025 URL
    url = 'https://d37ci6vzurychx.cloudfront.net/trip-data/green_tripdata_2025-11.parquet'
    
    # Build connection string
    engine = create_engine(f'postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}')
    
    print(f"Downloading parquet file from: {url}")
    df = pd.read_parquet(url)
    
    print(f"Loaded {len(df)} rows")
    print(df.head())
    print(df.dtypes)
    
    # Get DDL Schema
    print(pd.io.sql.get_schema(df, name=target_table, con=engine))
    
    # Insert data
    df.to_sql(name=target_table, con=engine, if_exists="replace", index=False)
    print(f"Table '{target_table}' created and inserted: {len(df)} rows")

if __name__ == '__main__':
    run()