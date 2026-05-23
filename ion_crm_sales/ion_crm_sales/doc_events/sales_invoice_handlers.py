import frappe
from frappe import _

COMMISSION_MODIFIERS = {
    "Old Accounts": 0.0075,
    "Lead Acquisition": 0.01,
    "Upsell": 0.02,
    "Above Target": 0.06
}


def validate_contract_for_source_sales_orders(doc, method=None):
	sales_orders = set()
	for item in doc.get("items", []):
		sales_order = item.get("sales_order")
		if not sales_order and item.get("prevdoc_doctype") == "Sales Order":
			sales_order = item.get("prevdoc_docname")
		if sales_order:
			sales_orders.add(sales_order)

	if not sales_orders:
		return

	for sales_order in sales_orders:
		validate_sales_order_contract_for_invoice(sales_order)


@frappe.whitelist()
def validate_sales_order_contract_for_invoice(sales_order):
	source = frappe.db.get_value(
		"Sales Order",
		sales_order,
		["custom_opportunity_from", "custom_contract"],
		as_dict=True,
	)

	if not source or not source.custom_opportunity_from:
		return True

	if not source.custom_contract:
		frappe.throw(
			_(
				"You must create or link an Active Contract on Sales Order {0} before creating a Sales Invoice."
			).format(sales_order)
		)

	contract_status = frappe.db.get_value("Contract", source.custom_contract, "status")
	if not contract_status:
		frappe.throw(
			_(
				"The linked Contract {0} on Sales Order {1} does not exist. Link an Active Contract before creating a Sales Invoice."
			).format(source.custom_contract, sales_order)
		)

	if contract_status != "Active":
		frappe.throw(
			_(
				"The linked Contract {0} on Sales Order {1} must be Active before creating a Sales Invoice."
			).format(source.custom_contract, sales_order)
		)

	return True

def on_submit(doc, method):
    if (doc.subscription):
        subscription = frappe.get_doc("Subscription", doc.subscription)
        grand_total = doc.grand_total
        comtr = frappe.new_doc("Commission Transaction")

        beneficiaries = []

        for d in subscription.custom_parties:
            beneficiaries.append({
                "party": d.party,
                "beneficiary": d.person,
            })

        comtr.update({
            "amount": grand_total * COMMISSION_MODIFIERS.get(subscription.custom_type, 0),
            "invoice": doc.name,
            "invoice_status": doc.status,
            "commission_status": "Unpaid",
            "beneficiaries": beneficiaries,
            "percentage": COMMISSION_MODIFIERS.get(subscription.custom_type, 0) * 100
        })
        

        comtr.save()

def on_change(doc, method):
    print("#############################")
    print("#############################")
    print("#############################")
    print("#############################")
    print("#############################")
    print(doc.status)
    print("#############################")
    print("#############################")
    print("#############################")
    print("#############################")
    print("#############################")
    print("#############################")

    if (not doc.has_value_changed("status")):
        return
    
    if (doc.subscription):
        comtr_name = frappe.get_value("Commission Transaction", {"invoice": doc.name}, "name")
        if comtr_name:
            comtr = frappe.get_doc("Commission Transaction", comtr_name)
            comtr.invoice_status = doc.status
            comtr.save()
