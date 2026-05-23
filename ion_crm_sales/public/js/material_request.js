frappe.ui.form.on("Material Request", {
	refresh(frm) {
		if (
			frm.doc.docstatus === 1 &&
			frm.doc.material_request_type === "Request for Quotation"
		) {
			frm.add_custom_button(
				__("Request for Quotation"),
				() => frm.trigger("make_request_for_quotation_from_rfq_type"),
				__("Create")
			);
		}
	},

	make_request_for_quotation_from_rfq_type(frm) {
		frappe.model.open_mapped_doc({
			method: "ion_crm_sales.material_request.make_request_for_quotation",
			frm: frm,
		});
	},
});
