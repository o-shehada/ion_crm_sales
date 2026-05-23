# -*- coding: utf-8 -*-
"""Commission transaction ledger generation and aggregation."""

import hashlib
import json

import frappe
from frappe.utils import flt, getdate, now_datetime

from ion_crm_sales.ion_crm_sales.commission.ba import (
	_ams_on_si,
	_ba_recipients_for_category,
	_category_amounts_for_si as _ba_category_amounts_for_si,
	_employees_on_si,
	_ion_role_for_person_on_si,
	_non_am_sm_employees_on_si,
	_penalty_factor_for_si,
	_rate_ion,
	_rate_non_ion,
	_skip_ba_commission,
	detect_tx_type,
)
from ion_crm_sales.ion_crm_sales.commission.compute import (
	_managers_on_si,
	_rest_on_si,
	_sales_category_amounts_for_si,
)
from ion_crm_sales.ion_crm_sales.commission.config import (
	BA_ITEM_GROUPS,
	FIRST_YEAR_ADDON_RATE,
	ION_ABOVE_ADDON,
	ION_ROLE_RATES,
	PROJECT_ACQ_BONUS,
	SALES_ITEM_GROUPS,
	SALES_RATES,
	SALES_SPLITS,
)
from ion_crm_sales.ion_crm_sales.commission.helpers import (
	employee_for_sales_person,
	get_fully_paid_invoice_names,
	get_fully_paid_invoice_refs,
	get_quarter_window,
	quarter_target_from_distribution,
)


CALCULATION_VERSION = "commission-ledger-v1"
ACTIVE_TRANSACTION_STATUSES = ("Draft", "Posted")


def sync_sheet_transactions(sheet):
	"""Create/update draft commission transactions for the sheet window."""
	q_start, q_end, months3 = get_quarter_window(sheet.fiscal_year, sheet.quarter)
	targets = _targets_by_department(sheet, months3)
	seen = set()

	seen.update(_sync_sales_transactions(sheet, q_start, q_end, targets.get("Sales", {})))
	seen.update(
		_sync_ba_transactions(sheet, q_start, q_end, targets.get("Business Accounts", {}))
	)

	_mark_stale_transactions(sheet, seen)
	aggregate_sheet_from_transactions(sheet, targets)
	sheet.last_transaction_sync_on = now_datetime()
	sheet.transaction_sync_status = "Synced"
	sheet.source_of_totals = "Commission Transactions"


def aggregate_sheet_from_transactions(sheet, targets=None):
	"""Summarize active commission transaction lines into sheet commission lines."""
	if targets is None:
		_q_start, _q_end, months3 = get_quarter_window(sheet.fiscal_year, sheet.quarter)
		targets = _targets_by_department(sheet, months3)

	actual_by_person = {}
	commission_by_person = {}
	transaction_count = 0

	for tx in frappe.get_all(
		"Commission Transaction",
		filters={
			"sales_target_and_commission_sheet": sheet.name,
			"transaction_status": ["in", ACTIVE_TRANSACTION_STATUSES],
		},
		pluck="name",
	):
		transaction_count += 1
		doc = frappe.get_doc("Commission Transaction", tx)
		for line in doc.get("lines") or []:
			sp = line.get("sales_person")
			if not sp:
				continue
			if line.get("commission_component") == "Base":
				actual_by_person[sp] = actual_by_person.get(sp, 0.0) + flt(line.get("basis_amount"))
			commission_by_person[sp] = commission_by_person.get(sp, 0.0) + flt(
				line.get("commission_amount")
			)

	total_target = total_actual = total_commission = 0.0
	for line in sheet.get("commission_lines") or []:
		line.target_value = flt((targets.get(line.department) or {}).get(line.sales_person))
		line.actual_sales = flt(actual_by_person.get(line.sales_person))
		line.achievement_pct = (
			round(line.actual_sales / line.target_value * 100.0, 2)
			if line.target_value
			else 0.0
		)
		line.commission_value = flt(commission_by_person.get(line.sales_person))
		line.commission_rate = (
			round(line.commission_value / line.actual_sales * 100.0, 2)
			if line.actual_sales
			else 0.0
		)
		total_target += flt(line.target_value)
		total_actual += flt(line.actual_sales)
		total_commission += flt(line.commission_value)

	sheet.total_target = round(total_target, 2)
	sheet.total_actual_sales = round(total_actual, 2)
	sheet.total_commission = round(total_commission, 2)
	sheet.commission_transaction_count = transaction_count


