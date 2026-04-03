## 📘 Documentazione Concettuale – Vista `vendite.vw_preventivi_righe_dettaglio`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[vendite.preventivi_righe](/dbzero/vendite/tabelle/preventivi_righe)
> [catalogo.articoli](/dbzero/catalogo/tabelle/articoli)
> [catalogo.unita_misura](/dbzero/catalogo/tabelle/unita_misura)
> [config.iva](/dbzero/config/tabelle/iva)

---
### 🎯 Scopo Principale
(latest review 03-04-2026)
`vendite.vw_preventivi_righe_dettaglio` arricchisce le righe preventivo con i dati
denormalizzati di articolo, unita' di misura operativa e aliquota IVA. Include **importi
calcolati** per evitare duplicazione della logica di calcolo nel backend/frontend.

---

### JOIN principali

| Tabella | Dati esposti |
|---------|-------------|
| `catalogo.articoli` | codice, descrizione articolo |
| `catalogo.unita_misura` | codice UoM operativa |
| `config.iva` | codice IVA, aliquota_iva |

---

### 📑 Campi calcolati

| Campo | Formula |
|-------|---------|
| `importo_riga` | `ROUND(quantita * prezzo_unitario * (1 - sconto/100), 2)` |
| `importo_iva_riga` | `ROUND(importo_riga * aliquota_iva / 100, 2)` |

---

### Note operative

* Include sia righe **attive** che **inattive** (campo `attivo`): le inattive servono
  per consultare lo storico revisioni.
* Ordinamento: `preventivo_id, ordine, id`.

---

### Esempio d'uso

```sql
-- Righe attive di un preventivo con importi
SELECT articolo_codice, descrizione, quantita, prezzo_unitario,
       sconto_percentuale, importo_riga, iva_codice, importo_iva_riga
FROM vendite.vw_preventivi_righe_dettaglio
WHERE preventivo_id = 42
  AND attivo IS TRUE
ORDER BY ordine;
```

---

{% include-markdown "signature-core.md" %}
