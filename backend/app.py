"""
AQMS Pakistan — Flask Backend v4
- Data logging: every fetch saves to PostgreSQL
- 50 stations across all provinces
- Fixed WAQI parsing, Open-Meteo weather, GDACS disasters
- PostGIS spatial queries
"""

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from dotenv import load_dotenv
import requests, psycopg2, psycopg2.extras
import math, random, os, logging
from datetime import datetime

load_dotenv()  # auto-loads backend/.env

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────
WAQI_TOKEN = os.getenv("WAQI_TOKEN", "")
DB_CONFIG  = {
    "dbname":   os.getenv("DB_NAME",     "aqms_pakistan"),
    "user":     os.getenv("DB_USER",     "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
    "host":     os.getenv("DB_HOST",     "localhost"),
    "port":     os.getenv("DB_PORT",     "5432"),
}

# ── 50 Stations matching DB IDs ────────────────────────────────
STATIONS = [
    # PUNJAB
    {"id": 1,  "name":"Lahore",           "province":"Punjab",      "lat":31.5497, "lon":74.3436, "pm25":128,"pm10":162},
    {"id": 2,  "name":"Faisalabad",       "province":"Punjab",      "lat":31.4504, "lon":73.1350, "pm25":108,"pm10":138},
    {"id": 3,  "name":"Rawalpindi",       "province":"Punjab",      "lat":33.5651, "lon":73.0169, "pm25": 68,"pm10": 90},
    {"id": 4,  "name":"Gujranwala",       "province":"Punjab",      "lat":32.1877, "lon":74.1945, "pm25":116,"pm10":148},
    {"id": 5,  "name":"Multan",           "province":"Punjab",      "lat":30.1575, "lon":71.5249, "pm25":114,"pm10":144},
    {"id": 6,  "name":"Sialkot",          "province":"Punjab",      "lat":32.4945, "lon":74.5229, "pm25": 91,"pm10":116},
    {"id": 7,  "name":"Bahawalpur",       "province":"Punjab",      "lat":29.4000, "lon":71.6833, "pm25": 86,"pm10":112},
    {"id": 8,  "name":"Sargodha",         "province":"Punjab",      "lat":32.0836, "lon":72.6711, "pm25": 97,"pm10":132},
    {"id": 9,  "name":"Sheikhupura",      "province":"Punjab",      "lat":31.7131, "lon":73.9783, "pm25":102,"pm10":138},
    {"id":10,  "name":"Dera Ghazi Khan",  "province":"Punjab",      "lat":30.0459, "lon":70.6403, "pm25": 88,"pm10":122},
    {"id":11,  "name":"Kasur",            "province":"Punjab",      "lat":31.1155, "lon":74.4467, "pm25":108,"pm10":144},
    {"id":12,  "name":"Sahiwal",          "province":"Punjab",      "lat":30.6706, "lon":73.1060, "pm25": 94,"pm10":128},
    {"id":13,  "name":"Okara",            "province":"Punjab",      "lat":30.8081, "lon":73.4458, "pm25": 92,"pm10":124},
    {"id":14,  "name":"Rahim Yar Khan",   "province":"Punjab",      "lat":28.4202, "lon":70.2952, "pm25": 80,"pm10":110},
    {"id":15,  "name":"Chakwal",          "province":"Punjab",      "lat":32.9304, "lon":72.8585, "pm25": 58,"pm10": 84},
    {"id":16,  "name":"Mianwali",         "province":"Punjab",      "lat":32.5836, "lon":71.5376, "pm25": 74,"pm10":108},
    {"id":17,  "name":"Jhang",            "province":"Punjab",      "lat":31.2690, "lon":72.3168, "pm25": 90,"pm10":124},
    # SINDH
    {"id":20,  "name":"Karachi",          "province":"Sindh",       "lat":24.8607, "lon":67.0011, "pm25": 82,"pm10":108},
    {"id":21,  "name":"Hyderabad",        "province":"Sindh",       "lat":25.3960, "lon":68.3578, "pm25": 76,"pm10": 98},
    {"id":22,  "name":"Sukkur",           "province":"Sindh",       "lat":27.7052, "lon":68.8574, "pm25": 72,"pm10":104},
    {"id":23,  "name":"Larkana",          "province":"Sindh",       "lat":27.5631, "lon":68.2158, "pm25": 78,"pm10":110},
    {"id":24,  "name":"Nawabshah",        "province":"Sindh",       "lat":26.2483, "lon":68.4096, "pm25": 64,"pm10": 96},
    {"id":25,  "name":"Mirpur Khas",      "province":"Sindh",       "lat":25.5251, "lon":69.0159, "pm25": 70,"pm10":102},
    {"id":26,  "name":"Jacobabad",        "province":"Sindh",       "lat":28.2810, "lon":68.4386, "pm25": 84,"pm10":116},
    {"id":27,  "name":"Shikarpur",        "province":"Sindh",       "lat":27.9571, "lon":68.6382, "pm25": 74,"pm10":106},
    {"id":28,  "name":"Khairpur",         "province":"Sindh",       "lat":27.5295, "lon":68.7592, "pm25": 68,"pm10": 98},
    {"id":29,  "name":"Dadu",             "province":"Sindh",       "lat":26.7319, "lon":67.7766, "pm25": 62,"pm10": 92},
    {"id":30,  "name":"Sanghar",          "province":"Sindh",       "lat":26.0466, "lon":68.9481, "pm25": 60,"pm10": 90},
    {"id":31,  "name":"Badin",            "province":"Sindh",       "lat":24.6550, "lon":68.8383, "pm25": 56,"pm10": 84},
    {"id":32,  "name":"Tharparkar",       "province":"Sindh",       "lat":25.3617, "lon":69.7361, "pm25": 58,"pm10": 88},
    # BALOCHISTAN
    {"id":35,  "name":"Quetta",           "province":"Balochistan", "lat":30.1798, "lon":66.9750, "pm25": 62,"pm10": 92},
    {"id":36,  "name":"Turbat",           "province":"Balochistan", "lat":25.9917, "lon":63.0711, "pm25": 30,"pm10": 48},
    {"id":37,  "name":"Gwadar",           "province":"Balochistan", "lat":25.1266, "lon":62.3220, "pm25": 26,"pm10": 40},
    {"id":38,  "name":"Khuzdar",          "province":"Balochistan", "lat":27.8000, "lon":66.6167, "pm25": 44,"pm10": 66},
    {"id":39,  "name":"Chaman",           "province":"Balochistan", "lat":30.9210, "lon":66.4512, "pm25": 52,"pm10": 78},
    {"id":40,  "name":"Sibi",             "province":"Balochistan", "lat":29.5448, "lon":67.8773, "pm25": 48,"pm10": 72},
    {"id":41,  "name":"Hub",              "province":"Balochistan", "lat":25.0500, "lon":66.8833, "pm25": 58,"pm10": 86},
    {"id":42,  "name":"Nushki",           "province":"Balochistan", "lat":29.5542, "lon":66.0214, "pm25": 36,"pm10": 54},
    {"id":43,  "name":"Dalbandin",        "province":"Balochistan", "lat":28.8881, "lon":64.4062, "pm25": 32,"pm10": 50},
    {"id":44,  "name":"Loralai",          "province":"Balochistan", "lat":30.3700, "lon":68.5981, "pm25": 42,"pm10": 64},
    # KPK
    {"id":45,  "name":"Peshawar",         "province":"KPK",         "lat":34.0151, "lon":71.5249, "pm25": 96,"pm10":122},
    {"id":46,  "name":"Abbottabad",       "province":"KPK",         "lat":34.1688, "lon":73.2215, "pm25": 40,"pm10": 58},
    {"id":47,  "name":"Mardan",           "province":"KPK",         "lat":34.1988, "lon":72.0447, "pm25": 82,"pm10":114},
    {"id":48,  "name":"Mansehra",         "province":"KPK",         "lat":34.3333, "lon":73.2000, "pm25": 42,"pm10": 62},
    {"id":49,  "name":"Swat",             "province":"KPK",         "lat":34.7701, "lon":72.3563, "pm25": 36,"pm10": 54},
    {"id":50,  "name":"Kohat",            "province":"KPK",         "lat":33.5869, "lon":71.4429, "pm25": 72,"pm10":104},
    {"id":51,  "name":"Dera Ismail Khan", "province":"KPK",         "lat":31.8320, "lon":70.9027, "pm25": 78,"pm10":112},
    # ICT + GB + AJK
    {"id":55,  "name":"Islamabad",        "province":"ICT",         "lat":33.6844, "lon":73.0479, "pm25": 55,"pm10": 72},
    {"id":56,  "name":"Gilgit",           "province":"GB",          "lat":35.9208, "lon":74.3081, "pm25": 28,"pm10": 42},
    {"id":57,  "name":"Skardu",           "province":"GB",          "lat":35.3075, "lon":75.5489, "pm25": 22,"pm10": 34},
    {"id":58,  "name":"Muzaffarabad",     "province":"AJK",         "lat":34.3700, "lon":73.4700, "pm25": 48,"pm10": 68},
    {"id":59,  "name":"Mirpur AJK",       "province":"AJK",         "lat":33.1474, "lon":73.7518, "pm25": 52,"pm10": 76},
]

# ── AQI helpers ──────────────────────────────────────────────
def aqi_from_pm25(pm25):
    if not pm25 or pm25 < 0: return 0
    bp = [(0,12,0,50),(12.1,35.4,51,100),(35.5,55.4,101,150),
          (55.5,150.4,151,200),(150.5,250.4,201,300),(250.5,500.4,301,500)]
    for cl,ch,il,ih in bp:
        if cl <= pm25 <= ch:
            return round(((ih-il)/(ch-cl))*(pm25-cl)+il)
    return 500

def aqi_cat(aqi):
    if aqi <= 50:  return ("Good",                        "#00e400")
    if aqi <= 100: return ("Moderate",                    "#ffff00")
    if aqi <= 150: return ("Unhealthy (Sensitive Groups)","#ff7e00")
    if aqi <= 200: return ("Unhealthy",                   "#ff0000")
    if aqi <= 300: return ("Very Unhealthy",              "#8f3f97")
    return ("Hazardous", "#7e0023")

# ── DB helper ─────────────────────────────────────────────────
def get_db():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME", "postgres"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", ""),
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            sslmode="require"
        )
        return conn
    except Exception as e:
        log.error(f"DB connection failed: {e}")
        return None