def _targets_by_department(sheet, months3):
	targets = {"Sales": {}, "Business Accounts": {}}
	for line in sheet.get("commission_lines") or []:
		if line.department not in targets:
			continue
		targets[line.department][line.sales_person] = quarter_target_from_distribution(
			line.sales_person, sheet.fiscal_year, months3
		)
	return targets


def _sync_sales_transactions(sheet, q_start, q_end, target):
	people = set(target)
	if not people:
		return set()

	cum_exposure = {sp: 0.0 for sp in people}
	seen = set()

	for paid_on, si_name in get_fully_paid_invoice_names(
		sheet.company,
		q_start,
		q_end,
		tuple(SALES_ITEM_GROUPS.values()),
	):
		si = frappe.get_doc("Sales Invoice", si_name)
		lines = []
		cat_amounts = _sales_category_amounts_for_si(si)
		mgrs = _people_on_sheet(_managers_on_si(si), people)
		rest = _people_on_sheet(_rest_on_si(si), people)

		for cat, amount in cat_amounts.items():
			rates = SALES_RATES[cat]
			splits = SALES_SPLITS[cat]

			if mgrs:
				basis = amount * splits["normal"]["manager"] / len(mgrs)
				for sp in mgrs:
					_add_base_line(lines, si, sp, "Sales", cat, basis, rates["normal"], len(mgrs))
					_add_above_line(lines, si, sp, "Sales", cat, basis, rates["above"], target, cum_exposure)
			elif rest:
				basis = amount * splits["normal"]["manager"] / len(rest)
				for sp in rest:
					_add_base_line(lines, si, sp, "Sales", cat, basis, rates["normal"], len(rest))
					_add_above_line(lines, si, sp, "Sales", cat, basis, rates["above"], target, cum_exposure)

			if rest:
				basis = amount * splits["normal"]["rest"] / len(rest)
				for sp in rest:
					_add_base_line(lines, si, sp, "Sales", cat, basis, rates["normal"], len(rest))
					_add_above_line(lines, si, sp, "Sales", cat, basis, rates["above"], target, cum_exposure)

		if lines:
			_apply_line_targets(lines, target)
			key = _source_key(sheet, "Sales", si.name)
			_upsert_transaction(sheet, si, paid_on, "Sales", None, lines, key)
			seen.add(key)

	return seen


def _sync_ba_transactions(sheet, q_start, q_end, target):
	people = set(target)
	if not people:
		return set()

	cum_exposure = {sp: 0.0 for sp in people}
	seen = set()

	for paid_on, inv in get_fully_paid_invoice_refs(
		sheet.company,
		q_start,
		q_end,
		tuple(BA_ITEM_GROUPS.values()),
	):
		si = frappe.get_doc("Sales Invoice", inv["name"])
		if _skip_ba_commission(si):
			continue

		lines = []
		prev_cum_before = dict(cum_exposure)
		tx_type = detect_tx_type(si, paid_on, is_renewal_flag=False)
		cat_amounts = _ba_category_amounts_for_si(si)
		externals_ok = bool(
			si.get("custom_external_rep_approved") or getattr(si, "external_rep_approved", None)
		)

		for cat_key, amount in cat_amounts.items():
			if amount <= 0:
				continue
			recipients = _people_on_sheet(
				_ba_recipients_for_category(si, cat_key, externals_ok), people
			)
			if not recipients:
				continue
			basis = amount / len(recipients)

			for sp in recipients:
				if cat_key == "ION_SOLUTIONS":
					role = _ion_role_for_person_on_si(si, sp)
					if not role:
						continue
					base_rate = ION_ROLE_RATES.get(role, 0.0)
					above_now = cum_exposure[sp] >= (target.get(sp) or 0.0)
					_add_base_line(
						lines,
						si,
						sp,
						"Business Accounts",
						cat_key,
						basis,
						base_rate,
						len(recipients),
						tx_type=tx_type,
						ion_role=role,
					)
					if above_now:
						lines.append(
							_line(
								si,
								sp,
								"Business Accounts",
								cat_key,
								"Above Target",
								basis,
								ION_ABOVE_ADDON,
								basis * ION_ABOVE_ADDON,
								tx_type=tx_type,
								cumulative_before=cum_exposure[sp],
								cumulative_after=cum_exposure[sp] + basis,
								above_target_amount=basis,
								split_count=len(recipients),
								ion_role=role,
							)
						)
					cum_exposure[sp] += basis
				else:
					base_rate = _rate_non_ion(cat_key, tx_type, False)
					above_rate = _rate_non_ion(cat_key, tx_type, True)
					_add_base_line(
						lines,
						si,
						sp,
						"Business Accounts",
						cat_key,
						basis,
						base_rate,
						len(recipients),
						tx_type=tx_type,
					)
					_add_above_line(
						lines,
						si,
						sp,
						"Business Accounts",
						cat_key,
						basis,
						above_rate,
						target,
						cum_exposure,
						tx_type=tx_type,
					)

		if tx_type == "NewLead" and (
			si.get("custom_first_year_contract_invoice")
			or getattr(si, "first_year_contract_invoice", None)
		):
			non_mgr = _people_on_sheet(_non_am_sm_employees_on_si(si), people)
			if non_mgr:
				commission = flt(si.base_grand_total) * FIRST_YEAR_ADDON_RATE / len(non_mgr)
				for sp in non_mgr:
					lines.append(
						_line(
							si,
							sp,
							"Business Accounts",
							"",
							"First Year Addon",
							flt(si.base_grand_total),
							FIRST_YEAR_ADDON_RATE,
							commission,
							tx_type=tx_type,
							split_count=len(non_mgr),
						)
					)

		if tx_type == "NewLead" and (
			si.get("custom_ba_project_acquisition_bonus")
			or getattr(si, "ba_project_acquisition_bonus", None)
		):
			has_bonus_category = bool(cat_amounts.get("HOTSPOT") or cat_amounts.get("ULTRA_MALLS"))
			employees = _people_on_sheet(_employees_on_si(si), people)
			if has_bonus_category and employees:
				commission = PROJECT_ACQ_BONUS / len(employees)
				for sp in employees:
					lines.append(
						_line(
							si,
							sp,
							"Business Accounts",
							"",
							"Acquisition Bonus",
							0,
							0,
							commission,
							tx_type=tx_type,
							split_count=len(employees),
						)
					)

		factor = _penalty_factor_for_si(si, paid_on)
		if factor < 1.0:
			_add_ba_penalty_lines(
				lines, si, paid_on, tx_type, cat_amounts, externals_ok, factor, target, prev_cum_before, people
			)

		if lines:
			_apply_line_targets(lines, target)
			key = _source_key(sheet, "Business Accounts", si.name)
			_upsert_transaction(sheet, si, paid_on, "Business Accounts", tx_type, lines, key)
			seen.add(key)

	return seen


