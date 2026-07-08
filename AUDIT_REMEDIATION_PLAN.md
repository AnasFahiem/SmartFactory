# SmartFactory Audit And Remediation Plan

Last updated: 2026-07-08

## Current Scan Status

- Git working tree status now contains intentional local remediation changes only. Nothing has been committed, pushed, or deployed.
- The current project tree contains additional auth, user, product, and analytics files compared with the earlier audit surface.
- The Spec Kit instruction in `AGENTS.md` says to read the current plan, but no `specs/**/plan.md` or `.specify/feature.json` exists. Treat this as project governance drift.

## Main Runtime Surfaces

- Python vision backend: `backend/app.py`, `backend/camera.py`, `backend/detector.py`
- ASP.NET IoT/API backend: `IoTBackend/`
- Angular frontend: `frontend/`
- AI anomaly monitor: `scripts/ai_dashboard_monitor.py`
- Training/dataset utilities: `train.py`, `scripts/*.py`

## Old Audit Findings Still Relevant

### Critical

1. Local end-to-end startup is inconsistent.
   - `IoTBackend/Program.cs` defaults to port `8080`.
   - `start_app.bat`, `SETUP_GUIDE.md`, and Angular dev environment expect `localhost:5005`.
   - `backend/app.py`, `frontend/src/app/services/sensor.service.ts`, and now `frontend/src/app/services/auth.service.ts` hardcode Azure URLs.
   - Fix: centralize API and hub URLs in environment/config files, default local .NET to port `5005`, and pass Python `API_URL` via environment.
   - Local status on 2026-07-08: fixed locally for Angular service URLs, Python camera API/source/secret, and .NET default port.

2. Secrets are committed in source.
   - Examples:
     - `backend/app.py`: camera RTSP credentials and shared secret.
     - `IoTBackend/Program.cs`: fallback MySQL password.
     - `IoTBackend/appsettings.json`: MySQL and MQTT credentials.
     - `IoTBackend/Services/MqttService.cs`: MQTT credentials.
     - `scripts/ai_dashboard_monitor.py`: MQTT and email credentials.
   - Fix: rotate exposed credentials, move secrets to environment variables, user-secrets, or Azure Key Vault, and commit only sanitized examples.
   - Local status on 2026-07-08: code/config was sanitized locally and `.env.example`/`appsettings.Development.example.json` were added. External credential rotation and Azure App Settings updates still must be done outside this repo.

3. Camera controls do not control the real camera process.
   - `.NET` controller updates static fields only.
   - Python process owns the actual camera connection and source.
   - Fix: either make .NET proxy camera commands to Python, or move camera control ownership into one backend.

4. MQTT messages still reset camera stats.
   - `IoTBackend/Services/MqttService.cs` broadcasts `total_people = 0` and `violations = 0` on every MQTT message.
   - This can wipe real camera stats received from `CameraController`.
   - Fix: remove the zero stats broadcast or maintain a cached camera stats state.
   - Local status on 2026-07-08: fixed locally. MQTT handling no longer emits zero `ReceiveStatsUpdate` values.

### Major

1. MQTT config is duplicated and partly ignored.
   - `IoTBackend/appsettings.json` defines MQTT options, but `MqttService.cs` hardcodes broker and credentials.
   - A duplicate top-level `Services/MqttService.cs` exists outside the compiled project.
   - Fix: bind MQTT options from config and remove or archive duplicate service code.
   - Local status on 2026-07-08: compiled `IoTBackend/Services/MqttService.cs` now reads broker, credentials, topics, command topic, TLS, and weight interval from config. Duplicate service cleanup is still pending.

2. Python camera failure returns black frames while reporting running.
   - `backend/camera.py` starts with `is_running = True` and returns zero frames on failure.
   - Fix: set `is_running = False` on failed connect, expose source/connection status, and add bounded reconnect logic.

