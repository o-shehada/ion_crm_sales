# دليل اختبار دورة العمولة

التاريخ: 2026-05-23
الموقع المستخدم: `testsite.local`
ورقة الاختبار الرئيسية: `STCT-05-26-00045`

هذا الملف هو نسخة عربية من دليل الاختبار العملي. الهدف منه أن يكون بديلا عن فيديو الشرح، بحيث يمكن لأي مستخدم أن يتبع الخطوات من النظام نفسه، بداية من تجهيز البيانات الأساسية، ثم إنشاء المستندات من الفرصة إلى فاتورة المبيعات والدفع، ثم مراجعة نتائج العمولة.

## 1. السيناريوهات التي تم اختبارها

الدورة الكاملة هي:

1. Opportunity
2. Quotation
3. Sales Order
4. Contract
5. Sales Invoice
6. Payment Entry
7. Sales Target and Commission Sheet
8. Commission Transaction
9. Commission Transaction Lines

### 1.1 أنواع الفرص

| نوع الفرصة | الغرض | مثال تم إنشاؤه |
|---|---|---|
| `Opportunity` | مسار الفرصة الأساسي / Dedicated | `CRM-OPP-2026-00036` |
| `Opportunity SM` | مسار فرص S&M | `CRM-OPP-2026-00037` |
| `Opportunity Hotels` | مسار فرص الفنادق | `CRM-OPP-2026-00041` |
| `Opportunity ISP` | مسار فرص ISP | `CRM-OPP-2026-00042` |
| `Opportunity Tenders` | مسار فرص المناقصات | `CRM-OPP-2026-00044` |

### 1.2 سيناريوهات المبيعات

| السيناريو | Service Category | ماذا يختبر؟ | معاملة العمولة |
|---|---|---|---|
| Sales Home | `Home` | عمولة المبيعات الأساسية، تقسيم المدير/المندوب، وعمولة تجاوز الهدف | `COMTR-05-26-00046` |
| Sales Hotspot | `Hotspot - Sales` | نسب Hotspot للمبيعات وعمولة تجاوز الهدف | `COMTR-05-26-00047` |

### 1.3 سيناريوهات Business Accounts

| السيناريو | Service Category | Transaction Type | ماذا يختبر؟ | معاملة العمولة |
|---|---|---|---|---|
| BA Dedicated NewLead | `Dedicated` | `NewLead` | نسبة العميل الجديد وإضافة أول سنة | `COMTR-05-26-00048` |
| BA Dedicated Upsell | `Dedicated` | `Upsell` | وجود تاريخ سابق للعميل يحول العملية إلى Upsell | `COMTR-05-26-00049` |
| BA Hotel NewLead | `Hotel` | `NewLead` | نسبة الفنادق | `COMTR-05-26-00050` |
| BA ISP NewLead | `ISPs` | `NewLead` | فرصة ISP ونسبة ISP | `COMTR-05-26-00051` |
| BA Hotspot Bonus | `Hotspot - BA` | `NewLead` | Hotspot BA مع مكافأة الاستحواذ | `COMTR-05-26-00052` |
| BA Ultra Malls Bonus | `Ultra - Malls` | `NewLead` | Ultra Malls مع مكافأة الاستحواذ ومسار المناقصات | `COMTR-05-26-00053` |
| BA ION Role Rates | `ION Solutions` | `NewLead` | نسب ION حسب الدور في Sales Team | `COMTR-05-26-00054` |
| BA External Rep Approved | `Dedicated` | `NewLead` | إدخال مندوب خارجي بعد اعتماد External Rep Approved | `COMTR-05-26-00055` |
| BA Late Payment Penalty | `Dedicated` | `NewLead` | خصم التأخير حسب خطة الدفع الربع سنوية | `COMTR-05-26-00056` |

### 1.4 ملاحظة مهمة

| النوع | حالة النظام الحالية |
|---|---|
| `Old` | الخيار موجود، لكن منطق إنشاء معاملات العمولة لا يستطيع إنتاجه حاليا لأن الاستدعاء يستخدم `detect_tx_type(..., is_renewal_flag=False)`. |
| `Renewal` | الخيار موجود في الحقول، لكن لا يوجد مسار حالي يرجع `Renewal`. |

## 2. تجهيز البيانات الأساسية

### 2.1 إنشاء Item Groups

