## 📘 Documentazione Concettuale – Funzione `vendite.fn_ricalcola_riepilogo_iva_fattura`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatture_righe](/dbzero/vendite/tabelle/fatture_righe)    
> • [vendite.fatture_riepiloghi_iva](/dbzero/vendite/tabelle/fatture_riepiloghi_iva)    
>
**Approfondimento funzioni:**
>
• [vendite.fn_ricalcola_riepiloghi_iva_lotto](/dbzero/vendite/funzioni/fn_ricalcola_riepiloghi_iva_lotto)    

---

### 🎯 Scopo Principale

(latest review 10-02-2026)  
La funzione **`vendite.fn_ricalcola_riepilogo_iva_fattura()`** ricalcola i riepiloghi
IVA per una singola fattura, eliminando i valori esistenti e rigenerandoli dalle
righe (`fatture_righe`).

---

### Regole principali

* `p_fattura_id` obbligatorio e `> 0`.
* Ricalcolo ammesso solo se lo stato documento è `DRAFT` o `EMESSA` (via `codice_interno`).
* L’imponibile e` arrotondato a 2 decimali (half-up) prima del calcolo imposta.
* L’imposta e` calcolata come `round(imponibile_arrotondato * aliquota_iva / 100, 2)` con arrotondamento half-up.
* L’aliquota IVA e` risolta in base allo **stato fiscale dell’emittente** (override da `config.iva_stati` se presente).
* Le righe devono avere `iva_id` gia` valorizzato dal processo di generazione.
* I riepiloghi sono ricreati aggregando per combinazione fiscale.

---

### Output

Ritorna una riga con:

* `deleted_rows` = numero righe rimosse da `fatture_riepiloghi_iva`
* `inserted_rows` = numero righe inserite

---

### Esempio d’uso

```sql
SELECT *
FROM vendite.fn_ricalcola_riepilogo_iva_fattura(
  p_fattura_id => 123
);
```

---

{% include-markdown "signature-core.md" %}
