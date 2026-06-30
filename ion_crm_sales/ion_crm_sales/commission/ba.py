# -*- coding: utf-8 -*-
"""
Commission engine for the **Business Accounts** department.

Handles:
  • Transaction-type detection (New Lead / Upsell / Renewal)
  • Category-specific rates (Dedicated, Hotel, ISPs, Hotspot-BA, Ultra-Malls)
  • ION Solutions role-based rates
  • Sales-team allocation percentages
  • First-year contract add-on (+1%)
  • Project acquisition bonus (+3 000)
  • Late-payment penalties (AM only)
"""

import frappe
from frappe.utils import flt, getdate
from datetime import date
from functools import lru_cache

from .config import (
    BA_ITEM_GROUPS, BA_RATES, ION_ROLE_RATES, ION_ABOVE_ADDON,
    FIRST_YEAR_ADDON_RATE, PROJECT_ACQ_BONUS, PENALTY_PLANS,
)
from .helpers import (
    get_quarter_window,
    get_fully_paid_invoice_refs,
    get_monthly_distribution,
    quarter_target_from_distribution,
    employee_for_sales_person,
    user_for_employee,
    department_for_employee,
)

# --------------------------
# Category detection (BA)
# --------------------------

def _category_of_item_by_group(ig: str) -> str | None:
    for key, name in BA_ITEM_GROUPS.items():
        if ig == name:
            return key
    return None

def _category_amounts_for_si(si) -> dict[str, float]:
    out = {}
    for it in (si.get("items") or []):
        ig = si.get("custom_service_category")
        amt = flt(it.get("base_amount") or 0)
        cat = _category_of_item_by_group(ig)
        if not cat:
            continue
        out[cat] = out.get(cat, 0.0) + amt
    return out

# -------------------------------------------------
# Transaction type detection (Old / NewLead / Upsell)
# -------------------------------------------------

BA_TRANSACTION_TYPE_FIELDS = (
    "custom_ba_transaction_type",
    "custom_ba_commission_transaction_type",
)

BA_TRANSACTION_TYPE_ALIASES = {
    "old": "Old",
    "old account": "Old",
    "old accounts": "Old",
    "old accounts transactions": "Old",
    "renewal": "Old",
    "renewals": "Old",
    "newlead": "NewLead",
    "new lead": "NewLead",
    "lead acquisition": "NewLead",
    "new accounts lead acquisition": "NewLead",
    "upsell": "Upsell",
    "new accounts transactions": "Upsell",
    "new accounts transactions / upsell": "Upsell",
    "new accounts transactions \\ upsell": "Upsell",
}

@lru_cache(maxsize=4096)
def _customer_has_prior_invoice(customer: str, before_date: date | None = None) -> bool:
    filters = {"customer": customer, "docstatus": 1}
    if before_date:
        filters["posting_date"] = ("<", before_date)
    return bool(frappe.db.exists("Sales Invoice", filters))

@lru_cache(maxsize=4096)
def _customer_has_prior_fully_paid(customer: str, before_paid_on: date | None = None) -> bool:
    """True if any SI for this customer is fully paid strictly before before_paid_on."""
    if not before_paid_on:
        return False
    rows = frappe.db.sql(
        """
        SELECT prior.name
        FROM (
            SELECT
                si.name,
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
                si.customer = %s
                AND si.docstatus = 1
                AND si.outstanding_amount = 0
        ) prior
        WHERE prior.paid_on < %s
        LIMIT 1
        """,
        (customer, before_paid_on),
    )
    return bool(rows)

def _normalize_ba_transaction_type(value: str | None) -> str | None:
    value = (value or "").strip()
    if not value:
        return None
    return BA_TRANSACTION_TYPE_ALIASES.get(value.lower())


def _get_manual_ba_transaction_type(doc) -> str | None:
    for fieldname in BA_TRANSACTION_TYPE_FIELDS:
        if doc.meta.has_field(fieldname):
            tx_type = _normalize_ba_transaction_type(doc.get(fieldname))
            if tx_type:
                return tx_type
    return None


