# Brief BE — DDT vendita: service, repository, endpoint (gemello ordini)

> **Tipo**: brief backend (target `dev/backend-tid`) · **Data**: 2026-07-09 · **Owner**: Tid
> **Stato**: ✅ **CHIUSO (2026-07-13)** — tutto lo scope del brief realizzato: slice principale + PDF (§12–§13), export lista, endpoint riepilogo-iva, CRUD `ddt_indirizzi`, uniformazione emittente (§14). Fuori scope (brief propri): **slice RESI** (`work-in-progress/brief-db-resi-vendita.md`) e **Lineage Fase 4** (`work-in-progress/brief-db-lineage-documenti-vendite.md` + tracker `analisi-ddt §6`).
> **Design-of-record**: [analisi-ddt-vendita-stato-e-sviluppi.md](analisi-ddt-vendita-stato-e-sviluppi.md)
> · **Prerequisito DB**: [brief-db-ddt-vendita-evasione-e-stati.md](../work-done/brief-db-ddt-vendita-evasione-e-stati.md)
> **Gate**: parte a oggetti DB applicati ([[feedback_be_fe_attende_prerequisiti_db]]).
> **Principio guida (D-4)**: **clonare il dominio ORDINI**, che è l'esempio più
> pulito e moderno; stessa impronta, logica DDT diversa. Non duplicare BB
> ([[feedback_vue_reuse]], regola del 2 [[feedback_regola_del_2_estrai_bb]]).

---

## 1. Scopo

Portare i DDT di vendita da "modello DB dormiente" a dominio BE completo:
CRUD testata/righe/componenti/indirizzi/note, emissione + macchina a stati
data-driven, **generazione DDT da ordine** (evasione) e **push a commessa**
(fatturazione differita). Il push handler `HandlerDdt` e la mappa
`fn_list_ddt_da_pushare` **esistono già** (`commesse_source_handlers.py:708`,
`commesse_repository.py:35`): non si tocca, si alimenta.

## 2. Prerequisiti DB — ✅ TUTTI APPLICATI (verificato 2026-07-10)

Slice DB atterrata su `dev/db-tid` (consuntivo brief DB §14). Verificato contro la doc
del DB vivo:

| Oggetto DB | Stato | Firma/nota reale |
|---|---|---|
| `vendite.fn_genera_ddt_da_ordine` | ✅ | **`(p_ordine_id bigint, p_righe jsonb DEFAULT NULL, p_data date DEFAULT CURRENT_DATE) → bigint`** — 3 param (no `p_emittente_sr_id`); `p_righe=[{ordine_riga_id, qta_da_evadere}]` in **unità operativa** |
| `config.transizioni_stati_ddt` + `trgfn_ddt_guard_transizione` | ✅ | matrice seedata (payload `meta.ui`: `action_key/label_key/severity/icon/requires_confirm/outlined/manuale`) |
| `config.stati_doc_ordini.PARZIALMENTE_EVASO` (id 9) + matrice | ✅ | fase IN_CORSO, terminale=f; `EVASO` invariato |
| `ddt_righe.sconto_percentuale` + `iva_id` (FK `fk_ddt_vendita_r_iva`) | ✅ | C8 |
| Rimozione UNIQUE `uq_ddt_v_sorgente_fk` → indice `ix_ddt_v_sorgente` | ✅ | multi-DDT A-1 |
| **numero a EMESSO**: `trgfn_ddt_gen_numero_emesso` (BEFORE INS/UPD), DDT fuori da `sistema_codici` | ✅ | il `numero` è NULL in DRAFT, assegnato alla transizione stato→EMESSO |
| **`vendite.vw_ddt_lista`** (view lista/dettaglio, `security_invoker=on`) | ✅ | colonne §5.1 |
| **`script.fn_available_actions_ddt(p_ddt_id) → jsonb`** | ✅ | output §4-capabilities |
| Seed `ui.lista_definizione`/`lista_colonna` `codice='vendite.ddt'` (id 8, 19 col) | ✅ | i18n `vendite.ddt.col_*` |
| `config.messaggi_errore` `E_DDT_*`/`E_STATO_DDT_*` (521-524) + `E_QTA_SUPERA_RESIDUO` (85) | ✅ | testo RAISE lato DB |
| `vendite.note_ddt`, `fn_list_ddt_da_pushare`, `fn_ddt_riga_componenti_init/preview` | ✅ | pre-esistenti |
| Seed `config.causali_trasporto` (8) + `config.aspetti_beni` (10) | ✅ | PDF-ready |

