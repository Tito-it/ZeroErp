## 📘 Documentazione Concettuale – Funzione `dbops.fn_attivo_fk_esclusa`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automazione_attivo_eccezioni](/dbzero/dbops/tabelle/automazione_attivo_eccezioni) — le FK che non si legano
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
| `NULL` | la FK si lega |
| `ECCEZIONE_DICHIARATA` | la FK è in `dbops.automazione_attivo_eccezioni` |
| `FK_EREDITATA` | la tabella è una partizione e la colonna ha solo FK ereditate dalla radice: la FK si lega, o si esclude, sulla radice |

Il nome della colonna non decide niente: una FK verso l'`id` del padre e una verso un suo codice si
legano allo stesso modo. Chi non si lega sta nel registro delle eccezioni, col motivo.

**Le partizioni.** Su una tabella partizionata la FK sta sulla radice, e ogni partizione la eredita.
Il motore lega la radice: il require della radice PostgreSQL lo copia su ogni partizione, anche su
quelle future, e il block conta le righe di tutte. Un'eccezione scritta sulla radice vale quindi per
tutte le partizioni. Se le partizioni si legassero da sé, ognuna avrebbe due require e un block in
più, e un'eccezione sulla radice non le coprirebbe. ⚠️ Una colonna che ha una FK propria **e** una
ereditata (una figlia verso un padre partizionato, coi vincoli copiati verso le partizioni del
padre) risponde `NULL`.

---

### ⭐ Una domanda, una sede

La domanda ha due lettori: il motore, che decide se generare, e il ritiro, che toglie ciò che non
dovrebbe esserci. Scritta in due posti risponderebbe prima o poi in due modi: un trigger generato
e ritirato a ogni giro, o uno che nessuno ritira. Per questo la rispondono entrambi qui.

Non guarda il padre: un padre senza la colonna `attivo` e le FK a più colonne li filtra il motore,
perché dipendono dal catalogo del padre.

È una funzione SQL `BEGIN ATOMIC` e `STABLE`: il registro delle eccezioni e il catalogo dei vincoli sono dipendenze nel catalogo.

---

### Test

* `db/pgtap/dbops/test-automazione-attivo-senza-filtro-nome-v1.sql` — test 5, le risposte
  (eccezione, eccezione sulla radice, FK ereditata, FK senza `_id`, FK con `_id`); test 6-13, la
  regola su tabelle costruite dal test, con una radice partizionata.
* `db/pgtap/dbops/test-automazione-attivo-inclusioni-v1.sql`, test 6 — le due FK `regime_fiscale_rf`
  si legano senza registro.

---
{% include-markdown "signature-core.md" %}
