# دليل UAT للعمولات من البداية إلى النهاية

هذا الدليل مخصص لاختبار المسار الكامل يدويا على موقع جديد، من `Opportunity` إلى `Quotation` ثم `Sales Invoice` و`Payment Entry` وصولا إلى `Sales Target and Commission Sheet` وترحيل قيد الاستحقاق.

استخدم الأسماء كما هي مكتوبة هنا حتى تكون نتائج الاختبار قابلة للمقارنة والمراجعة.

## 1. نطاق الاختبار

يغطي هذا الاختبار:

- إجراء Workflow باسم `Quote` على `Opportunity` وإنشاء `Quotation` تلقائيا.
- مسار البيع من `Opportunity` إلى `Quotation` ثم `Sales Invoice` ثم `Payment Entry`.
- احتساب `Sales Target and Commission Sheet`.
- سيناريوهات عمولات قسم المبيعات.
- سيناريوهات عمولات Business Accounts.
- حقول `Actual Sales` و`Achievement %` و`Commission Value` و`Commission Rate`.
- إجراء Workflow باسم `Post` لإنشاء وترحيل قيد استحقاق العمولة `Journal Entry`.

## 2. الإعدادات المطلوبة

استخدم القيم التالية:

- Company: `ION`
- Fiscal Year: `2026`
- Quarter: `Q1`
- Currency: `LYD`
- Price List: `Standard Selling`

تأكد أن الحسابات التالية موجودة للشركة `ION`:

- Income Account: `4110 - Sales - I`
- Receivable Account: `1310 - Debtors - I`
- Cash Account: `1110 - Cash - I`
- Cost Center: `Main - I`

في `Commission Policy Settings` اضبط:

- Expense Account: حساب مصروفات صالح، مثال `55002 - عمولة المبيعات - Sales Commission - I`
- Payable Account: حساب التزام صالح، مثال `2700 - حسابات دائنة أخرى - Other Payables - I`

## 3. البيانات الرئيسية

### 3.1 Monthly Distribution

أنشئ `Monthly Distribution`:

- Name: `UAT-COMM-2026-EVEN`
- Fiscal Year: `2026`

أضف 12 صفا:

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

المتوقع أن يكون هدف الربع الأول `Q1` مساويا لـ 25% من الهدف السنوي.

### 3.2 Employees وUsers وSales Persons

أنشئ لكل شخص:

- `Employee`
- `User`
- `Sales Person`

اربط كل `Sales Person` مع `Employee` الخاص به.

استخدم هدفا سنويا `40,000` لكل `Sales Person`. مع التوزيع الشهري أعلاه، يجب أن يكون هدف `Q1` هو `10,000`.

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

ملاحظات مهمة:

- الحقل `Sales Person.commission_rate` هو معدل ERPNext الافتراضي في صفوف `Sales Team`.
- هذا الحقل ليس مصدر الحقيقة لحساب عمولات `Sales Target and Commission Sheet` المخصصة.
- الحقل `Commission Lines.commission_rate` يجب أن يعرض المعدل الفعلي المحسوب:

```text
commission_rate = commission_value / actual_sales * 100
```

### 3.3 Item Groups وItems

أنشئ `Item Group` التالية إذا لم تكن موجودة:

- `Home`
- `Hotspot - Sales`
- `Dedicated`
- `Hotel`
- `ISPs`
- `ION Solutions`
- `Hotspot - BA`
- `Ultra - Malls`

أنشئ خدمة غير مخزنية لكل مجموعة:

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

لكل Item اضبط:

- Stock UOM: `Nos`
- Is Stock Item: غير محدد
- Income Account: `4110 - Sales - I`
- Selling Cost Center: `Main - I`

## 4. اختبار Workflow من Opportunity إلى Quotation

أنشئ `Opportunity` جديد:

- Customer: أنشئ `UAT Orbit Telecom Company`
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
- Service Active?: محدد

أضف Item واحد:

- Item: `UAT Dedicated Service`
- Qty: `1`
- Rate: `10,000`

انقل الـ Workflow إلى الحالة التي تسبق `Quote`، وغالبا تكون `Approved`.

اضغط إجراء Workflow:

- `Quote`

المتوقع:

- ينتقل `Opportunity` إلى `Accepted`.
- يتم إنشاء `Quotation` بحالة Draft تلقائيا.
- تصبح حالة `Opportunity` هي `Quotation`.
- يتم ربط `Quotation` بالـ `Opportunity`.
- يظهر في سجل التدقيق نص مثل `Quotation Created: <quotation name>`.

