## 📘 Documentazione Concettuale – Funzione `script.fn_doc_azioni_permesse(regclass, bigint)`

> 👀 **Vedi anche**
>
> [script.fn_doc_azione_passaggio](/dbzero/script/funzioni/fn_doc_azione_passaggio) ·
> [script.fn_doc_passaggio](/dbzero/script/funzioni/fn_doc_passaggio) ·
> [script.fn_check_azione_processo](/dbzero/script/funzioni/fn_check_azione_processo) ·
> [script.fn_doc_stato_modello](/dbzero/script/funzioni/fn_doc_stato_modello) ·
> guida [Il modello del documento di vendita](/guide/modello-documento-di-vendita) §6

### 🎯 Scopo
(27-10-2026 — brief `brief-modello-documento-vendita` §15.14, richiesta del team backend)

**Quali passaggi l'operatore può fare da qui.** Dato un documento e il suo stato, la funzione
risponde con i passaggi che un operatore può chiedere con un bottone: quelli vivi nella matrice,
manuali (non quelli che fa il sistema), e di cui l'operatore ha il permesso. Un passaggio che
non chiede un'azione resta nell'elenco: lì decide il permesso sul documento.

Serve a due posti con la stessa risposta: il dettaglio del documento (le capability) e la riga
di una lista, che così non propone un'azione che il dettaglio nasconde.

### Regole

* Riceve lo **stato**, non il documento: il permesso dipende dall'operatore e dall'azione, non
  dal documento, e lo stato lo hanno già sia il dettaglio sia la riga della lista.
* Non dice se il passaggio si può fare **adesso** (righe presenti, prezzi, date…): quello resta
  delle capability del dettaglio, che lo spiegano con i loro motivi.
* Ogni riga della matrice dichiara se è manuale; una condizione sul tipo di lotto sta solo sui
  passaggi di processo. Lo garantiscono due vincoli sulle tabelle, così la funzione non ha casi
  da interpretare.
* Uno stato vuoto non ha passaggi. Una tabella fuori dalla mappa: `E_SCRIPT_CHIAMATA_NON_VALIDA`.

### Chi la legge

Le capability dei documenti di vendita (preventivo, offerta, contratto, ordine, bolla, reso,
commessa, lotto di fatturazione) e il backend, per le azioni permesse sulle righe della lista
dei lotti.
