def get_data():
	return {
		"fieldname": "custom_opportunity_hotels",
		"non_standard_fieldnames": {
			"Material Request": "custom_hotels_opportunity",
			"Request for Quotation": "custom_hotels_opportunity",
			"Supplier Quotation": "custom_hotels_opportunity",
		},
		"transactions": [
			{"items": ["Quotation", "Material Request", "Request for Quotation", "Supplier Quotation"]},
		],
	}
