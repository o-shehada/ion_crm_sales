// ion_crm_sales/public/js/quotation_customer_branch.js
//
// Customer Branch select + auto-fetch ID for Quotation, mirroring the same
// behaviour on Opportunity (see opportunity_survey.js). When a Quotation is
// created from an Opportunity, Frappe's mapped-doc copy already carries
// custom_customer_branch / custom_customer_branch_id over automatically
// (identical fieldnames on both sides, no_copy not set). This file only
// handles the standalone case: picking a branch directly on a Quotation
// based on its own customer.

frappe.ui.form.on("Quotation", {
    refresh(frm) {
        set_customer_branch_options(frm, true);
    },
    party_name(frm) {
        set_customer_branch_options(frm, false);
    },
    quotation_to(frm) {
        set_customer_branch_options(frm, false);
    },
    custom_customer_branch(frm) {
        const branches = frm._customer_branches || [];
        const match = branches.find((b) => b.branch_customer === frm.doc.custom_customer_branch);
        frm.set_value("custom_customer_branch_id", match ? match.branch_id : "");
    },
});

function set_customer_branch_options(frm, preserve_value) {
    const customer = frm.doc.quotation_to === "Customer" ? frm.doc.party_name : null;

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
