# goit-mlops-fp

Final project for the MLOps CI/CD course.

The project implements a local Kubernetes-based MLOps workflow for a FastAPI ML inference service.

The original task mentions GitLab CI, but this project uses GitHub Actions because the repository is hosted on GitHub. The workflow implements the same CI/CD logic: retrain model, build Docker image, update Helm values, and trigger redeployment through GitOps.

## Components

| Component       | Purpose                                         |
| --------------- | ----------------------------------------------- |
| FastAPI         | ML inference API                                |
| scikit-learn    | Model training and prediction                   |
| Drift detector  | Detects out-of-range input features             |
| Docker          | Packages the API and model                      |
| Helm            | Deploys the service to Kubernetes               |
| ArgoCD          | GitOps deployment with auto-sync and self-heal  |
| Prometheus      | Collects application metrics                    |
| Grafana         | Shows requests, latency, and drift metrics      |
| Loki + Promtail | Collects and stores application logs            |
| GitHub Actions  | Runs model retraining and image update pipeline |

## Project structure

```text
goit-mlops-fp/
├── app/
│   ├── __init__.py
│   ├── drift.py
│   ├── main.py
│   └── schemas.py
├── model/
│   ├── train.py
│   ├── model.pkl
│   └── model_metadata.json
├── helm/
│   ├── Chart.yaml
│   ├── values.yaml
│   ├── values-ghcr.yaml
│   └── templates/
│       ├── deployment.yaml
│       ├── service.yaml
│       └── servicemonitor.yaml
├── argocd/
│   └── application.yaml
├── prometheus/
│   └── additionalScrapeConfigs.yaml
├── grafana/
│   └── dashboards.json
├── loki/
│   ├── loki-values.yaml
│   └── promtail-values.yaml
├── .github/
│   └── workflows/
│       └── retrain-model.yml
├── Dockerfile
├── requirements.txt
├── .dockerignore
├── .gitignore
└── README.md
```

## Requirements

Required local tools:

* Python 3.11
* Docker
* kind
* kubectl
* Helm

Install Kubernetes tools on macOS:

```bash
brew install kind kubectl helm
```

## 1. Install Python dependencies

```bash
python3.11 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 2. Train the model

```bash
python model/train.py
```

The script generates:

```text
model/model.pkl
model/model_metadata.json
```

The model is loaded by the FastAPI service at startup.

## 3. Run the API locally

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status":"ok"}
```

Prediction request:

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"features":[0.1,0.2,0.3,0.4]}'
```

Example response:

```json
{"prediction":0,"drift_detected":false}
```

Drift request:

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"features":[100,0.2,0.3,0.4]}'
```

Example response:

```json
{"prediction":1,"drift_detected":true}
```

The drift detector marks a request as drift when at least one input feature exceeds `DRIFT_THRESHOLD`.

Default value:

```text
DRIFT_THRESHOLD=5.0
```

## 4. Build Docker image

```bash
docker build -t goit-mlops-fp:local .
```

Run the container:

```bash
docker run --rm -p 8000:8000 goit-mlops-fp:local
```

Check:

```bash
curl http://localhost:8000/health
```

## 5. Create local Kubernetes cluster

```bash
kind create cluster --name goit-mlops-fp
```

Build and load the image into kind:

```bash
docker build -t goit-mlops-fp:local .
kind load docker-image goit-mlops-fp:local --name goit-mlops-fp
```

## 6. Install Prometheus and Grafana

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
```

```bash
helm upgrade --install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace
```

Check pods:

```bash
kubectl get pods -n monitoring
```

## 7. Deploy the application with Helm

```bash
helm upgrade --install goit-mlops-fp ./helm
```

Check resources:

```bash
kubectl get deploy
kubectl get pods
kubectl get svc
kubectl get servicemonitor
```

Expected resources:

```text
deployment.apps/goit-mlops-fp
service/goit-mlops-fp
servicemonitor.monitoring.coreos.com/goit-mlops-fp
```

## 8. Test the deployed API

Forward the service port:

```bash
kubectl port-forward svc/goit-mlops-fp 8000:8000
```

Health check:

```bash
curl http://localhost:8000/health
```

Prediction:

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"features":[0.1,0.2,0.3,0.4]}'
```

