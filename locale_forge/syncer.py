"""Sync: add missing keys, remove unused keys, sort locale files."""

from __future__ import annotations

import json
import os
from collections import OrderedDict
from pathlib import Path
from typing import Any

import yaml


def sync_locales(
    locale_data: dict[str, dict[str, str]],
    source_keys: set[str] | None = None,
    base_locale: str = "en",
    placeholder: str = "__TODO__",
    remove_unused: bool = False,
    sort_keys: bool = True,
) -> dict[str, dict[str, str]]:
    """Synchronize locale data: add missing keys, optionally remove unused.

    Args:
        locale_data: Dict mapping locale code to key-value pairs.
        source_keys: Optional set of keys from source code scan.
        base_locale: Reference locale.
        placeholder: Placeholder text for missing translations.
        remove_unused: If True, remove keys not in source_keys.
        sort_keys: If True, sort keys alphabetically.

    Returns:
        Updated locale data.
    """
    base_keys = set(locale_data.get(base_locale, {}).keys())

    # If source_keys provided, use union of base keys and source keys
    all_keys = base_keys | (source_keys or set())

    synced: dict[str, dict[str, str]] = {}

    for locale in locale_data:
        current = dict(locale_data[locale])

        # Add missing keys
        for key in all_keys:
            if key not in current:
                base_value = locale_data.get(base_locale, {}).get(key, "")
                if locale == base_locale:
                    current[key] = base_value or placeholder
                else:
                    current[key] = f"{placeholder}: {base_value}" if base_value else placeholder

        # Remove unused keys
        if remove_unused and source_keys:
            keys_to_remove = set(current.keys()) - source_keys
            for key in keys_to_remove:
                del current[key]

        # Sort keys
        if sort_keys:
            current = dict(sorted(current.items()))

        synced[locale] = current

    return synced


def write_locale_file(
    filepath: str,
    data: dict[str, str],
    nested: bool = True,
) -> None:
    """Write a locale file (JSON or YAML) with proper formatting.

    Args:
        filepath: Path to write to.
        data: Flattened key-value pairs.
        nested: If True, unflatten dot-separated keys into nested structure.
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    ext = path.suffix.lower()
    output_data = _unflatten_dict(data) if nested else data

    if ext in (".json", ".arb"):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
            f.write("\n")
    elif ext in (".yml", ".yaml"):
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(
                output_data,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )
    elif ext == ".properties":
        with open(filepath, "w", encoding="utf-8") as f:
            for key, value in sorted(data.items()):
                f.write(f"{key}={value}\n")
    else:
        raise ValueError(f"Cannot write format: {ext}")


def _unflatten_dict(flat: dict[str, str]) -> dict[str, Any]:
    """Convert dot-separated flat keys back to nested dict.

    "auth.login.title" -> {"auth": {"login": {"title": "..."}}}
    """
    nested: dict[str, Any] = {}

    for key, value in flat.items():
        parts = key.split(".")
        current = nested
        for part in parts[:-1]:
            if part not in current or not isinstance(current[part], dict):
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value

    return nested


def generate_sync_report(
    before: dict[str, dict[str, str]],
    after: dict[str, dict[str, str]],
) -> dict[str, dict[str, int]]:
    """Generate a report of changes made during sync.

    Returns dict mapping locale to {added, removed, unchanged}.
    """
    report: dict[str, dict[str, int]] = {}

    all_locales = set(before.keys()) | set(after.keys())
    for locale in all_locales:
        before_keys = set(before.get(locale, {}).keys())
        after_keys = set(after.get(locale, {}).keys())

        report[locale] = {
            "added": len(after_keys - before_keys),
            "removed": len(before_keys - after_keys),
            "unchanged": len(before_keys & after_keys),
            "total": len(after_keys),
        }

    return report


def add_missing_to_files(
    locale_dir: str,
    missing_keys: dict[str, list[str]],
    base_locale_data: dict[str, str],
    placeholder: str = "__TODO__",
) -> dict[str, int]:
    """Add missing keys directly to locale files on disk.

    Returns dict mapping locale to count of keys added.
    """
    from .parser import discover_locale_files, parse_locale_file

    locale_files = discover_locale_files(locale_dir)
    added_counts: dict[str, int] = {}

    for locale, missing in missing_keys.items():
        if locale not in locale_files:
            continue

        for filepath in locale_files[locale]:
            try:
                current = parse_locale_file(filepath)
            except (ValueError, Exception):
                continue

            added = 0
            for key in missing:
                if key not in current:
                    base_val = base_locale_data.get(key, "")
                    current[key] = f"{placeholder}: {base_val}" if base_val else placeholder
                    added += 1

            if added > 0:
                current = dict(sorted(current.items()))
                write_locale_file(filepath, current, nested=True)
                added_counts[locale] = added_counts.get(locale, 0) + added

    return added_counts
