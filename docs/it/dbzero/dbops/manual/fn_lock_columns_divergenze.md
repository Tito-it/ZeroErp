## 📘 Documentazione Concettuale – Funzione `dbops.fn_lock_columns_divergenze`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_lock_columns](/dbzero/dbops/tabelle/automation_lock_columns) — il registro delle colonne da bloccare
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl) — la regola `LOCK_COLUMNS` che dà il nome del trigger
>
> Approfondimento funzioni:
>
> * [dbops.fn_run_automations_lock_columns](/dbzero/dbops/funzioni/fn_run_automations_lock_columns) — esegue l'azione di ogni riga
> * [dbops.fn_trigger_argomenti](/dbzero/dbops/funzioni/fn_trigger_argomenti) — legge gli argomenti dei trigger vivi
> * [dbops.fn_resolve_scope](/dbzero/dbops/funzioni/fn_resolve_scope) — risolve l'ambito quando non si passano schemi
> * [script.trgfn_lock_columns](/dbzero/script/funzioni/trgfn_lock_columns) — la funzione che riconosce un lock vivo
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — il giro delle automazioni e le sue regole

---

### 🎯 Scopo Principale

Risponde a una domanda: **i lock di colonna vivi sono quelli che il registro dichiara?** Per ogni
tabella in cui la risposta è no restituisce una riga, con l'azione che li riallinea. Non modifica
niente.

È il **criterio unico** della convergenza: lo usano il runner, che esegue l'azione di ogni riga,
e il presidio pgTAP, che ne pretende zero su tutto il database. Nessuno dei due ricalcola il
confronto per conto suo.

---

### Atteso e vivo

* **Atteso**: `codice_interno`, se la tabella ce l'ha, con `E_CODICE_NON_MODIFICABILE`; poi le
  righe attive di `dbops.automation_lock_columns` su colonne che esistono, con il loro codice. Una
  riga di un altro `exec_mode` è attesa solo se la colonna è **già** bloccata: il modo dice
  quando un lock nasce, non quando esiste. Il nome atteso viene dal `name_template` della prima
  regola `LOCK_COLUMNS` attiva che copre la tabella (in ordine di priorità), e in mancanza dal
  template standard `trg_{table}_a10_lock_columns_upd`.
* **Vivo**: **ogni** trigger su `script.trgfn_lock_columns` della tabella, qualunque nome abbia.
  Le colonne che blocca sono quelle nominate negli argomenti (le coppie colonna, codice) più
  quelle del suo `UPDATE OF`. ⭐ Il riconoscimento è per funzione, non per nome, ed è voluto: un
  lock scritto a mano con un altro nome deve essere visto.

---

### Le tre azioni

* `CREA` — c'è qualcosa da bloccare e nessun lock vivo.
* `RIGENERA` — i lock vivi non sono **esattamente un** trigger col nome atteso, gli argomenti
  attesi nell'ordine atteso, `UPDATE OF` sulle colonne attese e la forma `BEFORE UPDATE` per riga.
* `TOGLIE` — niente da bloccare, e qualche lock vivo.

Le tabelle allineate non escono. Escono solo le tabelle dell'ambito coperte da una regola
`LOCK_COLUMNS` attiva per quel modo di esecuzione: ⚠️ su una tabella che nessuna regola copre,
un lock vivo non è né atteso né da togliere, e la funzione non lo vede.

---

### ⭐ Le colonne perse: «ignota» non è «disattivata»

Ogni riga porta anche le **colonne perse**: colonne bloccate da un lock vivo, che la tabella ha
ancora, e che il registro **non nomina affatto**. Sono lock nati fuori dal registro, e convergere
li cancellerebbe in silenzio: il runner, se ce n'è anche una sola, si ferma.

Una colonna con una riga disattivata non è persa: è una decisione di togliere il blocco, e la
convergenza la toglie.

---

### Test

* `db/pgtap/dbops/test-lock-columns-convergenza.sql` — su tutto il database la funzione non
  restituisce righe; su uno schema di prova costruito a mano dà `RIGENERA` e `TOGLIE` con le
  colonne perse; dopo la convergenza non resta nessuna divergenza; una riga di un altro
  `exec_mode` resta attesa solo se la colonna è già bloccata.

---

### Note di migrazione

* 2026-09-26 — nasce come criterio unico della convergenza dei lock di colonna
  (`brief-db-lock-di-colonna-fuori-registro`). Lo usa anche il changeSet di `90_end` che, il
  giorno della convergenza, ne ha preteso zero.

---

{% include-markdown "signature-core.md" %}
