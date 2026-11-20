-- Revenue, share of revenue, average discount and return rate per category.
SELECT p.category,
       SUM(CASE WHEN NOT i.returned THEN i.net_revenue ELSE 0 END)                         AS revenue,
       ROUND(100.0 * SUM(CASE WHEN NOT i.returned THEN i.net_revenue ELSE 0 END)
             / (SELECT SUM(net_revenue) FROM order_items WHERE NOT returned), 1)           AS revenue_share_pct,
       ROUND(100.0 * AVG(i.discount), 1)                                                   AS avg_discount_pct,
       ROUND(100.0 * AVG(i.returned), 1)                                                   AS return_rate_pct,
       COUNT(*)                                                                            AS lines
FROM order_items i
JOIN products p ON p.product_id = i.product_id
GROUP BY p.category
ORDER BY revenue DESC;
