# Commission Cycle Test Report

Date: 2026-05-23
Site used: `testsite.local`
Automated test:
`ion_crm_sales.ion_crm_sales.doctype.sales_target_and_commission_sheet.test_sales_target_and_commission_sheet`

## Full Scenario Testing Guide

This section is the desk guide for testing the full commission cycle without recording a video. It starts with the scenario list, then shows how to create the required master data, then walks through transaction creation from Opportunity to Commission Transactions, and finally explains how to read the results.

Main matrix sheet created on the system: `STCT-05-26-00045`

### A. Demonstrated Scenarios

The full matrix validates all active opportunity sources and the currently supported commission calculation paths.

| Scenario | Opportunity Type | Service Category | Purpose | Result Transaction |
|---|---|---|---|---|
| Sales Home | `Opportunity` | `Home` | Sales base commission, manager/rest split, above-target commission | `COMTR-05-26-00046` |
| Sales Hotspot | `Opportunity SM` | `Hotspot - Sales` | Hotspot sales rates and above-target commission | `COMTR-05-26-00047` |
| BA Dedicated NewLead | `Opportunity` | `Dedicated` | BA new lead rate and first-year addon | `COMTR-05-26-00048` |
| BA Dedicated Upsell | `Opportunity` | `Dedicated` | Existing customer history creates `Upsell` | `COMTR-05-26-00049` |
| BA Hotel NewLead | `Opportunity Hotels` | `Hotel` | Hotel opportunity and Hotel BA rate | `COMTR-05-26-00050` |
| BA ISP NewLead | `Opportunity ISP` | `ISPs` | ISP opportunity and ISP BA rate | `COMTR-05-26-00051` |
| BA Hotspot Bonus | `Opportunity SM` | `Hotspot - BA` | BA Hotspot plus acquisition bonus | `COMTR-05-26-00052` |
| BA Ultra Malls Bonus | `Opportunity Tenders` | `Ultra - Malls` | Tender opportunity plus acquisition bonus | `COMTR-05-26-00053` |
| BA ION Role Rates | `Opportunity` | `ION Solutions` | ION role rates from Sales Team rows | `COMTR-05-26-00054` |
| BA External Rep Approved | `Opportunity` | `Dedicated` | External Sales Person included after approval | `COMTR-05-26-00055` |
| BA Late Payment Penalty | `Opportunity` | `Dedicated` | Quarterly late payment penalty on AM commission | `COMTR-05-26-00056` |

Important limitation:

| Type | Current System Behavior |
|---|---|
| `Old` | The option exists, but the ledger sync currently cannot generate it because the sync always calls `detect_tx_type(..., is_renewal_flag=False)`. |
| `Renewal` | The option exists, but no current detection path returns `Renewal`. |

### B. Master Data Setup

Use these steps when recreating the matrix manually from the Desk.

#### B.1 Create Item Groups

1. Go to **Item Group**.
2. From the Item Group list, click **New**.
3. Fill the form:

| Field | Value |
|---|---|
| Item Group Name | `Home` |
| Parent Item Group | `All Item Groups` |
| Is Group | Unchecked |

4. Click **Save**.
5. Repeat the same steps for these Item Groups:

| Item Group Name |
|---|
| `Hotspot - Sales` |
| `Dedicated` |
| `Hotel` |
| `ISPs` |
| `ION Solutions` |
| `Hotspot - BA` |
| `Ultra - Malls` |

#### B.2 Create Monthly Distribution

1. Go to **Monthly Distribution**.
2. Click **New**.
3. Fill:

| Field | Value |
|---|---|
| Distribution ID | `Commission Cycle Even 0ckbfgtc` |
| Fiscal Year | `2026` |

4. In the **Percentages** table, add twelve rows:

| Month | Percentage Allocation |
|---:|---:|
| 1 | `8.333333` |
| 2 | `8.333333` |
| 3 | `8.333333` |
| 4 | `8.333333` |
| 5 | `8.333333` |
| 6 | `8.333333` |
| 7 | `8.333333` |
| 8 | `8.333333` |
| 9 | `8.333333` |
| 10 | `8.333333` |
| 11 | `8.333333` |
| 12 | `8.333333` |

5. Click **Save**.

This creates an even monthly distribution. Q2 is April, May, and June, so Q2 target is 25% of the annual target.

#### B.3 Create Employees and Users

For Sales reps:

1. Go to **Employee**.
2. Click **New**.
3. Fill:

| Field | Value |
|---|---|
| First Name | `Commission` |
| Last Name | `Rep Matrix` or another clear suffix |
| Gender | `Male` |
| Date of Birth | `1990-01-01` |
| Date of Joining | `2026-01-01` |
| Company | Same company used in the scenario |

