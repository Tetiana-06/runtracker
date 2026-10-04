<#
.SYNOPSIS
    Автоматизований скрипт виявлення секретів (Secret Scanner) у межах Лабораторної роботи №3.

.DESCRIPTION
    Скрипт перевіряє файли проєкту та підготовлені до коміту зміни (Git Staging Area)
    на наявність випадково залишених ключів API, приватних токенів, паролів або сертифікатів.
    Використовує Gitleaks v8.30.1.

.PARAMETER StagedOnly
    Якщо вказано - перевіряються лише зміни в staging area (захист перед комітом).
    Якщо не вказано - перевіряється весь репозиторій або робоча директорія.

.EXAMPLE
    .\scripts\scan_secrets.ps1 -StagedOnly
#>

param (
    [switch]$StagedOnly
)

$GitleaksBin = Join-Path $PSScriptRoot "..\backend\venv\Scripts\gitleaks.exe"

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " [SECRET SCANNER] Automated Secret Leak Detection" -ForegroundColor Cyan
Write-Host " Tool: Gitleaks v8.30.1" -ForegroundColor Cyan
Write-Host " Mode: $(if ($StagedOnly) { 'Staged Changes (Pre-commit guard)' } else { 'Repository History & Worktree' })" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

if (-not (Test-Path $GitleaksBin)) {
    Write-Host "[ERROR] Gitleaks binary not found at $GitleaksBin!" -ForegroundColor Red
    exit 1
}

if ($StagedOnly) {
    Write-Host "`n[*] Scanning staged changes..." -ForegroundColor Green
    & $GitleaksBin protect --staged --verbose
} else {
    Write-Host "`n[*] Scanning git repository history..." -ForegroundColor Green
    & $GitleaksBin git --verbose
}

$ScanExitCode = $LASTEXITCODE

if ($ScanExitCode -eq 0) {
    Write-Host "`n[+] PASS: Жодних секретів чи конфіденційних токенів не виявлено! Коміт дозволено." -ForegroundColor Green
} else {
    Write-Host "`n[-] FAIL: Виявлено конфіденційні дані або токен у коді! Операцію заблоковано." -ForegroundColor Red
    Write-Host "    Дія: Видаліть секрет, винесіть його в змінні оточення (.env) та очистіть Git index." -ForegroundColor Yellow
}

exit $ScanExitCode