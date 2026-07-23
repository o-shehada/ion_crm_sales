def get_dashboard_data(data=None):
	return {
		"fieldname": "opportunity",
		"non_standard_fieldnames": {
			"Customer": "opportunity_name",
			"Material Request": "custom_dedicated_opportunity",
			"Request for Quotation": "custom_dedicated_opportunity",
			"Supplier Quotation": "custom_dedicated_opportunity",
		},
		"transactions": [
			{"items": ["Customer", "Quotation", "Material Request", "Request for Quotation", "Supplier Quotation"]},
		],
	}
