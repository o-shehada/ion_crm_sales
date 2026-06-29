# -*- coding: utf-8 -*-
"""
Document-event hooks that auto-recalculate commission sheets when
Sales Invoices or Payment Entries are submitted/updated.
"""

import frappe
from frappe.utils import flt, getdate

from .helpers import quarter_of_date


def _touch_related_sheets(doc, method=None):
    """
    Triggered from Sales Invoice / Payment Entry events.
    Finds sheets for the same company, FY, quarter, department, and affected
    sales people, then calls the API to recalc.
    """
    from .api import recalculate_sheet  # import here to avoid circulars

    for candidate in _affected_sheet_candidates(doc):
        try:
            recalculate_sheet(name=candidate["name"])
        except Exception:
            frappe.log_error(
                f"ion_crm_sales: failed to auto-recalculate sheet {candidate['name']}",
                "Commission Trigger",
            )


def _affected_sheet_candidates(doc):
    candidates = {}
    for invoice_name, paid_on in _affected_paid_invoices(doc):
        invoice = frappe.get_doc("Sales Invoice", invoice_name)
        affected = _affected_people_by_department(invoice, paid_on)
        if not affected:
            continue

        fiscal_year = _fiscal_year_for_date(paid_on)
        if not fiscal_year:
            continue

        quarter = quarter_of_date(paid_on, fiscal_year)
        for department, people in affected.items():
            for sheet in _sheets_for_people(
                invoice.company,
                fiscal_year,
                quarter,
                department,
                people,
            ):
                candidates[sheet.name] = sheet

    return candidates.values()


def _affected_paid_invoices(doc):
    if doc.doctype == "Sales Invoice":
        paid_on = _fully_paid_on(doc.name)
        return [(doc.name, paid_on)] if paid_on else []

    if doc.doctype != "Payment Entry":
        return []

    paid = []
    for row in doc.get("references") or []:
        if row.get("reference_doctype") != "Sales Invoice" or not row.get("reference_name"):
            continue
        paid_on = _fully_paid_on(row.reference_name)
        if paid_on:
            paid.append((row.reference_name, paid_on))
    return paid


def _fully_paid_on(invoice_name):
    from .helpers import get_invoice_fully_paid_on

    return get_invoice_fully_paid_on(invoice_name)


def _fiscal_year_for_date(posting_date):
    posting_date = getdate(posting_date)
    return frappe.db.get_value(
        "Fiscal Year",
        {"year_start_date": ("<=", posting_date), "year_end_date": (">=", posting_date)},
        "name",
    )


def _affected_people_by_department(si, paid_on):
    out = {}
    sales_people = _affected_sales_people(si)
    if sales_people:
        out["Sales"] = sales_people

    ba_people = _affected_ba_people(si, paid_on)
    if ba_people:
        out["Business Accounts"] = ba_people
    return out


def _affected_sales_people(si):
    from .compute import _managers_on_si, _rest_on_si, _sales_category_amounts_for_si

    if not _sales_category_amounts_for_si(si):
        return set()

    return set(_managers_on_si(si)) | set(_rest_on_si(si))


def _affected_ba_people(si, paid_on):
    from .ba import (
        _ams_on_si,
        _ba_recipients_for_category,
        _category_amounts_for_si,
        _employees_on_si,
        _non_am_sm_employees_on_si,
        _penalty_factor_for_si,
        _skip_ba_commission,
        detect_tx_type,
    )

    if _skip_ba_commission(si):
        return set()

    people = set()
    cat_amounts = _category_amounts_for_si(si)
    if not cat_amounts:
        return people

    externals_ok = bool(
        si.get("custom_external_rep_approved") or getattr(si, "external_rep_approved", None)
    )
    for cat_key, amount in cat_amounts.items():
        if flt(amount) <= 0:
            continue
        people.update(_ba_recipients_for_category(si, cat_key, externals_ok))

    tx_type = detect_tx_type(si, paid_on, is_renewal_flag=False)
    if tx_type == "NewLead" and (
        si.get("custom_first_year_contract_invoice")
        or getattr(si, "first_year_contract_invoice", None)
    ):
        people.update(_non_am_sm_employees_on_si(si))

    if tx_type == "NewLead" and (
        si.get("custom_ba_project_acquisition_bonus")
        or getattr(si, "ba_project_acquisition_bonus", None)
    ):
        if flt(cat_amounts.get("HOTSPOT")) > 0 or flt(cat_amounts.get("ULTRA_MALLS")) > 0:
            people.update(_employees_on_si(si))

    if _penalty_factor_for_si(si, paid_on) < 1.0:
        people.update(_ams_on_si(si))

    return people


def _sheets_for_people(company, fiscal_year, quarter, department, people):
    if not people:
        return []

    people = tuple(people)
    placeholders = ", ".join(["%s"] * len(people))
    params = [company, fiscal_year, quarter, department, *people]
    return frappe.db.sql(
        f"""
        SELECT DISTINCT sheet.name
        FROM `tabSales Target and Commission Sheet` sheet
        JOIN `tabCommission Lines` line
            ON line.parent = sheet.name
            AND line.parenttype = 'Sales Target and Commission Sheet'
            AND line.parentfield = 'commission_lines'
        WHERE
            sheet.company = %s
            AND sheet.fiscal_year = %s
            AND sheet.quarter = %s
            AND sheet.status IN ('Draft', 'Submitted', 'Approved')
            AND line.department = %s
            AND line.sales_person IN ({placeholders})
        """,
        params,
        as_dict=True,
    )
