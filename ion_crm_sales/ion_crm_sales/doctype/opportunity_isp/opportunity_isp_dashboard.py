def get_data():
	return {
		"fieldname": "custom_opportunity_isp",
		"non_standard_fieldnames": {
			"Material Request": "custom_isp_opportunity",
			"Request for Quotation": "custom_isp_opportunity",
			"Supplier Quotation": "custom_isp_opportunity",
		},
		"transactions": [
			{"items": ["Quotation", "Material Request", "Request for Quotation", "Supplier Quotation"]},
		],
	}
