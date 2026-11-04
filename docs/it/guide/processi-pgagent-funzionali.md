# Guida — Processi pgAgent funzionali

> **Ultimo aggiornamento**: 4 novembre 2026
>
> Destinatari: sviluppatori database, backend, analisti funzionali
>
> Questa guida è l'**elenco dei lavori a orario**: quali esistono, quando
> partono, che cosa fanno, come se ne aggiunge uno.
>
> 🔴 **Non è qui che si decide la natura di un lavoro.** Ogni lavoro ha una
> natura dichiarata in un registro, e c'è una regola che vale per tutti: **un
> lavoro che tocca i dati di un'azienda non viene eseguito dentro pgAgent, viene
> messo in coda.** L'orologio si limita a svegliarlo.
> ⇒ [I lavori automatici: che natura hanno e per conto di chi girano](/guide/processi-automatici-classe-e-identita)
>
> Vedi anche:
>
> * [Estensione pgAgent](/postgresql/pgAgent) — concetti base, schedule, step, log
> * [Guida Tracciamento processi e job](/guide/analisi-tracciamento-processi-e-job) — tre livelli di tracciamento (audit, job run log, task runs)
> * [Framework automazione DB](/guide/automazione-db) — automazioni dichiarative infrastrutturali
> * [linee-guida-sql §7c](/linee-guida-sql) — pattern "ciclo stato + finestra di validita'"

---

## Che natura ha un lavoro

Le nature sono **tre**: manutenzione, amministrazione e dominio. Si sceglie
rispondendo a una domanda sola: *«questo lavoro scrive dati che appartengono a
un'azienda in particolare?»* ⇒ [I lavori automatici — capitolo 3](/guide/processi-automatici-classe-e-identita)

Per tutti vale il principio **"fonte di verita' =
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
| `chiusura_scadenze_daily` | ogni ora, al minuto 5 | 🔴 **Non chiude niente da sé: ACCODA.** Mette in coda un lavoro per ogni azienda, una volta per giorno aziendale, che poi viene eseguito con l'identità di quell'azienda. Vedi [fn_accoda_chiusura_scadenze](/dbzero/dbops/funzioni/fn_accoda_chiusura_scadenze) | vendite (per azienda) | `85_pgagent/20260905-25-...` |

---

## Schede dettaglio

### `sync_auth_user_expired_daily`

* **Scopo**: sincronizzare `django.auth_user.is_active = false` per risorse umane con finestra `valido_dal/valido_al` scaduta (decommissionamento automatico).
* **Che cosa esegue**: lo step chiama la procedura `maintenance.proc_sync_auth_user_expired_job()`, che esegue `anagrafiche.fn_sync_auth_user_expired()` e ne registra la corsa nel giornale.
* **Schedule**: tutti i giorni alle `06:00`.
* **Classe job**: `Routine Maintenance`.
* **Idempotenza**: la funzione processa tutti gli `auth_user` con finestra scaduta; rieseguirla non produce effetti se gia' applicata.
* **Migration**: [85_pgagent/20260302-04-create-pgagent-job-sync-auth-user-expired-daily-mctit.yaml](/migrations_v2/85_pgagent/20260302-04-create-pgagent-job-sync-auth-user-expired-daily-mctit.yaml).
* **Tabelle coinvolte**: `anagrafiche.risorse_umane`, `anagrafiche.identita_digitali`, `django.auth_user`.

### `chiusura_scadenze_daily` (framework parametrico)

