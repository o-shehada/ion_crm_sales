import frappe
from frappe.model.naming import make_autoname

# Two/three-letter code per Opportunity type, keyed by the Sales Order's
# custom_opportunity_from value (same values used on Quotation/Opportunity variants).
OPPORTUNITY_TYPE_CODE = {
    "Dedicated": "DD",
    "ISP": "ISP",
    "Hotels": "HT",
    "S&M": "SM",
    "Tenders": "TN",
}


def set_contract_name(doc, method=None):
    """Custom Contract ID for contracts created from a Sales Order that has
    a linked Opportunity type and a Territory:

        <TYPE_CODE>-<TERRITORY_ABBREVIATION>-#####-<CUSTOMER_BRANCH_ID>

    e.g. DD-BA-00001-1

    Runs after the core Contract.autoname() (party_name based) via the
    "autoname" doc_event, so it only overrides doc.name when every piece of
    data is available; otherwise the core naming stands.
    """
    if doc.document_type != "Sales Order" or not doc.document_name:
        return

    sales_order = frappe.db.get_value(
        "Sales Order",
        doc.document_name,
        ["custom_opportunity_from", "territory", "custom_customer_branch_id"],
        as_dict=True,
    )
    if not sales_order:
        return

    type_code = OPPORTUNITY_TYPE_CODE.get(sales_order.custom_opportunity_from)
    if not type_code or not sales_order.territory or not sales_order.custom_customer_branch_id:
        return

    territory_abbr = frappe.db.get_value(
        "Territory", sales_order.territory, "custom_territory_abbreviation"
    )
    if not territory_abbr:
        return

    running_number = make_autoname(f"{type_code}-{territory_abbr}-.#####.", doctype="Contract")
    doc.name = f"{running_number}-{sales_order.custom_customer_branch_id}"
