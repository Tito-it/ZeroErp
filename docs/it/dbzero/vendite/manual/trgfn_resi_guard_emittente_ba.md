## 📘 Documentazione Concettuale – Trigger function `vendite.trgfn_resi_guard_emittente_ba`

> 👀 [vendite.resi](/dbzero/vendite/tabelle/resi) ·
> [vendite.trgfn_resi_normalize](/dbzero/vendite/funzioni/trgfn_resi_normalize) ·
> [vendite.trgfn_ddt_guard_emittente_ba](/dbzero/vendite/funzioni/trgfn_ddt_guard_emittente_ba) (mirror)

---

### 🎯 Scopo Principale

(rev 2026-07-13)

`BEFORE INSERT/UPDATE OF billing_account_id, emittente_fiscale_id` su `vendite.resi`, fase **`z10`**
(dopo `trgfn_resi_normalize`, così vede i valori finali risolti). Verifica la **coerenza
emittente↔BA**: `emittente_fiscale_id` deve coincidere con
`anagrafiche.fn_get_emittente_fiscale_pk(billing_account_id)` (skip se BA NULL) —
`E_RESO_EMITTENTE_BA_INCOERENTE`.

All'INSERT eredita da un DDT già coerente → passa per costruzione; il guard protegge le UPDATE che
facciano divergere emittente o BA. Mirror di `trgfn_ordini_guard_emittente_ba`.
