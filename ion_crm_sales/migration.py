import json

import frappe


OPPORTUNITY_LAYOUT_SETTERS = (
	"Opportunity SM-main-field_order",
	"Opportunity Hotels-main-field_order",
	"Opportunity Tenders-main-field_order",
)


def remove_conflicting_opportunity_layout_setters():
	"""Keep app-owned Opportunity layouts controlled by their DocType JSON files."""
	frappe.db.delete("Property Setter", {"name": ("in", OPPORTUNITY_LAYOUT_SETTERS)})

	for doctype in ("Opportunity SM", "Opportunity Hotels", "Opportunity Tenders"):
		frappe.clear_cache(doctype=doctype)


def remove_legacy_sales_order_contract_scripts():
	"""Remove fixture scripts replaced by the app-owned template-agnostic flow."""
	frappe.db.delete("Client Script", {"name": "Sales Order Script"})
	frappe.db.delete("Server Script", {"name": "Sales Order"})


def ensure_sales_transaction_fields():
    """Keep service-category routing fields available on sales documents."""
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

    service_category = {
        "fieldname": "custom_service_category",
        "label": "Service Category",
        "fieldtype": "Select",
        "options": "\nDedicated\nHotel\nISPs\nION Solutions\nHotspot - Sales\nHotspot - BA\nUltra - Malls\nHome",
        "insert_after": "custom_opportunity_from",
        "reqd": 1,
    }
    transaction_type = {
        "fieldname": "custom_ba_transaction_type",
        "label": "BA Transaction Type",
        "fieldtype": "Select",
        "options": "\nOld Accounts\nLead Acquisition\nUpsell",
        "insert_after": "custom_service_category",
    }
    create_custom_fields(
        {
            "Sales Order": [service_category.copy(), transaction_type.copy()],
            "Sales Invoice": [service_category.copy(), transaction_type.copy()],
        },
        update=True,
    )

    for doctype in ("Sales Order", "Sales Invoice"):
        service_field_name = f"{doctype}-custom_service_category"
        if frappe.db.exists("Custom Field", service_field_name):
            frappe.db.set_value("Custom Field", service_field_name, "default", None)
        field_name = f"{doctype}-custom_opportunity_from"
        if frappe.db.exists("Custom Field", field_name):
            frappe.db.set_value("Custom Field", field_name, "read_only", 1)
        _place_fields_after(
            doctype,
            "custom_opportunity_from",
            ("custom_service_category", "custom_ba_transaction_type"),
        )
        frappe.clear_cache(doctype=doctype)


def _place_fields_after(doctype, anchor, fieldnames):
    setter = frappe.db.get_value(
        "Property Setter",
        {"doc_type": doctype, "property": "field_order"},
        ["name", "value"],
        as_dict=True,
    )
    if not setter or not setter.value:
        return

    field_order = json.loads(setter.value)
    for fieldname in fieldnames:
        if fieldname in field_order:
            field_order.remove(fieldname)
    position = field_order.index(anchor) + 1 if anchor in field_order else len(field_order)
    for fieldname in fieldnames:
        field_order.insert(position, fieldname)
        position += 1
    frappe.db.set_value("Property Setter", setter.name, "value", json.dumps(field_order))


def migrate_commission_sheet_sales_person():
    """Backfill the parent salesperson where a legacy sheet has one line."""
    sheets = frappe.get_all(
        "Sales Target and Commission Sheet",
        filters={"sales_person": ("is", "not set")},
        pluck="name",
    )
    for sheet_name in sheets:
        people = frappe.get_all(
            "Commission Lines",
            filters={
                "parent": sheet_name,
                "parenttype": "Sales Target and Commission Sheet",
                "parentfield": "commission_lines",
            },
            distinct=True,
            pluck="sales_person",
        )
        people = [person for person in people if person]
        if len(people) == 1:
            frappe.db.set_value(
                "Sales Target and Commission Sheet",
                sheet_name,
                "sales_person",
                people[0],
                update_modified=False,
            )


def backfill_commission_invoice_history_amounts():
    """Populate new invoice amount/category fields on existing history snapshots."""
    if not frappe.db.exists("DocType", "Sales Invoice Commission History"):
        return

    base_filters = {
        "parenttype": "Sales Target and Commission Sheet",
        "parentfield": "invoice_history",
    }
    sheet_names = set()
    for fieldname in ("invoice_amount", "service_category"):
        filters = {**base_filters, fieldname: ("is", "not set")}
        sheet_names.update(
            frappe.get_all(
                "Sales Invoice Commission History",
                filters=filters,
                pluck="parent",
            )
        )
    if not sheet_names:
        return

    from ion_crm_sales.ion_crm_sales.commission.triggers import (
        _persist_invoice_history,
        sync_invoice_history,
    )

    for sheet_name in sheet_names:
        sheet = frappe.get_doc("Sales Target and Commission Sheet", sheet_name)
        if not sheet.sales_person:
            continue
        sync_invoice_history(sheet)
        _persist_invoice_history(sheet)


