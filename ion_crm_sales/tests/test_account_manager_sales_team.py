import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_months, random_string, today


class TestAccountManagerSalesTeam(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    def test_manual_commission_limit_uses_service_category(self):
        from ion_crm_sales.ion_crm_sales.doc_events.sales_team_allocation import (
            get_manual_commission_limit,
        )

        doc = frappe._dict(
            custom_opportunity_from="Dedicated",
            custom_service_category="Hotel",
            custom_ba_transaction_type="Old Accounts",
        )
        self.assertEqual(get_manual_commission_limit(doc), 1)

    def test_single_sales_team_row_defaults_to_scenario_commission_limit(self):
        from ion_crm_sales.ion_crm_sales.doc_events.sales_team_allocation import (
            normalize_sales_team_allocation_for_sales_categories,
        )

        row = frappe._dict(
            custom_manual_commission_percentage=0,
            allocated_percentage=0,
        )
        doc = frappe._dict(
            custom_service_category="Hotel",
            custom_ba_transaction_type="Lead Acquisition",
            sales_team=[row],
            items=[],
        )

        normalize_sales_team_allocation_for_sales_categories(doc)

        self.assertEqual(row.custom_manual_commission_percentage, 5)
        self.assertEqual(row.allocated_percentage, 100)

    def test_opportunity_account_manager_defaults_on_mapped_sales_order(self):
        from ion_crm_sales.opportunity import make_quotation
        from ion_crm_sales.quotation import make_sales_order

        account_manager = self.create_account_manager_user()
        opportunity = self.create_opportunity(account_manager.name)

        quotation = make_quotation(opportunity.name)
        quotation.valid_till = add_months(today(), 1)
        quotation.insert(ignore_permissions=True)
        quotation.submit()

        sales_order = make_sales_order(quotation.name)
        self.assertEqual(quotation.custom_opportunity_from, "Dedicated")
        self.assertEqual(sales_order.custom_opportunity_from, "Dedicated")

        self.assertEqual(len(sales_order.sales_team), 1)
        self.assertEqual(sales_order.sales_team[0].allocated_percentage, 100)

        sales_person = frappe.get_doc("Sales Person", sales_order.sales_team[0].sales_person)
        self.assertEqual(sales_person.sales_person_name, account_manager.full_name)

    def test_user_sales_team_allocation_is_preserved_after_account_manager_sync(self):
        from ion_crm_sales.ion_crm_sales.doc_events.quotation_handlers import (
            get_or_create_sales_person_for_user,
        )
        from ion_crm_sales.ion_crm_sales.doc_events.sales_order_handlers import (
            set_account_manager_sales_team,
        )
        from ion_crm_sales.opportunity import make_quotation
        from ion_crm_sales.quotation import make_sales_order

        account_manager = self.create_account_manager_user()
        opportunity = self.create_opportunity(account_manager.name)

        quotation = make_quotation(opportunity.name)
        quotation.valid_till = add_months(today(), 1)
        quotation.insert(ignore_permissions=True)
        quotation.submit()

        sales_order = make_sales_order(quotation.name)
        second_user = self.create_account_manager_user()
        second_sales_person = get_or_create_sales_person_for_user(second_user.name)

        sales_order.sales_team[0].allocated_percentage = 60
        sales_order.append(
            "sales_team",
            {
                "sales_person": second_sales_person,
                "allocated_percentage": 40,
            },
        )

        set_account_manager_sales_team(sales_order)

        self.assertEqual(
            [row.allocated_percentage for row in sales_order.sales_team],
            [60, 40],
        )

    def test_contract_creation_does_not_require_a_hard_coded_template(self):
        from ion_crm_sales.ion_crm_sales.doc_events.sales_order_handlers import (
            create_contract,
        )
        from ion_crm_sales.opportunity import make_quotation
        from ion_crm_sales.quotation import make_sales_order

        account_manager = self.create_account_manager_user()
        opportunity = self.create_opportunity(account_manager.name)

        quotation = make_quotation(opportunity.name)
        quotation.valid_till = add_months(today(), 1)
        quotation.insert(ignore_permissions=True)
        quotation.submit()

        sales_order = make_sales_order(quotation.name)
        sales_order.custom_service_category = "Dedicated"
        sales_order.db_insert()

        contract_name = create_contract(
            sales_order.name,
            contract_terms="<p>Test contract terms</p>",
        )
        contract = frappe.get_doc("Contract", contract_name)

        self.assertFalse(contract.contract_template)
        self.assertEqual(contract.contract_terms, "<p>Test contract terms</p>")
        self.assertEqual(contract.document_type, "Sales Order")
        self.assertEqual(contract.document_name, sales_order.name)
        self.assertEqual(
            frappe.db.get_value("Sales Order", sales_order.name, "custom_contract"),
            contract.name,
        )

    def test_direct_sales_order_defaults_current_user_sales_person(self):
        user = self.create_account_manager_user(role="Dedicated Account Manager")
        sales_person = self.create_sales_person_for_user(user.name)

        sales_order = self.create_direct_sales_order()
        frappe.set_user(user.name)
        sales_order.insert(ignore_permissions=True)

        self.assertEqual(len(sales_order.sales_team), 1)
        self.assertEqual(sales_order.sales_team[0].sales_person, sales_person.name)
        self.assertEqual(sales_order.sales_team[0].allocated_percentage, 100)

    def test_direct_sales_order_without_existing_sales_person_is_not_defaulted(self):
        user = self.create_account_manager_user(role="Dedicated Account Manager")

        sales_order = self.create_direct_sales_order()
        frappe.set_user(user.name)
        sales_order.insert(ignore_permissions=True)

        self.assertFalse(sales_order.sales_team)

    def test_direct_sales_order_preserves_existing_sales_team(self):
        user = self.create_account_manager_user(role="Dedicated Account Manager")
        self.create_sales_person_for_user(user.name)
        existing_sales_person = self.create_sales_person()

        sales_order = self.create_direct_sales_order()
        sales_order.append(
            "sales_team",
            {
                "sales_person": existing_sales_person.name,
                "allocated_percentage": 100,
            },
        )
        frappe.set_user(user.name)
        sales_order.insert(ignore_permissions=True)

        self.assertEqual(len(sales_order.sales_team), 1)
        self.assertEqual(sales_order.sales_team[0].sales_person, existing_sales_person.name)

    def test_direct_sales_order_linked_to_opportunity_is_not_defaulted(self):
        user = self.create_account_manager_user(role="Dedicated Account Manager")
        self.create_sales_person_for_user(user.name)
        opportunity = self.create_opportunity(user.name)

        sales_order = self.create_direct_sales_order()
        sales_order.opportunity = opportunity.name
        frappe.set_user(user.name)
        sales_order.insert(ignore_permissions=True)

        self.assertFalse(sales_order.sales_team)

    def test_account_manager_must_set_ba_scenario_fields_on_save(self):
        from ion_crm_sales.ion_crm_sales.doc_events.sales_order_handlers import (
            validate_ba_scenario_fields_for_account_manager_save,
        )

        user = self.create_account_manager_user(role="Dedicated Account Manager")
        frappe.set_user(user.name)

        with self.assertRaises(frappe.ValidationError):
            validate_ba_scenario_fields_for_account_manager_save(frappe._dict())

    def test_non_account_manager_can_save_without_ba_scenario_fields(self):
        from ion_crm_sales.ion_crm_sales.doc_events.sales_order_handlers import (
            validate_ba_scenario_fields_for_account_manager_save,
        )

        user = self.create_account_manager_user()
        frappe.set_user(user.name)

        validate_ba_scenario_fields_for_account_manager_save(frappe._dict())

    def test_account_manager_submit_requires_ba_scenario_fields(self):
        from ion_crm_sales.ion_crm_sales.doc_events.sales_order_handlers import (
            validate_ba_scenario_fields_for_submit,
        )

        user = self.create_account_manager_user(role="Dedicated Account Manager")
        frappe.set_user(user.name)

        with self.assertRaises(frappe.ValidationError):
            validate_ba_scenario_fields_for_submit(frappe._dict())

        validate_ba_scenario_fields_for_submit(
            frappe._dict(
                custom_service_category="Dedicated",
                custom_ba_transaction_type="Old Accounts",
            )
        )

    def test_non_account_manager_can_submit_without_ba_scenario_fields(self):
        from ion_crm_sales.ion_crm_sales.doc_events.sales_order_handlers import (
            validate_ba_scenario_fields_for_submit,
        )

        user = self.create_account_manager_user()
        frappe.set_user(user.name)

        validate_ba_scenario_fields_for_submit(frappe._dict())

    def test_non_account_manager_cannot_edit_ba_scenario_fields(self):
        from ion_crm_sales.ion_crm_sales.doc_events.sales_order_handlers import (
            prevent_non_account_manager_ba_scenario_field_changes,
        )

        user = self.create_account_manager_user()
        frappe.set_user(user.name)

        with self.assertRaises(frappe.ValidationError):
            prevent_non_account_manager_ba_scenario_field_changes(
                ChangedFieldsDoc(changed_fields={"custom_service_category"})
            )

    def test_account_manager_can_edit_ba_scenario_fields(self):
        from ion_crm_sales.ion_crm_sales.doc_events.sales_order_handlers import (
            prevent_non_account_manager_ba_scenario_field_changes,
        )

        user = self.create_account_manager_user(role="Dedicated Account Manager")
        frappe.set_user(user.name)

        prevent_non_account_manager_ba_scenario_field_changes(
            ChangedFieldsDoc(changed_fields={"custom_service_category"})
        )

    def create_account_manager_user(self, role=None):
        suffix = random_string(8).lower()
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": f"am.sales.{suffix}@example.com",
                "first_name": "Account",
                "last_name": f"Manager {suffix}",
                "user_type": "System User",
                "send_welcome_email": 0,
            }
        ).insert(ignore_permissions=True)
        if role:
            user.add_roles(role)
        return user

    def create_opportunity(self, account_manager):
        customer = self.create_customer()
        item = self.create_item()

        opportunity = frappe.get_doc(
            {
                "doctype": "Opportunity",
                "company": self.first_record("Company"),
                "opportunity_from": "Customer",
                "party_name": customer.name,
                "opportunity_type": "Dedicated",
                "sales_stage": "Opportunity",
                "expected_closing": today(),
                "transaction_date": today(),
                "conversion_rate": 1.0,
                "territory": self.first_record("Territory"),
                "industry": self.first_record("Industry Type"),
                "market_segment": self.first_record("Market Segment"),
                "city": "Test City",
                "custom_material_type": self.first_record("Material Type"),
                "custom_account_manager": account_manager,
                "custom_surveyor_manager": "Administrator",
                "custom_request": "Test request",
                "items": [
                    {
                        "item_code": item.name,
                        "qty": 1,
                        "rate": 1000,
                        "uom": item.stock_uom,
                        "custom_availability": "Available",
                        "custom_valuation_rate": 1000,
                        "custom_valuation_rate_company_currency": 1000,
                    }
                ],
            }
        )
        return opportunity.insert(ignore_permissions=True)

    def create_customer(self):
        suffix = random_string(8).lower()
        return frappe.get_doc(
            {
                "doctype": "Customer",
                "customer_name": f"Account Manager Test Customer {suffix}",
                "customer_type": "Company",
                "customer_group": self.first_record("Customer Group"),
                "territory": self.first_record("Territory"),
            }
        ).insert(ignore_permissions=True)

    def create_item(self):
        suffix = random_string(8).lower()
        uom = self.first_record("UOM")
        return frappe.get_doc(
            {
                "doctype": "Item",
                "item_code": f"AM-SALES-TEAM-{suffix}",
                "item_name": f"AM Sales Team {suffix}",
                "item_group": self.first_record("Item Group"),
                "custom_material_type": self.first_record("Material Type"),
                "stock_uom": uom,
                "is_stock_item": 0,
                "is_sales_item": 1,
            }
        ).insert(ignore_permissions=True)

    def create_employee_for_user(self, user):
        suffix = random_string(8).lower()
        employee = frappe.get_doc(
            {
                "doctype": "Employee",
                "name": f"AM-EMP-{suffix}",
                "first_name": "Account",
                "last_name": f"Manager {suffix}",
                "gender": "Male",
                "date_of_birth": "1990-01-01",
                "date_of_joining": today(),
                "company": self.first_record("Company"),
                "user_id": user,
            }
        )
        employee.db_insert()
        return employee

    def create_sales_person_for_user(self, user):
        employee = self.create_employee_for_user(user)
        return self.create_sales_person(employee.name)

    def create_sales_person(self, employee=None):
        suffix = random_string(8).lower()
        sales_person = frappe.get_doc(
            {
                "doctype": "Sales Person",
                "sales_person_name": f"AM Sales Person {suffix}",
                "parent_sales_person": self.first_sales_person_group(),
                "enabled": 1,
                "is_group": 0,
            }
        )
        if employee:
            sales_person.employee = employee
        return sales_person.insert(ignore_permissions=True)

    def create_direct_sales_order(self):
        customer = self.create_customer()
        item = self.create_item()
        company = self.first_record("Company")
        currency = frappe.db.get_value("Company", company, "default_currency")
        price_list = frappe.db.get_single_value("Selling Settings", "selling_price_list")
        return frappe.get_doc(
            {
                "doctype": "Sales Order",
                "customer": customer.name,
                "company": company,
                "currency": currency,
                "conversion_rate": 1,
                "selling_price_list": price_list,
                "price_list_currency": currency,
                "plc_conversion_rate": 1,
                "cost_center": self.first_cost_center(company),
                "custom_service_category": "Dedicated",
                "custom_ba_transaction_type": "Old Accounts",
                "transaction_date": today(),
                "delivery_date": add_months(today(), 1),
                "items": [
                    {
                        "item_code": item.name,
                        "qty": 1,
                        "rate": 1000,
                        "uom": item.stock_uom,
                        "delivery_date": add_months(today(), 1),
                    }
                ],
            }
        )

    def first_sales_person_group(self):
        records = frappe.get_all(
            "Sales Person",
            filters={"is_group": 1},
            pluck="name",
            limit=1,
        )
        self.assertTrue(records, "Sales Person group is required for this test")
        return records[0]

    def first_cost_center(self, company):
        records = frappe.get_all(
            "Cost Center",
            filters={"company": company, "is_group": 0},
            pluck="name",
            limit=1,
        )
        self.assertTrue(records, f"Cost Center is required for {company}")
        return records[0]

    def first_record(self, doctype):
        records = frappe.get_all(doctype, pluck="name", limit=1)
        self.assertTrue(records, f"{doctype} is required for this test")
        return records[0]


class ChangedFieldsDoc:
    def __init__(self, changed_fields=None):
        self.changed_fields = changed_fields or set()

    def is_new(self):
        return False

    def has_value_changed(self, fieldname):
        return fieldname in self.changed_fields
