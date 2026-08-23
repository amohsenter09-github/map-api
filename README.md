# map-api

Map API microservice built with FastAPI.

Kubernetes manifests live in the sibling `kustomization-resources-applications` repo (`apps/map-api`, image `map-api:01`).

## Endpoints

- `GET /health` -> service health check
- `GET /geocode?city=Berlin` -> forward geocode
- `GET /reverse?latitude=52.52&longitude=13.41` -> reverse geocode (Nominatim / OpenStreetMap)
- `GET /map` -> location plus viewport (`center`, `bounding_box`, `zoom`)

### `GET /map` query params

- `city` (string) OR
- `latitude` (float) + `longitude` (float)
- `zoom` (int, optional, 1-18, default 10)

## Local dev (venv)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8002
```

Open the GUI at `http://localhost:8002/` and API docs at `http://localhost:8002/docs`.

## Docker

```bash
docker build -t map-api:01 .
docker compose up --build
```

Local host port: **8002** (`http://localhost:8002`).

## Kubernetes

```bash
docker build -t map-api:01 .
kubectl apply -k ../kustomization-resources-applications/apps/map-api/overlays/local
```
