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

# TrellisForge 1.0 -> 1.1 电梯模型升级器。
#
# 默认只做预检；只有显式 -Apply 才会写入目标项目。升级目标永远是当前
# TrellisForge 版本的完整覆盖层（最新版本直达），历史版本正文从 Forge 侧
# canonical 内容库取得，不保存逐对 new/ 快照。
#
# 有有效收据时，来源版本与项目参数从收据读取；无收据且省略 -FromVersion
# 时默认按 1.0 入场候选，但仍必须显式传入项目参数并通过历史 manifest /
# canonical 对象 / 结构迁移链 / 三方合并预检验证兼容性，无法验证时以
# unsupported 停止，不修改目标仓库。

$ErrorActionPreference = 'Stop'

$modulePath = Join-Path $PSScriptRoot 'lib\TrellisForgeOverlay.psm1'
if (-not (Test-Path -LiteralPath $modulePath -PathType Leaf)) {
    throw "共享模块缺失: $modulePath"
}
Import-Module $modulePath -Force -ErrorAction Stop

$overlay = 'embedded-c'
$targetRootFull = Assert-OverlayTargetRoot -TargetRoot $TargetRoot
$forgeVersion = Get-OverlayForgeVersion

# live 1.1 模板根目录（与首次安装器相同的包含/排除规则来源）
$sourceRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\templates\embedded-c-overlay'))
if (-not (Test-Path -LiteralPath $sourceRoot -PathType Container)) {
    throw "模板目录不存在: $sourceRoot"
}

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
$resolvedPrefix = $null
$resolvedName = $null

if ($null -ne $receipt) {
    if ([string]$receipt.trellisforge_version -eq $forgeVersion) {
        Write-Host "目标已是 TrellisForge $forgeVersion（收据 .trellis/trellisforge.json）。"
        Write-Host "状态: already-current。无需升级，安全退出。"
        exit 0
    }
    # 已安装旧版本（有收据）。来源版本 = 收据 trellisforge_version。
    $from = [string]$receipt.trellisforge_version
    $resolvedPrefix = [string]$receipt.project_prefix
    $resolvedName = [string]$receipt.project_name
    if ([string]::IsNullOrWhiteSpace($resolvedName)) {
        $resolvedName = [string]$receipt.project_name
    }
    if ($prefixProvided) {
        if ($resolvedPrefix -ne $ProjectPrefix -or $resolvedName -ne $ProjectName -or
            [string]$receipt.overlay -ne $overlay) {
            throw "已有收据与传入的项目参数不一致（fail closed）：收据 prefix=$resolvedPrefix name=$resolvedName overlay=$($receipt.overlay)。"
        }
    }
}
else {
    # 无收据：只支持默认/显式 1.0 入场适配。
    if (($null -eq $FromVersion -or [string]::IsNullOrWhiteSpace($FromVersion))) {
        $from = '1.0'
        Write-Host '未检测到安装收据；默认按 TrellisForge 1.0 入场候选执行兼容性预检。'
    }
    else {
        $from = [string]$FromVersion
    }
    if ($from -ne '1.0') {
        throw "unsupported: 来源版本 $from 不在支持范围。无收据目标只支持 TrellisForge 1.0 入场适配；目标缺少可验证收据并且无法按 1.0 基线预检时拒绝写入。"
    }
    if (-not $prefixProvided -or -not $nameProvided) {
        throw "没有安装收据时必须显式传入 -ProjectPrefix 和 -ProjectName（原安装使用的项目参数），不得猜测。"
    }
    $resolvedPrefix = $ProjectPrefix
    $resolvedName = $ProjectName
}

Write-Host "预检来源版本: $from -> 目标版本 $forgeVersion（overlay=$overlay）"

# ---------------------------------------------------------------- manifest
$srcManifest = Get-OverlayVersionManifest -Overlay $overlay -Version $from
$dstManifest = Get-OverlayVersionManifest -Overlay $overlay -Version $forgeVersion

# live 模板与目标 1.1 manifest / canonical 对象一致性（同一版本内漂移 fail closed）
Assert-OverlayLiveTemplateMatchesManifest `
    -Overlay $overlay `
    -Version $forgeVersion `
    -TemplateRoot $sourceRoot `
    -Manifest $dstManifest | Out-Null

