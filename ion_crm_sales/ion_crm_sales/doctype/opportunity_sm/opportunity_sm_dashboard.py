def get_data():
	return {
		"fieldname": "custom_opportunity_sm",
		"non_standard_fieldnames": {
			"Material Request": "custom_sm_opportunity",
			"Request for Quotation": "custom_sm_opportunity",
			"Supplier Quotation": "custom_sm_opportunity",
		},
		"transactions": [
			{"items": ["Quotation", "Material Request", "Request for Quotation", "Supplier Quotation"]},
		],
	}