def _linked_sales_orders_for_si(si) -> list[str]:
    sales_orders = []
    for item in si.get("items") or []:
        sales_order = item.get("sales_order")
        if not sales_order and item.get("prevdoc_doctype") == "Sales Order":
            sales_order = item.get("prevdoc_docname")
        if sales_order and sales_order not in sales_orders:
            sales_orders.append(sales_order)
    return sales_orders


def _explicit_ba_transaction_type(si) -> str | None:
    tx_type = _get_manual_ba_transaction_type(si)
    if tx_type:
        return tx_type

    sales_order_meta = frappe.get_meta("Sales Order")
    if not any(sales_order_meta.has_field(fieldname) for fieldname in BA_TRANSACTION_TYPE_FIELDS):
        return None

    for sales_order in _linked_sales_orders_for_si(si):
        so = frappe.get_doc("Sales Order", sales_order)
        tx_type = _get_manual_ba_transaction_type(so)
        if tx_type:
            return tx_type
    return None


def detect_tx_type(si, fully_paid_on: "date", is_renewal_flag=False) -> str:
    """
    Manual BA Transaction Type wins when available.
    NewLead -> no submitted SI for this customer before this posting_date
               AND no fully-paid SI strictly before this fully_paid_on.
    Old     -> explicit renewal flag, or manual Old/Renewal value.
    Upsell  -> otherwise, when customer has prior history.
    """
    explicit_tx_type = _explicit_ba_transaction_type(si)
    if explicit_tx_type:
        return explicit_tx_type

    if is_renewal_flag:
        return "Old"

    had_prior_by_posting = _customer_has_prior_invoice(si.customer, before_date=si.posting_date)
    had_prior_by_paid    = _customer_has_prior_fully_paid(si.customer, before_paid_on=fully_paid_on)
    if not had_prior_by_posting and not had_prior_by_paid:
        return "NewLead"
    return "Upsell"

# -------------------------------------------
# AM / SM detection via Role Profile
# -------------------------------------------

@lru_cache(maxsize=1024)
def _is_user_role_profile(user: str, code: str) -> bool:
    rp = (frappe.db.get_value("User", user, "role_profile_name") or "").strip().upper()
    return rp == code.upper()

def _salesperson_is_am(sales_person: str) -> bool:
    emp = employee_for_sales_person(sales_person)
    if not emp:
        return False
    user = user_for_employee(emp)
    if not user:
        return False
    return _is_user_role_profile(user, "AM")

def _is_manager_or_sm(sales_person: str) -> bool:
    emp = employee_for_sales_person(sales_person)
    if not emp:
        return False
    user = user_for_employee(emp)
    if not user:
        return False
    rp = (frappe.db.get_value("User", user, "role_profile_name") or "").strip().upper()
    return rp in {"AM", "SM", "SALES MANAGER"}

# -----------------------------------------
# Payment plan & penalties
# -----------------------------------------

def _payment_plan(si) -> str:
    plan = (
        getattr(si, "custom_payment_plan", None)
        or getattr(si, "payment_plan", None)
        or ""
    ).strip().lower()
    return {"yearly": "yearly", "6 months": "6mo", "quarterly": "quarterly"}.get(plan, "yearly")

def _grace_and_cadence_days(plan_key: str) -> tuple[int, int]:
    plan = PENALTY_PLANS.get(plan_key) or PENALTY_PLANS["yearly"]
    return int(plan["grace_days"]), int(plan["cadence_days"])

def _penalty_anchor_date(si):
    """Anchor penalties to SI.due_date (fallback to posting_date)."""
    return getdate(getattr(si, "due_date", None) or si.posting_date)

