## 📘 Documentazione Concettuale – Trigger function `vendite.trgfn_resi_riconsegne_guard`

> 👀 [vendite.resi_righe_riconsegne](/dbzero/vendite/tabelle/resi_righe_riconsegne) ·
> [config.tipi_reso](/dbzero/config/tabelle/tipi_reso) ·
> [vendite.trgfn_ordini_ful_guard_consistenza](/dbzero/vendite/funzioni/trgfn_ordini_ful_guard_consistenza) (mirror)

---

### 🎯 Scopo Principale

(rev 2026-07-26)

`BEFORE INSERT/UPDATE` sul ponte `vendite.resi_righe_riconsegne`. Due regole + lock:

1. la riga reso referenziata deve essere di tipo **ri-consegna** (`tipi_reso.riapre_residuo = true`)
   → `E_RESO_RICONSEGNA_TIPO_NON_VALIDO`;
2. **non si ri-spedisce più di quanto reso**, al netto anche delle quote **rinunciate**:
   `Σ riconsegnate + Σ rinunciate ≤ quantità resa` → `E_RESO_RICONSEGNA_SUPERA_RESO`;
3. lock `FOR UPDATE` serializzante (riga reso + **entrambi** i ponti).

### ⚠️ Perché conta anche le rinunce (rev 2026-07-26)

Le due uscite di una riga reso — ri-spedire al cliente e dichiarare la quota **definitiva**
([`resi_righe_rinunce`](/dbzero/vendite/tabelle/resi_righe_rinunce)) — **consumano la stessa
copertura**. Finché questo guard sommava solo le ri-consegne, su una riga da 10 con 7
rinunciati vedeva ancora residuo 10 e lasciava ri-spedire 10: `Σric + Σrin = 17 > 10`,
invariante violato **dal lato opposto**.

L'invariante `quantita ≥ Σric + Σrin` va quindi presidiato **simmetricamente**: qui e nel
gemello [`trgfn_resi_rinunce_guard`](/dbzero/vendite/funzioni/trgfn_resi_rinunce_guard).
Presidiare un solo lato non basta.

Il `FOR UPDATE` su `resi_righe` (la **riga padre**) è ciò che serializza rinuncia e
ri-consegna concorrenti: nessun advisory lock serve.
