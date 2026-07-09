## 📘 Documentazione Concettuale – Funzione `vendite.fn_ordine_ha_residuo_evasione`

> 👀 **Vedi anche**
>
> Tabelle:
> [vendite.ordini_righe](/dbzero/vendite/tabelle/ordini_righe)
> [vendite.ordini_righe_fulfillment](/dbzero/vendite/tabelle/ordini_righe_fulfillment)
>
> Funzioni:
> [vendite.fn_genera_ddt_da_ordine](/dbzero/vendite/funzioni/fn_genera_ddt_da_ordine)
> [vendite.fn_preventivo_ha_residuo_ordine](/dbzero/vendite/funzioni/fn_preventivo_ha_residuo_ordine) (gemella)

---

### 🎯 Scopo Principale

(rev 2026-07-09)

**`vendite.fn_ordine_ha_residuo_evasione(p_ordine_id) → boolean`** ritorna `TRUE` se l'ordine ha
ancora quantità da evadere su **almeno una** riga. È il gemello di
`fn_preventivo_ha_residuo_ordine`, applicato all'asse fulfillment (DDT), ed è il **gate** con cui
`fn_genera_ddt_da_ordine` proietta lo stato ordine (`CONFERMATO` / `PARZIALMENTE_EVASO` / `EVASO`).

`STABLE`, `SECURITY INVOKER`. Guard input: errore se `p_ordine_id` `NULL` o `<= 0`.

### Formula (reso-aware per costruzione)

```
residuo(riga) = ordini_righe.quantita − Σ qta_evasa  [ + Σ qta_resa_per_riconsegna ]
```

Tutto in **unità base** (coerente con il guard `trgfn_ordini_ful_guard_consistenza`). L'addendo
dei resi **non è ancora presente** (nessun modello resi): la slice resi estenderà questa funzione
aggiungendo il termine di rientro, **senza toccare** i gate di stato che la consumano
(vedi brief §12).
