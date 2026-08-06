#!/usr/bin/env python3
"""Read-only, bounded inspection for Apple localization resources.

The tool intentionally never writes catalogs and never prints their full contents.
It supports compact inventory, targeted lookup, key-level git diff, and validation for
.xcstrings, .strings, and .stringsdict files.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


SUPPORTED_SUFFIXES = {".xcstrings", ".strings", ".stringsdict"}
EXCLUDED_DIRS = {
    ".git",
    ".build",
    ".swiftpm",
    "build",
    "DerivedData",
    "Pods",
    "Carthage",
    "node_modules",
    "vendor",
    "Vendor",
    "Generated",
    "generated",
}
STRINGS_ENTRY_RE = re.compile(
    r'"((?:\\.|[^"\\])*)"\s*(?:=\s*"((?:\\.|[^"\\])*)"\s*)?;', re.DOTALL
)
COMMENT_RE = re.compile(r"/\*.*?\*/|//[^\n]*", re.DOTALL)
STRINGSDICT_VARIABLE_RE = re.compile(r"%(?:\d+\$)?#@([^@]+)@")


@dataclass
class ParsedFile:
    path: str
    kind: str
    entries: dict[str, Any]
    source_language: str | None = None
    locales: set[str] = field(default_factory=set)
    duplicates: list[str] = field(default_factory=list)
    variation_keys: set[str] = field(default_factory=set)
    extraction_states: Counter[str] = field(default_factory=Counter)
    metadata: dict[str, Any] = field(default_factory=dict)
    entry_order: list[str] = field(default_factory=list)


class CatalogError(RuntimeError):
    pass


class UniquePlistDict(dict[Any, Any]):
    def __setitem__(self, key: Any, value: Any) -> None:
        if key in self:
            raise CatalogError(f"duplicate plist key: {quoted(str(key))}")
        super().__setitem__(key, value)


def compact(value: str, limit: int = 120) -> str:
    value = " ".join(value.split())
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 1)] + "…"


def bounded(value: str, limit: int = 500) -> str:
    if len(value) <= limit:
        return value
    digest = hashlib.sha256(value.encode("utf-8", errors="surrogatepass")).hexdigest()[:12]
    return f"{value[:limit]}…<len={len(value)} sha256={digest}>"


def quoted(value: str, limit: int = 200) -> str:
    rendered = json.dumps(bounded(value, limit), ensure_ascii=False)
    return rendered.encode("utf-8", errors="backslashreplace").decode("utf-8")


def render_atoms(values: Iterable[str], max_items: int = 12) -> str:
    items = sorted(str(value) for value in values)
    rendered = [quoted(value, 60) for value in items[:max_items]]
    if len(items) > max_items:
        rendered.append(f"…(+{len(items) - max_items})")
    return ",".join(rendered) or "-"


def render_counts(values: Counter[str], max_items: int = 12) -> str:
    items = sorted((str(key), count) for key, count in values.items())
    rendered = [f"{quoted(key, 60)}:{count}" for key, count in items[:max_items]]
    if len(items) > max_items:
        rendered.append(f"…(+{len(items) - max_items})")
    return ",".join(rendered) or "none"


def excluded(path: Path) -> bool:
    return any(part in EXCLUDED_DIRS for part in path.parts)


def assert_safe_current_path(path: Path, root: Path) -> None:
    root = root.resolve()
    try:
        relative = path.relative_to(root)
    except ValueError as error:
        raise CatalogError(f"resource path is outside --root: {quoted(str(path))}") from error
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise CatalogError(f"symlink component is not allowed in localization path: {quoted(str(cursor))}")
    if path.exists():
        try:
            path.resolve(strict=True).relative_to(root)
        except (OSError, ValueError) as error:
            raise CatalogError(f"resource resolves outside --root: {quoted(str(path))}") from error


def discover(root: Path) -> list[Path]:
    root = root.resolve()
    found: list[Path] = []

    def walk_error(error: OSError) -> None:
        raise CatalogError(f"cannot scan {quoted(str(error.filename or root))}: {error.strerror or error}")

    for current, dirs, files in os.walk(root, followlinks=False, onerror=walk_error):
        current_path = Path(current)
        candidate_dirs = sorted(d for d in dirs if d not in EXCLUDED_DIRS)
        for directory in candidate_dirs:
            candidate = current_path / directory
            if candidate.is_symlink():
                raise CatalogError(f"symlink directory is not allowed under --root: {quoted(str(candidate))}")
        dirs[:] = candidate_dirs
        for name in sorted(files):
            path = current_path / name
            if path.suffix not in SUPPORTED_SUFFIXES or excluded(path.relative_to(root)):
                continue
            assert_safe_current_path(path, root)
            try:
                resolved = path.resolve(strict=True)
                resolved.relative_to(root)
            except (OSError, ValueError) as error:
                raise CatalogError(f"localization resource escapes or cannot resolve under --root: {quoted(str(path))}") from error
            found.append(path)
    return found


def decode_text(data: bytes) -> str:
    encodings: list[str] = []
    if data.startswith((b"\xff\xfe\x00\x00", b"\x00\x00\xfe\xff")):
        encodings.append("utf-32")
    elif data.startswith((b"\xff\xfe", b"\xfe\xff")):
        encodings.append("utf-16")
    else:
        even_nuls = data[0::2].count(0)
        odd_nuls = data[1::2].count(0)
        if odd_nuls > even_nuls and odd_nuls > len(data) // 8:
            encodings.append("utf-16-le")
        elif even_nuls > odd_nuls and even_nuls > len(data) // 8:
            encodings.append("utf-16-be")
    encodings.extend(["utf-8-sig", "mac_roman"])
    for encoding in encodings:
        try:
            return data.decode(encoding)
        except UnicodeError:
            continue
    raise CatalogError("unsupported text encoding")


def strip_comments(text: str) -> str:
    output: list[str] = []
    index = 0
    state = "normal"
    while index < len(text):
        char = text[index]
        nxt = text[index + 1] if index + 1 < len(text) else ""
        if state == "normal":
            if char == '"':
                state = "string"
                output.append(char)
            elif char == "/" and nxt == "*":
                state = "block"
                output.extend("  ")
                index += 1
            elif char == "/" and nxt == "/":
                state = "line"
                output.extend("  ")
                index += 1
            else:
                output.append(char)
        elif state == "string":
            output.append(char)
            if char == "\\" and index + 1 < len(text):
                output.append(text[index + 1])
                index += 1
            elif char == '"':
                state = "normal"
        elif state == "block":
            if char == "*" and nxt == "/":
                output.extend("  ")
                index += 1
                state = "normal"
            else:
                output.append("\n" if char == "\n" else " ")
        else:  # line comment
            if char == "\n":
                output.append(char)
                state = "normal"
            else:
                output.append(" ")
        index += 1
    if state == "block":
        raise CatalogError("unterminated block comment")
    if state == "string":
        raise CatalogError("unterminated quoted string")
    return "".join(output)


def unescape_strings_token(token: str) -> str:
    result: list[str] = []
    index = 0
    simple = {
        "a": "\a",
        "b": "\b",
        "f": "\f",
        "n": "\n",
        "r": "\r",
        "t": "\t",
        "v": "\v",
        '"': '"',
        "'": "'",
        "?": "?",
        "\\": "\\",
    }
    while index < len(token):
        if token[index] != "\\" or index + 1 >= len(token):
            result.append(token[index])
            index += 1
            continue
        marker = token[index + 1]
        if marker in simple:
            result.append(simple[marker])
            index += 2
            continue
        if marker in "01234567":
            end = index + 1
            while end < min(len(token), index + 4) and token[end] in "01234567":
                end += 1
            result.append(chr(int(token[index + 1 : end], 8)))
            index = end
            continue
        if marker in {"u", "U"}:
            width = 4
            digits = token[index + 2 : index + 2 + width]
            if len(digits) == width and all(c in "0123456789abcdefABCDEF" for c in digits):
                codepoint = int(digits, 16)
                next_index = index + 2 + width
                if 0xD800 <= codepoint <= 0xDBFF:
                    next_digits = token[next_index + 2 : next_index + 6]
                    if (
                        token[next_index : next_index + 2] in {"\\u", "\\U"}
                        and len(next_digits) == 4
                        and all(c in "0123456789abcdefABCDEF" for c in next_digits)
                        and 0xDC00 <= int(next_digits, 16) <= 0xDFFF
                    ):
                        low = int(next_digits, 16)
                        result.append(chr(0x10000 + ((codepoint - 0xD800) << 10) + (low - 0xDC00)))
                        index = next_index + 6
                        continue
                    raise CatalogError("unpaired high surrogate in .strings escape")
                if 0xDC00 <= codepoint <= 0xDFFF:
                    raise CatalogError("unpaired low surrogate in .strings escape")
                result.append(chr(codepoint))
                index = next_index
                continue
        result.append(marker)
        index += 2
    return "".join(result)


def parse_strings(data: bytes, label: str) -> ParsedFile:
    locale = locale_from_path(label)
    decoded_text: str | None = None
    is_property_list = data.startswith(b"bplist00")
    if not is_property_list:
        try:
            decoded_text = decode_text(data)
        except CatalogError:
            decoded_text = None
        is_property_list = bool(decoded_text and decoded_text.lstrip().startswith(("<?xml", "<plist")))
    if is_property_list:
        try:
            plist = plistlib.loads(data, dict_type=UniquePlistDict)
        except Exception as error:
            raise CatalogError(f"invalid property-list .strings: {error}") from error
        if not isinstance(plist, dict) or not all(isinstance(key, str) and isinstance(value, str) for key, value in plist.items()):
            raise CatalogError("property-list .strings must be a string-to-string dictionary")
        return ParsedFile(
            path=label,
            kind="strings",
            entries={key: {"value": value} for key, value in plist.items()},
            locales={locale} if locale else set(),
            entry_order=list(plist),
        )
    raw_text = decoded_text if decoded_text is not None else decode_text(data)
    text = strip_comments(raw_text)
    entries: dict[str, Any] = {}
    duplicates: list[str] = []
    entry_order: list[str] = []
    previous_end = 0
    for match in STRINGS_ENTRY_RE.finditer(text):
        key = unescape_strings_token(match.group(1))
        value = unescape_strings_token(match.group(2)) if match.group(2) is not None else key
        comments = [comment.strip() for comment in COMMENT_RE.findall(raw_text[previous_end : match.start()])]
        format_signature = re.sub(r'"(?:\\.|[^"\\])*"', '"<STRING>"', match.group(0))
        if key in entries:
            duplicates.append(key)
        entries[key] = {
            "value": value,
            "comment": "\n".join(comments),
            "_format": format_signature,
        }
        entry_order.append(key)
        previous_end = match.end()
    if entry_order:
        trailing_comments = [comment.strip() for comment in COMMENT_RE.findall(raw_text[previous_end:])]
        if trailing_comments:
            last_entry = entries[entry_order[-1]]
            existing_comment = str(last_entry.get("comment", ""))
            last_entry["comment"] = "\n".join(
                value for value in (existing_comment, "\n".join(trailing_comments)) if value
            )
    residual = STRINGS_ENTRY_RE.sub("", text)
    if residual.strip():
        line = residual[: residual.find(residual.lstrip())].count("\n") + 1
        raise CatalogError(f"unparsed or malformed content near line {line}")
    if text.strip() and not entries:
        raise CatalogError("no valid key/value entries found")
    return ParsedFile(
        path=label,
        kind="strings",
        entries=entries,
        locales={locale} if locale else set(),
        duplicates=duplicates,
        entry_order=entry_order,
    )


def parse_stringsdict(data: bytes, label: str) -> ParsedFile:
    try:
        plist = plistlib.loads(data, dict_type=UniquePlistDict)
    except Exception as error:  # plistlib exposes multiple parse exceptions
        raise CatalogError(f"invalid plist: {error}") from error
    if not isinstance(plist, dict):
        raise CatalogError("top-level stringsdict value is not a dictionary")
    for key, entry in plist.items():
        if not isinstance(entry, dict):
            raise CatalogError(f"{quoted(str(key))}: entry is not a dictionary")
        format_value = entry.get("NSStringLocalizedFormatKey")
        if not isinstance(format_value, str):
            raise CatalogError(f"{quoted(str(key))}: missing NSStringLocalizedFormatKey")
        variable_names = STRINGSDICT_VARIABLE_RE.findall(format_value)
        if not variable_names:
            raise CatalogError(f"{quoted(str(key))}: format key has no %#@variable@ reference")
        for variable_name in variable_names:
            variable = entry.get(variable_name)
            if not isinstance(variable, dict):
                raise CatalogError(f"{quoted(str(key))}: missing variable dictionary {quoted(variable_name)}")
            rule_type = variable.get("NSStringFormatSpecTypeKey")
            value_type = variable.get("NSStringFormatValueTypeKey")
            if not isinstance(rule_type, str) or not isinstance(value_type, str) or not value_type:
                raise CatalogError(f"{quoted(str(key))}: incomplete format spec for {quoted(variable_name)}")
            if rule_type == "NSStringPluralRuleType" and not isinstance(variable.get("other"), str):
                raise CatalogError(f"{quoted(str(key))}: plural variable {quoted(variable_name)} has no string 'other' form")
    locale = locale_from_path(label)
    return ParsedFile(
        path=label,
        kind="stringsdict",
        entries={str(key): value for key, value in plist.items()},
        locales={locale} if locale else set(),
        variation_keys={str(key) for key in plist},
        entry_order=[str(key) for key in plist],
    )


def contains_key_recursively(value: Any, wanted: str) -> bool:
    if isinstance(value, dict):
        return wanted in value or any(contains_key_recursively(item, wanted) for item in value.values())
    if isinstance(value, list):
        return any(contains_key_recursively(item, wanted) for item in value)
    return False


def collect_string_units(value: Any, prefix: str = "") -> list[tuple[str, str]]:
    units: list[tuple[str, str]] = []
    if isinstance(value, dict):
        if isinstance(value.get("value"), str) and ("state" in value or prefix.endswith("stringUnit")):
            units.append((prefix or "stringUnit", value["value"]))
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            units.extend(collect_string_units(child, child_prefix))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            units.extend(collect_string_units(child, f"{prefix}[{index}]"))
    return units


def parse_xcstrings(data: bytes, label: str) -> ParsedFile:
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise CatalogError(f"duplicate JSON object key: {quoted(key)}")
            result[key] = value
        return result

    try:
        document = json.loads(data.decode("utf-8-sig"), object_pairs_hook=unique_object)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise CatalogError(f"invalid JSON: {error}") from error
    if not isinstance(document, dict):
        raise CatalogError("top-level xcstrings value is not an object")
    strings = document.get("strings")
    if not isinstance(strings, dict):
        raise CatalogError("missing top-level strings dictionary")
    source_language = document.get("sourceLanguage")
    if source_language is not None and not isinstance(source_language, str):
        raise CatalogError("sourceLanguage is not a string")
    version = document.get("version")
    if not isinstance(version, str):
        raise CatalogError("version is not a string")
    locales: set[str] = set()
    variations: set[str] = set()
    states: Counter[str] = Counter()
    for key, entry in strings.items():
        if not isinstance(entry, dict):
            raise CatalogError(f"entry {quoted(str(key))} is not an object")
        localizations = entry.get("localizations", {})
        if not isinstance(localizations, dict):
            raise CatalogError(f"entry {quoted(str(key))} localizations is not an object")
        for locale, payload in localizations.items():
            if not isinstance(payload, dict):
                raise CatalogError(
                    f"entry {quoted(str(key))} locale {quoted(str(locale))} payload is not an object"
                )
            locales.add(str(locale))
        extraction_state = entry.get("extractionState", "unspecified")
        if not isinstance(extraction_state, str):
            raise CatalogError(f"entry {quoted(str(key))} extractionState is not a string")
        if contains_key_recursively(entry, "variations") or contains_key_recursively(entry, "substitutions"):
            variations.add(str(key))
        states[extraction_state] += 1
    metadata = {key: value for key, value in document.items() if key != "strings"}
    return ParsedFile(
        path=label,
        kind="xcstrings",
        entries={str(key): value for key, value in strings.items()},
        source_language=source_language,
        locales=locales,
        variation_keys=variations,
        extraction_states=states,
        metadata=metadata,
        entry_order=[str(key) for key in strings],
    )


def parse_blob(data: bytes, label: str) -> ParsedFile:
    suffix = Path(label).suffix
    if suffix == ".xcstrings":
        return parse_xcstrings(data, label)
    if suffix == ".strings":
        return parse_strings(data, label)
    if suffix == ".stringsdict":
        return parse_stringsdict(data, label)
    raise CatalogError(f"unsupported suffix: {suffix}")


def parse_path(path: Path, root: Path) -> ParsedFile:
    return parse_blob(path.read_bytes(), path.relative_to(root).as_posix())


def locale_from_path(label: str) -> str | None:
    for part in Path(label).parts:
        if part.endswith(".lproj"):
            return part[: -len(".lproj")]
    return None


def logical_legacy_path(label: str) -> str:
    parts = list(Path(label).parts)
    for index, part in enumerate(parts):
        if part.endswith(".lproj"):
            parts[index] = "{locale}.lproj"
            break
    return Path(*parts).as_posix()


def key_shape(keys: Iterable[str]) -> str:
    keys = list(keys)
    if not keys:
        return "empty"
    opaque = sum(bool(re.fullmatch(r"[A-Za-z0-9_.-]+", key)) for key in keys)
    ratio = opaque / len(keys)
    if ratio >= 0.8:
        return "identifier-like"
    if ratio <= 0.2:
        return "sentence-like"
    return "mixed"


def load_current(root: Path) -> tuple[list[ParsedFile], list[str]]:
    parsed: list[ParsedFile] = []
    errors: list[str] = []
    for path in discover(root):
        try:
            parsed.append(parse_path(path, root))
        except (OSError, CatalogError) as error:
            errors.append(
                f"path={quoted(path.relative_to(root).as_posix())} error={quoted(str(error), 240)}"
            )
    return parsed, errors


def inventory(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    parsed, errors = load_current(root)
    legacy: dict[tuple[str, str], list[ParsedFile]] = defaultdict(list)
    catalog_count = 0
    total_keys = 0
    catalog_lines: list[str] = []
    for item in parsed:
        if item.kind == "xcstrings":
            catalog_count += 1
            total_keys += len(item.entries)
            states = render_counts(item.extraction_states)
            samples = sorted(item.entries)[: min(args.samples, args.limit)]
            line = (
                f"CATALOG type=xcstrings path={quoted(item.path)} keys={len(item.entries)} "
                f"source={quoted(item.source_language or '-')} locales={render_atoms(item.locales)} "
                f"variations={len(item.variation_keys)} keyShape={key_shape(item.entries)} states={states}"
            )
            if samples:
                line += " samples=" + ",".join(quoted(key) for key in samples)
            catalog_lines.append(line)
        else:
            legacy[(item.kind, logical_legacy_path(item.path))].append(item)
    for (kind, logical_path), files in sorted(legacy.items()):
        catalog_count += 1
        union = set().union(*(set(item.entries) for item in files))
        total_keys += len(union)
        locales = set().union(*(item.locales for item in files))
        duplicate_count = sum(len(item.duplicates) for item in files)
        samples = sorted(union)[: min(args.samples, args.limit)]
        count_items = [
            f"{quoted(next(iter(item.locales), '-'), 60)}:{len(item.entries)}"
            for item in sorted(files, key=lambda value: value.path)
        ]
        counts = ",".join(count_items[:12])
        if len(count_items) > 12:
            counts += f",…(+{len(count_items) - 12})"
        line = (
            f"CATALOG type={kind} path={quoted(logical_path)} files={len(files)} keys={len(union)} "
            f"locales={render_atoms(locales)} perLocale={counts or '-'} "
            f"duplicates={duplicate_count} keyShape={key_shape(union)}"
        )
        if samples:
            line += " samples=" + ",".join(quoted(key) for key in samples)
        catalog_lines.append(line)
    for line in catalog_lines[: args.limit]:
        print(bounded(line, 500))
    if len(catalog_lines) > args.limit:
        print(f"CATALOGS_TRUNCATED total={len(catalog_lines)} shown={args.limit}; narrow --root to the owning scope")
    for error in errors[: args.limit]:
        print(bounded(f"ERROR {error}", 500))
    if len(errors) > args.limit:
        print(f"ERRORS_TRUNCATED total={len(errors)} shown={args.limit}")
    print(f"TOTAL catalogs={catalog_count} files={len(parsed)} uniqueKeysApprox={total_keys} parseErrors={len(errors)}")
    return 1 if errors else 0


def values_for_xc_entry(entry: Any) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    if not isinstance(entry, dict):
        return result
    localizations = entry.get("localizations", {})
    if not isinstance(localizations, dict):
        return result
    for locale, payload in localizations.items():
        result[str(locale)] = [value for _, value in collect_string_units(payload)]
    return result


def stringsdict_values(value: Any) -> list[str]:
    values: list[str] = []
    if isinstance(value, dict):
        for field, child in value.items():
            if str(field).startswith("NSString"):
                continue
            values.extend(stringsdict_values(child))
    elif isinstance(value, list):
        for child in value:
            values.extend(stringsdict_values(child))
    elif isinstance(value, str):
        values.append(value)
    return values


def source_values(item: ParsedFile, key: str, source_locale: str | None = None) -> list[str]:
    entry = item.entries[key]
    if item.kind == "xcstrings":
        values = values_for_xc_entry(entry)
        locale = source_locale or item.source_language
        if locale and values.get(locale):
            return values[locale]
        return [key]
    if item.kind == "strings":
        return [str(entry.get("value", key))]
    if item.kind == "stringsdict":
        return stringsdict_values(entry) or [key]
    return [key]


def entry_kind(item: ParsedFile, key: str) -> str:
    if item.kind == "stringsdict" or key in item.variation_keys:
        return "variation"
    return "simple"


def read_list_file(path: Path | None) -> list[str]:
    if path is None:
        return []
    text = path.read_text(encoding="utf-8-sig")
    if text.lstrip().startswith("["):
        value = json.loads(text)
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise CatalogError(f"{path}: expected a JSON array of strings")
        return value
    return [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]


def build_groups(parsed: list[ParsedFile]) -> list[tuple[str, str, list[ParsedFile]]]:
    groups: list[tuple[str, str, list[ParsedFile]]] = []
    legacy: dict[tuple[str, str], list[ParsedFile]] = defaultdict(list)
    for item in parsed:
        if item.kind == "xcstrings":
            groups.append((item.kind, item.path, [item]))
        else:
            legacy[(item.kind, logical_legacy_path(item.path))].append(item)
    groups.extend((kind, logical, files) for (kind, logical), files in sorted(legacy.items()))
    return sorted(groups, key=lambda value: (value[1], value[0]))


def representative_for_key(files: list[ParsedFile], key: str, source_locale: str | None) -> ParsedFile:
    if source_locale:
        selected = next((item for item in files if key in item.entries and source_locale in item.locales), None)
        if selected is not None:
            return selected
    return next(item for item in files if key in item.entries)


def source_representative_for_key(
    files: list[ParsedFile], key: str, source_locale: str | None
) -> ParsedFile | None:
    if files[0].kind == "xcstrings" or not source_locale:
        return representative_for_key(files, key, source_locale)
    return next((item for item in files if key in item.entries and source_locale in item.locales), None)


def lookup(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    parsed, errors = load_current(root)
    if errors:
        for error in errors[: args.limit]:
            print(bounded(f"ERROR {error}", 500))
        return 1
    keys = set(args.key or []) | set(read_list_file(args.keys_file))
    values = set(args.value or []) | set(read_list_file(args.values_file))
    contains = [value.casefold() for value in (args.contains or [])]
    if not keys and not values and not contains:
        raise CatalogError("lookup requires --key/--keys-file, --value/--values-file, or --contains")
    matches: list[tuple[str, str, str, list[ParsedFile]]] = []
    match_count = 0
    key_match_counts: Counter[str] = Counter()
    value_match_counts: Counter[str] = Counter()
    for kind, logical, files in build_groups(parsed):
        union = set().union(*(set(item.entries) for item in files))
        for key in sorted(union):
            representative = representative_for_key(files, key, args.source_locale)
            source_representative = source_representative_for_key(files, key, args.source_locale)
            sources = source_values(source_representative, key, args.source_locale) if source_representative else [key]
            haystack = f"{key}\n" + "\n".join(sources)
            matched_values = values.intersection(sources)
            if key in keys:
                key_match_counts[key] += 1
            for value in matched_values:
                value_match_counts[value] += 1
            if key in keys or matched_values or any(needle in haystack.casefold() for needle in contains):
                match_count += 1
                if len(matches) < args.limit:
                    matches.append((kind, logical, key, files))
    shown = matches
    for kind, logical, key, files in shown:
        locales: set[str] = set()
        representative = representative_for_key(files, key, args.source_locale)
        values_by_locale: dict[str, list[str]] = {}
        comment = ""
        state = "-"
        if kind == "xcstrings":
            entry = representative.entries[key]
            values_by_locale = values_for_xc_entry(entry)
            locales.update(values_by_locale)
            if isinstance(entry, dict):
                comment = str(entry.get("comment", ""))
                state = str(entry.get("extractionState", "unspecified"))
        else:
            for item in files:
                if key not in item.entries:
                    continue
                locale = next(iter(item.locales), "-")
                locales.add(locale)
                if kind == "strings":
                    values_by_locale[locale] = [str(item.entries[key].get("value", ""))]
                elif kind == "stringsdict":
                    values_by_locale[locale] = stringsdict_values(item.entries[key])
        fields = [
            f"MATCH catalog={quoted(logical)}",
            f"type={kind}",
            f"key={quoted(key)}",
            f"kind={entry_kind(representative, key)}",
            f"locales={render_atoms(locales)}",
            f"state={quoted(state, 60)}",
        ]
        if comment:
            fields.append(f"comment={quoted(compact(comment))}")
        if args.show_values:
            wanted_locales = set(args.locale or [])
            if not wanted_locales:
                if args.source_locale:
                    wanted_locales.add(args.source_locale)
                elif representative.source_language:
                    wanted_locales.add(representative.source_language)
            rendered: list[str] = []
            for locale in sorted(wanted_locales)[: args.limit]:
                locale_values = values_by_locale.get(locale, [])
                if locale_values:
                    value_items = [quoted(value, 120) for value in locale_values[:12]]
                    if len(locale_values) > 12:
                        value_items.append(f"…(+{len(locale_values) - 12})")
                    rendered.append(f"{quoted(locale, 60)}:[{','.join(value_items)}]")
            if len(wanted_locales) > args.limit:
                rendered.append(f"…(+{len(wanted_locales) - args.limit} locales)")
            fields.append("values=" + (";".join(rendered) if rendered else "-"))
        print(bounded(" ".join(fields), 800))
    if match_count > args.limit:
        print(f"MATCHES_TRUNCATED total={match_count} shown={args.limit}; refine the query or raise --limit deliberately")
    query_details: list[str] = []
    for key in sorted(keys):
        if key_match_counts[key] == 0:
            query_details.append(f"MISSING_KEY {quoted(key)}")
        elif key_match_counts[key] > 1:
            query_details.append(f"AMBIGUOUS_KEY {quoted(key)} matches={key_match_counts[key]}")
    for value in sorted(values):
        if value_match_counts[value] == 0:
            query_details.append(f"MISSING_VALUE {quoted(value)}")
        elif value_match_counts[value] > 1:
            query_details.append(f"AMBIGUOUS_VALUE {quoted(value)} matches={value_match_counts[value]}")
    for detail in query_details[: args.limit]:
        print(bounded(detail, 500))
    if len(query_details) > args.limit:
        print(f"QUERY_DETAILS_TRUNCATED total={len(query_details)} shown={args.limit}")
    print(
        f"LOOKUP matches={match_count} shown={len(shown)} catalogs={len(build_groups(parsed))} "
        f"requestedKeys={len(keys)} matchedKeys={sum(count > 0 for count in key_match_counts.values())} "
        f"requestedValues={len(values)} matchedValues={sum(count > 0 for count in value_match_counts.values())}"
    )
    return 2 if match_count > args.limit else 0


def git(root: Path, *arguments: str, check: bool = True) -> bytes:
    process = subprocess.run(
        ["git", "-C", str(root), *arguments],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and process.returncode != 0:
        raise CatalogError(process.stderr.decode("utf-8", errors="replace").strip() or "git command failed")
    return process.stdout


def git_context(root: Path) -> tuple[Path, str]:
    git_root = Path(git(root, "rev-parse", "--show-toplevel").decode().strip()).resolve()
    try:
        scope = root.resolve().relative_to(git_root).as_posix()
    except ValueError as error:
        raise CatalogError(f"root {root} is outside git worktree {git_root}") from error
    return git_root, "" if scope == "." else scope


def base_localization_paths(git_root: Path, scope: str, base: str) -> set[str]:
    arguments = ["ls-tree", "-r", "-z", "--name-only", base]
    if scope:
        arguments.extend(["--", scope])
    lines = [os.fsdecode(value) for value in git(git_root, *arguments).split(b"\0") if value]
    result = set()
    for line in lines:
        path = Path(line)
        if path.suffix in SUPPORTED_SUFFIXES and not excluded(path):
            result.add(path.as_posix())
    return result


def current_localization_paths(git_root: Path, scope_root: Path) -> set[str]:
    return {path.relative_to(git_root).as_posix() for path in discover(scope_root)}


def git_blob(git_root: Path, revision: str, path: str) -> bytes | None:
    process = subprocess.run(
        ["git", "-C", str(git_root), "show", f"{revision}:{path}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return process.stdout if process.returncode == 0 else None


def changed_entry_fields(before: Any, after: Any) -> str:
    if not isinstance(before, dict) or not isinstance(after, dict):
        return "value"
    fields: list[str] = []
    for key in sorted(set(before) | set(after)):
        if before.get(key) == after.get(key):
            continue
        if key == "localizations" and isinstance(before.get(key), dict) and isinstance(after.get(key), dict):
            locales = sorted(set(before[key]) | set(after[key]))
            changed = [locale for locale in locales if before[key].get(locale) != after[key].get(locale)]
            fields.append("locales:" + ",".join(changed))
        else:
            fields.append(str(key))
    return ",".join(fields) or "value"


def changed_line_count(before: bytes | None, after: bytes | None) -> int:
    if before is None or after is None:
        return len((before or after or b"").splitlines())
    matcher = difflib.SequenceMatcher(None, before.splitlines(), after.splitlines(), autojunk=True)
    return sum(max(old_end - old_start, new_end - new_start) for tag, old_start, old_end, new_start, new_end in matcher.get_opcodes() if tag != "equal")


def normalize_repo_paths(values: Iterable[str]) -> set[str]:
    result: set[str] = set()
    for value in values:
        normalized = value.strip().replace("\\", "/")
        parts = [part for part in normalized.split("/") if part not in {"", "."}]
        if not normalized or normalized.startswith("/") or ".." in parts:
            raise CatalogError(f"expected path must be git-root-relative: {quoted(value)}")
        result.add("/".join(parts))
    return result


def parse_expected_entries(values: Iterable[str]) -> set[tuple[str, str]]:
    result: set[tuple[str, str]] = set()
    for value in values:
        if "::" not in value:
            raise CatalogError(f"expected entry must use REPO_PATH::KEY: {quoted(value)}")
        raw_path, key = value.split("::", 1)
        if not key:
            raise CatalogError(f"expected entry has an empty key: {quoted(value)}")
        path = next(iter(normalize_repo_paths([raw_path])))
        result.add((path, key))
    return result


def diff_command(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    git_root, scope = git_context(root)
    base_paths = base_localization_paths(git_root, scope, args.base)
    current_paths = current_localization_paths(git_root, root)
    expected = set(args.expected_key or []) | set(read_list_file(args.keys_file))
    expected_paths = normalize_repo_paths(set(args.expected_path or []) | set(read_list_file(args.paths_file)))
    expected_added_paths = normalize_repo_paths(
        set(args.expected_added_path or []) | set(read_list_file(args.added_paths_file))
    )
    expected_entries = parse_expected_entries(
        set(args.expected_entry or []) | set(read_list_file(args.entries_file))
    )
    if expected_entries and (expected or expected_paths):
        raise CatalogError("path-qualified expected entries cannot be mixed with global expected keys/paths")
    if expected_entries:
        expected = {key for _, key in expected_entries}
        entry_paths = {path for path, _ in expected_entries}
        expected_paths = entry_paths - expected_added_paths
    if args.expect_no_key_changes and (expected or expected_paths or expected_added_paths or expected_entries):
        raise CatalogError("--expect-no-key-changes cannot be combined with key/path expectations")
    if args.strict and not expected and not args.expect_no_key_changes:
        raise CatalogError("diff --strict requires expected keys or --expect-no-key-changes")
    if args.strict and expected and not (expected_paths or expected_added_paths):
        raise CatalogError("diff --strict with expected keys also requires expected repo-relative paths")
    if args.strict and expected and not expected_entries and len(expected_paths | expected_added_paths) != 1:
        raise CatalogError("strict diff across multiple paths requires path-qualified --expected-entry/--entries-file")
    touched_keys: set[str] = set()
    touched_entries: set[tuple[str, str]] = set()
    removed_keys: set[str] = set()
    unexpected: set[str] = set()
    missing_expected: set[str] = set()
    changed_paths: set[str] = set()
    added_files: set[str] = set()
    deleted_files: set[str] = set()
    raw_only_files: set[str] = set()
    unexpected_paths: set[str] = set()
    missing_expected_paths: set[str] = set()
    failures: list[str] = []
    changed_files = 0
    detail_emitted = 0
    detail_total = 0

    def emit_detail(line: str) -> None:
        nonlocal detail_emitted, detail_total
        detail_total += 1
        if detail_emitted < args.limit:
            print(bounded(line, 500))
            detail_emitted += 1

    for path in sorted(base_paths | current_paths):
        before_bytes = git_blob(git_root, args.base, path) if path in base_paths else None
        current_path = git_root / path
        assert_safe_current_path(current_path, root)
        after_bytes = current_path.read_bytes() if current_path.exists() else None
        if before_bytes == after_bytes:
            continue
        changed_files += 1
        changed_paths.add(path)
        file_added = before_bytes is None
        file_deleted = after_bytes is None
        if file_added:
            added_files.add(path)
        if file_deleted:
            deleted_files.add(path)
        try:
            before = parse_blob(before_bytes, path) if before_bytes is not None else None
            after = parse_blob(after_bytes, path) if after_bytes is not None else None
        except CatalogError as error:
            failures.append(f"path={quoted(path)} error={quoted(str(error), 240)}")
            continue
        before_entries = before.entries if before else {}
        after_entries = after.entries if after else {}
        added = sorted(set(after_entries) - set(before_entries))
        removed = sorted(set(before_entries) - set(after_entries))
        changed = sorted(
            key for key in set(before_entries) & set(after_entries) if before_entries[key] != after_entries[key]
        )
        meta_changed = bool(before and after and before.metadata != after.metadata)
        common_keys = set(before_entries) & set(after_entries)
        before_common_order = [key for key in before.entry_order if key in common_keys] if before else []
        after_common_order = [key for key in after.entry_order if key in common_keys] if after else []
        order_changed = before_common_order != after_common_order
        format_changed = [
            key
            for key in common_keys
            if isinstance(before_entries[key], dict)
            and isinstance(after_entries[key], dict)
            and before_entries[key].get("_format") != after_entries[key].get("_format")
        ]
        removed_comments = [
            key
            for key in common_keys
            if isinstance(before_entries[key], dict)
            and isinstance(after_entries[key], dict)
            and before_entries[key].get("comment")
            and not after_entries[key].get("comment")
        ]
        raw_changed_lines = changed_line_count(before_bytes, after_bytes)
        semantic_change_count = len(added) + len(removed) + len(changed) + int(meta_changed)
        disproportionate_raw_churn = bool(
            before is not None
            and after is not None
            and semantic_change_count
            and raw_changed_lines > max(80, semantic_change_count * 120)
        )
        raw_only_changed = not (added or removed or changed or meta_changed)
        touched_keys.update(added + removed + changed)
        touched_entries.update((path, key) for key in added + removed + changed)
        removed_keys.update(removed)
        emit_detail(
            f"FILE path={quoted(path)} added={len(added)} changed={len(changed)} removed={len(removed)} "
            f"metadataChanged={'yes' if meta_changed else 'no'} rawOnlyChanged={'yes' if raw_only_changed else 'no'} "
            f"orderChanged={'yes' if order_changed else 'no'} rawChangedLines={raw_changed_lines} "
            f"lifecycle={'added' if file_added else ('deleted' if file_deleted else 'existing')}"
        )
        for prefix, keys in (("+", added), ("-", removed)):
            for key in keys:
                emit_detail(f"{prefix} {quoted(key)}")
        for key in changed:
            emit_detail(
                f"~ {quoted(key)} fields={quoted(changed_entry_fields(before_entries[key], after_entries[key]))}"
            )
        if meta_changed:
            failures.append(f"path={quoted(path)} catalog-level metadata changed")
        if order_changed:
            failures.append(f"path={quoted(path)} relative order of existing localization keys changed")
        for key in sorted(format_changed):
            failures.append(f"path={quoted(path)} key={quoted(key)} raw entry formatting changed")
        for key in sorted(removed_comments):
            failures.append(f"path={quoted(path)} key={quoted(key)} translator comment removed")
        if disproportionate_raw_churn:
            failures.append(
                f"path={quoted(path)} raw changed lines ({raw_changed_lines}) are disproportionate to semantic changes ({semantic_change_count})"
            )
        if raw_only_changed:
            raw_only_files.add(path)
            failures.append(f"path={quoted(path)} bytes changed without a key/metadata delta (comments or raw rewrite)")
        if file_deleted:
            failures.append(f"path={quoted(path)} localization file deleted")
        if file_added and path not in expected_added_paths:
            failures.append(f"path={quoted(path)} localization file added without --expected-added-path")
        if file_added and not added:
            failures.append(f"path={quoted(path)} added localization file has no entries")

    unexpected = touched_keys - expected
    missing_expected = expected - touched_keys
    unexpected_entries = touched_entries - expected_entries if expected_entries else set()
    missing_expected_entries = expected_entries - touched_entries if expected_entries else set()
    allowed_paths = expected_paths | expected_added_paths
    unexpected_paths = changed_paths - allowed_paths
    missing_expected_paths = expected_paths - changed_paths
    missing_expected_added_paths = expected_added_paths - added_files
    for key in sorted(unexpected):
        emit_detail(f"UNEXPECTED_KEY {quoted(key)}")
    for key in sorted(missing_expected):
        emit_detail(f"MISSING_EXPECTED_KEY {quoted(key)}")
    for path, key in sorted(unexpected_entries):
        emit_detail(f"UNEXPECTED_ENTRY path={quoted(path)} key={quoted(key)}")
    for path, key in sorted(missing_expected_entries):
        emit_detail(f"MISSING_EXPECTED_ENTRY path={quoted(path)} key={quoted(key)}")
    for path in sorted(unexpected_paths):
        emit_detail(f"UNEXPECTED_PATH {quoted(path)}")
    for path in sorted(missing_expected_paths):
        emit_detail(f"MISSING_EXPECTED_PATH {quoted(path)}")
    for path in sorted(missing_expected_added_paths):
        emit_detail(f"MISSING_EXPECTED_ADDED_PATH {quoted(path)}")
    for failure in failures:
        emit_detail(f"ERROR {failure}")
    if detail_total > detail_emitted:
        print(f"DETAILS_TRUNCATED total={detail_total} shown={detail_emitted}")
    if changed_files == 0:
        print("NO_LOCALIZATION_CHANGES")
    print(
        f"DIFF files={changed_files} touchedKeys={len(touched_keys)} removedKeys={len(removed_keys)} "
        f"unexpectedKeys={len(unexpected)} missingExpectedKeys={len(missing_expected)} "
        f"unexpectedEntries={len(unexpected_entries)} missingExpectedEntries={len(missing_expected_entries)} "
        f"addedFiles={len(added_files)} deletedFiles={len(deleted_files)} rawOnlyFiles={len(raw_only_files)} "
        f"unexpectedPaths={len(unexpected_paths)} missingExpectedPaths={len(missing_expected_paths) + len(missing_expected_added_paths)} "
        f"errors={len(failures)} base={quoted(args.base)}"
    )
    strict_failure = bool(
        failures
        or removed_keys
        or unexpected
        or missing_expected
        or unexpected_entries
        or missing_expected_entries
        or unexpected_paths
        or missing_expected_paths
        or missing_expected_added_paths
    )
    return 2 if args.strict and strict_failure else (1 if failures else 0)


def changed_current_paths(root: Path, base: str) -> tuple[set[Path], set[str]]:
    git_root, scope = git_context(root)
    base_paths = base_localization_paths(git_root, scope, base)
    current_paths = current_localization_paths(git_root, root)
    result: set[Path] = set()
    deleted: set[str] = set()
    for relative in base_paths | current_paths:
        current = git_root / relative
        assert_safe_current_path(current, root)
        if not current.exists():
            if relative in base_paths:
                deleted.add(relative)
            continue
        before = git_blob(git_root, base, relative) if relative in base_paths else None
        if before != current.read_bytes():
            result.add(current)
    return result, deleted


def validate(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    if args.changed_from:
        paths, deleted_files = changed_current_paths(root, args.changed_from)
    else:
        paths, deleted_files = set(discover(root)), set()
    failures: list[str] = []
    duplicate_count = 0
    total_keys = 0
    xcode_checked = 0
    plutil_checked = 0
    for deleted in sorted(deleted_files):
        failures.append(f"path={quoted(deleted)} localization file deleted; run diff gate")
    xcrun = shutil.which("xcrun")
    if args.xcode and any(path.suffix == ".xcstrings" for path in paths) and not xcrun:
        failures.append("--xcode requested for changed .xcstrings but xcrun is unavailable")
    for path in sorted(paths):
        label = path.relative_to(root).as_posix()
        try:
            parsed = parse_path(path, root)
            total_keys += len(parsed.entries)
            duplicate_count += len(parsed.duplicates)
            if parsed.duplicates:
                failures.append(
                    f"path={quoted(label)} duplicate keys {','.join(quoted(key) for key in parsed.duplicates[:5])}"
                )
            if path.suffix in {".strings", ".stringsdict"} and shutil.which("plutil"):
                process = subprocess.run(
                    ["plutil", "-lint", str(path)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    check=False,
                )
                plutil_checked += 1
                if process.returncode != 0:
                    message = compact(process.stderr.decode("utf-8", errors="replace"), 300)
                    failures.append(f"path={quoted(label)} plutil failed: {quoted(message, 240)}")
            if args.xcode and path.suffix == ".xcstrings" and xcrun:
                with tempfile.TemporaryDirectory(prefix="localization-context-") as output:
                    process = subprocess.run(
                        [
                            "xcrun",
                            "xcstringstool",
                            "compile",
                            str(path),
                            "--output-directory",
                            output,
                            "--dry-run",
                        ],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.PIPE,
                        check=False,
                    )
                xcode_checked += 1
                if process.returncode != 0:
                    message = compact(process.stderr.decode("utf-8", errors="replace"), 300)
                    failures.append(f"path={quoted(label)} xcstringstool failed: {quoted(message, 240)}")
        except (OSError, CatalogError) as error:
            failures.append(f"path={quoted(label)} error={quoted(str(error), 240)}")
    for failure in failures[: args.limit]:
        print(bounded(f"ERROR {failure}", 500))
    if len(failures) > args.limit:
        print(f"ERRORS_TRUNCATED total={len(failures)} shown={args.limit}")
    print(
        f"VALIDATE files={len(paths)} deletedFiles={len(deleted_files)} keys={total_keys} duplicateKeys={duplicate_count} "
        f"plutilChecked={plutil_checked} xcodeChecked={xcode_checked} errors={len(failures)}"
    )
    return 1 if failures else 0


def common_root_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--root", type=Path, required=True, help="Repository root or scoped source directory")
    parser.add_argument("--limit", type=int, default=20, help="Maximum detail rows to emit (default: 20)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compact, read-only inspection of .xcstrings/.strings/.stringsdict without dumping catalogs"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    inventory_parser = subparsers.add_parser("inventory", help="Summarize catalogs without values")
    common_root_argument(inventory_parser)
    inventory_parser.add_argument("--samples", type=int, default=0, help="Sample this many keys per catalog")
    inventory_parser.set_defaults(handler=inventory)

    lookup_parser = subparsers.add_parser("lookup", help="Find only requested keys/source values")
    common_root_argument(lookup_parser)
    lookup_parser.add_argument("--key", action="append", help="Exact key; repeat as needed")
    lookup_parser.add_argument("--keys-file", type=Path, help="Newline list or JSON array of exact keys")
    lookup_parser.add_argument("--value", action="append", help="Exact source value; repeat as needed")
    lookup_parser.add_argument("--values-file", type=Path, help="Newline list or JSON array of source values")
    lookup_parser.add_argument("--contains", action="append", help="Substring in key/source value")
    lookup_parser.add_argument("--source-locale", help="Source locale for legacy tables or override")
    lookup_parser.add_argument("--locale", action="append", help="Locale whose value may be shown")
    lookup_parser.add_argument("--show-values", action="store_true", help="Show only selected/source locale values")
    lookup_parser.set_defaults(handler=lookup)

    diff_parser = subparsers.add_parser("diff", help="Summarize key-level changes against a git revision")
    common_root_argument(diff_parser)
    diff_parser.add_argument("--base", default="HEAD", help="Git revision before the feature batch (default: HEAD)")
    diff_parser.add_argument("--expected-key", action="append", help="Exact required touched key; repeat as needed")
    diff_parser.add_argument("--keys-file", type=Path, help="Newline/JSON list of exact required touched keys")
    diff_parser.add_argument(
        "--expected-entry",
        action="append",
        help="Exact path-qualified touched entry as REPO_PATH::KEY; repeat as needed",
    )
    diff_parser.add_argument(
        "--entries-file",
        type=Path,
        help="Newline/JSON list of exact REPO_PATH::KEY expectations (required for multiple paths)",
    )
    diff_parser.add_argument(
        "--expected-path",
        action="append",
        help="Exact required changed existing file, relative to git root; repeat as needed",
    )
    diff_parser.add_argument("--paths-file", type=Path, help="Newline/JSON list of expected changed existing paths")
    diff_parser.add_argument(
        "--expected-added-path",
        action="append",
        help="Explicitly allowed new localization file, relative to git root; repeat as needed",
    )
    diff_parser.add_argument(
        "--added-paths-file",
        type=Path,
        help="Newline/JSON list of explicitly allowed new localization files",
    )
    diff_parser.add_argument(
        "--expect-no-key-changes",
        action="store_true",
        help="Explicitly require zero touched localization keys",
    )
    diff_parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 2 unless touched keys/paths exactly match expectations and no destructive/raw metadata change occurs",
    )
    diff_parser.set_defaults(handler=diff_command)

    validate_parser = subparsers.add_parser("validate", help="Parse catalogs and optionally run xcstringstool")
    common_root_argument(validate_parser)
    validate_parser.add_argument("--changed-from", help="Validate only localization files changed from this revision")
    validate_parser.add_argument("--xcode", action="store_true", help="Run xcstringstool compile --dry-run for .xcstrings")
    validate_parser.set_defaults(handler=validate)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be positive")
    if not args.root.exists() or not args.root.is_dir():
        parser.error("--root must be an existing directory")
    if args.command == "inventory" and args.samples < 0:
        parser.error("--samples must be zero or positive")
    try:
        return int(args.handler(args))
    except (CatalogError, OSError, json.JSONDecodeError) as error:
        print(bounded(f"ERROR {quoted(str(error), 400)}", 500), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
