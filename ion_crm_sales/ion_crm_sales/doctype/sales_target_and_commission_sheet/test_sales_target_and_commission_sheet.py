import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_months, getdate, random_string, today


class TestSalesTargetandCommissionSheet(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    def test_sales_commission_cycle_creates_transactions_and_rolls_up_sheet(self):
        fiscal_year = "2026"
        company = self.get_company()
        self.ensure_item_group("Home")
        distribution = self.create_even_monthly_distribution(fiscal_year)
        manager = self.create_sales_person(
            target_amount=20000,
            distribution=distribution.name,
            fiscal_year=fiscal_year,
            is_manager=True,
        )
        rep = self.create_sales_person(
            target_amount=40000,
            distribution=distribution.name,
            fiscal_year=fiscal_year,
            employee=self.create_employee(company).name,
        )

        invoice = self.create_paid_sales_invoice(
            company=company,
            amount=20000,
            sales_team=[
                {
                    "sales_person": manager.name,
                    "custom_manual_commission_percentage": 1,
                    "allocated_percentage": 30,
                },
                {
                    "sales_person": rep.name,
                    "custom_manual_commission_percentage": 2,
                    "allocated_percentage": 70,
                },
            ],
        )
        self.assertEqual(invoice.custom_opportunity_from, "Dedicated")
        self.assertEqual(invoice.custom_service_category, "Home")

        for (
            sales_person,
            expected_target,
            expected_basis,
            expected_rate,
            expected_commission,
        ) in (
            (manager.name, 5000, 6000, 1, 6),
            (rep.name, 10000, 14000, 2, 19),
        ):
            auto_sheet_name = frappe.db.get_value(
                "Sales Target and Commission Sheet",
                {
                    "company": company.name,
                    "fiscal_year": fiscal_year,
                    "quarter": "Q2",
                    "sales_person": sales_person,
                },
                "name",
            )
            self.assertTrue(auto_sheet_name)
            auto_sheet = frappe.get_doc(
                "Sales Target and Commission Sheet", auto_sheet_name
            )
            self.assertEqual(auto_sheet.sales_person, sales_person)
            self.assertEqual(len(auto_sheet.invoice_history), 1)
            self.assertEqual(auto_sheet.invoice_history[0].sales_invoice, invoice.name)
            self.assertEqual(auto_sheet.invoice_history[0].invoice_status, "Paid")
            self.assertAlmostEqual(auto_sheet.invoice_history[0].invoice_amount, 20000)
            self.assertAlmostEqual(
                auto_sheet.invoice_history[0].commission_rate,
                expected_rate,
            )
            self.assertAlmostEqual(
                auto_sheet.invoice_history[0].commission_amount,
                expected_commission,
            )
            self.assertAlmostEqual(auto_sheet.total_paid_invoices, expected_commission)
            self.assertEqual(auto_sheet.total_unpaid_invoices, 0)
            self.assertAlmostEqual(auto_sheet.total_paid_invoice_amount, 20000)
            self.assertEqual(auto_sheet.total_unpaid_invoice_amount, 0)
            self.assertEqual(auto_sheet.transaction_sync_status, "Synced")
            self.assertEqual(auto_sheet.source_of_totals, "Commission Transactions")
            self.assertEqual(auto_sheet.commission_transaction_count, 1)
            self.assertAlmostEqual(auto_sheet.total_target, expected_target)
            self.assertAlmostEqual(auto_sheet.total_actual_sales, 20000)
            self.assertAlmostEqual(auto_sheet.total_commission, expected_commission)

            transaction = frappe.db.get_value(
                "Commission Transaction",
                {"sales_target_and_commission_sheet": auto_sheet.name},
                "name",
            )
            tx = frappe.get_doc("Commission Transaction", transaction)
            self.assertEqual(tx.sales_invoice, invoice.name)
            self.assertEqual(tx.department, "Sales")
            self.assertEqual(tx.fully_paid_on, getdate("2026-04-20"))
            self.assertAlmostEqual(tx.eligible_amount, expected_basis)
            self.assertAlmostEqual(tx.total_commission, expected_commission)
            self.assertTrue(all(line.sales_person == sales_person for line in tx.lines))

    def test_sales_hotspot_above_target_uses_above_split(self):
        fiscal_year = "2026"
        company = self.get_company()
        self.ensure_item_group("Hotspot - Sales")
        distribution = self.create_even_monthly_distribution(fiscal_year)
        manager = self.create_sales_person(
            target_amount=8000,
            distribution=distribution.name,
            fiscal_year=fiscal_year,
            is_manager=True,
        )
        rep = self.create_sales_person(
            target_amount=32000,
            distribution=distribution.name,
            fiscal_year=fiscal_year,
            employee=self.create_employee(company).name,
        )

        flow = _create_matrix_flow(
            self,
            company,
            "Sales Hotspot Above Split Regression",
            "Opportunity SM",
            "Hotspot - Sales",
            20000,
            [
                {"sales_person": manager.name},
                {"sales_person": rep.name},
            ],
        )

        sales_order = frappe.get_doc("Sales Order", flow["sales_order"])
        invoice = frappe.get_doc("Sales Invoice", flow["sales_invoice"])
        self.assertAlmostEqual(sum(row.allocated_percentage for row in sales_order.sales_team), 100)
        self.assertAlmostEqual(sum(row.allocated_percentage for row in invoice.sales_team), 100)

        for sales_person, expected_target, expected_basis, expected_commission in (
            (manager.name, 2000, 6000, 180),
            (rep.name, 8000, 14000, 620),
        ):
            sheet = frappe.get_doc(
                "Sales Target and Commission Sheet",
                frappe.db.get_value(
                    "Sales Target and Commission Sheet",
                    {"sales_person": sales_person, "quarter": "Q2"},
                    "name",
                ),
            )
            tx = frappe.get_doc(
                "Commission Transaction",
                frappe.db.get_value(
                    "Commission Transaction",
                    {"sales_target_and_commission_sheet": sheet.name},
                    "name",
                ),
            )
            self.assertEqual(tx.sales_invoice, flow["sales_invoice"])
            self.assertAlmostEqual(tx.eligible_amount, expected_basis)
            self.assertAlmostEqual(tx.total_commission, expected_commission)
            self.assertAlmostEqual(sheet.total_target, expected_target)
            self.assertAlmostEqual(sheet.total_actual_sales, 20000)
            self.assertAlmostEqual(sheet.total_commission, expected_commission)
            self.assertTrue(all(line.sales_person == sales_person for line in tx.lines))

    def test_ba_newlead_uses_allocated_percentage_and_combined_rate(self):
        fiscal_year = "2026"
        company = self.get_company()
        self.ensure_item_group("Dedicated")
        distribution = self.create_even_monthly_distribution(fiscal_year)
        ba_am = _create_ba_sales_person(self, company, distribution.name, fiscal_year, "AM")
        ba_exec = _create_ba_sales_person(self, company, distribution.name, fiscal_year, "SM")

        flow = _create_matrix_flow(
            self,
            company,
            "BA Dedicated NewLead allocation regression",
            "Opportunity",
            "Dedicated",
            8000,
            [
                {"sales_person": ba_am.name, "allocated_percentage": 30},
                {"sales_person": ba_exec.name, "allocated_percentage": 70},
            ],
            invoice_flags={"custom_ba_transaction_type": "Lead Acquisition"},
        )

        for sales_person, expected_basis, expected_commission, expected_split in (
            (ba_am.name, 2400, 72, 30),
            (ba_exec.name, 5600, 168, 70),
        ):
            sheet_name = frappe.db.get_value(
                "Sales Target and Commission Sheet",
                {"sales_person": sales_person, "quarter": "Q2"},
                "name",
            )
            sheet = frappe.get_doc("Sales Target and Commission Sheet", sheet_name)
            tx = frappe.get_doc(
                "Commission Transaction",
                frappe.db.get_value(
                    "Commission Transaction",
                    {"sales_target_and_commission_sheet": sheet.name},
                    "name",
                ),
            )
            self.assertEqual(tx.sales_invoice, flow["sales_invoice"])
            self.assertEqual(tx.transaction_type, "NewLead")
            self.assertAlmostEqual(tx.eligible_amount, expected_basis)
            self.assertAlmostEqual(tx.total_commission, expected_commission)
            self.assertAlmostEqual(sheet.total_actual_sales, 8000)
            self.assertAlmostEqual(sheet.total_commission, expected_commission)
            self.assertEqual(
                sheet.invoice_history[0].custom_ba_transaction_type,
                "Lead Acquisition",
            )
            self.assertEqual(sheet.invoice_history[0].service_category, "Dedicated")
            self.assertAlmostEqual(sheet.invoice_history[0].invoice_amount, 8000)
            base = next(line for line in tx.lines if line.commission_component == "Base")
            self.assertAlmostEqual(base.split_percentage, expected_split)

    def test_payment_trigger_targets_only_matching_sales_person_sheets(self):
        from ion_crm_sales.ion_crm_sales.commission.triggers import _affected_sheet_candidates

        fiscal_year = "2026"
        company = self.get_company()
        self.ensure_item_group("Home")
        distribution = self.create_even_monthly_distribution(fiscal_year)
        matching_rep = self.create_sales_person(
            target_amount=40000,
            distribution=distribution.name,
            fiscal_year=fiscal_year,
            employee=self.create_employee(company).name,
        )
        unrelated_rep = self.create_sales_person(
            target_amount=40000,
            distribution=distribution.name,
            fiscal_year=fiscal_year,
            employee=self.create_employee(company).name,
        )

        chain = self.create_paid_sales_invoice(
            company=company,
            amount=20000,
            sales_team=[{"sales_person": matching_rep.name, "allocated_percentage": 100}],
            return_chain=True,
        )

        matching_sheet = frappe.get_doc(
            "Sales Target and Commission Sheet",
            frappe.db.get_value(
                "Sales Target and Commission Sheet",
                {"sales_person": matching_rep.name, "quarter": "Q2"},
                "name",
            ),
        )
        unrelated_person_sheet = frappe.get_doc(
            {
                "doctype": "Sales Target and Commission Sheet",
                "company": company.name,
                "fiscal_year": fiscal_year,
                "quarter": "Q2",
                "sales_person": unrelated_rep.name,
            }
        ).insert(ignore_permissions=True)
        other_quarter_sheet = frappe.get_doc(
            {
                "doctype": "Sales Target and Commission Sheet",
                "company": company.name,
                "fiscal_year": fiscal_year,
                "quarter": "Q3",
                "sales_person": matching_rep.name,
            }
        ).insert(ignore_permissions=True)

        candidate_names = {
            row.name for row in _affected_sheet_candidates(chain["payment_entry"])
        }

        self.assertIn(matching_sheet.name, candidate_names)
        self.assertNotIn(unrelated_person_sheet.name, candidate_names)
        self.assertNotIn(other_quarter_sheet.name, candidate_names)


    def test_invoice_submit_creates_unpaid_person_sheet_history(self):
        fiscal_year = "2026"
        company = self.get_company()
        self.ensure_item_group("Home")
        distribution = self.create_even_monthly_distribution(fiscal_year)
        rep = self.create_sales_person(
            target_amount=40000,
            distribution=distribution.name,
            fiscal_year=fiscal_year,
            employee=self.create_employee(company).name,
        )

        invoice = self.create_paid_sales_invoice(
            company=company,
            amount=10000,
            sales_team=[
                {
                    "sales_person": rep.name,
                    "custom_manual_commission_percentage": 1,
                    "allocated_percentage": 100,
                }
            ],
            pay_invoice=False,
        )

        sheet_name = frappe.db.get_value(
            "Sales Target and Commission Sheet",
            {
                "company": company.name,
                "fiscal_year": fiscal_year,
                "quarter": "Q2",
                "sales_person": rep.name,
            },
            "name",
        )
        self.assertTrue(sheet_name)
        sheet = frappe.get_doc("Sales Target and Commission Sheet", sheet_name)
        self.assertEqual(len(sheet.invoice_history), 1)
        self.assertEqual(sheet.invoice_history[0].sales_invoice, invoice.name)
        self.assertEqual(sheet.invoice_history[0].invoice_status, "Unpaid")
        self.assertAlmostEqual(sheet.invoice_history[0].invoice_amount, 10000)
        self.assertAlmostEqual(sheet.invoice_history[0].commission_rate, 1)
        self.assertAlmostEqual(sheet.invoice_history[0].commission_amount, 100)
        self.assertEqual(sheet.total_paid_invoices, 0)
        self.assertAlmostEqual(sheet.total_unpaid_invoices, 100)
        self.assertEqual(sheet.total_paid_invoice_amount, 0)
        self.assertAlmostEqual(sheet.total_unpaid_invoice_amount, 10000)

    def test_payment_recalculates_submitted_commission_sheet(self):
        from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

        fiscal_year = "2026"
        company = self.get_company()
        self.ensure_item_group("Home")
        distribution = self.create_even_monthly_distribution(fiscal_year)
        rep = self.create_sales_person(
            target_amount=40000,
            distribution=distribution.name,
            fiscal_year=fiscal_year,
            employee=self.create_employee(company).name,
        )
        invoice = self.create_paid_sales_invoice(
            company=company,
            amount=10000,
            sales_team=[{"sales_person": rep.name, "allocated_percentage": 100}],
            pay_invoice=False,
        )
        sheet_name = frappe.db.get_value(
            "Sales Target and Commission Sheet",
            {
                "company": company.name,
                "fiscal_year": fiscal_year,
                "quarter": "Q2",
                "sales_person": rep.name,
            },
            "name",
        )
        sheet = frappe.get_doc("Sales Target and Commission Sheet", sheet_name)
        sheet.submit()
        previous_sync_on = sheet.last_transaction_sync_on

        payment = get_payment_entry("Sales Invoice", invoice.name)
        payment.posting_date = "2026-04-20"
        payment.reference_no = random_string(10)
        payment.reference_date = "2026-04-20"
        payment.paid_to = company.default_cash_account
        payment.insert(ignore_permissions=True)
        payment.submit()

        sheet.reload()
        self.assertEqual(sheet.docstatus, 1)
        self.assertEqual(sheet.transaction_sync_status, "Synced")
        self.assertEqual(sheet.commission_transaction_count, 1)
        self.assertGreater(sheet.last_transaction_sync_on, previous_sync_on)

    def test_unpaid_invoice_submit_does_not_modify_existing_transactions(self):
        from ion_crm_sales.ion_crm_sales.commission.api import recalculate_sheet

        fiscal_year = "2026"
        company = self.get_company()
        self.ensure_item_group("Home")
        distribution = self.create_even_monthly_distribution(fiscal_year)
        rep = self.create_sales_person(
            target_amount=40000,
            distribution=distribution.name,
            fiscal_year=fiscal_year,
            employee=self.create_employee(company).name,
        )
        self.create_paid_sales_invoice(
            company=company,
            amount=10000,
            sales_team=[{"sales_person": rep.name, "allocated_percentage": 100}],
        )
        sheet_name = frappe.db.get_value(
            "Sales Target and Commission Sheet",
            {"sales_person": rep.name, "quarter": "Q2"},
            "name",
        )
        transaction_name = frappe.db.get_value(
            "Commission Transaction",
            {"sales_target_and_commission_sheet": sheet_name},
            "name",
        )
        before = frappe.db.get_value(
            "Commission Transaction",
            transaction_name,
            ["modified", "calculation_hash"],
            as_dict=True,
        )

        recalculate_sheet(sheet_name)
        after_unchanged_rebuild = frappe.db.get_value(
            "Commission Transaction",
            transaction_name,
            ["modified", "calculation_hash"],
            as_dict=True,
        )
        self.assertEqual(after_unchanged_rebuild.modified, before.modified)
        self.assertEqual(after_unchanged_rebuild.calculation_hash, before.calculation_hash)

        self.create_paid_sales_invoice(
            company=company,
            amount=5000,
            sales_team=[{"sales_person": rep.name, "allocated_percentage": 100}],
            pay_invoice=False,
        )

        after = frappe.db.get_value(
            "Commission Transaction",
            transaction_name,
            ["modified", "calculation_hash"],
            as_dict=True,
        )
        self.assertEqual(after.modified, before.modified)
        self.assertEqual(after.calculation_hash, before.calculation_hash)

    def test_payment_cancellation_rebuilds_existing_transaction_sheet(self):
        fiscal_year = "2026"
        company = self.get_company()
        self.ensure_item_group("Home")
        distribution = self.create_even_monthly_distribution(fiscal_year)
        rep = self.create_sales_person(
            target_amount=40000,
            distribution=distribution.name,
            fiscal_year=fiscal_year,
            employee=self.create_employee(company).name,
        )
        chain = self.create_paid_sales_invoice(
            company=company,
            amount=10000,
            sales_team=[{"sales_person": rep.name, "allocated_percentage": 100}],
            return_chain=True,
        )
        sheet_name = frappe.db.get_value(
            "Sales Target and Commission Sheet",
            {"sales_person": rep.name, "quarter": "Q2"},
            "name",
        )
        transaction_name = frappe.db.get_value(
            "Commission Transaction",
            {"sales_target_and_commission_sheet": sheet_name},
            "name",
        )

        chain["payment_entry"].cancel()

        transaction = frappe.get_doc("Commission Transaction", transaction_name)
        sheet = frappe.get_doc("Sales Target and Commission Sheet", sheet_name)
        self.assertEqual(transaction.transaction_status, "Superseded")
        self.assertEqual(sheet.commission_transaction_count, 0)
        self.assertEqual(sheet.total_actual_sales, 0)
        self.assertEqual(sheet.invoice_history[0].invoice_status, "Unpaid")
        self.assertEqual(sheet.total_paid_invoice_amount, 0)
        self.assertAlmostEqual(sheet.total_unpaid_invoice_amount, 10000)

    def create_paid_sales_invoice(
        self, company, amount, sales_team, return_chain=False, pay_invoice=True
    ):
        from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
        from ion_crm_sales.opportunity import make_quotation
        from ion_crm_sales.quotation import make_sales_order
        from ion_crm_sales.sales_order import make_sales_invoice

        opportunity = self.create_opportunity(company, amount)

        quotation = make_quotation(opportunity.name)
        quotation.valid_till = add_months(today(), 1)
        quotation.transaction_date = "2026-04-10"
        quotation.set_posting_time = 1
        quotation.insert(ignore_permissions=True)
        quotation.submit()

        sales_order = make_sales_order(quotation.name)
        sales_order.transaction_date = "2026-04-12"
        sales_order.delivery_date = "2026-04-30"
        sales_order.cost_center = company.cost_center
        sales_order.custom_service_category = "Home"
        sales_order.custom_contract = self.create_active_contract(
            sales_order.customer, sales_order.name
        ).name
        sales_order.set("sales_team", [])
        for row in sales_team:
            sales_order.append("sales_team", row)
        for item in sales_order.items:
            item.cost_center = company.cost_center
        sales_order.set("payment_schedule", [])
        sales_order.append(
            "payment_schedule",
            {
                "due_date": "2026-04-30",
                "invoice_portion": 100,
                "payment_amount": amount,
            },
        )
        sales_order.insert(ignore_permissions=True)
        sales_order.submit()

        invoice = make_sales_invoice(sales_order.name, ignore_permissions=True)
        invoice.posting_date = "2026-04-15"
        invoice.due_date = "2026-04-30"
        invoice.set_posting_time = 1
        invoice.debit_to = company.default_receivable_account
        invoice.cost_center = company.cost_center
        invoice.set("sales_team", [])
        for row in sales_team:
            invoice.append("sales_team", row)
        for item in invoice.items:
            item.income_account = company.default_income_account
            item.cost_center = company.cost_center
        invoice.insert(ignore_permissions=True)
        invoice.submit()
        if not pay_invoice:
            invoice.reload()
            return invoice

        payment = get_payment_entry("Sales Invoice", invoice.name)
        payment.posting_date = "2026-04-20"
        payment.reference_no = random_string(10)
        payment.reference_date = "2026-04-20"
        payment.paid_to = company.default_cash_account
        payment.insert(ignore_permissions=True)
        payment.submit()

        invoice.reload()
        self.assertEqual(invoice.items[0].sales_order, sales_order.name)
        self.assertAlmostEqual(invoice.outstanding_amount, 0)
        if return_chain:
            return {
                "opportunity": opportunity,
                "quotation": quotation,
                "sales_order": sales_order,
                "contract": frappe.get_doc("Contract", sales_order.custom_contract),
                "sales_invoice": invoice,
                "payment_entry": payment,
            }
        return invoice

    def create_opportunity(self, company, amount):
        customer = self.create_customer()
        item = self.create_item(company)
        currency = frappe.db.get_value("Company", company.name, "default_currency")
        selling_price_list = frappe.db.get_value(
            "Price List",
            {"currency": currency, "selling": 1, "enabled": 1},
            "name",
        )

        return frappe.get_doc(
            {
                "doctype": "Opportunity",
                "company": company.name,
                "opportunity_from": "Customer",
                "party_name": customer.name,
                "opportunity_type": "Dedicated",
                "sales_stage": "Opportunity",
                "expected_closing": "2026-04-30",
                "transaction_date": "2026-04-10",
                "currency": currency,
                "selling_price_list": selling_price_list,
                "conversion_rate": 1.0,
                "territory": self.first_record("Territory"),
                "industry": self.first_record("Industry Type"),
                "market_segment": self.first_record("Market Segment"),
                "city": "Test City",
                "custom_material_type": self.first_record("Material Type"),
                "custom_account_manager": "Administrator",
                "custom_surveyor_manager": "Administrator",
                "custom_request": "Commission cycle test request",
                "items": [
                    {
                        "item_code": item.name,
                        "qty": 1,
                        "rate": amount,
                        "uom": item.stock_uom,
                        "custom_availability": "Available",
                        "custom_valuation_rate": amount,
                        "custom_valuation_rate_company_currency": amount,
                    }
                ],
            }
        ).insert(ignore_permissions=True)

    def create_active_contract(self, customer, sales_order):
        contract = frappe.get_doc(
            {
                "doctype": "Contract",
                "party_type": "Customer",
                "party_name": customer,
                "start_date": "2026-04-01",
                "status": "Active",
                "document_type": "Sales Order",
                "document_name": sales_order,
                "contract_terms": "Commission cycle test contract",
            }
        )
        contract.insert(ignore_permissions=True)
        contract.db_set("status", "Active")
        return contract

    def create_sales_person(
        self, target_amount, distribution, fiscal_year, is_manager=False, employee=None
    ):
        suffix = random_string(8).lower()
        sales_person = frappe.get_doc(
            {
                "doctype": "Sales Person",
                "sales_person_name": f"Commission Cycle {suffix}",
                "parent_sales_person": "Sales Team",
                "is_group": 0,
                "enabled": 1,
                "employee": employee,
                "custom_is_sales_manager": 1 if is_manager else 0,
                "targets": [
                    {
                        "item_group": "Home",
                        "fiscal_year": fiscal_year,
                        "target_amount": target_amount,
                        "distribution_id": distribution,
                    }
                ],
            }
        )
        return sales_person.insert(ignore_permissions=True)

    def create_even_monthly_distribution(self, fiscal_year):
        suffix = random_string(8).lower()
        distribution = frappe.get_doc(
            {
                "doctype": "Monthly Distribution",
                "distribution_id": f"Commission Cycle Even {suffix}",
                "fiscal_year": fiscal_year,
            }
        )
        for month in range(1, 13):
            distribution.append(
                "percentages",
                {"month": str(month), "percentage_allocation": 100.0 / 12.0},
            )
        return distribution.insert(ignore_permissions=True)

    def create_employee(self, company):
        suffix = random_string(8).lower()
        return frappe.get_doc(
            {
                "doctype": "Employee",
                "first_name": "Commission",
                "last_name": f"Rep {suffix}",
                "gender": "Male",
                "date_of_birth": "1990-01-01",
                "date_of_joining": "2026-01-01",
                "company": company.name,
            }
        ).insert(ignore_permissions=True)

    def create_customer(self):
        suffix = random_string(8).lower()
        return frappe.get_doc(
            {
                "doctype": "Customer",
                "customer_name": f"Commission Cycle Customer {suffix}",
                "customer_type": "Company",
                "customer_group": self.first_record("Customer Group"),
                "territory": self.first_record("Territory"),
            }
        ).insert(ignore_permissions=True)

    def create_item(self, company):
        self.ensure_item_group("Home")
        suffix = random_string(8).lower()
        return frappe.get_doc(
            {
                "doctype": "Item",
                "item_code": f"COMM-CYCLE-{suffix}",
                "item_name": f"Commission Cycle {suffix}",
                "item_group": "Home",
                "custom_material_type": self.first_record("Material Type"),
                "stock_uom": self.first_record("UOM"),
                "is_stock_item": 0,
                "is_sales_item": 1,
            }
        ).insert(ignore_permissions=True)

    def ensure_item_group(self, item_group):
        if frappe.db.exists("Item Group", item_group):
            return

        frappe.get_doc(
            {
                "doctype": "Item Group",
                "item_group_name": item_group,
                "parent_item_group": "All Item Groups",
                "is_group": 0,
            }
        ).insert(ignore_permissions=True)

    def get_company(self):
        for company in frappe.get_all(
            "Company",
            fields=[
                "name",
                "default_receivable_account",
                "default_income_account",
                "default_cash_account",
                "cost_center",
                "default_currency",
            ],
        ):
            if (
                company.default_receivable_account
                and company.default_income_account
                and company.default_cash_account
                and company.cost_center
                and frappe.db.exists("Account", company.default_receivable_account)
                and frappe.db.exists("Account", company.default_income_account)
                and frappe.db.exists("Account", company.default_cash_account)
                and frappe.db.exists("Cost Center", company.cost_center)
                and frappe.db.exists(
                    "Price List",
                    {"currency": company.default_currency, "selling": 1, "enabled": 1},
                )
            ):
                return company
        self.fail("A company with default receivable, income, cash, and cost center is required")

    def get_expense_account(self, company):
        return frappe.db.get_value(
            "Account",
            {"company": company, "root_type": "Expense", "is_group": 0},
            "name",
        )

    def first_record(self, doctype):
        records = frappe.get_all(doctype, pluck="name", limit=1)
        self.assertTrue(records, f"{doctype} is required for this test")
        return records[0]

    def assert_line(
        self,
        transaction,
        sales_person,
        component,
        basis,
        rate,
        commission,
        cumulative_before=0,
        cumulative_after=0,
        above_target_amount=0,
    ):
        matches = [
            line
            for line in transaction.lines
            if line.sales_person == sales_person and line.commission_component == component
        ]
        self.assertEqual(len(matches), 1)
        line = matches[0]
        self.assertAlmostEqual(line.basis_amount, basis)
        self.assertAlmostEqual(line.rate, rate)
        self.assertAlmostEqual(line.commission_amount, commission)
        self.assertAlmostEqual(line.cumulative_before, cumulative_before)
        self.assertAlmostEqual(line.cumulative_after, cumulative_after)
        self.assertAlmostEqual(line.above_target_amount, above_target_amount)


def create_persistent_sales_commission_cycle():
    """Create and commit a traceable A-to-Z commission scenario on the current site."""
    case = TestSalesTargetandCommissionSheet(
        methodName="test_sales_commission_cycle_creates_transactions_and_rolls_up_sheet"
    )
    case.setUp()

    fiscal_year = "2026"
    company = case.get_company()
    case.ensure_item_group("Home")
    distribution = case.create_even_monthly_distribution(fiscal_year)
    manager = case.create_sales_person(
        target_amount=20000,
        distribution=distribution.name,
        fiscal_year=fiscal_year,
        is_manager=True,
    )
    rep = case.create_sales_person(
        target_amount=40000,
        distribution=distribution.name,
        fiscal_year=fiscal_year,
        employee=case.create_employee(company).name,
    )

    chain = case.create_paid_sales_invoice(
        company=company,
        amount=20000,
        sales_team=[
            {"sales_person": manager.name, "allocated_percentage": 30},
            {"sales_person": rep.name, "allocated_percentage": 70},
        ],
        return_chain=True,
    )

    sheet_names = frappe.get_all(
        "Sales Target and Commission Sheet",
        filters={
            "company": company.name,
            "fiscal_year": fiscal_year,
            "quarter": "Q2",
            "sales_person": ("in", (manager.name, rep.name)),
        },
        pluck="name",
    )
    sheet = frappe.get_doc(
        "Sales Target and Commission Sheet",
        frappe.db.get_value(
            "Sales Target and Commission Sheet",
            {"sales_person": rep.name, "quarter": "Q2"},
            "name",
        ),
    )

    transactions = frappe.get_all(
        "Commission Transaction",
        filters={"sales_target_and_commission_sheet": ("in", sheet_names)},
        pluck="name",
    )

    frappe.db.commit()

    return {
        "company": company.name,
        "monthly_distribution": distribution.name,
        "manager_sales_person": manager.name,
        "rep_sales_person": rep.name,
        "opportunity": chain["opportunity"].name,
        "quotation": chain["quotation"].name,
        "sales_order": chain["sales_order"].name,
        "contract": chain["contract"].name,
        "sales_invoice": chain["sales_invoice"].name,
        "payment_entry": chain["payment_entry"].name,
        "commission_sheet": sheet.name,
        "commission_sheets": sheet_names,
        "commission_transactions": transactions,
        "sheet_total_target": sheet.total_target,
        "sheet_total_actual_sales": sheet.total_actual_sales,
        "sheet_total_commission": sheet.total_commission,
    }


def create_persistent_commission_matrix():
    """Create a committed matrix of opportunity and commission scenarios."""
    case = TestSalesTargetandCommissionSheet(
        methodName="test_sales_commission_cycle_creates_transactions_and_rolls_up_sheet"
    )
    case.setUp()

    fiscal_year = "2026"
    company = case.get_company()
    distribution = case.create_even_monthly_distribution(fiscal_year)
    for item_group in (
        "Home",
        "Hotspot - Sales",
        "Dedicated",
        "Hotel",
        "ISPs",
        "ION Solutions",
        "Hotspot - BA",
        "Ultra - Malls",
    ):
        case.ensure_item_group(item_group)

    sales_manager = case.create_sales_person(
        target_amount=20000,
        distribution=distribution.name,
        fiscal_year=fiscal_year,
        is_manager=True,
    )
    sales_rep = case.create_sales_person(
        target_amount=40000,
        distribution=distribution.name,
        fiscal_year=fiscal_year,
        employee=case.create_employee(company).name,
    )
    ba_am = _create_ba_sales_person(case, company, distribution.name, fiscal_year, "AM")
    ba_exec = _create_ba_sales_person(case, company, distribution.name, fiscal_year, "SM")
    ba_ion_offer = _create_ba_sales_person(case, company, distribution.name, fiscal_year, "SM")
    ba_external = case.create_sales_person(
        target_amount=36000,
        distribution=distribution.name,
        fiscal_year=fiscal_year,
    )

    scenarios = []

    sales_team = [
        {"sales_person": sales_manager.name, "allocated_percentage": 30},
        {"sales_person": sales_rep.name, "allocated_percentage": 70},
    ]
    ba_team = [
        {"sales_person": ba_am.name, "allocated_percentage": 50},
        {"sales_person": ba_exec.name, "allocated_percentage": 50},
    ]

    scenarios.append(
        _create_matrix_flow(
            case,
            company,
            "Sales Home via Dedicated Opportunity",
            "Opportunity",
            "Home",
            20000,
            sales_team,
        )
    )
    scenarios.append(
        _create_matrix_flow(
            case,
            company,
            "Sales Hotspot via S&M Opportunity",
            "Opportunity SM",
            "Hotspot - Sales",
            15000,
            sales_team,
        )
    )

    scenarios.append(
        _create_matrix_flow(
            case,
            company,
            "BA Dedicated NewLead via Dedicated Opportunity",
            "Opportunity",
            "Dedicated",
            12000,
            ba_team,
            invoice_flags={"custom_first_year_contract_invoice": 1},
        )
    )

    upsell_customer = case.create_customer()
    _create_matrix_flow(
        case,
        company,
        "BA Dedicated prior invoice for Upsell seed",
        "Opportunity",
        "Dedicated",
        1000,
        ba_team,
        customer=upsell_customer,
        posting_date="2026-03-10",
        due_date="2026-03-20",
        payment_date="2026-03-20",
    )
    scenarios.append(
        _create_matrix_flow(
            case,
            company,
            "BA Dedicated Upsell via Dedicated Opportunity",
            "Opportunity",
            "Dedicated",
            9000,
            ba_team,
            customer=upsell_customer,
        )
    )

    scenarios.append(
        _create_matrix_flow(
            case,
            company,
            "BA Hotel NewLead via Hotels Opportunity",
            "Opportunity Hotels",
            "Hotel",
            11000,
            ba_team,
        )
    )
    scenarios.append(
        _create_matrix_flow(
            case,
            company,
            "BA ISP NewLead via ISP Opportunity",
            "Opportunity ISP",
            "ISPs",
            13000,
            ba_team,
        )
    )
    scenarios.append(
        _create_matrix_flow(
            case,
            company,
            "BA Hotspot NewLead Bonus via S&M Opportunity",
            "Opportunity SM",
            "Hotspot - BA",
            10000,
            ba_team,
            invoice_flags={"custom_ba_project_acquisition_bonus": 1},
        )
    )
    scenarios.append(
        _create_matrix_flow(
            case,
            company,
            "BA Ultra Malls NewLead Bonus via Tenders Opportunity",
            "Opportunity Tenders",
            "Ultra - Malls",
            10000,
            ba_team,
            invoice_flags={"custom_ba_project_acquisition_bonus": 1},
        )
    )
    scenarios.append(
        _create_matrix_flow(
            case,
            company,
            "BA ION Solutions Role Rates via Dedicated Opportunity",
            "Opportunity",
            "ION Solutions",
            16000,
            [
                {
                    "sales_person": ba_am.name,
                    "allocated_percentage": 50,
                    "custom_ion_role": "Account Lead Acquisition",
                },
                {
                    "sales_person": ba_ion_offer.name,
                    "allocated_percentage": 50,
                    "custom_ion_role": "Offer Team",
                },
            ],
        )
    )
    scenarios.append(
        _create_matrix_flow(
            case,
            company,
            "BA Dedicated Late Payment Penalty",
            "Opportunity",
            "Dedicated",
            8000,
            ba_team,
            posting_date="2026-04-01",
            due_date="2026-04-01",
            payment_date="2026-06-01",
            invoice_flags={"custom_payment_plan": "Quarterly"},
        )
    )
    scenarios.append(
        _create_matrix_flow(
            case,
            company,
            "BA Dedicated External Rep Approved",
            "Opportunity",
            "Dedicated",
            7000,
            [
                {"sales_person": ba_am.name, "allocated_percentage": 50},
                {"sales_person": ba_external.name, "allocated_percentage": 50},
            ],
            invoice_flags={"custom_external_rep_approved": 1},
        )
    )

    sales_people = (
        sales_manager.name,
        sales_rep.name,
        ba_am.name,
        ba_exec.name,
        ba_ion_offer.name,
        ba_external.name,
    )
    sheet_names = frappe.get_all(
        "Sales Target and Commission Sheet",
        filters={
            "company": company.name,
            "fiscal_year": fiscal_year,
            "quarter": "Q2",
            "sales_person": ("in", sales_people),
        },
        pluck="name",
    )

    tx_rows = frappe.get_all(
        "Commission Transaction",
        filters={"sales_target_and_commission_sheet": ("in", sheet_names)},
        fields=[
            "name",
            "department",
            "sales_invoice",
            "transaction_type",
            "eligible_amount",
            "total_commission",
            "fully_paid_on",
        ],
        order_by="fully_paid_on, name",
    )

    frappe.db.commit()

    return {
        "company": company.name,
        "monthly_distribution": distribution.name,
        "sales_people": {
            "sales_manager": sales_manager.name,
            "sales_rep": sales_rep.name,
            "ba_am": ba_am.name,
            "ba_exec": ba_exec.name,
            "ba_ion_offer": ba_ion_offer.name,
            "ba_external": ba_external.name,
        },
        "scenarios": scenarios,
        "commission_sheets": sheet_names,
        "commission_transactions": tx_rows,
        "unsupported_transaction_types": {
            "Old": "The current ledger sync always calls detect_tx_type(..., is_renewal_flag=False), so Old cannot be produced.",
            "Renewal": "Renewal is available in DocType options but is not returned by detect_tx_type or passed by sync logic.",
        },
    }


def _create_ba_sales_person(case, company, distribution, fiscal_year, role_profile):
    user = _create_user(role_profile)
    employee = case.create_employee(company)
    employee.user_id = user.name
    employee.department = _business_department(company.name)
    employee.save(ignore_permissions=True)
    return case.create_sales_person(
        target_amount=36000,
        distribution=distribution,
        fiscal_year=fiscal_year,
        employee=employee.name,
    )


def _create_user(role_profile):
    suffix = random_string(8).lower()
    return frappe.get_doc(
        {
            "doctype": "User",
            "email": f"commission.matrix.{suffix}@example.com",
            "first_name": "Commission",
            "last_name": f"Matrix {suffix}",
            "user_type": "System User",
            "role_profile_name": role_profile,
            "send_welcome_email": 0,
        }
    ).insert(ignore_permissions=True)


def _business_department(company):
    existing = frappe.db.get_value("Department", {"department_name": "Business Accounts"})
    if existing:
        return existing
    abbr = frappe.db.get_value("Company", company, "abbr")
    return frappe.get_doc(
        {
            "doctype": "Department",
            "department_name": "Business Accounts",
            "company": company,
            "parent_department": "All Departments",
            "is_group": 0,
        }
    ).insert(ignore_permissions=True).name


def _create_matrix_flow(
    case,
    company,
    label,
    opportunity_doctype,
    service_category,
    amount,
    sales_team,
    customer=None,
    posting_date="2026-04-15",
    due_date="2026-04-30",
    payment_date="2026-04-20",
    invoice_flags=None,
):
    from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
    from ion_crm_sales.quotation import make_sales_order
    from ion_crm_sales.sales_order import make_sales_invoice

    opportunity = _create_matrix_opportunity(
        case, company, opportunity_doctype, service_category, amount, customer=customer
    )
    quotation = _make_matrix_quotation(opportunity_doctype, opportunity.name)
    quotation.valid_till = add_months(today(), 1)
    quotation.transaction_date = posting_date
    quotation.set_posting_time = 1
    quotation.insert(ignore_permissions=True)
    quotation.submit()

    sales_order = make_sales_order(quotation.name)
    sales_order.transaction_date = posting_date
    sales_order.delivery_date = due_date
    sales_order.cost_center = company.cost_center
    sales_order.custom_service_category = service_category
    sales_order.custom_contract = case.create_active_contract(
        sales_order.customer, sales_order.name
    ).name
    sales_order.set("sales_team", [])
    for row in sales_team:
        sales_order.append("sales_team", row)
    for item in sales_order.items:
        item.cost_center = company.cost_center
    sales_order.set("payment_schedule", [])
    sales_order.append(
        "payment_schedule",
        {"due_date": due_date, "invoice_portion": 100, "payment_amount": amount},
    )
    sales_order.insert(ignore_permissions=True)
    sales_order.submit()

    invoice = make_sales_invoice(sales_order.name, ignore_permissions=True)
    invoice.posting_date = posting_date
    invoice.due_date = due_date
    invoice.set_posting_time = 1
    invoice.debit_to = company.default_receivable_account
    invoice.cost_center = company.cost_center
    for fieldname, value in (invoice_flags or {}).items():
        if invoice.meta.has_field(fieldname):
            invoice.set(fieldname, value)
    invoice.set("sales_team", [])
    for row in sales_team:
        invoice.append("sales_team", row)
    for item in invoice.items:
        item.income_account = company.default_income_account
        item.cost_center = company.cost_center
    invoice.insert(ignore_permissions=True)
    invoice.submit()
    invoice.reload()
    case.assertEqual(invoice.custom_service_category, service_category)

    payment = get_payment_entry("Sales Invoice", invoice.name)
    payment.posting_date = payment_date
    payment.reference_no = random_string(10)
    payment.reference_date = payment_date
    payment.paid_to = company.default_cash_account
    payment.insert(ignore_permissions=True)
    payment.submit()

    return {
        "label": label,
        "opportunity_doctype": opportunity_doctype,
        "service_category": service_category,
        "opportunity": opportunity.name,
        "quotation": quotation.name,
        "sales_order": sales_order.name,
        "sales_invoice": invoice.name,
        "payment_entry": payment.name,
    }


def _create_matrix_opportunity(
    case, company, opportunity_doctype, service_category, amount, customer=None
):
    if not customer:
        customer = case.create_customer()
    item = case.create_item_for_group(company, service_category)
    doc = frappe.new_doc(opportunity_doctype)
    values = {
        "company": company.name,
        "opportunity_from": "Customer",
        "party_name": customer.name if hasattr(customer, "name") else customer,
        "opportunity_type": "Dedicated",
        "sales_stage": "Opportunity",
        "expected_closing": "2026-04-30",
        "transaction_date": "2026-04-10",
        "conversion_rate": 1.0,
        "territory": case.first_record("Territory"),
        "industry": case.first_record("Industry Type"),
        "market_segment": case.first_record("Market Segment"),
        "city": "Test City",
        "custom_material_type": case.first_record("Material Type"),
        "custom_account_manager": "Administrator",
        "custom_surveyor_manager": "Administrator",
        "custom_request": f"Commission matrix {opportunity_doctype} {service_category}",
        "custom_rfp_document": "/files/commission-matrix-rfp.pdf",
    }
    for fieldname, value in values.items():
        if doc.meta.has_field(fieldname):
            doc.set(fieldname, value)
    doc.append(
        "items",
        {
            "item_code": item.name,
            "qty": 1,
            "rate": amount,
            "amount": amount,
            "base_rate": amount,
            "base_amount": amount,
            "uom": item.stock_uom,
            "custom_availability": "Available",
            "custom_valuation_rate": amount,
            "custom_valuation_rate_company_currency": amount,
        },
    )
    return doc.insert(ignore_permissions=True)


def _make_matrix_quotation(opportunity_doctype, opportunity_name):
    if opportunity_doctype == "Opportunity":
        from ion_crm_sales.opportunity import make_quotation
    elif opportunity_doctype == "Opportunity SM":
        from ion_crm_sales.ion_crm_sales.doctype.opportunity_sm.opportunity_sm import make_quotation
    elif opportunity_doctype == "Opportunity Hotels":
        from ion_crm_sales.ion_crm_sales.doctype.opportunity_hotels.opportunity_hotels import make_quotation
    elif opportunity_doctype == "Opportunity Tenders":
        from ion_crm_sales.ion_crm_sales.doctype.opportunity_tenders.opportunity_tenders import make_quotation
    elif opportunity_doctype == "Opportunity ISP":
        from ion_crm_sales.ion_crm_sales.doctype.opportunity_isp.opportunity_isp import make_quotation
    else:
        frappe.throw(f"Unsupported opportunity doctype {opportunity_doctype}")
    return make_quotation(opportunity_name)


def _create_item_for_group(case, company, item_group):
    case.ensure_item_group(item_group)
    suffix = random_string(8).lower()
    return frappe.get_doc(
        {
            "doctype": "Item",
            "item_code": f"COMM-MATRIX-{suffix}",
            "item_name": f"Commission Matrix {item_group} {suffix}",
            "item_group": item_group,
            "custom_material_type": case.first_record("Material Type"),
            "stock_uom": case.first_record("UOM"),
            "is_stock_item": 0,
            "is_sales_item": 1,
        }
    ).insert(ignore_permissions=True)


TestSalesTargetandCommissionSheet.create_item_for_group = _create_item_for_group
