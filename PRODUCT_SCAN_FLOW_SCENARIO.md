# سيناريو تشغيل دورة المنتج بعد تعديلات الأودت

آخر تحديث: 2026-07-08

هذا الملف موجه لمسؤول الـ backend والتشغيل، وهدفه شرح دورة المنتج خطوة بخطوة من أول دخوله خط الإنتاج لحد ظهوره في الموقع، مع توضيح التعديلات الجديدة وتأثيرها على التشغيل المحلي وAzure.

## ملخص التعديلات الجديدة

تمت إضافة وتحسين الآتي:

- صفحة Product Analytics تعرض الآن كل scan منفصل ببياناته.
- صفحة Product Analytics ما زالت تعرض المتوسط العام `Average Actual Weight` وعدد السكانات.
- كل scan يظهر معه:
  - رقم ترتيبي للـ scan.
  - وقت تسجيله.
  - الوزن الفعلي.
  - الفرق عن الوزن المثالي.
  - حالة scan: داخل النطاق أو خارج النطاق.
- تم إضافة زر `Reset Scans` لمسح سكانات منتج محدد.
- زر reset يظهر فقط لمستخدم دوره `Manager` أو `Admin`.
- الـ API أضاف endpoint لمسح scans الخاصة بمنتج بدون حذف المنتج نفسه.

## توضيح مهم بخصوص API URL

في تعديلات الأودت تم نقل روابط الـ API من hardcoded services إلى ملفات environment.

هذا لا يعني أن نسخة Azure ستستخدم localhost.

الوضع الحالي:

- `frontend/src/environments/environment.ts`
  - يستخدم Azure backend URL.
  - هذا هو الملف المستخدم في production build.
- `frontend/src/environments/environment.development.ts`
  - يستخدم `http://localhost:5005`.
  - هذا الملف يستخدم فقط في development mode.

بالتالي:

- عند تشغيل `npm run build` يتم استخدام production config وAzure URL.
- عند تشغيل Angular محليا بـ `npm start` أو `ng serve` يتم استخدام localhost.

إذا تغير رابط الـ backend على Azure، يجب تعديل `frontend/src/environments/environment.ts` قبل بناء ورفع الفرونت.

## دورة المنتج خطوة بخطوة

### 1. تسجيل المنتج في النظام

المسؤول أو المدير يضيف المنتج من الموقع.

المطلوب:

- Product Code مثل `SP-A1-001`.
- Ideal Weight بالجرام.

ما يحدث في الـ backend:

- API يتحقق أن الكود غير فارغ.
- API يتحقق أن الوزن ليس سالبا.
- API يمنع تكرار نفس Product Code.
- العملية مسموحة فقط لـ `Manager` أو `Admin`.

نقطة فشل محتملة:

- لو المنتج غير مسجل، سكان QR لاحق لن يتم ربطه بوزن مثالي ولن يظهر في analytics بشكل صحيح.

### 2. دخول المنتج على الخط وقراءة QR

عند دخول المنتج، الجهاز أو الكاميرا يقرأ QR أو product code.

مصدر القراءة المتوقع:

- MQTT topic خاص بـ QR/product/barcode.
- أو JSON payload يحتوي على `qr`, `productNumber`, `product_number`, `product`, `code`, أو `barcode`.

ما يحدث في الـ backend:

- `MqttService` يستقبل الرسالة.
- يستخرج product code.
- يخزن آخر QR تم استقباله مؤقتا.
- يرسل SignalR event باسم `ReceiveProductNumberUpdate`.

ما يحدث في الفرونت:

- `SensorService` يستقبل `ReceiveProductNumberUpdate`.
- Dashboard يعرض Product Number الحالي.
- عند الضغط على product card يتم فتح صفحة analytics للمنتج.

نقاط فشل محتملة:

- MQTT broker غير متصل.
- `Mqtt:Host` غير مضبوط، وفي هذه الحالة MQTT يتعطل برسالة warning.
- topic غير داخل `Mqtt:Topics`.
- payload لا يحتوي على أي field معروف للكود.
- SignalR hub URL غير صحيح.
- CORS لا يسمح بدومين الفرونت.

### 3. طلب الوزن من الجهاز

بعد وصول QR:

- الـ backend يبدأ إرسال `GET_WEIGHT` على topic الأوامر.
- الفترة بين الطلبات مضبوطة من `Mqtt:WeightRequestIntervalSeconds`.
- الافتراضي الحالي 6 ثواني.

نقاط فشل محتملة:

- ESP32 لا يستمع على نفس command topic.
- `Mqtt:CommandTopic` غير متطابق بين backend والـ firmware.
- الجهاز لا يرد بوزن.

### 4. استقبال الوزن وتسجيل scan

عند وصول وزن المنتج:

- `MqttService` يوقف طلبات الوزن المتكررة.
- يرسل SignalR event باسم `ReceiveWeightUpdate`.
- يبحث عن المنتج باستخدام آخر QR تم استقباله.
- لو المنتج موجود، ينشئ صف جديد في `ProductScans`.
- الصف يحتوي على:
  - `ProductNumber`
  - `ActualWeight`
  - `ScanTime`

بعد التسجيل:

- يتم مقارنة الوزن الفعلي بالوزن المثالي.
- لو الفرق داخل 10 بالمئة، يرسل backend نتيجة قبول.
- لو خارج 10 بالمئة، يرسل backend نتيجة رفض أو warning للجهاز حسب البروتوكول الحالي.

نقاط فشل محتملة:

- وصول وزن قبل وصول QR.
- وصول QR جديد قبل وزن المنتج السابق.
- Product Code غير موجود في جدول Products.
- اختلاف formatting بين QR الموجود في DB والـ QR القادم من الجهاز.
- قاعدة البيانات غير متاحة.

