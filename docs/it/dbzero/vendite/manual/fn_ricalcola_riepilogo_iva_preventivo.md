## 📘 Documentazione Concettuale – Funzione `vendite.fn_ricalcola_riepilogo_iva_preventivo`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> [vendite.preventivi_riepiloghi_iva](/dbzero/vendite/tabelle/preventivi_riepiloghi_iva)
> [vendite.preventivi_righe](/dbzero/vendite/tabelle/preventivi_righe)
>
Approfondimento funzioni:
> [vendite.fn_ricalcola_riepilogo_iva_fattura](/dbzero/vendite/funzioni/fn_ricalcola_riepilogo_iva_fattura)
> [vendite.fn_ricalcola_totali_preventivo](/dbzero/vendite/funzioni/fn_ricalcola_totali_preventivo)
> [config.fn_get_aliquota_iva](/dbzero/config/funzioni/fn_get_aliquota_iva)

### 🎯 Scopo Principale

(latest review 02-05-2026)

Ricalcola il riepilogo IVA per il preventivo target, alimentando la tabella
`vendite.preventivi_riepiloghi_iva`. Logica **fiscalmente corretta** (DPR
633/72 art.21 + DM 24/12/93): aggregazione per aliquota, ROUND a 2 decimali
sul SUM, mai per riga. Speculare a `vendite.fn_ricalcola_riepilogo_iva_fattura`.

### Firma

```sql
vendite.fn_ricalcola_riepilogo_iva_preventivo(
    p_preventivo_id vendite.preventivi.id%TYPE
) RETURNS TABLE (deleted_rows integer, inserted_rows integer)
```

`%TYPE` su `p_preventivo_id` per coerenza con la convenzione progetto (vedi
`linee-guida-sql §5`).

### Algoritmo

1. **Guard parametro**: `p_preventivo_id` obbligatorio e `> 0`. Raise
   `E_PARAMETRO_INVALIDO` altrimenti.
2. **Lookup stato emittente** per override aliquota IVA. Chain di JOIN:

   ```
   vendite.preventivi.emittente_fiscale_id
     -> anagrafiche.emittenti_fiscali.soggetto_ruolo_id
     -> anagrafiche.soggetti_ruoli.soggetto_id
     -> anagrafiche.soggetti.stato_id
   ```

   Se la chain non risolve (preventivo senza emittente), `v_stato_emittente_id`
   resta `NULL` e `config.fn_get_aliquota_iva` ritorna l'aliquota base.

3. **DELETE riepiloghi precedenti** del `preventivo_id` (idempotenza). Conta in
   `deleted_rows`.
4. **CTE `righe`**: imponibile_riga **full precision** = `qta * prezzo *
   (1 - COALESCE(sconto%, 0)/100)`, niente ROUND. Filtra `attivo IS TRUE` e
   `quantita > 0`.
5. **INSERT aggregato**, group by `iva_id` (preventivi non hanno
   natura/esigibilita/split, quei campi sono `NULL`):

   ```sql
   imponibile      = ROUND(SUM(imponibile_riga), 2)
   imposta         = ROUND(imponibile * fn_get_aliquota_iva(iva_id, stato)/100, 2)
   arrotondamento  = SUM(imponibile_riga) - ROUND(SUM(imponibile_riga), 2)
   ```

   `fn_get_aliquota_iva` applica l'override per stato emittente coerente con
   le fatture: pattern uniforme cross-documento.

6. Ritorna `(deleted_rows, inserted_rows)`.

### Override aliquota IVA da stato emittente

Pattern **non opzionale** (allineato alle fatture). La fn `config.fn_get_aliquota_iva(iva_id, stato_emittente_id)` consente:

* aliquota base se `stato_emittente_id` IS NULL o non override-ata
* aliquota personalizzata se l'emittente ha sede in stato che la richiede

Senza questo, una fattura emessa da un preventivo con cliente/emittente con
stato fiscale diverso avrebbe aliquota diversa rispetto al preventivo →
divergenza centesimi sul totale documento. Allineamento al pattern fatture
chiude il loop.

### Errori sollevati

| Codice | Contesto | Quando |
|---|---|---|
| `E_PARAMETRO_INVALIDO` | `parametro=p_preventivo_id`, `valore=...` | `p_preventivo_id IS NULL OR <= 0` |

### Caller

* `vendite.fn_ricalcola_totali_preventivo` (wrapper, single source of truth dei totali testata)
* Indirettamente via trigger AFTER su `preventivi_righe`
  (`trg_preventivi_righe_z90_ricalcola_totali_*` → `trgfn_preventivi_righe_ricalcola_totali` → `fn_ricalcola_totali_preventivo` → questa fn)
* Eventuali batch / migration data-fix (manuale)

### Esempi

**Ricalcolo manuale di un preventivo:**

```sql
SELECT * FROM vendite.fn_ricalcola_riepilogo_iva_preventivo(42);
-- (deleted_rows, inserted_rows) = (2, 2)
```

**Ricalcolo di tutti i preventivi (data fix one-shot):**

```sql
DO $$
DECLARE r record;
BEGIN
  FOR r IN SELECT id FROM vendite.preventivi LOOP
    PERFORM vendite.fn_ricalcola_riepilogo_iva_preventivo(r.id);
    PERFORM vendite.fn_ricalcola_totali_preventivo(r.id);
  END LOOP;
END$$;
```

(Per ricalcolare anche i totali testata, invocare il wrapper
`fn_ricalcola_totali_preventivo`, che a sua volta chiama questa fn).

### Note operative

* **Idempotenza**: DELETE+INSERT atomico, replay safe.
* **Performance**: 1 SELECT chain + 1 DELETE + 1 INSERT con CTE. O(n) sulle righe del preventivo. Costo trascurabile.
* **No SECURITY DEFINER**: la fn non eleva privilegi, viene eseguita con i
  diritti del caller. Le tabelle target sono accessibili al ruolo applicativo.

---

<!-- rev-2026-09-28-liste-righe -->
### 🔄 rev 2026-09-28 — brief-db-liste-righe-documento

L'imponibile di riga della CTE `righe` non è più scritto qui: viene da [script.fn_imponibile_riga](/dbzero/script/funzioni/fn_imponibile_riga), la sede unica della formula (`20260928-25`). Stesso valore — provato su una griglia di 252 casi e sui dati di dev — ma una regola sola: prezzo o quantità assenti danno **nessun valore**, mai zero; sconto assente è nessuno sconto; l'arrotondamento resta a chi consuma. La firma è di nuovo ancorata (`%TYPE`) e `SECURITY INVOKER` è esplicito.

---

{% include-markdown "signature-core.md" %}

---
