// Copyright (c) 2026, ard.ly and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Opportunity Distributor", {
// 	refresh(frm) {

// 	},
// });

frappe.ui.form.on("Opportunity Distributor", {
	setup(frm) {
		frm.set_query("distributor", () => ({
			filters: {
				custom_is_distributor: 1,
			},
		}));
	},

	refresh(frm) {
		frm.trigger("render_distributor_address_and_contact");
	},

	distributor(frm) {
		frm.trigger("render_distributor_address_and_contact");
	},

	async render_distributor_address_and_contact(frm) {
		if (!frm.doc.distributor) {
			frappe.contacts.clear_address_and_contact(frm);
			return;
		}

		const distributor = frm.doc.distributor;
		const customer = await frappe.model.with_doc("Customer", distributor);

		// Ignore stale data if the distributor changed while the Customer loaded.
		if (frm.doc.distributor !== distributor) {
			return;
		}

		frappe.contacts.render_address_and_contact({
			doc: customer,
			fields_dict: frm.fields_dict,
		});

		$(frm.fields_dict.address_html.wrapper).find(".btn-address").remove();
		$(frm.fields_dict.contact_html.wrapper).find(".btn-contact").remove();
	},
});
