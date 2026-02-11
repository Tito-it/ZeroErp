## 📘 Documentazione Concettuale – Funzione `vendite.fn_reset_fondi_fattura`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
> • [vendite.fatture_fondi_fattura_source](/dbzero/vendite/tabelle/fatture_fondi_fattura_source)  
> • [vendite.fatture_fondi_fattura](/dbzero/vendite/tabelle/fatture_fondi_fattura)  
>
> **Approfondimento funzioni:**
>
> • [vendite.fn_applica_fondi_fattura](/dbzero/vendite/funzioni/fn_applica_fondi_fattura)  
>
---

### 🎯 Scopo Principale

La funzione **`vendite.fn_reset_fondi_fattura()`** ripristina i fondi fattura
applicati ad una **fattura figlia**:

* riapre la `source` (stato `DISPONIBILE`)
* elimina le righe in `fatture_fondi_fattura`

---

### ✅ Regole principali

* `p_fattura_id` obbligatorio.
* Opera solo su `source` con `stato = 'ASSEGNATO'`.
* Resetta campi di assegnazione (`fattura_figlia_id`, date/utente).
* Applica il reset solo ai tipi con `codice_interno = 'F_F_ADD_ACC'`.

---

### ✅ Output

Ritorna:

* `updated_source` = numero righe source ripristinate
* `deleted_fondi` = numero righe fondi eliminate

---

### 🧪 Esempio d’uso

```sql
SELECT *
FROM vendite.fn_reset_fondi_fattura(
  p_fattura_id => 123
);
```

---

{% include-markdown "signature-core.md" %}
