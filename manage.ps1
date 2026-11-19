param(
    [ValidateSet('Install','Uninstall')][string]$Action = 'Install',
    [string]$DocumentsRoot = [Environment]::GetFolderPath('MyDocuments'),
    [string]$InstallRoot = (Join-Path $env:LOCALAPPDATA 'HoudiniResourceMonitor')
)
$ErrorActionPreference = 'Stop'
$release = 'v005'
$statePath = Join-Path $InstallRoot 'install-state.json'
$packageName = 'houdini_resource_monitor.json'

function Write-Utf8Json($Path, $Data) {
    $content = ConvertTo-Json -InputObject $Data -Depth 10
    [IO.File]::WriteAllText($Path, $content, (New-Object Text.UTF8Encoding($false)))
}

try {
    if ($Action -eq 'Uninstall') {
        if (-not (Test-Path -LiteralPath $statePath)) {
            Write-Host '没有找到由此便携包安装的记录。'
            exit 0
        }
        $state = Get-Content -LiteralPath $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
        foreach ($entry in $state.entries) {
            if (-not (Test-Path -LiteralPath $entry.path)) { continue }
            $current = Get-Content -LiteralPath $entry.path -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($current.path -ne $state.activePath) {
                Write-Host ('配置已被其他程序更改，保留：' + $entry.path)
                continue
            }
            if ($entry.existed) {
                [IO.File]::WriteAllBytes($entry.path, [Convert]::FromBase64String($entry.original))
                Write-Host ('已恢复安装前配置：' + $entry.path)
            } else {
                Remove-Item -LiteralPath $entry.path
                Write-Host ('已移除启动配置：' + $entry.path)
            }
        }
        # 保留插件文件与安装记录，以便重复卸载或重新安装，不删除用户目录。
        Write-Host '卸载完成。正在运行的 Houdini 需要重启才生效。'
        exit 0
    }

    $payload = Join-Path $PSScriptRoot 'plugin'
    if (-not (Test-Path -LiteralPath (Join-Path $payload 'python3.11libs\hrm\ui.py'))) {
        throw '缺少插件文件。请先完整解压 ZIP，不能只复制安装脚本。'
    }
    $manifestPath = Join-Path $PSScriptRoot 'manifest.json'
    $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($file in $manifest.files) {
        $sourceFile = Join-Path $PSScriptRoot $file.path
        $hasher = [Security.Cryptography.SHA256]::Create()
        try {
            $hash = [BitConverter]::ToString($hasher.ComputeHash([IO.File]::ReadAllBytes($sourceFile))).Replace('-','')
        } finally { $hasher.Dispose() }
        if ($hash -ne $file.sha256) { throw ('文件校验失败，请重新解压：' + $file.path) }
    }
    $destination = Join-Path $InstallRoot "$release\plugin"
    New-Item -ItemType Directory -Force -Path $destination | Out-Null
    Get-ChildItem -LiteralPath $payload | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $destination -Recurse -Force
    }
    foreach ($helper in @('manage.ps1','卸载.cmd','使用说明.txt')) {
        Copy-Item -LiteralPath (Join-Path $PSScriptRoot $helper) -Destination (Join-Path $InstallRoot $helper) -Force
    }
    $activePath = $destination.Replace('\','/')
    $entries = @()
    if (Test-Path -LiteralPath $statePath) {
        $old = Get-Content -LiteralPath $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
        $entries = @($old.entries)
    }
    $changes = @()
    try {
        foreach ($version in @('21.0','22.0')) {
            $packageDir = Join-Path $DocumentsRoot "houdini$version\packages"
            New-Item -ItemType Directory -Force -Path $packageDir | Out-Null
            $target = Join-Path $packageDir $packageName
            $existed = Test-Path -LiteralPath $target
            $original = ''
            if ($existed) { $original = [Convert]::ToBase64String([IO.File]::ReadAllBytes($target)) }
            $snapshot = [pscustomobject]@{ path=$target; existed=$existed; original=$original }
            $changes += $snapshot
            if (-not ($entries | Where-Object { $_.path -eq $target })) { $entries += $snapshot }
            Write-Utf8Json $target @{ path=$activePath }
            Write-Host ('已配置 Houdini ' + $version + '：' + $target)
        }
        Write-Utf8Json $statePath @{ release=$release; activePath=$activePath; entries=@($entries) }
    } catch {
        foreach ($change in $changes) {
            if ($change.existed) {
                [IO.File]::WriteAllBytes($change.path,[Convert]::FromBase64String($change.original))
            } elseif (Test-Path -LiteralPath $change.path) { Remove-Item -LiteralPath $change.path }
        }
        throw
    }
    Write-Host ''
    Write-Host ('安装成功。插件目录：' + $destination)
    Write-Host '可以删除解压包或拔出 U 盘，插件仍可使用。'
    Write-Host '请启动或重启 Houdini 21 / 22。无需管理员权限，无需另装 Python。'
    Write-Host 'GPU / VRAM 数据需要 NVIDIA 显卡和可用驱动；其他显卡仍可查看 CPU / RAM。'
    exit 0
} catch {
    Write-Host ('操作失败：' + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
