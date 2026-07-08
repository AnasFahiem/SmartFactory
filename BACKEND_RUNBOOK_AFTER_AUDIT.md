# دليل تشغيل الباك إند والنشر بعد الأودت

آخر تحديث: 2026-07-08

الملف ده معمول للشخص المسؤول عن الباك إند وتشغيل الموقع، سواء هيشغله لوكال أو هيعمله deploy على Azure بعد تعديلات الأودت.

## إيه اللي اتغير؟

تعديلات الأودت كانت مركزة على إن إعدادات اللوكال والكلاود تبقى واضحة، وإن بيانات الـ QR تظهر في الفرونت، وإن الـ auth يبقى أأمن، وإن بيانات المنتجات والسكانات تبقى أسهل في التتبع.

أهم الحاجات اللي اتغيرت:

- الـ ASP.NET backend بقى يشتغل لوكال على port `5005` لو Azure مبعتش `PORT`.
- خدمات Angular بقت تقرأ روابط الباك إند من environment files بدل hardcoded Azure URLs.
- Python camera backend بقى يقرأ API URL والـ camera secret والـ camera source من environment variables أو `.env`.
- إعدادات MQTT مبقتش hardcoded جوه service. بقت من .NET configuration.
- قراءة QR/product من MQTT بقت أوسع وبتقبل payloads بأشكال أكتر.
- أي QR/product update بيتبعت للفرونت عن طريق SignalR.
- رسائل MQTT مبقتش تصفر camera stats بالغلط.
- الـ auth sessions بقى ليها expiry، واتضاف `/api/auth/me` و`/api/auth/logout`.
- default admin مبقاش بيتعمل بكلمة سر public hardcoded. لازم يتظبط من configuration.
- إنشاء أو تعديل المنتجات بقى يمنع product codes المكررة والوزن السالب.
- add/update/delete للمنتجات مسموح لـ `Manager` أو `Admin` فقط.
- صفحة analytics بقت تعرض كل scan لوحدها مع المتوسط العام.
- اتضاف reset لسكانات منتج معين بدون حذف المنتج.
- `/health` و`/health/live` بقوا liveness checks، و`/health/ready` بيفحص جاهزية قاعدة البيانات.
- `appsettings.json` اتنضف من الأسرار. أي secrets حقيقية لازم تتحط في environment variables أو Azure App Settings أو secret store.

## تأثير التعديلات على التشغيل

في شوية إعدادات لازم تبقى موجودة، وإلا الباك إند ممكن يفشل أو يشغل جزء ويعطل جزء:

- `ConnectionStrings:DefaultConnection` إجباري. من غيره .NET API مش هيبدأ.
- `Camera:SecretKey` أو `CAMERA_SECRET` إجباري خارج `Development`.
- `Mqtt:Host` اختياري في اللوكال. لو فاضي، MQTT هيتعطل برسالة warning بدل ما يوقع التطبيق كله.
- `DefaultAdmin:Username` و`DefaultAdmin:Password` اختياريين. لو مش موجودين، إنشاء admin افتراضي هيتعمله skip.
- unique index بتاع `Product.ProductNumber` متعرف في EF model، لكن محتاج migration تتعمل وتتطبق على قاعدة البيانات عشان يتفعل فعليا.

## الأدوات المطلوبة لوكال

قبل ما تعمل validation كامل للسيستم، اتأكد إن دول موجودين:

- `.NET 8 SDK`
- Node.js LTS و npm
- Python 3.10 أو 3.11 أفضل للـ ML compatibility
- MySQL-compatible database والـ .NET backend يقدر يوصلها

اتأكد من .NET SDK:

```powershell
dotnet --list-sdks
```

## إعدادات الباك إند

استخدم الملف ده كـ template لإعدادات اللوكال:

```text
IoTBackend/appsettings.Development.example.json
```

متحطش credentials حقيقية في git. الأفضل تستخدم:

- `appsettings.Development.json`
- .NET user-secrets
- environment variables
- Azure App Settings

أهم .NET configuration keys:

```text
ConnectionStrings__DefaultConnection
DefaultAdmin__Username
DefaultAdmin__Password
Camera__SecretKey
Auth__SessionMinutes
Cors__AllowedOrigins__0
Cors__AllowedOrigins__1
Mqtt__Host
Mqtt__Port
Mqtt__UseTls
Mqtt__ClientId
Mqtt__CommandTopic
Mqtt__WeightRequestIntervalSeconds
Mqtt__Username
Mqtt__Password
Mqtt__Topics__0
```

مثال قيم لوكال:

