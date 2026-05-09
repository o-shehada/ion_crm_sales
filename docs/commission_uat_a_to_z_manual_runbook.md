# Commission UAT A-to-Z Manual Runbook

This runbook is for manually testing the full CRM-to-commission flow on a fresh site with new master data.

Use the names exactly as written so the test evidence is easy to compare.

## 1. Scope

This UAT covers:

- Opportunity workflow `Quote` action auto-creating a Quotation.
- Sales flow from Opportunity to Quotation, Sales Invoice, Payment Entry.
- Sales Target and Commission Sheet calculation.
- Sales commission scenarios.
- Business Accounts commission scenarios.
- Actual Sales, Achievement %, Commission Value, and effective Commission Rate.
- Workflow `Post` action posting the commission accrual Journal Entry.

## 2. Required Setup

Use:

- Company: `ION`
- Fiscal Year: `2026`
- Quarter: `Q1`
- Currency: `LYD`
- Price List: `Standard Selling`

Make sure these accounts exist for `ION`:

- Income Account: `4110 - Sales - I`
- Receivable Account: `1310 - Debtors - I`
- Cash Account: `1110 - Cash - I`
- Cost Center: `Main - I`

In `Commission Policy Settings`, set:

- Expense Account: a valid expense ledger, for example `55002 - عمولة المبيعات - Sales Commission - I`
- Payable Account: a valid liability ledger, for example `2700 - حسابات دائنة أخرى - Other Payables - I`

## 3. Master Data

### 3.1 Monthly Distribution

Create Monthly Distribution:

- Name: `UAT-COMM-2026-EVEN`
- Fiscal Year: `2026`

Add 12 rows:

| Month | Percentage Allocation |
|---|---:|
| January | 8.333333 |
| February | 8.333333 |
| March | 8.333333 |
| April | 8.333333 |
| May | 8.333333 |
| June | 8.333333 |
| July | 8.333333 |
| August | 8.333333 |
| September | 8.333333 |
| October | 8.333333 |
| November | 8.333333 |
| December | 8.333333 |

Expected Q1 target share is 25% of annual target.

### 3.2 Employees, Users, Sales Persons

Create each Employee, User, and Sales Person. Link each Sales Person to its Employee.

Use annual target `40,000` for every Sales Person. With the even distribution above, Q1 target should be `10,000`.

| Sales Person | Employee/User Role | Department | Sales Person Commission Rate | Is Sales Manager |
|---|---|---|---:|---:|
| Omar Al-Mahdi | Sales | Sales Department | 0.50 | Yes |
| Nadia El-Sherif | Sales | Sales Department | 0.70 | No |
| Karim Ben Younes | Sales | Sales Department | 1.00 | No |
| Mariam Al-Fitouri | AM | Business Accounts | 1.00 | No |
| Salem Al-Obeidi | SM | Business Accounts | 1.00 | No |
| Huda Al-Werfalli | Sales | Business Accounts | 2.00 | No |
| Tarek Al-Zintani | Sales | Business Accounts | 5.00 | No |
| Ayman Al-Kikli | Sales | Business Accounts | 5.00 | No |
| Leila Mansour | Sales | Business Accounts | 2.00 | No |

Important:

- `Sales Person.commission_rate` is only ERPNext’s default row rate for Sales Team. It is not the source of truth for the custom commission sheet.
- `Commission Lines.commission_rate` should show effective rate:

```text
commission_rate = commission_value / actual_sales * 100
```

### 3.3 Item Groups and Items

Create these Item Groups if missing:

- `Home`
- `Hotspot - Sales`
- `Dedicated`
- `Hotel`
- `ISPs`
- `ION Solutions`
- `Hotspot - BA`
- `Ultra - Malls`

Create one non-stock service item for each group:

| Item Code | Item Group |
|---|---|
| UAT Home Service | Home |
| UAT Hotspot Sales Service | Hotspot - Sales |
| UAT Dedicated Service | Dedicated |
| UAT Hotel Service | Hotel |
| UAT ISPs Service | ISPs |
| UAT ION Solutions Service | ION Solutions |
| UAT Hotspot BA Service | Hotspot - BA |
| UAT Ultra Malls Service | Ultra - Malls |

For each item:

- Stock UOM: `Nos`
- Is Stock Item: unchecked
- Income Account: `4110 - Sales - I`
- Selling Cost Center: `Main - I`

## 4. Opportunity to Quotation Workflow Test

