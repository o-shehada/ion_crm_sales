import frappe

from ion_crm_sales.ion_crm_sales.doc_events.quotation_handlers import (
    OPPORTUNITY_SOURCE_FIELDS,
    get_or_create_sales_person_for_user,
    get_source_opportunity,
    set_sales_team_contributor,
)


DIRECT_SALES_ORDER_ACCOUNT_MANAGER_ROLES = {
    "ISP Account Manager",
    "Tenders Account Manager",
    "Hotels Account Manager",
    "SM Account Manager",
    "Dedicated Account Manager",
}

BA_SCENARIO_FIELDS = {
    "custom_service_category": "Service Category",
    "custom_ba_transaction_type": "BA Transaction Type",
}


def before_insert(doc, method=None):
    set_sales_order_source_fields(doc)
    set_account_manager_sales_team(doc)
    set_current_user_sales_team_for_direct_sales_order(doc)


def validate(doc, method=None):
    set_sales_order_source_fields(doc)
    set_account_manager_sales_team(doc)
    set_current_user_sales_team_for_direct_sales_order(doc)
    validate_ba_scenario_fields_for_account_manager_save(doc)
    prevent_non_account_manager_ba_scenario_field_changes(doc)


def before_submit(doc, method=None):
    validate_ba_scenario_fields_for_submit(doc)


def set_sales_order_source_fields(doc, method=None):
    """Copy the source type from a linked Quotation; preserve direct-entry values."""
    quotation = get_source_quotation(doc)
    if quotation and not doc.get("custom_opportunity_from"):
        doc.custom_opportunity_from = quotation.get("custom_opportunity_from")


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


def prevent_non_account_manager_ba_scenario_field_changes(doc):
    if doc.is_new() or user_has_direct_sales_order_account_manager_role(frappe.session.user):
        return

    changed_fields = [
        label
        for fieldname, label in BA_SCENARIO_FIELDS.items()
        if doc.has_value_changed(fieldname)
    ]
    if changed_fields:
        frappe.throw(
            "Only Account Manager users can edit {0} on Sales Order.".format(
                " and ".join(changed_fields)
            )
        )


def validate_ba_scenario_fields_for_account_manager_save(doc):
    if user_has_direct_sales_order_account_manager_role(frappe.session.user):
        validate_ba_scenario_fields(doc)


def validate_ba_scenario_fields_for_submit(doc):
    if user_has_direct_sales_order_account_manager_role(frappe.session.user):
        validate_ba_scenario_fields(doc)


def validate_ba_scenario_fields(doc):
    missing_fields = [label for fieldname, label in BA_SCENARIO_FIELDS.items() if not doc.get(fieldname)]
    if missing_fields:
        frappe.throw(
            "{0} required before saving or submitting Sales Order.".format(
                " and ".join(missing_fields)
            )
        )


def set_current_user_sales_team_for_direct_sales_order(doc):
    if not doc.is_new():
        return

    if get_source_quotation(doc) or has_linked_opportunity(doc):
        return

    if not user_has_direct_sales_order_account_manager_role(frappe.session.user):
        return

    sales_person = get_existing_sales_person_for_user(frappe.session.user)
    if not sales_person:
        return

    set_sales_team_contributor(doc, sales_person)


def user_has_direct_sales_order_account_manager_role(user):
    return bool(DIRECT_SALES_ORDER_ACCOUNT_MANAGER_ROLES.intersection(frappe.get_roles(user)))


def get_existing_sales_person_for_user(user):
    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if not employee:
        return None

    return frappe.db.get_value(
        "Sales Person",
        {
            "employee": employee,
            "enabled": 1,
            "is_group": 0,
        },
        "name",
    )


def has_linked_opportunity(doc):
    for fieldname, _source_label in OPPORTUNITY_SOURCE_FIELDS:
        if doc.get(fieldname):
            return True

    for item in doc.get("items") or []:
        if (item.get("prevdoc_doctype") or "").startswith("Opportunity"):
            return True

    return False


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
