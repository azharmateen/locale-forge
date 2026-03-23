"""Scan source code for translation key usage across multiple frameworks."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

# Translation function patterns by framework
PATTERNS = [
    # i18next / react-i18next: t("key"), t('key'), t(`key`)
    re.compile(r"""\bt\(\s*["'`]([a-zA-Z0-9_.:-]+)["'`]"""),
    # Vue i18n: $t("key"), $t('key')
    re.compile(r"""\$t\(\s*["']([a-zA-Z0-9_.:-]+)["']"""),
    # React Intl: <FormattedMessage id="key" />, intl.formatMessage({id: "key"})
    re.compile(r"""FormattedMessage\s+id=["']([a-zA-Z0-9_.:-]+)["']"""),
    re.compile(r"""formatMessage\(\s*\{\s*id:\s*["']([a-zA-Z0-9_.:-]+)["']"""),
    # Python gettext: _("key"), gettext("key"), ngettext("key", ...)
    re.compile(r"""_\(\s*["']([a-zA-Z0-9_.:-]+)["']"""),
    re.compile(r"""gettext\(\s*["']([a-zA-Z0-9_.:-]+)["']"""),
    re.compile(r"""ngettext\(\s*["']([a-zA-Z0-9_.:-]+)["']"""),
    # Ruby i18n: I18n.t("key"), t("key") in Rails
    re.compile(r"""I18n\.t\(\s*["':]+([a-zA-Z0-9_.:-]+)["']?"""),
    # Flutter/Dart ARB: AppLocalizations.of(context)!.key
    re.compile(r"""AppLocalizations\.of\([^)]*\)[!.]+(\w+)"""),
    # Angular: {{ 'key' | translate }}, translate.instant('key')
    re.compile(r"""\|\s*translate\s*[}:]"""),  # Less useful, but catches pipe usage
    re.compile(r"""translate\.(?:instant|get)\(\s*["']([a-zA-Z0-9_.:-]+)["']"""),
    # Svelte: $_("key")
    re.compile(r"""\$_\(\s*["']([a-zA-Z0-9_.:-]+)["']"""),
    # Generic namespace: i18n.t("key"), trans("key"), localize("key")
    re.compile(r"""i18n\.t\(\s*["']([a-zA-Z0-9_.:-]+)["']"""),
    re.compile(r"""trans\(\s*["']([a-zA-Z0-9_.:-]+)["']"""),
    re.compile(r"""localize\(\s*["']([a-zA-Z0-9_.:-]+)["']"""),
]

# File extensions to scan
SCAN_EXTENSIONS = {
    ".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte",
    ".py", ".rb", ".erb",
    ".dart",
    ".php", ".blade.php",
    ".html", ".htm",
    ".go",
}

SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    "dist", "build", ".next", "vendor", "target", ".dart_tool",
    "coverage", ".cache",
}


def scan_source(
    directory: str,
    extensions: set[str] | None = None,
    extra_patterns: list[str] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Scan source code directory for translation key usage.

    Returns dict mapping translation keys to list of usage locations.
    Each location: {"file": str, "line": int, "pattern": str}
    """
    exts = extensions or SCAN_EXTENSIONS
    patterns = list(PATTERNS)
    if extra_patterns:
        for p in extra_patterns:
            patterns.append(re.compile(p))

    keys_found: dict[str, list[dict[str, Any]]] = {}

    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for filename in files:
            # Check extension
            file_ext = ""
            for ext in exts:
                if filename.endswith(ext):
                    file_ext = ext
                    break
            if not file_ext:
                continue

            filepath = os.path.join(root, filename)
            try:
                with open(filepath, encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except OSError:
                continue

            for line_num, line in enumerate(content.splitlines(), 1):
                for pattern in patterns:
                    for match in pattern.finditer(line):
                        groups = match.groups()
                        for g in groups:
                            if g and re.match(r"^[a-zA-Z]", g):
                                key = g
                                ref = {
                                    "file": os.path.relpath(filepath, directory),
                                    "line": line_num,
                                    "pattern": pattern.pattern[:40],
                                }
                                keys_found.setdefault(key, []).append(ref)

    return keys_found


def get_scan_summary(keys_found: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """Summarize scan results."""
    total_refs = sum(len(refs) for refs in keys_found.values())
    files = set()
    for refs in keys_found.values():
        for ref in refs:
            files.add(ref["file"])

    return {
        "total_keys": len(keys_found),
        "total_references": total_refs,
        "files_scanned": len(files),
        "top_keys": sorted(
            keys_found.items(),
            key=lambda x: -len(x[1]),
        )[:10],
    }
