## 📘 Documentazione Concettuale – Funzione `vendite.fn_get_arrotondamento_scope`

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
La funzione **`vendite.fn_get_arrotondamento_scope()`** restituisce il
**saldo tecnico** degli arrotondamenti per l'ambito di fatturazione
(BA, utility, tipo documento, emittente, valuta). Se l'ambito non esiste,
ritorna `0`.

---

### ✅ Regole principali

* Parametri obbligatori (ID > 0).
* Se l'ambito non esiste, il saldo e` `0`.

---

### 🧪 Esempio d’uso

```sql
SELECT vendite.fn_get_arrotondamento_scope(
  p_billing_account_id => 100,
  p_utility_id => 1,
  p_tipo_doc_fiscale_id => 10,
  p_emittente_soggetto_ruolo_id => 7,
  p_valuta_id => 1
);
```

---

{% include-markdown "signature-core.md" %}
