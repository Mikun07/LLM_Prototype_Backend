[CmdletBinding(SupportsShouldProcess = $true)]
param(
  [string]$Version,
  [switch]$Latest,
  [string]$Branch,
  [switch]$Fetch,
  [switch]$CleanIgnored,
  [switch]$Install
)

$ErrorActionPreference = 'Stop'

function Stop-WithMessage {
  param([string]$Message)
  Write-Error $Message
  exit 1
}

function Get-AvailableVersionTags {
  @(git tag --list 'v*' | Sort-Object)
}

function Resolve-VersionTag {
  param([string]$RequestedVersion)

  $raw = $RequestedVersion.Trim()
  $withoutPrefix = if ($raw.StartsWith('v')) { $raw.Substring(1) } else { $raw }
  $candidates = New-Object System.Collections.Generic.List[string]

  if ($raw.StartsWith('v')) {
    $candidates.Add($raw)
  } else {
    $candidates.Add("v$raw")
  }

  if ($withoutPrefix -match '^\d+\.\d+$') {
    $candidates.Add("v$withoutPrefix.0")
  }

  if ($withoutPrefix -match '^\d+$') {
    $candidates.Add("v$withoutPrefix.0.0")
  }

  $availableTags = Get-AvailableVersionTags

  foreach ($candidate in ($candidates | Select-Object -Unique)) {
    if ($availableTags -contains $candidate) {
      return $candidate
    }
  }

  $availableText = if ($availableTags.Count -gt 0) {
    $availableTags -join ', '
  } else {
    'no version tags found'
  }

  Stop-WithMessage "Version '$RequestedVersion' was not found. Available versions: $availableText"
}

if ([string]::IsNullOrWhiteSpace($Version) -and -not $Latest) {
  Stop-WithMessage 'Provide -Version vX.Y.Z, -Version vX.Y, -Version X.Y, or -Latest.'
}

if (-not [string]::IsNullOrWhiteSpace($Version) -and $Latest) {
  Stop-WithMessage 'Use either -Version or -Latest, not both.'
}

$root = git rev-parse --show-toplevel
Set-Location $root

$dirty = git status --porcelain
if ($dirty) {
  Stop-WithMessage 'Working tree has uncommitted tracked or untracked changes. Commit, stash, or remove them before switching versions.'
}

if ($Fetch) {
  git fetch origin --tags --prune
}

if ($Latest) {
  if ($PSCmdlet.ShouldProcess('main', 'switch to latest branch')) {
    git switch main
  }
} else {
  $resolvedVersion = Resolve-VersionTag -RequestedVersion $Version

  if ([string]::IsNullOrWhiteSpace($Branch)) {
    if ($PSCmdlet.ShouldProcess($resolvedVersion, 'switch to version tag in detached HEAD')) {
      git switch --detach $resolvedVersion
    }
  } else {
    if ($PSCmdlet.ShouldProcess($Branch, "create branch from $resolvedVersion")) {
      git switch -c $Branch $resolvedVersion
    }
  }
}

if ($CleanIgnored) {
  if ($PSCmdlet.ShouldProcess('ignored generated files', 'remove with git clean -fdX')) {
    git clean -fdX
  }
}

if ($Install) {
  if ($PSCmdlet.ShouldProcess('dependencies', 'install with python -m pip install -r requirements.txt')) {
    python -m pip install -r requirements.txt
  }
}

git describe --tags --always --dirty
