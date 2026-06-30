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
        self._validate_one_sheet_per_sales_person()
        if self.is_new():
            return
        sync_sheet_transactions(self)

    def after_insert(self):
        sync_sheet_transactions(self)
        self.db_update()
        for row in self.get("invoice_history") or []:
            if row.is_new():
                row.db_insert()
            else:
                row.db_update()

    def before_submit(self):
        if not flt(self.total_target):
            frappe.throw(
                f"Missing quarter target for {self.sales_person}. "
                "Make sure Sales Person Targets are entered and have a Monthly Distribution."
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

    def _validate_one_sheet_per_sales_person(self):
        if not self.sales_person:
            return

        duplicate = frappe.db.get_value(
            "Sales Target and Commission Sheet",
            {
                "company": self.company,
                "fiscal_year": self.fiscal_year,
                "quarter": self.quarter,
                "sales_person": self.sales_person,
                "docstatus": ("<", 2),
                "name": ("!=", self.name or ""),
            },
            "name",
        )
        if duplicate:
            frappe.throw(
                f"Commission sheet {duplicate} already exists for "
                f"{self.sales_person} in {self.fiscal_year} {self.quarter}."
            )

    def _should_post_accrual_from_workflow(self):
        if self.docstatus != 1 or self.status != "Posted" or self.accrual_je:
            return False

        previous = self.get_doc_before_save()
        if not previous:
            return False

        return previous.status == "Approved"
