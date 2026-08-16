#!/usr/bin/env python3
"""Regenerate every install-channel manifest for the creator-skills aggregator.

Reads scripts/mapping.tsv (single source of truth for the group/skill mapping)
and writes, idempotently:

  .claude-plugin/marketplace.json   -> skills CLI grouping + Claude Code + Codex (legacy-compat)
  marketplace.json                  -> ZCode plugin marketplace (repo root)
  skills/<group>/.claude-plugin/plugin.json
  skills/<group>/.zcode-plugin/plugin.json
  skills/<group>/.codex-plugin/plugin.json   (same content, three installers' preferred slots)

Never edit the generated files by hand — change mapping.tsv / GROUP_META and rerun.
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MAPPING_TSV = REPO_ROOT / "scripts" / "mapping.tsv"

OWNER = {"name": "ChHsiching", "url": "https://github.com/ChHsiching"}
REPO_URL = "https://github.com/ChHsiching/creator-skills"

# Suite descriptions shown in every install channel. Keyed by group id; the id
# itself becomes the UI group title (rendered as e.g. "Video Localization").
GROUP_META = {
    "video-localization": {
        "description": (
            "Bring an existing video over the language barrier: download it, "
            "transcribe, subtitle, and optionally re-voice it in Chinese."
        ),
        "category": "video",
    },
    "video-production": {
        "description": (
            "Produce an original video from source material: planning, "
            "provider-agnostic voiceover, and 4K render polish."
        ),
        "category": "video",
    },
    "image-text-cards": {
        "description": (
            "Turn articles and posts into vertical 3:4 image-text card decks "
            "for Xiaohongshu (小红书)."
        ),
        "category": "image-text",
    },
    "novel-promotion": {
        "description": (
            "Scout novels worth promoting and produce the promo video: "
            "selection, copywriting, source assembly, narration."
        ),
        "category": "novel",
    },
}


def load_mapping() -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    with open(MAPPING_TSV, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            group, skill, _repo, _path = line.split("\t")
            groups.setdefault(group, []).append(skill)
    missing = set(groups) - set(GROUP_META)
    extra = set(GROUP_META) - set(groups)
    if missing or extra:
        sys.exit(f"mapping.tsv groups {sorted(missing)} lack GROUP_META / {sorted(extra)} unused")
    return groups


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {path.relative_to(REPO_ROOT)}")


def main() -> None:
    groups = load_mapping()

    # Channel 1: skills CLI (vercel-labs/skills) grouping + Claude Code + Codex
    # legacy marketplace. The per-plugin `skills` arrays are what the skills CLI
    # reads to group the interactive picker; Claude/Codex ignore them.
    claude_marketplace = {
        "name": "creator-skills",
        "owner": OWNER,
        "plugins": [
            {
                "name": group,
                "source": f"./skills/{group}",
                "description": GROUP_META[group]["description"],
                "skills": [f"./{skill}" for skill in skills],
            }
            for group, skills in groups.items()
        ],
    }
    write_json(REPO_ROOT / ".claude-plugin" / "marketplace.json", claude_marketplace)

    # Channel 2: ZCode marketplace, repo-root marketplace.json (the layout
    # ZCode consumes today — proven by the rm-guard plugin).
    zcode_marketplace = {
        "name": "creator-skills",
        "description": (
            "Content-creation skill suites for AI agents: video localization, "
            "original video production, Xiaohongshu image-text cards, and novel "
            "promotion videos. Source repos stay canonical; this repo is the "
            "one-command installer."
        ),
        "owner": OWNER,
        "plugins": [
            {
                "name": group,
                "description": GROUP_META[group]["description"],
                "source": f"./skills/{group}",
                "category": GROUP_META[group]["category"],
                "homepage": REPO_URL,
            }
            for group in groups
        ],
    }
    write_json(REPO_ROOT / "marketplace.json", zcode_marketplace)

    # Channels 3-5: per-suite plugin manifests in each installer's preferred
    # slot (.claude-plugin for Claude Code, .zcode-plugin for ZCode,
    # .codex-plugin for Codex). Identical content — all three parsers accept
    # the skills array (Codex: RawPluginManifestPaths untagged enum).
    for group, skills in groups.items():
        manifest = {
            "name": group,
            "description": GROUP_META[group]["description"],
            "skills": [f"./{skill}" for skill in skills],
        }
        for slot in (".claude-plugin", ".zcode-plugin", ".codex-plugin"):
            write_json(REPO_ROOT / "skills" / group / slot / "plugin.json", manifest)

    total = sum(len(s) for s in groups.values())
    print(f"manifests ok: {len(groups)} suites, {total} skills")


if __name__ == "__main__":
    main()
