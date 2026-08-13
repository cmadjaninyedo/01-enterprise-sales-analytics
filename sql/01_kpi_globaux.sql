SELECT
    ROUND (SUM ( sales_amount ), 2) AS ca_total ,
    ROUND (SUM ( profit ), 2) AS marge_totale ,
    COUNT ( DISTINCT order_id ) AS nb_commandes
FROM fact_sales ;