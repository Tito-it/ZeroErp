# Guida Tecnica - Fatturazione (processo end-to-end)

> Destinatari: analisti funzionali, sviluppatori backend e database di Zero ERP
>
> Vedi anche:
>
> * [Guida API Commesse](/guide/gestione-commesse)
> * [vendite.commesse](/dbzero/vendite/tabelle/commesse)
> * [vendite.stati_commessa](/dbzero/vendite/tabelle/stati_commessa)
> * [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)
> * [vendite.fn_emit_attivita_fatturabili_da_commessa](/dbzero/vendite/funzioni/fn_emit_attivita_fatturabili_da_commessa)
> * [vendite.fatture](/dbzero/vendite/tabelle/fatture)
> * [vendite.fatture_righe](/dbzero/vendite/tabelle/fatture_righe)
> * [vendite.event_log](/dbzero/vendite/tabelle/event_log)
> * [Messaggi di errore e log](/guide/Messaggi-di-Errore-e-Generazione-Log)

---

## Introduzione

Il processo di fatturazione e` stato ristrutturato.

Modello attuale:

1. Le sorgenti business NON alimentano direttamente `attivita_fatturabili`.
2. Tutte le sorgenti passano da `commesse` / `commesse_attivita`.
3. Le righe commessa idonee vengono emesse in `attivita_fatturabili` tramite funzioni dedicate.
4. La pipeline fatturazione a lotti opera poi su `attivita_fatturabili` per produrre ed emettere le fatture.

In sintesi: la commessa e` il livello di governo operativo prima della fatturazione fiscale.

---

## Architettura logica

```mermaid
flowchart TD
  A[Sorgenti: preventivi ordini contratti ddt consumi] --> B[Push commesse]
  B --> C[vendite.commesse]
  C --> D[vendite.commesse_attivita]
  D --> E[Emissione da commessa]
  E --> F[vendite.attivita_fatturabili]
  F --> G[Pipeline fatturazione lotti]
  G --> H[vendite.fatture_righe]
  G --> I[vendite.fatture]
  I --> L[DEFINITIVA numerazione]
  L --> M[INVIATA SDI output]
```

### Ruolo dei layer

Il processo e` suddiviso su tre layer con responsabilita` distinte:

| Layer             | Responsabilita`                                                | Esempi                                                                              |
| ----------------- | -------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| **PostgreSQL**    | Stato, regole di dominio, vincoli, log funzionali              | `fn_get_or_create_commessa`, `fn_set_fatturazione_lotto_stato`, trigger append-only |
| **Python/Django** | Orchestrazione, sequencing, fan-out, gestione errori, API REST | `CommessaPushOrchestrator`, `LottoPipelineRunner`, `PipelineStepExecutor`           |
| **API REST**      | Esposizione endpoint, validazione input, idempotenza request   | `/api/vendite/run-lotto-pipeline/`, `/api/vendite/run-commesse-push/`               |

Principio generale: il database e` l'autorita` su stato e regole; Python orchestra il flusso e gestisce le eccezioni; l'API espone e protegge.

### Componenti Python principali

```text
apps/vendite/
  api/views.py                         # Endpoint REST
  services/
    pipeline_service.py                # Entrypoint facade (run_lotto_pipeline)
    pipeline_runner.py                 # LottoPipelineRunner — orchestratore pipeline lotti
    pipeline_step_executor.py          # PipelineStepExecutor — esecuzione singolo step
    pipeline_error_logger.py           # PipelineErrorLogger — dual-log (error_log + dominio)
    commesse_push_orchestrator.py      # CommessaPushOrchestrator — fan-out push sorgenti
    commesse_source_handlers.py        # BaseSourceHandler + handler concreti per sorgente
    lotto_segnalazioni_service.py      # Valutazione segnalazioni blocco lotto
  db/
    pipeline_repository.py             # Repository DB pipeline (stato, log, event_log)
    commesse_repository.py             # Repository DB commesse (CRUD, push log, event_log)
```

---

## Schema ER (minimale)

