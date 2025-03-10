<#
.SYNOPSIS
    Automates the prerequisite setup to disable Windows Defender components via registry modifications.
.DESCRIPTION
    This script performs two distinct steps:
      Step 1:
         - Verifies that Tamper Protection is disabled.
         - Disables Real-Time Protection by setting the corresponding registry key (mimicking the Group Policy setting).
         - Prompts for a reboot.
      Step 2:
         - Disables Microsoft Defender Antivirus by setting the appropriate registry key.
         - Prompts for a final reboot.
    Note: Tamper Protection must be manually disabled prior to running Step 1.
    Usage:
      - Run as Administrator.
      - Execute this script with -Step 1 (or default) for the first part.
      - After reboot, execute the script with -Step 2.
#>

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("1","2")]
    [string]$Step = "1"
)

# Ensure the script is running with administrative privileges.
if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Error "Script must be run as Administrator."
    exit
}

# Function to check if Tamper Protection is disabled.
function Check-TamperProtection {
    try {
        $tp = Get-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows Defender\Features" -Name TamperProtection -ErrorAction Stop
        if ($tp.TamperProtection -eq 0) {
            Write-Host "Tamper Protection is disabled."
            return $true
        }
        else {
            Write-Host "Tamper Protection is enabled. Please disable it manually via Windows Security before proceeding."
            return $false
        }
    }
    catch {
        Write-Host "Unable to read Tamper Protection status. Please verify manually."
        return $false
    }
}

switch ($Step) {
    "1" {
        Write-Host "Step 1: Disabling Real-Time Protection via Group Policy settings..."
        if (-not (Check-TamperProtection)) {
            Write-Host "Exiting script. Disable Tamper Protection manually and re-run this step."
            exit
        }
        $rtpPath = "HKLM:\Software\Policies\Microsoft\Windows Defender\Real-Time Protection"
        if (-not (Test-Path $rtpPath)) {
            New-Item -Path $rtpPath -Force | Out-Null
        }
        try {
            Set-ItemProperty -Path $rtpPath -Name "DisableRealtimeMonitoring" -Value 1 -Type DWord -ErrorAction Stop
            Write-Host "Real-Time Protection has been permanently disabled via Group Policy settings."
            Write-Host "Please reboot your machine before proceeding to Step 2."
        }
        catch {
            Write-Error "Failed to disable Real-Time Protection. Error details: $_"
        }
    }
    "2" {
        Write-Host "Step 2: Disabling Microsoft Defender Antivirus via Group Policy settings..."
        $mdPath = "HKLM:\Software\Policies\Microsoft\Windows Defender"
        if (-not (Test-Path $mdPath)) {
            New-Item -Path $mdPath -Force | Out-Null
        }
        try {
            Set-ItemProperty -Path $mdPath -Name "DisableAntiSpyware" -Value 1 -Type DWord -ErrorAction Stop
            Write-Host "Microsoft Defender Antivirus has been permanently disabled via Group Policy settings."
            Write-Host "Please reboot your machine to finalize changes."
        }
        catch {
            Write-Error "Failed to disable Microsoft Defender Antivirus. Error details: $_"
        }
    }
}
