# Copyright (c) 2025, ard.ly and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import frappe
from frappe.utils import flt, nowdate
import json

class CommissionTransaction(Document):
	pass


@frappe.whitelist()
def create_commission_payment(source_docname, amount=None, beneficiaries=None):
    source_doc = frappe.get_doc('Commission Transaction', source_docname)

    if source_doc.get("commission_status") == "Paid":
        existing = frappe.db.get_value(
            "Commission Payment",
            {"commission_transaction": source_docname},
            "name",
        )
        if existing:
            return existing

    amount = flt(amount or source_doc.get("total_commission") or source_doc.get("amount"))
    payment_beneficiaries = _get_payment_beneficiaries(source_doc, beneficiaries, amount)
    if not payment_beneficiaries:
        frappe.throw("No beneficiaries found for this Commission Transaction.")

    new_doc = frappe.new_doc('Commission Payment')

    new_doc.commission_transaction = source_docname
    new_doc.date_of_payment = nowdate()

    for row in payment_beneficiaries:
        new_doc.append('beneficiaries', row)

    try:
        new_doc.insert(ignore_permissions=True)

        source_doc.commission_status = 'Paid'
        source_doc.save(ignore_permissions=True)

        frappe.db.commit()

        return new_doc.name

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), 'Commission Payment Creation Error')
        frappe.throw(f"Could not create Commission Payment: {e}")


def _get_payment_beneficiaries(source_doc, beneficiaries=None, amount=0):
    parsed_beneficiaries = _parse_beneficiaries(beneficiaries)
    if not parsed_beneficiaries:
        parsed_beneficiaries = [
            {"party": row.party, "beneficiary": row.beneficiary}
            for row in (source_doc.get("beneficiaries") or [])
            if row.get("party") and row.get("beneficiary")
        ]

    if parsed_beneficiaries:
        share = flt(amount) / len(parsed_beneficiaries)
        return [
            {
                "party": row.get("party"),
                "beneficiary": row.get("beneficiary"),
                "share": share,
            }
            for row in parsed_beneficiaries
        ]

    shares_by_party = {}
    for line in source_doc.get("lines") or []:
        beneficiary = line.get("employee") or line.get("sales_person")
        if not beneficiary:
            continue

        party = "Employee" if line.get("employee") else "Sales Person"
        key = (party, beneficiary)
        shares_by_party[key] = shares_by_party.get(key, 0) + flt(line.get("commission_amount"))

    return [
        {"party": party, "beneficiary": beneficiary, "share": share}
        for (party, beneficiary), share in shares_by_party.items()
        if share
    ]


def _parse_beneficiaries(beneficiaries):
    if not beneficiaries:
        return []

    if isinstance(beneficiaries, str):
        try:
            return json.loads(beneficiaries)
        except Exception:
            return []

    return beneficiaries
