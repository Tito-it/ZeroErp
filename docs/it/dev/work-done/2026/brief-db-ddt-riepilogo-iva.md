# Brief DB — DDT vendita: viste riepilogo IVA (clone ordini)

> **Tipo**: brief al team DB · **Target**: `dev/db-tid` · **Data**: 2026-07-11 · **Owner**: Tid
> **Contesto**: chiusura del residuo "riepilogo IVA" del DDT
> ([brief-fe-ddt-vendita.md](brief-fe-ddt-vendita.md) §4/§11 "fuori scope predisposto").
> Richiesta piccola e autonoma: **2 viste**, clone 1:1 delle omologhe ordini.
> **Stato: ✅ CHIUSO (2026-07-12)** — viste applicate dal team DB (note recepite:
> clone dalla -16, security_invoker esplicito, filtro `prezzo_unitario IS NOT NULL`,
> pgTAP `test-ddt-riepilogo-iva.sql` + equivalenza cross-doc); BE/FE consegnati
> (mixin+factory riepilogo IVA, pannello nel DdtDrawer, doc `api_ddt.md`).

---

## Richiesta

Il pannello "Riepilogo IVA" di preventivi e ordini legge da coppie di viste
(`vw_<doc>_righe_iva_base` → `vw_<doc>_riepilogo_iva_dettaglio`); per i DDT non
esistono. Servono:

### 1. `vendite.vw_ddt_righe_iva_base`

Clone di `vendite.vw_ordini_righe_iva_base` con sostituzioni
`ordini_righe→ddt_righe`, `ordini→ddt`, `ordine_id→ddt_id`. Prerequisiti verificati:
`ddt_righe` ha `quantita/prezzo_unitario/sconto_percentuale/iva_id/attivo`;
`ddt.emittente_fiscale_id` esiste (per `fn_get_aliquota_iva` con stato emittente,
stessa catena JOIN emittenti_fiscali→soggetti_ruoli→soggetti).

**Unica differenza dal clone**: su DDT `prezzo_unitario` e `iva_id` sono **nullable**
(DDT anche solo "di trasporto", non valorizzato). Proposta: aggiungere al WHERE
`AND r.prezzo_unitario IS NOT NULL` — le righe non valorizzate restano fuori dal
riepilogo (DDT interamente non valorizzato → riepilogo vuoto, il FE nasconde il
pannello). A vostro giudizio se preferite `COALESCE(prezzo,0)`.

### 2. `vendite.vw_ddt_riepilogo_iva_dettaglio`

Clone di `vendite.vw_ordini_riepilogo_iva_dettaglio` (stessa formula fiscale: ROUND 2
sull'aggregato per aliquota, DPR 633/72 art. 21 + DM 24/12/93; shape allineato:
`natura_*`/`esigibilita`/`split_payment` NULL, niente `id` tecnico, chiave logica
`ddt_id + iva_id`), sorgente la vista del punto 1.

### 3. pgTAP

- Shape/formula: DDT con 2 aliquote e sconto riga → imponibile/imposta attesi
  (stessi casi dei test ordini).
- Riga con `prezzo_unitario NULL` esclusa; DDT non valorizzato → 0 righe.
- Aliquota effettiva via `fn_get_aliquota_iva` con emittente estero (se già
  testato per ordini, basta il mirror).

## Non richiesto

Nessuna tabella, nessun trigger, nessun ricalcolo di testata: lettura pura come per
gli ordini (i DDT non hanno totali di testata da mantenere).
