param(
    [string]$ExpectedContext = "kind-ecommerce-local",
    [string]$CloudProviderKindPath = "C:\tools\cloud-provider-kind\cloud-provider-kind.exe"
)

$ErrorActionPreference = "Stop"

Write-Host "[0] Checking Kubernetes context..."

$CurrentContext = kubectl config current-context

if ($LASTEXITCODE -ne 0) {
    throw "Could not read the current Kubernetes context."
}

if ($CurrentContext -ne $ExpectedContext) {
    throw "Unexpected Kubernetes context: $CurrentContext"
}

Write-Host "Kubernetes context is correct: $CurrentContext"

Write-Host "[1] Checking Docker..."

docker info *> $null

if ($LASTEXITCODE -ne 0) {
    throw "Docker Desktop is not ready."
}

Write-Host "Docker is ready."


Write-Host "[2] Checking Kind cluster..."

kubectl wait --for=condition=Ready node/ecommerce-local-control-plane --timeout=5s *> $null

if ($LASTEXITCODE -ne 0) {
    throw "Kind cluster ecommerce-local is not ready."
}

Write-Host "Kind cluster is ready."

Write-Host "[3] Checking cloud-provider-kind..."

$CloudProviderKind = Get-Process cloud-provider-kind -ErrorAction SilentlyContinue

if (-not $CloudProviderKind) {
    if (-not (Test-Path -LiteralPath $CloudProviderKindPath -PathType Leaf)) {
        throw "cloud-provider-kind was not found: $CloudProviderKindPath"
    }

    Write-Host "cloud-provider-kind is not running. Starting it..."

    Start-Process -FilePath $CloudProviderKindPath -Verb RunAs -WindowStyle Hidden

    $CloudProviderKind = $null

    for ($i = 0; $i -lt 15; $i++) {
        Start-Sleep -Seconds 1

        $CloudProviderKind = Get-Process cloud-provider-kind -ErrorAction SilentlyContinue

        if ($CloudProviderKind) {
            break
        }
    }

    if (-not $CloudProviderKind) {
        throw "cloud-provider-kind did not start."
    }

    Write-Host "cloud-provider-kind started."
} else {
    Write-Host "cloud-provider-kind is running."
}


Write-Host "[4] Checking Gateway xDS configuration..."

$CloudProviderPid = (Get-Process cloud-provider-kind).Id

$CurrentXdsPort = Get-NetTCPConnection -State Listen -OwningProcess $CloudProviderPid |
    Where-Object { $_.LocalPort -notin 80, 10000 } |
    Select-Object -ExpandProperty LocalPort -First 1

if (-not $CurrentXdsPort) {
    throw "Could not detect the current cloud-provider-kind xDS port."
}

$GatewayContainer = docker ps --filter "label=io.x-k8s.cloud-provider-kind.gateway.name=ecommerce-local/gateway-system/ecommerce-gateway" --format "{{.Names}}" |
    Select-Object -First 1

if (-not $GatewayContainer) {
    throw "Gateway Envoy container was not found."
}

$GatewayCommand = docker inspect $GatewayContainer --format "{{json .Config.Cmd}}"

$XdsMatch = [regex]::Match($GatewayCommand, 'port_value:\s*(\d+)')

if (-not $XdsMatch.Success) {
    throw "Could not detect the xDS port configured in Envoy."
}

$EnvoyXdsPort = [int]$XdsMatch.Groups[1].Value

Write-Host "cloud-provider-kind xDS port: $CurrentXdsPort"
Write-Host "Envoy xDS port:               $EnvoyXdsPort"

if ($CurrentXdsPort -ne $EnvoyXdsPort) {
    Write-Host "Gateway Envoy has stale xDS configuration. Recreating dataplane..."

    docker rm -f $GatewayContainer | Out-Null

    if ($LASTEXITCODE -ne 0) {
        throw "Failed to remove stale Gateway Envoy container."
    }

    $GatewayContainer = $null

    for ($i = 0; $i -lt 90; $i++) {
        Start-Sleep -Seconds 1

        $GatewayContainer = docker ps --filter "label=io.x-k8s.cloud-provider-kind.gateway.name=ecommerce-local/gateway-system/ecommerce-gateway" --format "{{.Names}}" |
            Select-Object -First 1

        if ($GatewayContainer) {
            break
        }
    }

    if (-not $GatewayContainer) {
        throw "Gateway Envoy container was not recreated."
    }

    Write-Host "Gateway Envoy container recreated."
} else {
    Write-Host "Gateway xDS configuration is healthy."
}



