## 📘 Documentazione Concettuale – Funzione `script.fn_stato_emissione_id(regclass)`

> 👀 **Vedi anche**
>
> [script.fn_stato_iniziale_id](/dbzero/script/funzioni/fn_stato_iniziale_id) ·
> [script.fn_doc_azione_passaggio](/dbzero/script/funzioni/fn_doc_azione_passaggio) ·
> guida [Il modello del documento di vendita](/guide/modello-documento-di-vendita) §7

### 🎯 Scopo
(25-10-2026 — brief `brief-modello-documento-vendita` §8, colonna decisa da Tid)

**Lo stato di emissione di un documento.** Un documento che si stampa si emette solo
da «Emetti», che produce numero e PDF insieme. Per rifiutare l'emissione sul cambio
di stato generico bisogna sapere **quale** stato è l'emissione: lo dice il vocabolario
degli stati, con la colonna `emissione`, come la colonna `iniziale` dice lo stato in
cui il documento nasce. Questa funzione la legge.

| Documento | Stato di emissione |
| --- | --- |
| Preventivo | Emesso |
| Offerta | Emessa |
| Contratto | Attivo |
| Ordine | Confermato |
| Bolla | Emessa |

### Regole

* Vuoto se il documento **non si emette**: reso (la conferma fa da emissione),
  commessa (nasce dalla push), fattura (segue la pipeline). Il loro vocabolario non ha
  la colonna.
* Al massimo uno stato di emissione per vocabolario, ed è attivo: lo garantiscono un
  indice unico e un vincolo sulla tabella.
* Riceve la testata del documento, non il vocabolario: chi lo chiede conosce il
  documento. Una tabella fuori dalla mappa: `E_SCRIPT_CHIAMATA_NON_VALIDA`.

### Chi la legge

Il backend (il cambio di stato generico rifiuta l'emissione di qualunque documento,
senza un nome di stato scritto per documento), la domanda intera
[`script.fn_doc_azione_passaggio`](/dbzero/script/funzioni/fn_doc_azione_passaggio)
e i verbi di preventivo e bolla.
