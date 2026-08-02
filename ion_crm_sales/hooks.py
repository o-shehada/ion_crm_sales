app_name = "ion_crm_sales"
app_title = "Ion Crm Sales"
app_publisher = "ard.ly"
app_description = "Ion Crm Sales App"
app_email = "d.jaziri@ard.ly"
app_license = "mit"

# doc_events = {
#     "Lead": {
#         "on_update": "ion_crm_sales.ion_crm_sales.doc_events.lead_handlers.handle_lead",
#     }
# }


# ion_crm_sales/ion_crm_sales/hooks.py

doc_events = {
    "Opportunity": {
        "before_save": [
            "ion_crm_sales.ion_crm_sales.doc_events.opportunity_dedicated_handlers.before_save",
            "ion_crm_sales.ion_crm_sales.doc_events.opportunity_handlers.before_save",
            # Add our notifier at the end so it runs after your validations/updates:
            "ion_crm_sales.ion_crm_sales.doc_events.survey_notifications.on_before_save",
        ],
        "validate": "ion_crm_sales.ion_crm_sales.doc_events.opportunity_handlers.validate",
    },
    "Customer": {
        "validate": "ion_crm_sales.ion_crm_sales.doc_events.customer_handlers.validate",
    },
    "Opportunity SM": {
        "before_save": [
            "ion_crm_sales.ion_crm_sales.doc_events.opportunity_handlers.before_save",
            "ion_crm_sales.ion_crm_sales.doc_events.survey_notifications.on_before_save",
        ]
    },
    "Opportunity Hotels": {
        "before_save": [
            "ion_crm_sales.ion_crm_sales.doc_events.opportunity_handlers.before_save",
            "ion_crm_sales.ion_crm_sales.doc_events.survey_notifications.on_before_save",
        ]
    },
    "Opportunity ISP": {
        "before_save": [
            "ion_crm_sales.ion_crm_sales.doc_events.opportunity_handlers.before_save",
            "ion_crm_sales.ion_crm_sales.doc_events.survey_notifications.on_before_save",
        ]
    },
    "Opportunity Tenders": {
        "before_save": [
            "ion_crm_sales.ion_crm_sales.doc_events.opportunity_handlers.before_save",
            "ion_crm_sales.ion_crm_sales.doc_events.survey_notifications.on_before_save",
        ]
    },
    "Hotspot": {
        "before_save": [
            "ion_crm_sales.ion_crm_sales.doc_events.hotspot_handlers.before_save",
            "ion_crm_sales.ion_crm_sales.doc_events.survey_notifications.on_before_save",
        ]
    },
    "Distributor": {
        "before_insert": "ion_crm_sales.ion_crm_sales.doc_events.distributor_handlers.before_insert",
        "after_insert": "ion_crm_sales.ion_crm_sales.doc_events.distributor_handlers.create_sales_partner_for_distributor",
    },
    "Sales Invoice": {
        "before_validate": [
            "ion_crm_sales.ion_crm_sales.doc_events.sales_invoice_handlers.set_sales_invoice_source_fields",
            "ion_crm_sales.ion_crm_sales.doc_events.sales_team_allocation.normalize_sales_team_allocation_for_sales_categories",
        ],
        "validate": "ion_crm_sales.ion_crm_sales.doc_events.sales_invoice_handlers.validate_contract_for_source_sales_orders",
        "on_submit": [
            "ion_crm_sales.ion_crm_sales.commission.triggers.create_person_sheets_for_invoice",
            "ion_crm_sales.ion_crm_sales.commission.triggers._touch_related_sheets",
        ],
        "on_cancel": "ion_crm_sales.ion_crm_sales.commission.triggers._touch_related_sheets",
        "on_update_after_submit": "ion_crm_sales.ion_crm_sales.commission.triggers._touch_related_sheets",
    },
    "Sales Order": {
        "before_validate": [
            "ion_crm_sales.ion_crm_sales.doc_events.sales_order_handlers.set_sales_order_source_fields",
            "ion_crm_sales.ion_crm_sales.doc_events.sales_team_allocation.normalize_sales_team_allocation_for_sales_categories",
        ],
        "before_insert": "ion_crm_sales.ion_crm_sales.doc_events.sales_order_handlers.before_insert",
        "validate": [
            "ion_crm_sales.ion_crm_sales.doc_events.sales_order_handlers.validate",
            "ion_crm_sales.ion_crm_sales.doc_events.sales_order_serial_batch.validate",
        ],
        "before_submit": "ion_crm_sales.ion_crm_sales.doc_events.sales_order_handlers.before_submit",
        "on_update": "ion_crm_sales.ion_crm_sales.doc_events.sales_order_serial_batch.link_bundles",
        "on_submit": "ion_crm_sales.ion_crm_sales.doc_events.sales_order_serial_batch.link_bundles",
        "on_cancel": "ion_crm_sales.ion_crm_sales.doc_events.sales_order_serial_batch.unlink_bundles",
        "on_trash": "ion_crm_sales.ion_crm_sales.doc_events.sales_order_serial_batch.unlink_bundles",
    },
    "Payment Entry": {
        "on_submit": "ion_crm_sales.ion_crm_sales.commission.triggers._touch_related_sheets",
        "on_cancel": "ion_crm_sales.ion_crm_sales.commission.triggers._touch_related_sheets",
    },
    "Supplier Quotation": {
        "on_update": "ion_crm_sales.ion_crm_sales.doc_events.supplier_quotation_handlers.on_update",
    },
    "Quotation": {
        "validate": "ion_crm_sales.ion_crm_sales.doc_events.quotation_handlers.validate",
        "before_insert": "ion_crm_sales.ion_crm_sales.doc_events.quotation_handlers.before_insert",
    },
    "Issue": {
        "after_insert": "ion_crm_sales.ion_support.support.notifications.new_issue_notification",
        "on_update": "ion_crm_sales.ion_support.support.notifications.issue_status_update",
    },
    "Contract": {
        "autoname": "ion_crm_sales.contract.set_contract_name",
    },
}