def cleanup_old_data():
    """Keep only last 7 days of data to control DB size."""
    conn = get_db()
    if not conn:
        return
    try:
        cur = conn.cursor()
        cur.execute("""
            DELETE FROM air_quality_readings
            WHERE recorded_at < NOW() - INTERVAL '7 days'
        """)
        aq_deleted = cur.rowcount

        cur.execute("""
            DELETE FROM weather_readings
            WHERE recorded_at < NOW() - INTERVAL '7 days'
        """)
        wx_deleted = cur.rowcount

        cur.execute("""
            DELETE FROM data_log
            WHERE fetched_at < NOW() - INTERVAL '3 days'
        """)

        conn.commit()
        cur.close()
        conn.close()
        log.info(f"Cleanup: removed {aq_deleted} AQ rows, {wx_deleted} WX rows")
    except Exception as e:
        log.error(f"Cleanup error: {e}")
        try:
            conn.rollback()
            conn.close()
        except:
            pass

# ── WAQI fetch + parse ────────────────────────────────────────
def waqi_fetch(lat, lon):
    """
    Fetch from WAQI geo endpoint.
    Returns normalized dict or None.
    """
    try:
        url  = f"https://api.waqi.info/feed/geo:{lat};{lon}/?token={WAQI_TOKEN}"
        r    = requests.get(url, timeout=8)
        r.raise_for_status()
        data = r.json()

        if data.get("status") != "ok":
            return None

        d    = data["data"]
        iaqi = d.get("iaqi", {})

        def g(k): return iaqi.get(k, {}).get("v")

        # WAQI AQI can be int or "-" string
        try:
            raw_aqi = int(d.get("aqi", 0))
            if raw_aqi <= 0: raw_aqi = None
        except (TypeError, ValueError):
            raw_aqi = None

        pm25 = g("pm25")
        pm10 = g("pm10")

        if raw_aqi is None and pm25:
            raw_aqi = aqi_from_pm25(pm25)

        cat, color = aqi_cat(raw_aqi) if raw_aqi else ("Unknown", "#888888")
        geo        = d.get("city", {}).get("geo", [lat, lon])

        return {
            "aqi":          raw_aqi,
            "aqi_category": cat,
            "color":        color,
            "pm25":         pm25,
            "pm10":         pm10,
            "no2":          g("no2"),
            "o3":           g("o3"),
            "so2":          g("so2"),
            "co":           g("co"),
            "temperature":  g("t"),
            "humidity":     g("h"),
            "wind_speed":   g("w"),
            "pressure":     g("p"),
            "dominant_pol": d.get("dominentpol"),
            "city_name":    d.get("city", {}).get("name", ""),
            "lat":          geo[0] if geo else lat,
            "lon":          geo[1] if geo else lon,
            "recorded_at":  d.get("time", {}).get("iso", datetime.now().isoformat()),
            "forecast_pm25":d.get("forecast",{}).get("daily",{}).get("pm25",[]),
            "forecast_pm10":d.get("forecast",{}).get("daily",{}).get("pm10",[]),
            "source":       "WAQI",
        }
    except Exception as e:
        log.warning(f"WAQI ({lat},{lon}): {e}")
        return None

