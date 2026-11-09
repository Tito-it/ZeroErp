## 📘 Documentazione Concettuale – Funzione `dbops.fn_indici_schema_nell_ambito`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_scope](/dbzero/dbops/tabelle/automation_scope) — l'ambito delle automazioni, di cui la funzione legge solo lo schema
> * [dbops.fk_index_policy](/dbzero/dbops/tabelle/fk_index_policy) — la politica degli indici delle FK, il cui perimetro è deciso qui
>
> Approfondimento viste:
>
> * [dbops.vw_fk_senza_indice](/dbzero/dbops/views/vw_fk_senza_indice) — le chiavi esterne scoperte degli schemi governati
> * [dbops.vw_fk_da_decidere](/dbzero/dbops/views/vw_fk_da_decidere) — il presidio, che mostra le righe fuori perimetro
> * [dbops.vw_indici_ridondanti_prefisso](/dbzero/dbops/views/vw_indici_ridondanti_prefisso) — gli indici ridondanti per prefisso
> * [dbops.vw_duplicate_indexes](/dbzero/dbops/views/vw_duplicate_indexes) — gli indici duplicati esatti
>
> Approfondimento funzioni:
>
> * [dbops.apply_fk_index_policy](/dbzero/dbops/funzioni/apply_fk_index_policy) — applica solo le righe degli schemi governati
> * [dbops.fn_table_in_scope](/dbzero/dbops/funzioni/fn_table_in_scope) — il filtro per tabella delle altre automazioni, che qui non si usa
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db#6-policy-indici-fk) — la politica degli indici delle FK

---

### 🎯 Scopo Principale

Risponde a una domanda sola: **lo schema è governato dalla politica degli indici delle chiavi
esterne?** Vero se lo schema ha almeno una riga in `dbops.automation_scope`, qualunque sia il suo
filtro per tabella. Uno schema senza righe è fuori, e uno schema mancante dà falso.

È il perimetro della politica degli indici scritto in un posto solo: prima la stessa lettura era
ricopiata in ogni vista degli indici, e la procedura che applica la politica non la faceva affatto.

---

### ⭐ Per schema, non per tabella

Le altre automazioni dentro uno schema guardano anche il filtro per tabella, con
`dbops.fn_table_in_scope`. La politica degli indici no, per scelta: l'indice di una chiave esterna
serve a ogni tabella, mentre l'elenco delle tabelle serve a decidere su quali montare i trigger.
Legare gli indici a quell'elenco vorrebbe dire che una tabella, per avere il suo indice, dovrebbe
ricevere anche i trigger delle altre automazioni.

Così in `dbops`, che espone ai trigger pochi registri, la politica governa le chiavi esterne di
tutte le tabelle.

---

### Chi la usa

| Chi | Per che cosa |
| --- | --- |
| `dbops.vw_fk_senza_indice` | quali chiavi esterne e quali indici guardare |
| `dbops.vw_indici_ridondanti_prefisso`, `dbops.vw_duplicate_indexes` | in quali schemi cercare indici ridondanti |
| `dbops.vw_fk_da_decidere` | quali righe di politica sono fuori perimetro |
| `dbops.apply_fk_index_policy` | quali righe applicare: una riga fuori perimetro non crea e non toglie |

È scritta come una sola interrogazione, perché il planner la sostituisca nella query che la chiama:
nelle viste costa quanto la condizione scritta a mano.

---

### Codici errore

Nessuno: risponde vero o falso, e non solleva.

---

### Test

* `db/pgtap/dbops/test-fk-index-policy-decisione-v1.sql` — vero per uno schema nell'ambito, falso
  per uno fuori e per un valore mancante; nessuna riga vera della politica è fuori perimetro.

---

### Note di migrazione

* 2026-11-09 — nasce, al posto della stessa lettura scritta in linea in sei oggetti; da qui la
  leggono anche la procedura che applica la politica e il presidio nuovo (`20261110-43`,
  brief-db-revisione-dbops, giro 10d).

---

{% include-markdown "signature-core.md" %}
