#!/usr/bin/env python3
"""
从 vendor/license.atlas（或 GitHub raw）同步 LicenseAtlas 数据到 scripts/license_atlas/。

生成:
  - index.json          （提交到仓库）
  - bodies/{slug}.txt   （不提交，见 .gitignore）

用法:
  python scripts/sync_license_atlas.py
  python scripts/sync_license_atlas.py --check-only
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_SUBMODULE = os.path.join(_REPO_ROOT, "vendor", "license.atlas")
_LICENSES_JSON = os.path.join(_SUBMODULE, "src", "data", "licenses.json")
_ATLAS_DIR = os.path.join(os.path.dirname(__file__), "license_atlas")
_BODIES_DIR = os.path.join(_ATLAS_DIR, "bodies")
_INDEX_PATH = os.path.join(_ATLAS_DIR, "index.json")
_RAW_LICENSES_URL = (
    "https://raw.githubusercontent.com/morningD/license.atlas/main/src/data/licenses.json"
)

_BUILTIN_ALIASES = {
    "mit license": "mit",
    "mit": "mit",
    "apache 2.0": "apache-2.0",
    "apache-2.0": "apache-2.0",
    "apache-2": "apache-2.0",
    "apache 2": "apache-2.0",
    "gpl-3.0": "gpl-3.0",
    "creativeml-openrail-m": "creativeml-openrail-m",
    "llama2": "llama-2-community-license-agreement",
    "llama 2": "llama-2-community-license-agreement",
}


def _git_submodule_commit() -> Optional[str]:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=_SUBMODULE,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        return out.stdout.strip() or None
    except Exception:
        return None


def _load_licenses() -> List[Dict[str, Any]]:
    if os.path.isfile(_LICENSES_JSON):
        with open(_LICENSES_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        raise ValueError(f"Unexpected licenses.json type: {type(data)}")

    print(f"Submodule file not found: {_LICENSES_JSON}", file=sys.stderr)
    print(f"Downloading from {_RAW_LICENSES_URL} ...", file=sys.stderr)
    with urllib.request.urlopen(_RAW_LICENSES_URL, timeout=120) as resp:
        data = json.load(resp)
    if not isinstance(data, list):
        raise ValueError("Downloaded licenses.json is not a list")
    return data


def _safe_slug(slug: str) -> str:
    s = (slug or "").strip().lower()
    if not s:
        raise ValueError("empty slug")
    if not re.match(r"^[a-z0-9][a-z0-9.-]*$", s):
        raise ValueError(f"unsafe slug: {slug!r}")
    return s


def _build_index(licenses: List[Dict[str, Any]], atlas_commit: Optional[str]) -> dict:
    by_spdx_id: Dict[str, str] = {}
    by_slug: Dict[str, dict] = {}
    spdx_conflicts: List[str] = []

    for item in licenses:
        slug = _safe_slug(item.get("slug") or "")
        spdx = (item.get("spdx_id") or "").strip()
        if spdx:
            if spdx in by_spdx_id and by_spdx_id[spdx] != slug:
                spdx_conflicts.append(f"{spdx}: {by_spdx_id[spdx]} vs {slug}")
            else:
                by_spdx_id[spdx] = slug
        by_slug[slug] = {
            "title": item.get("title"),
            "spdx_id": spdx or None,
            "type": item.get("type"),
        }

    if spdx_conflicts:
        print(f"Warning: {len(spdx_conflicts)} spdx_id conflicts (first 5):", file=sys.stderr)
        for line in spdx_conflicts[:5]:
            print(f"  {line}", file=sys.stderr)

    return {
        "atlas_commit": atlas_commit,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "license_count": len(licenses),
        "by_spdx_id": by_spdx_id,
        "by_slug": by_slug,
        "aliases": dict(_BUILTIN_ALIASES),
    }


def sync(check_only: bool = False) -> int:
    if not os.path.isfile(_LICENSES_JSON):
        if not os.path.isdir(_SUBMODULE):
            print(
                "Hint: git submodule update --init vendor/license.atlas",
                file=sys.stderr,
            )

    licenses = _load_licenses()
    atlas_commit = _git_submodule_commit()
    index = _build_index(licenses, atlas_commit)

    if check_only:
        if not os.path.isfile(_INDEX_PATH):
            print(f"MISSING: {_INDEX_PATH}", file=sys.stderr)
            return 1
        if not os.path.isdir(_BODIES_DIR):
            print(f"MISSING: {_BODIES_DIR}", file=sys.stderr)
            return 1
        body_count = len([f for f in os.listdir(_BODIES_DIR) if f.endswith(".txt")])
        if body_count < index["license_count"] * 0.9:
            print(
                f"INCOMPLETE bodies: {body_count}/{index['license_count']}",
                file=sys.stderr,
            )
            return 1
        print(f"OK: index + {body_count} bodies")
        return 0

    os.makedirs(_BODIES_DIR, exist_ok=True)
    written = 0
    skipped_empty = 0
    for item in licenses:
        slug = _safe_slug(item.get("slug") or "")
        body = (item.get("body") or "").strip()
        if not body:
            skipped_empty += 1
            continue
        path = os.path.join(_BODIES_DIR, f"{slug}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(body)
        written += 1

    with open(_INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"Wrote {_INDEX_PATH}")
    print(f"Wrote {written} files under {_BODIES_DIR}/ ({skipped_empty} empty bodies skipped)")
    if atlas_commit:
        print(f"Atlas submodule commit: {atlas_commit}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync LicenseAtlas data into scripts/license_atlas/")
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Verify index.json and bodies/ exist without writing",
    )
    args = parser.parse_args()
    try:
        return sync(check_only=args.check_only)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
