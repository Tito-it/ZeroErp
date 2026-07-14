## 📘 Documentazione Concettuale – Trigger function `vendite.trgfn_v_resi_protect_num`

> 👀 [vendite.resi](/dbzero/vendite/tabelle/resi) ·
> [vendite.trgfn_resi_gen_numero](/dbzero/vendite/funzioni/trgfn_resi_gen_numero) ·
> [vendite.trgfn_v_ddt_protect_num](/dbzero/vendite/funzioni/trgfn_v_ddt_protect_num) (mirror)

---

### 🎯 Scopo Principale

(rev 2026-07-13)

`BEFORE UPDATE` su `vendite.resi`. Rende `numero` **immutabile una volta assegnato** (alla
CONFERMA), ma **consente la prima valorizzazione** `NULL → valore` (`CODICE_NON_MODIFICABILE` su ogni
modifica successiva). Sostituisce il lock piatto del framework (disabilitato in
`automation_lock_columns` con `enabled=f`), necessario perché il numero reso si assegna a CONFERMATO
e non all'INSERT. Mirror di `trgfn_v_ddt_protect_num`.
