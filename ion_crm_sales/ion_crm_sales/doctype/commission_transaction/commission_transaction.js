// Copyright (c) 2025, ard.ly and contributors
// For license information, please see license.txt

frappe.ui.form.on("Commission Transaction", {
	refresh(frm) {
        if (frm.doc.commission_status === 'Unpaid') { // DocStatus 0 is Draft
            // Add the custom button
            frm.add_custom_button(__('Create Commission Payment'), function() {
                // Confirm action with the user (optional, but recommended)
                frappe.confirm(
                    'Do you want to create a Commission Payment for this transaction?',
                    function() {
                        // Call the server-side Python function
                        frappe.call({
                            method: 'ion_crm_sales.ion_crm_sales.doctype.commission_transaction.commission_transaction.create_commission_payment',
                            args: {
                                source_docname: frm.doc.name
                            },
                            callback: function(r) {
                                if (r.message) {
                                    // On success, notify user and redirect to the new document
                                    frappe.msgprint('Commission Payment created successfully!');
                                    // The r.message contains the name of the new Commission Payment
                                    frappe.set_route('Form', 'Commission Payment', r.message);
                                }
                            }
                        });
                    }
                );
            })
        }
	},
});