```mermaid
erDiagram
  COMMESSE ||--o{ COMMESSE_ATTIVITA : "commesse.id = commesse_attivita.commessa_id"
  COMMESSE ||--o{ COMMESSE_SORGENTI : "commesse.id = commesse_sorgenti.commessa_id"
  COMMESSE ||--o{ ATTIVITA_FATTURABILI : "commesse.id = attivita_fatturabili.commessa_id"
  COMMESSE_ATTIVITA ||--o{ ATTIVITA_FATTURABILI : "commesse_attivita.id = attivita_fatturabili.commessa_attivita_id"

  COMMESSE {
    bigint id PK
    bigint stato_commessa_id FK
  }
  COMMESSE_ATTIVITA {
    bigint id PK
    bigint commessa_id FK
    varchar segment_key
  }
  COMMESSE_SORGENTI {
    bigint id PK
    bigint commessa_id FK
    bigint sorgente_tipo_id
    text sorgente_uid
  }
  ATTIVITA_FATTURABILI {
    bigint id PK
    bigint commessa_id FK
    bigint commessa_attivita_id FK
    bigint sorgente_tipo_id
    uuid sorgente_uid
  }
```

---

## Tabelle core

### Livello commessa

* [vendite.commesse](/dbzero/vendite/tabelle/commesse)
* [vendite.stati_commessa](/dbzero/vendite/tabelle/stati_commessa)
* [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)
* [vendite.commesse_sorgenti](/dbzero/vendite/tabelle/commesse_sorgenti)
* [vendite.commesse_push_log](/dbzero/vendite/tabelle/commesse_push_log)

### Livello fatturazione

* [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)
* [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)
* [vendite.fatture](/dbzero/vendite/tabelle/fatture)
* [vendite.fatture_righe](/dbzero/vendite/tabelle/fatture_righe)
* [vendite.fatture_riepiloghi_iva](/dbzero/vendite/tabelle/fatture_riepiloghi_iva)
* [vendite.fatture_scadenze](/dbzero/vendite/tabelle/fatture_scadenze)

---

## Fase 1 - Push sorgenti su commesse

Scopo: costruire/aggiornare le commesse e le relative righe tecniche da emettere.

### Orchestrazione push (Python)

L'ingestione e` gestita da `CommessaPushOrchestrator` che:

1. Acquisisce un advisory lock PostgreSQL per evitare run concorrenti.
2. Esegue in sequenza gli handler registrati (uno per sorgente: preventivi, ordini, consumi, ...).
3. Isola gli errori per handler: un fallimento non blocca gli altri.
4. Scrive il log in `commesse_push_log` e emette eventi su `event_log` (`PUSH_STARTED`, `PUSH_COMPLETED`).

Ogni handler (`BaseSourceHandler`) implementa:

* `fetch_pushable_rows()` — recupera righe sorgente da sincronizzare
* `_expand_rows()` — trasforma una riga sorgente in una o piu` righe commessa
* `_process_rows()` — risolve/crea commessa, linka sorgente, batch upsert righe

### Funzioni DB

* [vendite.fn_get_or_create_commessa](/dbzero/vendite/funzioni/fn_get_or_create_commessa)
* [vendite.fn_upsert_commessa_attivita](/dbzero/vendite/funzioni/fn_upsert_commessa_attivita)
* [vendite.fn_batch_upsert_commessa_attivita](/dbzero/vendite/funzioni/fn_batch_upsert_commessa_attivita)
* [vendite.fn_link_commessa_sorgente](/dbzero/vendite/funzioni/fn_link_commessa_sorgente)
* [API run_commesse_push](/backend/vendite/manual/api_run_commesse_push)

### Regole principali

* match/creazione commessa su perimetro BA/utility/policy/emittente/competenza;
* idempotenza riga su `(commessa_id, segment_key)`;
* batch upsert: N righe in una singola chiamata DB per performance;
* validazioni forti su quantita`, prezzo e stato commessa modificabile;
* nessun bypass diretto sorgente -> `attivita_fatturabili`.

---

## Fase 2 - Governo stato commessa

Le operazioni sono governate da `vendite.stati_commessa`:

* `modificabile`: abilita upsert su `commesse_attivita`;
* `emittibile`: abilita discovery per emissione verso AF;
* `chiude_commessa`: impedisce riuso della commessa.

Funzioni di supporto:

* [vendite.fn_get_commessa_stato](/dbzero/vendite/funzioni/fn_get_commessa_stato)
* [vendite.fn_list_commessa_attivita](/dbzero/vendite/funzioni/fn_list_commessa_attivita)
* [vendite.fn_list_commesse_emittibili](/dbzero/vendite/funzioni/fn_list_commesse_emittibili)

---

