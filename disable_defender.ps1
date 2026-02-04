<#
.SYNOPSIS
    Prepares a Windows host for Commando VM by disabling Windows Defender
    components via Group Policy registry keys.
.DESCRIPTION
    This script performs two distinct steps (a reboot is required between them):

      Step 1:
         - Verifies that Tamper Protection is disabled (must be done manually first).
         - Disables Real-Time Protection via the Group Policy registry path.
         - Prompts for a reboot.

      Step 2:
         - Disables Microsoft Defender Antivirus via Group Policy registry path.
         - Verifies the final state of all components.
         - Prompts for a final reboot.

    IMPORTANT - Tamper Protection:
      Tamper Protection CANNOT be disabled programmatically. You must disable it
      manually BEFORE running Step 1:
        Windows Security > Virus & Threat Protection > Manage Settings
        > Toggle OFF "Tamper Protection"

    NOTE - DisableAntiSpyware:
      On Windows 10 2004+ and Windows 11, the DisableAntiSpyware registry key
      is ignored by Microsoft unless the machine is detected as a server or has
      no other AV installed. Step 2 sets it for compatibility, but it may have
      no effect on modern Windows desktop builds.

    Usage:
      1. Manually disable Tamper Protection (see above).
      2. Run as Administrator:  .\disable_defender.ps1 -Step 1
      3. Reboot the machine.
      4. Run as Administrator:  .\disable_defender.ps1 -Step 2
      5. Reboot the machine.
#>

param(
    [Parameter(Mandatory = $false)]
    [ValidateSet("1", "2")]
    [string]$Step = "1"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Colours for console output ──────────────────────────────────────────────
function Write-Success { param([string]$Message) Write-Host $Message -ForegroundColor Green  }
function Write-Warn    { param([string]$Message) Write-Host $Message -ForegroundColor Yellow }
function Write-Fail    { param([string]$Message) Write-Host $Message -ForegroundColor Red    }

# ── Admin check ─────────────────────────────────────────────────────────────
$principal = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "This script must be run as Administrator. Right-click PowerShell > Run as Administrator."
    exit 1
}

# ── OS build info (for the DisableAntiSpyware deprecation warning) ──────────
$osBuild = [System.Environment]::OSVersion.Version.Build

# ── Helper: Test Tamper Protection status ───────────────────────────────────
function Test-TamperProtection {
    try {
        $tp = Get-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows Defender\Features" `
                               -Name TamperProtection -ErrorAction Stop
        if ($tp.TamperProtection -eq 0) {
            Write-Success "[OK] Tamper Protection is disabled."
            return $true
        }
        else {
            Write-Fail "[BLOCKED] Tamper Protection is still enabled."
            Write-Warn @"
  You must disable it manually:
    Windows Security > Virus & Threat Protection > Manage Settings
    > Toggle OFF 'Tamper Protection'
"@
            return $false
        }
    }
    catch {
        Write-Fail "[ERROR] Unable to read Tamper Protection status: $_"
        Write-Warn "  Please verify manually in Windows Security settings."
        return $false
    }
}

# ── Helper: Set a DWORD registry value, creating the key if needed ──────────
function Set-RegistryDword {
    param(
        [string]$Path,
        [string]$Name,
        [int]$Value
    )
    if (-not (Test-Path $Path)) {
        New-Item -Path $Path -Force | Out-Null
    }
    Set-ItemProperty -Path $Path -Name $Name -Value $Value -Type DWord -ErrorAction Stop
}

# ── Helper: Read a registry DWORD, returning $null if missing ───────────────
function Get-RegistryDword {
    param(
        [string]$Path,
        [string]$Name
    )
    try {
        $prop = Get-ItemProperty -Path $Path -Name $Name -ErrorAction Stop
        return $prop.$Name
    }
    catch {
        return $null
    }
}

# ── Helper: Verify and report a registry value ─────────────────────────────
function Confirm-RegistryValue {
    param(
        [string]$Path,
        [string]$Name,
        [int]$Expected,
        [string]$Label
    )
    $actual = Get-RegistryDword -Path $Path -Name $Name
    if ($actual -eq $Expected) {
        Write-Success "  [OK] $Label = $actual"
    }
    else {
        Write-Fail "  [UNEXPECTED] $Label = $actual (expected $Expected)"
    }
}

# ── Main logic ──────────────────────────────────────────────────────────────
switch ($Step) {
    "1" {
        Write-Host "`n=== Step 1: Disable Real-Time Protection ===" -ForegroundColor Cyan

        if (-not (Test-TamperProtection)) {
            Write-Fail "`nAborting. Disable Tamper Protection manually, then re-run: .\disable_defender.ps1 -Step 1"
            exit 1
        }

        $rtpPath = "HKLM:\Software\Policies\Microsoft\Windows Defender\Real-Time Protection"
        try {
            Set-RegistryDword -Path $rtpPath -Name "DisableRealtimeMonitoring" -Value 1
            Write-Success "`n[OK] Real-Time Protection disabled via Group Policy registry key."
        }
        catch {
            Write-Fail "`n[FAILED] Could not set DisableRealtimeMonitoring: $_"
            exit 1
        }

        # Verify what was written
        Write-Host "`nVerification:" -ForegroundColor Cyan
        Confirm-RegistryValue -Path $rtpPath -Name "DisableRealtimeMonitoring" -Expected 1 `
                              -Label "DisableRealtimeMonitoring"

        Write-Warn "`nReboot required. After reboot, run: .\disable_defender.ps1 -Step 2"
    }
    "2" {
        Write-Host "`n=== Step 2: Disable Microsoft Defender Antivirus ===" -ForegroundColor Cyan

        $mdPath = "HKLM:\Software\Policies\Microsoft\Windows Defender"

        # Warn about the deprecation on modern Windows
        if ($osBuild -ge 19041) {
            Write-Warn "[NOTE] Windows build $osBuild detected (2004+)."
            Write-Warn "  The DisableAntiSpyware key is deprecated on modern Windows desktop builds."
            Write-Warn "  It will be set for compatibility, but may have no effect.`n"
        }

        try {
            Set-RegistryDword -Path $mdPath -Name "DisableAntiSpyware" -Value 1
            Write-Success "[OK] DisableAntiSpyware set via Group Policy registry key."
        }
        catch {
            Write-Fail "[FAILED] Could not set DisableAntiSpyware: $_"
            exit 1
        }

        # Final verification of all keys
        Write-Host "`nFinal verification of all Defender registry keys:" -ForegroundColor Cyan

        Confirm-RegistryValue -Path "HKLM:\SOFTWARE\Microsoft\Windows Defender\Features" `
                              -Name "TamperProtection" -Expected 0 `
                              -Label "TamperProtection"

        Confirm-RegistryValue -Path "HKLM:\Software\Policies\Microsoft\Windows Defender\Real-Time Protection" `
                              -Name "DisableRealtimeMonitoring" -Expected 1 `
                              -Label "DisableRealtimeMonitoring"

        Confirm-RegistryValue -Path $mdPath `
                              -Name "DisableAntiSpyware" -Expected 1 `
                              -Label "DisableAntiSpyware"

        Write-Warn "`nReboot required to finalize changes."
        Write-Host "After reboot, the host should be ready for Commando VM installation." -ForegroundColor Cyan
    }
}