4. Click **Save**.

For Business Accounts:

1. Go to **User**.
2. Click **New**.
3. Fill:

| Field | Value |
|---|---|
| Email | Any unique test email |
| First Name | `Commission` |
| Last Name | Any clear matrix suffix |
| User Type | `System User` |
| Role Profile | `AM` for Account Manager or `SM` for SM |
| Send Welcome Email | Unchecked |

4. Click **Save**.
5. Open the matching Employee.
6. Set **User ID** to this user.
7. Set **Department** to a department containing the word `Business`, for example `Business Accounts`.
8. Click **Save**.

#### B.4 Create Sales Persons

1. Go to **Sales Person**.
2. Click **New**.
3. Fill:

| Field | Value |
|---|---|
| Sales Person Name | Use one of the names below |
| Parent Sales Person | `Sales Team` |
| Is Group | Unchecked |
| Enabled | Checked |
| Employee | Set for normal employees; leave empty for external rep |
| Custom Is Sales Manager | `1` only for the Sales Manager |

4. In **Targets**, add one row:

| Field | Value |
|---|---|
| Item Group | `Home` |
| Fiscal Year | `2026` |
| Target Amount | Use the table below |
| Target Distribution | `Commission Cycle Even 0ckbfgtc` |

5. Click **Save**.

Created Sales Persons in the matrix:

| Role | Sales Person | Target Amount | Notes |
|---|---|---:|---|
| Sales Manager | `Commission Cycle unwmjuja` | 20,000 | `Custom Is Sales Manager = 1` |
| Sales Rep | `Commission Cycle evbs0zm8` | 40,000 | Linked to Employee |
| BA AM | `Commission Cycle da4ibstb` | 36,000 | Employee user has Role Profile `AM` |
| BA Executive | `Commission Cycle znslddnl` | 36,000 | Employee user has Role Profile `SM` |
| BA ION Offer Team | `Commission Cycle lvbxtqab` | 36,000 | Used for ION role scenario |
| BA External Rep | `Commission Cycle fwfyrinq` | 36,000 | No Employee link |

#### B.5 Create Items

1. Go to **Item**.
2. From the Item list, click **New**.
3. Fill:

| Field | Value |
|---|---|
| Item Code | Unique code, for example `COMM-MATRIX-HOME` |
| Item Name | Clear name, for example `Commission Matrix Home` |
| Item Group | One of the service category item groups |
| Material Type | Any valid Material Type |
| Stock UOM | Any valid UOM |
| Is Stock Item | Unchecked |
| Is Sales Item | Checked |

4. Click **Save**.
5. Repeat for all service categories: `Home`, `Hotspot - Sales`, `Dedicated`, `Hotel`, `ISPs`, `ION Solutions`, `Hotspot - BA`, `Ultra - Malls`.

### C. Create A Scenario Record From A to Z

This is the base flow. Use it for every scenario, then apply the scenario-specific values from section D.

#### C.1 Create Customer

1. Go to **Customer**.
2. Click **New**.
3. Fill:

| Field | Value |
|---|---|
| Customer Name | `Commission Cycle Customer` plus a unique suffix |
| Customer Type | `Company` |
| Customer Group | Any valid Customer Group |
| Territory | Any valid Territory |

4. Click **Save**.

#### C.2 Create Opportunity

1. Go to the required Opportunity doctype: **Opportunity**, **Opportunity SM**, **Opportunity Hotels**, **Opportunity ISP**, or **Opportunity Tenders**.
2. Click **New**.
3. Fill:

| Field | Value |
|---|---|
| Company | Matrix company |
| Opportunity From | `Customer` |
| Party Name | Customer from section C.1 |
| Opportunity Type | `Dedicated` |
| Sales Stage | `Opportunity` |
| Expected Closing | `2026-04-30` |
| Transaction Date | `2026-04-10` |
| Conversion Rate | `1.0` |
| Territory | Any valid Territory |
| Industry | Any valid Industry Type |
| Market Segment | Any valid Market Segment |
| City | `Test City` |
| Material Type | Any valid Material Type |
| Account Manager | `Administrator` |
| Surveyor Manager | `Administrator` |
| Request | Scenario label, for example `Commission matrix Opportunity Home` |

For **Opportunity Tenders**, also set:

| Field | Value |
|---|---|
| RFP Document | Any attached test file, for example `/files/commission-matrix-rfp.pdf` |

4. In **Items**, add:

| Field | Value |
|---|---|
| Item Code | Item for the scenario service category |
| Qty | `1` |
| Rate | Scenario amount |
| Amount | Scenario amount |
| Base Rate | Scenario amount |
| Base Amount | Scenario amount |
| UOM | Item UOM |
| Availability | `Available` |
| Valuation Rate | Scenario amount |
| Valuation Rate Company Currency | Scenario amount |

