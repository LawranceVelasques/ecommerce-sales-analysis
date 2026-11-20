-- How much revenue comes from the top 10% and top 20% of customers.
WITH spend AS (
    SELECT o.customer_id,
           SUM(CASE WHEN NOT i.returned THEN i.net_revenue ELSE 0 END) AS revenue
    FROM orders o JOIN order_items i ON i.order_id = o.order_id
    GROUP BY o.customer_id
),
ranked AS (
    SELECT revenue, NTILE(10) OVER (ORDER BY revenue DESC) AS decile FROM spend
)
SELECT decile,
       COUNT(*)                                                    AS customers,
       SUM(revenue)                                                AS revenue,
       ROUND(100.0 * SUM(revenue) / (SELECT SUM(revenue) FROM spend), 1) AS revenue_share_pct
FROM ranked
GROUP BY decile
ORDER BY decile;
