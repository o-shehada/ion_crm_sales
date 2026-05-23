import frappe
from frappe.model.mapper import get_mapped_doc


OPPORTUNITY_LINK_FIELDS = (
	"custom_dedicated_opportunity",
	"custom_sm_opportunity",
	"custom_hotels_opportunity",
	"custom_hotel_opportunity",
	"custom_tenders_opportunity",
	"custom_tender_opportunity",
	"custom_isp_opportunity",
)


def copy_opportunity_links(source, target):
	source_meta = frappe.get_meta(source.doctype)
	target_meta = frappe.get_meta(target.doctype)

	for fieldname in OPPORTUNITY_LINK_FIELDS:
		if source_meta.has_field(fieldname) and target_meta.has_field(fieldname) and source.get(fieldname):
			target.set(fieldname, source.get(fieldname))


@frappe.whitelist()
def make_request_for_quotation(source_name, target_doc=None):
	doclist = get_mapped_doc(
		"Material Request",
		source_name,
		{
			"Material Request": {
				"doctype": "Request for Quotation",
				"validation": {
					"docstatus": ["=", 1],
					"material_request_type": ["=", "Request for Quotation"],
				},
			},
			"Material Request Item": {
				"doctype": "Request for Quotation Item",
				"field_map": [
					["name", "material_request_item"],
					["parent", "material_request"],
					["project", "project_name"],
				],
			},
		},
		target_doc,
		copy_opportunity_links,
	)

	return doclist
