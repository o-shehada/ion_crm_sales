import frappe
from frappe.tests.utils import FrappeTestCase

from ion_crm_sales.ion_crm_sales.commission.config import BA_RATES, SALES_RATES


class TestCommissionRateSettings(FrappeTestCase):
    def test_settings_are_seeded_without_changing_code_configuration(self):
        settings = frappe.get_single("Commission Rate Settings")

        self.assertAlmostEqual(settings.sales_home_normal_rate, 0.05)
        self.assertAlmostEqual(settings.sales_hotspot_above_target_rate, 6)
        self.assertAlmostEqual(settings.ba_dedicated_old_rate, 0.75)
        self.assertAlmostEqual(settings.ba_dedicated_new_rate, 1)
        self.assertAlmostEqual(settings.ion_offer_team_rate, 5)
        self.assertEqual(settings.project_acquisition_bonus, 3000)
        self.assertEqual(settings.yearly_grace_days, 90)
        self.assertEqual(SALES_RATES["HOME"]["normal"], 0.0005)
        self.assertEqual(BA_RATES["DEDICATED"]["new"], 0.01)
