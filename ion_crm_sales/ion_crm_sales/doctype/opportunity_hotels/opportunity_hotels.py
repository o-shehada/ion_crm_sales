# Copyright (c) 2025, ard.ly and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc

from erpnext.setup.utils import get_exchange_rate
from erpnext.utilities.transaction_base import TransactionBase
from frappe.contacts.address_and_contact import load_address_and_contact

from erpnext.crm.utils import (
	CRMNote,
	copy_comments,
	link_communications,
	link_open_events,
	link_open_tasks,
)

class OpportunityHotels(TransactionBase, CRMNote):
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
	
	def onload(self):
		ref_doc = frappe.get_doc(self.opportunity_from, self.party_name)

		load_address_and_contact(ref_doc)
		load_address_and_contact(self)

		ref_doc_contact_list = ref_doc.get("__onload").get("contact_list")
		opportunity_doc_contact_list = [
			contact
			for contact in self.get("__onload").get("contact_list")
			if contact not in ref_doc_contact_list
		]
		ref_doc_contact_list.extend(opportunity_doc_contact_list)
		ref_doc.set_onload("contact_list", ref_doc_contact_list)

		ref_doc_addr_list = ref_doc.get("__onload").get("addr_list")
		opportunity_doc_addr_list = [
			addr for addr in self.get("__onload").get("addr_list") if addr not in ref_doc_addr_list
		]
		ref_doc_addr_list.extend(opportunity_doc_addr_list)
		ref_doc.set_onload("addr_list", ref_doc_addr_list)

		self.set("__onload", ref_doc.get("__onload"))


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

		# get default taxes
		taxes = get_default_taxes_and_charges("Sales Taxes and Charges Template", company=quotation.company)
		if taxes.get("taxes"):
			quotation.update(taxes)

		quotation.run_method("set_missing_values")
		quotation.run_method("calculate_taxes_and_totals")
		quotation.custom_opportunity_hotels = source.name
		quotation.custom_opportunity_from = "Hotels"


	doclist = get_mapped_doc(
		"Opportunity Hotels",
		source_name,
		{
			"Opportunity Hotels": {
				"doctype": "Quotation",
				"field_map": {"opportunity_from": "quotation_to", "name": "enq_no"},
			},
			"Opportunity Item": {
				"doctype": "Quotation Item",
				"field_map": {
					# "parent": "prevdoc_docname",
					# "parenttype": "prevdoc_doctype",
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
		for fieldname in (
			"custom_hotels_opportunity",
			"custom_hotel_opportunity",
			"custom_opportunity_hotels",
		):
			if frappe.get_meta("Supplier Quotation").has_field(fieldname):
				target.set(fieldname, source.name)

	doclist = get_mapped_doc(
		"Opportunity Hotels",
		source_name,
		{
			"Opportunity Hotels": {"doctype": "Supplier Quotation"},
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
		for fieldname in (
			"custom_hotels_opportunity",
			"custom_hotel_opportunity",
			"custom_opportunity_hotels",
		):
			if frappe.get_meta("Request for Quotation").has_field(fieldname):
				target.set(fieldname, source.name)

	doclist = get_mapped_doc(
		"Opportunity Hotels",
		source_name,
		{
			"Opportunity Hotels": {"doctype": "Request for Quotation"},
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
		material_request.material_request_type = "Request for Quotation"
		for fieldname in ("custom_hotels_opportunity", "custom_hotel_opportunity"):
			if frappe.get_meta("Material Request").has_field(fieldname):
				material_request.set(fieldname, source.name)

	doclist = get_mapped_doc(
		"Opportunity Hotels",
		source_name,
		{
			"Opportunity Hotels": {
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
