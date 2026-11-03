## 📘 Documentazione Concettuale – Funzione `dbops.fn_fix_lock_codice_interno_triggers`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_lock_columns](/dbzero/dbops/tabelle/automation_lock_columns) — il registro da cui oggi nascono i lucchetti di colonna
>
> Approfondimento funzioni:
>
> * [script.trgfn_lock_columns](/dbzero/script/funzioni/trgfn_lock_columns) — la funzione dei trigger che rimonta
> * [dbops.fn_run_automations_lock_columns](/dbzero/dbops/funzioni/fn_run_automations_lock_columns) — il runner che oggi monta e allinea i lucchetti
> * [dbops.fn_rename_triggers_by_order](/dbzero/dbops/funzioni/fn_rename_triggers_by_order) — l'altra utility della stessa campagna
>
> Guide:
>
> * [Linee guida Trigger](/linee-guida-trigger#i-trigger-generati) — i lucchetti sono trigger generati, e non si scrivono a mano

---

### 🎯 Scopo Principale

Utility **una tantum** del settembre 2025: rimonta i trigger del lucchetto sul codice interno,
quelli su `script.trgfn_lock_columns`, legandoli a `UPDATE OF` la colonna lucchettata e dando
loro un nome uniforme. Oggi non la chiama nessun runner, job o backend: è una **candidata al
ritiro**.

Esiste ancora perché il changeSet che la crea, nel primo albero (`db/changelog/migrations/50_dbops`),
gira su ogni database nuovo, e un secondo changeSet la **esegue** davvero, su tutti gli schemi.

---

### Che cosa fa

* Cerca i trigger utente su `script.trgfn_lock_columns` il cui nome contiene `codice_interno` o
  `upd_lock_codiceinterno`, in tutti gli schemi o in quello indicato.
* Dalla definizione ricava la funzione e i suoi argomenti, e il primo argomento come colonna.
* Sceglie la colonna dell'`UPDATE OF`: il primo argomento se è chiesto l'allineamento (il
  default), altrimenti la colonna forzata dal chiamante, altrimenti `codice_interno`.
* Toglie il trigger vecchio, se è chiesto (il default), e crea `trg_a10_upd_<tabella>_lock_<colonna>`,
  `BEFORE UPDATE OF` la colonna, solo quando il valore cambia, con la stessa funzione e gli stessi
  argomenti.
* In anteprima (il default) restituisce le istruzioni che eseguirebbe; altrimenti le esegue.
  Non ha una rete per gli errori: un `CREATE` che fallisce ferma tutta la chiamata.

---

### ⛔ Perché non si rilancia

* **I lucchetti di colonna oggi li monta il framework**, dal registro
  `dbops.automation_lock_columns`, con il runner `dbops.fn_run_automations_lock_columns` che li
  riconosce per funzione e li allinea. Un lucchetto montato da questa utility è un trigger
  generato scritto a mano, che le linee guida vietano.
* **Il nome che produce non è quello di oggi**: la fase in testa e l'evento prima della tabella
  (`trg_a10_upd_…`), dove il framework scrive `trg_<tabella>_a10_lock_columns_upd`.
* Senza togliere il vecchio (`p_drop_old` falso) monta un **secondo** lucchetto sulla stessa
  tabella.

---

### Note di migrazione

* 2025-09-21 — nasce nel primo albero dei changeSet, ed è eseguita su tutti gli schemi per
  uniformare i lucchetti sul codice interno. Il lucchetto di colonna è passato poi al registro
  `dbops.automation_lock_columns` e al suo runner.

---

{% include-markdown "signature-core.md" %}
