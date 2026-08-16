#!/bin/bash
# Segment-loop TTS synthesis with the safeguards baked in:
#   - skip-existing (interrupted runs resume without re-burning quota)
#   - serial (rate-limit friendly)
#   - per-run cost report
#   - --force to invalidate every cached file (voice change => full re-spend,
#     and the script says so with numbers before you run it)
#
# Input file: one segment per line, "<id>\\t<text>" (tab-separated).
# Output: <out-dir>/<id>.mp3 per segment + narration.mp3 (concat, stream copy).
#
# Usage:
#   synthesize.sh <segments.tsv> <out-dir> --provider minimax --voice <id>
#   synthesize.sh ... --force        # re-synthesize ALL segments
# Providers: minimax | openai   (add others in provider_synth() below)
set -eu
TSV="${1:?segments.tsv}"; OUT="${2:?out-dir}"; shift 2
PROVIDER=minimax; VOICE=""; FORCE=0
while [ $# -gt 0 ]; do
  case "$1" in
    --provider) PROVIDER="$2"; shift 2 ;;
    --voice) VOICE="$2"; shift 2 ;;
    --force) FORCE=1; shift ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done
mkdir -p "$OUT"
[ -n "$VOICE" ] || { echo "ERROR: --voice is required — audition first on the provider's free channel, never by synthesizing" >&2; exit 2; }

provider_synth() { # $1=text  $2=outfile
  case "$PROVIDER" in
    minimax) mmx speech synthesize --voice "$VOICE" --text "$1" --out "$2" ;;
    openai)
      curl -s --fail --max-time 120 https://api.openai.com/v1/audio/speech -X POST \
        -H "Authorization: Bearer $OPENAI_API_KEY" -H "Content-Type: application/json" \
        -d "{\"model\":\"tts-1\",\"voice\":\"$VOICE\",\"input\":$(python -c "import json,sys;print(json.dumps(sys.argv[1]))" "$1")}" \
        --output "$2" ;;
    *) echo "provider '$PROVIDER' not wired — add a case in provider_synth()" >&2; exit 2 ;;
  esac
}

N=0; DONE=0; SKIP=0; CHARS=0
TOTAL=$(grep -c . "$TSV")
if [ "$FORCE" = "1" ]; then
  SPEND=$(awk -F'\t' '{n+=length($2)} END{print n}' "$TSV")
  echo "FORCE: re-synthesizing ALL $TOTAL segments ($SPEND chars — full re-spend)"
  rm -f "$OUT"/*.mp3
fi
while IFS=$'\t' read -r id text; do
  id="${id%$'\r'}"; text="${text%$'\r'}"
  [ -z "$id" ] && continue
  N=$((N + 1))
  F="$OUT/$id.mp3"
  if [ -s "$F" ]; then SKIP=$((SKIP + 1)); printf '[%3d/%d] %s skip (exists)\n' "$N" "$TOTAL" "$id"; continue; fi
  provider_synth "$text" "$F"
  DONE=$((DONE + 1)); CHARS=$((CHARS + ${#text}))
  printf '[%3d/%d] %s ok (%ds chars)\n' "$N" "$TOTAL" "$id" "${#text}"
done < "$TSV"

# assemble once — segments share the provider's format, stream copy suffices
: > "$OUT/concat.txt"
while IFS=$'\t' read -r id _; do [ -n "$id" ] && echo "file '$id.mp3'"; done < "$TSV" >> "$OUT/concat.txt"
ffmpeg -y -v error -f concat -safe 0 -i "$OUT/concat.txt" -c copy "$OUT/narration.mp3"
echo "SYNTH_DONE new=$DONE skip=$SKIP chars=$CHARS -> $OUT/narration.mp3"
