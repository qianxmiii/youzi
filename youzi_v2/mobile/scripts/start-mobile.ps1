param(
    [switch]$Check,
    [ValidateRange(1024, 65535)]
    [int]$Port = 3002,
    [string]$Python = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
if (-not $Python) {
    $venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $venvPython) { $Python = $venvPython }
    else { $Python = "python" }
}
$env:PYTHONIOENCODING = "utf-8"
$mobileArgs = @("-m", "youzi_v2.mobile.backend", "--port", "$Port")
if ($Check) { $mobileArgs += "--check" }
Push-Location -LiteralPath $repoRoot
try {
    & $Python @mobileArgs
    $mobileExitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}
exit $mobileExitCode
