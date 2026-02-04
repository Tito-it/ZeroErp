# Generazione indici backend (`gen_bk_docs.py`)

## Scopo
Automatizzare la generazione degli indici `index.md` (e opzionalmente `index.ci.md`) per `docs/it/backend/<area>/`, includendo una descrizione breve estratta dalla sezione **Scopo**.

## Contesto
Script: `scripts/gen_bk_docs.py`  
Lo script e` separato da `gen_db_docs.py` per non toccare il flusso DB esistente.

## Input
- cartelle area backend (`docs/it/backend/<area>/`)
- file `manual/*.md` e `funzioni/*.md` per ogni area

## Output
- `index.md` aggiornato per ogni area
- `index.ci.md` opzionale (stessa struttura tecnica dell'indice principale)

## Regole
- Struttura indice tecnica unica: `API`, `Funzioni`, `Utility`, `Altri contenuti`.
- Priorita` descrizione: sezione `Scopo` / `Scopo Principale`.
- Fallback: primo paragrafo utile del file Markdown.
- Per API, naming consigliato: `api_<nome>.md` (i non conformi finiscono in `Altri contenuti`).
- Nessuna modifica automatica a `gen_db_docs.py`.

## Dipendenze DB
- Nessuna

## Note di utilizzo
```bash
python scripts/gen_bk_docs.py
python scripts/gen_bk_docs.py --ci
python scripts/gen_bk_docs.py --areas vendite,core --ci
python scripts/gen_bk_docs.py --dry-run --ci
```