3. Angular SignalR connections can be duplicated.
   - Dashboard and camera pages both call `sensorService.start()`.
   - `SensorService` has no guard around an existing connection.
   - Fix: make `start()` idempotent and add `stop()` only when needed.
   - Local status on 2026-07-08: fixed locally. `SensorService.start()` now avoids opening duplicate SignalR connections.

4. Setup dependency handling is incomplete.
   - `start_app.bat` checks only Flask before skipping Python install.
   - It never runs `npm install`.
   - `requirements.txt` omits direct script dependencies such as `openpyxl`, `PyYAML`, and explicit Torch guidance.
   - Fix: use `pip install -r requirements.txt`, `npm ci`, and document .NET SDK requirements.

5. Legacy Flask UI is orphaned.
   - `templates/index.html` expects `/video_feed`.
   - `static/js/script.js` expects `/api/status`.
   - Current `backend/app.py` exposes `/api/camera/status` and no `/video_feed`.
   - Fix: delete/archive legacy UI or restore matching routes if still needed.

## New Audit Findings From Current Tree

### Critical

1. New auth and sensor services still bypass Angular environments.
   - Files:
     - `frontend/src/app/services/auth.service.ts`
     - `frontend/src/app/services/sensor.service.ts`
   - Problem: both hardcode Azure backend URL, so local dev routes in `environment.development.ts` are ignored.
   - Fix:
     ```ts
     import { environment } from '../../environments/environment';
     private apiUrl = environment.apiUrl;
     private hubUrl = environment.hubUrl;
     ```
   - Local status on 2026-07-08: fixed locally in `AuthService` and `SensorService`.

2. Default admin account is created with a public password.
   - File: `IoTBackend/Data/DbSeeder.cs`
   - Original problem: seeded a public default admin password.
   - Local status on 2026-07-08: fixed locally. Seeding now requires `DefaultAdmin:Username` and `DefaultAdmin:Password` from configuration and skips safely when missing.

3. In-memory session tokens are not production safe.
   - File: `IoTBackend/Services/SessionManager.cs`
   - Problem: sessions disappear on restart, cannot scale across multiple instances, and have no expiration.
   - Fix: use signed JWTs with expiry, or persist sessions in database/Redis with expiration and revocation.
   - Local status on 2026-07-08: partially fixed locally. Sessions now expire, auth header extraction is centralized, and `/api/auth/me` plus `/api/auth/logout` exist. Persistence across restarts / multiple instances is still pending.

4. Authorization can throw on malformed `Authorization` header in profile update.
   - File: `IoTBackend/Controllers/AuthController.cs`
   - Original problem: `UpdateMyProfile` assumed the header starts with `Bearer ` and called `Substring`.
   - Local status on 2026-07-08: fixed locally with explicit safe bearer-header validation.

### Major

1. Product creation permissions are too broad.
   - File: `IoTBackend/Controllers/ProductsController.cs`
   - Problem: `[CustomAuthorize]` at class level allows any logged-in user to create products, while update/delete require Manager/Admin.
   - Fix: add `[CustomAuthorize(Roles = "Manager,Admin")]` to `CreateProduct`.
   - Local status on 2026-07-08: fixed locally. Backend create/update/delete and frontend route/navigation now require Manager/Admin.

2. Role values are not validated server-side.
   - Files:
     - `IoTBackend/Controllers/AuthController.cs`
     - `IoTBackend/Controllers/UsersController.cs`
   - Original problem: register/update role accepted arbitrary role strings.
   - Local status on 2026-07-08: fixed locally with a shared allow-list: `User`, `Manager`, `Admin`.

3. Product codes are not unique.
   - Files:
     - `IoTBackend/Models/Product.cs`
     - `IoTBackend/Controllers/ProductsController.cs`
   - Problem: duplicate `ProductNumber` values can corrupt analytics and delete multiple scan histories unintentionally.
   - Fix: add a unique index in `AppDbContext.OnModelCreating` and validate duplicates in create/update.
   - Local status on 2026-07-08: partially fixed locally. API create/update now reject duplicates and the EF model defines a unique index. A database migration still needs to be generated/applied after `.NET 8 SDK` is available and existing duplicate data is checked.

