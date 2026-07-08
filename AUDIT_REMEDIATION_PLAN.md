# SmartFactory Audit And Remediation Plan

Last updated: 2026-07-08

## Current Scan Status

- Git working tree status at scan time: clean.
- No uncommitted diff was present, but the current project tree contains additional auth, user, product, and analytics files compared with the earlier audit surface.
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

2. Secrets are committed in source.
   - Examples:
     - `backend/app.py`: camera RTSP credentials and shared secret.
     - `IoTBackend/Program.cs`: fallback MySQL password.
     - `IoTBackend/appsettings.json`: MySQL and MQTT credentials.
     - `IoTBackend/Services/MqttService.cs`: MQTT credentials.
     - `scripts/ai_dashboard_monitor.py`: MQTT and email credentials.
   - Fix: rotate exposed credentials, move secrets to environment variables, user-secrets, or Azure Key Vault, and commit only sanitized examples.

3. Camera controls do not control the real camera process.
   - `.NET` controller updates static fields only.
   - Python process owns the actual camera connection and source.
   - Fix: either make .NET proxy camera commands to Python, or move camera control ownership into one backend.

4. MQTT messages still reset camera stats.
   - `IoTBackend/Services/MqttService.cs` broadcasts `total_people = 0` and `violations = 0` on every MQTT message.
   - This can wipe real camera stats received from `CameraController`.
   - Fix: remove the zero stats broadcast or maintain a cached camera stats state.

### Major

1. MQTT config is duplicated and partly ignored.
   - `IoTBackend/appsettings.json` defines MQTT options, but `MqttService.cs` hardcodes broker and credentials.
   - A duplicate top-level `Services/MqttService.cs` exists outside the compiled project.
   - Fix: bind MQTT options from config and remove or archive duplicate service code.

2. Python camera failure returns black frames while reporting running.
   - `backend/camera.py` starts with `is_running = True` and returns zero frames on failure.
   - Fix: set `is_running = False` on failed connect, expose source/connection status, and add bounded reconnect logic.

3. Angular SignalR connections can be duplicated.
   - Dashboard and camera pages both call `sensorService.start()`.
   - `SensorService` has no guard around an existing connection.
   - Fix: make `start()` idempotent and add `stop()` only when needed.

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

2. Default admin account is created with a public password.
   - File: `IoTBackend/Data/DbSeeder.cs`
   - Problem: seeds `admin` / `admin123` and logs it.
   - Fix: require `DEFAULT_ADMIN_USERNAME` and `DEFAULT_ADMIN_PASSWORD` from environment. Refuse to seed if missing outside development.

3. In-memory session tokens are not production safe.
   - File: `IoTBackend/Services/SessionManager.cs`
   - Problem: sessions disappear on restart, cannot scale across multiple instances, and have no expiration.
   - Fix: use signed JWTs with expiry, or persist sessions in database/Redis with expiration and revocation.

4. Authorization can throw on malformed `Authorization` header in profile update.
   - File: `IoTBackend/Controllers/AuthController.cs`
   - Problem: `UpdateMyProfile` assumes the header starts with `Bearer ` and calls `Substring`.
   - Fix: reuse a validated current user accessor from `CustomAuthorizeAttribute` or safely parse the header.

### Major

1. Product creation permissions are too broad.
   - File: `IoTBackend/Controllers/ProductsController.cs`
   - Problem: `[CustomAuthorize]` at class level allows any logged-in user to create products, while update/delete require Manager/Admin.
   - Fix: add `[CustomAuthorize(Roles = "Manager,Admin")]` to `CreateProduct`.

2. Role values are not validated server-side.
   - Files:
     - `IoTBackend/Controllers/AuthController.cs`
     - `IoTBackend/Controllers/UsersController.cs`
   - Problem: register/update role accepts arbitrary role strings.
   - Fix: validate against an allow-list: `User`, `Manager`, `Admin`.