# ── SAVE AQ to DB ─────────────────────────────────────────────
def save_aq_reading(conn, station_id, live):
    """INSERT one air quality row into air_quality_readings."""
    if not conn or not live: return
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO air_quality_readings
              (station_id, pm25, pm10, no2, o3, so2, co,
               aqi, aqi_category, dominant_pol, source, recorded_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            station_id,
            live.get("pm25"), live.get("pm10"),
            live.get("no2"),  live.get("o3"),
            live.get("so2"),  live.get("co"),
            live.get("aqi"),  live.get("aqi_category"),
            live.get("dominant_pol"),
            live.get("source","WAQI"),
            datetime.now()
        ))
        conn.commit()
        cur.close()
    except Exception as e:
        log.error(f"save_aq_reading station {station_id}: {e}")
        try: conn.rollback()
        except: pass

# ── SAVE Weather to DB ────────────────────────────────────────
def save_weather_reading(conn, station_id, wx):
    """INSERT one weather row into weather_readings."""
    if not conn or not wx: return
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO weather_readings
              (station_id, temperature_c, feels_like_c, humidity_pct,
               wind_speed_ms, wind_dir_deg, cloud_cover_pct,
               precipitation_mm, pressure_hpa, weather_code, source, recorded_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            station_id,
            wx.get("temperature_c"),   wx.get("feels_like_c"),
            wx.get("humidity_pct"),
            wx.get("wind_speed_ms"),   wx.get("wind_dir_deg"),
            wx.get("cloud_cover_pct"), wx.get("precipitation_mm"),
            wx.get("pressure_hpa"),    wx.get("weather_code"),
            "Open-Meteo",
            datetime.now()
        ))
        conn.commit()
        cur.close()
    except Exception as e:
        log.error(f"save_weather station {station_id}: {e}")
        try: conn.rollback()
        except: pass

