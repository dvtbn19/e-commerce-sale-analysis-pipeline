# Monitoring Profile A Runbook

## Purpose

This runbook installs and verifies the local monitoring stack for the E-Commerce Sale Analysis project.

## Monitoring flow

```text
FastAPI /metrics
       ↓
ServiceMonitor
       ↓
Prometheus
       ↓
Grafana
```

## Pinned configuration

| Component | Configuration |
|---|---|
| Kubernetes environment | kind |
| Kubernetes context | `kind-ecommerce-local` |
| Namespace | `monitoring` |
| Helm release | `monitoring` |
| kube-prometheus-stack | `89.2.2` |
| Prometheus Operator | `v0.93.1` |
| Prometheus retention | `3d` |
| Prometheus storage | `5Gi`, StorageClass `standard` |
| Grafana storage | `1Gi`, StorageClass `standard` |
| Values file | `monitoring/values-profile-a.yaml` |
| Grafana dashboard backup | `monitoring/grafana/ecommerce-api-monitoring.json` |

The `monitoring/chart-cache` directory is local working data and must not be committed.

## CRD lifecycle

Prometheus Operator CRDs are managed separately from the main `monitoring` Helm release. The values file therefore contains:

```yaml
crds:
  enabled: false
```

On a new cluster, apply the CRD manifests from the same pinned chart version before installing the monitoring stack. Use `kubectl` only for those CRD manifests.

Manage all other monitoring resources, including Deployments, Services, ServiceMonitors, Prometheus and Alertmanager, through Helm.

Do not delete monitoring CRDs during routine uninstall or troubleshooting. Deleting a CRD can also remove all custom resources created from it.

Helm does not automatically upgrade CRDs during a normal chart upgrade. Review the kube-prometheus-stack upgrade guide before changing the chart version:

<https://github.com/prometheus-community/helm-charts/blob/main/charts/kube-prometheus-stack/UPGRADE.md>

## Prerequisites

Run all commands from the project root in PowerShell.

Confirm that the intended kind cluster is active:

```powershell
$currentContext = kubectl config current-context
if ($currentContext -ne "kind-ecommerce-local") { throw "Unexpected Kubernetes context: $currentContext" }
kubectl get nodes
helm version --short
```

Configure the Prometheus Community Helm repository:

```powershell
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts --force-update
helm repo update
```

## Prepare the pinned chart

Download the exact chart version into a unique temporary directory:

```powershell
$monitoringChartVersion = "89.2.2"
$monitoringChartRoot = Join-Path $env:TEMP ("kps-" + $monitoringChartVersion + "-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $monitoringChartRoot | Out-Null
helm pull prometheus-community/kube-prometheus-stack --version $monitoringChartVersion --untar --untardir $monitoringChartRoot
$monitoringChartPath = Join-Path $monitoringChartRoot "kube-prometheus-stack"
helm show chart $monitoringChartPath | Select-String -Pattern '^(version|appVersion):'
```

Expected versions:

```text
appVersion: v0.93.1
version: 89.2.2
```

## Install or update the CRDs

Resolve the CRD chart and manifest directories:

```powershell
$monitoringCrdsChartPath = Join-Path $monitoringChartPath "charts\crds"
$monitoringCrdsManifestPath = Join-Path $monitoringCrdsChartPath "crds"
Test-Path -LiteralPath $monitoringCrdsManifestPath
```

The final command must return `True`.

Lint the CRD chart and validate the CRDs with the Kubernetes API server:

```powershell
helm lint $monitoringCrdsChartPath
kubectl apply --server-side --dry-run=server --field-manager=helm -f $monitoringCrdsManifestPath
```

Stop if either validation command fails. After successful validation, apply only the CRD manifests:

```powershell
kubectl apply --server-side --field-manager=helm -f $monitoringCrdsManifestPath
$monitoringCrdResources = kubectl create --dry-run=client -f $monitoringCrdsManifestPath -o name
$monitoringCrdResources | ForEach-Object { kubectl wait --for=condition=Established $_ --timeout=120s }
kubectl api-resources --api-group=monitoring.coreos.com
```

Do not add `--force-conflicts` when an update fails. Review the CRD conflict and the chart upgrade guide first.

## Validate the monitoring stack

Resolve the project values file:

```powershell
$monitoringValuesPath = (Resolve-Path ".\monitoring\values-profile-a.yaml").Path
```

