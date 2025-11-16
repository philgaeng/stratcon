# Verify WSL2 Port Forwarding State
# This script checks if manual port forwarding rules have been removed

Write-Host "=== Checking Port Proxy Rules ===" -ForegroundColor Cyan
$portProxy = netsh interface portproxy show all
if ([string]::IsNullOrWhiteSpace($portProxy) -or $portProxy -match "Listen on ipv4:\s+Connect to ipv4:\s+Address\s+Port\s+Address\s+Port\s+-+\s+-+") {
    Write-Host "✓ No port proxy rules found (expected - WSL2 uses automatic forwarding)" -ForegroundColor Green
} else {
    Write-Host "Port proxy rules found:" -ForegroundColor Yellow
    netsh interface portproxy show all
}

Write-Host ""
Write-Host "=== Checking Windows Firewall Rules ===" -ForegroundColor Cyan
$firewallRules = Get-NetFirewallRule -DisplayName "Allow Frontend Port 3000","Allow Backend Port 8000" -ErrorAction SilentlyContinue

if ($null -eq $firewallRules -or $firewallRules.Count -eq 0) {
    Write-Host "✓ Custom firewall rules removed (expected)" -ForegroundColor Green
} else {
    Write-Host "Custom firewall rules still exist:" -ForegroundColor Yellow
    $firewallRules | Format-Table DisplayName, Enabled, Direction, Action -AutoSize
}

Write-Host ""
Write-Host "=== Testing WSL2 Connection ===" -ForegroundColor Cyan
$wslIp = (wsl hostname -I).Trim()
if ($wslIp) {
    Write-Host "WSL2 IP Address: $wslIp" -ForegroundColor Green
    Write-Host ""
    Write-Host "You can test connectivity by:" -ForegroundColor Yellow
    Write-Host "  1. From Windows, open: http://localhost:3000 (should work automatically)" -ForegroundColor Cyan
    Write-Host "  2. From WSL, check if services are running:" -ForegroundColor Cyan
    Write-Host "     - Backend:  curl http://localhost:8000" -ForegroundColor Gray
    Write-Host "     - Frontend: curl http://localhost:3000" -ForegroundColor Gray
} else {
    Write-Host "⚠ Could not get WSL2 IP address. Is WSL running?" -ForegroundColor Yellow
}

