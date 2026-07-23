# ion_crm_sales/opportunity_permissions.py

import frappe

# Roles with unrestricted visibility of every opportunity.
FULL_ACCESS_ROLES = {"System Manager"}

# Each opportunity-family doctype has its own Account Manager role.
ACCOUNT_MANAGER_ROLE_BY_DOCTYPE = {
	"Opportunity": "Dedicated Account Manager",
	"Opportunity Hotels": "Hotels Account Manager",
	"Opportunity SM": "SM Account Manager",
	"Opportunity ISP": "ISP Account Manager",
	"Opportunity Tenders": "Tenders Account Manager",
}

# The "Surveyor" (surveyor-team) row-membership restriction only applies to
# core Opportunity for now; Hotels/SM/ISP/Tenders' Surveyor role keeps its
# existing unrestricted access until asked otherwise.
RESTRICT_SURVEYOR_ROLE_DOCTYPES = {"Opportunity"}


def get_permission_query_conditions(user=None, doctype=None):
	"""Row-level visibility for Opportunity-family list/report views.

	- System Manager: sees everything.
	- <Doctype> Account Manager: docs with custom_account_manager unset, or
	  set to them. Once another Account Manager claims a doc, it drops out
	  of their view.
	- Surveyor Manager: only docs where custom_surveyor_manager = them.
	- Sales Engineer: only docs where custom_sales_engineer = them.
	- Surveyor: only docs where they appear as a row in custom_surveyors
	  (core Opportunity only, see RESTRICT_SURVEYOR_ROLE_DOCTYPES).
	"""
	if not user:
		user = frappe.session.user

	if user == "Administrator":
		return ""

	roles = set(frappe.get_roles(user))

	if roles & FULL_ACCESS_ROLES:
		return ""

	conditions = []

	account_manager_role = ACCOUNT_MANAGER_ROLE_BY_DOCTYPE.get(doctype)
	if account_manager_role and account_manager_role in roles:
		conditions.append(
			f"""(ifnull(`tab{doctype}`.custom_account_manager, '') = ''
				or `tab{doctype}`.custom_account_manager = {frappe.db.escape(user)})"""
		)

	if "Surveyor Manager" in roles:
		conditions.append(f"`tab{doctype}`.custom_surveyor_manager = {frappe.db.escape(user)}")

	if "Sales Engineer" in roles:
		conditions.append(f"`tab{doctype}`.custom_sales_engineer = {frappe.db.escape(user)}")

	if "Surveyor" in roles and doctype in RESTRICT_SURVEYOR_ROLE_DOCTYPES:
		conditions.append(
			f"""exists (
				select 1 from `tabTechnical Surveyor` ts
				where ts.parenttype = {frappe.db.escape(doctype)}
				and ts.parent = `tab{doctype}`.name
				and ts.surveyor = {frappe.db.escape(user)}
			)"""
		)

	if not conditions:
		# None of the scoped roles -> no extra restriction from this hook;
		# base Custom DocPerm rows already gate access.
		return ""

	return "(" + " or ".join(conditions) + ")"


def has_permission(doc, ptype=None, user=None):
	"""Single-document permission check, mirrors get_permission_query_conditions."""
	if not user:
		user = frappe.session.user

	if user == "Administrator":
		return True

	roles = set(frappe.get_roles(user))

	if roles & FULL_ACCESS_ROLES:
		return True

	account_manager_role = ACCOUNT_MANAGER_ROLE_BY_DOCTYPE.get(doc.doctype)
	if account_manager_role and account_manager_role in roles:
		account_manager = doc.get("custom_account_manager")
		if not account_manager or account_manager == user:
			return True

	if "Surveyor Manager" in roles and doc.get("custom_surveyor_manager") == user:
		return True

	if "Sales Engineer" in roles and doc.get("custom_sales_engineer") == user:
		return True

	if "Surveyor" in roles and doc.doctype in RESTRICT_SURVEYOR_ROLE_DOCTYPES:
		for row in doc.get("custom_surveyors") or []:
			if row.get("surveyor") == user:
				return True

	scoped_roles = {"Surveyor Manager", "Sales Engineer"}
	if account_manager_role:
		scoped_roles.add(account_manager_role)
	if doc.doctype in RESTRICT_SURVEYOR_ROLE_DOCTYPES:
		scoped_roles.add("Surveyor")

	if not (roles & scoped_roles):
		# none of the scoped roles -> defer to standard role-permission checks
		return True

	return False
