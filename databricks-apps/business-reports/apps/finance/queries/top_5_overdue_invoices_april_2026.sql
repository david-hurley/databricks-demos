-- name: overdue_invoices
SELECT invoice_id, vendor_id, invoice_date, due_date, amount, status
FROM classic_stable_been2c_catalog.finance_reporting_accounts_payable.invoices
WHERE status = 'overdue'
  AND due_date >= '2026-04-01'
  AND due_date < '2026-05-01'
ORDER BY amount DESC
LIMIT 5
