# دليل تدريبي وتحليلي لمسار CRM والمبيعات والفرق بين Sales وBusiness Accounts

## 1. الهدف من الدليل

هذا الدليل مخصص لتدريب الموظفين على استخدام نظام CRM/ERPNext في شركة أيون من منظور عملي وتحليلي. يوضح الدليل رحلة المستندات من بداية الفرصة إلى التحصيل والعمولة، مع التركيز على الفرق بين:

- قسم المبيعات `Sales Department`
- قسم حسابات الأعمال `Business Accounts`

الدليل مبني على قراءة الكود الحالي لتطبيق `ion_crm_sales`، وملفات Excel وWord الموجودة داخل مجلد `docs`، خصوصا ملفات العمولات، الأهداف، الـKPIs، وتحليل الفجوات.

## 2. الصورة العامة للنظام

النظام ليس مجرد CRM لإدخال فرص بيع. التطبيق يضيف طبقة تشغيلية فوق ERPNext تربط بين:

- الفرص `Opportunity` وأنواعها.
- عروض الأسعار `Quotation`.
- أوامر البيع `Sales Order`.
- العقود `Contract`.
- فواتير المبيعات `Sales Invoice`.
- التحصيل `Payment Entry`.
- العمولة والأهداف `Sales Target and Commission Sheet`.
- معاملات العمولة التفصيلية `Commission Transaction`.
- مستندات تشغيلية إضافية مثل `Hotspot` و`Distributor` و`Booking` و`Technical Survey`.

القاعدة المهمة في التدريب: كل خطوة في النظام تترك أثرا لاحقا. إدخال بيانات ناقصة أو تصنيف خاطئ في الفرصة أو الفاتورة يؤثر على العقد، الفاتورة، التحصيل، التقارير، والعمولة.

## 3. المسار القياسي من الفرصة إلى التحصيل

المسار العام في النظام كالتالي:

```text
Opportunity
→ Quotation
→ Sales Order
→ Contract
→ Sales Invoice
→ Payment Entry
→ Commission Transaction
→ Sales Target and Commission Sheet
→ Journal Entry للعمولة عند الترحيل
```

قد تختلف بعض التفاصيل حسب نوع الخدمة أو القسم، لكن هذا هو العمود الفقري للعملية.

## 4. أنواع الفرص في النظام

يوجد أكثر من نوع فرصة، وليس كل الأعمال تدخل من نفس الشاشة فقط:

| نوع الفرصة | الاستخدام | تصنيفها على Quotation |
|---|---|---|
| `Opportunity` | المسار الأساسي، ويستخدم كثيرا مع Dedicated | `Dedicated` |
| `Opportunity SM` | فرص S&M أو المشاريع/الخدمات ذات طبيعة خاصة | `S&M` |
| `Opportunity Hotels` | فرص الفنادق | `Hotels` |
| `Opportunity Tenders` | المناقصات | `Tenders` |
| `Opportunity ISP` | مزودي الإنترنت ISPs | `ISP` في الكود، مع ملاحظة أن حقل `custom_opportunity_from` الحالي لا يظهر خيار ISP ضمن الخيارات المستخرجة من fixtures |

### 4.1 أثر نوع الفرصة

نوع الفرصة لا يغير اسم الشاشة فقط، بل يؤثر على:

- الحقول التي تربط `Quotation` بالفرصة الأصلية.
- قيمة `custom_opportunity_from` في `Quotation` ثم `Sales Order` ثم `Sales Invoice`.
- طريقة قراءة التقارير والتحليل التجاري.
- مسار التشغيل المتوقع، مثل الفنادق، المناقصات، ISP، Dedicated.

### 4.2 التحول من Dedicated إلى Opportunity SM

في كود `opportunity_dedicated_handlers.py`، إذا تغيرت حالة `Opportunity` الأساسية إلى `Converted`، يقوم النظام بإنشاء `Opportunity SM` جديدة وينسخ إليها الحقول المتاحة ثم يضعها في حالة `Scoping`.

معنى ذلك تدريبيا:

- ليست كل فرصة Dedicated تنتهي مباشرة ببيع.
- بعض الفرص تتحول إلى مسار S&M لمزيد من الدراسة أو النطاق.
- يجب على الموظف فهم أن التحويل ينشئ مستندا جديدا، وليس مجرد تغيير حالة.

## 5. مرحلة Opportunity

### 5.1 وظيفة الفرصة

الفرصة هي نقطة تسجيل الطلب التجاري والفني الأولية. فيها يتم تحديد:

- العميل أو العميل المحتمل.
- نوع الفرصة.
- المرحلة التجارية.
- مسؤول الحساب `Account Manager`.
- مهندس المبيعات `Sales Engineer`.
- متطلبات العميل.
- بيانات العقد المتوقعة.
- بيانات فنية أولية.
- الأصناف المطلوبة.
- المسح الفني `Survey` إن وجد.
- نطاق العمل `Scope`.
- المخرجات `Deliverables`.

### 5.2 حقول مهمة في Opportunity

من الحقول الموجودة أو المعدلة في النظام:

