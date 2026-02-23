## 📘 Documentazione Concettuale – Funzione `vendite.fn_get_attivita_lotto_info`

### 🎯 Scopo Principale

Restituisce in un'unica chiamata le informazioni di stato principali del lotto attivita:
* `stato_lotto`
* `stato_operativo`
* `is_in_esecuzione`

Obiettivo: evitare query duplicate lato backend sulla tabella
`vendite.attivita_fatturabili_lotti`.

---

### ✅ Regole principali

* `p_lotto_id` obbligatorio (`> 0`).
* se il lotto non esiste, la funzione ritorna 0 righe.
* `is_in_esecuzione` e` derivato da `stato_lotto = 'IN_ESECUZIONE'`.

---

### ✅ Output

Ritorna una tabella con:
* `stato_lotto` (`text`)
* `stato_operativo` (`text`)
* `is_in_esecuzione` (`boolean`)

---

### 🧪 Esempio d'uso

```sql
SELECT *
FROM vendite.fn_get_attivita_lotto_info(123);
```

---

### 🧩 Utilizzo previsto

* runner pipeline attivita (check stato esecuzione e stato operativo);
* endpoint status lotto attivita;
* riduzione round-trip DB e coerenza logica stato.

---

{% include-markdown "signature-core.md" %}

