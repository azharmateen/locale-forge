# Locale Forge

[![Built with Claude Code](https://img.shields.io/badge/Built%20with-Claude%20Code-blue?logo=anthropic&logoColor=white)](https://claude.ai/code)


**Your i18n keys are a mess.** Some are in the code but not translated. Some are translated but no longer used. Some have broken placeholders. Locale Forge finds all of it.

```
$ locale-forge scan ./src --locales ./locales

Found 247 translation keys in source code
Found 4 locales: de, en, es, fr

Translation Coverage
┌────────┬────────────┬─────────┬────────┬──────────┐
│ Locale │ Translated │ Missing │ Unused │ Coverage │
├────────┼────────────┼─────────┼────────┼──────────┤
│ en     │ 247        │ 0       │ 12     │ 100.0%   │
│ es     │ 231        │ 16      │ 12     │ 93.5%    │
│ fr     │ 198        │ 49      │ 12     │ 80.2%    │
│ de     │ 180        │ 67      │ 12     │ 72.9%    │
└────────┴────────────┴─────────┴────────┴──────────┘

$ locale-forge validate --locales ./locales

ERROR (3):
  es/checkout.total: Missing placeholders: amount, currency
  fr/auth.welcome: HTML tag mismatch
  de/settings.bio: Translation is empty

WARNING (5):
  es/nav.home: Translation identical to source (possibly untranslated)
```

## Why Locale Forge?

- **Multi-framework** - React (i18next), Vue ($t), Angular, Svelte, Python (gettext), Ruby (I18n), Flutter (ARB)
- **Multi-format** - JSON (flat/nested), YAML, .properties, .po/.pot, .arb
- **Finds missing keys** - in code but not in locale files
- **Finds unused keys** - in locale files but not in code
- **Validates** - placeholder consistency, HTML tag balance, empty translations, length limits
- **Auto-sync** - add missing keys with TODO placeholders, remove unused keys, sort alphabetically

## Install

```bash
pip install locale-forge
```

## Quick Start

```bash
# Scan and show coverage
locale-forge scan ./src --locales ./locales

# Find missing translations
locale-forge missing ./src --locales ./locales

# Find unused translations
locale-forge unused ./src --locales ./locales

# Validate placeholder consistency
locale-forge validate --locales ./locales

# Auto-sync: add missing keys, sort
locale-forge sync ./src --locales ./locales

# Sync with cleanup
locale-forge sync ./src --locales ./locales --remove-unused

# Export all to single JSON
locale-forge export --locales ./locales -o translations.json
```

## Commands

| Command | Description |
|---------|-------------|
| `locale-forge scan <src> -l <locales>` | Coverage report |
| `locale-forge missing <src> -l <locales>` | Keys in code but not translated |
| `locale-forge unused <src> -l <locales>` | Keys in locales but not in code |
| `locale-forge validate -l <locales>` | Validate placeholders, HTML, etc. |
| `locale-forge sync <src> -l <locales>` | Auto-add missing, sort keys |
| `locale-forge export -l <locales> -f json` | Export to JSON/CSV |

## Supported Frameworks

| Framework | Pattern | Example |
|-----------|---------|---------|
| i18next / React | `t("key")` | `t("auth.login.title")` |
| Vue i18n | `$t("key")` | `$t("nav.home")` |
| React Intl | `<FormattedMessage id="key" />` | `formatMessage({id: "btn.submit"})` |
| Python gettext | `_("key")` | `gettext("welcome")` |
| Ruby I18n | `I18n.t("key")` | `t(:hello)` |
| Flutter | `AppLocalizations.of(context)!.key` | `AppLocalizations.of(context)!.title` |
| Svelte | `$_("key")` | `$_("page.title")` |
| Angular | `translate.instant("key")` | `'key' \| translate` |

## Supported Locale Formats

| Format | Extensions | Example |
|--------|-----------|---------|
| JSON (flat/nested) | `.json` | `{"auth": {"login": "Log in"}}` |
| YAML | `.yml`, `.yaml` | Rails-style with locale key |
| Properties | `.properties` | `auth.login=Log in` |
| Gettext | `.po`, `.pot` | `msgid/msgstr` pairs |
| Flutter ARB | `.arb` | JSON with `@` metadata |

## Validation Checks

- **Placeholder consistency** - `{name}`, `{{name}}`, `%{name}`, `%s` must match source
- **HTML tag balance** - opening/closing tags must match between source and target
- **Empty translations** - flags empty strings where source has content
- **Untranslated** - flags translations identical to source
- **Length limits** - optional max character length check
- **Whitespace** - leading/trailing whitespace mismatches

## License

MIT
