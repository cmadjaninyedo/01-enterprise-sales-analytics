WITH ca_mensuel AS (
    SELECT d.year , d.month , SUM(f. sales_amount ) AS ca
    FROM fact_sales f
    JOIN dim_date d ON f. date_id = d. date_id
    GROUP BY d.year , d. month
)
SELECT
    year , month , ROUND (ca , 2) AS ca ,
    ROUND (
        AVG (ca) OVER (
            ORDER BY year , month
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ), 2
    ) AS moyenne_mobile_3mois
FROM ca_mensuel
ORDER BY year , month ;