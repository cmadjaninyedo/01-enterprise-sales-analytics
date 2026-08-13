SELECT
    c. segment ,
    ROUND (AVG (f. sales_amount ), 2) AS panier_moyen ,
    ROUND (SUM (f. sales_amount ) / COUNT ( DISTINCT f. order_id ), 2)
        AS ca_moyen_par_commande
FROM fact_sales f
JOIN dim_customer c ON f. customer_id = c. customer_id
GROUP BY c. segment
ORDER BY panier_moyen DESC ;