# ── SAVE data_log row ─────────────────────────────────────────
def log_fetch(conn, fetch_type, total, waqi_hits, demo_hits, errors=""):
    if not conn: return
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO data_log (fetch_type, stations_fetched, waqi_hits, demo_hits, errors)
            VALUES (%s,%s,%s,%s,%s)
        """, (fetch_type, total, waqi_hits, demo_hits, errors[:500] if errors else None))
        conn.commit()
        cur.close()
    except Exception as e:
        log.error(f"log_fetch: {e}")

# ═══════════════════════════════════════════════════════════════
# ROUTES
# ═══════════════════════════════════════════════════════════════

@app.route('/')
def index():
    return render_template('index.html')

# ── /api/stations ─────────────────────────────────────────────
@app.route('/api/stations')
def get_stations():
    """
    Returns live AQ for all 50 stations.
    For each station:
      1. Try WAQI geo lookup
      2. If WAQI returns data → save to DB, return live
      3. If WAQI fails → use demo ±noise, still return result
    Also writes a data_log summary row.
    """
    result     = []
    waqi_hits  = 0
    demo_hits  = 0
    errors     = []
    db_conn    = get_db()  # single connection reused for all inserts

    for s in STATIONS:
        live = waqi_fetch(s["lat"], s["lon"])

        if live and live.get("aqi"):
            waqi_hits += 1
            # Use WAQI data; fallback pm values from demo if WAQI returned None
            rec = {
                "id":           s["id"],
                "name":         s["name"],
                "province":     s["province"],
                "lat":          s["lat"],
                "lon":          s["lon"],
                "pm25":         live["pm25"]  if live["pm25"]  is not None else round(s["pm25"]*random.uniform(.9,1.1),1),
                "pm10":         live["pm10"]  if live["pm10"]  is not None else round(s["pm10"]*random.uniform(.9,1.1),1),
                "no2":          live.get("no2"),
                "o3":           live.get("o3"),
                "so2":          live.get("so2"),
                "co":           live.get("co"),
                "aqi":          live["aqi"],
                "aqi_category": live["aqi_category"],
                "color":        live["color"],
                "dominant_pol": live.get("dominant_pol"),
                "recorded_at":  live.get("recorded_at"),
                "source":       "WAQI",
            }
            # ── SAVE TO DATABASE ──────────────────────────────
            save_aq_reading(db_conn, s["id"], live)
        else:
            demo_hits += 1
            if live is None:
                errors.append(s["name"])
            # Demo fallback ±10% noise
            pm25 = round(s["pm25"] * random.uniform(0.90, 1.10), 1)
            pm10 = round(s["pm10"] * random.uniform(0.90, 1.10), 1)
            aqi  = aqi_from_pm25(pm25)
            cat, color = aqi_cat(aqi)
            rec = {
                "id":           s["id"],
                "name":         s["name"],
                "province":     s["province"],
                "lat":          s["lat"],
                "lon":          s["lon"],
                "pm25":         pm25,
                "pm10":         pm10,
                "aqi":          aqi,
                "aqi_category": cat,
                "color":        color,
                "recorded_at":  datetime.now().isoformat(),
                "source":       "Demo",
            }
            # Even demo data gets saved so DB fills up for history
            save_aq_reading(db_conn, s["id"], {
                "pm25": pm25, "pm10": pm10,
                "aqi": aqi, "aqi_category": cat,
                "dominant_pol": "pm25", "source": "Demo",
            })

        result.append(rec)

    # Log this fetch cycle
    log_fetch(db_conn, "aq", len(STATIONS), waqi_hits, demo_hits,
              ", ".join(errors) if errors else "")
    if db_conn:
        try: db_conn.close()
        except: pass

    log.info(f"/api/stations: {len(result)} stations | WAQI={waqi_hits} Demo={demo_hits}")

    # Cleanup old data — runs roughly once every 2 hours
    # At 3-min fetches: 1 in 40 chance = triggers ~once per 2 hrs
    if random.randint(1, 40) == 1:
        cleanup_old_data()

    return jsonify(result)

# ── /api/waqi (single point, for map click) ───────────────────
@app.route('/api/waqi')
def get_waqi():
    lat = request.args.get("lat", type=float, default=30.3753)
    lon = request.args.get("lon", type=float, default=69.3451)
    data = waqi_fetch(lat, lon)
    if data:
        return jsonify(data)
    return jsonify({"error": "No WAQI data available for this location"}), 404

# ── /api/weather (Open-Meteo, saves to DB) ───────────────────
WMO_DESC = {
    0:"Clear sky",1:"Mainly clear",2:"Partly cloudy",3:"Overcast",
    45:"Fog",48:"Icy fog",51:"Light drizzle",53:"Moderate drizzle",
    55:"Dense drizzle",61:"Slight rain",63:"Moderate rain",65:"Heavy rain",
    71:"Slight snow",73:"Moderate snow",75:"Heavy snow",
    80:"Slight showers",81:"Moderate showers",82:"Violent showers",
    95:"Thunderstorm",99:"Thunderstorm + hail",
}

@app.route('/api/weather')
def get_weather():
    lat         = request.args.get("lat", 30.3753)
    lon         = request.args.get("lon", 69.3451)
    station_id  = request.args.get("station_id", type=int)
    try:
        url    = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude":  lat, "longitude": lon,
            "current":   [
                "temperature_2m","apparent_temperature",
                "relative_humidity_2m","wind_speed_10m",
                "wind_direction_10m","cloud_cover",
                "precipitation","weather_code","surface_pressure"
            ],
            "timezone":      "Asia/Karachi",
            "forecast_days": 1,
        }
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        cur  = r.json().get("current", {})
        code = cur.get("weather_code", 0)

        wx = {
            "temperature_c":    cur.get("temperature_2m"),
            "feels_like_c":     cur.get("apparent_temperature"),
            "humidity_pct":     cur.get("relative_humidity_2m"),
            "wind_speed_kmh":   cur.get("wind_speed_10m"),
            "wind_speed_ms":    round(cur.get("wind_speed_10m",0)/3.6, 2),
            "wind_direction":   cur.get("wind_direction_10m"),
            "wind_dir_deg":     cur.get("wind_direction_10m"),
            "cloud_cover_pct":  cur.get("cloud_cover"),
            "precipitation_mm": cur.get("precipitation"),
            "pressure_hpa":     cur.get("surface_pressure"),
            "weather_code":     code,
            "weather_description": WMO_DESC.get(code, "—"),
            "source":           "Open-Meteo",
            "lat": float(lat), "lon": float(lon),
        }

        # ── SAVE weather to DB if station_id provided ─────────
        if station_id:
            conn = get_db()
            if conn:
                save_weather_reading(conn, station_id, wx)
                conn.close()

        return jsonify(wx)
    except Exception as e:
        log.error(f"Open-Meteo: {e}")
        return jsonify({"error": str(e)}), 500

# ── /api/wind-grid ────────────────────────────────────────────
@app.route('/api/wind-grid')
def get_wind_grid():
    try:
        r = requests.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": 30.5, "longitude": 69.0,
            "hourly": ["wind_speed_10m","wind_direction_10m"],
            "timezone": "Asia/Karachi", "forecast_days": 1,
        }, timeout=8)
        r.raise_for_status()
        hourly = r.json().get("hourly", {})
        hi     = datetime.now().hour
        spd    = hourly.get("wind_speed_10m",  [5]*24)[hi]   # km/h
        dirr   = hourly.get("wind_direction_10m",[180]*24)[hi]
        rad    = math.radians(dirr)
        # Convert km/h wind direction to U/V in m/s
        spd_ms = spd / 3.6
        bu     = -spd_ms * math.sin(rad)
        bv     = -spd_ms * math.cos(rad)
        nx, ny = 18, 14
        n      = nx * ny
        return jsonify({
            "header": {"la1":23,"la2":37,"lo1":60,"lo2":77,"nx":nx,"ny":ny,"dx":0.94,"dy":1.0},
            "u":   [round(bu + random.gauss(0, 0.2), 3) for _ in range(n)],
            "v":   [round(bv + random.gauss(0, 0.2), 3) for _ in range(n)],
            "base_u": round(bu, 3),
            "base_v": round(bv, 3),
            "speed_kmh": spd, "direction_deg": dirr,
            "source": "Open-Meteo",
        })
    except Exception as e:
        log.warning(f"wind-grid fallback: {e}")
        bu, bv = 1.2, 0.4
        return jsonify({
            "header":{"la1":23,"la2":37,"lo1":60,"lo2":77,"nx":10,"ny":8,"dx":1.7,"dy":1.75},
            "u": [round(bu+random.gauss(0,.15),3) for _ in range(80)],
            "v": [round(bv+random.gauss(0,.15),3) for _ in range(80)],
            "base_u": bu, "base_v": bv, "source": "fallback",
        })

# ── /api/disasters ────────────────────────────────────────────
@app.route('/api/disasters')
def get_disasters():
    try:
        r = requests.get(
            "https://www.gdacs.org/gdacsapi/api/events/geteventlist/EVENTS",
            params={"eventlist":"EQ,TC,FL,VO,DR,WF","alertlevel":"Green,Orange,Red"},
            timeout=12
        )
        if r.status_code == 200:
            alerts = []
            TYPE_MAP = {"EQ":"Earthquake","TC":"Tropical Cyclone","FL":"Flood",
                        "VO":"Volcano","DR":"Drought","WF":"Wildfire","LS":"Landslide"}
            for f in r.json().get("features",[]):
                p   = f.get("properties",{})
                geo = f.get("geometry",{}).get("coordinates",[0,0])
                lat, lon = geo[1], geo[0]
                if not (18 <= lat <= 40 and 55 <= lon <= 82): continue
                alerts.append({
                    "id":        str(p.get("eventid","")),
                    "type":      p.get("eventtype",""),
                    "type_name": TYPE_MAP.get(p.get("eventtype",""),"Alert"),
                    "severity":  p.get("alertlevel","Green").lower(),
                    "title":     p.get("eventname","Alert"),
                    "lat": lat, "lon": lon, "source": "GDACS",
                })
            if alerts:
                return jsonify({"count":len(alerts),"alerts":alerts,"source":"GDACS"})
    except Exception as e:
        log.warning(f"GDACS: {e}")

    demo = [
        {"id":"d1","type":"FL","type_name":"Flood","severity":"high",
         "title":"Flood Alert — Sindh River Basin","lat":27.5,"lon":68.5,"source":"Demo"},
        {"id":"d2","type":"EQ","type_name":"Earthquake","severity":"medium",
         "title":"Seismic Activity — Balochistan","lat":29.5,"lon":66.5,"source":"Demo"},
        {"id":"d3","type":"LS","type_name":"Landslide","severity":"medium",
         "title":"Landslide Warning — KPK Hills","lat":34.5,"lon":72.0,"source":"Demo"},
        {"id":"d4","type":"DR","type_name":"Drought","severity":"low",
         "title":"Drought — Thar Desert","lat":25.0,"lon":70.0,"source":"Demo"},
    ]
    return jsonify({"count":len(demo),"alerts":demo,"source":"Demo"})

# ── /api/check-disasters ──────────────────────────────────────
@app.route('/api/check-disasters')
def check_disasters():
    lat = request.args.get("lat", type=float, default=30.37)
    lon = request.args.get("lon", type=float, default=69.34)
    conn = get_db()
    if conn:
        try:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                SELECT alert_type, severity, title, description
                FROM disaster_alerts WHERE is_active=TRUE
                AND ST_Intersects(geom, ST_SetSRID(ST_MakePoint(%s,%s),4326))
            """, (lon, lat))
            rows = cur.fetchall(); cur.close(); conn.close()
            return jsonify(list(rows))
        except Exception as e:
            log.error(e); conn.close()
    return jsonify([])

