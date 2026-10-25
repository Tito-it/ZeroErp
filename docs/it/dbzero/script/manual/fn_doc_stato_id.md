## 📘 Documentazione Concettuale – Funzione `script.fn_doc_stato_id(regclass, text)`

> 👀 **Vedi anche**
>
> [script.fn_doc_stato_modello](/dbzero/script/funzioni/fn_doc_stato_modello) ·
> [script.fn_doc_azione_passaggio](/dbzero/script/funzioni/fn_doc_azione_passaggio) ·
> guida [Il modello del documento di vendita](/guide/modello-documento-di-vendita) §4

### 🎯 Scopo
(25-10-2026 — brief `brief-modello-documento-vendita` §8, richiesta del team backend, U-3)

**Dal codice all'id dello stato.** Per un documento (la sua testata) e il codice di
uno stato, rende l'id di quello stato nel vocabolario del documento. Il codice è il
`codice_interno`, la chiave che non cambia; il `codice` mostrato si può cambiare.

### Regole

* Solo gli stati **attivi**: uno stato spento non è una destinazione. Un codice che
  il vocabolario non ha, o uno stato spento, rende vuoto: l'errore lo decide chi
  chiama (il verbo risponde «stato di destinazione non trovato»).
* Il vocabolario lo dice la mappa dei documenti
  ([`script.fn_doc_stato_modello`](/dbzero/script/funzioni/fn_doc_stato_modello)).
  Una tabella che non è nella mappa: `E_SCRIPT_CHIAMATA_NON_VALIDA`.

### Chi la legge

È la **sede unica** della traduzione: i verbi di stato (preventivo, bolla), la domanda
intera del backend
([`script.fn_doc_azione_passaggio`](/dbzero/script/funzioni/fn_doc_azione_passaggio)),
la fixture dei test e il backend. Prima la stessa traduzione era scritta in quattro
posti.
