import frappe


QUOTATION_LINK_FIELDS = {
    "Opportunity": (("opportunity", "enq_no"), "Dedicated"),
    "Opportunity SM": (("opportunity_sm", "custom_opportunity_sm"), "S&M"),
    "Opportunity Hotels": (("opportunity_hotels", "custom_opportunity_hotels"), "Hotels"),
    "Opportunity Tenders": (("opportunity_tenders", "custom_opportunity_tenders"), "Tenders"),
    "Opportunity ISP": (("opportunity_isp", "custom_opportunity_isp"), "ISP"),
}


QUOTATION_MAPPERS = {
    "Opportunity": "ion_crm_sales.opportunity.make_quotation",
    "Opportunity SM": "ion_crm_sales.ion_crm_sales.doctype.opportunity_sm.opportunity_sm.make_quotation",
    "Opportunity Hotels": "ion_crm_sales.ion_crm_sales.doctype.opportunity_hotels.opportunity_hotels.make_quotation",
    "Opportunity Tenders": "ion_crm_sales.ion_crm_sales.doctype.opportunity_tenders.opportunity_tenders.make_quotation",
    "Opportunity ISP": "ion_crm_sales.ion_crm_sales.doctype.opportunity_isp.opportunity_isp.make_quotation",
}


def before_save(doc, method):

    if not doc.get_doc_before_save():
        return

    create_quotation_on_quote_workflow(doc)

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


def create_quotation_on_quote_workflow(doc):
    previous = doc.get_doc_before_save()
    if not previous or previous.workflow_state == doc.workflow_state:
        return

    if doc.workflow_state != "Accepted" or doc.doctype not in QUOTATION_MAPPERS:
        return

    if not doc.get("items"):
        frappe.throw("Add at least one item before using the Quote workflow action.")

    existing = get_existing_quotation(doc)
    if existing:
        doc.status = "Quotation"
        frappe.msgprint(f"Quotation already exists: {existing}")
        return

    mapper = frappe.get_attr(QUOTATION_MAPPERS[doc.doctype])
    quotation = mapper(doc.name)
    apply_quotation_links(doc, quotation)
    quotation.insert(ignore_permissions=True)

    doc.status = "Quotation"
    doc.append(
        "custom_audit_log",
        {
            "user": frappe.session.user,
            "step": f"Quotation Created: {quotation.name}",
            "datetime": frappe.utils.now(),
        },
    )
    frappe.msgprint(f"Quotation created: {quotation.name}")


def get_existing_quotation(doc):
    link_field = get_quotation_link_field(doc.doctype)
    if not link_field:
        return None

    return frappe.db.get_value(
        "Quotation",
        {link_field: doc.name, "docstatus": ["<", 2]},
        "name",
    )


def apply_quotation_links(doc, quotation):
    link_field = get_quotation_link_field(doc.doctype)
    if link_field:
        quotation.set(link_field, doc.name)

    _link_fields, source_label = QUOTATION_LINK_FIELDS.get(doc.doctype, (None, None))
    if source_label and frappe.get_meta("Quotation").has_field("custom_opportunity_from"):
        quotation.custom_opportunity_from = source_label


def get_quotation_link_field(doctype):
    link_fields, _source_label = QUOTATION_LINK_FIELDS.get(doctype, ((), None))
    quotation_meta = frappe.get_meta("Quotation")
    for fieldname in link_fields:
        if quotation_meta.has_field(fieldname):
            return fieldname
    return None


def validate(doc, method):
    if not doc.get("custom_survey_template"):
        return
