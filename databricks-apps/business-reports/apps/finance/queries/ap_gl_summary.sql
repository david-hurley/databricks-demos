-- name: kpis
SELECT
  ROUND(SUM(CASE WHEN status = 'overdue' THEN amount ELSE 0 END), 2)  AS overdue_total,
  ROUND(SUM(CASE WHEN status = 'open'    THEN amount ELSE 0 END), 2)  AS open_total,
  ROUND(SUM(CASE WHEN status = 'approved' THEN amount ELSE 0 END), 2) AS approved_total,
  ROUND(SUM(CASE WHEN status = 'paid'    THEN amount ELSE 0 END), 2)  AS paid_total,
  COUNT(CASE WHEN status = 'overdue' THEN 1 END) AS overdue_count,
  COUNT(*) AS total_invoices,
  ROUND(AVG(amount), 2) AS avg_invoice_amount
FROM classic_stable_been2c_catalog.finance_reporting_accounts_payable.invoices

-- name: ap_by_status
SELECT
  status,
  COUNT(*)                       AS invoice_count,
  ROUND(SUM(amount), 2)          AS total_amount
FROM classic_stable_been2c_catalog.finance_reporting_accounts_payable.invoices
GROUP BY status
ORDER BY total_amount DESC

-- name: ap_monthly_trend
SELECT
  DATE_FORMAT(invoice_date, 'yyyy-MM')  AS month,
  COUNT(*)                               AS invoice_count,
  ROUND(SUM(amount), 2)                  AS total_amount
FROM classic_stable_been2c_catalog.finance_reporting_accounts_payable.invoices
GROUP BY month
ORDER BY month DESC
LIMIT 12

-- name: gl_monthly_activity
SELECT
  period,
  ROUND(SUM(total_debit), 2)   AS total_activity
FROM classic_stable_been2c_catalog.finance_reporting_general_ledger.monthly_trial_balance
GROUP BY period
ORDER BY period DESC
LIMIT 12

-- name: overdue_invoices
SELECT
  i.invoice_id,
  v.name AS vendor_name,
  i.invoice_date,
  i.due_date,
  ROUND(i.amount, 2)  AS amount,
  DATEDIFF(current_date(), i.due_date) AS days_overdue
FROM classic_stable_been2c_catalog.finance_reporting_accounts_payable.invoices i
JOIN classic_stable_been2c_catalog.finance_reporting_accounts_payable.vendors v
  ON i.vendor_id = v.vendor_id
WHERE i.status = 'overdue'
ORDER BY days_overdue DESC
LIMIT 25
