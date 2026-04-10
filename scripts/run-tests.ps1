param(
  [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

function Get-BrowserPath {
  $candidates = @(
    "C:\Program Files\Google\Chrome\Application\chrome.exe",
    "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
  )

  foreach ($candidate in $candidates) {
    if (Test-Path $candidate) {
      return $candidate
    }
  }

  throw "Could not find Chrome or Edge. Install one of them to run the browser tests."
}

function Get-PythonCommand {
  foreach ($candidate in @("python", "py")) {
    try {
      & $candidate --version *> $null
      if ($LASTEXITCODE -eq 0) {
        return $candidate
      }
    } catch {
    }
  }

  throw "Could not find Python in PATH."
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$browserPath = Get-BrowserPath
$pythonCommand = Get-PythonCommand
$profileDir = Join-Path $repoRoot ".tmp-browser-profile"
$testUrl = "http://localhost:$Port/tests/"

if (!(Test-Path $profileDir)) {
  New-Item -ItemType Directory -Path $profileDir | Out-Null
}

Write-Host ""
Write-Host "Running Python tests..." -ForegroundColor Cyan
$previousErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
$pythonOutput = & $pythonCommand "$repoRoot\\scripts\\run-python-tests.py" 2>&1 | Out-String
$pythonExitCode = $LASTEXITCODE
$ErrorActionPreference = $previousErrorActionPreference
Write-Host $pythonOutput.Trim()
if ($pythonExitCode -ne 0) {
  throw "Python tests failed."
}

$serverJob = Start-Job -ScriptBlock {
  param($root, $pythonExe, $portNumber)
  Set-Location $root
  & $pythonExe -m http.server $portNumber
} -ArgumentList $repoRoot, $pythonCommand, $Port

try {
  Start-Sleep -Seconds 2

  $previousErrorActionPreference = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  $rawOutput = & $browserPath `
    --headless `
    --disable-gpu `
    --no-first-run `
    --user-data-dir="$profileDir" `
    --virtual-time-budget=5000 `
    --dump-dom `
    $testUrl 2>&1 | Out-String
  $browserExitCode = $LASTEXITCODE
  $ErrorActionPreference = $previousErrorActionPreference

  if ($browserExitCode -ne 0) {
    throw "Headless browser run failed. Output: $rawOutput"
  }

  $summaryMatch = [regex]::Match($rawOutput, '<p id="summary" class="summary">(?<summary>.*?)</p>')
  if (!$summaryMatch.Success) {
    throw "Could not find the test summary in the rendered page. Output: $rawOutput"
  }

  Write-Host ""
  Write-Host "Snake test summary" -ForegroundColor Cyan
  Write-Host $summaryMatch.Groups["summary"].Value
  Write-Host ""

  $resultMatches = [regex]::Matches($rawOutput, '<strong>(?<label>PASS|FAIL): (?<name>.*?)</strong>')
  foreach ($match in $resultMatches) {
    $label = $match.Groups["label"].Value
    $name = $match.Groups["name"].Value
    $color = if ($label -eq "PASS") { "Green" } else { "Red" }
    Write-Host ("[{0}] {1}" -f $label, $name) -ForegroundColor $color
  }

  if ($summaryMatch.Groups["summary"].Value -match '(\d+) failed') {
    throw "One or more tests failed."
  }
} finally {
  Stop-Job $serverJob -ErrorAction SilentlyContinue | Out-Null
  Remove-Job $serverJob -ErrorAction SilentlyContinue | Out-Null
}
