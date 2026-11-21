## 📘 Documentazione Concettuale – Funzione `dbops.fn_attivo_fk_esclusa`

> **Ultimo aggiornamento**: 21 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automazione_attivo_eccezioni](/dbzero/dbops/tabelle/automazione_attivo_eccezioni) — le FK che non si legano
> * [dbops.automazione_attivo_inclusioni](/dbzero/dbops/tabelle/automazione_attivo_inclusioni) — le FK senza `_id` che si legano comunque
>
> Approfondimento funzioni:
>
> * [dbops.fn_run_automations_attivo](/dbzero/dbops/funzioni/fn_run_automations_attivo) — il motore, che non genera le FK escluse
> * [dbops.fn_ritira_attivo_eccezioni](/dbzero/dbops/funzioni/fn_ritira_attivo_eccezioni) — il ritiro, che toglie i trigger delle FK escluse
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — §4.2, la regola ATTIVO

---

### 🎯 Scopo Principale

Dice se una FK resta **fuori** dall'automazione ATTIVO, e perché. La FK si nomina dalla figlia:
schema, tabella, colonna FK.

| Risposta | Quando |
| --- | --- |
| `NULL` | la FK si lega: la colonna finisce in `_id`, oppure la FK è in `dbops.automazione_attivo_inclusioni` |
| `ECCEZIONE_DICHIARATA` | la FK è in `dbops.automazione_attivo_eccezioni`; prevale anche su un'inclusione |
| `FK_NO_ID_SUFFIX` | la colonna non finisce in `_id` e la FK non è fra le inclusioni |

⚠️ Il predicato `_id` è `LIKE '%_id'`, col `_` jolly: è quello che il motore ha sempre usato.

---

### ⭐ Una domanda, una sede

La domanda ha due lettori: il motore, che decide se generare, e il ritiro, che toglie ciò che non
dovrebbe esserci. Scritta in due posti risponderebbe prima o poi in due modi: un trigger generato
e ritirato a ogni giro, o uno che nessuno ritira. Per questo la rispondono entrambi qui.

Non guarda il padre: un padre senza la colonna `attivo` e le FK a più colonne li filtra il motore,
perché dipendono dal catalogo e non dai registri.

È una funzione SQL `BEGIN ATOMIC` e `STABLE`: i due registri sono dipendenze nel catalogo.

---

### Test

* `db/pgtap/dbops/test-automazione-attivo-inclusioni-v1.sql`, test 6 — le quattro risposte:
  eccezione, FK senza `_id` fuori registro, FK inclusa, FK con `_id`.

---
{% include-markdown "signature-core.md" %}