* **Scopo**: motore unico per la chiusura automatica dello stato gestionale su tabelle con pattern "ciclo stato + finestra di validita'" (vedi [linee-guida-sql §7c](/linee-guida-sql)). Itera sulle righe `attivo=true` di `dbops.automazione_chiusura_scadenze`: una testata sotto la porta del modello del documento si chiude chiamando il verbo dichiarato in `verbo_chiusura` (è la strada di tutti i bersagli di oggi), ogni altra tabella con un `UPDATE` dinamico dello stato.
* **Che cosa esegue**: lo step chiama la procedura `maintenance.proc_accoda_chiusura_scadenze_job()`, che passa dal giornale dei job e mette in coda un lavoro `CHIUSURA_SCADENZE` per ogni azienda ([fn_accoda_chiusura_scadenze](/dbzero/dbops/funzioni/fn_accoda_chiusura_scadenze)). Il lavoro vero lo fa poi la coda, con l'identità di quell'azienda, applicando `dbops.fn_apply_chiusura_scadenze()`, che ritorna JSONB con conteggio righe chiuse per tabella + meta-info esecuzione (`{"vendite.listini_versioni": 3, "vendite.contratti": 12, "_total": 15, "_executed_at": "..."}`).
* **Schedule**: **ogni ora, al minuto 5**, anche se il nome dice «daily». Il giorno di una scadenza è quello dell'azienda (`script.fn_data_operativa()`, nel suo fuso), non l'orologio del server: la prima sveglia dopo la mezzanotte dell'azienda accoda il lavoro, le altre del giorno lo trovano già accodato o fatto e non accodano niente. Semantica `valido_al` = ultimo giorno **incluso**. Lo step parte solo se `maintenance.fn_sveglia_accesa('chiusura_scadenze_daily')` è vero.
* **Classe**: il processo `chiusura_scadenze_daily` del catalogo `dbops.processi` è di classe `DOMINIO`, sul canale `CODA_AUTOMATICA`: tocca i dati delle aziende, e gira con l'identità tecnica di ciascuna dentro la RLS.
* **Tabelle attualmente configurate**:
  * `vendite.listini_versioni` (`tipo_stato=FK`, lookup `config.stati_doc_listino_versioni.codice_interno`, ciclo `BOZZA -> ATTIVA -> CHIUSA`; sotto la porta del modello: chiude il verbo `vendite.fn_chiudi_versioni_listino_scadute`)
  * `vendite.contratti` (`tipo_stato=FK`, lookup `config.stati_doc_contratti.codice_interno`, ciclo `DRAFT -> ATTIVO -> CESSATO`; `SOSPESO` fuori scope operativo; sotto la porta: chiude il verbo `vendite.fn_cessa_contratti_scaduti`)
  * `vendite.preventivi` (`tipo_stato=FK`, lookup `config.stati_doc_preventivi.codice_interno`, `EMESSO -> SCADUTO` sulla colonna `validita_al`; sotto la porta: chiude il verbo `vendite.fn_chiudi_preventivi_scaduti`; dal 31-10-2026, brief-db-scadenza-preventivi)
* **Pre-check**: prima di ogni UPDATE la fn verifica esistenza schema/tabella/colonne (e per FK anche tabella di lookup + codici). Errore tipato `E_AUTOMAZIONE_CHIUSURA_CONFIG_INVALIDA` in caso di config invalida (no exec parziale).
* **Idempotenza**: la query seleziona solo righe ancora attive con `valido_al` scaduto; esecuzioni ripetute nella stessa giornata sono no-op.
* **Interazione con guard tabella-specifici**: i tre bersagli di oggi si chiudono col loro verbo, che passa dalla porta del modello; il ramo `UPDATE` diretto attraversa i guard di transizione della tabella. La scadenza si confronta con `script.fn_data_operativa()`, non con `CURRENT_DATE`. Nessun bypass, nessun GUC, nessun privilegio elevato: la funzione è `SECURITY INVOKER` e chiude solo ciò che vede l'identità dell'azienda.
* **Effetto sulla UX**: fra `PATCH valido_al = oggi` e la prima sveglia dopo la mezzanotte dell'azienda (più il tempo del drenatore della coda) lo stato resta `ATTIVA`/`ATTIVO`. L'**applicabilita' operativa** (resolver prezzi, lookup contratti operativi) e' gia' scaduta perche' basata su `validita @> data`, non sullo stato.
* **SQL dinamico sicuro**: `format(%I)` per identificatori, `format(%L)` per valori. I codici nella config sono comunque amministrativamente controllati (Liquibase seed).
* **Audit**: a giro finito `fn_apply_chiusura_scadenze` scrive una riga in `dbops.audit_log` con `dbops.fn_audit_log_once`, status `OK`, con il riepilogo nei `params`. La scrittura è best-effort: se fallisce l'errore si inghiotte, e il riepilogo arriva comunque all'handler, che lo scrive nel risultato del lavoro di coda.
* **Migration job**: [85_pgagent/20260905-25-replace-pgagent-job-chiusura-scadenze-accoda-mctit.yaml](/migrations_v2/85_pgagent/20260905-25-replace-pgagent-job-chiusura-scadenze-accoda-mctit.yaml).
* **Migration funzione**: [20_code/dbops/20260426-02-create-fn-apply-chiusura-scadenze-mctit.yaml](/migrations_v2/20_code/dbops/20260426-02-create-fn-apply-chiusura-scadenze-mctit.yaml).
* **Migration tabella config**: [00_schema/dbops/20260426-01-create-automazione-chiusura-scadenze-mctit.yaml](/migrations_v2/00_schema/dbops/20260426-01-create-automazione-chiusura-scadenze-mctit.yaml).
* **Tabella config**: [dbops.automazione_chiusura_scadenze](/dbzero/dbops/tabelle/automazione_chiusura_scadenze).

#### Come aggiungere una nuova tabella al framework

