## 📘 Documentazione Concettuale – Procedura `maintenance.proc_automations_attivo_job`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — il processo `automations_attivo`: job pgAgent, procedura e posto nella convergenza del rilascio
> * [maintenance.job_run_log](/dbzero/maintenance/tabelle/job_run_log) — il giornale in cui ogni corsa lascia la sua riga
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl) — la regola `ATTIVO` e il suo `exec_mode`
> * [dbops.automazione_attivo_eccezioni](/dbzero/dbops/tabelle/automazione_attivo_eccezioni) — le FK che non si legano, ognuna col suo motivo
>
> Approfondimento viste:
>
> * [dbops.vw_processi_programmazione](/dbzero/dbops/views/vw_processi_programmazione) — il calendario vivo e lo stato del processo
> * [maintenance.vw_job_run_da_guardare](/dbzero/maintenance/views/vw_job_run_da_guardare) — dove una corsa fallita diventa una cosa da guardare
>
> Approfondimento funzioni:
>
> * [dbops.fn_run_automations_attivo](/dbzero/dbops/funzioni/fn_run_automations_attivo) — il lavoro vero: il blocco sul padre e il requisito sul figlio
> * [maintenance.fn_run_and_log](/dbzero/maintenance/funzioni/fn_run_and_log) — il giornale da cui passa la chiamata, col lock e il verbale del fallimento
> * [maintenance.fn_sveglia_accesa](/dbzero/maintenance/funzioni/fn_sveglia_accesa) — il cancello dello step pgAgent
>
> Guide:
>
> * [Framework di Automazione DB, §4.2](/guide/automazione-db#42-attivo-soft-delete-blocco-sul-padre-requisito-sul-figlio) — la regola ATTIVO
> * [Framework di Automazione DB, §9](/guide/automazione-db#9-quando-girano-le-automazioni) — quando girano le automazioni

---

### 🎯 Scopo Principale

Il wrapper del processo `automations_attivo`: esegue `dbops.fn_run_automations_attivo` su
tutto l'ambito, passando dal giornale delle esecuzioni sotto il codice del processo.

La procedura non aggiunge logica: delega a `maintenance.fn_run_and_log`, che apre la riga
della corsa in `maintenance.job_run_log`, esegue il runner e chiude la riga con l'esito.

---

### Che cosa allinea: un padre non si spegne sotto figli attivi

Il runner porta le chiavi esterne dell'ambito alla regola `ATTIVO`. Dove il **padre** ha la
colonna `attivo`, monta sul padre il trigger che rifiuta la disattivazione se ci sono figli
attivi collegati, e sul figlio quello che rifiuta l'aggancio a un padre spento. Nessuna
cascata: i figli non si toccano.

A ogni giro toglie anche i trigger che non devono più esserci: quelli delle FK dichiarate in
`dbops.automazione_attivo_eccezioni` e quelli che nominano una tabella o una colonna che non
esiste più. Chi genera ritira. Le regole complete sono nella scheda del runner.

---

### Due strade, la stessa procedura

| Dove | Chi la chiama | Quando |
| --- | --- | --- |
| dbdev e installazioni con pgAgent | il job `automations_attivo`, step `run_automations_attivo` | al giro del suo calendario |
| CI, database ricostruito da zero, ogni migrazione di sviluppo | la convergenza del rilascio (passata `ci_apply`) | `ci_ordine` 50: dopo `automations_tx_id`, prima di `automations_lock_columns` |

Lo step pgAgent chiama la procedura solo se `maintenance.fn_sveglia_accesa('automations_attivo')`
è vero: a processo spento il giro programmato non parte e il giornale non scrive niente. La
convergenza invece gira sempre — spegnere ferma la sveglia, non l'aggiornamento — e dopo la
chiamata pretende nel giornale una riga riuscita di quel giro, che non sia un salto; altrimenti
la migrazione si ferma nominando il processo.

Il calendario dei job è in [Job pgAgent](/dbzero/maintenance/job_pgagent), quello vivo di
un'installazione in `dbops.vw_processi_programmazione`. ⚠️ In CI il job non esiste
(`85_pgagent` finisce `MARK_RAN`): lì il lavoro lo fa solo la convergenza.

⚠️ Nel giornale le due strade hanno la stessa `origine` (`PGAGENT`, il valore di partenza
della colonna): a distinguerle è `ruolo_sessione`, cioè chi si è collegato.

---

### ⭐ Una corsa, una riga nel giornale

Il meccanismo è quello di `maintenance.fn_run_and_log`, e la sua scheda lo racconta per intero.
Per chi legge il giornale di questo processo:

* **Il nome della corsa è il codice del processo**, `automations_attivo`: così il giornale
  risale alla riga di `dbops.processi`, e la convergenza riconosce la corsa del suo giro.
* **Una corsa alla volta.** La procedura passa come chiave un advisory lock sull'hash del
  codice. Se una corsa dello stesso processo è già in giro, la seconda non esegue niente e
  lascia una riga **saltata**: `saltata` vero, `ok` vuoto, già chiusa. Un salto non è una
  corsa riuscita.
* **Un fallimento si propaga, e il verbale resta.** Se il runner fallisce, `fn_run_and_log`
  scrive il verbale **fuori transazione**, con `maintenance.fn_job_run_log_failure`, e poi
  rilancia l'errore: lo step pgAgent fallisce, la convergenza si ferma, e la transazione si
  annulla con tutto il DDL del giro. La riga rossa porta in `error_code` il codice di dominio
  del runner (`E_…`) o, in mancanza, lo SQLSTATE, che sta anche in `sqlstate`; il dettaglio
  dell'errore è in `dbops.error_log`. Da lì la corsa compare in
  `maintenance.vw_job_run_da_guardare`.
* **Gira come il proprietario.** La procedura è `SECURITY DEFINER`, con `search_path` fissato,
  e appartiene a `zeroerp_owner`: chiunque la chiami — `zeroerp_job` di notte, la convergenza —
  il DDL gira come `zeroerp_owner`, e i trigger nascono suoi. Il giornale registra come ruolo
  della sessione chi si è collegato.

---

### `SCHEDULED`, tutto l'ambito, mai in simulazione

La procedura chiama il runner con tre scelte fisse:

* **modo `SCHEDULED`.** Una regola di `dbops.automation_rules_tbl` gira se il suo `exec_mode`
  è `AUTO` oppure uguale al modo della chiamata. La regola `ATTIVO` del seed è `AUTO`, e gira
  qui come in ogni altro modo. ⚠️ Il modo dice **chi** chiama, non **quando**: anche la
  convergenza del rilascio passa da questa procedura, e quindi chiama in `SCHEDULED`.
* **ambito non indicato.** Gli schemi li risolve `dbops.fn_resolve_scope`: quelli di
  `dbops.automation_scope` e, se il registro è vuoto, tutti gli schemi utente tranne `storico`.
* **niente simulazione.** Il DDL si fa. Per sapere che cosa farebbe un giro non si passa dalla
  procedura: si chiama il runner con la simulazione accesa, e `dbops.audit_log` registra le
  azioni previste.

---

### Codici errore

La procedura non ne solleva di suoi: l'errore è del runner, e arriva com'è.

* `E_ATTIVO_BLOCK` — il trigger di blocco sul padre non si è potuto creare.
* `E_ATTIVO_REQUIRE` — il trigger di requisito sul figlio non si è potuto creare.

Un guasto dell'ambiente (connessione, risorse, privilegi, lock) non si traveste: il runner lo
scrive nel registro errori e lo rilancia col suo SQLSTATE.

---

### Test

* `db/pgtap/maintenance/test-proc-job-definer-v1.sql` — per ogni `maintenance.proc_*_job`:
  `SECURITY DEFINER`, `search_path` fissato, proprietario dello schema, nessun `EXECUTE` a
  `PUBLIC` né a `zeroerp_app`.
* `db/pgtap/dbops/test-processi-jobname-wrapper.sql` — il nome che il wrapper passa al giornale
  esiste in `dbops.processi`.
* `db/pgtap/dbops/test-processi-convergenza-ci.sql` — la procedura dichiarata esiste, ha girato
  con esito positivo sul database, e `automations_attivo` viene prima di
  `automations_lock_columns`.
* `db/pgtap/dbops/test-automazione-attivo-eccezioni-v1.sql` e
  `db/pgtap/dbops/test-trigger-attivo-orfani-v1.sql` — il runner: le eccezioni dichiarate e
  il ritiro dei trigger orfani.

---

### Note di migrazione

* 2026-09-26 — entra nella convergenza del rilascio, che chiama le procedure dei job
  strutturali dove pgAgent non c'è (`brief-db-job-notturni-in-ci`).
* 2026-10-14 — diventa `SECURITY DEFINER`, come tutte le `maintenance.proc_*_job`
  (`brief-db-ruoli-di-sistema`).
* 2026-10-16 — lo step pgAgent passa dal cancello `maintenance.fn_sveglia_accesa`
  (`brief-db-processi-accensione-per-ambiente`).
* 2026-11-03 — pagina riscritta: la versione precedente descriveva un giornale che non esiste
  (`maintenance.job_log`, `start_time`, `status`, `tx_id`), un errore che non interrompeva lo
  scheduler, un orario notturno inventato e lo step come una chiamata nuda.

---

{% include-markdown "signature-core.md" %}
