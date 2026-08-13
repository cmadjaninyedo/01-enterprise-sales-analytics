WITH ventes_produit AS (
    SELECT p. product_name , SUM(f. sales_amount ) AS ca
    FROM fact_sales f
    JOIN dim_product p ON f. product_id = p. product_id
    GROUP BY p. product_name
)
SELECT product_name , ROUND (ca , 2) AS ca
FROM ventes_produit
ORDER BY ca DESC
LIMIT 10;