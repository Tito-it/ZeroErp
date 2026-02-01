## 📘 Documentazione Concettuale – Funzione `vendite.fn_sync_lotto_fatture_stato`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)   
> • [vendite.fatturazione_lotti_fatture](/dbzero/vendite/tabelle/fatturazione_lotti_fatture)   
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)   
>
> **Approfondimento funzioni:**
>
> • [vendite.fn_set_fatturazione_lotto_stato](/dbzero/vendite/funzioni/fn_set_fatturazione_lotto_stato)   
> • [vendite.pr_run_lotto_pipeline](/dbzero/vendite/funzioni/pr_run_lotto_pipeline)   
>
---

### 🎯 Scopo Principale

(latest review 30-01-2026)  
La funzione **`vendite.fn_sync_lotto_fatture_stato()`** allinea lo stato
documentale delle fatture collegate a un lotto.

---

### ✅ Regole principali

* `p_lotto_id` obbligatorio.
* Se `p_target_stato_doc_fiscale_id` è NULL, usa `stato_doc_fiscale_id` del lotto.
* Lotto **GIORNALIERO**: se il target è `INVIATA`, imposta `stato_operativo = CHIUSO`.

---

### ✅ Output

Nessun output (RETURN void).

---

### 🧪 Esempi d’uso

```sql
-- Allinea fatture al lotto (usa stato_doc_fiscale_id del lotto)
SELECT vendite.fn_sync_lotto_fatture_stato(123);

-- Forza un target specifico
SELECT vendite.fn_sync_lotto_fatture_stato(123, 3);
```

---

{% include-markdown "signature-core.md" %}
