-- Silver: cleaned, typed POS transactions read incrementally from Bronze.
-- Expectations enforce data quality; constraints are evaluated on the projected
-- (cast) columns below, so an unparseable transaction_ts casts to NULL and is dropped.
-- Dedup note: this is an append-only Streaming Table, so we do NOT run a stateful
-- dropDuplicates here (that would require a watermark and can silently drop late data).
-- transaction_id is the business key; last-write-wins dedup is handled downstream
-- (e.g. an AUTO CDC flow) rather than with an unsafe streaming distinct.
CREATE OR REFRESH STREAMING TABLE slv_pos_transaction (
  CONSTRAINT valid_store_id       EXPECT (store_id IS NOT NULL)        ON VIOLATION DROP ROW,
  CONSTRAINT valid_transaction_ts EXPECT (transaction_ts IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT positive_amount      EXPECT (amount > 0),
  CONSTRAINT positive_quantity    EXPECT (quantity > 0),
  CONSTRAINT known_category       EXPECT (product_category IS NOT NULL)
)
  COMMENT 'Silver cleaned + typed POS transactions with data-quality expectations.'
  CLUSTER BY (sale_date)
AS SELECT
  transaction_id,
  CAST(store_id AS INT)                       AS store_id,
  store_province,
  CAST(transaction_ts AS TIMESTAMP)           AS transaction_ts,
  to_date(CAST(transaction_ts AS TIMESTAMP))  AS sale_date,
  product_id,
  product_name,
  product_category,
  CAST(quantity AS INT)                       AS quantity,
  CAST(unit_price AS DECIMAL(10, 2))          AS unit_price,
  CAST(amount AS DECIMAL(10, 2))              AS amount,
  loyalty_id,
  payment_method
FROM STREAM(brz_pos_transaction);
