# Backend And Deployment Runbook After Audit

Last updated: 2026-07-08

This file is for the backend / operations owner who will run the project locally or deploy it after the audit fixes.

## What Changed

The audit changes focused on making local/cloud configuration predictable, fixing QR-to-frontend delivery, hardening auth, and reducing data integrity risks.

Main affected areas:

- ASP.NET backend now defaults locally to port `5005` when Azure does not provide `PORT`.
- Angular services now read backend URLs from Angular environment files instead of hardcoded Azure URLs.
- Python camera backend now reads API URL, camera secret, and source from environment variables / `.env`.
- MQTT broker settings are no longer hardcoded in the service. They come from .NET configuration.
- MQTT QR/product payload parsing is more flexible and forwards product numbers to SignalR clients.
- MQTT sensor messages no longer reset camera stats to zero.
- Auth sessions now expire, and `/api/auth/me` / `/api/auth/logout` were added.
- Default admin seeding no longer uses a public hardcoded password. It requires configuration.
- Product creation/update now rejects duplicate product codes and invalid negative weights.
- Product create/update/delete now require `Manager` or `Admin`.
- `/health` and `/health/live` are liveness checks. `/health/ready` checks database readiness.
- `appsettings.json` is sanitized. Real secrets must be supplied through environment variables, user-secrets, Azure App Settings, or a secure secret store.

## Important Runtime Impact

The backend can fail or partially disable services if required configuration is missing:

- `ConnectionStrings:DefaultConnection` is required. The .NET API will not start without it.
- `Camera:SecretKey` or `CAMERA_SECRET` is required outside `Development`.
- `Mqtt:Host` is optional for local/dev. If empty, MQTT is disabled with a warning instead of crashing the app.
- `DefaultAdmin:Username` and `DefaultAdmin:Password` are optional. If missing, admin seeding is skipped.
- The product-code unique index is defined in the EF model, but a migration still needs to be generated/applied before it is enforced in the database.

## Required Local Tooling

Install these before validating the full stack:

- `.NET 8 SDK`
- Node.js LTS and npm
- Python 3.10 or 3.11 recommended for ML compatibility
- MySQL-compatible database reachable by the .NET backend

Check the .NET SDK:

```powershell
dotnet --list-sdks
```

## Backend Configuration

Use `IoTBackend/appsettings.Development.example.json` as a template for local backend settings.

Do not commit real credentials. Prefer `appsettings.Development.json`, .NET user-secrets, or real environment variables.

Important .NET configuration keys:

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

Example local values:

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

## Python Camera Configuration

The Python camera backend reads `.env` from the project root.

Use `.env.example` as a template:

```text
API_URL=http://localhost:5005/api/camera/upload
CAMERA_SECRET=CHANGE_THIS_CAMERA_SECRET
CAMERA_SOURCE=0
```

`CAMERA_SECRET` must match the .NET backend `Camera:SecretKey`.

If these do not match, the Python backend may send frames successfully from its side, but the .NET backend will reject them with `401 Unauthorized`.

## Frontend Configuration

Local Angular dev should call the local .NET backend:

```ts
apiUrl: 'http://localhost:5005'
hubUrl: 'http://localhost:5005/hubs/factory'
```

This is currently set in:

```text
frontend/src/environments/environment.development.ts
```

For production, make sure the Angular production environment points to the deployed .NET backend and SignalR hub.

## Local Run Order

Start the system in this order when testing integration:

1. Start MySQL and confirm the connection string works.
2. Start the .NET backend:

```powershell
dotnet restore IoTBackend\IoTBackend.csproj
dotnet build IoTBackend\IoTBackend.csproj
dotnet run --project IoTBackend\IoTBackend.csproj
```

3. Confirm backend health:

```text
http://localhost:5005/health
http://localhost:5005/health/live
http://localhost:5005/health/ready
```

4. Start Angular:

```powershell
cd frontend
npm install
npm run start
```

5. Start Python camera backend:

```powershell
python backend\app.py
```

6. Start the AI anomaly monitor only if MQTT/email environment variables are configured:

```powershell
python scripts\ai_dashboard_monitor.py
```

## Database Migration Required

The EF model now defines a unique index on `Product.ProductNumber`.

Before deploying this to a real database:

1. Check for duplicate product codes in the current DB.
2. Clean duplicates manually if any exist.
3. Generate a migration after `.NET 8 SDK` is available.
4. Apply the migration in a controlled environment.

Suggested migration command:

```powershell
dotnet ef migrations add EnforceUniqueProductNumber --project IoTBackend\IoTBackend.csproj
dotnet ef database update --project IoTBackend\IoTBackend.csproj
```

