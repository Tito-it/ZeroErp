## 📘 Documentazione Concettuale – Funzione `vendite.fn_sync_pagamento_fondo_fattura`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.fatture_fondi_fattura_source](/dbzero/vendite/tabelle/fatture_fondi_fattura_source)  
> • [pagamenti.centri_riscossione](/dbzero/pagamenti/tabelle/centri_riscossione)  
> • [pagamenti.vendite_movimenti](/dbzero/pagamenti/tabelle/vendite_movimenti)  
>
> **Approfondimento funzioni:**
>
> • [pagamenti.fn_get_saldo_fattura](/dbzero/pagamenti/funzioni/fn_get_saldo_fattura)  
> • [vendite.fn_reset_fondi_fattura](/dbzero/vendite/funzioni/fn_reset_fondi_fattura)  
>
---

### 🎯 Scopo Principale

(latest review 12-02-2026)  
La funzione **`vendite.fn_sync_pagamento_fondo_fattura()`** allinea i
movimenti in `pagamenti.vendite_movimenti` per i fondi fattura assegnati a una
fattura figlia.

---

### ✅ Regole principali

* `p_fattura_figlia_id` obbligatorio.
* Richiede un centro riscossione attivo con `is_fondo_fattura = true`.
* Lavora solo su source `ASSEGNATO` con `codice_interno = 'F_F_ADD_ACC'`.
* Se la fattura sorgente ha saldo `0`, la source viene portata a `ANNULLATO`.
* Per le source eseguibili crea/aggiorna un movimento dedicato in
  `pagamenti.vendite_movimenti` con:
  * `centro_riscossione_id` di tipo fondo fattura
  * date (`effettiva`, `registrazione`, `contabile`) allineate alla data fattura sorgente
  * `escluso_da_interessi = true`
  * metadato `origine = FONDO_FATTURA`.

---

### ✅ Output

Ritorna:

* `inserted_movimenti`: movimenti inseriti
* `updated_movimenti`: movimenti aggiornati
* `annullati_source`: source portate a stato `ANNULLATO`

---

### 🧪 Esempio d’uso

```sql
SELECT *
FROM vendite.fn_sync_pagamento_fondo_fattura(
  p_fattura_figlia_id => 123
);
```

---

{% include-markdown "signature-core.md" %}
