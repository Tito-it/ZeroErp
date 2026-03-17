## 📘 Documentazione Concettuale – Funzione `vendite.fn_genera_fondi_fattura_source`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
> • [vendite.fatture_fondi_fattura_source](/dbzero/vendite/tabelle/fatture_fondi_fattura_source)  
> • [pagamenti.vendite_movimenti](/dbzero/pagamenti/tabelle/vendite_movimenti)  
>
🎯 Scopo Principale

(latest review 12-02-2026)  
La funzione **`vendite.fn_genera_fondi_fattura_source()`** genera record
in `fatture_fondi_fattura_source` per fatture con `minimo = true`,
e mantiene allineata la source in base al saldo documento.

---

### Regole principali

* Parametri obbligatori (ID > 0).
* Seleziona fatture con `minimo = true` nel perimetro BA/utility/tipo_doc/emittente/valuta.
* Inserisce nuove source con stato `DISPONIBILE` solo per fatture con saldo effettivo diverso da `0`.
* Se la source esiste gia` (non assegnata), aggiorna importo e stato:
  * `saldo_effettivo = 0` -> `ANNULLATO`
  * `saldo_effettivo <> 0` -> `DISPONIBILE`
* La funzione e` idempotente: riallinea i dati senza creare duplicati.
* `saldo_effettivo` e` calcolato come:
  * `residuo_fattura (totale_a_pagare - movimenti)`
  * meno saldo contabile postabile (`vendite_contabili_righe_stati.is_postabile = true`).

---

### Output

Ritorna il numero totale di record modificati (`insert` + `update`).

---

### Esempio d’uso

```sql
SELECT vendite.fn_genera_fondi_fattura_source(
  p_billing_account_id => 100,
  p_utility_id => 1,
  p_tipo_doc_fiscale_id => 10,
  p_emittente_soggetto_ruolo_id => 7,
  p_valuta_id => 1,
  p_tipo_fondo_fattura_id => 1
);
```

---

{% include-markdown "signature-core.md" %}
