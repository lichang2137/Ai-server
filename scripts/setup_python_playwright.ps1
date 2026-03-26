$ErrorActionPreference = "Stop"

function Find-Python {
  $candidates = @(
    (Get-Command python -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue),
    (Get-Command py -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue),
    "C:\Users\26265\AppData\Local\Programs\Python\Python313\python.exe",
    "C:\Users\26265\AppData\Local\Programs\Python\Python312\python.exe",
    "C:\Users\26265\AppData\Local\Programs\Python\Python311\python.exe",
    "C:\Python313\python.exe",
    "C:\Python312\python.exe",
    "C:\Python311\python.exe"
  ) | Where-Object { $_ -and (Test-Path $_) }

  if ($candidates.Count -gt 0) {
    return $candidates[0]
  }
  return $null
}

$pythonExe = Find-Python
if (-not $pythonExe) {
  Write-Host "[ERROR] Python executable not found."
  Write-Host "Please install Python 3.11+ and enable 'Add python.exe to PATH'."
  exit 1
}

Write-Host "[INFO] Using Python: $pythonExe"
& $pythonExe --version

Write-Host "[INFO] Upgrading pip"
& $pythonExe -m pip install --upgrade pip

Write-Host "[INFO] Installing Playwright"
& $pythonExe -m pip install playwright

Write-Host "[INFO] Installing Chromium browser for Playwright"
& $pythonExe -m playwright install chromium

Write-Host "[INFO] Validating Playwright import"
& $pythonExe -c "from playwright.sync_api import sync_playwright; print('playwright_ok')"

Write-Host "[INFO] Running ingestion help check"
& $pythonExe "C:\Users\26265\Documents\New project\Ai-server\scripts\kb_ingest_helpcenter_playwright.py" --help

Write-Host "[DONE] Python + Playwright initialization complete."
