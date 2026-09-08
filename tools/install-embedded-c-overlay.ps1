[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-z0-9]+(?:-[a-z0-9]+)*$', Options = 'None')]
    [string]$ProjectPrefix,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('.+')]
    [string]$ProjectName,

    [Parameter(Mandatory = $true)]
    [string]$TargetRoot,

    [switch]$Force
)

$ErrorActionPreference = 'Stop'

$modulePath = Join-Path $PSScriptRoot 'lib\TrellisForgeOverlay.psm1'
if (-not (Test-Path -LiteralPath $modulePath -PathType Leaf)) {
    throw "共享模块缺失: $modulePath"
}
Import-Module $modulePath -Force -ErrorAction Stop

Assert-OverlayProjectParams -ProjectPrefix $ProjectPrefix -ProjectName $ProjectName | Out-Null

$sourceRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\templates\embedded-c-overlay'))
if (-not (Test-Path -LiteralPath $sourceRoot -PathType Container)) {
    throw "模板目录不存在: $sourceRoot"
}

$targetRoot = Assert-OverlayTargetRoot -TargetRoot $TargetRoot

# 模板含 Python 缓存时拒绝继续
$cacheFiles = @(Get-OverlayTemplateCacheFiles -SourceRoot $sourceRoot)
if ($cacheFiles.Count -gt 0) {
    throw "模板目录包含 Python 缓存，拒绝安装。请先清理: $($cacheFiles[0].FullName)"
}

$sourceFiles = @(Get-ChildItem -LiteralPath $sourceRoot -Recurse -File |
    Where-Object {
        $_.FullName -notmatch '[\\/]__pycache__[\\/]' -and
        $_.Extension -notin '.pyc', '.pyo' -and
        $_.Name -notin 'AGENTS.md.template', 'TEMPLATE-CONTENTS.md'
    })

# 构造写入计划与收据文件条目（全部写操作在同一事务内完成）
$writes = @()
$receiptEntries = @()
foreach ($sourceFile in $sourceFiles) {
    $relative = $sourceFile.FullName.Substring($sourceRoot.Length).TrimStart('\', '/')
    $renderedRelative = Get-OverlayRenderRelative -Relative $relative -ProjectPrefix $ProjectPrefix
    $content = Get-OverlayRenderContent `
        -Content (Get-OverlayContentText -Path $sourceFile.FullName) `
        -ProjectPrefix $ProjectPrefix `
        -ProjectName $ProjectName
    $writes += [pscustomobject]@{
        Relative = $renderedRelative
        Content  = $content
        Action   = 'overwrite'
    }
    $renderedHash = Get-OverlayTextHash -Text $content -NormalizeLineEndings
    $receiptEntries += [pscustomobject]@{
        Path             = $renderedRelative
        TemplateSha256   = $renderedHash
        InstalledSha256  = $renderedHash
    }
}

# AGENTS.md.trellisforge-template：人工合并模板，也纳入同一事务
$agentsRelative = 'AGENTS.md.trellisforge-template'
$agentsContent = Get-OverlayRenderContent `
    -Content (Get-OverlayContentText -Path (Join-Path $sourceRoot 'AGENTS.md.template')) `
    -ProjectPrefix $ProjectPrefix `
    -ProjectName $ProjectName
$agentsHash = Get-OverlayTextHash -Text $agentsContent -NormalizeLineEndings
$writes += [pscustomobject]@{
    Relative = $agentsRelative
    Content  = $agentsContent
    Action   = 'overwrite'
}
$receiptEntries += [pscustomobject]@{
    Path            = $agentsRelative
    TemplateSha256  = $agentsHash
    InstalledSha256 = $agentsHash
}

# 冲突与目录占用预检（不修改工作树）
$conflicts = @()
foreach ($item in $writes) {
    $destination = Assert-OverlaySafeRelative -Relative $item.Relative -TargetRoot $targetRoot
    if (Test-Path -LiteralPath $destination -PathType Container) {
        throw "目标路径是目录，无法覆盖模板文件: $destination"
    }
    if (Test-Path -LiteralPath $destination -PathType Leaf) {
        $conflicts += $destination
    }
    # 父路径链上出现文件时无法创建模板文件
    $parent = Split-Path -Parent $destination
    while ($parent) {
        if ($parent -eq $targetRoot) { break }
        if (Test-Path -LiteralPath $parent -PathType Leaf) {
            throw "目标父路径不是目录，无法创建模板文件: $parent"
        }
        if (Test-Path -LiteralPath $parent -PathType Container) { break }
        $nextParent = Split-Path -Parent $parent
        if ($nextParent -eq $parent) { break }
        $parent = $nextParent
    }
}

# 已有收据兼容性（避免把首次安装伪装成升级）
$existingReceipt = Read-OverlayReceipt -TargetRoot $targetRoot
if ($null -ne $existingReceipt) {
    if ([string]$existingReceipt.overlay -ne 'embedded-c' -or
        [string]$existingReceipt.project_prefix -ne $ProjectPrefix) {
        throw "目标仓库已有不兼容的 Forge 收据（overlay=$($existingReceipt.overlay), prefix=$($existingReceipt.project_prefix)）。如为 1.0 项目请使用 tools/update-embedded-c-overlay.ps1 升级，不要用首次安装器覆盖。"
    }
    Write-Host '检测到已有的 TrellisForge 收据，将执行覆盖安装（不修改升级后的 .trellis/.version 或 .template-hashes.json）。'
}

if ($conflicts.Count -gt 0 -and -not $Force) {
    $preview = $conflicts | Select-Object -First 10 | ForEach-Object { "  $_" }
    throw ("发现 $($conflicts.Count) 个将被覆盖的文件。请先审查差异；确认后使用 -Force。`n" + ($preview -join "`n"))
}

$forgeVersion = Get-OverlayForgeVersion
$receiptJson = New-OverlayReceiptPayload `
    -Overlay 'embedded-c' `
    -ProjectPrefix $ProjectPrefix `
    -ProjectName $ProjectName `
    -FileEntries $receiptEntries

$applyResult = Invoke-OverlayApply `
    -TargetRoot $targetRoot `
    -Writes $writes `
    -NewReceiptContent $receiptJson `
    -ManifestExtra @{
        from_version = $null
        to_version   = $forgeVersion
        overlay      = 'embedded-c'
    }

Write-Host "TrellisForge $forgeVersion 覆盖层已安装。"
if ($applyResult.BackupRoot) {
    Write-Host "所有将被模板覆盖的既有文件已备份到: $($applyResult.BackupRoot)"
    Write-Host "备份清单: $($applyResult.BackupManifestPath)"
}
Write-Host "安装收据: .trellis/trellisforge.json"
Write-Host "请将 AGENTS.md.trellisforge-template 的项目规则合并到 AGENTS.md，并填写所有 <...> 占位符。"
Write-Host '然后运行 docs/接入指南.md 中的脚本与 Hook 验证命令。'