## 📘 Documentazione Concettuale – Funzione `vendite.fn_set_arrotondamento_scope`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.fatture_arrotondamenti_scope](/dbzero/vendite/tabelle/fatture_arrotondamenti_scope)  
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
>
---

### 🎯 Scopo Principale

(latest review 10-02-2026)  
La funzione **`vendite.fn_set_arrotondamento_scope()`** imposta (upsert)
il **saldo tecnico** degli arrotondamenti per lo scope di fatturazione.

---

### ✅ Regole principali

* Parametri obbligatori (ID > 0).
* `p_saldo` obbligatorio.
* Se lo scope non esiste, viene creato.
* Ritorna il saldo impostato.

---

### 🧪 Esempio d’uso

```sql
SELECT vendite.fn_set_arrotondamento_scope(
  p_billing_account_id => 100,
  p_utility_id => 1,
  p_tipo_doc_fiscale_id => 10,
  p_emittente_soggetto_ruolo_id => 7,
  p_valuta_id => 1,
  p_saldo => 0.03
);
```

---

{% include-markdown "signature-core.md" %}
