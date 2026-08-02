import frappe
from frappe.utils import cint

from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note as erpnext_make_delivery_note
from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice as erpnext_make_sales_invoice

from ion_crm_sales.ion_crm_sales.doc_events.sales_invoice_handlers import (
    set_sales_invoice_source_fields,
    validate_sales_order_contract_for_invoice,
)
from ion_crm_sales.ion_crm_sales.doc_events.sales_order_serial_batch import (
    carry_serial_batch_to_target,
)


@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None, ignore_permissions=False):
	validate_sales_order_contract_for_invoice(source_name)
	sales_invoice = erpnext_make_sales_invoice(source_name, target_doc, ignore_permissions)
	set_sales_invoice_source_fields(sales_invoice)

	# Serial / Batch Nos only mean something on an invoice that moves stock.
	if cint(sales_invoice.get("update_stock")):
		carry_serial_batch_to_target(source_name, sales_invoice)

	return sales_invoice


@frappe.whitelist()
def make_delivery_note(source_name, target_doc=None, kwargs=None):
	delivery_note = erpnext_make_delivery_note(source_name, target_doc, kwargs)
	carry_serial_batch_to_target(source_name, delivery_note)
	return delivery_note
