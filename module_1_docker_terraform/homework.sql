-- Question 3. For the trips in November 2025, 
-- how many trips had a trip_distance of less than or equal to 1 mile? (1 point)
SELECT count(*)
FROM public.green_taxi_trips
WHERE lpep_pickup_datetime >= '2025-11-01' 
  AND lpep_pickup_datetime < '2025-12-01'
  AND trip_distance <= 1;

-- Question 4. Which was the pick up day with the longest trip distance? 
-- Only consider trips with trip_distance less than 100 miles. 
SELECT lpep_pickup_datetime, trip_distance
FROM public.green_taxi_trips
WHERE trip_distance < 100
order by trip_distance DESC

-- Question 5. Which was the pickup zone with the largest total_amount (sum of all trips) on November 18th, 2025? (1 point)
SELECT 
    z."Zone",
    SUM(g.total_amount) as total_amount_sum
FROM public.green_taxi_trips g
JOIN public.taxi_zone_lookup z ON g."PULocationID" = z."LocationID"
WHERE DATE(g.lpep_pickup_datetime) = '2025-11-18'
GROUP BY z."Zone"
ORDER BY total_amount_sum DESC
LIMIT 1;

-- Question 6. For the passengers picked up in the zone named "East Harlem North" in November 2025, 
-- which was the drop off zone that had the largest tip?
-- which was the drop off zone that had the largest tip?
SELECT 
    do_zone."Zone" as dropoff_zone,
    MAX(g.tip_amount) as largest_tip
FROM public.green_taxi_trips g
JOIN public.taxi_zone_lookup pu_zone ON g."PULocationID" = pu_zone."LocationID"
JOIN public.taxi_zone_lookup do_zone ON g."DOLocationID" = do_zone."LocationID"
WHERE pu_zone."Zone" = 'East Harlem North'
  AND g.lpep_pickup_datetime >= '2025-11-01'
  AND g.lpep_pickup_datetime < '2025-12-01'
GROUP BY do_zone."Zone"
ORDER BY largest_tip DESC
LIMIT 1;
