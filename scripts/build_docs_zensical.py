#!/usr/bin/env python3
# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
FULL_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
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
EMPTY_BRACKET_LITERAL_RE = re.compile(r"(?<!\\)\[\](?!\(|:)")
URI_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
SOURCE_FILE_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".vue",
    ".sql",
    ".sh",
    ".yaml",
    ".yml",
    ".json",
    ".csv",
    ".txt",
}
DEFAULT_EXCLUDED_DOC_DIRS = {
    "work-in-progress",
    "work-done",
}
EXTERNAL_REPO_DOC_LINKS = {
    ".codex/AGENTS.md",
}


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


# Scopo: evitare link docs rotti verso file sorgente del repository che nel sito statico non sono pagine navigabili.
def normalize_source_file_links(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        label = match.group(1)
        target = match.group(2).strip()

        path_part = target
        for sep in ("#", "?"):
            if sep in path_part:
                path_part = path_part.split(sep, 1)[0]

        if not is_rebasable_relative_target(path_part):
            return match.group(0)

        if Path(path_part).suffix.lower() not in SOURCE_FILE_EXTENSIONS:
            return match.group(0)

        display = label
        if display.startswith("`") and display.endswith("`") and len(display) >= 2:
            display = display[1:-1]
        return f"`{display}`"

    return FULL_MARKDOWN_LINK_RE.sub(repl, text)


# Scopo: evitare link navigabili verso documenti esclusi dal sito statico.
def normalize_excluded_doc_links(
    text: str, docs_root: Path, current_file: Path, excluded_dirs: set[str]
) -> str:
    docs_root = docs_root.resolve()
    current_dir = current_file.parent.resolve()

    def split_target(raw_target: str) -> tuple[str, str]:
        path_part = raw_target.strip()
        suffix = ""
        for sep in ("#", "?"):
            if sep in path_part:
                idx = path_part.find(sep)
                suffix = path_part[idx:] + suffix
                path_part = path_part[:idx]
        return path_part, suffix

    def repo_path_for_target(raw_target: str) -> str | None:
        path_part, suffix = split_target(raw_target)
        if not path_part or path_part.startswith("#") or URI_SCHEME_RE.match(path_part):
            return None

        if any(path_part.endswith(repo_doc) for repo_doc in EXTERNAL_REPO_DOC_LINKS):
            repo_doc = next(
                repo_doc
                for repo_doc in EXTERNAL_REPO_DOC_LINKS
                if path_part.endswith(repo_doc)
            )
            return f"{repo_doc}{suffix}"

        if path_part.startswith("/"):
            normalized = path_part.lstrip("/")
            if normalized.startswith(("it/", "en/")):
                rel_path = Path(normalized)
            else:
                rel_path = Path("it") / normalized
        else:
            resolved = (current_dir / path_part).resolve()
            try:
                rel_path = resolved.relative_to(docs_root)
            except ValueError:
                return None

        if not any(part in excluded_dirs for part in rel_path.parts):
            return None
        return f"docs/{rel_path.as_posix()}{suffix}"

    def repl(match: re.Match[str]) -> str:
        label = match.group(1)
        target = match.group(2)
        repo_path = repo_path_for_target(target)
        if repo_path is None:
            return match.group(0)
        display = label
        if display.startswith("`") and display.endswith("`") and len(display) >= 2:
            display = display[1:-1]
        return f"{display} (`{repo_path}`)"

    return FULL_MARKDOWN_LINK_RE.sub(repl, text)


# Scopo: impedire che parentesi quadre dentro inline-code diventino link reference.
def normalize_inline_code_with_brackets(text: str) -> str:
    normalized_parts: list[str] = []
    cursor = 0

    for match in re.finditer(r"`([^`\n]*)`", text):
        code = match.group(1)
        is_link_label = (
            match.start() > 0
            and text[match.start() - 1] == "["
            and text[match.end() : match.end() + 2] == "]("
        )
        if is_link_label or ("[" not in code and "]" not in code):
            continue

        normalized_parts.append(text[cursor : match.start()])
        escaped = (
            code.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("[", "&#91;")
            .replace("]", "&#93;")
        )
        normalized_parts.append(f"<code>{escaped}</code>")
        cursor = match.end()

    if not normalized_parts:
        return text

    normalized_parts.append(text[cursor:])
    return "".join(normalized_parts)


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
        elif not (normalized.startswith(("it/", "en/"))):
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
def normalize_ambiguous_markdown(
    text: str, docs_root: Path, current_file: Path, excluded_dirs: set[str]
) -> str:
    normalized = normalize_source_file_links(text)
    normalized = normalize_excluded_doc_links(
        normalized, docs_root, current_file, excluded_dirs
    )
    normalized = normalize_inline_code_with_brackets(normalized)
    normalized = CHECKLIST_STATUS_RE.sub(r"\1\\[\2\\]", normalized)
    normalized = IDENTIFIER_EMPTY_BRACKETS_RE.sub(r"\1\\[\\]", normalized)
    normalized = IDENTIFIER_INDEX_RE.sub(r"\1\\[\2\\]", normalized)
    normalized = EMPTY_BRACKET_LITERAL_RE.sub(r"\\[\\]", normalized)
    normalized = STANDALONE_BRACKET_LITERAL_RE.sub(r"\\[\1\\]", normalized)
    return normalized


# Scopo: preprocessare tutti i file markdown in una copia temporanea della cartella docs.
def prune_excluded_doc_dirs(dst_docs: Path, excluded_dirs: set[str]) -> int:
    removed_dirs = 0
    for path in sorted(dst_docs.rglob("*")):
        if not path.is_dir():
            continue
        if path.name not in excluded_dirs:
            continue
        shutil.rmtree(path)
        removed_dirs += 1
    return removed_dirs


# Scopo: preprocessare tutti i file markdown in una copia temporanea della cartella docs.
def preprocess_docs(
    src_docs: Path, dst_docs: Path, excluded_dirs: set[str]
) -> tuple[int, int, int, int, list[str]]:
    if dst_docs.exists():
        shutil.rmtree(dst_docs)
    shutil.copytree(src_docs, dst_docs)
    removed_dirs = prune_excluded_doc_dirs(dst_docs, excluded_dirs)

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
        normalized = normalize_ambiguous_markdown(rewritten, dst_docs, md, excluded_dirs)
        md.write_text(normalized, encoding="utf-8")

        processed_files += 1
        include_expansions += include_count
        rewritten_links += link_count

    return processed_files, include_expansions, rewritten_links, removed_dirs, warnings


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
    parser.add_argument(
        "--exclude-dir",
        action="append",
        default=[],
        help="Nome cartella docs da escludere dalla build preprocessata. Ripetibile.",
    )
    return parser.parse_args()


# Scopo: orchestrare preprocess e build, emettendo metriche utili per il go/no-go.
def main() -> int:
    args = parse_args()
    src_config = Path(args.config).resolve()
    src_docs = Path(args.docs_in).resolve()
    dst_docs = Path(args.docs_out).resolve()
    dst_config = Path(args.config_out).resolve()
    excluded_dirs = DEFAULT_EXCLUDED_DOC_DIRS | set(args.exclude_dir)

    processed_files, include_expansions, rewritten_links, removed_dirs, warnings = preprocess_docs(
        src_docs, dst_docs, excluded_dirs
    )
    rel_docs_dir = os.path.relpath(dst_docs, start=dst_config.parent)
    rel_site_dir = os.path.relpath(Path(args.site_dir).resolve(), start=dst_config.parent)
    build_temp_config(src_config, dst_config, docs_dir=rel_docs_dir, site_dir=rel_site_dir)

    print(f"preprocess_files={processed_files}")
    print(f"include_expanded={include_expansions}")
    print(f"links_rewritten={rewritten_links}")
    print(f"excluded_dirs_removed={removed_dirs}")
    print(f"excluded_dir_names={','.join(sorted(excluded_dirs))}")
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
