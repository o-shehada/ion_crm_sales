frappe.ui.form.on("Delivery Note", {
	refresh(frm) {
		if (
			frm.doc.docstatus === 1 &&
			!frm.doc.is_return &&
			frm.doc.status !== "Closed" &&
			frappe.model.can_create("Sales Order")
		) {
			frm.add_custom_button(
				__("Sales Order"),
				() => {
					frappe.model.open_mapped_doc({
						method: "ion_crm_sales.api.make_sales_order_from_delivery_note",
						frm: frm,
					});
				},
				__("Create")
			);

			frm.page.set_inner_btn_group_as_primary(__("Create"));
		}
	},
});
