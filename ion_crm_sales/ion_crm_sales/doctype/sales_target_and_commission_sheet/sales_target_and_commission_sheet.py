# -*- coding: utf-8 -*-
"""
Controller for the Sales Target and Commission Sheet doctype.

Orchestrates calls to both the Sales and BA commission engines
during validate, before_submit, and on_update_after_submit.
"""

import frappe
from frappe.model.document import Document
from frappe.utils import flt

from ion_crm_sales.ion_crm_sales.commission.gl import post_accrual
from ion_crm_sales.ion_crm_sales.commission.helpers import (
    ensure_quarter_on,
)
from ion_crm_sales.ion_crm_sales.commission.transactions import sync_sheet_transactions


ALLOWED_STATES = {"Draft", "Submitted", "Approved"}


class SalesTargetandCommissionSheet(Document):
    def validate(self):
        ensure_quarter_on(self)
        if self.is_new():
            return
        sync_sheet_transactions(self)

    def after_insert(self):
        sync_sheet_transactions(self)
        self.db_update()
        for line in self.get("commission_lines") or []:
            line.db_update()

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
            sync_sheet_transactions(self)

    # ---------- helpers ---------- #

    def _should_post_accrual_from_workflow(self):
        if self.docstatus != 1 or self.status != "Posted" or self.accrual_je:
            return False

        previous = self.get_doc_before_save()
        if not previous:
            return False

        return previous.status == "Approved"
