# -*- coding: utf-8 -*-
"""
Shared helpers for the commission engines (Sales + BA).

These were previously duplicated across compute.py and ba.py.
"""

import frappe
from frappe.utils import flt, getdate
from datetime import date, timedelta
from calendar import monthrange
from functools import lru_cache


# ────────────────────────────────────
# Date arithmetic
# ────────────────────────────────────

def add_months(d: date, m: int) -> date:
    """Shift *d* forward by *m* calendar months, clamping the day."""
    y = d.year + (d.month - 1 + m) // 12
    m2 = (d.month - 1 + m) % 12 + 1
    day = min(d.day, monthrange(y, m2)[1])
    return date(y, m2, day)


# ────────────────────────────────────
# Fiscal-year quarter window
# ────────────────────────────────────

def get_quarter_window(fiscal_year: str, quarter: str) -> tuple[date, date, list[int]]:
    """
    Return (q_start, q_end, [month_numbers]) for the requested quarter
    within the given Fiscal Year.
    """
    fy = frappe.get_doc("Fiscal Year", fiscal_year)
    off = {"Q1": 0, "Q2": 3, "Q3": 6, "Q4": 9}[quarter]
    q_start = add_months(fy.year_start_date, off)
    q_end = add_months(q_start, 3) - timedelta(days=1)
    months: list[int] = []
    m = q_start.month
    y = q_start.year
    for _ in range(3):
        months.append(m)
        m += 1
        if m > 12:
            m = 1
            y += 1
    return q_start, q_end, months


def quarter_of_date(d, fy_name: str) -> str:
    """Return 'Q1'..'Q4' for date *d* within Fiscal Year *fy_name*."""
    d = getdate(d)
    fy = frappe.get_doc("Fiscal Year", fy_name)
    ysd = fy.year_start_date
    bounds = [
        (ysd, add_months(ysd, 3) - timedelta(days=1), "Q1"),
        (add_months(ysd, 3), add_months(ysd, 6) - timedelta(days=1), "Q2"),
        (add_months(ysd, 6), add_months(ysd, 9) - timedelta(days=1), "Q3"),
        (add_months(ysd, 9), add_months(ysd, 12) - timedelta(days=1), "Q4"),
    ]
    for start, end, label in bounds:
        if start <= d <= end:
            return label
    return "Q1"


# ────────────────────────────────────
# Quarter field normaliser
# ────────────────────────────────────

def ensure_quarter_on(doc) -> str:
    """
    Read 'custom_quarter' or 'quarter' from *doc*, validate it, and
    write it back to ``doc.quarter`` so every engine sees the same field.

    Returns the quarter string ('Q1'..'Q4').
    """
    q = getattr(doc, "custom_quarter", None) or getattr(doc, "quarter", None)
    if not q:
        frappe.throw("Please set Quarter (Q1/Q2/Q3/Q4) on the sheet.")
    if getattr(doc, "quarter", None) != q:
        setattr(doc, "quarter", q)
    return q


# ────────────────────────────────────
# Fully-paid date (single invoice)
# ────────────────────────────────────

def get_invoice_fully_paid_on(si_name: str):
    """
    Return the date when *si_name* became fully paid, or ``None``
    if it still has an outstanding balance.

    Uses a single SQL query instead of loading the full document.
    """
    si = frappe.db.get_value(
        "Sales Invoice", si_name,
        ["outstanding_amount", "modified"],
        as_dict=True,
    )
    if not si or flt(si.outstanding_amount):
        return None
    paid = frappe.db.sql(
        """
        SELECT MAX(pe.posting_date)
        FROM `tabPayment Entry Reference` per
        JOIN `tabPayment Entry` pe ON pe.name = per.parent
        WHERE
            per.reference_doctype = 'Sales Invoice'
            AND per.reference_name = %s
            AND pe.docstatus = 1
        """,
        (si_name,),
    )[0][0]
    return getdate(paid) if paid else getdate(si.modified)


# ────────────────────────────────────
# Batch: fully-paid invoices in a quarter
# ────────────────────────────────────

_FULLY_PAID_SQL = """
    SELECT paid.name, paid.customer, paid.posting_date,
           paid.custom_service_category,
           paid.outstanding_amount, paid.paid_on
    FROM (
        SELECT
                si.name,
                si.customer,
                si.posting_date,
                si.custom_service_category,
                si.outstanding_amount,
            COALESCE(pe_refs.paid_on, DATE(si.modified)) AS paid_on
        FROM `tabSales Invoice` si
        LEFT JOIN (
            SELECT
                per.reference_name,
                MAX(pe.posting_date) AS paid_on
            FROM `tabPayment Entry Reference` per
            JOIN `tabPayment Entry` pe ON pe.name = per.parent
            WHERE
                per.reference_doctype = 'Sales Invoice'
                AND pe.docstatus = 1
            GROUP BY per.reference_name
        ) pe_refs ON pe_refs.reference_name = si.name
        WHERE
            si.company = %s
            AND si.docstatus = 1
            AND si.outstanding_amount = 0
            AND si.posting_date <= %s
    ) paid
    WHERE paid.paid_on BETWEEN %s AND %s
    ORDER BY paid.paid_on, paid.name
"""


def get_fully_paid_invoice_refs(
    company: str, q_start: date, q_end: date, service_categories: tuple[str, ...] | None = None,
) -> list[tuple[date, dict]]:
    """
    Return ``[(paid_on, {name, customer, posting_date, …}), …]`` for all
    submitted invoices fully paid inside the quarter.

    Used by the **BA** engine which needs the customer column.
    """
    query = _FULLY_PAID_SQL
    params: list = [company, q_end, q_start, q_end]
    if service_categories:
        placeholders = ", ".join(["%s"] * len(service_categories))
        query = query.replace(
            "ORDER BY paid.paid_on, paid.name",
            f"AND paid.custom_service_category IN ({placeholders})\n    ORDER BY paid.paid_on, paid.name",
        )
        params.extend(service_categories)
    rows = frappe.db.sql(query, params, as_dict=True)
    return [(getdate(r.paid_on), r) for r in rows]