# 结构迁移链预演（1.0->1.1 线性链，actions 为空 = 签收 bootstrap）
$chain = Get-OverlayStructuralChain -Overlay $overlay -FromVersion $from -ToVersion $forgeVersion
if ([string]::IsNullOrWhiteSpace([string]$chain.receipt_transition)) {
    throw "unsupported: 结构迁移链缺少收据转换定义（$from -> $forgeVersion）。"
}

# 来源/目标 manifest 完整比较，导出受影响集合
$srcByPath = @{}
foreach ($e in $srcManifest.Files) { $srcByPath[$e.Path] = $e }
$dstByPath = @{}
foreach ($e in $dstManifest.Files) { $dstByPath[$e.Path] = $e }

$allPaths = @(($srcByPath.Keys + $dstByPath.Keys | Sort-Object -Unique))

# 来源有目标无 = 结构迁移必须显式处理；当前 1.0->1.1 无删除
$srcOnly = @($allPaths | Where-Object { $srcByPath.ContainsKey($_) -and -not $dstByPath.ContainsKey($_) })
if ($srcOnly.Count -gt 0) {
    $missing = @($srcOnly | Where-Object { -not ($chain.actions | Where-Object { $_.path -eq $_ }) })
    if ($missing.Count -gt 0) {
        throw "unsupported: 来源路径在目标版本缺失且缺少显式结构迁移动作: $($missing -join ', ')"
    }
}

# ---------------------------------------------------------------- 预检分类
function Get-OverlayStatusText {
    param([AllowNull()][string]$Text)
    return (Get-OverlayNormalizedText -Text $Text)
}

function Add-OverlayClassification {
    param(
        [System.Collections.ArrayList]$List,
        [string]$Path,
        [string]$Action,
        [string]$Status,
        [AllowNull()][string]$Content,
        [AllowNull()][string]$Candidate,
        [string]$Suggestion,
        [bool]$UseCrLf
    )
    $null = $List.Add([pscustomobject]@{
            Path       = $Path
            Action     = $Action
            Status     = $Status
            Content    = $Content
            Candidate  = $Candidate
            Suggestion = $Suggestion
            UseCrLf    = $UseCrLf
        })
}