1. اذهب إلى **Item Group**.
2. من القائمة، اضغط **New**.
3. عبئ الحقول:

| الحقل | القيمة |
|---|---|
| Item Group Name | `Home` |
| Parent Item Group | `All Item Groups` |
| Is Group | غير مفعل |

4. اضغط **Save**.
5. كرر نفس الخطوات للقيم التالية:

| Item Group Name |
|---|
| `Hotspot - Sales` |
| `Dedicated` |
| `Hotel` |
| `ISPs` |
| `ION Solutions` |
| `Hotspot - BA` |
| `Ultra - Malls` |

### 2.2 إنشاء Monthly Distribution

1. اذهب إلى **Monthly Distribution**.
2. اضغط **New**.
3. عبئ:

| الحقل | القيمة |
|---|---|
| Distribution ID | `Commission Cycle Even 0ckbfgtc` |
| Fiscal Year | `2026` |

4. في جدول **Percentages** أضف 12 صفا:

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

5. اضغط **Save**.

هذه التوزيعة تجعل هدف الربع الثاني Q2 يساوي 25% من الهدف السنوي، لأن Q2 هو أبريل ومايو ويونيو.

### 2.3 إنشاء Employees و Users

لمندوبي المبيعات:

1. اذهب إلى **Employee**.
2. اضغط **New**.
3. عبئ:

| الحقل | القيمة |
|---|---|
| First Name | `Commission` |
| Last Name | `Rep Matrix` أو أي اسم واضح |
| Gender | `Male` |
| Date of Birth | `1990-01-01` |
| Date of Joining | `2026-01-01` |
| Company | نفس الشركة المستخدمة في السيناريو |

4. اضغط **Save**.

لموظفي Business Accounts:

1. اذهب إلى **User**.
2. اضغط **New**.
3. عبئ:

| الحقل | القيمة |
|---|---|
| Email | بريد اختبار فريد |
| First Name | `Commission` |
| Last Name | أي لاحقة واضحة |
| User Type | `System User` |
| Role Profile | `AM` للـ Account Manager أو `SM` للـ SM |
| Send Welcome Email | غير مفعل |

4. اضغط **Save**.
5. افتح الموظف المرتبط.
6. ضع **User ID** على نفس المستخدم.
7. ضع **Department** على قسم يحتوي كلمة `Business`، مثل `Business Accounts`.
8. اضغط **Save**.

### 2.4 إنشاء Sales Persons

1. اذهب إلى **Sales Person**.
2. اضغط **New**.
3. عبئ:

| الحقل | القيمة |
|---|---|
| Sales Person Name | استخدم أحد الأسماء في الجدول التالي |
| Parent Sales Person | `Sales Team` |
| Is Group | غير مفعل |
| Enabled | مفعل |
| Employee | يعبأ للموظفين الداخليين، ويترك فارغا للمندوب الخارجي |
| Custom Is Sales Manager | `1` فقط لمدير المبيعات |

4. في جدول **Targets** أضف صفا:

| الحقل | القيمة |
|---|---|
| Item Group | `Home` |
| Fiscal Year | `2026` |
| Target Amount | حسب الجدول التالي |
| Target Distribution | `Commission Cycle Even 0ckbfgtc` |

5. اضغط **Save**.

الأشخاص المستخدمون في السيناريو:

| الدور | Sales Person | Target Amount | ملاحظات |
|---|---|---:|---|
| Sales Manager | `Commission Cycle unwmjuja` | 20,000 | `Custom Is Sales Manager = 1` |
| Sales Rep | `Commission Cycle evbs0zm8` | 40,000 | مربوط بموظف |
| BA AM | `Commission Cycle da4ibstb` | 36,000 | المستخدم المرتبط لديه Role Profile = `AM` |
| BA Executive | `Commission Cycle znslddnl` | 36,000 | المستخدم المرتبط لديه Role Profile = `SM` |
| BA ION Offer Team | `Commission Cycle lvbxtqab` | 36,000 | يستخدم في سيناريو ION |
| BA External Rep | `Commission Cycle fwfyrinq` | 36,000 | بدون Employee |

### 2.5 إنشاء Items

1. اذهب إلى **Item**.
2. من قائمة الأصناف، اضغط **New**.
3. عبئ:

