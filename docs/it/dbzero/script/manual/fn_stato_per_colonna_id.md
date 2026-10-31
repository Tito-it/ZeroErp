## 📘 Documentazione Concettuale – Funzione `script.fn_stato_per_colonna_id(regclass, name, text)`

> 👀 **Vedi anche**
>
> [script.fn_stato_emissione_id](/dbzero/script/funzioni/fn_stato_emissione_id) ·
> [script.fn_stato_abortito_id](/dbzero/script/funzioni/fn_stato_abortito_id) ·
> [script.fn_stato_cessazione_id](/dbzero/script/funzioni/fn_stato_cessazione_id) ·
> [script.fn_stato_accettazione_id](/dbzero/script/funzioni/fn_stato_accettazione_id) ·
> [script.fn_doc_stato_modello](/dbzero/script/funzioni/fn_doc_stato_modello)

### 🎯 Scopo
(31-10-2026 — brief `brief-modello-documento-vendita` §17, regola del 2)

**La logica comune dei lettori degli stati con un significato.** Il vocabolario degli
stati marca con una colonna sì/no gli stati che il codice deve riconoscere: l'emissione,
l'annullo, la cessazione, l'accettazione. I quattro lettori con il nome fanno tutti la
stessa cosa — trovano il vocabolario del documento, guardano se ha la colonna, prendono
lo stato marcato — e quella cosa sta qui, una volta.

### Regole

* ⛔ **Non si chiama dai consumatori**: si chiama il lettore con il nome, che è la porta
  documentata (la guida e i messaggi parlano di «stato di emissione», non di una
  colonna).
* Vocabolario senza la colonna: vuoto. È il caso voluto del documento che quello stato
  non lo ha.
* Colonna che c'è ma non è sì/no, o tabella fuori dalla mappa:
  `E_SCRIPT_CHIAMATA_NON_VALIDA` (il chiamante è rotto).
* Nessuno stato marcato: vuoto. Al massimo uno lo garantisce l'indice unico parziale di
  ogni colonna.
* Il terzo argomento è il nome del lettore che chiama: il messaggio di una chiamata non
  valida nomina la funzione che il chiamante ha usato, non questa.
