$ErrorActionPreference = 'Stop'
$pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
if (-not $pythonCommand) {
    $pythonCommand = Get-Command py.exe -ErrorAction SilentlyContinue
}
if (-not $pythonCommand) {
    throw '未找到 Python。请安装 Python 3.9–3.12，并确保 python.exe 或 py.exe 在 PATH 中。'
}
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $root

$client = New-Object System.Net.Sockets.TcpClient
$connect = $client.BeginConnect('127.0.0.1', 8877, $null, $null)
$portOpen = $connect.AsyncWaitHandle.WaitOne(300)
if ($portOpen) {
    try {
        $client.EndConnect($connect)
    } catch {
        $portOpen = $false
    }
}
$client.Close()

if ($portOpen) {
    $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8877/health' -TimeoutSec 2
    if ($health.service -eq 'roi-web') {
        Start-Process 'http://127.0.0.1:8877'
        return
    }
    throw '端口 8877 已被其他程序占用。'
}

& $pythonCommand.Source -m roi_web --host 127.0.0.1 --port 8877
