# Guida — Processi pgAgent funzionali

> (latest review 2026-04-24)
>
> Destinatari: sviluppatori database, backend, analisti funzionali
>
> Questa guida cataloga i **job pgAgent di dominio** (business-driven):
> processi notturni/periodici che operano sui dati operativi per
> sincronizzare stato, chiudere finestre temporali, allineare flag
> governativi con le regole di workflow.
>
> Vedi anche:
>
> * [Estensione pgAgent](/postgresql/pgAgent) — concetti base, schedule, step, log
> * [Guida Tracciamento processi e job](/guide/Analisi-tracciamento-processi-e-job) — tre livelli di tracciamento (audit, job run log, task runs)
> * [Framework automazione DB](/guide/automazione-db) — automazioni dichiarative infrastrutturali
> * [linee-guida-sql §7c](/linee-guida-sql) — pattern "ciclo stato + finestra di validita'"

---

## Funzionale vs infrastrutturale

In Zero ERP convivono due tipologie di job pgAgent.

**Infrastrutturali** — non operano su dati di dominio, fanno manutenzione del DB:
applicazione policy indici FK, storicizzazione tecnica, cleanup framework
automazioni. Documentati in [framework automazione DB](/guide/automazione-db).

**Funzionali** — agiscono su entita' di dominio per mantenere la coerenza
del workflow di business (es. chiudere stati, disattivare utenti,
scadere finestre). Sono quelli di cui si occupa questa guida.

Ogni job funzionale rispetta il principio **"fonte di verita' =
dato operativo, job sincronizza flag derivati"**: il job non decide
la logica, applica il workflow gia' codificato nei trigger/funzioni.
Se il job non scatta (DB down, disabilitato), la logica operativa
basata sui dati primari (es. `validita @> oggi` per i listini) resta
corretta.

---

## Catalogo processi funzionali

| Job | Schedule | Scopo | Dominio | Migration |
|---|---|---|---|---|
| `sync_auth_user_expired_daily` | daily 06:00 | Disattiva `auth_user` per risorse umane con finestra temporale scaduta | anagrafiche | `85_pgagent/20260302-04-...` |
| `listini_versioni_close_scadute_daily` | daily 00:05 | Chiude versioni listino ATTIVA con `valido_al` scaduto | vendite | `85_pgagent/20260424-01-...` |

---

## Schede dettaglio

### `sync_auth_user_expired_daily`

* **Scopo**: sincronizzare `django.auth_user.is_active = false` per risorse umane con finestra `valido_dal/valido_al` scaduta (decommissionamento automatico).
* **Funzione chiamata**: `anagrafiche.fn_sync_auth_user_expired()`.
* **Schedule**: tutti i giorni alle `06:00`.
* **Classe job**: `Routine Maintenance`.
* **Idempotenza**: la funzione processa tutti gli `auth_user` con finestra scaduta; rieseguirla non produce effetti se gia' applicata.
* **Migration**: [85_pgagent/20260302-04-create-pgagent-job-sync-auth-user-expired-daily-mctit.yaml](/migrations_v2/85_pgagent/20260302-04-create-pgagent-job-sync-auth-user-expired-daily-mctit.yaml).
* **Tabelle coinvolte**: `anagrafiche.risorse_umane`, `anagrafiche.identita_digitali`, `django.auth_user`.

### `listini_versioni_close_scadute_daily`

* **Scopo**: portare a `stato = 'CHIUSA'` le versioni listino ATTIVA la cui finestra temporale e' gia' scaduta (`valido_al < CURRENT_DATE`).
* **Funzione chiamata**: `vendite.fn_listini_versioni_close_scadute()` — ritorna il numero di righe chiuse.
* **Schedule**: tutti i giorni alle `00:05` (subito dopo il cambio data; il ritardo stato ↔ realta' e' ~5 minuti).
* **Classe job**: `Routine Maintenance`.
* **Idempotenza**: la query UPDATE seleziona solo versioni ancora ATTIVA con `valido_al` scaduto; esecuzioni ripetute nella stessa giornata sono no-op.
* **Interazione con guard**: l'UPDATE attraversa il trigger `trg_listini_versioni_a10_guard_transizione_stato_upd` (vedi [linee-guida-sql §7c](/linee-guida-sql)) e lo soddisfa per costruzione — nessun bypass.
* **Effetto sulla UX**: fra `PATCH valido_al = oggi` e le 00:05 del giorno successivo la versione resta `ATTIVA` a livello `stato`. L'**applicabilita' operativa** (resolver prezzi) e' gia' scaduta perche' basata su `validita @> data`, non sullo stato.
* **Migration**: [85_pgagent/20260424-01-create-pgagent-job-listini-versioni-close-scadute-daily-mctit.yaml](/migrations_v2/85_pgagent/20260424-01-create-pgagent-job-listini-versioni-close-scadute-daily-mctit.yaml).
* **Tabelle coinvolte**: `vendite.listini_versioni`.
* **Tabella manuale**: [listini_versioni](/dbzero/vendite/tabelle/listini_versioni).

