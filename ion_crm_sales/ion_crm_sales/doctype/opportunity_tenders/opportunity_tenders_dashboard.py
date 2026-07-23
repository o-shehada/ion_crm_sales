def get_data():
	return {
		"fieldname": "custom_opportunity_tenders",
		"non_standard_fieldnames": {
			"Material Request": "custom_tenders_opportunity",
			"Request for Quotation": "custom_tenders_opportunity",
			"Supplier Quotation": "custom_tenders_opportunity",
		},
		"transactions": [
			{"items": ["Quotation", "Material Request", "Request for Quotation", "Supplier Quotation"]},
		],
	}