### 5. ظهور البيانات في الموقع

في Dashboard:

- يظهر product number الحالي.
- يظهر الوزن الحالي.
- يظهر status الاتصال.

في صفحة Product Analytics:

- يظهر Ideal Weight.
- يظهر Average Actual Weight.
- يظهر Total Scans.
- يظهر Variance العام.
- يظهر جدول لكل scan منفصل:
  - Scan number.
  - Scan time.
  - Actual weight.
  - Difference from ideal.
  - Status.

هذا يساعد في tracing لأن المشكلة لم تعد تظهر كمتوسط فقط. يمكن معرفة أي scan بالتحديد خرجت عن النطاق.

### 6. Reset Scans

زر `Reset Scans` يمسح جميع سكانات المنتج الحالي فقط.

ما يحدث:

- API endpoint يحذف rows من `ProductScans` حيث `ProductNumber` يساوي المنتج المفتوح.
- المنتج نفسه لا يتم حذفه.
- ideal weight لا يتغير.
- بعد reset، `Total Scans` يرجع 0 والمتوسط يصبح `No Scans`.

الصلاحيات:

- مسموح فقط لـ `Manager` أو `Admin`.
- المستخدم العادي لا يرى الزر ولا يستطيع استخدام endpoint.

تحذير تشغيلي:

- Reset يمسح history الخاص بهذا المنتج من قاعدة البيانات.
- لو مطلوب الاحتفاظ بالأثر التشغيلي الكامل، يجب تصدير البيانات أو إضافة archive قبل استخدام reset في الإنتاج.

## هل تعديلات الأودت تؤثر بالسلب على العملية؟

التعديلات لا يفترض أن تؤثر بالسلب إذا تم ضبط الإعدادات بشكل صحيح.

لكن توجد تغييرات تشغيلية يجب الانتباه لها:

### 1. نقل الروابط إلى environment

الأثر:

- إيجابي. يمنع خلط local وAzure.

المطلوب:

- قبل production build تأكد أن `environment.ts` يحتوي على Azure backend الصحيح.
- قبل local dev تأكد أن `environment.development.ts` يحتوي على `localhost:5005`.

### 2. تنظيف الأسرار من الكود

الأثر:

- إيجابي أمنيا.

المطلوب:

- Azure App Settings يجب أن تحتوي على connection string وMQTT وCamera secret.
- بدون هذه القيم قد يبدأ التطبيق ناقص الخدمات أو يفشل عند الاتصال بقاعدة البيانات.

### 3. MQTT أصبح configurable

الأثر:

- إيجابي، لكن يتطلب ضبط صحيح.

المطلوب:

- `Mqtt:Host`
- `Mqtt:Username`
- `Mqtt:Password`
- `Mqtt:Topics`
- `Mqtt:CommandTopic`

لو `Mqtt:Host` فارغ، MQTT لن يعمل ولن تصل QR/weight events.

### 4. SignalR start أصبح idempotent

الأثر:

- إيجابي. يقلل connections مكررة.

### 5. منع تكرار Product Code

الأثر:

- إيجابي للـ tracing.

المطلوب:

- تنظيف أي duplicates قديمة قبل تطبيق migration الخاص بالـ unique index.

### 6. Sessions أصبحت تنتهي

الأثر:

- إيجابي أمنيا.

ملاحظة:

- restart للـ backend سيخرج المستخدمين لأن sessions ما زالت in-memory.
- لو Azure شغال بأكثر من instance، يفضل استخدام JWT أو Redis/DB sessions.

### 7. Camera secret أصبح مطلوبا خارج Development

الأثر:

- إيجابي أمنيا.

المطلوب:

- `Camera__SecretKey` في Azure يجب أن يطابق `CAMERA_SECRET` في Python camera backend.

## Checklist للمسؤول قبل تشغيل Azure

تأكد من الآتي:

- `frontend/src/environments/environment.ts` يشير إلى backend Azure الصحيح.
- Azure App Settings تحتوي على:
  - `ConnectionStrings__DefaultConnection`
  - `Camera__SecretKey`
  - `Auth__SessionMinutes`
  - `Cors__AllowedOrigins__0`
  - `Mqtt__Host`
  - `Mqtt__Port`
  - `Mqtt__UseTls`
  - `Mqtt__ClientId`
  - `Mqtt__CommandTopic`
  - `Mqtt__WeightRequestIntervalSeconds`
  - `Mqtt__Username`
  - `Mqtt__Password`
  - `Mqtt__Topics__0`
- Frontend origin موجود في CORS.
- MQTT topic القادم من الجهاز داخل `Mqtt__Topics__0`.
- `Mqtt__CommandTopic` مطابق للـ ESP32 firmware.
- Python camera `CAMERA_SECRET` مطابق لـ Azure `Camera__SecretKey`.
- تم اختبار `/health/live` و`/health/ready`.
- تم اختبار QR scan من الجهاز ومتابعة logs.
- تم فتح Product Analytics والتأكد أن scan ظهر في الجدول.
- تم تجربة reset scans بحساب Manager/Admin فقط.

## اختبار سريع للسيناريو

1. سجل دخول كـ Admin أو Manager.
2. أضف Product Code وIdeal Weight.
3. اعمل scan للـ QR بنفس Product Code.
4. تأكد أن Dashboard عرض Product Number.
5. انتظر قراءة الوزن.
6. افتح Product Analytics.
7. تأكد أن:
   - Total Scans زاد.
   - Average Actual Weight اتحدث.
   - scan جديد ظهر في الجدول.
   - status صحيح حسب الفرق عن ideal.
8. اضغط Reset Scans.
9. تأكد أن Total Scans رجع 0 وأن الجدول أصبح فارغا.

