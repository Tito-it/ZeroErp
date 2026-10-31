## 📘 Documentazione Concettuale – Funzione `script.fn_stato_accettazione_id(regclass)`

> 👀 **Vedi anche**
>
> [script.fn_stato_cessazione_id](/dbzero/script/funzioni/fn_stato_cessazione_id) ·
> [script.fn_stato_emissione_id](/dbzero/script/funzioni/fn_stato_emissione_id) ·
> [script.fn_stato_per_colonna_id](/dbzero/script/funzioni/fn_stato_per_colonna_id) ·
> [script.fn_doc_stato_codice](/dbzero/script/funzioni/fn_doc_stato_codice) ·
> guida [Il modello del documento di vendita](/guide/modello-documento-di-vendita) §4

### 🎯 Scopo
(31-10-2026 — brief `brief-modello-documento-vendita` §17, ok di Tid)

**Lo stato di accettazione di un documento.** Preventivo e offerta si accettano quando il
cliente dice sì, e da lì partono i passaggi agli altri documenti: la commessa e l'ordine
dal preventivo, il contratto e l'ordine dall'offerta. Quale stato sia l'accettazione lo
dice il vocabolario degli stati, con la colonna `accettazione`. Questa funzione la legge,
così nessuno scrive `'ACCETTATO'` o `'ACCETTATA'` nel codice per dire «lo stato di
accettazione».

| Documento | Stato di accettazione |
| --- | --- |
| Preventivo | Accettato |
| Offerta | Accettata |

### Regole

* Vuoto se il documento **non si accetta**: tutti tranne preventivo e offerta. Il loro
  vocabolario non ha la colonna.
* L'accettazione non chiude il documento: dal preventivo accettato si va a *evaso*
  quando è smistato tutto.
* Al massimo uno stato di accettazione per vocabolario, ed è attivo: lo garantiscono un
  indice unico e un vincolo sulla tabella.
* Riceve la testata del documento, non il vocabolario. Una tabella fuori dalla mappa:
  `E_SCRIPT_CHIAMATA_NON_VALIDA`.

### Chi la legge

Il lister del push dei preventivi a commessa e il push del preventivo a ordine; il
backend, al posto dei nomi di stato scritti nei service. Chi ha già in mano la riga del
vocabolario (le capability di preventivo e offerta, il passaggio dell'offerta a contratto,
l'ordine dall'offerta) legge la colonna `accettazione` direttamente.
