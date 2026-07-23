// ion_crm_sales/public/js/opportunity_survey.js
//
// - Filters the Technical Survey Q&A table so each surveyor
//   only sees the questions from their assigned template.
// - Department-based surveyor filtering in the configured surveyor table.
// - Locks the form for surveyors and provides a "Submit Survey Answers"
//   button that opens a dialog for entering answers.

const survey_field_config = {
    "Hotspot": {
        surveyors: "surveyor_table",
        questions: "technical_survey_template_table",
        manager: null,
    },
};

function get_survey_field_config(frm) {
    return survey_field_config[frm.doctype] || {
        surveyors: "custom_surveyors",
        questions: "custom_technical_survey_template_table",
        manager: "custom_surveyor_manager",
    };
}

frappe.ui.form.on(cur_frm.doctype, {
    refresh(frm) {
        setup_surveyor_filters(frm);
        add_opportunity_material_request_button(frm);
        show_next_workflow_statuses(frm);
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


// ─── Next workflow status indicator ─────────────────────────
function show_next_workflow_statuses(frm) {
    if (frm.is_new() || frm.is_dirty()) return;
    if (!frappe.workflow.get_state_fieldname(frm.doctype)) return;

    const state = frappe.workflow.get_state(frm.doc);
    const request_key = [frm.doctype, frm.doc.name, state].join(":");
    frm.__next_workflow_status_request = request_key;

    frappe.workflow.get_transitions(frm.doc).then(function(transitions) {
        // Ignore a response if the user navigated away or the workflow state changed.
        if (
            frm.__next_workflow_status_request !== request_key ||
            frappe.workflow.get_state(frm.doc) !== state
        ) {
            return;
        }

        const user = frappe.session.user;
        const available_transitions = transitions.filter(function(transition) {
            return (
                user === "Administrator" ||
                transition.allow_self_approval ||
                user !== frm.doc.owner
            );
        });
        const next_states = [...new Set(
            available_transitions
                .map((transition) => transition.next_state)
                .filter(Boolean)
        )];

        frm.dashboard.stats_area_row
            .find(".opportunity-next-status-indicator")
            .remove();

        let label;
        let color;
        if (next_states.length) {
            const translated_states = next_states.map((next_state) => __(next_state));
            label = next_states.length === 1
                ? __("Next available status: {0}", [translated_states[0]])
                : __("Next available statuses: {0}", [translated_states.join(" / ")]);
            color = "blue";
        } else {
            label = __("No next status available to you");
            color = "grey";
        }

        frm.dashboard
            .add_indicator(frappe.utils.escape_html(label), color)
            .addClass("opportunity-next-status-indicator");
    }).catch(function(error) {
        console.warn("Unable to load the next workflow status", error);
    });
}


// ─── Department-based surveyor filtering ────────────────────
function setup_surveyor_filters(frm) {
    const config = get_survey_field_config(frm);
    frm.set_query("surveyor", config.surveyors, function(doc, cdt, cdn) {
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
    const config = get_survey_field_config(frm);
    const user = frappe.session.user;

    const is_admin =
        user === "Administrator" ||
        (frappe.user_roles && frappe.user_roles.includes("System Manager"));

    const surveyor_manager = config.manager ? frm.doc[config.manager] : null;
    const is_manager = is_admin || (user === surveyor_manager);

    if (is_manager) return;

    // Check if the current user is listed as a surveyor
    const surveyor_rows = frm.doc[config.surveyors] || [];
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
        open_survey_dialog(frm, my_templates, config.questions);
    }).addClass("btn-primary");
}


// ─── Survey Answer Dialog ───────────────────────────────────
function open_survey_dialog(frm, my_templates, questions_field) {
    // Collect the Q&A rows that belong to this surveyor's templates
    const qa_rows = (frm.doc[questions_field] || []).filter(function(r) {
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
    const config = get_survey_field_config(frm);
    const user = frappe.session.user;

    const is_admin =
        user === "Administrator" ||
        (frappe.user_roles && frappe.user_roles.includes("System Manager"));

    const surveyor_manager = config.manager ? frm.doc[config.manager] : null;
    const is_manager = is_admin || (user === surveyor_manager);

    const grid = frm.fields_dict[config.questions];
    if (!grid || !grid.grid) return;

    const grid_obj = grid.grid;

    if (is_manager) {
        show_all_rows(grid_obj);
        return;
    }

    const surveyor_rows = frm.doc[config.surveyors] || [];
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

// ─── Opportunity (all variants): Customer Branch select + auto-fetch ID ────
// Shared by Opportunity, Opportunity SM, Opportunity Hotels, Opportunity Tenders,
// Opportunity ISP (all have opportunity_from/party_name + the two branch fields).
// "Hotspot" also loads this file (for the survey logic above) but has neither
// field, so every handler below is guarded with has_customer_branch_fields(frm).
frappe.ui.form.on(cur_frm.doctype, {
    refresh(frm) {
        if (has_customer_branch_fields(frm)) set_customer_branch_options(frm, true);
    },
    party_name(frm) {
        if (has_customer_branch_fields(frm)) set_customer_branch_options(frm, false);
    },
    opportunity_from(frm) {
        if (has_customer_branch_fields(frm)) set_customer_branch_options(frm, false);
    },
    custom_customer_branch(frm) {
        if (!has_customer_branch_fields(frm)) return;
        const branches = frm._customer_branches || [];
        const match = branches.find((b) => b.branch_customer === frm.doc.custom_customer_branch);
        frm.set_value("custom_customer_branch_id", match ? match.branch_id : "");
    },
});

function has_customer_branch_fields(frm) {
    return frappe.meta.has_field(frm.doctype, "custom_customer_branch")
        && frappe.meta.has_field(frm.doctype, "opportunity_from");
}

function set_customer_branch_options(frm, preserve_value) {
    const customer = frm.doc.opportunity_from === "Customer" ? frm.doc.party_name : null;

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


function add_opportunity_material_request_button(frm) {
    if (frm.doctype !== "Opportunity" || frm.is_new() || frm.doc.status === "Lost") return;

    frm.add_custom_button(
        __("Material Request"),
        () => {
            frappe.model.open_mapped_doc({
                method: "ion_crm_sales.opportunity.make_material_request",
                frm: frm,
            });
        },
        __("Create")
    );
}
