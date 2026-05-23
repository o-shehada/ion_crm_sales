// Copyright (c) 2025, ard.ly and contributors
// For license information, please see license.txt

frappe.provide("erpnext.crm");
frappe.provide("ion_crm_sales");
erpnext.pre_sales.set_as_lost("Opportunity SM");
erpnext.sales_common.setup_selling_controller();

frappe.ui.form.on("Opportunity SM", {
	onload: function (frm) {
		frm.trigger("setup_queries");
	},

	party_name: function (frm) {
		if (frm.doc.opportunity_from !== "Customer") {
			return;
		}

		frappe.call({
			method: "frappe.client.get_value",
			args: {
				doctype: "Customer",
				filters: {
					name: frm.doc.party_name,
				},
				fieldname: ["custom_nationality"],
			},
			callback: function (r) {
				if (r.message && r.message.custom_nationality) {
					frappe.model.set_value(
						"Opportunity SM",
						frm.doc.name,
						"custom_nationality",
						r.message.custom_nationality,
					);
				}
			},
		});
	},

	custom_warehouse: function (frm) {
		frm.doc.items.forEach(function (item) {
			if (item.item_code) {
				frappe.call({
					method: "frappe.client.get_value",
					args: {
						doctype: "Bin",
						filters: {
							item_code: item.item_code,
							warehouse: frm.doc.custom_warehouse,
						},
						fieldname: ["valuation_rate", "actual_qty"],
					},
					callback: function (r) {
						if (r.message && r.message.valuation_rate) {
							let valuation_rate = flt(r.message.valuation_rate);
							frappe.model.set_value(
								item.doctype,
								item.name,
								"custom_valuation_rate",
								valuation_rate,
							);
							frappe.model.set_value(
								item.doctype,
								item.name,
								"custom_valuation_rate_company_currency",
								flt(frm.doc.conversion_rate) * valuation_rate,
							);
							frappe.model.set_value(
								item.doctype,
								item.name,
								"custom_availability",
								r.message.actual_qty >= item.qty ? "Available" : "Unavailable",
							);
						} else {
							frappe.model.set_value(
								item.doctype,
								item.name,
								"custom_availability",
								"Unavailable",
							);
							frappe.show_alert(
								"Valuation rate not found for " + item.item_code,
								"orange",
							);
						}
					},
				});
			}
		});
	},

	opportunity_from: function (frm) {
		switch (frm.doc.opportunity_from) {
			case "Customer":
				frm.set_value("sales_stage", "Opportunity");
				break;
			case "Prospect":
				frm.set_value("sales_stage", "Prospecting");
				break;
		}
	},

	custom_material_type: function (frm) {
		frappe.model.clear_table(frm.doc, "items");
		frm.refresh_field("items");
		frm.trigger("setup_queries");
	},

	setup_queries: function (frm) {
		frm.set_query("item_code", "items", function () {
			let filters = { is_sales_item: 1 };
			if (frm.doc.custom_material_type) {
				filters.custom_material_type = frm.doc.custom_material_type;
			}

			return {
				query: "erpnext.controllers.queries.item_query",
				filters: filters,
			};
		});
	},

	refresh: function (frm) {
		var doc = frm.doc;
		frm.trigger("setup_queries");

		if (!frm.is_new() && doc.status !== "Lost") {
			if (doc.items) {
				frm.add_custom_button(
				    __("Supplier Quotation"),
				    function () {
				        frm.trigger("make_supplier_quotation");
				    },
				    __("Create")
				);
				frm.add_custom_button(
				    __("Request For Quotation"),
				    function () {
				        frm.trigger("make_request_for_quotation");
				    },
				    __("Create")
				);
			}

			if (frm.doc.opportunity_from == "Customer") {
				frm.add_custom_button(
					__("Issue"),
					function () {
						frm.trigger("create_issue");
					},
					__("Create"),
				);
			}

			if (frm.doc.opportunity_from != "Customer") {
				frm.add_custom_button(
					__("Customer"),
					function () {
						frm.trigger("make_customer");
					},
					__("Create"),
				);
			}

			frm.add_custom_button(
				__("Quotation"),
				function () {
					frm.trigger("create_quotation");
				},
				__("Create"),
			);

			frm.add_custom_button(
				__("Material Request"),
				function () {
					frm.trigger("create_material_request");
				},
				__("Create"),
			);

			let company_currency = erpnext.get_currency(frm.doc.company);
			if (company_currency != frm.doc.currency) {
				frm.add_custom_button(__("Fetch Latest Exchange Rate"), function () {
					frm.trigger("currency");
				});
			}
		}

		if (!frm.is_new()) {
			frappe.contacts.render_address_and_contact(frm);
			// frm.trigger('render_contact_day_html');
		} else {
			frappe.contacts.clear_address_and_contact(frm);
		}

		if (frm.doc.opportunity_type === "Sales") {
			frm.set_value("opportunity_type", "Dedicated");
		}

		if (!frm.doc.custom_request) {
			frm.set_df_property("custom_requirements", "read_only", 1);
		}
	},

	validate: function (frm) {
		if (frm.doc.custom_request) {
			frm.set_df_property("custom_requirements", "read_only", 0);
		}

		if (
			frm.doc.custom_requirements &&
			frm.doc.workflow_state !== "Scoping" &&
			frm.doc.workflow_state === "Requirements Gathering"
		) {
			frm.set_value("workflow_state", "Scoping");
			frm.refresh();
		}

		if (
			frm.doc.custom_scope_description &&
			frm.doc.custom_deliverables &&
			frm.doc.workflow_state === "Scoping"
		) {
			frm.set_value("workflow_state", "Qualifying");
			frm.refresh();
		}
	},

	make_supplier_quotation: function (frm) {
		frappe.model.open_mapped_doc({
			method: "ion_crm_sales.ion_crm_sales.doctype.opportunity_sm.opportunity_sm.make_supplier_quotation",
			frm: frm,
		});
	},

	make_request_for_quotation: function (frm) {
		frappe.model.open_mapped_doc({
			method: "ion_crm_sales.ion_crm_sales.doctype.opportunity_sm.opportunity_sm.make_request_for_quotation",
			frm: frm,
		});
	},

	create_quotation() {
		frappe.model.open_mapped_doc({
			method: "ion_crm_sales.ion_crm_sales.doctype.opportunity_sm.opportunity_sm.make_quotation",
			frm: cur_frm,
		});
	},

	make_customer() {
		frappe.model.open_mapped_doc({
			method: "erpnext.crm.doctype.opportunity.opportunity.make_customer",
			frm: cur_frm,
		});
	},

	create_issue() {
		frappe.model.open_mapped_doc({
			method: "ion_crm_sales.ion_support.support.triggers.create_issue",
			frm: cur_frm,
			args: {
				issue_from_dt: "Opportunity SM",
			},
		});
	},

	create_material_request() {
		frappe.model.open_mapped_doc({
			method: "ion_crm_sales.ion_crm_sales.doctype.opportunity_sm.opportunity_sm.make_material_request",
			frm: cur_frm,
		});
	},

	onload_post_render: function (frm) {
		frm.get_field("items").grid.set_multiple_add("item_code", "qty");
	},

	change_grid_labels: function (frm) {
		let company_currency = erpnext.get_currency(frm.doc.company);
		frm.set_currency_labels(["base_rate", "base_amount"], company_currency, "items");
		frm.set_currency_labels(["rate", "amount"], frm.doc.currency, "items");

		let item_grid = frm.fields_dict.items.grid;
		$.each(["base_rate", "base_amount"], function (i, fname) {
			if (frappe.meta.get_docfield(item_grid.doctype, fname))
				item_grid.set_column_disp(fname, frm.doc.currency != company_currency);
		});
		frm.refresh_fields();
	},

	calculate_total: function (frm) {
		let total = 0,
			base_total = 0;
		frm.doc.items.forEach((item) => {
			total += item.amount;
			base_total += item.base_amount;
		});

		frm.set_value({
			total: flt(total),
			base_total: flt(base_total),
		});
	},
});

