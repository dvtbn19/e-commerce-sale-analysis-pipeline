# E-Commerce Sale Analysis

An end-to-end data engineering pipeline that turns a raw Amazon sales export into a monitored, self-healing analytics service running on Kubernetes — ingestion, transformation, an API with caching, a dashboard with authenticated data entry, orchestration, observability, and CI/CD, all built as a hands-on portfolio project.

## Why this project exists

Most portfolio pipelines stop at "the notebook runs." This one is built to answer the questions a real Data Engineer actually gets asked:

- Does the pipeline survive a dependency going down, or does it just fall over?
- Can someone else redeploy this from the Helm chart alone, or does it only work on one laptop?
- If the database is lost, is there a tested backup — or just an assumption that there is?
- Is there evidence (tests, CI runs, dashboards) that this works, or just a claim that it does?

Every section below links to something that was actually run and verified, not just written down.

## Architecture

```mermaid
flowchart LR
    CSV["Amazon Sale Report CSV"] --> ING["services/ingestion"]
    ING --> RAW[("PostgreSQL raw.amazon_sales")]
    RAW --> STG[("dbt: staging.stg_amazon_sales")]
    STG --> FACT[("dbt: analytics.fct_sales")]
    FACT --> SUMM[("analytics.sales_summary")]
    FACT --> CAT[("analytics.sales_by_category")]

    SUMM --> API["FastAPI"]
    CAT --> API
    FACT --> API
    API <--> REDIS[("Redis cache")]

    GATEWAY["Kubernetes Gateway API"] --> API
    GATEWAY --> FRONTEND["React dashboard"]
    USER(["Browser"]) --> GATEWAY

    API -. "authenticated writes" .-> RAW
    API -. rebuild .-> SUMM

    AIRFLOW["Airflow DAG"] -. orchestrates .-> ING
    AIRFLOW -.-> STG

    API -. "/metrics" .-> PROM["Prometheus"]
    PROM --> GRAF["Grafana"]
```

The Airflow DAG (`ecommerce_pipeline`) runs the pipeline end to end: `ingest -> dbt run -> dbt test -> invalidate_cache`. See [airflow/dags/ecommerce_pipeline.py](airflow/dags/ecommerce_pipeline.py).

## Tech stack

| Layer | Technology |
|---|---|
| Orchestration | Apache Airflow |
| Transformation | dbt (Postgres adapter) |
| Database | PostgreSQL 16 |
| Cache | Redis 7 |
| API | FastAPI + SQLAlchemy |
| Authentication | bcrypt password hashing, JWT in an httpOnly cookie |
| Frontend | React + Vite, served by nginx |
| Runtime | Kubernetes (Kind locally) |
| Deployment | Helm |
| Networking | Kubernetes Gateway API (Envoy via cloud-provider-kind) |
| Monitoring | kube-prometheus-stack (Prometheus + Grafana + Alertmanager) |
| CI/CD | GitHub Actions |
| Container registry | GitHub Container Registry (GHCR) |

## Repository layout

```text
airflow/             Airflow DAG + Docker Compose for local Airflow
dbt/ecommerce/       dbt project: staging + analytics models, tests
helm/ecommerce/      Helm chart for the application (Postgres, Redis, API, frontend, routes, alert rules)
k8s/                 Original raw manifests; superseded by the Helm chart except the shared Gateway and Airflow route
monitoring/          kube-prometheus-stack values, Grafana dashboard, and the monitoring install runbook
scripts/             Operational PowerShell scripts (startup health check, Postgres backup)
services/api/        FastAPI application + pytest suite
services/frontend/   React dashboard
services/ingestion/  CSV -> PostgreSQL loader + pytest suite + CI test fixture
.github/workflows/   CI pipeline
```

## Prerequisites

