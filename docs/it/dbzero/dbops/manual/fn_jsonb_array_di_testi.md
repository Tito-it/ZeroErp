## 📘 Documentazione Concettuale – Funzione `dbops.fn_jsonb_array_di_testi`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automazione_overlap](/dbzero/dbops/tabelle/automazione_overlap) — il registro delle regole di non sovrapposizione, il cui CHECK la legge
>
> Approfondimento funzioni:
>
> * [dbops.fn_apply_automazione_overlap](/dbzero/dbops/funzioni/fn_apply_automazione_overlap) — legge le chiavi nella forma che lei garantisce
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — l'automazione OVERLAP

---

### 🎯 Scopo Principale

Risponde a una domanda sola: **il valore è vuoto, oppure un array JSON i cui elementi sono tutti
testi?** Vero se il valore manca, o se è un array e nessun elemento è un numero, un booleano, un
oggetto, un altro array o un `null` JSON. Un array vuoto vale vero.

È il pezzo che manca a un CHECK: un CHECK non può scorrere gli elementi di un array JSON da sé,
e lo fa chiamando questa funzione.

---

### Chi la usa

| Chi | Su che cosa |
| --- | --- |
| il CHECK `chk_automazione_overlap_chiavi` di `dbops.automazione_overlap` | `key_columns` e `key_expressions`, le due liste di chiave del vincolo |

È generica: non sa che cosa contengono i testi. Un registro che tiene una lista di nomi in un
array JSON può usarla per il suo CHECK.

---

### Codici errore

Nessuno: risponde vero o falso, e non solleva.

---

### Test

* `db/pgtap/dbops/test-nomi-e-chiavi-registri-v1.sql` — il CHECK che la chiama rifiuta una chiave
  che non è un array e un array con un elemento che non è un testo.

---

### Note di migrazione

* 2026-11-09 — nasce, per il CHECK della forma delle chiavi di `dbops.automazione_overlap`, quando
  le due colonne diventano `jsonb` (`20261110-37`, brief-db-revisione-dbops, giro 10c).

---

{% include-markdown "signature-core.md" %}
