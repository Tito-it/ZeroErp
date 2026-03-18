## 📘 Documentazione Concettuale – Funzione `vendite.fn_cleanup_fatture_by_ids`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatturazione_lotti_fatture](/dbzero/vendite/tabelle/fatturazione_lotti_fatture)  
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
> • [vendite.fatture_righe](/dbzero/vendite/tabelle/fatture_righe)  
> • [vendite.fatture_riepiloghi_iva](/dbzero/vendite/tabelle/fatture_riepiloghi_iva)  
> • [vendite.fatture_log](/dbzero/vendite/tabelle/fatture_log)  
> • [vendite.note_fatture](/dbzero/vendite/tabelle/note_fatture)  
> • [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)  
>
**Approfondimento funzioni:**
>
• [vendite.fn_reset_lotto_draft](/dbzero/vendite/funzioni/fn_reset_lotto_draft)  
> • [vendite.fn_reset_lotto_fattura_draft](/dbzero/vendite/funzioni/fn_reset_lotto_fattura_draft)  

---
### 🎯 Scopo Principale
(latest review 10-02-2026)  
La funzione **`vendite.fn_cleanup_fatture_by_ids()`** centralizza il cleanup
di fatture e righe correlate, ripristinando le righe di `attivita_fatturabili`.

---

### Regole principali

* Input principale: array `p_fatture_ids`.
* Se l'array e` vuoto -> nessuna modifica.
* Elimina: note (su tabella partizionata `vendite.note`), riepiloghi IVA, righe, log,
  link lotto-fatture, testate.
* Ripristina le righe `attivita_fatturabili` legate alle righe cancellate.
* Ripristina fondi fattura applicati tramite `vendite.fn_reset_fondi_fattura()`.
  In caso di movimenti fondo gia` contabilizzati, il reset fondi non elimina
  i dati e registra warning in `vendite.fatture_log`.
* Usa GUC `zeroerp.maintenance_reset_lotto_draft` per bypassare la guard fatturato.

---

### Output

Ritorna una riga con:

* `deleted_fatture`
* `deleted_righe`
* `updated_attivita`

---

### Esempio d’uso

```sql
SELECT *
FROM vendite.fn_cleanup_fatture_by_ids(
  p_fatture_ids => ARRAY[1001, 1002],
  p_lock_batch_id => NULL
);
```

Nota: il cleanup note avviene su `vendite.note` (partizione `note_fatture`).

---

{% include-markdown "signature-core.md" %}
