# API Resi di vendita `vendite.reso`

## Scopo

Motore **resi di vendita su DDT**: il reso NASCE solo da un DDT **CONSEGNATO**
(pannello nel drawer DDT), mai standalone. Clone strutturale ridotto di
[api_ddt.md](api_ddt.md): niente componenti BoM / PDF / push / note / riepilogo
IVA / indirizzi in questa slice. Le azioni di dominio (conferma, annullo,
generazione DDT di ri-consegna) hanno effetti applicati dalle **fn madri DB** —
nessun cambia-stato generico. Espone la lista configurabile + export e le **due
code di lavoro** (da accreditare / da ri-consegnare), anch'esse liste
configurabili con export.

> Stato: BE completo. Modello e state machine (DRAFT→CONFERMATO, +ANNULLATO),
> residuo ordine, flip DDT→RESO: vedi
> [brief-db-resi-vendita.md](../../../dev/work-done/brief-db-resi-vendita.md).
> Code configurabili + export: vedi
> [brief-be-fe-resi-code-configurabili.md](../../../dev/work-done/brief-be-fe-resi-code-configurabili.md).

## Endpoints

Convenzioni identiche ad api_ddt.md (envelope standard, lista configurabile,
export via `ListaExportService`, scope emittente RLS + filtro applicativo).

### Lista + testata

- Lista `GET /api/v1/vendite/resi/` — lista configurabile `vendite.resi`. Filtri:
  `stato_codice_interno` (DRAFT|CONFERMATO|ANNULLATO), `billing_account_id`,
  `data_da/data_a`, `search` (min 3: numero/destinatario/ba_codice/id fiscale/DDT
  origine), `order_by`/`order_dir` (campi del catalogo).
- **Export** `GET /api/v1/vendite/resi/export/?formato=csv|xlsx` — stessi
  filtri/sort della lista; colonne visibili/ordine/permessi dalla config
  `vendite.resi`. Fetch fino a `EXPORT_MAX_ROWS+1` (nessun troncamento silenzioso;
  oltre soglia → `E_UI_EXPORT_LIMIT_EXCEEDED`).
- Create `POST /api/v1/vendite/resi/` — `{ddt_id, data?, righe?}`. Nasce DRAFT,
  `numero` NULL fino a CONFERMATO (trigger). BA/destinatario/utility/valuta/
  emittente ereditati dal DDT sorgente (**CONSEGNATO**, guard DB).
- Detail `GET /<id>/` — testata + capabilities data-driven
  (`fn_available_actions_reso`).
- Update `PATCH /<id>/` — solo DRAFT (data/meta). Delete `DELETE /<id>/` — hard
  delete solo DRAFT + 0 righe (abbandono bozza).

### Azioni di dominio (fn madri DB, effetti atomici)

- Conferma `POST /<id>/conferma/` — DRAFT→CONFERMATO: numero dal trigger,
  riapertura residuo ordine, proiezione stato ordine, flip DDT→RESO se reso totale.
- Annullo `POST /<id>/annulla/` — storna gli effetti post-conferma; bloccato se
  già ri-spedito (`E_RESO_ANNULLO_CON_RICONSEGNE`).
- Genera ri-consegna `POST /<id>/genera-ddt-riconsegna/` — body
  `{righe?: [{resi_riga_id, qta}], data?}` in unità BASE; omesse/null = tutta la
  copertura residua. Il DDT nasce DRAFT. Righe degeneri → 400 (mai degrado a
  "ri-spedisci tutto").

### Righe

- `GET/POST /<id>/righe/`, `PATCH/DELETE /<id>/righe/<riga_id>/` — solo DRAFT.
  Articolo/UoM/factor sono **snapshot** dalla riga DDT sorgente.
- `GET /api/v1/vendite/ddt/<ddt_id>/righe-per-reso/` — righe DDT con
  `qta_gia_resa`/`qta_resa_residua` (alimenta il pannello "crea reso").

### Code di lavoro (liste configurabili di RIGHE reso CONFERMATE)

Grana RIGA (`resi_riga_id` = dataKey; azione "apri reso" via `reso_id`). Filtri:
`billing_account_id`, `data_da/data_a`, `search` (min 3), `order_by`/`order_dir`
(whitelist per vista). Si auto-limitano ai resi CONFERMATO pertinenti (niente
filtro stato).

- Da accreditare `GET /api/v1/vendite/resi/da-accreditare/` (+ `…/export/`) —
  righe a credito (`tipi_reso.riapre_residuo=false`), config `vendite.resi_da_accreditare`.
- Da ri-consegnare `GET /api/v1/vendite/resi/da-riconsegnare/` (+ `…/export/`) —
  righe con copertura incompleta + `stato_riconsegna` derivato
  (DA_RICONSEGNARE/PARZIALE/COMPLETATA), config `vendite.resi_da_riconsegnare`.

### Lineage / genealogia (brief-be-fe-lineage, 2026-07-15)

- **Passaggi** `GET /api/v1/vendite/resi/<id>/passaggi/` — genealogia del
  reso; catena significativa = **Origine** (reso ← DDT ← ordine ← …, arco R
  ramo inverso). Contratto: [api_lineage_passaggi.md](api_lineage_passaggi.md).
  Nessuna colonna lineage sulla lista resi (fuori perimetro Fase B).

## Codici errore principali

`E_RESO_NOT_FOUND` (404), `E_RESO_DDT_NON_CONSEGNATO` (create su DDT non
consegnato), `E_RESO_QTA_SUPERA_CONSEGNATO` (over-return), `E_RESO_ANNULLO_CON_RICONSEGNE`,
`E_UI_EXPORT_FORMAT_INVALID` (400), `E_UI_EXPORT_LIMIT_EXCEEDED` (422).

## Riferimenti

- Service: `apps/vendite/services/resi_service.py` · Repo:
  `apps/vendite/db/resi_repository.py` (`_list_coda` = letture condivise delle
  due code, whitelist sort + search per vista) · Views: `apps/vendite/api/views_resi.py`
  · URLs: `urls_resi.py`.
- FE: `frontend/src/vendite/resi/` (lista, drawer, code configurabili, host dal
  drawer DDT).
