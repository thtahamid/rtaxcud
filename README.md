# FlowSync — RTA Traffic Intelligence × Mistral AI

An end-to-end AI-powered traffic orchestration system for RTA Dubai. Replays historical traffic data on an interactive OpenStreetMap dashboard and uses Mistral AI to optimize signal timings and reroute fleets.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Frontend (Next.js + React + Tailwind)                  │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐ │
│  │ OpenStreetMap│  │ Live Telemetry│  │ Mistral AI   │ │
│  │ (react-leaflet)│ │ (Baseline vs │  │ Reasoning    │ │
│  │              │  │  FlowSync)   │  │ Panel        │ │
│  └─────────────┘  └──────────────┘  └───────────────┘ │
└──────────────────────────┬──────────────────────────────┘
                           │ HTTP/REST
┌──────────────────────────▼──────────────────────────────┐
│  Backend (FastAPI)                                      │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐ │
│  │ RTA Dataset │  │ Simulation   │  │ Mistral AI    │ │
│  │ Loader      │  │ Engine       │  │ Optimizer     │ │
│  │ (952K rows) │  │ (time-slice  │  │ (mistral-     │ │
│  │             │  │  frames)     │  │  large-latest)│ │
│  └─────────────┘  └──────────────┘  └───────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## Quick Start

### Backend

```bash
cd backend

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate    # macOS/Linux
# venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Optional: set Mistral API key for AI optimization
export MISTRAL_API_KEY=your_key_here

# Start the server
python main.py
# API runs at http://localhost:8000
```

> **Note:** The `venv/` directory is gitignored. Always activate it before running the backend.

### Frontend

```bash
cd frontend
npm install
npm run dev
# Dashboard at http://localhost:3000
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/health` | Service health + Mistral status |
| `GET /api/dates` | List all available dates |
| `GET /api/hours?date=YYYY-MM-DD` | Hours available for a date |
| `GET /api/frame?date=&hour=` | Baseline simulation frame |
| `GET /api/optimize?date=&hour=` | Mistral-optimized frame |
| `GET /api/compare?date=&hour=` | Side-by-side comparison |

## Dataset

Uses the RTA Traffic Dataset (`rta_traffic_dataset/datasets/`) — 952K rows across 18 CSV files covering 2023-2025:
- Traffic volume (473K rows, 18 locations)
- Signal performance (263K rows, 10 junctions)
- Signal timing plans (195 rows)
- Incidents, weather, calendar, Salik tolls, metro ridership

## Mistral AI Integration

The system uses `mistral-large-latest` via the Mistral Python SDK to:
1. Analyze real-time traffic state (v/c ratios, delays, queues, weather)
2. Recommend signal timing adjustments (green time deltas within safety bounds)
3. Suggest fleet rerouting for critical congestion points
4. Predict improvement metrics (delay reduction, throughput increase)

When no API key is configured, a deterministic heuristic fallback provides the same interface.

## Features

- **Interactive Map**: OpenStreetMap with color-coded congestion markers
- **Baseline vs FlowSync Toggle**: Switch between raw data and AI-optimized views
- **Live Telemetry**: 8 key metrics with before/after comparison
- **Mistral Reasoning Panel**: Live feed of AI decision-making
- **Auto-Play**: Step through 24 hours automatically
- **RTA Branded**: Corporate blue (#004B87) dark mode dashboard
