# CargoOpt

AI-based container loading and ship stowage optimizer with a live 3D view, fuel/emissions estimates, and a downloadable PDF voyage report.

## Features

- Two optimizers: Genetic Algorithm (best of 5 runs) and Q-learning with hill-climbing polish, selectable in the app
- Stowage rules: weight balance, stacking, hazardous/fragile separation, and destination-port unload order
- Stability check (port/starboard balance, center of gravity)
- Fuel, CO2 and CII grade estimate based on voyage distance
- Real-time 3D ship view (Three.js) with labelled containers
- Add, edit and delete containers and bay sections from the browser
- PDF report: ship details, GA vs RL scores, voyage and stability report, rule check, unload plan, six 3D views

## Tech Stack

- Backend: Python, FastAPI, Uvicorn, MySQL, NumPy, ReportLab
- Frontend: Vite, JavaScript, Three.js

## Project Structure

```
CargoOpt/
├── backend/
│   ├── app.py
│   ├── container.py
│   ├── ship.py
│   ├── genetic_optimizer.py
│   ├── rl_optimizer.py
│   ├── compare_rl.py
│   ├── stability_checker.py
│   ├── emissions_calculator.py
│   ├── report_pdf.py
│   ├── database.py            (not in repo, create from database.example.py)
│   └── database.example.py
└── frontend/
    ├── index.html
    └── src/main.js
```

## Setup

### 1. Database

1. Install MySQL 8.0 and create a database named `cargoopt`.
2. Create the `bays` and `containers` tables (see `schema.sql` when available).
3. Copy `backend/database.example.py` to `backend/database.py` and set your MySQL password in `DB_CONFIG`.

### 2. Backend

```
cd backend
python -m venv venv
venv\Scripts\activate
pip install fastapi uvicorn mysql-connector-python pydantic numpy reportlab
uvicorn app:app --reload
```

The PDF report uses Arial from `C:\Windows\Fonts\` (Windows).

### 3. Frontend

```
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and click **Optimize**.

## Usage

1. Choose the optimizer (GA or RL) and the voyage distance.
2. Click **Optimize** to see the 3D stowage plan, voyage report and rule check.
3. Click **Download Report** to get the PDF.

## Author

Annlita Paulson, B.Tech CSE (Data Science), Kalasalingam Academy of Research and Education