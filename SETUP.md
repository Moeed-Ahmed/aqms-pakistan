# 🇵🇰 AQMS Pakistan — Setup Guide

## Project Structure

```
aqms/
├── backend/
│   ├── app.py              ← Flask API server
│   └── requirements.txt
├── database/
│   └── schema.sql          ← PostgreSQL + PostGIS schema
└── frontend/
    ├── index.html           ← Main page
    └── static/
        ├── css/style.css
        └── js/app.js
```

---

## 1. Prerequisites

Install these first:
- Python 3.10+
- PostgreSQL 14+ with PostGIS 3.x
- Node.js (optional, only needed if you install JS tools)

---

## 2. PostgreSQL + PostGIS Setup

```bash
# Create database
psql -U postgres -c "CREATE DATABASE aqms_pakistan;"
psql -U postgres -d aqms_pakistan -c "CREATE EXTENSION postgis;"

# Run schema (creates all tables + seed data)
psql -U postgres -d aqms_pakistan -f database/schema.sql
```

---

## 3. Python Backend Setup

```bash
# In VS Code terminal
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### Configure credentials via `.env`

The `.env` file is **already created** in the `backend/` folder with your WAQI token filled in.
Just update the PostgreSQL password:

```env
# backend/.env
WAQI_TOKEN=152d028071b73bcd98ead9968c65569a15bc1041   ← already set ✅
DB_NAME=aqms_pakistan
DB_USER=postgres
DB_PASSWORD=your_postgres_password_here               ← change this
DB_HOST=localhost
DB_PORT=5432
```

> The app uses `python-dotenv` to load `.env` automatically when `app.py` starts.
> Never commit `.env` to GitHub — it's listed in `.gitignore`.

---

## 4. Run the Server

```bash
# From backend/
python app.py
```

Open browser: **http://localhost:5000**

---

## 5. APIs Used (All Free, No Key Required)

| API | Purpose | Token? | URL |
|-----|---------|--------|-----|
| **WAQI** | Real PM2.5 / PM10 / AQI (live) | ✅ In `.env` | api.waqi.info |
| Open-Meteo | Live weather, wind, rain | ❌ Free | api.open-meteo.com |
| GDACS | Disaster alerts (floods, EQ…) | ❌ Free | gdacs.org |
| NASA GIBS | Satellite cloud tile overlay | ❌ Free | gibs.earthdata.nasa.gov |
| CartoDB | Dark / light base maps | ❌ Free | basemaps.cartocdn.com |

> Your WAQI token `152d028071b73bcd98ead9968c65569a15bc1041` is already in `.env`.
> WAQI provides: AQI, PM2.5, PM10, NO₂, O₃, SO₂, CO, temperature, humidity, wind, pressure + 7-day forecast.
> If WAQI returns no data for a station the system falls back to demo values automatically.

---

## 6. Features

- ✅ Real-time PM2.5 / PM10 from OpenAQ
- ✅ Live weather (temp, wind, humidity, clouds, rain) from Open-Meteo
- ✅ Wind particle animation (earth.nullschool-style)
- ✅ AQI heatmap overlay
- ✅ Disaster alerts (floods, earthquakes, cyclones, landslides)
- ✅ NASA satellite cloud tiles
- ✅ Day/Night mode
- ✅ 4 base map styles (dark, light, terrain, satellite)
- ✅ Click any point → popup + sidebar with live data
- ✅ Layer toggles (PM2.5, PM10, wind, heatmap, disasters, clouds)
- ✅ PostGIS spatial queries (nearest station, radius search, ST_Intersects)
- ✅ Educational info panel (PM2.5, PM10, disasters, wind)
- ✅ National statistics dashboard

---

## 7. PostGIS Spatial Queries (Backend)

The backend exposes:

| Endpoint | PostGIS Feature |
|---------|-----------------|
| `/api/nearest-station?lat=31&lon=74` | ST_Distance – find closest station |
| `/api/stations-in-radius?lat=31&lon=74&radius_km=200` | ST_DWithin – circle query |
| `/api/check-disasters?lat=27&lon=68` | ST_Intersects – point in zone |

---

## 8. VS Code Tips

1. Install extensions: **Python**, **Pylance**, **Prettier**
2. Set Python interpreter to `backend/venv`
3. Use **Live Server** extension for hot reload during CSS/JS edits
4. Open integrated terminal with `Ctrl+~`
