#!/usr/bin/env python3
"""Git merge driver for gnome-index.json.

Git calls it as: merge-gnome-index.py <base> <ours> <theirs>
and expects the merged result written to <ours>, exiting 0 on success.

Entries are merged one GIF at a time against the common base:
- changed on one side only  -> take that side
- changed on both sides     -> keep the version with OCR text; if both or
                               neither have it, keep ours
- deleted on one side, untouched on the other -> delete
- deleted on one side, changed on the other   -> keep the change
Other top-level fields follow the same rule; a conflict keeps ours.

Output matches the app's format: 2-space indent, "key" : value,
sorted keys, escaped slashes, no trailing newline.
"""

import json
import sys

MISSING = object()


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        return {}
    return json.loads(text) if text.strip() else {}


def pick(base, ours, theirs, prefer):
    if ours == theirs:
        return ours
    if ours == base:
        return theirs
    if theirs == base:
        return ours
    # Both sides changed it.
    if ours is MISSING:
        return theirs
    if theirs is MISSING:
        return ours
    return prefer(ours, theirs)


def prefer_ocr(ours, theirs):
    if isinstance(ours, dict) and isinstance(theirs, dict):
        if "ocrText" in theirs and "ocrText" not in ours:
            return theirs
    return ours


def merge_dicts(base, ours, theirs, prefer):
    result = {}
    for key in set(base) | set(ours) | set(theirs):
        value = pick(
            base.get(key, MISSING),
            ours.get(key, MISSING),
            theirs.get(key, MISSING),
            prefer,
        )
        if value is not MISSING:
            result[key] = value
    return result


def main():
    base_path, ours_path, theirs_path = sys.argv[1:4]
    base, ours, theirs = load(base_path), load(ours_path), load(theirs_path)

    merged = merge_dicts(
        {k: v for k, v in base.items() if k != "entries"},
        {k: v for k, v in ours.items() if k != "entries"},
        {k: v for k, v in theirs.items() if k != "entries"},
        lambda o, t: o,
    )
    merged["entries"] = merge_dicts(
        base.get("entries", {}),
        ours.get("entries", {}),
        theirs.get("entries", {}),
        prefer_ocr,
    )

    text = json.dumps(
        merged, indent=2, separators=(",", " : "), sort_keys=True, ensure_ascii=False
    )
    # The app escapes "/" inside strings; "/" can only appear inside strings.
    text = text.replace("/", "\\/")
    with open(ours_path, "w", encoding="utf-8") as f:
        f.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
