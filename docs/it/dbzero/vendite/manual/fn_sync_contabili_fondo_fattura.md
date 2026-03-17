## 📘 Documentazione Concettuale – Funzione `vendite.fn_sync_contabili_fondo_fattura`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatture_fondi_fattura_source](/dbzero/vendite/tabelle/fatture_fondi_fattura_source)  
> • [pagamenti.vendite_contabili](/dbzero/pagamenti/tabelle/vendite_contabili)  
> • [pagamenti.vendite_contabili_righe](/dbzero/pagamenti/tabelle/vendite_contabili_righe)  
>
**Approfondimento funzioni:**
>
• [pagamenti.fn_get_saldo_fattura](/dbzero/pagamenti/funzioni/fn_get_saldo_fattura)  
> • [pagamenti.fn_get_or_create_vendite_contabile](/dbzero/pagamenti/funzioni/fn_get_or_create_vendite_contabile)  
> • [vendite.fn_reset_fondi_fattura](/dbzero/vendite/funzioni/fn_reset_fondi_fattura)  
>
🎯 Scopo Principale

Sincronizzare i fondi fattura assegnati a una fattura figlia nel layer
**contabile pre-posting** (`pagamenti.vendite_contabili` / `pagamenti.vendite_contabili_righe`),
senza scrivere movimenti pagamenti diretti.

---

### Regole principali

* `p_fattura_figlia_id` obbligatorio.
* Lavora su source `ASSEGNATO` con tipo `F_F_ADD_ACC`.
* Se il saldo effettivo della fattura sorgente risulta `0`, porta la source a `ANNULLATO`.
* Altrimenti crea/aggiorna una riga in `pagamenti.vendite_contabili_righe`:
  * `meta.origine = 'FONDO_FATTURA'`
  * `meta.fondo_source_id = source_id`
  * `fattura_id` = fattura sorgente
  * `billing_account_id` = source billing account
* Usa `pagamenti.fn_get_or_create_vendite_contabile()` per risolvere la testata.
* Il saldo effettivo e` calcolato come:
  * residuo fattura (`totale_a_pagare - movimenti`)
  * meno righe contabili postabili (`is_postabile = true`),
  * escludendo la riga del source corrente per mantenere idempotenza.

---

### Output

Ritorna:

* `inserted_righe`
* `updated_righe`
* `annullati_source`

---

### Esempio d’uso

```sql
SELECT *
FROM vendite.fn_sync_contabili_fondo_fattura(
  p_fattura_figlia_id => 123
);
```

---

{% include-markdown "signature-core.md" %}