Create a new `Opportunity`:

- Customer: create `UAT Orbit Telecom Company`
- Opportunity From: `Customer`
- Party: `UAT Orbit Telecom Company`
- Company: `ION`
- Expected Closing: `2026-01-31`
- Industry: `Telecommunications`
- Market Segment: `Middle Income`
- Territory: `Libya`
- City: `Benghazi`
- Material Type: `Sold items`
- Surveyor Manager: `Administrator`
- Request: `UAT quote workflow test`
- Service Active?: checked

Add one item:

- Item: `UAT Dedicated Service`
- Qty: `1`
- Rate: `10,000`

Move the workflow to the state before `Quote`, usually `Approved`.

Click workflow action:

- `Quote`

Expected:

- Opportunity moves to `Accepted`.
- A draft Quotation is created automatically.
- Opportunity status becomes `Quotation`.
- The Quotation is linked back to the Opportunity.
- Audit log has `Quotation Created: <quotation name>`.

## 5. Sales Invoice and Payment Rules

For every scenario:

1. Create or reuse Customer.
2. Create Opportunity with at least one item.
3. Use workflow `Quote`, or create Quotation manually from the Opportunity.
4. Create Sales Invoice from the Quotation or manually with the same customer/item.
5. Set `Sales Invoice.custom_service_category` to the matching service category.
6. Add Sales Team rows.
7. Submit Sales Invoice.
8. Create Payment Entry against the Sales Invoice.
9. Submit Payment Entry.

Commission includes only Sales Invoices that are:

- submitted,
- fully paid,
- paid inside the commission sheet quarter,
- using service categories configured in the commission engine.

## 6. Sales Department Scenarios

### Scenario S1: Home Below Target

Sales Invoice:

- Customer: `UAT Home Below Target Customer`
- Posting Date: `2026-01-10`
- Due Date: `2026-01-20`
- Payment Date: `2026-01-20`
- Service Category: `Home`
- Item: `UAT Home Service`
- Amount: `6,000`

Sales Team:

| Sales Person | Allocation % |
|---|---:|
| Omar Al-Mahdi | 50 |
| Nadia El-Sherif | 50 |

Expected:

- Home normal rate applies.
- Manager/rest split applies.
- No above-target add-on if still below target.

### Scenario S2: Home Above Target

Sales Invoice:

- Customer: `UAT Home Above Target Customer`
- Posting Date: `2026-01-15`
- Due Date: `2026-01-25`
- Payment Date: `2026-01-25`
- Service Category: `Home`
- Item: `UAT Home Service`
- Amount: `40,000`

Sales Team:

| Sales Person | Allocation % |
|---|---:|
| Omar Al-Mahdi | 50 |
| Nadia El-Sherif | 50 |

Expected:

- Normal commission applies on the full amount.
- Above-target add-on applies only to the over-target slice.

### Scenario S3: Hotspot Sales Below Target

Sales Invoice:

- Customer: `UAT Hotspot Sales Below Target Customer`
- Posting Date: `2026-01-18`
- Due Date: `2026-01-28`
- Payment Date: `2026-01-28`
- Service Category: `Hotspot - Sales`
- Item: `UAT Hotspot Sales Service`
- Amount: `7,000`

Sales Team:

| Sales Person | Allocation % |
|---|---:|
| Omar Al-Mahdi | 50 |
| Karim Ben Younes | 50 |

Expected:

- Hotspot Sales normal commission applies.
- Manager/rest split applies.

### Scenario S4: Hotspot Sales Above Target

Sales Invoice:

- Customer: `UAT Hotspot Sales Above Target Customer`
- Posting Date: `2026-02-01`
- Due Date: `2026-02-15`
- Payment Date: `2026-02-15`
- Service Category: `Hotspot - Sales`
- Item: `UAT Hotspot Sales Service`
- Amount: `35,000`

Sales Team:

| Sales Person | Allocation % |
|---|---:|
| Omar Al-Mahdi | 50 |
| Karim Ben Younes | 50 |

Expected:

- Normal commission applies.
- Above-target add-on applies to the over-target slice.

### Scenario S5: No Sales Manager

Sales Invoice:

- Customer: `UAT Sales No Manager Customer`
- Posting Date: `2026-02-05`
- Due Date: `2026-02-15`
- Payment Date: `2026-02-15`
- Service Category: `Home`
- Item: `UAT Home Service`
- Amount: `8,000`

