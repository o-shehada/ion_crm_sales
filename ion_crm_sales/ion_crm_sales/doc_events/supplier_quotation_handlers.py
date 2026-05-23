import frappe


OPPORTUNITY_TABLE_FIELDS = {
	"Opportunity": "custom_opportunity_supplier_quotation_table",
	"Opportunity SM": "opportunity_supplier_quotation_table",
	"Opportunity Hotels": "opportunity_supplier_quotation_table",
	"Opportunity Tenders": "opportunity_supplier_quotation_table",
	"Opportunity ISP": "opportunity_supplier_quotation_table",
}


SUPPLIER_QUOTATION_OPPORTUNITY_FIELDS = {
	"Opportunity": ("opportunity", "custom_dedicated_opportunity"),
	"Opportunity SM": ("opportunity_sm", "custom_sm_opportunity", "custom_opportunity_sm"),
	"Opportunity Hotels": (
		"opportunity_hotels",
		"custom_hotels_opportunity",
		"custom_hotel_opportunity",
		"custom_opportunity_hotels",
	),
	"Opportunity Tenders": (
		"opportunity_tenders",
		"custom_tenders_opportunity",
		"custom_tender_opportunity",
		"custom_opportunity_tenders",
	),
	"Opportunity ISP": ("opportunity_isp", "custom_isp_opportunity", "custom_opportunity_isp"),
}


def on_update(doc, method=None):
	for opportunity_doctype, opportunity_name in get_linked_opportunities(doc):
		add_supplier_quotation_row(opportunity_doctype, opportunity_name, doc)


def get_linked_opportunities(doc):
	linked_opportunities = []
	seen = set()
	supplier_quotation_meta = frappe.get_meta(doc.doctype)

	for opportunity_doctype, fieldnames in SUPPLIER_QUOTATION_OPPORTUNITY_FIELDS.items():
		for fieldname in fieldnames:
			if not supplier_quotation_meta.has_field(fieldname) or not doc.get(fieldname):
				continue

			opportunity_name = doc.get(fieldname)
			if not frappe.db.exists(opportunity_doctype, opportunity_name):
				continue

			key = (opportunity_doctype, opportunity_name)
			if key not in seen:
				linked_opportunities.append(key)
				seen.add(key)

	add_standard_opportunity_fallback(doc, linked_opportunities, seen)

	return linked_opportunities


def add_standard_opportunity_fallback(doc, linked_opportunities, seen):
	if not doc.get("opportunity") or frappe.db.exists("Opportunity", doc.opportunity):
		return

	for opportunity_doctype in (
		"Opportunity SM",
		"Opportunity Hotels",
		"Opportunity Tenders",
		"Opportunity ISP",
	):
		if not frappe.db.exists(opportunity_doctype, doc.opportunity):
			continue

		key = (opportunity_doctype, doc.opportunity)
		if key not in seen:
			linked_opportunities.append(key)
			seen.add(key)


def add_supplier_quotation_row(opportunity_doctype, opportunity_name, supplier_quotation):
	table_field = OPPORTUNITY_TABLE_FIELDS.get(opportunity_doctype)
	if not table_field:
		return

	opportunity_meta = frappe.get_meta(opportunity_doctype)
	if not opportunity_meta.has_field(table_field):
		return

	if supplier_quotation_exists_in_table(opportunity_doctype, opportunity_name, table_field, supplier_quotation.name):
		return

	opportunity = frappe.get_doc(opportunity_doctype, opportunity_name)
	opportunity.append(
		table_field,
		{
			"supplier_quotation": supplier_quotation.name,
			"supplier": supplier_quotation.get("supplier"),
			"supplier_name": supplier_quotation.get("supplier_name"),
			"total": supplier_quotation.get("grand_total"),
		},
	)
	opportunity.save(ignore_permissions=True)


def supplier_quotation_exists_in_table(
	opportunity_doctype, opportunity_name, table_field, supplier_quotation_name
):
	return frappe.db.exists(
		"Opportunity Supplier Quotation Table",
		{
			"parenttype": opportunity_doctype,
			"parent": opportunity_name,
			"parentfield": table_field,
			"supplier_quotation": supplier_quotation_name,
		},
	)
