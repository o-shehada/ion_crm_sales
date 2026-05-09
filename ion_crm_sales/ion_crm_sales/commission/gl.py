# -*- coding: utf-8 -*-
"""
General Ledger integration — creates the commission accrual Journal Entry.
"""

import frappe
from frappe.utils import today, flt

from .helpers import ensure_quarter_on


def _settings_accounts():
    """Read the Expense + Payable accounts from Commission Policy Settings."""
    expense_acc = frappe.db.get_single_value(
        "Commission Policy Settings", "expense_account"
    )
    payable_acc = frappe.db.get_single_value(
        "Commission Policy Settings", "payable_account"
    )
    if not expense_acc or not payable_acc:
        frappe.throw("Set Expense and Payable accounts in Commission Policy Settings.")
    return expense_acc, payable_acc


def _validate_accounts(expense_acc, payable_acc, company):
    """Basic sanity checks on the selected GL accounts."""
    if expense_acc == payable_acc:
        frappe.throw("Commission Expense and Commission Payable accounts must be different.")

    for acc_name, expected_root in ((expense_acc, "Expense"), (payable_acc, "Liability")):
        acc = frappe.db.get_value(
            "Account", acc_name, ["is_group", "root_type", "company"], as_dict=True,
        )
        if not acc:
            frappe.throw(f"Account '{acc_name}' does not exist.")
        if acc.is_group:
            frappe.throw(f"Account '{acc_name}' is a group account — select a ledger account.")
        if acc.company != company:
            frappe.throw(
                f"Account '{acc_name}' belongs to {acc.company}, "
                f"but the sheet company is {company}."
            )


def _ensure_single_posted_per_quarter(sheet):
    """Prevent posting two sheets for the same company + FY + quarter."""
    quarter = ensure_quarter_on(sheet)
    conflict = frappe.get_all(
        "Sales Target and Commission Sheet",
        filters={
            "company": sheet.company,
            "fiscal_year": sheet.fiscal_year,
            "quarter": quarter,
            "status": "Posted",
            "name": ["!=", sheet.name],
        },
        fields=["name", "accrual_je"],
        limit=1,
    )
    if conflict:
        c = conflict[0]
        frappe.throw(
            f"A sheet for {sheet.company} {sheet.fiscal_year} {quarter} is already Posted "
            f"(Sheet: {c['name']}, JE: {c.get('accrual_je')})."
        )


def post_accrual(sheet, save: bool = True):
    """Create and submit the commission accrual Journal Entry."""
    _ensure_single_posted_per_quarter(sheet)

    expense_acc, payable_acc = _settings_accounts()
    _validate_accounts(expense_acc, payable_acc, sheet.company)

    amount = flt(sheet.total_commission)
    if amount <= 0:
        frappe.throw("Commission total is zero; nothing to accrue.")

    q = ensure_quarter_on(sheet)

    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Journal Entry"
    je.posting_date = today()
    je.company = sheet.company
    je.user_remark = (
        f"Commission accrual for {sheet.company} {sheet.fiscal_year} "
        f"{q} - sheet {sheet.name}"
    )

    je.append("accounts", {"account": expense_acc, "debit_in_account_currency": amount})
    je.append("accounts", {"account": payable_acc, "credit_in_account_currency": amount})

    je.insert()
    je.submit()
    je.add_comment("Comment", text=f"Accrual posted from sheet {sheet.name}")

    sheet.accrual_posted_amount = amount
    sheet.accrual_je = je.name
    if save:
        sheet.save()
