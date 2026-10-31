## 📘 Documentazione Concettuale – Funzione `script.fn_stato_scadenza_id(regclass)`

> 👀 **Vedi anche**
>
> [script.fn_stato_cessazione_id](/dbzero/script/funzioni/fn_stato_cessazione_id) ·
> [script.fn_stato_accettazione_id](/dbzero/script/funzioni/fn_stato_accettazione_id) ·
> [script.fn_stato_per_colonna_id](/dbzero/script/funzioni/fn_stato_per_colonna_id) ·
> [script.fn_doc_stato_codice](/dbzero/script/funzioni/fn_doc_stato_codice) ·
> guida [Il modello del documento di vendita](/guide/modello-documento-di-vendita) §4

### 🎯 Scopo
(31-10-2026 — brief `brief-db-scadenza-preventivi` §8.1, D-1)

**Lo stato di scadenza di un documento.** Un preventivo scade quando la sua validità
finisce senza che il cliente abbia risposto: lo porta lì il job delle scadenze. Quale stato
sia la scadenza lo dice il vocabolario degli stati, con la colonna `scadenza`, come
`cessazione` dice lo stato in cui un contratto finisce il suo corso. Questa funzione la
legge, così nessuno scrive `'SCADUTO'` nel codice per dire «lo stato di scadenza».

| Documento | Stato di scadenza |
| --- | --- |
| Preventivo | Scaduto |

### Regole

* Vuoto se il documento **non scade**: tutti tranne il preventivo. Il loro vocabolario non
  ha la colonna.
* Al massimo uno stato di scadenza per vocabolario, ed è attivo: lo garantiscono un indice
  unico e un vincolo sulla tabella.
* Riceve la testata del documento, non il vocabolario. Una tabella fuori dalla mappa:
  `E_SCRIPT_CHIAMATA_NON_VALIDA`.
* Il codice dello stato, per un messaggio, si traduce con
  [`script.fn_doc_stato_codice`](/dbzero/script/funzioni/fn_doc_stato_codice).

### Chi la legge

Il verbo della scadenza dei preventivi,
[`vendite.fn_chiudi_preventivi_scaduti`](/dbzero/vendite/funzioni/fn_chiudi_preventivi_scaduti)
(la destinazione). La revisione del preventivo e la sua capability, che da uno scaduto
ripropongono il documento, leggono la stessa colonna dalla riga del vocabolario che hanno
già in mano.
