#!/bin/bash
# Segmented parallel render driver for long Remotion videos, with the
# session-proven safeguards baked in:
#   - frame-exact segments, stream-copy concat (zero quality loss)
#   - skip-existing resume (a crash costs only the in-flight segment)
#   - staggered queue starts (process-spawn spikes collide otherwise)
#   - per-segment retry (transient ffmpeg spawn failures happen under load)
#   - moov integrity check BEFORE concat (killed segments never join the master)
#
# Usage:
#   render_segments.sh <entry.ts(x)> <CompositionId> <total-frames> <out-mp4> \
#                      [--segments N] [--queues N] [--concurrency N]
#                      [-- extra render args, e.g. --scale=2 --props='{"x":1}']
set -eu
ENTRY="${1:?entry}"; COMP="${2:?composition id}"; TOTAL="${3:?total frames}"; OUT="${4:?out.mp4}"
shift 4
SEGMENTS=12; QUEUES=auto; CONCURRENCY=8
while [ $# -gt 0 ]; do
  case "$1" in
    --segments) SEGMENTS="$2"; shift 2 ;;
    --queues) QUEUES="$2"; shift 2 ;;  # or auto: computed from measured cores+free RAM
    --concurrency) CONCURRENCY="$2"; shift 2 ;;
    --) shift; break ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done
EXTRA="$*"
if [ "$QUEUES" = "auto" ]; then
  CORES=$(python -c "import os; print(os.cpu_count() or 4)")
  FREE_GB=$(python -c "import ctypes" 2>/dev/null && powershell -NoProfile -Command "[math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB)" 2>/dev/null || echo 8)
  QUEUES=$(( CORES / 4 )); [ $((FREE_GB / 7)) -lt $QUEUES ] && QUEUES=$((FREE_GB / 7))
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
