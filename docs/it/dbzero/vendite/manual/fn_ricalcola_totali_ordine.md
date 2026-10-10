## 📘 Documentazione Concettuale – Funzione `vendite.fn_ricalcola_totali_ordine(...)`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> [vendite.ordini](/dbzero/vendite/tabelle/ordini)
> [vendite.ordini_righe](/dbzero/vendite/tabelle/ordini_righe)
>
Approfondimento viste e funzioni:
> [vendite.vw_ordini_righe_iva_base](/dbzero/vendite/views/vw_ordini_righe_iva_base)
> [vendite.vw_ordini_riepilogo_iva_dettaglio](/dbzero/vendite/views/vw_ordini_riepilogo_iva_dettaglio)
> [vendite.trgfn_ordini_righe_ricalcola_totali](/dbzero/vendite/funzioni/trgfn_ordini_righe_ricalcola_totali)

---

### 🎯 Scopo Principale

(latest review 05-06-2026)

`vendite.fn_ricalcola_totali_ordine(p_ordine_id)` aggiorna i totali persistiti
in testata ordine:

```text
imponibile_tot, sconto_tot, iva_tot, totale_doc
```

La funzione usa come sorgente il riepilogo IVA derivato
`vendite.vw_ordini_riepilogo_iva_dettaglio`, cosi' testata, drawer, lista e
stampa leggono valori coerenti con la stessa logica.

---

### Firma

```sql
vendite.fn_ricalcola_totali_ordine(
    p_ordine_id vendite.ordini.id%TYPE
) RETURNS TABLE (
    ordine_id      vendite.ordini.id%TYPE,
    imponibile_tot vendite.ordini.imponibile_tot%TYPE,
    sconto_tot     vendite.ordini.sconto_tot%TYPE,
    iva_tot        vendite.ordini.iva_tot%TYPE,
    totale_doc     vendite.ordini.totale_doc%TYPE
)
```

Parametro e output usano `%TYPE` sulle colonne reali di `vendite.ordini`.

---

### Algoritmo

1. **Guard parametro**: `p_ordine_id` obbligatorio e `> 0`. In caso contrario
   solleva `E_PARAMETRO_INVALIDO`.
2. Somma il riepilogo IVA:

   ```sql
   imponibile_tot = SUM(vw_ordini_riepilogo_iva_dettaglio.imponibile)
   iva_tot        = SUM(vw_ordini_riepilogo_iva_dettaglio.imposta)
   totale_doc     = SUM(vw_ordini_riepilogo_iva_dettaglio.totale_riga)
   ```

3. Calcola il lordo righe da `vendite.vw_ordini_righe_iva_base`:

   ```sql
   lordo = ROUND(SUM(imponibile_lordo_full), 2)
   ```

4. Calcola:

   ```sql
   sconto_tot = lordo - imponibile_tot
   ```

5. Aggiorna `vendite.ordini`.
6. Ritorna i totali aggiornati.

---

### Rounding

Il calcolo IVA non arrotonda per riga. La catena corretta e':

```text
righe full precision
  -> somma per aliquota
  -> ROUND(imponibile aggregato, 2)
  -> imposta sull'imponibile aggregato
  -> somma totali in testata
```

Questo replica il principio adottato sui preventivi ed evita differenze di
centesimi tra riepilogo IVA, testata e documenti a valle.

---

### Trigger automatici

La funzione e' invocata automaticamente:

* dai trigger statement-level su `vendite.ordini_righe` dopo INSERT/UPDATE.

Non c'è più un ricalcolo «dopo il cambio di emittente» sulla testata: l'emittente
dell'ordine non cambia (in bozza è quello del billing account, fuori bozza è bloccato).

Il trigger DELETE sulle righe e' registrato strutturalmente, ma l'hard-delete di
`vendite.ordini_righe` e' bloccato dal guard `_a10_`
`trg_ordini_righe_a10_block_dlt`.

---

### Esempio

```sql
SELECT *
  FROM vendite.fn_ricalcola_totali_ordine(42);
```

---

{% include-markdown "signature-core.md" %}
