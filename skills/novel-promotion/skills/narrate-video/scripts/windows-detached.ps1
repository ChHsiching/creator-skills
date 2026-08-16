# windows-detached.ps1
#
# Template for launching narrate-video's long jobs (IndexTTS2 synthesis, ffmpeg
# burn) detached on Windows so they survive shell timeouts (~10 min in some
# agent environments). PowerShell's Start-Process is the reliable form — the
# `start /b` bat trick breaks under Git Bash path translation and the child
# doesn't always detach cleanly from the parent shell.
#
# Fill in the variables below, then run:
#     powershell -ExecutionPolicy Bypass -File windows-detached.ps1
# The launch returns immediately. Monitor with `Get-Process python` / the log.
#
# Two typical uses:
#   1. gen_audio.py (IndexTTS2 sentence synthesis) — slow, ~4 min per 30s audio
#   2. ffmpeg burn-in for long videos (15+ min) — slow encode

# ---- fill these in ----
# Use uv to run python inside the IndexTTS2 venv (preferred), or a direct
# python.exe path. When using uv, set $Uv = "uv" and leave $Python = "".
$Uv          = "uv"
$Python      = ""                              # e.g. "C:\path\to\.venv\Scripts\python.exe"

$WorkDir     = "C:\path\to\index-tts"          # IndexTTS2 install dir (has checkpoints/)
$Script      = "C:\path\to\narrate-video-skill\scripts\gen_audio.py"
$Args        = @(
    "C:\path\to\video-subdir\script.txt",
    "C:\path\to\narrate-video-skill\voices\yunxi-male-fast.mp3",
    "C:\path\to\video-subdir\output",
    "--tempo", "1.15",
    "--emo-alpha", "0.6",
    "--indextts-dir", "C:\path\to\index-tts"
)
$EnvVars     = @{
    PYTHONPATH = $WorkDir                       # so indextts.* modules resolve
}
$LogFile     = "C:\path\to\video-subdir\output\_segments\gen_audio.log"
$ErrLogFile  = "C:\path\to\video-subdir\output\_segments\gen_audio.err.log"
# -----------------------

# Ensure log directory exists before Start-Process tries to write to it.
$logDir = Split-Path $LogFile -Parent
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }

# Build the command. uv run python ... — or direct python.exe if $Uv is empty.
if ($Uv) {
    $cmd = $Uv
    $cmdArgs = @("run", "python", $Script) + $Args
} else {
    $cmd = $Python
    $cmdArgs = @($Script) + $Args
}

# Set env vars for the child process.
foreach ($k in $EnvVars.Keys) { Set-Item -Path "Env:$k" -Value $EnvVars[$k] }

Start-Process -FilePath $cmd `
              -ArgumentList $cmdArgs `
              -WorkingDirectory $WorkDir `
              -RedirectStandardOutput $LogFile `
              -RedirectStandardError $ErrLogFile `
              -WindowStyle Hidden

# Give it a moment, then confirm it's alive and writing.
Start-Sleep -Seconds 15
$proc = Get-Process -Name python -ErrorAction SilentlyContinue
if ($proc) {
    $size = if (Test-Path $LogFile) { (Get-Item $LogFile).Length } else { 0 }
    Write-Host "detached OK: PID $($proc.Id -join ', '), log $size bytes"
} else {
    Write-Host "WARN: no python process after 15s — check $ErrLogFile"
}
