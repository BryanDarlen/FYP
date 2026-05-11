const API = {
  status: "/status",
  latest: "/latest",
  alerts: "/alerts",
  forecast: (stationId) => `/forecast/${encodeURIComponent(stationId)}`,
  explain: (stationId) => `/explain/${encodeURIComponent(stationId)}`,
  history: (stationId, hours = 12) => `/history/${encodeURIComponent(stationId)}?hours=${hours}`,
};

const MAP_BOUNDS = {
  minLat: 0.7,
  maxLat: 7.6,
  minLon: 99.4,
  maxLon: 119.7,
};

const LEAFLET_BOUNDS = [[MAP_BOUNDS.minLat, MAP_BOUNDS.minLon], [MAP_BOUNDS.maxLat, MAP_BOUNDS.maxLon]];
const NORMAL_REFRESH_MS = 60000;
const STARTUP_REFRESH_MS = 10000;
const STARTUP_REFRESH_WINDOW_MS = 120000;

const state = {
  latest: [],
  selectedId: null,
  trendMode: "raw",
  status: null,
  leafletMap: null,
  markerLayer: null,
  mapTileFailed: false,
  startupPollTimer: null,
  stationRequestId: 0,
};

const el = {
  lastUpdated: document.getElementById("last-updated"),
  stationCount: document.getElementById("station-count"),
  alertCount: document.getElementById("alert-count"),
  offlineBanner: document.getElementById("offline-banner"),
  stateFilter: document.getElementById("state-filter"),
  search: document.getElementById("station-search"),
  stationList: document.getElementById("station-list"),
  map: document.getElementById("station-map"),
  detailName: document.getElementById("detail-name"),
  detailState: document.getElementById("detail-state"),
  detailApi: document.getElementById("detail-api"),
  detailRain: document.getElementById("detail-rain"),
  detailHotspots: document.getElementById("detail-hotspots"),
  detailWind: document.getElementById("detail-wind"),
  firmsStatus: document.getElementById("firms-status"),
  firmsRegionalCount: document.getElementById("firms-regional-count"),
  firmsRegionalFrp: document.getElementById("firms-regional-frp"),
  firmsLocalCount: document.getElementById("firms-local-count"),
  firmsLocalFrp: document.getElementById("firms-local-frp"),
  trendChart: document.getElementById("trend-chart"),
  forecastChart: document.getElementById("forecast-chart"),
  trendSummary: document.getElementById("trend-summary"),
  forecastSummary: document.getElementById("forecast-summary"),
  alertsList: document.getElementById("alerts-list"),
  alertUpdated: document.getElementById("alert-updated"),
  explanationText: document.getElementById("explanation-text"),
  featureList: document.getElementById("feature-list"),
  refreshButton: document.getElementById("refresh-button"),
};

function bandClass(band) {
  const key = String(band || "unknown").toLowerCase().replaceAll(" ", "-");
  return `band-${key}`;
}

function stationLabel(row) {
  return row.STATION_LOCATION || row.station_location || row.STATION_ID;
}

function formatTime(value) {
  if (!value) return "--";
  return String(value).replace("T", " ").slice(0, 16);
}

async function getJson(url) {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json();
}

function setStatus(payload) {
  state.status = payload.status || payload;
  const status = state.status;
  el.stationCount.textContent = status.stations ?? "--";
  el.lastUpdated.textContent = `Last updated: ${formatTime(status.last_updated)}`;
  if (status.stale) {
    el.offlineBanner.hidden = false;
    el.offlineBanner.textContent = `Last updated: ${formatTime(status.last_updated)}. Live data may be stale.`;
  } else {
    el.offlineBanner.hidden = true;
    el.offlineBanner.textContent = "";
  }
}

function populateStates(rows) {
  const current = el.stateFilter.value || "all";
  const states = [...new Set(rows.map((row) => row.STATE_NAME).filter(Boolean))].sort();
  el.stateFilter.innerHTML = '<option value="all">All states</option>';
  for (const name of states) {
    const option = document.createElement("option");
    option.value = name;
    option.textContent = name;
    el.stateFilter.appendChild(option);
  }
  el.stateFilter.value = states.includes(current) ? current : "all";
}

function filteredStations() {
  const query = el.search.value.trim().toLowerCase();
  const selectedState = el.stateFilter.value;
  return state.latest.filter((row) => {
    const inState = selectedState === "all" || row.STATE_NAME === selectedState;
    const haystack = `${row.STATION_ID} ${row.STATION_LOCATION} ${row.STATE_NAME}`.toLowerCase();
    return inState && (!query || haystack.includes(query));
  });
}