| الحقل | المعنى العملي |
|---|---|
| `custom_account_manager` | مدير الحساب المسؤول. يؤثر لاحقا على Sales Team في Sales Order. |
| `custom_sales_engineer` | مهندس المبيعات أو الشخص الفني/التجاري المساند. |
| `custom_surveyor_manager` | مسؤول تعيين المساحين/الفنيين. |
| `custom_request` | طلب العميل. |
| `custom_requirements` | المتطلبات التفصيلية. |
| `custom_scope_description` | وصف نطاق العمل. |
| `custom_deliverables` | المخرجات المطلوب تنفيذها أو متابعتها. |
| `custom_out_of_scope` | الأعمال خارج النطاق. |
| `custom_contract_starting_date` | تاريخ بداية العقد المتوقع. |
| `custom_contract_end_date` | تاريخ نهاية العقد المتوقع. |
| `custom_service_active` | هل الخدمة نشطة. |
| `custom_price_list` | قائمة السعر المستخدمة للفرصة. |
| `custom_warehouse` | المخزن المستخدم لجلب الكمية والتكلفة. |

### 5.3 حقول إلزامية حسب تحليل الفجوة

حسب مستند CRP2 وملف GAP Analysis، هناك توجه لجعل حقول مثل:

- `expected_closing`
- `city`
- `industry`
- `territory`
- `market_segment`

إلزامية في جميع الفرص.

الغرض التدريبي: هذه الحقول ليست شكلية. تستخدم في التقارير، تقسيم السوق، متابعة الفرص المتأخرة، وقياس أداء المناطق والقطاعات.

### 5.4 أثر الأصناف والمخزون في Opportunity

يوجد Client Script يقرأ من `Bin` عند اختيار `custom_warehouse` أو عند الضغط على حساب داخل `Opportunity Item`:

- يجلب `valuation_rate`.
- يجلب `actual_qty`.
- يحدد إن كانت الكمية متاحة أو غير متاحة.
- يحسب التكلفة بعملة الشركة.

الأثر على العمل:

- الموظف يرى التكلفة والتوفر قبل العرض.
- الإدارة تستطيع تقييم الربحية قبل اعتماد السعر.
- الخطأ في المخزن أو الصنف يؤدي إلى قراءة تكلفة أو توفر غير صحيح.

## 6. إنشاء Quotation من Opportunity

### 6.1 الإنشاء الآلي عند قبول الفرصة

الكود يحتوي على منطق مهم: عند تغير `workflow_state` إلى `Accepted` في أحد أنواع الفرص المدعومة، يقوم النظام بإنشاء `Quotation` تلقائيا إذا كانت الفرصة تحتوي على Items.

الشروط الأساسية:

- تغير حالة Workflow إلى `Accepted`.
- وجود Items داخل الفرصة.
- عدم وجود Quotation سابق لنفس الفرصة.

النتيجة:

- إنشاء `Quotation` بحالة Draft.
- ربطه بالفرصة الأصلية.
- تحديث حالة الفرصة إلى `Quotation`.
- إضافة سجل في `custom_audit_log` مثل `Quotation Created: <quotation name>`.

### 6.2 الربط بين Quotation ونوع الفرصة

الحقل `custom_opportunity_from` على `Quotation` يأخذ قيمة مثل:

- `Dedicated`
- `S&M`
- `Hotels`
- `Tenders`
- `ISP` حسب الكود

هذا الحقل مهم لأنه ينتقل لاحقا إلى `Sales Order` ثم `Sales Invoice` عبر Server Scripts.

### 6.3 الفرق بين إنشاء Quotation يدويا وآليا

| الطريقة | متى تستخدم | المخاطر |
|---|---|---|
| من Workflow `Accepted` | المسار الأفضل لأنه يحافظ على الربط | يحتاج Items قبل الإجراء |
| من زر إنشاء يدوي | عند الحاجة أو التصحيح | يجب التأكد من ربط الفرصة وتصنيف `custom_opportunity_from` |
| إدخال Quotation مباشرة | حالات استثنائية | قد تضيع علاقة الفرصة والتقارير والعمولة |

## 7. مرحلة Quotation

### 7.1 وظيفة Quotation

عرض السعر هو المستند التجاري الذي يعرض:

- الأصناف والخدمات.
- الكميات والأسعار.
- الضرائب.
- شروط الدفع.
- الشروط والأحكام.
- مرجع الفرصة.

في ملف `Dedicated Qoutation.docx` يظهر قالب عرض لخدمة Dedicated يتضمن:

- الباقة.
- مدة العقد.
- طريقة الدفع.
- القيمة الشهرية.
- القيمة السنوية.
- أسعار معدات الربط والتركيب حسب السرعة.

### 7.2 أثر Quotation على Sales Order

عند إنشاء `Sales Order` من `Quotation`، يستدعي النظام دالة مخصصة تضيف منطق Sales Team:

- يبحث عن الفرصة الأصلية.
- يقرأ `custom_account_manager`.
- ينشئ أو يجد `Sales Person` مرتبطا بهذا المستخدم.
- يضعه في `sales_team` بنسبة 100%.

معنى ذلك:

- مدير الحساب في الفرصة يتحول تلقائيا إلى مساهم في أمر البيع.
- إذا لم يكن المستخدم مربوطا بـEmployee/Sales Person، قد لا تتم إضافة الشخص كما هو متوقع.

## 8. مرحلة Sales Order

### 8.1 وظيفة Sales Order

أمر البيع هو الالتزام التجاري الداخلي بتنفيذ البيع بعد قبول العرض. في النظام الحالي له دور مهم في العقود والفوترة.

### 8.2 الحقول المهمة على Sales Order

| الحقل | المعنى |
|---|---|
| `custom_opportunity_from` | مصدر الفرصة المنقول من Quotation. |
| `custom_contract` | العقد المرتبط بأمر البيع. |
| `sales_team` | فريق المبيعات/حسابات الأعمال المرتبط بالعملية. |

