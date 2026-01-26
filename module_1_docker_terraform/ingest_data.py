#!/usr/bin/env python
# coding: utf-8
# ingest_data.py - v3 - Flexible ingestion script with dataset selection

import pandas as pd
import click
from sqlalchemy import create_engine

@click.command()
@click.option('--pg-user', default='root', help='PostgreSQL user')
@click.option('--pg-pass', default='root', help='PostgreSQL password')
@click.option('--pg-host', default='localhost', help='PostgreSQL host')
@click.option('--pg-port', default=5432, type=int, help='PostgreSQL port')
@click.option('--pg-db', default='ny_taxi', help='PostgreSQL database name')
@click.option('--dataset', type=click.Choice(['yellow', 'green', 'zones', 'all']), default='all', help='Which dataset to load')
def run(pg_user, pg_pass, pg_host, pg_port, pg_db, dataset):
    """Ingest NYC taxi data into PostgreSQL database"""
    
    engine = create_engine(f'postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}')
    
    if dataset in ['yellow', 'all']:
        print("\n=== Loading Yellow Taxi Data ===")
        yellow_url = 'https://github.com/DataTalksClub/nyc-tlc-data/releases/download/yellow/yellow_tripdata_2021-01.csv.gz'
        df_yellow = pd.read_csv(yellow_url, parse_dates=['tpep_pickup_datetime', 'tpep_dropoff_datetime'])
        print(f"Loaded {len(df_yellow)} rows")
        df_yellow.to_sql(name='yellow_taxi_trips', con=engine, if_exists='replace', index=False)
        print("✓ Yellow taxi data inserted")
    
    if dataset in ['green', 'all']:
        print("\n=== Loading Green Taxi Data ===")
        green_url = 'https://d37ci6vzurychx.cloudfront.net/trip-data/green_tripdata_2019-10.parquet'
        df_green = pd.read_parquet(green_url)
        print(f"Loaded {len(df_green)} rows")
        df_green.to_sql(name='green_taxi_trips', con=engine, if_exists='replace', index=False)
        print("✓ Green taxi data inserted")
    
    if dataset in ['zones', 'all']:
        print("\n=== Loading Zone Lookup Data ===")
        zones_url = 'https://github.com/DataTalksClub/nyc-tlc-data/releases/download/misc/taxi_zone_lookup.csv'
        df_zones = pd.read_csv(zones_url)
        print(f"Loaded {len(df_zones)} rows")
        df_zones.to_sql(name='taxi_zone_lookup', con=engine, if_exists='replace', index=False)
        print("✓ Zone lookup data inserted")
    
    print("\n=== Done! ===")

if __name__ == '__main__':
    run()