3. Product codes are not unique.
   - Files:
     - `IoTBackend/Models/Product.cs`
     - `IoTBackend/Controllers/ProductsController.cs`
   - Problem: duplicate `ProductNumber` values can corrupt analytics and delete multiple scan histories unintentionally.
   - Fix: add a unique index in `AppDbContext.OnModelCreating` and validate duplicates in create/update.

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

6. MQTT command topic mixes command meanings.
   - File: `IoTBackend/Services/MqttService.cs`
   - Problem: publishes `GET_WEIGHT`, then later publishes `true`/`false` to the same `factory/commands` topic.
   - Fix: use explicit payload schema, e.g. `{ "type": "GET_WEIGHT" }` and `{ "type": "WEIGHT_CHECK", "accepted": true }`, or separate topics.

7. Health endpoint depends on database.
   - File: `IoTBackend/Program.cs`
   - Problem: `/health` returns failure if DB is down. This can make hosting platforms think the app process is dead.
   - Fix: split `/health/live` for process liveness and `/health/ready` for dependencies.

8. CORS allows only Azure frontend.
   - File: `IoTBackend/Program.cs`
   - Problem: local Angular at `http://localhost:4200` will be blocked.
   - Fix: configure allowed origins from config and include local origin in development.

9. Add product form rejects zero and lacks user-visible errors.
   - File: `frontend/src/app/components/add-product/add-product.component.ts`
   - Problem: `if (this.product.weight && this.product.code)` treats `0` as invalid implicitly and silently ignores invalid submissions.
   - Fix: validate with explicit numeric checks and show errors.

10. Navigation and route permissions are inconsistent.
   - Files:
     - `frontend/src/app/app.component.html`
     - `frontend/src/app/app.module.ts`
     - `frontend/src/app/components/sensor-dashboard.component.html`
   - Problem: main nav shows Live Stream to all logged-in users, but route allows only Manager/Admin.
   - Fix: hide role-restricted links based on current role.

11. Frontend auth state trusts localStorage role.
   - Files:
     - `frontend/src/app/services/auth.service.ts`
     - `frontend/src/app/guards/auth.guard.ts`
   - Problem: client-side role can be edited in localStorage. Server authorization protects API, but UI may show unauthorized screens until API rejects.
   - Fix: keep server-side authorization, and add `/api/auth/me` validation on app startup for correct UX.

### Minor

1. `RegisterDto.Email` and frontend `email` field are unused.
   - Files:
     - `IoTBackend/Controllers/AuthController.cs`
     - `frontend/src/app/components/add-user/add-user.component.ts`
   - Fix: either add `Email` to `User` model and migration or remove the field from UI/DTO.

2. `ProductsController` uses synchronous EF calls inside API actions.
   - File: `IoTBackend/Controllers/ProductsController.cs`
   - Fix: use `ToListAsync`, `FirstOrDefaultAsync`, and `AnyAsync`.

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

1. Replace hardcoded URLs in Angular services with `environment`.
2. Make .NET default local port `5005`, or update every local reference to the chosen port.
3. Move Python `API_URL`, `MY_SECRET`, and `CAMERA_SOURCE` to environment variables.
4. Bind MQTT and DB settings from configuration.
5. Rotate all exposed credentials.
6. Add `.env.example` and sanitized `appsettings.Development.example.json`.

### Phase 2 - Auth Hardening

Goal: make login/users safe enough for real use.

1. Replace in-memory sessions with JWTs or persistent expiring sessions.
2. Remove public default admin password. Seed from env only.
3. Validate roles on register and role update.
4. Add safe current-user extraction helper.
5. Add `/api/auth/me` and optionally `/api/auth/logout`.

### Phase 3 - Product And Scan Data Integrity

Goal: make analytics reliable.

1. Add unique index for `Product.ProductNumber`.
2. Validate duplicate product creation/update.
3. Add FK from `ProductScan` to `Product`.
4. Convert ProductsController EF calls to async.
5. Restrict product create/update/delete to Manager/Admin.

### Phase 4 - Camera And MQTT Runtime Flow

Goal: make dashboard data stable.

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

