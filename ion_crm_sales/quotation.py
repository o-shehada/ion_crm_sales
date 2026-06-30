import frappe
from erpnext.selling.doctype.quotation.quotation import make_sales_order as erpnext_make_sales_order

from ion_crm_sales.ion_crm_sales.doc_events.sales_order_handlers import (
    set_account_manager_sales_team,
    set_sales_order_source_fields,
)


@frappe.whitelist()
def make_sales_order(source_name, target_doc=None):
    sales_order = erpnext_make_sales_order(source_name, target_doc)
    set_sales_order_source_fields(sales_order)
    set_account_manager_sales_team(sales_order)
    return sales_order
