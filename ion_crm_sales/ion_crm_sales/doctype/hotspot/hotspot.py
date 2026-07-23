# Copyright (c) 2025, ard.ly and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc

from erpnext.setup.utils import get_exchange_rate
from erpnext.utilities.transaction_base import TransactionBase

class Hotspot(Document):
	def calculate_totals(self):
		total = base_total = 0
		for item in self.get("items"):
			item.amount = flt(item.rate) * flt(item.qty)
			item.base_rate = flt(self.conversion_rate) * flt(item.rate)
			item.base_amount = flt(self.conversion_rate) * flt(item.amount)
			total += item.amount
			base_total += item.base_amount

		self.total = flt(total)
		self.base_total = flt(base_total)

	def validate_item_details(self):
		if not self.get("items"):
			return

		# set missing values
		item_fields = ("item_name", "description", "item_group", "brand")

		for d in self.items:
			if not d.item_code:
				continue

			item = frappe.db.get_value("Item", d.item_code, item_fields, as_dict=True)
			for key in item_fields:
				if not d.get(key):
					d.set(key, item.get(key))

@frappe.whitelist()
def make_quotation(source_name, target_doc=None):
	def set_missing_values(source, target):
		from erpnext.controllers.accounts_controller import get_default_taxes_and_charges

		target.run_method("set_missing_values")

		company_currency = frappe.get_cached_value("Company", target.company, "default_currency")
		if company_currency == target.currency:
			target.conversion_rate = 1
		else:
			target.conversion_rate = get_exchange_rate(
				target.currency, company_currency, target.transaction_date, args="for_selling"
			)

		taxes = get_default_taxes_and_charges("Sales Taxes and Charges Template", company=target.company)
		if taxes and taxes.get("taxes"):
			target.update(taxes)

		target.run_method("calculate_taxes_and_totals")

	return get_mapped_doc(
		"Hotspot",
		source_name,
		{
			"Hotspot": {
				"doctype": "Quotation",
				"field_map": {"hotspot_for": "quotation_to"},
			},
			"Hotspot Item": {
				"doctype": "Quotation Item",
				"field_map": {"item": "item_code"},
			},
		},
		target_doc,
		set_missing_values,
	)



@frappe.whitelist()
def make_supplier_quotation(source_name, target_doc=None):
	doclist = get_mapped_doc(
		"Hotspot",
		source_name,
		{
			"Hotspot": {"doctype": "Supplier Quotation", "field_map": {"name": "opportunity"}},
			"Opportunity Item": {"doctype": "Supplier Quotation Item", "field_map": {"uom": "stock_uom"}},
		},
		target_doc,
	)

	return doclist

@frappe.whitelist()
def make_request_for_quotation(source_name, target_doc=None):
	def update_item(obj, target, source_parent):
		target.conversion_factor = 1.0

	doclist = get_mapped_doc(
		"Hotspot",
		source_name,
		{
			"Hotspot": {"doctype": "Request for Quotation"},
			"Opportunity Item": {
				"doctype": "Request for Quotation Item",
				"field_map": [["name", "opportunity_item"], ["parent", "opportunity"], ["uom", "uom"]],
				"postprocess": update_item,
			},
		},
		target_doc,
	)

	return doclist


@frappe.whitelist()
def make_customer(source_name, target_doc=None):
	def set_missing_values(source, target):

		target.prospect_name = source.party_name

	doclist = get_mapped_doc(
		"Hotspot",
		source_name,
		{
			"Hotspot": {
				"doctype": "Customer",
				"field_map": {"currency": "default_currency", "party_name": "customer_name"},
			}
		},
		target_doc,
		set_missing_values,
	)

	return doclist