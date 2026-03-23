"""Analysis: missing keys, unused keys, inconsistent structure across locales."""

from __future__ import annotations

from typing import Any


def find_missing_keys(
    source_keys: set[str],
    locale_keys: dict[str, set[str]],
) -> dict[str, list[str]]:
    """Find keys used in source code but missing from locale files.

    Args:
        source_keys: Set of keys found in source code.
        locale_keys: Dict mapping locale code to set of defined keys.

    Returns:
        Dict mapping locale code to list of missing keys.
    """
    missing: dict[str, list[str]] = {}

    for locale, keys in locale_keys.items():
        locale_missing = sorted(source_keys - keys)
        if locale_missing:
            missing[locale] = locale_missing

    return missing


def find_unused_keys(
    source_keys: set[str],
    locale_keys: dict[str, set[str]],
) -> dict[str, list[str]]:
    """Find keys in locale files but not referenced in source code.

    Args:
        source_keys: Set of keys found in source code.
        locale_keys: Dict mapping locale code to set of defined keys.

    Returns:
        Dict mapping locale code to list of unused keys.
    """
    unused: dict[str, list[str]] = {}

    for locale, keys in locale_keys.items():
        locale_unused = sorted(keys - source_keys)
        if locale_unused:
            unused[locale] = locale_unused

    return unused


def find_inconsistent_keys(
    locale_data: dict[str, dict[str, str]],
    base_locale: str = "en",
) -> dict[str, dict[str, Any]]:
    """Find keys that exist in some locales but not others.

    Args:
        locale_data: Dict mapping locale code to key-value pairs.
        base_locale: The reference locale (usually "en").

    Returns:
        Dict mapping key to consistency info.
    """
    if base_locale not in locale_data:
        # Use the first locale as base
        base_locale = next(iter(locale_data)) if locale_data else ""

    if not base_locale:
        return {}

    base_keys = set(locale_data.get(base_locale, {}).keys())
    all_locales = set(locale_data.keys())
    inconsistencies: dict[str, dict[str, Any]] = {}

    # Check each key in base locale
    for key in base_keys:
        missing_in: list[str] = []
        for locale in all_locales:
            if locale == base_locale:
                continue
            if key not in locale_data.get(locale, {}):
                missing_in.append(locale)

        if missing_in:
            inconsistencies[key] = {
                "present_in": [base_locale] + [
                    l for l in all_locales
                    if l != base_locale and key in locale_data.get(l, {})
                ],
                "missing_in": missing_in,
            }

    # Also check keys in other locales that aren't in base
    for locale in all_locales:
        if locale == base_locale:
            continue
        extra_keys = set(locale_data.get(locale, {}).keys()) - base_keys
        for key in extra_keys:
            if key not in inconsistencies:
                inconsistencies[key] = {
                    "present_in": [locale],
                    "missing_in": [base_locale],
                    "note": f"Extra key in {locale}, not in base ({base_locale})",
                }

    return inconsistencies


def get_coverage_report(
    source_keys: set[str],
    locale_data: dict[str, dict[str, str]],
) -> dict[str, dict[str, Any]]:
    """Generate a coverage report for each locale.

    Returns dict mapping locale to coverage stats.
    """
    report: dict[str, dict[str, Any]] = {}

    for locale, keys_data in locale_data.items():
        locale_keys = set(keys_data.keys())
        translated = source_keys & locale_keys
        missing = source_keys - locale_keys
        unused = locale_keys - source_keys

        total = len(source_keys) if source_keys else 1
        coverage_pct = len(translated) / total * 100

        report[locale] = {
            "total_source_keys": len(source_keys),
            "translated": len(translated),
            "missing": len(missing),
            "unused": len(unused),
            "coverage_pct": round(coverage_pct, 1),
            "missing_keys": sorted(missing)[:20],  # First 20 for display
            "unused_keys": sorted(unused)[:20],
        }

    return report
