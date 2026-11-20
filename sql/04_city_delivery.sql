-- Orders, revenue and delivery time per customer city.
SELECT c.city,
       COUNT(DISTINCT o.order_id)                                       AS orders,
       SUM(CASE WHEN NOT i.returned THEN i.net_revenue ELSE 0 END)      AS revenue,
       ROUND(AVG(o.shipping_days), 1)                                   AS avg_shipping_days,
       ROUND(100.0 * AVG(o.shipping_days > 3), 1)                       AS pct_over_3_days
FROM orders o
JOIN customers c   ON c.customer_id = o.customer_id
JOIN order_items i ON i.order_id = o.order_id
GROUP BY c.city
ORDER BY revenue DESC;
