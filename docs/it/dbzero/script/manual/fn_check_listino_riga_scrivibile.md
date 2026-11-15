## 📘 Documentazione Concettuale – Funzione `script.fn_check_listino_riga_scrivibile(p_listino_versione_id, p_listino_riga_id, p_operazione)`

> **Ultimo aggiornamento**: 15 novembre 2026

> 👀 **Vedi anche**
>
> [vendite.trgfn_listini_righe_guard_stato](/dbzero/vendite/manual/trgfn_listini_righe_guard_stato) — il guard che la solleva ·
> [vendite.vw_listini_versioni_azioni](/dbzero/vendite/manual/vw_listini_versioni_azioni) ·
> [vendite.vw_listini_righe_azioni](/dbzero/vendite/manual/vw_listini_righe_azioni) ·
> [config.stati_doc_listino_versioni](/dbzero/config/manual/stati_doc_listino_versioni) ·
> [linee guida SQL](/linee-guida-sql) §12.5

### 🎯 Scopo

**Perché una riga di listino non si scrive.** Restituisce l'elenco dei motivi (`codice`,
`reason`, `reason_key`, `dettaglio`, `valori`); il primo è quello che si solleva. Elenco vuoto =
si scrive. Non solleva.

* Senza `p_listino_riga_id` la domanda è **una riga nuova** della versione (INSERT).
* Con `p_listino_riga_id` è **la riga che c'è** (UPDATE, DELETE).
* `p_operazione` entra nei valori del messaggio; senza, è INSERT o UPDATE secondo la riga.

| # | Codice | `reason` | Quando |
| --- | --- | --- | --- |
| 1 | `E_RIGA_LISTINO_VERSIONE_CHIUSA` | `VERSIONE_CHIUSA` | la versione è CHIUSA: è la storia dei prezzi, e non si scrive niente, nemmeno una riga nuova |
| 2 | `E_RIGA_LISTINO_PROPAGATA` | `RIGA_PROPAGATA` | fuori dalla bozza, il prezzo della riga è stato usato da un documento |

Le `reason_key` sono `vendite.listini.azione_reason.versione_chiusa` e
`vendite.listini.azione_reason.riga_propagata`.

### Regole

* **In bozza si scrive tutto.** La bozza è lo stato che il vocabolario marca `iniziale`, mai il
  codice `BOZZA`.
* **CHIUSA si nomina col codice**: è la destinazione della chiusura (la versione la raggiunge dal
  job, `vendite.fn_chiudi_versioni_listino_scadute`).
* **Fuori dalla bozza una riga nuova è una rettifica**, e si scrive (in una versione ATTIVA).
* **Propagata**: la riga è citata (`listino_riga_id`) da una riga di commessa, un'attività
  fatturabile, o una riga principale o un componente di preventivo, ordine, contratto, DDT od
  offerta, anche in bozza. Una tabella nuova che cita una riga di listino entra qui, con un
  `UNION ALL`.
* I documenti si leggono col perimetro di chi scrive (`SECURITY INVOKER`), come il guard.
* La chiamano il guard di stato delle righe (che solleva il primo motivo) e le due superfici: una
  regola, tre letture.

---

{% include-markdown "signature-core.md" %}
