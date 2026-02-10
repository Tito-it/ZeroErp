## 📘 Documentazione Concettuale – Funzione `vendite.fn_reset_lotto_fattura_draft`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)  
> • [vendite.fatturazione_lotti_fatture](/dbzero/vendite/tabelle/fatturazione_lotti_fatture)  
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
> • [vendite.fatture_righe](/dbzero/vendite/tabelle/fatture_righe)  
> • [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)  
>
> **Approfondimento funzioni:**
>
> • [vendite.fn_cleanup_fatture_by_ids](/dbzero/vendite/funzioni/fn_cleanup_fatture_by_ids)  
> • [vendite.fn_reset_lotto_draft](/dbzero/vendite/funzioni/fn_reset_lotto_draft)  

---

### 🎯 Scopo Principale

(latest review 10-02-2026)  
La funzione **`vendite.fn_reset_lotto_fattura_draft()`** effettua il reset tecnico
di **una singola fattura** appartenente a un lotto **MASSIVO** in stato **DRAFT**,
senza annullare il lotto.

---

### ✅ Regole principali

* `p_lotto_id` e `p_fattura_id` obbligatori.
* Lotto deve essere `MASSIVO` e in `DRAFT`.
* La fattura deve appartenere al lotto ed essere in `DRAFT`.
* Usa `vendite.fn_cleanup_fatture_by_ids` per cleanup centralizzato.
* **Non** modifica lo stato del lotto.

---

### ✅ Output

Ritorna una riga con:

* `updated_attivita`
* `deleted_fatture`
* `deleted_righe`

---

### 🧪 Esempio d’uso

```sql
SELECT *
FROM vendite.fn_reset_lotto_fattura_draft(
  p_lotto_id => 123,
  p_fattura_id => 456
);
```

---

{% include-markdown "signature-core.md" %}
