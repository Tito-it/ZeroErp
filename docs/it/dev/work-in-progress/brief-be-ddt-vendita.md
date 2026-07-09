# Brief BE — DDT vendita: service, repository, endpoint (gemello ordini)

> **Tipo**: brief backend (target `dev/backend-tid`) · **Data**: 2026-07-09 · **Owner**: Tid
> **Design-of-record**: [analisi-ddt-vendita-stato-e-sviluppi.md](analisi-ddt-vendita-stato-e-sviluppi.md)
> · **Prerequisito DB**: [brief-db-ddt-vendita-evasione-e-stati.md](brief-db-ddt-vendita-evasione-e-stati.md)
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

## 2. Prerequisiti DB (verificare "applicati" prima di partire)

| Oggetto DB | Stato | Fonte |
|---|---|---|
| `vendite.fn_genera_ddt_da_ordine(...)` | da creare | brief DB §4 |
| `config.transizioni_stati_ddt` + guard `trgfn_ddt_guard_transizione` | da creare | brief DB §5 |
| `config.stati_doc_ordini.PARZIALMENTE_EVASO` + matrice | da creare | brief DB §4 |
| `ddt_righe.sconto_percentuale` + `iva_id` (C8) | da creare | brief DB §3 |
| Rimozione UNIQUE `uq_ddt_v_sorgente_fk` (multi-DDT) | da creare | brief DB §3 |
| **`vendite.vw_ddt_lista`** (view canonica lista, gemella `vw_ordini_lista`) | ⚠️ **DA AGGIUNGERE al brief DB** | vedi §9 |
| **`script.fn_available_actions_ddt(ddt_id)`** (capabilities data-driven) | ⚠️ **DA AGGIUNGERE al brief DB** | vedi §9 |
| `vendite.note_ddt` (partizione + view) | presente | catalogo BB |
| `fn_list_ddt_da_pushare`, `fn_ddt_riga_componenti_init/preview` | presenti | doc DB |

> ⚠️ **Gap da segnalare al team DB**: il brief DB Fase 1 copre evasione+stati ma
> **non** la read-side per il BE lista/dettaglio. Servono `vw_ddt_lista` e
> `script.fn_available_actions_ddt` (mirror esatti di `vw_ordini_lista` /
> `script.fn_available_actions_ordine`). Aggiungerli al brief DB o a un companion.

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
- **fn DB**: `push_da_ordine(ordine_id, righe)` → `SELECT vendite.fn_genera_ddt_da_ordine(%s,%s::jsonb,%s,%s)`;
  `init_componenti_riga`/`preview_componenti_riga` (fn `fn_ddt_riga_componenti_*`);
  `count_righe_pushable(ddt_id)` → `fn_list_ddt_da_pushare(NULL,NULL,NULL,%s)`.

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

## 9. Riepilogo dipendenze DB da confermare col team DB

Oltre agli oggetti del brief DB Fase 1, il BE ha bisogno di **`vw_ddt_lista`** (read
lista/dettaglio) e **`script.fn_available_actions_ddt`** (capabilities data-driven).
Sono mirror 1:1 di `vw_ordini_lista` e `script.fn_available_actions_ordine` sulla
matrice `config.transizioni_stati_ddt`. **Vanno aggiunti al capitolato DB** (li segnalo
in cima a §2): senza, la lista e le azioni di stato non funzionano.

## 10. Test (mirror ordini)

- `tests/services/test_ddt_service.py` (`SimpleTestCase` + mock repo, `_patch_atomic_noop`):
  guard stato, override componenti, `_db_errors`, **evasione da ordine** (residuo,
  copia snapshot, over-shipping → `E_QTA_SUPERA_RESIDUO`), push commessa, standalone.
- `tests/api/test_ddt_api.py` (`JwtMockedApiTest`): list/create/emetti/cambia-stato/push/
  patch/export + `ApiOrdineGeneraDdt`.
- Smoke E2E (`backend/scripts/tests/`): ordine CONFERMATO (trigger SPEDITO) → genera-ddt →
  emetti → SPEDITO → push commessa → attività fatturabile (giro completo differito).

## 11. Punti aperti (decisione)

- **`post_permission`**: ordini non li dichiara (solo `area_funzionale`), preventivi sì
  (`cambia_stato_preventivi`, `push_commessa_preventivi`). **Scelta**: DDT segue ordini
  (nessun `post_permission`) o introduce `emetti_ddt`/`push_commessa_ddt`? *(consiglio:
  come ordini, salvo esigenza di granularità permessi.)*
- **Indirizzi DDT** (`ddt_indirizzi`): non hanno gemello negli ordini (testata ordine
  senza indirizzi). Per la slice **da-ordine** gli indirizzi possono essere snapshot
  ereditati (mittente=emittente, destinatario=cliente): CRUD indirizzi dedicato →
  rimandabile alla slice **standalone/PDF**. Confermare.
- **`types.py`**: dict grezzo (come ordini) o TypedDict `DdtRow`/`DdtRigaRow`?
</content>
