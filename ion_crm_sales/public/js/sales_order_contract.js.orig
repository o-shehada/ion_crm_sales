const BA_MANUAL_COMMISSION_LIMITS = {
    Dedicated: {"Old Accounts": 0.75, "Lead Acquisition": 3, Upsell: 2},
    Hotel: {"Old Accounts": 1, "Lead Acquisition": 5, Upsell: 3},
    "Hotspot - BA": {"Old Accounts": 2, "Lead Acquisition": 5, Upsell: 3},
    "Ultra - Malls": {"Old Accounts": 0.5, "Lead Acquisition": 5, Upsell: 3},
    ISPs: {"Old Accounts": 0.25, "Lead Acquisition": 0.375, Upsell: 0.25},
};

frappe.ui.form.on("Sales Order", {
    refresh(frm) {
        update_manual_commission_limit_description(frm);

        if (
            frm.is_new() ||
            frm.doc.docstatus === 2 ||
            !frm.doc.custom_opportunity_from ||
            frm.doc.custom_contract
        ) {
            return;
        }

        frm.add_custom_button(
            __("Create Contract"),
            () => open_contract_dialog(frm),
        );
    },

    custom_service_category(frm) {
        update_manual_commission_limit_description(frm);
    },

    custom_ba_transaction_type(frm) {
        update_manual_commission_limit_description(frm);
    },

    validate(frm) {
        validate_manual_commission_total(frm);
    },
});

frappe.ui.form.on("Sales Invoice", {
    refresh(frm) {
        update_manual_commission_limit_description(frm);
    },

    custom_service_category(frm) {
        update_manual_commission_limit_description(frm);
    },

    custom_ba_transaction_type(frm) {
        update_manual_commission_limit_description(frm);
    },

    validate(frm) {
        validate_manual_commission_total(frm);
    },
});

frappe.ui.form.on("Sales Team", {
    custom_manual_commission_percentage(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        const limit = get_manual_commission_limit(frm);
        const value = flt(row.custom_manual_commission_percentage);

        if (limit !== null && value > limit) {
            frappe.msgprint(
                __("Manual Commission (%) cannot exceed {0}% for this scenario.", [limit]),
            );
            frappe.model
                .set_value(cdt, cdn, "custom_manual_commission_percentage", limit)
                .then(() => update_manual_sales_team_allocation(frm));
            return;
        }
        update_manual_sales_team_allocation(frm);
    },

    sales_team_add(frm) {
        update_manual_sales_team_allocation(frm);
    },

    sales_team_remove(frm) {
        update_manual_sales_team_allocation(frm);
    },
});

function update_manual_sales_team_allocation(frm) {
    const rows = frm.doc.sales_team || [];
    const total = rows.reduce(
        (sum, row) => sum + Math.max(flt(row.custom_manual_commission_percentage), 0),
        0,
    );

    if (!rows.length || total <= 0) {
        return;
    }

    let remainder = 100;
    rows.forEach((row, index) => {
        const allocation =
            index === rows.length - 1
                ? remainder
                : flt((flt(row.custom_manual_commission_percentage) / total) * 100, 6);

        remainder = flt(remainder - allocation, 6);
        frappe.model.set_value(
            row.doctype,
            row.name,
            "allocated_percentage",
            allocation,
        );
    });
}

function open_contract_dialog(frm) {
    const dialog = new frappe.ui.Dialog({
        title: __("Create Contract"),
        fields: [
            {
                fieldname: "contract_template",
                fieldtype: "Link",
                label: __("Contract Template"),
                options: "Contract Template",
                description: __("Optional. Select any configured Contract Template."),
            },
            {
                fieldname: "contract_terms",
                fieldtype: "Text Editor",
                label: __("Contract Terms"),
                description: __("Required when no Contract Template is selected."),
            },
        ],
        primary_action_label: __("Create"),
        primary_action(values) {
            if (!values.contract_template && !values.contract_terms) {
                frappe.msgprint(__("Select a Contract Template or enter Contract Terms."));
                return;
            }

            dialog.hide();
            frappe.call({
                method:
                    "ion_crm_sales.ion_crm_sales.doc_events.sales_order_handlers.create_contract",
                args: {
                    sales_order: frm.doc.name,
                    contract_template: values.contract_template,
                    contract_terms: values.contract_terms,
                },
                freeze: true,
                freeze_message: __("Creating Contract..."),
                callback(r) {
                    if (!r.message) {
                        return;
                    }

                    frm.reload_doc();
                    frappe.set_route("Form", "Contract", r.message);
                },
            });
        },
    });

    dialog.show();
}

function get_manual_commission_limit(frm) {
    const rates = BA_MANUAL_COMMISSION_LIMITS[frm.doc.custom_service_category];
    if (!rates) {
        return null;
    }
    return rates[frm.doc.custom_ba_transaction_type] ?? null;
}

function validate_manual_commission_total(frm) {
    const limit = get_manual_commission_limit(frm);
    const total = (frm.doc.sales_team || []).reduce(
        (sum, row) => sum + flt(row.custom_manual_commission_percentage),
        0,
    );

    if (limit !== null && total > 0 && Math.abs(total - limit) > 0.0001) {
        frappe.throw(
            __("Total Manual Commission (%) must equal {0}% for {1} / {2}.", [
                limit,
                frm.doc.custom_service_category,
                frm.doc.custom_ba_transaction_type,
            ]),
        );
    }
}

function update_manual_commission_limit_description(frm) {
    const grid = frm.fields_dict.sales_team?.grid;
    if (!grid) {
        return;
    }

    const limit = get_manual_commission_limit(frm);
    const description =
        limit === null
            ? __("Enter each person's share of the scenario commission rate.")
            : __("Maximum per row: {0}%. Entered row values must total {0}%.", [limit]);
    grid.update_docfield_property(
        "custom_manual_commission_percentage",
        "description",
        description,
    );
}