- Docker Desktop
- A [Kind](https://kind.sigs.k8s.io/) cluster named `ecommerce-local` with the Kubernetes Gateway API installed and a `Gateway` named `ecommerce-gateway` in namespace `gateway-system`
- `kubectl`, `helm`
- [cloud-provider-kind](https://github.com/kubernetes-sigs/cloud-provider-kind), which provides the Gateway's address on Kind
- Python 3.12, Node.js 22 for local development
- `dbt-core==1.12.2` and `dbt-postgres==1.11.0` for running dbt locally

> Creating the Kind cluster and installing the Gateway API CRDs from a completely empty machine isn't scripted yet — see [Known gaps](#known-gaps).

## Getting started after a reboot

Everything here runs locally on Docker + Kind, so it all stops when the machine shuts down.

1. Start Docker Desktop and wait until it's ready.
2. Run the startup health check from the project root:

   ```powershell
   .\scripts\start-profile-a.ps1
   ```

   It checks the Kind cluster and `kubectl` context, starts `cloud-provider-kind.exe` (elevated) if it isn't already running, detects and repairs a stale Gateway Envoy dataplane or a stale Windows `netsh portproxy` mapping, then verifies that the frontend, API, Airflow, Prometheus, Grafana, and the API's `/metrics` endpoint are all reachable through `http://ecommerce.local`, `http://api.ecommerce.local`, and `http://airflow.ecommerce.local`. It throws at the first failing step, naming exactly what to look at.
3. `Profile A is healthy.` means everything is up.

## Deploying changes

`helm/ecommerce` is the single source of deployment truth for PostgreSQL, Redis, the API, and the frontend. Don't `kubectl apply` those resources directly — it will fight with Helm's state.

```powershell
helm lint helm/ecommerce
helm template ecommerce helm/ecommerce | Out-Null
helm upgrade ecommerce helm/ecommerce --namespace ecommerce --wait --timeout 5m
```

Roll back a bad release:

```powershell
helm history ecommerce --namespace ecommerce
helm rollback ecommerce <REVISION> --namespace ecommerce --wait
```

The Gateway (`k8s/gateway/gateway.yml`) and the Airflow route are kept outside the application chart on purpose, so uninstalling the app can never take down shared infrastructure.

### Rebuilding the application images

Kind has its own image store, so a locally built image has to be loaded into the cluster before the chart can reference it:

```powershell
docker build -t ecommerce-api:v8 services/api
docker build -t ecommerce-frontend:v2 --build-arg VITE_API_BASE_URL=http://api.ecommerce.local services/frontend
kind load docker-image ecommerce-api:v8 --name ecommerce-local
kind load docker-image ecommerce-frontend:v2 --name ecommerce-local
```

Then bump `api.image.tag` / `frontend.image.tag` in `values.yaml` and run `helm upgrade`.

The frontend's API URL is compiled in by Vite at build time, not read at runtime, so pointing the dashboard at a different API means rebuilding the image — not editing a ConfigMap.

If `helm upgrade` fails with `conflict with "kubectl-client-side-apply"`, a field on that resource was once set by hand with `kubectl`, and Helm's server-side apply refuses to overwrite another field manager's field. Re-run with `--force-conflicts` to hand ownership back to the chart. That is the fix, not a workaround — but it is worth treating as a reminder of why chart-managed resources should never be edited with `kubectl` in the first place.

## CI/CD

Every push to `main` and every pull request runs [.github/workflows/ci.yml](.github/workflows/ci.yml):

| Job | What it checks |
|---|---|
| `python-tests` | pytest for `services/api` and `services/ingestion` — 40 tests covering `/live`/`/ready`, pagination validation, Redis cache HIT/MISS/BYPASS, CSV column normalization, DSN construction, login and token handling, the authenticated write endpoint with its validation and rate limit, and the environment-driven CORS configuration |
| `frontend` | `eslint` + `vite build` |
| `helm` | `helm lint` + `helm template` |
| `dbt-tests` | Loads a 30-row fixture into a throwaway Postgres service container, then runs `dbt run` and `dbt test` — 20 tests covering row-count consistency across raw/staging/analytics, not-null and uniqueness constraints, accepted category values, and the raw date format |

On push to `main`, once all four jobs pass, two more jobs build the API and frontend Docker images and push them to GHCR, tagged with the commit SHA and `latest` — replacing manually incrementing `v1`/`v2`/`v3` tags.

## Reading and writing data

The dashboard is readable by anyone who can reach it. Adding a sale requires an account.

| Path | Access |
|---|---|
| `GET /api/sales`, `/summary`, `/categories` | Open |
| `POST /api/sales` | Requires a valid session cookie |
| `POST /api/auth/login`, `/logout`, `GET /api/auth/me` | Session management |

There is deliberately **no self-registration endpoint**. Accounts are provisioned by running a seed script against a local, gitignored file of credentials:

```powershell
python services\api\seed_users.py
```

It reads `services/api/.env.users` (one `username:password` per line, `#` for comments), creates the `auth` schema and `auth.users` table if needed, and upserts bcrypt hashes. Re-run it to add an account or reset a password. The file itself is never committed.

Logging in issues a JWT in an httpOnly cookie with `SameSite=Lax`. The dashboard (`ecommerce.local`) and the API (`api.ecommerce.local`) are different hosts but share a registrable domain, so the browser treats them as same-site and the cookie travels without needing `SameSite=None`.

The signing key is read from the `api-auth` Secret. The application falls back to a development default only outside production, and that default is published in this repository — so the Secret must exist before the API can be trusted:

```powershell
$jwt = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 48 | ForEach-Object { [char]$_ })
kubectl create secret generic api-auth --namespace ecommerce --from-literal=jwt-secret=$jwt
Remove-Variable jwt
```

Setting `api.auth.appEnv: production` in the chart makes both `AUTH_JWT_SECRET` and an explicit CORS origin list mandatory, and `helm template` fails outright if either is missing — a misconfiguration becomes a template-time error instead of a running service with a publicly known signing key.

### What a write actually does

`POST /api/sales` is not a plain insert. In one transaction it writes the row to `raw.amazon_sales` (the source of truth, so the next `dbt run` does not erase it) and the equivalent row to `analytics.fct_sales`, then rebuilds `analytics.sales_summary` and `analytics.sales_by_category` with the same SQL as the dbt models. Afterwards it invalidates the Redis cache keys. The result is that a new sale shows up in the dashboard immediately rather than at the next pipeline run.

Writes are validated against the same nine categories the dbt `accepted_values` test enforces, so a manual entry can never break the pipeline it feeds. They are also rate-limited to 20 per minute per user through Redis — defence in depth, since a shared or compromised account should not be able to hammer the database.

Writing into a raw layer means matching the raw layer's conventions, not the API's. `raw.amazon_sales.date` is a text column holding the source CSV's `MM-DD-YY` strings, and the staging model parses it with exactly that mask — so an ISO date written there is accepted by Postgres and then kills the next `dbt run`. The endpoint formats that column to match the CSV and passes a real date only to `analytics.fct_sales`, where the column is typed. Both a pytest regression test and a dbt `assert_raw_date_format` test now guard this, the latter so bad data is reported by `dbt test` instead of crashing `dbt run`.

Verified end to end: with five API-written sales in the database, a full `dbt run` rebuilt `analytics.fct_sales` from `raw` and the row count, the distinct `source_row_id` count, and the revenue total were byte-identical before and after — the manual rows survived, were not duplicated, and came back out of the pipeline with correctly parsed dates.

## Monitoring

Prometheus and Grafana run in the `monitoring` namespace, installed via a pinned `kube-prometheus-stack` release. See [monitoring/README.md](monitoring/README.md) for the full install/upgrade runbook. Quick access:

```powershell
kubectl port-forward --namespace monitoring service/monitoring-grafana 3000:80
kubectl port-forward --namespace monitoring service/monitoring-kube-prometheus-prometheus 9090:9090
```

Three Prometheus alert rules ship with the application chart ([helm/ecommerce/templates/api-prometheusrule.yaml](helm/ecommerce/templates/api-prometheusrule.yaml)):

| Alert | Fires when |
|---|---|
| `EcommerceApiDown` | Prometheus can't scrape any API target |
| `EcommerceApiHigh5xxErrorRate` | 5xx rate exceeds the configured threshold with enough request volume to be meaningful |
| `EcommerceApiHighP95Latency` | p95 request latency exceeds the configured threshold with enough request volume to be meaningful |

## Backup and restore

```powershell
.\scripts\backup-postgres.ps1
```

Opens a temporary port-forward to `postgres-service`, runs `pg_dump` in custom format through a throwaway `postgres:16` container (no local PostgreSQL client install needed), verifies the archive's table of contents, and writes it to `backups/<timestamp>.dump`. That directory is gitignored — a database dump is never committed.

To restore, run `pg_restore` from the same image against a target database:

```powershell
docker run --rm `
  -e PGPASSWORD=<password> `
  -v "${PWD}\backups:/backups" `
  postgres:16 `
  pg_restore -h host.docker.internal -p <port> -U ecommerce -d ecommerce --no-owner --no-privileges /backups/<file>.dump
```

**Restoring into the real `postgres-service` overwrites existing data — confirm the target before running it there.** Restoring into a disposable container first, on a different local port, is the safe way to verify a backup without touching real data.

Verified 2026-09-12: a fresh backup restored into a disposable container reproduced the live database exactly — `raw.amazon_sales` and `analytics.fct_sales` both at 128,975 rows in both the source and the restored copy.

## Reliability

- The API exposes `/live` and `/ready`; PostgreSQL and Redis have their own liveness/readiness probes.
- Redis failure degrades gracefully: the API falls back to PostgreSQL and returns `X-Cache: BYPASS` instead of failing the request.
- PostgreSQL failure is caught by `/ready`, so Kubernetes stops routing traffic to a pod that can't serve requests instead of returning errors to users.
- Resource requests/limits are set on the API, frontend, PostgreSQL, Redis, and Airflow workloads.
- PostgreSQL backups are verified restorable (see above), not just assumed to work.

## Scope: local by design

This runs entirely on one machine — Kind, reachable through `*.ecommerce.local` hostnames — and is not deployed publicly. That was a deliberate choice, not an unfinished step.

A public deployment was fully planned (a small VPS running k3s, Envoy Gateway, cert-manager for TLS, DNS records on a domain already owned, and a CI job deploying on every push to `main`) and then dropped: the project's purpose is to demonstrate the engineering, and paying to keep a server running adds no evidence that the pipeline works. The application code carries no local-only assumptions — CORS origins, the cookie's `Secure` flag, and the JWT secret are all environment-driven, and `api.auth.appEnv: production` already enforces the stricter rules — so the remaining work would be infrastructure, not rewriting.

## Known gaps

- First-time cluster bootstrap (creating the Kind cluster, installing the Gateway API CRDs, initial secrets) isn't scripted end-to-end yet — today it's a manual, undocumented one-time setup.
- No centralized log aggregation; logs are read per-Pod with `kubectl logs`.
- Secrets are plain Kubernetes Secrets; SOPS/Sealed Secrets has been discussed but not adopted.
- Kubernetes hardening (NetworkPolicy, non-root containers, PodDisruptionBudget) isn't applied yet.
- A larger "Profile B" architecture (MinIO/Parquet/Iceberg/Spark/Trino, Kafka if real-time ingestion is ever needed) was scoped as a deliberate future direction, not started — this project stays PostgreSQL-centric by design at its current scale.
