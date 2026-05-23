# Copyright (c) 2026, ard.ly and contributors
# For license information, please see license.txt

# import frappe
import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from erpnext.setup.utils import get_exchange_rate


class OpportunityISP(Document):
	pass


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
		if frappe.get_meta("Quotation").has_field("custom_opportunity_isp"):
			quotation.custom_opportunity_isp = source.name
		if frappe.get_meta("Quotation").has_field("custom_opportunity_from"):
			quotation.custom_opportunity_from = "ISP"

	doclist = get_mapped_doc(
		"Opportunity ISP",
		source_name,
		{
			"Opportunity ISP": {
				"doctype": "Quotation",
				"field_map": {"opportunity_from": "quotation_to", "name": "enq_no"},
			},
			"Opportunity Item": {
				"doctype": "Quotation Item",
				"field_map": {
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
def make_supplier_quotation(source_name, target_doc=None):
	def update_item(obj, target, source_parent):
		target.stock_uom = obj.uom
		target.conversion_factor = 1.0
		if source_parent.get("custom_warehouse"):
			target.warehouse = source_parent.custom_warehouse

	def set_missing_values(source, target):
		for fieldname in ("custom_isp_opportunity", "custom_opportunity_isp"):
			if frappe.get_meta("Supplier Quotation").has_field(fieldname):
				target.set(fieldname, source.name)

	doclist = get_mapped_doc(
		"Opportunity ISP",
		source_name,
		{
			"Opportunity ISP": {"doctype": "Supplier Quotation"},
			"Opportunity Item": {
				"doctype": "Supplier Quotation Item",
				"field_map": {
					"item_code": "item_code",
					"item_name": "item_name",
					"description": "description",
					"qty": "qty",
					"uom": "uom",
					"rate": "rate",
					"amount": "amount",
					"brand": "brand",
					"item_group": "item_group",
				},
				"postprocess": update_item,
			},
		},
		target_doc,
		set_missing_values,
	)

	return doclist


@frappe.whitelist()
def make_request_for_quotation(source_name, target_doc=None):
	def update_item(obj, target, source_parent):
		target.stock_uom = obj.uom
		target.conversion_factor = 1.0
		if source_parent.get("custom_warehouse"):
			target.warehouse = source_parent.custom_warehouse

	def set_missing_values(source, target):
		for fieldname in ("custom_isp_opportunity", "custom_opportunity_isp"):
			if frappe.get_meta("Request for Quotation").has_field(fieldname):
				target.set(fieldname, source.name)

	doclist = get_mapped_doc(
		"Opportunity ISP",
		source_name,
		{
			"Opportunity ISP": {"doctype": "Request for Quotation"},
			"Opportunity Item": {
				"doctype": "Request for Quotation Item",
				"field_map": {
					"name": "opportunity_item",
					"parent": "opportunity",
					"item_code": "item_code",
					"item_name": "item_name",
					"description": "description",
					"qty": "qty",
					"uom": "uom",
					"brand": "brand",
					"item_group": "item_group",
				},
				"postprocess": update_item,
			},
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

		taxes = get_default_taxes_and_charges("Sales Taxes and Charges Template", company=material_request.company)
		if taxes.get("taxes"):
			material_request.update(taxes)

		material_request.run_method("set_missing_values")
		material_request.material_request_type = "Material Issue"
		if frappe.get_meta("Material Request").has_field("custom_isp_opportunity"):
			material_request.custom_isp_opportunity = source.name

	doclist = get_mapped_doc(
		"Opportunity ISP",
		source_name,
		{
			"Opportunity ISP": {
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
