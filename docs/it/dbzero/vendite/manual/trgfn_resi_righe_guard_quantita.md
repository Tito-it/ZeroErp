## 📘 Documentazione Concettuale – Trigger function `vendite.trgfn_resi_righe_guard_quantita`

> **Ultimo aggiornamento**: 14 novembre 2026

> 👀 [vendite.resi_righe](/dbzero/vendite/tabelle/resi_righe) · [vendite.ddt_righe](/dbzero/vendite/tabelle/ddt_righe) ·
> [vendite.trgfn_ordini_ful_guard_consistenza](/dbzero/vendite/funzioni/trgfn_ordini_ful_guard_consistenza) (mirror)

---

### 🎯 Scopo Principale

(rev 2026-07-13)

`BEFORE INSERT/UPDATE` su `vendite.resi_righe` (fase **`a20`**, dopo il calcolo della quantità base
da `qta_from_operativa`). **Anti over-return**: la Σ delle quantità rese dai resi **non annullati**
(non nello stato di annullo: la colonna `is_abortito` di
[config.stati_doc_reso](/dbzero/config/tabelle/stati_doc_reso)) sulla stessa `ddt_riga_id` non può
superare la quantità consegnata di quella riga DDT
(`E_RESO_QTA_SUPERA_CONSEGNATO`).

Lock `FOR UPDATE` serializzante (riga DDT + gruppo resi sulla stessa riga) per bloccare l'over-return
concorrente — mirror di `trgfn_ordini_ful_guard_consistenza`.
