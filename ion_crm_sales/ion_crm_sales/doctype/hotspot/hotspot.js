// Copyright (c) 2025, ard.ly and contributors
// For license information, please see license.txt

frappe.provide("erpnext.crm");
erpnext.pre_sales.set_as_lost("Hotspot");
erpnext.sales_common.setup_selling_controller();


frappe.ui.form.on("Hotspot", {
    refresh: function (frm) {
        

        frm.trigger("handle_fields");

        var doc = frm.doc;
        const quotation_states = [
            "Surveyed",
            "Requirements Gathering",
            "Setup",
            "Active",
            "Closed",
        ];

        if (!frm.is_new() && quotation_states.includes(doc.workflow_state)) {
            frm.add_custom_button(__("Quotation"), function () {
                open_hotspot_quotation_in_new_tab(frm);
            }, __("Create"));
        }

        if (!frm.is_new() && doc.status !== "Lost") {
            if (frm.doc.hotspot_for != "Customer") {
                frm.add_custom_button(
                    __("Customer"),
                    function () {
                        frm.trigger("make_customer");
                    },
                    __("Create")
                );
            }

            let company_currency = erpnext.get_currency(frm.doc.company);
            if (company_currency != frm.doc.currency) {
                frm.add_custom_button(__("Fetch Latest Exchange Rate"), function () {
                    frm.trigger("currency");
                });
            }
        }


        frm.set_df_property('party_name', 'label', String(frm.doc.hotspot_for))

        if (['Requirements Gathering', 'Closed', 'Setup', 'Active'].includes(frm.doc.workflow_state)) {
            frm.set_df_property('requirements', 'hidden', false)
        } else {
            frm.set_df_property('requirements', 'hidden', true)
        }

    },

    hotspot_for(frm) {
        if (frm.doc.hotspot_for)
            frm.set_df_property('party_name', 'label', String(frm.doc.hotspot_for))
    },

    type(frm) {
        if (frm.doc.type == 'Based on Company Proposal') {
            frm.set_df_property('request', 'hidden', true)
        } else {
            frm.set_df_property('request', 'hidden', false)
        }
    },

    validate(frm) {
        frm.trigger("handle_state");
        frm.trigger("handle_fields");
    },

    get_item_data: function (frm, item, overwrite_warehouse = false) {
		if (item && !item.item_code) {
			return;
		}

		frappe.call({
			method: "erpnext.stock.get_item_details.get_item_details",
			args: {
				args: {
					item_code: item.item_code,
					from_warehouse: item.from_warehouse,
					warehouse: item.warehouse,
					doctype: frm.doc.doctype,
					buying_price_list: frm.doc.buying_price_list
						? frm.doc.buying_price_list
						: frappe.defaults.get_default("buying_price_list"),
					currency: frappe.defaults.get_default("Currency"),
					name: frm.doc.name,
					qty: item.qty || 1,
					stock_qty: item.stock_qty,
					company: frm.doc.company,
					conversion_rate: 1,
					material_request_type: frm.doc.material_request_type,
					plc_conversion_rate: 1,
					rate: item.rate,
					uom: item.uom,
					conversion_factor: item.conversion_factor,
					project: item.project,
				},
				overwrite_warehouse: overwrite_warehouse,
			},
			callback: function (r) {
				const d = item;
				let allow_to_change_fields = [
					"actual_qty",
					"projected_qty",
					"min_order_qty",
					"item_name",
					"stock_uom",
					"uom",
					"conversion_factor",
					"stock_qty",
				];

				if (overwrite_warehouse) {
					allow_to_change_fields.push("description");
				}

				if (!r.exc) {
					$.each(r.message, function (key, value) {
						if (!d[key] || allow_to_change_fields.includes(key)) {
							d[key] = value;
						}
					});

					if (d.price_list_rate != r.message.price_list_rate) {
						d.rate = 0.0;
						d.price_list_rate = r.message.price_list_rate;
						frappe.model.set_value(d.doctype, d.name, "rate", d.price_list_rate);
					}

					refresh_field("items");
				}
			},
		});
	},

    make_customer() {
        frappe.model.open_mapped_doc({
            method: "ion_crm_sales.ion_crm_sales.doctype.hotspot.hotspot.make_customer",
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
        let total = 0;
        frm.doc.items.forEach((item) => {
            total += item.amount;
        });

        frm.set_value({
            total: flt(total),
        });
    },

    handle_fields: function (frm) {
        frm.$wrapper.find("[data-fieldname='proposal_tab']").show();
        frm.$wrapper.find("[data-fieldname='survey_tab']").hide();

        if (frm.doc.type == 'Based on Company Proposal') {
            frm.set_df_property('request', 'hidden', true)
        } else {
            frm.set_df_property('request', 'hidden', false)
        }

        if (frm.doc.workflow_state == 'Qualifying' && frm.doc.type == 'Based on Company Proposal'){
            frm.$wrapper.find("[data-fieldname='proposal_tab']").show();
        }

        if (frm.doc.request && frm.doc.type == 'Based on Customer Request'){
            frm.$wrapper.find("[data-fieldname='proposal_tab']").show();
        }


        if (!['Qualifying', 'Proposed'].includes(frm.doc.workflow_state)){
            frm.$wrapper.find("[data-fieldname='survey_tab']").show();
        }

        if ((frm.doc.workflow_state == "Qualifying")) {
            switch (frm.doc.type) {
                case 'Based on Company Proposal':
                    if (frm.doc.description && frm.doc.items.length > 0) {
                        frm.doc.workflow_state = 'Proposed'
                    }
                    break;
                case 'Based on Customer Request':
                    if (frm.doc.description && frm.doc.items.length > 0) {
                        frm.doc.workflow_state = 'Proposed'
                    }
                    break;
                case 'Custom':
                    if (frm.doc.description && frm.doc.items.length > 0) {
                        frm.doc.workflow_state = 'Proposed'
                    }
                    break;
                default:
                    break;
            }
        }
    },

    handle_state: function (frm) {
        if (frm.doc.workflow_state == 'Requirements Gathering' && frm.doc.requirements) {
            frm.doc.workflow_state = 'Setup';
            frm.doc.refresh();
        }

        if (frm.doc.workflow_state == 'Setup') {
            const doc = frm.doc
            if (doc.stock_entry && doc.installation_note && doc.materials_received && doc.service_marketed && doc.cards_package && doc.free_line && doc.username != '' && doc.password != '') {
                frm.doc.workflow_state = 'Active';
                frm.doc.refresh();
            }
        }
    }
});


frappe.ui.form.on("Hotspot Item", {
    calculate: function (frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);
        frappe.model.set_value(cdt, cdn, "amount", flt(row.qty) * flt(row.rate));
        frm.trigger("calculate_total");
        // frappe.db.get_doc('Item Price', row.item).then((item_price) => {
        //     frappe.model.set_value(cdt, cdn, "rate", flt(item_price.price_list_rate));
        //     frappe.model.set_value(cdt, cdn, "amount", flt(row.qty) * flt(item_price.price_list_rate));
        //     // frappe.model.set_value(cdt, cdn, "base_rate", flt(frm.doc.conversion_rate) * flt(row.rate));
        //     // frappe.model.set_value(cdt, cdn, "base_amount", flt(frm.doc.conversion_rate) * flt(row.amount));
        //     frm.trigger("calculate_total");
        // });
    },
    qty: function (frm, cdt, cdn) {
        frm.trigger("calculate", cdt, cdn);
    },
    rate: function (frm, cdt, cdn) {
        frm.trigger("calculate", cdt, cdn);
    },
});

frappe.ui.form.on("Material Request Item", {
	qty: function (frm, doctype, name) {
		const item = locals[doctype][name];
		if (flt(item.qty) < flt(item.min_order_qty)) {
			frappe.msgprint(__("Warning: Material Requested Qty is less than Minimum Order Qty"));
		}
		frm.events.get_item_data(frm, item, false);
	},

	from_warehouse: function (frm, doctype, name) {
		const item = locals[doctype][name];
		frm.events.get_item_data(frm, item, false);
	},

	warehouse: function (frm, doctype, name) {
		const item = locals[doctype][name];
		frm.events.get_item_data(frm, item, false);
	},

	rate(frm, doctype, name) {
		const item = locals[doctype][name];
		item.amount = flt(item.qty) * flt(item.rate);
		frappe.model.set_value(doctype, name, "amount", item.amount);
		refresh_field("amount", item.name, item.parentfield);
	},

	item_code: function (frm, doctype, name) {
		const item = locals[doctype][name];
		item.rate = 0;
		item.uom = "";
		set_schedule_date(frm);
		frm.events.get_item_data(frm, item, true);
	},

	schedule_date: function (frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (row.schedule_date) {
			if (!frm.doc.schedule_date) {
				erpnext.utils.copy_value_in_all_rows(frm.doc, cdt, cdn, "items", "schedule_date");
			} else {
				set_schedule_date(frm);
			}
		}
	},

	conversion_factor: function (frm, doctype, name) {
		const item = locals[doctype][name];
		frm.events.get_item_data(frm, item, false);
	},
});


function open_hotspot_quotation_in_new_tab(frm) {
    const quotation_window = window.open(
        frappe.urllib.get_full_url("/app/quotation"),
        "_blank"
    );

    if (!quotation_window) {
        frappe.msgprint(__("Allow pop-ups for this site to open the Quotation in a new tab."));
        return;
    }

    const max_attempts = 120;
    let attempts = 0;
    const wait_for_frappe = window.setInterval(function () {
        attempts += 1;

        if (quotation_window.closed) {
            window.clearInterval(wait_for_frappe);
            return;
        }

        try {
            const target_frappe = quotation_window.frappe;
            if (target_frappe && target_frappe.model && target_frappe.model.open_mapped_doc) {
                window.clearInterval(wait_for_frappe);
                target_frappe.model.open_mapped_doc({
                    method: "ion_crm_sales.ion_crm_sales.doctype.hotspot.hotspot.make_quotation",
                    source_name: frm.doc.name,
                    freeze_message: __("Creating Quotation..."),
                });
                return;
            }
        } catch (error) {
            // The new tab can be temporarily inaccessible while it is navigating.
        }

        if (attempts >= max_attempts) {
            window.clearInterval(wait_for_frappe);
            frappe.msgprint(__("The Quotation tab did not finish loading. Please try again."));
        }
    }, 250);
}

function set_schedule_date(frm) {
	if (frm.doc.schedule_date) {
		erpnext.utils.copy_value_in_all_rows(
			frm.doc,
			frm.doc.doctype,
			frm.doc.name,
			"items",
			"schedule_date"
		);
	}
}