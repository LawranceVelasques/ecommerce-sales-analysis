-- Orders by hour of day.
SELECT CAST(strftime('%H', order_ts) AS INTEGER) AS hour, COUNT(*) AS orders
FROM orders GROUP BY hour ORDER BY hour;
