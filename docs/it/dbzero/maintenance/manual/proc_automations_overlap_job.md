## 📘 Documentazione Concettuale – Procedura `maintenance.proc_automations_overlap_job`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — il processo `automations_overlap`: job pgAgent, procedura e posto nella convergenza del rilascio
> * [maintenance.job_run_log](/dbzero/maintenance/tabelle/job_run_log) — il giornale in cui ogni corsa lascia la sua riga
> * [dbops.automazione_overlap](/dbzero/dbops/tabelle/automazione_overlap) — la configurazione: chiave, periodo, predicato, `active` ed `exec_mode` di ogni tabella
>
> Approfondimento viste:
>
> * [dbops.vw_processi_programmazione](/dbzero/dbops/views/vw_processi_programmazione) — il calendario vivo e lo stato del processo
> * [maintenance.vw_job_run_da_guardare](/dbzero/maintenance/views/vw_job_run_da_guardare) — dove una corsa fallita diventa una cosa da guardare
>
> Approfondimento funzioni:
>
> * [dbops.fn_apply_automazione_overlap](/dbzero/dbops/funzioni/fn_apply_automazione_overlap) — il lavoro vero: i vincoli `EXCLUDE` che mancano
> * [maintenance.fn_run_and_log](/dbzero/maintenance/funzioni/fn_run_and_log) — il giornale da cui passa la chiamata, col lock e il verbale del fallimento
> * [maintenance.fn_sveglia_accesa](/dbzero/maintenance/funzioni/fn_sveglia_accesa) — il cancello dello step pgAgent
>
> Guide:
>
> * [Framework di Automazione DB, §4.3](/guide/automazione-db#43-overlap-anti-sovrapposizione-temporale) — la regola OVERLAP
> * [Framework di Automazione DB, §9](/guide/automazione-db#9-quando-girano-le-automazioni) — quando girano le automazioni

---

### 🎯 Scopo Principale

Il wrapper del processo `automations_overlap`: esegue `dbops.fn_apply_automazione_overlap`, che ricrea i vincoli `EXCLUDE` mancanti
dalle righe accese di `dbops.automazione_overlap`, passando dal giornale delle esecuzioni
sotto il codice del processo.

La procedura non aggiunge logica: delega a `maintenance.fn_run_and_log`, che apre la riga
della corsa in `maintenance.job_run_log`, esegue il runner e chiude la riga con l'esito.

---

### ⭐ Auto-guarigione: un `EXCLUDE` sparito torna al giro dopo

Per ogni riga accesa della configurazione, il runner crea sulla tabella il vincolo `EXCLUDE`
che impedisce a due righe con la stessa chiave di avere periodi sovrapposti: la chiave è fatta
di colonne e di espressioni, il periodo è una colonna intervallo o la coppia delle date, e un
predicato rende il vincolo parziale.

Salta la riga, e lo scrive nel registro delle azioni, quando la tabella non esiste
(`TABLE_NOT_FOUND`), quando manca la chiave, quando mancano le colonne del periodo, e quando
sulla tabella c'è già un vincolo che fa il lavoro: un `EXCLUDE`
che nomina la colonna del periodo (`EXCLUDE_EXISTS`) o un vincolo temporale
`UNIQUE … WITHOUT OVERLAPS` (`TEMPORAL_UNIQUE_EXISTS`). A regime quindi non fa niente; ma se un
`EXCLUDE` viene tolto per errore, il giro dopo lo ricrea.

⚠️ Il runner **crea e non modifica**: cambiare la chiave o il predicato di una tabella chiede di
togliere prima il vincolo vecchio, che altrimenti il giro trova e salta.

---

### ⚠️ Una tabella sparita si salta, righe sovrapposte fermano il giro

Il registro non ha una chiave esterna verso il catalogo, e non può averla: una riga può restare
indietro rispetto a una tabella rinominata o ritirata. Quella riga è un **salto dichiarato**,
come gli altri: il runner la scrive nel registro delle azioni col motivo `TABLE_NOT_FOUND` e
passa alla successiva, e le altre tabelle ricevono il loro vincolo.

Il runner invece non cattura gli altri errori, e un errore ferma la corsa intera, non solo la sua
tabella: il caso tipico è una tabella che ha già righe sovrapposte, su cui il vincolo non si può
creare. L'errore arriva col suo SQLSTATE, e la corsa annulla anche i vincoli creati prima nello
stesso giro.

---

### Due strade, la stessa procedura

| Dove | Chi la chiama | Quando |
| --- | --- | --- |
| dbdev e installazioni con pgAgent | il job `automations_overlap`, step `run_automations_overlap` | al giro del suo calendario |
| CI, database ricostruito da zero, ogni migrazione di sviluppo | la convergenza del rilascio (passata `ci_apply`) | `ci_ordine` 80: dopo `automations_delete_block`, prima di `automations_cleanup` |

Lo step pgAgent chiama la procedura solo se `maintenance.fn_sveglia_accesa('automations_overlap')`
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

* **Il nome della corsa è il codice del processo**, `automations_overlap`: così il giornale
  risale alla riga di `dbops.processi`, e la convergenza riconosce la corsa del suo giro.
* **Una corsa alla volta.** La procedura passa come chiave un advisory lock sull'hash del
  codice. Se una corsa dello stesso processo è già in giro, la seconda non esegue niente e
  lascia una riga **saltata**: `saltata` vero, `ok` vuoto, già chiusa. Un salto non è una
  corsa riuscita.
* **Un fallimento si propaga, e il verbale resta.** Se il runner fallisce, `fn_run_and_log`
  scrive il verbale **fuori transazione**, con `maintenance.fn_job_run_log_failure`, e poi
  rilancia l'errore: lo step pgAgent fallisce, la convergenza si ferma, e la transazione si
  annulla con tutto il DDL del giro. La riga rossa porta in `error_code` il codice di dominio
  del runner (`E_…`) o, in mancanza, lo SQLSTATE, che sta anche in `sqlstate`. Questo runner
  non passa dal registro errori: in `dbops.error_log` non resta niente. Da lì la corsa compare in
  `maintenance.vw_job_run_da_guardare`.
* **Gira come il proprietario.** La procedura è `SECURITY DEFINER`, con `search_path` fissato,
  e appartiene a `zeroerp_owner`: chiunque la chiami — `zeroerp_job` di notte, la convergenza —
  il DDL gira come `zeroerp_owner`, e i vincoli nascono suoi. Il giornale registra come ruolo
  della sessione chi si è collegato.

---

### `SCHEDULED`, tutto il registro, mai in simulazione

La procedura chiama il runner con tre scelte fisse:

* **modo `SCHEDULED`.** Una riga di `dbops.automazione_overlap` gira se il suo `exec_mode` è
  `AUTO` oppure uguale al modo della chiamata. ⚠️ Il modo dice **chi** chiama, non
  **quando**: anche la convergenza del rilascio passa da questa procedura, e quindi chiama in
  `SCHEDULED`.
* **nessun ambito.** Il runner non ha un elenco di schemi e non legge
  `dbops.automation_scope`: lavora su tutte le righe accese della configurazione, dovunque
  stia la loro tabella.
* **niente simulazione.** Il DDL si fa. Per sapere che cosa farebbe un giro non si passa dalla
  procedura: si chiama il runner con la simulazione accesa, e `dbops.audit_log` registra le
  azioni previste.

---

### Codici errore

La procedura non ne solleva di suoi, e il runner non ha codici di dominio: un errore arriva
col suo SQLSTATE, e `error_code` del giornale riporta quello.

---

### Test

* `db/pgtap/maintenance/test-proc-job-definer-v1.sql` — per ogni `maintenance.proc_*_job`:
  `SECURITY DEFINER`, `search_path` fissato, proprietario dello schema, nessun `EXECUTE` a
  `PUBLIC` né a `zeroerp_app`.
* `db/pgtap/dbops/test-processi-jobname-wrapper.sql` — il nome che il wrapper passa al giornale
  esiste in `dbops.processi`.
* `db/pgtap/dbops/test-processi-convergenza-ci.sql` — la procedura dichiarata esiste e ha
  girato con esito positivo sul database.
* `db/pgtap/dbops/test-fn-apply-automazione-overlap-key-expressions-v1.sql` e
  `db/pgtap/dbops/test-fn-apply-automazione-overlap-where-predicate-v1.sql` — il runner: le
  chiavi su espressione e i vincoli parziali.
* `db/pgtap/dbops/test-overlap-tabella-sparita-v1.sql` — una riga del registro su una tabella
  che non esiste non ferma il giro, e lascia nel registro delle azioni il salto col motivo
  `TABLE_NOT_FOUND`.

---

### Note di migrazione

* 2026-06-02 — nasce col suo job notturno: fino a quel giorno OVERLAP aveva il seed e
  l'applicazione ma nessun giro, e la configurazione restava inerte (`refactor-overlap-v2`).
* 2026-09-26 — entra nella convergenza del rilascio, che chiama le procedure dei job
  strutturali dove pgAgent non c'è (`brief-db-job-notturni-in-ci`).
* 2026-10-14 — diventa `SECURITY DEFINER`, come tutte le `maintenance.proc_*_job`
  (`brief-db-ruoli-di-sistema`).
* 2026-10-16 — lo step pgAgent passa dal cancello `maintenance.fn_sveglia_accesa`
  (`brief-db-processi-accensione-per-ambiente`).
* 2026-11-03 — una riga del registro su una tabella sparita diventa un salto dichiarato
  (`TABLE_NOT_FOUND`). Prima fermava il giro intero con lo SQLSTATE grezzo, e le tabelle che
  venivano dopo restavano senza vincolo (`brief-db-revisione-maintenance` D6).

---

{% include-markdown "signature-core.md" %}
