## 📘 Documentazione Concettuale – Funzione `vendite.fn_ricalcola_totali_fattura`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
> • [vendite.fatture_riepiloghi_iva](/dbzero/vendite/tabelle/fatture_riepiloghi_iva)  
> • [vendite.fatture_righe](/dbzero/vendite/tabelle/fatture_righe)  
> • [catalogo.articoli](/dbzero/catalogo/tabelle/articoli)  
>
> **Approfondimento funzioni:**
>
> • [vendite.fn_ricalcola_fattura](/dbzero/vendite/funzioni/fn_ricalcola_fattura)  

---

### 🎯 Scopo Principale

(latest review 10-02-2026)  
La funzione **`vendite.fn_ricalcola_totali_fattura()`** ricalcola i totali
della testata fattura a partire dai riepiloghi IVA e dalle righe “fondo fattura”.

---

### ✅ Regole principali

* `p_fattura_id` obbligatorio e `> 0`.
* `imponibile_tot` e `imposta_tot` derivano da `vendite.fatture_riepiloghi_iva`.
* `totale_escluso_imponibile` somma le righe con `catalogo.articoli.fondo_fattura = true`
  usando `totale_riga` (fallback su `imponibile_riga` se `totale_riga` NULL).

---

### ✅ Output

Ritorna una riga con:

* `imponibile_tot`
* `imposta_tot`
* `totale_escluso_imponibile`
* `totale_doc`

---

### 🧪 Esempio d’uso

```sql
SELECT *
FROM vendite.fn_ricalcola_totali_fattura(123);
```

---

{% include-markdown "signature-core.md" %}
