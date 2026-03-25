select
    -- identifiers
    cast(VendorID as int) as vendor_id,
    cast(RateCodeID as int) as rate_code_id,
    cast(PULocationID as int) as pickup_location_id,
    cast(DOLocationID as int) as dropoff_location_id,

    -- timestamps
    cast(tpep_pickup_datetime as timestamp) as pickup_datetime,
    cast(tpep_dropoff_datetime as timestamp) as dropoff_datetime,

    -- trip info
    store_and_fwd_flag,
    cast(passenger_count as int) as passenger_count,
    cast(trip_distance as numeric) as trip_distance,
    1 as trip_type, -- yellow taxis are street-hailed (0 for green taxis, 1 for everything else))

    -- payment info
    cast(fare_amount as numeric) as fare_amount,
    cast(extra as numeric) as extra,
    cast(mta_tax as numeric) as mta_tax,
    cast(tip_amount as numeric) as tip_amount,
    cast(tolls_amount as numeric) as tolls_amount,
    0 as ehail_fee, -- yellow taxis are street-hailed and do not have an ehail fee
    cast(improvement_surcharge as numeric) as improvement_surcharge,
    cast(total_amount as numeric) as total_amount,
    cast(congestion_surcharge as numeric) as congestion_surcharge,
    cast(payment_type as int) as payment_type

from {{ source('raw_data', 'yellow_tripdata') }}
where vendorid is not null