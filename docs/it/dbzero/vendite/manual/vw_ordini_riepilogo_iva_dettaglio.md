## 📘 Documentazione Concettuale – Vista `vendite.vw_ordini_riepilogo_iva_dettaglio`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> [vendite.ordini](/dbzero/vendite/tabelle/ordini)
> [vendite.ordini_righe](/dbzero/vendite/tabelle/ordini_righe)
> [config.iva](/dbzero/config/tabelle/iva)
>
Approfondimento viste e funzioni:
> [vendite.vw_ordini_righe_iva_base](/dbzero/vendite/views/vw_ordini_righe_iva_base)
> [vendite.fn_ricalcola_totali_ordine](/dbzero/vendite/funzioni/fn_ricalcola_totali_ordine)
> [config.fn_get_aliquota_iva](/dbzero/config/funzioni/fn_get_aliquota_iva)

---

### 🎯 Scopo Principale

(latest review 05-06-2026)

`vendite.vw_ordini_riepilogo_iva_dettaglio` espone il riepilogo IVA derivato di
un ordine vendita. E' la sorgente DB da leggere per il breakdown per aliquota
nel backend, nel drawer e nella stampa ordine.

Replica la logica fiscalmente corretta gia' adottata sui preventivi:
**si sommano prima gli imponibili della stessa aliquota e poi si applica
l'IVA sul totale aggregato**. Non si sommano imposte calcolate riga per riga.

---

### Algoritmo

1. Legge `vendite.vw_ordini_righe_iva_base`.
2. Aggrega per:

   ```text
   ordine_id, iva_id, aliquota_effettiva
   ```

3. Calcola:

   ```sql
   imponibile = ROUND(SUM(imponibile_riga_full), 2)
   imposta    = ROUND(imponibile * COALESCE(aliquota_effettiva, 0) / 100, 2)
   ```

4. Espone `totale_riga = imponibile + imposta`.
5. Espone `arrotondamento = imponibile_full - ROUND(imponibile_full, 2)` per
   tracciabilita' dello scarto da full precision.

---

### Shape

La vista non espone un `id` tecnico: il riepilogo e' derivato e la chiave logica
e' la combinazione `ordine_id + iva_id + aliquota_effettiva`.

| Campo | Descrizione |
| --- | --- |
| `ordine_id` | Ordine vendita |
| `iva_id`, `iva_codice`, `iva_descrizione` | Codice IVA e descrizioni da `config.iva` |
| `iva_aliquota` | Aliquota effettiva usata per il calcolo |
| `natura_id`, `natura_codice` | Sempre `NULL` per ordini |
| `esigibilita`, `split_payment` | Dal 2026-10-01 (D-4): per codice IVA da [script.fn_esigibilita_iva_documento](/dbzero/script/funzioni/fn_esigibilita_iva_documento), con emittente e cliente dell'ordine — la stessa regola delle righe di fattura, calcolata al momento. Senza cliente: `NULL` |
| `imponibile` | Imponibile aggregato e arrotondato a 2 decimali |
| `imposta` | IVA calcolata sull'imponibile aggregato |
| `arrotondamento` | Differenza tra full precision e imponibile arrotondato |
| `totale_riga` | `imponibile + imposta` |

---

### Differenza rispetto ai preventivi

I preventivi persistono il riepilogo IVA in una tabella fisica
(`preventivi_riepiloghi_iva`). Gli ordini non hanno questo requisito: il
riepilogo resta live in vista, mentre i soli totali aggregati vengono
persistiti in `vendite.ordini` da `fn_ricalcola_totali_ordine`.

---

### Esempio

```sql
SELECT iva_codice, iva_aliquota, imponibile, imposta, totale_riga
  FROM vendite.vw_ordini_riepilogo_iva_dettaglio
 WHERE ordine_id = 42
 ORDER BY iva_aliquota, iva_id;
```

---

{% include-markdown "signature-core.md" %}