4. Product scans are related by string instead of a foreign key.
   - Files:
     - `IoTBackend/Models/ProductScan.cs`
     - `IoTBackend/Services/MqttService.cs`
   - Problem: deleting or renaming a product can orphan or misassociate scans.
   - Fix: add `ProductId` FK to `ProductScan`, keep `ProductNumber` as denormalized display data only if needed.

5. MQTT weight loop comment and implementation conflict.
   - File: `IoTBackend/Services/MqttService.cs`
   - Problem: comment says 1 second; code delays 6000 ms.
   - Fix: decide intended interval and name it as a config setting, for example `WeightRequestIntervalSeconds`.
   - Local status on 2026-07-08: fixed locally. The interval is now `Mqtt:WeightRequestIntervalSeconds`, defaulting to 6 seconds.

6. MQTT command topic mixes command meanings.
   - File: `IoTBackend/Services/MqttService.cs`
   - Problem: publishes `GET_WEIGHT`, then later publishes `true`/`false` to the same `factory/commands` topic.
   - Fix: use explicit payload schema, e.g. `{ "type": "GET_WEIGHT" }` and `{ "type": "WEIGHT_CHECK", "accepted": true }`, or separate topics.
   - Local status on 2026-07-08: partially improved locally. `Mqtt:CommandTopic` is now configurable, but the payload schema remains backward-compatible (`GET_WEIGHT`, `true`, `false`) to avoid breaking the ESP32 until firmware changes are coordinated.

7. Health endpoint depends on database.
   - File: `IoTBackend/Program.cs`
   - Problem: `/health` returns failure if DB is down. This can make hosting platforms think the app process is dead.
   - Fix: split `/health/live` for process liveness and `/health/ready` for dependencies.
   - Local status on 2026-07-08: fixed locally. `/health` and `/health/live` are process liveness checks; `/health/ready` checks database readiness.

8. CORS allows only Azure frontend.
   - File: `IoTBackend/Program.cs`
   - Problem: local Angular at `http://localhost:4200` will be blocked.
   - Fix: configure allowed origins from config and include local origin in development.
   - Local status on 2026-07-08: fixed locally. CORS origins now come from config with localhost fallback.

9. Add product form rejects zero and lacks user-visible errors.
   - File: `frontend/src/app/components/add-product/add-product.component.ts`
   - Problem: `if (this.product.weight && this.product.code)` treats `0` as invalid implicitly and silently ignores invalid submissions.
   - Fix: validate with explicit numeric checks and show errors.
   - Local status on 2026-07-08: fixed locally. Add/edit product now uses explicit numeric validation and displays user-facing errors.

10. Navigation and route permissions are inconsistent.
   - Files:
     - `frontend/src/app/app.component.html`
     - `frontend/src/app/app.module.ts`
     - `frontend/src/app/components/sensor-dashboard.component.html`
   - Problem: main nav shows Live Stream to all logged-in users, but route allows only Manager/Admin.
   - Fix: hide role-restricted links based on current role.
   - Local status on 2026-07-08: fixed locally using a shared `AuthService.hasAnyRole()` helper and route metadata.

11. Frontend auth state trusts localStorage role.
   - Files:
     - `frontend/src/app/services/auth.service.ts`
     - `frontend/src/app/guards/auth.guard.ts`
   - Problem: client-side role can be edited in localStorage. Server authorization protects API, but UI may show unauthorized screens until API rejects.
   - Fix: keep server-side authorization, and add `/api/auth/me` validation on app startup for correct UX.
   - Local status on 2026-07-08: fixed locally for UX. App startup now validates stored sessions with `/api/auth/me` and clears invalid local state.

### Minor

