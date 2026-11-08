## 📘 Documentazione Concettuale – Procedura `maintenance.proc_automations_cleanup_job`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — il processo `automations_cleanup`: job pgAgent, procedura e posto nella convergenza del rilascio
> * [maintenance.job_run_log](/dbzero/maintenance/tabelle/job_run_log) — il giornale in cui ogni corsa lascia la sua riga
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl) — le regole `CLEANUP_AT` e `CLEANUP_PURGE`, coi loro parametri
> * [dbops.automation_scope](/dbzero/dbops/tabelle/automation_scope) — gli schemi dell'ambito, che la procedura non fissa
> * [dbops.automation_cleanup_exclusions](/dbzero/dbops/tabelle/automation_cleanup_exclusions) — le tabelle che la pulizia salta
> * [dbops.audit_log](/dbzero/dbops/tabelle/audit_log) — dove resta scritta una tabella che si è opposta
>
> Approfondimento viste:
>
> * [dbops.vw_processi_programmazione](/dbzero/dbops/views/vw_processi_programmazione) — il calendario vivo e lo stato del processo
> * [maintenance.vw_job_run_da_guardare](/dbzero/maintenance/views/vw_job_run_da_guardare) — dove una corsa fallita diventa una cosa da guardare
>
> Approfondimento funzioni:
>
> * [dbops.fn_run_automations_cleanup](/dbzero/dbops/funzioni/fn_run_automations_cleanup) — il lavoro vero: la scadenza delle righe e la loro cancellazione
> * [maintenance.fn_run_and_log](/dbzero/maintenance/funzioni/fn_run_and_log) — il giornale da cui passa la chiamata, col lock e il verbale del fallimento
> * [maintenance.fn_sveglia_accesa](/dbzero/maintenance/funzioni/fn_sveglia_accesa) — il cancello dello step pgAgent
>
> Guide:
>
> * [Framework di Automazione DB, §4.5](/guide/automazione-db#45-cleanup-pulizia-record-scaduti) — le regole CLEANUP
> * [Framework di Automazione DB, §9](/guide/automazione-db#9-quando-girano-le-automazioni) — quando girano le automazioni

---

### 🎯 Scopo Principale

Il wrapper del processo `automations_cleanup`: esegue `dbops.fn_run_automations_cleanup` sull'ambito che il registro dichiara, che dà una scadenza
alle righe temporanee e cancella quelle scadute, passando dal giornale delle esecuzioni
sotto il codice del processo.

La procedura non aggiunge logica: delega a `maintenance.fn_run_and_log`, che apre la riga
della corsa in `maintenance.job_run_log`, esegue il runner e chiude la riga con l'esito.

---

### Che cosa allinea: le righe temporanee scadono, e se ne vanno

Il runner applica due regole, tabella per tabella:

* `CLEANUP_AT` scrive la scadenza di ogni riga (`cleanup_at`), da un periodo fisso a partire da
  un istante della riga, con una regola sola per tabella
  ([dbops.fn_cleanup_at_regola](/dbzero/dbops/funzioni/fn_cleanup_at_regola));
* `CLEANUP_PURGE` cancella, a lotti, le righe la cui scadenza è passata.

Salta le tabelle escluse in `dbops.automation_cleanup_exclusions`, quelle senza la colonna della
scadenza, e quelle a cui manca l'istante di partenza, e scrive ogni salto nel registro delle
azioni. ⛔ Non pulisce oggetti: non toglie trigger, tabelle o vincoli generati.

---

### ⭐ L'ambito lo decide il registro

La procedura non fissa gli schemi: passa al runner l'ambito vuoto, e il runner lo legge dal
registro, come fanno gli altri processi delle automazioni. Gli schemi sono quelli di
`dbops.automation_scope`, le tabelle quelle delle regole `CLEANUP_AT` e `CLEANUP_PURGE`. Così le
regole dichiarate su tabelle di qualunque schema — i log di `vendite`, le tabelle dei tentativi di
`config` — girano di notte e nella convergenza del rilascio. ⛔ Una regola attiva ha un
esecutore, o non sta nel registro.

Allargare l'ambito non accorcia la vita di nessun log. La scadenza si scrive solo dove manca, e
su ogni tabella vale una sola regola `CLEANUP_AT`: quella dichiarata sulla tabella vince sulla
generica su tutte, che vale solo dove non c'è altro.

---

### ⭐ Una tabella che si è opposta rende rossa la corsa

Ogni passo — la scadenza, ogni purge — gira in una sottotransazione. Se una tabella rifiuta la pulizia — un trigger che la
vuole immutabile, il guard sulla cancellazione di un log — il runner la salta, scrive in
`dbops.audit_log` una riga `ERROR` col motivo `BLOCKED_BY_TABLE` e lo SQLSTATE, e prosegue con le
altre. A fine giro restituisce il suo riepilogo, e il giornale lo legge: con almeno una tabella
che si è opposta la corsa è **rossa**, «riuscita con scarti» (`E_JOB_ESITO_CON_SCARTI`), e le
tabelle pulite restano pulite. Quali tabelle, e perché, sta nell'esito della corsa e nel registro
delle azioni. Un annullamento invece resta un annullamento: si rilancia, e la corsa fallisce.

---

### Due strade, la stessa procedura

| Dove | Chi la chiama | Quando |
| --- | --- | --- |
| dbdev e installazioni con pgAgent | il job `automations_cleanup_weekly`, step `run_automations_cleanup` | al giro del suo calendario |
| CI, database ricostruito da zero, ogni migrazione di sviluppo | la convergenza del rilascio (passata `ci_apply`) | `ci_ordine` 90: dopo `automations_overlap`, l'ultima delle automazioni |

Lo step pgAgent chiama la procedura solo se `maintenance.fn_sveglia_accesa('automations_cleanup')`
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

* **Il nome della corsa è il codice del processo**, `automations_cleanup`: così il giornale
  risale alla riga di `dbops.processi`, e la convergenza riconosce la corsa del suo giro.
  ⚠️ Il job pgAgent si chiama invece `automations_cleanup_weekly`: il legame fra i due nomi lo tiene
  la colonna `jobname_pgagent` del processo.
* **Una corsa alla volta.** La procedura passa come chiave un advisory lock sull'hash del
  codice. Se una corsa dello stesso processo è già in giro, la seconda non esegue niente e
  lascia una riga **saltata**: `saltata` vero, `ok` vuoto, già chiusa. Un salto non è una
  corsa riuscita.
* **Un fallimento si propaga, e il verbale resta.** Se il runner fallisce, `fn_run_and_log`
  scrive il verbale **fuori transazione**, con `maintenance.fn_job_run_log_failure`, e poi
  rilancia l'errore: lo step pgAgent fallisce, la convergenza si ferma, e la transazione si
  annulla con tutto il lavoro del giro. La riga rossa porta in `error_code` il codice di dominio
  del runner (`E_…`) o, in mancanza, lo SQLSTATE, che sta anche in `sqlstate`. Questo runner
  non passa dal registro errori: in `dbops.error_log` non resta niente. Da lì la corsa compare in
  `maintenance.vw_job_run_da_guardare`.
* **Gira come il proprietario.** La procedura è `SECURITY DEFINER`, con `search_path` fissato,
  e appartiene a `zeroerp_owner`: chiunque la chiami — `zeroerp_job` di notte, la convergenza —
  la pulizia gira come `zeroerp_owner`. Il giornale registra come ruolo
  della sessione chi si è collegato.

---

### `SCHEDULED`, l'ambito del registro, mai in simulazione

La procedura chiama il runner con tre scelte fisse:

* **modo `SCHEDULED`.** Una regola di `dbops.automation_rules_tbl` gira se il suo `exec_mode`
  è `AUTO` oppure uguale al modo della chiamata. Le regole `CLEANUP_AT` e `CLEANUP_PURGE` del seed
  sono `AUTO`, e girano qui come in ogni altro modo. ⚠️ Il modo dice **chi** chiama, non **quando**: anche la
  convergenza del rilascio passa da questa procedura, e quindi chiama in `SCHEDULED`.
* **l'ambito del registro**, come detto sopra.
* **niente simulazione.** Le scadenze si scrivono e le righe si cancellano. Per sapere che cosa farebbe un giro non si passa dalla
  procedura: si chiama il runner con la simulazione accesa, e `dbops.audit_log` registra le
  azioni previste.

---

### Codici errore

La procedura non ne solleva di suoi, e il runner non ha codici di dominio. Il rifiuto di una
tabella non è un errore della corsa (sopra); un annullamento sì, e arriva col suo SQLSTATE.

---

### Test

* `db/pgtap/maintenance/test-proc-job-definer-v1.sql` — per ogni `maintenance.proc_*_job`:
  `SECURITY DEFINER`, `search_path` fissato, proprietario dello schema, nessun `EXECUTE` a
  `PUBLIC` né a `zeroerp_app`.
* `db/pgtap/dbops/test-processi-jobname-wrapper.sql` — il nome che il wrapper passa al giornale
  esiste in `dbops.processi`.
* `db/pgtap/dbops/test-processi-convergenza-ci.sql` — la procedura dichiarata esiste e ha
  girato con esito positivo sul database.
* `db/pgtap/dbops/test-cleanup-framework.sql` — il runner: la scadenza, la cancellazione e la
  tabella che si oppone.
* `db/pgtap/maintenance/test-cleanup-job-ambito-registro-v1.sql` — la procedura passa l'ambito
  vuoto (presidio sul testo del corpo); ogni regola `CLEANUP_*` attiva punta a uno schema che
  l'ambito del registro comprende; il runner gira in simulazione con quell'ambito.

---

### Note di migrazione

* 2026-02-07 — nasce col job settimanale `automations_cleanup_weekly`.
* 2026-08-23 — il runner smette di morire su una tabella che si oppone: la salta e la scrive
  nel registro delle azioni.
* 2026-09-05 — il processo a catalogo prende il nome che il wrapper passa al giornale,
  `automations_cleanup`; prima portava quello del job pgAgent
  (`brief-db-processi-automatici-residui-be`).
* 2026-09-26 — entra nella convergenza del rilascio, che chiama le procedure dei job
  strutturali dove pgAgent non c'è (`brief-db-job-notturni-in-ci`).
* 2026-10-14 — diventa `SECURITY DEFINER`, come tutte le `maintenance.proc_*_job`
  (`brief-db-ruoli-di-sistema`).
* 2026-10-16 — lo step pgAgent passa dal cancello `maintenance.fn_sveglia_accesa`
  (`brief-db-processi-accensione-per-ambiente`).
* 2026-11-03 — pagina riscritta allo standard.
* 2026-11-03 — l'ambito si legge dal registro. Prima la procedura passava il solo schema `dbops`,
  e le regole su `vendite` e `config` e la cancellazione generica non le eseguiva nessuno: le
  righe scadute di quelle tabelle non venivano mai cancellate (`brief-db-revisione-maintenance`
  D4).
* 2026-11-04 — una tabella che si oppone rende rossa la corsa: il runner restituisce il suo
  riepilogo, e il giornale lo legge (D40 di `brief-db-revisione-dbops`). Prima la corsa era verde e
  il rifiuto stava solo nel registro delle azioni. Il wrapper non cambia.

---

{% include-markdown "signature-core.md" %}
