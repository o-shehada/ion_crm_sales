# ion_crm_sales/ion_crm_sales/doc_events/survey_notifications.py

import frappe
from frappe import _
from frappe.utils import get_url_to_form

CHILD_DOCTYPE = "Technical Surveyor"  # child row doctype
SURVEYOR_FIELD = "surveyor"  # Link to User on child row
DEPARTMENT_FIELD = "department"  # department field on child row
TEMPLATE_FIELD = "template"  # Link to Technical Survey Template

SURVEY_FIELDS = {
    "Opportunity": {
        "surveyor_table": "custom_surveyors",
        "qa_table": "custom_technical_survey_template_table",
    },
    "Opportunity SM": {
        "surveyor_table": "custom_surveyors",
        "qa_table": "custom_technical_survey_template_table",
    },
    "Opportunity Hotels": {
        "surveyor_table": "custom_surveyors",
        "qa_table": "custom_technical_survey_template_table",
    },
    "Opportunity ISP": {
        "surveyor_table": "custom_surveyors",
        "qa_table": "custom_technical_survey_template_table",
    },
    "Opportunity Tenders": {
        "surveyor_table": "custom_surveyors",
        "qa_table": "custom_technical_survey_template_table",
    },
    "Hotspot": {
        "surveyor_table": "surveyor_table",
        "qa_table": "technical_survey_template_table",
    },
}


def on_before_save(doc, method):
    """Populate survey questions, notify new surveyors, and enforce completion."""
    fields = SURVEY_FIELDS.get(doc.doctype)
    if not fields:
        return

    surveyor_table = fields["surveyor_table"]
    qa_table = fields["qa_table"]
    current_rows = doc.get(surveyor_table) or []

    _populate_survey_questions(doc, current_rows, qa_table)
    _validate_survey_completion(doc, qa_table)

    previous = doc.get_doc_before_save()
    if not previous:
        added_rows = current_rows[:]
    else:
        previous_names = {row.name for row in (previous.get(surveyor_table) or [])}
        added_rows = [row for row in current_rows if row.name not in previous_names]

    for row in added_rows:
        if row.doctype != CHILD_DOCTYPE:
            continue

        user_id = row.get(SURVEYOR_FIELD)
        template_name = row.get(TEMPLATE_FIELD)
        if not user_id:
            continue

        recipient_email = _get_user_email(user_id)
        if recipient_email:
            _send_survey_notification(doc, row, recipient_email, template_name)


def _populate_survey_questions(doc, surveyor_rows, qa_table):
    """Rebuild questions from unique templates while preserving answers."""
    existing_answers = {}
    for qa_row in doc.get(qa_table) or []:
        key = (qa_row.get("template"), qa_row.get("question"))
        if qa_row.get("answer"):
            existing_answers[key] = qa_row.get("answer")

    templates_seen = set()
    ordered_templates = []
    for row in surveyor_rows:
        template = row.get(TEMPLATE_FIELD)
        if template and template not in templates_seen:
            templates_seen.add(template)
            ordered_templates.append(template)

    doc.set(qa_table, [])

    for template_name in ordered_templates:
        try:
            template_doc = frappe.get_doc("Technical Survey Template", template_name)
        except frappe.DoesNotExistError:
            continue

        for template_row in template_doc.get("technical_survey_template_table") or []:
            question = template_row.get("question")
            if not question:
                continue

            key = (template_name, question)
            doc.append(
                qa_table,
                {
                    "question": question,
                    "template": template_name,
                    "answer": existing_answers.get(key, ""),
                },
            )


def _validate_survey_completion(doc, qa_table):
    """Require every generated question to be answered before Surveyed."""
    previous = doc.get_doc_before_save()
    if (
        doc.get("workflow_state") != "Surveyed"
        or not previous
        or previous.get("workflow_state") == "Surveyed"
    ):
        return

    unanswered = [
        row for row in (doc.get(qa_table) or []) if not (row.get("answer") or "").strip()
    ]
    if unanswered:
        frappe.throw(
            _(
                "Complete all survey answers before moving to Surveyed. "
                "{0} question(s) remain unanswered."
            ).format(len(unanswered))
        )


