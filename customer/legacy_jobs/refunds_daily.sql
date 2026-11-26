-- job: refunds_daily
-- owner: finance-analytics
-- complexity: simple
-- Refunds per day as positive amounts.

CREATE OR REPLACE TABLE warehouse.legacy_reporting.refunds_daily AS
SELECT paid_ts::DATE AS refund_date, -SUM(amount) AS refunded, COUNT(*) AS refunds
FROM warehouse.raw.payments
WHERE method = 'refund'
GROUP BY 1;