Run lint, render and server-side dry-run:

```powershell
helm lint $monitoringChartPath --values $monitoringValuesPath
helm template monitoring $monitoringChartPath --namespace monitoring --values $monitoringValuesPath | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Helm template failed." }
helm upgrade --install monitoring $monitoringChartPath --namespace monitoring --create-namespace --values $monitoringValuesPath --dry-run=server --hide-secret
```

The dry-run must finish with `DESCRIPTION: Dry run complete`.

## Install or upgrade the monitoring stack

Run the deployment only after all validation steps succeed:

```powershell
helm upgrade --install monitoring $monitoringChartPath --namespace monitoring --create-namespace --values $monitoringValuesPath --wait --timeout 10m
```

Do not apply the rendered monitoring manifests with `kubectl apply`.

## Verify the deployment

Check the Helm release, Pods, persistent volumes and monitoring resources:

```powershell
helm status monitoring --namespace monitoring
kubectl get pods --namespace monitoring
kubectl get pvc --namespace monitoring
kubectl get prometheus --namespace monitoring
kubectl get servicemonitor --all-namespaces
```

Expected storage:

- Prometheus PVC: `Bound`, `5Gi`, StorageClass `standard`.
- Grafana PVC: `monitoring-grafana`, `Bound`, `1Gi`, StorageClass `standard`.

The `standard` StorageClass in the local kind environment uses local storage. PVC data survives Pod replacement but does not constitute a backup of the entire kind cluster.

## Access Grafana

Read the generated Grafana administrator password:

```powershell
$grafanaPasswordBase64 = kubectl get secret monitoring-grafana --namespace monitoring -o jsonpath='{.data.admin-password}'
[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($grafanaPasswordBase64))
```

Start port forwarding in a dedicated terminal:

```powershell
kubectl port-forward --namespace monitoring service/monitoring-grafana 3000:80
```

Open <http://localhost:3000>.

If the E-Commerce API dashboard is missing, import:

```text
monitoring/grafana/ecommerce-api-monitoring.json
```

Choose the `Prometheus` datasource if Grafana requests a datasource mapping.

## Access Prometheus

Start port forwarding in a dedicated terminal:

```powershell
kubectl port-forward --namespace monitoring service/monitoring-kube-prometheus-prometheus 9090:9090
```

Open the targets page:

<http://localhost:9090/targets>

The E-Commerce API target must appear as:

```text
serviceMonitor/ecommerce/ecommerce-api/0
```

Its state must be `UP`.

## Verify FastAPI application metrics

The API metrics endpoint and ServiceMonitor are managed by the `ecommerce` Helm chart.

Check the deployed image, metrics endpoint and ServiceMonitor:

```powershell
kubectl get deployment ecommerce-api --namespace ecommerce -o custom-columns='NAME:.metadata.name,IMAGE:.spec.template.spec.containers[*].image,READY:.status.readyReplicas'
curl.exe -i http://api.ecommerce.local/metrics
kubectl get servicemonitor ecommerce-api --namespace ecommerce
```

Expected API image:

```text
ecommerce-api:v7
```

The metrics endpoint must return HTTP `200` and include metrics such as:

```text
http_requests_total
http_request_duration_seconds
```

## Verify Grafana persistence

Back up any manually created dashboard before testing persistence. Restart Grafana and wait for the rollout:

```powershell
kubectl rollout restart deployment/monitoring-grafana --namespace monitoring
kubectl rollout status deployment/monitoring-grafana --namespace monitoring --timeout=5m
```

Open Grafana again without importing the dashboard. The `E-Commerce API Monitoring` dashboard must still contain:

- API Request Rate
- API 5xx Error Rate
- API Average Latency

## Upgrade procedure

When changing the kube-prometheus-stack version:

1. Read the upstream upgrade guide for every version boundary.
2. Download the exact target chart version into a new temporary directory.
3. Run the CRD lint and server-side dry-run.
4. Apply the CRDs before upgrading the main stack.
5. Run Helm lint, render and server-side dry-run for the main stack.
6. Upgrade the `monitoring` Helm release with `--wait`.
7. Verify Pods, PVCs, Prometheus targets and Grafana dashboards.
8. Update the pinned versions in this runbook.

A Helm rollback of the main stack does not roll back CRDs. Treat CRD changes as a separate lifecycle.