def _add_ba_penalty_lines(
	lines, si, paid_on, tx_type, cat_amounts, externals_ok, factor, target, prev_cum_before, people
):
	ams = _people_on_sheet(_ams_on_si(si), people)
	if not ams:
		return

	am_subtotal = 0.0
	for cat_key, amount in cat_amounts.items():
		if amount <= 0:
			continue
		recipients = _ba_recipients_for_category(si, cat_key, externals_ok)
		if not recipients:
			continue
		basis = amount / len(recipients)
		for sp in recipients:
			if sp not in ams:
				continue
			if cat_key == "ION_SOLUTIONS":
				role = _ion_role_for_person_on_si(si, sp)
				if not role:
					continue
				above_prev = prev_cum_before.get(sp, 0.0) >= (target.get(sp) or 0.0)
				am_subtotal += basis * _rate_ion(role, above_prev)
			else:
				base_rate = _rate_non_ion(cat_key, tx_type, False)
				above_rate = _rate_non_ion(cat_key, tx_type, True)
				am_subtotal += basis * base_rate
				prev = prev_cum_before.get(sp, 0.0) or 0.0
				tgt = target.get(sp, 0.0) or 0.0
				above_part = max(0.0, (prev + basis) - tgt) - max(0.0, prev - tgt)
				am_subtotal += above_part * above_rate

	reduction = am_subtotal * (1.0 - factor)
	if reduction <= 0:
		return

	for sp in ams:
		lines.append(
			_line(
				si,
				sp,
				"Business Accounts",
				"",
				"Penalty",
				0,
				0,
				-(reduction / len(ams)),
				tx_type=tx_type,
				penalty_factor=factor,
				remarks=f"Penalty based on fully paid date {paid_on}",
			)
		)


def _add_base_line(lines, si, sp, department, category, basis, rate, split_count, tx_type=None, ion_role=None):
	lines.append(
		_line(
			si,
			sp,
			department,
			category,
			"Base",
			basis,
			rate,
			basis * rate,
			tx_type=tx_type,
			split_count=split_count,
			split_percentage=(100.0 / split_count if split_count else 0),
			ion_role=ion_role,
		)
	)