def _send_survey_notification(doc, row, recipient_email, template_name):
    """Send an email notification to a surveyor with the template questions
    and a direct link to the source document."""

    dept = row.get(DEPARTMENT_FIELD) or _("(No Department)")
    doc_url = get_url_to_form(doc.doctype, doc.name)

    # Build the questions list for the email
    questions_html = ""
    if template_name:
        try:
            tpl_doc = frappe.get_doc("Technical Survey Template", template_name)
            questions = [
                r.get("question")
                for r in (tpl_doc.get("technical_survey_template_table") or [])
                if r.get("question")
            ]
            if questions:
                questions_html = "<ol>"
                for q in questions:
                    questions_html += f"<li>{frappe.utils.escape_html(q)}</li>"
                questions_html += "</ol>"
        except frappe.DoesNotExistError:
            pass

    subject = _("Survey Assignment – {doctype} {name}").format(
        doctype=doc.doctype, name=doc.name
    )

    email_content = frappe.render_template(
        """
        <p>You have been assigned as <b>Surveyor</b> for a survey.</p>
        <ul>
          <li><b>{{ doc_label }}:</b> {{ doc.name }}</li>
          <li><b>Department:</b> {{ dept }}</li>
          {% if template_name %}
          <li><b>Template:</b> {{ template_name }}</li>
          {% endif %}
        </ul>
        {% if questions_html %}
        <p><b>Questions to answer:</b></p>
        {{ questions_html }}
        {% endif %}
        <p>Please open the document to provide your answers:</p>
        <p><a href="{{ doc_url }}" style="background:#4CAF50;color:#fff;
           padding:10px 20px;text-decoration:none;border-radius:4px;
           display:inline-block;">Open {{ doc.doctype }}</a></p>
        """,
        {
            "doc": doc,
            "doc_label": doc.doctype,
            "dept": dept,
            "template_name": template_name,
            "questions_html": questions_html,
            "doc_url": doc_url,
        },
    )

    # --- Send via frappe.sendmail (queued, safe inside save cycle) ---
    try:
        frappe.sendmail(
            recipients=[recipient_email],
            subject=subject,
            message=email_content,
            reference_doctype=doc.doctype,
            reference_name=doc.name,
            delayed=True,
        )
    except Exception as e:
        frappe.log_error(
            title="Survey Notification Email Failed",
            message=f"Recipient={recipient_email} Doc={doc.name} Error={e}",
        )

    # --- Also create bell notification (in-app) ---
    try:
        frappe.get_doc(
            {
                "doctype": "Notification Log",
                "for_user": recipient_email,
                "type": "Alert",
                "subject": subject,
                "email_content": email_content,
                "document_type": doc.doctype,
                "document_name": doc.name,
                "from_user": frappe.session.user,
            }
        ).insert(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(
            title="Survey Notification Log Failed",
            message=f"Recipient={recipient_email} Doc={doc.name} Error={e}",
        )


def _get_user_email(user_id: str) -> str | None:
    """Return the user's email; fall back to user name if it looks like an email."""
    user = frappe.db.get_value("User", user_id, ["email", "name"], as_dict=True)
    if not user:
        return None
    if user.get("email"):
        return user["email"]
    # Many sites use email as User.name; fallback if it contains "@"
    if user.get("name") and "@" in user["name"]:
        return user["name"]
    return None


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_surveyors_by_department(doctype, txt, searchfield, start, page_len, filters):
    """Return User records whose linked Employee belongs to the given department.
    Used as a custom link query for surveyor child tables."""
    department = filters.get("department")
    if not department:
        return []

    return frappe.db.sql(
        """
        SELECT u.name, u.full_name
        FROM `tabUser` u
        INNER JOIN `tabEmployee` e ON e.user_id = u.name
        WHERE e.department = %(department)s
          AND e.status = 'Active'
          AND (u.name LIKE %(txt)s OR u.full_name LIKE %(txt)s)
        ORDER BY u.full_name
        LIMIT %(start)s, %(page_len)s
        """,
        {
            "department": department,
            "txt": f"%{txt}%",
            "start": start,
            "page_len": page_len,
        },
    )
