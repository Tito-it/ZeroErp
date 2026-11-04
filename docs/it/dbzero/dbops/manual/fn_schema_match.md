## 📘 Documentazione Concettuale – Funzione `dbops.fn_schema_match`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl) — le regole il cui bersaglio di schema si confronta qui
>
> Approfondimento funzioni:
>
> * [dbops.fn_schema_in_scope](/dbzero/dbops/funzioni/fn_schema_in_scope) — la stessa regola, contro un elenco di schemi invece che uno solo
> * [dbops.fn_resolve_scope](/dbzero/dbops/funzioni/fn_resolve_scope) — l'ambito degli schemi, dove `*all` ha un altro significato
>
> Guide:
>
> * [Automazione DB](/guide/automazione-db) — il framework delle regole

---

### 🎯 Scopo Principale

Dice se uno schema è il bersaglio di una regola di automazione: vero se il bersaglio della
regola è `*all` oppure se coincide con lo schema, senza distinguere maiuscole e minuscole.

È il filtro di schema con cui quasi tutti i runner `fn_run_automations_*`, la pulizia e il
censimento delle divergenze dei lock scelgono, per ogni tabella, le regole che la
riguardano.

---

### Le tre risposte

* bersaglio vuoto → **falso**: una regola senza bersaglio non colpisce niente;
* bersaglio `*all` → **vero** per qualunque schema;
* altrimenti → vero solo se i due nomi coincidono, a meno delle maiuscole.

⚠️ Qui `*all` vuol dire «qualunque schema». Nell'ambito di una corsa (`fn_resolve_scope`) la
stessa parola vuol dire «usa l'ambito di default»: sono due posti diversi, e la parola non
ha lo stesso significato.

La funzione è `IMMUTABLE`: non legge tabelle né cataloghi, e la risposta dipende solo dai due
argomenti.

---

{% include-markdown "signature-core.md" %}
