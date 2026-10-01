# Guida — Processi pgAgent funzionali

> (latest review 06-09-2026)
>
> Destinatari: sviluppatori database, backend, analisti funzionali
>
> Questa guida è l'**elenco dei lavori a orario**: quali esistono, quando
> partono, che cosa fanno, come se ne aggiunge uno.
>
> 🔴 **Dal 06-09-2026 non è più qui che si decide la natura di un lavoro.**
> La divisione «funzionale / infrastrutturale» che questa guida usava è stata
> sostituita da tre nature dichiarate in un registro, e da una regola che cambia
> il mestiere dell'orologio: **un lavoro che tocca i dati di un'azienda non viene
> più eseguito dentro pgAgent — viene messo in coda.**
> ⇒ [I lavori automatici: che natura hanno e per conto di chi girano](/guide/processi-automatici-classe-e-identita)
>
> Vedi anche:
>
> * [Estensione pgAgent](/postgresql/pgAgent) — concetti base, schedule, step, log
> * [Guida Tracciamento processi e job](/guide/analisi-tracciamento-processi-e-job) — tre livelli di tracciamento (audit, job run log, task runs)
> * [Framework automazione DB](/guide/automazione-db) — automazioni dichiarative infrastrutturali
> * [linee-guida-sql §7c](/linee-guida-sql) — pattern "ciclo stato + finestra di validita'"

---

## Funzionale vs infrastrutturale — ⛔ superata

> La divisione a **due** che stava qui non si usa più: metteva nello stesso
> mucchio la pulizia del database e la chiusura dei contratti di un'azienda.
> Oggi le nature sono **tre** (manutenzione, amministrazione, dominio) e si
> scelgono rispondendo a una domanda sola: *«questo lavoro scrive dati che
> appartengono a un'azienda in particolare?»*.
>
> ⇒ [I lavori automatici — capitolo 3](/guide/processi-automatici-classe-e-identita)

Resta valido, e vale per tutti, il principio **"fonte di verita' =
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
| `chiusura_scadenze_daily` | daily 00:05 | 🔴 **Non chiude più niente da sé: ACCODA.** Mette in coda un lavoro per ogni azienda, che poi viene eseguito con l'identità di quell'azienda. Vedi [fn_accoda_chiusura_scadenze](/dbzero/dbops/manual/fn_accoda_chiusura_scadenze) | vendite (per azienda) | `85_pgagent/20260905-25-...` |

> **Nota storica (26-04-2026)**: il job `listini_versioni_close_scadute_daily` (creato il 24-04-2026 per chiudere le sole versioni listino) e' stato sostituito dal job parametrico `chiusura_scadenze_daily`. La funzione specifica `vendite.fn_listini_versioni_close_scadute()` e' stata droppata. Aggiungere nuove tabelle al pattern non richiede piu' nuovo codice DB: basta una INSERT seed in `dbops.automazione_chiusura_scadenze`.

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

### `chiusura_scadenze_daily` (framework parametrico)

