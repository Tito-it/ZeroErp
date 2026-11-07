## 📘 Documentazione Concettuale – Funzione `dbops.fn_fusione_righe_doppie`

> **Ultimo aggiornamento**: 7 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [dbops.fn_fusione_figlie](/dbzero/dbops/funzioni/fn_fusione_figlie) — le tabelle in cui cerca
> * [dbops.fn_fusione_ripunta_figlie](/dbzero/dbops/funzioni/fn_fusione_ripunta_figlie) — la chiama prima di scrivere
> * [dbops.fn_admin_merge_stradario](/dbzero/dbops/funzioni/fn_admin_merge_stradario) — dove il doppio tipico è un indirizzo
> * [dbops.fn_admin_merge_comune](/dbzero/dbops/funzioni/fn_admin_merge_comune) — dove il doppio tipico è una via

---

### 🎯 Scopo Principale

Dice, prima di fondere due righe di una tabella, quali righe delle tabelle figlie **diventerebbero
doppie**: per ogni coppia, la riga dell'origine come diventerebbe e la riga che la destinazione ha
già con la stessa chiave. È in sola lettura: si può lanciare anche per vedere che cosa succederebbe.

Nessuna riga in uscita vuol dire che la fusione non trova doppi.

---

### Come li trova

Per ogni tabella figlia, e per ogni suo indice unico che contiene una colonna della chiave esterna:

1. prende ogni riga che riferisce l'origine e la costruisce come sarebbe dopo la fusione: le
   colonne della chiave esterna con i valori della destinazione, le altre uguali;
2. la confronta, sulle colonne dell'indice, con le righe che ci sono già.

Le regole dell'indice si rispettano:

* con **NULLS NOT DISTINCT** due valori vuoti collidono; senza, no;
* un **indice parziale** conta solo per le righe che soddisfano il suo predicato, sia la riga
  spostata sia quella già presente;
* le colonne **INCLUDE** non sono chiave e non contano.

Ogni riga si nomina con la sua chiave primaria, in formato jsonb (o con la posizione fisica, se la
tabella non ne ha una).

---

### ⚠️ Che cosa non vede

Un indice su un'**espressione** (per esempio sul testo in minuscolo), e una colonna che un trigger
ricalcola a partire dalla chiave esterna: lì il confronto non si può fare prima. Quei doppi li
intercetta `dbops.fn_fusione_ripunta_figlie` al momento della scrittura, con lo stesso codice.

---

### Test

`db/pgtap/dbops/test-fusioni-comune-stradario-v1.sql`, test 6, 15, 21, 22 e 23: l'indirizzo doppio
fra due vie, la via doppia fra due comuni, l'indice parziale con i valori vuoti distinti, il
NULLS NOT DISTINCT, l'indice su espressione che sfugge al controllo.

---

{% include-markdown "signature-core.md" %}
