from frappe import _


OPPORTUNITY_LINKS = {
	"Opportunity": "opportunity",
	"Opportunity SM": "custom_opportunity_sm",
	"Opportunity Hotels": "custom_opportunity_hotels",
	"Opportunity Tenders": "custom_opportunity_tenders",
	"Opportunity ISP": "custom_opportunity_isp",
}


def get_dashboard_data(data=None):
	data = data or {}
	data.setdefault("internal_links", {})
	data.setdefault("transactions", [])

	data["internal_links"].update(OPPORTUNITY_LINKS)
	add_reference_group(data)

	return data


def add_reference_group(data):
	reference_items = list(OPPORTUNITY_LINKS)

	for group in data["transactions"]:
		if group.get("label") == _("Reference"):
			for item in reference_items:
				if item not in group.get("items", []):
					group.setdefault("items", []).append(item)
			return

	data["transactions"].append({"label": _("Reference"), "items": reference_items})