## 5. قواعد Sales Invoice وPayment

لكل سيناريو:

1. أنشئ Customer جديد أو أعد استخدام Customer موجود.
2. أنشئ Opportunity يحتوي على Item واحد على الأقل.
3. استخدم Workflow action باسم `Quote` أو أنشئ Quotation يدويا من Opportunity.
4. أنشئ Sales Invoice من Quotation أو يدويا بنفس Customer وItem.
5. اضبط `Sales Invoice.custom_service_category` حسب نوع الخدمة في السيناريو.
6. أضف صفوف `Sales Team`.
7. اعتمد `Sales Invoice` عن طريق Submit.
8. أنشئ `Payment Entry` مقابل `Sales Invoice`.
9. اعتمد `Payment Entry` عن طريق Submit.

العمولة تحتسب فقط لفواتير Sales Invoice التي تكون:

- Submitted.
- مدفوعة بالكامل.
- تاريخ الدفع داخل ربع `Sales Target and Commission Sheet`.
- تستخدم Service Category مدعومة في محرك العمولات.

## 6. سيناريوهات قسم المبيعات

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

المتوقع:

- تطبيق معدل Home العادي.
- تطبيق تقسيم المدير وباقي الفريق.
- لا يتم تطبيق إضافة Above Target إذا كان الإنجاز ما زال أقل من الهدف.

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

المتوقع:

- تطبيق العمولة العادية على كامل المبلغ.
- تطبيق إضافة Above Target فقط على الجزء الذي تجاوز الهدف.

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

المتوقع:

- تطبيق عمولة Hotspot Sales العادية.
- تطبيق تقسيم المدير وباقي الفريق.

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

المتوقع:

- تطبيق العمولة العادية.
- تطبيق إضافة Above Target على الجزء الذي تجاوز الهدف.

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

المتوقع:

- إعادة توزيع حصة المدير على Sales Persons المؤهلين غير المديرين.

### Scenario S6: Unpaid Invoice

Sales Invoice:

- Customer: `UAT Unpaid Excluded Customer`
- Posting Date: `2026-02-10`
- Due Date: `2026-02-20`
- Service Category: `Home`
- Item: `UAT Home Service`
- Amount: `9,000`

لا تنشئ `Payment Entry`.

المتوقع:

- يتم استبعاد الفاتورة من العمولة.

### Scenario S7: Paid in Next Quarter

Sales Invoice:

- Customer: `UAT Paid In Q2 Customer`
- Posting Date: `2026-03-15`
- Due Date: `2026-03-20`
- Payment Date: `2026-04-05`
- Service Category: `Home`
- Item: `UAT Home Service`
- Amount: `9,000`

المتوقع:

- يتم استبعاد الفاتورة من عمولة `Q1`.
- يجب أن تظهر الفاتورة في عمولة `Q2`.

## 7. سيناريوهات Business Accounts

### Scenario B1: Dedicated Old Renewal

أولا أنشئ تاريخا سابقا للعميل:

- Customer: `UAT Dedicated Existing Customer`
- أنشئ Sales Invoice من نوع Dedicated في سنة 2025 بقيمة `1,000`، ثم Submit وPayment.

بعد ذلك أنشئ فاتورة Q1:

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

المتوقع:

- العميل لديه تاريخ فواتير سابق.
- يتم تطبيق معدل Old/Renewal.

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

المتوقع:

- يتم تطبيق معدل New Lead.

### Scenario B3: Dedicated Upsell

استخدم عميلا لديه تاريخ فاتورة مدفوعة سابقا، ثم أنشئ:

- Service Category: `Dedicated`
- Amount: `15,000`
- Payment Date داخل `Q1`

المتوقع:

- يتم تطبيق معدل Upsell.

### Scenario B4: Hotel New Lead

- Customer: `UAT Hotel Customer`
- Service Category: `Hotel`
- Amount: `11,000`
- Payment Date داخل `Q1`

Sales Team:

| Sales Person | Allocation % |
|---|---:|
| Mariam Al-Fitouri | 50 |
| Huda Al-Werfalli | 50 |

المتوقع:

- يتم تطبيق معدل Hotel New Lead.

### Scenario B5: ISPs New Lead

- Customer: `UAT ISP Customer`
- Service Category: `ISPs`
- Amount: `20,000`
- Payment Date داخل `Q1`

المتوقع:

- يتم تطبيق معدل ISP New Lead.

### Scenario B6: Hotspot BA Acquisition Bonus

- Customer: `UAT Hotspot BA Customer`
- Service Category: `Hotspot - BA`
- Amount: `12,000`
- Payment Date داخل `Q1`
- حدد: `BA Project Acquisition Bonus`

