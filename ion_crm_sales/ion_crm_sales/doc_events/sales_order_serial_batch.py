"""Server wiring for the custom "Serial and Batch No" fields on Sales Order Item.

The fields mirror Delivery Note Item but were added through Customize Form, so they
carry a ``custom_`` prefix and none of erpnext's serial / batch handling applies to
them. This module supplies the validation, keeps the picked Serial and Batch Bundles
tied to their Sales Order, and hands the selection over to the stock documents that
get created from the order.

A Sales Order is not a stock voucher: nothing here moves stock or submits a bundle.
Anything that would be wrong to record is rejected; anything that is merely not in
stock yet is reported as a warning, since an order may well be placed before the
goods arrive.
"""

import frappe
from frappe import _
from frappe.utils import cint, cstr, flt, formatdate, get_link_to_form

USE_FIELDS = "custom_use_serial_no__batch_fields"
BUNDLE = "custom_serial_and_batch_bundle"
SERIAL_NO = "custom_serial_no"
BATCH_NO = "custom_batch_no"


def validate(doc, method=None):
    """Validate the Serial / Batch selection on every item row."""
    for row in doc.items:
        item = get_serial_batch_item(row.item_code)

        if not item.has_serial_no and not item.has_batch_no:
            clear_selection(row)
            continue

        if cint(row.get(USE_FIELDS)):
            row.set(BUNDLE, None)
            serial_nos = validate_serial_nos(doc, row, item)
            validate_batch_no(doc, row, item, serial_nos)
        else:
            row.set(SERIAL_NO, None)
            row.set(BATCH_NO, None)
            validate_bundle(doc, row, item)


def link_bundles(doc, method=None):
    """Stamp the Sales Order onto the bundles picked for it, once the name is final."""
    for row in doc.items:
        bundle = row.get(BUNDLE)
        if not bundle:
            continue

        current = frappe.db.get_value(
            "Serial and Batch Bundle",
            bundle,
            ["voucher_no", "voucher_detail_no", "posting_date", "docstatus"],
            as_dict=True,
        )

        if not current or current.docstatus != 0:
            continue

        values = {}
        if current.voucher_no != doc.name:
            values["voucher_no"] = doc.name
        if current.voucher_detail_no != row.name:
            values["voucher_detail_no"] = row.name
        if not current.posting_date:
            # The picker copies this from the parent, and a Sales Order has no posting date.
            values["posting_date"] = doc.transaction_date

        if values:
            frappe.db.set_value("Serial and Batch Bundle", bundle, values, update_modified=False)


def unlink_bundles(doc, method=None):
    """Drop the draft bundles picked for a Sales Order that is being cancelled or deleted."""
    bundles = frappe.get_all(
        "Serial and Batch Bundle",
        filters={"voucher_type": "Sales Order", "voucher_no": doc.name, "docstatus": 0},
        pluck="name",
    )

    for bundle in bundles:
        frappe.delete_doc("Serial and Batch Bundle", bundle, force=True, ignore_permissions=True)


def carry_serial_batch_to_target(source_name, target_doc, detail_field="so_detail"):
    """Copy the Serial / Batch selection from a Sales Order onto a mapped stock document.

    The target rows keep erpnext's core fieldnames, so the selection is written into
    ``serial_no`` / ``batch_no`` and ``use_serial_batch_fields`` is switched on. Bundles
    are not shared between the two documents: the entries are read out of the Sales
    Order's bundle and handed over as plain values, leaving the target free to build
    its own bundle when it is submitted.
    """
    target_rows = target_doc.get("items") or []
    if not target_rows or not frappe.get_meta(target_rows[0].doctype).has_field(
        "use_serial_batch_fields"
    ):
        return target_doc

    targets_by_source = {}
    for row in target_rows:
        if row.get(detail_field):
            targets_by_source.setdefault(row.get(detail_field), []).append(row)

    if not targets_by_source:
        return target_doc

    source_rows = frappe.get_all(
        "Sales Order Item",
        filters={"parent": source_name, "name": ("in", list(targets_by_source))},
        fields=["name", "idx", "parent", "item_code", USE_FIELDS, BUNDLE, SERIAL_NO, BATCH_NO],
    )

    for source in source_rows:
        serial_nos, batch_no, warning = resolve_selection(source)

        if warning:
            frappe.msgprint(warning, title=_("Serial / Batch No"), indicator="orange")

        if not serial_nos and not batch_no:
            continue

        for target in targets_by_source[source.name]:
            apply_selection(target, source, serial_nos, batch_no)

    return target_doc