function renderStationList() {
  const rows = filteredStations();
  el.stationList.innerHTML = "";
  for (const row of rows) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `station-item ${row.STATION_ID === state.selectedId ? "active" : ""}`;
    button.innerHTML = `
      <div>
        <strong>${stationLabel(row)}</strong>
        <span>${row.STATE_NAME || "--"} · ${row.STATION_ID}</span>
      </div>
      <div class="api-chip ${bandClass(row.CLASS)}">${Math.round(Number(row.API) || 0)}</div>
    `;
    button.addEventListener("click", () => selectStation(row.STATION_ID));
    el.stationList.appendChild(button);
  }
}

function mapPosition(row) {
  const lat = Number(row.LATITUDE);
  const lon = Number(row.LONGITUDE);
  const x = ((lon - MAP_BOUNDS.minLon) / (MAP_BOUNDS.maxLon - MAP_BOUNDS.minLon)) * 100;
  const y = (1 - ((lat - MAP_BOUNDS.minLat) / (MAP_BOUNDS.maxLat - MAP_BOUNDS.minLat))) * 100;
  return {
    x: Math.max(2, Math.min(98, x)),
    y: Math.max(2, Math.min(98, y)),
  };
}

function initLeafletMap() {
  if (state.leafletMap || typeof L === "undefined") return;

  state.leafletMap = L.map(el.map, {
    zoomControl: true,
    attributionControl: true,
    scrollWheelZoom: true,
    maxBounds: LEAFLET_BOUNDS,
    maxBoundsViscosity: 1.0,
  });

  const tileLayer = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: '&copy; OpenStreetMap contributors',
  });

  tileLayer.on("tileerror", () => {
    state.mapTileFailed = true;
    renderMap();
  });

  tileLayer.addTo(state.leafletMap);
  state.markerLayer = L.layerGroup().addTo(state.leafletMap);
  state.leafletMap.fitBounds(LEAFLET_BOUNDS, { padding: [18, 18] });
  state.leafletMap.whenReady(() => {
    const initialZoom = state.leafletMap.getZoom();
    state.leafletMap.setMinZoom(initialZoom);
    state.leafletMap.setMaxBounds(LEAFLET_BOUNDS);
  });
}

function renderFallbackMap(rows) {
  el.map.innerHTML = `
    <span class="map-label" style="left:8%;top:78%">Peninsular Malaysia</span>
    <span class="map-label" style="left:62%;top:42%">Sabah / Sarawak</span>
    <span class="map-fallback-note">Map tiles unavailable. Showing station coordinates only.</span>
  `;
  for (const row of rows) {
    const pos = mapPosition(row);
    const dot = document.createElement("button");
    dot.type = "button";
    dot.dataset.stationId = row.STATION_ID;
    dot.className = `station-dot ${bandClass(row.CLASS)} ${row.STATION_ID === state.selectedId ? "active" : ""}`;
    dot.style.left = `${pos.x}%`;
    dot.style.top = `${pos.y}%`;
    dot.title = `${stationLabel(row)} API ${row.API}`;
    dot.addEventListener("click", () => selectStation(row.STATION_ID));
    el.map.appendChild(dot);
  }
}

function renderLeafletMap(rows) {
  initLeafletMap();
  if (!state.leafletMap || !state.markerLayer) {
    renderFallbackMap(rows);
    return;
  }

  state.markerLayer.clearLayers();
  for (const row of rows) {
    const lat = Number(row.LATITUDE);
    const lon = Number(row.LONGITUDE);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue;

    const marker = L.marker([lat, lon], {
      icon: L.divIcon({
        className: "",
        html: `<button type="button" data-station-id="${row.STATION_ID}" class="map-marker ${bandClass(row.CLASS)} ${row.STATION_ID === state.selectedId ? "active" : ""}" title="${stationLabel(row)} API ${row.API}"></button>`,
        iconSize: [18, 18],
        iconAnchor: [9, 9],
      }),
      keyboard: true,
      title: `${stationLabel(row)} API ${row.API}`,
    });
    marker.on("click", () => selectStation(row.STATION_ID));
    marker.addTo(state.markerLayer);
  }

  if (state.mapTileFailed && !document.querySelector(".map-fallback-note")) {
    const note = document.createElement("span");
    note.className = "map-fallback-note";
    note.textContent = "Map tiles unavailable. Station markers remain usable.";
    el.map.appendChild(note);
  }

  setTimeout(() => state.leafletMap.invalidateSize(), 0);
}

function renderMap() {
  const rows = filteredStations();
  renderLeafletMap(rows);
}

