## 📘 Documentazione Concettuale – Funzione `vendite.fn_ricalcola_totali_fattura`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
> • [vendite.fatture_riepiloghi_iva](/dbzero/vendite/tabelle/fatture_riepiloghi_iva)  
> • [vendite.fatture_fondi_fattura](/dbzero/vendite/tabelle/fatture_fondi_fattura)  
>
> **Approfondimento funzioni:**
>
> • [vendite.fn_ricalcola_fattura](/dbzero/vendite/funzioni/fn_ricalcola_fattura)  

---

### 🎯 Scopo Principale

(latest review 10-02-2026)  
La funzione **`vendite.fn_ricalcola_totali_fattura()`** ricalcola i totali
della testata fattura a partire dai riepiloghi IVA e dai fondi fattura.

---

### ✅ Regole principali

* `p_fattura_id` obbligatorio e `> 0`.
* `imponibile_tot` e `imposta_tot` derivano da `vendite.fatture_riepiloghi_iva`.
* I fondi fattura sono sommati da `vendite.fatture_fondi_fattura` (solo `attivo = true`).
* `totale_a_pagare` = `totale_doc` + arrotondamenti + somma fondi.

---

### ✅ Output

Effetti principali:

* aggiorna `imponibile_tot`, `imposta_tot`, `totale_doc`, `totale_a_pagare`.

---

### 🧪 Esempio d’uso

```sql
SELECT vendite.fn_ricalcola_totali_fattura(123);
```

---

{% include-markdown "signature-core.md" %}
