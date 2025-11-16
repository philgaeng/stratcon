# Remove WSL2 Port Forwarding Configuration
# This script removes the Windows Firewall rules and port proxy rules
# that were added manually. WSL2 has built-in port forwarding that should work automatically.

Write-Host "Removing Windows Firewall rules..." -ForegroundColor Yellow

# Remove firewall rules
Remove-NetFirewallRule -DisplayName "Allow Frontend Port 3000" -ErrorAction SilentlyContinue
Remove-NetFirewallRule -DisplayName "Allow Backend Port 8000" -ErrorAction SilentlyContinue

Write-Host "Removing port proxy rules..." -ForegroundColor Yellow

# Remove port proxy rules
netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=3000 2>&1 | Out-Null
netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=8000 2>&1 | Out-Null

Write-Host ""
Write-Host "Configuration removed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "WSL2's built-in port forwarding should now handle the connections automatically." -ForegroundColor Cyan
Write-Host ""
Write-Host "Verifying removal..." -ForegroundColor Yellow
netsh interface portproxy show all