1. Verificare che la tabella abbia il pattern `<col_stato> + <col_valido_al>` ([linee-guida-sql §7c](/linee-guida-sql)).
2. Creare un trigger guard transizione tabella-specifico (`trgfn_<tabella>_guard_transizione_stato`) con la matrice transizioni del workflow + precondizione temporale per la transizione terminale.
3. Aggiungere una riga in `dbops.automazione_chiusura_scadenze` (via INSERT seed in `80_data/sql/dbops/automazione_chiusura_scadenze.csv`) con `tipo_stato='VARCHAR'` o `tipo_stato='FK'`, i codici stato attivo/chiuso, la `classe` e, per una testata sotto la porta del modello, il verbo in `verbo_chiusura` (una funzione viva senza argomenti).
4. Nessun nuovo codice DB oltre al verbo, se serve: il lavoro di coda la prende in carico alla prima sveglia del giorno aziendale successivo.

---

## Convenzioni di naming

* **Job name**: `<entita>_<azione>_<frequenza>` in snake_case, tutto minuscolo (es. `listini_versioni_close_scadute_daily`, `sync_auth_user_expired_daily`). Il nome e' usato come chiave per delete/replace nel changeSet.
* **Schedule name**: `<frequenza>_<ora>` (es. `daily_00_05`, `daily_06`).
* **Step name**: `run_<descrizione_azione>` (es. `run_listini_versioni_close_scadute`).
* **Migration file**: `YYYYMMDD-NN-create-pgagent-job-<job-name-kebab-case>-<author>.yaml` in `85_pgagent/`.

---

## Con che utente girano i lavori

pgAgent non entra nel database come amministratore. Si collega con un utente
dedicato, **`zeroerp_job`**, che ha un solo permesso: **avviare i lavori
previsti**. Non può leggere né scrivere tabelle, e non può eseguire SQL qualsiasi.

Ogni lavoro è una **procedura** con un nome fisso, `maintenance.proc_<nome>_job()`,
e lo step di pgAgent contiene solo la sua chiamata:

```sql
CALL maintenance.proc_sync_auth_user_expired_job();
```

La procedura lavora come il **proprietario** del database (`SECURITY DEFINER`):
così ciò che il lavoro crea (tabelle di storico, indici) appartiene al
proprietario come tutto il resto, e `zeroerp_job` da solo non può fare niente fuori
da quella procedura. Uno step scritto a mano con un comando qualsiasi viene
rifiutato.

**Per un lavoro nuovo** quindi servono due cose:

* la procedura `maintenance.proc_<nome>_job()`, `SECURITY DEFINER`, con il
  `search_path` fissato e l'esecuzione tolta a tutti. A `zeroerp_job` la dà il
  provisioning, da solo, per ogni procedura con quel nome. Il controllo
  `maintenance/test-proc-job-definer-v1` verifica ogni procedura con quel nome,
  quindi se ne manca un pezzo lo segnala;
* lo step pgAgent che la chiama, e niente altro.

**Come sapere che nessun lavoro gira da amministratore.** Il giornale delle
esecuzioni registra per ogni corsa l'utente che si è collegato. Il controllo
`maintenance.vw_job_run_da_superuser` resta vuoto finché i lavori girano come
devono, e segnala al gestore del server ogni processo la cui ultima corsa è stata
fatta da un amministratore.

Come si installa pgAgent con questo utente: [Installazione](/installazione), passo 10,
e [Estensione pgAgent](/postgresql/pgAgent). I ruoli del database e le loro regole:
[Provisioning ruoli DB](/dev/backend/provisioning-db-roles).

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

1. **Funzione incapsulata in `20_code/<schema>/`**: il job non deve contenere SQL business inline. Creare `schema.fn_<operazione>()` che ritorna un conteggio o un JSON di risultato, richiamabile anche manualmente per test e recovery fuori schedulazione. La chiama la procedura del job (sezione qui sopra), che è l'unica cosa che lo step contiene.
2. **Logica nel trigger, non nel job**: le regole (quali righe modificare, a quale condizione) vivono nei trigger/funzioni di dominio. Il job esegue UPDATE/SELECT che **attraversa** i guard e li soddisfa per costruzione. La procedura del job è `SECURITY DEFINER` per un motivo preciso (lavorare come proprietario); la funzione che chiama no, salvo necessità dimostrata, e nessun bypass via GUC.
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
* **Giornale delle esecuzioni**: [maintenance.job_run_log](/dbzero/maintenance/tabelle/job_run_log) — è il tracciamento che conta. Ogni corsa lascia una riga con **chi era** (quale lavoro, per conto di chi, con quale utente si è collegato), non solo com'è andata:
  * una corsa che non dice per conto di chi gira finisce in [vw_run_senza_attore](/dbzero/dbops/views/vw_run_senza_attore);
  * una corsa **fallita** resta nel giornale: il verbale viaggia su una connessione separata e non viene annullato insieme all'errore. Senza, un lavoro rotto potrebbe restarlo per mesi senza che nessuno lo sappia.

  Il racconto per esteso: [I lavori automatici — capitolo 6](/guide/processi-automatici-classe-e-identita).

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
