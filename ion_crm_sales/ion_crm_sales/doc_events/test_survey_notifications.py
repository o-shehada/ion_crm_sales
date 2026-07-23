from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ion_crm_sales.ion_crm_sales.doc_events import survey_notifications


class SurveyDocument:
    def __init__(self, doctype="Hotspot", previous=None, **values):
        self.doctype = doctype
        self.name = values.pop("name", "HOT-TEST-00001")
        self._previous = previous
        self._values = values

    def get(self, key, default=None):
        return self._values.get(key, default)

    def set(self, key, value):
        self._values[key] = value

    def append(self, key, value):
        self._values.setdefault(key, []).append(frappe._dict(value))

    def get_doc_before_save(self):
        return self._previous


class TestSurveyNotifications(FrappeTestCase):
    def test_hotspot_uses_its_survey_table_fields(self):
        self.assertEqual(
            survey_notifications.SURVEY_FIELDS["Hotspot"],
            {
                "surveyor_table": "surveyor_table",
                "qa_table": "technical_survey_template_table",
            },
        )

    @patch.object(survey_notifications, "_send_survey_notification")
    @patch.object(survey_notifications, "_get_user_email", return_value="surveyor@example.com")
    @patch.object(survey_notifications, "_populate_survey_questions")
    def test_new_hotspot_surveyor_is_notified_once(
        self, populate_questions, get_user_email, send_notification
    ):
        existing = frappe._dict(
            name="row-1",
            doctype="Technical Surveyor",
            surveyor="existing@example.com",
            template="Template A",
        )
        added = frappe._dict(
            name="row-2",
            doctype="Technical Surveyor",
            surveyor="new@example.com",
            template="Template B",
        )
        previous = SurveyDocument(surveyor_table=[existing], workflow_state="Surveying")
        doc = SurveyDocument(
            previous=previous,
            surveyor_table=[existing, added],
            technical_survey_template_table=[],
            workflow_state="Surveying",
        )

        survey_notifications.on_before_save(doc, None)

        populate_questions.assert_called_once_with(
            doc, [existing, added], "technical_survey_template_table"
        )
        get_user_email.assert_called_once_with("new@example.com")
        send_notification.assert_called_once_with(
            doc, added, "surveyor@example.com", "Template B"
        )

    def test_answers_are_preserved_when_questions_are_rebuilt(self):
        template = frappe._dict(
            technical_survey_template_table=[
                frappe._dict(question="Is power available?"),
                frappe._dict(question="How many access points?"),
            ]
        )
        doc = SurveyDocument(
            technical_survey_template_table=[
                frappe._dict(
                    template="Site Survey",
                    question="Is power available?",
                    answer="Yes",
                )
            ],
        )
        rows = [frappe._dict(template="Site Survey")]

        with patch.object(frappe, "get_doc", return_value=template):
            survey_notifications._populate_survey_questions(
                doc, rows, "technical_survey_template_table"
            )

        answers = {
            row.question: row.answer
            for row in doc.get("technical_survey_template_table")
        }
        self.assertEqual(answers["Is power available?"], "Yes")
        self.assertEqual(answers["How many access points?"], "")

    def test_surveyed_state_requires_all_answers(self):
        previous = SurveyDocument(workflow_state="Surveying")
        doc = SurveyDocument(
            previous=previous,
            workflow_state="Surveyed",
            technical_survey_template_table=[
                frappe._dict(question="Is power available?", answer="")
            ],
        )

        with self.assertRaises(frappe.ValidationError):
            survey_notifications._validate_survey_completion(
                doc, "technical_survey_template_table"
            )

    def test_surveyed_state_accepts_completed_answers(self):
        previous = SurveyDocument(workflow_state="Surveying")
        doc = SurveyDocument(
            previous=previous,
            workflow_state="Surveyed",
            technical_survey_template_table=[
                frappe._dict(question="Is power available?", answer="Yes")
            ],
        )

        survey_notifications._validate_survey_completion(
            doc, "technical_survey_template_table"
        )
