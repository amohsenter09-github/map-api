const form = document.getElementById("form");
const statusEl = document.getElementById("status");
const result = document.getElementById("result");
const placeEl = document.getElementById("place");
let map;
let marker;

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
    placeEl.textContent = place;
    result.hidden = false;
    statusEl.hidden = true;
    ensureMap(lat, lon, viewport.zoom || 10);
    setTimeout(() => map.invalidateSize(), 50);
  } catch (error) {
    statusEl.className = "status error";
    statusEl.textContent = error.message;
  }
});
