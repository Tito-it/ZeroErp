## 📘 Documentazione Concettuale – Trigger function `documenti.trgfn_documenti_generati_eventi_block_update`

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
> * [documenti.trgfn_documenti_generati_eventi_block_delete](/dbzero/documenti/funzioni/trgfn_documenti_generati_eventi_block_delete) — il blocco della cancellazione
> * [documenti.trgfn_documenti_generati_protect_snapshot](/dbzero/documenti/funzioni/trgfn_documenti_generati_protect_snapshot) — l'immutabilità sulla stampa
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — il rifiuto
>
> Guide:
>
> * [Documenti e stampe](/guide/documenti-e-stampe) — le garanzie del modulo

---

### 🎯 Scopo Principale

Trigger function `BEFORE UPDATE` su `documenti.documenti_generati_eventi` che rifiuta qualunque modifica di un
evento già registrato, su qualunque colonna.

Un evento è definitivo dal momento in cui si scrive: né il messaggio, né il dettaglio, né l'esito, né `meta`
cambiano dopo. Una correzione è un evento nuovo sulla stessa stampa.

---

### ⭐ Tutte le colonne, non un elenco

Il trigger non è `UPDATE OF` qualche colonna: rifiuta ogni `UPDATE`. Un elenco di colonne bloccate lascerebbe in
dubbio che cosa si possa davvero cambiare; la regola è che non si cambia niente.

Per lo stesso motivo i campi di audit dell'aggiornamento non si muovono mai: il trigger che li valorizza a ogni
`UPDATE` viene dopo questo, e non arriva a girare. Valgono come data e autore dell'inserimento.

---

### Codici errore

* `E_EVENTO_DOCUMENTO_UPDATE_VIETATA` — sempre; il contesto porta l'evento, la stampa, il tipo e il momento.

---

### Test

* `db/pgtap/documenti/test-documenti-generati-eventi.sql` — la modifica rifiutata.

---

### Note di migrazione

* 2026-05-03 — nasce il blocco, con la tabella.
* 2026-08-05 — il rifiuto arriva col suo codice, invece di un errore generico.

---

{% include-markdown "signature-core.md" %}
