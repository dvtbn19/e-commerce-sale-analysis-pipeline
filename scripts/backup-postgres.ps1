param(
    [string]$Namespace = "ecommerce",
    [string]$ServiceName = "postgres-service",
    [int]$LocalPort = 5433,
    [string]$Database = "ecommerce",
    [string]$Username = "ecommerce",
    [string]$SecretName = "postgres-credentials",
    [string]$OutputDir = "backups"
)

$ErrorActionPreference = "Stop"

Write-Host "[0] Checking Postgres service..."

kubectl get service $ServiceName -n $Namespace *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Service $ServiceName not found in namespace $Namespace."
}

Write-Host "[1] Starting temporary port-forward to $ServiceName..."

$PortForward = Start-Process -FilePath "kubectl" `
    -ArgumentList "port-forward", "svc/$ServiceName", "$($LocalPort):5432", "-n", $Namespace `
    -WindowStyle Hidden -PassThru

Start-Sleep -Seconds 2

try {
    docker run --rm postgres:16 pg_isready -h host.docker.internal -p $LocalPort -U $Username
    if ($LASTEXITCODE -ne 0) {
        throw "Postgres is not reachable via port-forward."
    }

    Write-Host "[2] Retrieving credentials from Secret $SecretName..."

    $PasswordBase64 = kubectl get secret $SecretName -n $Namespace -o jsonpath='{.data.password}'
    if (-not $PasswordBase64) {
        throw "Could not read password from Secret $SecretName."
    }
    $env:PGPASSWORD = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($PasswordBase64))

    Write-Host "[3] Running pg_dump..."

    New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
    $Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $DumpFile = "ecommerce_$Timestamp.dump"

    docker run --rm `
        -e PGPASSWORD=$env:PGPASSWORD `
        -v "${PWD}\${OutputDir}:/backups" `
        postgres:16 `
        pg_dump -h host.docker.internal -p $LocalPort -U $Username -d $Database -Fc -f "/backups/$DumpFile"

    if ($LASTEXITCODE -ne 0) {
        throw "pg_dump failed."
    }

    Write-Host "[4] Verifying dump contents..."

    docker run --rm -v "${PWD}\${OutputDir}:/backups" postgres:16 pg_restore --list "/backups/$DumpFile" | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "pg_restore --list failed; dump may be corrupt."
    }

    $BackupInfo = Get-Item -LiteralPath (Join-Path $OutputDir $DumpFile)
    Write-Host "Backup complete: $($BackupInfo.FullName) ($([math]::Round($BackupInfo.Length / 1MB, 1)) MB)"
}
finally {
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
    Stop-Process -Id $PortForward.Id -ErrorAction SilentlyContinue
}
