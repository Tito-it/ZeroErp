## 📘 Documentazione Concettuale – Tabella `dbops.audit_sources`

> **Ultimo aggiornamento**: 7 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento viste:
>
> * [script.vw_audit_sources](/dbzero/script/views/vw_audit_sources) — la vista che il backend legge: solo le righe attive
>
> Approfondimento funzioni:
>
> * [script.fn_audit_summary](/dbzero/script/funzioni/fn_audit_summary) — il riepilogo di uno snapshot, che usa `storico_table` e `storico_pk_col`
>
> Guide:
>
> * [Audit e tracciabilità](/guide/audit-e-tracciabilita) — lo storico dei dati e come si consulta

---

### 🎯 Scopo Principale

Il catalogo delle **tabelle di storico consultabili dall'amministrazione**: una riga per ogni
`storico.*` che il pannello dell'audit mostra, con l'etichetta da tradurre e l'area in cui
raggrupparla.

È la sola fonte di quell'elenco: il backend non ha una lista sua, e una tabella entra nel
pannello aggiungendo una riga qui, senza toccare schema né codice.

---

### Che cosa dice una riga

* `code` è l'**identità logica** della sorgente: il backend ci ordina, ci filtra e la riceve
  dall'interfaccia. Di solito coincide con il nome della tabella di origine, ma non è il nome
  fisico.
* `storico_table` è il **nome fisico**, qualificato con lo schema, della tabella di storico. ⚠️ Chi
  costruisce una lettura dinamica legge questa colonna, mai `code`: i due si separano alla prima
  tabella rinominata, e senza avviso.
* `storico_pk_col` è la colonna dello storico che identifica la riga di origine: serve a
  `script.fn_audit_summary` per mettere in fila gli snapshot della stessa riga e confrontare
  ciascuno con il precedente.
* `label_key` è una chiave di traduzione: il database non traduce, la traduce l'interfaccia.
* `area_funzionale` raggruppa le sorgenti nel pannello.
* `attivo` spegne una sorgente senza cancellarla: la vista e il riepilogo leggono solo le righe
  attive.

---

### Il vocabolario di `area_funzionale` sta nel test, non in un vincolo

I valori ammessi sono `PERMESSI`, `AUTH`, `ANAGRAFICHE`, `EMITTENTI` e `FATTURAZIONE`. Non c'è un
vincolo CHECK: il vocabolario lo tiene il pgTAP del seed, che fallisce se una riga attiva ne usa
un altro. Un valore nuovo entra quindi aggiornando insieme il seed e il test.

---

### Si alimenta dal seed

Le righe stanno nel CSV `80_data/sql/dbops/audit_sources.csv`, caricato con un upsert sulla
chiave `id` che si rilancia quando il CSV cambia. Per rendere consultabile una tabella nuova:

1. la tabella di origine deve essere già storicizzata, con la sua tabella `storico.*`;
2. si aggiunge la riga nel CSV, con codice, tabella di storico, colonna della riga di origine,
   chiave di traduzione e area.

La vista e il riepilogo la vedono al rilascio successivo, senza altre modifiche.

---

### ⭐ Fuori dalle automazioni, e senza le colonne che le promettono

La tabella **non** sta nello scope delle automazioni: è un catalogo che riempie solo il seed, e
nessun trigger di audit, di transaction id o di storico la tocca. Per questo non porta né `tx_id`
né `storicizza`, né `data_update` e `user_update`: sarebbero colonne che nessuno scrive, e che
direbbero il falso a chi le legge. Restano `data_insert` e `user_insert`, che riempie il default
alla nascita della riga.

⛔ Una tabella che ha una di quelle colonne senza chi la esegue la segnala il presidio
[dbops.vw_marcatori_automazione_senza_esecutore](/dbzero/dbops/views/vw_marcatori_automazione_senza_esecutore).

---

### Test

* `db/pgtap/dbops/test-audit-sources-seed.sql` — le sorgenti attive attese ci sono, nessuna usa
  un'area fuori vocabolario, ogni `storico_table` e ogni `storico_pk_col` esistono davvero, le
  sorgenti ritirate non ricompaiono, e la vista espone esattamente codice, chiave di traduzione,
  area e tabella di storico.
* `db/pgtap/script/test-fn-audit-summary.sql` — il riepilogo che passa da questo catalogo.

---

### Note di migrazione

* 2026-04-29 — nasce al posto della lista scritta nel backend e delle costanti del frontend.
* 2026-05-04 — escono le sorgenti del vecchio modello `profili_reparto_*`, entrano le tre
  `profili_accesso_*`.
* 2026-09-02 — `storico_table` entra nella vista pubblica: prima il backend ricostruiva il nome
  fisico da `code`.
* 2026-09-12 — la sorgente `risorse_umane_auth_user` è cancellata, insieme alla tabella ponte
  legacy e al suo storico; l'audit delle identità passa da `identita_digitali`.
* 2026-11-07 — escono `tx_id`, `storicizza`, `data_update` e `user_update`, che fuori dallo scope
  delle automazioni nessuno scriveva; con loro la riga della tabella in
  `config.storico_set_storicizza`.

---

{% include-markdown "signature-core.md" %}