Write-Host "[5] Checking Gateway host port..."

$GatewayHostPortRaw = docker port $GatewayContainer 80/tcp |
    Select-Object -First 1

if (-not $GatewayHostPortRaw) {
    throw "Could not detect the Gateway host port."
}

$GatewayHostPort = [int]($GatewayHostPortRaw -replace '^.*:', '')

Write-Host "Gateway host port: $GatewayHostPort"

Write-Host "[6] Checking Windows portproxy..."

$PortProxy = netsh interface portproxy show v4tov4 |
    Select-String '127.0.0.1\s+80\s+127.0.0.1\s+(\d+)'

if ($PortProxy) {
    $PortProxyMatch = [regex]::Match($PortProxy.Line, '127\.0\.0\.1\s+80\s+127\.0.0.1\s+(\d+)')
    $PortProxyTargetPort = [int]$PortProxyMatch.Groups[1].Value

    Write-Host "portproxy target port: $PortProxyTargetPort"

    if ($PortProxyTargetPort -ne $GatewayHostPort) {
        Write-Host "Windows portproxy is stale. Updating it..."

        $Process = Start-Process netsh.exe -Verb RunAs -Wait -PassThru -ArgumentList `
            'interface','portproxy','set','v4tov4',`
            'listenaddress=127.0.0.1','listenport=80',`
            'connectaddress=127.0.0.1',"connectport=$GatewayHostPort"

        if ($Process.ExitCode -ne 0) {
            throw "Failed to update Windows portproxy."
        }

        Write-Host "Windows portproxy updated."
    } else {
        Write-Host "Windows portproxy is healthy."
    }
} else {
    Write-Host "Windows portproxy was not found. Creating it..."

    $Process = Start-Process netsh.exe -Verb RunAs -Wait -PassThru -ArgumentList `
        'interface','portproxy','add','v4tov4',`
        'listenaddress=127.0.0.1','listenport=80',`
        'connectaddress=127.0.0.1',"connectport=$GatewayHostPort"

    if ($Process.ExitCode -ne 0) {
        throw "Failed to create Windows portproxy."
    }

    Write-Host "Windows portproxy created."
}


Write-Host "[7] Checking frontend..."

$FrontendStatus = curl.exe -s -o NUL -w "%{http_code}" http://ecommerce.local

if ($FrontendStatus -ne "200") {
    throw "Frontend health check failed with HTTP $FrontendStatus."
}

Write-Host "Frontend is healthy."

Write-Host "[8] Checking API..."

$ApiStatus = curl.exe -s -o NUL -w "%{http_code}" http://api.ecommerce.local/live

if ($ApiStatus -ne "200") {
    throw "API health check failed with HTTP $ApiStatus."
}

Write-Host "API is healthy."

Write-Host "[9] Checking Airflow..."

$AirflowStatus = curl.exe -s -o NUL -w "%{http_code}" http://airflow.ecommerce.local

if ($AirflowStatus -ne "200") {
    throw "Airflow health check failed with HTTP $AirflowStatus."
}

Write-Host "Airflow is healthy."

Write-Host "[10] Checking Prometheus..."

kubectl wait --for=condition=Available prometheus/monitoring-kube-prometheus-prometheus --namespace monitoring --timeout=10s *> $null

if ($LASTEXITCODE -ne 0) {
    throw "Prometheus is not available."
}

Write-Host "Prometheus is available."

Write-Host "[11] Checking Grafana..."

kubectl wait --for=condition=Available deployment/monitoring-grafana --namespace monitoring --timeout=10s *> $null

if ($LASTEXITCODE -ne 0) {
    throw "Grafana is not available."
}

Write-Host "Grafana is available."

Write-Host "[12] Checking API metrics..."

kubectl get servicemonitor ecommerce-api --namespace ecommerce *> $null

if ($LASTEXITCODE -ne 0) {
    throw "E-Commerce API ServiceMonitor was not found."
}

$MetricsStatus = curl.exe -s -o NUL -w "%{http_code}" http://api.ecommerce.local/metrics

if ($MetricsStatus -ne "200") {
    throw "API metrics health check failed with HTTP $MetricsStatus."
}

Write-Host "API metrics are available."
Write-Host "Profile A is healthy."