Sales Team:

| Sales Person | Allocation % |
|---|---:|
| Mariam Al-Fitouri | 33 |
| Salem Al-Obeidi | 33 |
| Huda Al-Werfalli | 34 |

المتوقع:

- يتم تطبيق عمولة Hotspot BA.
- يتم تقسيم مكافأة الاستحواذ `3,000` بين Sales Persons المرتبطين بموظفين.

### Scenario B7: Ultra Malls Acquisition Bonus

- Customer: `UAT Ultra Malls Customer`
- Service Category: `Ultra - Malls`
- Amount: `13,000`
- Payment Date داخل `Q1`
- حدد: `BA Project Acquisition Bonus`

Sales Team:

| Sales Person | Allocation % |
|---|---:|
| Mariam Al-Fitouri | 33 |
| Salem Al-Obeidi | 33 |
| Huda Al-Werfalli | 34 |

المتوقع:

- يتم تطبيق عمولة Ultra Malls.
- يتم تقسيم مكافأة الاستحواذ `3,000` بين Sales Persons المرتبطين بموظفين.

### Scenario B8: ION Solutions Roles

- Customer: `UAT ION Solutions Customer`
- Service Category: `ION Solutions`
- Amount: `18,000`
- Payment Date داخل `Q1`

Sales Team:

| Sales Person | Allocation % | ION Role |
|---|---:|---|
| Huda Al-Werfalli | 33 | Account Lead Acquisition |
| Tarek Al-Zintani | 33 | Offer Team |
| Ayman Al-Kikli | 34 | Execution Team |

المتوقع:

- تطبيق معدل Account Lead Acquisition على Huda.
- تطبيق معدل Offer Team على Tarek.
- تطبيق معدل Execution Team على Ayman.

### Scenario B9: First-Year Contract Add-On

- Customer: `UAT First Year Contract Customer`
- Service Category: `Dedicated`
- Amount: `16,000`
- Payment Date داخل `Q1`
- حدد: `First Year Contract Invoice`

Sales Team:

| Sales Person | Allocation % |
|---|---:|
| Mariam Al-Fitouri | 33 |
| Salem Al-Obeidi | 33 |
| Huda Al-Werfalli | 34 |

المتوقع:

- يتم تطبيق إضافة السنة الأولى فقط في حالة New Lead.
- يتم تقسيم الإضافة بين الموظفين المرتبطين من غير AM وغير SM.

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

المتوقع:

- يتم تطبيق غرامة التأخر في الدفع على عمولة AM فقط.
- تاريخ بداية حساب الغرامة هو `Sales Invoice.due_date`. إذا لم يكن موجودا، يستخدم النظام `posting_date`.
- في خطة `Yearly` تكون فترة السماح 90 يوما، ثم يتم تطبيق تخفيض 50% مرة واحدة، ثم تخفيض إضافي 10% لكل فترة 30 يوما بعد فترة السماح.
- في هذا السيناريو، من `2026-01-10` إلى `2026-04-20` يوجد 100 يوم تأخير. فترة السماح 90 يوما، إذن التأخير بعد السماح هو 10 أيام.
- معامل الغرامة المتوقع هو `1.0 - 0.50 - (0.10 * 0) = 0.50`.
- Mariam Al-Fitouri هي AM في هذا السيناريو، لذلك يجب تخفيض عمولة AM الخاصة بها من هذه الفاتورة بنسبة 50%.
- Huda Al-Werfalli ليست AM، لذلك لا يجب تخفيض عمولتها بسبب غرامة التأخر في الدفع.

اختبارات إضافية لخطة الغرامة:

| Payment Plan | Grace Period | Cadence After Grace | Test Example | Expected |
|---|---:|---:|---|---|
| Yearly | 90 days | 30 days | Due `2026-01-10`, paid `2026-04-20` | 50% AM reduction |
| 6 Months | 42 days | 14 days | Due `2026-01-10`, paid `2026-02-25` | 50% AM reduction |
| Quarterly | 21 days | 7 days | Due `2026-01-10`, paid `2026-02-07` | 60% AM reduction |

معادلة الغرامة:

```text
if fully_paid_on - due_date <= grace_days:
    factor = 1.0
else:
    over = late_days - grace_days
    blocks = over // cadence_days
    factor = max(0.0, 1.0 - 0.50 - 0.10 * blocks)
```

### Scenario B11: Penalty Exception

استخدم نفس إعداد B10، لكن حدد:

- `Penalty Exception Approved`