1. `RegisterDto.Email` and frontend `email` field are unused.
   - Files:
     - `IoTBackend/Controllers/AuthController.cs`
     - `frontend/src/app/components/add-user/add-user.component.ts`
   - Fix: either add `Email` to `User` model and migration or remove the field from UI/DTO.

2. `ProductsController` uses synchronous EF calls inside API actions.
   - File: `IoTBackend/Controllers/ProductsController.cs`
   - Fix: use `ToListAsync`, `FirstOrDefaultAsync`, and `AnyAsync`.
   - Local status on 2026-07-08: fixed locally.

3. `PasswordHasher` uses 10,000 PBKDF2 iterations.
   - File: `IoTBackend/Services/PasswordHasher.cs`
   - Fix: increase iterations significantly for production or use ASP.NET Core Identity password hasher.

4. `dd.md` is empty.
   - Fix: remove it or replace it with useful project notes.

5. Console/log output still contains garbled characters in multiple files.
   - Fix: normalize source encoding to UTF-8 and replace mojibake text.

## Recommended Fix Order

### Phase 0 - Baseline Verification

Goal: know exactly what currently runs.

1. Install/verify local toolchain:
   - Python 3.10 or 3.11 recommended for ML compatibility.
   - .NET 8 SDK.
   - Node LTS.
2. Run:
   - `python -m compileall -q backend scripts train.py`
   - `python -m pip check`
   - `npm ci` from `frontend`
   - `npm run build` from `frontend`
   - `dotnet build IoTBackend/IoTBackend.csproj`

### Phase 1 - Config And Secrets

Goal: make local/cloud environments predictable and remove credentials from code.

Local progress on 2026-07-08:
- Angular `SensorService` and `AuthService` now read URLs from Angular environment files.
- `environment.development.ts` now points to the local .NET backend on `localhost:5005`.
- Python camera backend now reads `API_URL`, `CAMERA_SECRET`, and `CAMERA_SOURCE` from `.env`/environment variables.
- .NET default local port is now `5005` when Azure `PORT` is not set.
- Camera upload secret now comes from .NET configuration/environment.
- .NET camera upload secret is now required outside Development; `dev-camera-secret` only remains as a local development fallback/example.
- MQTT connection settings now come from .NET configuration instead of hardcoded service values.
- MQTT hosted service now disables itself with a warning when `Mqtt:Host` is not configured, instead of stopping the whole app.
- `IoTBackend/appsettings.json` was sanitized with local/example placeholders.
- `.env.example` was added.
- `requirements.txt` now includes `openpyxl` and `PyYAML`.
- Not done yet: real credential rotation in external services and Azure App Settings configuration.

1. Replace hardcoded URLs in Angular services with `environment`.
2. Make .NET default local port `5005`, or update every local reference to the chosen port.
3. Move Python `API_URL`, `MY_SECRET`, and `CAMERA_SOURCE` to environment variables.
4. Bind MQTT and DB settings from configuration.
5. Rotate all exposed credentials.
6. Add `.env.example` and sanitized `appsettings.Development.example.json`.

### Phase 2 - Auth Hardening

Goal: make login/users safe enough for real use.

Local progress on 2026-07-08:
- Default admin seeding now requires `DefaultAdmin:Username` and `DefaultAdmin:Password` from configuration.
- Role values are now normalized and restricted to `User`, `Manager`, and `Admin`.
- Profile update now safely validates the bearer authorization header before reading the session token.
- Sessions now have configurable expiry through `Auth:SessionMinutes`.
- Added `/api/auth/me` and `/api/auth/logout`.
- Frontend now checks stored sessions against `/api/auth/me` on startup and clears expired/invalid sessions.
- Not done yet: replace in-memory sessions with JWTs or database/Redis-backed sessions for restart resilience and horizontal scaling.

1. Replace in-memory sessions with JWTs or persistent expiring sessions.
2. Remove public default admin password. Seed from env only.
3. Validate roles on register and role update.
4. Add safe current-user extraction helper.
5. Add `/api/auth/me` and optionally `/api/auth/logout`.

