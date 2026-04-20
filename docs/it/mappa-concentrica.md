# Mappa Concentrica — Stato dello Sviluppo ZeroERP

> Documento vivo. Aggiornare ad ogni milestone significativa.
>
> Riferimento metodologico: [sviluppo-concentrico.md](sviluppo-concentrico.md)

*Ultimo aggiornamento: 20 aprile 2026*

---

## Visione d'insieme

```
                    ┌─────────────────────────────────────────────┐
                    │           ANELLO 3 — PROCESSI               │
                    │                                             │
                    │   vendite    acquisti    magazzino          │
                    │   pagamenti  contabilita                    │
                    │                                             │
                    │  ┌───────────────────────────────────────┐  │
                    │  │    ANELLO 2 — ORCHESTRAZIONE          │  │
                    │  │                                       │  │
                    │  │          pratiche                     │  │
                    │  │    (workflow, giornale,               │  │
                    │  │     generazione, handler,             │  │
                    │  │     sospensioni, calcoli tempo)       │  │
                    │  │                                       │  │
                    │  │  ┌─────────────────────────────────┐  │  │
                    │  │  │  ANELLO 1 — DATI BASE           │  │  │
                    │  │  │                                 │  │  │
                    │  │  │  config  anagrafiche  catalogo  │  │  │
                    │  │  │                                 │  │  │
                    │  │  │  ┌───────────────────────────┐  │  │  │
                    │  │  │  │  ANELLO 0 — NUCLEO        │  │  │  │
                    │  │  │  │                           │  │  │  │
                    │  │  │  │  core (infrastruttura)    │  │  │  │
                    │  │  │  │  dbops, script            │  │  │  │
                    │  │  │  │                           │  │  │  │
                    │  │  │  └───────────────────────────┘  │  │  │
                    │  │  └─────────────────────────────────┘  │  │
                    │  └───────────────────────────────────────┘  │
                    └─────────────────────────────────────────────┘
```

**Regola fondamentale**: ogni anello dipende solo dagli anelli interni. Mai dipendenze inverse o laterali.

---

## Anello 0 — Nucleo Infrastrutturale

> Il protocollo operativo del sistema. Si tocca solo per correggere limiti reali.

| Componente    | Tipo       | Stato     | Descrizione                                                                                                                              |
| ------------- | ---------- | --------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `core`        | App Django | Operativo | error_manager, middleware, permissions, endpoint_helpers, pagination, throttling, tracciamento processi/job, audit sessioni, request log |
| `dbops`       | Schema DB  | Operativo | fn_run_automations, apply_fk_index_policy, registry task, vw_duplicate_indexes, audit_log, sessioni_utente, request_log, **automazione daterange** |
| `script`      | Schema DB  | Operativo | fn_log_and_raise_error, viste e funzioni riusabili, **trgfn_set_validita** (trigger generico daterange)                                   |
| `public`      | Schema DB  | Operativo | version_info                                                                                                                             |
| `maintenance` | Schema DB  | Operativo | Job schedulati pgAgent, job_run_log                                                                                                      |

### Cosa fornisce agli anelli esterni

- Error handling centralizzato (`ServiceError`, `ErrorManager.require`)
- Middleware API (exception handling, JWT audit, request context, request log)
- Pattern uniformi: `handle_post_json`, paginazione, throttling, search validators
- Automazioni DB: audit fields, tx_id, storicizzazione, lock colonne, protezione attivo, **daterange nativo** (`script.trgfn_set_validita`)
- **Tracciamento processi e job**: API per audit log, task registry multi-dominio, job run log (6 endpoint REST, 27 test)
- **Audit sessioni**: login/refresh JWT tracciati in `dbops.sessioni_utente` con IP, user_agent, request_id (19 test)
- **Request logging**: ogni request `/api/*` registrata in `dbops.request_log` con metodo, path, status, durata
- **Token blacklist**: refresh token rotation con blacklist automatica (SimpleJWT `token_blacklist`)
- Policy indici FK automatica
- Logging e raise errori DB (`script.fn_log_and_raise_error`)

### Audit sessioni, request logging e token blacklist

Implementato il 6 marzo 2026 (vedi [Audit-logging-sessionii-request-token.md](dev/work-done/Audit-logging-sessionii-request-token.md)):

| Capacita'                         | Componente DB               | Componente Backend                                                             | Stato     |
| --------------------------------- | --------------------------- | ------------------------------------------------------------------------------ | --------- |
| Audit sessioni (login/refresh)    | `dbops.sessioni_utente`     | `session_audit_service` + `AuditTokenObtainPairView` / `AuditTokenRefreshView` | Operativo |
| Request logging (chi chiama cosa) | `dbops.request_log`         | `RequestLogMiddleware`                                                         | Operativo |
| Token blacklist e revoca          | SimpleJWT `token_blacklist` | Settings `ROTATE_REFRESH_TOKENS` + `BLACKLIST_AFTER_ROTATION`                  | Operativo |

