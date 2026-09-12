# TrellisForgeOverlay.psm1
# Shared safety/mechanism layer used by BOTH first-time installation
# (install-embedded-c-overlay.ps1) and elevator-model upgrades to the current
# TrellisForge version (update-embedded-c-overlay.ps1).
#
# Contract (tools spec `tooling/powershell.md`):
#   - Target root must be a real Git worktree root that ran `trellis init`.
#   - Paths are handled with -LiteralPath; relative paths that escape the
#     target root, absolute paths, or control-char/glob patterns are rejected.
#   - Text is read/written as UTF-8 without BOM; CRLF and LF are treated as
#     equivalent line endings for hashing and three-way merges, but the target
#     file's actual newline style is preserved when writing merged results.
#   - Overwrites always happen after a Git-metadata backup with SHA-256 manifest.
#   - Every write goes through one atomic transaction that restores backups and
#     removes newly created files on failure; the install receipt
#     (.trellis/trellisforge.json) is part of that transaction.
#   - Never touch .trellis/.version or .trellis/.template-hashes.json.
#
# Elevator model: versioned manifests under history/embedded-c-overlay/versions/
# plus a SHA-256-keyed canonical object library under
# history/embedded-c-overlay/objects/. A manifest entry references its canonical
# body by `canonical_sha256`; the object file path is derived as
# objects/<canonical_sha256>. Upgrades compose the ADJACENT structural steps
# (migrations/embedded-c-overlay/structural/<from>-to-<to>.json) across the
# ordered manifest-version range, while file bodies always merge directly from
# the source canonical to the live template. Installers load the current
# VERSION manifest to prove the live template equals the published target
# before writing.
#
# The module keeps a deliberately narrow export surface; entry scripts own
# parameter parsing and user-facing output.

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Test-OverlayHasProperty {
    param($Object, [string]$Name)
    return $null -ne $Object -and $Object.psobject.Properties.Name -contains $Name
}

# ---------------------------------------------------------------- internals

function Get-OverlayNormalizedText {
    # Unify line endings for hashing/merge: CRLF -> LF only. Never trims
    # trailing whitespace or trailing blank lines.
    param([AllowNull()][string]$Text)
    if ($null -eq $Text) { return '' }
    return $Text.Replace("`r`n", "`n")
}

function Test-OverlayTextUsesCrLf {
    param([AllowNull()][string]$Text)
    if ($null -eq $Text) { return $false }
    return $Text.Contains("`r`n")
}

function ConvertTo-OverlayLineEndings {
    # Converts text to the requested newline style, keeping all other content
    # bytes (including trailing whitespace/blank lines) unchanged.
    param(
        [AllowEmptyString()][string]$Text,
        [bool]$UseCrLf
    )
    $lf = Get-OverlayNormalizedText -Text $Text
    if (-not $UseCrLf) { return $lf }
    return ($lf -replace "`n", "`r`n")
}

function Assert-OverlaySafeRelative {
    # Rejects absolute paths, parent traversals, glob metacharacters injected
    # via prefixes, reserved segments and paths that escape the target root.
    param(
        [Parameter(Mandatory = $true)][AllowNull()][string]$Relative,
        [Parameter(Mandatory = $true)][string]$TargetRoot
    )
    if ([string]::IsNullOrEmpty($Relative)) {
        throw "相对路径为空"
    }
    if ($Relative.IndexOfAny([char[]]@("`r", "`n", "`0", "`t")) -ge 0) {
        throw "相对路径包含换行/空字符: $Relative"
    }
    $normalized = $Relative.Replace('/', [System.IO.Path]::DirectorySeparatorChar)
    $rootFull = [System.IO.Path]::GetFullPath($TargetRoot).TrimEnd([System.IO.Path]::DirectorySeparatorChar)
    $full = [System.IO.Path]::GetFullPath((Join-Path $rootFull $normalized))
    if (-not $full.StartsWith($rootFull + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "路径逃逸目标仓库根目录: $Relative"
    }
    $segments = $Relative.Split(@('/', '\'), [System.StringSplitOptions]::RemoveEmptyEntries)
    foreach ($segment in $segments) {
        if ($segment -eq '..') {
            throw "路径包含上级目录引用: $Relative"
        }
        if ($segment -eq '.' -or $segment -eq '-') {
            throw "路径包含非法目录段: $Relative"
        }
        if ($segment.IndexOfAny([char[]]@('*', '?', '[')) -ge 0) {
            throw "路径包含目录/文件名通配符: $Relative"
        }
    }
    return $full
}

function Get-OverlayUtf8NoBom {
    return [System.Text.UTF8Encoding]::new($false)
}

function Get-OverlaySha256Bytes {
    param([Parameter(Mandatory = $true)][byte[]]$Bytes)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        return (($sha.ComputeHash($Bytes) | ForEach-Object { $_.ToString('x2') }) -join '')
    }
    finally {
        $sha.Dispose()
    }
}

function Get-OverlayContentText {
    # Reads a template or target text file as UTF-8 (no BOM); returns string.
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [switch]$AllowMissing
    )
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        if ($AllowMissing) { return $null }
        throw "文件不存在: $Path"
    }
    return [System.IO.File]::ReadAllText($Path, (Get-OverlayUtf8NoBom))
}

