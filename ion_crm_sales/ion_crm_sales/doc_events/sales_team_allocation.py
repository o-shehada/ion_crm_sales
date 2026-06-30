import frappe
from frappe.utils import flt

from ion_crm_sales.ion_crm_sales.commission.config import BA_RATES, SALES_ITEM_GROUPS

SALES_SERVICE_CATEGORIES = set(SALES_ITEM_GROUPS.values())

BA_CATEGORY_BY_SERVICE_CATEGORY = {
    "Dedicated": "DEDICATED",
    "Hotel": "HOTEL",
    "ISPs": "ISPS",
    "Hotspot - BA": "HOTSPOT",
    "Ultra - Malls": "ULTRA_MALLS",
}
BA_TRANSACTION_RATE_KEYS = {
    "Old Accounts": "old",
    "Lead Acquisition": "new",
    "Upsell": "upsell",
}


def normalize_sales_team_allocation_for_sales_categories(doc, method=None):
    """Validate manual commission rates and derive ERPNext allocation."""
    rows = doc.get("sales_team") or []
    if not rows:
        return

    manual_rates = [flt(row.get("custom_manual_commission_percentage")) for row in rows]
    if any(rate < 0 for rate in manual_rates):
        frappe.throw("Manual Commission (%) cannot be negative.")

    manual_total = sum(manual_rates)
    if manual_total > 0:
        limit = get_manual_commission_limit(doc)
        if limit is not None:
            if any(rate > limit + 0.000001 for rate in manual_rates):
                frappe.throw(
                    f"Each Manual Commission (%) value must not exceed {limit:g}% for this scenario."
                )
            if abs(manual_total - limit) > 0.0001:
                frappe.throw(
                    f"Total Manual Commission (%) must equal {limit:g}% for "
                    f"{doc.get('custom_service_category')} / {doc.get('custom_ba_transaction_type')}."
                )
        _set_normalized_allocations(rows, manual_rates, manual_total)
        return

    # Preserve the previous behavior for Sales categories when no manual
    # commission rates have been entered.
    if not _is_sales_service_document(doc):
        return

    total = sum(flt(row.get("allocated_percentage")) for row in rows)
    if abs(total - 100.0) < 0.0001:
        return

    _set_normalized_allocations(rows, [1.0] * len(rows), float(len(rows)))


def get_manual_commission_limit(doc):
    category = BA_CATEGORY_BY_SERVICE_CATEGORY.get(doc.get("custom_service_category"))
    transaction_key = BA_TRANSACTION_RATE_KEYS.get(doc.get("custom_ba_transaction_type"))
    if not category or not transaction_key:
        return None

    rates = BA_RATES[category]
    if transaction_key == "new":
        return round((rates["new"] + rates["upsell"]) * 100.0, 6)
    return round(rates[transaction_key] * 100.0, 6)


def _set_normalized_allocations(rows, weights, total):
    remainder = 100.0
    for row, weight in zip(rows[:-1], weights[:-1]):
        allocation = round(weight / total * 100.0, 6)
        row.allocated_percentage = allocation
        remainder -= allocation
    rows[-1].allocated_percentage = round(remainder, 6)


def _is_sales_service_document(doc):
    category = doc.get("custom_service_category")
    if category in SALES_SERVICE_CATEGORIES:
        return True

    for item in doc.get("items") or []:
        item_group = item.get("item_group")
        if not item_group and item.get("item_code"):
            item_group = frappe.db.get_value("Item", item.item_code, "item_group")
        if item_group in SALES_SERVICE_CATEGORIES:
            return True

    return False
