# Copyright (c) 2025, ard.ly and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class Booking(Document):
	def validate(self):
		self._validate_payment()
		self._compute_financials()

	def _validate_payment(self):
		"""Ensure payment_amount >= package_price when payment is present."""
		if self.payment_amount and self.package_price:
			if float(self.payment_amount) < float(self.package_price):
				frappe.msgprint(
					_("Payment amount ({0}) is less than package price ({1}). "
					  "The client_credit will be 0.").format(
						self.payment_amount, self.package_price
					),
					indicator="orange",
					alert=True,
				)

	def _compute_financials(self):
		"""Re-derive financial fields on every save to keep them consistent."""
		if self.package_price and self.commission_percent is not None:
			price = float(self.package_price)
			pct = float(self.commission_percent)
			self.company_share = price
			self.distributor_commission = round(price * (pct / 100), 2)
		if self.payment_amount and self.package_price:
			self.client_credit = round(
				max(float(self.payment_amount) - float(self.package_price), 0), 2
			)
