## 📘 Documentazione Concettuale – Tabella `pagamenti.vendite_contabili`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [pagamenti.centri_riscossione](/dbzero/pagamenti/tabelle/centri_riscossione)  
> • [pagamenti.enti_incasso](/dbzero/pagamenti/tabelle/enti_incasso)  
> • [pagamenti.vendite_contabili_stati](/dbzero/pagamenti/tabelle/vendite_contabili_stati)  
> • [pagamenti.vendite_contabili_righe](/dbzero/pagamenti/tabelle/vendite_contabili_righe)  
> • [pagamenti.vendite_movimenti](/dbzero/pagamenti/tabelle/vendite_movimenti)  
>
### 🎯 Scopo Principale
La tabella **`pagamenti.vendite_contabili`** rappresenta la **testata contabile**
per l’aggregazione di movimenti vendite. Serve a raggruppare movimenti per
centro riscossione e data contabile, con eventuale dettaglio del canale
(`ente_incasso`) e stato operativo della testata.

---

### Campi chiave (semantica)

* `codice`: identificativo testata contabile.
* `centro_riscossione_id`: riferimento principale al centro riscossione.
* `ente_incasso_id`: ente/canale specifico (opzionale).
* `compensazione_id`: testata processo compensazione (opzionale, univoca).
* `stato_id`: stato della testata contabile.
* `data_contabile`: data contabile di riferimento.
* `data_conferma` / `user_conferma`: tracciamento conferma testata.

---

### Regole principali

* `codice` univoco.
* Ogni testata e` collegata a un solo centro riscossione.
* Se `ente_incasso_id` e` valorizzato, deve essere coerente con
  `centro_riscossione_id` della testata (guard applicativa).
* Se `compensazione_id` e` valorizzato:
  * il centro riscossione deve avere `is_compensazione = true`
  * la testata non puo` essere collegata a lotti (`vendite_contabili_lotti`).
* `stato_id` punta al lookup `pagamenti.vendite_contabili_stati`.

---

### Esempio d’uso

```sql
SELECT *
FROM pagamenti.vendite_contabili
WHERE data_contabile = current_date;
```

---

{% include-markdown "signature-core.md" %}
