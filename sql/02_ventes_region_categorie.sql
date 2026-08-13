SELECT
    r.region ,
    p. category ,
    ROUND (SUM (f. sales_amount ), 2) AS ca ,
    ROUND (SUM (f. profit ), 2) AS marge
FROM fact_sales f
JOIN dim_region r ON f. region_id = r. region_id
JOIN dim_product p ON f. product_id = p. product_id
GROUP BY r.region , p. category
ORDER BY ca DESC ;