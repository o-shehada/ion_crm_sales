import frappe
from ion_crm_sales.ion_crm_sales import doctype
from ion_crm_sales.technical_survey import load_template_fields
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from frappe.model.mapper import get_mapped_doc

from frappe.utils import nowdate, add_days, get_link_to_form, date_diff, today


@frappe.whitelist()
def make_sales_order_from_delivery_note(source_name, target_doc=None):
    def set_missing_values(source, target):
        target.transaction_date = nowdate()
        target.delivery_date = source.get("posting_date") or nowdate()
        target.status = "Draft"

        target.run_method("set_missing_values")
        target.run_method("calculate_taxes_and_totals")

    def update_item(source, target, source_parent):
        target.delivery_date = source_parent.get("posting_date") or nowdate()
        target.delivered_qty = 0
        target.billed_amt = 0
        target.produced_qty = 0
        target.returned_qty = 0
        target.ordered_qty = 0
        target.planned_qty = 0
        target.work_order_qty = 0
        target.prevdoc_docname = None
        target.prevdoc_doctype = None
        target.prevdoc_detail_docname = None

    doclist = get_mapped_doc(
        "Delivery Note",
        source_name,
        {
            "Delivery Note": {
                "doctype": "Sales Order",
                "validation": {"docstatus": ["=", 1]},
                "field_no_map": [
                    "amended_from",
                    "against_sales_invoice",
                    "billing_status",
                    "delivery_status",
                    "inter_company_reference",
                    "is_return",
                    "naming_series",
                    "per_billed",
                    "per_delivered",
                    "per_installed",
                    "posting_date",
                    "posting_time",
                    "return_against",
                    "status",
                    "title",
                ],
            },
            "Delivery Note Item": {
                "doctype": "Sales Order Item",
                "field_no_map": [
                    "against_sales_invoice",
                    "against_sales_order",
                    "billed_amt",
                    "delivered_qty",
                    "dn_detail",
                    "packed_qty",
                    "picked_qty",
                    "prevdoc_detail_docname",
                    "prevdoc_docname",
                    "prevdoc_doctype",
                    "returned_qty",
                    "serial_and_batch_bundle",
                    "serial_no",
                    "so_detail",
                    "target_warehouse",
                    "use_serial_batch_fields",
                ],
                "postprocess": update_item,
            },
            "Sales Taxes and Charges": {
                "doctype": "Sales Taxes and Charges",
                "reset_value": True,
            },
            "Sales Team": {
                "doctype": "Sales Team",
                "add_if_empty": True,
            },
            "Payment Schedule": {
                "doctype": "Payment Schedule",
            },
        },
        target_doc,
        set_missing_values,
    )

    return doclist

@frappe.whitelist()
def renew_subscription(subscription_name: str, renewal_window_days: int = 30):
    """
    Renew a Subscription only if it is expiring (within window) or expired.
    - Keeps party_type / party
    - Copies plans child table (if present)
    - Carries forward common settings
    - Retains dynamic origin (custom_originating_doctype + custom_originating_document)
    - New start_date = end_date + 1 day
    """
    src = frappe.get_doc("Subscription", subscription_name)

    end_date = src.get("end_date")
    if not end_date:
        frappe.throw("Cannot renew: Subscription has no end_date set.")

    days_to_expiry = date_diff(end_date, today())
    if days_to_expiry > renewal_window_days:
        frappe.throw(f"Not due for renewal: {days_to_expiry} days remain (window = {renewal_window_days} days).")

    new_start_date = add_days(end_date, 1)

    dst = frappe.new_doc("Subscription")
    dst.party_type = src.party_type
    dst.party = src.party
    dst.start_date = new_start_date

    # Carry forward common fields (extend as needed)
    for f in ("days_until_due", "sales_taxes_and_charges_template",
              "apply_additional_discount", "apply_discount_on",
              "additional_discount_percentage", "additional_discount_amount"):
        if src.meta.get_field(f):
            dst.set(f, src.get(f))

    # Copy plans (so billing keeps working)
    if src.meta.get_field("plans") and src.get("plans"):
        for row in src.get("plans"):
            data = {k: v for k, v in row.as_dict().items()
                    if k not in ("name", "parent", "parenttype", "parentfield", "idx", "docstatus")}
            dst.append("plans", data)

    dst.insert()
    frappe.db.commit()

    # Retain dynamic origin via custom fieldnames
    if src.get("custom_originating_doctype") and src.get("custom_originating_document"):
        frappe.db.set_value("Subscription", dst.name, "custom_originating_doctype", src.get("custom_originating_doctype"))
        frappe.db.set_value("Subscription", dst.name, "custom_originating_document", src.get("custom_originating_document"))

    dst.add_comment('Info', f"Renewed from {subscription_name}")
    return dst.name



