param(
    [string]$AppHost = "127.0.0.1",
    [int]$AppPort = 8000,
    [string]$McpHost = "127.0.0.1",
    [int]$McpPort = 8001,
    [string]$McpTransport = "streamable-http"
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
$mcpProcess = $null
$previousTransport = $null
$previousHost = $null
$previousPort = $null

Push-Location $backendDir
try {
    & $pythonCommand -c "import uvicorn; import mcp.server.fastmcp; import mcp_sqlite.server" *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Required packages or local backend modules are not available for $pythonCommand. Install them with: $pythonCommand -m pip install -r requirements.txt"
    }

    $previousTransport = $env:MCP_TRANSPORT
    $previousHost = $env:MCP_HOST
    $previousPort = $env:MCP_PORT

    $env:MCP_TRANSPORT = $McpTransport
    $env:MCP_HOST = $McpHost
    $env:MCP_PORT = "$McpPort"

    $appProcess = Start-Process -FilePath $pythonCommand -ArgumentList @("-m", "uvicorn", "app.main:app", "--reload", "--host", $AppHost, "--port", "$AppPort") -WorkingDirectory $backendDir -NoNewWindow -PassThru
    $mcpProcess = Start-Process -FilePath $pythonCommand -ArgumentList @("-m", "mcp_sqlite.server") -WorkingDirectory $backendDir -NoNewWindow -PassThru

    Write-Host "FastAPI app: http://$AppHost`:$AppPort"
    if ($McpTransport -eq "streamable-http") {
        Write-Host "MCP server:   http://$McpHost`:$McpPort/mcp ($McpTransport)"
    }
    else {
        Write-Host "MCP server:   http://$McpHost`:$McpPort ($McpTransport)"
    }
    Write-Host "Press Ctrl-C to stop both services."

    while (-not $appProcess.HasExited -and -not $mcpProcess.HasExited) {
        Start-Sleep -Seconds 1
        $appProcess.Refresh()
        $mcpProcess.Refresh()
    }

    $appProcess.Refresh()
    $mcpProcess.Refresh()

    if ($appProcess.HasExited -and -not $mcpProcess.HasExited) {
        throw "FastAPI app exited unexpectedly."
    }

    if ($mcpProcess.HasExited -and -not $appProcess.HasExited) {
        throw "MCP server exited unexpectedly."
    }

    if ($appProcess.ExitCode -ne 0) {
        throw "FastAPI app stopped with exit code $($appProcess.ExitCode)."
    }

    if ($mcpProcess.ExitCode -ne 0) {
        throw "MCP server stopped with exit code $($mcpProcess.ExitCode)."
    }
}
finally {
    foreach ($process in @($appProcess, $mcpProcess)) {
        if ($null -ne $process -and -not $process.HasExited) {
            Stop-Process -Id $process.Id -ErrorAction SilentlyContinue
            $process.WaitForExit()
        }
    }

    if ($null -ne $previousTransport) {
        $env:MCP_TRANSPORT = $previousTransport
    }
    else {
        Remove-Item Env:MCP_TRANSPORT -ErrorAction SilentlyContinue
    }

    if ($null -ne $previousHost) {
        $env:MCP_HOST = $previousHost
    }
    else {
        Remove-Item Env:MCP_HOST -ErrorAction SilentlyContinue
    }

    if ($null -ne $previousPort) {
        $env:MCP_PORT = $previousPort
    }
    else {
        Remove-Item Env:MCP_PORT -ErrorAction SilentlyContinue
    }

    Pop-Location
}
