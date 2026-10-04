param (
    [string]$RequirementsPath = "tracker/requirements.txt",
    [string]$OutputJson = "tracker/sca_audit_latest.json"
)

$VenvPython = Join-Path $PSScriptRoot "..\backend\venv\Scripts\python.exe"
$VenvPipAudit = Join-Path $PSScriptRoot "..\backend\venv\Scripts\pip-audit.exe"

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " [SCA SECURITY AUDIT] Software Supply Chain Security Check" -ForegroundColor Cyan
Write-Host " Tool: pip-audit v2.10.1 (OSV / PyPI Advisory DB)" -ForegroundColor Cyan
Write-Host " Requirements file: $RequirementsPath" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

if (-not (Test-Path $VenvPipAudit)) {
    Write-Host "[INFO] pip-audit not found in venv. Installing..." -ForegroundColor Yellow
    & $VenvPython -m pip install pip-audit
}

if (-not (Test-Path $RequirementsPath)) {
    Write-Host "[ERROR] Requirements file '$RequirementsPath' not found!" -ForegroundColor Red
    exit 1
}

Write-Host "`n[RUNNING] Executing pip-audit scan..." -ForegroundColor Green
& $VenvPipAudit -r $RequirementsPath
$AuditExitCode = $LASTEXITCODE

Write-Host "[INFO] Saving machine-readable JSON report to $OutputJson..." -ForegroundColor Gray
& $VenvPipAudit -r $RequirementsPath --format json | Out-File -FilePath $OutputJson -Encoding utf8

if ($AuditExitCode -eq 0) {
    Write-Host "`n[PASS] All third-party dependencies are secure. 0 vulnerabilities found!" -ForegroundColor Green
} else {
    Write-Host "`n[FAIL] Known vulnerabilities detected in dependencies! CVE triage required." -ForegroundColor Red
}

exit $AuditExitCode