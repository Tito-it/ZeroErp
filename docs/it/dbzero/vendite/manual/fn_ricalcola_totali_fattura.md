## 📘 Documentazione Concettuale – Funzione `vendite.fn_ricalcola_totali_fattura`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
> • [vendite.fatture_riepiloghi_iva](/dbzero/vendite/tabelle/fatture_riepiloghi_iva)  
> • [vendite.fatture_fondi_fattura](/dbzero/vendite/tabelle/fatture_fondi_fattura)  
> • [anagrafiche.emittenti_fiscali_utilities](/dbzero/anagrafiche/tabelle/emittenti_fiscali_utilities)  
>
**Approfondimento funzioni:**
>
• [vendite.fn_get_totale_fondi_fattura](/dbzero/vendite/funzioni/fn_get_totale_fondi_fattura)  
> • [vendite.fn_get_arrotondamento_scope](/dbzero/vendite/funzioni/fn_get_arrotondamento_scope)  
> • [vendite.fn_set_arrotondamento_scope](/dbzero/vendite/funzioni/fn_set_arrotondamento_scope)  
> • [vendite.fn_sync_contabili_fondo_fattura](/dbzero/vendite/funzioni/fn_sync_contabili_fondo_fattura)  
>
### 🎯 Scopo Principale
La funzione **`vendite.fn_ricalcola_totali_fattura()`** ricalcola i totali
sulla testata fattura a partire dai **riepiloghi IVA** e dai **fondi fattura**,
applicando le regole di arrotondamento definite per **emittente/utility**.

---

### Regole principali

* `p_fattura_id` obbligatorio.
* Totali calcolati da `fatture_riepiloghi_iva`.
* Totale fondi fattura via `vendite.fn_get_totale_fondi_fattura()`.
* Arrotondamento calcolato in base a:
  * `anagrafiche.emittenti_fiscali_utilities.arrotondamento_importi_dec`
  * `anagrafiche.emittenti_fiscali_utilities.metodo_arrotondamento_importi`
* Aggiorna il saldo tecnico con `fn_set_arrotondamento_scope()`.
* Imposta `minimo = true` quando `totale_a_pagare` rientra nella soglia
  (`minimo_soglia_min`/`minimo_soglia_max`).
* Esegue la sincronizzazione contabile dei fondi assegnati alla fattura
  (`fn_sync_contabili_fondo_fattura`).

---

### Output

Non ritorna valori. Aggiorna la testata fattura.

---

### Esempio d’uso

```sql
SELECT vendite.fn_ricalcola_totali_fattura(
  p_fattura_id => 123
);
```

---

{% include-markdown "signature-core.md" %}
