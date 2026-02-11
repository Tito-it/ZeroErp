## 📘 Documentazione Concettuale – Funzione `vendite.fn_ricalcola_fattura`

> 👀 **Vedi anche**
>
> **Approfondimento funzioni:**
>
> • [vendite.fn_ricalcola_riepilogo_iva_fattura](/dbzero/vendite/funzioni/fn_ricalcola_riepilogo_iva_fattura)  
> • [vendite.fn_ricalcola_totali_fattura](/dbzero/vendite/funzioni/fn_ricalcola_totali_fattura)  
>
---

### 🎯 Scopo Principale

La funzione **`vendite.fn_ricalcola_fattura()`** e` un wrapper che esegue,
**in sequenza**:

1. ricalcolo dei riepiloghi IVA
2. ricalcolo dei totali testata

---

### ✅ Regole principali

* `p_fattura_id` obbligatorio.
* Il ricalcolo totali applica regole di arrotondamento e soglie minimo
  definite per **emittente/utility**.

---

### ✅ Output

Non ritorna valori. Aggiorna la fattura.

---

### 🧪 Esempio d’uso

```sql
SELECT vendite.fn_ricalcola_fattura(
  p_fattura_id => 123
);
```

---

{% include-markdown "signature-core.md" %}
