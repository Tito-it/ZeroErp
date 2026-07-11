# Brief DB — `pdf_mode` esposto in `vendite.vw_ordini_lista` (azione PDF per-riga data-driven)

> **Tipo**: brief DB (target `dev/db-tid`) · **Data**: 2026-07-11 · **Owner**: Tid
> **Origine**: coda della slice «Bottone PDF data-driven via capabilities»
> ([[piano-db-pdf-mode-capabilities-5-domini]] — GIA' APPLICATO). Quel piano ha
> reso data-driven il bottone PDF **nei drawer** (capability `pdf` di
> `fn_available_actions_*`), ma la **lista Ordini** non era coperta.
> **Azioni DB al team DB** ([[feedback_db_actions_passaggio_team]]): questo brief
> descrive *cosa*; la modifica vista la scrive il team DB su `dev/db-tid`.
> **Gate**: la slice FE di consumo (già predisposta, vedi §4) parte **dopo**
> l'applicazione DB ([[feedback_be_fe_attende_prerequisiti_db]]).

## 1. Problema

`OrdiniSearchTable.vue` mostra un'azione PDF **per-riga** in lista. La
capability `pdf {mode, allow_allegati}` introdotta dal piano precedente è
calcolata **per-detail** (`fn_available_actions_ordine` su singolo ordine): le
**righe di lista non la portano**. Perciò la lista usa ancora la costante FE
hardcoded `STATI_ORDINE_CON_DOCUMENTO` (`frontend/src/vendite/ordini/constants.js`)
per decidere se la riga ha un PDF archiviato — **l'unico residuo** della mappa
stato→modalità-PDF che la slice voleva eliminare (le altre 4 famiglie di costanti
e il resto di quella ordini sono già rimosse; drawer tutti data-driven).

La lista ha bisogno di **una sola informazione**: la modalità PDF dello stato
corrente della riga → `pdf_mode`. (Non serve `pdf_allow_allegati`: in lista non
si fa append allegati, quello resta solo nel dialog del drawer.)

## 2. Richiesta — modello

Esporre la colonna **`pdf_mode`** (già esistente su `config.stati_doc_ordini`,
seedata dalla slice precedente) nella vista canonica di lista
**`vendite.vw_ordini_lista`**.

La vista **già fa il JOIN** su `config.stati_doc_ordini sd`
(`ON sd.id = o.stato_doc_ordine_id`) ed espone `sd.codice_interno AS
stato_codice_interno` (create view `20260603-14`, aggiornata da revisioni
successive — **ribasare sulla versione corrente autogen `dbzero`**, non da YAML
stale, [[feedback_no_hand_edit_autogen_docs]]). Basta aggiungere alla SELECT:

```sql
sd.pdf_mode,
```

accanto a `stato_codice_interno`. Pura denominazione/denormalizzazione display,
nessun filtro/scope/logica nuova (coerente con la natura della vista).

## 3. pgTAP

Smoke: la vista espone `pdf_mode` coerente col seed `stati_doc_ordini` per
almeno un caso `ARCHIVE` (es. `CONFERMATO`) e un caso `NONE` (`ANNULLATO`).
(Un ordine `DRAFT` in lista → `PREVIEW`, ma la lista non offre anteprima: la
riga PDF resterà comunque non-archivio; la coerenza col seed è ciò che si testa.)

## 4. Recepimento a valle (slice FE — GATE: DB applicato)

`vendite.vw_ordini_lista` è letta dal repo con `SELECT v.*` → `pdf_mode` arriva
a `row.pdf_mode` **senza modifiche BE**. La slice FE:

- `OrdiniSearchTable.vue`: sostituire i due usi di
  `STATI_ORDINE_CON_DOCUMENTO.includes(row.stato_codice_interno)` con
  `row.pdf_mode === PDF_MODE.ARCHIVE` (enum già centralizzato in
  `frontend/src/documenti/constants.js`, come `EntityPdfButton`);
- `frontend/src/vendite/ordini/constants.js`: **eliminare** `STATI_ORDINE_CON_DOCUMENTO`
  (ultimo residuo) e il relativo commento «RESIDUO TRANSITORIO».

Progetto non in produzione → switch big-bang, nessun dual-path
([[project_no_produzione_solo_sviluppo]]).

## 5. Note

- **Scope minimo**: nessuna delle altre viste di lista vendite ha un'azione PDF
  inline (verificato: solo `OrdiniSearchTable` importa quelle costanti) → si
  espone `pdf_mode` **solo** su `vw_ordini_lista`. Se in futuro una lista gemella
  (DDT, preventivi…) dovesse offrire PDF per-riga, si replicherà lì.
- **Doc auto-gen `dbzero`**: da rigenerare dopo l'apply (cambia `vw_ordini_lista`).