## Snapshot pricing su commessa e propagazione ad AF

Le righe `commesse_attivita` portano con sé lo **snapshot del prezzo** calcolato al push dal resolver v5. Questa sezione copre la parte prezzi del modello fatturazione; per il dettaglio del calcolo, dei 3 stadi (promo/contratto/categoria) e delle autorizzazioni L1/L2/L3 vedere la [guida Gestione Listini e Pricing](/guide/gestione-listini).

### Campi pricing rilevanti

Oltre a quantità, UOM e competenza, la riga `vendite.commesse_attivita` include:

Snapshot resolver (calcolato al push):

* `prezzo_snapshot` — prezzo corrente della riga
* `prezzo_base_snapshot` — prezzo base di listino prima della variazione
* `origine_prezzo` — `PROMO`, `CONTRATTO_OVERRIDE`, `CONTRATTO_LISTINO`, `CATEGORIA`, `MANUALE`
* `tipo_variazione_applicata` + `valore_variazione_applicata`
* `listino_versione_id`, `listino_riga_id` — FK alla riga di listino usata
* `promo_id`, `contratto_id`, `categoria_cliente_id_snapshot`, `classe_utenza_id_snapshot` — FK congelate al momento del calcolo

Flag operativi post-resolver:

* `prezzo_bloccato` — se `TRUE`, il prezzo è bloccato da override manuale e il riallineamento automatico lo salta
* `prezzo_da_riallineare` — flag di segnalazione per dashboard "prezzi da riallineare"
* `pricing_mode` — predisposizione futura (`FIXED`, `FORMULA`, `SCAGLIONI`); oggi solo `FIXED` è operativo

### Ciclo di vita post-push

