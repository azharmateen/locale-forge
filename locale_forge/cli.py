"""Locale Forge CLI - i18n translation key manager."""

from __future__ import annotations

import json
import sys

import click
from rich.console import Console
from rich.table import Table

from . import __version__
from .analyzer import (
    find_inconsistent_keys,
    find_missing_keys,
    find_unused_keys,
    get_coverage_report,
)
from .parser import parse_all_locales
from .scanner import scan_source
from .syncer import (
    add_missing_to_files,
    sync_locales,
    generate_sync_report,
)
from .validator import validate_translations, get_validation_summary

console = Console()


@click.group()
@click.version_option(__version__, prog_name="locale-forge")
def cli() -> None:
    """Locale Forge - i18n translation key manager.

    Scan source code for translation keys, detect missing/unused translations,
    validate placeholder consistency, and sync locale files.
    """
    pass


@cli.command()
@click.argument("src", default="./src")
@click.option("--locales", "-l", default="./locales", help="Locale files directory.")
@click.option("--base", "-b", default="en", help="Base locale code.")
def scan(src: str, locales: str, base: str) -> None:
    """Scan source code and locale files, show coverage report."""
    console.print(f"\n[bold blue]Scanning source:[/] {src}")
    console.print(f"[bold blue]Locale dir:[/] {locales}\n")

    # Scan source code
    source_refs = scan_source(src)
    source_keys = set(source_refs.keys())
    console.print(f"Found [cyan]{len(source_keys)}[/] translation keys in source code")

    # Parse locale files
    locale_data = parse_all_locales(locales)
    if not locale_data:
        console.print("[yellow]No locale files found.[/]")
        return

    console.print(f"Found [cyan]{len(locale_data)}[/] locales: {', '.join(sorted(locale_data.keys()))}\n")

    # Coverage report
    report = get_coverage_report(source_keys, locale_data)

    table = Table(title="Translation Coverage")
    table.add_column("Locale", style="cyan")
    table.add_column("Translated", justify="right")
    table.add_column("Missing", justify="right", style="red")
    table.add_column("Unused", justify="right", style="yellow")
    table.add_column("Coverage", justify="right")

    for locale, stats in sorted(report.items()):
        pct = stats["coverage_pct"]
        pct_color = "green" if pct >= 90 else "yellow" if pct >= 70 else "red"
        table.add_row(
            locale,
            str(stats["translated"]),
            str(stats["missing"]),
            str(stats["unused"]),
            f"[{pct_color}]{pct}%[/]",
        )

    console.print(table)


@cli.command()
@click.argument("src", default="./src")
@click.option("--locales", "-l", default="./locales", help="Locale files directory.")
@click.option("--base", "-b", default="en", help="Base locale code.")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def missing(src: str, locales: str, base: str, as_json: bool) -> None:
    """Find translation keys missing from locale files."""
    source_refs = scan_source(src)
    source_keys = set(source_refs.keys())
    locale_data = parse_all_locales(locales)

    locale_keysets = {loc: set(data.keys()) for loc, data in locale_data.items()}
    missing_result = find_missing_keys(source_keys, locale_keysets)

    if as_json:
        click.echo(json.dumps(missing_result, indent=2))
        return

    if not missing_result:
        console.print("[green]No missing keys! All translations are complete.[/]")
        return

    for locale, keys in sorted(missing_result.items()):
        console.print(f"\n[bold red]{locale}[/] - {len(keys)} missing:")
        for key in keys[:30]:
            refs = source_refs.get(key, [])
            location = f" ({refs[0]['file']}:{refs[0]['line']})" if refs else ""
            console.print(f"  [red]-[/] {key}{location}")
        if len(keys) > 30:
            console.print(f"  ... and {len(keys) - 30} more")


@cli.command()
@click.argument("src", default="./src")
@click.option("--locales", "-l", default="./locales", help="Locale files directory.")
def unused(src: str, locales: str) -> None:
    """Find translation keys defined but not used in source code."""
    source_refs = scan_source(src)
    source_keys = set(source_refs.keys())
    locale_data = parse_all_locales(locales)

    locale_keysets = {loc: set(data.keys()) for loc, data in locale_data.items()}
    unused_result = find_unused_keys(source_keys, locale_keysets)

    if not unused_result:
        console.print("[green]No unused keys found.[/]")
        return

    for locale, keys in sorted(unused_result.items()):
        console.print(f"\n[bold yellow]{locale}[/] - {len(keys)} unused:")
        for key in keys[:30]:
            console.print(f"  [yellow]-[/] {key}")
        if len(keys) > 30:
            console.print(f"  ... and {len(keys) - 30} more")


