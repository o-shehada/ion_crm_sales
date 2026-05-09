# -*- coding: utf-8 -*-
"""
Public API for commission sheet operations.

Exposed via ``@frappe.whitelist()`` so the client-side JS and
doc-event triggers can call them.
"""

import frappe
from frappe.utils import flt
from ion_crm_sales.ion_crm_sales.commission.compute import (
    compute_totals_quarterly as compute_sales_quarterly,
)
from ion_crm_sales.ion_crm_sales.commission.ba import compute_ba_for_sheet
from ion_crm_sales.ion_crm_sales.commission.gl import post_accrual
from ion_crm_sales.ion_crm_sales.commission.helpers import ensure_quarter_on


@frappe.whitelist()
def recalculate_sheet(name: str):
    """Re-run both commission engines and save the sheet."""
    doc = frappe.get_doc("Sales Target and Commission Sheet", name)
    if doc.docstatus == 2 or doc.status == "Posted":
        frappe.throw("Recalculation is not allowed on Cancelled or Posted sheets.")

    ensure_quarter_on(doc)

    # SALES engine
    compute_sales_quarterly(doc)

    # BA engine
    _apply_ba(doc)
    _retotal(doc)

    doc.save()
    return {"message": "Recalculated."}


def _apply_ba(doc):
    """Write BA engine results into the BA commission lines."""
    ba_map, ba_actual_map = compute_ba_for_sheet(doc, include_actuals=True)
    for ln in (doc.get("commission_lines") or []):
        if ln.department == "Business Accounts":
            ln.actual_sales = ba_actual_map.get(ln.sales_person) or 0.0
            ln.achievement_pct = (
                round((ln.actual_sales / ln.target_value * 100.0), 2)
                if ln.target_value
                else 0.0
            )
            ln.commission_value = ba_map.get(ln.sales_person) or 0.0
            ln.commission_rate = (
                round((ln.commission_value / ln.actual_sales * 100.0), 2)
                if ln.actual_sales
                else 0.0
            )


def _retotal(doc):
    total_target = total_actual = total_commission = 0.0
    for ln in (doc.get("commission_lines") or []):
        total_target += flt(ln.target_value)
        total_actual += flt(ln.actual_sales)
        total_commission += flt(ln.commission_value)
    doc.total_target = round(total_target, 2)
    doc.total_actual_sales = round(total_actual, 2)
    doc.total_commission = round(total_commission, 2)


@frappe.whitelist()
def post_sheet_accrual(name: str):
    """Recalculate, then post the accrual Journal Entry."""
    doc = frappe.get_doc("Sales Target and Commission Sheet", name)
    if doc.docstatus != 1 or doc.status != "Approved":
        frappe.throw("Only Approved & Submitted sheets can be posted.")

    ensure_quarter_on(doc)

    # Refresh numbers before posting
    compute_sales_quarterly(doc)
    _apply_ba(doc)
    _retotal(doc)
    doc.save()

    post_accrual(doc)
    doc.status = "Posted"
    doc.save()
    return {"message": f"Accrual posted: {doc.accrual_je}"}
