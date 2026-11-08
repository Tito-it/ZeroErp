## 📘 Documentazione Concettuale – Tabella `dbops.automation_cleanup_exclusions`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl) — le regole `CLEANUP_AT` e `CLEANUP_PURGE` da cui l'esclusione sottrae una tabella
> * [dbops.automation_scope](/dbzero/dbops/tabelle/automation_scope) — l'ambito che il giro percorre prima di guardare le esclusioni
> * [dbops.audit_log](/dbzero/dbops/tabelle/audit_log) — dove il salto lascia traccia
>
> Approfondimento funzioni:
>
> * [dbops.fn_cleanup_esclusa](/dbzero/dbops/funzioni/fn_cleanup_esclusa) — l'unica lettura della tabella: la tabella è esclusa?
> * [dbops.fn_cleanup_at_regola](/dbzero/dbops/funzioni/fn_cleanup_at_regola) — la regola di scadenza: per una tabella esclusa non si applica
> * [dbops.fn_run_automations_cleanup](/dbzero/dbops/funzioni/fn_run_automations_cleanup) — il giro di pulizia, che salta la tabella esclusa
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — il giro delle automazioni e le sue regole

---

### 🎯 Scopo Principale

L'elenco delle tabelle che il cleanup **non tocca**: per una tabella esclusa nessuno scrive la
scadenza `cleanup_at` — né il giro di pulizia né il trigger alla nascita — e non si cancellano le
righe scadute, qualunque regola la copra.

Serve quando una regola generica (per esempio una `CLEANUP_PURGE` su tutte le tabelle di uno
schema) prenderebbe anche una tabella che va conservata. La chiave è la coppia
(`schema_name`, `table_name`): un'esclusione per tabella, con il suo motivo in `reason`.

---

### L'esclusione vale per tabella, non per regola

La domanda «la tabella è esclusa?» ha una sede sola,
[fn_cleanup_esclusa](/dbzero/dbops/funzioni/fn_cleanup_esclusa): una riga con `enabled` vero per
quello schema e quella tabella, confronto esatto. La leggono:

* il giro di [fn_run_automations_cleanup](/dbzero/dbops/funzioni/fn_run_automations_cleanup), che
  salta la tabella **intera**: né `CLEANUP_AT` né `CLEANUP_PURGE`;
* la regola di scadenza [fn_cleanup_at_regola](/dbzero/dbops/funzioni/fn_cleanup_at_regola), che per
  una tabella esclusa risponde «la regola c'è ma non si applica» (`EXCLUDED`): il trigger alla
  nascita scrive una scadenza vuota, anche se il chiamante ne passa una, e il login non scrive
  scadenze sulle sue tabelle;
* la vista [vw_marcatori_automazione_senza_esecutore](/dbzero/dbops/views/vw_marcatori_automazione_senza_esecutore),
  che segnala una tabella esclusa che ha `cleanup_at`.

Non si può escludere una tabella da una regola sola.

Il salto lascia in `dbops.audit_log` una riga con status `WARN` e motivo `EXCLUDED` nei
parametri: chi legge l'audit vede che la tabella è stata vista e lasciata stare di proposito.

`enabled` falso tiene la riga come promemoria e restituisce la tabella al giro dalla corsa
successiva. Non c'è un controllo che la tabella esista: un'esclusione su una tabella che non c'è
è inerte.

---

### ⚠️ Che cosa l'esclusione non ferma

* **Le chiamate dirette.** `dbops.fn_apply_cleanup_at` e `dbops.fn_purge_cleanup_expired` non
  leggono questa tabella: chi le chiama a mano su una tabella esclusa la tratta comunque.
* **Le scadenze già scritte.** Escludere una tabella non svuota le scadenze che le sue righe hanno
  già: restano scritte, ma nessuno le esegue.

---

### Test

* `db/pgtap/dbops/test-cleanup-framework.sql` — con l'esclusione attiva il giro non cancella la
  riga scaduta; con l'esclusione disattivata la cancella. La prova mette in ambito la propria
  tabella, perché senza ambito le due asserzioni non eserciterebbero il giro.
* `db/pgtap/dbops/test-cleanup-at-regola-unica-v1.sql` — una tabella esclusa non riceve scadenza
  né dal trigger alla nascita, nemmeno se il chiamante ne passa una, né dal giro.

---

### Note di migrazione

* 2026-02-07 — nasce col framework di cleanup basato su `cleanup_at`.
* 2026-11-08 — perde `data_update` e `user_update`, che nessuno aggiornava: la tabella la
  scrive solo la migrazione (regola dello scrittore, `automazione-db.md` §1.1;
  `brief-db-revisione-dbops`, giro 7-bis).
* 2026-11-08 — l'esclusione vale anche per la scadenza alla nascita, e la si legge da
  `dbops.fn_cleanup_esclusa` (`20261109-84`..`-86`, brief-db-revisione-dbops, giro 10b). Prima il
  trigger alla nascita non la guardava, e una tabella esclusa riceveva scadenze che nessuno
  eseguiva.

---

{% include-markdown "signature-core.md" %}