| الحقل | القيمة |
|---|---|
| Item Code | كود فريد مثل `COMM-MATRIX-HOME` |
| Item Name | اسم واضح مثل `Commission Matrix Home` |
| Item Group | مجموعة الصنف حسب Service Category |
| Material Type | أي Material Type صحيح في النظام |
| Stock UOM | أي UOM صحيح |
| Is Stock Item | غير مفعل |
| Is Sales Item | مفعل |

4. اضغط **Save**.
5. كرر لكل Service Category: `Home`, `Hotspot - Sales`, `Dedicated`, `Hotel`, `ISPs`, `ION Solutions`, `Hotspot - BA`, `Ultra - Malls`.

## 3. إنشاء سيناريو كامل من البداية إلى النهاية

اتبع هذه الخطوات لأي سيناريو، ثم غير القيم حسب جدول السيناريوهات في القسم 4.

### 3.1 إنشاء Customer

1. اذهب إلى **Customer**.
2. اضغط **New**.
3. عبئ:

| الحقل | القيمة |
|---|---|
| Customer Name | `Commission Cycle Customer` مع لاحقة فريدة |
| Customer Type | `Company` |
| Customer Group | أي Customer Group صحيح |
| Territory | أي Territory صحيح |

4. اضغط **Save**.

### 3.2 إنشاء Opportunity

1. اذهب إلى نوع الفرصة المطلوب: **Opportunity** أو **Opportunity SM** أو **Opportunity Hotels** أو **Opportunity ISP** أو **Opportunity Tenders**.
2. اضغط **New**.
3. عبئ:

| الحقل | القيمة |
|---|---|
| Company | الشركة المستخدمة في السيناريو |
| Opportunity From | `Customer` |
| Party Name | العميل الذي تم إنشاؤه |
| Opportunity Type | `Dedicated` |
| Sales Stage | `Opportunity` |
| Expected Closing | `2026-04-30` |
| Transaction Date | `2026-04-10` |
| Conversion Rate | `1.0` |
| Territory | أي Territory صحيح |
| Industry | أي Industry Type صحيح |
| Market Segment | أي Market Segment صحيح |
| City | `Test City` |
| Material Type | أي Material Type صحيح |
| Account Manager | `Administrator` |
| Surveyor Manager | `Administrator` |
| Request | اسم السيناريو، مثل `Commission matrix Opportunity Home` |

في **Opportunity Tenders** أضف أيضا:

| الحقل | القيمة |
|---|---|
| RFP Document | أي ملف اختبار مرفق مثل `/files/commission-matrix-rfp.pdf` |

4. في جدول **Items** أضف:

| الحقل | القيمة |
|---|---|
| Item Code | الصنف الخاص بالـ Service Category |
| Qty | `1` |
| Rate | مبلغ السيناريو |
| Amount | مبلغ السيناريو |
| Base Rate | مبلغ السيناريو |
| Base Amount | مبلغ السيناريو |
| UOM | وحدة الصنف |
| Availability | `Available` |
| Valuation Rate | مبلغ السيناريو |
| Valuation Rate Company Currency | مبلغ السيناريو |

5. اضغط **Save**.

### 3.3 إنشاء Quotation

1. افتح الفرصة.
2. اضغط إجراء إنشاء **Quotation**.
3. في عرض السعر، ضع:

| الحقل | القيمة |
|---|---|
| Transaction Date | `2026-04-15`، وسيناريو التأخير يستخدم `2026-04-01` |
| Valid Till | أي تاريخ مستقبلي |

4. تأكد أن العميل والصنف تم نسخهما.
5. اضغط **Save**.
6. اضغط **Submit**.

### 3.4 إنشاء Sales Order

1. افتح عرض السعر المعتمد.
2. اضغط **Create > Sales Order**.
3. ضع:

| الحقل | القيمة |
|---|---|
| Transaction Date | نفس تاريخ Quotation |
| Delivery Date | `2026-04-30`، وسيناريو التأخير يستخدم `2026-04-01` |
| Cost Center | مركز تكلفة الشركة |

4. أضف Sales Team حسب القسم 4.
5. في **Payment Schedule** أضف:

| الحقل | القيمة |
|---|---|
| Due Date | تاريخ الاستحقاق الخاص بالسيناريو |
| Invoice Portion | `100` |
| Payment Amount | مبلغ السيناريو |

6. أنشئ Contract فعال حسب القسم التالي واربطه في Sales Order.
7. اضغط **Save**.
8. اضغط **Submit**.

### 3.5 إنشاء Active Contract