# ── /api/nearest-station ──────────────────────────────────────
@app.route('/api/nearest-station')
def nearest_station():
    lat = request.args.get("lat", type=float, default=30.37)
    lon = request.args.get("lon", type=float, default=69.34)
    conn = get_db()
    if conn:
        try:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                SELECT id, name, province,
                       ST_X(geom) lon, ST_Y(geom) lat,
                       ROUND(ST_Distance(geom::geography,
                           ST_SetSRID(ST_MakePoint(%s,%s),4326)::geography)::numeric/1000,1) dist_km
                FROM monitoring_stations WHERE is_active=TRUE
                ORDER BY dist_km LIMIT 1
            """, (lon, lat))
            row = cur.fetchone(); cur.close(); conn.close()
            if row: return jsonify(dict(row))
        except Exception as e: log.error(e); conn.close()
    best = min(STATIONS, key=lambda s:(s["lat"]-lat)**2+(s["lon"]-lon)**2)
    return jsonify({**best, "dist_km": round(math.sqrt((best["lat"]-lat)**2+(best["lon"]-lon)**2)*111,1)})

# ── /api/stations-in-radius ───────────────────────────────────
@app.route('/api/stations-in-radius')
def stations_in_radius():
    lat = request.args.get("lat", type=float, default=30.37)
    lon = request.args.get("lon", type=float, default=69.34)
    km  = request.args.get("radius_km", type=float, default=200)
    conn = get_db()
    if conn:
        try:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                SELECT id, name, province,
                       ST_X(geom) lon, ST_Y(geom) lat,
                       ROUND(ST_Distance(geom::geography,
                           ST_SetSRID(ST_MakePoint(%s,%s),4326)::geography)::numeric/1000,1) dist_km
                FROM monitoring_stations
                WHERE ST_DWithin(geom::geography,
                      ST_SetSRID(ST_MakePoint(%s,%s),4326)::geography, %s*1000)
                AND is_active=TRUE ORDER BY dist_km
            """, (lon,lat,lon,lat,km))
            rows = cur.fetchall(); cur.close(); conn.close()
            return jsonify(list(rows))
        except Exception as e: log.error(e); conn.close()
    return jsonify([
        dict(s, dist_km=round(math.sqrt((s["lat"]-lat)**2+(s["lon"]-lon)**2)*111,1))
        for s in STATIONS if math.sqrt((s["lat"]-lat)**2+(s["lon"]-lon)**2)*111 <= km
    ])

