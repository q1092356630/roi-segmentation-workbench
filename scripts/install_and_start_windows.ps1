$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root
$venv = Join-Path $root '.venv'
$venvPython = Join-Path $venv 'Scripts\python.exe'
$venvPythonw = Join-Path $venv 'Scripts\pythonw.exe'

function Invoke-SystemPython {
    $pyLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        & $pyLauncher.Source -3 @args
        return
    }
    $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        & $pythonCommand.Source @args
        return
    }
    throw '未找到 Python 3。请先安装 Python 3.9–3.12，并确保 py.exe 或 python.exe 在 PATH 中。'
}

if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Host '正在创建项目专用 Python 环境…'
    Invoke-SystemPython -m venv $venv
}

if (-not (Test-Path -LiteralPath $venvPython)) {
    throw "虚拟环境创建失败：$venvPython"
}

Write-Host '正在安装或更新 Python 依赖…'
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r (Join-Path $root 'requirements-roi-workbench.txt')

$configPath = Join-Path $root 'config\model_paths.json'
$exampleConfigPath = Join-Path $root 'config\model_paths.example.json'
if (-not (Test-Path -LiteralPath $configPath)) {
    Copy-Item -LiteralPath $exampleConfigPath -Destination $configPath
    Write-Host '已创建 config\model_paths.json；如需半自动推理，请把其中路径改成目标电脑的 WSL/Python/模型路径。'
}

if (-not (Test-Path -LiteralPath $venvPythonw)) {
    $venvPythonw = $venvPython
}
Write-Host '正在启动 ROI 工作台…'
Start-Process -FilePath $venvPythonw -ArgumentList @((Join-Path $root 'run_roi_web.pyw')) -WorkingDirectory $root -WindowStyle Hidden
Write-Host '启动请求已发送，浏览器将打开 http://127.0.0.1:8877。'
