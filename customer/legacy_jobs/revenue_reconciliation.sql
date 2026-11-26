-- job: revenue_reconciliation
-- owner: finance-analytics
-- complexity: hard
-- Gross and refunds per day; an INSERT adds refund-only days.

CREATE OR REPLACE TABLE warehouse.legacy_reporting.revenue_reconciliation AS
SELECT d.revenue_date AS day, d.gross_revenue, COALESCE(r.refunded, 0) AS refunded,
       d.gross_revenue - COALESCE(r.refunded, 0) AS net_revenue
FROM warehouse.legacy_reporting.daily_revenue d
LEFT JOIN warehouse.legacy_reporting.refunds_daily r ON r.refund_date = d.revenue_date;

INSERT INTO warehouse.legacy_reporting.revenue_reconciliation
SELECT r.refund_date, 0, r.refunded, -r.refunded
FROM warehouse.legacy_reporting.refunds_daily r
WHERE r.refund_date NOT IN (SELECT revenue_date FROM warehouse.legacy_reporting.daily_revenue);
