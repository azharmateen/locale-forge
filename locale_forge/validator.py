"""Validate translations: placeholder consistency, plural forms, HTML tags, length."""

from __future__ import annotations

import re
from typing import Any


# Patterns for detecting placeholders
PLACEHOLDER_PATTERNS = [
    re.compile(r"\{(\w+)\}"),           # {name}, {count}
    re.compile(r"\{\{(\w+)\}\}"),       # {{name}} (Handlebars/Angular)
    re.compile(r"%\{(\w+)\}"),          # %{name} (Ruby i18n)
    re.compile(r"%[sdfo]"),             # %s, %d (printf-style)
    re.compile(r"\$\{(\w+)\}"),         # ${name} (template literals)
    re.compile(r"\$(\w+)"),             # $name (PHP/Perl)
]

# HTML tag pattern
HTML_TAG_PATTERN = re.compile(r"</?[a-zA-Z][\w-]*[^>]*>")

# Common plural forms expected per language
PLURAL_FORMS = {
    "en": 2,  # singular, plural
    "fr": 2,
    "de": 2,
    "es": 2,
    "pt": 2,
    "it": 2,
    "nl": 2,
    "ja": 1,  # No plural distinction
    "zh": 1,
    "ko": 1,
    "ar": 6,  # singular, dual, plural (3-10), plural (11-99), etc.
    "pl": 3,  # singular, few (2-4), many (5+)
    "ru": 3,
    "cs": 3,
}


class ValidationIssue:
    """A single validation issue found in a translation."""

    def __init__(
        self,
        key: str,
        locale: str,
        issue_type: str,
        severity: str,
        message: str,
        source_value: str = "",
        target_value: str = "",
    ):
        self.key = key
        self.locale = locale
        self.issue_type = issue_type
        self.severity = severity  # "error", "warning", "info"
        self.message = message
        self.source_value = source_value
        self.target_value = target_value

    def to_dict(self) -> dict[str, str]:
        return {
            "key": self.key,
            "locale": self.locale,
            "type": self.issue_type,
            "severity": self.severity,
            "message": self.message,
        }

    def __repr__(self) -> str:
        return f"[{self.severity}] {self.locale}/{self.key}: {self.message}"


def validate_translations(
    locale_data: dict[str, dict[str, str]],
    base_locale: str = "en",
    max_length: int | None = None,
) -> list[ValidationIssue]:
    """Run all validation checks on locale data.

    Args:
        locale_data: Dict mapping locale code to key-value pairs.
        base_locale: The reference locale.
        max_length: Optional max character length for translations.

    Returns:
        List of ValidationIssue objects.
    """
    issues: list[ValidationIssue] = []
    base_data = locale_data.get(base_locale, {})

    for locale, translations in locale_data.items():
        if locale == base_locale:
            continue

        for key, target_value in translations.items():
            source_value = base_data.get(key, "")

            # 1. Placeholder consistency
            issues.extend(
                _check_placeholders(key, locale, source_value, target_value)
            )

            # 2. HTML tag balance
            issues.extend(
                _check_html_tags(key, locale, source_value, target_value)
            )

            # 3. Length check
            if max_length and len(target_value) > max_length:
                issues.append(ValidationIssue(
                    key=key,
                    locale=locale,
                    issue_type="length",
                    severity="warning",
                    message=f"Translation exceeds {max_length} chars ({len(target_value)} chars)",
                    source_value=source_value,
                    target_value=target_value,
                ))

            # 4. Empty translation
            if not target_value.strip() and source_value.strip():
                issues.append(ValidationIssue(
                    key=key,
                    locale=locale,
                    issue_type="empty",
                    severity="error",
                    message="Translation is empty",
                    source_value=source_value,
                    target_value=target_value,
                ))

            # 5. Identical to source (might be untranslated)
            if (
                target_value == source_value
                and locale != base_locale
                and len(source_value) > 3  # Skip very short strings
            ):
                issues.append(ValidationIssue(
                    key=key,
                    locale=locale,
                    issue_type="untranslated",
                    severity="info",
                    message="Translation identical to source (possibly untranslated)",
                    source_value=source_value,
                    target_value=target_value,
                ))

            # 6. Leading/trailing whitespace mismatch
            if source_value and target_value:
                if source_value[0] == " " and target_value[0] != " ":
                    issues.append(ValidationIssue(
                        key=key, locale=locale, issue_type="whitespace",
                        severity="warning",
                        message="Source has leading space but translation does not",
                    ))
                if source_value[-1] == "\n" and not target_value.endswith("\n"):
                    issues.append(ValidationIssue(
                        key=key, locale=locale, issue_type="whitespace",
                        severity="warning",
                        message="Source ends with newline but translation does not",
                    ))

    return issues


def _check_placeholders(
    key: str, locale: str, source: str, target: str
) -> list[ValidationIssue]:
    """Check that placeholders in source exist in target."""
    issues = []

    for pattern in PLACEHOLDER_PATTERNS:
        source_matches = set(pattern.findall(source))
        target_matches = set(pattern.findall(target))

        missing = source_matches - target_matches
        extra = target_matches - source_matches

        if missing:
            issues.append(ValidationIssue(
                key=key,
                locale=locale,
                issue_type="placeholder_missing",
                severity="error",
                message=f"Missing placeholders: {', '.join(sorted(missing))}",
                source_value=source,
                target_value=target,
            ))

        if extra:
            issues.append(ValidationIssue(
                key=key,
                locale=locale,
                issue_type="placeholder_extra",
                severity="warning",
                message=f"Extra placeholders not in source: {', '.join(sorted(extra))}",
                source_value=source,
                target_value=target,
            ))

    return issues


def _check_html_tags(
    key: str, locale: str, source: str, target: str
) -> list[ValidationIssue]:
    """Check HTML tag balance between source and target."""
    issues = []

    source_tags = HTML_TAG_PATTERN.findall(source)
    target_tags = HTML_TAG_PATTERN.findall(target)

    if not source_tags and not target_tags:
        return issues

    # Compare tag counts
    source_tag_names = sorted(_extract_tag_names(source_tags))
    target_tag_names = sorted(_extract_tag_names(target_tags))

    if source_tag_names != target_tag_names:
        issues.append(ValidationIssue(
            key=key,
            locale=locale,
            issue_type="html_mismatch",
            severity="error",
            message=(
                f"HTML tag mismatch. Source: {source_tag_names}, "
                f"Target: {target_tag_names}"
            ),
            source_value=source,
            target_value=target,
        ))

    return issues


def _extract_tag_names(tags: list[str]) -> list[str]:
    """Extract tag names from HTML tag strings."""
    names = []
    for tag in tags:
        match = re.match(r"</?(\w+)", tag)
        if match:
            names.append(match.group(1))
    return names


def get_validation_summary(issues: list[ValidationIssue]) -> dict[str, Any]:
    """Summarize validation issues."""
    by_severity: dict[str, int] = {"error": 0, "warning": 0, "info": 0}
    by_type: dict[str, int] = {}
    by_locale: dict[str, int] = {}

    for issue in issues:
        by_severity[issue.severity] = by_severity.get(issue.severity, 0) + 1
        by_type[issue.issue_type] = by_type.get(issue.issue_type, 0) + 1
        by_locale[issue.locale] = by_locale.get(issue.locale, 0) + 1

    return {
        "total_issues": len(issues),
        "by_severity": by_severity,
        "by_type": dict(sorted(by_type.items(), key=lambda x: -x[1])),
        "by_locale": dict(sorted(by_locale.items(), key=lambda x: -x[1])),
    }
