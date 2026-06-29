# -*- coding: utf-8 -*-
"""
Commission engine for the **Sales** department (Home / Hotspot).

Calculation logic:
  • Base: normal rate on whole amount, split by manager/rest (even split).
  • Above: add-on = full 'above' rate on the over-target slice per person
           (per invoice, in fully-paid order across the quarter).
  • No late-payment penalties in Sales.
"""

import frappe
from frappe.utils import flt
from functools import lru_cache

from .config import SALES_ITEM_GROUPS, SALES_RATES, SALES_SPLITS
from .helpers import (
    get_quarter_window,
    get_fully_paid_invoice_names,
    get_monthly_distribution,
    quarter_target_from_distribution,
    employee_for_sales_person,
)

# --------------------------
# Sales category detection
# --------------------------

def _sales_category_of_item_group(ig: str) -> str | None:
    if ig == SALES_ITEM_GROUPS["HOME"]:
        return "HOME"
    if ig == SALES_ITEM_GROUPS["HOTSPOT"]:
        return "HOTSPOT"
    return None

def _sales_category_amounts_for_si(si) -> dict[str, float]:
    out = {}
    for it in (si.get("items") or []):
        ig = si.get("custom_service_category")
        amt = flt(it.get("base_amount") or 0)
        cat = _sales_category_of_item_group(ig)
        if not cat:
            continue
        out[cat] = out.get(cat, 0.0) + amt
    return out

# --------------------------
# Manager / rest on invoice
# --------------------------

@lru_cache(maxsize=1024)
def _is_sales_manager(sp: str) -> bool:
    # Prefer custom_ field; fallback to legacy if it exists
    val = frappe.db.get_value("Sales Person", sp, "custom_is_sales_manager")
    if val is None:
        val = frappe.db.get_value("Sales Person", sp, "is_sales_manager")
    return bool(val)

def _managers_on_si(si) -> list[str]:
    out = []
    for st in (si.get("sales_team") or []):
        sp = st.get("sales_person")
        if sp and _is_sales_manager(sp):
            out.append(sp)
    return out

def _rest_on_si(si) -> list[str]:
    out = []
    for st in (si.get("sales_team") or []):
        sp = st.get("sales_person")
        if not sp:
            continue
        if not _is_sales_manager(sp):
            emp = employee_for_sales_person(sp)
            if emp:
                out.append(sp)
    return out

# --------------------------
# Compute (Sales engine)
# --------------------------