### Phase 3 - Product And Scan Data Integrity

Goal: make analytics reliable.

Local progress on 2026-07-08:
- Product create/update now trims product codes and rejects duplicates.
- `Product.ProductNumber` and `ProductScan.ProductNumber` now have required/max-length model validation.
- `AppDbContext` now defines a unique model index for `Product.ProductNumber`.
- `ProductsController` now uses async EF calls.
- Product create/update/delete are restricted to Manager/Admin in backend and frontend routing/navigation.
- Add/edit product UI now validates weight explicitly and shows user-facing errors.
- Not done yet: generate/apply the database migration for the unique index after `.NET 8 SDK` is available and existing duplicate product data is checked.
- Not done yet: add a `ProductScan.ProductId` foreign key and backfill existing scan rows.

1. Add unique index for `Product.ProductNumber`.
2. Validate duplicate product creation/update.
3. Add FK from `ProductScan` to `Product`.
4. Convert ProductsController EF calls to async.
5. Restrict product create/update/delete to Manager/Admin.

### Phase 4 - Camera And MQTT Runtime Flow

Goal: make dashboard data stable.

Local progress on 2026-07-08:
- MQTT QR/product parsing now accepts common raw-topic and JSON payload shapes and forwards product number updates to SignalR.
- MQTT sensor messages no longer reset camera stats to zero.
- MQTT numeric parsing now uses invariant/current culture fallback for decimal payloads.
- MQTT command topic and weight request interval are now configurable.
- SignalR startup in the frontend is idempotent.
- Not done yet: coordinate an explicit JSON MQTT command schema with ESP32 firmware.
- Not done yet: make .NET camera controls actually control the Python camera process.
- Not done yet: improve Python camera failed-connection status/reconnect behavior.

1. Remove MQTT zero camera stats broadcast.
2. Make SignalR start idempotent in `SensorService`.
3. Decide camera owner:
   - Option A: Python owns camera and .NET proxies commands to Python.
   - Option B: .NET owns camera config and Python polls/receives it.
4. Fix `VideoCamera` failed connect state.
5. Make MQTT command payloads explicit JSON or split topics.
6. Add cooldown to email anomaly alerts.

### Phase 5 - Frontend UX And Routing

Goal: prevent user confusion and broken screens.

Local progress on 2026-07-08:
- Role-restricted navigation and add-product route visibility now match backend permissions.
- Stored frontend auth state is validated against `/api/auth/me` on startup.
- Add-product errors are now visible to users.
- Product analytics URLs now encode product numbers before API calls.
- Not done yet: add route fallback for unknown paths and visible errors for every remaining form.

1. Hide role-restricted nav links.
2. Add visible form errors for add-product/add-user/profile.
3. Add route fallback for unknown paths.
4. Validate auth state against server on app startup.
5. Ensure dashboard, stream, product list, analytics, and profile all use local/cloud env correctly.

### Phase 6 - Cleanup

Goal: reduce confusion.

1. Remove or archive duplicate `Services/MqttService.cs`.
2. Remove or reconnect legacy `templates/` and `static/`.
3. Remove empty `dd.md`.
4. Normalize encoding of docs/source files.
5. Update README and SETUP_GUIDE to match actual commands.

## Verification Checklist After Repairs

- `git status --short` shows only intentional changes.
- Python compile succeeds.
- Main Python imports succeed.
- `npm ci` succeeds.
- Angular build succeeds.
- .NET build succeeds.
- Local backend starts at expected port.
- Angular local frontend can login through local backend.
- SignalR connects from local Angular to local .NET backend.
- Python camera backend posts frames/stats to local .NET backend.
- MQTT sensor update does not reset camera stats.
- Product scan creates a `ProductScan` row and analytics updates.
- Role restrictions are enforced by backend and reflected in frontend navigation.
