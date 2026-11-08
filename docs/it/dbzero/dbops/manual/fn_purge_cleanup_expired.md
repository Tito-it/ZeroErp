## 📘 Documentazione Concettuale – Funzione `dbops.fn_purge_cleanup_expired`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl) — la regola `CLEANUP_PURGE` da cui arriva la dimensione del lotto
>
> Approfondimento funzioni:
>
> * [dbops.fn_run_automations_cleanup](/dbzero/dbops/funzioni/fn_run_automations_cleanup) — il runner che la chiama, tabella per tabella
> * [dbops.fn_apply_cleanup_at](/dbzero/dbops/funzioni/fn_apply_cleanup_at) — il passo prima: scrive la scadenza
> * [vendite.trgfn_logs_guard_delete](/dbzero/vendite/funzioni/trgfn_logs_guard_delete) — un guard di cancellazione che lascia passare le righe scadute
>
> Guide:
>
> * [Automazione DB](/guide/automazione-db) — il framework delle automazioni e le regole di cleanup
> * [Audit e tracciabilità](/guide/audit-e-tracciabilita) — §7, manutenzione e retention

---

### 🎯 Scopo Principale

Cancella le righe di una tabella la cui scadenza (`cleanup_at`) è passata, a lotti di
dimensione fissa, e restituisce quante ne ha cancellate, o quante ne cancellerebbe in
simulazione. È il passo `CLEANUP_PURGE` del framework di cleanup.

---

### Che cosa è scaduto

Una riga è scaduta quando la sua scadenza è valorizzata e non è nel futuro. Una scadenza vuota
vuol dire «non scade mai»: quella riga non si cancella, qualunque sia la sua età.

La funzione non sa **perché** una riga scade: il termine l'ha scritto prima qualcun altro
([fn_apply_cleanup_at](/dbzero/dbops/funzioni/fn_apply_cleanup_at) o il trigger alla nascita).
Qui si legge solo la data.

---

### I lotti stanno nella stessa transazione

La cancellazione procede a lotti — 5000 righe se la dimensione manca, è zero o è negativa — a
partire dalle scadenze più vecchie, e si ferma al primo lotto che non cancella niente.

⚠️ I lotti limitano la dimensione di ogni singola istruzione, non la durata dei lock: tutta la
funzione gira nella transazione di chi la chiama, e i lock delle righe cancellate restano presi
fino alla sua fine.

⚠️ Il lotto si sceglie per posizione fisica della riga. Su una tabella partizionata la posizione
non identifica una riga fra partizioni diverse: la funzione va chiamata sulle partizioni, non sul
padre. Il runner lo fa già, perché scorre solo le tabelle semplici.

---

### I guard di cancellazione decidono loro

Il `DELETE` passa dai trigger della tabella. Un registro che vieta la cancellazione la deve
ammettere per le righe scadute — è ciò che fanno
[trgfn_logs_guard_delete](/dbzero/vendite/funzioni/trgfn_logs_guard_delete) e
[trgfn_event_log_append_only](/dbzero/vendite/funzioni/trgfn_event_log_append_only) — altrimenti
la funzione fallisce, e il runner registra la tabella come bloccata e va avanti.

### La colonna è sempre `cleanup_at`

La scadenza sta in `cleanup_at`, nome fisso del framework. Il parametro `p_cleanup_column` resta
nella firma ma può solo confermarlo: vuoto o `cleanup_at`; un altro nome è un errore. Se la tabella
non ha `cleanup_at`, la funzione non fa niente e restituisce zero.

⚠️ La funzione non legge le esclusioni del cleanup: chi la chiama a mano su una tabella esclusa
la tratta comunque. Il runner salta le tabelle escluse prima di chiamarla.

---

### Codici errore

* `E_GENERICO` — schema o tabella mancanti.
* `E_PARAMETRO_INVALIDO` — una colonna di scadenza diversa da `cleanup_at`.

---

### Test

* `db/pgtap/dbops/test-cleanup-framework.sql` — la simulazione conta le righe scadute, la
  cancellazione le toglie e lascia le altre (test 8-10).
* `db/pgtap/vendite/test-registri-fatturazione-scadenza-alla-nascita.sql` — su un registro dei log
  di fatturazione la simulazione vede la riga scaduta e il guard la lascia cancellare; su
  `fatture_log` il purge di un critico scaduto spegne il critico della fattura.

---

### Note di migrazione

* 2026-11-08 — la colonna della scadenza è sempre `cleanup_at` (`20261109-88`,
  brief-db-revisione-dbops, giro 10b): prima il parametro la poteva cambiare.

---

{% include-markdown "signature-core.md" %}
