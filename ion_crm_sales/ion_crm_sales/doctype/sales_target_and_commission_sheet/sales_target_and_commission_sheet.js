frappe.ui.form.on("Sales Target and Commission Sheet", {
	refresh(frm) {
		const canRecalc =
			["Draft", "Submitted", "Approved"].includes(frm.doc.status) && frm.doc.docstatus !== 2;
		if (canRecalc) {
			frm.add_custom_button(
				__("Recalculate Commission"),
				() => {
					frappe.call({
						method: "ion_crm_sales.ion_crm_sales.commission.api.recalculate_sheet",
						args: { name: frm.doc.name },
						freeze: true,
						callback: () => frm.reload_doc(),
					});
				},
				__("Actions"),
			);
		}
		if (frm.doc.status === "Approved" && frm.doc.docstatus === 1) {
			frm.add_custom_button(
				__("Post Accrual _"),
				() => {
					frappe.call({
						method: "ion_crm_sales.ion_crm_sales.commission.api.post_sheet_accrual",
						args: { name: frm.doc.name },
						freeze: true,
						callback: () => frm.reload_doc(),
					});
				},
				__("Actions"),
			);
		}
		frm.set_intro(
			__(
				'Use "Recalculate Commission" after invoices/payments/returns. "Post Accrual" creates the JE.',
			),
		);
	},
});