Sales Team:

| Sales Person | Allocation % |
|---|---:|
| Nadia El-Sherif | 50 |
| Karim Ben Younes | 50 |

Expected:

- Manager share reallocates to eligible non-manager Sales Persons.

### Scenario S6: Unpaid Invoice

Sales Invoice:

- Customer: `UAT Unpaid Excluded Customer`
- Posting Date: `2026-02-10`
- Due Date: `2026-02-20`
- Service Category: `Home`
- Item: `UAT Home Service`
- Amount: `9,000`

Do not create Payment Entry.

Expected:

- Invoice is excluded from commission.

### Scenario S7: Paid in Next Quarter

Sales Invoice:

- Customer: `UAT Paid In Q2 Customer`
- Posting Date: `2026-03-15`
- Due Date: `2026-03-20`
- Payment Date: `2026-04-05`
- Service Category: `Home`
- Item: `UAT Home Service`
- Amount: `9,000`

Expected:

- Invoice is excluded from Q1 commission.
- Invoice should be included in Q2 commission.

## 7. Business Accounts Scenarios

### Scenario B1: Dedicated Old Renewal

First create customer history:

- Customer: `UAT Dedicated Existing Customer`
- Create a submitted and paid Dedicated Sales Invoice in 2025 for `1,000`.

Then create Q1 invoice:

- Posting Date: `2026-01-20`
- Due Date: `2026-01-30`
- Payment Date: `2026-01-30`
- Service Category: `Dedicated`
- Item: `UAT Dedicated Service`
- Amount: `12,000`

Sales Team:

| Sales Person | Allocation % |
|---|---:|
| Mariam Al-Fitouri | 50 |
| Huda Al-Werfalli | 50 |

Expected:

- Customer has previous invoice history.
- Old/Renewal rate applies.

### Scenario B2: Dedicated New Lead

Sales Invoice:

- Customer: `UAT Dedicated New Lead Customer`
- Posting Date: `2026-01-22`
- Due Date: `2026-02-01`
- Payment Date: `2026-02-01`
- Service Category: `Dedicated`
- Amount: `10,000`

Sales Team:

| Sales Person | Allocation % |
|---|---:|
| Mariam Al-Fitouri | 50 |
| Huda Al-Werfalli | 50 |

Expected:

- New Lead rate applies.

### Scenario B3: Dedicated Upsell

Use a customer with previous paid invoice history, then create:

- Service Category: `Dedicated`
- Amount: `15,000`
- Payment inside Q1

Expected:

- Upsell rate applies.

### Scenario B4: Hotel New Lead

- Customer: `UAT Hotel Customer`
- Service Category: `Hotel`
- Amount: `11,000`
- Payment inside Q1

Sales Team:

| Sales Person | Allocation % |
|---|---:|
| Mariam Al-Fitouri | 50 |
| Huda Al-Werfalli | 50 |

Expected:

- Hotel New Lead rate applies.

### Scenario B5: ISPs New Lead

- Customer: `UAT ISP Customer`
- Service Category: `ISPs`
- Amount: `20,000`
- Payment inside Q1

Expected:

- ISP New Lead rate applies.

### Scenario B6: Hotspot BA Acquisition Bonus

- Customer: `UAT Hotspot BA Customer`
- Service Category: `Hotspot - BA`
- Amount: `12,000`
- Payment inside Q1
- Check: `BA Project Acquisition Bonus`

Sales Team:

| Sales Person | Allocation % |
|---|---:|
| Mariam Al-Fitouri | 33 |
| Salem Al-Obeidi | 33 |
| Huda Al-Werfalli | 34 |

Expected:

- Hotspot BA commission applies.
- `3,000` acquisition bonus is split among linked employee Sales Persons.

### Scenario B7: Ultra Malls Acquisition Bonus

- Customer: `UAT Ultra Malls Customer`
- Service Category: `Ultra - Malls`
- Amount: `13,000`
- Payment inside Q1
- Check: `BA Project Acquisition Bonus`

Sales Team:

| Sales Person | Allocation % |
|---|---:|
| Mariam Al-Fitouri | 33 |
| Salem Al-Obeidi | 33 |
| Huda Al-Werfalli | 34 |

Expected:

- Ultra Malls commission applies.
- `3,000` acquisition bonus is split among linked employee Sales Persons.

### Scenario B8: ION Solutions Roles