If `dotnet ef` is missing:

```powershell
dotnet tool install --global dotnet-ef
```

Do not apply the unique index to production before checking for duplicate `ProductNumber` values.

## Azure App Settings Checklist

Before deploying to Azure, configure these in App Service settings or a secure secret store:

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

Notes:

- Azure usually provides `PORT`; locally the backend defaults to `5005`.
- If `Mqtt__Host` is empty, MQTT will not run.
- If `DefaultAdmin__Username` or `DefaultAdmin__Password` is missing, no admin user will be seeded.
- Rotate any credentials that were previously committed before relying on this deployment.

## QR / MQTT / SignalR Flow

Expected QR flow after the audit fixes:

1. ESP32 or camera bridge publishes a QR/product code to MQTT.
2. .NET `MqttService` receives it.
3. Backend logs something like:

```text
QR Code forwarded to SignalR clients: PRODUCT_CODE
```

4. Backend sends SignalR event:

```text
ReceiveProductNumberUpdate
```

5. Angular `SensorService` receives it and updates `productNumber`.

Supported QR payload examples:

```json
{ "qr": "P-1001" }
{ "productNumber": "P-1001" }
{ "product_number": "P-1001" }
{ "code": "P-1001" }
```

Also supported:

- Raw payload on a QR/product/barcode topic.
- JSON object with `value` on a QR/product/barcode topic.

If QR appears in Azure logs but not in the frontend:

- Confirm the frontend `hubUrl` points to the correct deployed backend `/hubs/factory`.
- Confirm CORS includes the frontend origin.
- Check browser console for SignalR errors.
- Check backend logs for `QR Code forwarded to SignalR clients`.
- Confirm the frontend is listening for `ReceiveProductNumberUpdate`.
- Confirm the user is looking at the same backend instance that receives MQTT.

## Auth Changes Operators Need To Know

Login response now includes `expiresAtUtc`.

Sessions are still in-memory, but now expire after `Auth:SessionMinutes`.

Operational impact:

- Restarting the .NET backend logs out all users.
- Scaling to multiple backend instances can cause inconsistent sessions unless sticky sessions are used.
- For production-grade multi-instance hosting, replace this with JWT or DB/Redis-backed sessions.

Admin user behavior:

- Admin seeding only happens when both `DefaultAdmin:Username` and `DefaultAdmin:Password` are configured.
- No public default admin password is created anymore.

## Product API Changes

Product create/update now:

- Trim product code.
- Reject empty product code.
- Reject negative weight.
- Reject duplicate product code.
- Require `Manager` or `Admin`.

Frontend routes and buttons were updated to match these permissions.

Product analytics now returns detailed scan rows in addition to aggregate values:

```text
GET /api/products/analytics/{productNumber}
```

The response includes `scans`, where each row contains the scan id, sequence, actual weight, scan time, difference from ideal weight, and tolerance status.

Managers/Admins can reset scan history for one product without deleting the product:

```text
DELETE /api/products/analytics/{productNumber}/scans
```

Operational note: reset deletes rows from `ProductScans` for that product. Export or archive data first if the scan history must be preserved.

## Health Endpoints

Use these endpoints depending on what you need to check:

```text
/health       process is alive
/health/live  process is alive
/health/ready database is reachable
```

Use `/health/live` for basic App Service liveness.

Use `/health/ready` when you want to know whether the app can reach the database.

## Verification Checklist

Run these before handing the build to deployment:

```powershell
python -m compileall -q backend scripts train.py
python -m pip check
cd frontend
npm run build
cd ..
dotnet build IoTBackend\IoTBackend.csproj
```

Then verify manually:

- Backend starts on `http://localhost:5005`.
- `/health` returns alive.
- `/health/ready` returns database connected.
- Angular can login through local backend.
- SignalR connects to `/hubs/factory`.
- Python camera upload is accepted by .NET.
- MQTT QR updates appear in Angular.
- Product scans create analytics data.
- Manager/Admin can add products.
- Normal users cannot add/update/delete products.

## Known Pending Work

These items are intentionally not fully completed yet:

- Generate and apply EF migration for unique `ProductNumber`.
- Add a real `ProductScan.ProductId` foreign key and backfill old scan rows.
- Replace in-memory sessions with JWT or persistent sessions for multi-instance production.
- Make .NET camera controls actually control the Python camera process.
- Coordinate a JSON MQTT command schema with ESP32 firmware.
- Clean or remove legacy Flask/static UI files if they are not used.
