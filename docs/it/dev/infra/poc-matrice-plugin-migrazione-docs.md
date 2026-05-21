# PoC Matrice Plugin - Migrazione Docs

Data: 2026-03-04
Repo: `/home/tid/software/ZeroErp`

## Scopo

Ridurre l'incertezza prima del salto secco verso stack docs piu` recente, concentrandosi sui plugin attualmente usati.

## Baseline attuale (misurata)

- Plugin in `mkdocs.yml`: `include-markdown`, `abs-to-rel`, `search`, `i18n`.
- Occorrenze `{% include-markdown ... %}` nei contenuti: **1562**.
- Warning `unrecognized relative link` su build attuale: **8066**.
- Warning `nav` su file mancanti: **2** (stessa voce ripetuta su build multilingua).
- Errori hard in build: **0**.

Comandi usati:

```bash
source .venv/bin/activate
mkdocs build > .tmp.docs.poc.log 2>&1
rg -n '\{\% include-markdown|\{% include-markdown' docs | wc -l
rg -n 'unrecognized relative link' .tmp.docs.poc.log | wc -l
rg -n "A reference to '.*' is included in the 'nav' configuration" .tmp.docs.poc.log | wc -l
rg -n '^ERROR| ERROR ' .tmp.docs.poc.log | wc -l
```

## Matrice rischio plugin

| Plugin | Uso nel progetto | Compatibilita` dichiarata (fonti) | Rischio migrazione | Esito PoC |
|---|---:|---|---|---|
| `include-markdown` | Molto alto (1562 include) | Non trovato esplicitamente nelle pagine compatibilita` Zensical consultate | Alto | **Bloccante da verificare** |
| `i18n` (`mkdocs-static-i18n`) | Alto | Presente in lista plugin compatibili Zensical | Medio | **Probabile compatibile** |
| `abs-to-rel` | Medio | Non trovato esplicitamente nelle pagine compatibilita` Zensical consultate | Medio/Alto | **Da verificare** |
| `search` | Standard | Feature base del motore docs | Basso | **Compatibile atteso** |

## PoC tecnico eseguito su Zensical

Toolchain testata:

- `zensical==0.0.24` installato nel `.venv`.
- Build eseguita con: `zensical build -f mkdocs.yml`.
- Exit code build: `0`.

Evidenze oggettive post-build:

- Cartelle lingua generate: `site/it` e `site/en` presenti.
- Tag include rimasti raw nel render HTML: **1558** occorrenze.
  - Esempio: `site/it/manifesto/index.html` contiene ancora
    `{% include-markdown "signature-core.md" %}`.
- Link assoluti root `/dbzero/...` rimasti in output: **9** occorrenze
  (non riscritti dal flusso corrente).

Comandi usati:

```bash
source .venv/bin/activate
zensical build -f mkdocs.yml > .tmp.docs.zensical.log 2>&1
rg -n '\{\% include-markdown' site/it site/en | wc -l
rg -n 'href=\"/dbzero' site/it site/en | wc -l
```

## PoC tecnico con preprocess (include + rewrite link)

Script introdotto:

- `scripts/build_docs_zensical.py`

Flow:

1. copia `docs/` in `.tmp/zensical_docs`;
2. espande ricorsivamente il tag di include-markdown (esempio: `{ % include-markdown "file.md" % }`);
3. riscrive i link markdown `](/dbzero/...)` in `](/it/dbzero/...)`;
4. genera config temporanea `mkdocs.zensical.yml`;
5. esegue `zensical build`.

Comando:

```bash
source .venv/bin/activate
python scripts/build_docs_zensical.py > .tmp.docs.zensical.preprocessed.log 2>&1
```

Metriche PoC preprocess (misurate):

- `preprocess_files=1434`
- `include_expanded=1564`
- `links_rewritten=3795`
- `raw_include_in_site_zensical=2` (solo testo di esempio nel report, non tag non-processati)
- `abs_root_dbzero_links_in_site_zensical=0`
- `abs_root_it_dbzero_links_in_site_zensical=9`

Comandi verifica:

```bash
rg -n '\{\% include-markdown' site-zensical/it site-zensical/en | wc -l
rg -n 'href=\"/dbzero' site-zensical/it site-zensical/en | wc -l
rg -n 'href=\"/it/dbzero' site-zensical/it site-zensical/en | wc -l
```

## Evidenze esterne consultate

- Material: warning MkDocs 2 / contesto e banner (`NO_MKDOCS_2_WARNING`):  
  https://squidfunk.github.io/mkdocs-material/blog/2026/02/18/mkdocs-2.0/
- Zensical compatibilita` generale:  
  https://zensical.org/compatibility/
- Zensical plugin compatibility (presenza `mkdocs-static-i18n`):  
  https://zensical.org/compatibility/plugins/

## Decisione Go / No-Go (fase corrente)

- **No-Go** al cutover secco con sola config `mkdocs.yml` (senza preprocess).
- **Go condizionato** al cutover secco usando il nuovo preprocess script:
  1. build docs via `python scripts/build_docs_zensical.py`;
  2. verifiche smoke su un set di pagine campione IT/EN;
  3. chiusura warning link/nav residui gia` presenti nella baseline.

## Prossimo step operativo (1 giorno)

1. Collegare CI al comando `python scripts/build_docs_zensical.py`.
2. Pubblicare da `site-zensical/` (o allineare `site_dir` definitivo).
3. Smaltire progressivamente warning link/nav gia` presenti in baseline.
4. Rimuovere dipendenze/plugin MkDocs non piu` usati nel flusso finale.