def ensure_commission_rate_settings_defaults():
    """Seed the settings UI from config.py without making it authoritative."""
    if not frappe.db.exists("DocType", "Commission Rate Settings"):
        return

    settings = frappe.get_single("Commission Rate Settings")
    if settings.get("initialized_from_code"):
        return

    from ion_crm_sales.ion_crm_sales.commission.config import (
        BA_ITEM_GROUPS,
        BA_RATES,
        FIRST_YEAR_ADDON_RATE,
        ION_ABOVE_ADDON,
        ION_ROLE_RATES,
        PENALTY_PLANS,
        PROJECT_ACQ_BONUS,
        SALES_ITEM_GROUPS,
        SALES_RATES,
        SALES_SPLITS,
    )

    values = {
        "sales_home_item_group": SALES_ITEM_GROUPS["HOME"],
        "sales_home_normal_rate": SALES_RATES["HOME"]["normal"] * 100,
        "sales_home_above_target_rate": SALES_RATES["HOME"]["above"] * 100,
        "sales_home_normal_manager_split": SALES_SPLITS["HOME"]["normal"]["manager"] * 100,
        "sales_home_normal_team_split": SALES_SPLITS["HOME"]["normal"]["rest"] * 100,
        "sales_home_above_manager_split": SALES_SPLITS["HOME"]["above"]["manager"] * 100,
        "sales_home_above_team_split": SALES_SPLITS["HOME"]["above"]["rest"] * 100,
        "sales_hotspot_item_group": SALES_ITEM_GROUPS["HOTSPOT"],
        "sales_hotspot_normal_rate": SALES_RATES["HOTSPOT"]["normal"] * 100,
        "sales_hotspot_above_target_rate": SALES_RATES["HOTSPOT"]["above"] * 100,
        "sales_hotspot_normal_manager_split": SALES_SPLITS["HOTSPOT"]["normal"]["manager"] * 100,
        "sales_hotspot_normal_team_split": SALES_SPLITS["HOTSPOT"]["normal"]["rest"] * 100,
        "sales_hotspot_above_manager_split": SALES_SPLITS["HOTSPOT"]["above"]["manager"] * 100,
        "sales_hotspot_above_team_split": SALES_SPLITS["HOTSPOT"]["above"]["rest"] * 100,
        "ion_item_group": BA_ITEM_GROUPS["ION_SOLUTIONS"],
        "ion_account_lead_rate": ION_ROLE_RATES["Account Lead Acquisition"] * 100,
        "ion_offer_team_rate": ION_ROLE_RATES["Offer Team"] * 100,
        "ion_execution_team_rate": ION_ROLE_RATES["Execution Team"] * 100,
        "ion_above_addon_rate": ION_ABOVE_ADDON * 100,
        "first_year_addon_rate": FIRST_YEAR_ADDON_RATE * 100,
        "project_acquisition_bonus": PROJECT_ACQ_BONUS,
        "yearly_grace_days": PENALTY_PLANS["yearly"]["grace_days"],
        "yearly_cadence_days": PENALTY_PLANS["yearly"]["cadence_days"],
        "six_month_grace_days": PENALTY_PLANS["6mo"]["grace_days"],
        "six_month_cadence_days": PENALTY_PLANS["6mo"]["cadence_days"],
        "quarterly_grace_days": PENALTY_PLANS["quarterly"]["grace_days"],
        "quarterly_cadence_days": PENALTY_PLANS["quarterly"]["cadence_days"],
    }
    ba_fields = {
        "DEDICATED": "ba_dedicated",
        "HOTEL": "ba_hotel",
        "ISPS": "ba_isp",
        "HOTSPOT": "ba_hotspot",
        "ULTRA_MALLS": "ba_ultra_malls",
    }
    for category, prefix in ba_fields.items():
        values[f"{prefix}_item_group"] = BA_ITEM_GROUPS[category]
        values[f"{prefix}_old_rate"] = BA_RATES[category]["old"] * 100
        values[f"{prefix}_new_rate"] = BA_RATES[category]["new"] * 100
        values[f"{prefix}_upsell_rate"] = BA_RATES[category]["upsell"] * 100
        values[f"{prefix}_above_rate"] = BA_RATES[category]["above"] * 100

    settings.update(values)
    settings.initialized_from_code = 1
    settings.flags.ignore_links = True
    settings.save(ignore_permissions=True)
