SELECT
    d.year , d.month , d. month_name ,
    ROUND (SUM (f. sales_amount ), 2) AS ca_mensuel
FROM fact_sales f
JOIN dim_date d ON f. date_id = d. date_id
GROUP BY d.year , d.month , d. month_name
ORDER BY d.year , d. month ;