Estensioni non-breaking: nuove tabelle in `dbops`, nuovo middleware in `core`, override view JWT. Nessun contratto esistente modificato. Gli anelli esterni ne beneficiano automaticamente senza alcuna modifica al proprio codice.

### Stabilita'

Stabile. Modifiche solo per correzioni o estensioni non-breaking (nuove policy, nuovi middleware).

---

## Anello 1 — Dati Base e Configurazione

> Entita' di riferimento condivise da tutti i processi. Vocabolario comune del sistema.

| Componente     | Tipo       | DB        | Backend   | Frontend  | Descrizione                                                                                                                |
| -------------- | ---------- | --------- | --------- | --------- | -------------------------------------------------------------------------------------------------------------------------- |
| `config`       | App Django | Operativo | Operativo | Operativo | Stati, nazioni, UO, termini pagamento, priorita', canali; policy operative trasversali; impostazioni parametri multi-scope |
| `anagrafiche`  | App Django | Operativo | Operativo | Operativo | Soggetti, indirizzi, contatti, risorse umane, emittenti fiscali, billing account                                           |
| `catalogo`     | App Django | Operativo | Operativo | Operativo | Articoli (CRUD, UoM, BoM, note) — **completato e testato** (work-done/gestione-articoli.md)                                |
| `amm-software` | App Django | Operativo | Operativo | Operativo | Gestione operatori, permessi riepilogo, profili reparto, audit log (solo ADMIN), drawer dedicato gestione permessi         |

> **Refactor in corso (20-04-2026) — Multi-Face Auth + Shop B2C:** `anagrafiche` ha ora il bridge `identita_digitali` (SSO multi-veste post-cutover 19-04-2026); `amm-software` BE/FE sono in refactor su PR-B per supportare i canali portale + shop. Dettaglio e contratti: [pr-b-shop-b2c-cambio-modello.md](dev/work-in-progress/pr-b-shop-b2c-cambio-modello.md). Guida: [architettura-multi-face-auth v2.0](guide/architettura-multi-face-auth.md).

### Frontend Anello 1 — Stato dettagliato

| Area                            | Stato      | Note                                                                                                                                                                    |
| ------------------------------- | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Gestione Geografica             | Operativo  | 7 tab: indirizzi, toponomastica, comuni, CAP, province, regioni, stati — CRUD completo. UI da migliorare                                                                |
| Gestione Soggetti               | In test UI | PF/PG/ENTE end-to-end, 3 building block, ruoli, CF validator IT con omocodia                                                                                            |
| Pannello Config                 | Operativo  | 67 tabelle CRUD generiche con drawer dinamico, metadata-driven                                                                                                          |
| Building block soggetto         | Operativo  | SoggettoForm, ContattoForm, IndirizzoSoggettoForm, DatiSocietariForm, ComuneAutocomplete, StradarioAutocomplete, StradarioGeneraleAutocomplete                          |
| Modalita' sola lettura          | Operativo  | Pattern protect CSS + provide/inject: tutti i drawer con app-readonly, 2 componenti core auto-hide (NewButton, DrawerFooter)                                            |
| Azioni processo (Livello 2)     | Operativo  | Prop `action` su NewButton/DrawerFooter, composable useActionPermission, mappa da /me/                                                                                  |
| Amm. Software — Operatori       | Operativo  | Lista con filtri/sort, drawer crea/modifica unificato, tab permessi override, rename utenti→operatori                                                                   |
| Amm. Software — Profili         | Operativo  | Lista reparti, drawer editor aree (Select livello) + azioni (ToggleSwitch), confirm save                                                                                |
| Amm. Software — Permessi        | Operativo  | Matrice operatori × aree con Tag colorati, colonne dinamiche, filtri reparto/ruolo                                                                                      |
| Amm. Software — Audit Log       | Operativo  | Timeline globale 6 tabelle storico, paginazione lazy, sort server-side, filtro tipo                                                                                     |
| Amm. Software — Drawer Permessi | Operativo  | Drawer dedicato gestione permessi richiamabile dalla riga lista operatori; `OperatorePermessiTab` riusabile reattivo a `authUserId`                                     |
| Catalogo — Articoli             | Operativo  | Lista con 7 filtri, drawer 3 tab (UoM, BoM, note), `ArticoloLookup` BB cross-dominio. **Completato e testato**                                                          |
| Catalogo — Unita' di Misura     | Operativo  | Lista, drawer CRUD, conversioni UoM, lookup generico whitelist                                                                                                          |
| Impostazioni Parametri          | Operativo  | Lista multi-scope (default/emittente/gruppo/utente), drawer override con selettore scope (Personale/Emittente) per admin, `PARAMETER_SCOPE` come unica fonte di verita' |

### Cosa fornisce agli anelli esterni

