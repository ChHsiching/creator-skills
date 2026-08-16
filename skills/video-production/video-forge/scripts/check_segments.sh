#!/bin/bash
# Integrity-check a directory of rendered segments before concatenation.
# A force-killed render leaves files that exist but lack their moov atom —
# "file exists" is not "file is complete". This script finds the broken ones
# and lists them for re-render.
#
# Usage: check_segments.sh <segment-dir> [expected-duration-seconds]
# Exit 0 = all healthy; exit 1 = broken segments listed on stdout.
set -u
DIR="${1:?usage: check_segments.sh <dir> [expected-duration]}"
EXPECT="${2:-}"
BROKEN=0
FOUND=0
for f in "$DIR"/seg_*.mp4; do
  [ -e "$f" ] || continue
  FOUND=$((FOUND + 1))
  d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f" 2>&1 | head -1)
  case "$d" in
    ''|*[!0-9.]*) echo "BROKEN (no moov): $f"; BROKEN=1 ;;
    *)
      if [ -n "$EXPECT" ]; then
        ok=$(python -c "print(1 if abs($d - $EXPECT) < 2 else 0)" 2>/dev/null || echo 1)
        [ "$ok" = "0" ] && { echo "WRONG DURATION: $f (${d}s, expected ~${EXPECT}s)"; BROKEN=1; }
      fi ;;
  esac
done
[ "$FOUND" = "0" ] && { echo "no segments found in $DIR"; exit 1; }
[ "$BROKEN" = "0" ] && echo "all $FOUND segments healthy" || exit 1
