## 📘 Documentazione Concettuale – Funzione `vendite.fn_ricalcola_totali_preventivo(...)`

> 👀 **Vedi anche**
>
[vendite.preventivi](/dbzero/vendite/tabelle/preventivi)
> [vendite.preventivi_righe](/dbzero/vendite/tabelle/preventivi_righe)
> [config.iva](/dbzero/config/tabelle/iva)
> [vendite.trgfn_preventivi_righe_ricalcola_totali](/dbzero/vendite/funzioni/trgfn_preventivi_righe_ricalcola_totali)

---
### 🎯 Scopo Principale
(latest review 03-04-2026)
`vendite.fn_ricalcola_totali_preventivo(p_preventivo_id)` ricalcola i **totali della testata**
(imponibile, IVA, totale documento) a partire dalle righe attive. Invocata sia direttamente
dal backend sia automaticamente dal trigger AFTER STATEMENT su `preventivi_righe`.

---

### Regole di calcolo

Il calcolo usa una **CTE con arrotondamento per riga** (correttezza fiscale):

1. Per ogni riga attiva calcola:
   * `importo_riga = ROUND(quantita * prezzo_unitario * (1 - sconto/100), 2)`
   * `iva_riga = ROUND(importo_riga * aliquota_iva / 100, 2)`
2. Poi somma i valori gia' arrotondati:
   * `totale_imponibile = SUM(importo_riga)`
   * `totale_iva = SUM(iva_riga)`
   * `totale_documento = totale_imponibile + totale_iva`

Questo evita differenze di centesimi rispetto all'arrotondamento sull'aggregato.

* Solo righe con `attivo = true` e `quantita > 0`.
* Se nessuna riga attiva: totali = 0.

---

### Parametri

| Parametro | Tipo | Note |
|-----------|------|------|
| `p_preventivo_id` | `vendite.preventivi.id%TYPE` | ID del preventivo. Obbligatorio, > 0. |

---

### 📦 Output

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `preventivo_id` | bigint | ID del preventivo ricalcolato |
| `totale_imponibile` | numeric | Somma importi riga arrotondati |
| `totale_iva` | numeric | Somma IVA riga arrotondate |
| `totale_documento` | numeric | Imponibile + IVA |

---

### Trigger automatico

La funzione e' invocata automaticamente dai trigger STATEMENT-level su `preventivi_righe`
(vedi `trgfn_preventivi_righe_ricalcola_totali`). Il ricalcolo avviene **una sola volta
per ogni preventivo coinvolto** dall'operazione DML, anche in caso di bulk INSERT.

---

### Esempio d'uso

```sql
-- Ricalcolo esplicito
SELECT * FROM vendite.fn_ricalcola_totali_preventivo(42);

-- I totali vengono aggiornati anche automaticamente al cambio righe:
INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, quantita, prezzo_unitario, ...)
VALUES (42, '...', 10, 100.00, ...);
-- → il trigger STATEMENT invoca fn_ricalcola_totali_preventivo(42) una sola volta
```

---

{% include-markdown "signature-core.md" %}