frappe.ui.form.on("Opportunity Item", {
	calculate: function (frm, cdt, cdn) {
		let row = frappe.get_doc(cdt, cdn);
		frappe.model.set_value(cdt, cdn, "amount", flt(row.qty) * flt(row.rate));
		frappe.model.set_value(
			cdt,
			cdn,
			"base_rate",
			flt(frm.doc.conversion_rate) * flt(row.rate),
		);
		frappe.model.set_value(
			cdt,
			cdn,
			"base_amount",
			flt(frm.doc.conversion_rate) * flt(row.amount),
		);
		frm.trigger("calculate_total");

		if (row.item_code && frm.doc.custom_warehouse) {
			frappe.call({
				method: "frappe.client.get_value",
				args: {
					doctype: "Bin",
					filters: {
						item_code: row.item_code,
						warehouse: frm.doc.custom_warehouse,
					},
					fieldname: ["valuation_rate", "actual_qty"],
				},
				callback: function (r) {
					if (r.message && r.message.valuation_rate) {
						let valuation_rate = flt(r.message.valuation_rate);
						frappe.model.set_value(cdt, cdn, "custom_valuation_rate", valuation_rate);
						frappe.model.set_value(
							cdt,
							cdn,
							"custom_valuation_rate_company_currency",
							flt(frm.doc.conversion_rate) * valuation_rate,
						);
						frappe.model.set_value(
							cdt,
							cdn,
							"custom_availability",
							r.message.actual_qty >= row.qty ? "Available" : "Unavailable",
						);
					} else {
						frappe.model.set_value(cdt, cdn, "custom_valuation_rate", flt(0));
						frappe.model.set_value(
							cdt,
							cdn,
							"custom_valuation_rate_company_currency",
							flt(0),
						);
						frappe.model.set_value(cdt, cdn, "custom_availability", "Unavailable");
						console.log(
							"Valuation rate not found for item: " +
								row.item_code +
								" in warehouse: " +
								frm.doc.custom_warehouse,
						);
					}
				},
			});
		}
	},
	item_code: function (frm, cdt, cdn) {
		let row = frappe.get_doc(cdt, cdn);
		if (!row.item_code) {
			return;
		}

		frappe.call({
			method: "erpnext.crm.doctype.opportunity.opportunity.get_item_details",
			args: {
				item_code: row.item_code,
			},
			callback: function (r) {
				if (r.message) {
					$.each(r.message, function (key, value) {
						frappe.model.set_value(cdt, cdn, key, value);
					});
					refresh_field("image_view", row.name, "items");
				}

				if (frm.doc.custom_price_list) {
					frappe.call({
						method: "frappe.client.get_value",
						args: {
							doctype: "Item Price",
							filters: {
								item_code: row.item_code,
								price_list: frm.doc.custom_price_list,
							},
							fieldname: "price_list_rate",
						},
						callback: function (response) {
							if (response && response.message) {
								frappe.model.set_value(cdt, cdn, "rate", response.message.price_list_rate);
							}
						},
					});
				}
			},
		});
	},
	qty: function (frm, cdt, cdn) {
		frm.trigger("calculate", cdt, cdn);
	},
	rate: function (frm, cdt, cdn) {
		frm.trigger("calculate", cdt, cdn);
	},
});

ion_crm_sales.OpportunitySM = class OpportunitySM extends frappe.ui.form.Controller {
	refresh() {
		this.show_notes();
		this.show_activities();
	}

	show_notes() {
		const crm_notes = new erpnext.utils.CRMNotes({
			frm: this.frm,
			notes_wrapper: $(this.frm.fields_dict.notes_html.wrapper),
		});
		crm_notes.refresh();
	}

	show_activities() {
		const crm_activities = new erpnext.utils.CRMActivities({
			frm: this.frm,
			open_activities_wrapper: $(this.frm.fields_dict.open_activities_html.wrapper),
			all_activities_wrapper: $(this.frm.fields_dict.all_activities_html.wrapper),
			form_wrapper: $(this.frm.wrapper),
		});
		crm_activities.refresh();
	}
};

extend_cscript(cur_frm.cscript, new ion_crm_sales.OpportunitySM({ frm: cur_frm }));
