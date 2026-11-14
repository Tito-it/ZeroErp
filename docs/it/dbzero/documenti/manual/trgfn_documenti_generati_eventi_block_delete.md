## 📘 Documentazione Concettuale – Trigger function `documenti.trgfn_documenti_generati_eventi_block_delete`

> **Ultimo aggiornamento**: 14 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.documenti_generati_eventi](/dbzero/documenti/tabelle/documenti_generati_eventi) — la timeline che il trigger protegge
>
> Approfondimento funzioni:
>
> * [documenti.trgfn_documenti_generati_eventi_block_update](/dbzero/documenti/funzioni/trgfn_documenti_generati_eventi_block_update) — il blocco della modifica
> * [documenti.trgfn_documenti_generati_block_delete](/dbzero/documenti/funzioni/trgfn_documenti_generati_block_delete) — lo stesso blocco sulla stampa
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — il rifiuto
>
> Guide:
>
> * [Documenti e stampe](/guide/documenti-e-stampe) — le garanzie del modulo

---

### 🎯 Scopo Principale

Trigger function `BEFORE DELETE` su `documenti.documenti_generati_eventi` che rifiuta sempre la cancellazione di
un evento.

La timeline di una stampa si aggiunge e basta: un evento sbagliato non si toglie, si registra un evento nuovo
che lo corregge, con l'esito `KO` o `WARN` e il riferimento nel dettaglio.

---

### Nessuna eccezione

Il rifiuto non guarda la riga né chi cancella. Insieme al blocco della modifica rende la timeline immutabile, ed è
la ragione per cui la tabella non ha lo storico standard.

---

### Codici errore

* `E_EVENTO_DOCUMENTO_DELETE_VIETATA` — sempre; il contesto porta l'evento, la stampa, il tipo e il momento.

---

### Test

* `db/pgtap/documenti/test-documenti-generati-eventi.sql` — la cancellazione rifiutata.

---

### Note di migrazione

* 2026-05-03 — nasce il blocco, con la tabella.
* 2026-08-05 — il rifiuto arriva col suo codice, invece di un errore generico.

---

{% include-markdown "signature-core.md" %}
