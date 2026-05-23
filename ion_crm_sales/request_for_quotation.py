import json

import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc

from erpnext.accounts.party import get_party_account_currency, get_party_details
from erpnext.buying.doctype.request_for_quotation.request_for_quotation import add_items
from erpnext.stock.doctype.material_request.material_request import set_missing_values


OPPORTUNITY_LINK_FIELDS = (
	"custom_dedicated_opportunity",
	"custom_sm_opportunity",
	"custom_hotels_opportunity",
	"custom_hotel_opportunity",
	"custom_tenders_opportunity",
	"custom_tender_opportunity",
	"custom_isp_opportunity",
	"custom_opportunity_isp",
)


def copy_opportunity_links(source, target):
	source_meta = frappe.get_meta(source.doctype)
	target_meta = frappe.get_meta(target.doctype)

	for fieldname in OPPORTUNITY_LINK_FIELDS:
		if source_meta.has_field(fieldname) and target_meta.has_field(fieldname) and source.get(fieldname):
			target.set(fieldname, source.get(fieldname))


@frappe.whitelist()
def make_supplier_quotation_from_rfq(source_name, target_doc=None, for_supplier=None):
	def postprocess(source, target_doc):
		if for_supplier:
			target_doc.supplier = for_supplier
			args = get_party_details(for_supplier, party_type="Supplier", ignore_permissions=True)
			target_doc.currency = args.currency or get_party_account_currency(
				"Supplier", for_supplier, source.company
			)
			target_doc.buying_price_list = args.buying_price_list or frappe.db.get_value(
				"Buying Settings", None, "buying_price_list"
			)

		copy_opportunity_links(source, target_doc)
		set_missing_values(source, target_doc)

	doclist = get_mapped_doc(
		"Request for Quotation",
		source_name,
		{
			"Request for Quotation": {
				"doctype": "Supplier Quotation",
				"validation": {"docstatus": ["=", 1]},
				"field_map": {"opportunity": "opportunity"},
			},
			"Request for Quotation Item": {
				"doctype": "Supplier Quotation Item",
				"field_map": {
					"name": "request_for_quotation_item",
					"parent": "request_for_quotation",
					"project_name": "project",
				},
			},
		},
		target_doc,
		postprocess,
	)

	return doclist


@frappe.whitelist()
def create_supplier_quotation(doc):
	if isinstance(doc, str):
		doc = json.loads(doc)

	try:
		sq_doc = frappe.get_doc(
			{
				"doctype": "Supplier Quotation",
				"supplier": doc.get("supplier"),
				"terms": doc.get("terms"),
				"company": doc.get("company"),
				"currency": doc.get("currency")
				or get_party_account_currency("Supplier", doc.get("supplier"), doc.get("company")),
				"buying_price_list": doc.get("buying_price_list")
				or frappe.db.get_value("Buying Settings", None, "buying_price_list"),
			}
		)
		copy_opportunity_links(frappe._dict({"doctype": "Request for Quotation", **doc}), sq_doc)
		add_items(sq_doc, doc.get("supplier"), doc.get("items"))
		sq_doc.flags.ignore_permissions = True
		sq_doc.run_method("set_missing_values")
		sq_doc.save()
		frappe.msgprint(_("Supplier Quotation {0} Created").format(sq_doc.name))
		return sq_doc.name
	except Exception:
		return None
