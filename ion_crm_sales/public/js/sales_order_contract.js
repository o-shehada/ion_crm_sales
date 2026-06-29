frappe.ui.form.on("Sales Order", {
    refresh(frm) {
        if (frm.doc.docstatus !== 0 || frm.is_new()) {
            return;
        }

        frm.add_custom_button(
            __("Create Contract"),
            () => open_contract_dialog(frm),
            __("Actions"),
        );
    },
});

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
