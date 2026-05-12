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
MARKDOWN_ABS_LINK_RE = re.compile(r"\]\((/(?!/)[^)]+)\)")
HTML_ABS_HREF_RE = re.compile(r'href="(/(?!/)[^"]*)"')
MARKDOWN_LINK_RE = re.compile(r"\]\(([^)]+)\)")
HTML_HREF_RE = re.compile(r'href="([^"]*)"')
CHECKLIST_STATUS_RE = re.compile(
    r"(?m)^(\s*[-*]\s+)\[(DONE|TODO|WIP)\](?=\s)"
)
IDENTIFIER_EMPTY_BRACKETS_RE = re.compile(
    r"(?<!\\)(\b[A-Za-z_][A-Za-z0-9_.:%-]*)\[\]"
)
IDENTIFIER_INDEX_RE = re.compile(
    r"(?<!\\)(\b[A-Za-z_][A-Za-z0-9_.:%-]*)\[([A-Za-z0-9_., -]+)\]"
)
STANDALONE_BRACKET_LITERAL_RE = re.compile(
    r"(?<!\\)\[([^\]\n]{1,80})\](?!\(|:)"
)
URI_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")


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


# Scopo: capire se un target va lasciato invariato o ribasato rispetto al file includente.
def is_rebasable_relative_target(target: str) -> bool:
    stripped = target.strip()
    if not stripped or stripped.startswith(("/", "#")):
        return False
    if URI_SCHEME_RE.match(stripped):
        return False
    return True


# Scopo: ribasare i link relativi di un file incluso verso il file che lo incorpora.
def rebase_relative_links(text: str, from_file: Path, to_file: Path) -> str:
    from_dir = from_file.parent
    to_dir = to_file.parent

    def rebase_target(raw_target: str) -> str:
        path_part, suffix = raw_target, ""
        for sep in ("#", "?"):
            if sep in path_part:
                idx = path_part.find(sep)
                suffix = path_part[idx:] + suffix
                path_part = path_part[:idx]

        if not is_rebasable_relative_target(path_part):
            return raw_target

        resolved = (from_dir / path_part).resolve()
        rebased = os.path.relpath(resolved, start=to_dir)
        if not rebased.startswith("."):
            rebased = f"./{rebased}"
        if path_part.endswith("/") and not rebased.endswith("/"):
            rebased = f"{rebased}/"
        return f"{rebased}{suffix}"

    def repl_md(match: re.Match[str]) -> str:
        return f"]({rebase_target(match.group(1))})"

    def repl_html(match: re.Match[str]) -> str:
        return f'href="{rebase_target(match.group(1))}"'

    rebased = MARKDOWN_LINK_RE.sub(repl_md, text)
    rebased = HTML_HREF_RE.sub(repl_html, rebased)
    return rebased


