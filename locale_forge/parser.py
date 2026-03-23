"""Parse locale files: JSON (flat/nested), YAML, .properties, .po, .arb."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import yaml


def parse_locale_file(filepath: str) -> dict[str, str]:
    """Parse a locale file and return flattened key-value pairs.

    Supports: JSON, YAML, .properties, .po, .arb (Flutter)
    """
    path = Path(filepath)
    ext = path.suffix.lower()

    if ext in (".json", ".arb"):
        return _parse_json(filepath)
    elif ext in (".yml", ".yaml"):
        return _parse_yaml(filepath)
    elif ext == ".properties":
        return _parse_properties(filepath)
    elif ext == ".po":
        return _parse_po(filepath)
    elif ext == ".pot":
        return _parse_po(filepath)
    else:
        raise ValueError(f"Unsupported locale file format: {ext}")


def _parse_json(filepath: str) -> dict[str, str]:
    """Parse JSON locale file (handles flat and nested structures)."""
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    # For ARB files, skip metadata keys starting with @
    flat: dict[str, str] = {}
    _flatten_dict(data, "", flat, skip_prefix="@")
    return flat


def _parse_yaml(filepath: str) -> dict[str, str]:
    """Parse YAML locale file."""
    with open(filepath, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    # Some YAML locale files have a top-level locale key (e.g. Rails)
    # e.g. { "en": { "hello": "Hello" } }
    if len(data) == 1:
        key = list(data.keys())[0]
        if isinstance(data[key], dict) and len(key) <= 5:  # Probably a locale code
            data = data[key]

    flat: dict[str, str] = {}
    _flatten_dict(data, "", flat)
    return flat


def _parse_properties(filepath: str) -> dict[str, str]:
    """Parse Java .properties locale file."""
    result: dict[str, str] = {}
    with open(filepath, encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("!"):
                continue
            # Split on first = or :
            for sep in ("=", ":"):
                if sep in line:
                    key, value = line.split(sep, 1)
                    result[key.strip()] = value.strip()
                    break
    return result


def _parse_po(filepath: str) -> dict[str, str]:
    """Parse gettext .po/.pot file."""
    result: dict[str, str] = {}
    current_msgid = ""
    current_msgstr = ""
    in_msgstr = False

    with open(filepath, encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()

            if line.startswith("msgid "):
                if current_msgid and current_msgstr:
                    result[current_msgid] = current_msgstr
                current_msgid = _extract_po_string(line[6:])
                current_msgstr = ""
                in_msgstr = False
            elif line.startswith("msgstr "):
                current_msgstr = _extract_po_string(line[7:])
                in_msgstr = True
            elif line.startswith('"') and line.endswith('"'):
                # Continuation line
                continued = _extract_po_string(line)
                if in_msgstr:
                    current_msgstr += continued
                else:
                    current_msgid += continued

    # Don't forget the last entry
    if current_msgid:
        result[current_msgid] = current_msgstr

    return result


def _extract_po_string(s: str) -> str:
    """Extract string value from a .po file line."""
    s = s.strip()
    if s.startswith('"') and s.endswith('"'):
        s = s[1:-1]
    # Unescape common escape sequences
    s = s.replace('\\"', '"').replace("\\n", "\n").replace("\\t", "\t")
    return s


def _flatten_dict(
    data: Any,
    prefix: str,
    result: dict[str, str],
    separator: str = ".",
    skip_prefix: str = "",
) -> None:
    """Recursively flatten a nested dict into dot-separated keys."""
    if isinstance(data, dict):
        for key, value in data.items():
            if skip_prefix and str(key).startswith(skip_prefix):
                continue
            new_key = f"{prefix}{separator}{key}" if prefix else str(key)
            _flatten_dict(value, new_key, result, separator, skip_prefix)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            new_key = f"{prefix}[{i}]"
            _flatten_dict(item, new_key, result, separator, skip_prefix)
    else:
        result[prefix] = str(data) if data is not None else ""


def discover_locale_files(
    locale_dir: str,
    extensions: set[str] | None = None,
) -> dict[str, list[str]]:
    """Discover locale files organized by locale code.

    Returns dict mapping locale code to list of file paths.
    Handles common directory structures:
    - locales/en.json, locales/fr.json
    - locales/en/translation.json, locales/fr/translation.json
    - locales/en/common.json, locales/en/auth.json (namespaced)
    """
    exts = extensions or {".json", ".yml", ".yaml", ".properties", ".po", ".pot", ".arb"}
    locale_files: dict[str, list[str]] = {}

    for root, dirs, files in os.walk(locale_dir):
        for filename in files:
            filepath = os.path.join(root, filename)
            ext = Path(filename).suffix.lower()

            if ext not in exts:
                continue

            # Determine locale from path
            rel_path = os.path.relpath(filepath, locale_dir)
            parts = Path(rel_path).parts

            locale = None
            if len(parts) >= 2:
                # Directory structure: en/translation.json
                candidate = parts[0]
                if _is_locale_code(candidate):
                    locale = candidate
            if locale is None:
                # File name: en.json, messages_en.properties
                stem = Path(filename).stem
                if _is_locale_code(stem):
                    locale = stem
                else:
                    # Try extracting: messages_en -> en, translation.en -> en
                    for sep in ("_", "-", "."):
                        if sep in stem:
                            last_part = stem.rsplit(sep, 1)[-1]
                            if _is_locale_code(last_part):
                                locale = last_part
                                break

            if locale:
                locale_files.setdefault(locale, []).append(filepath)

    return locale_files


def _is_locale_code(s: str) -> bool:
    """Check if a string looks like a locale code (en, fr, zh-CN, pt-BR, etc.)."""
    return bool(re.match(r"^[a-z]{2}([_-][A-Za-z]{2,4})?$", s))


def parse_all_locales(locale_dir: str) -> dict[str, dict[str, str]]:
    """Parse all locale files in a directory.

    Returns dict mapping locale code to flattened key-value pairs.
    If a locale has multiple files (namespaced), keys are prefixed with filename.
    """
    locale_files = discover_locale_files(locale_dir)
    all_locales: dict[str, dict[str, str]] = {}

    for locale, files in locale_files.items():
        merged: dict[str, str] = {}
        for filepath in files:
            try:
                keys = parse_locale_file(filepath)
                if len(files) > 1:
                    # Namespace by filename
                    namespace = Path(filepath).stem
                    keys = {f"{namespace}.{k}": v for k, v in keys.items()}
                merged.update(keys)
            except (ValueError, json.JSONDecodeError, yaml.YAMLError) as e:
                # Skip invalid files but continue
                continue
        all_locales[locale] = merged

    return all_locales
