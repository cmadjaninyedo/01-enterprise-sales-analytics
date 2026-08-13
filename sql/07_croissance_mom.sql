WITH ca_mensuel AS (
    SELECT
        d.year , d.month ,
        SUM (f. sales_amount ) AS ca
    FROM fact_sales f
    JOIN dim_date d ON f. date_id = d. date_id
    GROUP BY d.year , d. month
)
SELECT
    year , month , ROUND (ca , 2) AS ca ,
    ROUND (
        (ca - LAG(ca) OVER ( ORDER BY year , month ))
        / NULLIF ( LAG(ca) OVER ( ORDER BY year , month ), 0) * 100 , 2
    ) AS croissance_mom_pct
FROM ca_mensuel
ORDER BY year , month ;