### 8.3 شرط العقد قبل الفاتورة

يوجد تحقق في النظام يمنع إنشاء أو اعتماد `Sales Invoice` من `Sales Order` إذا كان:

- `custom_opportunity_from` موجودا.
- ولا يوجد `custom_contract`.
- أو العقد موجود لكنه ليس `Active`.

رسالة النظام المتوقعة:

```text
You must create or link an Active Contract on Sales Order before creating a Sales Invoice.
```

المعنى التدريبي:

- العقد ليس مرفقا اختياريا في المسار المنظم.
- لا يجب الانتقال إلى الفاتورة قبل إنشاء أو ربط عقد Active.
- مسؤولية الفريق التجاري والمالي التأكد من حالة العقد قبل الفوترة.

### 8.4 إنشاء العقد من Sales Order

يوجد Client Script يضيف زر `Create Contract` على `Sales Order`. الزر يستدعي Server Script باسم `create_contract_for_so` لإنشاء عقد من قالب `RMT Contract` وربطه بالـSales Order.

ملاحظة مهمة: في السكربت يوجد محاولة ربط العقد بحقل باسم `contract`، بينما الحقل الفعلي المستخرج من fixtures هو `custom_contract`. هذا يحتاج مراجعة تنفيذية في الموقع إذا كان الزر لا يربط العقد تلقائيا كما هو متوقع.

## 9. مرحلة Contract

### 9.1 وظيفة العقد

العقد يمثل الأساس القانوني والتشغيلي قبل إصدار الفاتورة. في ملف `Dedicated Contract.docx` يظهر عقد خدمة خط إنترنت مخصص ويتضمن:

- أطراف العقد.
- تمهيد الخدمة.
- التزامات الطرف الأول.
- قيمة العقد.
- شروط الدفع.
- مدة العقد.
- التجديد السنوي.
- نقل الخدمة أو تغيير الوصلة.
- منع التنازل دون موافقة.

### 9.2 أثر العقد على النظام

العقد يؤثر مباشرة على:

- السماح بإنشاء الفاتورة.
- ضبط الانضباط المالي.
- توثيق شروط الخدمة.
- دعم التجديد والاشتراكات.
- تقليل مخاطر بيع خدمة دون سند تعاقدي.

## 10. مرحلة Sales Invoice

### 10.1 وظيفة الفاتورة

`Sales Invoice` هي المستند المالي الرسمي الذي يعترف بالإيراد والذمة المدينة. في هذا التطبيق هي أيضا نقطة رئيسية لحساب العمولة، لكن العمولة لا تعتمد على الفاتورة بمجرد إنشائها فقط، بل على سدادها بالكامل.

### 10.2 الحقول المخصصة المهمة على Sales Invoice

| الحقل | الاستخدام |
|---|---|
| `custom_opportunity_from` | مصدر الفرصة المنقول من Sales Order. |
| `custom_service_category` | تصنيف الخدمة، وهو أهم حقل للعمولة. |
| `custom_payment_plan` | خطة الدفع: Yearly / 6 Months / Quarterly. |
| `custom_penalty_exception_approved` | استثناء معتمد من عقوبة التأخير. |
| `custom_first_year_contract_invoice` | تفعيل إضافة أول سنة في Business Accounts. |
| `custom_ba_project_acquisition_bonus` | تفعيل مكافأة الاستحواذ في BA لبعض الفئات. |
| `custom_external_rep_approved` | السماح باحتساب مندوب خارجي غير موظف في BA. |
| `sales_team` | الأشخاص الذين ستقرأهم العمولة. |

### 10.3 أهمية Service Category

هذا الحقل هو أساس تمييز الفاتورة:

| Service Category | القسم المرتبط غالبا |
|---|---|
| `Home` | Sales |
| `Hotspot - Sales` | Sales |
| `Dedicated` | Business Accounts |
| `Hotel` | Business Accounts |
| `ISPs` | Business Accounts |
| `ION Solutions` | Business Accounts |
| `Hotspot - BA` | Business Accounts |
| `Ultra - Malls` | Business Accounts |

إذا تم اختيار تصنيف خاطئ:

- قد تدخل الفاتورة في محرك عمولة خاطئ.
- قد لا تظهر في ورقة العمولة.
- قد تتغير نسب العمولة بالكامل.
- قد تتأثر التقارير.

## 11. مرحلة Payment Entry

### 11.1 وظيفة الدفع

`Payment Entry` يسجل تحصيل الفاتورة. محرك العمولة في النظام لا يعتمد على الفاتورة المفتوحة، بل يبحث عن الفواتير:

- `docstatus = 1`
- `outstanding_amount = 0`
- وتاريخ السداد الكامل يقع داخل الربع المطلوب.

### 11.2 تاريخ السداد الكامل

النظام يحدد تاريخ السداد الكامل من:

- آخر `Payment Entry` مرتبط بالفاتورة.
- وإذا لم يجد Payment Entry يستخدم تاريخ تعديل الفاتورة كحل بديل عند كونها مسددة.

الأثر التدريبي:

- تاريخ الدفع وليس تاريخ الفاتورة هو الذي يحدد ربع العمولة.
- فاتورة صادرة في مارس ومدفوعة بالكامل في أبريل تدخل في ربع أبريل، وليس ربع مارس.
- الفاتورة غير المسددة بالكامل لا تدخل في العمولة.

### 11.3 أثر Payment Entry على إعادة احتساب العمولة

عند Submit لـ`Payment Entry`، النظام يبحث عن أوراق العمولة المتأثرة ويعيد احتسابها تلقائيا إذا كانت في حالات:

- `Draft`
- `Submitted`
- `Approved`

## 12. الفرق الجوهري بين Sales وBusiness Accounts

## 12.1 الفرق من حيث طبيعة العمل

| المحور | Sales Department | Business Accounts |
|---|---|---|
| طبيعة العملاء | مبيعات Home وHotspot وقنوات توزيع أو نقاط بيع | شركات، حسابات، فنادق، ISP، مشاريع، حلول |
| التركيز | حجم المبيعات، الانتشار، نقاط البيع، الهوتسبوت | العقود، التجديد، الحسابات الكبيرة، المشاريع، التحصيل |
| المستندات التشغيلية المرتبطة | Hotspot, Distributor, Booking, POS Reports | Opportunity, Survey, Quotation, Contract, Sales Order, Sales Invoice |
| حساسية العقد | مهمة في المسار العام | أعلى، لأنها تؤثر مباشرة على الفوترة والتجديد |
| حساسية التحصيل | مهم | حاسم، وتوجد عقوبات تأخير على AM |
| منطق العمولة | بسيط نسبيا: Home/Hotspot، Manager/Rest، Above Target | متعدد: Old/NewLead/Upsell، فئات مختلفة، ION roles، إضافات، مكافآت، عقوبات |

## 12.2 الفرق من حيث Service Categories

### Sales

| الفئة | Item Group |
|---|---|
| HOME | `Home` |
| HOTSPOT | `Hotspot - Sales` |

### Business Accounts

| الفئة | Item Group |
|---|---|
| DEDICATED | `Dedicated` |
| HOTEL | `Hotel` |
| ISPS | `ISPs` |
| ION_SOLUTIONS | `ION Solutions` |
| HOTSPOT | `Hotspot - BA` |
| ULTRA_MALLS | `Ultra - Malls` |

## 13. عمولات Sales Department

### 13.1 القاعدة العامة

عمولة Sales تعتمد على:

- الفواتير المسددة بالكامل داخل الربع.
- `custom_service_category` يساوي `Home` أو `Hotspot - Sales`.
- الأشخاص في `sales_team`.
- تمييز المدير من خلال `Sales Person.custom_is_sales_manager`.
- الهدف الربعي المستخرج من `Sales Person Target` و`Monthly Distribution`.

### 13.2 نسب Sales

| الفئة | النسبة العادية | نسبة Above Target |
|---|---:|---:|
| `Home` | 0.05% | 0.30% |
| `Hotspot - Sales` | 1.00% | 6.00% |

### 13.3 تقسيم العمولة في Sales

| الفئة | الحالة | حصة المدير | حصة باقي الفريق |
|---|---|---:|---:|
| Home | Normal | 30% | 70% |
| Home | Above | 30% | 70% |
| Hotspot - Sales | Normal | 30% | 70% |
| Hotspot - Sales | Above | 20% | 80% |

إذا لم يوجد Sales Manager في الفاتورة، يعاد توزيع حصة المدير على باقي الفريق.

### 13.4 لا توجد عقوبة تأخير في Sales

الكود يذكر صراحة أن Sales لا تطبق عليها عقوبات الدفع المتأخر. التأخير يؤثر فقط على توقيت دخول الفاتورة في الربع، لأنه لا توجد عمولة قبل السداد الكامل.

## 14. عمولات Business Accounts

### 14.1 القاعدة العامة

Business Accounts أكثر تعقيدا لأنها تعتمد على:

- نوع العملية: `Old` أو `NewLead` أو `Upsell`.
- فئة الخدمة.
- الأشخاص في `sales_team`.
- Department الموظف، ويجب أن يحتوي على كلمة `Business` للموظفين الداخليين.
- اعتماد المندوب الخارجي إن وجد.
- دور الشخص في ION Solutions.
- الهدف الربعي.
- السداد الكامل.
- خطة الدفع وعقوبة التأخير.

### 14.2 أنواع معاملات Business Accounts

| النوع | المعنى |
|---|---|
| `Old` | تجديد أو حساب قديم أو مبيعات مستمرة. |
| `NewLead` | عميل جديد لا توجد له فواتير سابقة قبل العملية. |
| `Upsell` | زيادة مبيعات أو بيع جديد لعميل لديه تاريخ سابق. |

ملاحظة مهمة: الكود يدعم قراءة نوع يدوي من حقول مثل `custom_ba_transaction_type` أو `custom_ba_commission_transaction_type` إذا كانت موجودة على `Sales Invoice` أو `Sales Order`. لكن الحقول المستخرجة من fixtures الحالية لا تظهر هذه الحقول. لذلك إذا أرادت الإدارة اختيار النوع يدويا في الشاشة، يجب التأكد أن الحقول مضافة على الموقع.

### 14.3 منطق اكتشاف النوع آليا

إذا لم يجد النظام نوعا يدويا:

- إذا لم يكن للعميل أي فاتورة Submitted قبل تاريخ الفاتورة، ولم يكن له فاتورة مدفوعة بالكامل قبل تاريخ السداد الحالي، تعتبر العملية `NewLead`.
- خلاف ذلك تعتبر `Upsell`.
- خيار `Old` موجود في الكود لكنه يحتاج إشارة يدوية أو Renewal flag، والكود الحالي يستدعي الكشف مع `is_renewal_flag=False`.

## 14.4 نسب Business Accounts لغير ION Solutions

