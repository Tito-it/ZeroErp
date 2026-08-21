## 📘 Documentazione Concettuale – Trigger Function `vendite.trgfn_preventivi_righe_componenti_guard_pending()`

> 👀 **Vedi anche**
>
> Tabelle correlate:
>
> [vendite.preventivi_righe_componenti](/dbzero/vendite/tabelle/preventivi_righe_componenti) — tabella guardata
> [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) — pratica di richiesta approvazione (FK `pratica_approvazione_prezzo_id`)
>
> Funzioni correlate:
>
> [vendite.trgfn_preventivi_righe_guard_pending](/dbzero/vendite/funzioni/trgfn_preventivi_righe_guard_pending) — guard simmetrico sulla riga padre
> [vendite.trgfn_preventivi_guard_transizione_approvazione](/dbzero/vendite/funzioni/trgfn_preventivi_guard_transizione_approvazione) — guard complementare: blocca ACCETTATO se componente PENDING
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)
>
> Tipo ENUM:
>
> `stato_approvazione_prezzo` (colonna, non tabella) — PENDING/APPROVED/REJECTED
>
> Guide:
>
> [Gestione Listini v5 §6.1](/guide/gestione-listini) — workflow L3 approvazione out-of-policy

La trigger function **`vendite.trgfn_preventivi_righe_componenti_guard_pending()`** congela i **campi struttura** di un componente BoM mentre il componente è in `stato_approvazione_prezzo = 'PENDING'`. È il simmetrico di `trgfn_preventivi_righe_guard_pending` applicato alla tabella componenti.

---

### 🎯 Scopo Principale

- **Decisione L3 sul componente esatto** — quando un componente ha un prezzo out-of-policy in attesa di approvazione, l'approvatore L3 deve decidere sulla riga esatta che è stata proposta. Cambi a prezzo, quantita' o articolo durante la fase di approvazione renderebbero la decisione ambigua.
- **Coerenza con il guard L3 esistente** — `trgfn_preventivi_guard_transizione_approvazione` blocca la transizione ad ACCETTATO se qualsiasi componente è PENDING. Insieme garantiscono che nessuna decisione commerciale avvenga con prezzi incerti sui componenti BoM CASO A.
- **Pattern denylist difensivo** — elenco esplicito dei campi struttura: se `preventivi_righe_componenti` viene estesa con nuove colonne struttura, il trigger va aggiornato.

---

### Logica

**Guard attivo solo quando `OLD.stato_approvazione_prezzo = 'PENDING'`**. In tutti gli altri casi fa early return senza vincoli.

Quando il guard è attivo:

- **Allowlist (ammessi)**: `stato_approvazione_prezzo`, `pratica_approvazione_prezzo_id`, `meta`, `data_update`, `user_update` (questi ultimi gestiti da `trgfn_audit_data_user_generic`).
- **Denylist (bloccati)**: `riga_preventivo_id`, `articolo_componente_id`, `componente_id`, `coeff_qta_snapshot`, `quantita`, `uom_operativa_id`, `factor_to_base`, `qta_operativa`, `prezzo_unitario`, `iva_id`, `origine_prezzo`, `ordine`, `attivo` → raise `E_COMPONENTE_PREZZO_PENDENTE`.

**Transizioni workflow ammesse**: `PENDING → APPROVED`, `PENDING → REJECTED`. Queste modifcano solo `stato_approvazione_prezzo` (allowlist) e passano senza blocco.

**Update misto rilevato**: se l'UPDATE cambia sia lo stato sia un campo struttura, il trigger blocca. Aggiustamenti post-approvazione richiedono un UPDATE separato dopo la transizione di stato.

---

### Applicazione

Trigger creato dalla migration `20260511-08-02`:

- **`trg_preventivi_righe_componenti_a10_guard_pending_upd`** su `vendite.preventivi_righe_componenti`

Specifiche:

- Timing: **BEFORE UPDATE**
- Fase: **_a10_** (guard/block)
- Scope: **FOR EACH ROW**
- **No `UPDATE OF <colonna>`**: deve intercettare qualsiasi UPDATE su un componente PENDING per confrontare NEW vs OLD su tutte le colonne struttura.

---

### Codice errore sollevato

**`E_COMPONENTE_PREZZO_PENDENTE`** (id 439) — `config.messaggi_errore` CSV.

Messaggio: `"Modifica struttura bloccata: il componente BoM [id=<id>] è in attesa di approvazione prezzo (stato_approvazione_prezzo=PENDING)."`.

Causa: componente in workflow L3, campi struttura frozen. Soluzione: attendere APPROVED/REJECTED o rifiutare la pratica prima di modificare.

---

### Quando NON scatta

- `OLD.stato_approvazione_prezzo IS DISTINCT FROM 'PENDING'`: early return. La grande maggioranza dei componenti (stato NULL o già deciso) non ha vincoli.
- **INSERT** di un componente con stato PENDING: scope BEFORE UPDATE, non scatta.
- **DELETE** di un componente PENDING: scope BEFORE UPDATE, non scatta.
- **UPDATE di soli campi allowlist** (es. transizione stato, aggiornamento pratica, meta): pass-through.

---

### Note implementative

- Implementazione identica a `trgfn_preventivi_righe_guard_pending` con denylist adattata alle colonne di `preventivi_righe_componenti`.
- Il cast `'PENDING'::config.stato_approvazione_prezzo` è necessario per il confronto ENUM efficiente.
- `%TYPE` non usato per `v_comp_id`: il trigger lavora solo con `NEW`/`OLD` già tipati dalla tabella.