# Scopo: espandere ricorsivamente i tag include-markdown evitando loop.
def expand_includes(
    text: str,
    docs_root: Path,
    current_file: Path,
    stack: tuple[Path, ...],
    warnings: list[str],
    source_texts: dict[Path, str],
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
        include_text = source_texts.get(include_path)
        if include_text is None and include_path.exists():
            include_text = include_path.read_text(encoding="utf-8")
        if include_text is None:
            warnings.append(
                f"{current_file.as_posix()}: include mancante ignorato: '{target}'"
            )
            return match.group(0)
        expanded_count += 1
        expanded_text, nested_count = expand_includes(
            include_text,
            docs_root,
            include_path,
            (*stack, include_path),
            warnings,
            source_texts,
        )
        expanded_count += nested_count
        return rebase_relative_links(expanded_text, include_path, current_file)

    previous = text
    while True:
        current = ANY_INCLUDE_RE.sub(repl, previous)
        if current == previous:
            return current, expanded_count
        previous = current


# Scopo: convertire link assoluti markdown in link relativi (compatibili con GitHub Pages project site).
def rewrite_root_links(text: str, docs_root: Path, current_file: Path) -> tuple[str, int]:
    current_rel_dir = current_file.parent.relative_to(docs_root)
    rewritten_count = 0

    def to_relative(raw_target: str) -> str:
        path_part = raw_target
        suffix = ""
        for sep in ("#", "?"):
            if sep in path_part:
                idx = path_part.find(sep)
                suffix = path_part[idx:] + suffix
                path_part = path_part[:idx]

        normalized = path_part.lstrip("/")
        wants_trailing_slash = normalized.endswith("/")
        if normalized.startswith("dbzero/"):
            normalized = f"it/{normalized}"
        elif not (normalized.startswith("it/") or normalized.startswith("en/")):
            normalized = f"it/{normalized}"

        rel_target = os.path.relpath(normalized, start=current_rel_dir.as_posix())
        if not rel_target.startswith("."):
            rel_target = f"./{rel_target}"
        if wants_trailing_slash and not rel_target.endswith("/"):
            rel_target = f"{rel_target}/"
        return f"{rel_target}{suffix}"

    def repl_md(match: re.Match[str]) -> str:
        nonlocal rewritten_count
        rewritten_count += 1
        return f"]({to_relative(match.group(1))})"

    def repl_html(match: re.Match[str]) -> str:
        nonlocal rewritten_count
        rewritten_count += 1
        return f'href="{to_relative(match.group(1))}"'

    rewritten = MARKDOWN_ABS_LINK_RE.sub(repl_md, text)
    rewritten = HTML_ABS_HREF_RE.sub(repl_html, rewritten)
    return rewritten, rewritten_count


# Scopo: neutralizzare marker checklist testuali che Zensical interpreta come reference link.
def normalize_ambiguous_markdown(text: str) -> str:
    normalized = CHECKLIST_STATUS_RE.sub(r"\1\\[\2\\]", text)
    normalized = IDENTIFIER_EMPTY_BRACKETS_RE.sub(r"\1\\[\\]", normalized)
    normalized = IDENTIFIER_INDEX_RE.sub(r"\1\\[\2\\]", normalized)
    normalized = STANDALONE_BRACKET_LITERAL_RE.sub(r"\\[\1\\]", normalized)
    return normalized


# Scopo: preprocessare tutti i file markdown in una copia temporanea della cartella docs.
def preprocess_docs(src_docs: Path, dst_docs: Path) -> tuple[int, int, int, list[str]]:
    if dst_docs.exists():
        shutil.rmtree(dst_docs)
    shutil.copytree(src_docs, dst_docs)

    processed_files = 0
    include_expansions = 0
    rewritten_links = 0
    warnings: list[str] = []

    source_texts: dict[Path, str] = {}
    for md in dst_docs.rglob("*.md"):
        source_texts[md.resolve()] = md.read_text(encoding="utf-8")

    for md in dst_docs.rglob("*.md"):
        text = md.read_text(encoding="utf-8")
        expanded, include_count = expand_includes(
            text, dst_docs, md, (md.resolve(),), warnings, source_texts
        )
        rewritten, link_count = rewrite_root_links(expanded, dst_docs, md)
        normalized = normalize_ambiguous_markdown(rewritten)
        md.write_text(normalized, encoding="utf-8")

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


# Scopo: creare una homepage root compatibile con GitHub Pages che reindirizza alla lingua default.
def write_root_redirect(site_dir: Path, target: str = "./it/") -> None:
    site_dir.mkdir(parents=True, exist_ok=True)
    index_file = site_dir / "index.html"
    html = f"""<!doctype html>
<html lang="it">
  <head>
    <meta charset="utf-8">
    <meta http-equiv="refresh" content="0; url={target}">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Zero ERP Documentation</title>
    <script>location.replace("{target}");</script>
  </head>
  <body>
    <p>Redirecting to <a href="{target}">{target}</a></p>
  </body>
</html>
"""
    index_file.write_text(html, encoding="utf-8")


# Scopo: correggere link HTML verso /index.md in / per evitare 404 su site statico.
def normalize_site_html_links(site_dir: Path) -> int:
    changed_files = 0
    pattern = re.compile(r'href="([^"]*?)index\.md([#?][^"]*)?"')
    dir_like_href = re.compile(r'href="((?:\./|\.\./)[^"#?]+)([#?][^"]*)?"')

    for html_file in site_dir.rglob("*.html"):
        content = html_file.read_text(encoding="utf-8")

        def repl(match: re.Match[str]) -> str:
            base = match.group(1)
            suffix = match.group(2) or ""
            target = base
            if not target.endswith("/") and not suffix:
                target = f"{target}/"
            return f'href="{target}{suffix if suffix else ""}"'

        rewritten = pattern.sub(repl, content)

        def repl_dir(match: re.Match[str]) -> str:
            target = match.group(1)
            suffix = match.group(2) or ""
            if target.endswith("/"):
                return match.group(0)
            if target in {"./", "../", "./.", "././"}:
                return match.group(0)
            last = target.rsplit("/", 1)[-1]
            if "." in last:
                return match.group(0)
            return f'href="{target}/{suffix}"'

        rewritten = dir_like_href.sub(repl_dir, rewritten)
        if rewritten != content:
            html_file.write_text(rewritten, encoding="utf-8")
            changed_files += 1

    return changed_files


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
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Solo preprocess (include + link rewrite), senza build statico zensical.",
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

    if args.skip_build:
        print("skip_build=true — preprocess completato, build statico saltato.")
        return 0

    exit_code = run_zensical_build(dst_config)
    if exit_code == 0:
        site_dir = Path(args.site_dir)
        changed = normalize_site_html_links(site_dir)
        write_root_redirect(site_dir)
        print(f"html_links_normalized_files={changed}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