```powershell
$env:ConnectionStrings__DefaultConnection="Server=localhost;Database=IotDb;User=root;Password=YOUR_LOCAL_PASSWORD;"
$env:DefaultAdmin__Username="admin"
$env:DefaultAdmin__Password="CHANGE_THIS_ADMIN_PASSWORD"
$env:Camera__SecretKey="CHANGE_THIS_CAMERA_SECRET"
$env:Auth__SessionMinutes="480"
$env:Cors__AllowedOrigins__0="http://localhost:4200"
$env:Mqtt__Host="YOUR_HIVEMQ_HOST"
$env:Mqtt__Port="8883"
$env:Mqtt__UseTls="true"
$env:Mqtt__Username="YOUR_MQTT_USER"
$env:Mqtt__Password="YOUR_MQTT_PASSWORD"
$env:Mqtt__Topics__0="factory/#"
```

## إعدادات Python Camera

Python camera backend بيقرأ `.env` من root بتاع المشروع.

استخدم `.env.example` كـ template:

```text
API_URL=http://localhost:5005/api/camera/upload
CAMERA_SECRET=CHANGE_THIS_CAMERA_SECRET
CAMERA_SOURCE=0
```

مهم جدا:

`CAMERA_SECRET` لازم يساوي نفس قيمة .NET backend `Camera:SecretKey`.

لو القيمتين مختلفين، Python ممكن يبعت frames عادي من ناحيته، لكن .NET backend هيرفضها بـ `401 Unauthorized`.

## إعدادات الفرونت

في اللوكال، Angular لازم يكلم .NET backend المحلي:

```ts
apiUrl: 'http://localhost:5005'
hubUrl: 'http://localhost:5005/hubs/factory'
```

ده موجود هنا:

```text
frontend/src/environments/environment.development.ts
```

في production، Angular بيستخدم:

```text
frontend/src/environments/environment.ts
```

اتأكد إن الملف ده شااور على Azure backend الصحيح والـ SignalR hub الصحيح قبل ما تعمل build وتنشر.

ملاحظة مهمة:

- `npm run build` بيستخدم production config وAzure URL.
- `ng serve` أو development build بيستخدم `environment.development.ts` وlocalhost.

## ترتيب التشغيل لوكال

لما تحب تختبر integration كامل، شغل بالترتيب ده:

1. شغل MySQL واتأكد إن connection string شغال.
2. شغل .NET backend:

```powershell
dotnet restore IoTBackend\IoTBackend.csproj
dotnet build IoTBackend\IoTBackend.csproj
dotnet run --project IoTBackend\IoTBackend.csproj
```

3. اتأكد من health endpoints:

```text
http://localhost:5005/health
http://localhost:5005/health/live
http://localhost:5005/health/ready
```

4. شغل Angular:

```powershell
cd frontend
npm install
npm run start
```

5. شغل Python camera backend:

```powershell
python backend\app.py
```

6. شغل AI anomaly monitor بس لو MQTT/email env vars متظبطة:

```powershell
python scripts\ai_dashboard_monitor.py
```

## Migration المطلوبة لقاعدة البيانات

EF model دلوقتي معرف unique index على:

```text
Product.ProductNumber
```

قبل ما تطبق ده على database حقيقية:

1. راجع هل فيه duplicate product codes موجودة حاليا.
2. لو فيه duplicates، نضفها يدوي قبل migration.
3. اعمل migration بعد ما `.NET 8 SDK` يبقى متاح.
4. طبق migration على environment متحكم فيه الأول.

أوامر migration المقترحة:

```powershell
dotnet ef migrations add EnforceUniqueProductNumber --project IoTBackend\IoTBackend.csproj
dotnet ef database update --project IoTBackend\IoTBackend.csproj
```

لو `dotnet ef` مش موجود:

```powershell
dotnet tool install --global dotnet-ef
```

مهم:

متطبقش unique index على production قبل ما تتأكد إن مفيش duplicate `ProductNumber` values.

## Azure App Settings Checklist

قبل deploy على Azure، حط القيم دي في App Service settings أو secret store آمن:

```text
ConnectionStrings__DefaultConnection
Camera__SecretKey
Auth__SessionMinutes
Cors__AllowedOrigins__0
Mqtt__Host
Mqtt__Port
Mqtt__UseTls
Mqtt__ClientId
Mqtt__CommandTopic
Mqtt__WeightRequestIntervalSeconds
Mqtt__Username
Mqtt__Password
Mqtt__Topics__0
DefaultAdmin__Username
DefaultAdmin__Password
```

ملاحظات:

- Azure غالبا بيوفر `PORT`، أما لوكال فالـ backend default على `5005`.
- لو `Mqtt__Host` فاضي، MQTT مش هيشتغل.
- لو `DefaultAdmin__Username` أو `DefaultAdmin__Password` مش موجودين، مفيش admin user هيتعمله seed.
- أي credentials كانت committed قبل كده لازم تتعملها rotation قبل الاعتماد على deployment.

## مسار QR / MQTT / SignalR

المسار المتوقع بعد تعديلات الأودت:

1. ESP32 أو camera bridge ينشر QR/product code على MQTT.
2. .NET `MqttService` يستقبل الرسالة.
3. الباك إند يطبع log شبه ده:

