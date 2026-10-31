## 📘 Documentazione Concettuale – Funzione `script.fn_stato_cessazione_id(regclass)`

> 👀 **Vedi anche**
>
> [script.fn_stato_accettazione_id](/dbzero/script/funzioni/fn_stato_accettazione_id) ·
> [script.fn_stato_emissione_id](/dbzero/script/funzioni/fn_stato_emissione_id) ·
> [script.fn_stato_per_colonna_id](/dbzero/script/funzioni/fn_stato_per_colonna_id) ·
> [script.fn_doc_stato_codice](/dbzero/script/funzioni/fn_doc_stato_codice) ·
> guida [Il modello del documento di vendita](/guide/modello-documento-di-vendita) §4

### 🎯 Scopo
(31-10-2026 — brief `brief-modello-documento-vendita` §17, ok di Tid)

**Lo stato di cessazione di un documento.** Un contratto cessa quando finisce il suo
corso, alla sua data di fine: lo fa il verbo della cessazione, o il job delle scadenze.
Quale stato sia la cessazione lo dice il vocabolario degli stati, con la colonna
`cessazione`, come `emissione` dice lo stato in cui il documento si emette. Questa
funzione la legge, così nessuno scrive `'CESSATO'` nel codice per dire «lo stato di
cessazione».

| Documento | Stato di cessazione |
| --- | --- |
| Contratto | Cessato |

### Regole

* Vuoto se il documento **non cessa**: tutti tranne il contratto. Il loro vocabolario
  non ha la colonna.
* Al massimo uno stato di cessazione per vocabolario, ed è attivo: lo garantiscono un
  indice unico e un vincolo sulla tabella.
* Riceve la testata del documento, non il vocabolario. Una tabella fuori dalla mappa:
  `E_SCRIPT_CHIAMATA_NON_VALIDA`.
* Il codice dello stato, per un messaggio o per un verbo, si traduce con
  [`script.fn_doc_stato_codice`](/dbzero/script/funzioni/fn_doc_stato_codice).

### Chi la legge

Il verbo della cessazione e il job delle scadenze del contratto (la destinazione), la
sede della regola del push dei contratti (che genera i canoni anche dei contratti
cessati, fino alla loro data di fine) e il backend, per mandare la cessazione al suo
verbo.
