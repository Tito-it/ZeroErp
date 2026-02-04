#!/usr/bin/env python3
"""
Generatore indici documentazione backend (docs/it/backend).

Obiettivi:
- creare/aggiornare index.md per ogni area backend
- indice tecnico unico (API/Funzioni/Utility), no split auto/manuale
- includere descrizione breve per ogni voce (priorita': sezione Scopo)
- opzionalmente creare index.ci.md con stessa struttura tecnica
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def strip_md_noise(paragraph: str) -> str:
    cleaned = re.sub(r"`([^`]+)`", r"\1", paragraph)
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)
    cleaned = re.sub(r"^[>*\-\s]+", "", cleaned)
    return normalize_spaces(cleaned)


def truncate(text: str, max_len: int = 220) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def extract_description(markdown_text: str) -> str:
    # 1) Cerca sezione Scopo (##/###, con o senza emoji)
    scope_match = re.search(
        r"(?ims)^#{2,4}\s*(?:🎯\s*)?scopo(?:\s+principale)?\s*$\n(?P<body>.*?)(?=^#{2,4}\s+|\Z)",
        markdown_text,
    )
    if scope_match:
        block = scope_match.group("body")
        for part in re.split(r"\n\s*\n", block):
            candidate = strip_md_noise(part)
            if candidate and not candidate.lower().startswith("(latest"):
                return truncate(candidate)

    # 2) Fallback: primo paragrafo utile
    for part in re.split(r"\n\s*\n", markdown_text):
        p = part.strip()
        if not p:
            continue
        if p.startswith("{% include-markdown"):
            continue
        if p.startswith("#"):
            continue
        if p.startswith(">"):
            continue
        if p.startswith("```"):
            continue
        candidate = strip_md_noise(p)
        if candidate:
            return truncate(candidate)
    return ""


def read_description(md_file: Path) -> str:
    if not md_file.is_file():
        return ""
    return extract_description(md_file.read_text(encoding="utf-8"))


def list_md_stems(dir_path: Path) -> list[str]:
    if not dir_path.is_dir():
        return []
    return sorted(p.stem for p in dir_path.glob("*.md") if p.is_file())


def _is_api_manual_stem(stem: str) -> bool:
    return (
        stem.startswith("api_")
        or stem.startswith("api-")
        or stem.endswith("_api")
        or stem.endswith("-api")
        or "-api-" in stem
    )


def _is_utility_manual_stem(stem: str) -> bool:
    return (
        stem.startswith("utility_")
        or stem.startswith("util_")
        or stem.endswith("_utils")
        or stem.endswith("-utils")
        or "normalizer" in stem
        or "helper" in stem
    )


def build_entries(
    *,
    stems: list[str],
    link_prefix: str,
    source_dir: Path,
    manual_dir: Path,
    label_transform=lambda x: x,
) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for stem in stems:
        desc = read_description(manual_dir / f"{stem}.md")
        if not desc:
            desc = read_description(source_dir / f"{stem}.md")
        entry = f"- [{label_transform(stem)}]({link_prefix}/{stem}.md)"
        if desc:
            entry += f" — {desc}"
        entries.append((stem, entry))
    return entries


def build_manual_entries(stems: list[str], manual_dir: Path) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for stem in stems:
        desc = read_description(manual_dir / f"{stem}.md")
        entry = f"- [{stem}](manual/{stem}.md)"
        if desc:
            entry += f" — {desc}"
        entries.append((stem, entry))
    return entries


def append_section(lines: list[str], title: str, entries: list[tuple[str, str]]) -> None:
    if not entries:
        return
    lines.append(title)
    for _, entry in entries:
        lines.append(entry)
    lines.append("")


def split_api_entries(api_stems: list[str]) -> tuple[list[str], list[str]]:
    valid = [s for s in api_stems if s.startswith("api_")]
    invalid = [s for s in api_stems if not s.startswith("api_")]
    return valid, invalid


def render_index(area_name: str, area_dir: Path) -> str:
    api_dir = area_dir / "api"
    funzioni_dir = area_dir / "funzioni"
    utility_dir = area_dir / "utility"
    utilities_dir = area_dir / "utilities"
    utils_dir = area_dir / "utils"
    manual_dir = area_dir / "manual"

    api_all = list_md_stems(api_dir)
    api_ok, api_non_standard = split_api_entries(api_all)
    funzioni = list_md_stems(funzioni_dir)
    utility = sorted(
        set(list_md_stems(utility_dir))
        | set(list_md_stems(utilities_dir))
        | set(list_md_stems(utils_dir))
    )
    manual = list_md_stems(manual_dir)

    lines: list[str] = [f"# Area '{area_name}' (Backend)", ""]

    known = set(api_ok) | set(funzioni) | set(utility)
    manual_api = sorted([s for s in manual if _is_api_manual_stem(s) and s not in known])
    known.update(manual_api)
    manual_utility = sorted([s for s in manual if _is_utility_manual_stem(s) and s not in known])
    known.update(manual_utility)

    api_entries = build_entries(
        stems=api_ok,
        link_prefix="api",
        source_dir=api_dir,
        manual_dir=manual_dir,
        label_transform=lambda s: s[4:],
    )
    api_entries.extend(build_manual_entries(manual_api, manual_dir))
    append_section(lines, "## API", api_entries)

    funzioni_entries = build_entries(
        stems=funzioni,
        link_prefix="funzioni",
        source_dir=funzioni_dir,
        manual_dir=manual_dir,
    )
    append_section(lines, "## Funzioni", funzioni_entries)

    utility_entries: list[tuple[str, str]] = []
    if utility:
        utility_link_prefix = (
            "utility"
            if utility_dir.is_dir()
            else ("utilities" if utilities_dir.is_dir() else "utils")
        )
        utility_source_dir = (
            utility_dir
            if utility_dir.is_dir()
            else (utilities_dir if utilities_dir.is_dir() else utils_dir)
        )
        utility_entries.extend(
            build_entries(
                stems=utility,
                link_prefix=utility_link_prefix,
                source_dir=utility_source_dir,
                manual_dir=manual_dir,
            )
        )
    utility_entries.extend(build_manual_entries(manual_utility, manual_dir))
    append_section(lines, "## Utility", utility_entries)

    extra_manual = sorted(set(manual) - known)
    extra_entries = build_manual_entries(extra_manual, manual_dir)
    extra_entries.extend(
        build_entries(
            stems=api_non_standard,
            link_prefix="api",
            source_dir=api_dir,
            manual_dir=manual_dir,
        )
    )
    append_section(lines, "## Altri contenuti", extra_entries)

    if api_non_standard:
        lines.append("## Note")
        lines.append("- Convenzione API consigliata: `api_<nome>.md`.")
        lines.append(
            f"- File API non conformi trovati: {', '.join(sorted(api_non_standard))}."
        )
        lines.append("")

    return "\n".join(lines)


def render_index_ci(area_name: str, area_dir: Path) -> str:
    # Struttura CI allineata all'indice principale, mantenendo sezione tecnica unica.
    return render_index(area_name, area_dir)


def discover_areas(backend_docs_root: Path) -> list[Path]:
    return sorted(
        p
        for p in backend_docs_root.iterdir()
        if p.is_dir() and not p.name.startswith("_")
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Genera index.md (e index.ci.md) per docs/it/backend/<area>/."
    )
    parser.add_argument(
        "--root",
        default="docs/it/backend",
        help="Root documentazione backend (default: docs/it/backend)",
    )
    parser.add_argument(
        "--areas",
        default="",
        help="Lista aree separate da virgola (es: vendite,core). Vuoto=autodiscovery.",
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help="Genera anche index.ci.md (stessa struttura tecnica dell'indice principale).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra file target senza scrivere su disco.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(args.root)
    if not root.is_dir():
        raise SystemExit(f"Root non trovata: {root}")

    if args.areas.strip():
        selected = {x.strip() for x in args.areas.split(",") if x.strip()}
        areas = [root / name for name in sorted(selected) if (root / name).is_dir()]
    else:
        areas = discover_areas(root)

    for area_dir in areas:
        index_path = area_dir / "index.md"
        content = render_index(area_dir.name, area_dir)
        if args.dry_run:
            print(f"[DRY] write {index_path}")
        else:
            index_path.write_text(content, encoding="utf-8")
            print(f"[OK] {index_path}")

        if args.ci:
            ci_path = area_dir / "index.ci.md"
            ci_content = render_index_ci(area_dir.name, area_dir)
            if args.dry_run:
                print(f"[DRY] write {ci_path}")
            else:
                ci_path.write_text(ci_content, encoding="utf-8")
                print(f"[OK] {ci_path}")


if __name__ == "__main__":
    main()
