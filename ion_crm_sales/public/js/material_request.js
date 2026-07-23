frappe.ui.form.on("Material Request", {
	refresh(frm) {
		if (
			frm.doc.docstatus === 1 &&
			frm.doc.material_request_type === "Request for Quotation"
		) {
			frm.add_custom_button(
				__("Request for Quotation"),
				() => frm.trigger("make_request_for_quotation_from_rfq_type"),
				__("Create")
			);
		}

		show_next_workflow_statuses(frm);
	},

	make_request_for_quotation_from_rfq_type(frm) {
		frappe.model.open_mapped_doc({
			method: "ion_crm_sales.material_request.make_request_for_quotation",
			frm: frm,
		});
	},
});


// ─── Next workflow status indicator (Connections tab / Stats) ───
// Mirrors the indicator shown on Opportunity (see opportunity_survey.js):
// shows which workflow states the current user can move this document to next.
function show_next_workflow_statuses(frm) {
	if (frm.is_new() || frm.is_dirty()) return;
	if (!frappe.workflow.get_state_fieldname(frm.doctype)) return;

	const state = frappe.workflow.get_state(frm.doc);
	const request_key = [frm.doctype, frm.doc.name, state].join(":");
	frm.__next_workflow_status_request = request_key;

	frappe.workflow.get_transitions(frm.doc).then(function (transitions) {
		// Ignore a response if the user navigated away or the workflow state changed.
		if (
			frm.__next_workflow_status_request !== request_key ||
			frappe.workflow.get_state(frm.doc) !== state
		) {
			return;
		}

		const user = frappe.session.user;
		const available_transitions = transitions.filter(function (transition) {
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
			.find(".material-request-next-status-indicator")
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
			.addClass("material-request-next-status-indicator");
	}).catch(function (error) {
		console.warn("Unable to load the next workflow status", error);
	});
}