def get_fully_paid_invoice_names(
    company: str, q_start: date, q_end: date, service_categories: tuple[str, ...] | None = None,
) -> list[tuple[date, str]]:
    """
    Return ``[(paid_on, si_name), …]`` — lighter variant used by the
    **Sales** engine which only needs the invoice name.
    """
    rows = get_fully_paid_invoice_refs(company, q_start, q_end, service_categories)
    return [(paid_on, r.name) for paid_on, r in rows]


# ────────────────────────────────────
# Monthly Distribution reader
# ────────────────────────────────────

_MONTH_MAP = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

_EVEN_SPLIT = {i: 1.0 / 12.0 for i in range(1, 13)}


@lru_cache(maxsize=256)
def get_monthly_distribution(md_name: str) -> dict[int, float]:
    """
    Return ``{1..12: fraction}`` for a Monthly Distribution.

    Supports:
      A) child rows (Monthly Distribution Percentage)
      B) legacy parent columns ``jan``..``dec``

    Normalises to fractions that sum ≈ 1.0; falls back to an even
    1/12 split when the record is missing or empty.
    """
    try:
        md = frappe.get_doc("Monthly Distribution", md_name)
    except Exception:
        return dict(_EVEN_SPLIT)

    # --- Shape A: child table ---
    try:
        meta = frappe.get_meta("Monthly Distribution")
        child_fieldname = None
        for f in meta.fields:
            if getattr(f, "fieldtype", "") == "Table" and f.options:
                if f.options == "Monthly Distribution Percentage":
                    child_fieldname = f.fieldname
                    break
                if not child_fieldname:
                    child_fieldname = f.fieldname

        rows = md.get(child_fieldname) if child_fieldname else None
        if rows:
            out = {i: 0.0 for i in range(1, 13)}
            total = 0.0
            for r in rows:
                m_val = (
                    r.get("month") or r.get("month_name") or r.get("month_no") or ""
                ).strip()
                p_val = r.get("percentage")
                if p_val is None:
                    p_val = r.get("percentage_allocation")
                try:
                    m_num = int(m_val)
                except (ValueError, TypeError):
                    m_num = _MONTH_MAP.get(str(m_val).lower())
                p = flt(p_val or 0)
                if m_num in out:
                    out[m_num] += p
                    total += p

            if total > 0:
                if abs(total - 100.0) < 1e-6:
                    return {m: out[m] / 100.0 for m in out}
                if 0.999 <= total <= 1.001:
                    return out
                return {m: out[m] / total for m in out}
            return dict(_EVEN_SPLIT)
    except Exception:
        pass

    # --- Shape B: legacy parent columns ---
    try:
        values = {
            1: flt(getattr(md, "jan", 0) or 0),
            2: flt(getattr(md, "feb", 0) or 0),
            3: flt(getattr(md, "mar", 0) or 0),
            4: flt(getattr(md, "apr", 0) or 0),
            5: flt(getattr(md, "may", 0) or 0),
            6: flt(getattr(md, "jun", 0) or 0),
            7: flt(getattr(md, "jul", 0) or 0),
            8: flt(getattr(md, "aug", 0) or 0),
            9: flt(getattr(md, "sep", 0) or 0),
            10: flt(getattr(md, "oct", 0) or 0),
            11: flt(getattr(md, "nov", 0) or 0),
            12: flt(getattr(md, "dec", 0) or 0),
        }
        total = sum(values.values())
        if total > 0:
            if abs(total - 100.0) < 1e-6:
                return {m: values[m] / 100.0 for m in values}
            if 0.999 <= total <= 1.001:
                return values
            return {m: values[m] / total for m in values}
    except Exception:
        pass

    return dict(_EVEN_SPLIT)


# ────────────────────────────────────
# Quarter target from Target Detail
# ────────────────────────────────────

def quarter_target_from_distribution(
    sales_person: str, fiscal_year: str, months3: list[int],
) -> float:
    """
    Sum the quarterly share of every Target Detail row on the
    Sales Person record, weighted by Monthly Distribution.
    """
    rows = frappe.get_all(
        "Target Detail",
        filters={
            "parenttype": "Sales Person",
            "parent": sales_person,
            "fiscal_year": fiscal_year,
        },
        fields=["target_amount", "distribution_id"],
    )
    if not rows:
        return 0.0

    total = 0.0
    for r in rows:
        amt = flt(r.get("target_amount") or 0)
        if not amt:
            continue
        md_name = r.get("distribution_id")
        if md_name:
            dist = get_monthly_distribution(md_name)
            share = sum(dist.get(m, 0) for m in months3)
            total += amt * share
        else:
            total += amt * (3.0 / 12.0)
    return round(total, 2)


# ────────────────────────────────────
# Employee / User lookups (cached)
# ────────────────────────────────────

@lru_cache(maxsize=1024)
def employee_for_sales_person(sales_person: str):
    """Return the Employee linked to a Sales Person, or None."""
    return frappe.db.get_value("Sales Person", sales_person, "employee")


@lru_cache(maxsize=1024)
def user_for_employee(employee: str):
    """Return the User ID linked to an Employee, or None."""
    return frappe.db.get_value("Employee", employee, "user_id")


@lru_cache(maxsize=1024)
def department_for_employee(employee: str):
    """Return the Department of an Employee, or None."""
    return frappe.db.get_value("Employee", employee, "department")