| الفئة | Old | New Lead | Upsell | Above Target |
|---|---:|---:|---:|---:|
| Dedicated | 0.75% | 1.00% | 2.00% | 6.00% |
| ISPs | 0.25% | 0.125% | 0.25% | 0.50% |
| Hotel | 1.00% | 2.00% | 3.00% | 6.00% |
| Hotspot - BA | 2.00% | 2.00% | 3.00% | 6.00% |
| Ultra - Malls | 0.50% | 2.00% | 3.00% | 2.00% |

ملاحظة حسابية مهمة: في الكود، إذا كانت العملية `NewLead` لغير ION Solutions، يتم احتساب معدل الأساس كالتالي:

```text
new + upsell
```

أي أن Dedicated NewLead يأخذ 1% + 2% = 3% كأساس، ثم يمكن أن يضاف Above Target على الجزء الذي تجاوز الهدف.

## 14.5 ION Solutions

ION Solutions لا تستخدم نفس جدول النسب حسب Old/New/Upsell. تستخدم أدوارا داخل `Sales Team.custom_ion_role`:

| الدور | النسبة الأساسية |
|---|---:|
| `Account Lead Acquisition` | 1% |
| `Offer Team` | 5% |
| `Execution Team` | 5% |

وعند تجاوز الهدف يضاف:

```text
+3%
```

هذا يعني أن دور الشخص في Sales Team يجب أن يكون صحيحا. إذا كانت الفاتورة ION Solutions ولم يتم تحديد الدور، قد لا يتم احتساب العمولة لذلك الشخص.

## 14.6 إضافات ومكافآت BA

| الحقل | متى يعمل | الأثر |
|---|---|---|
| `custom_first_year_contract_invoice` | فقط `NewLead` | يضيف 1% من إجمالي الفاتورة، توزع على الموظفين غير AM/SM. |
| `custom_ba_project_acquisition_bonus` | فقط `NewLead` ولفئات `Hotspot - BA` أو `Ultra - Malls` | يضيف مكافأة ثابتة 3000، تقسم على جميع الموظفين في الفاتورة. |
| `custom_external_rep_approved` | عند وجود مندوب خارجي غير موظف | يسمح بإدخاله ضمن مستحقي العمولة. |

## 14.7 استثناءات BA

النظام يستبعد عمولة BA بالكامل إذا كان العميل عليه أحد المؤشرات التالية:

- Partnership at cost.
- ISP BW partnership أو بيع بسعر التكلفة.

المعنى:

- بعض العملاء لا يجب أن تدخل فواتيرهم في عمولة BA حتى لو كانت الفاتورة مدفوعة.
- يجب تدريب الموظفين على معرفة العملاء المستثنين قبل توقع العمولة.

## 14.8 عقوبة التأخير في BA

تطبق عقوبة التأخير على Account Managers فقط، وليس على كل الفريق.

خطة العقوبة:

| خطة الدفع | فترة السماح | الزيادة بعد السماح |
|---|---:|---:|
| Yearly | 90 يوم | كل 30 يوم |
| 6 Months | 42 يوم | كل 14 يوم |
| Quarterly | 21 يوم | كل 7 أيام |

منطق الخصم:

- إذا تم السداد داخل فترة السماح: لا يوجد خصم.
- بعد فترة السماح: خصم 50% مرة واحدة.
- ثم خصم 10% إضافية عن كل فترة cadence.
- لا ينزل العامل عن 0%.
- إذا تم تفعيل `custom_penalty_exception_approved` لا تطبق العقوبة.

مثال تدريبي:

إذا كانت الفاتورة Quarterly واستحقت في 1 يناير، فترة السماح 21 يوما. إذا تم سدادها بعد ذلك، يبدأ خصم 50% على عمولة AM، ثم 10% لكل أسبوع إضافي بعد السماح.

## 15. Sales Team وتأثيره

### 15.1 في Sales

Sales Team يستخدم لتحديد:

- من هو المدير.
- من هم باقي الفريق.
- تقسيم العمولة بين manager/rest.

النسب المدخلة في `allocated_percentage` ليست المصدر الأساسي لتقسيم Sales المخصص، لأن الكود يستخدم منطق manager/rest.

### 15.2 في Business Accounts

Business Accounts يستخدم `allocated_percentage` فعليا لتوزيع أساس العمولة بين المستحقين. إذا لم توجد نسب مفيدة، يستخدم النظام تقسيم متساو.

التدريب المهم:

- في BA يجب إدخال Sales Team بعناية.
- يجب ضبط نسبة التوزيع عند وجود أكثر من شخص.
- يجب تحديد `custom_ion_role` إذا كانت الخدمة ION Solutions.
- يجب اعتماد `custom_external_rep_approved` إذا كان هناك مندوب خارجي.

## 16. Sales Target and Commission Sheet

### 16.1 وظيفة الورقة

هذه الورقة تجمع أهداف الربع والفعلي والعمولة لكل شخص. تحتوي على `Commission Lines` لكل Sales Person.

الورقة تقرأ:

- الشركة.
- السنة المالية.
- الربع.
- الأشخاص في Commission Lines.
- أهداف الأشخاص من `Sales Person`.
- الفواتير المدفوعة بالكامل داخل الربع.
- معاملات العمولة التفصيلية.

### 16.2 الحقول الناتجة

| الحقل | المعنى |
|---|---|
| `target_value` | الهدف الربعي للشخص. |
| `actual_sales` | المبيعات الفعلية المحتسبة للشخص. |
| `achievement_pct` | نسبة الإنجاز. |
| `commission_value` | قيمة العمولة. |
| `commission_rate` | المعدل الفعلي = العمولة / المبيعات الفعلية * 100. |

