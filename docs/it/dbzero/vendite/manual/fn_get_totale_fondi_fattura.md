## 📘 Documentazione Concettuale – Funzione `vendite.fn_get_totale_fondi_fattura`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatture_fondi_fattura](/dbzero/vendite/tabelle/fatture_fondi_fattura)  
>
**Approfondimento funzioni:**
>
• [vendite.fn_ricalcola_totali_fattura](/dbzero/vendite/funzioni/fn_ricalcola_totali_fattura)  
>
### 🎯 Scopo Principale
La funzione **`vendite.fn_get_totale_fondi_fattura()`** restituisce il totale
dei fondi fattura **attivi** associati alla testata.

---

### Regole principali

* `p_fattura_id` obbligatorio.
* Somma solo righe `fatture_fondi_fattura` con `attivo = true`.

---

### Output

Ritorna un valore numerico con il totale fondi fattura.

---

### Esempio d’uso

```sql
SELECT vendite.fn_get_totale_fondi_fattura(
  p_fattura_id => 123
);
```

---

{% include-markdown "signature-core.md" %}
