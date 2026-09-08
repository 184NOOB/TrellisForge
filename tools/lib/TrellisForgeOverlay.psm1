# TrellisForgeOverlay.psm1
# Shared safety/mechanism layer used by BOTH first-time installation
# (install-embedded-c-overlay.ps1) and 1.0->1.1 upgrades
# (update-embedded-c-overlay.ps1).
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
# The module keeps a deliberately narrow export surface. Entry scripts own
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

function Resolve-OverlayAssetPath {
    # Resolves a manifest-relative asset path (old/new) against a base
    # directory. Both baseline/ and new/ are frozen snapshot trees that live
    # inside the migration dir, so the manifest refs stay relative to it (the
    # `new` field points at new/, NOT at the live template root). Parent
    # traversal remains allowed only for robustness; we reject absolute paths,
    # glob characters and control characters. The target-write boundary is
    # enforced separately against the real TargetRoot.
    param(
        [Parameter(Mandatory = $true)][AllowNull()][string]$Relative,
        [Parameter(Mandatory = $true)][string]$BaseDir
    )
    if ([string]::IsNullOrEmpty($Relative)) {
        throw "空相对路径"
    }
    if ([System.IO.Path]::IsPathRooted(($Relative.Replace('/', [System.IO.Path]::DirectorySeparatorChar)))) {
        throw "资产路径不允许为绝对路径: $Relative"
    }
    if ($Relative.IndexOfAny([char[]]@("`r", "`n", "`0", "`t")) -ge 0) {
        throw "资产路径包含换行/空字符: $Relative"
    }
    if ($Relative.IndexOfAny([char[]]@('*', '?', '[')) -ge 0) {
        throw "资产路径包含通配符: $Relative"
    }
    $baseFull = [System.IO.Path]::GetFullPath($BaseDir)
    $full = [System.IO.Path]::GetFullPath((Join-Path $baseFull ($Relative.Replace('/', [System.IO.Path]::DirectorySeparatorChar))))
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

# ------------------------------------------------------------- public API

function Get-OverlayForgeVersion {
    # TrellisForge version fact source: repo-root VERSION file.
    # module lives at <repo>\tools\lib\TrellisForgeOverlay.psm1, so the
    # release root (with VERSION) is two levels up.
    $releaseRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
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
    # Builds the receipt payload for the given overlay installation.
    # $FileEntries: array of @{ Path; TemplateSha256; InstalledSha256 }
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
            template_sha256  = $entry.TemplateSha256
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
    return ($payload | ConvertTo-Json -Depth 5)
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
        & git merge-file -L target -L 'trellisforge-base(1.0)' -L 'trellisforge-new(1.1)' $currentFile $oldFile $newFile 2>$errFile
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

function Get-OverlayMigrationManifest {
    # Loads and validates a versioned migration manifest plus its assets.
    # Renders every old/new path, verifies LF-normalized SHA-256 against the
    # manifest, and returns a normal form:
    #   { Manifest; Paths = [ @{ Action; Relative; RenderedPath; OldText; NewText;
    #                            OldSha256; NewSha256 } ] }
    # Any inconsistency makes this throw -> caller reports `unsupported`.
    param(
        [Parameter(Mandatory = $true)][string]$MigrationDir,
        [Parameter(Mandatory = $true)][string]$ProjectPrefix,
        [Parameter(Mandatory = $true)][string]$ProjectName
    )
    $migrationFile = Join-Path $MigrationDir 'migration.json'
    if (-not (Test-Path -LiteralPath $migrationFile -PathType Leaf)) {
        throw "迁移清单不存在: $migrationFile"
    }
    $manifest = $null
    try {
        $manifest = Get-Content -LiteralPath $migrationFile -Raw -Encoding UTF8 | ConvertFrom-Json -ErrorAction Stop
        if ($null -eq $manifest) { throw 'JSON 内容为空' }
    }
    catch {
        throw "迁移清单解析失败（unsupported）: $migrationFile`n$($_.Exception.Message)"
    }
    if (-not (Test-OverlayHasProperty -Object $manifest -Name 'schema_version') -or $manifest.schema_version -ne 1) {
        throw "迁移清单 schema 不受支持"
    }
    if (-not (Test-OverlayHasProperty -Object $manifest -Name 'overlay') -or
        -not (Test-OverlayHasProperty -Object $manifest -Name 'from_version') -or
        -not (Test-OverlayHasProperty -Object $manifest -Name 'to_version') -or
        [string]::IsNullOrWhiteSpace([string]$manifest.overlay) -or
        [string]::IsNullOrWhiteSpace([string]$manifest.from_version) -or
        [string]::IsNullOrWhiteSpace([string]$manifest.to_version)) {
        throw "迁移清单缺少 overlay/from_version/to_version"
    }

    $seen = @{}
    $results = @()
    foreach ($entry in $manifest.paths) {
        $relative = [string]$entry.path
        if ([string]::IsNullOrWhiteSpace($relative)) {
            throw "迁移清单包含空路径"
        }
        if ($seen.ContainsKey($relative)) {
            throw "迁移清单路径重复: $relative"
        }
        $seen[$relative] = $true
        $renderedRelative = Get-OverlayRenderRelative -Relative $relative -ProjectPrefix $ProjectPrefix
        $action = [string]$entry.action
        if ($action -notin @('merge', 'adopt', 'add')) {
            throw "迁移清单动作不受支持: action=$action path=$relative"
        }
        $oldText = $null
        $oldSha = $null
        $hasOld = Test-OverlayHasProperty -Object $entry -Name 'old'
        if ($hasOld -and -not [string]::IsNullOrWhiteSpace([string]$entry.old)) {
            $oldRel = [string]$entry.old
            $oldPath = Resolve-OverlayAssetPath -Relative $oldRel -BaseDir $MigrationDir
            if (-not (Test-Path -LiteralPath $oldPath -PathType Leaf)) {
                throw "迁移旧基线缺失: $oldRel（${relative}）"
            }
            # Manifest hashes are computed over the RAW stored asset (CRLF->LF
            # only); the project placeholders are applied afterwards for the
            # three-way merge so the manifest stays independent of the runtime
            # ProjectPrefix/ProjectName.
            $rawOld = Get-OverlayContentText -Path $oldPath
            $oldText = Get-OverlayRenderContent -Content $rawOld -ProjectPrefix $ProjectPrefix -ProjectName $ProjectName
            $oldSha = Get-OverlayTextHash -Text $rawOld -NormalizeLineEndings
            if (-not (Test-OverlayHasProperty -Object $entry -Name 'old_sha256') -or $oldSha -ne [string]$entry.old_sha256) {
                throw "迁移旧基线内容哈希不符（unsupported）: $relative"
            }
        }
        $newRel = [string]$entry.new
        if ([string]::IsNullOrWhiteSpace($newRel)) {
            throw "迁移清单缺少 new 引用: $relative"
        }
        $newPath = Resolve-OverlayAssetPath -Relative $newRel -BaseDir $MigrationDir
        if (-not (Test-Path -LiteralPath $newPath -PathType Leaf)) {
            throw "迁移新模板缺失: $newRel（${relative}）"
        }
        $rawNew = Get-OverlayContentText -Path $newPath
        $newText = Get-OverlayRenderContent -Content $rawNew -ProjectPrefix $ProjectPrefix -ProjectName $ProjectName
        $newSha = Get-OverlayTextHash -Text $rawNew -NormalizeLineEndings
        if (-not (Test-OverlayHasProperty -Object $entry -Name 'new_sha256') -or $newSha -ne [string]$entry.new_sha256) {
            throw "迁移新模板内容哈希不符（unsupported）: $relative"
        }

        $results += [pscustomobject]@{
            Action         = $action
            Relative       = $relative
            RenderedPath   = $renderedRelative
            OldText        = $oldText
            NewText        = $newText
            OldSha256      = $oldSha
            NewSha256      = $newSha
        }
    }
    return [pscustomobject]@{
        Manifest     = $manifest
        Paths        = $results
        MigrationDir = $MigrationDir
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
    'Read-OverlayReceipt',
    'New-OverlayReceiptPayload',
    'Invoke-OverlayThreeWayMerge',
    'Get-OverlayMigrationManifest',
    'Invoke-OverlayApply',
    'Get-OverlayNormalizedText',
    'Test-OverlayTextUsesCrLf',
    'ConvertTo-OverlayLineEndings',
    'Get-OverlayContentText',
    'Write-OverlayContentText'
)