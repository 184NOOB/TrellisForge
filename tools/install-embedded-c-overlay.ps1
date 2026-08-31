[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-z0-9]+(?:-[a-z0-9]+)*$')]
    [string]$ProjectPrefix,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('.+')]
    [string]$ProjectName,

    [Parameter(Mandatory = $true)]
    [string]$TargetRoot,

    [switch]$Force
)

$ErrorActionPreference = 'Stop'

$sourceRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\templates\embedded-c-overlay'))
$targetRootFull = [System.IO.Path]::GetFullPath($TargetRoot)

if (-not (Test-Path -LiteralPath $sourceRoot -PathType Container)) {
    throw "模板目录不存在: $sourceRoot"
}

if (-not (Test-Path -LiteralPath $targetRootFull -PathType Container)) {
    throw "目标目录不存在: $targetRootFull"
}

 $gitPath = Join-Path $targetRootFull '.git'
if (-not (Test-Path -LiteralPath $gitPath -PathType Container) -and
    -not (Test-Path -LiteralPath $gitPath -PathType Leaf)) {
    throw "目标不是 Git 仓库根目录: $targetRootFull"
}

$resolvedRoot = (& git -C $targetRootFull rev-parse --show-toplevel 2>$null)
if ($LASTEXITCODE -ne 0 -or [System.IO.Path]::GetFullPath($resolvedRoot.Trim()) -ne $targetRootFull.TrimEnd('\')) {
    throw "目标目录不是 Git 工作树根目录: $targetRootFull"
}

if (-not (Test-Path -LiteralPath (Join-Path $targetRootFull '.trellis') -PathType Container)) {
    throw "请先在目标仓库运行 trellis init: $targetRootFull"
}

$cacheFiles = @(Get-ChildItem -LiteralPath $sourceRoot -Recurse -File |
    Where-Object { $_.FullName -match '[\\/]__pycache__[\\/]' -or $_.Extension -in '.pyc', '.pyo' })
if ($cacheFiles.Count -gt 0) {
    throw "模板目录包含 Python 缓存，拒绝安装。请先清理: $($cacheFiles[0].FullName)"
}

$sourceFiles = @(Get-ChildItem -LiteralPath $sourceRoot -Recurse -File |
    Where-Object { $_.FullName -notmatch '[\\/]__pycache__[\\/]' -and $_.Extension -notin '.pyc', '.pyo' })
$conflicts = @()
foreach ($sourceFile in $sourceFiles) {
    $relative = $sourceFile.FullName.Substring($sourceRoot.Length).TrimStart('\', '/')
    if ($relative -eq 'AGENTS.md.template') {
        continue
    }
    $relative = $relative.Replace('__PROJECT_PREFIX__', $ProjectPrefix)
    $destination = Join-Path $targetRootFull $relative
    if (Test-Path -LiteralPath $destination) {
        $conflicts += $destination
    }
}

$agentsDestination = Join-Path $targetRootFull 'AGENTS.md.trellisforge-template'
if (Test-Path -LiteralPath $agentsDestination) {
    $conflicts += $agentsDestination
}

if ($conflicts.Count -gt 0 -and -not $Force) {
    $preview = $conflicts | Select-Object -First 10 | ForEach-Object { "  $_" }
    throw ("发现 $($conflicts.Count) 个将被覆盖的文件。请先审查差异；确认后使用 -Force。`n" + ($preview -join "`n"))
}

$backupRoot = $null
if ($Force) {
    $overwrittenFiles = @($sourceFiles | ForEach-Object {
        $relative = $_.FullName.Substring($sourceRoot.Length).TrimStart('\', '/')
        if ($relative -eq 'AGENTS.md.template') {
            return
        }
        $relative = $relative.Replace('__PROJECT_PREFIX__', $ProjectPrefix)
        $destination = Join-Path $targetRootFull $relative
        if (Test-Path -LiteralPath $destination -PathType Leaf) {
            [PSCustomObject]@{ Source = $destination; Relative = $relative }
        }
    })
    if (Test-Path -LiteralPath $agentsDestination -PathType Leaf) {
        $overwrittenFiles += [PSCustomObject]@{
            Source = $agentsDestination
            Relative = 'AGENTS.md.trellisforge-template'
        }
    }

    if ($overwrittenFiles.Count -gt 0) {
        $backupRoot = Join-Path $targetRootFull ('.trellisforge-backup\' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
        $backupEntries = @()
        foreach ($file in $overwrittenFiles) {
            $backup = Join-Path $backupRoot $file.Relative
            New-Item -ItemType Directory -Path (Split-Path -Parent $backup) -Force | Out-Null
            Copy-Item -LiteralPath $file.Source -Destination $backup
            $backupEntries += [ordered]@{
                path = $file.Relative.Replace('\', '/')
                sha256 = (Get-FileHash -LiteralPath $file.Source -Algorithm SHA256).Hash.ToLowerInvariant()
            }
        }
        $backupManifest = [ordered]@{
            schema_version = 1
            created_at = (Get-Date).ToString('o')
            files = $backupEntries
        }
        $manifestPath = Join-Path $backupRoot 'backup-manifest.json'
        [System.IO.File]::WriteAllText(
            $manifestPath,
            ($backupManifest | ConvertTo-Json -Depth 3),
            [System.Text.UTF8Encoding]::new($false)
        )
    }
}

foreach ($sourceFile in $sourceFiles) {
    $relative = $sourceFile.FullName.Substring($sourceRoot.Length).TrimStart('\', '/')
    if ($relative -eq 'AGENTS.md.template') {
        continue
    }
    $relative = $relative.Replace('__PROJECT_PREFIX__', $ProjectPrefix)
    $destination = Join-Path $targetRootFull $relative
    $destinationParent = Split-Path -Parent $destination
    New-Item -ItemType Directory -Path $destinationParent -Force | Out-Null

    $content = [System.IO.File]::ReadAllText($sourceFile.FullName, [System.Text.UTF8Encoding]::new($false))
    $content = $content.Replace('PROJECT_PREFIX', $ProjectPrefix)
    $content = $content.Replace('PROJECT_NAME', $ProjectName)
    [System.IO.File]::WriteAllText($destination, $content, [System.Text.UTF8Encoding]::new($false))
}

$agentsTemplate = Join-Path $sourceRoot 'AGENTS.md.template'
$agentsContent = [System.IO.File]::ReadAllText($agentsTemplate, [System.Text.UTF8Encoding]::new($false))
$agentsContent = $agentsContent.Replace('PROJECT_PREFIX', $ProjectPrefix).Replace('PROJECT_NAME', $ProjectName)
[System.IO.File]::WriteAllText($agentsDestination, $agentsContent, [System.Text.UTF8Encoding]::new($false))

Write-Host 'TrellisForge 覆盖层已安装。'
if ($backupRoot) {
    Write-Host "所有将被模板覆盖的既有文件已备份到: $backupRoot"
    Write-Host "备份清单: $(Join-Path $backupRoot 'backup-manifest.json')"
}
Write-Host "请将 $agentsDestination 的项目规则合并到 AGENTS.md，并填写所有 <...> 占位符。"
Write-Host '然后运行 docs/接入指南.md 中的脚本与 Hook 验证命令。'
