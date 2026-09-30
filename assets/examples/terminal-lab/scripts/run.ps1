#requires -Version 7.0
param([Parameter(Mandatory)][string]$Label, [switch]$Fail)
$ErrorActionPreference = 'Stop'
# PowerShell 的错误偏好不能代替外部程序的退出码检查。
$PSNativeCommandUseErrorActionPreference = $false
$root = Split-Path -Parent $PSScriptRoot
$null = Get-Command python -ErrorAction Stop
Push-Location -LiteralPath $root
try {
    $null = New-Item -ItemType Directory -Path logs -Force
    $runId = 'demo-' + [DateTimeOffset]::UtcNow.ToString('yyyyMMddTHHmmss') + '-' + [guid]::NewGuid().ToString('N')
    $log = Join-Path $root "logs/$runId.log"
    # CreateNew 即使碰撞也不会覆盖既有日志。
    $stream = [IO.File]::Open($log, [IO.FileMode]::CreateNew)
    $stream.Dispose()
    @("run_id=$runId", 'case_id=demo-v1',
      "started_at=$([DateTimeOffset]::UtcNow.ToString('o'))",
      'phase=sample', 'pair=1', 'order=1') | Set-Content -LiteralPath $log -Encoding utf8
    $demoArgs = @('scripts/demo.py', '--label', $Label)
    if ($Fail) { $demoArgs += '--fail' }
    & python @demoArgs 2>&1 | Out-File -LiteralPath $log -Append -Encoding utf8
    $programRc = $LASTEXITCODE
    "exit_code=$programRc" | Add-Content -LiteralPath $log -Encoding utf8
    Get-Content -LiteralPath $log -Encoding utf8
    exit $programRc
} finally {
    Pop-Location
}
