## 📘 Documentazione Concettuale – Funzione `pagamenti.fn_get_saldo_fattura_contabili`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [pagamenti.vendite_contabili_righe](/dbzero/pagamenti/tabelle/vendite_contabili_righe)  
> • [pagamenti.vendite_contabili_righe_stati](/dbzero/pagamenti/tabelle/vendite_contabili_righe_stati)  
> • [pagamenti.vendite_contabili](/dbzero/pagamenti/tabelle/vendite_contabili)  
>
---

### 🎯 Scopo Principale

(latest review 13-02-2026)  
La funzione **`pagamenti.fn_get_saldo_fattura_contabili()`** restituisce il
saldo contabile di una fattura calcolato sulle sole righe in stato
`is_postabile = true`.

---

### ✅ Regole principali

* `p_fattura_id` obbligatorio (`> 0`).
* Considera solo:
  * `vendite_contabili_righe.attivo = true`
  * `vendite_contabili_righe_stati.is_postabile = true`
  * testata contabile con stato non finale (`vendite_contabili_stati.is_final = false`),
    con fallback `stato_id NULL` trattato come non finale.

---

### ✅ Output

Ritorna una riga con:

* `saldo_contabile` (numeric)
* `has_righe_postabili` (boolean)

---

### 🧪 Esempio d’uso

```sql
SELECT *
FROM pagamenti.fn_get_saldo_fattura_contabili(123);
```

---

{% include-markdown "signature-core.md" %}
