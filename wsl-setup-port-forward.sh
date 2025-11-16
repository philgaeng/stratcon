#!/bin/bash
# WSL2 Port Forwarding Setup Script
# This script sets up port forwarding from Windows localhost to WSL2
# Add this to your WSL profile to run automatically on WSL startup

# Get WSL2 IP address
WSL_IP=$(hostname -I | awk '{print $1}')

if [ -z "$WSL_IP" ]; then
    echo "Failed to get WSL2 IP address"
    exit 1
fi

# Get Windows host IP (for accessing Windows from WSL)
WIN_IP=$(ip route | grep default | awk '{print $3}')

# Remove existing port proxy rules
netsh.exe interface portproxy delete v4tov4 listenaddress=127.0.0.1 listenport=3000 > /dev/null 2>&1
netsh.exe interface portproxy delete v4tov4 listenaddress=127.0.0.1 listenport=8000 > /dev/null 2>&1

# Add port forwarding rules (run via Windows PowerShell)
powershell.exe -Command "
    netsh interface portproxy add v4tov4 listenaddress=127.0.0.1 listenport=3000 connectaddress=$WSL_IP connectport=3000 2>&1 | Out-Null;
    netsh interface portproxy add v4tov4 listenaddress=127.0.0.1 listenport=8000 connectaddress=$WSL_IP connectport=8000 2>&1 | Out-Null;
    if (\$LASTEXITCODE -eq 0) {
        Write-Host 'Port forwarding configured: localhost:3000 -> $WSL_IP:3000, localhost:8000 -> $WSL_IP:8000' -ForegroundColor Green
    } else {
        Write-Host 'Port forwarding requires Administrator privileges. Run the wsl-port-forward.ps1 script manually.' -ForegroundColor Yellow
    }
"

