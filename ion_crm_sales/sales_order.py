import frappe
from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice as erpnext_make_sales_invoice

from ion_crm_sales.ion_crm_sales.doc_events.sales_invoice_handlers import (
    set_sales_invoice_source_fields,
    validate_sales_order_contract_for_invoice,
)


@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None, ignore_permissions=False):
	validate_sales_order_contract_for_invoice(source_name)
	sales_invoice = erpnext_make_sales_invoice(source_name, target_doc, ignore_permissions)
	set_sales_invoice_source_fields(sales_invoice)
	return sales_invoice
