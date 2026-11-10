## 📘 Documentazione Concettuale – Funzione `dbops.fn_apply_cleanup_at`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl) — le regole `CLEANUP_AT` da cui arrivano termine e colonna base
>
> Approfondimento funzioni:
>
> * [dbops.fn_run_automations_cleanup](/dbzero/dbops/funzioni/fn_run_automations_cleanup) — il runner che la chiama, tabella per tabella
> * [dbops.fn_cleanup_at_regola](/dbzero/dbops/funzioni/fn_cleanup_at_regola) — la regola da cui il runner prende termine, colonna base e ricalcolo
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

### Le colonne

* **La colonna base è obbligatoria.** La sceglie chi chiama: il runner la prende da
  [fn_cleanup_at_regola](/dbzero/dbops/funzioni/fn_cleanup_at_regola), la dichiarata o la prima
  della catena. La funzione non la indovina.
* **La colonna della scadenza è sempre `cleanup_at`**, nome fisso del framework, e non è un
  parametro.
* Se la tabella non ha `cleanup_at` o non ha la colonna base, la funzione non fa niente e
  restituisce zero.
* In simulazione (`p_dry_run`) conta le righe che aggiornerebbe, senza scrivere.

⚠️ La funzione non legge le esclusioni del cleanup: chi la chiama a mano su una tabella esclusa
la tratta comunque. Il runner salta le tabelle escluse prima di chiamarla.

---

### Codici errore

* `E_GENERICO` — schema o tabella mancanti, oppure termine mancante o negativo.
* `E_PARAMETRO_INVALIDO` — colonna base mancante.

---

### Test

* `db/pgtap/dbops/test-cleanup-framework.sql` — la simulazione conta le righe senza scadenza,
  l'esecuzione le valorizza tutte (test 5-7), e il runner la usa sulle tabelle in ambito.
* `db/pgtap/dbops/test-cleanup-at-regola-unica-v1.sql` — la scadenza che il runner scrive con lei
  è quella che il trigger alla nascita aveva scritto; una riga con la base vuota non si tocca.
* `db/pgtap/dbops/test-nomi-e-chiavi-registri-v1.sql` — la firma non ha più `p_cleanup_column`.

---

### Note di migrazione

* 2026-11-08 — la colonna base è obbligatoria e la colonna della scadenza è sempre `cleanup_at`
  (`20261109-88`, brief-db-revisione-dbops, giro 10b). Prima la base, se mancava, era
  `data_insert` — una terza regola accanto a quelle del trigger e del runner — e la colonna della
  scadenza si poteva cambiare col parametro.
* 2026-11-09 — il parametro `p_cleanup_column` esce dalla firma: poteva solo confermare
  `cleanup_at`. La firma è ora schema, tabella, colonna base, termine in giorni, ricalcolo e
  simulazione; la funzione è stata ricreata e il runner la chiama così (`20261110-36`,
  brief-db-revisione-dbops, giro 10c).

---

{% include-markdown "signature-core.md" %}
