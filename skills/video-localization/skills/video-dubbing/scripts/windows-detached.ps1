# windows-detached.ps1
#
# Template for launching video-dubbing's long TTS job (dub_audio.py with
# VoxCPM2 on CPU) detached on Windows so it survives shell timeouts
# (~10 min in some agent environments). PowerShell's Start-Process is the
# reliable form — the `start /b` bat trick breaks under Git Bash path
# translation and the child doesn't always detach cleanly from the parent.
#
# Fill in the variables below, then run:
#     powershell -ExecutionPolicy Bypass -File windows-detached.ps1
# The launch returns immediately. Monitor with `Get-Process python` / the log.
#
# Typical use: dub_audio.py with VoxCPM2 — slow on CPU, near-realtime per cue
# but a 30-min video has hundreds of cues so the total run is hours.

# ---- fill these in ----
# Use uv to run python inside the shared video-tools venv (preferred), or a
# direct python.exe path. When using uv, set $Uv = "uv" and leave $Python = "".
$Uv          = "uv"
$Python      = ""                              # e.g. "C:\Users\...\.venvs\Scripts\python.exe"

# The shared video-tools venv (same one video-subtitle uses for whisperX).
# Set this so uv runs in the right environment. If using $Python directly,
# point it at the venv's python.exe and ignore $Venv.
$Venv        = "C:\Users\$env:USERNAME\.venvs\video-tools"

$Script      = "C:\path\to\video-dubbing-skill\skills\video-dubbing\scripts\dub_audio.py"
$Args        = @(
    "C:\path\to\<output-root>\transcript\<name>.zh.srt",
    "C:\path\to\<output-root>\dubbed\_reference\ref.wav",
    "C:\path\to\<output-root>\dubbed\_reference\ref.txt",
    "C:\path\to\<output-root>\dubbed",
    "--tts-backend", "voxcpm2"
)
$EnvVars     = @{
    # VoxCPM2 doesn't need PYTHONPATH (it's a pip package). Keep this empty
    # unless you switched to the IndexTTS2 backend, in which case set:
    #   PYTHONPATH = "C:\path\to\index-tts"
    #   INDEXTTS_DIR = "C:\path\to\index-tts"
}
$LogFile     = "C:\path\to\<output-root>\dubbed\dub.log"
$ErrLogFile  = "C:\path\to\<output-root>\dubbed\dub.err.log"
# -----------------------

# Ensure log directory exists before Start-Process tries to write to it.
$logDir = Split-Path $LogFile -Parent
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }

# Build the command. uv run python ... — or direct python.exe if $Uv is empty.
if ($Uv) {
    $cmd = $Uv
    $cmdArgs = @("run", "--python", $Venv, "python", $Script) + $Args
} else {
    $cmd = $Python
    $cmdArgs = @($Script) + $Args
}

# Set env vars for the child process.
foreach ($k in $EnvVars.Keys) { Set-Item -Path "Env:$k" -Value $EnvVars[$k] }

Start-Process -FilePath $cmd `
              -ArgumentList $cmdArgs `
              -WorkingDirectory $Venv `
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