5. Click **Save**.

#### C.3 Create Quotation

1. Open the Opportunity.
2. Click the create action for **Quotation**.
3. On the Quotation, set:

| Field | Value |
|---|---|
| Transaction Date | `2026-04-15`, except late penalty scenario uses `2026-04-01` |
| Valid Till | Any future date |

4. Confirm the item and customer copied from the Opportunity.
5. Click **Save**.
6. Click **Submit**.

#### C.4 Create Sales Order

1. Open the submitted Quotation.
2. Click **Create > Sales Order**.
3. Set:

| Field | Value |
|---|---|
| Transaction Date | Same as Quotation transaction date |
| Delivery Date | `2026-04-30`, except late penalty scenario uses `2026-04-01` |
| Cost Center | Company cost center |

4. Add Sales Team rows based on section D.
5. In **Payment Schedule**, use:

| Field | Value |
|---|---|
| Due Date | Scenario due date |
| Invoice Portion | `100` |
| Payment Amount | Scenario amount |

6. Create and link an Active Contract using section C.5.
7. Click **Save**.
8. Click **Submit**.

#### C.5 Create Active Contract

1. Go to **Contract**.
2. Click **New**.
3. Fill:

| Field | Value |
|---|---|
| Party Type | `Customer` |
| Party Name | Customer from Sales Order |
| Start Date | `2026-04-01` |
| Status | `Active` |
| Document Type | `Sales Order` |
| Document Name | Sales Order name |
| Contract Terms | `Commission cycle test contract` |

4. Click **Save**.
5. Return to the Sales Order.
6. Set **Custom Contract** to the Contract.
7. Save and submit the Sales Order.

#### C.6 Create Sales Invoice

1. Open the submitted Sales Order.
2. Click **Create > Sales Invoice**.
3. Set:

| Field | Value |
|---|---|
| Posting Date | Scenario posting date |
| Due Date | Scenario due date |
| Service Category | Scenario service category |
| Debit To | Company receivable account |
| Cost Center | Company cost center |

4. In item rows, verify:

| Field | Value |
|---|---|
| Income Account | Company income account |
| Cost Center | Company cost center |

5. In Sales Team, verify rows match section D.
6. Apply invoice flags from section D, if any.
7. Click **Save**.
8. Click **Submit**.

#### C.7 Create Payment Entry

1. Open the submitted Sales Invoice.
2. Click **Create > Payment**.
3. Fill:

| Field | Value |
|---|---|
| Posting Date | Scenario payment date |
| Reference No | Any unique value |
| Reference Date | Scenario payment date |
| Paid To | Company cash account |
| Paid Amount | Full invoice amount |

4. Click **Save**.
5. Click **Submit**.
6. Reopen the Sales Invoice and confirm **Outstanding Amount = 0**.

#### C.8 Create Sales Target and Commission Sheet

1. Go to **Sales Target and Commission Sheet**.
2. Click **New**.
3. Fill:

| Field | Value |
|---|---|
| Company | Same company used on invoices |
| Fiscal Year | `2026` |
| Quarter | `Q2` |
| Remarks | `Persistent full commission matrix scenario for tracking.` |

4. Add Commission Lines:

| Sales Person | Department |
|---|---|
| `Commission Cycle unwmjuja` | `Sales` |
| `Commission Cycle evbs0zm8` | `Sales` |
| `Commission Cycle da4ibstb` | `Business Accounts` |
| `Commission Cycle znslddnl` | `Business Accounts` |
| `Commission Cycle lvbxtqab` | `Business Accounts` |
| `Commission Cycle fwfyrinq` | `Business Accounts` |

5. Click **Save**.
6. The sheet sync creates Commission Transactions automatically.

### D. Scenario-Specific Values

Use the base flow from section C and change these values per scenario.