permission_query_conditions = {
    "Opportunity": "ion_crm_sales.opportunity_permissions.get_permission_query_conditions",
    "Opportunity Hotels": "ion_crm_sales.opportunity_permissions.get_permission_query_conditions",
    "Opportunity SM": "ion_crm_sales.opportunity_permissions.get_permission_query_conditions",
    "Opportunity ISP": "ion_crm_sales.opportunity_permissions.get_permission_query_conditions",
    "Opportunity Tenders": "ion_crm_sales.opportunity_permissions.get_permission_query_conditions",
}

has_permission = {
    "Opportunity": "ion_crm_sales.opportunity_permissions.has_permission",
    "Opportunity Hotels": "ion_crm_sales.opportunity_permissions.has_permission",
    "Opportunity SM": "ion_crm_sales.opportunity_permissions.has_permission",
    "Opportunity ISP": "ion_crm_sales.opportunity_permissions.has_permission",
    "Opportunity Tenders": "ion_crm_sales.opportunity_permissions.has_permission",
}

fixtures = [
    {"dt": "Client Script", "filters": [["module", "=", "Ion Crm Sales"]]},
    {"dt": "Server Script", "filters": [["module", "=", "Ion Crm Sales"]]},
    "Number Card",
    "Report",
    "Gender",
    "Print Format",
    "Role",
    "Role Profile",
    "Opportunity Type",
    {"dt": "Dashboard Chart", "filters": [["is_standard", "=", 0]]},
    {
        "dt": "Custom DocPerm",
        "filters": [
            ["parent", "in", [
                "Opportunity", "Opportunity Hotels", "Opportunity SM", "Opportunity ISP", "Opportunity Tenders",
            ]],
        ],
    },
]

after_migrate = [
    "ion_crm_sales.migration.remove_conflicting_opportunity_layout_setters",
    "ion_crm_sales.migration.remove_legacy_sales_order_contract_scripts",
    "ion_crm_sales.migration.ensure_sales_transaction_fields",
    "ion_crm_sales.migration.migrate_commission_sheet_sales_person",
    "ion_crm_sales.migration.backfill_commission_invoice_history_amounts",
    "ion_crm_sales.migration.ensure_commission_rate_settings_defaults",
]

scheduler_events = {
    "hourly": ["ion_crm_sales.notifications.send_subscription_expiry_alerts"]
}