function Invoke-OverlayUpgradePreflight {
    param(
        [Parameter(Mandatory = $true)][object]$Source,
        [Parameter(Mandatory = $true)][object]$Destination,
        [Parameter(Mandatory = $true)][hashtable]$SrcByPath,
        [Parameter(Mandatory = $true)][hashtable]$DstByPath,
        [Parameter(Mandatory = $true)][object[]]$AllPaths,
        [Parameter(Mandatory = $true)][string]$Root,
        [Parameter(Mandatory = $true)][string]$Prefix,
        [Parameter(Mandatory = $true)][string]$Name
    )
    $classifications = [System.Collections.ArrayList]::new()
    foreach ($relative in $AllPaths) {
        $srcEntry = $null
        $dstEntry = $null
        if ($SrcByPath.ContainsKey($relative)) { $srcEntry = $SrcByPath[$relative] }
        if ($DstByPath.ContainsKey($relative)) { $dstEntry = $DstByPath[$relative] }

        if ($null -eq $dstEntry) {
            # 来源独有：已被结构链显式处理（本版本无删除动作），不进入合并计划
            Add-OverlayClassification -List $classifications -Path $relative -Action 'structural-remove' -Status 'already-current' -Content $null -Candidate $null -Suggestion '来源版本独有路径已由结构迁移链显式处理。' -UseCrLf $false
            continue
        }

        $renderedRelative = Get-OverlayRenderRelative -Relative $relative -ProjectPrefix $Prefix
        $targetPath = Assert-OverlaySafeRelative -Relative $renderedRelative -TargetRoot $Root
        $currentExists = Test-Path -LiteralPath $targetPath -PathType Leaf
        $useCrlf = $false
        $currentText = $null
        if ($currentExists) {
            $currentText = Get-OverlayContentText -Path $targetPath
            $useCrlf = Test-OverlayTextUsesCrLf -Text $currentText
        }
        elseif (Test-Path -LiteralPath $targetPath -PathType Container) {
            Add-OverlayClassification -List $classifications -Path $relative -Action $dstEntry.Ownership -Status 'unsupported' -Content $null -Candidate $null -Suggestion "目标路径是目录，无法作为文件处理: $targetPath" -UseCrLf $false
            continue
        }

        $dstCanonical = Get-OverlayCanonicalText -Overlay $overlay -CanonicalSha256 $dstEntry.CanonicalSha256
        $dstRendered = Get-OverlayRenderContent -Content $dstCanonical -ProjectPrefix $Prefix -ProjectName $Name
        $dstRenderedHash = Get-OverlayTextHash -Text $dstRendered -NormalizeLineEndings

        if ($null -eq $srcEntry) {
            # add：目标版本新增且没有来源 canonical old
            if (-not $currentExists) {
                Add-OverlayClassification -List $classifications -Path $relative -Action 'add' -Status 'add' -Content $dstRendered -Candidate $null -Suggestion '1.1 新增文件，写入模板内容。' -UseCrLf $false
            }
            elseif ((Get-OverlayStatusText -Text $currentText) -eq (Get-OverlayStatusText -Text $dstRendered)) {
                Add-OverlayClassification -List $classifications -Path $relative -Action 'add' -Status 'already-current' -Content $null -Candidate $null -Suggestion '新增文件内容已等于 1.1 模板，视为已满足。' -UseCrLf $useCrlf
            }
            else {
                Add-OverlayClassification -List $classifications -Path $relative -Action 'add' -Status 'conflict' -Content $dstRendered -Candidate $relative -Suggestion '新增路径已存在且内容与 1.1 模板不同；保留 1.1 候选到 candidates/ 供人工处理，不静默覆盖。' -UseCrLf $false
            }
            continue
        }

        # 来源与目标共同路径
        $srcCanonical = Get-OverlayCanonicalText -Overlay $overlay -CanonicalSha256 $srcEntry.CanonicalSha256
        $srcRendered = Get-OverlayRenderContent -Content $srcCanonical -ProjectPrefix $Prefix -ProjectName $Name

        if ($srcEntry.CanonicalSha256 -eq $dstEntry.CanonicalSha256) {
            # canonical 相同：保持工作树不变，仅记录收据
            if (-not $currentExists) {
                Add-OverlayClassification -List $classifications -Path $relative -Action 'managed' -Status 'add' -Content $dstRendered -Candidate $null -Suggestion 'canonical 未变但目标缺少该文件，写入 1.1 渲染内容。' -UseCrLf $false
            }
            else {
                Add-OverlayClassification -List $classifications -Path $relative -Action 'managed' -Status 'already-current' -Content $null -Candidate $null -Suggestion 'canonical 对象相同，保持工作树不变。' -UseCrLf $useCrlf
            }
            continue
        }

        # canonical 变化：managed（Forge 双方管理）或 adoption-baseline（接管合并）
        $mergeAction = if ($srcEntry.Ownership -eq 'adoption-baseline') { 'adopt' } else { 'merge' }
        if (-not $currentExists) {
            Add-OverlayClassification -List $classifications -Path $relative -Action $mergeAction -Status 'add' -Content $dstRendered -Candidate $null -Suggestion '目标缺少由 1.0/上游生成的文件，直接写入 1.1 模板内容。' -UseCrLf $false
            continue
        }
        $merge = Invoke-OverlayThreeWayMerge -OldText $srcRendered -CurrentText $currentText -NewText $dstRendered
        if ($merge.ExitCode -gt 1) {
            Add-OverlayClassification -List $classifications -Path $relative -Action $mergeAction -Status 'unsupported' -Content $null -Candidate $null -Suggestion "git merge-file 工具错误(exit=$($merge.ExitCode)): $($merge.Error)" -UseCrLf $false
            continue
        }
        if ($merge.ExitCode -eq 1) {
            Add-OverlayClassification -List $classifications -Path $relative -Action $mergeAction -Status 'conflict' -Content $merge.MergedText -Candidate $relative -Suggestion '三方合并产生冲突。请根据 .git/trellisforge-upgrade/<时间戳>-<GUID>/candidates/ 候选与 report.txt 手工解决目标文件后重新预检。' -UseCrLf $useCrlf
            continue
        }
        $merged = $merge.MergedText
        $mergedNorm = Get-OverlayStatusText -Text $merged
        $currentNorm = Get-OverlayStatusText -Text $currentText
        $dstNorm = Get-OverlayStatusText -Text $dstRendered
        if ($mergedNorm -eq $currentNorm -and $srcRendered -eq $currentText) {
            Add-OverlayClassification -List $classifications -Path $relative -Action $mergeAction -Status 'already-current' -Content $null -Candidate $null -Suggestion '当前文件已等于是 1.0 来源渲染内容。' -UseCrLf $useCrlf
        }
        elseif ($mergedNorm -eq $currentNorm) {
            Add-OverlayClassification -List $classifications -Path $relative -Action $mergeAction -Status 'already-current' -Content $null -Candidate $null -Suggestion '当前内容已等于三方合并结果，无需修改。' -UseCrLf $useCrlf
        }
        elseif ($mergedNorm -eq $dstNorm) {
            Add-OverlayClassification -List $classifications -Path $relative -Action $mergeAction -Status 'update' -Content (ConvertTo-OverlayLineEndings -Text $merged -UseCrLf $useCrlf) -Candidate $null -Suggestion '无用户差异，按 1.1 模板更新。' -UseCrLf $useCrlf
        }
        else {
            Add-OverlayClassification -List $classifications -Path $relative -Action $mergeAction -Status 'user-merged' -Content (ConvertTo-OverlayLineEndings -Text $merged -UseCrLf $useCrlf) -Candidate $null -Suggestion '已在 1.1 更新基础上保留非重叠用户定制。' -UseCrLf $useCrlf
        }
    }
    return @($classifications)
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
        project_prefix  = $resolvedPrefix
        project_name    = $resolvedName
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
    $lines += "TrellisForge $from -> $forgeVersion 升级预检失败（工作树未被修改）"
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

$classifications = Invoke-OverlayUpgradePreflight `
    -Source $srcManifest `
    -Destination $dstManifest `
    -SrcByPath $srcByPath `
    -DstByPath $dstByPath `
    -AllPaths $allPaths `
    -Root $targetRootFull `
    -Prefix $resolvedPrefix `
    -Name $resolvedName

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
    $destinationRelative = Get-OverlayRenderRelative -Relative $cl.Path -ProjectPrefix $resolvedPrefix
    $renderedRelative = (Assert-OverlaySafeRelative -Relative $destinationRelative -TargetRoot $targetRootFull)
    $dstEntry = $dstByPath[$cl.Path]
    $canonicalHash = $dstEntry.CanonicalSha256
    $baselineHash = $null
    $installedHash = $null

    if ($cl.Status -eq 'already-current') {
        $renderedCanonical = Get-OverlayRenderContent -Content (Get-OverlayCanonicalText -Overlay $overlay -CanonicalSha256 $canonicalHash) -ProjectPrefix $resolvedPrefix -ProjectName $resolvedName
        $baselineHash = Get-OverlayTextHash -Text $renderedCanonical -NormalizeLineEndings
        $installedHash = Get-OverlayFileHash -Path $renderedRelative -NormalizeLineEndings
    }
    else {
        $renderedCanonical = Get-OverlayRenderContent -Content (Get-OverlayCanonicalText -Overlay $overlay -CanonicalSha256 $canonicalHash) -ProjectPrefix $resolvedPrefix -ProjectName $resolvedName
        $baselineHash = Get-OverlayTextHash -Text $renderedCanonical -NormalizeLineEndings
        $writes += [pscustomobject]@{
            Relative = $destinationRelative
            Content  = $cl.Content
            Action   = $cl.Status
        }
        $installedHash = Get-OverlayTextHash -Text $cl.Content -NormalizeLineEndings
    }
    $receiptEntries += [pscustomobject]@{
        Path             = $destinationRelative
        CanonicalSha256  = $canonicalHash
        BaselineSha256   = $baselineHash
        InstalledSha256  = $installedHash
    }
}

$receiptJson = New-OverlayReceiptPayload `
    -Overlay $overlay `
    -ProjectPrefix $resolvedPrefix `
    -ProjectName $resolvedName `
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
Write-Host "安装收据: .trellis/trellisforge.json（canonical_sha256/baseline_sha256/installed_sha256）"
Write-Host '请提交迁移结果前审查 git diff，并按 docs/接入指南.md 的“从 1.0 升级到 1.1”章节执行升级后验证。'