| Scenario | Opportunity Type | Service Category | Amount | Sales Team | Invoice Flags / Dates |
|---|---|---|---:|---|---|
| Sales Home | `Opportunity` | `Home` | 20,000 | Sales Manager 30%, Sales Rep 70% | Posting `2026-04-15`, Due `2026-04-30`, Paid `2026-04-20` |
| Sales Hotspot | `Opportunity SM` | `Hotspot - Sales` | 15,000 | Sales Manager 30%, Sales Rep 70% | Posting `2026-04-15`, Due `2026-04-30`, Paid `2026-04-20` |
| BA Dedicated NewLead | `Opportunity` | `Dedicated` | 12,000 | BA AM 50%, BA Executive 50% | First Year Contract Invoice checked |
| BA Dedicated Upsell | `Opportunity` | `Dedicated` | 9,000 | BA AM 50%, BA Executive 50% | Create a prior paid invoice for the same customer first |
| BA Hotel NewLead | `Opportunity Hotels` | `Hotel` | 11,000 | BA AM 50%, BA Executive 50% | Standard Q2 payment |
| BA ISP NewLead | `Opportunity ISP` | `ISPs` | 13,000 | BA AM 50%, BA Executive 50% | Standard Q2 payment |
| BA Hotspot Bonus | `Opportunity SM` | `Hotspot - BA` | 10,000 | BA AM 50%, BA Executive 50% | BA Project Acquisition Bonus checked |
| BA Ultra Malls Bonus | `Opportunity Tenders` | `Ultra - Malls` | 10,000 | BA AM 50%, BA Executive 50% | BA Project Acquisition Bonus checked; RFP document required |
| BA ION Role Rates | `Opportunity` | `ION Solutions` | 16,000 | BA AM 50%, BA ION Offer 50% | ION roles set on Sales Team rows |
| BA Late Payment Penalty | `Opportunity` | `Dedicated` | 8,000 | BA AM 50%, BA Executive 50% | Payment Plan `Quarterly`, Posting/Due `2026-04-01`, Paid `2026-06-01` |
| BA External Rep Approved | `Opportunity` | `Dedicated` | 7,000 | BA AM 50%, BA External Rep 50% | External Rep Approved checked |

For ION role rows:

| Sales Person | ION Role |
|---|---|
| `Commission Cycle da4ibstb` | `Account Lead Acquisition` |
| `Commission Cycle lvbxtqab` | `Offer Team` |

### E. Results and Analysis

Open `STCT-05-26-00045` and verify:

| Field | Expected Value |
|---|---:|
| Transaction Sync Status | `Synced` |
| Source of Totals | `Commission Transactions` |
| Commission Transaction Count | 11 |
| Total Target | 51,000 |
| Total Actual Sales | 131,000 |
| Total Commission | 11,600.25 |

Generated transactions:

| Transaction | Department | Sales Invoice | Type | Eligible Amount | Total Commission | Fully Paid On |
|---|---|---|---|---:|---:|---|
| `COMTR-05-26-00046` | Sales | `ACC-SINV-2026-00037` | | 20,000 | 25 | `2026-04-20` |
| `COMTR-05-26-00047` | Sales | `ACC-SINV-2026-00038` | | 15,000 | 1,050 | `2026-04-20` |
| `COMTR-05-26-00048` | Business Accounts | `ACC-SINV-2026-00039` | `NewLead` | 12,000 | 360 | `2026-04-20` |
| `COMTR-05-26-00049` | Business Accounts | `ACC-SINV-2026-00041` | `Upsell` | 9,000 | 360 | `2026-04-20` |
| `COMTR-05-26-00050` | Business Accounts | `ACC-SINV-2026-00042` | `NewLead` | 11,000 | 880 | `2026-04-20` |
| `COMTR-05-26-00051` | Business Accounts | `ACC-SINV-2026-00043` | `NewLead` | 13,000 | 81.25 | `2026-04-20` |
| `COMTR-05-26-00052` | Business Accounts | `ACC-SINV-2026-00044` | `NewLead` | 10,000 | 3,800 | `2026-04-20` |
| `COMTR-05-26-00053` | Business Accounts | `ACC-SINV-2026-00045` | `NewLead` | 10,000 | 3,400 | `2026-04-20` |
| `COMTR-05-26-00054` | Business Accounts | `ACC-SINV-2026-00046` | `NewLead` | 16,000 | 720 | `2026-04-20` |
| `COMTR-05-26-00055` | Business Accounts | `ACC-SINV-2026-00048` | `NewLead` | 7,000 | 420 | `2026-04-20` |
| `COMTR-05-26-00056` | Business Accounts | `ACC-SINV-2026-00047` | `NewLead` | 8,000 | 504 | `2026-06-01` |

#### E.1 Sales Home Calculation

Sales Home invoice: `ACC-SINV-2026-00037`

| Person | Basis | Q2 Target | Base Commission | Above Target Commission | Total |
|---|---:|---:|---:|---:|---:|
| Sales Manager | 6,000 | 5,000 | 3 | 3 | 6 |
| Sales Rep | 14,000 | 10,000 | 7 | 12 | 19 |
| Total | 20,000 | 15,000 | 10 | 15 | 25 |

Explanation:

1. Manager receives 30% of `20,000`, which is `6,000`.
2. Sales Rep receives 70% of `20,000`, which is `14,000`.
3. Home base rate is `0.05%`.
4. Home above-target rate is `0.3%`.
5. Manager exceeds Q2 target by `1,000`.
6. Sales Rep exceeds Q2 target by `4,000`.

