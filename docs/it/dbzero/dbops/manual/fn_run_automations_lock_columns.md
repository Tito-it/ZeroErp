## 📘 Documentazione Concettuale – Funzione `dbops.fn_run_automations_lock_columns`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_lock_columns](/dbzero/dbops/tabelle/automation_lock_columns) — il registro delle colonne da bloccare
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl) — la regola `LOCK_COLUMNS` e il suo template di nome
> * [dbops.audit_log](/dbzero/dbops/tabelle/audit_log) — dove il dry run scrive che cosa farebbe
>
> Approfondimento funzioni:
>
> * [dbops.fn_lock_columns_divergenze](/dbzero/dbops/funzioni/fn_lock_columns_divergenze) — il confronto fra atteso e vivo, che qui si esegue
> * [script.trgfn_lock_columns](/dbzero/script/funzioni/trgfn_lock_columns) — la funzione dei trigger che monta
> * [maintenance.proc_automations_lock_columns_job](/dbzero/maintenance/funzioni/proc_automations_lock_columns_job) — il wrapper del processo serale
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — il giro delle automazioni e le sue regole

---

### 🎯 Scopo Principale

Porta i **lock di colonna** delle tabelle dell'ambito allo stato che il registro dichiara. Un lock
di colonna è un trigger su `script.trgfn_lock_columns` che rifiuta il cambio di una colonna dopo
la nascita della riga.

⭐ **Converge, non si limita a creare**: un lock già montato si rigenera se il registro è cambiato,
e si toglie se non c'è più niente da bloccare. Il confronto non lo fa questa funzione, ma
[fn_lock_columns_divergenze](/dbzero/dbops/funzioni/fn_lock_columns_divergenze): qui si esegue
l'azione di ogni tabella che diverge.

---

### Le azioni

* `CREA` — monta il trigger col nome atteso, `BEFORE UPDATE OF` le colonne attese, con le coppie
  colonna e codice come argomenti.
* `RIGENERA` — toglie **tutti** i lock vivi della tabella, qualunque nome abbiano, e monta quello
  atteso. Un lock scritto a mano con un altro nome viene così riassorbito.
* `TOGLIE` — toglie tutti i lock vivi della tabella.

Una tabella già allineata non si tocca: un secondo giro non ricrea niente. Un lock vivo si
riconosce sempre dalla funzione, altrimenti uno scritto a mano resterebbe invisibile. Il nome
atteso viene dal template della regola `LOCK_COLUMNS`, obbligatorio: non c'è un nome di ripiego.

---

### ⛔ Si ferma prima di cancellare un lock che il registro non conosce

Prima di qualunque DDL, e per tutte le tabelle insieme, la funzione guarda le **colonne perse**:
colonne bloccate da un trigger vivo che il registro non nomina affatto. Se ce n'è anche una
sola, solleva `E_LOCK_COLUMNS` e nomina in un solo errore tutte le tabelle e le colonne in
quella situazione: chi rilascia riceve l'elenco intero, non la prima tabella. Convergere
cancellerebbe quei lock in silenzio.

Il rimedio è una riga in `dbops.automation_lock_columns`: attiva se il lock va tenuto,
disattivata se va tolto. Una riga disattivata è una decisione, e quella colonna si toglie senza
fermarsi.

---

### Il dry run non tocca niente e non si ferma

Con `p_dry_run` vero la funzione non fa DDL e non si ferma sulle colonne perse: scrive in
`dbops.audit_log`, per ogni tabella che diverge, l'azione che farebbe, le colonne attese, i
trigger vivi e le colonne perse. Quelle righe di audit sono firmate col nome di questa funzione,
`dbops.fn_run_automations_lock_columns`.

---

### Un errore ferma tutto il giro

Un DDL che fallisce su una tabella solleva `E_LOCK_COLUMNS` con la tabella e l'azione nel
contesto, e annulla il giro intero: nessuna tabella resta a metà, e nessuna viene convergita.
Un guasto dell'**ambiente** (connessione, risorse, privilegio, lock) si scrive nel registro
errori con lo stesso codice e poi si rilancia col suo SQLSTATE originale, perché il presidio dei
job lo mandi a chi gestisce l'ambiente e non allo sviluppo.

---

### Chi la chiama

* la passata `ci_apply` di ogni rilascio, in modo `CI`;
* il processo `automations_lock_columns`, ogni sera alle 21:10, tramite
  `maintenance.proc_automations_lock_columns_job`, in modo `SCHEDULED`: dopo la famiglia delle
  automazioni delle 21:00, perché una tabella nuova abbia già i suoi trigger. Lo stesso wrapper
  esegue subito dopo `dbops.fn_run_automations_date_validita`;
* alcuni changeSet `90_end` che, dopo aver aggiunto righe al registro, convergono subito.

---

### Codici errore

* `E_LOCK_COLUMNS` — una o più colonne bloccate da un lock che il registro non nomina (prima di
  ogni DDL), oppure un DDL fallito su una tabella.

---

### Test

* `db/pgtap/dbops/test-lock-columns-convergenza.sql` — il runner si ferma e nomina le colonne
  perse senza toccare i lock scritti a mano; il dry run non fa DDL; col registro completo resta un
  solo lock col nome da template e gli argomenti attesi; un secondo giro non ricrea il trigger;
  una colonna aggiunta al registro arriva nel lock vivo, e il lock funziona.
* I pgTAP dei singoli lock di dominio la chiamano per montare il lock che provano, per esempio
  `db/pgtap/vendite/test-ordini-lock-cliente.sql` e
  `db/pgtap/catalogo/test-articoli-seed-uom-base-lock.sql`.

---

### Note di migrazione

* 2026-01-10 — nasce: creava il trigger solo dove mancava.
* 2026-09-26 — converge, e assorbe `fn_run_automations_drop_lock_trg` (ritirata), che ogni sera
  cancellava i lock che il registro non nominava, anche quelli scritti a mano
  (`brief-db-lock-di-colonna-fuori-registro`). Prima un lock nato una volta non si riallineava
  più: codici ritirati negli argomenti, colonne aggiunte al registro che non arrivavano mai.
* 2026-10-16 — un guasto dell'ambiente si rilancia col suo SQLSTATE invece di diventare un errore
  di dominio (`brief-db-presidio-job-run-a-chi-tocca`).
* 2026-11-04 — ritirato l'orchestratore `dbops.fn_run_automations`, che la chiamava per la parte
  `LOCK_COLUMNS`; la firma del dry run ne porta ancora il nome (`brief-db-revisione-dbops`).
* 2026-11-08 — il dry run firma col proprio nome; il nome atteso del lock viene solo dal template
  della regola, senza ripiego (`20261109-73`, brief-db-revisione-dbops R1, D20).

---

{% include-markdown "signature-core.md" %}