@frappe.whitelist()
def bookings(data):
    if (len(data.get("client_national_id")) < 12): 
        return


    customer = None

    if (frappe.db.exists("Customer", data.get("client_name"))):
        customer = frappe.get_doc("Customer", data.get("client_name"))
    else:
        customer = frappe.get_doc({
            "doctype" : "Customer",
            "customer_type" : "Individual",
            "customer_name": data.get("client_name")
        })
        customer.insert(ignore_permissions=True)
            

    # customer.customer_name = data.get("client_name")
    # customer.customer_type = "Individual"

    doc = frappe.new_doc("Booking")
    doc.client_name = customer.customer_name
    doc.client_national_id = data.get("client_national_id")
    doc.client_phone = data.get("client_phone")
    doc.location = data.get("location")
    doc.package_id = data.get("package_id")
    doc.package_price = data.get("package_price")
    doc.payment_method = data.get("payment_method")
    doc.payment_amount = data.get("payment_amount")
    doc.distributor_id = data.get("distributor_id")
    doc.status = "Pending"

    doc.distributor_commission = float(frappe.get_doc('Sales Partner', data.get("distributor_id")).commission_rate) * float(data.get("package_price")) / 100


    if (data.get("payment_amount") > data.get("package_price")):
        doc.client_credit = data.get("payment_amount") - data.get("package_price")

    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return doc.as_dict()

@frappe.whitelist()
def bookings_confirm(data):
    doc = frappe.get_doc("Booking", data.get("booking_id"))
    doc.status = "Confirmed"
    doc.contract_number = data.get("contract_number")
    doc.confirmed_at = frappe.utils.now()
    doc.payment_status = "Received"
    doc.save(ignore_permissions=True)

    invoice = frappe.get_doc({
        "doctype": "Sales Invoice",
        "customer": doc.client_name,
        "posting_date": frappe.utils.nowdate(),
        "due_date": frappe.utils.nowdate(),
        "items": [
            {
                "item_code": doc.package_id,
                "rate": doc.package_price,
                "qty": 1,
                "warehouse": frappe.get_doc("Distributor", {
                    "sales_partner": doc.distributor_id
                }).warehouse
            }
        ],
        # "booking_reference": doc.name
    })

    invoice.insert(ignore_permissions=True)
    invoice.submit()

    doc.append("references", {
        "sales_invoice": invoice.name
    })

    doc.save(ignore_permissions=True)

    payment = get_payment_entry(
        dt="Sales Invoice",
        dn=invoice.name,
    )

    payment.mode_of_payment = doc.payment_method

    payment.reference_no = doc.name
    payment.reference_date = frappe.utils.nowdate()


    payment.insert(ignore_permissions=True)
    payment.submit()

    make_contract_from_rmt_template(party_name=doc.client_name, start_date=frappe.utils.nowdate(), submit=True)


def make_contract_from_rmt_template(party_name, start_date, submit=True):
    # 1) Create the contract doc
    contract = frappe.new_doc("Contract")
    contract.party_type = "Customer"          # e.g., "Customer"
    contract.party_name = party_name
    contract.start_date = start_date

    # 2) Set the template
    template_name = "RMT Contract"
    contract.contract_template = template_name

    # 3) Copy the terms from the template (server-side)
    # Try common fieldnames on the template
    terms = frappe.db.get_value("Contract Template", template_name, "contract_terms")
    if not terms:
        terms = frappe.db.get_value("Contract Template", template_name, "terms")
    if not terms:
        terms = frappe.db.get_value("Contract Template", template_name, "content")

    # Map to your contract’s terms field
    if "contract_terms" in contract.as_dict():
        contract.contract_terms = terms or ""
    elif "terms" in contract.as_dict():
        contract.terms = terms or ""
    elif "content" in contract.as_dict():
        contract.content = terms or ""

    # 4) Save/submit
    contract.insert(ignore_permissions=True)
    if submit:
        contract.submit()

    contract.is_signed = 1
    contract.signed_on = frappe.utils.nowdate()
    contract.signee = party_name
    contract.save(ignore_permissions=True)


