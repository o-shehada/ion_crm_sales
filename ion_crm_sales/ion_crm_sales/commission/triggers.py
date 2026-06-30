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
    Rebuilds the ledger only when the event affects a paid invoice or an
    existing commission transaction. Invoice history is refreshed separately.
    """
    from .api import recalculate_sheet  # import here to avoid circulars

    sheet_names = {
        candidate["name"] for candidate in _affected_sheet_candidates(doc)
    }
    sheet_names.update(_transaction_sheet_names_for_event(doc))
    for sheet_name in sheet_names:
        try:
            recalculate_sheet(name=sheet_name)
        except Exception:
            frappe.log_error(
                f"ion_crm_sales: failed to auto-recalculate sheet {sheet_name}",
                "Commission Trigger",
            )

    _refresh_invoice_histories_for_event(doc)


def _transaction_sheet_names_for_event(doc):
    """Return sheets with active ledger entries for the event's invoices.

    This keeps cancellation/reversal events correct after an invoice is no
    longer fully paid, without rebuilding sheets for ordinary unpaid invoices.
    """
    invoice_names = _invoice_names_for_event(doc)
    if not invoice_names:
        return set()

    return set(
        frappe.get_all(
            "Commission Transaction",
            filters={
                "sales_invoice": ("in", tuple(invoice_names)),
                "transaction_status": ("in", ("Draft", "Posted")),
            },
            pluck="sales_target_and_commission_sheet",
        )
    ) - {None}


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
        for _department, people in affected.items():
            for sheet in _sheets_for_people(
                invoice.company,
                fiscal_year,
                quarter,
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


def _sheets_for_people(company, fiscal_year, quarter, people):
    if not people:
        return []

    people = tuple(people)
    placeholders = ", ".join(["%s"] * len(people))
    params = [company, fiscal_year, quarter, *people]
    return frappe.db.sql(
        f"""
        SELECT DISTINCT sheet.name
        FROM `tabSales Target and Commission Sheet` sheet
        WHERE
            sheet.company = %s
            AND sheet.fiscal_year = %s
            AND sheet.quarter = %s
            AND sheet.status IN ('Draft', 'Submitted', 'Approved')
            AND sheet.sales_person IN ({placeholders})
        """,
        params,
        as_dict=True,
    )


def create_person_sheets_for_invoice(doc, method=None):
    """Create one posting-quarter commission sheet per Sales Team person."""
    if doc.docstatus != 1:
        return

    fiscal_year = _fiscal_year_for_date(doc.posting_date)
    if not fiscal_year:
        frappe.throw(f"No Fiscal Year contains Sales Invoice date {doc.posting_date}.")
    quarter = quarter_of_date(doc.posting_date, fiscal_year)
    sales_people = []
    for row in doc.get("sales_team") or []:
        sales_person = row.get("sales_person")
        if sales_person and sales_person not in sales_people:
            sales_people.append(sales_person)

    for sales_person in sales_people:
        sheet_name = frappe.db.get_value(
            "Sales Target and Commission Sheet",
            {
                "company": doc.company,
                "fiscal_year": fiscal_year,
                "quarter": quarter,
                "sales_person": sales_person,
                "docstatus": ("<", 2),
            },
            "name",
        )
        if sheet_name:
            sheet = frappe.get_doc("Sales Target and Commission Sheet", sheet_name)
            sync_invoice_history(sheet)
            _persist_invoice_history(sheet)
            continue

        frappe.get_doc(
            {
                "doctype": "Sales Target and Commission Sheet",
                "company": doc.company,
                "fiscal_year": fiscal_year,
                "quarter": quarter,
                "sales_person": sales_person,
            }
        ).insert(ignore_permissions=True)


def sync_invoice_history(sheet):
    """Populate a per-person posting-quarter Sales Invoice history snapshot."""
    sales_person = sheet.get("sales_person")
    if not sales_person or not sheet.meta.has_field("invoice_history"):
        return

    from .helpers import get_quarter_window

    q_start, q_end, _months = get_quarter_window(sheet.fiscal_year, sheet.quarter)
    invoice_names = frappe.db.sql_list(
        """
        SELECT DISTINCT si.name
        FROM `tabSales Invoice` si
        JOIN `tabSales Team` team
          ON team.parent = si.name
         AND team.parenttype = 'Sales Invoice'
         AND team.parentfield = 'sales_team'
        WHERE si.company = %s
          AND si.docstatus = 1
          AND si.posting_date BETWEEN %s AND %s
          AND team.sales_person = %s
        ORDER BY si.posting_date, si.name
        """,
        (sheet.company, q_start, q_end, sales_person),
    )

    sheet.set("invoice_history", [])
    total_paid_commission = 0.0
    total_unpaid_commission = 0.0
    total_paid_invoice_amount = 0.0
    total_unpaid_invoice_amount = 0.0
    for invoice_name in invoice_names:
        invoice = frappe.get_doc("Sales Invoice", invoice_name)
        paid = abs(flt(invoice.outstanding_amount)) < 0.000001
        invoice_amount = flt(invoice.base_grand_total)
        actual = _actual_commission_for_invoice(sheet.name, invoice_name, sales_person)
        if paid and actual.count:
            commission_amount = flt(actual.commission_amount)
            commission_rate = (
                commission_amount / flt(actual.basis_amount) * 100.0
                if flt(actual.basis_amount)
                else 0.0
            )
        else:
            commission_rate = _estimated_commission_rate(invoice, sales_person)
            basis = flt(invoice.base_net_total or invoice.base_grand_total)
            commission_amount = basis * commission_rate / 100.0

        sheet.append(
            "invoice_history",
            {
                "sales_invoice": invoice.name,
                "custom_ba_transaction_type": invoice.get("custom_ba_transaction_type"),
                "service_category": invoice.get("custom_service_category"),
                "invoice_amount": round(invoice_amount, 2),
                "commission_rate": round(commission_rate, 6),
                "commission_amount": round(commission_amount, 2),
                "invoice_status": "Paid" if paid else "Unpaid",
            },
        )
        if paid:
            total_paid_commission += commission_amount
            total_paid_invoice_amount += invoice_amount
        else:
            total_unpaid_commission += commission_amount
            total_unpaid_invoice_amount += invoice_amount

    sheet.total_paid_invoices = round(total_paid_commission, 2)
    sheet.total_unpaid_invoices = round(total_unpaid_commission, 2)
    sheet.total_paid_invoice_amount = round(total_paid_invoice_amount, 2)
    sheet.total_unpaid_invoice_amount = round(total_unpaid_invoice_amount, 2)


def _actual_commission_for_invoice(sheet_name, invoice_name, sales_person):
    rows = frappe.db.sql(
        """
        SELECT COUNT(*) AS count,
               COALESCE(SUM(line.commission_amount), 0) AS commission_amount,
               COALESCE(SUM(CASE WHEN line.commission_component = 'Base'
                    THEN line.basis_amount ELSE 0 END), 0) AS basis_amount
        FROM `tabCommission Transaction` tx
        JOIN `tabCommission Transaction Line` line ON line.parent = tx.name
        WHERE tx.sales_target_and_commission_sheet = %s
          AND tx.sales_invoice = %s
          AND tx.transaction_status IN ('Draft', 'Posted')
          AND line.sales_person = %s
        """,
        (sheet_name, invoice_name, sales_person),
        as_dict=True,
    )
    return rows[0]


def _estimated_commission_rate(invoice, sales_person):
    rows = [
        row for row in invoice.get("sales_team") or []
        if row.get("sales_person") == sales_person
    ]
    manual_rate = sum(flt(row.get("custom_manual_commission_percentage")) for row in rows)
    if manual_rate:
        return manual_rate

    from ion_crm_sales.ion_crm_sales.doc_events.sales_team_allocation import (
        get_manual_commission_limit,
    )

    scenario_rate = get_manual_commission_limit(invoice)
    if scenario_rate is not None:
        allocation = sum(flt(row.get("allocated_percentage")) for row in rows)
        return scenario_rate * allocation / 100.0
    return sum(flt(row.get("commission_rate")) for row in rows)


def _history_sheet_names_for_event(doc):
    invoice_names = _invoice_names_for_event(doc)
    if not invoice_names:
        return set()
    return set(
        frappe.get_all(
            "Sales Invoice Commission History",
            filters={"sales_invoice": ("in", tuple(invoice_names))},
            pluck="parent",
        )
    )


def _invoice_names_for_event(doc):
    if doc.doctype == "Sales Invoice":
        return [doc.name]
    if doc.doctype == "Payment Entry":
        return [
            row.reference_name
            for row in doc.get("references") or []
            if row.get("reference_doctype") == "Sales Invoice" and row.get("reference_name")
        ]
    return []


def _refresh_invoice_histories_for_event(doc):
    for sheet_name in _history_sheet_names_for_event(doc):
        sheet = frappe.get_doc("Sales Target and Commission Sheet", sheet_name)
        sync_invoice_history(sheet)
        _persist_invoice_history(sheet)


def _persist_invoice_history(sheet):
    """Persist generated history without changing sheet workflow state."""
    frappe.db.delete(
        "Sales Invoice Commission History",
        {"parent": sheet.name, "parenttype": sheet.doctype, "parentfield": "invoice_history"},
    )
    for index, row in enumerate(sheet.get("invoice_history") or [], 1):
        row.idx = index
        row.parent = sheet.name
        row.parenttype = sheet.doctype
        row.parentfield = "invoice_history"
        row.db_insert()
    frappe.db.set_value(
        sheet.doctype,
        sheet.name,
        {
            "total_paid_invoices": sheet.total_paid_invoices,
            "total_unpaid_invoices": sheet.total_unpaid_invoices,
            "total_paid_invoice_amount": sheet.total_paid_invoice_amount,
            "total_unpaid_invoice_amount": sheet.total_unpaid_invoice_amount,
        },
        update_modified=False,
    )