#### E.2 BA NewLead vs Upsell

`NewLead` is produced when the customer has no prior submitted invoice and no prior fully paid invoice before the current paid date.

`Upsell` is produced when the customer has prior invoice history. The matrix creates a seed invoice for the same customer before the Upsell invoice, so `ACC-SINV-2026-00041` becomes `Upsell`.

#### E.3 Bonus Scenarios

| Transaction | Reason |
|---|---|
| `COMTR-05-26-00052` | `Hotspot - BA` invoice has BA Project Acquisition Bonus checked. |
| `COMTR-05-26-00053` | `Ultra - Malls` invoice has BA Project Acquisition Bonus checked. |

The configured acquisition bonus is `3,000` and is split among eligible employees.

#### E.4 ION Solutions

`COMTR-05-26-00054` validates role-based ION rates. The role is read from the Sales Team row, not from the Sales Person master.

#### E.5 External Rep

`COMTR-05-26-00055` validates that an external Sales Person without Employee is included only when **External Rep Approved** is checked on the Sales Invoice.

#### E.6 Late Payment Penalty

`COMTR-05-26-00056` validates late payment behavior:

| Field | Value |
|---|---|
| Due Date | `2026-04-01` |
| Fully Paid On | `2026-06-01` |
| Payment Plan | `Quarterly` |

The payment is still inside Q2, so the invoice is included in the Q2 sheet, but payment is late enough to trigger the penalty logic.

### F. How to Verify From the Desk

1. Open **Sales Target and Commission Sheet** `STCT-05-26-00045`.
2. Confirm the totals in section E.
3. Go to **Commission Transaction**.
4. Filter by **Sales Target and Commission Sheet** = `STCT-05-26-00045`.
5. Open each transaction listed in section E.
6. Check **Lines**:
   - Sales scenarios should show `Base` and `Above Target` lines.
   - BA bonus scenarios should show bonus/addon lines where applicable.
   - Late payment scenario should show a `Penalty` component.
7. Open each Sales Invoice and confirm:
   - Docstatus is Submitted.
   - Outstanding Amount is `0`.
   - Service Category matches the scenario.
   - Sales Team rows match section D.

## Appendix: Original Report Details

## Scope

This report documents the full commission cycle test scenario from the first sales document through commission ledger creation:

1. Opportunity
2. Quotation
3. Sales Order
4. Sales Invoice
5. Payment Entry
6. Sales Target and Commission Sheet
7. Commission Transaction and Commission Transaction Lines

The automated test currently covers the Sales department, Home service category, fully paid invoice, base commission, above-target commission, target rollup, actual sales rollup, and transaction ledger creation.

## Executed Automated Scenario

### Scenario: Sales Home Commission Cycle

Purpose: verify that a paid invoice created from the normal selling flow produces commission transactions and rolls totals back to the commission sheet.

Flow:

1. Create the `Home` Item Group when missing.
2. Create an even Monthly Distribution for fiscal year `2026`.
3. Create a Sales Manager Sales Person with annual target `20,000`.
4. Create a Sales Rep Sales Person linked to an Employee with annual target `40,000`.
5. Create a Customer and non-stock sales Item in Item Group `Home`.
6. Create an Opportunity with the Home item.
7. Map Opportunity to Quotation using `ion_crm_sales.opportunity.make_quotation`.
8. Submit the Quotation.
9. Map Quotation to Sales Order using `ion_crm_sales.quotation.make_sales_order`.
10. Attach an Active Contract to satisfy Sales Invoice creation rules.
11. Add Sales Team:
    - Manager: 30%
    - Rep: 70%
12. Submit the Sales Order.
13. Map Sales Order to Sales Invoice using `ion_crm_sales.sales_order.make_sales_invoice`.
14. Set Sales Invoice service category to `Home`.
15. Submit the Sales Invoice.
16. Create and submit Payment Entry dated `2026-04-20`.
17. Create Sales Target and Commission Sheet for fiscal year `2026`, quarter `Q2`.
18. Verify Commission Transaction generation and sheet rollup.

Expected calculations:

| Person | Q2 Target | Basis | Base Rate | Base Commission | Above Basis | Above Rate | Above Commission | Total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Sales Manager | 5,000 | 6,000 | 0.05% | 3 | 1,000 | 0.3% | 3 | 6 |
| Sales Rep | 10,000 | 14,000 | 0.05% | 7 | 4,000 | 0.3% | 12 | 19 |
| Total | 15,000 | 20,000 | | 10 | 5,000 | | 15 | 25 |

Verified outcomes:

