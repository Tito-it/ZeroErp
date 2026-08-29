# API DDT di vendita `vendite.ddt`

## Scopo

CRUD operativo dei **DDT di vendita** (documenti di trasporto), gemello
strutturale di [api_ordini.md](api_ordini.md) (D-4: stessa impronta, logica
DDT). Espone testata trasporto, **righe** con **componenti BoM**, **emissione**
(`DRAFT -> EMESSO`, numero assegnato dal trigger a EMESSO — C6), cambio stato
data-driven, **push singolo a commessa** (fatturazione differita), lista
configurabile + export, note partizionate, **riepilogo IVA** e **indirizzi
documento**. L'evasione (genera DDT da ordine) vive sul dominio ORDINE:
`POST /api/v1/vendite/ordini/<id>/genera-ddt/`.

> Stato: BE completo (brief-be-ddt-vendita + slice riepilogo IVA/indirizzi
> 2026-07-11/12). Per il modello e la state machine
> (DRAFT→EMESSO→SPEDITO→CONSEGNATO→RESO, +ANNULLATO) vedi
> [brief-db-ddt-vendita-evasione-e-stati.md](../../../dev/work-done/brief-db-ddt-vendita-evasione-e-stati.md).

## Endpoints

Convenzioni identiche ad api_ordini.md (envelope, lista configurabile
`vendite.ddt`, export via `ListaExportService`, note via
`PartitionedNoteRepository`, documenti/stampa via factory
`build_documenti_sorgente_views` sorgente `DDT_VENDITA`).

- Lista `GET /api/v1/vendite/ddt/` — filtri: `stato_codice` (codice_interno),
  `billing_account_id`, `utility_id`, `data_da/data_al`, `search` (min 3:
  numero/destinatario/ba_codice/id fiscale). Scope emittente (RLS + filtro
  applicativo).
- Export `GET /api/v1/vendite/ddt/export/?formato=csv|xlsx`.
- Form-defaults `GET /api/v1/vendite/ddt/form-defaults/`.
- Create `POST /api/v1/vendite/ddt/` — `billing_account_id` **obbligatorio**
  (risolve emittente via trigger `trgfn_ddt_normalize`, NOT NULL + scope RLS);
  `destinatario_soggetto_ruolo_id` derivato dal BA se assente. Stato iniziale
  DRAFT, `numero` NULL fino a EMESSO. **Auto-assegnazione indirizzo** (UX v2):
  alla creazione (standalone ed evasione, se la cascata non l'ha gia' portato)
  lo slot Consegna viene valorizzato best-effort dall'indirizzo di RUOLO del
  cliente (CON, fallback FATT); mai bloccante.
- Detail `GET /api/v1/vendite/ddt/<id>/` — testata + capabilities data-driven
  (`fn_available_actions_ddt`).
- Update `PATCH /api/v1/vendite/ddt/<id>/` — solo DRAFT; cliente immutabile.
- Delete `DELETE /api/v1/vendite/ddt/<id>/` — hard delete solo DRAFT
  (pattern abbandono bozza).
- Riepilogo IVA `GET /api/v1/vendite/ddt/<id>/riepilogo-iva/` — lettura pura
  da `vendite.vw_ddt_riepilogo_iva_dettaglio` (ROUND 2 per aliquota, DPR
  633/72 art. 21; righe con `prezzo_unitario` NULL escluse: DDT solo di
  trasporto → riepilogo vuoto). Shape identico a ordini
  ([api_ordini.md](api_ordini.md) §Riepilogo IVA).
- Indirizzi `GET/POST /<id>/indirizzi/` + `DELETE /<id>/indirizzi/<iid>/` —
  BB condiviso, vedi [api_indirizzi_documento.md](api_indirizzi_documento.md).
  Ambito `DDT`: solo `CON` (consegna), **obbligatorio all'emissione** (guard
  DB `E_INDIRIZZO_DOC_OBBLIGATORIO`).
- Emetti `POST /api/v1/vendite/ddt/<sorgente_id>/emetti/` (multipart) —
  DRAFT→EMESSO + genera PDF accompagnatorio + allegati, atomico (factory
  documenti). Il trigger assegna `numero` e valida componenti BoM + indirizzi
  obbligatori.
- Cambia stato `POST /api/v1/vendite/ddt/<id>/cambia-stato/` — body
  `{stato_codice}` (matrice `config.transizioni_stati_ddt`).
- Push `POST /api/v1/vendite/ddt/<id>/push/` — push singolo a commessa
  (sorgente `DDT_VENDITA`, fatturazione differita).
- Righe `GET/POST /<id>/righe/`, `PATCH/DELETE /<id>/righe/<riga_id>/` — solo
  DRAFT; `prezzo_unitario`/`iva_id` nullable (DDT anche solo di trasporto).
  ⭐ **Il DDT è l'unico documento dove il prezzo mancante non è un errore**:
  vedi la sezione dedicata più sotto.
- Componenti BoM `GET /<id>/righe/<rid>/componenti/` +
  `PATCH/DELETE .../componenti/<cid>/` + preview — mixin condiviso.
- Note `GET/POST /<id>/note/` + `GET/PATCH/DELETE /<id>/note/<note_id>/` —
  building block, contratto comune in [api_note_documento](../../core/manual/api_note_documento.md)
  (partizione `vendite.note_ddt`, `target_tipo='DDT'`).
