## 📘 Documentazione Concettuale – Procedura `maintenance.proc_analyze_statistiche_job`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — il processo `analyze_statistiche`: job pgAgent, procedura e posto nella convergenza di CI
> * [maintenance.job_run_log](/dbzero/maintenance/tabelle/job_run_log) — il giornale in cui ogni corsa lascia la sua riga
>
> Approfondimento viste:
>
> * [maintenance.vw_job_run_da_guardare](/dbzero/maintenance/views/vw_job_run_da_guardare) — dove una corsa fallita diventa una cosa da guardare
>
> Approfondimento funzioni:
>
> * [maintenance.fn_analyze_statistiche](/dbzero/maintenance/funzioni/fn_analyze_statistiche) — il lavoro vero: `ANALYZE` e autoverifica
> * [maintenance.fn_run_and_log](/dbzero/maintenance/funzioni/fn_run_and_log) — il giornale da cui passa la chiamata
> * [maintenance.fn_sveglia_accesa](/dbzero/maintenance/funzioni/fn_sveglia_accesa) — il cancello dello step pgAgent
>
> Guide:
>
> * [Liquibase, setup e workflow](/liquibase-setup-workflow) — §1 e §5: chi possiede le tabelle, e con quale ruolo gira ogni passata

---

### 🎯 Scopo Principale

Il wrapper del job `analyze_statistiche`: esegue `maintenance.fn_analyze_statistiche` passando
dal giornale delle esecuzioni, sotto il codice del processo.

La procedura non aggiunge logica: delega tutto a `maintenance.fn_run_and_log`, che apre la riga
della corsa in `maintenance.job_run_log`, esegue l'analisi e chiude la riga con l'esito.

---

### Due strade, la stessa procedura

| Dove | Chi la chiama | Quando |
| --- | --- | --- |
| dbdev e installazioni | il job pgAgent `analyze_statistiche`, step `analyze` | ogni notte alle 02:30 |
| CI e scratch | la convergenza dei job strutturali (passata `ci_apply`) | per **ultima** (`ci_ordine` 900): dopo che le automazioni hanno creato le tabelle di storico, prima dei pgTAP |

Lo step pgAgent chiama la procedura solo se `maintenance.fn_sveglia_accesa('analyze_statistiche')`
è vero: a sveglia spenta il lavoro non parte, e il giornale non scrive niente.

⚠️ In CI il job pgAgent non esiste: i changeSet di `85_pgagent` girano solo dove c'è
l'estensione, e altrove finiscono `MARK_RAN`. Il lavoro gira lo stesso perché il processo
dichiara in `dbops.processi` la sua posizione e la sua procedura, e lo chiama la convergenza.

---

### ⭐ Il giornale è ciò che rende visibile un fallimento

Se l'autoverifica solleva `E_STATISTICHE_MANCANTI`, `fn_run_and_log` scrive il verbale del
fallimento **fuori transazione** (con `maintenance.fn_job_run_log_failure`), con le tabelle
nominate nel messaggio, e poi **rilancia** l'errore: lo step pgAgent fallisce, la convergenza
in CI si ferma. Il lavoro si annulla, il verbale resta, e da lì lo vedono il panorama dei
processi e il digest. Il dettaglio del meccanismo è nella scheda di `fn_run_and_log`.

La procedura non passa una chiave di lock: non c'è il salto della corsa sovrapposta. Il numero
di righe che il giornale registra per questa corsa è quello dell'istruzione eseguita, non il
numero delle tabelle analizzate.

⚠️ Il nome del job che passa al giornale è il **codice del processo** (`analyze_statistiche`),
uguale al nome del job pgAgent: è così che il giornale risale al processo, e che la convergenza
in CI riconosce la riga di quel giro.

⚠️ Nessun `COMMIT`: in CI gira dentro la transazione del changeSet.

---

### Gira come il proprietario, e il proprietario possiede tutto

La procedura è `SECURITY DEFINER`, con `search_path` fissato, e appartiene a `zeroerp_owner`,
come tutte le `maintenance.proc_*_job`. Chiunque la chiami — `zeroerp_job` di notte, la
convergenza in CI — l'analisi gira come `zeroerp_owner`. Il giornale registra come ruolo della
sessione chi si è collegato; l'errore dell'autoverifica, nel contesto, il ruolo che ha eseguito.

Per analizzare una tabella bisogna esserne proprietari (o superuser, o avere `MAINTAIN`). Il
disegno è il primo: `zeroerp_owner` possiede tutte le tabelle del perimetro, comprese quelle che
il primo passo dell'installazione crea da superuser (le tabelle di Liquibase e
`internal.project_metadata`), perché la fase `pre` di `scripts/sql/provision_zeroerp.sql` gliele
passa. In CI la stessa fase gira prima della migrazione, e la convergenza gira come
`zeroerp_owner`. È provisioning, mai un changeSet. Se una tabella restasse di un altro, la riga
rossa del giornale la nomina con il motivo `NON_ANALIZZABILE`.

---

### Test

* `db/pgtap/maintenance/test-fn-analyze-statistiche-v1.sql` — fra l'altro, che il processo
  `analyze_statistiche` è a catalogo come job pgAgent con questa procedura, e che è l'ultimo
  della convergenza in CI.
* `db/pgtap/maintenance/test-proc-job-definer-v1.sql` — per ogni `maintenance.proc_*_job`:
  `SECURITY DEFINER`, `search_path` fissato, proprietario dello schema, nessun `EXECUTE` a
  `PUBLIC` né a `zeroerp_app`.
* `db/pgtap/dbops/test-processi-jobname-wrapper.sql` — il nome passato dal wrapper esiste in
  `dbops.processi`.
* `db/pgtap/dbops/test-processi-convergenza-ci.sql` — la procedura dichiarata esiste, e sul
  database ha girato con esito positivo.

---

### Note di migrazione

* 2026-10-14 — nasce col job notturno (`brief-db-statistiche-tabelle-job-notturno`, D15).
  Nello stesso giro tutte le `maintenance.proc_*_job` diventano `SECURITY DEFINER`
  (`brief-db-ruoli-di-sistema`).
* 2026-10-15 — la CI sostituisce il `GRANT pg_maintain` al ruolo della migrazione col passaggio
  di proprietà a `zeroerp_owner`, e le passate girano come `zeroerp_owner`
  (`brief-db-ruoli-di-sistema`, fase 2).

---

{% include-markdown "signature-core.md" %}