function Write-OverlayContentText {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Content
    )
    [System.IO.File]::WriteAllText($Path, $Content, (Get-OverlayUtf8NoBom))
}

# ---------------------------------------------------------------- release root

function Get-OverlayReleaseRoot {
    # The release root holds VERSION, history/ and migrations/. The module
    # lives at <release-root>\tools\lib\TrellisForgeOverlay.psm1.
    $releaseRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
    if (-not (Test-Path -LiteralPath $releaseRoot -PathType Container)) {
        throw "无法定位 TrellisForge 发布根目录: $releaseRoot"
    }
    return $releaseRoot
}

# ------------------------------------------------------------- public API

function Get-OverlayForgeVersion {
    # TrellisForge version fact source: repo-root VERSION file.
    $releaseRoot = Get-OverlayReleaseRoot
    $versionPath = Join-Path $releaseRoot 'VERSION'
    if (-not (Test-Path -LiteralPath $versionPath -PathType Leaf)) {
        throw "版本事实文件缺失: $versionPath"
    }
    $version = (Get-Content -LiteralPath $versionPath -Raw -ErrorAction Stop).Trim()
    if ($version -notmatch '^\d+\.\d+$') {
        throw "版本事实文件内容无效: '$version'"
    }
    return $version
}

function Get-OverlayHistoryRoot {
    # The asset library lives at history/<overlay>-overlay (e.g.
    # history/embedded-c-overlay). The overlay identifier in manifests and
    # receipts is the short form ("embedded-c").
    param([Parameter(Mandatory = $true)][string]$Overlay)
    $releaseRoot = Get-OverlayReleaseRoot
    $dirName = "$Overlay-overlay"
    $root = [System.IO.Path]::GetFullPath((Join-Path $releaseRoot "history\$dirName"))
    if (-not (Test-Path -LiteralPath $root -PathType Container)) {
        throw "历史内容库缺失: $root"
    }
    return $root
}

function Get-OverlayStructuralDir {
    param([Parameter(Mandatory = $true)][string]$Overlay)
    $releaseRoot = Get-OverlayReleaseRoot
    $dirName = "$Overlay-overlay"
    $dir = [System.IO.Path]::GetFullPath((Join-Path $releaseRoot "migrations\$dirName\structural"))
    if (-not (Test-Path -LiteralPath $dir -PathType Container)) {
        throw "结构迁移目录缺失: $dir"
    }
    return $dir
}

function Assert-OverlayTargetRoot {
    # Requires TargetRoot to be an existing container, a Git work-tree root,
    # and to have run `trellis init` (a .trellis directory exists).
    param(
        [Parameter(Mandatory = $true)][string]$TargetRoot
    )
    $targetFull = [System.IO.Path]::GetFullPath($TargetRoot)
    if (-not (Test-Path -LiteralPath $targetFull -PathType Container)) {
        throw "目标目录不存在: $targetFull"
    }
    if (-not (Test-Path -LiteralPath (Join-Path $targetFull '.trellis') -PathType Container)) {
        throw "请先在目标仓库运行 trellis init: $targetFull"
    }
    & git -C $targetFull rev-parse --show-toplevel 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        $detail = (& git -C $targetFull rev-parse --show-toplevel 2>&1 | Out-String).Trim()
        throw "目标目录不是 Git 仓库工作树根目录: $targetFull$(if ($detail) { [Environment]::NewLine + $detail } else { '' })"
    }
    $resolved = (& git -C $targetFull rev-parse --show-toplevel 2>$null | Out-String).Trim()
    if ([string]::IsNullOrWhiteSpace($resolved)) {
        throw "无法解析目标 Git 工作树根目录: $targetFull"
    }
    $resolvedFull = [System.IO.Path]::GetFullPath($resolved)
    if ($resolvedFull.TrimEnd([System.IO.Path]::DirectorySeparatorChar) -ne $targetFull.TrimEnd([System.IO.Path]::DirectorySeparatorChar)) {
        throw "目标目录不是 Git 工作树根目录（实际根为 $resolvedFull）: $targetFull"
    }
    return $targetFull
}

function Assert-OverlayProjectParams {
    # Defense-in-depth for project parameters. Entry scripts also declare
    # [ValidatePattern] on their own parameters.
    param(
        [Parameter(Mandatory = $true)][AllowNull()][string]$ProjectPrefix,
        [Parameter(Mandatory = $true)][AllowNull()][string]$ProjectName
    )
    if ([string]::IsNullOrWhiteSpace($ProjectPrefix)) {
        throw "ProjectPrefix 必填"
    }
    if ($ProjectPrefix -cnotmatch '^[a-z0-9]+(?:-[a-z0-9]+)*$') {
        throw "ProjectPrefix 只能包含小写字母、数字和连字符: $ProjectPrefix"
    }
    if ([string]::IsNullOrWhiteSpace($ProjectName)) {
        throw "ProjectName 必填"
    }
    if ($ProjectName.IndexOfAny([char[]]@("`r", "`n", "`0")) -ge 0) {
        throw "ProjectName 不能包含换行或空字符"
    }
    if ($ProjectName -match '`') {
        throw "ProjectName 不能包含反引号: $ProjectName"
    }
    return $true
}