- Documenti/Stampa `…/<id>/documenti/…` — vedi api_ordini.md §Documenti.

### Lineage / genealogia (brief-be-fe-lineage, 2026-07-15)

- **Colonne lineage in lista** (Fase B): la lista espone anche `fase`
  (proiezione normalizzata dallo stato), `pratica_id`/`pratica_numero`/
  `n_pratiche` (pratica collegata), `frontiera_tipo_id` +
  `frontiera_tipo_codice_interno` e `frontiera_natura_doc_codice_interno`
  (dalla vista, non piu' decodificati dal repository: changeSet `20260829-01/02`
  — ⛔ il nome e' cambiato, e con lui la sorgente),
  `frontiera_codice`/`frontiera_stato_codice_interno`/`frontiera_fase`,
  `n_discendenti_attivi`, `is_transitato` — dalla vista canonica estesa
  (LEFT JOIN `vendite.vw_documento_lineage`). Colonne configurabili
  `pratica`/`fase`/`transito` visibili di default (seed preset). `order_by`
  accetta anche `pratica_numero` e `fase` (la frontiera NON e' ordinabile).
- **Passaggi** `GET /api/v1/vendite/ddt/<id>/passaggi/` — genealogia del
  documento: pratica + frontiera + catena transiti in entrambe le direzioni.
  Contratto completo nel manuale del BB condiviso:
  [api_lineage_passaggi.md](api_lineage_passaggi.md).

## Righe senza prezzo — il campo `prezzo_esito`

⭐ **Il DDT è l'unico documento dove il prezzo mancante non è un errore.** Una
riga in conto visione, un reso in ri-consegna, un articolo fuori listino: sono
casi legittimi, e pretendere il prezzo significherebbe impedire di salvare la
riga. Ordini, preventivi, contratti e offerte continuano invece a **rifiutare**
la riga: lì il prezzo assente è un difetto.

### Cosa risponde `POST /api/v1/vendite/ddt/{id}/righe/`

Quando il prezzo non è passato dal client, il BE lo risolve. Se **non** è
risolvibile, la riga **si salva lo stesso** con `prezzo_unitario = null`, e la
risposta porta il motivo:

```json
{ "data": { "ddt_id": 12, "riga_id": 31, "is_composito": false,
            "prezzo_esito": { "codice": "E_CATEGORIA_LISTINO_NON_MAPPATA",
                              "messaggio": "Categoria cliente non mappata a listino per la quadrupla indicata." } } }
```

Quando il prezzo si risolve, `prezzo_esito` è `null`.

| | |
|---|---|
| **dov'è** | dentro `data`, **non** nell'envelope degli errori: la riga è stata salvata, quindi non è un fallimento (DEC-3) |
| **il testo** | è il messaggio a catalogo del codice, **senza segnaposto** — il FE lo mostra, non lo riscrive e non ne tiene una copia i18n (DEC-4) |
| **persistenza** | il motivo resta anche dopo il ricarico: sta in `ddt_righe.meta.prezzo_resolver_context.esito_codice`, stesso nome della colonna che il DB usa sui componenti (DEC-8) |

⛔ **`importo_riga` esce `null`, non `0`.** La lista righe non fa più
`COALESCE(prezzo, 0)`: uno zero sarebbe indistinguibile da una riga che vale
davvero zero, e il totale del documento tornerebbe «giusto» sommando quel che
non c'è.

⛔ **Il padre di un kit si inserisce con prezzo `null`**, non `0`: il ricalcolo
lato DB mette `NULL` se anche un solo figlio è scoperto.

### Cosa serve al client per decidere

`GET /api/v1/vendite/ddt/{id}/` espone **`causale_trasporto_fatturabile`**:

* `true` — il documento vende: una riga senza prezzo bloccherà l'emissione;
* `false` — non vende (conto visione, ri-consegna): il prezzo assente è normale;
* `null` — **causale non ancora scelta**, che è un terzo caso e non un `false`.

Il BE non fa `COALESCE(false)` di proposito: al client serve distinguere «non
vende» da «non lo so ancora» (DEC-5).

Riferimento: `docs/it/dev/work-done/brief-ddt-righe-senza-prezzo.md`.

## Codici errore principali

`E_DDT_NOT_FOUND` (404), `E_DDT_VALIDAZIONE` (400), `E_DDT_STATO_TRANSIZIONE`,
`E_STATO_DDT_TRANSIZIONE_NON_VALIDA` (matrice), `E_QTA_SUPERA_RESIDUO`
(evasione), `E_INDIRIZZO_DOC_OBBLIGATORIO` (emissione senza CON),
`E_TIPO_INDIRIZZO` (whitelist), `E_INDIRIZZO_SNAPSHOT_NOT_FOUND` (404).

## Riferimenti

- Service: `apps/vendite/services/ddt_service.py` · Repo:
  `apps/vendite/db/ddt_repository.py` (mixin componenti + riepilogo IVA +
  indirizzi) · Views: `apps/vendite/api/views_ddt.py` + `ddt_documenti_views.py`
  · URLs: `urls_ddt.py`.
- FE: `frontend/src/vendite/ddt/` (lista, drawer, evasione dal drawer ordine).
