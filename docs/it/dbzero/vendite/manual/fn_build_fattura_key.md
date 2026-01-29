## 📘 Documentazione Concettuale – Funzione `vendite.fn_build_fattura_key`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)  
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
> • [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)  
> • [anagrafiche.resellers_billing_account](/dbzero/anagrafiche/tabelle/resellers_billing_account)  
> • [config.tipi_doc_fiscale](/dbzero/config/tabelle/tipi_doc_fiscale)  
>
---

### 🎯 Scopo Principale

(latest review 29-01-2026)  
La funzione **`vendite.fn_build_fattura_key()`** costruisce la **chiave logica**
di aggregazione documento a partire da una riga di `attivita_fatturabili`.

---

### ✅ Regole principali

* La fattura viene emessa sul **BA padre** se presente, altrimenti sul BA stesso.
* L’emittente fiscale e` risolto dal mapping BA → emittente.
* Il reseller e` risolto dal mapping BA → reseller (se presente).
* Il registro e` risolto dal tipo documento fiscale.
* La chiave include: BA fattura, tipo documento, valuta, emittente, reseller, utility, registro.

---

### ✅ Output

Ritorna un **jsonb** con i campi chiave per l’aggregazione documento.

---

### 🧪 Esempio

```sql
SELECT vendite.fn_build_fattura_key(12345);
```

---

{% include-markdown "signature-core.md" %}
