## 📘 Documentazione Concettuale – Funzione `vendite.fn_get_lotto_segnalazioni_summary`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)   
> • [vendite.fatturazione_lotti_fatture](/dbzero/vendite/tabelle/fatturazione_lotti_fatture)   
> • [vendite.fatture_log](/dbzero/vendite/tabelle/fatture_log)   
> • [vendite.fatturazione_lotti_log](/dbzero/vendite/tabelle/fatturazione_lotti_log)   
>
> **Approfondimento funzioni:**
>
> • [vendite.fn_log_lotto_esito_fatture](/dbzero/vendite/funzioni/fn_log_lotto_esito_fatture)   
>
---

### 🎯 Scopo Principale

(latest review 18-02-2026)  
La funzione **`vendite.fn_get_lotto_segnalazioni_summary()`** restituisce
un riepilogo aggregato delle segnalazioni attive (`C`/`W`/`I`) di un lotto,
unificando:

* log fattura (`vendite.fatture_log`) tramite legame lotto-fatture;
* log lotto (`vendite.fatturazione_lotti_log`).

---

### ✅ Regole principali

* `p_lotto_id` è obbligatorio e deve essere `> 0`.
* Le conte vengono calcolate solo su record **attivi** (`disabilitato = false`).
* Le severità considerate:
  * `C` = critical
  * `W` = warning
  * `I` = info (solo su log lotto)
* Output sempre valorizzato con `0` quando non ci sono righe.

---

### ✅ Output

La funzione ritorna una sola riga con:

* `fatture_critical_count`
* `fatture_warning_count`
* `lotto_critical_count`
* `lotto_warning_count`
* `lotto_info_count`

---

### 🧪 Esempio d’uso

```sql
SELECT *
FROM vendite.fn_get_lotto_segnalazioni_summary(
  p_lotto_id => 120
);
```

---

{% include-markdown "signature-core.md" %}
