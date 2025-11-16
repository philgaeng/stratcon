# WSL2 Port Forwarding Script
# This script forwards Windows localhost ports to WSL2 IP addresses
# 
# IMPORTANT: This script must be run as Administrator

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host ""
    Write-Host "To run as Administrator:" -ForegroundColor Yellow
    Write-Host "1. Right-click PowerShell in Start Menu" -ForegroundColor Yellow
    Write-Host "2. Select 'Run as Administrator'" -ForegroundColor Yellow
    Write-Host "3. Navigate to the project directory and run this script" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Or run this command to restart PowerShell as admin:" -ForegroundColor Cyan
    Write-Host 'Start-Process powershell -Verb RunAs -ArgumentList "-NoExit", "-Command", "cd ''\\wsl.localhost\Ubuntu\home\philg\projects\stratcon''; .\wsl-port-forward.ps1"' -ForegroundColor Gray
    exit 1
}

# Get WSL2 IP address dynamically
Write-Host "Getting WSL2 IP address..." -ForegroundColor Yellow
$wslIp = (wsl hostname -I).Trim()

if ([string]::IsNullOrWhiteSpace($wslIp)) {
    Write-Host "Failed to get WSL2 IP address. Is WSL running?" -ForegroundColor Red
    exit 1
}

Write-Host "WSL2 IP Address: $wslIp" -ForegroundColor Green
Write-Host ""

# Remove existing port proxy rules (ignore errors if they don't exist)
Write-Host "Removing existing port proxy rules..." -ForegroundColor Yellow
netsh interface portproxy delete v4tov4 listenaddress=127.0.0.1 listenport=3000 2>&1 | Out-Null
netsh interface portproxy delete v4tov4 listenaddress=127.0.0.1 listenport=8000 2>&1 | Out-Null
netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=3000 2>&1 | Out-Null
netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=8000 2>&1 | Out-Null

# Add new port proxy rules forwarding Windows localhost to WSL2 IP
Write-Host "Setting up port forwarding from localhost to WSL2..." -ForegroundColor Yellow
try {
    netsh interface portproxy add v4tov4 listenaddress=127.0.0.1 listenport=3000 connectaddress=$wslIp connectport=3000 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to add port proxy for port 3000"
    }
    
    netsh interface portproxy add v4tov4 listenaddress=127.0.0.1 listenport=8000 connectaddress=$wslIp connectport=8000 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to add port proxy for port 8000"
    }
    
    Write-Host ""
    Write-Host "Port forwarding configured successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Current port proxy rules:" -ForegroundColor Cyan
    netsh interface portproxy show all
    Write-Host ""
    Write-Host "You can now access from Windows:" -ForegroundColor Green
    Write-Host "  Frontend: http://localhost:3000" -ForegroundColor Cyan
    Write-Host "  Backend:  http://localhost:8000" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Note: If WSL2 restarts and gets a new IP, run this script again." -ForegroundColor Yellow
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
    exit 1
}