Drift check:

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"features":[100,0.2,0.3,0.4]}'
```

## 9. Check logs

```bash
kubectl logs deploy/goit-mlops-fp
```

Expected log entries:

```text
Prediction request
Drift detected
```

## 10. Check Prometheus metrics

The API exposes metrics on:

```text
/metrics
```

Check directly:

```bash
curl http://localhost:8000/metrics
```

Expected custom metrics:

```text
inference_requests_total
drift_detected_total
prediction_latency_seconds
```

Open Prometheus:

```bash
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090
```

Open:

```text
http://localhost:9090
```

Useful PromQL queries:

```promql
rate(inference_requests_total[1m]) * 60
```

```promql
rate(prediction_latency_seconds_sum[1m])
/
rate(prediction_latency_seconds_count[1m])
```

```promql
increase(drift_detected_total[5m])
```

## 11. Check Grafana dashboard

Open Grafana:

```bash
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80
```

Open:

```text
http://localhost:3000
```

Login:

```text
admin
```

Get password:

```bash
kubectl get secret -n monitoring prometheus-grafana \
  -o jsonpath="{.data.admin-password}" | base64 --decode
echo
```

Dashboard file:

```text
grafana/dashboards.json
```

Import path:

```text
Dashboards → New → Import
```

The dashboard contains:

* requests per minute
* average prediction latency
* drift detections

## 12. Install Loki and Promtail

```bash
helm repo add grafana-community https://grafana-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
```

Install Loki:

```bash
helm upgrade --install loki grafana-community/loki \
  --namespace logging \
  --create-namespace \
  -f loki/loki-values.yaml
```

Install Promtail:

```bash
helm upgrade --install promtail grafana/promtail \
  --namespace logging \
  -f loki/promtail-values.yaml
```

Check:

```bash
kubectl get pods -n logging
kubectl get daemonset -n logging
```

Add Loki datasource in Grafana:

```text
Connections → Data sources → Add data source → Loki
```

Loki URL:

```text
http://loki.logging.svc.cluster.local:3100
```

Check logs in Grafana Explore:

```logql
{namespace="default"} |= "Prediction request"
```

```logql
{namespace="default"} |= "Drift detected"
```

## 13. ArgoCD

ArgoCD manifest:

```text
argocd/application.yaml
```

It enables:

* GitHub repository source
* Helm chart deployment
* auto-sync
* prune
* self-heal

Install ArgoCD:

```bash
kubectl create namespace argocd
```

```bash
kubectl apply -n argocd \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

Check:

```bash
kubectl get pods -n argocd
```

Open ArgoCD UI:

```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

Open:

```text
https://localhost:8080
```

Get admin password:

```bash
kubectl get secret argocd-initial-admin-secret \
  -n argocd \
  -o jsonpath="{.data.password}" | base64 --decode
echo
```

Apply application:

```bash
kubectl apply -f argocd/application.yaml
```

Check:

```bash
kubectl get applications -n argocd
```

Expected result:

```text
goit-mlops-fp   Synced   Healthy
```

## 14. GitHub Actions retrain pipeline

Workflow file:

```text
.github/workflows/retrain-model.yml
```

Manual run:

```text
GitHub → Actions → Retrain Model → Run workflow
```

The workflow:

1. Runs `python model/train.py`
2. Generates a new `model.pkl`
3. Builds a Docker image
4. Pushes the image to GHCR
5. Updates `helm/values-ghcr.yaml`
6. Pushes the updated files to the `final-project` branch

Image location:

```text
ghcr.io/<github-username>/goit-mlops-fp
```

For local ArgoCD deployment with GHCR, the GHCR package should be public.

## 15. Update the model manually

```bash
python model/train.py
docker build -t goit-mlops-fp:local .
kind load docker-image goit-mlops-fp:local --name goit-mlops-fp
helm upgrade --install goit-mlops-fp ./helm
kubectl rollout restart deploy/goit-mlops-fp
```

## Final verification checklist

FastAPI service:

```bash
curl http://localhost:8000/health
```

Prediction:

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"features":[0.1,0.2,0.3,0.4]}'
```

Drift:

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"features":[100,0.2,0.3,0.4]}'
```

Logs:

```bash
kubectl logs deploy/goit-mlops-fp
```

Metrics:

```bash
curl http://localhost:8000/metrics
```

Prometheus:

```promql
rate(inference_requests_total[1m]) * 60
```

Grafana:

```text
Dashboard shows requests, latency, and drift detections.
```

Loki:

```logql
{namespace="default"} |= "Drift detected"
```

GitHub Actions:

```text
Retrain Model workflow completes successfully.
```

ArgoCD:

```text
goit-mlops-fp application is Synced and Healthy.
```
