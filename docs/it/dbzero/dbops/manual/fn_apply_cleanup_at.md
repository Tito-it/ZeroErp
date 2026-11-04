## 📘 Documentazione Concettuale – Funzione `dbops.fn_apply_cleanup_at`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl) — le regole `CLEANUP_AT` da cui arrivano termine e colonne
>
> Approfondimento funzioni:
>
> * [dbops.fn_run_automations_cleanup](/dbzero/dbops/funzioni/fn_run_automations_cleanup) — il runner che la chiama, tabella per tabella
> * [dbops.fn_purge_cleanup_expired](/dbzero/dbops/funzioni/fn_purge_cleanup_expired) — il passo dopo: cancella le righe scadute
> * [dbops.trgfn_cleanup_at_alla_nascita](/dbzero/dbops/funzioni/trgfn_cleanup_at_alla_nascita) — l'altra via: la scadenza scritta all'INSERT
>
> Guide:
>
> * [Automazione DB](/guide/automazione-db) — il framework delle automazioni e le regole di cleanup
> * [Audit e tracciabilità](/guide/audit-e-tracciabilita) — §7, manutenzione e retention

---

### 🎯 Scopo Principale

Scrive la scadenza (`cleanup_at`) delle righe di una tabella: colonna di base più un termine
fisso in giorni. È il passo `CLEANUP_AT` del framework di cleanup, e restituisce quante righe
ha aggiornato, o quante ne aggiornerebbe in simulazione.

---

### Riempie i vuoti, o ricalcola tutto

Il comportamento lo decide `p_apply_on_update`:

* **falso** (il default, e il caso di tutte le regole del seed): tocca solo le righe che non
  hanno ancora una scadenza e che hanno la colonna di base valorizzata. Una scadenza già
  scritta — dal trigger alla nascita, o da un giro precedente — non si cambia;
* **vero**: ricalcola ogni riga con la colonna di base valorizzata la cui scadenza è vuota o
  diversa da quella che il termine darebbe oggi. Serve quando il termine cambia e deve valere
  anche per il pregresso.

Una riga con la colonna di base vuota non riceve mai una scadenza, quindi non scade.

⚠️ È un `UPDATE`: passa dai trigger di `UPDATE` della tabella e riscrive le colonne di
aggiornamento. Su un registro che non deve cambiare dopo la nascita la scadenza si scrive
all'`INSERT` con [trgfn_cleanup_at_alla_nascita](/dbzero/dbops/funzioni/trgfn_cleanup_at_alla_nascita),
e questa funzione resta per le righe nate prima del trigger.

---

### Le colonne mancanti non sono un errore

* La colonna di scadenza, se non indicata, è `cleanup_at`; la colonna di base, se non
  indicata, è `data_insert`. Il runner passa sempre una colonna di base: quella dichiarata
  nella regola, o la prima che trova nella sua catena di ripiego.
* Se una delle due colonne non esiste sulla tabella, la funzione non fa niente e restituisce
  zero.
* In simulazione (`p_dry_run`) conta le righe che aggiornerebbe, senza scrivere.

---

### Codici errore

* `E_GENERICO` — schema o tabella mancanti, oppure termine mancante o negativo.

---

### Test

* `db/pgtap/dbops/test-cleanup-framework.sql` — la simulazione conta le righe senza scadenza,
  l'esecuzione le valorizza tutte (test 5-7), e il runner la usa sulle tabelle in ambito.

---

{% include-markdown "signature-core.md" %}
