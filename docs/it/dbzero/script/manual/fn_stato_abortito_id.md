## 📘 Documentazione Concettuale – Funzione `script.fn_stato_abortito_id(regclass)`

> 👀 **Vedi anche**
>
> [script.fn_stato_emissione_id](/dbzero/script/funzioni/fn_stato_emissione_id) ·
> [script.fn_doc_stato_codice](/dbzero/script/funzioni/fn_doc_stato_codice) ·
> [script.fn_stato_per_colonna_id](/dbzero/script/funzioni/fn_stato_per_colonna_id) (la logica comune, dal 31-10-2026) ·
> [script.fn_doc_stato_modello](/dbzero/script/funzioni/fn_doc_stato_modello) ·
> guida [Il modello del documento di vendita](/guide/modello-documento-di-vendita) §8

### 🎯 Scopo
(25-10-2026 — brief `brief-modello-documento-vendita` §9, decisione Z-3 di Tid)

**Lo stato d'annullo di un documento.** Annullare un documento vuol dire portarlo nel
suo stato d'annullo. Quale sia lo dice il vocabolario degli stati, con la colonna
`is_abortito`, come la colonna `iniziale` dice lo stato in cui il documento nasce e
`emissione` quello in cui si emette. Questa funzione la legge, così nessuno scrive
`'ANNULLATO'` nel codice per dire «lo stato d'annullo».

### Regole

* Al massimo uno stato d'annullo per vocabolario, ed è attivo: lo garantiscono un
  indice unico e un vincolo sulla tabella, negli otto vocabolari dei documenti di
  vendita.
* Vuoto se il vocabolario non ne dichiara.
* Riceve la testata del documento, non il vocabolario: chi lo chiede conosce il
  documento. Una tabella fuori dalla mappa: `E_SCRIPT_CHIAMATA_NON_VALIDA`.
* I verbi di stato prendono il **codice** dello stato: chi lo passa a un verbo lo
  traduce con [`script.fn_doc_stato_codice`](/dbzero/script/funzioni/fn_doc_stato_codice).

### Chi la legge

I verbi d'annullo di preventivo, offerta, contratto, ordine, commessa e lotto di
fatturazione, il verbo della bolla per riconoscere l'annullo di una bolla emessa (che
storna i movimenti di magazzino) e il backend, per mandare l'annullo chiesto dal cambio di
stato al verbo d'annullo.
