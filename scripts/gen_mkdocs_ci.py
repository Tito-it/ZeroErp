#!/usr/bin/env python3
# 
# NOTE:
# - Genera mkdocs.ci.yml da mkdocs.yml sostituendo index.md con index.ci.md
#   per gli schemi dbzero.
# - Le esclusioni (exclude_docs) sono opzionali e attive solo con flag
#   --exclude-ddl/--exclude-views.##
# --------------------------------------------------------------
import argparse
import pathlib
import re


DDL_EXCLUDES = [
    "it/dbzero/**/tabelle/**",
    "it/dbzero/**/funzioni/**",
    "it/dbzero/**/views/**",
]


def add_exclude_docs(text, excludes):
    if not excludes:
        return text
    if re.search(r"^exclude_docs:", text, flags=re.MULTILINE):
        return text

    block_lines = ["exclude_docs: |"]
    block_lines.extend([f"        {item}" for item in excludes])
    block = "\n".join(block_lines) + "\n"

    match = re.search(r"^site_dir:.*$", text, flags=re.MULTILINE)
    if not match:
        return text + ("\n" if not text.endswith("\n") else "") + block

    insert_at = match.end()
    return text[:insert_at] + "\n\n" + block + text[insert_at:]


def replace_schema_indexes(text):
    return re.sub(
        r"(it/dbzero/[^/]+/)index\.md",
        r"\1index.ci.md",
        text,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Generate mkdocs.ci.yml from mkdocs.yml with CI-only tweaks."
    )
    parser.add_argument("--source", default="mkdocs.yml")
    parser.add_argument("--dest", default="mkdocs.ci.yml")
    parser.add_argument(
        "--exclude-ddl",
        action="store_true",
        help="Exclude docs under it/dbzero/**/tabelle/** and it/dbzero/**/funzioni/**",
    )
    parser.add_argument(
        "--exclude-views",
        action="store_true",
        help="Exclude docs under it/dbzero/**/views/**",
    )
    args = parser.parse_args()

    src = pathlib.Path(args.source)
    dst = pathlib.Path(args.dest)

    text = src.read_text(encoding="utf-8")
    excludes = []
    if args.exclude_ddl:
        excludes.extend(DDL_EXCLUDES[:2])
        if args.exclude_views:
            excludes.append(DDL_EXCLUDES[2])
    elif args.exclude_views:
        excludes.append(DDL_EXCLUDES[2])

    text = add_exclude_docs(text, excludes)
    text = replace_schema_indexes(text)

    dst.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
