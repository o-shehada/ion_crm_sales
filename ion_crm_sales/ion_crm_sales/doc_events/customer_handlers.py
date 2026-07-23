from __future__ import annotations


BRANCH_CUSTOMER_TABLE_FIELD = "custom_branch_customer_table"


def validate(doc, method=None):
    assign_branch_customer_ids(doc)


def assign_branch_customer_ids(doc):
    rows = list(doc.get(BRANCH_CUSTOMER_TABLE_FIELD) or [])
    used_ids_by_branch = {}
    rows_to_assign = []

    for row in rows:
        branch = row.get("branch_customer")
        if not branch:
            row.branch_id = None
            continue

        used_ids = used_ids_by_branch.setdefault(branch, set())
        branch_id = row.get("branch_id")

        if branch_id and branch_id not in used_ids:
            used_ids.add(branch_id)
        else:
            row.branch_id = None
            rows_to_assign.append(row)

    next_id_by_branch = {branch: 1 for branch in used_ids_by_branch}

    for row in rows_to_assign:
        branch = row.get("branch_customer")
        used_ids = used_ids_by_branch.setdefault(branch, set())
        next_id = next_id_by_branch.get(branch, 1)

        while next_id in used_ids:
            next_id += 1

        row.branch_id = next_id
        used_ids.add(next_id)
        next_id_by_branch[branch] = next_id + 1
