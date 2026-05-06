# Copyright (c) 2025, ard.ly and contributors
# For license information, please see license.txt

"""
RMT Booking Lifecycle API
=========================

Endpoints (all via POST/GET to /api/method/...):

- POST  ion_crm_sales.ion_crm_sales.rmt_api.create_booking
- POST  ion_crm_sales.ion_crm_sales.rmt_api.confirm_booking
- POST  ion_crm_sales.ion_crm_sales.rmt_api.cancel_booking
- GET   ion_crm_sales.ion_crm_sales.rmt_api.get_booking
- POST  ion_crm_sales.ion_crm_sales.rmt_api.renew_booking
"""

import frappe
from frappe import _
from frappe.utils import nowdate, now_datetime, add_years


# ─── helpers ────────────────────────────────────────────────────────────────

DEFAULT_COMMISSION_PERCENT = 10  # fallback if distributor has no contract term


def _validate_required(data, fields):
    """Raise if any of *fields* are missing from *data*."""
    missing = [f for f in fields if not data.get(f)]
    if missing:
        frappe.throw(
            _("Missing required fields: {0}").format(", ".join(missing)),
            title=_("Validation Error"),
        )


def _get_distributor(distributor_id):
    """
    Look up a Distributor by its ``distributor_codeid`` field.
    Returns the Distributor doc or throws if not found / inactive.
    """
    distributors = frappe.get_all(
        "Distributor",
        filters={"distributor_codeid": distributor_id},
        fields=["name", "status", "distributor_name", "distributor_codeid"],
        limit=1,
    )
    if not distributors:
        frappe.throw(
            _("Distributor with ID {0} not found").format(distributor_id),
            title=_("Invalid Distributor"),
        )
    dist = distributors[0]
    if dist.get("status") != "Active":
        frappe.throw(
            _("Distributor {0} is not active (status: {1})").format(
                distributor_id, dist.get("status")
            ),
            title=_("Inactive Distributor"),
        )
    return dist


def _get_commission_percent(distributor_doc_name):
    """
    Derive the commission % for a distributor.
    Currently returns the default; extend this to read from a contract or
    Sales Partner commission table when available.
    """
    # Try to read from the linked Sales Partner's commission_rate
    sales_partner = frappe.db.get_value(
        "Distributor", distributor_doc_name, "sales_partner"
    )
    if sales_partner:
        rate = frappe.db.get_value("Sales Partner", sales_partner, "commission_rate")
        if rate:
            return float(rate)
    return DEFAULT_COMMISSION_PERCENT


def _compute_financials(package_price, payment_amount, commission_percent):
    """Return a dict with the derived financial fields."""
    company_share = package_price
    distributor_commission = round(package_price * (commission_percent / 100), 2)
    client_credit = round(max(payment_amount - package_price, 0), 2)
    return {
        "commission_percent": commission_percent,
        "company_share": company_share,
        "distributor_commission": distributor_commission,
        "client_credit": client_credit,
    }


def _booking_response(booking, include_financial=True):
    """Build the standard JSON response dict for a Booking doc."""
    resp = {
        "booking_id": booking.name,
        "client_name": booking.client_name,
        "client_national_id": booking.client_national_id,
        "client_phone": booking.client_phone,
        "location": booking.location,
        "package_id": booking.package_id,
        "status": booking.status,
        "contract_number": booking.contract_number,
        "distributor_id": booking.distributor_id,
        "created_at": str(booking.created_at) if booking.created_at else None,
        "confirmed_at": str(booking.confirmed_at) if booking.confirmed_at else None,
        "cancelled_at": str(booking.cancelled_at) if booking.cancelled_at else None,
    }
    if include_financial:
        resp["financial"] = {
            "package_price": booking.package_price,
            "payment_method": booking.payment_method,
            "payment_amount": booking.payment_amount,
            "payment_status": booking.payment_status,
            "client_credit": booking.client_credit,
            "company_share": booking.company_share,
            "distributor_commission": booking.distributor_commission,
            "commission_percent": booking.commission_percent,
        }
    if booking.status == "Failed":
        resp["refund"] = {
            "amount_refunded": booking.refunded_amount,
            "refund_method": booking.payment_method,
            "refunded_by": "ion",
        }
    return resp


# ─── API Endpoints ──────────────────────────────────────────────────────────


