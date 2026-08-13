WITH classement AS (
    SELECT
        p.category, p.product_name,
        ROUND(SUM(f.sales_amount), 2) AS ca,
        RANK() OVER (
            PARTITION BY p.category ORDER BY SUM(f.sales_amount) DESC
        ) AS rang_categorie
    FROM fact_sales f
    JOIN dim_product p ON f.product_id = p.product_id
    GROUP BY p.category, p.product_name
)
SELECT * FROM classement
WHERE rang_categorie <= 3
ORDER BY category, rang_categorie;