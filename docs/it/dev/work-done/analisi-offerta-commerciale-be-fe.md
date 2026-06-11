# Piano BE + FE — Dominio Offerta Commerciale

> **Stato**: ✅ CHIUSO (rev. 2026-05-26g) — dominio offerta commerciale
> completo BE + FE, tutti gli step §8 atterrati. 42/42 test BE verdi,
> 1351/1351 complessivi, build vite verde, eslint pulito. Follow-up residui
> (non bloccanti): smoke UI manuale §5.3, cross-link pratiche
> `OFFERTA_QUADRO` (§7), guida operatore, seed permessi `OFFERTA_GESTISCI`
> (§2.3).
>
> **Revisione 2026-05-24a**: allineato alle correzioni del brief DB
> (B1/B2/B3/I1/I2/I3/I4) e alla conferma di modello sulla utility.
>
> **Revisione 2026-05-24b**: chiusi 5 gap emersi dalla verifica BE contro il
> `ContrattoDrawer` reale e il brief DB accettato. In sintesi: la utility
> **non è solo l'id** ma porta i campi business di `contratti_utilities`
> (tipo/classe utenza + parametri), quindi rientra una sezione utility editabile
> (GAP 1); tolti tab "giornale stati" e "allegati" per simmetria col contratto
> (GAP 2/3); aggiunta `motivazione_rifiuto` (GAP 4); annullamento via cambio
> stato con nuovo stato `ANNULLATA` distinto da `RIFIUTATA` (GAP 5).
>
> **Revisione 2026-05-26g** (questa): chiuso il cantiere FE end-to-end.
> Lato FE: nuova cartella dedicata `frontend/src/vendite/offerte/`
> (pattern preventivi), drawer 3 tab (testata+utility inline / eccezioni /
> revisioni), sub-drawer eccezioni master-detail inline, sub-drawer note
> partizionate, 3 dialog di processo (Emissione / Esito multi-modalita' /
> Push contratto), dialog parlante "Contratto gia' generato" con link al
> contratto esistente, deep-link `/vendite/contratti?open=<id>` post-push.
> Lato DB: applicata `script.fn_available_actions_offerta` (migration
> `20260526-01`) + seed `stati_doc_offerte_transizioni.csv` con
> `requires_motivazione`. Lato BE: cablato il capability blob nel detail
> via `repo.get_available_actions` + merge in `get_offerta`; atomicita'
> utility 1:1 inline su `crea_offerta` + `aggiorna_offerta` (sub-oggetto
> `utility` opzionale, transaction unica); SELECT con alias
> `billing_account_display` / `utility_display` + LEFT JOIN
> `vendite.contratti.offerta_id` per `contratto_id`/`contratto_numero`;
> cablate note partizionate `target_tipo='OFFERTA'`. FE refactor:
> `OffertaDrawer` data-driven con `useEntityCapabilities` +
> `mapAvailableActionsToDrawerActions` (dispatch unico
> `onActionDispatch(action.key)`), rimossi tutti i computed
> `isBozza/isEmessa/isAccettata` hardcoded. **42/42 test BE verdi, build
> vite verde, eslint pulito**. Dominio offerta commerciale: **completo
> BE + FE**. Vedi §0.8.
>
> **Revisione 2026-05-25f**: cablato lato BE quanto consegnato dal
> commit DB `906720ac5` del 2026-05-25 PM (step 8-9: push a contratto +
> suite pgTAP completa). Il dominio offerta commerciale lato BE e'
> **funzionalmente completo**. `POST /<id>/push-contratto/` end-to-end con
> pattern A idempotenza, helper `get_contratto_minimal` per coupling-zero
> col `ContrattiService`, costante `_STATI_PUSHABILI`. 38/38 test verdi.
> Resta solo il cantiere FE. Vedi §0.7.
>
> **Revisione 2026-05-25e**: cablato lato BE quanto consegnato dal
> commit DB `13d57a846` del 2026-05-25 (step 5-7 brief DB). In sintesi:
> codice `OFC-*` automatico via trigger DB (rimosso dalla whitelist payload),
> `POST /<id>/crea-revisione/` end-to-end (chiama `fn_crea_revisione_offerta`)
> e `GET /<id>/revisioni/` (catena via CTE ricorsiva). 32/32 test verdi.
> **Solo step 8 (push a contratto) resta fuori scope**. Vedi §0.6.
>
> **Revisione 2026-05-24d**: riallineamento al DB realmente consegnato
> dal team DB il 2026-05-24 (commit `2000d8261`). Step 1-4 del brief + addendum
> §0.3 atterrati. Tre divergenze minori recepite (D1 `data_annullamento`, D2
> note in tabella separata, D3 `articolo_id` UUID). Perimetro BE iniziale
> ristretto al solo cablabile: niente `crea_revisione` né `push_a_contratto`
> finché il team DB non chiude step 5-8 (D4). Vedi §0.5.
>
> **Revisione 2026-05-24c**: rifiniture di coerenza dopo verifica
> incrociata col `ContrattoDrawer` reale e risposte utente. (1) La utility non
> ha un tab/panel separato: i campi business sono **inline nella testata**
> esattamente come nel `ContrattoDrawer` (tab del drawer offerta passano da
> 4 a **3**); (2) state machine asimmetrica simmetrica al contratto:
> **BOZZA → ANNULLATA** (annullamento da noi), **EMESSA → RIFIUTATA** (no
> cliente). Nessun annullamento da EMESSA, nessun rifiuto da BOZZA;
> (3) endpoint utility mirror del contratto (POST + PATCH per id);
> (4) altre rifiniture di coerenza interna (count stati, count tab, test,
> smoke UI, dipendenza addendum DB). Vedi §0.4 changelog.
> **Alcune correzioni toccano anche il brief DB** (già accettato): vedi
> nota DB in §0.3.
>
> **Sorgente di verità**:
>
> - Modello: [analisi-offerta-commerciale.md](analisi-offerta-commerciale.md)
>   (decisioni §5 chiuse 2026-05-23)
> - Brief DB: [analisi-offerta-commerciale-db.md](analisi-offerta-commerciale-db.md)
>   (ex `brief-db-offerta-commerciale.md`; revisione 2026-05-24, correzioni
>   B1/B2/B3/I1/I2/I3/I4 — chiuso, step 1-9 applicati)
>
> **Prerequisito di applicabilità**: il piano BE può partire solo dopo che il
> team DB ha chiuso almeno gli step 1-3 del brief DB (sorgenti, tabelle, ALTER
> su contratti). Il piano FE può iniziare in parallelo al BE se ci si attiene
> a contratti API stabili (vedi §6 sequenza).
>
> **Cosa NON è questo documento**:
>
> - non è un brief DB (quello è separato)
> - non riformula il modello (lo applica)
> - non descrive il flusso pratiche `OFFERTA_QUADRO` (quello è nel documento
>   pratiche §11.2: si aggancia a questo dominio una volta esistente)

---

## 0. Changelog correzioni

### 0.1 Revisione 2026-05-24a (allineamento al brief DB)

Il piano era stato scritto contro la stesura precedente del brief DB (offerta
multi-utility e FK errate). Queste correzioni lo riallineano al brief corretto.

| Rif. | Punto del piano corretto     | Cosa cambia                                                             |
| ---- | ---------------------------- | ----------------------------------------------------------------------- |
| B2   | `OffertaRow` (BE-1)          | `istanza_utility_id` / `utility_id` NOT NULL derivati dal BA            |
| B3   | `EccezioneOffertaRow` (BE-1) | `tipo_eccezione: str` (enum `vendite.tipo_eccezione_contratto`, non FK) |
| I2   | `OffertaRow` (BE-1)          | `tipo_variazione_globale: str` (VARCHAR+CHECK, non FK)                  |

### 0.2 Revisione 2026-05-24b (chiusura 5 gap verifica BE)

| Gap   | Punto corretto                                                     | Cosa cambia                                                                                                                                                                                                                                                                                                                                                                             |
| ----- | ------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GAP 1 | Utility: TypedDict, repository, drawer (testata + sezione utility) | La utility porta **tutti** i campi business di `contratti_utilities` (`tipo_utenza_id`, `classe_utenza_id`, `param_1_num`, `param_2_txt`, `istanza_dati_precontrattuali_id`), editabili come nel `ContrattoDrawer`. `istanza_utility_id`/`utility_id` restano derivati dal BA. **Rientra la sezione utility** (la semplificazione "solo testata sola lettura" della rev. a era errata). |
| GAP 2 | FE-3 drawer                                                        | **Rimosso tab "Giornale stati"** (non esiste tabella log né nel contratto né nel preventivo). Resta simmetrico al contratto.                                                                                                                                                                                                                                                            |
| GAP 3 | FE-3 / FE-4                                                        | **Rimosso `AllegatiPanel`** (non esiste oggi; il contratto non lo ha). Allegati rinviati a brief separato.                                                                                                                                                                                                                                                                              |
| GAP 4 | OffertaEsitoDialog + testata                                       | Aggiunta colonna `motivazione_rifiuto` sulla testata (non JSONB). Tocca il brief DB (vedi nota).                                                                                                                                                                                                                                                                                        |
| GAP 5 | Lifecycle + endpoint                                               | Annullamento via **cambio stato** (no hard delete come via di processo), con nuovo stato **`ANNULLATA`** (da noi) distinto da `RIFIUTATA` (dal cliente). Logica uniforme col contratto ("annulla contratto").                                                                                                                                                                           |

