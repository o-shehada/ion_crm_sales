import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_months, random_string, today


class TestAccountManagerSalesTeam(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

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

    def create_account_manager_user(self):
        suffix = random_string(8).lower()
        return frappe.get_doc(
            {
                "doctype": "User",
                "email": f"am.sales.{suffix}@example.com",
                "first_name": "Account",
                "last_name": f"Manager {suffix}",
                "user_type": "System User",
                "send_welcome_email": 0,
            }
        ).insert(ignore_permissions=True)

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

    def first_record(self, doctype):
        records = frappe.get_all(doctype, pluck="name", limit=1)
        self.assertTrue(records, f"{doctype} is required for this test")
        return records[0]
