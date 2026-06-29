import frappe


OPPORTUNITY_LAYOUT_SETTERS = (
	"Opportunity SM-main-field_order",
	"Opportunity Hotels-main-field_order",
	"Opportunity Tenders-main-field_order",
)


def remove_conflicting_opportunity_layout_setters():
	"""Keep app-owned Opportunity layouts controlled by their DocType JSON files."""
	frappe.db.delete("Property Setter", {"name": ("in", OPPORTUNITY_LAYOUT_SETTERS)})

	for doctype in ("Opportunity SM", "Opportunity Hotels", "Opportunity Tenders"):
		frappe.clear_cache(doctype=doctype)


def remove_legacy_sales_order_contract_scripts():
	"""Remove fixture scripts replaced by the app-owned template-agnostic flow."""
	frappe.db.delete("Client Script", {"name": "Sales Order Script"})
	frappe.db.delete("Server Script", {"name": "Sales Order"})