**Addendum SCOPE §15 — ✅ APPLICATO (2026-07-10, `dev/db-tid` 114185433).** Il DB ha
scelto l'opzione migliorativa "emittente memorizzato" (mirror ordini/preventivi):

| Oggetto DB (addendum) | Stato | Nota |
|---|---|---|
| `vendite.ddt.emittente_fiscale_id` (bigint **NOT NULL**, FK `fk_ddt_v_emittente_fiscale`) | ✅ | risolto in scrittura da `trgfn_ddt_normalize`: ereditato dall'ordine sorgente, o dal `billing_account` per lo standalone (`fn_get_emittente_fiscale_pk`) |
| RLS su `vendite.ddt`: policy `rls_ddt_ef_whitelist` (FOR ALL, enabled non forced) + guard scrittura `trgfn_guard_emittente_scope` | ✅ | scope via `script.fn_scope_ef_whitelist` sui GUC operatore, parità con ordini/preventivi/fatture |
| `vw_ddt_lista` + `emittente_fiscale_id` / `emittente_fiscale_codice` | ✅ | abilita il filtro applicativo BE (defense-in-depth) |
| pgTAP `test-rls-ddt-ef-whitelist-write.sql` | ✅ | |

**Conseguenze BE (recepite nel codice 2026-07-10):** filtro applicativo emittente
**attivato** in `DdtRepository.list_ddt` (mirror ordini); `_resolve_emittente_sr_id`
legge la colonna memorizzata (niente risoluzione runtime BA→emittente);
`crea_ddt` richiede `billing_account_id` (senza, il trigger non può valorizzare
l'emittente NOT NULL → guard parlante); FK `fk_ddt_v_emittente_fiscale` mappata
in `_FK_CONSTRAINTS`.

**Gate superato**: prerequisiti DB completi (slice principale + addendum scope).

## 3. Struttura file — clonare da ordini

Riferimento (tutto sotto `backend/apps/vendite/`):

| Nuovo file DDT | Clona da | Differenze principali |
|---|---|---|
| `services/ddt_service.py` | `services/ordini_service.py` (modulo di funzioni libere, **non** classe) | §4 |
| `db/ddt_repository.py` (**estendere** l'esistente) | `db/ordini_repository.py` | §5 |
| `api/views_ddt.py` | `api/views_ordini.py` | §6 |
| `api/urls_ddt.py` | `api/urls_ordini.py` (montare in `api/urls_v1.py`: `path("ddt/", include("apps.vendite.api.urls_ddt"))`) | §6 |
| blocco note in `api/note_views.py` | righe 99-119 (blocco ORDINE) | §7 |
| famiglia `E_DDT_*` in `apps/core/services/error_policies.py` | blocco `E_ORD_*` (da riga 1742) | §8 |
| `tests/services/test_ddt_service.py` + `tests/api/test_ddt_api.py` | omonimi ordini | §10 |

`types.py`: gli ordini usano **`dict` grezzo** (nessun TypedDict). Per i DDT
**seguire lo stesso pattern** (dict), salvo tua diversa indicazione.

## 4. `ddt_service.py` — funzioni (mirror ordini, con logica DDT)

Costanti di dominio: `_STATO_BOZZA="DRAFT"`, `_STATO_EMESSO="EMESSO"`,
`_STATI_MODIFICABILI={"DRAFT"}`, whitelist campi create/update testata+riga.

**Letture/lista** (mirror): `list_ddt_rows(...)`, `list_ddt(...)` (envelope paginato),
`get_ddt(ddt_id)` (**merge capabilities** da `repo.get_capabilities` + `righe_count`),
`list_righe(ddt_id)`, `list_riepilogo_iva(ddt_id)`, `resolve_filtri_export_label(...)`.

**CRUD testata**:
- `crea_ddt(payload)` — **DDT standalone** (senza sorgente): richiede `billing_account_id`
  proprio; DRAFT; **numero NON assegnato in DRAFT** (C6, lo assegna l'emissione).
- `aggiorna_ddt(ddt_id, payload)` — solo DRAFT; billing_account immutabile
  (`E_DDT_CLIENTE_IMMUTABILE`).
- `elimina_ddt(ddt_id)` — hard-delete solo bozza orfana (0 righe, 0 fulfillment).

**Cambio stato (data-driven, C7)**: `cambia_stato(ddt_id, stato_codice)` — target =
`available_actions[].target_state`, **nessun grafo in Python**, enforcement dal trigger
DB `trgfn_ddt_guard_transizione`. `emetti(ddt_id, ...)` — DRAFT→EMESSO: **qui il DB
assegna il `numero`** (C6) e scatta il guard approvazione componenti (brief DB §6).

**CRUD righe + componenti BoM**: `gestisci_riga`/`aggiorna_riga`/`elimina_riga` (solo
DRAFT); `preview_componenti_riga`, `list_componenti_riga`, `update_componente`,
`delete_componente` — identici a ordini (mixin componenti).

**Generazione da ordine (evasione)** — l'endpoint vive nel **dominio sorgente
(ordine)**, ma la logica sta qui:
- `crea_ddt_da_ordine(ordine_id, righe=None) -> dict` — delega a
  `DdtRepository.push_da_ordine(ordine_id, righe)` → `SELECT vendite.fn_genera_ddt_da_ordine(...)`.
  La fn DB è **atomica** (crea testata+righe+fulfillment+proiezione stato ordine):
  **niente `transaction.atomic()` extra** (come `crea_ordine_da_preventivo`).
  Ritorna `{ddt_id, numero(None in DRAFT), ordine_id}`.

**Push a commessa**: `push_a_commessa(ddt_id, user=None)` — `transaction.atomic()` che
avvolge `commesse_service.pr_run_commesse_push_one(sorgente_codice="DDT_VENDITA",
sorgente_uid=ddt_id)`. Eleggibilità (SPEDITO/CONSEGNATO) già in `fn_list_ddt_da_pushare`.

**Helper**: riusare il pattern `_db_errors(op)` di ordini (context manager che traduce
`IntegrityError`/`DatabaseError` P0001 e estrae il codice `E_*` via regex) — **copiare
il context manager**, non reinventarlo.

## 5. `ddt_repository.py` — estendere l'esistente

Oggi `DdtRepository(ComponentiRepositoryMixin)` legge solo `ddt_righe_componenti`
(`_componenti_table_name="vendite.ddt_righe_componenti"`, `_componenti_fk_riga="riga_ddt_id"`).
**Estenderlo** allo schema di `OrdiniRepository`:

- **Letture**: `list_ddt(...)` su **`vw_ddt_lista`** (alias `v`, WHERE dinamico
  stato/BA/utility/data/search ILIKE + **scope emittente** via
  `script.fn_get_emittenti_scope_pk_ids(auth_user_id)`, COUNT separato, ORDER BY
  whitelisted `+ v.id ASC` tiebreaker, `LIMIT min(limit,200)`); `get_ddt(ddt_id)`
  (view + JOIN `vendite.ddt` per `meta`); `get_capabilities(ddt_id)` =
  `call_jsonb_fn("script.fn_available_actions_ddt", ddt_id)`; `get_stato_codice`,
  `list_righe`, `get_riga`, `list_riepilogo_iva`, `get_for_documento_generation`.
- **Scritture**: `create_ddt(...)` (INSERT, colonne opzionali omesse se None;
  `numero` lo mette il trigger solo a EMESSO — C6), `update_ddt`, `delete_ddt`,
  `update_stato` (transizione validata dal trigger), righe `next_riga_nr`/`create_riga`/
  `update_riga`/`delete_riga`.
- **fn DB**: `push_da_ordine(ordine_id, righe, data=None)` → `SELECT vendite.fn_genera_ddt_da_ordine(%s, %s::jsonb, COALESCE(%s, CURRENT_DATE))`
  (**3 param**; `righe` in **unità operativa**); `init_componenti_riga`/`preview_componenti_riga`
  (fn `fn_ddt_riga_componenti_*`); `count_righe_pushable(ddt_id)` → `fn_list_ddt_da_pushare(NULL,NULL,NULL,%s)`.
- **numero a EMESSO (C6)**: `emetti` = `update_stato(ddt_id, EMESSO_id)`; il numero lo assegna
  il trigger `trgfn_ddt_gen_numero_emesso` (BEFORE UPDATE) — il service non passa il numero.

## 6. Endpoint

**Dominio DDT** (`views_ddt.py` + `urls_ddt.py`, `area_funzionale="vendite"`; seguire il
pattern-ordini **senza `post_permission`** salvo diversa scelta — vedi §11):

| Metodo | Path | View | Azione |
|---|---|---|---|
| GET/POST | `/api/v1/vendite/ddt/` | `ApiDdtList` | lista + crea (standalone) |
| GET | `/api/v1/vendite/ddt/export/` | `ApiDdtExport` | export CSV/XLSX (`?formato=`) |
| GET/PATCH/DELETE | `/api/v1/vendite/ddt/<id>/` | `ApiDdtDetail` | dettaglio (+capabilities) / patch / delete |
| POST | `/api/v1/vendite/ddt/<id>/emetti/` | `ApiDdtEmetti` | DRAFT→EMESSO (assegna numero) |
| POST | `/api/v1/vendite/ddt/<id>/cambia-stato/` | `ApiDdtCambiaStato` | transizione data-driven `{stato_codice}` |
| POST | `/api/v1/vendite/ddt/<id>/push/` | `ApiDdtPush` | push a commessa (DDT_VENDITA) |
| GET/POST | `/api/v1/vendite/ddt/<id>/righe/…` | `ApiDdtRighe*` | CRUD righe |
| GET/PATCH/DELETE | `/api/v1/vendite/ddt/<id>/righe/<rid>/componenti/…` | `ApiDdtRigaComponenti*` | componenti BoM |
| GET | `/api/v1/vendite/ddt/<id>/riepilogo-iva/` | `ApiDdtRiepilogoIva` | IVA aggregata |
| GET/POST · GET/PATCH/DELETE | `/api/v1/vendite/ddt/<id>/note/[<nid>/]` | note (factory) | §7 |

**Dominio ORDINE (sorgente)** — l'endpoint di conversione va in `views_ordini.py`/`urls_ordini.py`
(come `genera-ordine` sta nei preventivi):

| POST | `/api/v1/vendite/ordini/<ordine_id>/genera-ddt/` | `ApiOrdineGeneraDdt` → `ddt_service.crea_ddt_da_ordine(ordine_id, _parse_righe(payload))` |

Body: `{righe: [{ordine_riga_id, qta_da_evadere}]}` (NULL = tutto il residuo). Import
locale di `ddt_service` nel metodo (evita cicli).

## 7. Note DDT — clonare ~21 righe

Clonare il blocco ORDINE di `api/note_views.py` (righe 99-119) con:
`partition_table="vendite.note_ddt"`, `target_tipo="DDT"`, `parent_table="vendite.ddt"`,
`parent_pk="id"`, `child_table="vendite.ddt_righe"`, `child_parent_fk="ddt_id"`,
`model_permission=("vendite","ddt")`; + 2 righe URL in `urls_ddt.py` + import. Il BB
(`make_note_views`/`PartitionedNoteRepository`) e la whitelist `DDT` sono già pronti.

## 8. `error_policies.py` — famiglia `E_DDT_*`

Registrare speculare a `E_ORD_*` (stesse coppie status/ui_action):
`E_DDT_NOT_FOUND` (404/show_empty_state), `E_DDT_VALIDAZIONE` (400/highlight_form_fields),
`E_DDT_CLIENTE_IMMUTABILE` (400/show_error_banner), `E_DDT_STATO_TRANSIZIONE`
(409/show_error_banner), `E_DDT_NESSUNA_RIGA` (409), `E_DDT_ORDINE_STATO_NON_EVADIBILE`
(409), `E_DDT_NIENTE_DA_EVADERE` (409). **Registrare anche `E_QTA_SUPERA_RESIDUO`** (il
guard fulfillment lo solleva in evasione — brief DB C2, over-shipping) se non già presente.
I codici sollevati dai trigger DB (`E_STATO_DDT_*`, `E_COMPONENTE_PREZZO_PENDENTE`)
arrivano via regex `_db_errors`: comunque registrarne la policy per la UI.

## 9. Riepilogo dipendenze DB — ✅ TUTTE CONSEGNATE

Storico: il capitolato Fase 1 non copriva la read-side; segnalati al team DB
`vw_ddt_lista` + `script.fn_available_actions_ddt` (consegnati col consuntivo §14
del brief DB) e poi l'addendum scope §15 (colonna emittente + RLS + vista,
consegnato 2026-07-10). Nessuna dipendenza DB residua per questa slice.

## 10. Test (mirror ordini)

- `tests/services/test_ddt_service.py` (`SimpleTestCase` + mock repo, `_patch_atomic_noop`):
  guard stato, override componenti, `_db_errors`, **evasione da ordine** (residuo,
  copia snapshot, over-shipping → `E_QTA_SUPERA_RESIDUO`), push commessa, standalone.
- `tests/api/test_ddt_api.py` (`JwtMockedApiTest`): list/create/emetti/cambia-stato/push/
  patch/export + `ApiOrdineGeneraDdt`.
- Smoke E2E (`backend/scripts/tests/`): ordine CONFERMATO (trigger SPEDITO) → genera-ddt →
  emetti → SPEDITO → push commessa → attività fatturabile (giro completo differito).

## 11. Punti aperti — CHIUSI in implementazione (2026-07-10)

- **`post_permission`**: DDT segue il pattern-ordini — nessun `post_permission`,
  solo `area_funzionale="vendite"`.
- **Indirizzi DDT** (`ddt_indirizzi`): rimandati alla slice **standalone/PDF**
  (nessun CRUD in questa slice; snapshot ereditati quando servirà la stampa).
- **`types.py`**: dict grezzo (come ordini), nessun TypedDict.
- **Cliente obbligatorio in create** (conseguenza addendum §15): `crea_ddt`
  richiede `billing_account_id` — l'emittente NOT NULL è risolto dal trigger a
  partire dal BA.

## 12. Consuntivo realizzazione (2026-07-10) — ✅ REALIZZATO

Slice BE completa sul working tree `dev/backend-tid` (**non committato**, il commit
lo fa Tid). `manage.py check` pulito; **84 test verdi** (35 DDT + 49 ordini, no
regressione). Ambiente sandbox senza Postgres reale: la suite completa ha fallimenti
pre-esistenti/ambientali (connection refused) su commesse/pricing — non DDT.

### File creati
- `services/ddt_service.py` — funzioni libere (clone `ordini_service`): CRUD testata/righe,
  emissione (→EMESSO, numero dal trigger), `cambia_stato` data-driven, componenti BoM,
  `crea_ddt_da_ordine` (evasione, delega a `fn_genera_ddt_da_ordine`), `push_a_commessa`
  (sorgente `DDT_VENDITA`), `_db_errors`.
- `api/views_ddt.py` + `api/urls_ddt.py` (montato in `urls_v1.py`).
- `tests/services/test_ddt_service.py` (24) + `tests/api/test_ddt_api.py` (10, +1 dopo review = 35).

### File modificati
- `db/ddt_repository.py` — esteso da minimale a completo (letture `vw_ddt_lista`, scritture,
  `push_da_ordine`, capabilities, componenti, **filtro scope emittente attivo**, `count_righe`).
- `api/views_ordini.py` + `urls_ordini.py` — `ApiOrdineGeneraDdt` (`POST /ordini/<id>/genera-ddt/`).
- `api/note_views.py` — cablaggio note DDT (`make_note_views`).
- `core/services/error_policies.py` — famiglia `E_DDT_*` + `E_STATO_DDT_*`, `E_QTA_SUPERA_RESIDUO`,
  `E_COMPONENTE_PREZZO_PENDENTE`, `E_DOC_COMPONENTI_PENDING_VALORIZZAZIONE`.

### Addendum scope §15 recepito (colonna emittente memorizzata)
`list_ddt` filtra su `emittente_fiscale_id` (mirror ordini); `_resolve_emittente_sr_id`
legge la colonna memorizzata; `crea_ddt` richiede `billing_account_id`; FK
`fk_ddt_v_emittente_fiscale` in `_FK_CONSTRAINTS`.

### Fix da code-review high (10 finding, applicati)
Vedi anche il diff. Sintesi: **residuo evasione** (repo `list_righe` espone
`qta_evasa/residua_operativa`; il pannello FE usa il residuo), **`esposto_in_fattura`**
rimosso dalla allowed-set (ddt+ordini, era no-op silenzioso), **policy errore emissione**
registrate, **letture pesanti** ridotte (guard leggeri `get_stato_codice`, `count_righe`,
no re-read numero), **codice morto** rimosso (`list_ddt` wrapper, param inerte),
convenzioni (`# Scopo:`, `assert` post-`require`). REFUTED: `int()`→500 (framework
mappa 400) e `@extend_schema` mancanti (parità ordini).

### Fuori scope (predisposto, slice successive)
Editing `ddt_indirizzi`, riepilogo IVA, export lista, colonna "Emittente" in
lista (aggiunta seed `ui.lista_colonna` DB-side). Slice **resi** documentata nel brief DB §12.
PDF DDT — ✅ **realizzato** (§13). Lineage (Fase 4) — aperto (tracker §6).

## 13. Consuntivo slice 2026-07-11 (valuta + emittente + STAMPA PDF + orfano + refactor) — ✅ REALIZZATO

Estensione BE su `dev/backend-tid` (**non committato**). 1304 test BE verdi; verificato LIVE
(gunicorn, token operatore). Dettaglio in [[handoff_20260711_ddt_stampa_orfano_refactor]].

### Valuta default sul drawer DDT

`fn_get_ddt_form_defaults` (service, variante DDT del BB form-defaults condiviso) +
`ApiDdtFormDefaults` (view) + route `GET /vendite/ddt/form-defaults/`. La valuta era vuota
in create (vs ordini/preventivi); ora prefillata dai default del BA/operatore.

### STAMPA DDT (PDF) — 5° dominio del motore `documenti`, operativa E2E

- `services/ddt_document_context_builder.py` (CODE=`DDT_VENDITA`, shape
  ddt/destinatario/trasporto/righe; registrato in `apps/vendite/apps.py`).
- `POST /vendite/ddt/<id>/emetti/` reso **multipart e ATOMICO**: transizione DRAFT→EMESSO +
  genera PDF + allegati in una transazione; se il render fallisce → rollback, numero non
  consumato. `emetti()` ritorna LIGHT (parità `ordini_service.conferma`).
- View di dominio generate via la **factory** (vedi refactor sotto). Template DDT →
  DB template 76 / versione 46 PUBBLICATA.

### Fix ORFANO push ordine (bug trovato da Tid)

Ordine `fatturazione_trigger=CONFERMATO` evaso in DDT restava non-pushabile né come ordine né
come DDT. Fix DB #962; recepito BE: `_STATI_PUSHABILI` esteso a
`{CONFERMATO, PARZIALMENTE_EVASO, EVASO}` in `ordini_service` (+2 test). **Lezione**: il guard
applicativo duplicava `fn_list_ordini_da_pushare` → fonte unica = fn DB
([[handoff_20260711_ddt_stampa_orfano_refactor]], nota metodo).

### 2 refactor BB (regola del 2, da code-review high)

- **Factory `build_documenti_sorgente_views`** (`apps/documenti/api/sorgente_documenti_views.py`):
  genera le 7 view per dominio; i 5 domini (ordini/preventivi/offerte/contratti/ddt) ora ~80
  righe di delta ciascuno. Bonus: aggiunte route `file/<file_id>/` mancanti a preventivi+contratti.
- **Scope emittente** (`apps/core/db/emittente_scope_helpers.py`,
  `add_emittente_scope_condition`): risolve l'array scope UNA volta in Python (era 2×/query in 5 repo).

### PDF data-driven via capabilities (`pdf_mode`/`pdf_allow_allegati`) — recepimento BE = ZERO

Le 5 `fn_available_actions_*` ora espongono il blocco `pdf {mode, allow_allegati}`: il blob
capabilities è spread `**capabilities` nei service → arriva al FE **senza modifiche BE**. Per la
lista Ordini, `vw_ordini_lista.pdf_mode` viaggia via `SELECT v.*` + response `DictField()`.
Dettaglio DB+FE: [piano-db-pdf-mode-capabilities-5-domini](../work-done/piano-db-pdf-mode-capabilities-5-domini.md).

## 14. Backlog residuo — ✅ CHIUSO (2026-07-13)

Aree pianificate in §6, dichiarate "fuori scope" nel consuntivo §12 e realizzate nelle slice
11-13/07. Storicizzato qui per tracciabilità (verifica originaria del codice 2026-07-11).

- **Endpoint export lista — ✅ REALIZZATO (2026-07-11)**: `ApiDdtExportView` +
  rotta `/vendite/ddt/export/` (`?formato=csv|xlsx`) + `ddt_service.resolve_filtri_export_label`.
  Riuso `build_export_response`/`EXPORT_MAX_ROWS` + `_LISTA_CODICE_DDT='vendite.ddt'` (config lista
  già seedata), mirror `ApiOrdiniExportView` ([[feedback_export_lista_rispetta_preferenza]]).
  +2 test api (formato invalido 400, overflow cap 422). Recepito FE (brief FE §13).
- **Endpoint riepilogo IVA — ✅ REALIZZATO (slice riepilogo IVA, 11-13/07)**:
  `ApiDdtRiepilogoIva` + rotta `/vendite/ddt/<id>/riepilogo-iva/`; il service legge la vista DB
  `vw_ddt_riepilogo_iva_dettaglio` (una riga per aliquota, formula fiscale in DB, righe prezzo
  NULL escluse) senza ricalcolo Python. Consumato dal `RiepilogoIvaTable` FE (brief FE §13).
- **CRUD `ddt_indirizzi` — ✅ REALIZZATO (slice indirizzi documento UX v2, 12-13/07)**:
  endpoint `ApiDdtIndirizzi` + `ApiDdtIndirizzoDetail` (`/vendite/ddt/<id>/indirizzi/[<id>/]`)
  via factory indirizzi documento condivisa (`_shared/indirizzi`, 5 domini). Il FE monta la
  `DocumentoIndirizziSection` (BB condiviso) nel `DdtDrawer` — NON il `DdtIndirizziPanel`
  originariamente ipotizzato in §4 (superato dal BB cross-dominio). Snapshot slot CON +
  auto-assegnazione default; PDF DDT con blocco consegna (builder v2 + template 76/v2).

### Consuntivo emittente (uniformazione 2026-07-13)

Il create DDT ora accetta `emittente_fiscale_id` nel payload (whitelist `_CREATE_KEYS_DDT`,
prefill FE dal profilo operatore, mirror ordini): l'emittente è legato allo USER, non "risolto a
sorpresa" dal BA. Reti di sicurezza DB invariate (default-da-GUC soft + fallback-da-BA in
`trgfn_ddt_normalize`, guard coerenza `trg_ddt_z10_guard_emittente_ba`). I detail DDT/ordini NON
calcolano più `emittente_fiscale_descrizione` con JOIN proprio: arriva dalla vista (`SELECT v.*`),
ora che le 5 viste lista la espongono (ragione sociale del soggetto, non il codice tecnico). I 5
codici `E_*_EMITTENTE_BA_INCOERENTE` registrati in `error_policies.py`. Dettaglio:
[work-done/brief-db-ddt-emittente-user-e-etichetta-soggetto.md](../work-done/brief-db-ddt-emittente-user-e-etichetta-soggetto.md)
(CHIUSO).

> Fuori scope residuo: **slice RESI** (brief `work-in-progress/brief-db-resi-vendita.md`, in corso
> lato DB). Colonna "Emittente" in lista: ✅ seedata (opt-in) e ora bind alla ragione sociale.
</content>