function updateMapSelection() {
  document.querySelectorAll(".map-marker, .station-dot").forEach((marker) => {
    marker.classList.toggle("active", marker.dataset.stationId === state.selectedId);
  });
}

function setApiBadge(row) {
  el.detailApi.className = `api-badge ${bandClass(row.CLASS)}`;
  el.detailApi.textContent = Math.round(Number(row.API) || 0);
}

function formatMetric(value, digits = 0) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "--";
  return numeric.toLocaleString(undefined, {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  });
}

function renderFirmsEvidence(row) {
  const regionalHotspots = Number(row.HOTSPOT_COUNT);
  const localHotspots = Number(row.HOTSPOT_COUNT_100KM);
  const regionalFrp = Number(row.FRP_MW_MAX);
  const localFrp = Number(row.FRP_MW_MAX_100KM);
  const hasRegional = Number.isFinite(regionalHotspots) && regionalHotspots > 0;
  const hasLocal = Number.isFinite(localHotspots) && localHotspots > 0;

  el.firmsRegionalCount.textContent = formatMetric(regionalHotspots, 0);
  el.firmsRegionalFrp.textContent = `${formatMetric(regionalFrp, 2)} MW`;
  el.firmsLocalCount.textContent = formatMetric(localHotspots, 0);
  el.firmsLocalFrp.textContent = `${formatMetric(localFrp, 2)} MW`;

  if (hasLocal) {
    el.firmsStatus.textContent = "Nearby fire signal detected";
  } else if (hasRegional) {
    el.firmsStatus.textContent = "Regional fire signal detected";
  } else {
    el.firmsStatus.textContent = "No FIRMS hotspots for this hour";
  }
}

function renderStationDetail(row) {
  el.detailName.textContent = stationLabel(row);
  el.detailState.textContent = `${row.STATE_NAME || "--"} · ${row.STATION_ID} · ${formatTime(row.HOUR_MYT)}`;
  setApiBadge(row);
  el.detailRain.textContent = formatMetric(row.RAIN_FORECAST_SLOTS, 0);
  el.detailHotspots.textContent = formatMetric(row.HOTSPOT_COUNT_100KM, 0);
  el.detailWind.textContent = "N/A";
  renderFirmsEvidence(row);
}

function rolling(values, windowSize) {
  return values.map((_, index) => {
    const start = Math.max(0, index - windowSize + 1);
    const slice = values.slice(start, index + 1).filter((value) => Number.isFinite(value));
    if (!slice.length) return null;
    return slice.reduce((sum, value) => sum + value, 0) / slice.length;
  });
}

function trendDirection(delta) {
  if (delta >= 5) return "rising";
  if (delta <= -5) return "easing";
  return "mostly stable";
}

function summarizeTrend(rows, mode) {
  const points = rows
    .map((row) => ({ api: Number(row.API), hour: formatTime(row.HOUR_MYT).slice(11, 16) }))
    .filter((row) => Number.isFinite(row.api));

  if (points.length < 2) {
    return "Recent API history is not available enough yet for this station.";
  }

  const first = points[0];
  const last = points[points.length - 1];
  const values = points.map((row) => row.api);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const delta = last.api - first.api;
  const modeText = mode === "roll3" ? "3-hour average" : mode === "roll12" ? "12-hour average" : "hourly readings";

  return (
    `Observed APIMS API for this station is ${trendDirection(delta)} over the available last ${points.length} hour(s): ` +
    `${Math.round(first.api)} at ${first.hour} to ${Math.round(last.api)} at ${last.hour}. ` +
    `Range: ${Math.round(min)}-${Math.round(max)}. Display mode: ${modeText}.`
  );
}

function summarizeForecast(payload, currentRow) {
  const forecast = payload.forecast || [];
  const points = forecast
    .map((row) => ({ horizon: Number(row.horizon_hours), api: Number(row.api), band: row.band }))
    .filter((row) => Number.isFinite(row.horizon) && Number.isFinite(row.api));

  if (!points.length) {
    return "Forecast values are not available for this station yet.";
  }

  const currentApi = Number(currentRow?.API);
  const peak = points.reduce((best, row) => (row.api > best.api ? row : best), points[0]);
  const last = points[points.length - 1];
  let direction = "similar to the current API";
  if (Number.isFinite(currentApi)) {
    const delta = last.api - currentApi;
    if (delta >= 5) direction = "higher than the current API";
    else if (delta <= -5) direction = "lower than the current API";
  }

  return (
    `Model forecast estimates API will peak at ${peak.api.toFixed(1)} (${peak.band}) around +${peak.horizon}h. ` +
    `The +${last.horizon}h estimate is ${last.api.toFixed(1)}, ${direction}. These are predicted values, not observed readings.`
  );
}

