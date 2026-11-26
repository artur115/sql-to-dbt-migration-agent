# Migration scorecard: baseline translator

17 of 24 jobs accepted, 0 rejected for mismatch, 7 sent to a person.

| Job | Owner | Complexity | Status | Attempts | Why |
|---|---|---|---|---:|---|
| daily_revenue | finance-analytics | simple | accepted | 1 | parallel run matches |
| dim_customers | crm-analytics | simple | accepted | 1 | parallel run matches |
| dim_products | merchandising | simple | accepted | 1 | parallel run matches |
| promo_usage | growth | simple | accepted | 1 | parallel run matches |
| refunds_daily | finance-analytics | simple | accepted | 1 | parallel run matches |
| returns_by_reason | ops-analytics | simple | accepted | 1 | parallel run matches |
| sessions_by_source | growth | simple | accepted | 1 | parallel run matches |
| stg_orders_clean | data-platform | simple | accepted | 1 | parallel run matches |
| aov_by_segment | finance-analytics | medium | accepted | 1 | parallel run matches |
| category_monthly_sales | merchandising | medium | accepted | 1 | parallel run matches |
| channel_mix | growth | medium | accepted | 1 | parallel run matches |
| customer_orders_summary | crm-analytics | medium | accepted | 1 | parallel run matches |
| order_totals | finance-analytics | medium | accepted | 1 | parallel run matches |
| repeat_purchase_rate | crm-analytics | medium | accepted | 1 | parallel run matches |
| return_rate_by_category | ops-analytics | medium | accepted | 1 | parallel run matches |
| top_products_by_region | merchandising | medium | accepted | 1 | parallel run matches |
| customer_status | crm-analytics | hard | needs_human | 1 | rule-based translator can't express it: UPDATE statement changes the table after it is created |
| ltv_bands | crm-analytics | hard | needs_human | 1 | rule-based translator can't express it: UPDATE statement changes the table after it is created |
| marketing_audience | growth | hard | needs_human | 1 | rule-based translator can't express it: DELETE statement changes the table after it is created |
| open_orders_snapshot | ops-analytics | hard | needs_human | 0 | output depends on when it runs (current_date); agree a fixed as-of date or seed with the owner |
| qa_sample_orders | data-platform | hard | needs_human | 0 | output depends on when it runs (random); agree a fixed as-of date or seed with the owner |
| revenue_reconciliation | finance-analytics | hard | needs_human | 1 | rule-based translator can't express it: INSERT statement changes the table after it is created |
| session_attribution | growth | hard | accepted | 1 | parallel run matches |
| weekly_kpis | finance-analytics | hard | needs_human | 1 | rule-based translator can't express it: UPDATE statement changes the table after it is created |