| Check | Expected |
|---|---|
| Sales Invoice outstanding amount | `0` |
| Sales Invoice linked to Sales Order | Yes |
| Commission Transaction count | `1` |
| Transaction department | `Sales` |
| Transaction status | `Draft` |
| Transaction kind | `Original` |
| Fully paid date | `2026-04-20` |
| Eligible amount | `20,000` |
| Total commission | `25` |
| Sheet total target | `15,000` |
| Sheet total actual sales | `20,000` |
| Sheet total commission | `25` |
| Sheet sync status | `Synced` |
| Sheet source of totals | `Commission Transactions` |

Validation command:

```bash
bench --site testsite.local run-tests --module ion_crm_sales.ion_crm_sales.doctype.sales_target_and_commission_sheet.test_sales_target_and_commission_sheet --skip-test-records
```

Result:

```text
Ran 1 test in 2.006s
OK
```

## Persistent Tracking Scenario

The same A-to-Z flow was also created outside the test runner and committed on `testsite.local` so the records can be inspected from the desk.

| Document | Name |
|---|---|
| Company | `ion t` |
| Monthly Distribution | `Commission Cycle Even emvqfrk7` |
| Manager Sales Person | `Commission Cycle ecpaqrcj` |
| Rep Sales Person | `Commission Cycle oeoz10oq` |
| Opportunity | `CRM-OPP-2026-00023` |
| Quotation | `SAL-QTN-2026-00027` |
| Sales Order | `SAL-ORD-2026-00027` |
| Contract | `Commission Cycle Customer edksmihj` |
| Sales Invoice | `ACC-SINV-2026-00024` |
| Payment Entry | `ACC-PAY-2026-00044` |
| Sales Target and Commission Sheet | `STCT-05-26-00032` |
| Commission Transaction | `COMTR-05-26-00033` |

Persistent scenario totals:

| Metric | Value |
|---|---:|
| Sheet total target | 15,000 |
| Sheet total actual sales | 20,000 |
| Sheet total commission | 25 |

## Persistent Full Matrix Scenario

A broader matrix was created and committed on `testsite.local` to cover all active opportunity sources and the supported Sales and Business Accounts commission paths.

Matrix sheet: `STCT-05-26-00045`

Sales people:

| Role | Sales Person |
|---|---|
| Sales Manager | `Commission Cycle unwmjuja` |
| Sales Rep | `Commission Cycle evbs0zm8` |
| BA AM | `Commission Cycle da4ibstb` |
| BA Executive | `Commission Cycle znslddnl` |
| BA ION Offer Team | `Commission Cycle lvbxtqab` |
| BA External Rep | `Commission Cycle fwfyrinq` |

Scenario documents:

| Scenario | Opportunity Type | Service Category | Opportunity | Quotation | Sales Order | Sales Invoice | Payment Entry |
|---|---|---|---|---|---|---|---|
| Sales Home via Dedicated Opportunity | `Opportunity` | `Home` | `CRM-OPP-2026-00036` | `SAL-QTN-2026-00040` | `SAL-ORD-2026-00040` | `ACC-SINV-2026-00037` | `ACC-PAY-2026-00057` |
| Sales Hotspot via S&M Opportunity | `Opportunity SM` | `Hotspot - Sales` | `CRM-OPP-2026-00037` | `SAL-QTN-2026-00041` | `SAL-ORD-2026-00041` | `ACC-SINV-2026-00038` | `ACC-PAY-2026-00058` |
| BA Dedicated NewLead via Dedicated Opportunity | `Opportunity` | `Dedicated` | `CRM-OPP-2026-00038` | `SAL-QTN-2026-00042` | `SAL-ORD-2026-00042` | `ACC-SINV-2026-00039` | `ACC-PAY-2026-00059` |
| BA Dedicated Upsell via Dedicated Opportunity | `Opportunity` | `Dedicated` | `CRM-OPP-2026-00040` | `SAL-QTN-2026-00044` | `SAL-ORD-2026-00044` | `ACC-SINV-2026-00041` | `ACC-PAY-2026-00061` |
| BA Hotel NewLead via Hotels Opportunity | `Opportunity Hotels` | `Hotel` | `CRM-OPP-2026-00041` | `SAL-QTN-2026-00045` | `SAL-ORD-2026-00045` | `ACC-SINV-2026-00042` | `ACC-PAY-2026-00062` |
| BA ISP NewLead via ISP Opportunity | `Opportunity ISP` | `ISPs` | `CRM-OPP-2026-00042` | `SAL-QTN-2026-00046` | `SAL-ORD-2026-00046` | `ACC-SINV-2026-00043` | `ACC-PAY-2026-00063` |
| BA Hotspot NewLead Bonus via S&M Opportunity | `Opportunity SM` | `Hotspot - BA` | `CRM-OPP-2026-00043` | `SAL-QTN-2026-00047` | `SAL-ORD-2026-00047` | `ACC-SINV-2026-00044` | `ACC-PAY-2026-00064` |
| BA Ultra Malls NewLead Bonus via Tenders Opportunity | `Opportunity Tenders` | `Ultra - Malls` | `CRM-OPP-2026-00044` | `SAL-QTN-2026-00048` | `SAL-ORD-2026-00048` | `ACC-SINV-2026-00045` | `ACC-PAY-2026-00065` |
| BA ION Solutions Role Rates via Dedicated Opportunity | `Opportunity` | `ION Solutions` | `CRM-OPP-2026-00045` | `SAL-QTN-2026-00049` | `SAL-ORD-2026-00049` | `ACC-SINV-2026-00046` | `ACC-PAY-2026-00066` |
| BA Dedicated Late Payment Penalty | `Opportunity` | `Dedicated` | `CRM-OPP-2026-00046` | `SAL-QTN-2026-00050` | `SAL-ORD-2026-00050` | `ACC-SINV-2026-00047` | `ACC-PAY-2026-00067` |
| BA Dedicated External Rep Approved | `Opportunity` | `Dedicated` | `CRM-OPP-2026-00047` | `SAL-QTN-2026-00051` | `SAL-ORD-2026-00051` | `ACC-SINV-2026-00048` | `ACC-PAY-2026-00068` |

