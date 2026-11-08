## 📘 Documentazione Concettuale – Funzione `dbops.fn_cleanup_esclusa`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_cleanup_exclusions](/dbzero/dbops/tabelle/automation_cleanup_exclusions) — il registro delle esclusioni che la funzione legge
>
> Approfondimento funzioni:
>
> * [dbops.fn_cleanup_at_regola](/dbzero/dbops/funzioni/fn_cleanup_at_regola) — la regola di scadenza: una tabella esclusa risponde `EXCLUDED`
> * [dbops.fn_run_automations_cleanup](/dbzero/dbops/funzioni/fn_run_automations_cleanup) — il giro di pulizia, che salta la tabella intera
>
> Approfondimento viste:
>
> * [dbops.vw_marcatori_automazione_senza_esecutore](/dbzero/dbops/views/vw_marcatori_automazione_senza_esecutore) — segnala `cleanup_at` su una tabella esclusa
>
> Guide:
>
> * [Automazione DB](/guide/automazione-db) — §4.5, la regola CLEANUP

---

### 🎯 Scopo Principale

Risponde a una domanda sola: **la tabella è esclusa dal cleanup?** Vero se
`dbops.automation_cleanup_exclusions` ha una riga abilitata per quello schema e quella tabella.

Per il cleanup una tabella esclusa non esiste: nessuna regola `CLEANUP_AT` le dà una scadenza e
nessuna regola `CLEANUP_PURGE` le cancella righe. È la sede unica della domanda, così chi decide
la scadenza, chi pulisce e chi controlla le promesse rispondono allo stesso modo.

| Chi la legge | Che cosa ne fa |
| --- | --- |
| [fn_cleanup_at_regola](/dbzero/dbops/funzioni/fn_cleanup_at_regola) | la regola c'è ma non si applica (`EXCLUDED`): il trigger alla nascita e il login non scrivono scadenze |
| [fn_run_automations_cleanup](/dbzero/dbops/funzioni/fn_run_automations_cleanup) | salta la tabella intera, né scadenza né purge, con una riga `WARN` nell'audit |
| [vw_marcatori_automazione_senza_esecutore](/dbzero/dbops/views/vw_marcatori_automazione_senza_esecutore) | una tabella esclusa con `cleanup_at` ha una promessa che nessuno esegue |

---

### Regole

* Il confronto è **esatto** su schema e tabella: niente caratteri jolly, niente maiuscole
  ignorate. Un'esclusione vale per una tabella sola.
* Conta solo una riga con `enabled` vero: una riga disattivata è un promemoria e restituisce la
  tabella al cleanup.
* L'esclusione è per tabella, non per regola: non si può escludere una tabella dalla sola
  scadenza o dal solo purge.

---

### Casi limite

* **Tabella che non esiste**: la funzione non lo controlla. Un'esclusione su una tabella che non
  c'è è inerte, e la risposta per un nome qualunque senza riga è falso.
* **Chiamate dirette ai passi**: [fn_apply_cleanup_at](/dbzero/dbops/funzioni/fn_apply_cleanup_at)
  e [fn_purge_cleanup_expired](/dbzero/dbops/funzioni/fn_purge_cleanup_expired) non la leggono: chi
  li chiama a mano su una tabella esclusa la tratta comunque.

---

### Codici errore

La funzione non solleva codici suoi.

---

### Test

* `db/pgtap/dbops/test-cleanup-at-regola-unica-v1.sql` — una tabella esclusa risponde `EXCLUDED`,
  il trigger alla nascita le scrive una scadenza vuota anche se il chiamante ne passa una, e il
  runner non gliene dà.
* `db/pgtap/dbops/test-cleanup-framework.sql` — con l'esclusione attiva il giro non cancella la
  riga scaduta; con l'esclusione disattivata la cancella.
* `db/pgtap/dbops/test-marcatori-automazione-senza-esecutore-v1.sql` — l'esclusione lascia
  scoperto `cleanup_at`.

---

### Note di migrazione

* 2026-11-08 — nasce (`20261109-84`, brief-db-revisione-dbops, giro 10b): la domanda la facevano
  da sé il runner del cleanup e la vista dei marcatori, e la risoluzione della regola di scadenza
  ne aveva bisogno per terza.

---

{% include-markdown "signature-core.md" %}
