param(
    [string]$AppHost = "127.0.0.1",
    [int]$AppPort = 8000
)

$ErrorActionPreference = "Stop"

$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $rootDir "backend"

function Find-PythonCommand {
    $candidates = @(
        (Join-Path $rootDir ".venv\Scripts\python.exe"),
        (Join-Path $backendDir ".venv\Scripts\python.exe"),
        (Join-Path $rootDir ".venv\bin\python"),
        (Join-Path $backendDir ".venv\bin\python")
    )

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    foreach ($commandName in @("py", "python", "python3")) {
        $command = Get-Command $commandName -ErrorAction SilentlyContinue
        if ($null -ne $command) {
            return $command.Source
        }
    }

    throw "Python was not found. Install Python and the project requirements first."
}

$pythonCommand = Find-PythonCommand
$appProcess = $null

Push-Location $backendDir
try {
    & $pythonCommand -c "import uvicorn; import app.main" *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Required packages or local backend modules are not available for $pythonCommand. Install them with: $pythonCommand -m pip install -r requirements.txt"
    }

    $appProcess = Start-Process -FilePath $pythonCommand -ArgumentList @("-m", "uvicorn", "app.main:app", "--reload", "--host", $AppHost, "--port", "$AppPort") -WorkingDirectory $backendDir -NoNewWindow -PassThru

    Write-Host "FastAPI app: http://$AppHost`:$AppPort"
    Write-Host "Press Ctrl-C to stop the service."

    while (-not $appProcess.HasExited) {
        Start-Sleep -Seconds 1
        $appProcess.Refresh()
    }

    $appProcess.Refresh()

    if ($appProcess.ExitCode -ne 0) {
        throw "FastAPI app stopped with exit code $($appProcess.ExitCode)."
    }
}
finally {
    foreach ($process in @($appProcess)) {
        if ($null -ne $process -and -not $process.HasExited) {
            Stop-Process -Id $process.Id -ErrorAction SilentlyContinue
            $process.WaitForExit()
        }
    }

    Pop-Location
}
