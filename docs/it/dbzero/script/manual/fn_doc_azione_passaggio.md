## 📘 Documentazione Concettuale – Funzione `script.fn_doc_azione_passaggio(regclass, bigint, text)`

> 👀 **Vedi anche**
>
> [script.fn_doc_passaggio](/dbzero/script/funzioni/fn_doc_passaggio) ·
> [script.fn_doc_stato_id](/dbzero/script/funzioni/fn_doc_stato_id) ·
> [script.fn_stato_emissione_id](/dbzero/script/funzioni/fn_stato_emissione_id) ·
> guida [Il modello del documento di vendita](/guide/modello-documento-di-vendita) §6

### 🎯 Scopo
(25-10-2026 — brief `brief-modello-documento-vendita` §8, richiesta del team backend)

**Che cosa chiede questo passaggio.** Il backend risponde «non hai il permesso» (403)
prima di aprire la transazione, con le stesse regole del verbo. Per farlo deve sapere
quale azione chiede il passaggio dallo stato in cui il documento si trova allo stato
richiesto. Questa funzione risponde alla domanda intera: riceve il documento e il codice
dello stato richiesto, e rende una riga.

| Colonna | Che cosa dice |
| --- | --- |
| `stato_da_id` | lo stato in cui il documento si trova |
| `stato_a_id` | lo stato richiesto; vuoto se il codice non è uno stato attivo |
| `emissione` | lo stato richiesto è quello di emissione: si raggiunge solo da «Emetti» |
| `nella_matrice` | il passaggio è nella matrice; se no, il guard del documento lo rifiuterà |
| `manuale` | `false`: passaggio di processo, che non si chiede a mano |
| `azione_processo_codename` | l'azione che il passaggio chiede; vuoto: basta il permesso sul documento |

### Regole

* Nessuna riga se il documento non c'è o chi chiama non lo vede (gira con i diritti di
  chi chiama).
* Non decide: il backend applica la regola del verbo (azione → permesso dell'azione;
  nessuna azione → permesso sul documento).
* Un documento non ancora portato al modello, o una tabella fuori mappa:
  `E_SCRIPT_CHIAMATA_NON_VALIDA`.