- Entita' master referenziate via FK: soggetti, emittenti, risorse umane
- Tabelle config condivise: stati (doc fiscale, pratiche, flussi), priorita', canali
- Lookup e decodifiche centralizzate
- **Policy operative trasversali**: configurazioni che governano il comportamento del sistema su piu' domini e non appartengono a nessun dominio specifico (es. `user_emittenti_fiscali` — ambito operativo per emittente)
- **Gestione geografica completa**: indirizzi, toponomastica, comuni, province, regioni, stati — API + UI con autorizzazione per area `anagrafiche`
- **Building block frontend riutilizzabili**: composable centralizzati (useSearchTable, useDrawerState, useTabFreshness, useReadonlyMode, useActionPermission), componenti atomici (SoggettoForm, AuthUserForm, autocomplete, NewButton, DrawerFooter con prop `action`), CSS utility classes
- **Sistema permessi a 2 livelli**: Livello 1 area (TUTTO/LETTURA/BLOCCATO) + Livello 2 azioni processo (abilitata/negata), con enforcement backend (ZeroERPPermission) e auto-hide frontend (prop `action`)

### Regola di posizionamento in `config`

`config` e' l'unico schema di Anello 1 con natura cross-schema. Ospita due categorie distinte:

1. **Cataloghi condivisi**: dati di riferimento statici usati come vocabolario comune (stati, priorita', canali, UO, termini pagamento)
2. **Policy operative trasversali**: configurazioni che descrivono regole di governo applicabili a piu' processi, quando non esiste uno schema di dominio piu' appropriato

Una tabella appartiene alla seconda categoria se: (a) non descrive un'entita' di business ma una regola di visibilita' o operativita', e (b) la regola vale trasversalmente su piu' schemi di Anello 3. In assenza di uno schema dedicato, `config` e' la collocazione meno artificiale — non `dbops` (infrastruttura tecnica) ne' `anagrafiche` (entita' anagrafiche).

### Stabilita'

Stabile. Cresce per aggiunta di nuove tabelle config (es. `config.canali_pratiche` aggiunta per pratiche) senza rompere quanto esistente.

---

## Anello 2 — Orchestrazione di Dominio

> Motore trasversale che gli anelli esterni usano per tracciare, orchestrare e automatizzare.

| Componente | Tipo       | DB        | Backend   | Frontend  | Descrizione                                                                                                                          |
| ---------- | ---------- | --------- | --------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `pratiche` | App Django | Operativo | Operativo | Operativo | Workflow engine, giornale, generazione cross-pratica, handler dispatch, sospensioni, calcoli tempo, macchina a stati, note, allegati |

### Cosa fornisce agli anelli esterni

- **Pratiche**: contenitore tracciabile per qualsiasi processo (onboarding cliente, gestione ordine, assistenza tecnica)
- **Flussi**: step operativi con prerequisiti, esiti, scadenze, assegnazione risorse
- **Giornale di bordo**: audit trail immutabile, append-only, con correlazione `tx_id`
- **Generazione cross-pratica**: un flusso completato puo' generare automaticamente nuove pratiche
- **Handler dispatch**: mapping `handler_key` → classe Python per automazione step
- **Canali**: visibilita' dei flussi su sorgenti esterne (WEB_CLIENTI, APP_TECNICA, PORTALE_FORNITORI)
- **Sospensioni**: fermo temporaneo pratica/flusso con propagazione automatica e riattivazione (manuale o pgAgent)
- **Calcoli tempo**: tracking tempi netti tra coppie di flussi (formula da/a), con esclusione giorni sospensione
- **Macchina a stati rigida**: transizioni ammesse validate da trigger DB (config-driven)
- **API interna**: `pratiche_service` come facade per gli anelli esterni

### Perche' e' un anello separato (non anello 1)

`pratiche` non e' un dato di riferimento statico — e' un **motore di orchestrazione con stato e ciclo di vita**. Dipende da anello 1 (config, anagrafiche) per le FK, ma fornisce capacita' operative che gli anelli esterni consumano. E' il cuore operativo del sistema: ogni evento significativo (nuovo cliente, nuovo ordine, nuova assistenza) genera una pratica con il suo giornale.

### Perche' non e' anello 3 (processi)

Non e' un processo di business specifico (come vendite o acquisti). E' l'**infrastruttura di processo** che tutti i domini usano. E' al servizio dei processi, non un processo in se'.

### Stato sviluppo dettagliato

**v1 (4-6 marzo 2026):**

| Fase                       | Stato | Riferimento                                                      |
| -------------------------- | ----- | ---------------------------------------------------------------- |
| DB-1..DB-7                 | FATTO | Tabelle, funzioni, trigger, seed, test pgTAP                     |
| BE-1..BE-5                 | FATTO | App setup, repository, service, API (19 endpoint), 90 test       |
| BE-6 Sospensioni + Calcoli | FATTO | Service, repository, API, 26 test unitari, 18 smoke test curl    |
| BE-7 Macchina a stati      | FATTO | Transizioni validate da trigger DB (config-driven)               |