### 16.3 الهدف الربعي

الهدف الربعي لا يساوي بالضرورة 25% دائما. النظام يقرأ `Monthly Distribution`. إذا كانت التوزيعة شهرية متساوية، يكون كل ربع 25%. إذا كانت مختلفة، يحسب الربع حسب أشهره.

### 16.4 حالات الورقة

إعادة الاحتساب تعمل إذا كانت الورقة في حالات:

- `Draft`
- `Submitted`
- `Approved`

عند الوصول إلى `Posted` يتم إنشاء قيد استحقاق عمولة `Journal Entry`.

## 17. Commission Transaction

بدلا من تخزين رقم نهائي فقط، النظام ينشئ معاملات عمولة تفصيلية:

- لكل فاتورة مدفوعة.
- لكل قسم.
- لكل شخص.
- لكل مكون عمولة مثل Base أو Above Target أو Penalty أو First Year Addon أو Acquisition Bonus.

الفائدة التدريبية:

- يمكن مراجعة سبب عمولة كل شخص.
- يمكن معرفة هل العمولة جاءت من أساس المبيعات أو من تجاوز الهدف أو من مكافأة.
- يمكن رؤية الخصومات كخطوط سالبة في حالة عقوبة التأخير.

## 18. الترحيل المحاسبي للعمولة

عندما تصبح ورقة العمولة `Posted`، يقوم النظام بإنشاء `Journal Entry`:

- Debit على حساب مصروف العمولة.
- Credit على حساب عمولات مستحقة الدفع.

الحسابات تؤخذ من `Commission Policy Settings`:

- `expense_account`
- `payable_account`

شروط مهمة:

- يجب أن تكون الحسابات من نفس الشركة.
- حساب المصروف يجب أن يكون Root Type = Expense.
- حساب الالتزام يجب أن يكون Root Type = Liability.
- لا يسمح بترحيل أكثر من ورقة Posted لنفس الشركة والسنة والربع.

## 19. Hotspot

### 19.1 Hotspot كمسار تشغيلي

DocType `Hotspot` يغطي بيانات مهمة من ملف `CRM_HOTSPOT 2025_v2.xlsx`، مثل:

- نوع المنتج.
- نوع Hotspot.
- نوع Reseller.
- بيانات المالك.
- المدينة والمنطقة.
- تفاصيل العنوان.
- الإحداثيات.
- بيانات الخط المجاني Username/Password/Voucher.
- المعدات Assets.
- بيانات الشبكة.
- Access Controller.
- SSID.
- VLAN.
- Tower/Sector.
- ملاحظات فنية.

### 19.2 Workflow عملي داخل Hotspot

من JavaScript الخاص بـHotspot:

- إذا كانت الحالة `Qualifying` وتوجد بيانات Proposal/Request قد ينتقل إلى `Proposed`.
- في حالة `Setup` يجب توفر عناصر مثل:
  - `stock_entry`
  - `installation_note`
  - `materials_received`
  - `service_marketed`
  - `cards_package`
  - `free_line`
  - `username`
  - `password`

عند اكتمالها يمكن أن يصبح `Active`.

### 19.3 أثر Hotspot على Sales وBA

يوجد نوعان في العمولة:

- `Hotspot - Sales`: يدخل في Sales Department.
- `Hotspot - BA`: يدخل في Business Accounts.

يجب عدم الخلط بينهما. Hotspot كعملية تشغيلية قد يستخدم في قسم المبيعات، لكن إذا كانت الفاتورة مصنفة `Hotspot - BA` ستدخل منطق BA وليس Sales.

## 20. Distributor

### 20.1 وظيفة Distributor

DocType `Distributor` يغطي الوكلاء والموزعين، ومتوافق مع ملف `CRM_AGENTS 2025_v2.xlsx`.

حقول مهمة:

- اسم الموزع.
- كود الموزع.
- Sales Partner.
- Warehouse.
- Status.
- Distributor Category.
- Voucher Distribution Type.
- بيانات الاتصال.
- المدينة.
- المنطقة/النطاق المغطى.
- الموقع الجغرافي.
- بيانات الترخيص.
- بيانات الفني.
- RMT Username/Password.
- POS Username/Password.

### 20.2 إنشاء Sales Partner تلقائيا

في hooks يوجد:

- `before_insert` لمستند Distributor.
- `after_insert` لإنشاء `Sales Partner` للموزع.

المعنى:

- الموزع يمكن أن يتحول إلى شريك مبيعات داخل ERPNext.
- هذا يدعم العمولات أو الربط التجاري مع القنوات.

## 21. Booking وRMT

DocType `Booking` يمثل تكامل أو سجل حجز مرتبط بـRMT:

- Location.
- Contract Number.
- Distributor ID.
- Client Name.
- National ID.
- Phone.
- Package ID.
- Package Price.
- Payment Method.
- Payment Status.
- Commission Percent.
- Company Share.
- Distributor Commission.
- Client Credit.
- References للفاتورة.

هذا المسار أقرب لقنوات التوزيع أو الحجوزات الخارجية، وليس نفس مسار Business Accounts التقليدي.

## 22. POS Reports

حسب مستند CRP2، الحل المعتمد لتقارير نقاط البيع:

1. استخراج تقرير POS من نظام أيون بصيغة PDF/Excel.
2. إنشاء `Sales Invoice` في ERPNext لنفس الفترة.
3. إدخال البنود كمجاميع، مثل:
   - POS Sales - Cards
   - POS Discounts
   - VAT
