## 📘 Documentazione Concettuale – Funzione `vendite.fn_ordine_ha_residuo_evasione`

> **Ultimo aggiornamento**: 3 novembre 2026

> 👀 **Vedi anche**
>
> Tabelle:
> [vendite.ordini_righe](/dbzero/vendite/tabelle/ordini_righe)
> [vendite.ordini_righe_fulfillment](/dbzero/vendite/tabelle/ordini_righe_fulfillment)
> [vendite.resi_righe](/dbzero/vendite/tabelle/resi_righe)
>
> Funzioni:
> [vendite.fn_ordine_riga_qta_riconsegna](/dbzero/vendite/funzioni/fn_ordine_riga_qta_riconsegna) (helper addendo)
> [vendite.fn_genera_ddt_da_ordine](/dbzero/vendite/funzioni/fn_genera_ddt_da_ordine)
> [vendite.fn_conferma_reso](/dbzero/vendite/funzioni/fn_conferma_reso)

---

### 🎯 Scopo Principale

(rev 2026-07-13 — **reso-aware**; rev 2026-11-03 — **solo merce**, `20261103-22`)

**`vendite.fn_ordine_ha_residuo_evasione(p_ordine_id) → boolean`** ritorna `TRUE` se l'ordine ha
ancora quantità da evadere su **almeno una** riga **merce**. È il **gate** con cui `fn_genera_ddt_da_ordine`,
`fn_conferma_reso` e `fn_genera_ddt_riconsegna` proiettano lo stato ordine
(`CONFERMATO` / `PARZIALMENTE_EVASO` / `EVASO`).

`STABLE`, `SECURITY INVOKER`. Guard input: errore se `p_ordine_id` `NULL` o `<= 0`.

### Formula (reso-aware)

```
residuo(riga) = ordini_righe.quantita − Σ qta_evasa + Σ qta_riconsegna
```

Tutto in **unità base**. L'addendo `Σ qta_riconsegna` è calcolato dall'**helper unico**
[`fn_ordine_riga_qta_riconsegna`](/dbzero/vendite/funzioni/fn_ordine_riga_qta_riconsegna)
(somma delle righe reso di tipo *ri-consegna* su resi **CONFERMATI**). Lo stesso helper alimenta
il guard `trgfn_ordini_ful_guard_consistenza`, così gate ed enforcement usano **la stessa formula**.

### La riga-onere non ha residuo (2026-11-03)

Dal giro 1 degli oneri come righe del documento (brief-db-addebito-trasporto-ordine §8.1) un ordine
può portare articoli-onere. L'onere **non si evade**: la riga conta solo se
`script.fn_natura_e_merce(natura_vendita_id)` è vero, sulla natura **congelata** della riga. Su
ordine «non merce» vuol dire onere, perché l'ammissione lascia entrare solo merce e articoli-onere.
Così un onere non spedito non tiene l'ordine fuori da `EVASO`.

### Ciclo che converge

Evaso 10 → reso per ri-consegna 3 (residuo riaperto = 3 → ordine `PARZIALMENTE_EVASO`) →
ri-spedizione 3 (nuovo fulfillment: Σqta_evasa=13 → residuo = 10−13+3 = 0 → ordine `EVASO`).
La ri-spedizione **chiude** ciò che il reso ha riaperto.
