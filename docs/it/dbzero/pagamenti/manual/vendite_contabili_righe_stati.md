## 📘 Documentazione Concettuale – Tabella `pagamenti.vendite_contabili_righe_stati`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [pagamenti.vendite_contabili](/dbzero/pagamenti/tabelle/vendite_contabili)  
> • [pagamenti.vendite_contabili_stati](/dbzero/pagamenti/tabelle/vendite_contabili_stati)  
> • [pagamenti.vendite_movimenti](/dbzero/pagamenti/tabelle/vendite_movimenti)  
>
---

### 🎯 Scopo Principale

(latest review 13-02-2026)  
La tabella **`pagamenti.vendite_contabili_righe_stati`** definisce il lookup
degli stati delle **righe contabili** legate ai movimenti vendite.

---

### 🧱 Campi chiave (semantica)

* `codice`: codice stato di riga.
* `codice_interno`: codice tecnico applicativo.
* `descrizione`: descrizione funzionale.
* `is_postabile`: indica se lo stato consente contabilizzazione/posting.
* `is_final`: indica stato terminale per la riga.
* `ordine`: sequenza di avanzamento stato.
* `attivo`: stato abilitato/disabilitato.
* `meta`: estensioni configurative.
* audit: `data_insert/user_insert/data_update/user_update`.

---

### ✅ Regole principali

* `codice` univoco.
* `is_postabile = true` per gli stati ammessi al passaggio contabile.
* Stati terminali marcati con `is_final = true`.

---

### 🧪 Esempio d’uso

```sql
SELECT id, codice, codice_interno, is_postabile, is_final
FROM pagamenti.vendite_contabili_righe_stati
WHERE attivo IS TRUE
ORDER BY ordine, id;
```

---

{% include-markdown "signature-core.md" %}
