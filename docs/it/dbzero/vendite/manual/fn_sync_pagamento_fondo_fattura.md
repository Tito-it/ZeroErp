## 📘 Documentazione Concettuale – Funzione `vendite.fn_sync_pagamento_fondo_fattura` (DEPRECATA)

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatture_fondi_fattura_source](/dbzero/vendite/tabelle/fatture_fondi_fattura_source)  
> • [pagamenti.centri_riscossione](/dbzero/pagamenti/tabelle/centri_riscossione)  
> • [pagamenti.vendite_contabili](/dbzero/pagamenti/tabelle/vendite_contabili)  
> • [pagamenti.vendite_contabili_righe](/dbzero/pagamenti/tabelle/vendite_contabili_righe)  
>
**Approfondimento funzioni:**
>
• [vendite.fn_sync_contabili_fondo_fattura](/dbzero/vendite/funzioni/fn_sync_contabili_fondo_fattura)  
> • [vendite.fn_reset_fondi_fattura](/dbzero/vendite/funzioni/fn_reset_fondi_fattura)  
>
🎯 Scopo Principale

(latest review 13-02-2026)  
La funzione **`vendite.fn_sync_pagamento_fondo_fattura()`** e` mantenuta solo
per retrocompatibilita` ed e` **deprecata**.
La logica effettiva ora e` demandata a
**`vendite.fn_sync_contabili_fondo_fattura()`**, che scrive su
`pagamenti.vendite_contabili` / `pagamenti.vendite_contabili_righe`.

---

### Regole principali

* `p_fattura_figlia_id` obbligatorio.
* La funzione invoca internamente `vendite.fn_sync_contabili_fondo_fattura()`.
* I campi di output restano invariati (`inserted_movimenti`, `updated_movimenti`,
  `annullati_source`) ma rappresentano ora il risultato della sync contabili.

---

### Output

Ritorna:

* `inserted_movimenti`: righe contabili inserite (wrapper legacy)
* `updated_movimenti`: righe contabili aggiornate (wrapper legacy)
* `annullati_source`: source portate a stato `ANNULLATO`

---

### Esempio d’uso

```sql
SELECT *
FROM vendite.fn_sync_pagamento_fondo_fattura(
  p_fattura_figlia_id => 123
);
```

---

{% include-markdown "signature-core.md" %}
