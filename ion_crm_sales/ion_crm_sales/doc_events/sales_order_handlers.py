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


@frappe.whitelist()
def create_contract(sales_order, contract_template=None, contract_terms=None):
    """Create and link a Contract without assuming a specific template."""
    from erpnext.crm.doctype.contract_template.contract_template import (
        get_contract_template,
    )

    sales_order_doc = frappe.get_doc("Sales Order", sales_order)
    sales_order_doc.check_permission("write")

    if sales_order_doc.get("custom_contract"):
        frappe.throw("A Contract is already linked to this Sales Order.")

    terms = (contract_terms or "").strip()
    template_doc = None
    start_date = frappe.utils.nowdate()

    if contract_template:
        payload = sales_order_doc.as_dict()
        payload.update(
            {
                "party_type": "Customer",
                "party_name": sales_order_doc.customer,
                "customer_name": sales_order_doc.customer_name,
                "start_date": start_date,
                "document_type": "Sales Order",
                "document_name": sales_order_doc.name,
                "project_name_or_description": sales_order_doc.get("project")
                or sales_order_doc.get("title")
                or sales_order_doc.name,
            }
        )
        template_result = get_contract_template(contract_template, payload)
        template_doc = template_result.get("contract_template")
        terms = (template_result.get("contract_terms") or "").strip()

    if not terms:
        frappe.throw("Select a Contract Template or enter Contract Terms.")

    contract = frappe.new_doc("Contract")
    contract.check_permission("create")
    contract.party_type = "Customer"
    contract.party_name = sales_order_doc.customer
    contract.start_date = start_date
    contract.status = "Unsigned"
    contract.document_type = "Sales Order"
    contract.document_name = sales_order_doc.name
    contract.contract_terms = terms

    if template_doc:
        contract.contract_template = template_doc.name
        contract.requires_fulfilment = template_doc.requires_fulfilment
        for fulfilment_term in template_doc.get("fulfilment_terms") or []:
            contract.append(
                "fulfilment_terms",
                {"requirement": fulfilment_term.requirement},
            )

    contract.insert()
    sales_order_doc.db_set("custom_contract", contract.name)
    return contract.name
