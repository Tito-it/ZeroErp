#!/usr/bin/env python3
# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Preprocess docs Markdown (include-markdown + rewrite link) e avvia build Zensical.
# ------------------------------------------------------------

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
from pathlib import Path


# Scopo: intercettare qualsiasi include-markdown dichiarato nei file docs.
ANY_INCLUDE_RE = re.compile(r"\{\%\s*include-markdown\s+\"([^\"]+)\"\s*\%\}")
# Scopo: processare solo include verso file markdown reali.
INCLUDE_MD_RE = re.compile(r"\.md$", re.IGNORECASE)
ROOT_DBZERO_LINK_RE = re.compile(r"(\]\()(/dbzero/)")


# Scopo: risolvere il path del file incluso con fallback robusto.
def resolve_include_target(target: str, docs_root: Path, current_file: Path) -> Path:
    normalized = target.strip()
    candidates: list[Path] = []
    if normalized.startswith("/"):
        candidates.append(docs_root / normalized.lstrip("/"))
    else:
        candidates.append(docs_root / normalized)
        candidates.append(current_file.parent / normalized)
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return candidates[0].resolve()


# Scopo: espandere ricorsivamente i tag include-markdown evitando loop.
def expand_includes(
    text: str,
    docs_root: Path,
    current_file: Path,
    stack: tuple[Path, ...],
    warnings: list[str],
) -> tuple[str, int]:
    expanded_count = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal expanded_count
        target = match.group(1)
        if not INCLUDE_MD_RE.search(target):
            warnings.append(
                f"{current_file.as_posix()}: include ignorato (target non .md): '{target}'"
            )
            return match.group(0)

        include_path = resolve_include_target(target, docs_root, current_file)
        if include_path in stack:
            chain = " -> ".join([p.as_posix() for p in (*stack, include_path)])
            warnings.append(f"{current_file.as_posix()}: include circolare ignorato: {chain}")
            return match.group(0)
        if not include_path.exists():
            warnings.append(
                f"{current_file.as_posix()}: include mancante ignorato: '{target}'"
            )
            return match.group(0)

        included_text = include_path.read_text(encoding="utf-8")
        expanded_count += 1
        expanded_text, nested_count = expand_includes(
            included_text, docs_root, include_path, (*stack, include_path), warnings
        )
        expanded_count += nested_count
        return expanded_text

    previous = text
    while True:
        current = ANY_INCLUDE_RE.sub(repl, previous)
        if current == previous:
            return current, expanded_count
        previous = current


# Scopo: riscrivere link root assoluti /dbzero/... su /it/dbzero/... per output i18n.
def rewrite_root_links(text: str) -> tuple[str, int]:
    rewritten, count = ROOT_DBZERO_LINK_RE.subn(r"\1/it/dbzero/", text)
    return rewritten, count


# Scopo: preprocessare tutti i file markdown in una copia temporanea della cartella docs.
def preprocess_docs(src_docs: Path, dst_docs: Path) -> tuple[int, int, int, list[str]]:
    if dst_docs.exists():
        shutil.rmtree(dst_docs)
    shutil.copytree(src_docs, dst_docs)

    processed_files = 0
    include_expansions = 0
    rewritten_links = 0
    warnings: list[str] = []

    for md in dst_docs.rglob("*.md"):
        text = md.read_text(encoding="utf-8")
        expanded, include_count = expand_includes(
            text, dst_docs, md, (md.resolve(),), warnings
        )
        rewritten, link_count = rewrite_root_links(expanded)
        md.write_text(rewritten, encoding="utf-8")

        processed_files += 1
        include_expansions += include_count
        rewritten_links += link_count

    return processed_files, include_expansions, rewritten_links, warnings


# Scopo: creare una config temporanea puntata alla docs preprocessata e al site_dir richiesto.
def build_temp_config(
    src_config: Path, dst_config: Path, docs_dir: str, site_dir: str
) -> None:
    content = src_config.read_text(encoding="utf-8")
    content = re.sub(r"(?m)^docs_dir:\s*.*$", f"docs_dir: {docs_dir}", content)
    content = re.sub(r"(?m)^site_dir:\s*.*$", f"site_dir: {site_dir}", content)
    dst_config.parent.mkdir(parents=True, exist_ok=True)
    dst_config.write_text(content, encoding="utf-8")


# Scopo: eseguire il comando zensical build e restituire l'exit code.
def run_zensical_build(config_file: Path) -> int:
    proc = subprocess.run(["zensical", "build", "-f", str(config_file)], check=False)
    return proc.returncode


# Scopo: definire e parsare gli argomenti CLI per il flow di preprocess+build.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preprocess docs for Zensical and run build."
    )
    parser.add_argument("--config", default="mkdocs.yml", help="Source config file.")
    parser.add_argument(
        "--docs-in", default="docs", help="Source docs directory (default: docs)."
    )
    parser.add_argument(
        "--docs-out",
        default=".tmp/zensical_docs",
        help="Temporary docs directory for preprocessed files.",
    )
    parser.add_argument(
        "--config-out",
        default="mkdocs.zensical.yml",
        help="Temporary config file for Zensical build.",
    )
    parser.add_argument(
        "--site-dir",
        default="site-zensical",
        help="Output site directory for Zensical build.",
    )
    return parser.parse_args()


# Scopo: orchestrare preprocess e build, emettendo metriche utili per il go/no-go.
def main() -> int:
    args = parse_args()
    src_config = Path(args.config).resolve()
    src_docs = Path(args.docs_in).resolve()
    dst_docs = Path(args.docs_out).resolve()
    dst_config = Path(args.config_out).resolve()

    processed_files, include_expansions, rewritten_links, warnings = preprocess_docs(
        src_docs, dst_docs
    )
    rel_docs_dir = os.path.relpath(dst_docs, start=dst_config.parent)
    rel_site_dir = os.path.relpath(Path(args.site_dir).resolve(), start=dst_config.parent)
    build_temp_config(src_config, dst_config, docs_dir=rel_docs_dir, site_dir=rel_site_dir)

    print(f"preprocess_files={processed_files}")
    print(f"include_expanded={include_expansions}")
    print(f"links_rewritten={rewritten_links}")
    print(f"include_warnings={len(warnings)}")
    print(f"temp_docs={dst_docs.as_posix()}")
    print(f"temp_config={dst_config.as_posix()}")
    for warning in warnings:
        print(f"WARNING: {warning}")

    return run_zensical_build(dst_config)


if __name__ == "__main__":
    raise SystemExit(main())