function Get-OverlayTemplateCacheFiles {
    # Returns Python cache artifacts resident in a template tree.
    param([Parameter(Mandatory = $true)][string]$SourceRoot)
    return @(Get-ChildItem -LiteralPath $SourceRoot -Recurse -File -ErrorAction Stop |
        Where-Object {
            $_.FullName -match '[\\/]__pycache__[\\/]' -or $_.Extension -in '.pyc', '.pyo'
        })
}

function Get-OverlayRenderRelative {
    # Replaces the path token __PROJECT_PREFIX__.
    param(
        [Parameter(Mandatory = $true)][string]$Relative,
        [Parameter(Mandatory = $true)][string]$ProjectPrefix
    )
    return $Relative.Replace('__PROJECT_PREFIX__', $ProjectPrefix)
}

function Get-OverlayRenderContent {
    # Replaces content tokens PROJECT_PREFIX and PROJECT_NAME in order.
    param(
        [Parameter(Mandatory = $true)][AllowEmptyString()][string]$Content,
        [Parameter(Mandatory = $true)][string]$ProjectPrefix,
        [Parameter(Mandatory = $true)][string]$ProjectName
    )
    return $Content.Replace('PROJECT_PREFIX', $ProjectPrefix).Replace('PROJECT_NAME', $ProjectName)
}

function Get-OverlayTextHash {
    # SHA-256 over UTF-8 bytes. With -NormalizeLineEndings, CRLF and LF are
    # treated as equal (CRLF -> LF only; nothing else is altered).
    param(
        [AllowEmptyString()][string]$Text,
        [switch]$NormalizeLineEndings
    )
    $effective = $Text
    if ($NormalizeLineEndings) {
        $effective = Get-OverlayNormalizedText -Text $Text
    }
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($effective)
    return Get-OverlaySha256Bytes -Bytes $bytes
}

function Get-OverlayFileHash {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [switch]$NormalizeLineEndings
    )
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "文件不存在: $Path"
    }
    if ($NormalizeLineEndings) {
        return Get-OverlayTextHash -Text (Get-OverlayContentText -Path $Path) -NormalizeLineEndings
    }
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $stream = [System.IO.File]::OpenRead([System.IO.Path]::GetFullPath($Path))
        try {
            return ((($sha.ComputeHash($stream)) | ForEach-Object { $_.ToString('x2') }) -join '')
        }
        finally {
            $stream.Dispose()
        }
    }
    finally {
        $sha.Dispose()
    }
}

function Get-OverlayGitMetadataDir {
    # Returns an absolute git-metadata path for a named entry, e.g.
    # 'trellisforge-backup' -> <worktree>/.git/trellisforge-backup.
    param(
        [Parameter(Mandatory = $true)][string]$TargetRoot,
        [Parameter(Mandatory = $true)][string]$GitPathEntry
    )
    $meta = & git -C $TargetRoot rev-parse --path-format=absolute --git-path $GitPathEntry 2>$null | Out-String
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($meta)) {
        throw "无法解析 Git 元数据路径 ($GitPathEntry): $TargetRoot"
    }
    $metaFull = [System.IO.Path]::GetFullPath(($meta.Trim())).TrimEnd([System.IO.Path]::DirectorySeparatorChar)
    $commonRaw = (& git -C $TargetRoot rev-parse --path-format=absolute --git-common-dir 2>$null | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($commonRaw)) {
        throw "无法解析 Git 公共目录: $TargetRoot"
    }
    $gitCommonFull = [System.IO.Path]::GetFullPath($commonRaw).TrimEnd([System.IO.Path]::DirectorySeparatorChar)
    if (-not $metaFull.StartsWith($gitCommonFull + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Git 元数据路径逃逸了 .git 目录: $metaFull"
    }
    return $metaFull
}

function New-OverlayUniqueDir {
    param([Parameter(Mandatory = $true)][string]$ParentPath)
    if (-not (Test-Path -LiteralPath $ParentPath -PathType Container)) {
        New-Item -ItemType Directory -Path $ParentPath -Force -ErrorAction Stop | Out-Null
    }
    $name = (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [Guid]::NewGuid().ToString('N')
    $dir = Join-Path $ParentPath $name
    New-Item -ItemType Directory -Path $dir -ErrorAction Stop | Out-Null
    return $dir
}

# ------------------------------------------------- elevator asset loading

function Read-OverlayJsonFile {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$What
    )
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "$What 缺失: $Path"
    }
    try {
        $obj = Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json -ErrorAction Stop
        if ($null -eq $obj) {
            throw 'JSON 内容为空'
        }
        return $obj
    }
    catch {
        throw "$What 解析失败（fail closed）: $Path`n$($_.Exception.Message)"
    }
}

