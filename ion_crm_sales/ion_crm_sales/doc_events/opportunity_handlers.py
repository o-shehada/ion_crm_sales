import frappe


def before_save(doc, method):

    if not doc.get_doc_before_save():
        return

    old_rows = {row.name: row for row in doc.get_doc_before_save().custom_deliverables}
    new_rows = {row.name: row for row in doc.custom_deliverables}

    added = [row for name, row in new_rows.items() if name not in old_rows]

    changed = []

    for name, row in new_rows.items():
        if (
            name in old_rows
            and row.as_dict().achieved != old_rows[name].as_dict().achieved
        ):
            changed.append(row)

    for addition in added:
        doc.append(
            "custom_audit_log",
            {
                "user": frappe.session.user,
                "step": f"Added Deliverable: {addition.deliverable}",
                "datetime": frappe.utils.now(),
            },
        )

    for change in changed:
        doc.append(
            "custom_audit_log",
            {
                "user": frappe.session.user,
                "step": f"Deliverable State: {change.deliverable}",
                "datetime": frappe.utils.now(),
            },
        )

    if doc.get_doc_before_save().workflow_state != doc.workflow_state:
        doc.append(
            "custom_audit_log",
            {
                "user": frappe.session.user,
                "step": doc.get_doc_before_save().workflow_state,
                "datetime": frappe.utils.now(),
            },
        )

        if doc.workflow_state == "Rejected":
            doc.status = "Lost"


def validate(doc, method):
    if not doc.custom_survey_template:
        return
