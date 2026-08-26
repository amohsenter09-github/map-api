const form = document.getElementById("form");
const saveBtn = document.getElementById("save");
const statusEl = document.getElementById("status");
const result = document.getElementById("result");
const placeEl = document.getElementById("place");
const pinsEl = document.getElementById("pins");
let map;
let marker;
let lastLocation = null;

function ensureMap(lat, lon, zoom) {
  if (!map) {
    map = L.map("map");
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap",
    }).addTo(map);
  }
  map.setView([lat, lon], zoom);
  if (marker) marker.remove();
  marker = L.marker([lat, lon]).addTo(map);
}

function showError(message) {
  statusEl.hidden = false;
  statusEl.className = "status error";
  statusEl.textContent = message;
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
        result.hidden = false;
        placeEl.textContent = label.textContent;
        ensureMap(pin.latitude, pin.longitude, 10);
        setTimeout(() => map.invalidateSize(), 50);
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

  statusEl.hidden = false;
  statusEl.className = "status";
  statusEl.textContent = "Loading…";
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
    result.hidden = false;
    statusEl.hidden = true;
    ensureMap(lat, lon, viewport.zoom || 10);
    setTimeout(() => map.invalidateSize(), 50);
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
  statusEl.hidden = false;
  statusEl.className = "status";
  statusEl.textContent = "Saving…";
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

loadPins();
