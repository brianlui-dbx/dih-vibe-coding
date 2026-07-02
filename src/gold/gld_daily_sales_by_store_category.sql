-- Gold: daily sales aggregated by store, province, product category, and date.
-- Materialized View with a BATCH read of Silver (no STREAM) — aggregates recompute
-- correctly as Silver changes. All four slice dimensions are preserved so analysts
-- can filter by store, region, category, and day without losing information.
CREATE OR REFRESH MATERIALIZED VIEW gld_daily_sales_by_store_category
  COMMENT 'Gold daily sales rollup by store, province, product category, and sale date.'
  CLUSTER BY (sale_date, store_id)
AS SELECT
  store_id,
  store_province,
  product_category,
  sale_date,
  SUM(amount)                    AS total_sales,
  SUM(quantity)                  AS units_sold,
  COUNT(*)                       AS line_items,
  COUNT(DISTINCT transaction_id) AS transactions,
  COUNT(DISTINCT loyalty_id)     AS loyalty_members
FROM slv_pos_transaction
GROUP BY store_id, store_province, product_category, sale_date;
