const form = document.getElementById("form");
const saveBtn = document.getElementById("save");
const locateBtn = document.getElementById("locate");
const statusEl = document.getElementById("status");
const result = document.getElementById("result");
const placeEl = document.getElementById("place");
const pinsEl = document.getElementById("pins");
const activitiesEl = document.getElementById("activities");
const toggleBtn = document.getElementById("activity-toggle");
const chipsEl = document.getElementById("live-chips");
const hintEl = document.getElementById("activity-hint");

let map;
let marker;
let lastLocation = null;
let watchId = null;
let currentActivity = null;
let lastSampleAt = 0;
let lastRecorded = null;
const trailLayers = [];

function aqiColor(value) {
  if (value == null) return "#7da8ce";
  if (value <= 50) return "#7dcea0";
  if (value <= 100) return "#e2d36a";
  if (value <= 150) return "#e2b36a";
  if (value <= 200) return "#e27a7a";
  return "#b07dce";
}

function aqiLabel(value) {
  if (value == null) return "AQI –";
  if (value <= 50) return `AQI ${Math.round(value)} good`;
  if (value <= 100) return `AQI ${Math.round(value)} moderate`;
  if (value <= 150) return `AQI ${Math.round(value)} sensitive`;
  if (value <= 200) return `AQI ${Math.round(value)} unhealthy`;
  return `AQI ${Math.round(value)} hazardous`;
}

function showError(message) {
  statusEl.hidden = false;
  statusEl.className = "status error";
  statusEl.textContent = message;
}

function showStatus(message) {
  statusEl.hidden = false;
  statusEl.className = "status";
  statusEl.textContent = message;
}

function geoErrorMessage(error) {
  if (!window.isSecureContext) {
    return "Location needs HTTPS. Open https://map-api.cnpe-dev.cloud-master-ai.com";
  }
  const code = error && error.code;
  if (code === 1) {
    return "Location permission denied. Allow it for this site, or click the map to place yourself.";
  }
  if (code === 2) {
    return "GPS is unavailable on this device. Click the map to place yourself.";
  }
  if (code === 3) {
    return "Location timed out. Click the map, or try Use my location again.";
  }
  return (error && error.message) || "Could not read your location. Click the map to place yourself.";
}

function openMapForClick(message) {
  if (!lastLocation && !map) {
    ensureMap(52.52, 13.41, 12);
    placeEl.textContent = "Click the map to set your position";
  } else if (lastLocation) {
    ensureMap(lastLocation.latitude, lastLocation.longitude, 14);
  }
  hintEl.textContent = message;
  hintEl.className = "meta";
}

function readLocation(onOk, onFail) {
  if (!navigator.geolocation) {
    onFail({ code: 2, message: "This browser has no geolocation." });
    return;
  }
  const attempt = (highAccuracy) => {
    navigator.geolocation.getCurrentPosition(
      onOk,
      (error) => {
        if (highAccuracy && error && error.code === 3) {
          attempt(false);
          return;
        }
        onFail(error);
      },
      {
        enableHighAccuracy: highAccuracy,
        timeout: highAccuracy ? 8000 : 20000,
        maximumAge: 60000,
      },
    );
  };
  attempt(true);
}

function ensureMap(lat, lon, zoom) {
  result.hidden = false;
  if (!map) {
    map = L.map("map");
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap",
    }).addTo(map);
    map.on("click", (event) => {
      const lat = event.latlng.lat;
      const lon = event.latlng.lng;
      lastLocation = { latitude: lat, longitude: lon, label: "Map click" };
      document.getElementById("latitude").value = lat;
      document.getElementById("longitude").value = lon;
      document.getElementById("city").value = "";
      placeEl.textContent = `${lat.toFixed(5)}, ${lon.toFixed(5)}`;
      if (marker) marker.setLatLng([lat, lon]);
      if (currentActivity) recordPoint(lat, lon, true);
    });
  }
  map.setView([lat, lon], zoom || map.getZoom() || 14);
  if (marker) marker.remove();
  marker = L.circleMarker([lat, lon], {
    radius: 9,
    color: "#fff8ee",
    weight: 2,
    fillColor: "#e2b36a",
    fillOpacity: 1,
  }).addTo(map);
  setTimeout(() => map.invalidateSize(), 50);
}

function clearTrail() {
  for (const layer of trailLayers) layer.remove();
  trailLayers.length = 0;
}

function drawSegment(from, to, aqi) {
  const line = L.polyline(
    [[from.latitude, from.longitude], [to.latitude, to.longitude]],
    { color: aqiColor(aqi), weight: 5, opacity: 0.9 },
  ).addTo(map);
  trailLayers.push(line);
}

