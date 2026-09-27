# One-command startup for storage infrastructure (Redis + TimescaleDB)

$ErrorActionPreference = "Stop"

Write-Host "Starting Redis and TimescaleDB using Docker Compose..."
docker compose up -d redis timescaledb

Write-Host "Waiting for services health checks..."
Start-Sleep -Seconds 5

Write-Host "Current status:"
docker compose ps

Write-Host "Done."
