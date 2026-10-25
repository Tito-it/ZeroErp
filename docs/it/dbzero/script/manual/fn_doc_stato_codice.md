## 📘 Documentazione Concettuale – Funzione `script.fn_doc_stato_codice(regclass, bigint)`

> 👀 **Vedi anche**
>
> [script.fn_doc_stato_id](/dbzero/script/funzioni/fn_doc_stato_id) ·
> [script.fn_stato_emissione_id](/dbzero/script/funzioni/fn_stato_emissione_id) ·
> [script.fn_doc_stato_modello](/dbzero/script/funzioni/fn_doc_stato_modello) ·
> guida [Il modello del documento di vendita](/guide/modello-documento-di-vendita) §4

### 🎯 Scopo
(25-10-2026 — brief `brief-modello-documento-vendita` §8.11, richiesta del team backend, V-1)

**Dall'id al codice dello stato.** Per un documento (la sua testata) e l'id di uno
stato, rende il codice di quello stato nel vocabolario del documento. È il gemello
inverso di [`script.fn_doc_stato_id`](/dbzero/script/funzioni/fn_doc_stato_id): uno
stato ha due chiavi, l'id e il `codice_interno` (la chiave che non cambia), e la
traduzione nei due sensi sta in questa coppia.

### Regole

* Rende il `codice_interno`, quello che i verbi di stato ricevono.
* Vuoto se l'id è vuoto o se il vocabolario non lo ha: decide chi chiama.
* Anche uno stato **spento** rende il suo codice: un id è già una riga che esiste.
  Che uno stato spento non sia una destinazione lo dice il verbo, quando traduce il
  codice con `fn_doc_stato_id`.
* Il vocabolario lo dice la mappa dei documenti
  ([`script.fn_doc_stato_modello`](/dbzero/script/funzioni/fn_doc_stato_modello)).
  Una tabella che non è nella mappa: `E_SCRIPT_CHIAMATA_NON_VALIDA`.

### Chi la legge

Il backend, per «Emetti»: chiede in una lettura sola il codice dello stato di
emissione del documento, componendo questa funzione con
[`script.fn_stato_emissione_id`](/dbzero/script/funzioni/fn_stato_emissione_id), e
lo passa al verbo. Così nessun nome di stato di emissione è scritto nel codice. Per
un documento che non si emette (reso, commessa, fattura) il codice è vuoto.
