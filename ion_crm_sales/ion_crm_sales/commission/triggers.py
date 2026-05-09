# -*- coding: utf-8 -*-
"""
Document-event hooks that auto-recalculate commission sheets when
Sales Invoices or Payment Entries are submitted/updated.
"""

import frappe
from frappe.utils import getdate

from .helpers import quarter_of_date


def _touch_related_sheets(doc, method=None):
    """
    Triggered from Sales Invoice / Payment Entry events.
    Finds Sheets for same Company + FY + Quarter and calls the API to recalc.
    """
    from .api import recalculate_sheet  # import here to avoid circulars

    company = getattr(doc, "company", None)
    posting_date = getattr(doc, "posting_date", None)
    if not company or not posting_date:
        return

    posting_date = getdate(posting_date)

    # Resolve fiscal year covering the document date
    fy = frappe.db.get_value(
        "Fiscal Year",
        {"year_start_date": ("<=", posting_date), "year_end_date": (">=", posting_date)},
        "name",
    )
    if not fy:
        return

    quarter = quarter_of_date(posting_date, fy)

    sheets = frappe.get_all(
        "Sales Target and Commission Sheet",
        filters={
            "company": company,
            "fiscal_year": fy,
            "status": ["in", ["Draft", "Submitted", "Approved"]],
        },
        fields=["name", "quarter"],
    )

    for s in sheets:
        if s.get("quarter") != quarter:
            continue
        try:
            recalculate_sheet(name=s["name"])
        except Exception:
            frappe.log_error(
                f"ion_crm_sales: failed to auto-recalculate sheet {s['name']}",
                "Commission Trigger",
            )
