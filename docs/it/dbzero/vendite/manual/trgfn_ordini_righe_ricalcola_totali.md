## 📘 Documentazione Concettuale – Trigger Function `vendite.trgfn_ordini_righe_ricalcola_totali()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> [vendite.ordini](/dbzero/vendite/tabelle/ordini)
> [vendite.ordini_righe](/dbzero/vendite/tabelle/ordini_righe)
>
Approfondimento funzioni:
> [vendite.fn_ricalcola_totali_ordine](/dbzero/vendite/funzioni/fn_ricalcola_totali_ordine)
> [vendite.trgfn_preventivi_righe_ricalcola_totali](/dbzero/vendite/funzioni/trgfn_preventivi_righe_ricalcola_totali)

---

### 🎯 Scopo Principale

(latest review 05-06-2026)

`vendite.trgfn_ordini_righe_ricalcola_totali()` e' la trigger function
statement-level che mantiene i totali di testata ordine coerenti con le righe.
Invoca `vendite.fn_ricalcola_totali_ordine()` una sola volta per ogni
`ordine_id` coinvolto dall'operazione DML.

E' il gemello operativo del pattern usato sui preventivi.

---

### Trigger associati

| Nome | Timing | Evento | Transition tables |
| --- | --- | --- | --- |
| `trg_ordini_righe_z90_ricalcola_totali_ins` | AFTER STATEMENT | INSERT | `NEW TABLE AS new_rows` |
| `trg_ordini_righe_z90_ricalcola_totali_upd` | AFTER STATEMENT | UPDATE | `OLD TABLE AS old_rows`, `NEW TABLE AS new_rows` |
| `trg_ordini_righe_z90_ricalcola_totali_dlt` | AFTER STATEMENT | DELETE | `OLD TABLE AS old_rows` |

La fase `_z90_` esegue il ricalcolo dopo i trigger di normalizzazione e guard.

---

### Logica

* Su **INSERT** raccoglie i `DISTINCT ordine_id` da `new_rows`.
* Su **UPDATE** raccoglie i `DISTINCT ordine_id` da `new_rows UNION old_rows`.
  Questo copre anche eventuali spostamenti tecnici di righe tra ordini.
* Su **DELETE** raccoglie i `DISTINCT ordine_id` da `old_rows`.
* Per ogni ordine coinvolto esegue:

  ```sql
  PERFORM vendite.fn_ricalcola_totali_ordine(v_ordine_id);
  ```

Il trigger UPDATE non usa `UPDATE OF <colonne>` perche' PostgreSQL non consente
transition tables con una lista colonne sul trigger.

---

### Nota sul DELETE righe

Il trigger DELETE di ricalcolo e' registrato per completezza del modello, ma la
policy attuale vieta l'hard-delete di `vendite.ordini_righe` tramite
`trg_ordini_righe_a10_block_dlt`. In pratica il caso funzionale ordinario e':

* INSERT riga -> ricalcolo testata;
* UPDATE riga -> ricalcolo testata;
* DELETE fisico -> bloccato dal guard `_a10_`.

---

### Vantaggio rispetto a FOR EACH ROW

| Operazione | FOR EACH ROW | FOR EACH STATEMENT |
| --- | --- | --- |
| INSERT 20 righe stesso ordine | 20 ricalcoli | 1 ricalcolo |
| UPDATE bulk piu' ordini | 1 ricalcolo per riga | 1 ricalcolo per ordine coinvolto |
| UPDATE singola riga | 1 ricalcolo | 1 ricalcolo |

---

{% include-markdown "signature-core.md" %}