def _add_above_line(lines, si, sp, department, category, basis, rate, target, cum_exposure, tx_type=None):
	prev = cum_exposure.get(sp, 0.0) or 0.0
	tgt = target.get(sp, 0.0) or 0.0
	above_part = max(0.0, (prev + basis) - tgt) - max(0.0, prev - tgt)
	if above_part > 0:
		lines.append(
			_line(
				si,
				sp,
				department,
				category,
				"Above Target",
				above_part,
				rate,
				above_part * rate,
				tx_type=tx_type,
				cumulative_before=prev,
				cumulative_after=prev + basis,
				above_target_amount=above_part,
			)
		)
	cum_exposure[sp] = prev + basis


def _line(
	si,
	sales_person,
	department,
	service_category,
	component,
	basis,
	rate,
	commission,
	tx_type=None,
	cumulative_before=0,
	cumulative_after=0,
	above_target_amount=0,
	split_percentage=0,
	split_count=0,
	penalty_factor=0,
	ion_role=None,
	remarks=None,
):
	return {
		"sales_person": sales_person,
		"employee": employee_for_sales_person(sales_person),
		"department": department,
		"service_category": service_category,
		"commission_component": component,
		"transaction_type": tx_type,
		"basis_amount": flt(basis),
		"target_value": 0,
		"cumulative_before": flt(cumulative_before),
		"cumulative_after": flt(cumulative_after),
		"above_target_amount": flt(above_target_amount),
		"rate": flt(rate) * 100,
		"split_percentage": flt(split_percentage),
		"split_count": split_count,
		"penalty_factor": flt(penalty_factor),
		"commission_amount": flt(commission),
		"ion_role": ion_role,
		"remarks": remarks,
	}


def _upsert_transaction(sheet, si, paid_on, department, tx_type, lines, source_key):
	total_commission = sum(flt(line.get("commission_amount")) for line in lines)
	eligible_amount = sum(flt(line.get("basis_amount")) for line in lines if line.get("commission_component") == "Base")
	payload_hash = _calculation_hash(lines)

	name = frappe.db.get_value("Commission Transaction", {"source_key": source_key}, "name")
	doc = frappe.get_doc("Commission Transaction", name) if name else frappe.new_doc("Commission Transaction")
	doc.update(
		{
			"company": sheet.company,
			"fiscal_year": sheet.fiscal_year,
			"quarter": sheet.quarter,
			"department": department,
			"sales_target_and_commission_sheet": sheet.name,
			"sales_invoice": si.name,
			"customer": si.customer,
			"posting_date": si.posting_date,
			"fully_paid_on": getdate(paid_on),
			"transaction_status": "Draft",
			"transaction_kind": "Original",
			"transaction_type": tx_type,
			"eligible_amount": eligible_amount,
			"actual_basis_amount": eligible_amount,
			"total_commission": total_commission,
			"calculation_version": CALCULATION_VERSION,
			"calculation_hash": payload_hash,
			"source_key": source_key,
			"is_backfill": 0,
		}
	)
	_set_if_field_exists(doc, "invoice", si.name)
	_set_if_field_exists(doc, "invoice_status", si.status)
	_set_if_field_exists(doc, "commission_status", "Unpaid")
	_set_if_field_exists(doc, "amount", total_commission)
	_set_if_field_exists(doc, "date", getdate(paid_on))
	doc.set("lines", [])
	for line in lines:
		doc.append("lines", line)

	if doc.is_new():
		doc.insert(ignore_permissions=True)
	else:
		doc.save(ignore_permissions=True)


def _mark_stale_transactions(sheet, seen):
	for row in frappe.get_all(
		"Commission Transaction",
		filters={
			"sales_target_and_commission_sheet": sheet.name,
			"transaction_status": ["in", ACTIVE_TRANSACTION_STATUSES],
		},
		fields=["name", "source_key"],
	):
		if row.source_key in seen:
			continue
		doc = frappe.get_doc("Commission Transaction", row.name)
		doc.transaction_status = "Superseded"
		doc.save(ignore_permissions=True)


def _source_key(sheet, department, invoice):
	return f"{sheet.name}|{department}|{invoice}"


def _calculation_hash(lines):
	payload = json.dumps(lines, sort_keys=True, default=str)
	return hashlib.sha256(payload.encode()).hexdigest()


def _people_on_sheet(people, allowed):
	out = []
	for person in people:
		if person in allowed and person not in out:
			out.append(person)
	return out


def _apply_line_targets(lines, target):
	for line in lines:
		line["target_value"] = flt(target.get(line.get("sales_person")))


def _set_if_field_exists(doc, fieldname, value):
	if doc.meta.has_field(fieldname):
		doc.set(fieldname, value)
