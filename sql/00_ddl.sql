CREATE TABLE dim_date (
date_id SERIAL PRIMARY KEY ,
full_date DATE NOT NULL UNIQUE ,
year INT NOT NULL ,
quarter INT NOT NULL ,
month INT NOT NULL ,
month_name VARCHAR (20) NOT NULL ,
day INT NOT NULL ,
day_of_week VARCHAR (10) NOT NULL ,
is_weekend BOOLEAN NOT NULL
);
CREATE TABLE dim_customer (
customer_id VARCHAR (20) PRIMARY KEY ,
customer_name VARCHAR (100) NOT NULL ,
segment VARCHAR (50) NOT NULL
);
CREATE TABLE dim_product (
product_id VARCHAR (20) PRIMARY KEY ,
product_name VARCHAR (200) NOT NULL ,
category VARCHAR (50) NOT NULL ,
sub_category VARCHAR (50) NOT NULL
);
CREATE TABLE dim_region (
region_id SERIAL PRIMARY KEY ,
region VARCHAR (50) NOT NULL ,
state VARCHAR (50) NOT NULL ,
city VARCHAR (100) NOT NULL ,
postal_code VARCHAR (10) ,
country VARCHAR (50) NOT NULL
);

CREATE TABLE fact_sales (
sales_id SERIAL PRIMARY KEY ,
order_id VARCHAR (20) NOT NULL ,
date_id INT NOT NULL REFERENCES dim_date ( date_id ),
customer_id VARCHAR (20) NOT NULL REFERENCES dim_customer ( customer_id ),
product_id VARCHAR (20) NOT NULL REFERENCES dim_product ( product_id ),
region_id INT NOT NULL REFERENCES dim_region ( region_id ),
ship_mode VARCHAR (30) ,
sales_amount NUMERIC (12 ,2) NOT NULL ,
quantity INT NOT NULL ,
discount NUMERIC (5 ,2) DEFAULT 0,
profit NUMERIC (12 ,2) NOT NULL
);
CREATE INDEX idx_fact_sales_date ON fact_sales ( date_id );
CREATE INDEX idx_fact_sales_customer ON fact_sales ( customer_id );
CREATE INDEX idx_fact_sales_product ON fact_sales ( product_id );