## 📘 Documentazione Concettuale – Trigger Function `vendite.trgfn_contratti_righe_componenti_guard_pending()`

> 👀 **Vedi anche**
>
> Tabelle correlate:
>
> [vendite.contratti_righe_componenti](/dbzero/vendite/tabelle/contratti_righe_componenti) — tabella guardata
> [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) — pratica di richiesta approvazione
>
> Funzioni correlate:
>
> [vendite.trgfn_preventivi_righe_componenti_guard_pending](/dbzero/vendite/funzioni/trgfn_preventivi_righe_componenti_guard_pending) — guard simmetrico su preventivi (pattern originale)
> [vendite.trgfn_contratti_guard_transizione_stato](/dbzero/vendite/funzioni/trgfn_contratti_guard_transizione_stato) — guard complementare su testata: blocca DRAFT→ATTIVO se componente PENDING
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)
>
> Tipo ENUM:
>
> [config.stato_approvazione_prezzo](/dbzero/config/tabelle/stato_approvazione_prezzo) — PENDING/APPROVED/REJECTED
>
> Guide:
>
> [Gestione Listini v5 §6.1](/guide/gestione-listini) — workflow L3 approvazione out-of-policy

La trigger function **`vendite.trgfn_contratti_righe_componenti_guard_pending()`** congela i **campi struttura** di un componente BoM CASO A sul contratto mentre il componente è in `stato_approvazione_prezzo = 'PENDING'`. Pattern simmetrico a `trgfn_preventivi_righe_componenti_guard_pending`.

---

### 🎯 Scopo Principale

- **Decisione L3 sul componente esatto** — quando un componente di una riga contratto ha un prezzo out-of-policy in attesa di approvazione, l'approvatore L3 deve decidere sulla riga esatta proposta.
- **Guard testata complementare** — `trgfn_contratti_guard_transizione_stato` (aggiornato in `20260511-41`) blocca la transizione DRAFT→ATTIVO se qualsiasi componente è PENDING. I due guard garantiscono che nessun contratto divenga operativo con prezzi incerti.
- **Pattern denylist difensivo** — elenco esplicito dei campi struttura.

---

### Logica

**Guard attivo solo quando `OLD.stato_approvazione_prezzo = 'PENDING'`**. In tutti gli altri casi fa early return senza vincoli.

Quando il guard è attivo:

- **Allowlist (ammessi)**: `stato_approvazione_prezzo`, `pratica_approvazione_prezzo_id`, `meta`, `data_update`, `user_update`.
- **Denylist (bloccati)**: `riga_contratto_id`, `articolo_componente_id`, `componente_id`, `coeff_qta_snapshot`, `quantita`, `uom_operativa_id`, `factor_to_base`, `qta_operativa`, `prezzo_unitario`, `iva_id`, `origine_prezzo`, `ordine`, `attivo` → raise `E_COMPONENTE_PREZZO_PENDENTE`.

**Transizioni workflow ammesse**: `PENDING → APPROVED`, `PENDING → REJECTED` — pass-through senza blocco.

---

### Applicazione

Trigger creato dalla migration `20260511-40-02`:

- **`trg_contratti_righe_componenti_a10_guard_pending_upd`** su `vendite.contratti_righe_componenti`
- Timing: **BEFORE UPDATE** — Fase: **_a10_** — Scope: **FOR EACH ROW**

---

### Codice errore sollevato

**`E_COMPONENTE_PREZZO_PENDENTE`** (id 439) — `config.messaggi_errore`.

---

### Guard complementare sulla testata

A differenza di ordini e DDT (che non hanno guard di transizione stato), per i contratti esiste il doppio livello di protezione:

| Livello | Guard | Blocca |
|---|---|---|
| Componente | `trgfn_contratti_righe_componenti_guard_pending` | UPDATE struttura del componente in PENDING |
| Testata | `trgfn_contratti_guard_transizione_stato` (aggiornato) | DRAFT→ATTIVO se qualsiasi componente è PENDING |

Questo garantisce che un contratto non possa diventare operativo con prezzi in attesa di approvazione.

---

### Differenze rispetto a `trgfn_preventivi_righe_componenti_guard_pending`

| Aspetto | Preventivi | Contratti |
|---|---|---|
| Tabella | `preventivi_righe_componenti` | `contratti_righe_componenti` |
| FK col denylist | `riga_preventivo_id` | `riga_contratto_id` |
| Guard testata | blocca `ACCETTATO` | blocca `ATTIVO` (DRAFT→ATTIVO) |

---

### Quando NON scatta

- `OLD.stato_approvazione_prezzo IS DISTINCT FROM 'PENDING'`: early return.
- INSERT/DELETE: scope BEFORE UPDATE, non scatta.
- UPDATE di soli campi allowlist: pass-through.
