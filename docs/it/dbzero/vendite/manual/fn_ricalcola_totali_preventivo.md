## 📘 Documentazione Concettuale – Funzione `vendite.fn_ricalcola_totali_preventivo(...)`

> 👀 **Vedi anche**
>
[vendite.preventivi](/dbzero/vendite/tabelle/preventivi)
> [vendite.preventivi_righe](/dbzero/vendite/tabelle/preventivi_righe)
> [vendite.preventivi_riepiloghi_iva](/dbzero/vendite/tabelle/preventivi_riepiloghi_iva)
> [vendite.fn_ricalcola_riepilogo_iva_preventivo](/dbzero/vendite/funzioni/fn_ricalcola_riepilogo_iva_preventivo)
> [vendite.trgfn_preventivi_righe_ricalcola_totali](/dbzero/vendite/funzioni/trgfn_preventivi_righe_ricalcola_totali)

---

### 🎯 Scopo Principale

(latest review 02-05-2026)

`vendite.fn_ricalcola_totali_preventivo(p_preventivo_id)` ricalcola i **totali
della testata** (imponibile, IVA, totale documento) leggendo dalla tabella
`vendite.preventivi_riepiloghi_iva` (popolata da
`fn_ricalcola_riepilogo_iva_preventivo`). E' un **wrapper sopra** la fn
riepilogo IVA: garantisce **single source of truth** dei totali e regola
fiscalmente corretta (DPR 633/72 art.21 + DM 24/12/93).

Invocata sia direttamente dal backend sia automaticamente dal trigger AFTER
STATEMENT su `preventivi_righe`.

> **Cambio breaking 2026-05-02**: la versione precedente arrotondava per
> riga e poi sommava (errato fiscalmente). La nuova versione delega al
> riepilogo aggregato per aliquota. I totali coincidono - centesimo per
> centesimo - con quelli della fattura emessa dallo stesso preventivo.

---

### Algoritmo

1. **Guard parametro**: `p_preventivo_id` obbligatorio e `> 0`. Raise
   `E_PARAMETRO_INVALIDO` altrimenti.
2. **Step 1 — Ricalcola riepilogo IVA**:
   `PERFORM vendite.fn_ricalcola_riepilogo_iva_preventivo(p_preventivo_id)`.
   La fn fa DELETE+INSERT idempotente su `preventivi_riepiloghi_iva` con
   group by aliquota e ROUND aggregato.
3. **Step 2 — Calcola totali derivati**:

   ```sql
   v_imponibile := SUM(ri.imponibile)
   v_iva        := SUM(ri.imposta)
   v_totale     := v_imponibile + v_iva
   ```

   da `vendite.preventivi_riepiloghi_iva` per il `preventivo_id`.

4. **Step 3 — UPDATE testata** `vendite.preventivi`:

   ```sql
   totale_imponibile, totale_iva, totale_documento
   ```

5. **RETURN** `(preventivo_id, totale_imponibile, totale_iva, totale_documento)`.

---

### Firma

```sql
vendite.fn_ricalcola_totali_preventivo(
    p_preventivo_id vendite.preventivi.id%TYPE
) RETURNS TABLE (
    preventivo_id     vendite.preventivi.id%TYPE,
    totale_imponibile vendite.preventivi.totale_imponibile%TYPE,
    totale_iva        vendite.preventivi.totale_iva%TYPE,
    totale_documento  vendite.preventivi.totale_documento%TYPE
)
```

`%TYPE` su parametro e RETURNS TABLE (vedi `linee-guida-sql §5`). Tipi
concreti risolti a `(bigint, numeric, numeric, numeric)`.

---

### Parametri

| Parametro         | Tipo                          | Note                                       |
|-------------------|-------------------------------|--------------------------------------------|
| `p_preventivo_id` | `vendite.preventivi.id%TYPE`  | ID del preventivo. Obbligatorio, `> 0`.    |

---

### 📦 Output

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `preventivo_id` | `vendite.preventivi.id%TYPE` | ID del preventivo ricalcolato |
| `totale_imponibile` | `vendite.preventivi.totale_imponibile%TYPE` | `SUM(imponibile)` da riepilogo |
| `totale_iva` | `vendite.preventivi.totale_iva%TYPE` | `SUM(imposta)` da riepilogo |
| `totale_documento` | `vendite.preventivi.totale_documento%TYPE` | `imponibile + iva` |

---

### Trigger automatico

La funzione e' invocata automaticamente dai trigger STATEMENT-level su
`preventivi_righe` (vedi `trgfn_preventivi_righe_ricalcola_totali`). Il
ricalcolo avviene **una sola volta per ogni preventivo coinvolto**
dall'operazione DML, anche in caso di bulk INSERT.

---

### Esempio d'uso

```sql
-- Ricalcolo esplicito (rifa anche il riepilogo IVA in cascata)
SELECT * FROM vendite.fn_ricalcola_totali_preventivo(42);

-- I totali vengono aggiornati anche automaticamente al cambio righe:
INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, quantita, prezzo_unitario, ...)
VALUES (42, '...', 10, 100.00, ...);
-- -> il trigger STATEMENT invoca fn_ricalcola_totali_preventivo(42) una sola volta
-- -> che a sua volta invoca fn_ricalcola_riepilogo_iva_preventivo(42)
```

---

### Coerenza preventivo <-> fattura emessa

Dopo questo refactor:

* `vendite.preventivi.totale_imponibile == SUM(preventivi_riepiloghi_iva.imponibile)` (centesimo per centesimo)
* `vendite.preventivi.totale_iva == SUM(preventivi_riepiloghi_iva.imposta)` (centesimo per centesimo)
* La fattura emessa dallo stesso preventivo (a parita' di righe e stato emittente) ha `fatture.totale_iva == preventivi.totale_iva`. Il bug "differenza centesimi" e' risolto strutturalmente.

---

{% include-markdown "signature-core.md" %}