### 0.8 Revisione 2026-05-26g (cantiere FE chiuso + capability layer data-driven)

Chiusura end-to-end del dominio offerta commerciale dopo la consegna DB della
fn `script.fn_available_actions_offerta` (migration `20260526-01`).

| Punto | Cosa cambia |
| ----- | --- |
| G1 | **Nuova cartella `frontend/src/vendite/offerte/`** (stessa logica preventivi): `api/`, `stores/`, `views/`, `components/`, `components/dialogs/`, `constants.js`. Niente flat in `vendite/components/`. |
| G2 | **Drawer 3 tab** (`OffertaDrawer.vue`): Testata con sezione utility inline (mirror `ContrattoDrawer.vue:777-785`), Eccezioni (sintesi + bottone manage), Revisioni (CTE ricorsiva). |
| G3 | **Sub-drawer eccezioni** master-detail inline (`OffertaEccezioniDrawer.vue`): pattern `formMode` null/create/edit + readonly cumulativo via `useInjectReadonly`. |
| G4 | **Sub-drawer note partizionate** (`OffertaNoteDrawer.vue`) thin wrapper su `NoteDrawer` core + `makeNotesApi('/vendite/offerte/<id>')`. |
| G5 | **3 dialog di processo**: `OffertaEmissioneDialog`, `OffertaEsitoDialog` multi-modalita' (ACCETTATA / RIFIUTATA / ANNULLATA con motivazione obbligatoria per le ultime due), `OffertaPushDialog` con `pratica_id` opzionale. |
| G6 | **Dialog parlante `E_OFFERTA_CONTRATTO_GIA_GENERATO`**: doppio trigger (proattivo via `detail.contratto_id` + reattivo via `extractApiErrorCode` su race condition). Bottone "Apri contratto esistente" → emit `navigate-contratto`. |
| G7 | **Deep-link contratto post-push**: `OfferteView.onNavigateContratto` → `router.push({name:'vendite-contratti', query:{open:id}})`. `ContrattiListView` con watcher su `route.query.open` che apre il drawer + pulisce il query param via `router.replace`. |
| G8 | **DB D7 — `script.fn_available_actions_offerta`** consegnata (migration `20260526-01-create-fn-available-actions-offerta-mctit.yaml`), seed `stati_doc_offerte_transizioni.csv` aggiornato con `requires_motivazione` su transizioni manuali, severity corretti, 9 test pgTAP. |
| G9 | **BE D7 — capability blob in `get_offerta`**: `repo.get_available_actions(offerta_id)` wrapper su `call_jsonb_fn`; `get_offerta` ora include `available_actions[]`, `can_edit_*`, `can_push_contratto*`, `non_editable_fields[]`, `stato_codice`. TypedDict `OffertaRow` aggiornato. |
| G10 | **BE D7 — atomicita' utility 1:1 inline**: `_CREATE_KEYS_OFFERTA` + `_UPDATE_KEYS_OFFERTA` accettano sub-oggetto `utility` opzionale; nuovi helper privati `_add_utility_inline` + `_upsert_utility_inline` (distingue create vs update via lookup esistente, eredita `istanza_utility_id`/`utility_id` dalla testata). Atomicita' garantita dalla stessa `transaction.atomic()`. Niente piu' 2 round-trip ne' `.catch()` silenziosi lato FE. |
| G11 | **BE D7 — display fields backend** alias rinominati: `ba_ragione_sociale -> billing_account_display`, `utility_descrizione -> utility_display` (allineamento al piano FE+BE rev. f). LEFT JOIN `vendite.contratti.offerta_id` per esporre `contratto_id`/`contratto_numero` (consumati dal dialog "gia' generato" e dal deep-link). |
| G12 | **BE D7 — note partizionate `target_tipo='OFFERTA'`**: aggiunto a `TARGET_TIPI_AMMESSI` in `apps/core/db/partitioned_note_repository.py`; factory `_OFFERTA_REPO` + views `ApiOffertaNoteList/Detail` in `apps/vendite/api/note_views.py`; rotte `<id>/note/` e `<id>/note/<note_id>/` in `urls_offerte.py`. |
| G13 | **FE D7 — refactor data-driven** del `OffertaDrawer`: rimossi `isBozza`/`isEmessa`/`isAccettata`/`isOffertaLocked`, sostituiti da `canEditTestata` derivato da `useEntityCapabilities`. `drawerActions` computed ora composito `mapAvailableActionsToDrawerActions(...) + manage-eccezioni + manage-note` (50 righe → 25). Dispatch unico `onActionDispatch(action)` con `switch (action.key)`. |
| G14 | **FE D7 — pulizia code-coverage**: rimosso `STATI_OFFERTA_EDITABILI` (mai usato dopo refactor); rimosse 3 store action morte (`loadUtility`/`addUtility`/`aggiornaUtility`) — utility ora atomica via `payload.utility` inline su `create`/`update`. |
| G15 | **Test BE 38 → 42**: 2 test atomicita' utility CREATE (`con_utility_inline_atomico` + `senza_utility_inline_non_chiama_repo`), 2 test atomicita' utility UPDATE (upsert in ramo update e in ramo create per offerta senza utility), test `get_offerta_ok_arricchisce_eccezioni_e_utility` esteso col blob capability. |
| G16 | **Build vite verde**, eslint pulito sui file `vendite/offerte/`, 1351 → **1351** test BE complessivi (vendite + core). |

### 0.7 Revisione 2026-05-25f (sblocco step DB 8-9: BE completo)

Il team DB ha consegnato il 2026-05-25 PM (commit `906720ac5`) gli ultimi
step del brief: `fn_push_offerta_a_contratto`, ALTER `contratti.offerta_id`
e suite pgTAP completa. Cablato lato BE in giornata.

| Punto | Cosa cambia                                                                                                                                                                                                                  |
| ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| F1    | **`POST /<id>/push-contratto/`** (step 8): nuovo endpoint che invoca `vendite.fn_push_offerta_a_contratto(p_offerta_id, p_pratica_id)`. Body opzionale `{pratica_id: int?}` per collegare il contratto generato a una pratica. Guard applicativo `ACCETTATA`; il DB ha guard finale + pattern A idempotenza (UNIQUE `uq_contratti_offerta_id`). Ritorna `{contratto_id, contratto_codice, sorgente_uid}` (il FE naviga al `ContrattoDrawer`). |
| F2    | **`get_contratto_minimal` helper nel repository**: lettura `{id, numero, uid, stato_codice}` da `vendite.contratti` post-push. Evita coupling cross-service col `ContrattiService` (`ContrattiRepository` non importato). Query separata di lookup minimal.                                                                                                                                                                                |
| F3    | **Costante `_STATI_PUSHABILI = frozenset({ACCETTATA})`** module-level. Coerente col pattern `_STATI_EDITABILI` e `_STATI_DA_EMESSA`: nessuna allocazione inline per chiamata.                                                                                                                                                                                                                                                                |
| F4    | **Codice errore `E_CONFIG_MANCANTE` mappato**: la fn DB lo solleva se `OFFERTA_COMMERCIALE` / `CONTRATTO` non sono in `config.sorgenti` o stato `DRAFT` non in `config.stati_doc_contratti`. Propagato come `code` originale via regex `_DB_ERROR_CODE_RE`.                                                                                                                                                                                  |
| F5    | **Test suite 32 → 38**: 6 test push (da EMESSA/BOZZA fallisce, happy path con costruzione `OffertaPushResult`, idempotenza pattern A, pratica_id passato al repo, pratica_id non-positivo rifiutato).                                                                                                                                                                                                                                       |
| F6    | **Refactor `_STATI_DA_EMESSA`** ereditato rev. e: 3 siti deduplicati (registra_accettazione, registra_rifiuto, crea_revisione).                                                                                                                                                                                                                                                                                                                |
| F7    | **Suite pgTAP DB completa** (step 9): test per fn_crea_revisione + fn_push + codice + struttura testata/eccezioni/utility + revisione trigger + state machine + end-to-end. Non duplichiamo lato BE (mock unit test).                                                                                                                                                                                                                       |

### 0.6 Revisione 2026-05-25e (sblocco step DB 5-7)

Il team DB ha consegnato il 2026-05-25 (commit `13d57a846`) tre step
brief in un colpo: numerazione `OFC-*`, trigger revisione, fn revisione.
Cablato lato BE in giornata, senza anticipare lo step 8 (push).