- Customer: `UAT ION Solutions Customer`
- Service Category: `ION Solutions`
- Amount: `18,000`
- Payment inside Q1

Sales Team:

| Sales Person | Allocation % | ION Role |
|---|---:|---|
| Huda Al-Werfalli | 33 | Account Lead Acquisition |
| Tarek Al-Zintani | 33 | Offer Team |
| Ayman Al-Kikli | 34 | Execution Team |

Expected:

- Account Lead Acquisition role rate applies to Huda.
- Offer Team role rate applies to Tarek.
- Execution Team role rate applies to Ayman.

### Scenario B9: First-Year Contract Add-On

- Customer: `UAT First Year Contract Customer`
- Service Category: `Dedicated`
- Amount: `16,000`
- Payment inside Q1
- Check: `First Year Contract Invoice`

Sales Team:

| Sales Person | Allocation % |
|---|---:|
| Mariam Al-Fitouri | 33 |
| Salem Al-Obeidi | 33 |
| Huda Al-Werfalli | 34 |

Expected:

- First-year add-on applies only for New Lead.
- Add-on is split among non-AM/non-SM linked employees.

### Scenario B10: AM Late Payment Penalty

- Customer: `UAT AM Late Penalty Customer`
- Service Category: `Dedicated`
- Amount: `10,000`
- Posting Date: `2026-01-01`
- Due Date: `2026-01-10`
- Payment Date: `2026-04-20`
- Payment Plan: `Yearly`

Sales Team:

| Sales Person | Allocation % |
|---|---:|
| Mariam Al-Fitouri | 50 |
| Huda Al-Werfalli | 50 |

Expected:

- Late payment penalty applies to AM commission only.
- Penalty anchor date is `Sales Invoice.due_date`; if missing, the engine uses `posting_date`.
- For `Yearly`, grace period is 90 days, then a 50% reduction applies once, then another 10% reduction for every 30-day block after grace.
- In this case, from `2026-01-10` to `2026-04-20` is 100 days late. Grace is 90 days, so over-grace is 10 days.
- Expected penalty factor is `1.0 - 0.50 - (0.10 * 0) = 0.50`.
- Only Mariam Al-Fitouri is AM in this scenario, so her AM commission from this invoice should be reduced by 50%.
- Huda Al-Werfalli is not AM, so her commission should not be reduced by the late payment penalty.

Additional penalty plan checks:

| Payment Plan | Grace Period | Cadence After Grace | Test Example | Expected |
|---|---:|---:|---|---|
| Yearly | 90 days | 30 days | Due `2026-01-10`, paid `2026-04-20` | 50% AM reduction |
| 6 Months | 42 days | 14 days | Due `2026-01-10`, paid `2026-02-25` | 50% AM reduction |
| Quarterly | 21 days | 7 days | Due `2026-01-10`, paid `2026-02-07` | 60% AM reduction |

Penalty formula:

```text
if fully_paid_on - due_date <= grace_days:
    factor = 1.0
else:
    over = late_days - grace_days
    blocks = over // cadence_days
    factor = max(0.0, 1.0 - 0.50 - 0.10 * blocks)
```

### Scenario B11: Penalty Exception

Use same setup as B10, but check:

- `Penalty Exception Approved`

Expected:

- No late penalty.
- AM commission should remain at the normal calculated value even when the invoice is paid after the grace period.

### Scenario B12: Partnership at Cost

Customer:

- `UAT Partnership At Cost Customer`
- Check customer field: `Partnership At Cost`

Invoice:

- Service Category: `Dedicated`
- Amount: `10,000`
- Payment inside Q1

Expected:

- BA commission skipped.

### Scenario B13: ISP BW Partnership

Customer:

- `UAT ISP BW Partnership Customer`
- Check customer field: `ISP BW Partnership`

Invoice:

- Service Category: `ISPs`
- Amount: `10,000`
- Payment inside Q1

Expected:

- BA commission skipped.

### Scenario B14: External Rep Not Approved

- Customer: `UAT External Rep Not Approved Customer`
- Service Category: `Dedicated`
- Amount: `10,000`
- Payment inside Q1
- Do not check `External Rep Approved`

Sales Team:

| Sales Person | Allocation % |
|---|---:|
| Mariam Al-Fitouri | 50 |
| Leila Mansour | 50 |

Expected:

- External rep is excluded if not eligible/approved.

### Scenario B15: External Rep Approved

Same as B14, but check:

- `External Rep Approved`

Expected:

- External rep is included where allowed by the engine.

## 8. Create Commission Sheet

Create `Sales Target and Commission Sheet`:

- Company: `ION`
- Fiscal Year: `2026`
- Quarter: `Q1`
- Status: `Draft`

Add Commission Lines:

| Sales Person | Department |
|---|---|
| Omar Al-Mahdi | Sales |
| Nadia El-Sherif | Sales |
| Karim Ben Younes | Sales |
| Mariam Al-Fitouri | Business Accounts |
| Salem Al-Obeidi | Business Accounts |
| Huda Al-Werfalli | Business Accounts |
| Tarek Al-Zintani | Business Accounts |
| Ayman Al-Kikli | Business Accounts |
| Leila Mansour | Business Accounts |

Save the sheet.

Expected:

- `Target Value` is populated from Sales Person targets.
- `Actual Sales` is populated for Sales and Business Accounts.
- `Achievement Pct` is populated.
- `Commission Value` is populated.
- `Commission Rate` is populated as effective rate.

Click:

- `Recalculate Commission`

Expected:

- Values refresh without posting accrual.

## 9. Submit, Approve, Post

Use workflow:

1. From `Draft`, click `Submit`.
2. From `Submitted`, click `Approve`.
3. From `Approved`, click `Post`.

Expected on `Post`:

- Sheet status becomes `Posted`.
- Accrual Journal Entry is created and submitted.
- `Accrual JE` is filled.
- `Accrual Posted Amount` equals `Total Commission`.

The custom button `Post Accrual _` should still work from `Approved`, but the workflow `Post` button must create the same result.

## 10. Report Checks

After posting, check these reports:

- `Target vs Actual`
- `Commission to Revenue Ratio`
- `Accrued Commission Payable`

Expected:

- Posted sheet appears in reports.
- Total commission matches the sheet.
- Actual Sales includes Sales and BA actuals.

## 11. UAT Evidence Table

Fill this table during testing:

| Scenario | Opportunity | Quotation | Sales Invoice | Payment Entry | Expected | Actual | Pass/Fail | Notes |
|---|---|---|---|---|---|---|---|---|
| Quote workflow | | | | | Quotation auto-created | | | |
| S1 Home Below Target | | | | | Commission calculated | | | |
| S2 Home Above Target | | | | | Above-target add-on | | | |
| S3 Hotspot Sales Below Target | | | | | Commission calculated | | | |
| S4 Hotspot Sales Above Target | | | | | Above-target add-on | | | |
| S5 No Manager | | | | | Manager share reallocated | | | |
| S6 Unpaid | | | | | Excluded | | | |
| S7 Paid in Q2 | | | | | Excluded from Q1 | | | |
| B1 Dedicated Old | | | | | Old rate | | | |
| B2 Dedicated New | | | | | New Lead rate | | | |
| B3 Dedicated Upsell | | | | | Upsell rate | | | |
| B4 Hotel | | | | | Hotel rate | | | |
| B5 ISPs | | | | | ISP rate | | | |
| B6 Hotspot BA Bonus | | | | | Bonus included | | | |
| B7 Ultra Malls Bonus | | | | | Bonus included | | | |
| B8 ION Solutions | | | | | Role rates | | | |
| B9 First Year Add-On | | | | | Add-on included | | | |
| B10 AM Late Penalty | | | | | AM penalty applied | | | |
| B11 Penalty Exception | | | | | No penalty | | | |
| B12 Partnership At Cost | | | | | Skipped | | | |
| B13 ISP BW Partnership | | | | | Skipped | | | |
| B14 External Not Approved | | | | | External excluded | | | |
| B15 External Approved | | | | | External included | | | |
| Workflow Post | | | | | JE posted | | | |

## 12. Known Interpretation Rules

Use these rules when reviewing results:

- `Sales Person.commission_rate` is not the source of the custom commission sheet calculation.
- `Commission Lines.commission_rate` is the effective calculated rate.
- Fully paid date controls the commission quarter.
- Unpaid invoices are excluded.
- BA exclusions are customer-level.
- AM late payment penalty affects AM commission only.
- Penalty is controlled by `Sales Invoice.custom_payment_plan`, `Sales Invoice.due_date`, full payment date, and `Sales Invoice.custom_penalty_exception_approved`.
- `Service Active?` on Opportunity does not affect commission unless a future business rule is added.