@cli.command()
@click.option("--locales", "-l", default="./locales", help="Locale files directory.")
@click.option("--base", "-b", default="en", help="Base locale code.")
@click.option("--max-length", default=None, type=int, help="Max translation length.")
def validate(locales: str, base: str, max_length: int | None) -> None:
    """Validate translations for placeholder consistency, HTML tags, and more."""
    locale_data = parse_all_locales(locales)
    if not locale_data:
        console.print("[yellow]No locale files found.[/]")
        return

    issues = validate_translations(locale_data, base_locale=base, max_length=max_length)

    if not issues:
        console.print("[green]All translations are valid![/]")
        return

    summary = get_validation_summary(issues)
    console.print(f"\n[bold]Validation Results:[/] {summary['total_issues']} issues\n")

    # Show by severity
    for severity in ("error", "warning", "info"):
        count = summary["by_severity"].get(severity, 0)
        if count == 0:
            continue

        color = {"error": "red", "warning": "yellow", "info": "blue"}[severity]
        console.print(f"[{color} bold]{severity.upper()} ({count}):[/]")

        severity_issues = [i for i in issues if i.severity == severity]
        for issue in severity_issues[:20]:
            console.print(f"  [{color}]{issue.locale}/{issue.key}[/]: {issue.message}")

        if len(severity_issues) > 20:
            console.print(f"  ... and {len(severity_issues) - 20} more")
        console.print()


@cli.command()
@click.argument("src", default="./src")
@click.option("--locales", "-l", default="./locales", help="Locale files directory.")
@click.option("--base", "-b", default="en", help="Base locale code.")
@click.option("--placeholder", "-p", default="__TODO__", help="Placeholder for missing translations.")
@click.option("--remove-unused", is_flag=True, help="Remove unused keys.")
@click.option("--dry-run", is_flag=True, help="Show changes without writing files.")
def sync(src: str, locales: str, base: str, placeholder: str,
         remove_unused: bool, dry_run: bool) -> None:
    """Sync locale files: add missing keys, optionally remove unused."""
    source_refs = scan_source(src)
    source_keys = set(source_refs.keys())
    locale_data = parse_all_locales(locales)

    if not locale_data:
        console.print("[yellow]No locale files found.[/]")
        return

    synced = sync_locales(
        locale_data,
        source_keys=source_keys,
        base_locale=base,
        placeholder=placeholder,
        remove_unused=remove_unused,
    )

    report = generate_sync_report(locale_data, synced)

    table = Table(title="Sync Report")
    table.add_column("Locale", style="cyan")
    table.add_column("Added", style="green", justify="right")
    table.add_column("Removed", style="red", justify="right")
    table.add_column("Total", justify="right")

    has_changes = False
    for locale, stats in sorted(report.items()):
        if stats["added"] > 0 or stats["removed"] > 0:
            has_changes = True
        table.add_row(
            locale,
            str(stats["added"]),
            str(stats["removed"]),
            str(stats["total"]),
        )

    console.print(table)

    if not has_changes:
        console.print("\n[green]All locales are in sync![/]")
        return

    if dry_run:
        console.print("\n[yellow]Dry run - no files modified.[/]")
    else:
        # Write synced data back to files
        base_data = locale_data.get(base, {})
        locale_keysets = {loc: set(data.keys()) for loc, data in locale_data.items()}
        missing_keys = find_missing_keys(source_keys, locale_keysets)

        if missing_keys:
            added_counts = add_missing_to_files(locales, missing_keys, base_data, placeholder)
            for locale, count in added_counts.items():
                console.print(f"  [green]+{count} keys added to {locale}[/]")

        console.print("\n[green]Sync complete.[/]")


@cli.command(name="export")
@click.option("--locales", "-l", default="./locales", help="Locale files directory.")
@click.option("--format", "-f", "fmt", default="json", type=click.Choice(["json", "csv"]))
@click.option("--output", "-o", default=None, help="Output file.")
def export_cmd(locales: str, fmt: str, output: str | None) -> None:
    """Export all locale data to a single file."""
    locale_data = parse_all_locales(locales)

    if fmt == "json":
        content = json.dumps(locale_data, indent=2, ensure_ascii=False)
    elif fmt == "csv":
        all_keys = set()
        for data in locale_data.values():
            all_keys.update(data.keys())

        lines = ["key," + ",".join(sorted(locale_data.keys()))]
        for key in sorted(all_keys):
            values = []
            for locale in sorted(locale_data.keys()):
                val = locale_data[locale].get(key, "")
                # Escape CSV
                val = val.replace('"', '""')
                if "," in val or '"' in val or "\n" in val:
                    val = f'"{val}"'
                values.append(val)
            lines.append(f"{key},{','.join(values)}")
        content = "\n".join(lines)
    else:
        content = ""

    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(content)
        console.print(f"[green]Exported to {output}[/]")
    else:
        click.echo(content)


if __name__ == "__main__":
    cli()