| Punto | Cosa cambia                                                                                                                                                                                                              |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| E1    | **Codice `OFC-*` automatico** (step 5): `codice` rimosso da `_CREATE_KEYS_OFFERTA` (whitelist payload service) e da `_OFFERTA_CREATE_COLS` (whitelist write repo). Il trigger DB `trgfn_offerte_commerciali_gen_codice` (BEFORE INSERT) genera il codice se NULL. Se passato in payload: rifiutato come `unknown_key`. |
| E2    | **`POST /<id>/crea-revisione/`** (step 6-7): nuovo endpoint che invoca `vendite.fn_crea_revisione_offerta(p_offerta_id, p_user)`. Guard applicativo `EMESSA`; il DB ha guard finale (`E_OFFERTA_REVISIONE_STATO_NON_AMMESSO` propagato come `code` originale). User di audit preso da `request.user.username`. Ritorna il dettaglio della nuova rev.N+1.                                                                                |
| E3    | **`GET /<id>/revisioni/`**: lista catena di revisioni che condividono il root con l'offerta passata. CTE ricorsiva ancestors → root → descendants. Lettura libera in ogni stato.                                          |
| E4    | **Firma fn revisione**: il brief diceva `(p_offerta_id, p_motivazione TEXT)` ma il team DB ha implementato `(p_offerta_id, p_user TEXT)` per coerenza con `fn_crea_revisione_preventivo`. La motivazione di processo non esiste nel flusso revisione (`motivazione_rifiuto` e' riservata a RIFIUTATA/ANNULLATA). Il service passa `request.user.username` o NULL (la fn DB ha `COALESCE(..., CURRENT_USER)`).                          |
| E5    | **Refuso messaggio errore corretto dal team DB** (bonus): `E_OFFERTA_TRANSIZIONE_NON_AMMESSA` ora documenta correttamente `BOZZA→EMESSA / BOZZA→ANNULLATA`, non piu' `BOZZA→RIFIUTATA`.                                                                                                                                                |
| E6    | **Test suite 26 → 32**: aggiunti 6 test (crea_revisione da BOZZA/ACCETTATA fallisce + happy path + propagazione errore DB; list_revisioni 404 + happy path) e adattati i 2 test crea_offerta al payload senza `codice`.    |

### 0.5 Revisione 2026-05-24d (riallineamento al DB consegnato)

Il team DB ha consegnato gli step 1-4 del brief + l'addendum §0.3 in un unico
commit. Tre divergenze minori emerse dalle docs `dbzero/vendite/tabelle/*`
appena pubblicate, recepite qui:

| Punto | Cosa cambia                                                                                                                                                                                                                                                                                                                              |
| ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1    | **`OffertaRow` — aggiunta `data_annullamento: datetime \| None`**: il team DB l'ha aggiunta per simmetria con `data_emissione`/`data_accettazione`/`data_rifiuto` (bonus utile, non richiesto in addendum). Valorizzata dal trigger di transizione quando si entra in ANNULLATA.                                                          |
| D2    | **`OffertaRow` — rimossa `note: str \| None`**: il team DB ha estratto le note in tabella dedicata `vendite.note_offerte_commerciali`, partizione del sistema note generico (target_tipo='OFFERTA'). **Niente repository dedicato**: si cabla il building block esistente `apps.core.db.PartitionedNoteRepository` (gia' attivo per PREVENTIVO e CONTRATTO, vedi `apps/vendite/api/note_views.py`). L'integrazione e' a 3 punti: (1) aggiungere `'OFFERTA'` alla whitelist `TARGET_TIPI_AMMESSI`; (2) instanziare il factory `_OFFERTA_REPO` con `partition_table='vendite.note_offerte_commerciali'`, `parent_table='vendite.offerte_commerciali'`, `child_table='vendite.offerte_commerciali_eccezioni'`; (3) generare le view via `make_note_views(...)`. **Differito a fine sprint BE iniziale** (non bloccante per testata/eccezioni/utility). |
| D3    | **`EccezioneOffertaRow` — `articolo_id: str` (UUID), non `int`**: la PK di `vendite.articoli` è UUID. Conferma: `OffertaRow.billing_account_id` resta `int` (la testata ha `billing_account_id bigint`, non UUID — la stesura precedente diceva erroneamente `str`).                                                                    |
| D4    | **Perimetro BE in attesa step 5-8**: BE-1/2/3/4 implementano **solo** ciò che il DB ha consegnato (testata, eccezioni, utility 1:1, state machine, note). **Non** vengono cablati `crea_revisione` e `push_a_contratto`: si aggiungeranno appena le fn DB esisteranno (step 7-8 brief originale).                                          |

### 0.4 Revisione 2026-05-24c (rifiniture coerenza)

| Punto | Cosa cambia                                                                                                                                                                                                                                                                                                                                                                |
| ----- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| C1    | **Utility inline in testata** (verifica `ContrattoDrawer.vue:777-785` + `:401-405`): i campi business (`tipo_utenza_id`, `classe_utenza_id`, `param_1_num`, `param_2_txt`) sono form fields della testata, **non** un tab a sé. Drawer offerta passa da **4 → 3 tab** (Testata con sezione utility inline, Eccezioni, Revisioni). `UtilityOffertaPanel.vue` **rimosso**.    |
| C2    | **Endpoint utility mirror contratto**: `POST .../utility/` (create record 1:1) + `PATCH .../utility/{utilityId}/` (update), simmetrico ad `apps/vendite/api/contratti.js`. Sostituisce la coppia `GET/PUT .../utility/` proposta in rev. b. In create offerta, la utility entra **inline nel payload** POST `/offerte/` (sub-oggetto `utility: {...}`), come fa il contratto. |
| C3    | **State machine asimmetrica chiusa**: `BOZZA → ANNULLATA` solo (annullamento da noi); `EMESSA → RIFIUTATA` solo (no del cliente). **Nessun annullamento da EMESSA**, **nessun rifiuto da BOZZA**. Logica uniforme col contratto (`DRAFT → ANNULLATO` solo da DRAFT). Punto aperto §0.3 GAP 5 chiuso.                                                                       |
| C4    | **Coerenze numeriche**: count stati passa a **6** in i18n (BOZZA, EMESSA, ACCETTATA, RIFIUTATA, ANNULLATA, SUPERATA); count tab del drawer **3** (era 4); critical path FE-4 nominato correttamente "panel eccezioni" (la utility non è più un panel).                                                                                                                     |
| C5    | **Dipendenze addendum DB**: §8 esplicita che BE-1 dipende **anche** dall'addendum (colonna `motivazione_rifiuto`, stato `ANNULLATA` + transizioni), non solo dagli step 1-3 originali del brief.                                                                                                                                                                          |
| C6    | **Test BE/smoke UI**: aggiunti casi per upsert utility (tipo/classe utenza + parametri), annullamento da BOZZA con motivazione, simmetria push utility completa.                                                                                                                                                                                                           |

> **Principio guida invariato**: l'offerta è **specchio fedele del contratto**.
> Il GAP 1 nasce proprio dall'aver violato questo principio (utility
> semplificata). La correzione lo ripristina: utility ricca come nel contratto.

### 0.3 Nota per il team DB — il brief DB va ritoccato

Le correzioni GAP 4 e GAP 5 (e la verifica GAP 1) **toccano il brief DB già
accettato**. Da girare al team DB come addendum:

1. **GAP 1 — verifica campi utility**: confermare che
   `offerte_commerciali_utilities` (brief §3 step 3, "mirror fedele di
   `contratti_utilities`") includa **esplicitamente** i 5 campi business:
   `tipo_utenza_id`, `classe_utenza_id`, `param_1_num`, `param_2_txt`,
   `istanza_dati_precontrattuali_id`. Se il mirror è davvero fedele ci sono
   già; va solo confermato, non assunto.
2. **GAP 4 — colonna nuova**: aggiungere
   `vendite.offerte_commerciali.motivazione_rifiuto TEXT NULL` (testata).
   Valorizzata alla transizione verso RIFIUTATA/ANNULLATA.
3. **GAP 5 — sesto stato + transizioni (chiusa rev. c)**: aggiungere lo stato
   `ANNULLATA` al seed `config.stati_doc_offerte` (ora **6 stati**: BOZZA,
   EMESSA, ACCETTATA, RIFIUTATA, ANNULLATA, SUPERATA) e le transizioni in
   `config.stati_doc_offerte_transizioni`:
   - `BOZZA → ANNULLATA` (annullamento da noi) — **unica via di uscita "negativa"
     dalla bozza**
   - `BOZZA → RIFIUTATA` **rimossa dal brief originale**: RIFIUTATA è solo "no
     del cliente", e dal cliente non si arriva mai con un'offerta ancora in
     bozza (la deve aver vista). Coerente col contratto (`DRAFT → ANNULLATO`
     solo da DRAFT)
   - `EMESSA → RIFIUTATA` (no del cliente) — **unica via terminale negativa
     post-emissione**
   - `EMESSA → ANNULLATA` **non ammessa**: una volta emessa, o accetta o
     rifiuta il cliente. Se ci si accorge di un errore strutturale, si crea
     una revisione (rev.N+1) che manda la corrente in SUPERATA
   - `EMESSA → SUPERATA` (via trigger revisione, già nel brief)
   - `EMESSA → ACCETTATA` (già nel brief)
   - `ANNULLATA` terminale, nessuna transizione uscente
   - codice errore: nessuno nuovo necessario (riusa
     `E_OFFERTA_TRANSIZIONE_NON_AMMESSA`)

---

## 1. Inquadramento del lavoro applicativo

### 1.1 Obiettivo

Esporre il dominio `vendite.offerte_commerciali` come funzionalità end-to-end
operativa: drawer di editing, lista con filtri, push verso contratto,
revisioni, lifecycle:

- **BOZZA → EMESSA** (emissione al cliente)
- **BOZZA → ANNULLATA** (annullamento da noi, terminale)
- **EMESSA → ACCETTATA** (sì del cliente)
- **EMESSA → RIFIUTATA** (no del cliente, terminale)
- **EMESSA → SUPERATA** (creazione rev.N+1, automatica via trigger DB)

L'utente operatore commerciale deve poter:

1. Creare un'offerta in BOZZA dal menù vendite (punto di ingresso autonomo,
   §5.8 del documento pratiche).
2. Compilare testata (con utility derivata dal BA) + eccezioni proposte.
3. Emettere l'offerta congelando la versione del listino.
4. Registrare l'esito dell'accettazione cliente (ACCETTATA / RIFIUTATA).
5. Su ACCETTATA, lanciare il push verso contratto DRAFT e navigare al
   `ContrattoDrawer` del nuovo contratto.
6. Creare revisioni (rev.N+1 da rev.N EMESSA) — pattern preventivi.

### 1.2 Pattern architetturali da rispettare (no negoziabili)

- **3 layer Django**: API view → service → repository (vedi `AGENTS.md` e
  `PROJECT_CONTEXT.md`).
- **Pricing centralizzato**: mai lookup diretto a `listini_righe` o
  `contratti` dal codice offerta — il pricing passa da `PricingService` o
  funzioni DB equivalenti (memoria `feedback_pricing_centralizzato`).
- **Display fields via JOIN backend**: la lista offerte deve già ritornare
  descrizioni leggibili (cliente, stato, listino, utility, ecc.). Niente
  lookup client-side per dati di riga (memoria
  `feedback_display_fields_backend`).
- **Drawer autonomo + readonly**: il drawer offerta deve supportare prop
  `readonly` con `useInjectReadonly` (memoria `feedback_drawer_readonly`).
- **Store Pinia con `userScoped: true`**: lo store offerte contiene dati
  utente, va flaggato per evitare leak cross-user al logout (memoria
  `feedback_pinia_userscoped`).
- **i18n obbligatorio**: ogni testo visibile usa `$t(...)`, mai stringhe
  hardcoded (AGENTS.md §Frontend).
- **Master-detail inline**: le eccezioni sono pannello detail dentro il drawer
  master (memoria `feedback_master_detail_inline`). La utility è un record 1:1
  i cui campi business (`tipo_utenza_id`, `classe_utenza_id`, `param_*`) stanno
  **inline nella testata** del drawer, esattamente come nel `ContrattoDrawer`
  ([ContrattoDrawer.vue:777-785](../../../../frontend/src/vendite/components/ContrattoDrawer.vue#L777-L785) +
  [:401-405](../../../../frontend/src/vendite/components/ContrattoDrawer.vue#L401-L405)).
  Nessun tab/panel utility separato (vedi §0.4 C1).
- **Dialog dedicato cambio stato**: le transizioni che richiedono dati di
  processo (BOZZA→EMESSA conferma versione listino; EMESSA→ACCETTATA;
  EMESSA→RIFIUTATA con motivazione; BOZZA→ANNULLATA con motivazione) usano
  dialog dedicato — pattern `feedback_dialog_cambio_stato_dati_processo`.
- **Drawer create auto-save bozza**: il drawer in creazione auto-salva come
  BOZZA al primo set di campi minimi (memoria
  `feedback_drawer_create_autosave_bozza`).
- **Niente quick fix**: ogni proposta deve essere la soluzione corretta in
  assoluto (memoria `feedback_no_quick_fix_soluzione_assoluta`).

### 1.3 Quello che NON va fatto in v1

- **Portale cliente-facing**: l'accettazione è dell'operatore, non
  self-service (decisione §5.4 dell'analisi). Niente endpoint pubblici di
  accettazione.
- **Pacchetto commerciale multi-contratto**: il dominio applicativo non
  conosce il pacchetto (predisposizione DB §5.1-bis non esercitata). Niente
  componenti `PacchettoOffertaPanel`, niente API di raggruppamento.
- **Offerta multi-utility**: l'offerta è mono-utility come il contratto
  (§5.1). Niente gestione di più utility per offerta (errore della stesura
  precedente del piano, corretto in §0).
- **Job di scadenza che cambiano stato**: la scadenza è segnalazione UI
  (decisione §5.6). Implementare il calcolo "scaduta = `validita_al < today`"
  come **attributo computato** lato BE nei display fields o lato FE in
  composable, mai come UPDATE su `stato_doc_offerta_id`.
- **Causale recesso/cessazione**: rinviata a brief separato (vedi nota in
  analisi §5.5). Il drawer offerta non ha campi "recesso".

---

## 2. Inventario complessivo BE + FE

### 2.1 Backend Django (`apps/vendite/`)

| Layer      | File nuovo                                                                                           | Pattern                                |
| ---------- | ---------------------------------------------------------------------------------------------------- | -------------------------------------- |
| Types      | `apps/vendite/types.py` (estensione)                                                                 | 5 TypedDict nuovi (vedi §3.1: OffertaRow, UtilityOffertaRow, EccezioneOffertaRow, NotaOffertaRow, OffertaPushResult)          |
| Repository | `apps/vendite/db/offerte_repository.py`                                                              | CRUD + list paginato + lookup          |
| Note (BB)  | `apps/vendite/api/note_views.py` (estensione) + whitelist `TARGET_TIPI_AMMESSI`                      | Cablaggio building block `PartitionedNoteRepository` per `target_tipo='OFFERTA'` (no repo dedicato, vedi §0.5 D2) |
| Service    | `apps/vendite/services/offerte_service.py`                                                           | Facade orchestrazione                  |
| API views  | `apps/vendite/api/views_offerte.py`                                                                  | view (vedi §3.4)                       |
| API routes | `apps/vendite/api/urls.py` (estensione)                                                              | path nuove                             |
| Tests      | `apps/vendite/tests/services/test_offerte_service.py` + `apps/vendite/tests/api/test_offerte_api.py` | mock DB, no DB reale (AGENTS.md §Test) |

> **Nota**: i TypedDict sono 4 — `UtilityOffertaRow` è reintrodotto con i campi
> business (GAP 1). Gli endpoint utility tornano come **sub-resource a record
> singolo** (1:1), non collezione: vedi §3.4.

### 2.2 Frontend Vue (`frontend/src/vendite/`)

| Layer      | File nuovo                                                           | Pattern                                                                                                  |
| ---------- | -------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| API client | `frontend/src/vendite/api/offerte.js`                                | Wrapper axios + token refresh                                                                            |
| Store      | `frontend/src/vendite/stores/useOfferteStore.js`                     | Pinia + `userScoped: true` + filters persistiti                                                          |
| View       | `frontend/src/vendite/views/OfferteView.vue`                         | Layout SearchTable + Drawer + lookup filters                                                             |
| Search     | `frontend/src/vendite/components/OfferteSearchTable.vue`             | ListaConfigurabile + paginazione + filtri data + filtro utility                                          |
| Drawer     | `frontend/src/vendite/components/OffertaDrawer.vue`                  | Drawer **3 tab** (testata con sezione utility inline, eccezioni, revisioni)                              |
| Panels     | `frontend/src/vendite/components/EccezioniOffertaPanel.vue`          | Master-detail inline (lista + form sotto)                                                                |
| Dialog     | `frontend/src/vendite/components/dialogs/OffertaEmissioneDialog.vue` | Cambio stato BOZZA→EMESSA con conferma versione listino                                                  |
| Dialog     | `frontend/src/vendite/components/dialogs/OffertaEsitoDialog.vue`     | Dialog multi-modalità: ACCETTATA / RIFIUTATA (da EMESSA), ANNULLATA (da BOZZA)                           |
| Dialog     | `frontend/src/vendite/components/dialogs/OffertaPushDialog.vue`      | Conferma push verso contratto + navigazione                                                              |
| i18n       | `frontend/src/i18n/it.json` (estensione `vendite.offerte.*`)         | Tutte le label, errori, conferme                                                                         |

> **Tab del drawer (3)**: Testata (form completo: anagrafica offerta + sezione
> utility inline con `tipo_utenza_id`/`classe_utenza_id`/`param_*` editabili,
> `istanza_utility_id`/`utility_id` mostrati in sola lettura), Eccezioni,
> Revisioni. **`UtilityOffertaPanel.vue` rimosso** in rev. c (la utility è
> inline come nel `ContrattoDrawer`, non in un tab a sé). **Tab non
> introdotti**: "giornale stati" (GAP 2, non esiste tabella log; il contratto
> e il preventivo non lo hanno) e "allegati" (GAP 3, `AllegatiPanel` non
> esiste oggi — rinviato a brief separato).

### 2.3 Navigation + permessi

- `frontend/src/core/navigation.js`: aggiungere voce "Offerte commerciali" in
  area Vendite, con icona e route `/vendite/offerte`.
- `config.azioni_processo` (seed DB, **non in questo piano** — chiedere al
  team DB se serve riga seed per `OFFERTA_GESTISCI`): azione di processo per
  granularità permessi sul drawer offerta. Pattern azioni di processo
  esistente (memoria `feedback_lookup_skip_area_check`).

> **Segnalazione coordinamento DB**: il seed `OFFERTA_GESTISCI` in
> `config.azioni_processo` **non è nel brief DB offerta corrente**. Va o
> aggiunto a quel brief o gestito come seed a parte prima di arrivare ai
> permessi del drawer, altrimenti resta un buco.

---

## 3. Step BE — Backend Django

### Step BE-1 — TypedDict in `types.py` ✅ Atterrato (rev. f)

**Scopo**: definire i contratti tipizzati di scambio backend ↔ API.

**Deliverable**:

```python
class OffertaRow(TypedDict):
    id: int
    uid: str
    codice: str
    emittente_fiscale_id: int
    billing_account_id: int          # bigint (D3): contratti/offerte usano bigint, non UUID
    istanza_utility_id: int          # NOT NULL (B2) — derivato dal BA
    utility_id: int                  # NOT NULL (B2) — derivato dal BA
    listino_id: int
    listino_versione_id: int | None
    valore_variazione_globale: Decimal | None
    tipo_variazione_globale: str | None   # VARCHAR+CHECK (I2), NON FK id
    validita_dal: date
    validita_al: date | None
    stato_doc_offerta_id: int
    revisione_numero: int
    revisione_padre_id: int | None
    data_emissione: datetime | None
    data_accettazione: datetime | None
    data_rifiuto: datetime | None
    data_annullamento: datetime | None  # (D1) bonus DB: simmetria con altre data_*
    motivazione_rifiuto: str | None  # (GAP 4) valorizzata a RIFIUTATA/ANNULLATA
    meta: dict
    # Niente campo note sulla testata (D2): le note vivono in
    # vendite.note_offerte_commerciali (mini-dominio satellite, mirror del
    # pattern note_contratto)
    # Display fields da JOIN
    stato_codice_interno: str
    stato_descrizione: str
    billing_account_display: str
    utility_display: str             # (B2) display della utility derivata
    listino_codice: str
    listino_descrizione: str
    listino_versione_codice: str | None
    is_scaduta: bool  # attributo calcolato (validita_al < today)
    # Audit
    data_insert: datetime
    user_insert: str

class UtilityOffertaRow(TypedDict):
    # (GAP 1) Estensione 1:1 — mirror fedele di contratti_utilities.
    # istanza_utility_id/utility_id derivano dal BA; il resto è editabile.
    id: int
    offerta_id: int
    istanza_utility_id: int
    utility_id: int
    tipo_utenza_id: int | None       # editabile (LookupSelect config.tipi_utenze)
    classe_utenza_id: int | None     # editabile (LookupSelect config.classi_utenze)
    param_1_num: Decimal | None      # editabile
    param_2_txt: str | None          # editabile
    istanza_dati_precontrattuali_id: int | None
    # Display fields da JOIN
    tipo_utenza_display: str | None
    classe_utenza_display: str | None

class EccezioneOffertaRow(TypedDict):
    id: int
    offerta_id: int
    articolo_id: str                 # UUID (D3): vendite.articoli.id è UUID, non bigint
    tipo_eccezione: str              # enum vendite.tipo_eccezione_contratto (B3), NON FK id
    # Mirror di vendite.contratti_righe (verifica diretta su
    # dbzero/vendite/tabelle/offerte_commerciali_eccezioni.md):
    tipo_erogazione: str | None
    fonte_quantita_attesa: str       # NOT NULL nel mirror
    periodicita: str | None
    generazione_canone: str | None
    competenza_canone: str | None
    prezzo_unitario: Decimal | None
    quantita: Decimal | None
    qta_operativa: Decimal | None
    uom_operativa_id: int | None
    factor_to_base: Decimal          # NOT NULL default 1
    ordine: int | None               # smallint default 0
    attivo: bool                     # default True
    meta: dict
    # Esclusi (I4): stato_approvazione_prezzo, pratica_approvazione_prezzo_id

class OffertaPushResult(TypedDict):
    # Rev. f (2026-05-25 PM): step 8 atterrato + cablato. Ritornato da
    # `OfferteService.push_a_contratto` via `repo.get_contratto_minimal`.
    contratto_id: int
    contratto_codice: str
    sorgente_uid: str
```

> **Correzioni B2/B3/I2/GAP1/GAP4/D1/D2/D3**:
> `istanza_utility_id`/`utility_id` NOT NULL derivati dal BA +
> `utility_display`; `tipo_variazione_globale` è `str`; `tipo_eccezione` è
> `str` enum; **`UtilityOffertaRow` reintrodotto** con i campi business di
> `contratti_utilities` (GAP 1); aggiunta `motivazione_rifiuto` (GAP 4) e
> `data_annullamento` (D1) sulla testata; `note` rimosso dalla testata (D2,
> tabella dedicata `note_offerte_commerciali`); `articolo_id` su eccezioni è
> `str` UUID (D3).

**Test**: nessun test dedicato (sono TypedDict). Verifica indiretta nei test
service.

### Step BE-2 — Repository `offerte_repository.py` ✅ Atterrato (rev. f)

**Scopo**: accesso DB tramite cursor + funzioni PG (no ORM).

**Deliverable**: classe `OfferteRepository` con metodi:

| Metodo                                                                 | Scopo                                                                                                              |
| ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `list_offerte(filters: dict) -> list[OffertaRow]`                      | Lista paginata con JOIN display fields + filtri (stato, cliente, utility, validita_dal/al, ricerca testo, scaduta) |
| `get_offerta(offerta_id: int) -> OffertaRow`                           | Dettaglio con display fields (incl. `utility_display`)                                                             |
| `create_offerta(data: dict) -> int`                                    | INSERT testata (incl. `istanza_utility_id`/`utility_id` derivati dal BA), ritorna id                               |
| `update_offerta(offerta_id: int, data: dict) -> bool`                  | UPDATE testata (solo in BOZZA, guard lato service)                                                                 |
| `delete_offerta(offerta_id: int) -> bool`                              | DELETE (solo BOZZA, guard lato service)                                                                            |
| `change_state(offerta_id: int, new_state: str, payload: dict) -> bool` | UPDATE stato_doc_offerta_id + valorizza data_emissione/accettazione/rifiuto                                        |
| `list_eccezioni(offerta_id: int) -> list[EccezioneOffertaRow]`         | Lista eccezioni dell'offerta                                                                                       |
| `create_eccezione(offerta_id, data) -> int`                            | INSERT eccezione                                                                                                   |
| `update_eccezione(eccezione_id, data) -> bool`                         | UPDATE                                                                                                             |
| `delete_eccezione(eccezione_id) -> bool`                               | DELETE                                                                                                             |
| `crea_revisione(offerta_id: int, user: str \| None) -> int`            | ✅ `SELECT vendite.fn_crea_revisione_offerta(%s, %s)` (rev. e, step 7)                                              |
| `push_a_contratto(offerta_id: int, pratica_id: int \| None) -> int`    | ✅ `SELECT vendite.fn_push_offerta_a_contratto(%s, %s)` (rev. f, step 8 — pattern A idempotenza)                    |
| `list_revisioni(offerta_id: int) -> list[OffertaRow]`                  | ✅ CTE ricorsiva ancestors→root→descendants (rev. e, step 6-7)                                                      |
| `get_contratto_minimal(contratto_id: int) -> dict`                     | ✅ Lookup minimal post-push (id+numero+uid, no JOIN superflui) (rev. f, step 8)                                     |
| `lookup_utility_da_ba(billing_account_id: str) -> dict`                | Risolve `istanza_utility_id`/`utility_id` dal BA (per popolare la testata in create, come fa il contratto)         |
| `get_utility(offerta_id: int) -> UtilityOffertaRow`                    | Legge il record utility 1:1 dell'offerta (campi business, GAP 1)                                                   |
| `upsert_utility(offerta_id: int, data: dict) -> int`                   | Crea/aggiorna il record utility 1:1 (tipo/classe utenza + parametri). Guard stato BOZZA lato service               |

> **Utility come record singolo (GAP 1)**: la utility è 1:1, quindi non c'è
> CRUD a collezione (`list/add/remove`). C'è `lookup_utility_da_ba` per
> derivare id utility dal BA in creazione, e `get/upsert_utility` per i campi
> business editabili (tipo/classe utenza, parametri), mirror di come il
> `ContrattoDrawer` gestisce `contratti_utilities`.

**Note pattern**:

- `_map_row()` con named columns (`cursor.description`), no indici posizionali
  (memoria `gestione-pratiche-v2.md` §2.3 — pattern già consolidato).
- Guard `if not row` / `assert row is not None` dopo `fetchone()`
  (AGENTS.md §Backend).
- Display fields via JOIN diretto (no lookup tramite altre repository).

**Test**: `test_offerte_repository.py` con `unittest.TestCase` + mock di
`django.db.connection` (AGENTS.md §Test).

### Step BE-3 — Service `offerte_service.py` ✅ Atterrato (rev. f)

**Scopo**: orchestrazione business logic (validazioni applicative + delega
repository).

**Deliverable**: classe `OfferteService` con metodi:

| Metodo                                       | Scopo                                                                                                                                                |
| -------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `list_offerte(filters)`                      | Pass-through al repository                                                                                                                           |
| `get_offerta(offerta_id)`                    | Pass-through + arricchimento `is_scaduta`                                                                                                            |
| `crea_offerta(payload)`                      | Validazione payload (`PayloadValidator`) + risoluzione utility dal BA + INSERT bozza                                                                 |
| `aggiorna_offerta(offerta_id, payload)`      | Guard: solo se stato BOZZA. ServiceError `E_OFFERTA_NON_EDITABILE`                                                                                   |
| `emetti(offerta_id, payload)`                | Guard: stato BOZZA + versione listino impostata. Cambia stato a EMESSA                                                                               |
| `registra_accettazione(offerta_id, payload)` | Guard: stato EMESSA. Cambia stato a ACCETTATA                                                                                                        |
| `registra_rifiuto(offerta_id, payload)`      | Guard: stato EMESSA. Cambia stato a RIFIUTATA (no del cliente) + `motivazione_rifiuto`                                                               |
| `annulla(offerta_id, payload)`               | Guard: **solo stato BOZZA**. Cambia stato a ANNULLATA + `motivazione_rifiuto`. Mirror "annulla contratto DRAFT" (GAP 5, chiarito C3)                 |
| `push_a_contratto(offerta_id, *, pratica_id?)` | ✅ Guard ACCETTATA + pattern A idempotenza (rev. f). Ritorna `OffertaPushResult` letto via `get_contratto_minimal`                                   |
| `crea_revisione(offerta_id, *, user?)`       | ✅ Guard EMESSA. Delega a `fn_crea_revisione_offerta`. Ritorna nuova rev.N+1 (rev. e)                                                                |
| `list_revisioni(offerta_id)`                 | ✅ Catena revisioni via CTE ricorsiva (rev. e). Lettura libera                                                                                       |
| `crud_eccezioni(...)`                        | Wrapper attorno a CRUD eccezioni. Guard: solo se stato BOZZA                                                                                         |
| `add_utility(offerta_id, payload)`           | Crea record utility 1:1 (tipo/classe utenza + parametri). Guard: solo se stato BOZZA. Mirror `add_utility_contratto`                                 |
| `update_utility(offerta_id, utility_id, payload)` | Aggiorna record utility 1:1. Guard: solo se stato BOZZA. Mirror `update_utility_contratto`                                                       |

> **Utility (GAP 1, mirror contratto, C2)**: `add_utility` / `update_utility`
> sono mirror di `add_utility_contratto` / `update_utility_contratto` (vedi
> `apps/vendite/api/contratti.js`). In `crea_offerta`, se il payload contiene
> il sub-oggetto `utility: {...}` (pattern `ContrattoDrawer.vue:401-405`), il
> service smista internamente verso `add_utility` nella stessa transazione.
> Gli id utility si derivano dal BA via `lookup_utility_da_ba`.

**Error handling**:

- Usa `ServiceError` + `ErrorManager.require(...)`.
- Cattura `DatabaseError` con codici PG `P0001` e mappa al codice errore
  semantico (es. `E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO`,
  `E_OFFERTA_CONTRATTO_GIA_GENERATO`) tramite `error_policies.py`.

**Test**: `test_offerte_service.py` con mock repository, casi:

- crea offerta valida → INSERT (con utility inline derivata dal BA + campi
  business `tipo_utenza`/`classe_utenza`/`param_*`)
- crea offerta con BA inesistente → fallisce
- emetti BOZZA senza versione listino → ServiceError mappato
- emetti EMESSA → ServiceError "non in BOZZA"
- push offerta ACCETTATA → contratto creato con utility **completa** copiata
  (id + tipo/classe utenza + parametri, verifica simmetria GAP 1)
- push offerta ACCETTATA doppia volta → seconda chiamata fallisce con
  `E_OFFERTA_CONTRATTO_GIA_GENERATO` (idempotenza testata anche lato BE)
- `update_utility` su offerta BOZZA → record aggiornato
- `update_utility` su offerta EMESSA/ACCETTATA → ServiceError
  `E_OFFERTA_NON_EDITABILE`
- `annulla` da BOZZA con motivazione → stato ANNULLATA + `motivazione_rifiuto`
  salvata
- `annulla` da EMESSA → ServiceError `E_OFFERTA_TRANSIZIONE_NON_AMMESSA` (non
  si annulla dopo l'emissione, C3)
- `registra_rifiuto` da BOZZA → ServiceError (no rifiuto da bozza, C3)

### Step BE-4 — API views + routes ✅ Atterrato (rev. f)

**Scopo**: esporre gli endpoint REST.

**Endpoint da creare**:

| Metodo | Path                                            | Scopo                                    |
| ------ | ----------------------------------------------- | ---------------------------------------- |
| GET    | `/api/v1/vendite/offerte/`                      | Lista paginata + filtri (search ≥3 char) |
| GET    | `/api/v1/vendite/offerte/{id}/`                 | Dettaglio                                |
| POST   | `/api/v1/vendite/offerte/`                      | Crea (BOZZA)                             |
| PATCH  | `/api/v1/vendite/offerte/{id}/`                 | Aggiorna testata (solo BOZZA)            |
| DELETE | `/api/v1/vendite/offerte/{id}/`                 | Cancella (solo BOZZA)                    |
| POST   | `/api/v1/vendite/offerte/{id}/emetti/`          | BOZZA → EMESSA                           |
| POST   | `/api/v1/vendite/offerte/{id}/registra-esito/`  | EMESSA → ACCETTATA / RIFIUTATA           |
| POST   | `/api/v1/vendite/offerte/{id}/annulla/`         | **BOZZA** → ANNULLATA (GAP 5, C3)        |
| POST   | `/api/v1/vendite/offerte/{id}/push-contratto/`  | ✅ ACCETTATA → crea contratto DRAFT (rev. f)            |
| POST   | `/api/v1/vendite/offerte/{id}/crea-revisione/`  | ✅ EMESSA → rev.N+1 BOZZA (rev. e)                      |
| GET    | `/api/v1/vendite/offerte/{id}/revisioni/`       | ✅ Catena revisioni (rev. e)                            |
| POST   | `/api/v1/vendite/offerte/{id}/utility/`         | Crea record utility 1:1 (solo BOZZA, C2) |
| PATCH  | `/api/v1/vendite/offerte/{id}/utility/{uid}/`   | Aggiorna utility 1:1 (solo BOZZA, C2)    |
| GET    | `/api/v1/vendite/offerte/{id}/eccezioni/`       | Lista eccezioni                          |
| POST   | `/api/v1/vendite/offerte/{id}/eccezioni/`       | Crea eccezione                           |
| PATCH  | `/api/v1/vendite/offerte/{id}/eccezioni/{eid}/` | Aggiorna                                 |
| DELETE | `/api/v1/vendite/offerte/{id}/eccezioni/{eid}/` | Cancella                                 |

> **Utility sub-resource — mirror contratto** (C2): `POST .../utility/` e
> `PATCH .../utility/{utilityId}/`, simmetrico agli endpoint contratto
> (`apps/vendite/api/contratti.js:65-71`). Il record è 1:1 logicamente ma
> l'endpoint usa il pattern collezione per coerenza col contratto. In create
> offerta, il payload POST `/offerte/` può includere `utility: {...}` inline
> (mirror `ContrattoDrawer.vue:401-405`) — il service smista internamente.
> Il `DELETE` offerta resta solo per pulizia tecnica di bozze vuote;
> l'annullamento di processo è `POST .../annulla/` → ANNULLATA (GAP 5, solo
> da BOZZA come per i contratti DRAFT, C3).

**Pattern obbligatori**:

- `@extend_schema` su ogni metodo HTTP pubblico (AGENTS.md §Test CI).
- `handle_post_json(...)` per parsing input + error envelope uniforme.
- `is_search_endpoint = True` sul GET lista per attivare throttling
  (AGENTS.md §Backend).
- Policy ricerca e paginazione (helper `apps/core/api/pagination.py`).

**Test**: `test_offerte_api.py` per ogni endpoint, mock di service.

---

## 4. Step FE — Frontend Vue

### Step FE-1 — API client + Store

**Scopo**: layer di accesso dati lato FE.

**`frontend/src/vendite/api/offerte.js`**: funzioni wrapper async che mappano
gli endpoint §3.4: `list`, `get`, `create` (payload può includere `utility`
inline come nel contratto), `update`, `remove`, `emetti`, `registraEsito`,
`annulla`, `pushContratto`, `creaRevisione`, 4 per eccezioni, e 2 per utility
(`addUtilityOfferta`, `updateUtilityOfferta`, mirror di
`addUtilityContratto`/`updateUtilityContratto`). Usa axios centralizzato.

**`frontend/src/vendite/stores/useOfferteStore.js`**: store Pinia con:

- state: `offerte`, `currentOfferta`, `filters` (persistiti localStorage per
  user), `loading`, `error`
- `userScoped: true` (memoria `feedback_pinia_userscoped`)
- actions: `fetchList`, `fetchOne`, `create`, `update`, `remove`,
  `cambiaStato` (wrapper di `emetti`/`registraEsito`/`annulla`), `push`,
  `creaRevisione`, azioni per eccezioni, `addUtility`/`updateUtility`
- `result !== null` check su save (memoria `feedback_drawer_result_check`)

### Step FE-2 — `OfferteSearchTable.vue`

**Scopo**: lista offerte con filtri e azioni.

**Specifiche**:

- Riusa `ListaConfigurabile` esistente (pattern Blocco F)
- Colonne default: codice (`OFC-*`), cliente (BA display), utility (display),
  stato (tag con severity), listino + versione, validità (range), data
  emissione, scaduta (badge giallo se `is_scaduta && stato in BOZZA/EMESSA`)
- Filtri: stato (Select), utility (Select), validita_dal/al (DatePicker),
  cliente (AutoComplete server-side soggetto), ricerca testo (≥3 char, memoria
  `gestione-pratiche-v2.md` §6.4 dashboard)
- Filtro data obbligatorio (memoria `feedback_filtro_data_liste`):
  `validita_dal` default = inizio anno-1
- Azioni: bottone "Nuova offerta" (apre Drawer in create), click su riga apre
  Drawer in edit/read

> **Nota (risposta utente 2026-05-24)**: il filtro per utility nella lista è
> coerente con l'interfaccia contratti (anche lì si filtra per utility nella
> SearchTable). Replica quel pattern.

### Step FE-3 — `OffertaDrawer.vue` (master)

**Scopo**: drawer **3 tab** per gestione end-to-end dell'offerta.

**Tab**:

1. **Testata** — form completo:
   - **Anagrafica offerta**: emittente, **cliente (BA)** → alla selezione del
     BA `istanza_utility_id`/`utility_id` vengono popolati automaticamente e
     mostrati in sola lettura (identico al `ContrattoDrawer`); listino +
     versione listino (Select dipendente, solo versioni ATTIVE); variazione
     globale (% + tipo VARCHAR); validità (range date); note.
   - **Sezione utility inline** (mirror `ContrattoDrawer.vue:777-785`):
     `tipo_utenza_id` (LookupSelect `config.tipi_utenze`), `classe_utenza_id`
     (LookupSelect `config.classi_utenze`), `param_1_num`, `param_2_txt`,
     `istanza_dati_precontrattuali_id`. Tutti editabili in BOZZA.
   - Auto-save al primo set completo (memoria
     `feedback_drawer_create_autosave_bozza`). In create, il payload include
     `utility: {...}` inline come fa il `ContrattoDrawer` (`:401-405`).
2. **Eccezioni** — `EccezioniOffertaPanel.vue` (master-detail inline)
3. **Revisioni** — lista catena revisioni (rev.1 SUPERATA, rev.2 EMESSA,
   ecc.), navigazione tra revisioni. Sola lettura.

> **Tab non introdotti**: "Utility" (C1 — rev. b lo prevedeva separato; in
> rev. c rientra inline nella testata per simmetria col `ContrattoDrawer`),
> "Giornale stati" (GAP 2 — non esiste tabella log), "Allegati" (GAP 3 —
> `AllegatiPanel` non esiste oggi, rinviato a brief separato). Tab finali: 3.

**Prop `readonly`**: drawer supporta `useInjectReadonly` (memoria
`feedback_drawer_readonly`). Drawer auto-readonly se stato ≠ BOZZA per i
campi testata (incl. sezione utility) ed eccezioni.

**Header**: codice + tag stato (severity da `core/utils/severity.js`) + badge
"SCADUTA" se applicabile + badge "rev.N" se revisione.

**Footer azioni** (dipendenti dallo stato):

- BOZZA: bottoni "Emetti" (apre `OffertaEmissioneDialog`), "Annulla offerta"
  (apre `OffertaEsitoDialog` in modalità ANNULLATA)
- EMESSA: bottoni "Registra accettazione" / "Registra rifiuto" (apre
  `OffertaEsitoDialog`), "Crea revisione"
- ACCETTATA: bottone "Push verso contratto" (apre `OffertaPushDialog`); se
  già pushato, mostra link al contratto generato (lettura sola)
- RIFIUTATA / ANNULLATA / SUPERATA: solo `DrawerFooter close-only` (memoria
  `feedback_drawer_footer_close_only`)

> **GAP 5 + C3 — state machine asimmetrica**: l'annullamento è un cambio di
> stato (→ ANNULLATA), non un hard delete, esattamente come "annulla contratto
> DRAFT". `RIFIUTATA` è "no del cliente" raggiungibile **solo da EMESSA**;
> `ANNULLATA` è "ritiro da parte nostra" raggiungibile **solo da BOZZA**.
> Niente bottone "Annulla offerta" su EMESSA (se serve correggere un'offerta
> emessa si crea revisione → SUPERATA). Entrambe le transizioni terminali
> negative salvano `motivazione_rifiuto`.

**`@after-show` content ready** (memoria `feedback_content_ready_after_show`):
caricamento dati con loading skeleton per evitare rimbalzo.

### Step FE-4 — Pannello detail eccezioni

**`EccezioniOffertaPanel.vue`** (master-detail inline, memoria
`feedback_master_detail_inline`):

- Lista paginata eccezioni dell'offerta (tipo, articolo, prezzo/sconto)
- Form sotto per nuova eccezione / edit (Select tipo OVERRIDE / ESCLUSIONE /
  AGGIUNTA — valori dall'enum `vendite.tipo_eccezione_contratto`, B3;
  AutoComplete articolo; prezzo)
- Editabile solo se stato offerta = BOZZA

> **Utility — niente panel** (C1): la sezione utility è **inline nella tab
> Testata** del drawer (vedi FE-3), non un panel separato. Mirror del
> `ContrattoDrawer`. `UtilityOffertaPanel.vue` (previsto in rev. b) è
> **rimosso** in rev. c.

### Step FE-5 — Dialogs cambio stato + push

**`OffertaEmissioneDialog.vue`** (memoria
`feedback_dialog_cambio_stato_dati_processo`):

- Conferma "Vuoi emettere questa offerta?"
- Mostra riepilogo: listino + versione fissata, validità, eccezioni count
- Avviso se versione listino non ATTIVA (lato BE solleverà
  `E_OFFERTA_EMISSIONE_VERSIONE_LISTINO_NON_ATTIVA`)

**`OffertaEsitoDialog.vue`** (esito cliente + annullamento, multi-modalità):

- Modalità ammesse (mutuamente esclusive, dipendenti dallo stato corrente):
  - ACCETTATA / RIFIUTATA → da EMESSA (esito cliente)
  - ANNULLATA → **solo da BOZZA** (annullamento da noi, C3)
- Data esito (DatePicker)
- Motivazione (Textarea) → salvata in `offerte_commerciali.motivazione_rifiuto`
  (GAP 4). Obbligatoria se RIFIUTATA o ANNULLATA, non richiesta se ACCETTATA
- Allegato opzionale: rinviato a brief allegati separato (GAP 3). In v1
  nessun upload qui

**`OffertaPushDialog.vue`**:

- Conferma "Vuoi generare il contratto da questa offerta?"
- Avviso "L'offerta resterà ACCETTATA, il contratto nascerà in DRAFT"
- Dopo push positivo: bottone "Apri contratto" che apre `ContrattoDrawer` del
  nuovo contratto (cross-component navigation via store)
- Su errore `E_OFFERTA_CONTRATTO_GIA_GENERATO`: dialog parlante con link al
  contratto esistente (pattern §5.3.3 documento pratiche "Opzione 1 errore
  propagato")

### Step FE-6 — i18n

**Scopo**: tutte le label sotto `vendite.offerte.*`.

**Chiavi minime**:

```
vendite.offerte.titolo = "Offerte commerciali"
vendite.offerte.nuova = "Nuova offerta"
vendite.offerte.colonne.codice = "Codice"
vendite.offerte.colonne.cliente = "Cliente"
vendite.offerte.colonne.utility = "Utility"
vendite.offerte.field_tipo_utenza = "Tipo utenza"
vendite.offerte.field_classe_utenza = "Classe utenza"
vendite.offerte.field_param_1_num = "Parametro 1"
vendite.offerte.field_param_2_txt = "Parametro 2"
vendite.offerte.field_motivazione = "Motivazione"
... (~50-60 chiavi totali tra colonne, label form testata+utility inline,
    bottoni, dialog, conferme annulla)
vendite.offerte.stati.BOZZA = "Bozza"
vendite.offerte.stati.EMESSA = "Emessa"
vendite.offerte.stati.ACCETTATA = "Accettata"
vendite.offerte.stati.RIFIUTATA = "Rifiutata"
vendite.offerte.stati.ANNULLATA = "Annullata"
vendite.offerte.stati.SUPERATA = "Superata"
... (6 stati, C4)
vendite.offerte.errori.E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO = "..."
... (6 codici errore)
```

### Step FE-7 — Navigation

**Scopo**: voce menu Offerte Commerciali in `core/navigation.js`.

- Sezione vendite, posizionata vicino a "Preventivi" e "Contratti"
- Icona: `pi pi-file-edit` o equivalente
- Permesso: si lega ad azione di processo (TODO seed DB, vedi §2.3)

---

## 5. Test e smoke test

### 5.1 Test BE Django

| Suite                        | Cosa copre                                                                                                                       |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `test_offerte_repository.py` | CRUD offerta + utility 1:1 (`get_utility`/`add_utility`/`update_utility`) + list filtri + display fields + lookup utility da BA  |
| `test_offerte_service.py`    | Logica orchestrazione + guard di stato (annullamento solo da BOZZA, rifiuto solo da EMESSA, C3) + idempotenza push               |
| `test_offerte_api.py`        | Tutti gli endpoint con mock service + error envelope (incl. POST/PATCH utility, POST annulla, POST registra-esito)               |

### 5.2 Smoke test bash

**File**: `backend/scripts/smoke-test-offerte.sh`

Con `# Indice test (0..N):` nell'header (regola AGENTS.md). Test minimi:

- 0: cleanup proattivo (memoria `feedback_smoke_test_idempotenti`)
- 1: crea offerta BOZZA (utility id popolati dal BA via payload inline)
- 2: PATCH utility (tipo/classe utenza + parametri) + aggiungi 2 eccezioni
- 3: emetti offerta (BOZZA → EMESSA)
- 4: tentativo modifica testata su EMESSA → 422 `E_OFFERTA_NON_EDITABILE`
- 5: tentativo annulla su EMESSA → 422 `E_OFFERTA_TRANSIZIONE_NON_AMMESSA` (C3)
- 6: registra accettazione (EMESSA → ACCETTATA)
- 7: push verso contratto → contratto DRAFT creato con utility **completa**
  copiata: id + tipo/classe utenza + parametri (verifica simmetria GAP 1)
- 8: ripeti push → seconda invocazione fallisce con
  `E_OFFERTA_CONTRATTO_GIA_GENERATO`
- 9: crea offerta nuova → emetti → crea revisione → rev.1 SUPERATA, rev.2 BOZZA
- 10: crea offerta nuova → tentativo registra-esito RIFIUTATA su BOZZA → 422
  (C3, rifiuto solo da EMESSA)
- 11: stessa offerta → annulla (BOZZA → ANNULLATA) → verifica stato +
  `motivazione_rifiuto` salvata
- 12: cleanup finale

### 5.3 Smoke test UI

Manuale, end-to-end, da fare in browser dopo deploy locale:

- Creazione offerta + selezione BA (verifica `istanza_utility_id`/`utility_id`
  auto-popolati in sola lettura) + compilazione **sezione utility inline**
  (tipo/classe utenza + parametri) + auto-save BOZZA
- Emissione → accettazione → push, verifica navigation verso `ContrattoDrawer`
  post-push e contratto con utility completa copiata (incl. tipo/classe utenza
  e parametri)
- Verifica badge "SCADUTA" su offerta EMESSA con `validita_al` superata
- Verifica readonly drawer per offerte non in BOZZA (testata + sezione utility
  inline + eccezioni)
- Verifica catena revisioni (rev.1 EMESSA → crea rev.2 → rev.1 SUPERATA,
  rev.2 BOZZA)
- Verifica annullamento da BOZZA via `OffertaEsitoDialog` modalità ANNULLATA,
  motivazione obbligatoria, stato finale ANNULLATA con motivazione visibile
- Verifica rifiuto da EMESSA via `OffertaEsitoDialog` modalità RIFIUTATA,
  motivazione obbligatoria salvata
- Verifica che il bottone "Annulla offerta" **non compare** su offerta EMESSA
  (C3) e "Registra rifiuto" non compare su BOZZA
- Verifica filtro utility nella lista

---

## 6. Sequenza di applicazione e parallelismi

### 6.1 Dipendenze dure

```
brief DB step 1-3 → BE-1 (types) → BE-2 (repository)
brief DB step 4-8 → BE-3 (service) → BE-4 (API)
                                        │
                                        ▼
                                    FE-1 (api client + store)
                                        │
                          ┌─────────────┼─────────────┐
                          ▼             ▼             ▼
                      FE-2 (lista)  FE-3 (drawer 3 tab)  FE-5 (dialogs)
                                        │
                                  FE-4 (panel eccezioni)
                                        │
                                        ▼
                                  FE-6 (i18n) + FE-7 (navigation)
                                        │
                                        ▼
                                  Smoke tests (5.2 + 5.3)
```

### 6.2 Parallelismi possibili

- **BE-1/BE-2 in parallelo a brief DB step 4-8**: i types e il repository
  scaffold (firma metodi) si possono scrivere appena il brief DB ha chiuso
  step 1-3 (tabelle + ALTER esistono). I metodi che chiamano fn DB
  (`crea_revisione`, `push_a_contratto`) si stub-bano e si completano quando
  le fn esistono.
- **FE-1/FE-2 in parallelo a BE-4**: appena gli endpoint sono firmati (anche
  prima dell'implementazione), il FE può scrivere api client + store con dati
  mock e SearchTable contro mock. Si collega al BE reale quando disponibile.
- **i18n FE-6 in parallelo a FE-3/FE-4/FE-5**: il file `it.json` si compila
  man mano che i componenti chiedono nuove chiavi (non aspettare la fine).

### 6.3 Critical path stimato (indicativo, dipende dal team DB)

| Settimana | DB                                   | BE                                        | FE                                              |
| --------- | ------------------------------------ | ----------------------------------------- | ----------------------------------------------- |
| 1         | Step 1-3 (seed + tabelle + ALTER)    | BE-1 (types) inizia                       | —                                               |
| 2         | Step 4-6 (state machine + revisione) | BE-2 (repository) + BE-3 (service inizio) | FE-1 (api+store) con mock                       |
| 3         | Step 7-8 (fn rev + push)             | BE-3 (service) completa + BE-4 (API)      | FE-2 (lista) + FE-3 (drawer scaffold)           |
| 4         | Step 9 (pgTAP suite completa)        | Test BE + smoke 5.2                       | FE-3/4/5 completi + FE-6 i18n + FE-7 navigation |
| 5         | —                                    | Smoke UI 5.3 + bugfix                     | Smoke UI 5.3 + bugfix                           |

---

## 7. Note operative

- **Autorizzazioni esplicite** (memoria `feedback_autorizzazioni_esplicite`):
  aggiunta dipendenze `requirements.in` o `package.json` solo dopo OK Tid. In
  v1 il piano non prevede dipendenze nuove (tutto su stack esistente Django
  6.01 + Vue 3.5 + PrimeVue 4.5).
- **Memoria pricing centralizzato** (`feedback_pricing_centralizzato`): se in
  futuro il drawer offerta dovesse mostrare anche un'anteprima prezzi
  calcolati, va via `PricingService` esistente, non implementare logica nuova.
- **Documentazione finale** (atterrata 2026-05-25):
  - [docs/it/backend/vendite/manual/api_offerte.md](../../backend/vendite/manual/api_offerte.md)
    (specchio di `api_contratti.md` ridotto al perimetro D4 + state machine offerta)
  - [docs/it/backend/vendite/manual/offerte_service.md](../../backend/vendite/manual/offerte_service.md)
    (struttura standard AGENTS.md §Regole Documentazione)
  - Voci aggiunte in `docs/it/backend/vendite/index.md` (sezione API + Altri contenuti)
  - Da fare quando il dominio sara' user-facing: `docs/it/guide/offerte-commerciali.md` (guida operatore)
- **Pratiche cross-link**: a fine sprint, scrivere il runtime end-to-end
  dell'asse `OFFERTA_QUADRO` in `analisi-pratiche-domini-anello3.md` §11.2
  (oggi solo ossatura, vedi §11.2.5 di quel documento). Dipende dall'esistenza
  reale del dominio → è davvero l'ultimo passo, dopo che BE+FE girano.
- **Branch**: lavoro su `dev/backend-tid` come da prassi (AGENTS.md §Ambiente
  di sviluppo).
- **Test idempotenza obbligatorio**: il caso "doppio push offerta → secondo
  fallisce con codice semantico" è obbligatorio sia in BE-3 (test_service
  mock) sia in smoke 5.2 step 7 (vedi convenzione §6.9.5 documento pratiche).

---

## 8. Stato del piano

| Step | Stato                                       | Dipendenze                                                         |
| ---- | ------------------------------------------- | ------------------------------------------------------------------ |
| BE-1 | **Atterrato** (rev. g)                      | DB step 1-9 + addendum + D7 (4 commit DB completati 2026-05-24/26) |
| BE-2 | **Atterrato**                               | DB step 1-9 + D7 OK                                                |
| BE-3 | **Atterrato**                               | DB step 1-9 + D7 OK                                                |
| BE-4 | **Atterrato**                               | DB step 1-9 + D7 OK                                                |
| FE-1 | **Atterrato** (rev. g)                      | BE-4 ✓                                                             |
| FE-2 | **Atterrato**                               | FE-1 ✓                                                             |
| FE-3 | **Atterrato** (data-driven)                 | FE-1 ✓ + fn DB capability                                          |
| FE-4 | **Atterrato**                               | FE-3 ✓                                                             |
| FE-5 | **Atterrato** (3 dialog + "gia' generato")  | FE-3 ✓                                                             |
| FE-6 | **Atterrato**                               | i18n it/en cablato                                                 |
| FE-7 | **Atterrato**                               | navigation + router + deep-link contratto                          |

> **Perimetro finale (rev. g, 2026-05-26)**: dominio offerta commerciale
> **completo lato BE + FE**. Tutto cablato:
>
> - **DB**: 6 stati + transizioni asimmetriche + numerazione `OFC-*` +
>   revisioni + push idempotente + 8 codici errore + suite pgTAP completa +
>   `script.fn_available_actions_offerta` (capability layer);
> - **BE Django**: testata + eccezioni + utility 1:1 atomica inline (su
>   CREATE e UPDATE) + note partizionate + capability blob nel detail +
>   display fields `billing_account_display` / `utility_display` +
>   `contratto_id`/`contratto_numero` collegati;
> - **FE Vue**: cartella dedicata `frontend/src/vendite/offerte/`, drawer
>   3 tab data-driven (`useEntityCapabilities` +
>   `mapAvailableActionsToDrawerActions` + dispatch `action.key`), drawer
>   eccezioni master-detail, drawer note, 3 dialog + dialog "gia' generato"
>   con link al contratto esistente, deep-link
>   `/vendite/contratti?open=<id>`.
>
> **42/42 test BE verdi, 1351/1351 test BE complessivi, build vite verde,
> eslint pulito**. Niente cantieri aperti.

---

*Piano BE + FE Offerta Commerciale — ZeroErp. Revisione 2026-05-26g
(chiusura cantiere FE + capability layer data-driven via
`script.fn_available_actions_offerta`). **Dominio completo BE + FE, 42/42
test verdi**. Eredita rev. f (step DB 8-9), rev. e (step 5-7), rev. d
(step 1-4), rev. c (rifiniture coerenza). Documento vivo, da aggiornare
solo se emergono follow-up (Pratiche cross-link `OFFERTA_QUADRO`).*