def compute_totals_quarterly(sheet):
    """
    Main Sales engine entry point.

    Iterates invoices in fully-paid order, applies base + above-target
    commission, and writes the results into the sheet's commission lines.
    """
    get_monthly_distribution.cache_clear()
    _is_sales_manager.cache_clear()
    employee_for_sales_person.cache_clear()

    q_start, q_end, months3 = get_quarter_window(sheet.fiscal_year, sheet.quarter)

    # Sales lines (people) & their quarter targets
    people = [
        ln.sales_person
        for ln in (sheet.get("commission_lines") or [])
        if ln.department == "Sales"
    ]
    if not people:
        return

    target = {
        sp: quarter_target_from_distribution(sp, sheet.fiscal_year, months3)
        for sp in people
    }

    # Candidate invoices sorted by fully-paid date
    cand_sorted = get_fully_paid_invoice_names(
        sheet.company,
        q_start,
        q_end,
        tuple(SALES_ITEM_GROUPS.values()),
    )

    # Running exposure (amount) per person to compute over-target slices
    cum_exposure = {sp: 0.0 for sp in people}
    # Outputs
    per_person   = {sp: 0.0 for sp in people}
    actual_basis = {sp: 0.0 for sp in people}

    for po, si_name in cand_sorted:
        si = frappe.get_doc("Sales Invoice", si_name)
        cat_amounts = _sales_category_amounts_for_si(si)
        mgrs = _managers_on_si(si)
        rest = _rest_on_si(si)

        for cat, amount in cat_amounts.items():
            rates  = SALES_RATES[cat]
            splits = SALES_SPLITS[cat]

            # Base commission (normal rate) split manager/rest
            base_mgr_comm  = amount * rates["normal"] * splits["normal"]["manager"]
            base_rest_comm = amount * rates["normal"] * splits["normal"]["rest"]

            if mgrs:
                eq = base_mgr_comm / len(mgrs)
                for sp in mgrs:
                    if sp in per_person:
                        per_person[sp] += eq
            else:
                # reallocate manager base to rest
                if rest:
                    eq = base_mgr_comm / len(rest)
                    for sp in rest:
                        if sp in per_person:
                            per_person[sp] += eq

            if rest:
                eq = base_rest_comm / len(rest)
                for sp in rest:
                    if sp in per_person:
                        per_person[sp] += eq

            # Exposure slices (amount), used for Above add-on.
            # Base/actual sales use normal split; above-target uses the
            # category's above split, e.g. Hotspot manager/rest = 20/80.
            if mgrs:
                eq_mgr_actual = amount * splits["normal"]["manager"] / len(mgrs)
                eq_mgr_above = amount * splits["above"]["manager"] / len(mgrs)
                for sp in mgrs:
                    if sp not in actual_basis:
                        continue
                    actual_basis[sp] += eq_mgr_actual
                    tgt  = target.get(sp, 0.0) or 0.0
                    prev = cum_exposure.get(sp, 0.0) or 0.0
                    above_part = max(0.0, (prev + eq_mgr_above) - tgt) - max(0.0, prev - tgt)
                    if above_part > 0:
                        per_person[sp] += above_part * rates["above"]
                    cum_exposure[sp] = prev + eq_mgr_above
            else:
                # if no managers, manager exposure realloc to rest too
                if rest:
                    eq_actual = amount * splits["normal"]["manager"] / len(rest)
                    eq_above = amount * splits["above"]["manager"] / len(rest)
                    for sp in rest:
                        if sp in actual_basis:
                            actual_basis[sp] += eq_actual
                        tgt  = target.get(sp, 0.0) or 0.0
                        prev = cum_exposure.get(sp, 0.0) or 0.0
                        above_part = max(0.0, (prev + eq_above) - tgt) - max(0.0, prev - tgt)
                        if above_part > 0:
                            per_person[sp] += above_part * rates["above"]
                        cum_exposure[sp] = prev + eq_above

            # Rest exposure share
            if rest:
                eq_rest_actual = amount * splits["normal"]["rest"] / len(rest)
                eq_rest_above = amount * splits["above"]["rest"] / len(rest)
                for sp in rest:
                    if sp in actual_basis:
                        actual_basis[sp] += eq_rest_actual
                    tgt  = target.get(sp, 0.0) or 0.0
                    prev = cum_exposure.get(sp, 0.0) or 0.0
                    above_part = max(0.0, (prev + eq_rest_above) - tgt) - max(0.0, prev - tgt)
                    if above_part > 0:
                        per_person[sp] += above_part * rates["above"]
                    cum_exposure[sp] = prev + eq_rest_above

    # Update Sales lines on the sheet
    total_target = total_actual = total_commission = 0.0
    for ln in (sheet.get("commission_lines") or []):
        if ln.department != "Sales":
            continue
        ln.target_value = flt(target.get(ln.sales_person) or 0.0)
        ln.actual_sales = flt(actual_basis.get(ln.sales_person) or 0.0)
        ln.achievement_pct = (
            round((ln.actual_sales / ln.target_value * 100.0), 2) if ln.target_value else 0.0
        )
        ln.commission_value = flt(per_person.get(ln.sales_person) or 0.0)
        ln.commission_rate = (
            round((ln.commission_value / ln.actual_sales * 100.0), 2)
            if ln.actual_sales
            else 0.0
        )

        total_target     += flt(ln.target_value)
        total_actual     += flt(ln.actual_sales)
        total_commission += flt(ln.commission_value)

    sheet.total_target = round(total_target, 2)
    sheet.total_actual_sales = round(total_actual, 2)
    sheet.total_commission = round(total_commission, 2)
