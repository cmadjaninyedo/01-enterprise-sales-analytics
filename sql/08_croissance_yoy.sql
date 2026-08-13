WITH ca_annuel AS (
    SELECT d.year , SUM(f. sales_amount ) AS ca
    FROM fact_sales f
    JOIN dim_date d ON f. date_id = d. date_id
    GROUP BY d. year
)
SELECT
    year , ROUND (ca , 2) AS ca ,
    ROUND (
        (ca - LAG(ca) OVER ( ORDER BY year ))
        / NULLIF ( LAG(ca) OVER ( ORDER BY year ), 0) * 100 , 2
    ) AS croissance_yoy_pct
FROM ca_annuel
ORDER BY year ;