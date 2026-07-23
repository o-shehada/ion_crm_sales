const ACCOUNT_MANAGER_ROLES = [
    "ISP Account Manager",
    "Tenders Account Manager",
    "Hotels Account Manager",
    "SM Account Manager",
    "Dedicated Account Manager",
];

const BA_SCENARIO_FIELDS = ["custom_service_category", "custom_ba_transaction_type"];

const BA_MANUAL_COMMISSION_LIMITS = {
    Dedicated: {"Old Accounts": 0.75, "Lead Acquisition": 3, Upsell: 2},
    Hotel: {"Old Accounts": 1, "Lead Acquisition": 5, Upsell: 3},
    "Hotspot - BA": {"Old Accounts": 2, "Lead Acquisition": 5, Upsell: 3},
    "Ultra - Malls": {"Old Accounts": 0.5, "Lead Acquisition": 5, Upsell: 3},
    ISPs: {"Old Accounts": 0.25, "Lead Acquisition": 0.375, Upsell: 0.25},
};

frappe.ui.form.on("Sales Order", {
    refresh(frm) {
        set_ba_scenario_field_access(frm);
        update_manual_commission_limit_description(frm);
        set_customer_branch_options(frm, true);

        if (
            frm.doc.docstatus === 1 &&
            frappe.model.can_create("Subscription")
        ) {
            frm.add_custom_button(
                __("Subscription"),
                () => open_new_subscription(frm),
                __("Create"),
            );
        }

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

    onload(frm) {
        set_ba_scenario_field_access(frm);
    },

    custom_service_category(frm) {
        update_manual_commission_limit_description(frm);
        set_single_sales_team_manual_commission(frm);
    },

    custom_ba_transaction_type(frm) {
        update_manual_commission_limit_description(frm);
        set_single_sales_team_manual_commission(frm);
    },

    customer(frm) {
        set_customer_branch_options(frm, false);
    },

    custom_customer_branch(frm) {
        sync_customer_branch_id(frm);
    },

    validate(frm) {
        validate_manual_commission_total(frm);
    },
});

frappe.ui.form.on("Sales Invoice", {
    refresh(frm) {
        set_ba_scenario_field_access(frm);
        update_manual_commission_limit_description(frm);
        set_customer_branch_options(frm, true);
    },

    onload(frm) {
        set_ba_scenario_field_access(frm);
    },

    custom_service_category(frm) {
        update_manual_commission_limit_description(frm);
        set_single_sales_team_manual_commission(frm);
    },

    custom_ba_transaction_type(frm) {
        update_manual_commission_limit_description(frm);
        set_single_sales_team_manual_commission(frm);
    },

    customer(frm) {
        set_customer_branch_options(frm, false);
    },

    custom_customer_branch(frm) {
        sync_customer_branch_id(frm);
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

function set_ba_scenario_field_access(frm) {
    const is_account_manager = ACCOUNT_MANAGER_ROLES.some((role) => frappe.user.has_role(role));

    BA_SCENARIO_FIELDS.forEach((fieldname) => {
        frm.set_df_property(fieldname, "hidden", is_account_manager ? 0 : 1);
        frm.set_df_property(fieldname, "read_only", is_account_manager ? 0 : 1);
        frm.set_df_property(fieldname, "reqd", is_account_manager ? 1 : 0);
    });
}

function open_new_subscription(frm) {
    const subscription_name = frappe.model.get_new_name("Subscription");
    const form_link = frappe.utils.get_form_link("Subscription", subscription_name);
    const defaults = new URLSearchParams({
        party_type: "Customer",
        party: frm.doc.customer,
        custom_type: frm.doc.custom_ba_transaction_type || "",
        custom_originating_doctype: "Sales Order",
        custom_originating_document: frm.doc.name,
    });

    window.open(`${form_link}?${defaults.toString()}`, "_blank", "noopener");
}

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

function set_single_sales_team_manual_commission(frm) {
    const rows = frm.doc.sales_team || [];
    const limit = get_manual_commission_limit(frm);

    if (rows.length !== 1 || limit === null) {
        return;
    }

    const row = rows[0];
    if (flt(row.custom_manual_commission_percentage) === limit) {
        return;
    }

    frappe.model
        .set_value(
            row.doctype,
            row.name,
            "custom_manual_commission_percentage",
            limit,
        )
        .then(() => update_manual_sales_team_allocation(frm));
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

// ─── Customer Branch select + auto-fetch ID (Sales Order / Sales Invoice) ───
// Both doctypes have a plain "customer" Link field (unlike Opportunity/Quotation's
// dynamic party_name). The value normally arrives pre-filled via the mapped-doc
// copy from Quotation/Sales Order (same fieldname, no_copy not set), but the
// Select control needs its `options` populated client-side to actually display
// an already-set value - otherwise it renders blank even though frm.doc holds it.
function set_customer_branch_options(frm, preserve_value) {
    if (!frappe.meta.has_field(frm.doctype, "custom_customer_branch")) {
        return;
    }

    const customer = frm.doc.customer;

    if (!customer) {
        frm._customer_branches = [];
        frm.set_df_property("custom_customer_branch", "options", "");
        frm.refresh_field("custom_customer_branch");
        if (!preserve_value) {
            frm.set_value("custom_customer_branch", "");
            frm.set_value("custom_customer_branch_id", "");
        }
        return;
    }

    frappe.call({
        method: "ion_crm_sales.opportunity.get_customer_branches",
        args: { customer },
        callback(r) {
            const branches = r.message || [];
            frm._customer_branches = branches;

            const options = [""].concat(branches.map((b) => b.branch_customer).filter(Boolean));
            frm.set_df_property("custom_customer_branch", "options", options.join("\n"));
            frm.refresh_field("custom_customer_branch");

            const current_value_still_valid = options.includes(frm.doc.custom_customer_branch);
            if (!preserve_value || !current_value_still_valid) {
                frm.set_value("custom_customer_branch", "");
                frm.set_value("custom_customer_branch_id", "");
            }
        },
    });
}

function sync_customer_branch_id(frm) {
    const branches = frm._customer_branches || [];
    const match = branches.find((b) => b.branch_customer === frm.doc.custom_customer_branch);
    frm.set_value("custom_customer_branch_id", match ? match.branch_id : "");
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
