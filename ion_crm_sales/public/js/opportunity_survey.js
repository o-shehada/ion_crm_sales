// ion_crm_sales/public/js/opportunity_survey.js
//
// - Filters the Technical Survey Q&A table so each surveyor
//   only sees the questions from their assigned template.
// - Department-based surveyor filtering in the custom_surveyors table.
// - Locks the form for surveyors and provides a "Submit Survey Answers"
//   button that opens a dialog for entering answers.

frappe.ui.form.on(cur_frm.doctype, {
    refresh(frm) {
        setup_surveyor_filters(frm);
        setTimeout(() => {
            filter_survey_table(frm);
            lock_form_for_surveyor(frm);
        }, 500);
    },
    onload(frm) {
        setup_surveyor_filters(frm);
        setTimeout(() => {
            filter_survey_table(frm);
            lock_form_for_surveyor(frm);
        }, 800);
    },
});


// ─── Department-based surveyor filtering ────────────────────
function setup_surveyor_filters(frm) {
    frm.set_query("surveyor", "custom_surveyors", function(doc, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);
        if (!row.department) {
            return { filters: { "name": ["=", ""] } };
        }
        return {
            query: "ion_crm_sales.ion_crm_sales.doc_events.survey_notifications.get_surveyors_by_department",
            filters: { department: row.department }
        };
    });
}


frappe.ui.form.on("Technical Surveyor", {
    surveyor: function(frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);
        if (!row.department && row.surveyor) {
            frappe.model.set_value(cdt, cdn, "surveyor", "");
            frappe.show_alert({
                message: __("Please select Department first before selecting Surveyor."),
                indicator: "orange"
            });
        }
    },
    department: function(frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);
        if (!row.department) {
            frappe.model.set_value(cdt, cdn, "surveyor", "");
        }
    }
});


// ─── Lock form for surveyors + "Submit Survey Answers" button ───
function lock_form_for_surveyor(frm) {
    const user = frappe.session.user;

    const is_admin =
        user === "Administrator" ||
        (frappe.user_roles && frappe.user_roles.includes("System Manager"));

    const surveyor_manager = frm.doc.custom_surveyor_manager;
    const is_manager = is_admin || (user === surveyor_manager);

    if (is_manager) return;

    // Check if the current user is listed as a surveyor
    const surveyor_rows = frm.doc.custom_surveyors || [];
    const my_templates = new Set();
    let is_surveyor = false;

    for (const row of surveyor_rows) {
        if (row.surveyor === user) {
            is_surveyor = true;
            if (row.template) {
                my_templates.add(row.template);
            }
        }
    }

    if (!is_surveyor) return;

    // ── Lock the entire form ──────────────────────────────────
    const meta = frappe.get_meta(frm.doctype);
    (meta.fields || []).forEach(function(df) {
        frm.set_df_property(df.fieldname, "read_only", 1);
    });

    // Hide grid controls on all child tables
    $.each(frm.fields_dict, function(fieldname, field) {
        if (field.grid) {
            field.grid.wrapper.find(".grid-add-row").hide();
            field.grid.wrapper.find(".grid-remove-rows").hide();
            field.grid.wrapper.find(".grid-remove-all-rows").hide();
        }
    });

    // Remove Save
    frm.page.clear_primary_action();
    frm.page.clear_secondary_action();

    // ── Add "Submit Survey Answers" button only in Surveying state ──
    if (frm.doc.workflow_state !== "Surveying") return;
    if (my_templates.size === 0) return;

    frm.add_custom_button(__("Submit Survey Answers"), function() {
        open_survey_dialog(frm, my_templates);
    }).addClass("btn-primary");
}


// ─── Survey Answer Dialog ───────────────────────────────────
function open_survey_dialog(frm, my_templates) {
    // Collect the Q&A rows that belong to this surveyor's templates
    const qa_rows = (frm.doc.custom_technical_survey_template_table || []).filter(function(r) {
        return my_templates.has(r.template);
    });

    if (qa_rows.length === 0) {
        frappe.msgprint(__("No survey questions found for your assigned templates."));
        return;
    }

    // Build dialog fields: for each question, show a read-only heading + editable answer
    let fields = [];

    // Group by template for clarity
    let current_template = null;
    qa_rows.forEach(function(row, idx) {
        if (row.template !== current_template) {
            current_template = row.template;
            fields.push({
                fieldtype: "Section Break",
                label: current_template
            });
        }

        // Question label (read-only HTML)
        fields.push({
            fieldtype: "HTML",
            options: '<div style="font-weight:600; margin-bottom:4px; color: var(--text-color);">'
                + (idx + 1) + '. ' + frappe.utils.escape_html(row.question)
                + '</div>'
        });

        // Editable answer field
        fields.push({
            fieldtype: "Small Text",
            fieldname: "answer_" + row.name,
            label: __("Answer"),
            default: row.answer || ""
        });
    });

    let d = new frappe.ui.Dialog({
        title: __("Survey Answers"),
        size: "large",
        fields: fields,
        primary_action_label: __("Save Answers"),
        primary_action: function(values) {
            // Write answers back to the child table rows
            qa_rows.forEach(function(row) {
                let val = values["answer_" + row.name] || "";
                frappe.model.set_value(row.doctype, row.name, "answer", val);
            });

            // Save the document
            frm.dirty();
            frm.save().then(function() {
                frappe.show_alert({
                    message: __("Survey answers saved successfully."),
                    indicator: "green"
                });
            });

            d.hide();
        }
    });

    d.show();
}


// ─── Filter Q&A table visibility per surveyor ───────────────
function filter_survey_table(frm) {
    const user = frappe.session.user;

    const is_admin =
        user === "Administrator" ||
        (frappe.user_roles && frappe.user_roles.includes("System Manager"));

    const surveyor_manager = frm.doc.custom_surveyor_manager;
    const is_manager = is_admin || (user === surveyor_manager);

    const grid = frm.fields_dict.custom_technical_survey_template_table;
    if (!grid || !grid.grid) return;

    const grid_obj = grid.grid;

    if (is_manager) {
        show_all_rows(grid_obj);
        return;
    }

    const surveyor_rows = frm.doc.custom_surveyors || [];
    const my_templates = new Set();
    let is_surveyor = false;

    for (const row of surveyor_rows) {
        if (row.surveyor === user) {
            is_surveyor = true;
            if (row.template) {
                my_templates.add(row.template);
            }
        }
    }

    if (!is_surveyor || my_templates.size === 0) {
        show_all_rows(grid_obj, true);
        return;
    }

    // Hide rows not belonging to surveyor's template(s)
    const rows = grid_obj.grid_rows || [];
    for (const grid_row of rows) {
        if (!grid_row.doc) continue;
        const row_el = $(grid_row.row);
        if (my_templates.has(grid_row.doc.template)) {
            row_el.show();
        } else {
            row_el.hide();
        }
    }

    // Hide grid controls for surveyors
    grid_obj.wrapper.find(".grid-add-row").hide();
    grid_obj.wrapper.find(".grid-remove-rows").hide();
    grid_obj.wrapper.find(".grid-remove-all-rows").hide();
}


function show_all_rows(grid_obj, fully_read_only) {
    const rows = grid_obj.grid_rows || [];
    for (const grid_row of rows) {
        $(grid_row.row).show();
    }
    if (fully_read_only) {
        grid_obj.wrapper.find(".grid-add-row").hide();
        grid_obj.wrapper.find(".grid-remove-rows").hide();
        grid_obj.wrapper.find(".grid-remove-all-rows").hide();
    }
}