Generated commission transactions:

| Transaction | Department | Sales Invoice | Type | Eligible Amount | Commission | Fully Paid On |
|---|---|---|---|---:|---:|---|
| `COMTR-05-26-00046` | Sales | `ACC-SINV-2026-00037` | | 20,000 | 25 | `2026-04-20` |
| `COMTR-05-26-00047` | Sales | `ACC-SINV-2026-00038` | | 15,000 | 1,050 | `2026-04-20` |
| `COMTR-05-26-00048` | Business Accounts | `ACC-SINV-2026-00039` | `NewLead` | 12,000 | 360 | `2026-04-20` |
| `COMTR-05-26-00049` | Business Accounts | `ACC-SINV-2026-00041` | `Upsell` | 9,000 | 360 | `2026-04-20` |
| `COMTR-05-26-00050` | Business Accounts | `ACC-SINV-2026-00042` | `NewLead` | 11,000 | 880 | `2026-04-20` |
| `COMTR-05-26-00051` | Business Accounts | `ACC-SINV-2026-00043` | `NewLead` | 13,000 | 81.25 | `2026-04-20` |
| `COMTR-05-26-00052` | Business Accounts | `ACC-SINV-2026-00044` | `NewLead` | 10,000 | 3,800 | `2026-04-20` |
| `COMTR-05-26-00053` | Business Accounts | `ACC-SINV-2026-00045` | `NewLead` | 10,000 | 3,400 | `2026-04-20` |
| `COMTR-05-26-00054` | Business Accounts | `ACC-SINV-2026-00046` | `NewLead` | 16,000 | 720 | `2026-04-20` |
| `COMTR-05-26-00055` | Business Accounts | `ACC-SINV-2026-00048` | `NewLead` | 7,000 | 420 | `2026-04-20` |
| `COMTR-05-26-00056` | Business Accounts | `ACC-SINV-2026-00047` | `NewLead` | 8,000 | 504 | `2026-06-01` |

Matrix totals:

| Metric | Value |
|---|---:|
| Sheet total target | 51,000 |
| Sheet total actual sales | 131,000 |
| Sheet total commission | 11,600.25 |

Important limitation found:

| Transaction Type | Current Status |
|---|---|
| `Old` | Cannot currently be produced by ledger sync because it always calls `detect_tx_type(..., is_renewal_flag=False)`. |
| `Renewal` | Present in DocType options, but no current detection path returns `Renewal`. |

## Commission Case Matrix

### Sales Department

| Case | Service Category | Expected Components | Notes |
|---|---|---|---|
| Sales Home below target | `Home` | Base | Verify no Above Target line when cumulative basis stays below Q target. |
| Sales Home crosses target | `Home` | Base, Above Target | Covered by the automated A-to-Z test. |
| Sales Home already above target | `Home` | Base, Above Target | Invoice ordered after earlier paid invoice should calculate above on full exposed amount above target. |
| Sales Hotspot below target | `Hotspot - Sales` | Base | Uses Hotspot sales normal rate and manager/rest split. |
| Sales Hotspot crosses target | `Hotspot - Sales` | Base, Above Target | Uses Hotspot sales above-target rate. |
| Manager present | `Home` or `Hotspot - Sales` | Base, optional Above Target | Manager share goes to manager; rest share goes to non-manager employees. |
| No manager present | `Home` or `Hotspot - Sales` | Base, optional Above Target | Manager share reallocates to rest. |
| Rep has no Employee link | `Home` or `Hotspot - Sales` | No rep line for rest role | `_rest_on_si` requires Employee for non-manager reps. |

