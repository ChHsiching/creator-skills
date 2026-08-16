#!/usr/bin/env bash
# Sync vendored skills from their canonical source repos into this aggregator,
# then regenerate every install-channel manifest.
#
# Run locally and in CI (workflows/sync.yml). Idempotent: two consecutive runs
# produce an identical tree, so CI commits nothing when no source changed.
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT=$PWD
MAPPING=scripts/mapping.tsv
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

# --- 1. clone every source repo once (shallow) ------------------------------
mapfile -t ROWS < <(grep -vE '^\s*(#|$)' "$MAPPING")
REPOS=()
for row in "${ROWS[@]}"; do
  repo=$(cut -f3 <<<"$row")
  [[ " ${REPOS[*]} " == *" $repo "* ]] || REPOS+=("$repo")
done
echo "cloning ${#REPOS[@]} source repos..."
for repo in "${REPOS[@]}"; do
  git clone --quiet --depth 1 "https://github.com/ChHsiching/${repo}.git" "$WORK/$repo"
done

# --- 2. vendor each skill -----------------------------------------------------
for row in "${ROWS[@]}"; do
  IFS=$'\t' read -r group skill repo srcpath <<<"$row"
  src="$WORK/$repo"
  [[ "$srcpath" == "." ]] || src="$src/$srcpath"

  skill_md="$src/SKILL.md"
  [[ -f "$skill_md" ]] || { echo "FATAL: $repo:$srcpath has no SKILL.md" >&2; exit 1; }

  # frontmatter name must match the mapping (guards against silent renames)
  fname=$(awk '/^---$/{n++; next} n==1 && /^name:/{sub(/^name:[[:space:]]*/,""); print; exit}' "$skill_md")
  fname=$(tr -d '"' <<<"$fname")
  [[ "$fname" == "$skill" ]] || {
    echo "FATAL: $repo:$srcpath frontmatter name '$fname' != mapping '$skill'" >&2; exit 1;
  }

  dest="$ROOT/skills/$group/$skill"
  rm -rf "$dest"
  mkdir -p "$dest"
  cp -r "$src/." "$dest/"
  rm -rf "$dest/.git" "$dest/.github"
  rm -f "$dest/.gitignore" "$dest/.gitattributes"

  # container-layout repos keep LICENSE at repo root; carry it into the skill dir
  if [[ "$srcpath" != "." && -f "$WORK/$repo/LICENSE" && ! -f "$dest/LICENSE" ]]; then
    cp "$WORK/$repo/LICENSE" "$dest/LICENSE"
  fi
  echo "  $group/$skill  <-  $repo"
done

# --- 3. regenerate manifests (single source: mapping.tsv) --------------------
python3 scripts/gen_manifests.py

echo "sync done."
