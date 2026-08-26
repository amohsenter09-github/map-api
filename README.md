# map-api

Map API microservice built with FastAPI.

Kubernetes manifests live in the sibling `kustomization-resources-applications` repo (`apps/map-api`, image `map-api:01`).

## Endpoints

- `GET /health` -> process up (does not need Postgres)
- `GET /ready` -> Postgres reachable
- `GET /geocode?city=Berlin` -> forward geocode
- `GET /reverse?latitude=52.52&longitude=13.41` -> reverse geocode (Nominatim / OpenStreetMap)
- `GET /map` -> location plus viewport (`center`, `bounding_box`, `zoom`)
- `POST /pins` -> save a pin (`{"city":"Berlin"}` or `{"latitude":52.52,"longitude":13.41,"label":"Home"}`)
- `GET /pins` -> list saved pins
- `GET /pins/{id}` -> one pin
- `DELETE /pins/{id}` -> remove a pin
- `POST /pins/{id}/reverse` -> fill name/country/address from Nominatim and store it
- `PUT /pins/{id}` -> move or rename a pin
- `POST /pins/{id}/notes` -> `{ "body": "met here" }`
- `GET /pins/{id}/notes` -> notes on a pin

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

For `POST /pins` and `GET /ready`, start Postgres first (`docker compose up postgres`).

## Docker

```bash
docker compose up --build
```

Local host port: **8002** (`http://localhost:8002`). Postgres is on host **5433**.

```bash
curl -X POST http://localhost:8002/pins -H 'Content-Type: application/json' -d '{"city":"Berlin"}'
curl http://localhost:8002/pins
```

## Kubernetes

```bash
docker build -t map-api:01 .
kubectl apply -k ../kustomization-resources-applications/apps/map-api/overlays/local
```
