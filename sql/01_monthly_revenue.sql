-- Net revenue, orders and average order value per month (returned lines excluded).
WITH order_totals AS (
    SELECT o.order_id,
           strftime('%Y-%m', o.order_ts) AS month,
           SUM(CASE WHEN NOT i.returned THEN i.net_revenue ELSE 0 END) AS revenue
    FROM orders o
    JOIN order_items i ON i.order_id = o.order_id
    GROUP BY o.order_id
)
SELECT month,
       COUNT(*)                     AS orders,
       SUM(revenue)                 AS revenue,
       ROUND(AVG(revenue), 0)       AS avg_order_value
FROM order_totals
GROUP BY month
ORDER BY month;
