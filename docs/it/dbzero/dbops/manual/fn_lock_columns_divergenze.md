## 📘 Documentazione Concettuale – Funzione `dbops.fn_lock_columns_divergenze`

> **Ultimo aggiornamento**: 13 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_lock_columns](/dbzero/dbops/tabelle/automation_lock_columns) — il registro delle colonne da bloccare
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl) — la regola `LOCK_COLUMNS` che governa la tabella e dà il nome del trigger
>
> Approfondimento viste:
>
> * [dbops.vw_lock_columns_vivi](/dbzero/dbops/views/vw_lock_columns_vivi) — i trigger di lock vivi, da cui legge il vivo
>
> Approfondimento funzioni:
>
> * [dbops.fn_run_automations_lock_columns](/dbzero/dbops/funzioni/fn_run_automations_lock_columns) — esegue l'azione di ogni riga
> * [dbops.fn_resolve_scope](/dbzero/dbops/funzioni/fn_resolve_scope) — risolve l'ambito quando non si passano schemi
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — il giro delle automazioni e le sue regole

---

### 🎯 Scopo Principale

Risponde a una domanda: **i lock di colonna vivi sono quelli che il registro dichiara?** Per ogni
tabella dell'ambito in cui la risposta è no restituisce una riga, con l'azione che li riallinea.
Non modifica niente.

È il **criterio unico** della convergenza: lo usano il runner, che esegue l'azione di ogni riga,
e il presidio pgTAP, che ne pretende zero su tutto il database. Nessuno dei due ricalcola il
confronto per conto suo.

---

### ⭐ Chi governa la tabella: la regola `LOCK_COLUMNS`

Ogni tabella dell'ambito sta in uno di tre casi, secondo le regole `LOCK_COLUMNS` attive di
`dbops.automation_rules_tbl` che la coprono:

| Caso | Che cosa si confronta |
| --- | --- |
| una regola attiva del modo della corsa | l'atteso (sotto) contro il vivo |
| solo regole attive di **un altro** modo | niente: la tabella la governa l'altra corsa, e non si tocca. Altrimenti ogni corsa disferebbe ciò che l'altra crea |
| nessuna regola attiva (spenta, cancellata o mai scritta) | niente di atteso: il lock vivo si toglie |

Spegnere la regola vuol dire togliere i lock che monta: è la stessa regola di una riga del registro
spenta.

---

### Atteso e vivo

* **Atteso**, sulle tabelle che una regola del modo copre: `codice_interno`, se la tabella ce l'ha,
  con `E_CODICE_NON_MODIFICABILE`; poi le righe attive di `dbops.automation_lock_columns` su colonne
  che esistono, con il loro codice. Una riga di un altro `exec_mode` è attesa solo se la colonna è
  **già** bloccata: il modo dice quando un lock nasce, non quando esiste. Il nome atteso viene dal
  `name_template` della prima regola che copre la tabella (in ordine di priorità), obbligatorio
  per `LOCK_COLUMNS`: non c'è un template di ripiego.
* **Vivo**: **ogni** trigger su `script.trgfn_lock_columns` della tabella, qualunque nome abbia,
  letto da `dbops.vw_lock_columns_vivi`. Le colonne che blocca sono quelle nominate negli argomenti
  (le coppie colonna, codice) più quelle del suo `UPDATE OF`. ⭐ Il riconoscimento è per funzione,
  non per nome, ed è voluto: un lock scritto a mano con un altro nome deve essere visto.

---

### Le tre azioni

* `CREA` — c'è qualcosa da bloccare e nessun lock vivo.
* `RIGENERA` — i lock vivi non sono **esattamente un** trigger abilitato, col nome atteso, gli
  argomenti attesi nell'ordine atteso, `UPDATE OF` sulle colonne attese e la forma `BEFORE UPDATE`
  per riga. Un trigger disabilitato non blocca niente, quindi non è allineato.
* `TOGLIE` — niente da bloccare, e qualche lock vivo.

Le tabelle allineate non escono.

---

### ⭐ Le colonne perse: «ignota» non è «disattivata»

Ogni riga porta anche le **colonne perse**: colonne bloccate da un lock vivo, che la tabella ha
ancora, e che il registro **non nomina affatto**. Sono lock nati fuori dal registro, e convergere
li cancellerebbe in silenzio: il runner, se ce n'è anche una sola, si ferma.

Una colonna con una riga disattivata non è persa: è una decisione di togliere il blocco, e la
convergenza la toglie. Nemmeno `codice_interno` è mai persa: è la colonna implicita del framework,
e su una tabella senza regola si toglie senza fermare il giro.

---

### ⛔ Fuori dall'ambito

La funzione guarda solo le tabelle dell'ambito (`dbops.fn_resolve_scope`, `dbops.fn_table_in_scope`):
è il perimetro del runner. Fuori dall'ambito un lock lo monta una migrazione e il registro lo
dichiara comunque (vedi [dbops.automation_lock_columns](/dbzero/dbops/tabelle/automation_lock_columns)):
che le due cose coincidano non lo dice questa funzione, ma il presidio
`dbops/test-lock-columns-convergenza`, che legge `dbops.vw_lock_columns_vivi`.

---

### Test

* `db/pgtap/dbops/test-lock-columns-convergenza.sql` — su tutto il database la funzione non
  restituisce righe, e fuori dall'ambito lock vivi e registro coincidono; su uno schema di prova costruito a
  mano dà `RIGENERA` e `TOGLIE` con le colonne perse; dopo la convergenza non resta nessuna
  divergenza; una riga di un altro `exec_mode` resta attesa solo se la colonna è già bloccata; una
  tabella governata da un'altra corsa non si confronta; un lock disabilitato si rigenera; con la
  regola spenta il lock si toglie, e il runner si ferma solo su una colonna ignota al registro.

---

### Note di migrazione

* 2026-09-26 — nasce come criterio unico della convergenza dei lock di colonna
  (`brief-db-lock-di-colonna-fuori-registro`). Lo usa anche il changeSet di `90_end` che, il
  giorno della convergenza, ne ha preteso zero.
* 2026-11-08 — anche le tabelle senza regola attiva entrano nel confronto, il vivo si legge da
  `dbops.vw_lock_columns_vivi`, un trigger disabilitato non è allineato, e il ripiego morto sul
  codice vuoto esce (`20261109-60`, brief-db-revisione-dbops D32 e R2). Prima una tabella che
  nessuna regola copriva usciva dal confronto con i suoi lock.
* 2026-11-08 — il nome atteso viene solo dal template della regola: esce il ripiego
  `trg_{table}_a10_lock_columns_upd` (`20261109-73`, brief-db-revisione-dbops D20).
* 2026-11-13 — la regola vale per la tabella che nomina: `target_table` si confronta con `=`,
  non più con `ILIKE`, che faceva del `_` di un nome un jolly (una regola su `event_log` copriva
  anche una `eventXlog`). `*all` ha una forma sola, garantita dal CHECK
  `chk_automation_rules_tbl_target_table_nome_esatto` (`90_end/20261112-66`). Testata ri-ancorata
  con `%TYPE`, firma invariata (`20261112-74`).

---

{% include-markdown "signature-core.md" %}
