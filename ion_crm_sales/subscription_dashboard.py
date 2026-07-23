from frappe import _


SALES_ORDER_LINKS = {
	"Sales Order": "custom_originating_document",
}


def get_dashboard_data(data=None):
	data = data or {}
	data.setdefault("internal_links", {})
	data.setdefault("transactions", [])

	data["internal_links"].update(SALES_ORDER_LINKS)
	add_selling_group(data)

	return data


def add_selling_group(data):
	for group in data["transactions"]:
		if group.get("label") == _("Selling"):
			items = group.setdefault("items", [])
			if "Sales Order" not in items:
				items.append("Sales Order")
			return

	data["transactions"].append({"label": _("Selling"), "items": ["Sales Order"]})
