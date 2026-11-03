## 📘 Documentazione Concettuale – Procedura `maintenance.proc_automations_lock_columns_job`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — il processo `automations_lock_columns`: job pgAgent, procedura e posto nella convergenza del rilascio
> * [maintenance.job_run_log](/dbzero/maintenance/tabelle/job_run_log) — il giornale in cui ogni corsa lascia la sua riga
> * [dbops.automation_lock_columns](/dbzero/dbops/tabelle/automation_lock_columns) — il registro delle colonne bloccate, oltre a `codice_interno`
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl) — le regole `LOCK_COLUMNS` e `DATE_VALIDITA` e il loro `exec_mode`
>
> Approfondimento viste:
>
> * [dbops.vw_processi_programmazione](/dbzero/dbops/views/vw_processi_programmazione) — il calendario vivo e lo stato del processo
> * [maintenance.vw_job_run_da_guardare](/dbzero/maintenance/views/vw_job_run_da_guardare) — dove una corsa fallita diventa una cosa da guardare
>
> Approfondimento funzioni:
>
> * [dbops.fn_run_automations_lock_columns](/dbzero/dbops/funzioni/fn_run_automations_lock_columns) — il primo lavoro: il lock di colonna portato al registro
> * [dbops.fn_lock_columns_divergenze](/dbzero/dbops/funzioni/fn_lock_columns_divergenze) — lo scarto fra il lock vivo e quello dichiarato, cioè che cosa farebbe un giro
> * [dbops.fn_run_automations_date_validita](/dbzero/dbops/funzioni/fn_run_automations_date_validita) — il secondo lavoro: il guard delle date di validità
> * [script.trgfn_lock_columns](/dbzero/script/funzioni/trgfn_lock_columns) — la funzione del lock
> * [script.trgfn_guard_date_validita](/dbzero/script/funzioni/trgfn_guard_date_validita) — la funzione del guard delle date
> * [maintenance.fn_run_and_log](/dbzero/maintenance/funzioni/fn_run_and_log) — il giornale da cui passa la chiamata, col lock e il verbale del fallimento
> * [maintenance.fn_sveglia_accesa](/dbzero/maintenance/funzioni/fn_sveglia_accesa) — il cancello dello step pgAgent
>
> Guide:
>
> * [Framework di Automazione DB, §4.1](/guide/automazione-db#41-lock_columns-blocco-colonne-critiche) — la regola LOCK_COLUMNS
> * [Framework di Automazione DB, §4.7](/guide/automazione-db#47-date_validita-la-regola-del-periodo) — la regola DATE_VALIDITA
> * [Framework di Automazione DB, §9](/guide/automazione-db#9-quando-girano-le-automazioni) — quando girano le automazioni

---

### 🎯 Scopo Principale

Il wrapper del processo `automations_lock_columns`: in una sola corsa esegue `dbops.fn_run_automations_lock_columns` e poi
`dbops.fn_run_automations_date_validita` su tutto l'ambito, passando dal giornale delle esecuzioni
sotto il codice del processo.

La procedura non aggiunge logica: delega a `maintenance.fn_run_and_log`, che apre la riga
della corsa in `maintenance.job_run_log`, esegue il runner e chiude la riga con l'esito.

---

### ⭐ Due automazioni della stessa famiglia, in una corsa

* **Il lock di colonna.** `dbops.fn_run_automations_lock_columns` porta il lock vivo a quello
  dichiarato — `codice_interno`, implicito dove esiste, più le colonne accese di
  `dbops.automation_lock_columns` — con tre azioni: lo **crea** dove manca, lo **rigenera** dove
  è diverso (anche se è stato scritto a mano, qualunque nome abbia), lo **toglie** dove il
  registro non lo vuole più. Una colonna spenta nel registro è la decisione di toglierla.
* **Il periodo che non si capovolge.** `dbops.fn_run_automations_date_validita` monta, su ogni
  tabella dell'ambito che ha `valido_dal` e `valido_al` (lo schema `storico` escluso), il guard
  che rifiuta una fine precedente all'inizio. Lo stesso guard gira anche a ogni migrazione, da
  una rete in `90_end`.

⚠️ Le due istruzioni stanno nella stessa corsa e nella stessa transazione: il giornale ne
registra una riga sola, e se il lock si ferma il guard delle date quella volta non gira.

---

### ⛔ Si ferma, invece di cancellare un lock che non conosce

Se un trigger vivo blocca una colonna che il registro non nomina affatto, il runner si ferma
**prima di qualunque DDL** con `E_LOCK_COLUMNS`, e nomina la colonna: la corsa è rossa, ed è
voluto. Il rimedio è una riga nel registro, dal suo CSV, non un altro giro. Un lock di colonna
non si scrive a mano: si dichiara.

Che cosa farebbe un giro si legge da `dbops.fn_lock_columns_divergenze`, che confronta il vivo
col dichiarato senza toccare niente: è lo stesso criterio del runner.

---

### ⭐ Dopo la famiglia, nello stesso ordine della convergenza

Il lucchetto viene dopo ciò su cui si chiude: una tabella nuova riceve prima le colonne e i
trigger della famiglia, poi il blocco. Nella convergenza l'ordine lo dà il catalogo
(`automations_attivo` 50, `automations_lock_columns` 60, `automations_delete_block` 70). Di
notte i job `automations_lock_columns` e `automations_delete_block` partono dieci minuti dopo
gli altri della famiglia (oggi alle 21:10 contro le 21:00, in
[Job pgAgent](/dbzero/maintenance/job_pgagent)): è una distanza, non una garanzia, e l'ordine
vero lo dà solo la convergenza.

---

### Due strade, la stessa procedura

| Dove | Chi la chiama | Quando |
| --- | --- | --- |
| dbdev e installazioni con pgAgent | il job `automations_lock_columns`, step `run_automations_lock_columns` | al giro del suo calendario |
| CI, database ricostruito da zero, ogni migrazione di sviluppo | la convergenza del rilascio (passata `ci_apply`) | `ci_ordine` 60: **dopo** `automations_attivo`, prima di `automations_delete_block` |

Lo step pgAgent chiama la procedura solo se `maintenance.fn_sveglia_accesa('automations_lock_columns')`
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

* **Il nome della corsa è il codice del processo**, `automations_lock_columns`: così il giornale
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

* **modo `SCHEDULED`.** Una regola di `dbops.automation_rules_tbl` — e una riga del registro
  dei lock — gira se il suo `exec_mode` è `AUTO` oppure uguale al modo della chiamata. Le
  regole `LOCK_COLUMNS` e `DATE_VALIDITA` del seed sono `AUTO`, come le righe del registro, e
  girano qui come in ogni altro modo. ⚠️ Il modo dice **chi** chiama, non **quando**: anche la
  convergenza del rilascio passa da questa procedura, e quindi chiama in `SCHEDULED`.
* **ambito non indicato.** Gli schemi li risolve `dbops.fn_resolve_scope`: quelli di
  `dbops.automation_scope` e, se il registro è vuoto, tutti gli schemi utente tranne `storico`.
* **niente simulazione.** Il DDL si fa. Per sapere che cosa farebbe un giro non si passa dalla
  procedura: si chiama il runner con la simulazione accesa, e `dbops.audit_log` registra le
  azioni previste.

---

### Codici errore

La procedura non ne solleva di suoi: l'errore è dei runner, e arriva com'è.

* `E_LOCK_COLUMNS` — il lock non converge: una colonna bloccata che il registro non nomina, o
  un trigger che non si è potuto creare, rigenerare o togliere.
* `E_DATE_VALIDITA` — il guard delle date non si è potuto montare su una tabella.

Un guasto dell'ambiente (connessione, risorse, privilegi, lock) non si traveste: il runner lo
scrive nel registro errori e lo rilancia col suo SQLSTATE.

---

### Test

* `db/pgtap/maintenance/test-proc-job-definer-v1.sql` — per ogni `maintenance.proc_*_job`:
  `SECURITY DEFINER`, `search_path` fissato, proprietario dello schema, nessun `EXECUTE` a
  `PUBLIC` né a `zeroerp_app`.
* `db/pgtap/dbops/test-processi-jobname-wrapper.sql` — il nome che il wrapper passa al giornale
  esiste in `dbops.processi`.
* `db/pgtap/dbops/test-processi-convergenza-ci.sql` — la procedura dichiarata esiste e ha
  girato con esito positivo sul database, e `automations_attivo` viene prima di `automations_lock_columns`.
* `db/pgtap/dbops/test-lock-columns-convergenza.sql` — il runner del lock: il vivo portato al
  dichiarato, e il fermo davanti a un lock che il registro non conosce.
* `db/pgtap/script/test-trgfn-guard-date-validita-v1.sql` — il guard delle date e il suo runner.

---

### Note di migrazione

* 2026-01-11 — nasce, ma senza un giro notturno: il runner girava solo alla migrazione.
* 2026-09-05 — nasce il job pgAgent `automations_lock_columns`, dieci minuti dopo la famiglia,
  e il processo entra a catalogo col nome che il wrapper passa al giornale
  (`brief-db-processi-automatici-residui-be`).
* 2026-09-23 — la corsa esegue anche il guard delle date di validità
  (`brief-db-guard-date-validita`).
* 2026-09-26 — non chiama più `dbops.fn_run_automations_drop_lock_trg`, ritirata: cancellava
  per funzione i lock delle tabelle che il registro non nominava, anche quelli scritti a mano,
  e su dbdev ne sono spariti così due. Togliere un lock è ora l'azione `TOGLIE` del runner
  (`brief-db-lock-di-colonna-fuori-registro`). Lo stesso giorno la procedura entra nella
  convergenza del rilascio (`brief-db-job-notturni-in-ci`).
* 2026-10-14 — diventa `SECURITY DEFINER`, come tutte le `maintenance.proc_*_job`
  (`brief-db-ruoli-di-sistema`).
* 2026-10-16 — lo step pgAgent passa dal cancello `maintenance.fn_sveglia_accesa`
  (`brief-db-processi-accensione-per-ambiente`).
* 2026-11-03 — pagina riscritta: lo scopo citava ancora la pulizia dei trigger obsoleti della
  funzione ritirata, e la pagina descriveva un giornale che non esiste (`maintenance.job_log`,
  `start_time`, `status`, `tx_id`) e un orario notturno inventato.

---

{% include-markdown "signature-core.md" %}
