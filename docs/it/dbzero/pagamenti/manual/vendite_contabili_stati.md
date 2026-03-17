## 📘 Documentazione Concettuale – Tabella `pagamenti.vendite_contabili_stati`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [pagamenti.vendite_contabili](/dbzero/pagamenti/tabelle/vendite_contabili)  
> • [pagamenti.vendite_contabili_righe_stati](/dbzero/pagamenti/tabelle/vendite_contabili_righe_stati)  
>
🎯 Scopo Principale

(latest review 13-02-2026)  
La tabella **`pagamenti.vendite_contabili_stati`** definisce il lookup
degli stati della **testata contabile vendite**.

---

### Campi chiave (semantica)

* `codice`: codice stato funzionale (es. DRAFT, CHIUSA, ANNULLATA).
* `descrizione`: testo descrittivo dello stato.
* `is_final`: indica se lo stato e` terminale.
* `ordine`: priorita`/sequenza di avanzamento stato.
* `attivo`: abilita/disabilita stato per nuovi processi.
* `meta`: estensioni configurative.

---

### Regole principali

* `codice` univoco.
* Stati finali marcati con `is_final = true`.
* `ordine` usato come supporto per ordinamento operativo.

---

### Esempio d’uso

```sql
SELECT id, codice, descrizione, is_final
FROM pagamenti.vendite_contabili_stati
WHERE attivo IS TRUE
ORDER BY ordine, id;
```

---

{% include-markdown "signature-core.md" %}
