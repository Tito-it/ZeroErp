# Brief DB — Bottone PDF data-driven via capabilities (5 domini vendite)

> **Tipo**: brief DB (target `dev/db-tid`) · **Data**: 2026-07-10 · **Owner**: Tid
> **Origine**: finding di code-review sulla slice stampa DDT (altitude): la mappa
> stato→modalità-PDF è oggi **hardcoded nel FE** per 5 domini, mentre il commento
> la dichiara "data-driven da config" — contraddizione. Il meccanismo giusto
> esiste già: le capabilities `script.fn_available_actions_*`.
> **Azioni DB al team DB** ([[feedback_db_actions_passaggio_team]]): questo brief
> descrive *cosa*; DDL/fn/seed/pgTAP li scrive il team DB su `dev/db-tid`.
> **Gate**: la slice FE/BE di consumo parte **dopo** l'applicazione DB
> ([[feedback_be_fe_attende_prerequisiti_db]]).

## 1. Problema

`EntityPdfButton` (FE condiviso) decide la modalità del bottone PDF da **liste di
stati hardcoded** per dominio (`STATI_ORDINE_ANTEPRIMA_PDF`, `STATI_DDT_CON_DOCUMENTO`,
e omologhe per preventivi/offerte/contratti in `frontend/src/vendite/*/constants.js`):

- `preview` → anteprima on-demand (bozza, non persistita);
- `archive` → apertura gestione documenti generati (PDF archiviati);
- `disabled` → nessuna gestione (es. ANNULLATO).

Se si aggiunge/rifasa uno stato in `config.stati_doc_*` senza toccare i file FE,
il bottone **degrada silenziosamente a disabled**. La verità deve stare nel
modello, come già avviene per `available_actions` (matrici transizioni).

## 2. Richiesta — modello

**2.1 Colonna `pdf_mode` sulle 5 tabelle stati** (`config.stati_doc_preventivi`,
`config.stati_doc_offerte`, `config.stati_doc_contratti`, `config.stati_doc_ordini`,
`config.stati_doc_ddt`):

```
pdf_mode varchar NOT NULL DEFAULT 'NONE'
  CHECK (pdf_mode IN ('PREVIEW','ARCHIVE','NONE'))
```

**2.2 Seed** allineato al comportamento FE attuale (single source: le costanti
FE odierne, che questa slice manda in pensione):

| Dominio | PREVIEW | ARCHIVE | NONE |
|---|---|---|---|
| ordini | DRAFT | CONFERMATO, EVASO, ALLOCATO, SPEDITO, CONSEGNATO, FATTURATO | ANNULLATO (e altri) |
| ddt | DRAFT | EMESSO, SPEDITO, CONSEGNATO, RESO | ANNULLATO |
| preventivi / offerte / contratti | stato bozza | stati post-emissione non annullati | annullati/scaduti |

(Per preventivi/offerte/contratti il team DB allinei il seed alle costanti FE
correnti in `frontend/src/vendite/{preventivi,offerte,contratti}/constants.js`.)

**2.3 Esposizione nelle capabilities.** Estendere le 5 fn
`script.fn_available_actions_{preventivo,offerta,contratto,ordine,ddt}` con un
blocco:

```json
"pdf": { "mode": "PREVIEW" | "ARCHIVE" | "NONE" }
```

letto dalla colonna `pdf_mode` dello stato corrente del documento. Nessuna
logica addizionale: pura proiezione config→capability (stesso stile di
`can_edit_testata`).

**2.4 pgTAP**: per un dominio pilota (DDT), verificare che il blob capability
esponga `pdf.mode` coerente col seed per DRAFT/EMESSO/ANNULLATO.

## 3. Recepimento a valle (slice FE successiva, fuori da questo brief)

`EntityPdfButton` riceve `pdf.mode` dal detail (che già include il blob
capabilities in tutti i drawer della famiglia) e **le costanti
`STATI_*_ANTEPRIMA_PDF` / `STATI_*_CON_DOCUMENTO` si eliminano** dai 5
`constants.js`. Progetto non in produzione → switch big-bang, nessun dual-path
([[project_no_produzione_solo_sviluppo]]).