function drawLineChart(canvas, labels, series, options = {}) {
  const ctx = canvas.getContext("2d");
  const height = Number(canvas.dataset.chartHeight) || 180;
  canvas.style.height = `${height}px`;
  canvas.style.width = "100%";
  const rect = canvas.getBoundingClientRect();
  const width = Math.max(1, Math.floor(rect.width || canvas.parentElement?.clientWidth || 320));
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.round(width * ratio);
  canvas.height = Math.round(height * ratio);
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  ctx.imageSmoothingEnabled = false;
  ctx.clearRect(0, 0, width, height);

  const padding = { top: 14, right: 14, bottom: 28, left: 38 };
  const plotW = width - padding.left - padding.right;
  const plotH = height - padding.top - padding.bottom;
  const allValues = series.flatMap((item) => item.values).filter((value) => Number.isFinite(value));
  const thresholds = options.thresholds || [];
  const maxValue = Math.max(120, ...allValues, ...thresholds);
  const minValue = Math.min(0, ...allValues);
  const span = Math.max(1, maxValue - minValue);

  const xFor = (index, count) => padding.left + (count <= 1 ? 0 : (index / (count - 1)) * plotW);
  const yFor = (value) => padding.top + (1 - ((value - minValue) / span)) * plotH;

  ctx.strokeStyle = "#d9e0e4";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(padding.left, padding.top);
  ctx.lineTo(padding.left, padding.top + plotH);
  ctx.lineTo(padding.left + plotW, padding.top + plotH);
  ctx.stroke();

  ctx.fillStyle = "#65727c";
  ctx.font = "11px Segoe UI, Arial";
  ctx.fillText(String(Math.round(maxValue)), 4, padding.top + 4);
  ctx.fillText(String(Math.round(minValue)), 8, padding.top + plotH);

  for (const threshold of thresholds) {
    const y = yFor(threshold);
    ctx.strokeStyle = threshold >= 200 ? "#991b1b" : "#b65f00";
    ctx.setLineDash([5, 5]);
    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(padding.left + plotW, y);
    ctx.stroke();
    ctx.setLineDash([]);
  }

  for (const item of series) {
    ctx.strokeStyle = item.color;
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    item.values.forEach((value, index) => {
      if (!Number.isFinite(value)) return;
      const x = xFor(index, item.values.length);
      const y = yFor(value);
      if (index === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();

    item.values.forEach((value, index) => {
      if (!Number.isFinite(value)) return;
      const x = xFor(index, item.values.length);
      const y = yFor(value);
      ctx.fillStyle = item.color;
      ctx.beginPath();
      ctx.arc(x, y, 3, 0, Math.PI * 2);
      ctx.fill();
    });
  }

  if (labels.length) {
    ctx.fillStyle = "#65727c";
    ctx.fillText(labels[0], padding.left, height - 8);
    ctx.textAlign = "right";
    ctx.fillText(labels[labels.length - 1], padding.left + plotW, height - 8);
    ctx.textAlign = "left";
  }
}

async function loadTrend(stationId, requestId = state.stationRequestId) {
  const payload = await getJson(API.history(stationId, 12));
  if (requestId !== state.stationRequestId || stationId !== state.selectedId) return;
  const rows = payload.history || [];
  const raw = rows.map((row) => Number(row.API));
  let values = raw;
  if (state.trendMode === "roll3") values = rolling(raw, 3);
  if (state.trendMode === "roll12") values = rolling(raw, 12);
  const labels = rows.map((row) => String(row.HOUR_MYT || "").slice(11, 16));
  drawLineChart(el.trendChart, labels, [{ values, color: "#156b75" }], { thresholds: [100, 200] });
  el.trendSummary.textContent = summarizeTrend(rows, state.trendMode);
}

async function loadForecast(stationId, requestId = state.stationRequestId) {
  const payload = await getJson(API.forecast(stationId));
  if (requestId !== state.stationRequestId || stationId !== state.selectedId) return null;
  const values = payload.forecast.map((row) => Number(row.api));
  const labels = payload.forecast.map((row) => `+${row.horizon_hours}h`);
  drawLineChart(el.forecastChart, labels, [{ values, color: "#2f7d32" }], { thresholds: [100, 200] });
  const currentRow = state.latest.find((row) => row.STATION_ID === stationId);
  el.forecastSummary.textContent = summarizeForecast(payload, currentRow);
  return payload;
}

async function loadExplanation(stationId, requestId = state.stationRequestId) {
  el.explanationText.textContent = "Loading explanation...";
  el.featureList.innerHTML = "";
  const payload = await getJson(API.explain(stationId));
  if (requestId !== state.stationRequestId || stationId !== state.selectedId) return;
  el.explanationText.textContent = payload.explanation || "--";
  el.featureList.innerHTML = "";
  const firms = payload.firms_evidence;
  if (firms) {
    const firmsCard = document.createElement("div");
    firmsCard.className = "feature-card evidence-card";
    firmsCard.innerHTML = `
      <strong>NASA FIRMS evidence</strong>
      <span>${firms.interpretation}</span>
    `;
    el.featureList.appendChild(firmsCard);
  }
  for (const item of payload.top_features || []) {
    const card = document.createElement("div");
    card.className = "feature-card";
    const value = item.shap_value ?? item.mean_abs_shap ?? "--";
    card.innerHTML = `<strong>${item.feature}</strong><span>${value}</span>`;
    el.featureList.appendChild(card);
  }
}

async function selectStation(stationId) {
  state.selectedId = stationId;
  const requestId = ++state.stationRequestId;
  const row = state.latest.find((item) => item.STATION_ID === stationId);
  if (!row) return;
  renderStationList();
  updateMapSelection();
  renderStationDetail(row);
  el.trendSummary.textContent = "Loading recent API summary...";
  el.forecastSummary.textContent = "Loading forecast summary...";
  loadTrend(stationId, requestId).catch(() => {});
  loadForecast(stationId, requestId).catch(() => {});
  loadExplanation(stationId, requestId).catch((error) => {
    if (requestId === state.stationRequestId && stationId === state.selectedId) {
      el.explanationText.textContent = `Explanation unavailable: ${error.message}`;
      el.featureList.innerHTML = "";
    }
  });
}

function renderAlerts(payload) {
  el.alertCount.textContent = payload.count ?? 0;
  el.alertUpdated.textContent = formatTime(payload.generated_at);
  el.alertsList.innerHTML = "";
  const alerts = payload.alerts || [];
  if (!alerts.length) {
    el.alertsList.innerHTML = '<p class="alert-empty">No active forecast alerts.</p>';
    return;
  }
  for (const alert of alerts.slice(0, 8)) {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "alert-card";
    card.innerHTML = `
      <strong>${alert.station_location}</strong>
      <span>${alert.state_name} · max ${alert.max_forecast_api} · ${alert.message}</span>
    `;
    card.addEventListener("click", () => selectStation(alert.station_id));
    el.alertsList.appendChild(card);
  }
}

async function loadDashboard() {
  const [latestPayload, alertsPayload] = await Promise.all([
    getJson(API.latest),
    getJson(API.alerts),
  ]);
  state.latest = latestPayload.latest || [];
  setStatus(latestPayload);
  populateStates(state.latest);
  renderAlerts(alertsPayload);

  if (!state.selectedId && state.latest.length) {
    state.selectedId = state.latest[0].STATION_ID;
  }
  renderStationList();
  renderMap();
  if (state.selectedId) {
    selectStation(state.selectedId);
  }
}

document.querySelectorAll(".trend-mode").forEach((button) => {
  button.addEventListener("click", async () => {
    document.querySelectorAll(".trend-mode").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    state.trendMode = button.dataset.mode;
    if (state.selectedId) await loadTrend(state.selectedId);
  });
});

el.stateFilter.addEventListener("change", () => {
  renderStationList();
  renderMap();
});

el.search.addEventListener("input", () => {
  renderStationList();
  renderMap();
});

el.refreshButton.addEventListener("click", async () => {
  el.refreshButton.disabled = true;
  try {
    await loadDashboard();
  } finally {
    el.refreshButton.disabled = false;
  }
});

window.addEventListener("resize", () => {
  if (state.selectedId) {
    loadTrend(state.selectedId);
    loadForecast(state.selectedId);
  }
});

loadDashboard().catch((error) => {
  el.offlineBanner.hidden = false;
  el.offlineBanner.textContent = `Dashboard error: ${error.message}`;
});

function startStartupPolling() {
  const startedAt = Date.now();
  if (state.startupPollTimer) {
    clearInterval(state.startupPollTimer);
  }
  state.startupPollTimer = setInterval(() => {
    if (Date.now() - startedAt > STARTUP_REFRESH_WINDOW_MS) {
      clearInterval(state.startupPollTimer);
      state.startupPollTimer = null;
      return;
    }
    loadDashboard().catch(() => {});
  }, STARTUP_REFRESH_MS);
}

startStartupPolling();

setInterval(() => {
  loadDashboard().catch(() => {});
}, NORMAL_REFRESH_MS);
