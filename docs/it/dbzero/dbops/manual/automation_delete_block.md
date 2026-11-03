## 📘 Documentazione Concettuale – Tabella `dbops.automation_delete_block`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_scope](/dbzero/dbops/tabelle/automation_scope) — l'ambito: una riga fuori ambito non monta niente
>
> Approfondimento funzioni:
>
> * [dbops.fn_run_automations_delete_block](/dbzero/dbops/funzioni/fn_run_automations_delete_block) — il giro che legge il registro
> * [dbops.fn_apply_delete_block_trigger](/dbzero/dbops/funzioni/fn_apply_delete_block_trigger) — monta il trigger su una tabella
> * [script.trgfn_delete_block_by_guc](/dbzero/script/funzioni/trgfn_delete_block_by_guc) — la funzione del trigger, che rifiuta la cancellazione
> * [maintenance.proc_automations_delete_block_job](/dbzero/maintenance/funzioni/proc_automations_delete_block_job) — il wrapper del processo
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — il giro delle automazioni e le sue regole

---

### 🎯 Scopo Principale

Il registro delle tabelle su cui una cancellazione è **vietata**, salvo che la sessione abbia
acceso un interruttore (`guc_key`). Il giro delle automazioni legge il registro e monta su ogni
tabella il trigger che rifiuta la `DELETE` con `E_DELETE_NOT_ALLOWED`.

Il seed lo usa per le tabelle dei **ruoli** dei soggetti (clienti, fornitori, gestori, vettori…):
un ruolo non si cancella, si chiude. L'interruttore, per tutte, è
`zeroerp.maintenance_ruoli_delete`, ed è una porta di manutenzione, non una strada del dominio.

---

### Una riga per tabella

La chiave naturale è (`schema_name`, `table_name`): una tabella ha una sola regola di blocco.

* `guc_key` — il nome del parametro di sessione che, se vale `on`, lascia passare la
  cancellazione. Finisce come argomento del trigger: cambiarlo nel registro non cambia un trigger
  già montato.
* `trigger_name` — il nome del trigger, se non si vuole quello del template
  (`trg_<tabella>_a10_delete_block_dlt`). Vuoto vuol dire template.
* `meta` — note libere. Il seed vi scrive il codice del ruolo che la tabella rappresenta; nessuna
  funzione lo legge.

---

### ⚠️ Il registro aggiunge, non toglie

Il giro **crea** il trigger dove manca e salta le tabelle che lo hanno già (lo riconosce per
nome). Non ne toglie mai uno:

* `enabled` falso fa solo uscire la riga dal giro: un trigger già montato resta, e continua a
  bloccare;
* cancellare la riga ha lo stesso effetto;
* cambiare `trigger_name` dopo il primo montaggio ne monta un secondo, accanto al vecchio.

Una tabella che non esiste più si salta: nel dry run il salto è dichiarato in audit
(`TABLE_NOT_FOUND`), nella corsa vera passa in silenzio.

---

### Note di migrazione

* 2026-01-23 — nasce, con il seed delle otto tabelle dei ruoli dei soggetti.

---

{% include-markdown "signature-core.md" %}
