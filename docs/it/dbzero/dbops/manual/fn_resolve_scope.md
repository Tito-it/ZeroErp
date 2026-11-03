## 📘 Documentazione Concettuale – Funzione `dbops.fn_resolve_scope`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_scope](/dbzero/dbops/tabelle/automation_scope) — l'elenco degli schemi che la funzione legge
>
> Approfondimento funzioni:
>
> * [dbops.fn_table_in_scope](/dbzero/dbops/funzioni/fn_table_in_scope) — il secondo livello, il filtro per tabella dentro gli schemi restituiti qui
> * [dbops.fn_schema_match](/dbzero/dbops/funzioni/fn_schema_match) — il confronto fra il bersaglio di una regola e uno schema
> * [dbops.fn_run_automations](/dbzero/dbops/funzioni/fn_run_automations) — l'orchestratore, che risolve gli schemi con una sua copia della stessa logica
>
> Guide:
>
> * [Automazione DB](/guide/automazione-db) — il framework che usa questo ambito

---

### 🎯 Scopo Principale

Restituisce l'elenco degli schemi su cui una corsa di automazione deve lavorare: l'elenco
passato dal chiamante, se ce n'è uno valido, altrimenti gli schemi di
`dbops.automation_scope`, altrimenti tutti gli schemi utente tranne `storico`.

È il primo passo di quasi tutti i runner `fn_run_automations_*`, della pulizia e dei seed
delle automazioni: chi la chiama con un ambito vuoto chiede «l'ambito di default».

---

### I tre gradini

1. **L'elenco del chiamante.** Si tolgono i valori vuoti o fatti di soli spazi e la parola
   `*all`, e si eliminano i doppioni. Se resta almeno uno schema, è la risposta.
2. **La tabella dell'ambito.** Se `dbops.automation_scope` esiste ed è popolata, la risposta
   sono i suoi schemi.
3. **Il fallback.** Tutti gli schemi che non sono di sistema (`pg_*`, `information_schema`) e
   non sono `storico`.

---

### ⚠️ `*all` vuol dire «usa il default», non «tutti gli schemi»

Passare `*all` non allarga l'ambito: lo scarta e fa scendere al gradino 2, cioè all'elenco
della tabella. Chi vuole davvero tutti gli schemi deve elencarli. È l'opposto del
significato di `*all` nel bersaglio di una regola, dove vuol dire «qualunque schema»
(`fn_schema_match`).

---

### ⚠️ Che cosa la risposta non garantisce

* **Gli schemi non si normalizzano.** Un valore con spazi attorno passa il filtro così
  com'è e poi non coincide con nessuno schema reale: la corsa lo ignora in silenzio.
* **Dal gradino 2 uno schema compare più volte**, una per riga della tabella (uno schema con
  più filtri di tabella). I runner lo usano come insieme e il doppione non cambia l'esito.
* **Non dice che lo schema esista**: un nome elencato e non presente nel database non dà
  errore, semplicemente non porta tabelle.
* Il gradino 2 contiene `storico` (è nel seed): sono i runner della storicizzazione a
  escluderlo.

---

### Test

* `db/pgtap/maintenance/test-cleanup-job-ambito-registro-v1.sql` — il giro di pulizia passa
  l'ambito vuoto, e ogni regola di pulizia attiva punta a uno schema che l'ambito risolto
  comprende.
* `db/pgtap/script/test-trgfn-guard-date-validita-v1.sql` — prende l'ambito risolto (con il
  filtro per tabella) come perimetro: ogni tabella che vi sta e ha la coppia di date porta il
  guard della regola del periodo.

---

{% include-markdown "signature-core.md" %}
