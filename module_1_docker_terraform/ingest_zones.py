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
@click.option('--target-table', default='taxi_zone_lookup', help='Target table name')
def run(pg_user, pg_pass, pg_host, pg_port, pg_db, target_table):
    """Ingest taxi zone lookup CSV into PostgreSQL database"""
    
    # Zone lookup CSV URL
    url = 'https://github.com/DataTalksClub/nyc-tlc-data/releases/download/misc/taxi_zone_lookup.csv'
    
    # Build connection string
    engine = create_engine(f'postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}')
    
    print(f"Downloading CSV file from: {url}")
    df = pd.read_csv(url)
    
    print(f"Loaded {len(df)} rows")
    print(df.head())
    
    # Insert data
    df.to_sql(name=target_table, con=engine, if_exists="replace", index=False)
    print(f"Table '{target_table}' created and inserted: {len(df)} rows")

if __name__ == '__main__':
    run()