```text
QR Code forwarded to SignalR clients: PRODUCT_CODE
```

4. الباك إند يبعت SignalR event:

```text
ReceiveProductNumberUpdate
```

5. Angular `SensorService` يستقبل event ويحدث `productNumber`.

أمثلة QR payloads مدعومة:

```json
{ "qr": "P-1001" }
{ "productNumber": "P-1001" }
{ "product_number": "P-1001" }
{ "code": "P-1001" }
```

كمان مدعوم:

- raw payload على topic فيه QR/product/barcode.
- JSON object فيه `value` على topic فيه QR/product/barcode.

لو QR ظاهر في Azure logs بس مش ظاهر في الفرونت:

- اتأكد إن frontend `hubUrl` شااور على `/hubs/factory` في نفس backend المنشور.
- اتأكد إن CORS فيه frontend origin.
- افتح browser console وشوف SignalR errors.
- راجع backend logs ودور على `QR Code forwarded to SignalR clients`.
- اتأكد إن الفرونت بيسمع `ReceiveProductNumberUpdate`.
- اتأكد إن المستخدم فاتح نفس backend instance اللي بيستقبل MQTT.

## تغييرات الـ Auth

login response دلوقتي بيرجع `expiresAtUtc`.

الـ sessions لسه in-memory، بس بقت بتنتهي بعد `Auth:SessionMinutes`.

تأثير ده على التشغيل:

- Restart للـ .NET backend هيعمل logout لكل المستخدمين.
- لو Azure شغال بأكتر من backend instance، sessions ممكن تبقى inconsistent إلا لو فيه sticky sessions.
- للإنتاج الحقيقي على أكتر من instance، الأفضل JWT أو DB/Redis-backed sessions.

سلوك admin user:

- admin seeding بيحصل بس لو `DefaultAdmin:Username` و`DefaultAdmin:Password` متظبطين.
- مفيش public default admin password بيتعمل خلاص.

## تغييرات Product API

إنشاء أو تعديل المنتج دلوقتي بيعمل الآتي:

- trim للـ product code.
- يرفض product code الفاضي.
- يرفض الوزن السالب.
- يرفض duplicate product code.
- يتطلب `Manager` أو `Admin`.

الفرونت routes والأزرار اتظبطت على نفس الصلاحيات.

Product analytics دلوقتي بترجع rows تفصيلية لكل scan بجانب القيم المجمعة:

```text
GET /api/products/analytics/{productNumber}
```

الـ response فيه `scans`، وكل scan فيها:

- scan id
- sequence
- actual weight
- scan time
- الفرق عن ideal weight
- tolerance status

Managers/Admins يقدروا يعملوا reset لسكانات منتج واحد من غير حذف المنتج نفسه:

```text
DELETE /api/products/analytics/{productNumber}/scans
```

ملاحظة تشغيلية:

reset بيمسح rows من `ProductScans` للمنتج ده. لو scan history لازم يفضل محفوظ، اعمل export أو archive قبل reset.

## Health Endpoints

استخدم endpoint حسب اللي عايز تتأكد منه:

```text
/health       process is alive
/health/live  process is alive
/health/ready database is reachable
```

استخدم `/health/live` كـ liveness check بسيط لـ App Service.

استخدم `/health/ready` لما تحب تتأكد إن التطبيق قادر يوصل لقاعدة البيانات.

## Checklist قبل التسليم أو النشر

شغل دول قبل ما تسلم build للـ deployment:

```powershell
python -m compileall -q backend scripts train.py
python -m pip check
cd frontend
npm run build
cd ..
dotnet build IoTBackend\IoTBackend.csproj
```

وبعدين اختبر يدوي:

- الباك إند بدأ على `http://localhost:5005`.
- `/health` بيرجع alive.
- `/health/ready` بيرجع database connected.
- Angular يقدر يعمل login من خلال backend.
- SignalR بيتصل بـ `/hubs/factory`.
- Python camera upload مقبول من .NET.
- MQTT QR updates بتظهر في Angular.
- product scans بتتسجل وتظهر في analytics.
- Manager/Admin يقدر يضيف منتجات.
- Manager/Admin يقدر يعمل reset scans.
- المستخدم العادي ميقدرش add/update/delete products ولا reset scans.

## شغل لسه متبقي

الحاجات دي لسه intentionally مش مخلصة بالكامل:

- Generate/apply EF migration للـ unique `ProductNumber`.
- إضافة `ProductScan.ProductId` كـ foreign key حقيقي وعمل backfill للسكانات القديمة.
- استبدال in-memory sessions بـ JWT أو persistent sessions لو الإنتاج multi-instance.
- تخلي .NET camera controls تتحكم فعلا في Python camera process.
- الاتفاق مع ESP32 firmware على JSON MQTT command schema واضح.
- تنظيف أو حذف legacy Flask/static UI files لو مش مستخدمة.
