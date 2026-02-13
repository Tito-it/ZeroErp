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
per i movimenti vendite (banca, posta, cassa, compensazioni, fondo fattura, ecc.).

---

### 🧱 Campi chiave (semantica)

* `codice`: identificativo leggibile.
* `codice_interno`: codice tecnico/integrazione.
* `is_compensazione`: identifica il centro usato per **compensazioni**.
* `is_fondo_fattura`: identifica il centro usato per movimenti di **fondo fattura**.
* `attivo`: centro attivo.

---

### ✅ Regole principali

* `codice` univoco.
* Solo **un centro** puo` avere `is_compensazione = true`.
* Un centro non puo` essere contemporaneamente `is_compensazione = true` e `is_fondo_fattura = true`.

---

### 🧪 Esempio d’uso

```sql
SELECT *
FROM pagamenti.centri_riscossione
WHERE is_compensazione IS TRUE
   OR is_fondo_fattura IS TRUE;
```

---

{% include-markdown "signature-core.md" %}
