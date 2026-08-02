/* Client wiring for the custom "Serial and Batch No" fields on Sales Order Item.
 *
 * The fields mirror Delivery Note Item, but they were added through Customize Form
 * so they carry a `custom_` prefix. Every erpnext handler for serial / batch is keyed
 * to the core fieldnames, so nothing here comes for free -- the button, the link
 * filters and the mutual exclusivity between the two entry modes are all set up below.
 */

const SB_USE_FIELDS = "custom_use_serial_no__batch_fields";
const SB_BUNDLE = "custom_serial_and_batch_bundle";
const SB_SERIAL_NO = "custom_serial_no";
const SB_BATCH_NO = "custom_batch_no";

frappe.ui.form.on("Sales Order", {
	setup(frm) {
		set_serial_batch_queries(frm);
	},

	refresh(frm) {
		set_bundle_route_options(frm);
	},
});

frappe.ui.form.on("Sales Order Item", {
	custom_pick_serial__batch_no(frm, cdt, cdn) {
		pick_serial_and_batch(frm, cdt, cdn);
	},

	custom_use_serial_no__batch_fields(frm, cdt, cdn) {
		const row = locals[cdt][cdn];

		// The two modes are exclusive: a bundle, or the plain Serial No / Batch No fields.
		if (cint(row[SB_USE_FIELDS])) {
			clear_bundle(frm, cdt, cdn);
		} else {
			clear_serial_batch_fields(frm, cdt, cdn);
		}
	},

	item_code(frm, cdt, cdn) {
		clear_selection(frm, cdt, cdn);
	},

	warehouse(frm, cdt, cdn) {
		// A bundle is tied to the warehouse it was picked from.
		clear_bundle(frm, cdt, cdn);
	},
});

function set_serial_batch_queries(frm) {
	const grid = frm.fields_dict.items && frm.fields_dict.items.grid;
	if (!grid) {
		return;
	}

	if (grid.get_field(SB_BUNDLE)) {
		frm.set_query(SB_BUNDLE, "items", function (doc, cdt, cdn) {
			const row = locals[cdt][cdn];
			return {
				filters: {
					item_code: row.item_code,
					voucher_type: doc.doctype,
					voucher_no: ["in", [doc.name, ""]],
					is_cancelled: 0,
				},
			};
		});
	}

	if (grid.get_field(SB_BATCH_NO)) {
		frm.set_query(SB_BATCH_NO, "items", function (doc, cdt, cdn) {
			const row = locals[cdt][cdn];

			if (!row.item_code) {
				frappe.throw(__("Please enter Item Code to get batch no"));
			}

			const filters = {
				item_code: row.item_code,
				posting_date: doc.transaction_date || frappe.datetime.nowdate(),
			};

			if (row.warehouse) {
				filters.warehouse = row.warehouse;
			}

			return {
				query: "erpnext.controllers.queries.get_batch_no",
				filters: filters,
			};
		});
	}
}

function set_bundle_route_options(frm) {
	// Prefill item / voucher type when a bundle is created straight from the link field.
	const field = frm.get_docfield("items", SB_BUNDLE);
	if (!field) {
		return;
	}

	field.get_route_options_for_new_doc = (row) => {
		return {
			item_code: row.doc.item_code,
			voucher_type: frm.doc.doctype,
			warehouse: row.doc.warehouse,
			company: frm.doc.company,
			type_of_transaction: "Outward",
		};
	};
}

function pick_serial_and_batch(frm, cdt, cdn) {
	const row = locals[cdt][cdn];

	if (!row.item_code) {
		frappe.throw(__("Row #{0}: Please select an Item first.", [row.idx]));
	}

	frappe.db.get_value("Item", row.item_code, ["has_batch_no", "has_serial_no"]).then((r) => {
		const item = r.message;

		if (!item || (!item.has_batch_no && !item.has_serial_no)) {
			frappe.msgprint({
				title: __("Not Applicable"),
				message: __("Item {0} is not maintained by Serial No or Batch No.", [
					row.item_code.bold(),
				]),
				indicator: "orange",
			});
			return;
		}

		if (!row.warehouse) {
			frappe.throw(
				__("Row #{0}: Please set the Warehouse before picking Serial / Batch No.", [row.idx])
			);
		}

		new erpnext.SerialBatchPackageSelector(frm, get_picker_row(row, item), (bundle) => {
			if (!bundle) {
				return;
			}

			frappe.model.set_value(cdt, cdn, {
				[SB_BUNDLE]: bundle.name,
				[SB_USE_FIELDS]: 0,
				[SB_SERIAL_NO]: "",
				[SB_BATCH_NO]: "",
			});
		});
	});
}

/* erpnext's picker reads and writes the core fieldnames on the row it is handed, so it
 * gets a detached copy with the custom values mapped onto those names. `serial_no` and
 * `batch_no` are deliberately left blank -- when they hold a value the picker calls
 * frappe.model.set_value() for them, which would write core fieldnames that do not
 * exist on Sales Order Item. The result comes back through the callback instead.
 */
function get_picker_row(row, item) {
	return Object.assign({}, row, {
		has_serial_no: item.has_serial_no,
		has_batch_no: item.has_batch_no,
		type_of_transaction: "Outward",
		is_rejected: 0,
		serial_and_batch_bundle: row[SB_BUNDLE] || "",
		use_serial_batch_fields: 0,
		serial_no: "",
		batch_no: "",
		title: get_picker_title(item),
	});
}

function get_picker_title(item) {
	if (item.has_serial_no && item.has_batch_no) {
		return __("Select Serial and Batch");
	}

	return item.has_serial_no ? __("Select Serial No") : __("Select Batch No");
}

function clear_selection(frm, cdt, cdn) {
	clear_bundle(frm, cdt, cdn);
	clear_serial_batch_fields(frm, cdt, cdn);
}

function clear_bundle(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	if (row[SB_BUNDLE]) {
		frappe.model.set_value(cdt, cdn, SB_BUNDLE, "");
	}
}

function clear_serial_batch_fields(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	const values = {};

	if (row[SB_SERIAL_NO]) {
		values[SB_SERIAL_NO] = "";
	}

	if (row[SB_BATCH_NO]) {
		values[SB_BATCH_NO] = "";
	}

	if (Object.keys(values).length) {
		frappe.model.set_value(cdt, cdn, values);
	}
}
