## 📘 Documentazione Concettuale – Funzione `vendite.fn_ricalcola_riepiloghi_iva_lotto`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatturazione_lotti_fatture](/dbzero/vendite/tabelle/fatturazione_lotti_fatture)   
> • [vendite.fatture_riepiloghi_iva](/dbzero/vendite/tabelle/fatture_riepiloghi_iva)   
>
**Approfondimento funzioni:**
>
• [vendite.fn_ricalcola_riepilogo_iva_fattura](/dbzero/vendite/funzioni/fn_ricalcola_riepilogo_iva_fattura)   

---

### 🎯 Scopo Principale

(latest review 10-02-2026)  
La funzione **`vendite.fn_ricalcola_riepiloghi_iva_lotto()`** ricalcola i
riepiloghi IVA per tutte le fatture collegate a un lotto, usando un’elaborazione
a batch e delegando il ricalcolo alla funzione per singola fattura.  
Al termine di ciascun ricalcolo aggiorna anche i **totali testata**.

---

### Regole principali

* `p_lotto_id` obbligatorio e `> 0`.
* `p_batch_size` obbligatorio e `> 0` (default 1000).
* Il ricalcolo e` eseguito a batch per ridurre impatti su carichi grandi.
* Dopo il ricalcolo IVA, aggiorna i totali testata con `fn_ricalcola_totali_fattura`.

---

### Output

Ritorna una riga con:

* `fatture_count` = numero fatture nel lotto
* `deleted_rows` = totale righe eliminate dai riepiloghi IVA
* `inserted_rows` = totale righe inserite

---

### Esempio d’uso

```sql
SELECT *
FROM vendite.fn_ricalcola_riepiloghi_iva_lotto(
  p_lotto_id => 45,
  p_batch_size => 500
);
```

---

{% include-markdown "signature-core.md" %}