@frappe.whitelist(allow_guest=False)
def create_booking(**kwargs):
    """
    POST /api/method/ion_crm_sales.ion_crm_sales.rmt_api.create_booking

    Body (JSON):
    {
        "client_name": "Salem Al-Fitouri",
        "client_national_id": "152025041129",
        "client_phone": "+218922334455",
        "location": "Benghazi - Al Kwayfiya",
        "package_id": "HOME700",
        "package_price": 700,
        "payment_method": "cheque",
        "payment_amount": 1000,
        "disrupter_id": "D-ION-009"
    }
    """
    data = frappe._dict(kwargs)

    _validate_required(data, [
        "client_name",
        "client_national_id",
        "client_phone",
        "location",
        "package_id",
        "package_price",
        "payment_method",
        "payment_amount",
        "disrupter_id",
    ])

    # --- validate distributor ---
    dist = _get_distributor(data.disrupter_id)
    commission_pct = _get_commission_percent(dist.name)

    # --- financial calculations ---
    financials = _compute_financials(
        float(data.package_price),
        float(data.payment_amount),
        commission_pct,
    )

    # --- create Booking doc ---
    booking = frappe.new_doc("Booking")
    booking.client_name = data.client_name
    booking.client_national_id = data.client_national_id
    booking.client_phone = data.client_phone
    booking.location = data.location
    booking.package_id = data.package_id
    booking.package_price = float(data.package_price)
    booking.payment_method = data.payment_method
    booking.payment_amount = float(data.payment_amount)
    booking.payment_status = "Pending"
    booking.distributor_id = data.disrupter_id
    booking.status = "Pending"
    booking.created_at = now_datetime()

    # financial fields
    booking.commission_percent = financials["commission_percent"]
    booking.company_share = financials["company_share"]
    booking.distributor_commission = financials["distributor_commission"]
    booking.client_credit = financials["client_credit"]

    booking.insert(ignore_permissions=True)
    frappe.db.commit()

    return _booking_response(booking)


@frappe.whitelist(allow_guest=False)
def confirm_booking(**kwargs):
    """
    POST /api/method/ion_crm_sales.ion_crm_sales.rmt_api.confirm_booking

    Body (JSON):
    {
        "booking_id": "RMT-20250710-0001"
    }
    """
    data = frappe._dict(kwargs)
    _validate_required(data, ["booking_id"])

    booking = frappe.get_doc("Booking", data.booking_id)

    if booking.status != "Pending":
        frappe.throw(
            _("Booking {0} is not in Pending status (current: {1}). Cannot confirm.").format(
                booking.name, booking.status
            )
        )

    # --- update status ---
    booking.status = "Confirmed"
    booking.payment_status = "Confirmed"
    booking.confirmed_at = now_datetime()

    # --- assign contract number ---
    booking.contract_number = "ION-CT-{0}".format(
        str(frappe.db.count("Booking", {"status": "Confirmed"}) + 1).zfill(6)
    )

    booking.save(ignore_permissions=True)

    # --- create Customer if new ---
    _ensure_customer(booking)

    # --- create Sales Invoice ---
    si = _create_sales_invoice(booking)
    if si:
        booking.append("references", {
            "sales_invoice": si.name,
            "addition_date": nowdate(),
        })
        booking.save(ignore_permissions=True)

    frappe.db.commit()

    resp = _booking_response(booking)
    resp["contract"] = {
        "number": booking.contract_number,
        "start_date": nowdate(),
        "end_date": str(add_years(nowdate(), 1)),
    }
    return resp


@frappe.whitelist(allow_guest=False)
def cancel_booking(**kwargs):
    """
    POST /api/method/ion_crm_sales.ion_crm_sales.rmt_api.cancel_booking

    Body (JSON):
    {
        "booking_id": "RMT-20250710-0001",
        "reason": "No internet coverage on technical visit"
    }
    """
    data = frappe._dict(kwargs)
    _validate_required(data, ["booking_id"])

    booking = frappe.get_doc("Booking", data.booking_id)

    if booking.status in ("Cancelled", "Failed"):
        frappe.throw(
            _("Booking {0} is already {1}.").format(booking.name, booking.status)
        )

    booking.reason = data.get("reason", "")
    booking.cancelled_at = now_datetime()

    if booking.status == "Pending":
        # ---- cancelled before confirmation: no financial impact ----
        booking.status = "Cancelled"
        booking.save(ignore_permissions=True)
        frappe.db.commit()
        return _booking_response(booking)

    if booking.status == "Confirmed":
        # ---- cancelled after confirmation: refund required ----
        booking.status = "Failed"
        booking.refunded_amount = booking.payment_amount

        booking.save(ignore_permissions=True)

        # create Credit Note (return Sales Invoice)
        _create_credit_note(booking)

        frappe.db.commit()

        return _booking_response(booking)

    frappe.throw(_("Cannot cancel booking in status {0}").format(booking.status))


@frappe.whitelist(allow_guest=False, methods=["GET"])
def get_booking(**kwargs):
    """
    GET /api/method/ion_crm_sales.ion_crm_sales.rmt_api.get_booking?booking_id=RMT-...
    """
    data = frappe._dict(kwargs)
    _validate_required(data, ["booking_id"])

    booking = frappe.get_doc("Booking", data.booking_id)

    resp = _booking_response(booking)

    # include contract info if confirmed
    if booking.status in ("Confirmed", "Failed") and booking.contract_number:
        resp["contract"] = {
            "number": booking.contract_number,
            "start_date": str(booking.confirmed_at.date()) if booking.confirmed_at else None,
            "end_date": str(add_years(booking.confirmed_at.date(), 1)) if booking.confirmed_at else None,
        }

    # include references
    if booking.references:
        resp["references"] = [
            {"sales_invoice": r.sales_invoice, "date": str(r.addition_date)}
            for r in booking.references
        ]

    return resp


