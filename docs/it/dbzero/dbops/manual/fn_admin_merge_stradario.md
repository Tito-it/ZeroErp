## 📘 Documentazione Concettuale – Funzione `dbops.fn_admin_merge_stradario`

> 👀 **Vedi anche**
>
> • [dbops.fn_admin_merge_comune](/dbzero/dbops/funzioni/fn_admin_merge_comune)
> • [script.fn_get_vie_discendenti](/dbzero/script/funzioni/fn_get_vie_discendenti)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Gemella di `fn_admin_merge_comune`, un livello più in basso: **fonde due vie** dello
stradario, registrando la trasformazione.

Stesso fatto del mondo reale — le vie cambiano nome, vengono accorpate, cambiano numerazione —
e stessa necessità: gli indirizzi esistenti restano validi, e chi cerca la via nuova trova
anche lo storico.

⭐ La catena delle trasformazioni è percorribile con
[script.fn_get_vie_discendenti](/dbzero/script/funzioni/fn_get_vie_discendenti), che risale
ricorsivamente da una via a tutte quelle che ne sono derivate.

---

{% include-markdown "signature-core.md" %}
