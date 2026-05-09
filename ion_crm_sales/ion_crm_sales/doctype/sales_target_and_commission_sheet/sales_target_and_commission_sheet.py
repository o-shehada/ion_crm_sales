# -*- coding: utf-8 -*-
"""
Controller for the Sales Target and Commission Sheet doctype.

Orchestrates calls to both the Sales and BA commission engines
during validate, before_submit, and on_update_after_submit.
"""

import frappe
from frappe.model.document import Document
from frappe.utils import flt

from ion_crm_sales.ion_crm_sales.commission.compute import (
    compute_totals_quarterly as compute_sales_quarterly,
)
from ion_crm_sales.ion_crm_sales.commission.ba import compute_ba_for_sheet
from ion_crm_sales.ion_crm_sales.commission.gl import post_accrual
from ion_crm_sales.ion_crm_sales.commission.helpers import (
    ensure_quarter_on,
    get_quarter_window,
    quarter_target_from_distribution,
)


ALLOWED_STATES = {"Draft", "Submitted", "Approved"}


class SalesTargetandCommissionSheet(Document):
    def validate(self):
        ensure_quarter_on(self)

        # SALES engine (Home/Hotspot)
        compute_sales_quarterly(self)

        # BA engine
        self._compute_ba_lines()

        # Recompute parent totals in case BA updated them via lines
        self._retotal()

    def before_submit(self):
        if not self.get("commission_lines"):
            frappe.throw("Add at least one commission line.")

        # Ensure every line has a quarter target (Sales/BA)
        for ln in (self.get("commission_lines") or []):
            if not flt(ln.target_value):
                frappe.throw(
                    f"Missing quarter target for {ln.sales_person} in {ln.department}. "
                    f"Make sure Sales Person Targets are entered and have a Monthly Distribution."
                )

    def before_save(self):
        if self._should_post_accrual_from_workflow():
            post_accrual(self, save=False)

    def before_update_after_submit(self):
        if self._should_post_accrual_from_workflow():
            post_accrual(self, save=False)

    def on_update_after_submit(self):
        # Allow recompute while not Posted
        if self.status in ALLOWED_STATES:
            ensure_quarter_on(self)
            compute_sales_quarterly(self)
            self._compute_ba_lines()
            self._retotal()

    # ---------- helpers ---------- #

    def _should_post_accrual_from_workflow(self):
        if self.docstatus != 1 or self.status != "Posted" or self.accrual_je:
            return False

        previous = self.get_doc_before_save()
        if not previous:
            return False

        return previous.status == "Approved"

    def _compute_ba_lines(self):
        """Fill BA lines using BA engine results; also fill BA quarter targets for visibility."""
        q_start, q_end, months3 = get_quarter_window(
            self.fiscal_year, ensure_quarter_on(self),
        )
        ba_map, ba_actual_map = compute_ba_for_sheet(self, include_actuals=True)

        for ln in (self.get("commission_lines") or []):
            if ln.department != "Business Accounts":
                continue
            ln.target_value = quarter_target_from_distribution(
                ln.sales_person, self.fiscal_year, months3,
            )
            ln.actual_sales = flt(ba_actual_map.get(ln.sales_person) or 0.0)
            ln.achievement_pct = (
                round((ln.actual_sales / ln.target_value * 100.0), 2)
                if ln.target_value
                else 0.0
            )
            ln.commission_value = flt(ba_map.get(ln.sales_person) or 0.0)
            ln.commission_rate = (
                round((ln.commission_value / ln.actual_sales * 100.0), 2)
                if ln.actual_sales
                else 0.0
            )

    def _retotal(self):
        total_target = total_actual = total_commission = 0.0
        for ln in (self.get("commission_lines") or []):
            total_target += flt(ln.target_value)
            total_actual += flt(ln.actual_sales)
            total_commission += flt(ln.commission_value)
        self.total_target = round(total_target, 2)
        self.total_actual_sales = round(total_actual, 2)
        self.total_commission = round(total_commission, 2)
