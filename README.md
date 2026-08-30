# map-api

Sample FastAPI workload used to exercise the delivery platform. This is not a production mapping product. The useful part is that the same image is built, pushed, and deployed through GitOps to more than one cluster.

Live trail UI (Leaflet), saved pins, and activity points enriched with Open-Meteo weather and AQI.

## Role in the platform

| Piece | Repo |
| --- | --- |
| This app + Dockerfile | [map-api](https://github.com/amohsenter09-github/map-api) |
| Kustomize base + overlays | [kustomization-resources-applications](https://github.com/amohsenter09-github/kustomization-resources-applications) (`apps/map-api`) |
| Argo CD Application | [bootstrap-control-plane](https://github.com/amohsenter09-github/bootstrap-control-plane) (`app-map-dev`, `app-map-prod`) |
| Cluster, registry, DNS | [scaleway-infrastructure](https://github.com/amohsenter09-github/scaleway-infrastructure) |

Argo CD watches the Kustomize overlay. Image Updater watches `rg.fr-par.scw.cloud/cnpe/map-api:02` and rolls a new digest without a tag bump.

**Scaleway URLs:** https://map-api.cnpe-dev.cloud-master-ai.com · https://map-api.cnpe-prod.cloud-master-ai.com

## Implementation

- FastAPI + SQLAlchemy async + PostgreSQL
- Static UI at `/` (`app/static`)
- Geocoding: Open-Meteo + Nominatim
- `POST /activities/{id}/points` samples weather and AQI when the client omits them (`app/services/conditions_client.py`)
- Desktop browsers often block GPS; clicking the map sets position

## Endpoints

- `GET /health` — process up (no Postgres)
- `GET /ready` — Postgres reachable
- `GET /geocode?city=Berlin` — forward geocode
- `GET /reverse?latitude=52.52&longitude=13.41` — reverse geocode
- `GET /map` — viewport (`city` or `latitude`+`longitude`, optional `zoom` 1–18)
- `POST /pins` · `GET /pins` · `GET /pins/{id}` · `PUT /pins/{id}` · `DELETE /pins/{id}`
- `POST /pins/{id}/reverse` · `POST /pins/{id}/notes` · `GET /pins/{id}/notes`
- `POST /activities` · `GET /activities` · `GET /activities/{id}` · `DELETE /activities/{id}`
- `POST /activities/{id}/points` — GPS; weather + AQI sampled if omitted
- `POST /activities/{id}/stop` — distance and duration

## Local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
docker compose up postgres
uvicorn app.main:app --reload --host 0.0.0.0 --port 8002
```

UI: http://localhost:8002/ · docs: http://localhost:8002/docs

Or `docker compose up --build` (API **8002**, Postgres host **5433**).

## Image for Kapsule

Nodes are `linux/amd64`. From this directory (not the parent folder):

```bash
docker buildx build --platform linux/amd64 --provenance=false --sbom=false \
  -t rg.fr-par.scw.cloud/cnpe/map-api:02 --push .
```

Kind local overlay still uses `map-api:01`.