**v2 (28-29 marzo 2026):**

| Fase | Stato | Riferimento |
| ---- | ----- | ----------- |
| DB: collegamento ruolo/istanza | FATTO | ALTER + trigger guard contesto + codice PRA via sistema_codici |
| BE: JOIN display fields | FATTO | list/get pratiche e flussi con 7 JOIN, named columns (no indici posizionali) |
| BE: contesto anagrafico | FATTO | soggetto_id + soggetto_ruolo_id + istanza_utility_id, validazione coerenza |
| BE: guard pre/post-attivazione | FATTO | Verifica stato BA del soggetto per tipo prestazione |
| BE: order_by + search | FATTO | Ordinamento dinamico con whitelist, ricerca ILIKE su codice/descrizione/soggetto |
| BE: filtro data | FATTO | data_da/data_a con default anno-1 |
| BE: note CRUD | FATTO | 4 endpoint (GET/POST/PATCH/DELETE), 6 test, giornale trigger |
| BE: allegati CRUD | FATTO | 3 endpoint (GET/POST/DELETE, immutabili), 4 test, giornale trigger |
| FE: lista pratiche | FATTO | SearchTable con filtri (stato, priorita', data_da/data_a, search), display fields |
| FE: drawer dettaglio | FATTO | 5 tab (Dati, Flussi, Note, Allegati, Giornale), azioni stato, severity |
| FE: drawer creazione | FATTO | Soggetto opzionale (SoggettoResolver), ruolo, tipo prestazione, priorita' |
| FE: tab flussi | FATTO | Lista compatta, crea/avvia/completa flusso inline |
| FE: tab note | FATTO | Form inline crea + lista con edit/delete |
| FE: tab allegati | FATTO | Lista metadati con delete (upload posticipato) |
| FE: tab giornale | FATTO | Timeline audit con icone/severity per tipo azione |
| Test totali | 115 | 105 Django (mock CI) + 25 smoke test bash |

Documentazione: [gestione-pratiche-v2.md](dev/work-in-progress/gestione-pratiche-v2.md) | API: [api_pratiche_list](backend/pratiche/manual/api_pratiche_list) | [api_pratiche_note](backend/pratiche/manual/api_pratiche_note) | [api_pratiche_allegati](backend/pratiche/manual/api_pratiche_allegati)

Piano v1 (storico): [work-done/piano-gestione-pratiche.md](dev/work-done/piano-gestione-pratiche.md)

---

## Anello 3 — Processi Operativi

> Cicli di business che usano anelli interni. Ogni processo e' autonomo ma condivide vocabolario e infrastruttura.

| Componente    | Tipo       | DB        | Backend   | Descrizione                                                                            |
| ------------- | ---------- | --------- | --------- | -------------------------------------------------------------------------------------- |
| `vendite`     | App Django | Operativo | Operativo | Ciclo attivo: preventivi, ordini, DDT, fatture, pipeline fatturazione, lotti, commesse, **listini v3** (pricing completo + rettifiche + alert) |
| `acquisti`    | App Django | Operativo | Stub      | Ciclo passivo: richieste offerta, ordini, DDT, fatture                                 |
| `magazzino`   | App Django | Operativo | Stub      | Movimenti, giacenze, lotti, seriali                                                    |
| `pagamenti`   | App Django | Operativo | Stub      | Scadenze, riconciliazioni                                                              |
| `contabilita` | App Django | Operativo | Stub      | Piano conti, registrazioni, partite                                                    |
| `storico`     | App Django | Operativo | Stub      | Audit temporale, storicizzazione                                                       |

### Dipendenze verso anelli interni

```
vendite ──────► config (stati_doc_fiscale, termini_pagamento)
              ► anagrafiche (soggetti, emittenti_fiscali)
              ► catalogo (articoli, UoM, listini)
              ► core (error_manager, endpoint_helpers)
              ► pratiche (FUTURO — giornale, workflow)

acquisti ─────► stesse dipendenze di vendite
              ► pratiche (FUTURO)
```

### Integrazione futura con pratiche

Quando l'anello 2 sara' operativo a livello backend, i processi di anello 3 potranno:

1. **Creare pratiche** per i propri eventi (`pratiche_service.crea_pratica`)
2. **Alimentare il giornale** con eventi di dominio (nuovo cliente → PRATICA_CREATA)
3. **Usare flussi** per step operativi tracciati (approvazione ordine, sopralluogo, collaudo)
4. **Sfruttare generazione cross-pratica** (ordine completato → genera pratica assistenza)

I processi **massivi** (lotto fatturazione, import batch) mantengono la propria infrastruttura di tracking (pipeline, task runs, log fatture) perche' hanno requisiti diversi (parallelismo, resume per singola fattura, tracing per step). Il giornale di pratiche traccia eventi a livello di **processo singolo**, non di batch.

### Stato sviluppo vendite (app leader)

| Area                                    | Stato                                              |
| --------------------------------------- | -------------------------------------------------- |
| Pipeline fatturazione                   | Operativo                                          |
| Lotti massivi/giornalieri               | Operativo                                          |
| Registry task DB multi-dominio          | Operativo                                          |
| Dispatch task con implementation_key    | Operativo                                          |
| Runtime task tracing                    | Operativo                                          |
| Builder XML SDI                         | In corso (payload pronto, generazione XML da fare) |
| Persistenza esito SDI                   | Da fare                                            |
| Commesse (push, orchestrator, handlers) | Operativo                                          |
| Listini v3 (N2/N5/N6/N7/N8a)           | Operativo — Sprint B-v3 completato (aprile 2026)   |
| Pricing commesse (N5/N7/N7-sblocco)    | Operativo — riallineamento, variazione, sblocco    |

---

## Matrice delle dipendenze

```
                 core   config   anagr.   catal.   pratiche   vendite
core              -       -        -        -        -          -
config           usa      -        -        -        -          -
anagrafiche      usa      -        -        -        -          -
catalogo         usa      -        -        -        -          -
pratiche         usa     usa      usa       -        -          -
vendite          usa     usa      usa      usa    (futuro)      -
acquisti         usa     usa      usa      usa    (futuro)      -
magazzino        usa     usa      usa       -     (futuro)      -
pagamenti        usa     usa       -        -     (futuro)      -
contabilita      usa     usa       -        -     (futuro)      -
```

Nessuna dipendenza inversa. Nessuna dipendenza laterale tra processi di anello 3.

Gli anelli esterni possono dipendere direttamente da anelli non adiacenti — vendite usa `core` e `config` senza passare per `pratiche`. Questo non viola la direzione delle dipendenze, sempre dall'esterno verso l'interno: descrive semplicemente come certi tipi di informazione attraversano il tronco (la linfa, nella metafora del vocabolario).

---

## Evoluzione prevista

### Completato (marzo 2026)

- ~~Completamento BE-1..BE-5 per `pratiche`~~ — **FATTO** (4 marzo 2026)
- ~~Sospensioni, calcoli tempo, macchina a stati (BE-6..BE-7)~~ — **FATTO** (6 marzo 2026)
- `pratiche` e' consumabile dagli anelli esterni (19 endpoint REST, 90 test unitari, 18 smoke test)
- ~~Audit sessioni, request logging, token blacklist~~ — **FATTO** (6 marzo 2026)
- Anello 0 traccia sessioni JWT, request API e supporta revoca token (19 test unitari)
- ~~Frontend Sprint 1: layout applicativo~~ — **FATTO** (marzo 2026)
  - AppLayout responsive (sidebar morfica, content tabs, breadcrumb, shortcut tastiera)
  - Ricerca universale soggetti con dettaglio parametrico per ruolo
- ~~Frontend Sprint 2: Amm. Software~~ — **FATTO** (marzo 2026)
  - Lista operatori con filtri, creazione/modifica operatore, profili reparto
  - Building block repository core (52 test)
- ~~Frontend Sprint 3: Building block riutilizzabili~~ — **FATTO** (marzo 2026)
  - SoggettoForm universale PF/PG/ENTE, AuthUserForm, ComuneAutocomplete, StradarioAutocomplete
  - Composable core: useLookup, useServerAutocomplete, useSoggettoForm, useAuthUser
  - CSS utility classes: app-page, app-datatable, form-grid, app-drawer-content
- ~~Frontend Sprint 4: Gestione Geografica~~ — **FATTO** (15 marzo 2026)
  - 7 tab CRUD: indirizzi, toponomastica, comuni, CAP, province, regioni, stati
  - 21 endpoint API con autorizzazione area `anagrafiche`, 657 test backend
  - Composable centralizzati: useSearchTable, useDrawerState, useTabFreshness, DrawerFooter, NewButton
- ~~Frontend Sprint 5: Gestione Soggetti~~ — **FATTO** (15 marzo 2026)
  - Soggetti PF/PG/ENTE end-to-end: 4 fasi, 3 building block, 11 endpoint, CF validator IT con omocodia
  - Building block riutilizzabili: ContattoForm, IndirizzoSoggettoForm, DatiSocietariForm + composable
  - Ruoli: assegnazione da drawer, lookup filtrato per natura, preparazione domini futuri
  - Pannello config generico: 67 tabelle CRUD con drawer dinamico metadata-driven
  - Code review: fix race condition watcher, cleanup timeout, eliminato doppio fetchList
  - 686 test backend, 471 moduli frontend
- ~~Frontend Sprint 6: Fix indirizzi + contatti soggetto~~ — **FATTO** (16 marzo 2026)
  - Fix gestione contatti (combo unita' organizzative, validazione email/PEC)
  - Fix gestione indirizzi soggetto (pre-populate replace, civico/estensione)
- ~~Refactor v3: Riallineamento modello concentrico~~ — **FATTO** (18 marzo 2026)
  - Logica duplicato centralizzata in `fn_check_indirizzo_duplicato` (DB)
  - CAP risolto via `fn_resolve_codice_postale` (DB)
  - `useIndirizzoBase.js` composable condiviso (elimina duplicazione IndirizzoDrawer/IndirizzoSoggettoForm)
  - `via_obj` unificato (elimina stradario_obj + stradario_generale_obj)
  - Default soggetti spostati da hardcode Python a `config.parameters` (DB source of truth)
  - Ordinamento tabelle config funzionante (order_by/order_dir)
  - 689 test backend
- ~~Refactor v4: Completamento modello concentrico~~ — **FATTO** (18 marzo 2026)
  - Auto-clone indirizzi spostato da frontend a backend (`_apply_auto_clone`)
  - `_buildNominativo` spostato nel service Python
  - `addressNotFound` centralizzato in `useIndirizzoBase`
  - Payload replace semplificato (usa `indirizzo_dettaglio_id` diretto)
- ~~Modalita' sola lettura~~ — **FATTO** (18 marzo 2026)
  - Pattern protect provide/inject: 11 drawer, 3 view, 2 componenti core auto-hide
  - DB: `fn_get_user_permissions_map`, `/me/` arricchito con `permessi_area`
- ~~Documentazione API~~ — **FATTO** (18 marzo 2026)
  - 57 endpoint documentati: soggetti, indirizzi, geo config, amm. software
  - 3 doc esistenti aggiornate: lookup codici, user profile, api overview

- ~~Frontend Sprint 7: Amm. Software completa + Permessi Livello 1+2~~ — **FATTO** (20 marzo 2026)
  - Area Amm. Software: 4 pagine operative (operatori, profili reparto, permessi riepilogo, audit log)
  - Refactor naming utenti→operatori su tutto lo stack (backend, frontend, test, doc, smoke test)
  - Livello 1 consolidato: useReadonlyMode su tutte le view, app-readonly su tutti i drawer
  - Livello 2 azioni processo: prop `action` su NewButton/DrawerFooter, composable useActionPermission
  - DB: fn_get_user_actions_map + fn_get_user_profile arricchito con azioni_abilitate
  - Costanti enum centralizzate in core/constants.js (RUOLO_SISTEMA, LIVELLO_ACCESSO)
  - Helper severity riutilizzabili, useConfirmAction (confirmSave/Delete/Action), displayTimestamp
  - Audit qualita': fix race condition, null safety, SQL validation, toast validazione
  - Sort default: soggetti (ragione_sociale), operatori (cognome), audit (timestamp DESC)

- ~~Frontend Split View (tab affiancate)~~ — **FATTO** (29 marzo 2026)
  - Split view read-only via provide/inject (stessa sola lettura degli operatori LETTURA)
  - Bottone "Affianca" sulla barra ContentTabs, Popover selettore tab
  - Responsive: solo desktop >= 1280px, chiusura automatica sotto soglia
- ~~Frontend Pratiche v2~~ — **FATTO** (29 marzo 2026)
  - Lista con display fields (7 JOIN backend), filtri (stato, priorita', data_da/data_a, search)
  - Drawer creazione con SoggettoResolver + selezione ruolo + cascata
  - Drawer dettaglio con 5 tab: Dati (azioni stato), Flussi, Note, Allegati, Giornale
  - Backend: 26 endpoint REST, 115 test Django, 25 smoke test
  - Collegamento anagrafico 3 livelli: soggetto → ruolo → istanza (guard DB + service)
  - Guard pre/post-attivazione tipo prestazione
- ~~Topbar: logout, badge iniziali utente, icone coerenti~~ — **FATTO** (29 marzo 2026)
- ~~Sidebar mobile: drawer collassato (solo icone)~~ — **FATTO** (29 marzo 2026)

### Completato (aprile 2026)

- ~~Integrazione AI v1~~ — **FATTO** (31 marzo 2026)
  - Anello 4 — strato di interazione intelligente sopra le API esistenti
  - 9 tool (6 lettura + 3 scrittura con conferma), widget flottante non modale
  - Contesto documentale statico, multi-tool chaining, timeout 30s
  - Shortcut Ctrl+., tema scuro, responsive, 61 test unitari
- ~~Gestione Autenticazioni fasi 1-3~~ — **FATTO** (1 aprile 2026)
  - Email building block: account multipli, template Jinja, log, risoluzione mittente per contesto
  - Token monouso: creazione, validazione, consumo, invalidazione, crittografia Fernet
  - Reset password self-service, invito operatore, cambio password obbligatorio al primo accesso
  - Frontend: 5 pagine auth (login, reset, invito, cambio pw), 890 test backend
  - Fase 4 (2FA TOTP) rimandata — pianificata in WIP
- ~~Refactor E_GENERICO~~ — **FATTO** (2 aprile 2026)
  - Deprecato codice errore generico `E_GENERICO` su tutto il DB
  - Sostituito con codici specifici per schema: `E_PARAMETRO_INVALIDO`, `E_PREZZO_LISTINO_NON_TROVATO`, `E_PREZZO_LISTINO_AMBIGUO`, ecc.
  - Tutte le funzioni PL/pgSQL ora usano codici identificabili per frontend/monitoring
- ~~Gestione Clienti v1~~ — **FATTO** (marzo 2026)
  - CRUD completo: creazione manuale, drawer con contatti/indirizzi/conti a 2 livelli
  - Catena automatica: istanza fittizia + billing account + cliente
  - 5 endpoint API, 29 test service, drawer frontend con sotto-drawer
  - v2 (subentro, disdetta, BA parent/child) pianificata in WIP
- ~~Gestione Articoli e Listini~~ — **FATTO** (3 aprile 2026)
  - Catalogo: backend 3 repository (articoli, UoM, BoM) + 19 funzioni service + 19 endpoint API
  - UoM CRUD: backend completo + frontend (lista, drawer, route)
  - Listini: backend 19 metodi repository + 18 funzioni service + 18 endpoint API
  - Frontend catalogo: ArticoliSearchTable, ArticoloDrawer (3 tab), UnitaMisuraView, ArticoloLookup BB
  - Frontend listini: ListiniSearchTable, ListinoDrawer (2 tab), VersioneDrawer (righe prezzo), TestResolverDialog
  - Building block: `LookupSelect` generico (29 Select sostituiti in 15 file), `ArticoloLookup` cross-dominio
  - Severity centralizzate: `statoVersioneListinoSeverity`, `dominioListinoSeverity`
  - 77 test backend, build frontend OK

### Completato (5-7 aprile 2026)

- ~~Catalogo Articoli~~ — **COMPLETATO E TESTATO** (5 aprile 2026)
  - Backend + frontend chiusi, 49 test verdi, doc consolidata in [work-done/gestione-articoli.md](dev/work-done/gestione-articoli.md)
  - Building block prodotti: `ArticoloLookup.vue` cross-dominio + endpoint lookup
- ~~Consolidamento WIP listini~~ — **FATTO** (6 aprile 2026)
  - I due vecchi WIP `gestione-articoli-listini.md` + `gestione-listini.md` consolidati in sviluppo-listini.md (ora in [work-done](dev/work-done/sviluppo-listini-v1.md), superseded da [sviluppo-listini-v3.md](dev/work-in-progress/sviluppo-listini-v3.md))
  - Estratte rettifiche prezzi (DB-L4) in [sviluppo-rettifiche.md](dev/work-in-progress/sviluppo-rettifiche.md)
- ~~Drawer dedicato gestione permessi operatore~~ — **FATTO** (6 aprile 2026)
  - `OperatorePermessiTab` reso riutilizzabile (watch su `authUserId`)
  - Nuovo `OperatorePermessiDrawer.vue` richiamabile dalla riga lista operatori
- ~~Parametri di sistema multi-scope~~ — **FATTO** (5-6 aprile 2026)
  - Drawer override con selettore scope (Personale/Emittente) visibile solo agli admin
  - Backend: `upsert_emittente_override` + check `IsAdminZeroERP`, fallback emittente "gestore di default"
  - Fix constraint v3 (`uq_overrides_full_scope_v3`) e fn `get_emittente_fiscale_id_for_user` allineata a `script.fn_get_emittenti_scope`
  - Costante condivisa `PARAMETER_SCOPE` come unica fonte di verita' frontend
- ~~AI tool catalogo + billing account~~ — **FATTO** (7 aprile 2026)
  - Nuovo `cerca_articoli` (dominio catalogo) — sblocca "cerca articolo X" via AI
  - Nuovo `cerca_billing_account` (dominio anagrafiche) — wrappa la ricerca dedicata BA con scope emittente
  - System prompt esteso con glossario di dominio italiano (cliente=BA, articolo=catalogo)
  - Tool registrati totali: **11** (era 9)
- ~~Logo brand ottimizzato~~ — **FATTO** (5 aprile 2026)
  - Master 1640x1640 → versioni ottimizzate 512/256/32 px per frontend, favicon (PNG+ICO), docs

### Completato (8-12 aprile 2026)

- ~~Migrazione `daterange` nativo PostgreSQL~~ — **FATTO** (12 aprile 2026)
  - Infrastruttura: `dbops.automazione_overlap` + `script.trgfn_set_validita()` (trigger generico riusabile)
  - Fase 1: 5 tabelle con GIST migrate (listini_versioni, listini_associazioni, uom_conversioni, contratti, articoli_componenti) + `fn_resolve_prezzo_listino` aggiornata
  - Fase 2: 11 tabelle config/anagrafiche migrate + 5 funzioni permessi semplificate con `@>`
  - Fase 3: 2 tabelle pratiche con `tstzrange`
  - Backend: ottimizzazione query repository (`validita @>` al posto dei doppi confronti)
  - Linee guida SQL: sezione 7b aggiunta
  - Analisi: [migrazione-daterange.md](dev/work-in-progress/migrazione-daterange.md)
- ~~Listini v3 — Sprint B completo~~ — **FATTO** (12 aprile 2026)
  - **N8a** Variazione % massa su BOZZA (backend + frontend dialog + 9 test)
  - **N2** Alert scadenze versioni (backend + frontend widget badge + 2 test)
  - **N6** Rettifica controllata riga ATTIVA non propagata (backend + trigger DB defense-in-depth + 4 test)
  - **N5** Riallineamento prezzo commessa (backend + 3 test)
  - **N7** Variazione prezzo eccezionale commessa + sblocco (backend + 6 test)
  - Avviso UX programmazione chiusura versione ATTIVA (`ProgrammaChiusuraDialog.vue`)
  - Documentazione: N3 lifecycle preventivo→commessa, N4 nota match_level 3, N8b guida "listino post-it"
  - 2 doc API create/aggiornate, error policies registrate, 1231 test totali
  - Analisi: [sviluppo-listini-v3.md](dev/work-in-progress/sviluppo-listini-v3.md)
- ~~Emittenti fiscali CRUD + BA mapping + Utilities~~ — **FATTO** (8 aprile 2026)
  - Admin CRUD + sub-resource mapping BA + matrice utilities slot/override
  - BB `list_entity_utility_matrix` + `UtilityPerRuoloSelect`, validazione P.IVA
- ~~Matrice utilities tipi ruolo~~ — **FATTO** (8 aprile 2026)
  - CRUD admin `config.utilities_tipi_ruolo`, app config attivata, drawer tab usage
- ~~Refactor operatore-emittenti 1-a-1~~ — **FATTO** (9 aprile 2026)
  - `JwtAuditAuthentication` Option A pura, GUC session-scoped
  - BE fasi 2-4 + FE completa + 7 fix critici review
- ~~Refactor invariante univocita' listini~~ — **FATTO** (10 aprile 2026)
  - Drop `priorita` da versioni e associazioni, constraint GIST cross-listino
  - Permessi v2: 6 fasi, `model_permission` su 33 view, `IvaSelect`/`ContoContabileSelect`

### In corso

- **Gestione Soggetti**: backend + frontend completati — in fase di test UI
- **Gestione Geografica**: operativo — UI da migliorare
- **Gestione Clienti/Fornitori**: drawer end-to-end operativo, v2 (subentro/disdetta) pianificata
- **Gestione Pratiche v2**: frontend operativo — in fase di test UI
- **Integrazione AI v2**: evoluzione con contesto dinamico e nuovi tool — WIP
- **Autenticazione 2FA**: fase 4 TOTP — WIP
- **Permessi v2**: livello oggetto e granularita' fine — in corso (33 view gia' configurate)
- **Rettifiche prezzi (DB-L4)**: motore delta + canali manuale/automatico — pianificato in WIP dedicato

### Breve termine

- Test UI reali su Articoli, UoM, Pratiche, Soggetti, Clienti, Fornitori
- Seed azioni processo per nuovi domini (catalogo, vendite) + prop `action` sui componenti
- Upload file allegati pratiche (storage filesystem/object storage)

### Medio termine

- Integrazione `vendite` → `pratiche`: eventi di vendita generano pratiche con giornale
- Integrazione `anagrafiche` → `pratiche`: onboarding cliente/fornitore tracciato
- Attivazione handler flusso per automazioni specifiche
- pgAgent job riattivazione automatica sospensioni

### Lungo termine

- Tutti i processi di anello 3 usano `pratiche` per tracciabilita' e orchestrazione
- Il giornale di bordo diventa la vista unificata sulle attivita' dell'azienda
- Canali esterni (portale clienti, app tecnica) operano tramite flussi con visibilita' controllata

---

## Come aggiornare questo documento

1. **Nuovo componente**: aggiungere nella tabella dell'anello corretto, con stato DB e Backend
2. **Cambio stato**: aggiornare la colonna Stato (Stub → DA FARE → Operativo)
3. **Nuova dipendenza**: aggiungere nella matrice e verificare che rispetti la direzione degli anelli
4. **Nuovo anello**: se emerge un livello intermedio, inserirlo e ri-numerare

> La mappa deve riflettere la realta', non le intenzioni. Aggiornare solo quando qualcosa cambia concretamente.

---

*Mappa Concentrica — ZeroERP (12 aprile 2026)*
