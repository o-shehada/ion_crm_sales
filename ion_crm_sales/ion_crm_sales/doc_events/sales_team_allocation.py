import frappe
from frappe.utils import flt

from ion_crm_sales.ion_crm_sales.commission.config import SALES_ITEM_GROUPS

SALES_SERVICE_CATEGORIES = set(SALES_ITEM_GROUPS.values())


def normalize_sales_team_allocation_for_sales_categories(doc, method=None):
    """Auto-fill allocation only where custom Sales commission ignores it."""
    rows = doc.get("sales_team") or []
    if not rows or not _is_sales_service_document(doc):
        return

    total = sum(flt(row.get("allocated_percentage")) for row in rows)
    if abs(total - 100.0) < 0.0001:
        return

    base = round(100.0 / len(rows), 6)
    remainder = 100.0
    for row in rows[:-1]:
        row.allocated_percentage = base
        remainder -= base
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
