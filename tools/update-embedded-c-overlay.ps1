[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$TargetRoot,

    [Parameter(Mandatory = $false)]
    [string]$ProjectPrefix,

    [Parameter(Mandatory = $false)]
    [string]$ProjectName,

    [Parameter(Mandatory = $false)]
    [string]$FromVersion,

    [switch]$Apply
)

# TrellisForge 1.0 -> 1.1 版本化升级器。
# 默认只做预检；只有显式 -Apply 才会写入目标项目。
# 无收据时来源版本按迁移候选默认 1.0（仍必填项目参数并执行全部兼容预检）。

$ErrorActionPreference = 'Stop'

$modulePath = Join-Path $PSScriptRoot 'lib\TrellisForgeOverlay.psm1'
if (-not (Test-Path -LiteralPath $modulePath -PathType Leaf)) {
    throw "共享模块缺失: $modulePath"
}
Import-Module $modulePath -Force -ErrorAction Stop

$overlay = 'embedded-c'
$targetRootFull = Assert-OverlayTargetRoot -TargetRoot $TargetRoot
$forgeVersion = Get-OverlayForgeVersion

# ---------------------------------------------------------------- 参数校验
$prefixProvided = -not [string]::IsNullOrWhiteSpace($ProjectPrefix)
$nameProvided = -not [string]::IsNullOrWhiteSpace($ProjectName)
if ($prefixProvided -xor $nameProvided) {
    throw "ProjectPrefix 与 ProjectName 必须同时提供或都省略，不能只提供其中一个。"
}
if ($prefixProvided) {
    Assert-OverlayProjectParams -ProjectPrefix $ProjectPrefix -ProjectName $ProjectName | Out-Null
}

# ---------------------------------------------------------------- 收据判定
$receipt = Read-OverlayReceipt -TargetRoot $targetRootFull
if ($null -ne $receipt) {
    if ([string]$receipt.trellisforge_version -ne $forgeVersion) {
        throw "unsupported: 目标收据版本 $($receipt.trellisforge_version) 不是 $forgeVersion。本升级器只支持 1.0 -> 1.1 迁移；无法确认来源版本，拒绝写入。"
    }
    if ($prefixProvided) {
        if ([string]$receipt.project_prefix -ne $ProjectPrefix -or
            [string]$receipt.project_name -ne $ProjectName -or
            [string]$receipt.overlay -ne $overlay) {
            throw "已有收据与传入的项目参数不一致（fail closed）：收据 prefix=$($receipt.project_prefix) name=$($receipt.project_name) overlay=$($receipt.overlay)。"
        }
    }
    Write-Host "目标已是 TrellisForge $forgeVersion（收据 .trellis/trellisforge.json）。"
    Write-Host "状态: already-current。无需升级，安全退出。"
    exit 0
}

if (($null -eq $FromVersion -or [string]::IsNullOrWhiteSpace($FromVersion))) {
    $from = '1.0'
    Write-Host '未检测到安装收据；默认按 TrellisForge 1.0 迁移候选执行兼容性预检。'
}
else {
    $from = [string]$FromVersion
}
if ($from -ne '1.0') {
    throw "unsupported: 来源版本 $from 不在支持范围。本升级器只支持 1.0 -> 1.1；目标缺少可验证收据并且无法按 1.0 基线预检时拒绝写入。"
}
if (-not $prefixProvided -or -not $nameProvided) {
    throw "没有安装收据时必须显式传入 -ProjectPrefix 和 -ProjectName（原安装使用的项目参数），不得猜测。"
}