def apply_selection(target, source, serial_nos, batch_no):
    """Write one Sales Order Item's selection onto a target stock row."""
    target.use_serial_batch_fields = 1
    target.serial_and_batch_bundle = None
    target.batch_no = batch_no or None

    if not serial_nos:
        target.serial_no = None
        return

    # A partial delivery / invoice takes the first n serial nos in the order they were listed.
    required = cint(abs(flt(target.get("stock_qty") or target.get("qty"))))
    if required and len(serial_nos) > required:
        frappe.msgprint(
            _("Item {0}: only the first {1} of {2} Serial Nos selected on {3} were carried over.").format(
                frappe.bold(source.item_code), required, len(serial_nos), frappe.bold(source.parent or "")
            ),
            title=_("Serial / Batch No"),
            indicator="orange",
        )
        serial_nos = serial_nos[:required]

    target.serial_no = "\n".join(serial_nos)


def resolve_selection(source):
    """Return ``(serial_nos, batch_no, warning)`` for one Sales Order Item row."""
    if cint(source.get(USE_FIELDS)):
        return get_serial_nos(source.get(SERIAL_NO)), source.get(BATCH_NO), None

    if not source.get(BUNDLE):
        return [], None, None

    entries = frappe.get_all(
        "Serial and Batch Entry",
        filters={"parent": source.get(BUNDLE)},
        fields=["serial_no", "batch_no"],
        order_by="idx",
    )

    serial_nos = [entry.serial_no for entry in entries if entry.serial_no]
    batch_nos = list(dict.fromkeys(entry.batch_no for entry in entries if entry.batch_no))

    if len(batch_nos) > 1:
        warning = _(
            "Item {0} was picked from {1} batches on the Sales Order. Only one Batch No fits a single row, "
            "so please pick the batches again here."
        ).format(frappe.bold(source.item_code), len(batch_nos))
        return serial_nos, None, warning

    return serial_nos, (batch_nos[0] if batch_nos else None), None


def validate_serial_nos(doc, row, item):
    """Check the Serial Nos listed on a row and return them as a list."""
    serial_nos = get_serial_nos(row.get(SERIAL_NO))
    if not serial_nos:
        return serial_nos

    if not item.has_serial_no:
        frappe.throw(
            _("Row #{0}: Item {1} is not maintained by Serial No.").format(
                row.idx, frappe.bold(row.item_code)
            )
        )

    duplicates = get_duplicates(serial_nos)
    if duplicates:
        frappe.throw(
            _("Row #{0}: Serial No {1} is listed more than once.").format(
                row.idx, frappe.bold(", ".join(duplicates))
            )
        )

    existing = {
        entry.name: entry
        for entry in frappe.get_all(
            "Serial No",
            filters={"name": ("in", serial_nos)},
            fields=["name", "item_code", "warehouse", "status"],
        )
    }

    missing = [serial_no for serial_no in serial_nos if serial_no not in existing]
    if missing:
        frappe.throw(
            _("Row #{0}: Serial No {1} does not exist.").format(
                row.idx, frappe.bold(", ".join(missing))
            )
        )

    wrong_item = [
        serial_no for serial_no in serial_nos if existing[serial_no].item_code != row.item_code
    ]
    if wrong_item:
        frappe.throw(
            _("Row #{0}: Serial No {1} does not belong to Item {2}.").format(
                row.idx, frappe.bold(", ".join(wrong_item)), frappe.bold(row.item_code)
            )
        )

    required = cint(abs(flt(row.stock_qty or row.qty)))
    if required and len(serial_nos) != required:
        frappe.throw(
            _("Row #{0}: {1} Serial Nos selected for Item {2}, but the ordered quantity is {3}.").format(
                row.idx, len(serial_nos), frappe.bold(row.item_code), required
            )
        )

    unavailable = [
        serial_no
        for serial_no in serial_nos
        if row.warehouse and existing[serial_no].warehouse != row.warehouse
    ]
    if unavailable:
        frappe.msgprint(
            _("Row #{0}: Serial No {1} is not in {2} right now.").format(
                row.idx, frappe.bold(", ".join(unavailable)), frappe.bold(row.warehouse)
            ),
            title=_("Serial / Batch No"),
            indicator="orange",
        )

    return serial_nos


def validate_batch_no(doc, row, item, serial_nos=None):
    """Check the Batch No on a row against the item, its expiry and the warehouse stock."""
    batch_no = row.get(BATCH_NO)
    if not batch_no:
        return

    if not item.has_batch_no:
        frappe.throw(
            _("Row #{0}: Item {1} is not maintained by Batch No.").format(
                row.idx, frappe.bold(row.item_code)
            )
        )

    batch = frappe.db.get_value(
        "Batch", batch_no, ["item", "disabled", "expiry_date"], as_dict=True
    )

    if not batch:
        # The link itself is checked later, by frappe's own validation.
        return

    if batch.item != row.item_code:
        frappe.throw(
            _("Row #{0}: Batch No {1} does not belong to Item {2}.").format(
                row.idx, frappe.bold(batch_no), frappe.bold(row.item_code)
            )
        )

    if cint(batch.disabled):
        frappe.throw(
            _("Row #{0}: Batch No {1} is disabled.").format(row.idx, frappe.bold(batch_no))
        )

    if batch.expiry_date and doc.transaction_date and batch.expiry_date < doc.transaction_date:
        frappe.throw(
            _("Row #{0}: Batch No {1} expired on {2}.").format(
                row.idx, frappe.bold(batch_no), formatdate(batch.expiry_date)
            )
        )

    mismatched = get_serial_nos_outside_batch(serial_nos, batch_no)
    if mismatched:
        frappe.throw(
            _("Row #{0}: Serial No {1} does not belong to Batch No {2}.").format(
                row.idx, frappe.bold(", ".join(mismatched)), frappe.bold(batch_no)
            )
        )

    warn_on_batch_shortage(row, batch_no)