1. اذهب إلى **Contract**.
2. اضغط **New**.
3. عبئ:

| الحقل | القيمة |
|---|---|
| Party Type | `Customer` |
| Party Name | عميل Sales Order |
| Start Date | `2026-04-01` |
| Status | `Active` |
| Document Type | `Sales Order` |
| Document Name | رقم Sales Order |
| Contract Terms | `Commission cycle test contract` |

4. اضغط **Save**.
5. ارجع إلى Sales Order.
6. ضع **Custom Contract** على هذا العقد.
7. احفظ ثم اعتمد Sales Order.

### 3.6 إنشاء Sales Invoice

1. افتح Sales Order المعتمد.
2. اضغط **Create > Sales Invoice**.
3. ضع:

| الحقل | القيمة |
|---|---|
| Posting Date | تاريخ السيناريو |
| Due Date | تاريخ الاستحقاق |
| Service Category | Service Category الخاصة بالسيناريو |
| Debit To | حساب المدينين للشركة |
| Cost Center | مركز تكلفة الشركة |

4. في صفوف الأصناف، تأكد من:

| الحقل | القيمة |
|---|---|
| Income Account | حساب الإيراد للشركة |
| Cost Center | مركز تكلفة الشركة |

5. في Sales Team، تأكد أن الصفوف مطابقة للقسم 4.
6. فعل أي أعلام خاصة بالسيناريو، مثل First Year Contract Invoice أو BA Project Acquisition Bonus.
7. اضغط **Save**.
8. اضغط **Submit**.

### 3.7 إنشاء Payment Entry

1. افتح Sales Invoice المعتمدة.
2. اضغط **Create > Payment**.
3. عبئ:

| الحقل | القيمة |
|---|---|
| Posting Date | تاريخ الدفع الخاص بالسيناريو |
| Reference No | أي رقم فريد |
| Reference Date | تاريخ الدفع |
| Paid To | حساب النقدية للشركة |
| Paid Amount | كامل مبلغ الفاتورة |

4. اضغط **Save**.
5. اضغط **Submit**.
6. افتح Sales Invoice وتأكد أن **Outstanding Amount = 0**.

### 3.8 إنشاء Sales Target and Commission Sheet

1. اذهب إلى **Sales Target and Commission Sheet**.
2. اضغط **New**.
3. عبئ:

| الحقل | القيمة |
|---|---|
| Company | نفس شركة الفواتير |
| Fiscal Year | `2026` |
| Quarter | `Q2` |
| Remarks | `Persistent full commission matrix scenario for tracking.` |

4. في **Commission Lines** أضف:

| Sales Person | Department |
|---|---|
| `Commission Cycle unwmjuja` | `Sales` |
| `Commission Cycle evbs0zm8` | `Sales` |
| `Commission Cycle da4ibstb` | `Business Accounts` |
| `Commission Cycle znslddnl` | `Business Accounts` |
| `Commission Cycle lvbxtqab` | `Business Accounts` |
| `Commission Cycle fwfyrinq` | `Business Accounts` |

5. اضغط **Save**.
6. عند الحفظ، يقوم النظام بإنشاء Commission Transactions تلقائيا.

## 4. قيم كل سيناريو

| السيناريو | Opportunity Type | Service Category | Amount | Sales Team | إعدادات خاصة |
|---|---|---|---:|---|---|
| Sales Home | `Opportunity` | `Home` | 20,000 | Sales Manager 30%, Sales Rep 70% | Posting `2026-04-15`, Due `2026-04-30`, Paid `2026-04-20` |
| Sales Hotspot | `Opportunity SM` | `Hotspot - Sales` | 15,000 | Sales Manager 30%, Sales Rep 70% | نفس تواريخ Q2 |
| BA Dedicated NewLead | `Opportunity` | `Dedicated` | 12,000 | BA AM 50%, BA Executive 50% | First Year Contract Invoice مفعل |
| BA Dedicated Upsell | `Opportunity` | `Dedicated` | 9,000 | BA AM 50%, BA Executive 50% | يجب إنشاء فاتورة مدفوعة سابقة لنفس العميل |
| BA Hotel NewLead | `Opportunity Hotels` | `Hotel` | 11,000 | BA AM 50%, BA Executive 50% | دفع عادي داخل Q2 |
| BA ISP NewLead | `Opportunity ISP` | `ISPs` | 13,000 | BA AM 50%, BA Executive 50% | دفع عادي داخل Q2 |
| BA Hotspot Bonus | `Opportunity SM` | `Hotspot - BA` | 10,000 | BA AM 50%, BA Executive 50% | BA Project Acquisition Bonus مفعل |
| BA Ultra Malls Bonus | `Opportunity Tenders` | `Ultra - Malls` | 10,000 | BA AM 50%, BA Executive 50% | BA Project Acquisition Bonus مفعل و RFP Document مطلوب |
| BA ION Role Rates | `Opportunity` | `ION Solutions` | 16,000 | BA AM 50%, BA ION Offer 50% | أدوار ION على صفوف Sales Team |
| BA Late Payment Penalty | `Opportunity` | `Dedicated` | 8,000 | BA AM 50%, BA Executive 50% | Payment Plan `Quarterly`, Due `2026-04-01`, Paid `2026-06-01` |
| BA External Rep Approved | `Opportunity` | `Dedicated` | 7,000 | BA AM 50%, BA External Rep 50% | External Rep Approved مفعل |

