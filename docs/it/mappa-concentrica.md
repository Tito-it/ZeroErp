# Mappa Concentrica — Stato dello Sviluppo ZeroERP

> Documento vivo. Aggiornare ad ogni milestone significativa.
>
> Riferimento metodologico: [sviluppo-concentrico.md](sviluppo-concentrico.md)

*Ultimo aggiornamento: 18 marzo 2026*

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
| `dbops`       | Schema DB  | Operativo | fn_run_automations, apply_fk_index_policy, registry task, vw_duplicate_indexes, audit_log, sessioni_utente, request_log                  |
| `script`      | Schema DB  | Operativo | fn_log_and_raise_error, viste e funzioni riusabili                                                                                       |
| `public`      | Schema DB  | Operativo | version_info                                                                                                                             |
| `maintenance` | Schema DB  | Operativo | Job schedulati pgAgent, job_run_log                                                                                                      |

### Cosa fornisce agli anelli esterni

- Error handling centralizzato (`ServiceError`, `ErrorManager.require`)
- Middleware API (exception handling, JWT audit, request context, request log)
- Pattern uniformi: `handle_post_json`, paginazione, throttling, search validators
- Automazioni DB: audit fields, tx_id, storicizzazione, lock colonne, protezione attivo
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

| Componente       | Tipo       | DB        | Backend   | Frontend  | Descrizione                                                                            |
| ---------------- | ---------- | --------- | --------- | --------- | -------------------------------------------------------------------------------------- |
| `config`         | App Django | Operativo | Operativo | —         | Stati, nazioni, UO, termini pagamento, priorita', canali; policy operative trasversali |
| `anagrafiche`    | App Django | Operativo | Operativo | Operativo | Soggetti, indirizzi, contatti, risorse umane, emittenti fiscali                        |
| `catalogo`       | App Django | Operativo | Operativo | —         | Articoli, UoM, listini, distinte base                                                  |
| `amm-software`   | App Django | Operativo | Operativo | Parziale  | Gestione operatori, permessi, profili reparto (solo ADMIN)                              |

### Frontend Anello 1 — Stato dettagliato

| Area                       | Stato     | Note                                                                          |
| -------------------------- | --------- | ----------------------------------------------------------------------------- |
| Gestione Geografica        | Operativo | 7 tab: indirizzi, toponomastica, comuni, CAP, province, regioni, stati — CRUD completo. UI da migliorare |
| Gestione Soggetti          | In test UI | PF/PG/ENTE end-to-end, 3 building block, ruoli, CF validator IT con omocodia  |
| Pannello Config            | Operativo | 67 tabelle CRUD generiche con drawer dinamico, metadata-driven               |
| Building block soggetto    | Operativo | SoggettoForm, ContattoForm, IndirizzoSoggettoForm, DatiSocietariForm, ComuneAutocomplete, StradarioAutocomplete, StradarioGeneraleAutocomplete |
| Modalita' sola lettura     | Operativo | Pattern protect CSS + provide/inject: 11 drawer, 3 view, 2 componenti core auto-hide (NewButton, DrawerFooter) |
| Amm. Software — Operatori  | Parziale  | Lista con filtri, creazione operatore, drawer modifica — mancano test UI reali |
| Amm. Software — Profili    | Parziale  | Gestione profili reparto — mancano test UI reali                               |
| Amm. Software — Permessi   | Placeholder | Solo pagina placeholder, da implementare                                     |
| Amm. Software — Audit Log  | Placeholder | Solo pagina placeholder, da implementare                                     |

### Cosa fornisce agli anelli esterni

- Entita' master referenziate via FK: soggetti, emittenti, risorse umane
- Tabelle config condivise: stati (doc fiscale, pratiche, flussi), priorita', canali
- Lookup e decodifiche centralizzate
- **Policy operative trasversali**: configurazioni che governano il comportamento del sistema su piu' domini e non appartengono a nessun dominio specifico (es. `user_emittenti_fiscali` — ambito operativo per emittente)
- **Gestione geografica completa**: indirizzi, toponomastica, comuni, province, regioni, stati — API + UI con autorizzazione per area `anagrafiche`
- **Building block frontend riutilizzabili**: composable centralizzati (useSearchTable, useDrawerState, useTabFreshness), componenti atomici (SoggettoForm, AuthUserForm, autocomplete), CSS utility classes

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

| Componente | Tipo       | DB        | Backend   | Descrizione                                                                                                                          |
| ---------- | ---------- | --------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `pratiche` | App Django | Operativo | Operativo | Workflow engine, giornale di bordo, generazione cross-pratica, handler dispatch, sospensioni, calcoli tempo, macchina a stati rigida |

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

| Fase                       | Stato | Riferimento                                                      |
| -------------------------- | ----- | ---------------------------------------------------------------- |
| DB-1..DB-7                 | FATTO | Tabelle, funzioni, trigger, seed, test pgTAP                     |
| BE-1 Setup app             | FATTO | Directory, apps.py, types.py, models.py                          |
| BE-2 Repository            | FATTO | pratiche_repository.py, generazione_repository.py                |
| BE-3 Services              | FATTO | pratiche_service.py, generazione_service.py, handler_registry.py |
| BE-4 API                   | FATTO | views.py, urls_v1.py, 19 endpoint REST                           |
| BE-5 Test                  | FATTO | 90 test (55 service + 35 API) con mock                           |
| BE-6 Sospensioni + Calcoli | FATTO | Service, repository, API, 26 test unitari, 18 smoke test curl    |
| BE-7 Macchina a stati      | FATTO | Transizioni validate da trigger DB (config-driven)               |

Documentazione backend: [docs/it/backend/pratiche/index.md](backend/pratiche/index.md)

Piano esecutivo: [piano-gestione-pratiche.md](dev/work-in-progress/piano-gestione-pratiche.md)

---

## Anello 3 — Processi Operativi

> Cicli di business che usano anelli interni. Ogni processo e' autonomo ma condivide vocabolario e infrastruttura.

| Componente    | Tipo       | DB        | Backend   | Descrizione                                                                            |
| ------------- | ---------- | --------- | --------- | -------------------------------------------------------------------------------------- |
| `vendite`     | App Django | Operativo | Operativo | Ciclo attivo: preventivi, ordini, DDT, fatture, pipeline fatturazione, lotti, commesse |
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

### In corso

- **Gestione Soggetti**: backend + frontend completati — in fase di test UI
- **Modalita' sola lettura**: implementata — da verificare con test UI utente LETTURA
- **Gestione Geografica**: operativo — UI da migliorare

### Breve termine

- Test UI reali su Gestione Soggetti, modalita' sola lettura, Gestione Geografica
- Completamento Amm. Software: pagine Permessi e Audit Log
- ClienteService Django (orchestrator creazione/subentro/disdetta cliente)

### Medio termine

- Integrazione `vendite` → `pratiche`: eventi di vendita generano pratiche con giornale
- Integrazione `anagrafiche` → `pratiche`: onboarding cliente/fornitore tracciato (attualmente CRUD anagrafiche NON scrive nel giornale di bordo — solo audit DB tecnico)
- Attivazione handler flusso per automazioni specifiche

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

*Mappa Concentrica — ZeroERP (marzo 2026)*