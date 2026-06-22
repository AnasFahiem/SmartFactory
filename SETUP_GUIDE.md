# SmartFactory System Setup Guide

This guide explains how to safely run the full SmartFactory system (AI Camera + IoT Backend + Angular Frontend) locally, and how to transition it back to the cloud.

## 1. Prerequisites

Before starting, ensure you have the following installed on your machine:
- **Python 3.9+** (For the AI computer vision models)
- **.NET 8 SDK** (For the IoT Backend)
- **Node.js & npm** (For the Angular Frontend)
- **MySQL / MariaDB** (Running locally on default port 3306)

## 2. Local Database Setup

By default, the system expects a local MySQL database for testing.
1. Make sure your local MySQL server is running.
2. The `IoTBackend/appsettings.json` is currently configured to use:
   - **Server:** `localhost`
   - **Database:** `IotDb`
   - **User:** `root`
   - **Password:** `12345678`
3. If your local DB uses different credentials, update `IoTBackend/appsettings.json` before running.

## 3. Running the System Locally

To launch the entire system with one click, run the provided batch file from the root directory:

```bash
# Windows
start_app.bat
```

**What this script does in the background:**
1. **Python AI Backend (Port 5000):** Activates the virtual environment, loads the trained `best.pt` model, and starts capturing from your webcam. It continuously pushes AI detection stats to Port 5005.
2. **.NET IoT Backend (Port 5005):** Starts the REST API and SignalR hub, listening for the AI Python script and connecting to the local database.
3. **Angular Frontend (Port 4200):** Starts the UI dashboard, configured in `environment.development.ts` to talk to `localhost:5005`.

Once everything initializes (takes about 15 seconds), your browser will automatically open to `http://localhost:4200`.

## 4. Transitioning to Cloud / Production

When you are ready to turn the cloud infrastructure back on, you need to update 3 files to point away from `localhost`:

### A. Python AI Backend (`backend/app.py`)
At the top of `backend/app.py`, change the `API_URL` variable to point to your Azure deployment.
```python
# Change this:
API_URL = os.getenv("API_URL", "http://localhost:5005/api/camera/upload")

# To this:
API_URL = os.getenv("API_URL", "https://smartest-factory-dcg4awhecvahcmgq.francecentral-01.azurewebsites.net/api/camera/upload")
```

### B. Angular Frontend (`frontend/src/environments/environment.ts`)
When building for production (`npm run build`), Angular uses `environment.ts`. Ensure it points to your Azure URL:
```typescript
export const environment = {
  production: true,
  apiUrl: 'https://smartest-factory-dcg4awhecvahcmgq.francecentral-01.azurewebsites.net',
  hubUrl: 'https://smartest-factory-dcg4awhecvahcmgq.francecentral-01.azurewebsites.net/hubs/factory'
};
```

### C. .NET Database Connections (`IoTBackend/appsettings.json`)
Update the `DefaultConnection` string from `localhost` back to your cloud MySQL database server.

---
**Note on Performance:** The Python AI backend (`backend/app.py`) requires a webcam. If no webcam is available, the script may loop silently looking for a camera source.
