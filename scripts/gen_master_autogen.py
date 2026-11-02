#!/usr/bin/env python3
# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Zero ERP - Liquibase master autogenerator (timeline globale)
# ------------------------------------------------------------
# Genera un changelog Liquibase autogenerato che include tutti i file
# di migrazione in ordine cronologico globale basato su YYYYMMDD-XX.
# I file devono essere nominati secondo lo schema:
#   20240115-01-descrizione.yaml
#   20240220-02-fix.sql
# ------------------------------------------------------------##
#  esempio di esecuzione:# 
#  python3 scripts/gen_master_autogen.py \
#  --root db/changelog/migrations_v2 \
#  --out  db/changelog/migrations_v2/changelog-autogen.yaml \
#  --base db/changelog
# ------------------------------------------------------------##  



from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple


FILENAME_RE = re.compile(r"^(?P<date>\d{8})-(?P<seq>\d{2})(?P<rest>.*)\.(?P<ext>ya?ml|sql)$", re.IGNORECASE)

DEFAULT_INCLUDE_EXTS = {".yaml", ".yml", ".sql"}

# Cartelle tipiche che non vuoi includere (modifica liberamente)
DEFAULT_EXCLUDE_DIRS = {
    ".git", ".idea", ".vscode", "__pycache__", "node_modules",
    "tmp", "temp", "backup", "backups", "old", "archive", "archivio"
}

# Escludi intere aree dalla timeline autogenerata (path relativo alla root scansionata)
DEFAULT_EXCLUDE_PREFIXES = (
    # 70_dati_sistema: i dati di sistema che il codice legge, inclusi a blocco
    #   nel master DOPO l'autogen e PRIMA di 80_data (fuso aziendale, T-8).
    "70_dati_sistema/",
    "80_data/",
    "85_pgagent/",
    "90_end/",
)

DEFAULT_EXCLUDE_FILES = {
    "changelog-autogen.yaml",
    "changelog-autogen.yml",
}


@dataclass(frozen=True)
class ChangeFile:
    path: Path                # path assoluto
    rel_path: str             # path relativo (posix) rispetto al master (root progetto o changelog)
    date: int                 # YYYYMMDD
    seq: int                  # XX
    sort_key: Tuple[int, int, str]



def iter_candidate_files(
    root: Path,
    include_exts: set[str],
    exclude_dirs: set[str],
    exclude_prefixes: tuple[str, ...],
) -> Iterable[Path]:
    for p in root.rglob("*"):
        if p.is_dir():
            continue

        # skip excluded directories (per nome cartella)
        if any(part in exclude_dirs for part in p.parts):
            continue

        if p.suffix.lower() not in include_exts:
            continue

        # skip excluded prefixes (relativi a root)
        rel = p.relative_to(root).as_posix()
        if any(rel.startswith(pref) for pref in exclude_prefixes):
            continue

        # skip excluded exact files (relativi a root)
        if rel in DEFAULT_EXCLUDE_FILES:
            continue    
        yield p



def parse_changefile(p: Path, root: Path) -> ChangeFile | None:
    m = FILENAME_RE.match(p.name)
    if not m:
        return None

    date = int(m.group("date"))
    seq = int(m.group("seq"))

    # path relativo alla root scansionata (migrations_v2)
    rel_path = p.relative_to(root).as_posix()

    sort_key = (date, seq, rel_path.lower())
    return ChangeFile(path=p, rel_path=rel_path, date=date, seq=seq, sort_key=sort_key)


def generate_autogen_yaml(
    changelog_files: List[ChangeFile],
    out_file: Path,
    header_comment: str,
    relative_to_changelog_file: bool = True,
) -> None:
    lines: List[str] = []
    lines.append(header_comment.rstrip())
    lines.append("")
    lines.append("databaseChangeLog:")

    for cf in changelog_files:
        lines.append("  - include:")
        lines.append(f"      file: {cf.rel_path}")
        lines.append(f"      relativeToChangelogFile: {'true' if relative_to_changelog_file else 'false'}")

    content = "\n".join(lines) + "\n"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(content, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Genera un changelog Liquibase autogenerato in ordine temporale globale (YYYYMMDD-XX...)"
    )
    ap.add_argument(
        "--root",
        default="migrations_v2",
        help="Directory radice da scansionare (default: migrations_v2)",
    )
    ap.add_argument(
        "--out",
        default="migrations_v2/changelog-autogen.yaml",
        help="File YAML generato (default: migrations_v2/changelog-autogen.yaml)",
    )
    ap.add_argument(
        "--base",
        default=".",
        help="Base path per calcolare i percorsi relativi (default: .). "
             "Usa la cartella dove vive changelog-master-v2.yaml, di solito il repo root.",
    )
    ap.add_argument(
        "--exclude-dir",
        action="append",
        default=[],
        help="Aggiungi directory da escludere (ripetibile).",
    )
    ap.add_argument(
        "--strict",
        action="store_true",
        help="Se attivo: fallisce se trova file con stesso (YYYYMMDD-XX) in path diversi (collisione).",
    )

    args = ap.parse_args()

    root = Path(args.root).resolve()
    out_file = Path(args.out).resolve()
    rel_base = Path(args.base).resolve()

    exclude_dirs = set(DEFAULT_EXCLUDE_DIRS) | set(args.exclude_dir)

    if not root.exists() or not root.is_dir():
        raise SystemExit(f"Root non valida: {root}")

   # candidates = list(iter_candidate_files(root, DEFAULT_INCLUDE_EXTS, exclude_dirs))
    exclude_prefixes = DEFAULT_EXCLUDE_PREFIXES
    candidates = list(iter_candidate_files(root, DEFAULT_INCLUDE_EXTS, exclude_dirs, exclude_prefixes))


    parsed: List[ChangeFile] = []
    skipped: List[Path] = []
    for p in candidates:
       # cf = parse_changefile(p, rel_base=rel_base)
        cf = parse_changefile(p, root=root)
        if cf is None:
            skipped.append(p)
            continue
        parsed.append(cf)

    parsed.sort(key=lambda x: x.sort_key)

    if args.strict:
        # collisione: stesso date+seq su file diversi
        seen: dict[Tuple[int, int], str] = {}
        for cf in parsed:
            k = (cf.date, cf.seq)
            if k in seen and seen[k] != cf.rel_path:
                raise SystemExit(
                    f"Collisione strict: {k} appare in:\n"
                    f" - {seen[k]}\n"
                    f" - {cf.rel_path}\n"
                    f"Soluzione: cambia il -XX o la data."
                )
            seen[k] = cf.rel_path

    header = (
        "# ------------------------------------------------------------\n"
        "# FILE AUTOGENERATO - NON MODIFICARE A MANO\n"
        "# Generato da gen_master_autogen.py\n"
        "# Ordine globale: YYYYMMDD-XX (poi path)\n"
        "# ------------------------------------------------------------"
    )

    generate_autogen_yaml(
        changelog_files=parsed,
        out_file=out_file,
        header_comment=header,
        relative_to_changelog_file=True,
    )

    print(f"[OK] Generato: {out_file}")
    print(f"     Root scan: {root}")
    print(f"     Base rel : {rel_base}")
    print(f"     Changes  : {len(parsed)}")
    if skipped:
        print(f"     Skipped  : {len(skipped)} (file non conformi a YYYYMMDD-XX.*.(yml|yaml|sql))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