أدوار ION:

| Sales Person | ION Role |
|---|---|
| `Commission Cycle da4ibstb` | `Account Lead Acquisition` |
| `Commission Cycle lvbxtqab` | `Offer Team` |

## 5. المستندات التي تم إنشاؤها

| السيناريو | Opportunity | Quotation | Sales Order | Sales Invoice | Payment Entry |
|---|---|---|---|---|---|
| Sales Home | `CRM-OPP-2026-00036` | `SAL-QTN-2026-00040` | `SAL-ORD-2026-00040` | `ACC-SINV-2026-00037` | `ACC-PAY-2026-00057` |
| Sales Hotspot | `CRM-OPP-2026-00037` | `SAL-QTN-2026-00041` | `SAL-ORD-2026-00041` | `ACC-SINV-2026-00038` | `ACC-PAY-2026-00058` |
| BA Dedicated NewLead | `CRM-OPP-2026-00038` | `SAL-QTN-2026-00042` | `SAL-ORD-2026-00042` | `ACC-SINV-2026-00039` | `ACC-PAY-2026-00059` |
| BA Dedicated Upsell | `CRM-OPP-2026-00040` | `SAL-QTN-2026-00044` | `SAL-ORD-2026-00044` | `ACC-SINV-2026-00041` | `ACC-PAY-2026-00061` |
| BA Hotel NewLead | `CRM-OPP-2026-00041` | `SAL-QTN-2026-00045` | `SAL-ORD-2026-00045` | `ACC-SINV-2026-00042` | `ACC-PAY-2026-00062` |
| BA ISP NewLead | `CRM-OPP-2026-00042` | `SAL-QTN-2026-00046` | `SAL-ORD-2026-00046` | `ACC-SINV-2026-00043` | `ACC-PAY-2026-00063` |
| BA Hotspot Bonus | `CRM-OPP-2026-00043` | `SAL-QTN-2026-00047` | `SAL-ORD-2026-00047` | `ACC-SINV-2026-00044` | `ACC-PAY-2026-00064` |
| BA Ultra Malls Bonus | `CRM-OPP-2026-00044` | `SAL-QTN-2026-00048` | `SAL-ORD-2026-00048` | `ACC-SINV-2026-00045` | `ACC-PAY-2026-00065` |
| BA ION Role Rates | `CRM-OPP-2026-00045` | `SAL-QTN-2026-00049` | `SAL-ORD-2026-00049` | `ACC-SINV-2026-00046` | `ACC-PAY-2026-00066` |
| BA Late Payment Penalty | `CRM-OPP-2026-00046` | `SAL-QTN-2026-00050` | `SAL-ORD-2026-00050` | `ACC-SINV-2026-00047` | `ACC-PAY-2026-00067` |
| BA External Rep Approved | `CRM-OPP-2026-00047` | `SAL-QTN-2026-00051` | `SAL-ORD-2026-00051` | `ACC-SINV-2026-00048` | `ACC-PAY-2026-00068` |

## 6. النتائج والتحليل

افتح `STCT-05-26-00045` وتأكد من:

| الحقل | القيمة المتوقعة |
|---|---:|
| Transaction Sync Status | `Synced` |
| Source of Totals | `Commission Transactions` |
| Commission Transaction Count | 11 |
| Total Target | 51,000 |
| Total Actual Sales | 131,000 |
| Total Commission | 11,600.25 |

