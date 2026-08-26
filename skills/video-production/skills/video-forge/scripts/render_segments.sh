#!/bin/bash
# Segmented parallel render driver for Remotion final renders, with the
# session-proven safeguards baked in:
#   - startup orphan-renderer cleanup (killed runs starve the queue computation)
#   - frame-exact segments, stream-copy concat (zero quality loss)
#   - skip-existing resume (a crash costs only the in-flight segment)
#   - staggered queue starts (process-spawn spikes collide otherwise)
#   - per-segment retry (transient ffmpeg spawn failures happen under load)
#   - moov integrity check BEFORE concat (killed segments never join the master)
#
# Usage:
#   render_segments.sh <entry.ts(x)> <CompositionId> <total-frames> <out-mp4> \
#                      [--segments N] [--queues N] [--concurrency N] [--queue-gb N]
#                      [-- extra render args, e.g. --scale=2 --props='{"x":1}']
set -eu
ENTRY="${1:?entry}"; COMP="${2:?composition id}"; TOTAL="${3:?total frames}"; OUT="${4:?out.mp4}"
shift 4
SEGMENTS=12; QUEUES=auto; CONCURRENCY=8; QUEUE_GB=7
while [ $# -gt 0 ]; do
  case "$1" in
    --segments) SEGMENTS="$2"; shift 2 ;;
    --queues) QUEUES="$2"; shift 2 ;;  # or auto: computed from measured cores+free RAM
    --concurrency) CONCURRENCY="$2"; shift 2 ;;
    --queue-gb) QUEUE_GB="$2"; shift 2 ;;  # GB per queue assumed by auto (7 ≈ a 4K instance; 1080p runs are smaller)
    --) shift; break ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done
EXTRA="$*"
# --queue-gb guard: empty/non-numeric/0 would zero-divide the auto computation below;
# 10# normalizes leading zeros, which $((...)) would otherwise read as octal.
case $QUEUE_GB in ''|*[!0-9]*) QUEUE_GB=7 ;; *) QUEUE_GB=$((10#$QUEUE_GB)) ;; esac
[ "$QUEUE_GB" -eq 0 ] && QUEUE_GB=7
# Orphan renderer cleanup — a killed run leaves chrome-headless-shell (Remotion's own
# worker, never the user's browser) and ffmpeg squatting GBs of RAM, which starves the
# free-RAM queue computation right below. Kill the shells outright; ffmpeg may be a
# legitimate user encode, so warn and let the operator decide. A concurrently running
# Remotion render shares this process name — confirm none is live before launching.
if command -v powershell >/dev/null 2>&1; then
  ORPHANS=$(powershell -NoProfile -Command "(Get-Process chrome-headless-shell -ErrorAction SilentlyContinue).Count" 2>/dev/null | tr -d '\r')
  if [ -n "$ORPHANS" ] && [ "$ORPHANS" -gt 0 ] 2>/dev/null; then
    powershell -NoProfile -Command "Get-Process chrome-headless-shell -ErrorAction SilentlyContinue | Stop-Process -Force" 2>/dev/null \
      && echo "cleaned $ORPHANS orphan chrome-headless-shell process(es)" \
      || echo "warning: orphan cleanup failed" >&2
  fi
  FFCNT=$(powershell -NoProfile -Command "(Get-Process ffmpeg -ErrorAction SilentlyContinue).Count" 2>/dev/null | tr -d '\r')
  if [ -n "$FFCNT" ] && [ "$FFCNT" -gt 0 ] 2>/dev/null; then
    echo "WARNING: $FFCNT ffmpeg process(es) running — leftover encodes squat RAM; kill them (or confirm they are wanted) if free RAM looks low"
  fi
fi
if [ "$QUEUES" = "auto" ]; then
  CORES=$(python -c "import os; print(os.cpu_count() or 4)")
  FREE_GB=$(python -c "import ctypes" 2>/dev/null && powershell -NoProfile -Command "[math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB)" 2>/dev/null || echo 8)
  QUEUES=$(( CORES / 4 )); [ $((FREE_GB / QUEUE_GB)) -lt $QUEUES ] && QUEUES=$((FREE_GB / QUEUE_GB))
  [ "$QUEUES" -lt 1 ] && QUEUES=1
  [ "$QUEUES" -gt "$SEGMENTS" ] && QUEUES=$SEGMENTS
  echo "auto queues: $QUEUES (cores=$CORES free_ram=${FREE_GB}GB)"
fi
SEGMENTS=$(( SEGMENTS < TOTAL ? SEGMENTS : TOTAL ))
SEG=$(( (TOTAL + SEGMENTS - 1) / SEGMENTS ))
OUT="${OUT//\\//}"; ENTRY="${ENTRY//\\//}"
DIR="$(dirname "$OUT")/segments"
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$DIR"

render_one() {
  local i=$1
  local A=$((i * SEG)); local B=$(((i + 1) * SEG - 1)); [ $B -ge $TOTAL ] && B=$((TOTAL - 1))
  local F="$DIR/seg_$(printf '%03d' $i).mp4"
  if [ -s "$F" ] && ffprobe -v error -show_entries format=duration -of csv=p=0 "$F" >/dev/null 2>&1; then
    echo "skip seg$i"; return 0
  fi
  echo "start seg$i [$A-$B] $(date +%H:%M:%S)"
  npx remotion render "$ENTRY" "$COMP" "$F" --codec=h264 $EXTRA \
    --concurrency=$CONCURRENCY --frames=$A-$B \
    || { sleep 10; npx remotion render "$ENTRY" "$COMP" "$F" --codec=h264 $EXTRA \
           --concurrency=$CONCURRENCY --frames=$A-$B; }
  echo "done seg$i $(date +%H:%M:%S)"
}

# split segments round-robin into per-queue lists, staggered starts
rm -f "$DIR"/q*.list
seq 0 $((SEGMENTS - 1)) | awk -v q=$QUEUES -v d="$DIR" '{ print > (d "/q" (NR % q) ".list") }' 
pids=()
for q in $(seq 0 $((QUEUES - 1))); do
  (
    sleep $((q * 40))
    while read -r i; do render_one "$i"; done < "$DIR/q$q.list"
  ) &
  pids+=($!)
done
FAIL=0
for p in "${pids[@]}"; do wait "$p" || { echo "queue pid $p FAILED"; FAIL=1; }; done
rm -f "$DIR"/q*.list
[ "$FAIL" = "1" ] && { echo "render queues failed — fix and re-run (completed segments are kept)"; exit 1; }

# integrity gate before concat — refuses broken segments
bash "$SKILL_DIR/scripts/check_segments.sh" "$DIR" || {
  echo "integrity check failed — delete the broken segments listed above, then re-run this script" >&2
  exit 1
}

: > "$DIR/concat.txt"
for i in $(seq 0 $((SEGMENTS - 1))); do
  echo "file 'seg_$(printf '%03d' $i).mp4'" >> "$DIR/concat.txt"
done
ffmpeg -y -v error -f concat -safe 0 -i "$DIR/concat.txt" -c copy "$OUT"
echo "RENDER_DONE $OUT $(date +%H:%M:%S)"
