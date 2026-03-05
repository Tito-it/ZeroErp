# Mappa Concentrica — Stato dello Sviluppo ZeroERP

> Documento vivo. Aggiornare ad ogni milestone significativa.
>
> Riferimento metodologico: [sviluppo-concentrico.md](sviluppo-concentrico.md)

*Ultimo aggiornamento: 5 marzo 2026*

---

## Visione d'insieme

```
                    ┌─────────────────────────────────────────────┐
                    │           ANELLO 3 — PROCESSI               │
                    │                                             │
                    │   vendite    acquisti    magazzino           │
                    │   pagamenti  contabilita                    │
                    │                                             │
                    │  ┌───────────────────────────────────────┐  │
                    │  │    ANELLO 2 — ORCHESTRAZIONE          │  │
                    │  │                                       │  │
                    │  │          pratiche                      │  │
                    │  │    (workflow, giornale,                │  │
                    │  │     generazione, handler)              │  │
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
                    │  │  │  │  dbops, script             │  │  │  │
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

| Componente | Tipo | Stato | Descrizione |
|---|---|---|---|
| `core` | App Django | Operativo | error_manager, middleware, permissions, endpoint_helpers, pagination, throttling, tracciamento processi/job |
| `dbops` | Schema DB | Operativo | fn_run_automations, apply_fk_index_policy, registry task, vw_duplicate_indexes, audit_log |
| `script` | Schema DB | Operativo | fn_log_and_raise_error, viste e funzioni riusabili |
| `public` | Schema DB | Operativo | version_info |
| `maintenance` | Schema DB | Operativo | Job schedulati pgAgent, job_run_log |

### Cosa fornisce agli anelli esterni

- Error handling centralizzato (`ServiceError`, `ErrorManager.require`)
- Middleware API (exception handling, JWT audit, request context)
- Pattern uniformi: `handle_post_json`, paginazione, throttling, search validators
- Automazioni DB: audit fields, tx_id, storicizzazione, lock colonne, protezione attivo
- **Tracciamento processi e job**: API per audit log, task registry multi-dominio, job run log (6 endpoint REST, 27 test)
- Policy indici FK automatica
- Logging e raise errori DB (`script.fn_log_and_raise_error`)

### Evoluzione pianificata (WIP)

Le seguenti capacita' sono in fase di progettazione (vedi [Audit-logging-sessionii-request-token.md](dev/work-in-progress/Audit-logging-sessionii-request-token.md)):

| Capacita' | Componente DB | Componente Backend | Stato |
| --- | --- | --- | --- |
| Audit sessioni (login/refresh/logout) | `dbops.sessioni_utente` | `session_audit_service` + auth views override | Pianificato |
| Request logging (chi chiama cosa) | `dbops.request_log` | `RequestLogMiddleware` | Pianificato |
| Token blacklist e revoca | SimpleJWT `token_blacklist` | Settings rotation + integrazione disabilitazione | Pianificato |

Queste estensioni sono non-breaking: nuove tabelle in `dbops`, nuovi middleware in `core`, override view JWT. Nessun contratto esistente viene modificato. Gli anelli esterni ne beneficiano automaticamente senza alcuna modifica al proprio codice.

### Stabilita'

Stabile. Modifiche solo per correzioni o estensioni non-breaking (nuove policy, nuovi middleware).

---

## Anello 1 — Dati Base e Configurazione

> Entita' di riferimento condivise da tutti i processi. Vocabolario comune del sistema.

| Componente | Tipo | DB | Backend | Descrizione |
|---|---|---|---|---|
| `config` | App Django | Operativo | Operativo | Stati, nazioni, UO, termini pagamento, priorita', canali |
| `anagrafiche` | App Django | Operativo | Operativo | Soggetti, indirizzi, contatti, risorse umane, emittenti fiscali |
| `catalogo` | App Django | Operativo | Operativo | Articoli, UoM, listini, distinte base |

### Cosa fornisce agli anelli esterni

- Entita' master referenziate via FK: soggetti, emittenti, risorse umane
- Tabelle config condivise: stati (doc fiscale, pratiche, flussi), priorita', canali
- Lookup e decodifiche centralizzate

### Stabilita'

Stabile. Cresce per aggiunta di nuove tabelle config (es. `config.canali_pratiche` aggiunta per pratiche) senza rompere quanto esistente.

---

## Anello 2 — Orchestrazione di Dominio

> Motore trasversale che gli anelli esterni usano per tracciare, orchestrare e automatizzare.

| Componente | Tipo | DB | Backend | Descrizione |
|---|---|---|---|---|
| `pratiche` | App Django | Operativo | Operativo | Workflow engine, giornale di bordo, generazione cross-pratica, handler dispatch |

### Cosa fornisce agli anelli esterni

- **Pratiche**: contenitore tracciabile per qualsiasi processo (onboarding cliente, gestione ordine, assistenza tecnica)
- **Flussi**: step operativi con prerequisiti, esiti, scadenze, assegnazione risorse
- **Giornale di bordo**: audit trail immutabile, append-only, con correlazione `tx_id`
- **Generazione cross-pratica**: un flusso completato puo' generare automaticamente nuove pratiche
- **Handler dispatch**: mapping `handler_key` → classe Python per automazione step
- **Canali**: visibilita' dei flussi su sorgenti esterne (WEB_CLIENTI, APP_TECNICA, PORTALE_FORNITORI)
- **API interna**: `pratiche_service` come facade per gli anelli esterni

### Perche' e' un anello separato (non anello 1)

`pratiche` non e' un dato di riferimento statico — e' un **motore di orchestrazione con stato e ciclo di vita**. Dipende da anello 1 (config, anagrafiche) per le FK, ma fornisce capacita' operative che gli anelli esterni consumano. E' il cuore operativo del sistema: ogni evento significativo (nuovo cliente, nuovo ordine, nuova assistenza) genera una pratica con il suo giornale.

### Perche' non e' anello 3 (processi)

Non e' un processo di business specifico (come vendite o acquisti). E' l'**infrastruttura di processo** che tutti i domini usano. E' al servizio dei processi, non un processo in se'.

### Stato sviluppo dettagliato

| Fase | Stato | Riferimento |
|---|---|---|
| DB-1..DB-7 | FATTO | Tabelle, funzioni, trigger, seed, test pgTAP |
| BE-1 Setup app | FATTO | Directory, apps.py, types.py, models.py |
| BE-2 Repository | FATTO | pratiche_repository.py, generazione_repository.py |
| BE-3 Services | FATTO | pratiche_service.py, generazione_service.py, handler_registry.py |
| BE-4 API | FATTO | views.py, urls_v1.py, 13 endpoint REST |
| BE-5 Test | FATTO | 63 test (38 service + 25 API) con mock |

Documentazione backend: [docs/it/backend/pratiche/index.md](backend/pratiche/index.md)

Piano esecutivo: [piano-gestione-pratiche.md](dev/work-in-progress/piano-gestione-pratiche.md)

---

## Anello 3 — Processi Operativi

> Cicli di business che usano anelli interni. Ogni processo e' autonomo ma condivide vocabolario e infrastruttura.

| Componente | Tipo | DB | Backend | Descrizione |
|---|---|---|---|---|
| `vendite` | App Django | Operativo | Operativo | Ciclo attivo: preventivi, ordini, DDT, fatture, pipeline fatturazione, lotti, commesse |
| `acquisti` | App Django | Operativo | Stub | Ciclo passivo: richieste offerta, ordini, DDT, fatture |
| `magazzino` | App Django | Operativo | Stub | Movimenti, giacenze, lotti, seriali |
| `pagamenti` | App Django | Operativo | Stub | Scadenze, riconciliazioni |
| `contabilita` | App Django | Operativo | Stub | Piano conti, registrazioni, partite |
| `storico` | App Django | Operativo | Stub | Audit temporale, storicizzazione |

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

| Area | Stato |
|---|---|
| Pipeline fatturazione | Operativo |
| Lotti massivi/giornalieri | Operativo |
| Registry task DB multi-dominio | Operativo |
| Dispatch task con implementation_key | Operativo |
| Runtime task tracing | Operativo |
| Builder XML SDI | In corso (payload pronto, generazione XML da fare) |
| Persistenza esito SDI | Da fare |
| Commesse (push, orchestrator, handlers) | Operativo |

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

---

## Evoluzione prevista

### Breve termine (marzo 2026)

- ~~Completamento BE-1..BE-5 per `pratiche`~~ — **FATTO** (4 marzo 2026)
- `pratiche` e' consumabile dagli anelli esterni (13 endpoint REST, 63 test)

### Medio termine

- Integrazione `vendite` → `pratiche`: eventi di vendita generano pratiche con giornale
- Integrazione `anagrafiche` → `pratiche`: onboarding cliente/fornitore tracciato
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
