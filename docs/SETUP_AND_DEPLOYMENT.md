# Setup and Deployment Guide

## 1. Local Development Setup

### Prerequisites
- Python `>= 3.11` (tested with Python `3.12.10`)
- Node.js `>= 18` and npm (tested with Node `v26.7.0`, npm `11.19.0`)

### Step 1: Install Backend Dependencies
```powershell
pip install -r backend/requirements.txt
```

### Step 2: Install Frontend Dependencies
```powershell
cd frontend
npm.cmd install
cd ..
```

### Step 3: Start the Backend API
```powershell
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```
On startup, `bootstrap_database()` automatically creates the SQLite database (`backend/data/placement_readiness.db`) and idempotently seeds all roles, skills, assessments, questions, and learning activities.

### Step 4: Start the Frontend Dev Server
```powershell
cd frontend
npm.cmd run dev
```
Open `http://localhost:5173` in your browser.

---

## 2. Production Build & Deployment

### Frontend Static Build
```powershell
cd frontend
npm.cmd run build
```
This runs TypeScript project references (`tsc -b`) and bundles static assets into `frontend/dist/`.

### Production Environment Variables
Set the following environment variables in your hosting platform (never commit `.env` to version control):
- `SECRET_KEY`: Strong cryptographically random string (`>= 32` bytes).
- `DATABASE_URL`: PostgreSQL connection string (e.g., `postgresql+psycopg2://user:pass@host:5432/placement_db`) or persistent SQLite volume path.
- `ALLOWED_ORIGINS`: Comma-separated list of deployed frontend origins (e.g., `https://placement-readiness.example.edu`).
- `VITE_API_BASE_URL`: Public URL of the backend `/api/v1` prefix used during frontend build.
