## 📘 Documentazione Concettuale – Trigger function `vendite.trgfn_resi_riconsegne_guard`

> 👀 [vendite.resi_righe_riconsegne](/dbzero/vendite/tabelle/resi_righe_riconsegne) ·
> [config.tipi_reso](/dbzero/config/tabelle/tipi_reso) ·
> [vendite.trgfn_ordini_ful_guard_consistenza](/dbzero/vendite/funzioni/trgfn_ordini_ful_guard_consistenza) (mirror)

---

### 🎯 Scopo Principale

(rev 2026-07-13)

`BEFORE INSERT/UPDATE` sul ponte `vendite.resi_righe_riconsegne`. Due regole + lock:

1. la riga reso referenziata deve essere di tipo **ri-consegna** (`tipi_reso.riapre_residuo = true`)
   → `E_RESO_RICONSEGNA_TIPO_NON_VALIDO`;
2. **non si ri-spedisce più di quanto reso**: Σ `qta` sulla stessa `resi_riga` ≤ quantità resa
   → `E_RESO_RICONSEGNA_SUPERA_RESO`;
3. lock `FOR UPDATE` serializzante (riga reso + gruppo riconsegne).
