## 📘 Documentazione Concettuale – Funzione `vendite.fn_reset_lotto_draft`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)  
> • [vendite.fatturazione_lotti_fatture](/dbzero/vendite/tabelle/fatturazione_lotti_fatture)  
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
> • [vendite.fatture_righe](/dbzero/vendite/tabelle/fatture_righe)  
> • [vendite.fatture_riepiloghi_iva](/dbzero/vendite/tabelle/fatture_riepiloghi_iva)  
> • [vendite.fatture_log](/dbzero/vendite/tabelle/fatture_log)  
> • [vendite.note_fatture](/dbzero/vendite/tabelle/note_fatture)  
> • [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)  
>
**Approfondimento funzioni:**
>
• [vendite.fn_select_attivita_fatturabili](/dbzero/vendite/funzioni/fn_select_attivita_fatturabili)  

---
### 🎯 Scopo Principale
(latest review 09-02-2026)  
La funzione **`vendite.fn_reset_lotto_draft()`** effettua il **rollback tecnico**
di un lotto **MASSIVO** in stato **DRAFT**, eliminando i documenti generati
dal draft e ripristinando le righe di `attivita_fatturabili`.

---

### Regole principali

* Ammesso **solo** per `tipo_lotto = MASSIVO`.
* Ammesso **solo** se `stato_doc_fiscale = DRAFT`.
* Tutte le fatture del lotto devono essere in **DRAFT**.
* Aggiorna il lotto:  
  * `stato_doc_fiscale = ANNULLATA`  
  * `stato_operativo = CHIUSO`  
  * `stato_lotto = COMPLETATO`
* Elimina:  
  * note fatture e note righe  
  * `fatture_riepiloghi_iva`  
  * `fatture_righe`  
  * `fatture_log`  
  * link `fatturazione_lotti_fatture`  
  * testate `fatture`
* Ripristina `attivita_fatturabili` (unlock + reset flags).
* Cleanup centralizzato tramite `vendite.fn_cleanup_fatture_by_ids`.
* Usa una **GUC di manutenzione** per bypassare il guard di fatturato durante il reset.
* I log di lotto (`fatturazione_lotti_log`) **non** vengono eliminati.

---

### Output

Ritorna una riga con:

* `updated_lotti`
* `updated_attivita`
* `deleted_fatture`
* `deleted_righe`

---

### Esempio d’uso

```sql
SELECT *
FROM vendite.fn_reset_lotto_draft(
  p_lotto_id => 123
);
```

---

{% include-markdown "signature-core.md" %}
