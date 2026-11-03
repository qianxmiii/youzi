param([switch]$CreateShortcut, [switch]$SkipInstall)
$ErrorActionPreference = 'Stop'
$widgetDirectory = $PSScriptRoot
$frontendDirectory = Join-Path (Split-Path $widgetDirectory -Parent) 'frontend'
$runtimePython = Join-Path $widgetDirectory '.venv\Scripts\python.exe'
if (-not $SkipInstall) {
if (-not (Test-Path -LiteralPath $runtimePython)) {
    python -m venv (Join-Path $widgetDirectory '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Python环境创建失败，请先安装Python。' }
}
& $runtimePython -m pip install -r (Join-Path $widgetDirectory 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw '桌面依赖安装失败，请检查网络后重试。' }
Push-Location $frontendDirectory
try {
    if (-not (Test-Path -LiteralPath 'node_modules\vite\bin\vite.js')) {
        npm ci
        if ($LASTEXITCODE -ne 0) { throw '前端依赖安装失败。' }
    }
    npm run build:quote-widget
    if ($LASTEXITCODE -ne 0) { throw '小窗构建失败。' }
} finally { Pop-Location }
}
if ($CreateShortcut) {
    $desktopDirectory = [Environment]::GetFolderPath('Desktop')
    $shortcutPath = Join-Path $desktopDirectory '柚子报价小窗.lnk'
    if (-not (Test-Path -LiteralPath $runtimePython) -or -not (Test-Path -LiteralPath (Join-Path $widgetDirectory 'build\quote-widget.html'))) { throw '请先安装并构建小窗。' }
    $exists = Test-Path -LiteralPath $shortcutPath
    $shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut($shortcutPath)
    $expectedTarget = Join-Path $widgetDirectory '.venv\Scripts\pythonw.exe'
    $expectedArguments = '"' + (Join-Path $widgetDirectory 'launcher.py') + '"'
    if ($exists -and ($shortcut.TargetPath -ne $expectedTarget -or $shortcut.Arguments -ne $expectedArguments)) { throw '同名桌面快捷方式指向其他程序，未覆盖。' }
    $shortcut.TargetPath = $expectedTarget
    $shortcut.Arguments = '"' + (Join-Path $widgetDirectory 'launcher.py') + '"'
    $shortcut.WorkingDirectory = $widgetDirectory
    $shortcut.Description = '独立报价计算小窗，可置顶和选择显示字段'
    $shortcut.Save()
}
Write-Host '安装完成。以后双击“启动报价小窗.cmd”即可，不需要启动网页或后端。'
