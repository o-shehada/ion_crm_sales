import frappe
from frappe.model.mapper import get_mapped_doc
from erpnext.setup.utils import get_exchange_rate


@frappe.whitelist()
def make_quotation(source_name, target_doc=None):
	def set_missing_values(source, target):
		from erpnext.controllers.accounts_controller import get_default_taxes_and_charges

		quotation = frappe.get_doc(target)

		company_currency = frappe.get_cached_value("Company", quotation.company, "default_currency")

		if company_currency == quotation.currency:
			exchange_rate = 1
		else:
			exchange_rate = get_exchange_rate(
				quotation.currency, company_currency, quotation.transaction_date, args="for_selling"
			)

		quotation.conversion_rate = exchange_rate

		taxes = get_default_taxes_and_charges("Sales Taxes and Charges Template", company=quotation.company)
		if taxes.get("taxes"):
			quotation.update(taxes)

		quotation.run_method("set_missing_values")
		quotation.run_method("calculate_taxes_and_totals")
		if frappe.get_meta("Quotation").has_field("opportunity"):
			quotation.opportunity = source.name
		if frappe.get_meta("Quotation").has_field("custom_opportunity_from"):
			quotation.custom_opportunity_from = "Dedicated"

	doclist = get_mapped_doc(
		"Opportunity",
		source_name,
		{
			"Opportunity": {
				"doctype": "Quotation",
				"field_map": {"opportunity_from": "quotation_to", "name": "enq_no"},
			},
			"Opportunity Item": {
				"doctype": "Quotation Item",
				"field_map": {
					"parent": "prevdoc_docname",
					"parenttype": "prevdoc_doctype",
					"uom": "stock_uom",
				},
				"add_if_empty": True,
			},
		},
		target_doc,
		set_missing_values,
	)

	return doclist


@frappe.whitelist()
def make_request_for_quotation(source_name, target_doc=None):
	def update_item(obj, target, source_parent):
		target.conversion_factor = 1.0

	def set_missing_values(source, target):
		target.opportunity = source.name
		if frappe.get_meta("Request for Quotation").has_field("custom_dedicated_opportunity"):
			target.custom_dedicated_opportunity = source.name

	doclist = get_mapped_doc(
		"Opportunity",
		source_name,
		{
			"Opportunity": {"doctype": "Request for Quotation"},
			"Opportunity Item": {
				"doctype": "Request for Quotation Item",
				"field_map": [["name", "opportunity_item"], ["parent", "opportunity"], ["uom", "uom"]],
				"postprocess": update_item,
			},
		},
		target_doc,
		set_missing_values,
	)

	return doclist


@frappe.whitelist()
def make_supplier_quotation(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.opportunity = source.name
		if frappe.get_meta("Supplier Quotation").has_field("custom_dedicated_opportunity"):
			target.custom_dedicated_opportunity = source.name

	doclist = get_mapped_doc(
		"Opportunity",
		source_name,
		{
			"Opportunity": {"doctype": "Supplier Quotation"},
			"Opportunity Item": {"doctype": "Supplier Quotation Item", "field_map": {"uom": "stock_uom"}},
		},
		target_doc,
		set_missing_values,
	)

	return doclist


@frappe.whitelist()
def make_material_request(source_name, target_doc=None):
	def set_missing_values(source, target):
		from erpnext.controllers.accounts_controller import get_default_taxes_and_charges

		material_request = frappe.get_doc(target)

		taxes = get_default_taxes_and_charges(
			"Sales Taxes and Charges Template", company=material_request.company
		)
		if taxes.get("taxes"):
			material_request.update(taxes)

		material_request.run_method("set_missing_values")
		material_request.material_request_type = "Request for Quotation"
		if frappe.get_meta("Material Request").has_field("custom_dedicated_opportunity"):
			material_request.custom_dedicated_opportunity = source.name

	doclist = get_mapped_doc(
		"Opportunity",
		source_name,
		{
			"Opportunity": {
				"doctype": "Material Request",
				"field_map": {"opportunity_from": "material_request_to", "name": "enq_no"},
			},
			"Opportunity Item": {
				"doctype": "Material Request Item",
				"field_map": {
					"parent": "prevdoc_docname",
					"parenttype": "prevdoc_doctype",
					"uom": "stock_uom",
				},
				"add_if_empty": True,
			},
		},
		target_doc,
		set_missing_values,
	)

	return doclist


@frappe.whitelist()
def get_customer_branches(customer):
	"""Return the Branch Customer Table rows (branch name + branch id) linked to a Customer."""
	if not customer:
		return []

	return frappe.get_all(
		"Branch Customer Table",
		filters={
			"parent": customer,
			"parenttype": "Customer",
			"parentfield": "custom_branch_customer_table",
		},
		fields=["branch_customer", "branch_id"],
	)


@frappe.whitelist()
def link_existing_quotations(pairs=None, dry_run=True):
	"""Link existing Quotations to original Opportunities from explicit pairs.

	Pairs may be a dict {opportunity: quotation} or a list of dicts with
	`opportunity` and `quotation`. This intentionally avoids fuzzy matching.
	"""
	if isinstance(dry_run, str):
		dry_run = dry_run.lower() not in ("0", "false", "no")

	if isinstance(pairs, str):
		frappe.parse_json(pairs)
		pairs = frappe.parse_json(pairs)

	if not pairs:
		return {"updated": [], "skipped": []}

	if isinstance(pairs, dict):
		pairs = [
			{"opportunity": opportunity, "quotation": quotation}
			for opportunity, quotation in pairs.items()
		]

	updated = []
	skipped = []
	quotation_meta = frappe.get_meta("Quotation")
	if not quotation_meta.has_field("opportunity"):
		frappe.throw("Quotation has no opportunity field on this site.")

	for pair in pairs:
		opportunity = pair.get("opportunity")
		quotation = pair.get("quotation")
		if not opportunity or not quotation:
			skipped.append({"pair": pair, "reason": "Missing opportunity or quotation"})
			continue

		if not frappe.db.exists("Opportunity", opportunity):
			skipped.append({"opportunity": opportunity, "quotation": quotation, "reason": "Opportunity not found"})
			continue
		if not frappe.db.exists("Quotation", quotation):
			skipped.append({"opportunity": opportunity, "quotation": quotation, "reason": "Quotation not found"})
			continue

		existing = frappe.db.get_value("Quotation", quotation, "opportunity")
		if existing and existing != opportunity:
			skipped.append({
				"opportunity": opportunity,
				"quotation": quotation,
				"reason": f"Quotation already linked to {existing}",
			})
			continue

		updated.append({"opportunity": opportunity, "quotation": quotation})
		if not dry_run and not existing:
			values = {"opportunity": opportunity}
			if quotation_meta.has_field("custom_opportunity_from"):
				values["custom_opportunity_from"] = "Dedicated"
			frappe.db.set_value("Quotation", quotation, values, update_modified=False)

	if not dry_run and updated:
		frappe.db.commit()

	return {"dry_run": dry_run, "updated": updated, "skipped": skipped}