@frappe.whitelist()
def bookings_cancel(data):
    doc = frappe.get_doc("Booking", data.get("booking_id"))

    if doc.status == "Pending":
        doc.status = "Cancelled"
        doc.reason = data.get("reason")
        doc.cancelled_at = frappe.utils.now()
    elif doc.status == "Confirmed":
        doc.status = "Failed"
        doc.reason = data.get("reason")
        doc.cancelled_at = frappe.utils.now()
        doc.refund_amount = data.get("refund_amount")
        create_credit_note(doc.references[0].sales_invoice, data.get("refund_amount"))
        
    
    doc.save(ignore_permissions=True)



def create_credit_note(original_invoice_name, return_amount=None):
    # Fetch original invoice
    original_invoice = frappe.get_doc("Sales Invoice", original_invoice_name)

    # Create a new Sales Invoice marked as return
    credit_note = frappe.get_doc({
        "doctype": "Sales Invoice",
        "customer": original_invoice.customer,
        "company": original_invoice.company,
        "posting_date": frappe.utils.nowdate(),
        "is_return": 1,  # ✅ This makes it a credit note
        "return_against": original_invoice.name,  # Link to original invoice
        "items": []
    })

    # Add items with negative qty or rate
    for item in original_invoice.items:
        qty_to_return = item.qty  # or partial qty
        if return_amount and return_amount < item.amount:
            # Partial return logic
            qty_to_return = return_amount / item.rate

        credit_note.append("items", {
                       "item_code": item.item_code,
            "rate": item.rate,
            "qty": -qty_to_return  # ✅ Negative qty for return
        })

    credit_note.insert(ignore_permissions=True)
    credit_note.submit()


@frappe.whitelist()
def bookings_get(booking_id):
    doc = frappe.get_doc("Booking", booking_id)
    return doc.as_dict()

@frappe.whitelist()
def save_survey(survey_data):
    # Validate and process the survey data
    if not survey_data.get("opportunity"):
        frappe.throw("Opportunity is required")
    if not survey_data.get("template"):
        frappe.throw("Template is required")
    if not survey_data.get("answers"):
        frappe.throw("Answers are required")

    doctype = survey_data.get("doctype", "Opportunity")
    custom_survey_field = survey_data.get("custom_survey_field", "custom_technical_survey")

    opportunity = frappe.get_doc(doctype, survey_data.get("opportunity"))

    survey = None
    survey_link = getattr(opportunity, custom_survey_field, None)

    if not survey_link:
        survey = frappe.new_doc("Technical Survey")
        survey.title = "Test Survey"
        survey.survey_template = survey_data.get("template")
        survey.save()
        survey.reload()
        load_template_fields(survey_data.get("template"), survey.name)
        survey.reload()
        setattr(opportunity, custom_survey_field, survey.name)
        opportunity.save(ignore_permissions=True)
    else:
        survey = frappe.get_doc("Technical Survey", survey_link)

    for field in survey.survey_fields:
        field.field_value = str(survey_data.get('answers').get(field.field_name))

    survey.save()
    return {"status": "success", "message": "Survey submitted successfully"}

@frappe.whitelist()
def submit_survey(opportunity_data):

    # Validate and process the opportunity data
    if not opportunity_data.get("opportunity"):
        frappe.throw("Opportunity is required")

    if not opportunity_data.get("doctype"):
        frappe.throw("Document Type is required")

    # Save the survey answers before submitting
    from ion_crm_sales.api import save_survey
    save_survey({
        "opportunity": opportunity_data.get("opportunity"),
        "template": opportunity_data.get("template"),
        "answers": opportunity_data.get("answers"),
        "doctype": opportunity_data.get("doctype"),
        "custom_survey_field": opportunity_data.get("custom_survey_field")
    })

    opportunity = frappe.get_doc(opportunity_data.get("doctype"), opportunity_data.get("opportunity"))

    if not opportunity:
        frappe.throw("Invalid Opportunity")
    
    opportunity.workflow_state = "Surveyed"
    opportunity.save(ignore_permissions=True)
    return {"status": "success", "message": "Survey submitted and saved successfully"}