4. تعبئة حقول التسوية إذا كانت مضافة.
5. إرفاق التقرير داخل الفاتورة.
6. Submit للفاتورة لتصبح المرجع المالي الرسمي.

ملاحظة: لم تظهر حقول POS Settlement ضمن الحقول المستخرجة من fixtures الحالية، لذلك قد تكون مطلبا موثقا أكثر من كونها منفذة حاليا في الكود.

## 23. المقارنة العملية بين Sales وBusiness Accounts خلال المستندات

| المرحلة | Sales | Business Accounts |
|---|---|---|
| Opportunity | غالبا أبسط، وقد ترتبط بـHotspot/Distributor | تحتوي متطلبات، Survey، Scope، عقد، حسابات كبيرة |
| Quotation | عرض مباشر أو من Hotspot/خدمات | عرض فني ومالي، Dedicated/Hotel/ISP/ION |
| Sales Order | يربط الفريق والعقد عند الحاجة | العقد شرط محوري قبل الفاتورة |
| Contract | مهم لكنه قد يختلف حسب القناة | أساسي جدا للفوترة والتجديد |
| Sales Invoice | يجب اختيار `Home` أو `Hotspot - Sales` | يجب اختيار Dedicated/Hotel/ISPs/ION/Hotspot-BA/Ultra |
| Payment Entry | يؤخر توقيت العمولة حتى السداد | يؤخر العمولة وقد يسبب عقوبة AM |
| Commission | Manager/Rest + Above Target | NewLead/Upsell/Old + Role + Addons + Penalty |
| Reporting | أداء مبيعات وانتشار | احتفاظ، تجديد، تحصيل، عقود، مشاريع |

## 24. أخطاء تدريبية شائعة يجب التحذير منها

| الخطأ | أثره |
|---|---|
| إنشاء Quotation بدون ربط Opportunity | ضعف التقارير وفقدان مصدر الفرصة. |
| نسيان Items قبل قبول الفرصة | لن يتم إنشاء Quotation آليا. |
| اختيار `custom_service_category` خطأ | عمولة خاطئة أو عدم احتساب. |
| عدم ربط Contract بـSales Order | النظام يمنع Sales Invoice في المسار المرتبط. |
| العقد ليس Active | النظام يمنع الفاتورة. |
| عدم إدخال Sales Team | لا يوجد مستحقون للعمولة. |
| عدم ربط Sales Person بـEmployee/User | قد لا يستطيع النظام تحديد القسم أو Role Profile. |
| عدم تحديد ION Role | ION Solutions قد لا تحتسب للشخص. |
| إدخال مندوب خارجي دون اعتماد | لا يدخل في BA. |
| توقع العمولة قبل السداد الكامل | النظام لا يحتسبها قبل `outstanding_amount = 0`. |
| عدم ضبط Monthly Distribution | الهدف الربعي قد يظهر صفرا أو غير صحيح. |

## 25. نقاط تدريب الموظفين حسب الدور

### 25.1 مندوب المبيعات

يجب أن يعرف:

- كيف ينشئ Opportunity.
- كيف يعبئ العميل، المدينة، القطاع، المنطقة، تاريخ الإغلاق المتوقع.
- كيف يضيف Items صحيحة.
- كيف يقرأ توفر الصنف والتكلفة.
- كيف يتابع Workflow حتى عرض السعر.
- متى يستخدم Hotspot أو Distributor بدلا من Opportunity التقليدية.

### 25.2 Account Manager

يجب أن يعرف:

- أهمية `custom_account_manager`.
- أن اسمه قد ينتقل إلى Sales Team لاحقا.
- أن التحصيل المتأخر قد يخفض عمولته في BA.
- أن العقود وتجديدها ليست خطوة شكلية.
- الفرق بين NewLead وUpsell وOld.
- متى يطلب اعتماد مندوب خارجي.

### 25.3 Sales Manager

يجب أن يعرف:

- مراجعة العروض قبل الاعتماد.
- التأكد من الربحية والتكلفة.
- مراجعة العقود النشطة قبل الفوترة.
- مراقبة Pipeline والفرص المتأخرة.
- مراجعة أسباب الرفض والفقد.

### 25.4 Finance

يجب أن يعرف:

- أن Sales Invoice هي المرجع المالي الرسمي.
- أن Payment Entry يطلق إعادة احتساب العمولة.
- أن العمولة لا تكتمل إلا بعد السداد الكامل.
- مراجعة `Commission Policy Settings`.
- ترحيل ورقة العمولة إلى Journal Entry عند الاعتماد النهائي.
- متابعة عقوبات التأخير والاستثناءات.

### 25.5 الفريق الفني / Survey

يجب أن يعرف:

- تعبئة Technical Survey.
- رفع مرفقات المسح.
- تسجيل بيانات الشبكة.
- تحديث حالة التنفيذ في Hotspot أو المشاريع.
- أن البيانات الفنية تؤثر على العقد والتنفيذ والدعم لاحقا.

## 26. ما هو منفذ حاليا مقابل ما يظهر كمتطلب

