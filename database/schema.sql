-- ============================================================
-- AQMS Pakistan — Full Database Schema v4
-- PostgreSQL + PostGIS
-- Run this entire file in pgAdmin Query Tool or psql
-- ============================================================

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- ============================================================
-- TABLE 1: monitoring_stations
-- ============================================================
CREATE TABLE IF NOT EXISTS monitoring_stations (
    id           SERIAL PRIMARY KEY,
    name         VARCHAR(100) NOT NULL,
    province     VARCHAR(60),
    country      VARCHAR(50) DEFAULT 'Pakistan',
    population   BIGINT,
    elevation_m  FLOAT,
    is_active    BOOLEAN DEFAULT TRUE,
    geom         GEOMETRY(Point, 4326) NOT NULL,
    created_at   TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_stations_geom ON monitoring_stations USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_stations_name ON monitoring_stations(name);

-- ============================================================
-- TABLE 2: air_quality_readings   ← now includes all pollutants
-- ============================================================
CREATE TABLE IF NOT EXISTS air_quality_readings (
    id           SERIAL PRIMARY KEY,
    station_id   INTEGER REFERENCES monitoring_stations(id) ON DELETE CASCADE,
    -- Particulates
    pm25         FLOAT,          -- µg/m³
    pm10         FLOAT,          -- µg/m³
    -- Gases (added v4)
    no2          FLOAT,          -- µg/m³  Nitrogen Dioxide
    o3           FLOAT,          -- µg/m³  Ozone
    so2          FLOAT,          -- µg/m³  Sulfur Dioxide
    co           FLOAT,          -- ppm    Carbon Monoxide
    -- AQI
    aqi          INTEGER,
    aqi_category VARCHAR(40),
    dominant_pol VARCHAR(20),    -- e.g. pm25, no2
    source       VARCHAR(50) DEFAULT 'WAQI',
    recorded_at  TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_aq_station_time ON air_quality_readings(station_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_aq_recorded_at  ON air_quality_readings(recorded_at DESC);

-- ============================================================
-- TABLE 3: weather_readings   ← already complete, no changes
-- ============================================================
CREATE TABLE IF NOT EXISTS weather_readings (
    id               SERIAL PRIMARY KEY,
    station_id       INTEGER REFERENCES monitoring_stations(id) ON DELETE CASCADE,
    temperature_c    FLOAT,
    feels_like_c     FLOAT,      -- added v4
    humidity_pct     FLOAT,
    wind_speed_ms    FLOAT,
    wind_dir_deg     FLOAT,
    cloud_cover_pct  FLOAT,
    precipitation_mm FLOAT,
    pressure_hpa     FLOAT,      -- added v4
    weather_code     INTEGER,
    source           VARCHAR(50) DEFAULT 'Open-Meteo',
    recorded_at      TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_wx_station_time ON weather_readings(station_id, recorded_at DESC);

-- ============================================================
-- TABLE 4: disaster_alerts
-- ============================================================
CREATE TABLE IF NOT EXISTS disaster_alerts (
    id          SERIAL PRIMARY KEY,
    alert_type  VARCHAR(50) NOT NULL,
    severity    VARCHAR(20) NOT NULL,
    title       VARCHAR(200),
    description TEXT,
    source      VARCHAR(100) DEFAULT 'GDACS',
    external_id VARCHAR(100),
    geom        GEOMETRY(Geometry, 4326),
    is_active   BOOLEAN DEFAULT TRUE,
    issued_at   TIMESTAMP,
    expires_at  TIMESTAMP,
    created_at  TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_disasters_geom   ON disaster_alerts USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_disasters_active ON disaster_alerts(is_active, alert_type);

-- ============================================================
-- TABLE 5: data_log   ← new — records every fetch for auditing
-- ============================================================
CREATE TABLE IF NOT EXISTS data_log (
    id          SERIAL PRIMARY KEY,
    fetch_type  VARCHAR(30),    -- 'aq', 'weather', 'disaster'
    stations_fetched INTEGER,
    waqi_hits   INTEGER DEFAULT 0,
    demo_hits   INTEGER DEFAULT 0,
    errors      TEXT,
    fetched_at  TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- SEED: 50 monitoring_stations across Pakistan
-- Covers Punjab, Sindh, Balochistan, KPK, GB, AJK, ICT
-- Using INSERT ... ON CONFLICT (id) DO NOTHING so safe to re-run
-- ============================================================

-- Add a unique constraint on id if not already primary key based
-- (SERIAL already makes id PK so ON CONFLICT (id) works)

INSERT INTO monitoring_stations (id, name, province, population, geom) VALUES
-- ── PUNJAB (15 stations) ────────────────────────────────────
( 1, 'Lahore',           'Punjab',       13100000, ST_SetSRID(ST_MakePoint(74.3436,31.5497),4326)),
( 2, 'Faisalabad',       'Punjab',        3640000, ST_SetSRID(ST_MakePoint(73.1350,31.4504),4326)),
( 3, 'Rawalpindi',       'Punjab',        2098231, ST_SetSRID(ST_MakePoint(73.0169,33.5651),4326)),
( 4, 'Gujranwala',       'Punjab',        2027001, ST_SetSRID(ST_MakePoint(74.1945,32.1877),4326)),
( 5, 'Multan',           'Punjab',        1871843, ST_SetSRID(ST_MakePoint(71.5249,30.1575),4326)),
( 6, 'Sialkot',          'Punjab',         655852, ST_SetSRID(ST_MakePoint(74.5229,32.4945),4326)),
( 7, 'Bahawalpur',       'Punjab',         762111, ST_SetSRID(ST_MakePoint(71.6833,29.4000),4326)),
( 8, 'Sargodha',         'Punjab',         659862, ST_SetSRID(ST_MakePoint(72.6711,32.0836),4326)),
( 9, 'Sheikhupura',      'Punjab',         473129, ST_SetSRID(ST_MakePoint(73.9783,31.7131),4326)),
(10, 'Dera Ghazi Khan',  'Punjab',         464742, ST_SetSRID(ST_MakePoint(70.6403,30.0459),4326)),
(11, 'Kasur',            'Punjab',         357525, ST_SetSRID(ST_MakePoint(74.4467,31.1155),4326)),
(12, 'Sahiwal',          'Punjab',         247706, ST_SetSRID(ST_MakePoint(73.1060,30.6706),4326)),
(13, 'Okara',            'Punjab',         232386, ST_SetSRID(ST_MakePoint(73.4458,30.8081),4326)),
(14, 'Rahim Yar Khan',   'Punjab',         420419, ST_SetSRID(ST_MakePoint(70.2952,28.4202),4326)),
(15, 'Chakwal',          'Punjab',          72472, ST_SetSRID(ST_MakePoint(72.8585,32.9304),4326)),
(16, 'Mianwali',         'Punjab',          75523, ST_SetSRID(ST_MakePoint(71.5376,32.5836),4326)),
(17, 'Jhang',            'Punjab',         341219, ST_SetSRID(ST_MakePoint(72.3168,31.2690),4326)),

-- ── SINDH (13 stations) ─────────────────────────────────────
(20, 'Karachi',          'Sindh',        14910000, ST_SetSRID(ST_MakePoint(67.0011,24.8607),4326)),
(21, 'Hyderabad',        'Sindh',         1732693, ST_SetSRID(ST_MakePoint(68.3578,25.3960),4326)),
(22, 'Sukkur',           'Sindh',          499900, ST_SetSRID(ST_MakePoint(68.8574,27.7052),4326)),
(23, 'Larkana',          'Sindh',          490508, ST_SetSRID(ST_MakePoint(68.2158,27.5631),4326)),
(24, 'Nawabshah',        'Sindh',          188866, ST_SetSRID(ST_MakePoint(68.4096,26.2483),4326)),
(25, 'Mirpur Khas',      'Sindh',          233914, ST_SetSRID(ST_MakePoint(69.0159,25.5251),4326)),
(26, 'Jacobabad',        'Sindh',          190776, ST_SetSRID(ST_MakePoint(68.4386,28.2810),4326)),
(27, 'Shikarpur',        'Sindh',          160477, ST_SetSRID(ST_MakePoint(68.6382,27.9571),4326)),
(28, 'Khairpur',         'Sindh',          198801, ST_SetSRID(ST_MakePoint(68.7592,27.5295),4326)),
(29, 'Dadu',             'Sindh',           98382, ST_SetSRID(ST_MakePoint(67.7766,26.7319),4326)),
(30, 'Sanghar',          'Sindh',           88659, ST_SetSRID(ST_MakePoint(68.9481,26.0466),4326)),
(31, 'Badin',            'Sindh',           76905, ST_SetSRID(ST_MakePoint(68.8383,24.6550),4326)),
(32, 'Tharparkar',       'Sindh',           40404, ST_SetSRID(ST_MakePoint(69.7361,25.3617),4326)),

-- ── BALOCHISTAN (10 stations) ───────────────────────────────
(35, 'Quetta',           'Balochistan',   1001205, ST_SetSRID(ST_MakePoint(66.9750,30.1798),4326)),
(36, 'Turbat',           'Balochistan',    104407, ST_SetSRID(ST_MakePoint(63.0711,25.9917),4326)),
(37, 'Gwadar',           'Balochistan',     90762, ST_SetSRID(ST_MakePoint(62.3220,25.1266),4326)),
(38, 'Khuzdar',          'Balochistan',     62132, ST_SetSRID(ST_MakePoint(66.6167,27.8000),4326)),
(39, 'Chaman',           'Balochistan',     80438, ST_SetSRID(ST_MakePoint(66.4512,30.9210),4326)),
(40, 'Sibi',             'Balochistan',     58516, ST_SetSRID(ST_MakePoint(67.8773,29.5448),4326)),
(41, 'Hub',              'Balochistan',    196268, ST_SetSRID(ST_MakePoint(66.8833,25.0500),4326)),
(42, 'Nushki',           'Balochistan',     30000, ST_SetSRID(ST_MakePoint(66.0214,29.5542),4326)),
(43, 'Dalbandin',        'Balochistan',     20000, ST_SetSRID(ST_MakePoint(64.4062,28.8881),4326)),
(44, 'Loralai',          'Balochistan',     60000, ST_SetSRID(ST_MakePoint(68.5981,30.3700),4326)),

-- ── KPK (7 stations) ────────────────────────────────────────
(45, 'Peshawar',         'KPK',           1970042, ST_SetSRID(ST_MakePoint(71.5249,34.0151),4326)),
(46, 'Abbottabad',       'KPK',            148587, ST_SetSRID(ST_MakePoint(73.2215,34.1688),4326)),
(47, 'Mardan',           'KPK',            358604, ST_SetSRID(ST_MakePoint(72.0447,34.1988),4326)),
(48, 'Mansehra',         'KPK',             50000, ST_SetSRID(ST_MakePoint(73.2000,34.3333),4326)),
(49, 'Swat',             'KPK',            134396, ST_SetSRID(ST_MakePoint(72.3563,34.7701),4326)),
(50, 'Kohat',            'KPK',            140000, ST_SetSRID(ST_MakePoint(71.4429,33.5869),4326)),
(51, 'Dera Ismail Khan', 'KPK',            180000, ST_SetSRID(ST_MakePoint(70.9027,31.8320),4326)),

-- ── ICT + Northern / AJK (5 stations) ───────────────────────
(55, 'Islamabad',        'ICT',           1014825, ST_SetSRID(ST_MakePoint(73.0479,33.6844),4326)),
(56, 'Gilgit',           'GB',             216760, ST_SetSRID(ST_MakePoint(74.3081,35.9208),4326)),
(57, 'Skardu',           'GB',              80000, ST_SetSRID(ST_MakePoint(75.5489,35.3075),4326)),
(58, 'Muzaffarabad',     'AJK',            725000, ST_SetSRID(ST_MakePoint(73.4700,34.3700),4326)),
(59, 'Mirpur AJK',       'AJK',            455762, ST_SetSRID(ST_MakePoint(73.7518,33.1474),4326))

ON CONFLICT (id) DO NOTHING;

-- ============================================================
-- RESET sequence so new rows don't collide
-- ============================================================
SELECT setval('monitoring_stations_id_seq', 100, true);

-- ============================================================
-- UPDATED VIEWS  (include new pollutant columns)
-- ============================================================
DROP VIEW IF EXISTS v_latest_air_quality;
CREATE VIEW v_latest_air_quality AS
SELECT DISTINCT ON (s.id)
    s.id, s.name, s.province,
    ST_X(s.geom) AS lon,
    ST_Y(s.geom) AS lat,
    r.pm25, r.pm10,
    r.no2, r.o3, r.so2, r.co,
    r.aqi, r.aqi_category, r.dominant_pol,
    r.source, r.recorded_at
FROM monitoring_stations s
LEFT JOIN air_quality_readings r ON r.station_id = s.id
WHERE s.is_active = TRUE
ORDER BY s.id, r.recorded_at DESC NULLS LAST;

DROP VIEW IF EXISTS v_latest_weather;
CREATE VIEW v_latest_weather AS
SELECT DISTINCT ON (s.id)
    s.id, s.name, s.province,
    ST_X(s.geom) AS lon,
    ST_Y(s.geom) AS lat,
    w.temperature_c, w.feels_like_c,
    w.humidity_pct,
    w.wind_speed_ms, w.wind_dir_deg,
    w.cloud_cover_pct, w.precipitation_mm,
    w.pressure_hpa, w.weather_code,
    w.source, w.recorded_at
FROM monitoring_stations s
LEFT JOIN weather_readings w ON w.station_id = s.id
WHERE s.is_active = TRUE
ORDER BY s.id, w.recorded_at DESC NULLS LAST;

-- Combined view for dashboard
DROP VIEW IF EXISTS v_dashboard;
CREATE VIEW v_dashboard AS
SELECT
    s.id, s.name, s.province,
    ST_X(s.geom) AS lon,
    ST_Y(s.geom) AS lat,
    aq.pm25, aq.pm10, aq.no2, aq.o3, aq.so2, aq.co,
    aq.aqi, aq.aqi_category, aq.dominant_pol,
    wx.temperature_c, wx.humidity_pct,
    wx.wind_speed_ms, wx.wind_dir_deg,
    wx.cloud_cover_pct, wx.precipitation_mm,
    wx.pressure_hpa, wx.weather_code,
    aq.recorded_at AS aq_time,
    wx.recorded_at AS wx_time
FROM monitoring_stations s
LEFT JOIN v_latest_air_quality aq ON aq.id = s.id
LEFT JOIN v_latest_weather     wx ON wx.id = s.id
WHERE s.is_active = TRUE;

-- ============================================================
-- USEFUL SPATIAL QUERIES  (copy-paste these in pgAdmin)
-- ============================================================

-- Q1: Latest reading per station with source
-- SELECT name, province, pm25, pm10, aqi, aqi_category, recorded_at
-- FROM v_latest_air_quality ORDER BY aqi DESC NULLS LAST;

-- Q2: All data logged today
-- SELECT s.name, r.pm25, r.aqi, r.recorded_at
-- FROM air_quality_readings r JOIN monitoring_stations s ON s.id=r.station_id
-- WHERE r.recorded_at >= CURRENT_DATE ORDER BY r.recorded_at DESC;

-- Q3: Nearest station to Lahore
-- SELECT name, ST_Distance(geom::geography,
--     ST_SetSRID(ST_MakePoint(74.34,31.55),4326)::geography)/1000 AS dist_km
-- FROM monitoring_stations ORDER BY dist_km LIMIT 3;

-- Q4: Stations within 200km of Karachi
-- SELECT name, province
-- FROM monitoring_stations
-- WHERE ST_DWithin(geom::geography,
--     ST_SetSRID(ST_MakePoint(67.0,24.86),4326)::geography, 200000);

-- Q5: PM2.5 trend for Lahore (last 24 readings)
-- SELECT r.pm25, r.aqi, r.recorded_at
-- FROM air_quality_readings r
-- JOIN monitoring_stations s ON s.id=r.station_id
-- WHERE s.name='Lahore' ORDER BY r.recorded_at DESC LIMIT 24;

-- Q6: Province average AQI
-- SELECT s.province, ROUND(AVG(r.aqi)) avg_aqi, COUNT(*) readings
-- FROM air_quality_readings r JOIN monitoring_stations s ON s.id=r.station_id
-- WHERE r.recorded_at >= NOW()-INTERVAL '24 hours'
-- GROUP BY s.province ORDER BY avg_aqi DESC;

-- Q7: Stations with NO2 data (check what's logging)
-- SELECT s.name, r.no2, r.o3, r.so2, r.co, r.recorded_at
-- FROM air_quality_readings r JOIN monitoring_stations s ON s.id=r.station_id
-- WHERE r.no2 IS NOT NULL ORDER BY r.recorded_at DESC LIMIT 20;

-- Q8: How much data is logged?
-- SELECT 'air_quality' AS tbl, COUNT(*) FROM air_quality_readings
-- UNION ALL SELECT 'weather', COUNT(*) FROM weather_readings
-- UNION ALL SELECT 'data_log', COUNT(*) FROM data_log;
