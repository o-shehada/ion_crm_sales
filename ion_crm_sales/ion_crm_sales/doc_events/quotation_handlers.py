import frappe


OPPORTUNITY_SOURCE_FIELDS = (
    ("opportunity", "Dedicated"),
    ("custom_opportunity_sm", "S&M"),
    ("opportunity_sm", "S&M"),
    ("custom_opportunity_hotels", "Hotels"),
    ("opportunity_hotels", "Hotels"),
    ("custom_opportunity_tenders", "Tenders"),
    ("opportunity_tenders", "Tenders"),
    ("custom_opportunity_isp", "ISP"),
    ("opportunity_isp", "ISP"),
)

OPPORTUNITY_SOURCE_DOCTYPES = (
    ("Opportunity", "Dedicated"),
    ("Opportunity SM", "S&M"),
    ("Opportunity Hotels", "Hotels"),
    ("Opportunity Tenders", "Tenders"),
    ("Opportunity ISP", "ISP"),
)


def before_insert(doc, method=None):
    set_opportunity_source(doc)


def validate(doc, method=None):
    set_opportunity_source(doc)


def set_opportunity_source(doc):
    if not frappe.get_meta("Quotation").has_field("custom_opportunity_from"):
        return

    if doc.get("custom_opportunity_from"):
        return

    for fieldname, source_label in OPPORTUNITY_SOURCE_FIELDS:
        if doc.get(fieldname):
            doc.custom_opportunity_from = source_label
            return

    if doc.get("enq_no"):
        for doctype, source_label in OPPORTUNITY_SOURCE_DOCTYPES:
            if frappe.db.exists(doctype, doc.enq_no):
                doc.custom_opportunity_from = source_label
                return


def get_source_opportunity(doc):
    for fieldname, _source_label in OPPORTUNITY_SOURCE_FIELDS:
        opportunity_name = doc.get(fieldname)
        if opportunity_name:
            doctype = get_opportunity_doctype_for_field(fieldname)
            if doctype and frappe.db.exists(doctype, opportunity_name):
                return frappe.get_cached_doc(doctype, opportunity_name)

    if doc.get("enq_no"):
        for doctype, _source_label in OPPORTUNITY_SOURCE_DOCTYPES:
            if frappe.db.exists(doctype, doc.enq_no):
                return frappe.get_cached_doc(doctype, doc.enq_no)

    return None


def get_opportunity_doctype_for_field(fieldname):
    field_doctype_map = {
        "opportunity": "Opportunity",
        "enq_no": "Opportunity",
        "custom_opportunity_sm": "Opportunity SM",
        "opportunity_sm": "Opportunity SM",
        "custom_opportunity_hotels": "Opportunity Hotels",
        "opportunity_hotels": "Opportunity Hotels",
        "custom_opportunity_tenders": "Opportunity Tenders",
        "opportunity_tenders": "Opportunity Tenders",
        "custom_opportunity_isp": "Opportunity ISP",
        "opportunity_isp": "Opportunity ISP",
    }
    return field_doctype_map.get(fieldname)


def get_or_create_sales_person_for_user(user):
    if not frappe.db.exists("User", user):
        return None

    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if employee:
        existing = frappe.db.get_value("Sales Person", {"employee": employee}, "name")
        if existing:
            return existing

    sales_person_name = frappe.db.get_value("User", user, "full_name") or user
    if frappe.db.exists("Sales Person", sales_person_name):
        return sales_person_name

    sales_person = frappe.new_doc("Sales Person")
    sales_person.sales_person_name = sales_person_name
    sales_person.enabled = 1
    sales_person.is_group = 0

    parent_sales_person = frappe.db.get_value(
        "Sales Person",
        {"is_group": 1},
        "name",
        order_by="lft asc",
    )
    if parent_sales_person:
        sales_person.parent_sales_person = parent_sales_person

    if employee:
        sales_person.employee = employee
        department = frappe.db.get_value("Employee", employee, "department")
        if department:
            sales_person.department = department

    sales_person.insert(ignore_permissions=True)
    return sales_person.name


def set_sales_team_contributor(doc, sales_person):
    sales_team_field = doc.meta.get_field("sales_team")
    if not sales_team_field or not sales_team_field.options:
        return

    existing_row = None
    for row in doc.get("sales_team") or []:
        if row.sales_person == sales_person:
            existing_row = row
        else:
            row.allocated_percentage = 0

    if not existing_row:
        existing_row = doc.append("sales_team", {"sales_person": sales_person})

    existing_row.allocated_percentage = 100
