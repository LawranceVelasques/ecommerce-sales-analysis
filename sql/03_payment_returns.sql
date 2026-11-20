-- Return rate and revenue lost to returns by payment method.
SELECT o.payment_method,
       COUNT(DISTINCT o.order_id)                                         AS orders,
       ROUND(100.0 * AVG(i.returned), 1)                                  AS return_rate_pct,
       SUM(CASE WHEN i.returned THEN i.net_revenue ELSE 0 END)            AS revenue_lost
FROM orders o
JOIN order_items i ON i.order_id = o.order_id
GROUP BY o.payment_method
ORDER BY return_rate_pct DESC;