Una volta sulla riga commessa, il prezzo può essere **ricalcolato, bloccato o sbloccato** tramite le operazioni dedicate del servizio vendite (vedi [guida listini §7](/guide/gestione-listini#7-ciclo-di-vita-del-prezzo-sulla-riga-commessa)):

* `POST .../attivita/<id>/riallinea-prezzo/` — ricalcola dal resolver; guardia su cambio versione listino; errore se `prezzo_bloccato=TRUE`
* `POST .../attivita/<id>/variazione-prezzo-eccezionale/` — override manuale con motivo obbligatorio; imposta `prezzo_bloccato=TRUE`
* `POST .../attivita/<id>/sblocca-prezzo/` — rimuove il blocco e ricalcola dal resolver

Tutte queste operazioni sono ammesse solo su commesse `modificabile` e righe non ancora fatturate.

### Propagazione a `attivita_fatturabili`

All'emissione (`fn_emit_attivita_fatturabili_da_commessa`) i campi snapshot e `prezzo_bloccato` vengono propagati sulla riga AF. Conseguenze operative:

* i task pipeline fatturazione **rispettano** `prezzo_bloccato=TRUE`: un prezzo da override manuale non viene riscritto da eventuali ricalcoli massivi in fase di lotto;
* lo snapshot resolver resta tracciabile fino a `fatture_righe`, utile per audit e contestazioni (origine prezzo, FK listino/contratto/promo, variazione applicata).

---

## Fase 3 - Emissione da commessa a attivita_fatturabili

Scopo: trasferire le righe `commesse_attivita` idonee in `attivita_fatturabili`.

### Orchestrazione emissione (Python)

L'emissione non e` un job autonomo: e` un **task pipeline** eseguito come primo
step del lotto (tipicamente DRAFT), gestito da `PipelineStepExecutor`:

1. Il task `pull_attivita_da_commessa_default` viene invocato dal runner.
2. L'executor chiama `commesse_repository.list_commesse_emittibili()` per scoprire
   le commesse pronte nel perimetro del lotto (competenza, utility, BA, emittente).
3. Per ogni commessa trovata chiama `commesse_repository.emit_attivita_fatturabili()`.
4. La funzione SQL sottostante trasferisce le righe e restituisce contatori
   (`inserted_rows`, `updated_rows`, `skipped_rows`).

Componenti Python:

| Componente | File | Ruolo |
| --- | --- | --- |
| Task handler | `pipeline_step_executor.py` (`_handle_pull_attivita_da_commessa_task`) | Orchestrazione discovery + emit per lotto |
| Discovery | `commesse_repository.py` (`list_commesse_emittibili`) | Trova commesse pronte per emissione |
| Emit wrapper | `commesse_repository.py` (`emit_attivita_fatturabili`) | Wrappa la fn SQL, restituisce `CommessaEmitResult` |

### Funzioni DB emissione

* [vendite.fn_emit_attivita_fatturabili_da_commessa](/dbzero/vendite/funzioni/fn_emit_attivita_fatturabili_da_commessa)
* [vendite.fn_list_commesse_emittibili](/dbzero/vendite/funzioni/fn_list_commesse_emittibili)

### Regole emissione

* sorgente AF forzata a tipo `COMMESSA`;
* mapping deterministico di `segment_key` su identificativo sorgente AF (`md5 → UUID`);
* idempotenza su chiave sorgente in AF (`sorgente_tipo_id`, `sorgente_uid`);
* blocco aggiornamento se la riga AF risulta gia` fatturata;
* aggiornamento stato righe commessa emesse (`stato_emissione = EMESSA`);
* supporto `dry_run` e filtro `only_approved` sulla funzione SQL.

---

## Fase 4 - Pipeline fatturazione a lotti

Dopo la fase commesse, la fatturazione resta governata dal dominio lotti.

### Orchestrazione pipeline (Python)

Il flusso e` orchestrato da `LottoPipelineRunner`:

1. Risolve o crea il lotto (`get_or_create_lotto`).
2. Verifica precondizioni: lotto non gia` in esecuzione, nessuna segnalazione critica attiva.
3. Imposta stato `IN_ESECUZIONE` e emette `PIPELINE_STARTED` su `event_log`.
4. Esegue un singolo step per run (modalita` operativa: avanzamento incrementale).
5. Per ogni step: aggiorna stato doc, logga fase, delega a `PipelineStepExecutor`, emette `STEP_COMPLETED`.
6. Se tutti gli step completano: stato `COMPLETATO`, emette `PIPELINE_COMPLETED`.
7. In caso di errore: stato `ERRORE`, dual-log (`error_log` tecnico + `event_log` di dominio), emette `PIPELINE_ERROR`.

Componenti:

* `LottoPipelineRunner` — orchestra il flusso, gestisce retry/rerun su lotti in errore.
* `PipelineStepExecutor` — esegue il singolo step con risoluzione task da registry.
* `PipelineErrorLogger` — dual-log: errore tecnico su `dbops.error_log` + log funzionale su tabelle dominio.
* `LottoSegnalazioniService` — valuta se il lotto ha segnalazioni bloccanti prima dell'avanzamento.

### Modello lotti (visione sintetica)

1. Un lotto (`fatturazione_lotti`) definisce perimetro operativo (competenza, utility, tipo documento, BA/emittente).
2. Gli step sono configurati in `fatturazione_pipeline` e risolti con fallback su `tipo_lotto`, `utility_id`, `tipo_doc_fiscale_id`.
3. Il runner esegue i task di step e traccia i tentativi in `fatturazione_lotti_task_runs`.
4. Le fatture generate sono collegate al lotto tramite `fatturazione_lotti_fatture`.

### Schema ER (pipeline lotti)

```mermaid
erDiagram
  ATTIVITA_FATTURABILI_LOTTI ||--o{ ATTIVITA_FATTURABILI : "lotto_attivita_id"
  ATTIVITA_FATTURABILI }o--|| COMMESSE_ATTIVITA : "commessa_attivita_id"
  FATTURAZIONE_LOTTI ||--o{ FATTURAZIONE_LOTTI_FATTURE : "lotto_id"
  FATTURE ||--o{ FATTURAZIONE_LOTTI_FATTURE : "fattura_id"
  FATTURAZIONE_PIPELINE ||--o{ FATTURAZIONE_LOTTI_TASK_RUNS : "pipeline_id"
  FATTURAZIONE_LOTTI ||--o{ FATTURAZIONE_LOTTI_TASK_RUNS : "lotto_id"

  COMMESSE_ATTIVITA {
    bigint id PK
    bigint commessa_id FK
    varchar segment_key
    varchar stato_emissione
  }
  ATTIVITA_FATTURABILI {
    bigint id PK
    bigint lotto_attivita_id FK
    bigint commessa_id FK
    bigint commessa_attivita_id FK
    varchar stato_esecuzione
  }
  ATTIVITA_FATTURABILI_LOTTI {
    bigint id PK
    varchar codice
    date competenza_mese
    bigint utility_id FK
    varchar stato_lotto
  }
  FATTURAZIONE_LOTTI {
    bigint id PK
    varchar tipo_lotto
    bigint stato_doc_fiscale_id FK
    varchar stato_lotto
  }
  FATTURAZIONE_PIPELINE {
    bigint id PK
    varchar tipo_lotto
    bigint stato_doc_fiscale_id FK
    jsonb processi
    jsonb rollback
  }
  FATTURAZIONE_LOTTI_TASK_RUNS {
    bigint id PK
    bigint lotto_id FK
    bigint pipeline_id FK
    varchar task_code
    smallint tentativo
    varchar task_stato
  }
  FATTURAZIONE_LOTTI_FATTURE {
    bigint id PK
    bigint lotto_id FK
    bigint fattura_id FK
  }
  FATTURE {
    bigint id PK
  }
```

### Tabelle core del modello lotti

* [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)
* [vendite.fatturazione_pipeline](/dbzero/vendite/tabelle/fatturazione_pipeline)
* [vendite.fatturazione_lotti_task_runs](/dbzero/vendite/tabelle/fatturazione_lotti_task_runs)
* [vendite.fatturazione_pipeline_task_policy](/dbzero/vendite/tabelle/fatturazione_pipeline_task_policy)
* [vendite.fatturazione_lotti_fatture](/dbzero/vendite/tabelle/fatturazione_lotti_fatture)

### Funzioni chiave pipeline lotti

* [vendite.fn_resolve_fatturazione_pipeline_step](/dbzero/vendite/funzioni/fn_resolve_fatturazione_pipeline_step)
* [vendite.fn_list_fatturazione_pipeline_steps](/dbzero/vendite/funzioni/fn_list_fatturazione_pipeline_steps)
* [vendite.fn_set_fatturazione_lotto_stato](/dbzero/vendite/funzioni/fn_set_fatturazione_lotto_stato)
* [backend.execute_pipeline_step](/backend/vendite/funzioni/fn_execute_pipeline_step)
* [backend.run_lotto_pipeline](/backend/vendite/funzioni/run_lotto_pipeline)
* [vendite.fn_start_lotto_task_run](/dbzero/vendite/funzioni/fn_start_lotto_task_run)
* [vendite.fn_complete_lotto_task_run](/dbzero/vendite/funzioni/fn_complete_lotto_task_run)
* [vendite.fn_fail_lotto_task_run](/dbzero/vendite/funzioni/fn_fail_lotto_task_run)
* [vendite.fn_cancel_lotto_task_run](/dbzero/vendite/funzioni/fn_cancel_lotto_task_run)
* [vendite.fn_list_lotto_task_runs](/dbzero/vendite/funzioni/fn_list_lotto_task_runs)

### Step operativi tipici (massivo)

1. DRAFT: selezione/preparazione delle attivita` da fatturare.
2. EMESSA: generazione documento e task pre-fiscali.
3. DEFINITIVA: numerazione documento.
4. INVIATA: preparazione/invio su canale esterno (es. SDI).

### Stato documentale della fattura: segue lo step (invariante)

Lotto **e** fatture condividono `config.stati_doc_fiscale` ma con **macchine a stati
distinte** (`config.stati_doc_fiscale_transizioni`, colonne `solo_lotto` / `solo_fattura`).
Lo stato della **fattura** segue lo `stato_doc_fiscale_id` dello **step** di pipeline: a ogni
avanzamento di step le fatture del lotto vengono allineate (`fn_sync_lotto_fatture_stato`).

**Invariante (imposto dalla matrice + `trgfn_fatture_guard_stato`)**: la fattura deve passare
per **EMESSA(2) prima di DEFINITIVA(8)** — `1→2→8`, **mai** `1→8`. Semantica: non si assegna
un numero fiscale (DEFINITIVA) a una fattura di cui non si è certificata l'IVA (EMESSA).

* **MASSIVO**: la fattura fa `1→2→8→3`. Lo step EMESSA calcola l'IVA (rifacibile: ha rollback
  `reset_lotto_draft`), poi DEFINITIVA numera.
* **GIORNALIERO**: stessa sequenza `1→2→8→3` a livello sia di lotto sia di fattura. L'IVA è già
  calcolata alla nascita del documento, quindi lo step EMESSA giornaliero non ha task
  (`processi=[]`): serve solo a portare lotto e fattura a EMESSA prima della numerazione,
  garantendo lo stesso invariante.

> Rollback: ammesso solo da stati **pre-fiscali** (DRAFT/EMESSA). `fn_reset_lotto_draft`
> **cancella** le fatture pre-fiscali del lotto (non numerate); le fiscali (DEFINITIVA in poi)
> sono rifiutate.

### Rollback di step (`fatturazione_pipeline.rollback`)

Ogni riga di `fatturazione_pipeline` ha due array JSONB paralleli:

* **`processi`** — task da eseguire in avanzamento (forward);
* **`rollback`** — task da eseguire quando il lotto torna a questo step (cleanup).

La fn SQL `fn_resolve_fatturazione_pipeline_step(p_rollback => true)` restituisce
i task di rollback al posto di quelli forward. Il `PipelineStepExecutor` chiama
`get_step_processes(rollback=True)` e li esegue con lo stesso meccanismo dei task normali.

**Quando scatta il rollback:**

Il rollback e` manuale (richiesto dall'operatore o dall'API `reset_lotto`) oppure
automatico se la pipeline ha `meta.auto_step_rollback = true`. Non scatta mai
spontaneamente su errore: un errore lascia il lotto in stato `ERRORE` e serve
un rerun esplicito.

**Esempio concreto (seed):**

| Step   | `processi`                                               | `rollback`           |
| ------ | -------------------------------------------------------- | -------------------- |
| DRAFT  | `select_attivita`, `generate_fatture_righe`              | `[]` (nessuno)       |
| EMESSA | `genera_fondi`, `applica_fondi`, `ricalcola_iva`         | `reset_lotto_draft`  |

In questo caso, se un lotto MASSIVO in stato EMESSA deve tornare a DRAFT,
il sistema esegue il task `reset_lotto_draft` che pulisce fondi, righe IVA
e totali generati dallo step forward.

**Vincoli:**

* Il rollback e` ammesso solo per lotti MASSIVO in stati pre-fiscali (tipicamente DRAFT ed EMESSA).
* Dopo la DEFINITIVA (numerazione fiscale) il rollback globale non e` piu` possibile;
  il sistema usa resume per fattura.
* Se `rollback` e` `[]` (array vuoto), lo step non prevede operazioni di pulizia.

### Regole operative del modello lotti

1. Lo step effettivo viene risolto con fallback configurativo (`utility + tipo_doc`, `utility`, `tipo_doc`, globale).
2. Le transizioni tecniche del lotto sono governate da `fn_set_fatturazione_lotto_stato`.
3. Ogni task-run deve essere tracciato con `tentativo` ed esito (`IN_ESECUZIONE`, `COMPLETATO`, `ERRORE`, `ANNULLATO`).
4. Le policy runtime task (resume/reset/annullabilita`) sono esterne alla sequenza step e risiedono in `fatturazione_pipeline_task_policy`.
5. I task devono lavorare con input centrato sul `lotto_id`, recuperando il resto dal contesto lotto.

### Naming runtime (Python)

Per evitare ambiguita` tra SQL legacy e runtime applicativo:

* nel runtime Python usare naming senza prefissi DB (`run_lotto_pipeline`, `execute_pipeline_step`, `run_commesse_push`);

* la semantica operativa corrente e` governata dai service Django.

---

## Dashboard operative

Vista funzionale consigliata (anche in singola UI a sezioni):

1. Input/Push Commesse: ingestione sorgenti e verifica errori push.
2. Gestione Commesse: stato testata, righe, approvazioni e anomalie.
3. Emissione da Commesse: pull verso `attivita_fatturabili`.
4. Emissione Fatture: gestione lotti, numerazione, invio.

---

## Gestione errori e osservabilita`

Obiettivo: garantire diagnosi rapida e riesecuzione sicura senza perdita di coerenza.

### Tre livelli di log

Il sistema utilizza tre livelli di logging complementari, ciascuno con finalita` distinta:

| Log                | Scopo                                    | Risponde a                            | Tabella                                                      |
| ------------------ | ---------------------------------------- | ------------------------------------- | ------------------------------------------------------------ |
| **Error log**      | Eccezioni tecniche con catalogo messaggi | "Cosa e` andato storto?"              | `dbops.error_log`                                            |
| **Event log**      | Timeline eventi di dominio per entita`   | "Cosa e` successo al lotto/commessa?" | `vendite.event_log`                                          |
| **Log funzionali** | Dettaglio operativo fase/fattura/push    | "Qual e` l'esito di questa fase?"     | `fatturazione_lotti_log`, `fatture_log`, `commesse_push_log` |

### vendite.event_log — timeline unificata

Tabella append-only (UPDATE/DELETE bloccati da trigger) che registra tutti gli eventi di dominio:

* **Domini**: `PIPELINE`, `COMMESSE`, `SDI`, `FATTURE`
* **Entita`**: `LOTTO`, `FATTURA`, `COMMESSA`, `TASK_RUN`
* **Severita`**: `INFO`, `WARN`, `ERROR`
* **Correlazione**: `correlation_id` (UUID) lega eventi dello stesso batch/job

### Come funziona il correlation_id

Il `correlation_id` consente di ricostruire la timeline completa di un singolo
run pipeline, collegando tutti gli eventi (start, step, completamento, errore)
in un'unica traccia.

**Ciclo di vita:**

1. Il chiamante (API o scheduler) passa un `lock_batch_id` (UUID) nella request.
2. `LottoPipelineRunner` lo estrae dal contesto lotto e lo usa come `correlation_id`.
3. Ogni chiamata a `fn_log_event()` lo riceve e lo persiste in `event_log`.
4. Se non fornito dal chiamante, il campo resta `NULL` (eventi non correlati).

**Query di debug:**

```sql
-- Timeline completa di un run pipeline
SELECT event_time, domain, event_code, severity, entity_type, entity_id, payload
FROM vendite.event_log
WHERE correlation_id = '<uuid-del-lock-batch>'
ORDER BY event_time;
```

**Stato attuale e limiti:**

* Il runner propaga il correlation_id a tutti e 4 gli eventi pipeline
  (`PIPELINE_STARTED`, `STEP_COMPLETED`, `PIPELINE_COMPLETED`, `PIPELINE_ERROR`).
* Il `PipelineStepExecutor` e i singoli `task_run` non ricevono ancora il
  correlation_id — la correlazione a livello task va ricostruita tramite
  `lotto_id` + `event_time`.
* Il push commesse (`CommessaPushOrchestrator`) non popola il correlation_id.

Eventi emessi dal backend:

| Dominio  | event_code           | Emesso da                  | Quando                                    |
| -------- | -------------------- | -------------------------- | ----------------------------------------- |
| PIPELINE | `PIPELINE_STARTED`   | `LottoPipelineRunner`      | Avvio pipeline lotto                      |
| PIPELINE | `STEP_COMPLETED`     | `LottoPipelineRunner`      | Completamento singolo step                |
| PIPELINE | `PIPELINE_COMPLETED` | `LottoPipelineRunner`      | Pipeline lotto completata                 |
| PIPELINE | `PIPELINE_ERROR`     | `LottoPipelineRunner`      | Errore pipeline (severity ERROR)          |
| COMMESSE | `PUSH_STARTED`       | `CommessaPushOrchestrator` | Avvio push sorgenti                       |
| COMMESSE | `PUSH_COMPLETED`     | `CommessaPushOrchestrator` | Push completato (WARN se parziale/errore) |

Funzione DB: `vendite.fn_log_event()` — interfaccia unificata chiamata dai repository Python.

### Regole operative

1. Le funzioni DB devono alzare errori strutturati tramite `script.fn_log_and_raise_error`.
2. Gli errori di validazione input devono essere distinti da errori runtime/transazionali.
3. Ogni run push/emissione deve produrre log di esito con contatori (`created`, `updated`, `skipped`, `errors`).
4. I servizi backend devono propagare un envelope errore coerente verso API.
5. I servizi Python emettono eventi di dominio su `event_log` nei punti chiave di inizio/fine/errore.

### Riferimenti

* [vendite.event_log](/dbzero/vendite/tabelle/event_log)
* [vendite.fn_log_event](/dbzero/vendite/funzioni/fn_log_event)
* [Messaggi di errore e log](/guide/Messaggi-di-Errore-e-Generazione-Log)
* [vendite.commesse_push_log](/dbzero/vendite/tabelle/commesse_push_log)
* [API run_commesse_push](/backend/vendite/manual/api_run_commesse_push)

---

## Concorrenza e idempotenza

Obiettivo: evitare duplicazioni o race condition su push ed emissione.

Regole tecniche:

1. Creazione/riuso commessa serializzata con advisory lock in `fn_get_or_create_commessa`.
2. Upsert righe commessa idempotente su `(commessa_id, segment_key)`.
3. Emissione verso AF idempotente su chiave sorgente (`sorgente_tipo_id`, `sorgente_uid`).
4. Se una riga AF risulta gia` fatturata, l'update deve essere bloccato.
5. Endpoint di orchestrazione protetti da `Idempotency-Key`.

---

## Scheduling e orchestrazione

Il flusso e` pensato per esecuzione schedulata e on-demand.

L'orchestrazione runtime e` applicativa (Python/Django): il database mantiene stato, regole e log di dominio.

### Job e classi orchestranti

| Job                   | Classe Python                                                     | Protezione concorrenza              | Frequenza tipica            |
| --------------------- | ----------------------------------------------------------------- | ----------------------------------- | --------------------------- |
| Push commesse         | `CommessaPushOrchestrator`                                        | Advisory lock PostgreSQL            | Alta (minuti)               |
| Emissione da commesse | `PipelineStepExecutor` (task `pull_attivita_da_commessa_default`) | Stato lotto `IN_ESECUZIONE` + guard | Integrata in pipeline lotto |
| Pipeline lotti        | `LottoPipelineRunner`                                             | Stato lotto `IN_ESECUZIONE` + guard | Batch controllato           |

### Guardrail operativi

* evitare sovrapposizione di job sullo stesso perimetro BA/utility/competenza;
* `CommessaPushOrchestrator`: advisory lock impedisce run concorrenti (stato `SKIPPED` se lock non acquisito);
* `LottoPipelineRunner`: lotto in `IN_ESECUZIONE` rifiuta nuovo avvio (`E_PIPELINE_LOTTO_IN_ESECUZIONE`);
* prevedere retry controllato solo su step idempotenti;
* mantenere la policy di retry/backoff nel layer orchestratore Python (non nelle funzioni SQL);
* monitorare timeline `event_log` per identificare run bloccati o anomali.

---

## Volumetrie e performance

Per ambienti ad alto volume, adottare queste linee guida:

1. Eseguire push/emissione in chunk (`limit/offset` o finestre per ID).
2. Limitare il perimetro per competenza, BA, utility, emittente.
3. Monitorare tempi medi per fase e cardinalita` righe processate.
4. Verificare periodicamente piani query e indici su tabelle `commesse_*` e `attivita_fatturabili`.
5. Definire soglie operative per split automatico dei lotti massivi.

KPI minimi:

* righe push/minuto
* righe emesse/minuto
* percentuale scarti/errori
* tempo medio run per fase

---

## Checklist pre-esecuzione

1. Sorgenti attive e coerenti in `config.sorgenti` (ambito push commessa).
2. Funzioni commessa installate/allineate:
   * `fn_get_or_create_commessa`
   * `fn_upsert_commessa_attivita`
   * `fn_list_commesse_emittibili`
   * `fn_emit_attivita_fatturabili_da_commessa`
3. Seed/lookup stati commessa coerente (`vendite.stati_commessa`).
4. Pipeline lotti fatturazione configurata (`vendite.fatturazione_pipeline`).
5. Transizioni stati documento configurate in `config.stati_doc_fiscale_transizioni`.
6. Task registry DBOps coerente con i task fatturazione effettivamente abilitati.

---

## Query rapide di controllo

```sql
-- Commesse emittibili nel mese
SELECT *
FROM vendite.fn_list_commesse_emittibili(
  p_competenza_mese => DATE '2026-02-01',
  p_limit => 100
);

-- Righe di una commessa non ancora emesse
SELECT *
FROM vendite.fn_list_commessa_attivita(
  p_commessa_id => 12345,
  p_stato_emissione => 'NON_EMESSA',
  p_limit => 200,
  p_offset => 0
);

-- Step pipeline lotto per tipo MASSIVO
SELECT stato_doc_fiscale_id, descrizione, ordine
FROM vendite.fn_list_fatturazione_pipeline_steps('MASSIVO', 1, 20);
```

---

## Risultato atteso

Il processo risulta separato in due livelli chiari:

* livello business-operativo: sorgenti -> commesse -> commesse_attivita;
* livello fiscale-documentale: attivita_fatturabili -> lotti -> fatture.

Questa separazione migliora controllo, idempotenza e tracciabilita` dei flussi.
