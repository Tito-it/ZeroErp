## 📘 Documentazione Concettuale – Funzione `dbops.fn_resolve_scope`

> **Ultimo aggiornamento**: 12 novembre 2026
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
>
> Guide:
>
> * [Automazione DB](/guide/automazione-db) — il framework che usa questo ambito

---

### 🎯 Scopo Principale

Restituisce l'elenco degli schemi su cui una corsa di automazione deve lavorare: l'elenco
passato dal chiamante, se ce n'è uno valido, altrimenti gli schemi di
`dbops.automation_scope`, altrimenti tutti gli schemi utente tranne `storico`. La risposta è
senza doppi e senza spazi attorno ai nomi.

È il primo passo di quasi tutti i runner `fn_run_automations_*`, della pulizia e dei seed
delle automazioni: chi la chiama con un ambito vuoto chiede «l'ambito di default».

---

### I tre gradini

1. **L'elenco del chiamante.** Si tolgono gli spazi attorno ai nomi, i valori vuoti e la
   parola `*all`, e si eliminano i doppioni. Se resta almeno uno schema, è la risposta.
2. **La tabella dell'ambito.** Se `dbops.automation_scope` esiste ed è popolata, la risposta
   sono i suoi schemi, ognuno una volta sola anche se ha più righe (più filtri di tabella), e
   senza spazi attorno.
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

* **Il confronto non abbassa le maiuscole**: lo spazio attorno si toglie, ma un nome scritto
  con una maiuscola diversa non coincide con lo schema reale, e la corsa lo ignora in silenzio.
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
* `db/pgtap/dbops/test-registro-regole-vincoli-v1.sql` — l'ambito risolto non ha doppi né spazi.

---

### Note di migrazione

* 2026-11-08 — la risposta è senza doppi e senza spazi: prima `dbops`, che ha sette righe in
  `automation_scope`, compariva sette volte, e un nome con spazi attorno passava così com'era
  (`brief-db-revisione-dbops`, D13).

---

{% include-markdown "signature-core.md" %}
