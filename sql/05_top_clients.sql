SELECT
    c. customer_name ,
    c. segment ,
    ROUND (SUM (f. sales_amount ), 2) AS ca_cumule ,
    COUNT ( DISTINCT f. order_id ) AS nb_commandes
FROM fact_sales f
JOIN dim_customer c ON f. customer_id = c. customer_id
GROUP BY c. customer_name , c. segment
ORDER BY ca_cumule DESC
LIMIT 10;