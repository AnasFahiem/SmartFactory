# IoT Smart Factory Dashboard

Factory-floor telemetry demo that streams MQTT sensor data into an ASP.NET Core backend, persists product events in MySQL, and pushes live updates to an Angular dashboard via SignalR.

## Architecture
- **Backend**: ASP.NET Core 8 Web API + SignalR, MQTTnet client, EF Core (Pomelo MySQL) for persistence
- **Frontend**: Angular dashboard consuming SignalR hub in real time
- **Messaging**: MQTT broker (HiveMQ Cloud-ready) with wildcard subscription
- **Database**: MySQL `Products` table storing product number and weight snapshots

## Message Flow
MQTT → MqttService → SignalR (FactoryHub) → Angular dashboard

## MQTT Topics & Payloads
- `factory/measurement` (batch):
	- Payload example: `{ "productNumber": "PN-00123", "weight": 12.34, "temperature": 23.7, "smoke": false }`
	- Effects: broadcasts all four values; stores `productNumber` + `weight` in DB
- `factory/temperature`: `{ "value": 23.7 }` → broadcasts temperature
- `factory/smoke`: `{ "value": false }` → broadcasts smoke status
- `factory/weight`: `{ "value": 12.34 }` → broadcasts + stores weight
- `factory/product`: `{ "value": "PN-00123" }` → broadcasts + stores product number
- Wildcard subscription `factory/#` is enabled for flexibility.

## Project Layout
- Backend: [IoTBackend](IoTBackend)
	- MQTT handler: [Services/MqttService.cs](IoTBackend/Services/MqttService.cs)
	- SignalR hub: [Hubs/FactoryHub.cs](IoTBackend/Hubs/FactoryHub.cs)
	- API controller: [Controllers/ProductsController.cs](IoTBackend/Controllers/ProductsController.cs)
	- EF model/context: [Models/Product.cs](IoTBackend/Models/Product.cs), [Data/AppDbContext.cs](IoTBackend/Data/AppDbContext.cs)
- Frontend: [IoTFrontend](IoTFrontend)
	- Dashboard component: [src/app/components/sensor-dashboard.component.ts](IoTFrontend/src/app/components/sensor-dashboard.component.ts)
	- SignalR client service: [src/app/services/sensor.service.ts](IoTFrontend/src/app/services/sensor.service.ts)

## Prerequisites
- .NET 8 SDK
- Node.js 18+ and npm
- MySQL 8 (or compatible) instance

## Backend Setup
```bash
cd "IoTBackend"
dotnet restore

# (optional) update DB connection string via env var
setx ConnectionStrings__DefaultConnection "Server=localhost;Database=IotDb;User=xxx;Password=xxx;" /M

# apply migrations (creates Products table if not present)
dotnet ef database update

# run API + MQTT + SignalR
dotnet run
```

## Frontend Setup
```bash
cd "IoTFrontend"
npm install
ng serve --open
```

The dashboard expects the backend at `http://localhost:5000/hubs/factory`. Adjust in [sensor.service.ts](IoTFrontend/src/app/services/sensor.service.ts) if needed.

## Configuration
Key settings live in [IoTBackend/appsettings.json](IoTBackend/appsettings.json):
- `ConnectionStrings:DefaultConnection` — MySQL connection string
- `Mqtt:Host/Port/UseTls/Username/Password/Topics` — broker settings; consider using env vars in production

Environment variable naming follows ASP.NET Core’s double-underscore convention, e.g.:
```
setx Mqtt__Host "your-broker" /M
setx Mqtt__Username "user" /M
setx Mqtt__Password "secret" /M
```

## API Surface
- `GET /api/products` — list all stored product events
- `GET /api/products/latest` — most recent product event

## Running the Full Stack
1) Start backend: `dotnet run` (listens on `https://localhost:5001` and `http://localhost:5000` by default)
2) Start frontend: `ng serve --open` (served at `http://localhost:4200`)
3) Publish MQTT messages to the configured broker; UI updates live via SignalR.

## Troubleshooting
- If Angular cannot connect, check CORS origin in [Program.cs](IoTBackend/Program.cs) (`http://localhost:4200` allowed).
- If DB writes fail, verify MySQL connection string and run `dotnet ef database update`.
- For MQTT connectivity issues, confirm broker host/port/TLS and credentials in configuration or env vars.

## Notes
- Credentials in `appsettings.json` are for development; use environment variables or user secrets in production.
- The MQTT client auto-reconnects and logs all received messages for diagnostics.
