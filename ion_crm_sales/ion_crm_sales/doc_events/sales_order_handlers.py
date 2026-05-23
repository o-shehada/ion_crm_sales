import frappe

from ion_crm_sales.ion_crm_sales.doc_events.quotation_handlers import (
    get_or_create_sales_person_for_user,
    get_source_opportunity,
    set_sales_team_contributor,
)


def before_insert(doc, method=None):
    set_account_manager_sales_team(doc)


def validate(doc, method=None):
    set_account_manager_sales_team(doc)


def set_account_manager_sales_team(doc):
    quotation = get_source_quotation(doc)
    if not quotation:
        return

    opportunity = get_source_opportunity(quotation)
    if not opportunity or not opportunity.get("custom_account_manager"):
        return

    sales_person = get_or_create_sales_person_for_user(opportunity.custom_account_manager)
    if not sales_person:
        return

    set_sales_team_contributor(doc, sales_person)


def get_source_quotation(doc):
    if doc.get("quotation") and frappe.db.exists("Quotation", doc.quotation):
        return frappe.get_cached_doc("Quotation", doc.quotation)

    for item in doc.get("items") or []:
        if item.get("prevdoc_docname") and frappe.db.exists("Quotation", item.prevdoc_docname):
            return frappe.get_cached_doc("Quotation", item.prevdoc_docname)

        if item.get("quotation_item"):
            quotation = frappe.db.get_value("Quotation Item", item.quotation_item, "parent")
            if quotation:
                return frappe.get_cached_doc("Quotation", quotation)

    return None
