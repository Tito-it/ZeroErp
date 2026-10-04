# Brief DB — I valori ammessi di una versione di template: da CHECK a vocabolario

> **Chi scrive:** sessione BE/FE (`dev/backend-tid`), 2026-10-03. **A chi:** team DB
> (`dev/db-tid`); poi BE/FE (§4).
> **Origine:** revisione del drawer dei modelli di documento (richiesta di Tid, 2026-10-03), che ha
> portato la versione in un drawer suo (`TemplateVersioneDrawer`).
> **Stato:** ⏳ da valutare e scrivere (team DB). Nessuna urgenza: il frontend è stato riallineato a
> mano (§2), ma resta una copia.

## 1. Il problema

Tre colonne di `documenti.template_documenti_versioni` hanno un insieme chiuso di valori, scritto
**solo** come CHECK:

| Colonna | CHECK | Valori |
| --- | --- | --- |
| `formato_template` | `chk_template_documenti_versioni_formato` | `HTML`, `HTML_MARKDOWN_BLOCKS` |
| `page_format` | `chk_template_documenti_versioni_page_format` | `A4`, `A3`, `LETTER` |
| `page_orientation` | `chk_template_documenti_versioni_orientation` | `PORTRAIT`, `LANDSCAPE` |

Un CHECK non si legge da una tendina. Così l'insieme vive in **tre** posti:

* il CHECK, a DB;
* tre `frozenset` nel backend (`template_versioni_admin_service.py`, `_FORMATI_VALIDI`,
  `_PAGE_FORMATS_VALIDI`, `_PAGE_ORIENTATIONS_VALIDI`), che anticipano il rifiuto;
* tre array nel frontend (`config/constants/documentiVersioniWhitelists.js`), che riempiono le
  tendine.

## 2. Il controesempio (fatto datato, 2026-10-03)

La copia del frontend era **già divergente**: offriva `MARKDOWN` e `A5`, che il DB rifiuta, e non
offriva `HTML_MARKDOWN_BLOCKS` né `A3`. Scegliendo «A5» la versione non si salvava; «A3» non si
poteva scegliere. Riallineata il 2026-10-03 leggendo il corpo dei CHECK da `pg_constraint`. La doc
API (`api_documenti_templates.md` §7) era giusta, il frontend no: nessun presidio confrontava le
copie.

## 3. Richiesta

| # | Cosa |
| --- | --- |
| **R-DB-1** | Tre vocabolari (`documenti.formati_template`, `documenti.formati_pagina`, `documenti.orientamenti_pagina`, o i nomi della casa), con `codice` + `etichetta_key` sulla forma di `config.esposizioni_componente` (`20261001-41`), e una FK dalle tre colonne al posto dei CHECK. Seed in `80_data` coi valori di §1 |
| **R-DB-2** | Le tre tabelle nella whitelist del lookup (`tabelle_gestibili.csv`, `lookup = true`, `pannello = false`), come R-DB-K1 dell'esposizione dei componenti |
| ❓ | Da decidere col team DB se `attivo` serve: sono la semantica del render (cosa sa stampare il motore), non una configurazione — stesso ragionamento del §9.2 di `brief-db-esposizione-componenti-kit-in-fattura` |

## 4. Dopo, lato BE/FE (si prenota qui)

* BE: le tre voci fra le `_LOOKUP_SPECIALIZZATE` (`etichetta_key`); via i tre `frozenset` del
  service — il rifiuto lo dà la FK, tradotto da `map_integrity_error`.
* FE: le tendine del `TemplateVersioneDrawer` dal lookup (etichette dal DB, ripiego sul codice); si
  ritira `documentiVersioniWhitelists.js`.
