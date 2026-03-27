$ErrorActionPreference = "Stop"

function Find-PythonExe {
  $cmdPython = Get-Command python -ErrorAction SilentlyContinue
  if ($cmdPython) { return $cmdPython.Source }

  $cmdPy = Get-Command py -ErrorAction SilentlyContinue
  if ($cmdPy) { return "$($cmdPy.Source) -3" }

  $candidates = @(
    "C:\Program Files\WindowsApps\PythonSoftwareFoundation.PythonManager_26.0.240.0_x64__3847v3x7pw1km\python.exe",
    "C:\Users\26265\AppData\Local\Python\pythoncore-3.14-64\python.exe",
    "C:\Users\26265\AppData\Local\Programs\Python\Python313\python.exe",
    "C:\Users\26265\AppData\Local\Programs\Python\Python312\python.exe",
    "C:\Users\26265\AppData\Local\Programs\Python\Python311\python.exe"
  )
  foreach ($p in $candidates) {
    if (Test-Path $p) { return $p }
  }
  return $null
}

function Invoke-Python {
  param(
    [string]$PythonExe,
    [string[]]$Args
  )

  if ($PythonExe -like "*py.exe -3") {
    $parts = $PythonExe.Split(" ")
    & $parts[0] $parts[1] @Args
  } else {
    & $PythonExe @Args
  }
}

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$pythonExe = Find-PythonExe
if (-not $pythonExe) {
  Write-Host "[ERROR] Python not found. Please install Python and reopen terminal."
  exit 1
}

Write-Host "[INFO] Using Python: $pythonExe"
Invoke-Python -PythonExe $pythonExe -Args @("--version")

Write-Host "[STEP] Build kb_master from source registry"
Invoke-Python -PythonExe $pythonExe -Args @(
  "scripts\kb_merge_bootstrap.py",
  "--registry", "data\kb\source_registry.json",
  "--out", "data\kb\kb_master.jsonl",
  "--root", $repoRoot
)

if (-not (Test-Path "data\kb\kb_master.jsonl")) {
  Write-Host "[ERROR] kb_master.jsonl was not generated."
  exit 1
}

$lineCount = (Get-Content "data\kb\kb_master.jsonl").Count
Write-Host "[INFO] kb_master rows: $lineCount"
if ($lineCount -lt 1) {
  Write-Host "[ERROR] kb_master is empty."
  exit 1
}

Write-Host "[STEP] Run search_kb smoke query"
$context = '{"platform":"okx"}'
Invoke-Python -PythonExe $pythonExe -Args @(
  "scripts\p0_tools.py",
  "search_kb",
  "--query", "deposit not credited",
  "--context", $context
)

Write-Host "[STEP] Run 20-query retrieval smoke"
Invoke-Python -PythonExe $pythonExe -Args @(
  "scripts\smoke_kb_queries_20.py"
)

Write-Host "[DONE] KB build pipeline completed."
