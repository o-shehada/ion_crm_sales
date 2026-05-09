import json

file_path = "ion_crm_sales/fixtures/custom_field.json"

with open(file_path, "r") as f:
    data = json.load(f)

# Filters out any block where dt is "Opportunity Item"
new_data = [block for block in data if block.get("dt") != "Opportunity Tenders"]

with open(file_path, "w") as f:
    json.dump(new_data, f, indent=4)

print(f"Done! Remaining blocks: {len(new_data)}")
