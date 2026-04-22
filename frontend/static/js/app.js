/**
 * AQMS Pakistan — app.js v4
 * Fixed wind animation (slow, nullschool-style),
 * full sidebar pollutants, WAQI + Open-Meteo, 50 stations
 */

// ═══════════════════════════════════════════════
// TILE LAYERS
// ═══════════════════════════════════════════════
const TILES = {
  dark:      { url:'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',        attr:'© CartoDB' },
  light:     { url:'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',       attr:'© CartoDB' },
  terrain:   { url:'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',                     attr:'© OpenTopoMap' },
  satellite: { url:'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr:'© Esri' }
};
const NASA_TILE = 'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/2024-04-01/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg';

// ═══════════════════════════════════════════════
// AQI UTILITIES
// ═══════════════════════════════════════════════
function aqiFromPM25(pm) {
  if (!pm || pm < 0) return 0;
  const bp = [[0,12,0,50],[12.1,35.4,51,100],[35.5,55.4,101,150],[55.5,150.4,151,200],[150.5,250.4,201,300],[250.5,500.4,301,500]];
  for (const [cl,ch,il,ih] of bp)
    if (pm >= cl && pm <= ch) return Math.round(((ih-il)/(ch-cl))*(pm-cl)+il);
  return 500;
}
function aqiColor(aqi) {
  if (!aqi || aqi <= 0) return '#888';
  if (aqi <= 50)  return '#00e400';
  if (aqi <= 100) return '#ffff00';
  if (aqi <= 150) return '#ff7e00';
  if (aqi <= 200) return '#ff0000';
  if (aqi <= 300) return '#8f3f97';
  return '#7e0023';
}
function aqiCat(aqi) {
  if (aqi <= 50)  return 'Good';
  if (aqi <= 100) return 'Moderate';
  if (aqi <= 150) return 'Unhealthy (Sensitive)';
  if (aqi <= 200) return 'Unhealthy';
  if (aqi <= 300) return 'Very Unhealthy';
  return 'Hazardous';
}
function wmoEmoji(c) {
  if (!c && c !== 0) return '🌡';
  if (c === 0)  return '☀️';
  if (c <= 2)   return '🌤';
  if (c === 3)  return '☁️';
  if (c <= 48)  return '🌫';
  if (c <= 67)  return '🌧';
  if (c <= 77)  return '❄️';
  if (c <= 82)  return '🌧';
  if (c <= 99)  return '⛈';
  return '🌡';
}
function windDir(deg) {
  if (deg === undefined || deg === null) return '';
  return ['N','NE','E','SE','S','SW','W','NW'][Math.round(deg/45)%8];
}
function fmt(v, d=1) {
  if (v === undefined || v === null) return '—';
  return (typeof v === 'number') ? v.toFixed(d) : String(v);
}

// ═══════════════════════════════════════════════
// MAIN APP
// ═══════════════════════════════════════════════
class AQMS {
  constructor() {
    this.map            = null;
    this.currentTile    = null;
    this.stationMarkers = [];
    this.heatLayer      = null;
    this.disasterMarkers= [];
    this.cloudLayer     = null;
    this.stationData    = [];
    this.windGridData   = null;

    // Wind state
    this.windCanvas  = null;
    this.windCtx     = null;
    this.particles   = [];
    this.windVisible = false;
    this.windBaseU   = 1.0;   // m/s east component (fallback)
    this.windBaseV   = 0.3;   // m/s north component

    // ── KEY WIND SETTINGS ──────────────────────
    // Tune these to control how the animation looks:
    this.PARTICLE_COUNT = 500;    // fewer = cleaner (was 1800!)
    this.PARTICLE_SPEED = 0.18;   // pixels per frame base (was ~1.5 — now 8× slower)
    this.TRAIL_FADE     = 0.04;   // alpha fade per frame (lower = longer trails)
    this.MAX_AGE_MIN    = 150;    // frames before a particle respawns
    this.MAX_AGE_RANGE  = 150;    // + random up to this
    // ───────────────────────────────────────────

    this.layers = { pm25:true, pm10:false, heat:true, wind:true, disasters:true, clouds:false };

    this.init();
  }

  // ── INIT ──────────────────────────────────────
  init() {
    this.initMap();
    this.initWind();
    this.initEvents();
    this.fetchAll();
    setInterval(() => this.fetchAll(), 180000); // every 3 min
  }

  initMap() {
    this.map = L.map('map', { center:[29.5,69.5], zoom:6, zoomControl:true });
    this.setTile('dark');
    this.map.on('mousemove', e => {
      const el = document.getElementById('coordDisplay');
      if (el) el.textContent = `${e.latlng.lat.toFixed(4)}°N  ${e.latlng.lng.toFixed(4)}°E`;
    });
    this.map.on('click',                    e  => this.onMapClick(e.latlng));
    this.map.on('moveend zoomend resize',   ()  => this.resizeWindCanvas());
  }

  setTile(name) {
    if (this.currentTile) this.map.removeLayer(this.currentTile);
    const t = TILES[name];
    this.currentTile = L.tileLayer(t.url, { attribution:t.attr, maxZoom:19 }).addTo(this.map);
    document.querySelectorAll('.tile-btn').forEach(b =>
      b.classList.toggle('active', b.dataset.tile === name));
  }

  // ════════════════════════════════════════════════
  // WIND ANIMATION  —  Nullschool-style, slow + clean
  // ════════════════════════════════════════════════
  initWind() {
    this.windCanvas = document.getElementById('windCanvas');
    this.windCtx    = this.windCanvas.getContext('2d');
    this.resizeWindCanvas();
    this.spawnParticles();
    this.tickWind();    // start the loop
  }

  resizeWindCanvas() {
    const rect = this.map.getContainer().getBoundingClientRect();
    this.windCanvas.width  = rect.width;
    this.windCanvas.height = rect.height;
    this.spawnParticles();  // respawn after resize
  }

  spawnParticles() {
    const W = this.windCanvas.width, H = this.windCanvas.height;
    this.particles = Array.from({ length: this.PARTICLE_COUNT }, () =>
      this.newParticle(W, H, true)   // randomise age so they don't all spawn together
    );
  }

  /** Create one particle. If `randomAge=true`, start at a random age (for initial spawn). */
  newParticle(W, H, randomAge = false) {
    const maxAge = this.MAX_AGE_MIN + Math.random() * this.MAX_AGE_RANGE;
    return {
      x:      Math.random() * W,
      y:      Math.random() * H,
      age:    randomAge ? Math.random() * maxAge : 0,
      maxAge: maxAge,
      width:  0.4 + Math.random() * 0.7,
    };
  }

  /**
   * Look up wind vector (U east, V north) at canvas position (x,y).
   * When wind grid is available, uses bilinear-ish lookup.
   * Falls back to a smooth sine-wave westerly.
   */
  windAt(x, y) {
    const W = this.windCanvas.width, H = this.windCanvas.height;
    const t = performance.now() * 0.00008;  // very slow time variation

    // Gentle spatial variation so adjacent particles move slightly differently
    const wave = Math.sin(x/W*5 + t) * 0.15 + Math.cos(y/H*4 - t*0.7) * 0.1;

    if (this.windGridData) {
      const { header, u, v } = this.windGridData;
      const bounds = this.map.getBounds();
      const lat    = bounds.getNorth() - (y/H)*(bounds.getNorth()-bounds.getSouth());
      const lon    = bounds.getWest()  + (x/W)*(bounds.getEast() -bounds.getWest());
      // Clamp to grid bounds
      if (lat >= header.la1 && lat <= header.la2 && lon >= header.lo1 && lon <= header.lo2) {
        const col = Math.max(0, Math.min(header.nx-1, Math.round((lon-header.lo1)/header.dx)));
        const row = Math.max(0, Math.min(header.ny-1, Math.round((header.la2-lat)/header.dy)));
        const idx = row*header.nx + col;
        return {
          u: (u[idx] ?? this.windBaseU) + wave,
          v: (v[idx] ?? this.windBaseV) + wave*0.5,
        };
      }
    }
    // Smooth fallback: gentle SW→NE flow with mild variation
    return {
      u: this.windBaseU + wave,
      v: this.windBaseV + wave * 0.5 + Math.sin(x/W*3 + t*0.5)*0.08,
    };
  }

  tickWind() {
    const ctx = this.windCtx;
    const W   = this.windCanvas.width;
    const H   = this.windCanvas.height;

    if (!this.windVisible) {
      ctx.clearRect(0, 0, W, H);
      requestAnimationFrame(() => this.tickWind());
      return;
    }

    const isDark = document.documentElement.getAttribute('data-theme') !== 'light';

    // ── Trail fade — lower alpha = longer, more nullschool-like trails ──
    ctx.fillStyle = isDark
      ? `rgba(9,13,18,${this.TRAIL_FADE})`          // dark bg
      : `rgba(238,242,248,${this.TRAIL_FADE + 0.01})`; // light bg
    ctx.fillRect(0, 0, W, H);

    for (const p of this.particles) {
      const wind = this.windAt(p.x, p.y);
      const spd  = Math.hypot(wind.u, wind.v);          // current speed magnitude

      // Opacity: fade in (birth) → full → fade out (death)
      const life  = p.age / p.maxAge;                   // 0→1
      const alpha = Math.sin(life * Math.PI) * 0.52;    // smooth sine envelope

      // Record start position for this segment
      const px = p.x, py = p.y;

      // ── MOVE the particle ────────────────────────────────
      // PARTICLE_SPEED is pixels per frame; wind vector magnitude scales it.
      // A 5 m/s wind should move the particle visibly but slowly.
      const normSpd = Math.max(0.2, Math.min(spd / 3.0, 1.8)); // normalise to ~0.2–1.8
      p.x += wind.u / Math.max(spd, 0.01) * normSpd * this.PARTICLE_SPEED * W * 0.001;
      p.y -= wind.v / Math.max(spd, 0.01) * normSpd * this.PARTICLE_SPEED * H * 0.001;
      p.age++;

      // Respawn if out of bounds or too old
      if (p.age > p.maxAge || p.x < -4 || p.x > W+4 || p.y < -4 || p.y > H+4) {
        Object.assign(p, this.newParticle(W, H, false));
        continue;
      }

      // ── DRAW segment ────────────────────────────────────
      const speedNorm = Math.min(spd / 6, 1);  // for colour

      // Colour: cyan (slow) → white-green (fast) in dark; blue→teal in light
      let r, g, b;
      if (isDark) {
        r = Math.round(56  + speedNorm * 150);
        g = Math.round(200 + speedNorm *  40);
        b = Math.round(240 - speedNorm * 160);
      } else {
        r = Math.round(10  + speedNorm * 60);
        g = Math.round(100 + speedNorm * 130);
        b = Math.round(200 - speedNorm * 140);
      }

      ctx.beginPath();
      ctx.moveTo(px, py);
      ctx.lineTo(p.x, p.y);
      ctx.strokeStyle = `rgba(${r},${g},${b},${alpha})`;
      ctx.lineWidth   = p.width * (0.6 + speedNorm * 0.5);
      ctx.lineCap     = 'round';
      ctx.stroke();
    }

    requestAnimationFrame(() => this.tickWind());
  }

  // ═══════════════════════════════════════════════
  // DATA FETCHING
  // ═══════════════════════════════════════════════
  async fetchAll() {
    this.showLoading(true);
    try {
      const [stRes, disRes, windRes] = await Promise.allSettled([
        fetch('/api/stations').then(r => r.json()),
        fetch('/api/disasters').then(r => r.json()),
        fetch('/api/wind-grid').then(r => r.json()),
      ]);

      if (stRes.status === 'fulfilled' && Array.isArray(stRes.value)) {
        this.stationData = stRes.value;
        this.renderStations();
        this.renderHeatmap();
        this.updateStats();
      }
      if (disRes.status === 'fulfilled') {
        const alerts = disRes.value?.alerts || [];
        this.renderDisasters(alerts);
        this.setText('statAlerts', alerts.length);
      }
      if (windRes.status === 'fulfilled' && windRes.value?.header) {
        this.windGridData = windRes.value;
        this.windBaseU    = windRes.value.base_u ?? 1.0;
        this.windBaseV    = windRes.value.base_v ?? 0.3;
      }
      const ts = new Date().toLocaleTimeString('en-PK',{hour:'2-digit',minute:'2-digit'});
      this.setText('lastUpdate', ts);
    } catch(e) { console.error('fetchAll:', e); }
    finally    { this.showLoading(false); }
  }

  // ═══════════════════════════════════════════════
  // RENDER
  // ═══════════════════════════════════════════════
  renderStations() {
    this.stationMarkers.forEach(m => this.map.removeLayer(m));
    this.stationMarkers = [];
    if (!this.layers.pm25 && !this.layers.pm10) return;

    for (const s of this.stationData) {
      const lat = s.lat ?? s.latitude;
      const lon = s.lon ?? s.longitude;
      if (!lat || !lon) continue;

      const pm  = this.layers.pm10 ? (s.pm10 ?? s.pm25 ?? 0) : (s.pm25 ?? 0);
      const aqi = s.aqi ?? aqiFromPM25(pm);
      const col = aqiColor(aqi);
      const cat = s.aqi_category ?? aqiCat(aqi);

      // Size: 10–22px based on AQI
      const sz = Math.max(10, Math.min(22, 10 + (aqi/500)*12));

      const icon = L.divIcon({
        html: `<div style="
          width:${sz}px;height:${sz}px;
          background:${col};border-radius:50%;
          border:2px solid rgba(255,255,255,0.5);
          box-shadow:0 0 ${sz*0.6}px ${col}99, 0 0 ${sz*0.25}px ${col}44;
          cursor:pointer;
        "></div>`,
        iconSize:[sz,sz], iconAnchor:[sz/2,sz/2], className:''
      });

      const marker = L.marker([lat, lon], { icon });

      marker.bindTooltip(`
        <b>${s.name}</b> · ${s.province}<br>
        AQI <b style="color:${col}">${aqi}</b> · ${cat}<br>
        PM<sub>2.5</sub>: ${fmt(s.pm25)} µg/m³ &nbsp; PM<sub>10</sub>: ${fmt(s.pm10)} µg/m³
        ${s.source==='WAQI' ? '<br><span style="color:#7cf09a;font-size:.6rem">⚡ WAQI live</span>' : ''}
      `, { direction:'top', offset:[0,-(sz/2+3)], className:'' });

      marker.on('click', async () => {
        const [waqi, wx] = await Promise.all([
          this.fetchWAQI(lat, lon),
          this.fetchWeather(lat, lon, s.id),
        ]);
        const liveAqi = waqi?.aqi ?? aqi;
        const liveCol = waqi ? aqiColor(liveAqi) : col;
        const liveCat = waqi?.aqi_category ?? cat;
        this.showMarkerPopup(marker, s, liveAqi, liveCol, liveCat, wx, waqi);
        this.updateSidebar(
          { name:s.name, pm25: waqi?.pm25??s.pm25, pm10: waqi?.pm10??s.pm10 },
          liveAqi, liveCol, liveCat, wx, waqi
        );
        this.checkDisastersNear(lat, lon);
      });

      marker.addTo(this.map);
      this.stationMarkers.push(marker);
    }
  }

  renderHeatmap() {
    if (this.heatLayer) { this.map.removeLayer(this.heatLayer); this.heatLayer=null; }
    if (!this.layers.heat || !this.stationData.length) return;
    const pts = this.stationData
      .map(s => [s.lat??s.latitude, s.lon??s.longitude, (s.aqi??aqiFromPM25(s.pm25??0))/400])
      .filter(p => p[0] && p[1]);
    this.heatLayer = L.heatLayer(pts, {
      radius:45, blur:35, maxZoom:9,
      gradient:{0:'#00e400',.25:'#ffff00',.5:'#ff7e00',.75:'#ff0000',1:'#7e0023'}
    }).addTo(this.map);
  }

  renderDisasters(alerts) {
    this.disasterMarkers.forEach(m => this.map.removeLayer(m));
    this.disasterMarkers = [];
    if (!this.layers.disasters) return;
    const ICONS = {FL:'🌊',EQ:'⚡',TC:'🌀',VO:'🌋',DR:'☀️',WF:'🔥',LS:'⛰️'};
    const CLRS  = {high:'#ff4040',medium:'#ff9900',low:'#ffcc00',critical:'#7e0023'};
    for (const d of alerts) {
      const em  = ICONS[d.type] || '⚠️';
      const clr = CLRS[d.severity] || '#ffcc00';
      const icon = L.divIcon({
        html:`<div class="dis-marker" style="width:34px;height:34px;background:rgba(0,0,0,.75);border:2px solid ${clr};border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:1rem;box-shadow:0 0 10px ${clr}80">${em}</div>`,
        iconSize:[34,34], iconAnchor:[17,17], className:''
      });
      const m = L.marker([d.lat, d.lon], {icon});
      m.bindPopup(`<div class="map-popup">
        <div class="popup-city">${em} ${d.type_name||d.type}</div>
        <div style="font-size:.7rem;color:${clr};font-weight:700">${(d.severity||'').toUpperCase()}</div>
        <div style="font-size:.7rem;margin-top:.25rem">${d.title||''}</div>
        <div style="font-size:.6rem;color:var(--text-muted);margin-top:.25rem">Source: ${d.source||'GDACS'}</div>
      </div>`, {maxWidth:240});
      m.addTo(this.map);
      this.disasterMarkers.push(m);
    }
  }

  toggleCloudLayer() {
    if (this.cloudLayer) { this.map.removeLayer(this.cloudLayer); this.cloudLayer=null; }
    else this.cloudLayer = L.tileLayer(NASA_TILE,{opacity:.5,attribution:'NASA GIBS'}).addTo(this.map);
  }

  // ═══════════════════════════════════════════════
  // API CALLS
  // ═══════════════════════════════════════════════
  async fetchWAQI(lat, lon) {
    try {
      const r = await fetch(`/api/waqi?lat=${lat}&lon=${lon}`);
      if (!r.ok) return null;
      const d = await r.json();
      return d.error ? null : d;
    } catch { return null; }
  }

  async fetchWeather(lat, lon, stationId) {
    try {
      const sid = stationId ? `&station_id=${stationId}` : '';
      const r   = await fetch(`/api/weather?lat=${lat}&lon=${lon}${sid}`);
      if (!r.ok) return null;
      const d = await r.json();
      return d.error ? null : d;
    } catch { return null; }
  }

  // ═══════════════════════════════════════════════
  // MAP CLICK
  // ═══════════════════════════════════════════════
  async onMapClick(latlng) {
    document.getElementById('clickHint')?.remove();
    this.showLoading(true);
    try {
      const lat = latlng.lat, lon = latlng.lng;
      const [waqi, wx] = await Promise.all([
        this.fetchWAQI(lat, lon),
        this.fetchWeather(lat, lon),
      ]);
      const near  = this.nearestStation(lat, lon);
      const pm25  = waqi?.pm25  ?? near?.pm25  ?? null;
      const pm10  = waqi?.pm10  ?? near?.pm10  ?? null;
      const aqi   = waqi?.aqi   ?? (pm25 !== null ? aqiFromPM25(pm25) : near?.aqi ?? null);
      const col   = aqiColor(aqi ?? 0);
      const cat   = waqi?.aqi_category ?? (aqi ? aqiCat(aqi) : '—');
      const name  = waqi?.city_name || near?.name || `${lat.toFixed(2)}°N ${lon.toFixed(2)}°E`;

      this.showClickPopup(latlng, name, pm25, pm10, aqi, col, cat, wx, waqi);
      this.updateSidebar({ name, pm25, pm10 }, aqi, col, cat, wx, waqi);
      this.checkDisastersNear(lat, lon);
    } finally { this.showLoading(false); }
  }

  nearestStation(lat, lon) {
    return this.stationData.reduce((best, s) => {
      const d = Math.hypot((s.lat??0)-lat, (s.lon??0)-lon);
      return (!best || d < best._d) ? {...s, _d:d} : best;
    }, null);
  }

  // ═══════════════════════════════════════════════
  // POPUPS
  // ═══════════════════════════════════════════════
  buildPopupHTML(name, pm25, pm10, aqi, col, cat, wx, waqi) {
    const w = wx || {}, q = waqi || {};

    // Dominant pollutant row
    const domStr = q.dominant_pol
      ? `<div style="font-size:.6rem;color:var(--text-muted);margin-bottom:.3rem">Dominant: <b style="color:${col}">${q.dominant_pol.toUpperCase()}</b></div>` : '';

    // Extra gas pollutants (only if WAQI returned them)
    const hasGases = q.no2 !== undefined || q.o3 !== undefined;
    const gasStr = hasGases ? `
      <div style="border-top:1px solid var(--border);margin-top:.35rem;padding-top:.35rem">
        <div style="font-size:.58rem;color:var(--text-muted);letter-spacing:.08em;margin-bottom:.2rem">OTHER POLLUTANTS</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:.12rem .45rem;font-size:.63rem">
          <span style="color:var(--text-muted)">NO₂</span><span style="font-weight:700">${fmt(q.no2)} µg/m³</span>
          <span style="color:var(--text-muted)">O₃</span><span style="font-weight:700">${fmt(q.o3)} µg/m³</span>
          <span style="color:var(--text-muted)">SO₂</span><span style="font-weight:700">${fmt(q.so2)} µg/m³</span>
          <span style="color:var(--text-muted)">CO</span><span style="font-weight:700">${fmt(q.co)} ppm</span>
        </div>
      </div>` : '';

    // Weather section
    const hasWx = w.temperature_c !== undefined;
    const wxStr = hasWx ? `
      <div style="border-top:1px solid var(--border);margin-top:.35rem;padding-top:.35rem">
        <div style="font-size:.58rem;color:var(--text-muted);letter-spacing:.08em;margin-bottom:.2rem">LIVE WEATHER</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:.12rem .45rem;font-size:.63rem">
          <span style="color:var(--text-muted)">Temp</span><span style="font-weight:700">${fmt(w.temperature_c)}°C (feels ${fmt(w.feels_like_c)}°C)</span>
          <span style="color:var(--text-muted)">Humidity</span><span style="font-weight:700">${fmt(w.humidity_pct)}%</span>
          <span style="color:var(--text-muted)">Wind</span><span style="font-weight:700">${fmt(w.wind_speed_kmh,0)} km/h ${windDir(w.wind_direction)}</span>
          <span style="color:var(--text-muted)">Cloud</span><span style="font-weight:700">${fmt(w.cloud_cover_pct)}%</span>
          <span style="color:var(--text-muted)">Rain</span><span style="font-weight:700">${fmt(w.precipitation_mm)} mm</span>
          <span style="color:var(--text-muted)">Pressure</span><span style="font-weight:700">${fmt(w.pressure_hpa,0)} hPa</span>
        </div>
        ${w.weather_description ? `<div style="font-size:.62rem;color:var(--accent);text-align:center;margin-top:.3rem">${wmoEmoji(w.weather_code)} ${w.weather_description}</div>` : ''}
      </div>` : '';

    const srcBadge = (q.source==='WAQI'||hasWx)
      ? `<div class="popup-footer">⚡ WAQI · Open-Meteo · data saved to DB</div>` : '';

    return `<div class="map-popup">
      <div class="popup-city">${name}</div>
      ${domStr}
      <div class="popup-aqi-row">
        <span class="popup-aqi-num" style="color:${col}">${aqi??'—'}</span>
        <span class="popup-aqi-cat">${cat}</span>
      </div>
      <div class="popup-pm-row">
        <div class="popup-pm-box">
          <div class="popup-pm-lbl">PM₂.₅</div>
          <div class="popup-pm-val" style="color:${col}">${fmt(pm25)}</div>
          <div class="popup-pm-unit">µg/m³</div>
        </div>
        <div class="popup-pm-box">
          <div class="popup-pm-lbl">PM₁₀</div>
          <div class="popup-pm-val" style="color:var(--accent4)">${fmt(pm10)}</div>
          <div class="popup-pm-unit">µg/m³</div>
        </div>
      </div>
      ${gasStr}
      ${wxStr}
      ${srcBadge}
    </div>`;
  }

  showClickPopup(latlng, name, pm25, pm10, aqi, col, cat, wx, waqi) {
    L.popup({maxWidth:295, className:''})
      .setLatLng(latlng)
      .setContent(this.buildPopupHTML(name, pm25, pm10, aqi, col, cat, wx, waqi))
      .openOn(this.map);
  }

  showMarkerPopup(marker, s, aqi, col, cat, wx, waqi) {
    marker.bindPopup(
      this.buildPopupHTML(s.name, s.pm25, s.pm10, aqi, col, cat, wx, waqi),
      {maxWidth:295}
    ).openPopup();
  }

  // ═══════════════════════════════════════════════
  // SIDEBAR
  // ═══════════════════════════════════════════════
  updateSidebar(station, aqi, col, cat, wx, waqi) {
    const q = waqi || {}, w = wx || {};

    document.getElementById('locationPanel').style.display = 'block';
    this.setText('locationName', station.name);
    const srcEl = document.getElementById('dataSrc');
    if (srcEl) srcEl.textContent = q.source === 'WAQI' ? '⚡ WAQI' : 'Demo';

    // AQI badge
    const badge = document.getElementById('aqiBadge');
    if (badge) { badge.style.background=col+'12'; badge.style.borderColor=col+'45'; }
    this.setText('aqiValue', aqi??'—', col);
    this.setText('aqiCat',   cat,        col);

    // PM hero cards
    const pm25 = station.pm25, pm10 = station.pm10;
    this.setText('infoPM25', pm25 !== null && pm25 !== undefined ? fmt(pm25) : '—');
    this.setText('infoPM10', pm10 !== null && pm10 !== undefined ? fmt(pm10) : '—');

    // Color pm25 value
    const pm25El = document.getElementById('infoPM25');
    if (pm25El) pm25El.style.color = col;

    // Card borders
    const c25 = document.getElementById('pm25Card');
    const c10 = document.getElementById('pm10Card');
    if (c25) c25.style.borderColor = col+'70';
    if (c10) c10.style.borderColor = 'var(--accent4)70';

    // Progress bars — PM2.5 WHO limit ~300 max, PM10 ~500
    const b25 = document.getElementById('pm25Bar');
    const b10 = document.getElementById('pm10Bar');
    if (b25) { b25.style.width=Math.min(100,((pm25??0)/300)*100)+'%'; b25.style.background=col; }
    if (b10) { b10.style.width=Math.min(100,((pm10??0)/500)*100)+'%'; }

    // Dominant pollutant
    const domRow = document.getElementById('domRow');
    if (domRow) {
      domRow.style.display = q.dominant_pol ? 'flex' : 'none';
      this.setText('domVal', q.dominant_pol?.toUpperCase() ?? '');
    }

    // Gas pollutants
    this.setText('infoNO2', fmt(q.no2));
    this.setText('infoO3',  fmt(q.o3));
    this.setText('infoSO2', fmt(q.so2));
    this.setText('infoCO',  fmt(q.co));

    // Weather
    const temp = w.temperature_c ?? q.temperature;
    this.setText('infoTemp',    temp !== undefined ? fmt(temp)+'°C' : '—');
    this.setText('infoFeels',   w.feels_like_c  !== undefined ? fmt(w.feels_like_c)+'°C' : '—');
    this.setText('infoHumidity',w.humidity_pct   !== undefined ? fmt(w.humidity_pct)+'%'   : '—');
    this.setText('infoClouds',  w.cloud_cover_pct!== undefined ? fmt(w.cloud_cover_pct)+'%'  : '—');
    this.setText('infoRain',    w.precipitation_mm!==undefined ? fmt(w.precipitation_mm)+'mm' : '—');
    this.setText('infoPressure',w.pressure_hpa   !== undefined ? fmt(w.pressure_hpa,0)+' hPa' : '—');

    const windStr = w.wind_speed_kmh !== undefined
      ? `${fmt(w.wind_speed_kmh,0)} km/h`
      : (q.wind_speed ? fmt(q.wind_speed)+' m/s' : '—');
    this.setText('infoWind',    windStr);
    this.setText('infoWindDir', windDir(w.wind_direction) || '—');

    this.setText('weatherIcon', wmoEmoji(w.weather_code ?? null));
    this.setText('weatherDesc', w.weather_description || (q.dominant_pol ? `Dominant: ${q.dominant_pol.toUpperCase()}` : '—'));
  }

  setText(id, val, color) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = (val !== undefined && val !== null) ? String(val) : '—';
    if (color) el.style.color = color;
  }

  // Disasters
  async checkDisastersNear(lat, lon) {
    try {
      const r  = await fetch(`/api/check-disasters?lat=${lat}&lon=${lon}`);
      const al = await r.json();
      const box  = document.getElementById('disasterBox');
      const list = document.getElementById('disasterList');
      if (!box || !list) return;
      if (al.length) {
        box.style.display='block';
        list.innerHTML = al.map(a =>
          `<div class="dis-item"><b>${a.alert_type}</b> · ${a.severity}: ${a.title}</div>`
        ).join('');
      } else { box.style.display='none'; }
    } catch {}
  }

  // Stats
  updateStats() {
    if (!this.stationData.length) return;
    const vals   = this.stationData.map(s=>s.pm25??0).filter(v=>v>0);
    const avg    = vals.length ? vals.reduce((a,b)=>a+b,0)/vals.length : 0;
    const sorted = [...this.stationData].sort((a,b)=>(b.pm25??0)-(a.pm25??0));
    this.setText('statCount',   this.stationData.length);
    this.setText('statAvgPM25', avg.toFixed(1)+' µg/m³');
    this.setText('statWorst',   sorted[0]?.name||'—');
    this.setText('statBest',    sorted[sorted.length-1]?.name||'—');
  }

  showLoading(show) {
    const el = document.getElementById('mapLoading');
    if (el) el.style.display = show ? 'flex' : 'none';
  }

  // ═══════════════════════════════════════════════
  // EVENTS
  // ═══════════════════════════════════════════════
  initEvents() {
    document.getElementById('toggleSidebar')?.addEventListener('click', () =>
      document.getElementById('sidebar').classList.toggle('collapsed'));

    document.getElementById('toggleTheme')?.addEventListener('click', () => {
      const html   = document.documentElement;
      const isDark = html.getAttribute('data-theme') === 'dark';
      html.setAttribute('data-theme', isDark ? 'light' : 'dark');
      const icon   = document.getElementById('themeIcon');
      icon.innerHTML = isDark
        ? '<circle cx="12" cy="12" r="5" fill="currentColor"/><path d="M12 2v2M12 20v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M2 12h2M20 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>'
        : '<path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" fill="currentColor"/>';
      this.setTile(isDark ? 'light' : 'dark');
    });

    document.getElementById('refreshBtn')?.addEventListener('click', () => this.fetchAll());

    // Layers
    const LM = {
      layerPM25:      () => { this.layers.pm25      = document.getElementById('layerPM25').checked;      this.renderStations(); },
      layerPM10:      () => { this.layers.pm10      = document.getElementById('layerPM10').checked;      this.renderStations(); },
      layerHeat:      () => { this.layers.heat      = document.getElementById('layerHeat').checked;      this.renderHeatmap(); },
      layerWind:      () => { this.windVisible      = document.getElementById('layerWind').checked; },
      layerDisasters: () => { this.layers.disasters = document.getElementById('layerDisasters').checked; this.fetchAll(); },
      layerClouds:    () => { this.layers.clouds    = document.getElementById('layerClouds').checked;    this.toggleCloudLayer(); },
    };
    for (const [id, fn] of Object.entries(LM))
      document.getElementById(id)?.addEventListener('change', fn);

    document.querySelectorAll('.tile-btn').forEach(btn =>
      btn.addEventListener('click', () => this.setTile(btn.dataset.tile)));

    // Collapsible panels (data-panel attribute)
    document.querySelectorAll('[data-panel]').forEach(hdr =>
      hdr.addEventListener('click', () => {
        const body = document.getElementById(hdr.dataset.panel);
        if (!body) return;
        body.classList.toggle('collapsed');
        hdr.classList.toggle('open');
      })
    );
  }
}

// Boot
window.addEventListener('DOMContentLoaded', () => { window.aqms = new AQMS(); });
