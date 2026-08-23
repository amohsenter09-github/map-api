# map-api

Map API microservice built with FastAPI.

## Endpoints

- `GET /health` -> service health check
- `GET /geocode?city=Berlin` -> forward geocode
- `GET /reverse?latitude=52.52&longitude=13.41` -> reverse geocode
- `GET /map` -> location plus viewport (`center`, `bounding_box`, `zoom`)

### `GET /map` query params

- `city` (string) OR
- `latitude` (float) + `longitude` (float)
- `zoom` (int, optional, 1-18, default 10)

Example:

- `GET /map?city=Berlin`
- `GET /map?latitude=52.52&longitude=13.41&zoom=12`

## Local dev (venv)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open API docs at `http://localhost:8000/docs`.

## Docker

```bash
docker compose up --build
```

## Kubernetes

Overlays live under `k8s/overlays/`:

| Overlay | Cluster | Namespace | Host | Image |
| --- | --- | --- | --- | --- |
| `local` | kind | `map-api` | `map-api.local` | `map-api:local` |
| `cnpe-dev` | cnpe-dev | `map-api-cnpe-dev` | `map-api.cnpe-dev` | `map-api:cnpe-dev` |
| `cnpe-prod` | cnpe-prod | `map-api-cnpe-prod` | `map-api.cnpe-prod` | `map-api:cnpe-prod` |

```bash
./scripts/kustomize-build.sh
```

### Local kind

```bash
kind delete cluster --name local-cluster
kind create cluster --name local-cluster --config kind-ingress-config.yaml
kubectl config use-context kind-local-cluster
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
kubectl -n ingress-nginx wait --for=condition=Ready pod -l app.kubernetes.io/component=controller --timeout=180s
docker build -t map-api:local .
kind load docker-image map-api:local --name local-cluster
kubectl apply -k k8s/overlays/local
sudo sh -c 'echo "127.0.0.1 map-api.local" >> /etc/hosts'
```

Then open `http://map-api.local/map?city=Berlin`.

### CNPE

```bash
kubectl apply -k k8s/overlays/cnpe-dev
kubectl apply -k k8s/overlays/cnpe-prod
```