function Get-OverlayVersionManifest {
    # Loads and validates a version manifest from
    # history/<overlay>/versions/<version>/manifest.json plus its canonical
    # object library. Returns the raw manifest object; callers use
    # Get-OverlayCanonicalText to resolve entry bodies.
    # Any inconsistency throws -> caller reports `unsupported`.
    param(
        [Parameter(Mandatory = $true)][string]$Overlay,
        [Parameter(Mandatory = $true)][string]$Version
    )
    if ($Version -notmatch '^\d+\.\d+(?:\.\d+)?$') {
        throw "版本号无效: '$Version'"
    }
    $historyRoot = Get-OverlayHistoryRoot -Overlay $Overlay
    $manifestPath = Join-Path $historyRoot "versions\$Version\manifest.json"
    $manifest = Read-OverlayJsonFile -Path $manifestPath -What "版本清单 ($Overlay $Version)"

    if ([int]$manifest.schema_version -ne 1) {
        throw "版本清单 schema 不受支持: schema_version=$($manifest.schema_version)"
    }
    if ([string]::IsNullOrWhiteSpace([string]$manifest.overlay) -or
        [string]$manifest.overlay -ne $Overlay) {
        throw "版本清单 overlay 不匹配: $($manifest.overlay)"
    }
    if ([string]$manifest.trellisforge_version -ne $Version) {
        throw "版本清单 trellisforge_version=$($manifest.trellisforge_version) != $Version"
    }
    $objectsRoot = Join-Path $historyRoot 'objects'
    if (-not (Test-Path -LiteralPath $objectsRoot -PathType Container)) {
        throw "canonical 对象库缺失: $objectsRoot"
    }

    $seen = @{}
    $files = @()
    foreach ($entry in $manifest.files) {
        $relative = [string]$entry.path
        if ([string]::IsNullOrWhiteSpace($relative)) {
            throw "版本清单包含空路径"
        }
        if ($seen.ContainsKey($relative)) {
            throw "版本清单路径重复: $relative"
        }
        $seen[$relative] = $true
        $ownership = [string]$entry.ownership
        if ($ownership -notin @('managed', 'adoption-baseline')) {
            throw "版本清单所有权不受支持: ownership=$ownership path=$relative"
        }
        $canon = [string]$entry.canonical_sha256
        if ($canon -notmatch '^[0-9a-f]{64}$') {
            throw "版本清单 canonical_sha256 无效: path=$relative"
        }
        $files += [pscustomobject]@{
            Path             = $relative
            Ownership        = $ownership
            CanonicalSha256  = $canon
        }
    }

    return [pscustomobject]@{
        Overlay     = $Overlay
        Version     = $Version
        Files       = $files
        ManifestRaw = $manifest
    }
}

function Get-OverlayCanonicalText {
    # Resolves a manifest entry's canonical object bytes to text.
    # The object path is objects/<canonical_sha256>. Returns UTF-8 text
    # (no BOM) whose LF-normalized hash equals the stored canonical hash.
    param(
        [Parameter(Mandatory = $true)][string]$Overlay,
        [Parameter(Mandatory = $true)][string]$CanonicalSha256
    )
    if ($CanonicalSha256 -notmatch '^[0-9a-f]{64}$') {
        throw "canonical_sha256 无效: $CanonicalSha256"
    }
    $historyRoot = Get-OverlayHistoryRoot -Overlay $Overlay
    $objPath = Join-Path $historyRoot "objects\$CanonicalSha256"
    if (-not (Test-Path -LiteralPath $objPath -PathType Leaf)) {
        throw "canonical 对象缺失: $objPath"
    }
    return Get-OverlayContentText -Path $objPath
}

