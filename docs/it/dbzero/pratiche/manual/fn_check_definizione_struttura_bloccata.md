## 📘 Documentazione Concettuale – Funzione `pratiche.fn_check_definizione_struttura_bloccata`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.workflow_definizioni](/dbzero/pratiche/tabelle/workflow_definizioni) — l'edizione della definizione, col suo stato e il suo emittente
>
> Approfondimento funzioni:
>
> * [pratiche.fn_check_definizione_congelata](/dbzero/pratiche/funzioni/fn_check_definizione_congelata) — il predicato gemello, che governa la cancellazione
> * [pratiche.trgfn_template_flussi_guard_immutabile](/dbzero/pratiche/funzioni/trgfn_template_flussi_guard_immutabile) · [pratiche.trgfn_template_flussi_figli_guard_immutabile](/dbzero/pratiche/funzioni/trgfn_template_flussi_figli_guard_immutabile) — i guard che lo leggono

---

### 🎯 Scopo Principale

`pratiche.fn_check_definizione_struttura_bloccata` risponde vero o falso alla domanda «la struttura di
questa edizione della definizione è bloccata alla modifica?», senza sollevare errori.

È vero se e solo se l'edizione appartiene a un emittente (è un fork) ed è già uscita dalla bozza:
pubblicata o ritirata.

---

### ⭐ Perché vale anche per una ritirata

Il predicato governa il blocco di inserimento e modifica dei passi e dei loro figli: le pratiche legate
a un'edizione emessa non devono veder cambiare la struttura sotto di loro. Una edizione ritirata ha
ancora pratiche legate alla sua versione, e per questo resta bloccata.

Il preset (senza emittente) e le edizioni in bozza restano liberamente modificabili. Una definizione
assente, o non indicata, vale come non bloccata.

---

### Due predicati, due assi

| Predicato | Vero su | Governa |
| --- | --- | --- |
| `fn_check_definizione_struttura_bloccata` | fork pubblicato o ritirato | inserimento e modifica della struttura |
| `fn_check_definizione_congelata` | fork pubblicato soltanto | cancellazione (edizione in uso) |

Conseguenza: un fork ritirato non si modifica ma si può cancellare. Lo smantellamento delle edizioni
storiche resta possibile, col percorso «ritira, poi cancella».

È l'unica sede della regola: i due guard di immutabilità dei passi e dei figli la chiamano per il ramo
di inserimento e modifica.

---

### Test

* `pratiche/test-definizione-ritirata-edit-freeze` — una ritirata è bloccata alla modifica ma
  cancellabile; preset e bozza restano liberi.

---

### Note di migrazione

* 2026-07-04 — nasce per separare il blocco della struttura (pubblicata o ritirata) dal blocco della
  cancellazione (solo pubblicata) (brief-db-accesso-write-editing-bozza).

---

{% include-markdown "signature-core.md" %}