| البند | الحالة من قراءة الكود والملفات |
|---|---|
| إنشاء Quotation تلقائيا عند Accepted | منفذ في الكود. |
| نقل مصدر الفرصة إلى Quotation/Sales Order/Sales Invoice | منفذ جزئيا عبر handlers/server scripts. |
| شرط العقد النشط قبل Sales Invoice | منفذ في handlers. |
| زر إنشاء Contract من Sales Order | موجود كـClient/Server Script، لكن يحتاج مراجعة حقل الربط `custom_contract`. |
| عمولات Sales | منفذة. |
| عمولات BA | منفذة بتفاصيل كثيرة. |
| Commission Transactions | منفذة. |
| ترحيل قيد استحقاق العمولة | منفذ عند Posted. |
| POS Settlement Fields | مذكورة في CRP2، لم تظهر ضمن الحقول المستخرجة. |
| WhatsApp API | مذكور كمرحلة ثانية/Integration activity، لم يظهر كتنفيذ في الكود الحالي. |
| Manual BA Transaction Type fields | مدعومة في الكود، لكن لم تظهر ضمن fixtures المستخرجة. |
| ISP ضمن `custom_opportunity_from` | مدعوم في بعض كود الربط، لكن خيارات الحقل المستخرجة لا تعرض ISP. |

## 27. سيناريو تدريبي كامل مختصر

### سيناريو Business Accounts - Dedicated New Lead

1. إنشاء Customer جديد.
2. إنشاء `Opportunity`.
3. تعبئة Account Manager والبيانات الأساسية.
4. إضافة Item من فئة `Dedicated`.
5. تحريك Workflow إلى `Accepted`.
6. يتولد `Quotation`.
7. إنشاء `Sales Order` من Quotation.
8. إنشاء أو ربط `Contract` وجعله `Active`.
9. إنشاء `Sales Invoice`.
10. اختيار `custom_service_category = Dedicated`.
11. ضبط `custom_payment_plan`.
12. إضافة Sales Team.
13. Submit للفاتورة.
14. إنشاء `Payment Entry` وسداد كامل الفاتورة.
15. إنشاء أو تحديث `Sales Target and Commission Sheet`.
16. مراجعة `Commission Transaction`.

الأثر:

- إذا كان العميل جديدا، قد تعتبر العملية `NewLead`.
- العمولة تدخل BA.
- التأخير في السداد قد يؤثر على AM.
- إذا تم تفعيل First Year أو Acquisition Bonus بشروطها، تضاف مكونات إضافية.

### سيناريو Sales - Hotspot

1. إنشاء مستند Hotspot أو Opportunity حسب المسار المستخدم.
2. تجهيز العرض والفريق.
3. إنشاء Quotation.
4. إنشاء Sales Order.
5. إنشاء Sales Invoice.
6. اختيار `custom_service_category = Hotspot - Sales`.
7. إضافة Sales Team وفيه Manager إن وجد.
8. Submit للفاتورة.
9. تحصيل كامل عبر Payment Entry.
10. تحديث ورقة العمولة.

الأثر:

- العمولة تدخل Sales.
- لا توجد عقوبة تأخير.
- يتم تقسيم العمولة بين Manager وباقي الفريق.
- Above Target له نسبة أعلى، وخاصة في Hotspot.

## 28. الرسائل الأساسية للموظفين

- لا توجد عمولة قبل السداد الكامل.
- نوع الخدمة في الفاتورة هو مفتاح العمولة.
- العقد Active شرط أساسي قبل الفاتورة في المسار المرتبط بالفرص.
- Business Accounts أكثر حساسية للتحصيل من Sales بسبب عقوبات AM.
- Sales Team ليس خانة شكلية؛ هو مصدر المستحقين للعمولة.
- Opportunity الصحيحة توفر تقارير صحيحة.
- Quotation بدون ربط صحيح يسبب ضعف تتبع لاحق.
- Monthly Distribution يحدد هدف الربع.
- المستندات التشغيلية مثل Hotspot وDistributor ليست بدائل عن الفاتورة، لكنها تغذي التشغيل والبيانات.

## 29. قائمة تحقق قبل تدريب المستخدمين

قبل التدريب العملي، تأكد من وجود:

- Item Groups المطلوبة:
  - `Home`
  - `Hotspot - Sales`
  - `Dedicated`
  - `Hotel`
  - `ISPs`
  - `ION Solutions`
  - `Hotspot - BA`
  - `Ultra - Malls`
- Items تجريبية لكل فئة.
- Monthly Distribution للسنة المالية.
- Sales Persons مربوطين بـEmployees.
- Users للـAM/SM مع Role Profile صحيح.
- Department يحتوي على `Business` لموظفي BA.
- Commission Policy Settings مضبوطة.
- Contract Template موجود.
- صلاحيات المستخدمين مضبوطة حسب الدور.
- سيناريوهات تدريب منفصلة لـSales وBA.

## 30. خلاصة تنفيذية

الفرق بين Sales وBusiness Accounts في هذا النظام ليس فرق اسم قسم فقط. الفرق يمتد إلى طريقة البيع، نوع العملاء، المستندات التشغيلية، شرط العقد، طريقة قراءة الفاتورة، منطق العمولة، أثر التحصيل، والتقارير.

قسم Sales أقرب إلى مبيعات مباشرة أو قنوات تشغيلية مثل Home وHotspot، ومنطق العمولة فيه يعتمد على التصنيف والفريق وتجاوز الهدف.

قسم Business Accounts أقرب إلى إدارة عقود وحسابات ومشاريع، ومنطق العمولة فيه يعتمد على نوع العملية، تاريخ العميل، التحصيل، خطة الدفع، أدوار الفريق، الاستثناءات، والمكافآت.

لذلك عند تدريب الموظفين يجب عدم الاكتفاء بشرح الأزرار. يجب شرح أثر كل إدخال على المراحل التالية، لأن النظام يحسب ويربط تلقائيا اعتمادا على البيانات التي يدخلها المستخدم في البداية.