---

## Convenzioni di naming

* **Job name**: `<entita>_<azione>_<frequenza>` in snake_case, tutto minuscolo (es. `listini_versioni_close_scadute_daily`, `sync_auth_user_expired_daily`). Il nome e' usato come chiave per delete/replace nel changeSet.
* **Schedule name**: `<frequenza>_<ora>` (es. `daily_00_05`, `daily_06`).
* **Step name**: `run_<descrizione_azione>` (es. `run_listini_versioni_close_scadute`).
* **Migration file**: `YYYYMMDD-NN-create-pgagent-job-<job-name-kebab-case>-<author>.yaml` in `85_pgagent/`.

---

## Pattern raccomandato per nuovi job funzionali

1. **Funzione incapsulata in `20_code/<schema>/`**: il job non deve contenere SQL business inline. Creare `schema.fn_<operazione>()` che ritorna un conteggio o un JSON di risultato, richiamabile anche manualmente per test e recovery fuori schedulazione.
2. **Logica nel trigger, non nel job**: le regole (quali righe modificare, a quale condizione) vivono nei trigger/funzioni di dominio. Il job esegue UPDATE/SELECT che **attraversa** i guard e li soddisfa per costruzione. Evitare bypass via GUC o SECURITY DEFINER salvo necessita' dimostrata.
3. **Fonte di verita' = dato primario**: il flag sincronizzato (es. `stato`, `is_active`) **non** deve essere usato dalla logica operativa. Il resolver/consumer legge il dato primario (date, ranges, eventi) e lo stato resta "cosmetico" per UI/reportistica. Se il job salta, la logica operativa resta corretta.
4. **Idempotenza**: la funzione deve essere sicura da eseguire N volte (selezioni condizionate, nessun side-effect duplicato).
5. **Ordinaria: `Routine Maintenance`**. Nuove classi solo se serve separazione operativa (es. priorita' diverse).
6. **ChangeSet con `runOnChange: true` + `validCheckSums: [ANY]`**: permette riesecuzione a modifica dello YAML (ricrea il job).
7. **PreCondition `pg_extension = 'pgagent'`** con `onFail: MARK_RAN, onError: CONTINUE`: consente deploy in ambienti dove pgAgent non e' installato (es. CI) senza far fallire il changelog.
8. **`DELETE FROM pgagent.pga_job WHERE jobname = '<nome>'`** all'inizio del DO block: idempotenza del changeSet (ogni riesecuzione ricrea il job pulito, senza residui schedule/step).

---

## Dove vengono tracciate le esecuzioni

* **pgAgent interno**: `pgagent.pga_joblog` (esito esecuzione job) e `pgagent.pga_jobsteplog` (esito singolo step).
* **Log applicativo**: se la funzione chiamata esegue `script.fn_log_and_raise_error` o `script.fn_log_error_only` in caso di problemi, il log finisce in `dbops.error_log` via dblink.
* **Framework job run log**: `maintenance.job_run_log` — usato dai wrapper `maintenance.run_and_log(...)` per i job che adottano quel pattern (oggi principalmente i job infrastrutturali).

Per i job funzionali elencati qui, il tracciamento primario e' `pga_joblog`. L'adozione del wrapper `maintenance.run_and_log` e' una best practice futura per uniformare il log.

---

## Quando NON usare un job pgAgent

Un job notturno e' appropriato quando:

* l'allineamento puo' essere **asincrono** (ritardo ore accettabile);
* la logica operativa **non dipende** dal flag sincronizzato (altrimenti diventa un single point of failure);
* l'operazione e' **batch-friendly** (UPDATE massivo, nessun lock lungo).

Se la coerenza deve essere **immediata** (es. un flag che il resolver legge davvero), il pattern corretto e' **trigger sincrono** o **colonna generata**, non job notturno.

Se la logica e' **event-driven** (reagisce a un INSERT/UPDATE specifico), usare trigger o pipeline task, non scheduled job.