@frappe.whitelist(allow_guest=False)
def renew_booking(**kwargs):
    """
    POST /api/method/ion_crm_sales.ion_crm_sales.rmt_api.renew_booking

    Body (JSON):
    {
        "booking_id": "RMT-20250710-0001",
        "payment_method": "cash",
        "payment_amount": 700
    }

    Creates a new Booking for the same client/package with a fresh contract cycle.
    """
    data = frappe._dict(kwargs)
    _validate_required(data, ["booking_id"])

    original = frappe.get_doc("Booking", data.booking_id)

    if original.status != "Confirmed":
        frappe.throw(
            _("Only confirmed bookings can be renewed (current status: {0}).").format(
                original.status
            )
        )

    # Carry forward payment info; allow overrides
    payment_method = data.get("payment_method", original.payment_method)
    payment_amount = float(data.get("payment_amount", original.payment_amount))

    # Create the renewal as a brand-new booking
    new_booking_data = {
        "client_name": original.client_name,
        "client_national_id": original.client_national_id,
        "client_phone": original.client_phone,
        "location": original.location,
        "package_id": original.package_id,
        "package_price": original.package_price,
        "payment_method": payment_method,
        "payment_amount": payment_amount,
        "disrupter_id": original.distributor_id,
    }

    # Re-use create_booking to get full validation + financial calcs
    result = create_booking(**new_booking_data)

    # Return with a reference to the original
    result["renewed_from"] = original.name
    return result


# ─── ERP Backend Helpers ────────────────────────────────────────────────────


def _ensure_customer(booking):
    """Create a Customer record if one doesn't already exist for this client."""
    existing = frappe.db.exists("Customer", {"customer_name": booking.client_name})
    if existing:
        return existing

    customer = frappe.new_doc("Customer")
    customer.customer_name = booking.client_name
    customer.customer_type = "Individual"
    customer.customer_group = frappe.db.get_single_value(
        "Selling Settings", "customer_group"
    ) or "All Customer Groups"
    customer.territory = frappe.db.get_single_value(
        "Selling Settings", "territory"
    ) or "All Territories"
    customer.insert(ignore_permissions=True, ignore_mandatory=True)
    frappe.db.commit()
    return customer.name


def _create_sales_invoice(booking):
    """
    Create a draft Sales Invoice for the booking.
    Uses a generic item "Home Internet Service" (will use the first Item
    if that doesn't exist).
    """
    try:
        # Determine item to use
        item_code = booking.package_id
        if not frappe.db.exists("Item", item_code):
            # Fallback: check for a generic service item
            item_code = frappe.db.get_value(
                "Item", {"item_group": "Services"}, "name"
            )
        if not item_code:
            frappe.log_error(
                "RMT Booking {0}: No suitable Item found for Sales Invoice".format(
                    booking.name
                ),
                "RMT Integration",
            )
            return None

        customer_name = frappe.db.get_value(
            "Customer", {"customer_name": booking.client_name}, "name"
        )
        if not customer_name:
            customer_name = _ensure_customer(booking)

        si = frappe.new_doc("Sales Invoice")
        si.customer = customer_name
        si.posting_date = nowdate()
        si.due_date = nowdate()
        si.set_posting_time = 1
        si.rmt_booking = booking.name  # custom link if added later

        si.append("items", {
            "item_code": item_code,
            "qty": 1,
            "rate": booking.package_price,
            "description": "RMT Booking – {0} ({1})".format(
                booking.package_id, booking.location
            ),
        })

        si.insert(ignore_permissions=True, ignore_mandatory=True)
        frappe.db.commit()
        return si

    except Exception:
        frappe.log_error(frappe.get_traceback(), "RMT: Sales Invoice Creation Error")
        return None


def _create_credit_note(booking):
    """
    Create a Credit Note (return invoice) when a confirmed booking fails/is cancelled.
    """
    try:
        # Find original invoice(s)
        if not booking.references:
            frappe.log_error(
                "RMT Booking {0}: No Sales Invoice reference found for credit note".format(
                    booking.name
                ),
                "RMT Integration",
            )
            return None

        original_si_name = booking.references[0].sales_invoice
        if not frappe.db.exists("Sales Invoice", original_si_name):
            return None

        original_si = frappe.get_doc("Sales Invoice", original_si_name)

        customer_name = original_si.customer

        cn = frappe.new_doc("Sales Invoice")
        cn.customer = customer_name
        cn.posting_date = nowdate()
        cn.due_date = nowdate()
        cn.is_return = 1
        cn.return_against = original_si_name
        cn.set_posting_time = 1

        for item in original_si.items:
            cn.append("items", {
                "item_code": item.item_code,
                "qty": -1 * item.qty,
                "rate": item.rate,
                "description": "RMT Refund – {0}".format(booking.reason or "Cancelled"),
            })

        cn.insert(ignore_permissions=True, ignore_mandatory=True)
        frappe.db.commit()

        # Add the credit note to booking references
        booking.append("references", {
            "sales_invoice": cn.name,
            "addition_date": nowdate(),
        })
        booking.save(ignore_permissions=True)

        return cn

    except Exception:
        frappe.log_error(frappe.get_traceback(), "RMT: Credit Note Creation Error")
        return None
