import frappe
from frappe.model.document import Document
from frappe.utils import flt


class CommissionRateSettings(Document):
    def validate(self):
        split_pairs = (
            ("sales_home_normal_manager_split", "sales_home_normal_team_split"),
            ("sales_home_above_manager_split", "sales_home_above_team_split"),
            ("sales_hotspot_normal_manager_split", "sales_hotspot_normal_team_split"),
            ("sales_hotspot_above_manager_split", "sales_hotspot_above_team_split"),
        )
        for manager_field, team_field in split_pairs:
            total = flt(self.get(manager_field)) + flt(self.get(team_field))
            if abs(total - 100.0) > 0.0001:
                manager_label = self.meta.get_label(manager_field)
                team_label = self.meta.get_label(team_field)
                frappe.throw(f"{manager_label} and {team_label} must total 100%.")
