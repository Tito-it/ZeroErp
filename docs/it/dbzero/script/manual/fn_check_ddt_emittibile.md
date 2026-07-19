## 📘 Documentazione Concettuale – Funzione `script.fn_check_ddt_emittibile`

> 👀 **Vedi anche**
>
**Consumatori (guard, sollevano):**
>
• [vendite.trgfn_ddt_guard_transizione](/dbzero/vendite/funzioni/trgfn_ddt_guard_transizione)
> • [vendite.trgfn_ddt_guard_causale_emissione](/dbzero/vendite/funzioni/trgfn_ddt_guard_causale_emissione)
> • [vendite.trgfn_ddt_guard_indirizzi_obbligatori](/dbzero/vendite/funzioni/trgfn_ddt_guard_indirizzi_obbligatori)
> • [vendite.trgfn_ddt_guard_transizione_approvazione](/dbzero/vendite/funzioni/trgfn_ddt_guard_transizione_approvazione)
>
**Consumatore (capability, disabilita+motiva):**
>
• [script.fn_available_actions_ddt](/dbzero/script/funzioni/fn_available_actions_ddt)

### 🎯 Scopo Principale

(creata 2026-07-19 — brief-db-guard-righe-avanzamento-stato §1a-bis Rev 2)

**Single source dei motivi che impediscono l'emissione (EMESSO) di un DDT.**
Ritorna `[]` se il DDT è emittibile, altrimenti l'array **ordinato** dei motivi
ostativi: `[{codice, reason, reason_key, dettaglio}, ...]`.

Nasce da un difetto reale: le cinque condizioni di emissione vivevano sparse in
quattro trigger, e la capability (`fn_available_actions_ddt`) ne conosceva una
sola — il pulsante «Emetti» risultava abilitato e il click falliva con 409.
Con questa funzione capability e guard leggono **lo stesso verdetto** e non
possono più divergere: al prossimo vincolo aggiunto, si aggiunge QUI e basta.

### Le cinque condizioni (in ordine di restituzione)

| # | asse | codice | quando |
|---|---|---|---|
| 1 | struttura | `E_DDT_EMISSIONE_SENZA_RIGHE` (543) | nessuna riga attiva — zero righe = niente da trasportare; il "solo trasporto" è righe **senza prezzo**, non zero righe |
| 2 | intento | `E_DDT_CAUSALE_OBBLIGATORIA` (544) | `causale_trasporto_id` NULL — in bozza il NULL è legittimo (DL-28): il vincolo è all'emissione |
| 3 | dati riga | `E_DDT_PREZZO_NON_RISOLVIBILE` (545) | causale **fatturabile** e almeno una riga attiva senza prezzo risolvibile (proprio o ereditato dall'ordine via fulfillment) |
| 4 | testata | `E_INDIRIZZO_DOC_OBBLIGATORIO` | mancano indirizzi marcati obbligatori per l'ambito DDT |
| 5 | componenti | `E_COMPONENTE_PREZZO_PENDENTE` / `E_DOC_COMPONENTI_PENDING_VALORIZZAZIONE` | componenti BoM CASO A in approvazione o senza prezzo |

### Regole

- **Pura** (convenzione `fn_check_*`): nessun raise, nessuna scrittura, STABLE.
  Chi solleva sono i guard, ognuno per i codici di propria competenza.
- **Il parametro è una riga `vendite.ddt`, non un id** — scelta deliberata:
  i guard sono `BEFORE UPDATE` e devono valutare i valori **candidati** (`NEW`).
  Con un id la funzione rileggerebbe da tabella i valori ancora vecchi, e un
  UPDATE che imposta insieme stato e causale verrebbe bloccato a torto.
  Le condizioni sulle righe figlie leggono comunque da tabella (un UPDATE di
  testata non le sta cambiando).
- La capability mostra come `reason`/`reason_key` il **primo** motivo
  dell'array, ed espone l'array completo nel campo `reasons` dell'azione.
- ⚠️ `vw_ddt_righe_iva_base` NON è riusabile per la condizione 3: filtra
  `prezzo_unitario IS NOT NULL`, perdendo proprio le righe da esaminare.

### Dipendenze DB

`vendite.ddt_righe`, `config.causali_trasporto` (`fatturabile`),
`vendite.ordini_righe_fulfillment` + `vendite.ordini_righe` (eredità prezzo),
`vendite.ddt_indirizzi` + `script.fn_indirizzi_obbligatori_mancanti`,
`vendite.ddt_righe_componenti`.
