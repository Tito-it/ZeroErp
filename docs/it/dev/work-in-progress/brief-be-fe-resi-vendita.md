# Brief BE+FE — Slice RESI vendita (motore resi su DDT)

> **Tipo**: brief backend + frontend (target `dev/backend-tid`) · **Data**: 2026-07-13 · **Owner**: Tid
> **Stato**: 🟡 BE ✅ (2026-07-13, committato `5176eb608` + review 8-finder con 9 fix e 3 BB
> estratti, non committati) · FE ✅ (2026-07-14, non committato) — resta SOLO lo step 9:
> smoke E2E + validazione in-app (tracker §17; consuntivi §18 BE / §19 FE)
> **Design-of-record**: [brief-db-resi-vendita.md](brief-db-resi-vendita.md) (decisioni §0/§9, handoff BE §11)
> · **Prerequisito DB**: slice DB **applicata e committata** (`54ff31598`, merge PR #976) — gate BE aperto.
> **Principio guida**: **clonare il dominio DDT** (`ddt_service`/`DdtRepository`/`views_ddt` +
> `frontend/src/vendite/ddt/`), che è a sua volta il clone moderno di ordini; stessa impronta,
> logica reso diversa e **ridotta** (niente prezzi, niente componenti BoM, niente PDF, niente
> push commessa, niente note, niente indirizzi). Riuso massimo BB
> ([[feedback_regola_del_2_estrai_bb]], [[feedback_vue_reuse]]).

---

## 1. Scopo

Portare i resi da "motore DB completo" a dominio BE+FE operativo:

- **CRUD reso da DDT** (testata + righe, editabili solo in DRAFT);
- **conferma** (`fn_conferma_reso`: riapre residuo ordine, proietta stato ordine, flip
  DDT→RESO se totale) e **annullo** (`fn_annulla_reso`: storno);
- **ri-spedizione** (`fn_genera_ddt_riconsegna`: nuovo DDT DRAFT + ponte, parziale/multipla);
- **lista resi** + **due code di lavoro** (`da accreditare` / `da ri-consegnare`);
- azioni **data-driven** da `script.fn_available_actions_reso`.

Il reso è un documento **senza valori economici** in questa slice (il branch nota di
credito è slice successiva): righe = articolo/qta/tipo_reso/motivo.

## 2. Prerequisiti DB — ✅ APPLICATI (verificato 2026-07-13 su doc auto-gen)

| Oggetto DB | Firma/nota reale |
|---|---|
| `vendite.resi` | testata: `sorgente_tipo_id`+`sorgente_uid` NOT NULL (solo `DDT_VENDITA`, DDT in **CONSEGNATO**), `emittente_fiscale_id` NOT NULL, `destinatario/BA/utility/valuta` **ereditati dal DDT** via `trgfn_resi_normalize` (payload create = minimo), `numero` NULL in DRAFT |
| `vendite.resi_righe` | `ddt_riga_id` NOT NULL, `ordine_riga_id` nullable, `articolo_id`/`descrizione` NOT NULL (**snapshot dalla riga DDT: lo fa il BE**, nessun trigger di copia), `tipo_reso_id` NOT NULL per riga, `qta_operativa`+`uom_operativa_id` (trigger `qta_from_operativa` calcola `quantita` base), guard `a20` anti over-return con lock |
| `vendite.resi_righe_riconsegne` | ponte reso↔DDT ri-spedizione; popolato SOLO da `fn_genera_ddt_riconsegna` (il BE non ci scrive mai) |
| `vendite.fn_conferma_reso(p_reso_id bigint) → void` | atomica: guard DRAFT+righe, transizione a CONFERMATO (numero dal trigger), riapertura residuo, proiezione stato ordine, flip DDT se reso totale |
| `vendite.fn_annulla_reso(p_reso_id bigint) → void` | da DRAFT o CONFERMATO; blocca se già ri-spedito (`E_RESO_ANNULLO_CON_RICONSEGNE`) |
| `vendite.fn_genera_ddt_riconsegna(p_reso_id bigint, p_righe jsonb DEFAULT NULL, p_data date DEFAULT CURRENT_DATE) → bigint` | ritorna il nuovo `ddt_id` (DRAFT); `p_righe=[{resi_riga_id, qta}]` (**unità base**) per il parziale, `NULL` = tutta la copertura residua; fulfillment auto se order-backed |
| `script.fn_available_actions_reso(p_reso_id) → jsonb` | mirror ridotto DDT: `available_actions` (conferma/annulla da matrice), `can_change_state`, `can_edit_testata`/`can_edit_righe` (solo DRAFT), `non_editable_fields`, `stato_codice`. **NIENTE** push/pdf |
| `vendite.vw_resi_lista` | `security_invoker=on`; colonne mirror `vw_ddt_lista` + `sorgente_codice_interno`, `ddt_origine_id/numero`, `emittente_fiscale_id/codice/descrizione` (filtro applicativo BE) |
| `vendite.vw_resi_da_accreditare` | riga reso CONFERMATO con `tipi_reso.riapre_residuo=false`: reso/DDT/articolo/qta/BA/emittente |
| `vendite.vw_resi_da_riconsegnare` | riga reso CONFERMATO `riapre_residuo=true` con copertura incompleta: `qta_resa`, `qta_riconsegnata`, `qta_residua`, **`stato_riconsegna`** derivato (`DA_RICONSEGNARE/PARZIALE/COMPLETATA`); si auto-svuota |
| RLS `rls_resi_ef_whitelist` + guard `z10` emittente-BA | parità DDT/ordini: liste già filtrate, dettaglio fuori scope → 404 |
| Matrice DDT aggiornata | `CONSEGNATO→RESO` `manuale:false` (il pulsante «Reso» **sparisce da solo** dalle capabilities DDT), `SPEDITO→RESO` disattivata, nuova `RESO→CONSEGNATO` automatica per l'annullo |
| `config.messaggi_errore` 530-541 | famiglia `E_RESO_*` + `E_STATO_RESO_TRANSIZIONE_NON_VALIDA` (§6) |
| Seed `tipi_reso` / `stati_doc_reso` / `transizioni_stati_reso` + `sistema_codici 'reso'` | `RESO_A_CREDITO` (riapre_residuo=f) / `RESO_PER_RICONSEGNA` (t); stati `DRAFT/CONFERMATO/ANNULLATO` |

### Residui DB — ✅ TUTTI CHIUSI (2026-07-13 sera, commit `53a679900` PR #978)

1. **Seed lista UI `vendite.resi`** — ✅ applicato come da
   [brief companion](../work-done/brief-db-seed-lista-ui-resi.md): `lista_definizione`
   id 9 + colonne 149-160 (inclusa `azioni`). Verificato live: lista 9 con 12 colonne.
2. **pgTAP** (riga T) — ✅ `db/pgtap/vendite/test-resi-motore-v1.sql` +
   `db/pgtap/rls/test-rls-resi-ef-whitelist-write.sql`.
3. **Guard sorgente CONSEGNATO** (scostamento §18) — ✅ chiuso:
   `trgfn_resi_guard_ddt_consegnato` (a10 INSERT, `E_RESO_DDT_NON_CONSEGNATO` 542,
   registrato in error_policies). In più: `fn_genera_ddt_riconsegna` v2 ri-proietta
   lo stato ordine dopo la ri-spedizione.

## 3. BE — Struttura file (clonare da DDT)

Tutto sotto `backend/apps/vendite/`:

| Nuovo file | Clona da | Differenze |
|---|---|---|
| `services/resi_service.py` | `services/ddt_service.py` (funzioni libere) | §4 — niente componenti/push/pdf/emetti; +conferma/annulla/riconsegna |
| `db/resi_repository.py` | `db/ddt_repository.py` | §5 — **senza** `ComponentiRepositoryMixin` |
| `api/views_resi.py` + `api/urls_resi.py` | `api/views_ddt.py` + `urls_ddt.py` | §6; montare in `urls_v1.py`: `path("resi/", include("apps.vendite.api.urls_resi"))` |
| famiglia `E_RESO_*` in `core/services/error_policies.py` | blocco `E_DDT_*` | §7 |
| `tests/services/test_resi_service.py` + `tests/api/test_resi_api.py` | omonimi ddt | §9 |

Convenzioni: dict grezzo (no TypedDict), `# Scopo:` su ogni def, `_db_errors(op)` copiato
dal pattern ordini/ddt (traduzione P0001 → codice `E_*` via regex).

## 4. `resi_service.py` — funzioni

Costanti: `_STATO_BOZZA="DRAFT"`, `_STATI_MODIFICABILI={"DRAFT"}`; whitelist campi
testata `{data, meta}` (tutto il resto è ereditato/immutabile: vedi `non_editable_fields`
della fn capabilities) e riga `{ddt_riga_id, tipo_reso_id, qta_operativa, uom_operativa_id, motivo}`.

**Letture**: `list_resi(...)` (envelope paginato su `vw_resi_lista`), `get_reso(reso_id)`
(**merge capabilities** `repo.get_capabilities` + `righe_count`), `list_righe(reso_id)`,
`list_da_accreditare(...)` / `list_da_riconsegnare(...)` (code, §6).

**CRUD testata**:
- `crea_reso(payload)` — payload minimo `{ddt_id | sorgente_uid, data?, righe?}`:
  il repo risolve `ddt.uid` da `ddt_id` (o accetta direttamente l'uid) e INSERT con
  `sorgente_tipo_id` = id di `config.sorgenti.DDT_VENDITA` risolto **per codice**
  ([[feedback_no_hardcoded_ids]]); BA/destinatario/utility/valuta/emittente li mette
  `trgfn_resi_normalize`. Guard parlante se il DDT non è CONSEGNATO (il normalize
  fail-fasta, tradurre in `E_RESO_VALIDAZIONE`). **Se `righe` presenti nel payload**
  (creazione dal pannello DDT, §12-FE): `with transaction.atomic()` intorno a
  testata + N righe (compone 2+ scritture — guardrail atomicità api.md).
- `aggiorna_reso(reso_id, payload)` — solo DRAFT (`can_edit_testata`), campi `{data, meta}`.
- `elimina_reso(reso_id)` — hard-delete solo bozza (0 righe attive), mirror DDT orfano.

**Righe** (solo con testata DRAFT — enforcement **BE** via `get_stato_codice`, il DB non
ha trigger di editabilità — item 14c del brief DB):
- `gestisci_riga(reso_id, payload)` / `aggiorna_riga` / `elimina_riga`.
- **Snapshot dalla riga DDT (a carico del BE)**: alla create il repo legge
  `ddt_righe` (id, `articolo_id`, `descrizione`, `uom_operativa_id`, `factor_to_base`,
  `ordine_riga_id` dal fulfillment della riga se presente) e copia; il chiamante passa solo
  `ddt_riga_id`, `tipo_reso_id`, `qta_operativa` (default = residuo reso della riga), `motivo`.
  Guard DB `a20` = rete di sicurezza anti over-return (532); il BE non duplica la formula,
  espone solo il **residuo per riga** in lettura (§5) per la UX.
  `ordine_riga_id`: derivarlo da `ordini_righe_fulfillment` per `ddt_riga_id`
  (una riga DDT da evasione ha esattamente un fulfillment; NULL per standalone).

**Azioni di dominio** (una `SELECT fn_madre` = atomica, **niente** `transaction.atomic()`):
- `conferma_reso(reso_id)` → `repo.conferma(reso_id)` (`fn_conferma_reso`); ritorna il
  detail LIGHT aggiornato (numero assegnato).
- `annulla_reso(reso_id)` → `repo.annulla(reso_id)` (`fn_annulla_reso`).
- `genera_ddt_riconsegna(reso_id, righe=None, data=None)` → `repo.genera_ddt_riconsegna(...)`
  → ritorna `{ddt_id, reso_id}`. `righe=[{resi_riga_id, qta}]` in **unità base**
  (attenzione: diversa dall'evasione ordine→DDT che viaggia in operativa — la fn DB
  ponte lavora su `quantita` base; documentarlo nel client FE).
- **NIENTE `cambia_stato` generico**: la matrice reso ha solo conferma/annullo e
  **entrambe le transizioni hanno effetti** → passare SEMPRE dalle fn madri, mai
  `UPDATE stato` diretto (un update nudo salterebbe storno/proiezioni). Il dispatch
  FE per `action.key` chiama i due endpoint dedicati.

## 5. `resi_repository.py`

Mirror `DdtRepository` **senza** mixin componenti:

- **Letture**: `list_resi(...)` su `vw_resi_lista` (WHERE dinamico stato/BA/data/search
  ILIKE + **scope emittente** via BB `add_emittente_scope_condition`
  (`apps/core/db/emittente_scope_helpers.py`), COUNT separato, ORDER BY whitelisted
  `+ v.id ASC`, LIMIT ≤200); `get_reso(reso_id)` (view + JOIN `vendite.resi` per `meta`);
  `get_capabilities(reso_id)` = `call_jsonb_fn("script.fn_available_actions_reso", reso_id)`;
  `get_stato_codice`; `list_righe(reso_id)` (JOIN decode tipo_reso/uom + **residuo
  ri-consegna** per riga via LEFT JOIN aggregato sul ponte).
- **Righe DDT per il pannello reso** (lettura di servizio): `list_righe_ddt_per_reso(ddt_id)` —
  righe del DDT + `qta_gia_resa` (Σ `resi_righe.quantita` su resi non ANNULLATI) +
  `qta_resa_residua` (consegnata − già resa). Alimenta la UX del pannello FE (§12) senza
  duplicare la guard (che resta DB).
- **Scritture**: `create_reso`, `update_reso`, `delete_reso`, `next_riga_nr`/`create_riga`/
  `update_riga`/`delete_riga` (INSERT/UPDATE espliciti; snapshot riga DDT come da §4).
- **fn DB**: `conferma(reso_id)`, `annulla(reso_id)`,
  `genera_ddt_riconsegna(reso_id, righe, data=None)` →
  `SELECT vendite.fn_genera_ddt_riconsegna(%s, %s::jsonb, COALESCE(%s, CURRENT_DATE))`.
- **Code**: `list_da_accreditare(...)` / `list_da_riconsegnare(...)` sulle due viste
  (stesso scope emittente + filtri BA/data + paginazione).
- `_FK_CONSTRAINTS` per `map_integrity_error`: `fk_resi_*` / `fk_resi_righe_*` (§2).

## 6. Endpoint (`area_funzionale="vendite"`, pattern DDT, no `post_permission`)

| Metodo | Path | Azione |
|---|---|---|
| GET/POST | `/api/v1/vendite/resi/` | lista + crea (da DDT, payload §4) |
| GET | `/api/v1/vendite/resi/da-accreditare/` | coda accrediti (`vw_resi_da_accreditare`) |
| GET | `/api/v1/vendite/resi/da-riconsegnare/` | coda ri-consegne (`vw_resi_da_riconsegnare`) |
| GET/PATCH/DELETE | `/api/v1/vendite/resi/<id>/` | dettaglio (+capabilities) / patch / delete bozza |
| POST | `/api/v1/vendite/resi/<id>/conferma/` | `fn_conferma_reso` |
| POST | `/api/v1/vendite/resi/<id>/annulla/` | `fn_annulla_reso` |
| POST | `/api/v1/vendite/resi/<id>/genera-ddt-riconsegna/` | `fn_genera_ddt_riconsegna`; body `{righe?: [{resi_riga_id, qta}], data?}` |
| GET/POST | `/api/v1/vendite/resi/<id>/righe/` · GET/PATCH/DELETE `.../righe/<rid>/` | CRUD righe (solo DRAFT) |

**Dominio DDT (sorgente)** — lettura di servizio per il pannello FE:

| GET | `/api/v1/vendite/ddt/<ddt_id>/righe-per-reso/` | `ApiDdtRighePerReso` → `resi_service` (righe DDT + già reso + residuo). Import locale per evitare cicli (pattern `genera-ddt`) |

`Idempotency-Key` sui POST di azione (conferma/annulla/riconsegna) come da linee guida.
Rotta export lista: **rimandata** (mirror DDT, si aggiunge quando c'è la config lista).

## 7. `error_policies.py` — famiglia `E_RESO_*`

Registrare (tutti sollevati dal DB via `_db_errors`, tranne i primi due applicativi):

| Codice | HTTP | ui_action |
|---|---|---|
| `E_RESO_NOT_FOUND` (535) | 404 | show_empty_state |
| `E_RESO_VALIDAZIONE` (applicativo) | 400 | highlight_form_fields |
| `E_STATO_RESO_TRANSIZIONE_NON_VALIDA` (531) | 409 | show_error_banner |
| `E_RESO_QTA_SUPERA_CONSEGNATO` (532) | 409 | show_error_banner |
| `E_RESO_RICONSEGNA_TIPO_NON_VALIDO` (533) | 409 | show_error_banner |
| `E_RESO_RICONSEGNA_SUPERA_RESO` (534) | 409 | show_error_banner |
| `E_RESO_STATO_NON_CONFERMABILE` (536) | 409 | show_error_banner |
| `E_RESO_SENZA_RIGHE` (537) | 409 | show_error_banner |
| `E_RESO_NESSUNA_RICONSEGNA_PENDENTE` (538) | 409 | show_error_banner |
| `E_RESO_STATO_NON_ANNULLABILE` (539) | 409 | show_error_banner |
| `E_RESO_ANNULLO_CON_RICONSEGNE` (540) | 409 | show_error_banner |
| `E_RESO_NON_CONFERMATO` (541) | 409 | show_error_banner |
| `E_RESO_EMITTENTE_BA_INCOERENTE` (530) | 400 | show_error_banner |

## 8. Lookup — whitelist da estendere

- **BE**: aggiungere `config.tipi_reso` e `config.stati_doc_reso` alla whitelist del
  lookup generico (`apps/core/db/dbops_repository.py`, blocco dove sta
  `config.stati_doc_ddt` — [[feedback_lookup_whitelist_first]], NO endpoint dedicato).
- **FE**: registrare le due tabelle in `core/config-tables.js` (mirror riga
  `config.stati_doc_ddt:33`) così `LookupSelect rel="..."` funziona subito.

## 9. Test BE (mirror ddt)

- `tests/services/test_resi_service.py` (`SimpleTestCase` + mock repo): create da DDT
  (snapshot riga, sorgente per codice, atomic con righe), guard DRAFT su patch/righe,
  conferma/annulla/riconsegna (delega fn + niente atomic), `_db_errors` (codici §7),
  code, validazioni payload.
- `tests/api/test_resi_api.py` (`JwtMockedApiTest`): list/create/detail/patch/delete +
  conferma/annulla/genera-ddt-riconsegna + righe + code + `righe-per-reso` sul DDT.
- Smoke E2E bash (`backend/scripts/tests/`, [[feedback_smoke_test_idempotenti]]):
  ordine→DDT→CONSEGNATO → reso misto (1 riga credito + 1 ri-consegna) → conferma
  (residuo riaperto, ordine PARZIALMENTE_EVASO, coda accrediti popolata) → ri-spedizione
  parziale → 2ª ri-spedizione (COMPLETATA, coda vuota, fulfillment richiuso) → reso
  totale su altro DDT → flip RESO → annullo → RESO→CONSEGNATO.

## 10. FE — Struttura file (clonare `vendite/ddt/` → `vendite/resi/`)

| Nuovo file `frontend/src/vendite/resi/` | Clona da (ddt) | Differenze |
|---|---|---|
| `views/ResiView.vue` | `views/DdtView.vue` | host lista+drawer, `useReadonlyMode(VENDITE, RESI)` |
| `stores/resi.js` | `stores/ddt.js` | `defineStore('vendite-resi', …, {userScoped:true})`; azioni `conferma`, `annulla`, `generaDdtRiconsegna`; `data_da` anno-1 |
| `api/resiApi.js` | `api/ddtApi.js` | `BASE='/vendite/resi'`; niente componenti/documenti; +`getRigheDdtPerReso(ddtId)` |
| `constants.js` | `constants.js` | `STATO_RESO` (DRAFT/CONFERMATO/ANNULLATO), `STATO_RICONSEGNA` (DA_RICONSEGNARE/PARZIALE/COMPLETATA), `TIPO_RESO` (codici interni per il default di riga) |
| `components/ResiSearchTable.vue` | `DdtSearchTable.vue` | §11 |
| `components/ResoDrawer.vue` | `DdtDrawer.vue` | §12 — niente PDF/note/indirizzi/riepilogo-IVA |
| `components/ResoForm.vue` | `DdtForm.vue` | testata minima: data, DDT origine (link), destinatario/BA/emittente display-only |
| `components/ResoRigheTable.vue` + `ResoRigaForm.vue` | `DdtRigheTable/DdtRigaForm` | wrapper `RigheMasterDetailTable`; riga = articolo (readonly da riga DDT), qta operativa, `tipo_reso` (LookupSelect), motivo |
| `components/ResoRiconsegnaPanel.vue` (**nuovo**) | `OrdineEvasionePanel.vue` (ordini) | §13 |
| `components/ResoDaDdtPanel.vue` (**nuovo**, in `vendite/ddt/components/`) | `OrdineEvasionePanel.vue` | §12 — vive nel drawer DDT |

## 11. Lista — `ResiSearchTable.vue`

`<ListaConfigurabile codice="vendite.resi">` (**dipende dal seed UI**, §2-residuo-1) +
`useListaConfigurabilePage` ([[feedback_lista_pattern_standard]]). Toolbar: search +
`LookupSelect rel="config.stati_doc_reso" value-field="codice_interno"` +
`UtilityPerRuoloSelect` cliente + 2× DatePicker + `PageActionsBar` (**senza** "new":
il reso nasce SOLO dal DDT, §12 — niente standalone in questa slice). Slot:
`#cell-stato` (Tag + `statoResoSeverity`), `#cell-numero` ("—" in DRAFT),
`#cell-ddt_origine_numero` (link/chip DDT). Row actions: kebab `RowActionsMenu`
([[feedback_row_actions_menu]]). `useTabFreshness(store, TAB_ENTITIES.RESI)`.

Le **code** (`da-accreditare` / `da-riconsegnare`): in questa slice come **tab/filtri
della vista Resi** (2 tab PrimeVue sopra la lista, fetch dalle rotte dedicate §6, colonne
fisse senza ListaConfigurabile) — sono liste di righe, non di documenti. Rimandabile la
promozione a dashboard.

## 12. Creazione reso — pannello nel drawer DDT (sorgente)

Gemello di `OrdineEvasionePanel` (stesso pattern smistamento):

- `ResoDaDdtPanel.vue` montato nel `DdtDrawer` quando `stato_codice === 'CONSEGNATO'`
  (l'azione manuale «Reso» è sparita dalla matrice: il pannello È il percorso).
- `DataTable` da `getRigheDdtPerReso(ddtId)`: articolo, consegnata, **già resa**,
  **residuo**; selezione multipla; per riga selezionata: input `qta` (default=residuo,
  `:max`=residuo), `LookupSelect` tipo reso (default `RESO_A_CREDITO`), motivo.
- Bottone "Crea reso" → `confirmAction({onAccept})` ([[feedback_useconfirmaction_destructuring]])
  → `POST /vendite/resi/` `{ddt_id, righe:[{ddt_riga_id, tipo_reso_id, qta_operativa, motivo}]}` →
  toast + `emitDataChanged(TAB_ENTITIES.RESI, resoId)`; **nessun router-push** (il reso
  nasce DRAFT, si rifinisce/conferma dal suo tab — parità smistamento/evasione).
- Nel `DdtDrawer` ripulire il dispatch `onAction`: il case `reso` è ramo morto (la
  transizione non è più manuale).

## 13. Drawer — `ResoDrawer.vue`

Mirror ridotto `DdtDrawer`:

- `DrawerEntityHeader`: Tag numero ("—" in DRAFT), data, **chip provenienza DDT**
  (`ddt_origine_numero`, apertura drawer DDT autonomo [[feedback_drawer_autonomi]]),
  `#status` Tag + `statoResoSeverity`.
- `DrawerActionsBar` data-driven: `useEntityCapabilities(detail, {editFlag:'can_edit_testata'})`
  + `mapAvailableActionsToDrawerActions`. Dispatch per `action.key`: `conferma` →
  confirm + `store.conferma(id)` (endpoint dedicato, NON cambia-stato); `annulla` →
  confirm + `store.annulla(id)`.
- `ResoForm` su `contentReady` ([[feedback_content_ready_after_show]]); testata quasi
  tutta display-only (`non_editable_fields` dal BE); prop `readonly` obbligatoria
  ([[feedback_drawer_readonly]]).
- `ResoRigheTable` master-detail ([[feedback_master_detail_inline]]): editabile solo se
  `can_edit_righe`; colonne articolo/qta/tipo reso/motivo + (post-conferma, per righe
  ri-consegna) `stato_riconsegna` + `qta_residua` dal `list_righe` BE.
- **`ResoRiconsegnaPanel`** (solo stato CONFERMATO, se esiste copertura residua):
  clone `OrdineEvasionePanel` sulle righe `riapre_residuo=true` — qta resa /
  ri-consegnata / residua, selezione + input qta (**unità base**, `:max`=residua),
  bottone "Genera DDT ri-consegna" → confirm →
  `store.generaDdtRiconsegna(id, righe)` → toast con link/`emitDataChanged(TAB_ENTITIES.DDT, ddtId)`.
- Niente: PDF, note, indirizzi, riepilogo IVA, componenti, push (§15).
- Drawer save: `if (result !== null)` ([[feedback_drawer_result_check]]).

## 14. Aggiunte core FE

| File | Aggiunta |
|---|---|
| `core/navigation.js` | voce `{key:'resi', to:'/vendite/resi'}` in `DOMAIN_MENUS.vendite` (dopo `ddt`) + `NAV_ICONS.RESI` + CSS `app-nav-icon-resi` se mancante |
| `router/index.js` | rotta `vendite/resi` → `ResiView.vue`, `meta:{domain:'vendite', menuKey:'resi'}` |
| `core/constants.js` | `TAB_ENTITIES.RESI`, `READONLY_MODELS.RESI` |
| `core/utils/severity.js` | `statoResoSeverity` (DRAFT=warn, CONFERMATO=success, ANNULLATO=danger) + `statoRiconsegnaSeverity` |
| `core/config-tables.js` | `config.stati_doc_reso` + `config.tipi_reso` (§8) |
| `locales/it.json` + `en.json` | blocco `vendite.resi.*` (titolo, filtri, field_*, riga_*, conferma_*, annullo_*, riconsegna_*, code, col_* quando c'è il seed) + `nav_menu.vendite.resi`; `@` escapato se serve ([[feedback_vue_i18n_linked_escape]]) |

## 15. Fuori perimetro (esplicito)

- Nota di credito (consumo coda accrediti) — slice NC.
- Reso standalone (senza DDT) e sorgente FATTURA — il vocabolario è predisposto.
- PDF reso, note reso (nessuna partizione `note_reso` in DB), indirizzi reso, export
  lista, push a commessa: non esistono lato DB in questa slice, non predisporre UI morte.
- Movimenti di magazzino.

## 16. Ordine di lavoro (concentrico)

1. **Brief DB companion** per il seed lista UI `vendite.resi` (§2-residuo-1) — parte
   subito, sblocca la lista mentre si sviluppa il resto.
2. BE anello 1: repository + service letture/CRUD + endpoint + error_policies + lookup
   whitelist + test unit.
3. BE anello 2: azioni (conferma/annulla/riconsegna) + `righe-per-reso` + test.
4. FE anello 1: core (nav/router/constants/severity/config-tables/i18n) + `resiApi` +
   store + lista (con code a tab).
5. FE anello 2: `ResoDrawer` + righe + `ResoDaDdtPanel` nel drawer DDT.
6. FE anello 3: `ResoRiconsegnaPanel` + rifiniture data-driven.
7. Smoke E2E + validazione in-app (gunicorn: `kill -HUP` dopo le modifiche
   [[project_backend_gunicorn_reload]]).

## 17. Avanzamento

| # | Step | Stato |
|---|---|---|
| 1 | Brief DB seed lista UI resi | ✅ applicato dal team DB (`53a679900`, [brief in work-done](../work-done/brief-db-seed-lista-ui-resi.md)) |
| 2 | BE letture/CRUD (service+repo+view+policies+lookup) | ✅ 2026-07-13 |
| 3 | BE azioni conferma/annulla/riconsegna + righe-per-reso | ✅ 2026-07-13 |
| 4 | Test BE (service+api) | ✅ 41 test (27 service + 14 api); suite vendite 1137 verdi |
| 5 | FE core + lista + code | ✅ 2026-07-14 |
| 6 | FE ResoDrawer + righe | ✅ 2026-07-14 |
| 7 | FE DdtResoPanel (drawer DDT; nessun case `reso` morto da ripulire: il dispatch DDT era già generico) | ✅ 2026-07-14 |
| 8 | FE ResoRiconsegnaPanel | ✅ 2026-07-14 |
| 9 | Smoke E2E + validazione in-app | ☐ (serve un giro ordine→DDT→CONSEGNATO: nessun DDT CONSEGNATO nei dati dev) |

## 19. Consuntivo FE (2026-07-14) — ✅ REALIZZATO (non committato)

Dominio FE resi completo su `dev/backend-tid`. **Build Vite verde** (warning
chunk-size pre-esistente), **eslint pulito**.

### File creati — `frontend/src/vendite/resi/`

`views/ResiView.vue` (3 tab: lista + coda accrediti + coda ri-consegne, host
`ResoDrawer`), `stores/resi.js` (userScoped, `data_da` anno-1,
`useListaEmptyStateFetch`; azioni `conferma`/`annulla`/`generaRiconsegna` con
notifica cross-tab DDT/ordini), `api/resiApi.js`, `constants.js`
(`STATO_RESO`/`STATO_RICONSEGNA`/`TIPO_RESO`), `components/`:
`ResiSearchTable` (ListaConfigurabile `vendite.resi`, senza New/Export),
`ResiCodaTable` (2 varianti sulle viste-coda BE), `ResoDrawer` (edit-only,
azioni data-driven → endpoint dedicati), `ResoForm` (testata quasi tutta
display: ereditata dal DDT), `ResoRigheTable`+`ResoRigaForm` (master-detail su
BB; create con Select righe DDT rendibili + residuo hint), `ResoRiconsegnaPanel`
(clone evasione: selezione + qta BASE, "tutto" → righe null race-proof).

### File creati/modificati — dominio DDT

`components/DdtResoPanel.vue` (nuovo, clone `OrdineEvasionePanel`: consegnata/
già-resa/residuo per riga + qta OPERATIVA + tipo reso + motivo → `POST
/vendite/resi/` con righe in transazione); `DdtDrawer.vue` (montaggio pannello
su stato CONSEGNATO — il pannello È il percorso, l'azione manuale «Reso» non
arriva più dalla matrice).

### Core modificati

`navigation.js` (voce `resi`, `NAV_ICONS.RESI`), `router/index.js` (rotta
`vendite/resi`), `core/constants.js` (`TAB_ENTITIES.RESO`,
`READONLY_MODELS.RESO`), `core/utils/severity.js` (`statoResoSeverity` +
`statoRiconsegnaSeverity`), `core/config-tables.js` (`config.stati_doc_reso`
+ `config.tipi_reso`), `locales/it.json`+`en.json` (blocco `vendite.resi.*`
~85 chiavi + `vendite.reso.azione_*` — namespace delle label della matrice
DB — + `nav_menu.vendite.resi`).

### BB riusati (nessuna duplicazione)

`ListaConfigurabile`, `useListaConfigurabilePage` (azioni new/export filtrate),
`useStoreFilterBindings`, `useListaEmptyStateFetch`, `RigheMasterDetailTable`,
`useEntityCapabilities`, `mapAvailableActionsToDrawerActions`,
`DrawerActionsBar`/`DrawerEntityHeader`/`DrawerTitle`/`FormFooter`,
`useDrawerContentReady`/`useDrawerClose`/`useDrawerDetailLoad`,
`EmittenteFiscaleField`, `LookupSelect`, `useGlobalLookup` (tipi reso),
`useTabFreshness`, `useConfirmAction` (destructured, `onAccept`).

### Review critica FE (2026-07-14) — 9 fix applicati

Bug BLOCCANTI (2): `DdtResoPanel` e `ResoRiconsegnaPanel` erano montati dentro
`.app-readonly` (lock-di-stato CONSEGNATO/CONFERMATO → `pointer-events:none`):
pannelli visibili ma inerti — impossibile creare un reso o ri-spedire dalla UI.
Fix: wrapper `app-escape` (mirror pannello evasione ordini). Altri fix:
dispatch azioni con mappa esplicita (un'azione futura della matrice NON
degrada più su `annulla` silenzioso; chiave ignota → warn), fallback
`tipoDefaultId` (fail-soft su rename seed), `Tabs lazy` (via 2 fetch inutili
al mount), `Promise.all` lookup+righe, empty-state onesto (`loaded`) nella
coda, etichette "(base)" sulle colonne ri-consegna (asimmetria unità
esplicitata), rimossi ref morto + 4 chiavi i18n orfane. Verificato: copertura
i18n completa, colonna `azioni` senza slot gestita dal BB. Build+lint verdi.
**Estrazioni regola-del-2 COMPLETATE (2026-07-14, ok Tid)**: BB
`useRigheSelezioneQta` (vendite/_shared/righe) adottato dai 3 pannelli
selezione-righe-quantità (OrdineEvasionePanel riscritto incluso); BB
`buildDocListParams`/`hasDocListActiveFilters` (vendite/_shared/listaDocumenti)
adottato dagli store ordini/ddt/resi; `ResiCodaTable` migrata su
`usePagedDashFetch` (guard anti-race + `loaded` dal BB, adapter
page→limit/offset — nessuna estensione del BB necessaria; metodi coda rimossi
dallo store). Catalogo BB FE aggiornato. Build+lint verdi.

## 18. Consuntivo BE (2026-07-13) — ✅ REALIZZATO (non committato)

Slice BE completa (committata in `5176eb608`, PR #979) + **review critica
8-finder con 9 fix applicati** (2026-07-13 sera, non committati): validazione
`righe` ri-consegna (body degenere ≠ "ri-spedisci tutto"), `qta_operativa`
obbligatoria (il trigger DB calcola sempre la base dall'operativa),
guard fulfillment multipli (modello 1:1 difeso con errore parlante), parse
ISO di `data`, codice guard CONSEGNATO allineato al trigger, stato
conferma/annullo riletto dal DB (non hardcoded), N+1 riga_nr eliminato,
lettura leggera in gestisci_riga, dedup interni (`_update_by_id`,
`PayloadValidator`). **3 BB estratti** (ok Tid, catalogo aggiornato):
`translate_db_errors`/`make_db_errors_translator` (core payload_helpers —
unifica i 5 `_db_errors` di resi/ddt/ordini/offerte/indirizzi);
`execute_dynamic_update` (core sql_write_helpers — unifica 8+ builder UPDATE
di ddt/ordini/preventivi/resi/componenti/email, e assorbe il vecchio
`dynamic_update` di _helpers come delegatore `skip_none=True`);
`extract_doc_list_filters` (vendite/api/_list_filters_helpers — unifica gli
`_extract_list_filters` di ordini/ddt/resi). `manage.py check` pulito;
**suite backend COMPLETA 3083 test verdi**. Letture validate LIVE sul DB.

### File creati
- `db/resi_repository.py` — letture `vw_resi_lista`/code, scritture
  testata/righe, fn madri (`conferma`/`annulla`/`genera_ddt_riconsegna`),
  lookup sorgente/stati, `get_ddt_riga_snapshot` (fulfillment → `ordine_riga_id`),
  `list_righe_ddt_per_reso` (già-reso/residuo per il pannello FE).
- `services/resi_service.py` — CRUD + azioni; guard applicativo **DDT
  sorgente CONSEGNATO** al create (vedi scostamento sotto); snapshot riga dal
  DDT nel BE; `transaction.atomic` su create testata+righe; `_db_errors`.
- `api/views_resi.py` + `api/urls_resi.py` (montato in `urls_v1.py`).
- `tests/services/test_resi_service.py` (27) + `tests/api/test_resi_api.py` (14).

### File modificati
- `api/views_ddt.py` + `urls_ddt.py` — `ApiDdtRighePerReso`
  (`GET /vendite/ddt/<id>/righe-per-reso/`, import locale di resi_service).
- `core/services/error_policies.py` — famiglia `E_RESO_*` (14 policy,
  codici DB 530-541 + `E_RESO_VALIDAZIONE`/`E_RESO_STATO_TRANSIZIONE` applicativi).
- `core/db/dbops_repository.py` — whitelist lookup `config.stati_doc_reso` +
  `config.tipi_reso`.

### Scostamento dal brief DB — ✅ CHIUSO (2026-07-13 sera)

Segnalato: mancava il guard DB "sorgente solo DDT in CONSEGNATO" (brief DB §3).
Chiuso dal team DB con `trgfn_resi_guard_ddt_consegnato` (a10 INSERT,
`E_RESO_DDT_NON_CONSEGNATO` 542) — commit `53a679900`. Recepito BE: policy 409
registrata, commenti service/repo/test allineati (il guard applicativo di
`crea_reso` resta come 4xx parlante pre-INSERT; il trigger è la fonte di
verità). Verificato live: trigger attivo su `vendite.resi`.
