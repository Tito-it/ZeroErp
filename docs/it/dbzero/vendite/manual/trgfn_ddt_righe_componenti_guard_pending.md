## 📘 Documentazione Concettuale – Trigger Function `vendite.trgfn_ddt_righe_componenti_guard_pending()`

> 👀 **Vedi anche**
>
> Tabelle correlate:
>
> [vendite.ddt_righe_componenti](/dbzero/vendite/tabelle/ddt_righe_componenti) — tabella guardata
> [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) — pratica di richiesta approvazione
>
> Funzioni correlate:
>
> [vendite.trgfn_preventivi_righe_componenti_guard_pending](/dbzero/vendite/funzioni/trgfn_preventivi_righe_componenti_guard_pending) — guard simmetrico su preventivi (pattern originale)
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)
>
> Tipo ENUM:
>
> `stato_approvazione_prezzo` (colonna, non tabella) — PENDING/APPROVED/REJECTED
>
> Guide:
>
> [Gestione Listini v5 §6.1](/guide/gestione-listini) — workflow L3 approvazione out-of-policy

La trigger function **`vendite.trgfn_ddt_righe_componenti_guard_pending()`** congela i **campi struttura** di un componente BoM CASO A sul DDT mentre il componente è in `stato_approvazione_prezzo = 'PENDING'`. Pattern simmetrico a `trgfn_preventivi_righe_componenti_guard_pending`.

---

### 🎯 Scopo Principale

- **Decisione L3 sul componente esatto** — quando un componente di una riga DDT ha un prezzo out-of-policy in attesa di approvazione, l'approvatore L3 deve decidere sulla riga esatta proposta.
- **Pattern denylist difensivo** — elenco esplicito dei campi struttura. Se `ddt_righe_componenti` viene estesa con nuove colonne struttura, il trigger va aggiornato.

---

### Logica

**Guard attivo solo quando `OLD.stato_approvazione_prezzo = 'PENDING'`**. In tutti gli altri casi fa early return senza vincoli.

Quando il guard è attivo:

- **Allowlist (ammessi)**: `stato_approvazione_prezzo`, `pratica_approvazione_prezzo_id`, `meta`, `data_update`, `user_update`.
- **Denylist (bloccati)**: `riga_ddt_id`, `articolo_componente_id`, `componente_id`, `coeff_qta_snapshot`, `quantita`, `uom_operativa_id`, `factor_to_base`, `qta_operativa`, `prezzo_unitario`, `iva_id`, `origine_prezzo`, `ordine`, `attivo` → raise `E_COMPONENTE_PREZZO_PENDENTE`.

**Transizioni workflow ammesse**: `PENDING → APPROVED`, `PENDING → REJECTED` — pass-through senza blocco.

---

### Applicazione

Trigger creato dalla migration `20260511-39-02`:

- **`trg_ddt_righe_componenti_a10_guard_pending_upd`** su `vendite.ddt_righe_componenti`
- Timing: **BEFORE UPDATE** — Fase: **_a10_** — Scope: **FOR EACH ROW**

---

### Codice errore sollevato

**`E_COMPONENTE_PREZZO_PENDENTE`** (id 439) — `config.messaggi_errore`.

Causa: componente in workflow L3, campi struttura frozen. Soluzione: attendere APPROVED/REJECTED prima di modificare.

---

### Differenze rispetto a `trgfn_preventivi_righe_componenti_guard_pending`

| Aspetto | Preventivi | DDT |
|---|---|---|
| Tabella | `preventivi_righe_componenti` | `ddt_righe_componenti` |
| FK col denylist | `riga_preventivo_id` | `riga_ddt_id` |
| Context JSONB | `riga_preventivo_id` | `riga_ddt_id` |
| Guard testata complementare (dal 2026-09-24) | ✅ `trgfn_preventivi_guard_transizione` / `fn_check_preventivo_emettibile` → [`fn_check_prezzi_autorizzati`](/dbzero/script/funzioni/fn_check_prezzi_autorizzati) | ✅ `fn_check_ddt_emittibile` punto 5 (solo se la causale vende), sollevato da `trgfn_ddt_guard_transizione_approvazione` → [`fn_check_prezzi_autorizzati`](/dbzero/script/funzioni/fn_check_prezzi_autorizzati) |

---

### Quando NON scatta

- `OLD.stato_approvazione_prezzo IS DISTINCT FROM 'PENDING'`: early return.
- INSERT/DELETE: scope BEFORE UPDATE, non scatta.
- UPDATE di soli campi allowlist: pass-through.
