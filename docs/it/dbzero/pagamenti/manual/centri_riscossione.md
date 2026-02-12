## 📘 Documentazione Concettuale – Tabella `pagamenti.centri_riscossione`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [pagamenti.vendite_movimenti](/dbzero/pagamenti/tabelle/vendite_movimenti)  
>
---

### 🎯 Scopo Principale

La tabella **`pagamenti.centri_riscossione`** definisce le **origini di incasso**
per i movimenti vendite (banca, posta, cassa, compensazioni, ecc.).

---

### 🧱 Campi chiave (semantica)

* `codice`: identificativo leggibile.
* `codice_interno`: codice tecnico/integrazione.
* `is_compensazione`: identifica il centro usato per **compensazioni**.
* `attivo`: centro attivo.

---

### ✅ Regole principali

* `codice` univoco.
* Solo **un centro** puo` avere `is_compensazione = true`.

---

### 🧪 Esempio d’uso

```sql
SELECT *
FROM pagamenti.centri_riscossione
WHERE is_compensazione IS TRUE;
```

---

{% include-markdown "signature-core.md" %}