# scheduler_events = {
#     "hourly": [
#         "ion_crm_sales.ion_crm_sales.api_sync.sync_rmt_opportunities"
#     ]
# }

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "ion_crm_sales",
# 		"logo": "/assets/ion_crm_sales/logo.png",
# 		"title": "Ion Crm Sales",
# 		"route": "/ion_crm_sales",
# 		"has_permission": "ion_crm_sales.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/ion_crm_sales/css/ion_crm_sales.css"
# app_include_js = "/assets/ion_crm_sales/js/ion_crm_sales.js"

# include js, css files in header of web template
# web_include_css = "/assets/ion_crm_sales/css/ion_crm_sales.css"
# web_include_js = "/assets/ion_crm_sales/js/ion_crm_sales.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "ion_crm_sales/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
    "Opportunity": "public/js/opportunity_survey.js",
    "Opportunity SM": "public/js/opportunity_survey.js",
    "Opportunity Hotels": "public/js/opportunity_survey.js",
    "Opportunity Tenders": "public/js/opportunity_survey.js",
    "Opportunity ISP": "public/js/opportunity_survey.js",
    "Hotspot": "public/js/opportunity_survey.js",
    "Quotation": "public/js/quotation_customer_branch.js",
    "Sales Order": [
        "public/js/sales_order_contract.js",
        "public/js/sales_order_serial_batch.js",
    ],
    "Sales Invoice": "public/js/sales_order_contract.js",
    "Material Request": "public/js/material_request.js",
    "Delivery Note": "public/js/delivery_note.js",
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

override_whitelisted_methods = {
    "erpnext.crm.doctype.opportunity.opportunity.make_quotation": "ion_crm_sales.opportunity.make_quotation",
    "erpnext.crm.doctype.opportunity.opportunity.make_request_for_quotation": "ion_crm_sales.opportunity.make_request_for_quotation",
    "erpnext.crm.doctype.opportunity.opportunity.make_supplier_quotation": "ion_crm_sales.opportunity.make_supplier_quotation",
    "erpnext.selling.doctype.quotation.quotation.make_sales_order": "ion_crm_sales.quotation.make_sales_order",
    "erpnext.selling.doctype.sales_order.sales_order.make_sales_invoice": "ion_crm_sales.sales_order.make_sales_invoice",
    "erpnext.selling.doctype.sales_order.sales_order.make_delivery_note": "ion_crm_sales.sales_order.make_delivery_note",
    "erpnext.buying.doctype.request_for_quotation.request_for_quotation.make_supplier_quotation_from_rfq": "ion_crm_sales.request_for_quotation.make_supplier_quotation_from_rfq",
    "erpnext.buying.doctype.request_for_quotation.request_for_quotation.create_supplier_quotation": "ion_crm_sales.request_for_quotation.create_supplier_quotation",
}

override_doctype_dashboards = {
    "Opportunity": "ion_crm_sales.opportunity_dashboard.get_dashboard_data",
    "Quotation": "ion_crm_sales.quotation_dashboard.get_dashboard_data",
    "Subscription": "ion_crm_sales.subscription_dashboard.get_dashboard_data",
}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "ion_crm_sales/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "ion_crm_sales.utils.jinja_methods",
# 	"filters": "ion_crm_sales.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "ion_crm_sales.install.before_install"
# after_install = "ion_crm_sales.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "ion_crm_sales.uninstall.before_uninstall"
# after_uninstall = "ion_crm_sales.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "ion_crm_sales.utils.before_app_install"
# after_app_install = "ion_crm_sales.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "ion_crm_sales.utils.before_app_uninstall"
# after_app_uninstall = "ion_crm_sales.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "ion_crm_sales.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"ion_crm_sales.tasks.all"
# 	],
# 	"daily": [
# 		"ion_crm_sales.tasks.daily"
# 	],
# 	"hourly": [
# 		"ion_crm_sales.tasks.hourly"
# 	],
# 	"weekly": [
# 		"ion_crm_sales.tasks.weekly"
# 	],
# 	"monthly": [
# 		"ion_crm_sales.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "ion_crm_sales.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "ion_crm_sales.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "ion_crm_sales.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["ion_crm_sales.utils.before_request"]
# after_request = ["ion_crm_sales.utils.after_request"]

# Job Events
# ----------
# before_job = ["ion_crm_sales.utils.before_job"]
# after_job = ["ion_crm_sales.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"ion_crm_sales.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }
