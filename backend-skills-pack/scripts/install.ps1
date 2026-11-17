<#
Install the backend skills pack by COPYING (never symlinking) its skills and agents.
Windows PowerShell 5.1 port of scripts/install.sh, same behaviour.

Usage: powershell -ExecutionPolicy Bypass -File scripts\install.ps1 [-Project [DIR] | -User] [-Apply]
  -Project DIR  install into DIR\.claude\ (default: .\.claude\ of the current folder)
  -User         install into ~\.claude\ (every project on this machine)
  -Apply        really copy. Without it, this is a dry run that only prints the plan.
What is copied: skills\<name>\ -> <target>\skills\<name>\, agents\*.md -> <target>\agents\.
Never copied: _work\, _quarantine\, tests\, scripts\, __pycache__\.
A skill or agent that already exists and differs is MOVED to
<target>\.backend-skills-pack-backup\<timestamp>\ first, so nothing is lost.
Undo: delete the installed names (listed in <target>\.backend-skills-pack-installed.txt)
and move the backup folders back. No network, no hooks, no settings changes.
#>
param(
    [string]$Project = "",
    [switch]$User,
    [switch]$Apply
)
$ErrorActionPreference = "Stop"

$Pack = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ($User) {
    $Target = Join-Path $HOME ".claude"
} elseif ($Project -ne "") {
    $Target = Join-Path (Resolve-Path $Project).Path ".claude"
} else {
    $Target = Join-Path (Get-Location).Path ".claude"
}
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$Backup = Join-Path $Target ".backend-skills-pack-backup\$Stamp"
$List = Join-Path $Target ".backend-skills-pack-installed.txt"
$Counts = @{ NEW = 0; SAME = 0; CHANGED = 0 }

function Get-TreeHashes([string]$Root) {
    # Relative path -> SHA256 for every file under Root, ignoring __pycache__.
    $map = @{}
    if (Test-Path -LiteralPath $Root -PathType Leaf) {
        $map["."] = (Get-FileHash -LiteralPath $Root -Algorithm SHA256).Hash
        return $map
    }
    Get-ChildItem -LiteralPath $Root -Recurse -File -Force |
        Where-Object { $_.FullName -notmatch '[\\/]__pycache__[\\/]' } |
        ForEach-Object {
            $rel = $_.FullName.Substring($Root.Length).TrimStart('\', '/')
            $map[$rel] = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
        }
    return $map
}

function Test-Same([string]$Src, [string]$Dest) {
    $a = Get-TreeHashes $Src
    $b = Get-TreeHashes $Dest
    if ($a.Count -ne $b.Count) { return $false }
    foreach ($k in $a.Keys) {
        if (-not $b.ContainsKey($k) -or $b[$k] -ne $a[$k]) { return $false }
    }
    return $true
}

function Copy-Skill([string]$Src, [string]$Dest) {
    # Real copy (no links), skipping __pycache__.
    New-Item -ItemType Directory -Force -Path $Dest | Out-Null
    Get-ChildItem -LiteralPath $Src -Recurse -Force |
        Where-Object { $_.FullName -notmatch '[\\/]__pycache__([\\/]|$)' } |
        ForEach-Object {
            $rel = $_.FullName.Substring($Src.Length).TrimStart('\', '/')
            $to = Join-Path $Dest $rel
            if ($_.PSIsContainer) { New-Item -ItemType Directory -Force -Path $to | Out-Null }
            else { Copy-Item -LiteralPath $_.FullName -Destination $to -Force }
        }
}

function Invoke-Plan([string]$Kind, [string]$Name, [string]$Src, [string]$Dest) {
    if (-not (Test-Path -LiteralPath $Dest)) { $state = "NEW" }
    elseif (Test-Same $Src $Dest) { $state = "SAME" }
    else { $state = "CHANGED" }
    $Counts[$state]++
    "{0,-8} {1,-6} {2}" -f $state, $Kind, $Name
    if (-not $Apply) { return }
    if ($state -eq "CHANGED") {
        $bk = Join-Path $Backup $Kind
        New-Item -ItemType Directory -Force -Path $bk | Out-Null
        Move-Item -LiteralPath $Dest -Destination $bk
    }
    if ($state -ne "SAME") {
        if ($Kind -eq "skill") { Copy-Skill $Src $Dest }
        else {
            New-Item -ItemType Directory -Force -Path (Split-Path $Dest) | Out-Null
            Copy-Item -LiteralPath $Src -Destination $Dest -Force
        }
    }
    Add-Content -LiteralPath $List -Value "$Kind $Name" -Encoding UTF8
}

"pack:   $Pack"
"target: $Target"
if ($Apply) {
    New-Item -ItemType Directory -Force -Path $Target | Out-Null
    Set-Content -LiteralPath $List -Value $null -Encoding UTF8
} else {
    "mode:   DRY RUN (nothing is written; add -Apply)"
}
Get-ChildItem -LiteralPath (Join-Path $Pack "skills") -Directory | Sort-Object Name | ForEach-Object {
    Invoke-Plan "skill" $_.Name $_.FullName (Join-Path $Target "skills\$($_.Name)")
}
Get-ChildItem -LiteralPath (Join-Path $Pack "agents") -Filter *.md -File | Sort-Object Name | ForEach-Object {
    Invoke-Plan "agent" $_.Name $_.FullName (Join-Path $Target "agents\$($_.Name)")
}
"new: $($Counts.NEW)  same: $($Counts.SAME)  changed: $($Counts.CHANGED)"
if ($Apply) {
    "installed list: $List"
    if ($Counts.CHANGED -gt 0) { "replaced copies were moved to: $Backup" }
    "Start a new Claude Code session (or /clear) to load them."
}