# ---------------------------------------------------------------- 迁移清单
$migrationDir = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\migrations\embedded-c-overlay\1.0-to-1.1'))
$migration = $null
try {
    $migration = Get-OverlayMigrationManifest `
        -MigrationDir $migrationDir `
        -ProjectPrefix $ProjectPrefix `
        -ProjectName $ProjectName
}
catch {
    throw "unsupported: 迁移清单加载失败：$($_.Exception.Message)"
}

if ([string]$migration.Manifest.from_version -ne $from) {
    throw "unsupported: 迁移清单 from_version=$($migration.Manifest.from_version) 与来源版本 $from 不一致。"
}
if ([string]$migration.Manifest.to_version -ne $forgeVersion) {
    throw "unsupported: 迁移清单 to_version=$($migration.Manifest.to_version) 与 TrellisForge 版本 $forgeVersion 不一致。"
}

# ---------------------------------------------------------------- 预检分类
function Get-OverlayStatusText {
    param([AllowNull()][string]$Text)
    return (Get-OverlayNormalizedText -Text $Text)
}

function Invoke-OverlayPreflight {
    param(
        [Parameter(Mandatory = $true)][object[]]$MigrationPaths,
        [Parameter(Mandatory = $true)][string]$Root
    )
    $classifications = @()
    foreach ($path in $MigrationPaths) {
        $targetPath = Assert-OverlaySafeRelative -Relative $path.RenderedPath -TargetRoot $Root
        $currentExists = Test-Path -LiteralPath $targetPath -PathType Leaf
        $useCrlf = $false
        $currentText = $null
        if ($currentExists) {
            $currentText = Get-OverlayContentText -Path $targetPath
            $useCrlf = Test-OverlayTextUsesCrLf -Text $currentText
        }
        elseif (Test-Path -LiteralPath $targetPath -PathType Container) {
            $classifications += [pscustomobject]@{
                Path        = $path.Relative
                Action      = $path.Action
                Status      = 'unsupported'
                Content     = $null
                Candidate    = $null
                Suggestion   = "目标路径是目录，无法作为文件处理: $targetPath"
                UseCrLf     = $false
            }
            continue
        }

        if ($path.Action -in @('merge', 'adopt')) {
            if (-not $currentExists) {
                $classifications += [pscustomobject]@{
                    Path        = $path.Relative
                    Action      = $path.Action
                    Status      = 'add'
                    Content     = $path.NewText
                    Candidate    = $null
                    Suggestion   = '目标缺少由 1.0/上游生成的文件，直接写入 1.1 模板内容。'
                    UseCrLf     = $false
                }
                continue
            }
            $merge = Invoke-OverlayThreeWayMerge -OldText $path.OldText -CurrentText $currentText -NewText $path.NewText
            if ($merge.ExitCode -gt 1) {
                $classifications += [pscustomobject]@{
                    Path       = $path.Relative
                    Action     = $path.Action
                    Status     = 'unsupported'
                    Content    = $null
                    Candidate   = $null
                    Suggestion = "git merge-file 工具错误(exit=$($merge.ExitCode)): $($merge.Error)"
                    UseCrLf    = $false
                }
                continue
            }
            if ($merge.ExitCode -eq 1) {
                $classifications += [pscustomobject]@{
                    Path       = $path.Relative
                    Action     = $path.Action
                    Status     = 'conflict'
                    Content    = $merge.MergedText
                    Candidate   = $path.Relative
                    Suggestion = '三方合并产生冲突。请根据 .git/trellisforge-upgrade/<时间戳>-<GUID>/candidates/ 候选与 report.txt 手工解决目标文件后重新预检。'
                    UseCrLf    = $useCrlf
                }
                continue
            }
            $merged = $merge.MergedText
            $mergedNorm = Get-OverlayStatusText -Text $merged
            $currentNorm = Get-OverlayStatusText -Text $currentText
            $newNorm = Get-OverlayStatusText -Text $path.NewText
            if ($mergedNorm -eq $currentNorm) {
                $classifications += [pscustomobject]@{
                    Path      = $path.Relative
                    Action    = $path.Action
                    Status    = 'already-current'
                    Content   = $null
                    Candidate  = $null
                    Suggestion = '当前内容已等于三方合并结果，无需修改。'
                    UseCrLf   = $useCrlf
                }
            }
            elseif ($mergedNorm -eq $newNorm) {
                $classifications += [pscustomobject]@{
                    Path      = $path.Relative
                    Action    = $path.Action
                    Status    = 'update'
                    Content   = (ConvertTo-OverlayLineEndings -Text $merged -UseCrLf $useCrlf)
                    Candidate  = $null
                    Suggestion = '无用户差异，按 1.1 模板更新。'
                    UseCrLf   = $useCrlf
                }
            }
            else {
                $classifications += [pscustomobject]@{
                    Path      = $path.Relative
                    Action    = $path.Action
                    Status    = 'user-merged'
                    Content   = (ConvertTo-OverlayLineEndings -Text $merged -UseCrLf $useCrlf)
                    Candidate  = $null
                    Suggestion = '已在 1.1 更新基础上保留非重叠用户定制。'
                    UseCrLf   = $useCrlf
                }
            }
        }
        else { # add
            if (-not $currentExists) {
                $classifications += [pscustomobject]@{
                    Path       = $path.Relative
                    Action     = $path.Action
                    Status     = 'add'
                    Content    = $path.NewText
                    Candidate   = $null
                    Suggestion  = '1.1 新增文件，写入模板内容。'
                    UseCrLf    = $false
                }
                continue
            }
            $currentNorm = Get-OverlayStatusText -Text $currentText
            $newNorm = Get-OverlayStatusText -Text $path.NewText
            if ($currentNorm -eq $newNorm) {
                $classifications += [pscustomobject]@{
                    Path      = $path.Relative
                    Action    = $path.Action
                    Status    = 'already-current'
                    Content   = $null
                    Candidate  = $null
                    Suggestion = '新增文件已等于 1.1 模板内容，视为已满足。'
                    UseCrLf   = $false
                }
            }
            else {
                $classifications += [pscustomobject]@{
                    Path       = $path.Relative
                    Action     = $path.Action
                    Status     = 'conflict'
                    Content    = $path.NewText
                    Candidate   = $path.Relative
                    Suggestion  = '新增路径已存在且内容与 1.1 模板不同，保留 1.1 候选到 candidates/ 供人工处理；不静默覆盖。'
                    UseCrLf    = $false
                }
            }
        }
    }
    return $classifications
}

function Write-OverlayUpgradeReport {
    param(
        [Parameter(Mandatory = $true)][string]$TargetRootFull,
        [Parameter(Mandatory = $true)][object[]]$Classifications,
        [Parameter(Mandatory = $true)][bool]$Unsupported
    )
    $gitEntry = Get-OverlayGitMetadataDir -TargetRoot $TargetRootFull -GitPathEntry 'trellisforge-upgrade'
    $runDir = New-OverlayUniqueDir -ParentPath $gitEntry
    $blocked = @($Classifications | Where-Object { $_.Status -in @('conflict', 'unsupported') })
    $candidatesDir = Join-Path $runDir 'candidates'
    $candidateEntries = @()
    foreach ($cl in $blocked) {
        if ([string]::IsNullOrWhiteSpace($cl.Candidate) -or $cl.Status -eq 'unsupported') { continue }
        $candPath = Assert-OverlaySafeRelative -Relative $cl.Candidate -TargetRoot $TargetRootFull
        $newParent = Join-Path $candidatesDir $cl.Candidate
        New-Item -ItemType Directory -Path (Split-Path -Parent $newParent) -Force -ErrorAction Stop | Out-Null
        $contentToWrite = $cl.Content
        if ([string]::IsNullOrWhiteSpace($contentToWrite)) { $contentToWrite = '' }
        [System.IO.File]::WriteAllText(
            $newParent,
            $contentToWrite,
            [System.Text.UTF8Encoding]::new($false)
        )
        $candidateEntries += $cl.Candidate.Replace('\', '/')
    }

    $reportJson = [ordered]@{
        schema_version  = 1
        status          = $(if ($Unsupported) { 'unsupported' } else { 'conflict' })
        created_at      = (Get-Date).ToString('o')
        from_version    = $from
        to_version      = $forgeVersion
        overlay         = $overlay
        project_prefix  = $ProjectPrefix
        project_name    = $ProjectName
        candidates_root = 'candidates/'
        paths           = @(foreach ($cl in $blocked) {
            [ordered]@{
                path       = $cl.Path
                action     = $cl.Action
                status     = $cl.Status
                candidate  = if ([string]::IsNullOrWhiteSpace($cl.Candidate)) { $null } else { 'candidates/' + $cl.Candidate.Replace('\', '/') }
                suggestion = $cl.Suggestion
            }
        })
    }
    $jsonPath = Join-Path $runDir 'report.json'
    [System.IO.File]::WriteAllText(
        $jsonPath,
        ($reportJson | ConvertTo-Json -Depth 6),
        [System.Text.UTF8Encoding]::new($false)
    )

    $lines = @()
    $lines += 'TrellisForge 1.0 -> 1.1 升级预检失败（工作树未被修改）'
    $lines += "状态: $(if ($Unsupported) { 'unsupported' } else { 'conflict' })"
    $lines += "运行目录: $runDir"
    $lines += ''
    foreach ($cl in $blocked) {
        $lines += ("[{0}] {1} ({2}) : {3}" -f $cl.Status.ToUpper(), $cl.Path, $cl.Action, $cl.Suggestion)
    }
    $lines += ''
    $lines += '请按 report.json / report.txt 与 candidates/* 处理目标仓库中的冲突文件后，重新运行本升级器预检；'
    $lines += '全部路径无冲突后才会允许 -Apply；本工具不会忽略冲突或部分应用。'
    [System.IO.File]::WriteAllText(
        (Join-Path $runDir 'report.txt'),
        (($lines -join "`r`n") + "`r`n"),
        [System.Text.UTF8Encoding]::new($false)
    )
    return $runDir
}

$classifications = Invoke-OverlayPreflight -MigrationPaths $migration.Paths -Root $targetRootFull

$blocked = @($classifications | Where-Object { $_.Status -in @('conflict', 'unsupported') })
$hasUnsupported = @($classifications | Where-Object { $_.Status -eq 'unsupported' }).Count -gt 0

if ($blocked.Count -gt 0) {
    $runDir = Write-OverlayUpgradeReport -TargetRootFull $targetRootFull -Classifications $classifications -Unsupported $hasUnsupported
    Write-Host '预检未通过：存在冲突或不受支持路径。'
    Write-Host "冲突报告: $runDir"
    foreach ($b in $blocked) {
        Write-Host ("  [{0}] {1} ({2})" -f $b.Status.ToUpper(), $b.Path, $b.Action)
    }
    Write-Host '本次预检未修改目标工作树，也没有写入或更新 1.1 安装收据。'
    exit 1
}

if (-not $Apply) {
    Write-Host '预检通过（未应用）。路径处理计划：'
    foreach ($cl in $classifications) {
        Write-Host ("  [{0}] {1} ({2})" -f $cl.Status.ToUpper(), $cl.Path, $cl.Action)
    }
    Write-Host '如需应用升级，请补充 -Apply 参数后重新运行。'
    exit 0
}

# ---------------------------------------------------------------- 应用事务
$writes = @()
$receiptEntries = @()
foreach ($cl in $classifications) {
    $renderedRelative = (Assert-OverlaySafeRelative -Relative $cl.Path -TargetRoot $targetRootFull)
    $templateHash = $null
    $installedHash = $null
    foreach ($migPath in $migration.Paths) {
        if ($migPath.Relative -eq $cl.Path) {
            $templateHash = Get-OverlayTextHash -Text $migPath.NewText -NormalizeLineEndings
            break
        }
    }
    if ($cl.Status -eq 'already-current') {
        $installedHash = Get-OverlayFileHash -Path $renderedRelative -NormalizeLineEndings
    }
    else {
        $writes += [pscustomobject]@{
            Relative = $cl.Path
            Content  = $cl.Content
            Action   = $cl.Status
        }
        $installedHash = Get-OverlayTextHash -Text $cl.Content -NormalizeLineEndings
    }
    $receiptEntries += [pscustomobject]@{
        Path            = $cl.Path
        TemplateSha256  = $templateHash
        InstalledSha256 = $installedHash
    }
}

$receiptJson = New-OverlayReceiptPayload `
    -Overlay $overlay `
    -ProjectPrefix $ProjectPrefix `
    -ProjectName $ProjectName `
    -FileEntries $receiptEntries

$applyResult = Invoke-OverlayApply `
    -TargetRoot $targetRootFull `
    -Writes $writes `
    -NewReceiptContent $receiptJson `
    -ManifestExtra @{
        from_version = $from
        to_version   = $forgeVersion
        overlay      = $overlay
    }

Write-Host "TrellisForge 升级完成: $from -> $forgeVersion"
if ($applyResult.BackupRoot) {
    Write-Host "覆盖前的原文件与旧收据已备份到: $($applyResult.BackupRoot)"
    Write-Host "备份清单: $($applyResult.BackupManifestPath)"
}
Write-Host "安装收据: .trellis/trellisforge.json"
Write-Host '请提交迁移结果前审查 git diff，并按 docs/接入指南.md 的“从 1.0 升级到 1.1”章节执行升级后验证。'