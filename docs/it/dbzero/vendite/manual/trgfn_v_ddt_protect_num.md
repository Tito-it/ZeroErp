## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_v_ddt_protect_num`

> 👀 **Vedi anche**
>
> Tabelle:
> [vendite.ddt](/dbzero/vendite/tabelle/ddt)
> [dbops.automation_lock_columns](/dbzero/dbops/tabelle/automation_lock_columns)
>
> Funzioni:
> [vendite.trgfn_ddt_gen_numero_emesso](/dbzero/vendite/funzioni/trgfn_ddt_gen_numero_emesso)

---

### 🎯 Scopo Principale

(rev 2026-07-09)

**Protect condizionale** del `numero` DDT: lo rende **immutabile una volta assegnato** (a EMESSO),
ma **consente la prima valorizzazione** (`NULL → valore`). Trigger function agganciata come
`trg_ddt_a10_v_protect_num_upd` (`BEFORE UPDATE OF numero`).

Regola: se `OLD.numero IS NOT NULL AND NEW.numero IS DISTINCT FROM OLD.numero` →
`CODICE_NON_MODIFICABILE`.

### Perché bespoke (eccezione al framework lock)

Il lock generico `script.trgfn_lock_columns` (auto-provisionato da `dbops.automation_lock_columns`)
blocca **qualsiasi** cambio, inclusa la prima assegnazione `NULL → valore` — incompatibile col
numero assegnato a EMESSO. Perciò, come per le fatture, la riga `automation_lock_columns` del DDT è
**disabilitata** (`enabled = false`) e si usa questo protect condizionale. Il trigger è
`BEFORE UPDATE OF numero`: **non** scatta sull'UPDATE di solo stato, quindi la prima assegnazione
(via `trgfn_ddt_gen_numero_emesso`) passa.
