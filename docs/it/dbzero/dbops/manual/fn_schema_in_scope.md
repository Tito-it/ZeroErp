## 📘 Documentazione Concettuale – Funzione `dbops.fn_schema_in_scope`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [dbops.fn_schema_match](/dbzero/dbops/funzioni/fn_schema_match) — la stessa regola su un solo schema
> * [dbops.fn_resolve_scope](/dbzero/dbops/funzioni/fn_resolve_scope) — produce l'elenco di schemi che qui si confronta
> * [dbops.fn_run_automations_attivo](/dbzero/dbops/funzioni/fn_run_automations_attivo) — l'unico chiamante
>
> Guide:
>
> * [Automazione DB](/guide/automazione-db) — il framework delle regole

---

### 🎯 Scopo Principale

Dice se il bersaglio di schema di una regola di automazione cade dentro un elenco di schemi:
vero se il bersaglio è `*all` oppure se coincide, senza distinguere maiuscole e minuscole, con
uno degli schemi dell'elenco.

La usa il runner della colonna `attivo` per tenere, fra le regole del registro, solo quelle
che riguardano l'ambito della corsa.

---

### Le risposte

* bersaglio vuoto → **falso**;
* bersaglio `*all` → **vero**, anche se l'elenco è vuoto;
* elenco vuoto o assente, bersaglio di uno schema preciso → **falso**;
* altrimenti → vero se il bersaglio coincide con almeno uno schema dell'elenco.

È la regola di `fn_schema_match` applicata a un elenco invece che a un solo schema. Come
quella è `IMMUTABLE` e non legge niente fuori dai suoi argomenti.

---

{% include-markdown "signature-core.md" %}