function renderChips(point, extra = "") {
  const bits = [
    point.temperature != null ? `${point.temperature}°` : null,
    point.windspeed != null ? `${point.windspeed} km/h` : null,
    aqiLabel(point.us_aqi),
    extra,
  ].filter(Boolean);
  chipsEl.innerHTML = bits.map((text) => `<span class="chip">${text}</span>`).join("");
  chipsEl.hidden = bits.length === 0;
  const warnings = [];
  if (point.us_aqi != null && point.us_aqi > 100) warnings.push("Air quality is elevated on this path.");
  if (point.windspeed != null && point.windspeed > 40) warnings.push("Strong wind along this activity.");
  if (point.temperature != null && point.temperature < 0) warnings.push("Freezing temperature.");
  hintEl.textContent = warnings.join(" ")
    || (currentActivity
      ? "Tracking. Click the map to add a point if GPS is unavailable."
      : "Allow location, or click the map while tracking to simulate movement.");
  hintEl.className = warnings.length ? "status error" : "meta";
}

function metersLabel(meters) {
  if (meters == null) return "0 m";
  if (meters >= 1000) return `${(meters / 1000).toFixed(2)} km`;
  return `${Math.round(meters)} m`;
}

async function recordPoint(lat, lon, force) {
  if (!currentActivity) return;
  const now = Date.now();
  if (!force && lastRecorded) {
    const moved = Math.hypot(lat - lastRecorded.latitude, lon - lastRecorded.longitude) * 111320;
    if (moved < 15 && now - lastSampleAt < 20000) return;
  }
  lastSampleAt = now;
  try {
    const response = await fetch(`/activities/${currentActivity.id}/points`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ latitude: lat, longitude: lon }),
    });
    const point = await response.json();
    if (!response.ok) throw new Error(point.detail || "Could not record point");
    lastLocation = { latitude: lat, longitude: lon, label: currentActivity.label };
    ensureMap(lat, lon, 16);
    if (lastRecorded) drawSegment(lastRecorded, point, point.us_aqi);
    lastRecorded = point;
    currentActivity.distance_m = (currentActivity.distance_m || 0);
    const live = await fetch(`/activities/${currentActivity.id}`);
    const detail = live.ok ? await live.json() : currentActivity;
    currentActivity = { ...currentActivity, ...detail };
    renderChips(point, metersLabel(detail.distance_m));
    if (detail.alerts?.length) hintEl.textContent = detail.alerts.join(" ");
  } catch (error) {
    showError(error.message);
  }
}

function stopWatch() {
  if (watchId != null && navigator.geolocation) {
    navigator.geolocation.clearWatch(watchId);
  }
  watchId = null;
}

async function startActivity() {
  const kind = document.getElementById("activity-kind").value;
  const label = document.getElementById("activity-label").value.trim();
  const response = await fetch("/activities", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ kind, label: label || undefined }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Could not start activity");
  currentActivity = data;
  lastRecorded = null;
  lastSampleAt = 0;
  clearTrail();
  toggleBtn.textContent = "Stop activity";
  showStatus("Activity started");
  if (navigator.geolocation && window.isSecureContext) {
    watchId = navigator.geolocation.watchPosition(
      (pos) => recordPoint(pos.coords.latitude, pos.coords.longitude, false),
      (error) => {
        hintEl.textContent = `${geoErrorMessage(error)} Tracking still works if you click the map.`;
        hintEl.className = "status error";
      },
      { enableHighAccuracy: false, maximumAge: 8000, timeout: 20000 },
    );
  } else {
    hintEl.textContent = geoErrorMessage({ code: 2 });
    hintEl.className = "status error";
  }
  if (lastLocation) {
    await recordPoint(lastLocation.latitude, lastLocation.longitude, true);
  } else if (!map) {
    ensureMap(52.52, 13.41, 12);
    placeEl.textContent = "Click the map to start the trail";
  }
}

async function stopActivity() {
  stopWatch();
  if (!currentActivity) return;
  const response = await fetch(`/activities/${currentActivity.id}/stop`, { method: "POST" });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "Could not stop activity");
  currentActivity = null;
  toggleBtn.textContent = "Start activity";
  chipsEl.hidden = true;
  hintEl.className = "meta";
  hintEl.textContent = data.alerts?.length
    ? data.alerts.join(" ")
    : `Saved ${metersLabel(data.distance_m)} in ${Math.round(data.duration_s || 0)}s.`;
  statusEl.hidden = true;
  await loadActivities();
}

toggleBtn.addEventListener("click", async () => {
  try {
    if (currentActivity) await stopActivity();
    else await startActivity();
  } catch (error) {
    showError(error.message);
  }
});

function drawActivity(detail) {
  clearTrail();
  const points = detail.points || [];
  if (!points.length) return;
  ensureMap(points[0].latitude, points[0].longitude, 14);
  for (let i = 1; i < points.length; i += 1) {
    drawSegment(points[i - 1], points[i], points[i].us_aqi);
  }
  const last = points[points.length - 1];
  ensureMap(last.latitude, last.longitude, 15);
  renderChips(last, metersLabel(detail.distance_m));
  if (detail.alerts?.length) {
    hintEl.textContent = detail.alerts.join(" ");
    hintEl.className = "status error";
  }
  const bounds = L.latLngBounds(points.map((p) => [p.latitude, p.longitude]));
  if (points.length > 1) map.fitBounds(bounds, { padding: [24, 24] });
}

