## 📘 Documentazione Concettuale – Funzione `vendite.fn_ricalcola_fattura`

> 👀 **Vedi anche**
>
> **Approfondimento funzioni:**
>
> • [vendite.fn_ricalcola_riepilogo_iva_fattura](/dbzero/vendite/funzioni/fn_ricalcola_riepilogo_iva_fattura)  
> • [vendite.fn_ricalcola_totali_fattura](/dbzero/vendite/funzioni/fn_ricalcola_totali_fattura)  

---

### 🎯 Scopo Principale

(latest review 10-02-2026)  
La funzione **`vendite.fn_ricalcola_fattura()`** e` un wrapper che esegue,
in sequenza, il ricalcolo dei riepiloghi IVA e dei totali testata.

---

### ✅ Regole principali

* `p_fattura_id` obbligatorio e `> 0`.
* Usa `fn_ricalcola_riepilogo_iva_fattura` e poi `fn_ricalcola_totali_fattura`.

---

### ✅ Output

Ritorna una riga con i totali testata aggiornati.

---

### 🧪 Esempio d’uso

```sql
SELECT *
FROM vendite.fn_ricalcola_fattura(123);
```

---

{% include-markdown "signature-core.md" %}