# ── /api/history/<station_id> ─────────────────────────────────
@app.route('/api/history/<int:station_id>')
def get_history(station_id):
    """Return last 48 AQ readings from DB for a station (for charts)."""
    conn = get_db()
    if not conn:
        return jsonify({"error":"DB not available"}), 503
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT r.pm25, r.pm10, r.aqi, r.aqi_category,
                   r.no2, r.o3, r.so2, r.co, r.source,
                   r.recorded_at
            FROM air_quality_readings r
            WHERE r.station_id = %s
            ORDER BY r.recorded_at DESC
            LIMIT 48
        """, (station_id,))
        rows = cur.fetchall(); cur.close(); conn.close()
        return jsonify(list(rows))
    except Exception as e:
        log.error(e); conn.close()
        return jsonify({"error": str(e)}), 500

# ── /api/db-stats ─────────────────────────────────────────────
@app.route('/api/db-stats')
def db_stats():
    """Show how much data is saved — useful for debugging empty tables."""
    conn = get_db()
    if not conn:
        return jsonify({"error":"DB not available"}), 503
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT
              (SELECT COUNT(*) FROM monitoring_stations)   AS stations,
              (SELECT COUNT(*) FROM air_quality_readings)  AS aq_readings,
              (SELECT COUNT(*) FROM weather_readings)      AS wx_readings,
              (SELECT COUNT(*) FROM data_log)              AS log_entries,
              (SELECT MAX(recorded_at) FROM air_quality_readings) AS last_aq,
              (SELECT MAX(recorded_at) FROM weather_readings)     AS last_wx
        """)
        row = cur.fetchone(); cur.close(); conn.close()
        return jsonify(dict(row))
    except Exception as e:
        conn.close()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("=" * 58)
    print("  🇵🇰  AQMS Pakistan  —  http://localhost:5000")
    print("=" * 58)
    print(f"  WAQI token : {WAQI_TOKEN[:14]}...")
    print(f"  DB host    : {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print(f"  DB name    : {DB_CONFIG['dbname']}")
    print(f"  Stations   : {len(STATIONS)}")
    print("")
    print("  Check DB is filling:  http://localhost:5000/api/db-stats")
    print("  Live data test:       http://localhost:5000/api/waqi?lat=31.55&lon=74.34")
    print("=" * 58)
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