### 6.1 معاملات العمولة

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

### 6.2 تحليل Sales Home

فاتورة Sales Home: `ACC-SINV-2026-00037`

| الشخص | Basis | Q2 Target | Base Commission | Above Target Commission | Total |
|---|---:|---:|---:|---:|---:|
| Sales Manager | 6,000 | 5,000 | 3 | 3 | 6 |
| Sales Rep | 14,000 | 10,000 | 7 | 12 | 19 |
| Total | 20,000 | 15,000 | 10 | 15 | 25 |

التحليل:

1. المدير يأخذ 30% من 20,000 = 6,000.
2. المندوب يأخذ 70% من 20,000 = 14,000.
3. نسبة Home الأساسية هي 0.05%.
4. نسبة تجاوز الهدف لـ Home هي 0.3%.
5. المدير تجاوز هدف Q2 بمبلغ 1,000.
6. المندوب تجاوز هدف Q2 بمبلغ 4,000.

### 6.3 تحليل NewLead و Upsell

`NewLead` يظهر عندما لا يوجد للعميل فواتير مبيعات معتمدة أو مدفوعة سابقا قبل هذه الفاتورة.

`Upsell` يظهر عندما يوجد تاريخ سابق للعميل. في السيناريو تم إنشاء فاتورة مدفوعة سابقة لنفس العميل، لذلك الفاتورة `ACC-SINV-2026-00041` أصبحت `Upsell`.

### 6.4 تحليل المكافآت

| Transaction | السبب |
|---|---|
| `COMTR-05-26-00052` | فاتورة `Hotspot - BA` عليها BA Project Acquisition Bonus. |
| `COMTR-05-26-00053` | فاتورة `Ultra - Malls` عليها BA Project Acquisition Bonus. |

مكافأة الاستحواذ قيمتها 3,000 وتقسم على الموظفين المؤهلين في الفاتورة.

### 6.5 تحليل ION Solutions

`COMTR-05-26-00054` يختبر نسب ION حسب الدور الموجود في صف Sales Team.

| Sales Person | ION Role |
|---|---|
| `Commission Cycle da4ibstb` | `Account Lead Acquisition` |
| `Commission Cycle lvbxtqab` | `Offer Team` |

### 6.6 تحليل External Rep

`COMTR-05-26-00055` يثبت أن المندوب الخارجي بدون Employee لا يدخل في العمولة إلا إذا كان **External Rep Approved** مفعلا في Sales Invoice.

### 6.7 تحليل Late Payment Penalty

`COMTR-05-26-00056` يختبر خصم التأخير:

| الحقل | القيمة |
|---|---|
| Due Date | `2026-04-01` |
| Fully Paid On | `2026-06-01` |
| Payment Plan | `Quarterly` |

الدفع تم داخل Q2، لذلك دخل في ورقة Q2، لكنه متأخر بما يكفي لتطبيق منطق الخصم.

## 7. طريقة التحقق من النظام

1. افتح **Sales Target and Commission Sheet** رقم `STCT-05-26-00045`.
2. تحقق من الإجماليات في القسم 6.
3. اذهب إلى **Commission Transaction**.
4. فلتر على **Sales Target and Commission Sheet** = `STCT-05-26-00045`.
5. افتح كل معاملة من الجدول.
6. راجع جدول **Lines**:
   - سيناريوهات Sales يجب أن تحتوي `Base` و `Above Target`.
   - سيناريوهات BA Bonus يجب أن تحتوي أسطر المكافأة أو الإضافة عند انطباقها.
   - سيناريو التأخير يجب أن يحتوي مكون `Penalty`.
7. افتح كل Sales Invoice وتأكد من:
   - المستند معتمد.
   - Outstanding Amount يساوي 0.
   - Service Category مطابق للسيناريو.
   - Sales Team مطابق للقيم في القسم 4.

## 8. الاختبار الآلي

أمر الاختبار:

```bash
bench --site testsite.local run-tests --module ion_crm_sales.ion_crm_sales.doctype.sales_target_and_commission_sheet.test_sales_target_and_commission_sheet --skip-test-records
```

آخر نتيجة:

```text
Ran 1 test in 4.726s
OK
```

الاختبار الآلي يغطي مسار Sales Home كاملا من Opportunity إلى Commission Transaction، ويتحقق من إنشاء الأسطر والإجماليات.