function Get-OverlayStructuralChain {
    # Loads and validates the adjacent-step structural chain from
    # FromVersion up to ToVersion. The walkable version set is the published
    # manifests under history/<overlay>/versions/; between the source and the
    # target the chain composes every adjacent step file
    # "<left>-to-<right>.json" in order. Each step must match schema 1, its
    # own from/to pair, a whitelisted receipt_transition and whitelisted
    # actions. A missing source/target manifest, reversed or equal versions,
    # a broken/duplicate step or an illegal action/transition throws
    # (unsupported) - the caller never proceeds on a partial chain.
    # Returns: { FromVersion; ToVersion; Steps; Actions; ReceiptTransition }
    #   Steps           - the raw step objects in chain order
    #   Actions         - order-aggregated structural actions from all steps
    #   ReceiptTransition - the step transitions joined for reporting
    param(
        [Parameter(Mandatory = $true)][string]$Overlay,
        [Parameter(Mandatory = $true)][string]$FromVersion,
        [Parameter(Mandatory = $true)][string]$ToVersion
    )
    if ($FromVersion -notmatch '^\d+\.\d+(?:\.\d+)?$' -or
        $ToVersion -notmatch '^\d+\.\d+(?:\.\d+)?$') {
        throw "结构迁移链版本无效: from=$FromVersion to=$ToVersion"
    }
    $historyRoot = Get-OverlayHistoryRoot -Overlay $Overlay
    $versionsDir = Join-Path $historyRoot 'versions'
    if (-not (Test-Path -LiteralPath $versionsDir -PathType Container)) {
        throw "版本清单目录缺失: $versionsDir"
    }
    $manifestedVersions = @(
        Get-ChildItem -LiteralPath $versionsDir -Directory |
            Where-Object {
                $_.Name -match '^\d+\.\d+(?:\.\d+)?$' -and
                (Test-Path -LiteralPath (Join-Path $_.FullName 'manifest.json') -PathType Leaf)
            } |
            ForEach-Object { $_.Name } |
            Sort-Object { [version]$_ }
    )
    if ($manifestedVersions -notcontains $FromVersion) {
        throw "unsupported: 来源版本缺少可校验的版本清单: $FromVersion"
    }
    if ($manifestedVersions -notcontains $ToVersion) {
        throw "unsupported: 目标版本缺少可校验的版本清单: $ToVersion"
    }
    $fromIndex = [Array]::IndexOf($manifestedVersions, $FromVersion)
    $toIndex = [Array]::IndexOf($manifestedVersions, $ToVersion)
    if ($fromIndex -ge $toIndex) {
        throw "unsupported: 版本顺序非法，无法构成结构迁移链: $FromVersion -> $ToVersion"
    }

    $structuralDir = Get-OverlayStructuralDir -Overlay $Overlay
    $allowedActions = @('rename', 'remove', 'receipt')
    $allowedTransitions = @('bootstrap-schema-1', 'preserve-schema-1')
    $steps = @()
    $aggregatedActions = @()
    $transitions = @()
    $seenSteps = @{}
    for ($i = $fromIndex; $i -lt $toIndex; $i++) {
        $left = $manifestedVersions[$i]
        $right = $manifestedVersions[$i + 1]
        $stepKey = "$left->$right"
        if ($seenSteps.ContainsKey($stepKey)) {
            throw "unsupported: 结构迁移链包含重复步骤: $stepKey"
        }
        $seenSteps[$stepKey] = $true
        $stepPath = Join-Path $structuralDir "$left-to-$right.json"
        $step = Read-OverlayJsonFile -Path $stepPath -What "结构迁移步骤 ($stepKey)"
        if ([int]$step.schema_version -ne 1) {
            throw "结构迁移链 schema 不受支持: schema_version=$($step.schema_version)（$stepKey）"
        }
        if ([string]$step.from_version -ne $left -or
            [string]$step.to_version -ne $right) {
            throw "结构迁移链版本不匹配: $stepKey（文件声明 from=$($step.from_version) to=$($step.to_version)）"
        }
        foreach ($action in @($step.actions)) {
            $kind = [string]$action.action
            if ($kind -notin $allowedActions) {
                throw "结构迁移动作不受支持: action=$kind（$stepKey，白名单: $($allowedActions -join ', ')）"
            }
            $aggregatedActions += $action
        }
        $transition = [string]$step.receipt_transition
        if ([string]::IsNullOrWhiteSpace($transition)) {
            throw "结构迁移链缺少 receipt_transition: $stepKey"
        }
        if ($transition -notin $allowedTransitions) {
            throw "unsupported: 收据转换不受支持: receipt_transition=$transition（$stepKey，白名单: $($allowedTransitions -join ', ')）"
        }
        $transitions += $transition
        $steps += $step
    }
    return [pscustomobject]@{
        FromVersion       = $FromVersion
        ToVersion         = $ToVersion
        Steps             = @($steps)
        Actions           = @($aggregatedActions)
        ReceiptTransition = ($transitions -join ' + ')
    }
}

function Assert-OverlayLiveTemplateMatchesManifest {
    # Ensures the live template equals the published target manifest. Each
    # managed entry's canonical object must LF-normalize to the exact live
    # template byte content; any drift fails closed.
    param(
        [Parameter(Mandatory = $true)][string]$Overlay,
        [Parameter(Mandatory = $true)][string]$Version,
        [Parameter(Mandatory = $true)][string]$TemplateRoot,
        [Parameter(Mandatory = $true)][object]$Manifest
    )
    $mismatches = @()
    foreach ($entry in $Manifest.Files) {
        if ($entry.Ownership -ne 'managed') { continue }
        $relative = $entry.Path
        if ($relative -eq 'AGENTS.md.trellisforge-template') {
            # AGENTS.md.trellisforge-template is produced at install time from
            # AGENTS.md.template, not a template source file. Its canonical
            # object is still validated by the object-library consistency check.
            continue
        }
        $liveText = Get-OverlayContentText -Path (Join-Path $TemplateRoot $relative) -AllowMissing
        if ($null -eq $liveText) {
            $mismatches += "$relative (missing from live template)"
            continue
        }
        $canonical = Get-OverlayCanonicalText -Overlay $Overlay -CanonicalSha256 $entry.CanonicalSha256
        if ((Get-OverlayTextHash -Text $liveText -NormalizeLineEndings) -ne
            (Get-OverlayTextHash -Text $canonical -NormalizeLineEndings)) {
            $mismatches += $relative
        }
    }
    if ($mismatches.Count -gt 0) {
        throw "同一版本 live 模板与 manifest 漂移（fail closed）: $($mismatches -join ', ')"
    }
    return $true
}

# ---------------------------------------------------------------- receipts

function Read-OverlayReceipt {
    # Reads .trellis/trellisforge.json. Returns $null when the file is absent,
    # or an object when valid. Throws on malformed or schema-invalid receipts
    # (fail closed).
    param(
        [Parameter(Mandatory = $true)][string]$TargetRoot,
        [string]$ReceiptRelative = '.trellis/trellisforge.json'
    )
    $receiptPath = Assert-OverlaySafeRelative -Relative $ReceiptRelative -TargetRoot $TargetRoot
    if (-not (Test-Path -LiteralPath $receiptPath -PathType Leaf)) {
        return $null
    }
    try {
        $raw = [System.IO.File]::ReadAllText($receiptPath, (Get-OverlayUtf8NoBom))
        $obj = $raw | ConvertFrom-Json -ErrorAction Stop
        if ($null -eq $obj) {
            throw 'JSON 内容为空'
        }
    }
    catch {
        throw "安装收据解析失败（fail closed）: $receiptPath`n$($_.Exception.Message)"
    }
    $hasSchema = Test-OverlayHasProperty -Object $obj -Name 'schema_version'
    $hasVersion = Test-OverlayHasProperty -Object $obj -Name 'trellisforge_version'
    $hasOverlay = Test-OverlayHasProperty -Object $obj -Name 'overlay'
    $hasPrefix = Test-OverlayHasProperty -Object $obj -Name 'project_prefix'
    if (-not $hasSchema -or -not $hasVersion) {
        throw "安装收据缺少必需字段: $receiptPath"
    }
    if ($obj.schema_version -ne 1) {
        throw "安装收据 schema 不受支持: schema_version=$($obj.schema_version)"
    }
    if (-not $hasOverlay -or -not $hasPrefix -or
        [string]::IsNullOrWhiteSpace([string]$obj.overlay) -or
        [string]::IsNullOrWhiteSpace([string]$obj.project_prefix)) {
        throw "安装收据缺少 overlay/project_prefix: $receiptPath"
    }
    return $obj
}

function New-OverlayReceiptPayload {
    # Builds the schema-1 receipt for the given overlay installation.
    # $FileEntries: array of @{ Path; CanonicalSha256; BaselineSha256; InstalledSha256 }
    #   CanonicalSha256 = hash of the pre-render canonical object
    #   BaselineSha256  = hash of the canonical body rendered with project params
    #   InstalledSha256 = hash of the actual content written / read from target
    param(
        [Parameter(Mandatory = $true)][string]$Overlay,
        [Parameter(Mandatory = $true)][string]$ProjectPrefix,
        [Parameter(Mandatory = $true)][string]$ProjectName,
        [object[]]$FileEntries = @()
    )
    $version = Get-OverlayForgeVersion
    $files = @()
    foreach ($entry in $FileEntries) {
        $files += [ordered]@{
            path             = $entry.Path.Replace('\', '/')
            canonical_sha256 = $entry.CanonicalSha256
            baseline_sha256  = $entry.BaselineSha256
            installed_sha256 = $entry.InstalledSha256
        }
    }
    $payload = [ordered]@{
        schema_version       = 1
        trellisforge_version = $version
        overlay              = $Overlay
        project_prefix       = $ProjectPrefix
        project_name         = $ProjectName
        files                = @($files)
    }
    # ConvertTo-Json emits CRLF under Windows PowerShell. Receipts are intended
    # to be committed, so normalize only the newline sequence to LF.
    return (Get-OverlayNormalizedText -Text ($payload | ConvertTo-Json -Depth 5))
}

function Invoke-OverlayThreeWayMerge {
    # Text three-way merge via `git merge-file`. Inputs may be CRLF or LF;
    # the merge runs on LF-normalized text and returns LF-normalized text.
    #
    # Returns: { ExitCode = 0|1|other; MergedText; Error }
    #   ExitCode 0 = clean result; 1 = conflicts (MergedText has markers);
    #   any other value is a tool error and must be treated as `unsupported`.
    param(
        [Parameter(Mandatory = $true)][AllowEmptyString()][string]$OldText,
        [Parameter(Mandatory = $true)][AllowEmptyString()][string]$CurrentText,
        [Parameter(Mandatory = $true)][AllowEmptyString()][string]$NewText
    )
    $tmpRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('trellisforge-merge-' + [Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $tmpRoot -ErrorAction Stop | Out-Null
    try {
        $oldFile = Join-Path $tmpRoot 'base.txt'
        $currentFile = Join-Path $tmpRoot 'current.txt'
        $newFile = Join-Path $tmpRoot 'new.txt'
        $errFile = Join-Path $tmpRoot 'stderr.txt'
        Write-OverlayContentText -Path $oldFile -Content (Get-OverlayNormalizedText -Text $OldText)
        Write-OverlayContentText -Path $currentFile -Content (Get-OverlayNormalizedText -Text $CurrentText)
        Write-OverlayContentText -Path $newFile -Content (Get-OverlayNormalizedText -Text $NewText)

        # NOTE: `git merge-file` WITHOUT -p merges INTO <current-file> in place.
        # PowerShell 5.1 cannot pipe native stdout bytes through redirection
        # without text-mode re-encoding (which corrupts UTF-8), so we let git
        # write the raw result into the temp current file instead of capturing
        # stdout; stderr stays a text-only diagnostic channel.
        & git merge-file -L target -L 'trellisforge-base' -L 'trellisforge-new' $currentFile $oldFile $newFile 2>$errFile
        $exit = $LASTEXITCODE
        $stderr = if (Test-Path -LiteralPath $errFile -PathType Leaf) {
            (Get-Content -LiteralPath $errFile -Raw -ErrorAction SilentlyContinue)
        } else { '' }

        if (Test-Path -LiteralPath $currentFile -PathType Leaf) {
            $merged = Get-OverlayNormalizedText -Text (Get-OverlayContentText -Path $currentFile)
        }
        else {
            $merged = ''
        }
        if ($exit -gt 1) {
            return [pscustomobject]@{
                ExitCode   = $exit
                MergedText = $null
                Error      = $stderr
            }
        }
        return [pscustomobject]@{
            ExitCode   = $exit
            MergedText = $merged
            Error      = $null
        }
    }
    finally {
        if (Test-Path -LiteralPath $tmpRoot) {
            Remove-Item -LiteralPath $tmpRoot -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}

function Invoke-OverlayApply {
    # The single write transaction for both installers and the upgrade apply.
    #
    # $Writes: array of @{ Relative; Content; Action (optional) }.
    # $NewReceiptContent: receipt JSON text to write as the final step, or
    #   '' / $null when no receipt should be created.
    # $BackupEntryName: git-metadata directory used for the backup set.
    # $ManifestExtra: extra fields merged into backup-manifest.json.
    #
    # Before writing anything, existing target files (and the existing receipt)
    # are copied into a fresh <BackupEntryName>/<ts>-<GUID>/ directory with
    # their SHA-256 recorded in backup-manifest.json. Any failure restores the
    # backups, removes newly created files, restores/removes the receipt, and
    # rethrows with the write error plus rollout status.
    param(
        [Parameter(Mandatory = $true)][string]$TargetRoot,
        [Parameter(Mandatory = $true)][object[]]$Writes,
        [string]$NewReceiptContent = $null,
        [string]$ReceiptRelative = '.trellis/trellisforge.json',
        [string]$BackupEntryName = 'trellisforge-backup',
        [hashtable]$ManifestExtra = $null
    )

    $plan = @()
    foreach ($item in $Writes) {
        $relative = [string]$item.Relative
        $target = Assert-OverlaySafeRelative -Relative $relative -TargetRoot $TargetRoot
        $existed = Test-Path -LiteralPath $target -PathType Leaf
        $wasDir = Test-Path -LiteralPath $target -PathType Container
        if ($wasDir) {
            throw "目标路径是目录，无法写入文件: $target"
        }
        $action = 'overwrite'
        if (Test-OverlayHasProperty -Object $item -Name 'Action' -and -not [string]::IsNullOrWhiteSpace([string]$item.Action)) {
            $action = [string]$item.Action
        }
        $plan += [pscustomobject]@{
            Relative = $relative
            Target   = $target
            Content  = [string]$item.Content
            Action   = $action
            Existed  = $existed
        }
    }

    $receiptTarget = Assert-OverlaySafeRelative -Relative $ReceiptRelative -TargetRoot $TargetRoot
    $receiptExisted = Test-Path -LiteralPath $receiptTarget -PathType Leaf

    $backupRoot = $null
    $addedPaths = @()
    try {
        $backupParent = Get-OverlayGitMetadataDir -TargetRoot $TargetRoot -GitPathEntry $BackupEntryName
        $backupRoot = New-OverlayUniqueDir -ParentPath $backupParent
        $backupEntries = @()
        foreach ($item in $plan) {
            if ($item.Existed) {
                $backupFile = Join-Path $backupRoot $item.Relative
                New-Item -ItemType Directory -Path (Split-Path -Parent $backupFile) -Force -ErrorAction Stop | Out-Null
                Copy-Item -LiteralPath $item.Target -Destination $backupFile -ErrorAction Stop
                $shaOld = Get-OverlayTextHash -Text (Get-OverlayContentText -Path $item.Target) -NormalizeLineEndings
                $backupEntries += [ordered]@{
                    path   = $item.Relative.Replace('\', '/')
                    sha256 = $shaOld
                    action = $item.Action
                }
            }
            else {
                $addedPaths += $item.Relative.Replace('\', '/')
            }
        }

        $receiptEntry = $null
        if ($receiptExisted) {
            $backupReceipt = Join-Path $backupRoot $ReceiptRelative
            New-Item -ItemType Directory -Path (Split-Path -Parent $backupReceipt) -Force -ErrorAction Stop | Out-Null
            Copy-Item -LiteralPath $receiptTarget -Destination $backupReceipt -ErrorAction Stop
            $receiptEntry = [ordered]@{
                path   = $ReceiptRelative.Replace('\', '/')
                sha256 = Get-OverlayTextHash -Text (Get-OverlayContentText -Path $receiptTarget) -NormalizeLineEndings
            }
        }

        $manifestJson = [ordered]@{
            schema_version = 1
            created_at     = (Get-Date).ToString('o')
        }
        if ($ManifestExtra) {
            foreach ($key in $ManifestExtra.Keys) {
                $manifestJson[$key] = $ManifestExtra[$key]
            }
        }
        $manifestJson['added'] = @($addedPaths)
        $manifestJson['receipt'] = $receiptEntry
        $manifestJson['files'] = @($backupEntries)
        $manifestPath = Join-Path $backupRoot 'backup-manifest.json'
        Write-OverlayContentText -Path $manifestPath -Content ($manifestJson | ConvertTo-Json -Depth 6)

        foreach ($item in $plan) {
            $parent = Split-Path -Parent $item.Target
            New-Item -ItemType Directory -Path $parent -Force -ErrorAction Stop | Out-Null
            Write-OverlayContentText -Path $item.Target -Content $item.Content
        }

        if ($NewReceiptContent) {
            $parent = Split-Path -Parent $receiptTarget
            New-Item -ItemType Directory -Path $parent -Force -ErrorAction Stop | Out-Null
            Write-OverlayContentText -Path $receiptTarget -Content $NewReceiptContent
        }
    }
    catch {
        $rollbackErrors = @()
        foreach ($item in $plan) {
            try {
                if ($item.Existed -and $null -ne $backupRoot) {
                    $backupFile = Join-Path $backupRoot $item.Relative
                    if (Test-Path -LiteralPath $backupFile -PathType Leaf) {
                        Copy-Item -LiteralPath $backupFile -Destination $item.Target -Force -ErrorAction Stop
                    }
                }
                elseif (-not $item.Existed) {
                    if (Test-Path -LiteralPath $item.Target -PathType Leaf) {
                        Remove-Item -LiteralPath $item.Target -Force -ErrorAction SilentlyContinue
                    }
                }
            }
            catch {
                $rollbackErrors += "恢复 $($item.Relative) 失败: $($_.Exception.Message)"
            }
        }
        try {
            if ($receiptExisted -and $null -ne $backupRoot) {
                $backupReceipt = Join-Path $backupRoot $ReceiptRelative
                if (Test-Path -LiteralPath $backupReceipt -PathType Leaf) {
                    Copy-Item -LiteralPath $backupReceipt -Destination $receiptTarget -Force -ErrorAction Stop
                }
            }
            elseif (-not $receiptExisted) {
                if (Test-Path -LiteralPath $receiptTarget -PathType Leaf) {
                    Remove-Item -LiteralPath $receiptTarget -Force -ErrorAction SilentlyContinue
                }
            }
        }
        catch {
            $rollbackErrors += "恢复安装收据失败: $($_.Exception.Message)"
        }
        $rollbackNote = ''
        if ($rollbackErrors.Count -gt 0) {
            $rollbackNote = " 回滚中另外出现错误:`n" + (($rollbackErrors | ForEach-Object { "  - $_" }) -join "`n")
        }
        if ($null -ne $backupRoot) {
            throw "覆盖层写入失败，已回滚。原始错误: $($_.Exception.Message) 备份: $backupRoot$rollbackNote"
        }
        throw "覆盖层写入失败，已回滚。原始错误: $($_.Exception.Message)$rollbackNote"
    }

    return [pscustomobject]@{
        BackupRoot         = $backupRoot
        Written            = @($plan | ForEach-Object { $_.Target })
        ReceiptWritten     = [bool]$NewReceiptContent
        BackupManifestPath = $(if ($null -ne $backupRoot) { Join-Path $backupRoot 'backup-manifest.json' } else { $null })
    }
}

Export-ModuleMember -Function @(
    'Get-OverlayForgeVersion',
    'Get-OverlayHistoryRoot',
    'Get-OverlayStructuralDir',
    'Assert-OverlayTargetRoot',
    'Assert-OverlayProjectParams',
    'Assert-OverlaySafeRelative',
    'Get-OverlayTemplateCacheFiles',
    'Get-OverlayRenderRelative',
    'Get-OverlayRenderContent',
    'Get-OverlayTextHash',
    'Get-OverlayFileHash',
    'Get-OverlayGitMetadataDir',
    'New-OverlayUniqueDir',
    'Read-OverlayJsonFile',
    'Get-OverlayVersionManifest',
    'Get-OverlayCanonicalText',
    'Get-OverlayStructuralChain',
    'Assert-OverlayLiveTemplateMatchesManifest',
    'Read-OverlayReceipt',
    'New-OverlayReceiptPayload',
    'Invoke-OverlayThreeWayMerge',
    'Invoke-OverlayApply',
    'Get-OverlayNormalizedText',
    'Test-OverlayTextUsesCrLf',
    'ConvertTo-OverlayLineEndings',
    'Get-OverlayContentText',
    'Write-OverlayContentText'
)
