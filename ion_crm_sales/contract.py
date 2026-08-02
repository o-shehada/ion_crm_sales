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
    """Custom Contract ID built from the Opportunity type, the Territory
    abbreviation and the customer branch id:

        <TYPE_CODE>-<TERRITORY_ABBR>-#####-<CUSTOMER_BRANCH_ID>   e.g. DD-BA-00001-1

    Each part except the Territory abbreviation is optional, so the naming
    degrades gracefully:

        no Opportunity type        -> <TERRITORY_ABBR>-#####-<CUSTOMER_BRANCH_ID>
        no customer branch id      -> <TYPE_CODE>-<TERRITORY_ABBR>-#####
        neither                    -> <TERRITORY_ABBR>-#####

    The last form is what a Contract created directly (not from a Sales Order)
    gets, with the Territory taken from the linked Customer.

    Runs after the core Contract.autoname() (party_name based) via the
    "autoname" doc_event, so the core naming only stands when no Territory
    abbreviation can be resolved at all.
    """
    type_code, territory, branch_id = _get_naming_parts(doc)

    territory_abbr = (
        frappe.db.get_value("Territory", territory, "custom_territory_abbreviation")
        if territory
        else None
    )
    if not territory_abbr:
        return

    prefix = f"{type_code}-{territory_abbr}" if type_code else territory_abbr
    running_number = make_autoname(f"{prefix}-.#####.", doctype="Contract")
    doc.name = f"{running_number}-{branch_id}" if branch_id else running_number


def _get_naming_parts(doc):
    """Return (type_code, territory, customer_branch_id) for the Contract.

    Values come from the source Sales Order when the Contract is linked to one;
    the Territory falls back to the Contract's own Customer so that a Contract
    created directly can still be named.
    """
    type_code = territory = branch_id = None

    if doc.document_type == "Sales Order" and doc.document_name:
        sales_order = frappe.db.get_value(
            "Sales Order",
            doc.document_name,
            ["custom_opportunity_from", "territory", "custom_customer_branch_id"],
            as_dict=True,
        )
        if sales_order:
            type_code = OPPORTUNITY_TYPE_CODE.get(sales_order.custom_opportunity_from)
            territory = sales_order.territory
            branch_id = sales_order.custom_customer_branch_id

    if not territory and doc.party_type == "Customer" and doc.party_name:
        territory = frappe.db.get_value("Customer", doc.party_name, "territory")

    return type_code, territory, branch_id
