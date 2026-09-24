# Generazione indici backend (`gen_bk_docs.py`)

## Scopo
Automatizzare la generazione degli indici `index.md` (e opzionalmente `index.ci.md`) per `docs/it/backend/<area>/`, includendo una descrizione breve estratta dalla sezione **Scopo**.

## Contesto
Script: `scripts/gen_bk_docs.py`  
Lo script e` separato da `gen_db_docs.py` per non toccare il flusso DB esistente.

## Input
- cartelle area backend (`docs/it/backend/<area>/`, escluse quelle che iniziano con `_`)
- file `*.md` delle sottocartelle `api/`, `funzioni/`, `utility/` (o `utilities/`, `utils/`) e `manual/` di ogni area

## Output
- `index.md` aggiornato per ogni area
- `index.ci.md` opzionale (stessa struttura tecnica dell'indice principale)

## Regole
- Struttura indice tecnica unica: `API`, `Funzioni`, `Utility`, `Altri contenuti`.
- Priorita` descrizione: sezione `Scopo` / `Scopo Principale`.
- Fallback: primo paragrafo utile del file Markdown.
- Classificazione:
  - `api/*.md`: in `API` solo se il nome inizia con `api_`; i non conformi finiscono in `Altri contenuti` e sono elencati in una sezione `Note` (naming consigliato `api_<nome>.md`).
  - `funzioni/*.md` -> `Funzioni`; `utility/`, `utilities/`, `utils/` -> `Utility`.
  - `manual/*.md`, per nome: `api_*`, `api-*`, `*_api`, `*-api` o `*-api-*` -> `API`; `utility_*`, `util_*`, `*_utils`, `*-utils` o nomi che contengono `normalizer` / `helper` -> `Utility`; tutto il resto -> `Altri contenuti`.
- Nessuna modifica automatica a `gen_db_docs.py`.

## Dipendenze DB
- Nessuna

## Note di utilizzo
La root di default e' `docs/it/backend`, relativa alla directory corrente: lo script si lancia dalla root del repo, oppure si indica `--root`.

```bash
python scripts/gen_bk_docs.py
python scripts/gen_bk_docs.py --ci
python scripts/gen_bk_docs.py --areas vendite,core --ci
python scripts/gen_bk_docs.py --dry-run --ci
python scripts/gen_bk_docs.py --root docs/it/backend --areas core
```
