# -*- coding: utf-8 -*-
"""
Public API for commission sheet operations.

Exposed via ``@frappe.whitelist()`` so the client-side JS and
doc-event triggers can call them.
"""

import frappe
from ion_crm_sales.ion_crm_sales.commission.gl import post_accrual
from ion_crm_sales.ion_crm_sales.commission.helpers import ensure_quarter_on
from ion_crm_sales.ion_crm_sales.commission.transactions import sync_sheet_transactions


@frappe.whitelist()
def recalculate_sheet(name: str):
    """Re-run both commission engines and save the sheet."""
    doc = frappe.get_doc("Sales Target and Commission Sheet", name)
    if doc.docstatus == 2 or doc.status == "Posted":
        frappe.throw("Recalculation is not allowed on Cancelled or Posted sheets.")

    ensure_quarter_on(doc)
    sync_sheet_transactions(doc)

    doc.save()
    return {"message": "Recalculated."}


@frappe.whitelist()
def post_sheet_accrual(name: str):
    """Recalculate, then post the accrual Journal Entry."""
    doc = frappe.get_doc("Sales Target and Commission Sheet", name)
    if doc.docstatus != 1 or doc.status != "Approved":
        frappe.throw("Only Approved & Submitted sheets can be posted.")

    ensure_quarter_on(doc)
    sync_sheet_transactions(doc)
    doc.save()

    post_accrual(doc)
    doc.status = "Posted"
    doc.save()
    return {"message": f"Accrual posted: {doc.accrual_je}"}
