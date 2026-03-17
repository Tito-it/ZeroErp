## 📘 Documentazione Concettuale – Funzione `pagamenti.fn_get_saldo_fattura`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [pagamenti.vendite_movimenti](/dbzero/pagamenti/tabelle/vendite_movimenti)  
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
>
🎯 Scopo Principale

(latest review 13-02-2026)  
La funzione **`pagamenti.fn_get_saldo_fattura()`** restituisce il **residuo**
della fattura:

* `saldo = totale_a_pagare - somma(movimenti attivi)`

---

### Regole principali

* `p_fattura_id` obbligatorio (`> 0`).
* Verifica che la fattura esista.
* Considera solo movimenti `attivo = true`.

---

### Output

Ritorna una riga con:

* `saldo` (numeric, residuo fattura)
* `has_movimenti` (boolean)

---

### Esempio d’uso

```sql
SELECT *
FROM pagamenti.fn_get_saldo_fattura(123);
```

---

{% include-markdown "signature-core.md" %}
