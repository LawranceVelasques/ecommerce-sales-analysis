-- Share of customers who ordered once vs more than once in 2025.
WITH counts AS (SELECT customer_id, COUNT(*) AS n FROM orders GROUP BY customer_id)
SELECT CASE WHEN n = 1 THEN '1 order' WHEN n <= 3 THEN '2-3 orders'
            WHEN n <= 10 THEN '4-10 orders' ELSE '11+ orders' END AS bucket,
       COUNT(*) AS customers,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM counts), 1) AS pct_customers
FROM counts
GROUP BY bucket
ORDER BY MIN(n);
