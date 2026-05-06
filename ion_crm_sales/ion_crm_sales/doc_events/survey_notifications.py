# ion_crm_sales/ion_crm_sales/doc_events/survey_notifications.py

import frappe
from frappe import _
from frappe.utils import get_url_to_form

TABLE_FIELD = "custom_surveyors"  # child table field on parent doctypes
CHILD_DOCTYPE = "Technical Surveyor"  # child row doctype
SURVEYOR_FIELD = "surveyor"  # Link to User on child row
DEPARTMENT_FIELD = "department"  # department field on child row
TEMPLATE_FIELD = "template"  # Link to Technical Survey Template
QA_TABLE_FIELD = "custom_technical_survey_template_table"  # Q&A table on Opportunity


def on_before_save(doc, method):
    """On save:
    1. Populate custom_technical_survey_template_table with questions from all
       templates selected in custom_surveyors.
    2. Send notification email to newly added surveyors with their template
       questions and a link to the Opportunity.

    Works for: Opportunity, Opportunity SM, Opportunity Hotels, Opportunity Tenders.
    """
    current_rows = doc.get(TABLE_FIELD) or []

    # --- Step 1: Populate the Q&A table with template questions -----------
    _populate_survey_questions(doc, current_rows)

    # --- Step 2: Detect newly added surveyor rows and notify --------------
    prev = doc.get_doc_before_save()
    if not prev:
        added_rows = current_rows[:]  # first save: all present rows are "added"
    else:
        previous_rows = prev.get(TABLE_FIELD) or []
        prev_names = {r.name for r in previous_rows}
        added_rows = [r for r in current_rows if r.name not in prev_names]

    if not added_rows:
        return

    for row in added_rows:
        if row.doctype != CHILD_DOCTYPE:
            continue

        user_id = row.get(SURVEYOR_FIELD)
        template_name = row.get(TEMPLATE_FIELD)
        if not user_id:
            continue

        recipient_email = _get_user_email(user_id)
        if not recipient_email:
            continue

        _send_survey_notification(doc, row, recipient_email, template_name)


def _populate_survey_questions(doc, surveyor_rows):
    """Clear and re-populate the Q&A table from all unique templates in
    custom_surveyors.  Preserves existing answers if the question+template
    combination already exists."""

    # Build a lookup of existing answers so we don't lose them on re-save.
    existing_answers = {}
    for qa_row in doc.get(QA_TABLE_FIELD) or []:
        key = (qa_row.get("template"), qa_row.get("question"))
        if qa_row.get("answer"):
            existing_answers[key] = qa_row.get("answer")

    # Collect unique templates from surveyor rows
    templates_seen = set()
    ordered_templates = []
    for row in surveyor_rows:
        tpl = row.get(TEMPLATE_FIELD)
        if tpl and tpl not in templates_seen:
            templates_seen.add(tpl)
            ordered_templates.append(tpl)

    # Clear the Q&A table and re-build from templates
    doc.set(QA_TABLE_FIELD, [])

    for tpl_name in ordered_templates:
        try:
            tpl_doc = frappe.get_doc("Technical Survey Template", tpl_name)
        except frappe.DoesNotExistError:
            continue

        for tpl_row in tpl_doc.get("technical_survey_template_table") or []:
            question = tpl_row.get("question")
            if not question:
                continue

            key = (tpl_name, question)
            doc.append(
                QA_TABLE_FIELD,
                {
                    "question": question,
                    "template": tpl_name,
                    "answer": existing_answers.get(key, ""),
                },
            )


def _send_survey_notification(doc, row, recipient_email, template_name):
    """Send an email notification to a surveyor with the template questions
    and a direct link to the Opportunity."""

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
    Used as a custom link query for the surveyor field in custom_surveyors table."""
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