### Business Accounts Department

| Case | Service Category | Transaction Type | Expected Components | Notes |
|---|---|---|---|---|
| Dedicated old account | `Dedicated` | `Old` | Base, optional Above Target | Uses BA old-account rate. |
| Dedicated new lead | `Dedicated` | `NewLead` | Base, optional Above Target | Uses BA new-lead rate. |
| Dedicated upsell | `Dedicated` | `Upsell` | Base, optional Above Target | Uses BA upsell rate. |
| Hotel old account | `Hotel` | `Old` | Base, optional Above Target | Uses Hotel old-account rate. |
| Hotel new lead | `Hotel` | `NewLead` | Base, optional Above Target | Uses Hotel new-lead rate. |
| Hotel upsell | `Hotel` | `Upsell` | Base, optional Above Target | Uses Hotel upsell rate. |
| ISP old account | `ISPs` | `Old` | Base, optional Above Target | Uses ISP old-account rate. |
| ISP new lead | `ISPs` | `NewLead` | Base, optional Above Target | Uses ISP new-lead rate. |
| ISP upsell | `ISPs` | `Upsell` | Base, optional Above Target | Uses ISP upsell rate. |
| ION Solutions account lead | `ION Solutions` | Any BA type | Base, optional Above Target | Role rate: Account Lead Acquisition. |
| ION Solutions offer team | `ION Solutions` | Any BA type | Base, optional Above Target | Role rate: Offer Team. |
| ION Solutions execution team | `ION Solutions` | Any BA type | Base, optional Above Target | Role rate: Execution Team. |
| BA Hotspot new lead | `Hotspot - BA` | `NewLead` | Base, optional Above Target, optional Acquisition Bonus | Bonus applies when project acquisition flag is set. |
| Ultra Malls new lead | `Ultra - Malls` | `NewLead` | Base, optional Above Target, optional Acquisition Bonus | Bonus applies when project acquisition flag is set. |
| First-year contract invoice | Any BA category | `NewLead` | First Year Addon | Applies when first-year contract flag is set. |
| Late payment penalty | BA categories | Any BA type | Penalty | Applies when fully paid date exceeds category/payment-plan grace. |
| External rep not approved | BA categories with external recipients | Any BA type | Excludes external rep | External recipients require approval flag. |
| BA skip flag | BA categories | Any BA type | No transaction | Skipped when the BA skip predicate is true. |

### Transaction Lifecycle

| Case | Expected Result |
|---|---|
| New qualifying paid invoice appears in quarter | Create Draft Original Commission Transaction. |
| Existing qualifying invoice recalculates | Update existing transaction using `source_key`; preserve one active transaction per invoice/department/sheet. |
| Invoice no longer qualifies | Mark previous active transaction as `Superseded`. |
| Sheet totals after sync | Aggregate active Draft/Posted transaction lines into commission lines. |
| Sheet submit with no commission lines | Block submission. |
| Sheet submit with zero target line | Block submission with missing quarter target message. |
| Approved sheet moved to Posted | Post accrual Journal Entry when configured and not already posted. |
| Posted/Reversed transaction | Excluded from active aggregation unless status is Draft or Posted. |

## Implementation Note

During test execution, the sheet insert lifecycle exposed a real issue: `validate` attempted to create linked Commission Transactions before the new Sales Target and Commission Sheet row existed. The controller now skips transaction sync during `validate` for new documents and runs sync in `after_insert`, then persists the calculated parent and child totals.

## Current Automated Coverage

Covered:

- Opportunity to Quotation mapping
- Quotation submission
- Quotation to Sales Order mapping
- Active Contract requirement before Sales Invoice
- Sales Order to Sales Invoice mapping
- Payment Entry full settlement
- Fully paid invoice detection inside Q2
- Sales Home commission calculation
- Manager/rest split
- Above-target calculation
- Commission Transaction creation
- Commission Transaction Line creation
- Sheet target, actual, commission, count, status, and source rollup

Not yet automated:

- Sales Hotspot category
- BA service categories
- BA transaction types: `NewLead`, `Upsell`, `Old`, `Renewal`
- BA ION role rates
- BA first-year addon
- BA acquisition bonus
- BA late-payment penalty
- Superseded transaction path
- Accrual posting on Approved to Posted workflow transition