def validate_bundle(doc, row, item):
    """Check the Serial and Batch Bundle picked for a row."""
    bundle_name = row.get(BUNDLE)
    if not bundle_name:
        return

    bundle = frappe.db.get_value(
        "Serial and Batch Bundle",
        bundle_name,
        [
            "item_code",
            "warehouse",
            "type_of_transaction",
            "total_qty",
            "is_cancelled",
            "voucher_no",
            "docstatus",
        ],
        as_dict=True,
    )

    if not bundle:
        # The link itself is checked later, by frappe's own validation.
        return

    link = get_link_to_form("Serial and Batch Bundle", bundle_name)

    if cint(bundle.is_cancelled) or bundle.docstatus == 2:
        frappe.throw(_("Row #{0}: Serial and Batch Bundle {1} is cancelled.").format(row.idx, link))

    if bundle.item_code != row.item_code:
        frappe.throw(
            _("Row #{0}: Serial and Batch Bundle {1} is for Item {2}, not {3}.").format(
                row.idx, link, frappe.bold(bundle.item_code), frappe.bold(row.item_code)
            )
        )

    if bundle.type_of_transaction != "Outward":
        frappe.throw(
            _("Row #{0}: Serial and Batch Bundle {1} is an {2} entry and cannot be sold.").format(
                row.idx, link, frappe.bold(_(bundle.type_of_transaction))
            )
        )

    if bundle.voucher_no and bundle.voucher_no != doc.name:
        frappe.throw(
            _("Row #{0}: Serial and Batch Bundle {1} already belongs to {2}.").format(
                row.idx, link, frappe.bold(bundle.voucher_no)
            )
        )

    required = abs(flt(row.stock_qty or row.qty))
    if required and abs(flt(bundle.total_qty)) != required:
        frappe.throw(
            _("Row #{0}: Serial and Batch Bundle {1} covers {2} units, but the ordered quantity is {3}.").format(
                row.idx, link, abs(flt(bundle.total_qty)), required
            )
        )

    if row.warehouse and bundle.warehouse and bundle.warehouse != row.warehouse:
        frappe.throw(
            _("Row #{0}: Serial and Batch Bundle {1} was picked from {2}, but the row ships from {3}.").format(
                row.idx, link, frappe.bold(bundle.warehouse), frappe.bold(row.warehouse)
            )
        )


def warn_on_batch_shortage(row, batch_no):
    """Report a batch that cannot cover the ordered quantity, without blocking the order."""
    if not row.warehouse:
        return

    from erpnext.stock.doctype.batch.batch import get_batch_qty

    available = flt(get_batch_qty(batch_no=batch_no, warehouse=row.warehouse, item_code=row.item_code))
    required = abs(flt(row.stock_qty or row.qty))

    if required and available < required:
        frappe.msgprint(
            _("Row #{0}: Batch No {1} has {2} of {3} units in {4}.").format(
                row.idx, frappe.bold(batch_no), available, required, frappe.bold(row.warehouse)
            ),
            title=_("Serial / Batch No"),
            indicator="orange",
        )


def get_serial_nos_outside_batch(serial_nos, batch_no):
    """Return the Serial Nos that are not part of ``batch_no``."""
    if not serial_nos:
        return []

    return frappe.get_all(
        "Serial No",
        filters={"name": ("in", serial_nos), "batch_no": ("!=", batch_no)},
        pluck="name",
    )


def get_serial_batch_item(item_code):
    """Return the serial / batch flags for an item, tolerating an empty row."""
    if not item_code:
        return frappe._dict(has_serial_no=0, has_batch_no=0)

    return frappe.get_cached_value(
        "Item", item_code, ["has_serial_no", "has_batch_no"], as_dict=True
    ) or frappe._dict(has_serial_no=0, has_batch_no=0)


def get_serial_nos(serial_no_text):
    """Split the Serial No text field the way erpnext does."""
    from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos as split_serial_nos

    if not cstr(serial_no_text).strip():
        return []

    return split_serial_nos(serial_no_text)


def get_duplicates(values):
    seen = set()
    duplicates = []

    for value in values:
        if value in seen and value not in duplicates:
            duplicates.append(value)
        seen.add(value)

    return duplicates


def clear_selection(row):
    """Blank every Serial / Batch field on a row that cannot carry one."""
    for fieldname in (BUNDLE, SERIAL_NO, BATCH_NO):
        row.set(fieldname, None)