المتوقع:

- لا يتم تطبيق غرامة التأخر.
- يجب أن تبقى عمولة AM بالقيمة العادية المحسوبة حتى لو تم دفع الفاتورة بعد فترة السماح.

### Scenario B12: Partnership at Cost

Customer:

- `UAT Partnership At Cost Customer`
- حدد حقل العميل: `Partnership At Cost`

Invoice:

- Service Category: `Dedicated`
- Amount: `10,000`
- Payment Date داخل `Q1`

المتوقع:

- يتم تجاهل عمولة BA لهذا العميل.

### Scenario B13: ISP BW Partnership

Customer:

- `UAT ISP BW Partnership Customer`
- حدد حقل العميل: `ISP BW Partnership`

Invoice:

- Service Category: `ISPs`
- Amount: `10,000`
- Payment Date داخل `Q1`

المتوقع:

- يتم تجاهل عمولة BA لهذا العميل.

### Scenario B14: External Rep Not Approved

- Customer: `UAT External Rep Not Approved Customer`
- Service Category: `Dedicated`
- Amount: `10,000`
- Payment Date داخل `Q1`
- لا تحدد `External Rep Approved`

Sales Team:

| Sales Person | Allocation % |
|---|---:|
| Mariam Al-Fitouri | 50 |
| Leila Mansour | 50 |

المتوقع:

- يتم استبعاد External Rep إذا لم يكن مؤهلا أو معتمدا.

### Scenario B15: External Rep Approved

نفس إعداد B14، لكن حدد:

- `External Rep Approved`

المتوقع:

- يتم احتساب External Rep في الحالات التي يسمح بها محرك العمولات.

## 8. إنشاء Sales Target and Commission Sheet

أنشئ `Sales Target and Commission Sheet`:

- Company: `ION`
- Fiscal Year: `2026`
- Quarter: `Q1`
- Status: `Draft`

أضف Commission Lines:

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

احفظ الـ Sheet.

المتوقع:

- يتم تعبئة `Target Value` من أهداف Sales Person.
- يتم تعبئة `Actual Sales` لقسم Sales وBusiness Accounts.
- يتم تعبئة `Achievement Pct`.
- يتم تعبئة `Commission Value`.
- يتم تعبئة `Commission Rate` كمعدل فعلي محسوب.

اضغط:

- `Recalculate Commission`

المتوقع:

- يتم تحديث القيم بدون إنشاء قيد استحقاق.

## 9. Submit وApprove وPost

استخدم الـ Workflow:

1. من `Draft` اضغط `Submit`.
2. من `Submitted` اضغط `Approve`.
3. من `Approved` اضغط `Post`.

المتوقع عند `Post`:

- تصبح حالة الـ Sheet هي `Posted`.
- يتم إنشاء `Journal Entry` للاستحقاق وترحيله.
- يتم تعبئة `Accrual JE`.
- قيمة `Accrual Posted Amount` تساوي `Total Commission`.

الزر المخصص `Post Accrual _` يجب أن يبقى يعمل من حالة `Approved`، لكن زر Workflow `Post` يجب أن يعطي نفس النتيجة.

## 10. فحص التقارير

بعد الترحيل، افحص التقارير التالية:

- `Target vs Actual`
- `Commission to Revenue Ratio`
- `Accrued Commission Payable`

المتوقع:

- تظهر الـ Sheet المرحلة في التقارير.
- إجمالي العمولة في التقارير يطابق الـ Sheet.
- `Actual Sales` يتضمن مبيعات Sales وBA.

## 11. جدول أدلة UAT

املأ هذا الجدول أثناء الاختبار:

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

## 12. قواعد تفسير النتائج

استخدم هذه القواعد عند مراجعة النتائج:

- `Sales Person.commission_rate` ليس مصدر حساب العمولة المخصصة في `Sales Target and Commission Sheet`.
- `Commission Lines.commission_rate` هو المعدل الفعلي المحسوب.
- تاريخ الدفع الكامل هو الذي يحدد ربع العمولة.
- الفواتير غير المدفوعة مستبعدة.
- استبعادات BA تكون على مستوى Customer.
- غرامة تأخر الدفع للـ AM تؤثر على عمولة AM فقط.
- الغرامة تعتمد على `Sales Invoice.custom_payment_plan` و`Sales Invoice.due_date` وتاريخ الدفع الكامل و`Sales Invoice.custom_penalty_exception_approved`.
- حقل `Service Active?` في `Opportunity` لا يؤثر على العمولة إلا إذا تمت إضافة قاعدة أعمال مستقبلية لذلك.