* **Scopo**: motore unico per la chiusura automatica dello stato gestionale su tabelle con pattern "ciclo stato + finestra di validita'" (vedi [linee-guida-sql §7c](/linee-guida-sql)). Itera sulle righe `attivo=true` di `dbops.automazione_chiusura_scadenze` e applica UPDATE dinamici.
* **Funzione chiamata**: `dbops.fn_apply_chiusura_scadenze()` — ritorna JSONB con conteggio righe chiuse per tabella + meta-info esecuzione (`{"vendite.listini_versioni": 3, "vendite.contratti": 12, "_total": 15, "_executed_at": "..."}`).
* **Schedule**: tutti i giorni alle `00:05` (subito dopo il cambio data; semantica `valido_al` = ultimo giorno **incluso**, quindi 00:05 del giorno successivo e' il primo momento utile per chiudere).
* **Classe job**: `Routine Maintenance`.
* **Tabelle attualmente configurate**:
  * `vendite.listini_versioni` (`tipo_stato=VARCHAR`, ciclo `BOZZA -> ATTIVA -> CHIUSA`)
  * `vendite.contratti` (`tipo_stato=FK`, lookup `config.stati_doc_contratti.codice_interno`, ciclo `DRAFT -> ATTIVO -> CESSATO`; `SOSPESO` fuori scope operativo)
* **Pre-check**: prima di ogni UPDATE la fn verifica esistenza schema/tabella/colonne (e per FK anche tabella di lookup + codici). Errore tipato `E_AUTOMAZIONE_CHIUSURA_CONFIG_INVALIDA` in caso di config invalida (no exec parziale).
* **Idempotenza**: la query seleziona solo righe ancora attive con `valido_al` scaduto; esecuzioni ripetute nella stessa giornata sono no-op.
* **Interazione con guard tabella-specifici**: l'UPDATE attraversa i trigger `trg_<tabella>_a10_guard_transizione_stato_upd` e li soddisfa per costruzione (precondizione `valido_al < CURRENT_DATE` identica al WHERE). Nessun bypass, nessun GUC, nessun privilegio elevato.
* **Effetto sulla UX**: fra `PATCH valido_al = oggi` e le 00:05 del giorno successivo lo stato resta `ATTIVA`/`ATTIVO`. L'**applicabilita' operativa** (resolver prezzi, lookup contratti operativi) e' gia' scaduta perche' basata su `validita @> data`, non sullo stato.
* **SQL dinamico sicuro**: `format(%I)` per identificatori, `format(%L)` per valori. I codici nella config sono comunque amministrativamente controllati (Liquibase seed).
* **Audit**: insert in `dbops.audit_log` con `area='database'`, `function_name='fn_apply_chiusura_scadenze'`, `context=<JSONB risultato>`.
* **Migration job**: [85_pgagent/20260426-06-replace-pgagent-job-chiusura-scadenze-daily-mctit.yaml](/migrations_v2/85_pgagent/20260426-06-replace-pgagent-job-chiusura-scadenze-daily-mctit.yaml).
* **Migration funzione**: [20_code/dbops/20260426-02-create-fn-apply-chiusura-scadenze-mctit.yaml](/migrations_v2/20_code/dbops/20260426-02-create-fn-apply-chiusura-scadenze-mctit.yaml).
* **Migration tabella config**: [00_schema/dbops/20260426-01-create-automazione-chiusura-scadenze-mctit.yaml](/migrations_v2/00_schema/dbops/20260426-01-create-automazione-chiusura-scadenze-mctit.yaml).
* **Tabella config**: [dbops.automazione_chiusura_scadenze](/dbzero/dbops/tabelle/automazione_chiusura_scadenze).

#### Come aggiungere una nuova tabella al framework

1. Verificare che la tabella abbia il pattern `<col_stato> + <col_valido_al>` ([linee-guida-sql §7c](/linee-guida-sql)).
2. Creare un trigger guard transizione tabella-specifico (`trgfn_<tabella>_guard_transizione_stato`) con la matrice transizioni del workflow + precondizione temporale per la transizione terminale.
3. Aggiungere una riga in `dbops.automazione_chiusura_scadenze` (via INSERT seed in `80_data/sql/dbops/automazione_chiusura_scadenze.csv`) con `tipo_stato='VARCHAR'` o `tipo_stato='FK'` e i codici stato attivo/chiuso.
4. Nessun nuovo codice DB: il job notturno la prende in carico al successivo run.

---

## Convenzioni di naming

* **Job name**: `<entita>_<azione>_<frequenza>` in snake_case, tutto minuscolo (es. `listini_versioni_close_scadute_daily`, `sync_auth_user_expired_daily`). Il nome e' usato come chiave per delete/replace nel changeSet.
* **Schedule name**: `<frequenza>_<ora>` (es. `daily_00_05`, `daily_06`).
* **Step name**: `run_<descrizione_azione>` (es. `run_listini_versioni_close_scadute`).
* **Migration file**: `YYYYMMDD-NN-create-pgagent-job-<job-name-kebab-case>-<author>.yaml` in `85_pgagent/`.

---

## Pattern raccomandato per nuovi job funzionali

> 🔴 **Prima di seguirlo, una domanda: questo lavoro tocca i dati di
> un'azienda?** Se sì, i punti qui sotto **non bastano**, e il punto 2 in
> particolare descrive ciò che oggi non si fa più: un lavoro di dominio non
> esegue dentro l'orologio, lo mette in **coda** e a eseguirlo è la coda, con
> l'identità dell'azienda addosso.
> ⇒ [I lavori automatici — capitoli 4 e 5](/guide/processi-automatici-classe-e-identita)
>
> ✅ I punti restano validi per i lavori di **manutenzione** e
> **amministrazione**, e per il job-sveglia di un lavoro di dominio (che è un
> job pgAgent a tutti gli effetti: si limita ad accodare).

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
* **Giornale delle esecuzioni**: [maintenance.job_run_log](/dbzero/maintenance/manual/job_run_log) — ogni corsa lascia una riga con **chi era** (quale lavoro, con quale identità), non solo com'è andata.

> ⛔ **Aggiornato il 06-09-2026.** Qui c'era scritto che per questi job il
> tracciamento primario era `pga_joblog` e che il giornale era «una best
> practice futura». Non è più così, e la differenza non è formale:
>
> * il giornale ora dice **chi** ha eseguito, e chi non lo dice finisce in
>   [vw_run_senza_attore](/dbzero/dbops/manual/vw_run_senza_attore);
> * fino a settembre **un fallimento non lasciava traccia**: la riga «è andata
>   male» veniva annullata insieme all'errore. Oggi il verbale viaggia su una
>   linea separata e sopravvive. È il motivo per cui un lavoro è rimasto rotto
>   sei mesi senza che nessuno lo sapesse.
>
> Il racconto per esteso: [I lavori automatici — capitolo 6](/guide/processi-automatici-classe-e-identita).

---

## Quando NON usare un job pgAgent

> 🔴 **La prima risposta oggi è una sola: quando il lavoro tocca i dati di
> un'azienda.** In quel caso l'orologio può soltanto **svegliare**, e il lavoro
> lo fa la coda. Dentro l'orologio nessuno ha un nome, e un fallimento non
> arriva a nessuno.

Per il resto, un job notturno e' appropriato quando:

* l'allineamento puo' essere **asincrono** (ritardo ore accettabile);
* la logica operativa **non dipende** dal flag sincronizzato (altrimenti diventa un single point of failure);
* l'operazione e' **batch-friendly** (UPDATE massivo, nessun lock lungo).

Se la coerenza deve essere **immediata** (es. un flag che il resolver legge davvero), il pattern corretto e' **trigger sincrono** o **colonna generata**, non job notturno.

Se la logica e' **event-driven** (reagisce a un INSERT/UPDATE specifico), usare trigger o pipeline task, non scheduled job.

---
{% include-markdown "signature-core.md" %}