async function loadActivities() {
  activitiesEl.innerHTML = "";
  try {
    const response = await fetch("/activities");
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Could not load activities");
    for (const activity of data.activities || []) {
      const item = document.createElement("li");
      const label = document.createElement("span");
      const when = new Date(activity.started_at).toLocaleString();
      const state = activity.ended_at ? "done" : "live";
      label.textContent = `${activity.label} · ${activity.kind} · ${metersLabel(activity.distance_m)} · ${state} · ${when}`;
      label.style.cursor = "pointer";
      const del = document.createElement("button");
      del.type = "button";
      del.className = "secondary";
      del.textContent = "Delete";
      label.addEventListener("click", async () => {
        const resp = await fetch(`/activities/${activity.id}`);
        const detail = await resp.json();
        if (!resp.ok) return showError(detail.detail || "Could not load activity");
        placeEl.textContent = `${detail.label} · ${metersLabel(detail.distance_m)}`;
        drawActivity(detail);
      });
      del.addEventListener("click", async (event) => {
        event.stopPropagation();
        const delResp = await fetch(`/activities/${activity.id}`, { method: "DELETE" });
        if (!delResp.ok && delResp.status !== 204) return showError("Could not delete activity");
        if (currentActivity?.id === activity.id) {
          stopWatch();
          currentActivity = null;
          toggleBtn.textContent = "Start activity";
        }
        await loadActivities();
      });
      item.append(label, del);
      activitiesEl.append(item);
    }
  } catch (error) {
    showError(error.message);
  }
}

async function loadPins() {
  pinsEl.innerHTML = "";
  try {
    const response = await fetch("/pins");
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Could not load pins");
    for (const pin of data.pins || []) {
      const item = document.createElement("li");
      const label = document.createElement("span");
      label.textContent = pin.label || `${pin.latitude}, ${pin.longitude}`;
      const del = document.createElement("button");
      del.type = "button";
      del.className = "secondary";
      del.textContent = "Delete";
      label.style.cursor = "pointer";
      label.addEventListener("click", () => {
        lastLocation = { latitude: pin.latitude, longitude: pin.longitude, label: pin.label };
        placeEl.textContent = label.textContent;
        ensureMap(pin.latitude, pin.longitude, 10);
      });
      del.addEventListener("click", async (event) => {
        event.stopPropagation();
        const delResp = await fetch(`/pins/${pin.id}`, { method: "DELETE" });
        if (!delResp.ok && delResp.status !== 204) {
          showError("Could not delete pin");
          return;
        }
        await loadPins();
      });
      item.append(label, del);
      pinsEl.append(item);
    }
  } catch (error) {
    showError(error.message);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const city = document.getElementById("city").value.trim();
  const latitude = document.getElementById("latitude").value.trim();
  const longitude = document.getElementById("longitude").value.trim();
  const params = new URLSearchParams();
  if (city) params.set("city", city);
  if (latitude) params.set("latitude", latitude);
  if (longitude) params.set("longitude", longitude);

  showStatus("Loading…");
  result.hidden = true;

  try {
    const response = await fetch(`/map?${params.toString()}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Request failed");
    const location = data.location || {};
    const viewport = data.viewport || {};
    const lat = location.latitude ?? viewport.center?.latitude;
    const lon = location.longitude ?? viewport.center?.longitude;
    const place = [location.name, location.admin1, location.country].filter(Boolean).join(", ")
      || `${lat}, ${lon}`;
    lastLocation = {
      city: city || null,
      latitude: lat,
      longitude: lon,
      label: location.name || city || place,
    };
    placeEl.textContent = place;
    statusEl.hidden = true;
    ensureMap(lat, lon, viewport.zoom || 10);
  } catch (error) {
    showError(error.message);
  }
});

saveBtn.addEventListener("click", async () => {
  const city = document.getElementById("city").value.trim();
  const latitude = document.getElementById("latitude").value.trim();
  const longitude = document.getElementById("longitude").value.trim();
  const body = lastLocation
    ? { latitude: lastLocation.latitude, longitude: lastLocation.longitude, label: lastLocation.label }
    : {};
  if (!lastLocation) {
    if (city) body.city = city;
    if (latitude) body.latitude = Number(latitude);
    if (longitude) body.longitude = Number(longitude);
  }
  showStatus("Saving…");
  try {
    const response = await fetch("/pins", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || "Could not save pin");
    statusEl.hidden = true;
    await loadPins();
  } catch (error) {
    showError(error.message);
  }
});

locateBtn.addEventListener("click", () => {
  showStatus("Locating…");
  readLocation(
    async (pos) => {
      const lat = pos.coords.latitude;
      const lon = pos.coords.longitude;
      document.getElementById("latitude").value = lat;
      document.getElementById("longitude").value = lon;
      document.getElementById("city").value = "";
      lastLocation = { latitude: lat, longitude: lon, label: "My location" };
      placeEl.textContent = `${lat.toFixed(5)}, ${lon.toFixed(5)}`;
      statusEl.hidden = true;
      ensureMap(lat, lon, 15);
      if (currentActivity) await recordPoint(lat, lon, true);
    },
    (error) => {
      const message = geoErrorMessage(error);
      showError(message);
      openMapForClick(message);
    },
  );
});

loadPins();
loadActivities();
