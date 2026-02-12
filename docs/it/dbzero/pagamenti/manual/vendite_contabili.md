## 📘 Documentazione Concettuale – Tabella `pagamenti.vendite_contabili`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [pagamenti.centri_riscossione](/dbzero/pagamenti/tabelle/centri_riscossione)  
> • [pagamenti.vendite_movimenti](/dbzero/pagamenti/tabelle/vendite_movimenti)  
>
---

### 🎯 Scopo Principale

La tabella **`pagamenti.vendite_contabili`** rappresenta la **testata contabile**
per l’aggregazione di movimenti vendite. Serve a raggruppare movimenti per
centro riscossione e data contabile.

---

### 🧱 Campi chiave (semantica)

* `codice`: identificativo testata contabile.
* `centro_riscossione_id`: riferimento al centro riscossione.
* `data_contabile`: data contabile di riferimento.

---

### ✅ Regole principali

* `codice` univoco.
* Ogni testata e` collegata a un solo centro riscossione.

---

### 🧪 Esempio d’uso

```sql
SELECT *
FROM pagamenti.vendite_contabili
WHERE data_contabile = current_date;
```

---

{% include-markdown "signature-core.md" %}
