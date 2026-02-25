## 📘 Documentazione Concettuale – Funzione `vendite.fn_get_attivita_branch_summary`

### 🎯 Scopo Principale

Restituisce il riepilogo dei task runtime del lotto attivita, aggregato per:
* `branch_code`
* `task_stato`

Obiettivo: ridurre logica di aggregazione lato backend per endpoint status pipeline.

---

### ✅ Regole principali

* `p_lotto_attivita_id` obbligatorio (`> 0`).
* legge da `vendite.attivita_fatturabili_lotti_task_runs`.
* aggrega con `COUNT(*)` per coppia (`branch_code`, `task_stato`).
* output ordinato per `branch_code`, `task_stato`.
* in caso di parametro non valido solleva errore applicativo (`scope=ATTIVITA_FATTURABILI`).

---

### ✅ Output

Ritorna una tabella con:
* `branch_code` (`varchar`)
* `task_stato` (`varchar`)
* `cnt` (`bigint`)

---

### 🧪 Esempio d'uso

```sql
SELECT *
FROM vendite.fn_get_attivita_branch_summary(123);
```

---

### 🧩 Utilizzo previsto

* endpoint status pipeline attivita;
* dashboard operativa branch-level;
* monitoraggio rapido distribuzione esiti (`IN_ESECUZIONE`, `COMPLETATO`, `ERRORE`, `ANNULLATO`).

---

{% include-markdown "signature-core.md" %}

