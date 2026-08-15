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
### 🎯 Scopo Principale
(latest review 15-08-2026)

> 🔴 **Questa funzione si ritira** (`DROP`), decisione del 2026-08-15 —
> [brief-db-fondo-fattura…](/dev/work-in-progress/brief-db-fondo-fattura-ricalcolo-e-governo)
> §8.1 F-4, passo **D-15**. **Questa pagina se ne va con lei.**
>
> ⚠️ **Non chiamarla, e non cercarci dentro il posting.** Nome e colonne di
> ritorno dicono *movimenti*, ma **non crea nessun movimento**: delega tutto a
> `fn_sync_contabili_fondo_fattura` e si limita a rinominare `inserted_righe` in
> `inserted_movimenti`. È probabilmente la ragione per cui in giro si legge che
> il posting esista: **nel database non c'è ancora nessuna funzione che scriva
> `pagamenti.vendite_movimenti`.**
>
> **Perché ritirarla invece di rinominarla**: il difetto non è il nome, è che la
> funzione **esiste**. Un nome onesto lascerebbe in piedi un oggetto che nessuno
> chiama — cioè una cosa in più da mantenere e da spiegare. Misurato il
> 2026-08-15: **zero** chiamanti fra le funzioni del database (dal 2026-02
> `fn_ricalcola_totali_fattura` chiama direttamente
> `fn_sync_contabili_fondo_fattura`), **zero** dal backend, e un solo
> riferimento in un pgTAP che ne collauda il guard di parametro.

La funzione **`vendite.fn_sync_pagamento_fondo_fattura()`** è mantenuta solo
per retrocompatibilità ed è **deprecata**.
La logica effettiva ora è demandata a
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
