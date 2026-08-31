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

if (-not (Test-Path -LiteralPath (Join-Path $targetRootFull '.git') -PathType Container)) {
    throw "目标不是 Git 仓库根目录: $targetRootFull"
}

if (-not (Test-Path -LiteralPath (Join-Path $targetRootFull '.trellis') -PathType Container)) {
    throw "请先在目标仓库运行 trellis init: $targetRootFull"
}

$sourceFiles = Get-ChildItem -LiteralPath $sourceRoot -Recurse -File
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
Write-Host "请将 $agentsDestination 的项目规则合并到 AGENTS.md，并填写所有 <...> 占位符。"
Write-Host '然后运行 docs/接入指南.md 中的脚本与 Hook 验证命令。'
