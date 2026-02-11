## 📘 Documentazione Concettuale – Funzione `vendite.fn_genera_fondi_fattura_source`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
> • [vendite.fatture_fondi_fattura_source](/dbzero/vendite/tabelle/fatture_fondi_fattura_source)  
> • [pagamenti.vendite_movimenti](/dbzero/pagamenti/tabelle/vendite_movimenti)  
>
---

### 🎯 Scopo Principale

(latest review 11-02-2026)  
La funzione **`vendite.fn_genera_fondi_fattura_source()`** genera record
in `fatture_fondi_fattura_source` per fatture con `minimo = true`,
non ancora presenti e non pagate.

---

### ✅ Regole principali

* Parametri obbligatori (ID > 0).
* Seleziona fatture con `minimo = true`.
* Esclude fatture gia` presenti in `fatture_fondi_fattura_source`.
* Esclude fatture con saldo movimenti >= `totale_a_pagare`.
* Inserisce record con stato `DISPONIBILE`.

---

### ✅ Output

Ritorna il numero di record inseriti.

---

### 🧪 Esempio d’uso

```sql
SELECT vendite.fn_genera_fondi_fattura_source(
  p_billing_account_id => 100,
  p_utility_id => 1,
  p_tipo_doc_fiscale_id => 10,
  p_emittente_soggetto_ruolo_id => 7,
  p_valuta_id => 1,
  p_tipo_fondo_fattura_id => 1
);
```

---

{% include-markdown "signature-core.md" %}