def _penalty_factor_for_si(si, fully_paid_on: "date") -> float:
    # skip penalty when exception approved
    if getattr(si, "custom_penalty_exception_approved", None) or getattr(si, "penalty_exception_approved", None):
        return 1.0
    plan = _payment_plan(si)
    grace, cadence = _grace_and_cadence_days(plan)
    anchor_date = _penalty_anchor_date(si)
    late_days = (getdate(fully_paid_on) - anchor_date).days
    if late_days <= grace:
        return 1.0
    over = late_days - grace
    blocks = 0 if cadence <= 0 else (over // cadence)
    factor = 1.0 - 0.50 - 0.10 * blocks
    return max(0.0, factor)

# -----------------------
# BA rate lookup helpers
# -----------------------

def _rate_non_ion(cat_key: str, tx_type: str, is_above: bool) -> float:
    if is_above:
        return BA_RATES[cat_key]["above"]
    if tx_type == "Old":
        return BA_RATES[cat_key]["old"]
    if tx_type == "NewLead":
        return BA_RATES[cat_key]["new"] + BA_RATES[cat_key]["upsell"]
    return BA_RATES[cat_key]["upsell"]

def _rate_ion(role: str, is_above: bool) -> float:
    base = ION_ROLE_RATES.get(role, 0.0)
    return base + (ION_ABOVE_ADDON if is_above else 0.0)

# -----------------------
# Helpers for recipients
# -----------------------

def _skip_ba_commission(si) -> bool:
    """Customer-level exclusions (partnership at cost, ISP BW at cost)."""
    cust = frappe.get_doc("Customer", si.customer)
    if getattr(cust, "custom_partnership_at_cost", None) or getattr(cust, "partnership_at_cost", None):
        return True
    if getattr(cust, "custom_isp_bw_partnership", None) or getattr(cust, "isp_bw_partnership", None):
        return True
    return False

def _ba_team_on_si(si, include_externals: bool) -> list[str]:
    out = []
    for st in (si.get("sales_team") or []):
        sp = st.get("sales_person")
        if not sp:
            continue
        emp = employee_for_sales_person(sp)
        dep = department_for_employee(emp) if emp else None
        if dep and "business" not in dep.lower():
            continue
        # externals excluded unless approved
        if not emp and not include_externals:
            continue
        if sp not in out:
            out.append(sp)
    return out

def _ion_role_for_person_on_si(si, sales_person: str) -> str | None:
    for st in (si.get("sales_team") or []):
        if st.get("sales_person") == sales_person:
            role = (st.get("custom_ion_role") or st.get("ion_role") or "").strip()
            return role if role else None
    return None

def _ba_recipients_for_category(si, cat_key: str, externals_ok) -> list[str]:
    if cat_key == "ION_SOLUTIONS":
        holders = []
        for st in (si.get("sales_team") or []):
            role = (st.get("custom_ion_role") or st.get("ion_role") or "").strip()
            if role in ("Account Lead Acquisition", "Offer Team", "Execution Team"):
                holders.append(st.get("sales_person"))
        return holders
    return _ba_team_on_si(si, bool(externals_ok))


def _allocation_fractions_on_si(si, recipients: list[str]) -> dict[str, float]:
    """
    Return normalized allocation fractions for the provided recipients.

    Uses Sales Team.allocated_percentage when available and falls back to an
    even split if no usable allocation exists.
    """
    if not recipients:
        return {}

    raw = {sp: 0.0 for sp in recipients}
    recipient_set = set(recipients)
    for st in (si.get("sales_team") or []):
        sp = st.get("sales_person")
        if sp not in recipient_set:
            continue
        raw[sp] += flt(st.get("allocated_percentage") or 0.0)

    total = sum(raw.values())
    if total <= 0:
        even = 1.0 / len(recipients)
        return {sp: even for sp in recipients}

    return {sp: raw.get(sp, 0.0) / total for sp in recipients}

def _ams_on_si(si) -> list[str]:
    ams = []
    for st in (si.get("sales_team") or []):
        sp = st.get("sales_person")
        if not sp:
            continue
        if _salesperson_is_am(sp):
            ams.append(sp)
    return ams

def _non_am_sm_employees_on_si(si) -> list[str]:
    out = []
    for st in (si.get("sales_team") or []):
        sp = st.get("sales_person")
        if not sp:
            continue
        if not _is_manager_or_sm(sp):
            emp = employee_for_sales_person(sp)
            if emp:
                out.append(sp)
    return out

def _employees_on_si(si) -> list[str]:
    out = []
    for st in (si.get("sales_team") or []):
        sp = st.get("sales_person")
        if not sp:
            continue
        emp = employee_for_sales_person(sp)
        if emp:
            out.append(sp)
    return out

# --------------------------------------
# Main BA computation per sheet quarter
# --------------------------------------

def compute_ba_for_sheet(sheet, include_actuals: bool = False):
    """
    Returns per-person commission map ``{sales_person: amount}`` for the
    Business Accounts department. When ``include_actuals`` is true, returns
    ``(commission_by_person, actual_by_person)``.

    Key behaviors:
      • Even split of category amounts among eligible BA recipients
        (ION = role-holders only).
      • Above = add-on on the over-target slice per person (non-ION);
        ION = role rate + 3 % addon when Above (no over-target slicing).
      • +1 % first-year add-on: split among non AM/SM employees
        (New Lead only).
      • +3 000 acquisition bonus: split among ALL employees
        (Hotspot/Ultra; New Lead only).
      • Penalties (AM only): factor applied to AM commissions per invoice.
    """
    get_monthly_distribution.cache_clear()
    _customer_has_prior_invoice.cache_clear()
    _customer_has_prior_fully_paid.cache_clear()
    _is_user_role_profile.cache_clear()
    employee_for_sales_person.cache_clear()
    user_for_employee.cache_clear()
    department_for_employee.cache_clear()

    q_start, q_end, months3 = get_quarter_window(sheet.fiscal_year, sheet.quarter)

    people = [sheet.sales_person] if sheet.get("sales_person") else []

    # Quarter targets per person
    quarter_target = {
        sp: quarter_target_from_distribution(sp, sheet.fiscal_year, months3)
        for sp in people
    }

    # Sorted by fully-paid date for correct over-target allocation.
    cand_sorted = get_fully_paid_invoice_refs(
        sheet.company,
        q_start,
        q_end,
        tuple(BA_ITEM_GROUPS.values()),
    )

    # Running exposure & results
    cum_exposure = {sp: 0.0 for sp in people}
    commission_by_person = {sp: 0.0 for sp in people}
    actual_by_person = {sp: 0.0 for sp in people}

    for paid_on, inv in cand_sorted:
        si = frappe.get_doc("Sales Invoice", inv["name"])
        if _skip_ba_commission(si):
            continue

        # --- SNAPSHOT exposure BEFORE processing this invoice (for penalty recomputation) ---
        prev_cum_before = dict(cum_exposure)

        tx_type = detect_tx_type(si, paid_on, is_renewal_flag=False)
        cat_amounts = _category_amounts_for_si(si)
        externals_ok = bool(
            si.get("custom_external_rep_approved")
            or getattr(si, "external_rep_approved", None)
        )

        # % commissions with allocation-based split and over-target add-on for non-ION
        for cat_key, amount in cat_amounts.items():
            if amount <= 0:
                continue
            rec = [
                sp
                for sp in _ba_recipients_for_category(si, cat_key, externals_ok)
                if sp in commission_by_person
            ]
            allocs = _allocation_fractions_on_si(si, rec)
            if not allocs:
                continue

            for sp, fraction in allocs.items():
                eq_base = amount * fraction

                actual_by_person[sp] += eq_base

                if cat_key == "ION_SOLUTIONS":
                    role = _ion_role_for_person_on_si(si, sp)
                    if not role:
                        actual_by_person[sp] -= eq_base
                        continue
                    is_above_now = cum_exposure[sp] >= (quarter_target.get(sp) or 0.0)
                    rate = _rate_ion(role, is_above_now)
                    commission_by_person[sp] += eq_base * rate
                    cum_exposure[sp] += eq_base
                else:
                    base_rate  = _rate_non_ion(cat_key, tx_type, False)
                    above_rate = _rate_non_ion(cat_key, tx_type, True)

                    commission_by_person[sp] += eq_base * base_rate

                    tgt      = quarter_target.get(sp, 0.0) or 0.0
                    prev_cum = cum_exposure.get(sp, 0.0) or 0.0
                    above_part = max(0.0, (prev_cum + eq_base) - tgt) - max(0.0, prev_cum - tgt)
                    if above_part > 0:
                        commission_by_person[sp] += above_part * above_rate

                    cum_exposure[sp] = prev_cum + eq_base

        # +1% first-year add-on (non AM/SM only), New Lead only
        is_new_lead_tx = (tx_type == "NewLead")
        if is_new_lead_tx and (
            si.get("custom_first_year_contract_invoice")
            or getattr(si, "first_year_contract_invoice", None)
        ):
            non_mgr = _non_am_sm_employees_on_si(si)
            if non_mgr:
                addon = flt(si.base_grand_total) * FIRST_YEAR_ADDON_RATE
                per   = addon / len(non_mgr)
                for sp in non_mgr:
                    if sp in commission_by_person:
                        commission_by_person[sp] += per

        # +3000 acquisition bonus (Hotspot/Ultra), New Lead only, split among ALL employees
        if is_new_lead_tx and (
            si.get("custom_ba_project_acquisition_bonus")
            or getattr(si, "ba_project_acquisition_bonus", None)
        ):
            has_hs_or_um = (cat_amounts.get("HOTSPOT", 0) > 0) or (cat_amounts.get("ULTRA_MALLS", 0) > 0)
            if has_hs_or_um:
                employees = _employees_on_si(si)
                if employees:
                    per = PROJECT_ACQ_BONUS / len(employees)
                    for sp in employees:
                        if sp in commission_by_person:
                            commission_by_person[sp] += per

        # Penalties (AM only): factor applied to AM % commissions for THIS invoice
        factor = _penalty_factor_for_si(si, paid_on)
        if factor < 1.0:
            ams = _ams_on_si(si)
            if ams:
                # Recompute AM subtotal pre-penalty for this invoice using the SNAPSHOT baseline
                am_subtotal = 0.0
                for cat_key, amount in cat_amounts.items():
                    if amount <= 0:
                        continue
                    rec = [
                        sp
                        for sp in _ba_recipients_for_category(si, cat_key, externals_ok)
                        if sp in ams
                    ]
                    allocs = _allocation_fractions_on_si(si, rec)
                    if not allocs:
                        continue
                    for sp, fraction in allocs.items():
                        eq_base = amount * fraction
                        if cat_key == "ION_SOLUTIONS":
                            role = _ion_role_for_person_on_si(si, sp)
                            if not role:
                                continue
                            is_above_prev = prev_cum_before.get(sp, 0.0) >= (quarter_target.get(sp) or 0.0)
                            rate = _rate_ion(role, is_above_prev)
                            am_subtotal += eq_base * rate
                        else:
                            base_rate  = _rate_non_ion(cat_key, tx_type, False)
                            above_rate = _rate_non_ion(cat_key, tx_type, True)
                            am_subtotal += eq_base * base_rate

                            tgt      = quarter_target.get(sp, 0.0) or 0.0
                            prev_cum = prev_cum_before.get(sp, 0.0) or 0.0
                            above_part = max(0.0, (prev_cum + eq_base) - tgt) - max(0.0, prev_cum - tgt)
                            if above_part > 0:
                                am_subtotal += above_part * above_rate

                reduction = am_subtotal * (1.0 - factor)
                per_am_reduction = reduction / len(ams)
                for sp in ams:
                    commission_by_person[sp] = max(
                        0.0, commission_by_person.get(sp, 0.0) - per_am_reduction,
                    )

    if include_actuals:
        return commission_by_person, actual_by_person
    return commission_by_person
