## 📘 Documentazione Concettuale – Trigger function `documenti.trgfn_documenti_generati_block_delete`

> **Ultimo aggiornamento**: 14 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.documenti_generati](/dbzero/documenti/tabelle/documenti_generati) — il registro delle stampe che il trigger protegge
>
> Approfondimento funzioni:
>
> * [documenti.trgfn_documenti_generati_protect_snapshot](/dbzero/documenti/funzioni/trgfn_documenti_generati_protect_snapshot) — la stampa non cambia
> * [documenti.trgfn_documenti_generati_eventi_block_delete](/dbzero/documenti/funzioni/trgfn_documenti_generati_eventi_block_delete) — lo stesso blocco sugli eventi
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — il rifiuto
>
> Guide:
>
> * [Documenti e stampe](/guide/documenti-e-stampe) — le garanzie del modulo

---

### 🎯 Scopo Principale

Trigger function `BEFORE DELETE` su `documenti.documenti_generati` che rifiuta sempre la cancellazione di una
stampa, senza condizioni.

Ogni stampa è un fatto emesso: cancellarla toglierebbe un anello alla serie delle stampe di un documento e
renderebbe impossibile verificare il PDF consegnato. La vita di una stampa si chiude con lo stato, non con un
`DELETE`.

---

### Nessuna eccezione

Il rifiuto non guarda la riga né chi cancella: non c'è un interruttore per aggirarlo. Lo storico standard su
questa tabella è spento proprio perché la riga non si cancella e non cambia; senza questo blocco lo spegnimento
dello storico lascerebbe un buco di audit.

Una stampa non ha una data di scadenza: si conserva quanto serve all'azienda. Una pulizia, se un giorno servirà,
sarà un'operazione amministrativa esplicita, fuori dal ciclo dell'applicazione.

---

### Codici errore

* `E_DOCUMENTI_GENERATO_DELETE_BLOCKED` — sempre; il contesto porta l'id, l'`uid` e lo stato della stampa.

---

### Test

* `db/pgtap/documenti/test-documenti-generati.sql` — la cancellazione rifiutata.

---

### Note di migrazione

* 2026-05-01 — nasce il blocco.
* 2026-08-05 — il rifiuto arriva col suo codice: prima la chiamata al rifiuto era scritta male e moriva su un
  errore generico, che bloccava lo stesso ma senza dire perché.

---

{% include-markdown "signature-core.md" %}
