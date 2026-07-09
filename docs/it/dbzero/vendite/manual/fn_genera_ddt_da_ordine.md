## 📘 Documentazione Concettuale – Funzione `vendite.fn_genera_ddt_da_ordine`

> 👀 **Vedi anche**
>
> Tabelle:
> [vendite.ddt](/dbzero/vendite/tabelle/ddt)
> [vendite.ddt_righe](/dbzero/vendite/tabelle/ddt_righe)
> [vendite.ordini_righe_fulfillment](/dbzero/vendite/tabelle/ordini_righe_fulfillment)
>
> Funzioni:
> [vendite.fn_ordine_ha_residuo_evasione](/dbzero/vendite/funzioni/fn_ordine_ha_residuo_evasione)
> [vendite.fn_push_preventivo_a_ordine](/dbzero/vendite/funzioni/fn_push_preventivo_a_ordine) (pattern madre)
> [vendite.trgfn_ordini_ful_guard_consistenza](/dbzero/vendite/funzioni/trgfn_ordini_ful_guard_consistenza)

---

### 🎯 Scopo Principale

(rev 2026-07-09)

**`vendite.fn_genera_ddt_da_ordine`** è la **funzione madre** dell'evasione: da un ordine di
vendita crea un **DDT** (testata `DRAFT` + righe + componenti) e il **fulfillment** riga↔riga.
È DB-first e **atomica** (una `SELECT`, `SECURITY INVOKER`), sullo stile di
`fn_push_preventivo_a_ordine`.

**Firma**: `fn_genera_ddt_da_ordine(p_ordine_id bigint, p_righe jsonb DEFAULT NULL, p_data date DEFAULT CURRENT_DATE) → bigint` (ddt_id).
`p_righe` = `[{ordine_riga_id, qta_da_evadere}]` in **unità operativa**; `NULL` = tutto il residuo.

### Logica

1. **Guard**: `p_ordine_id > 0`; ordine esistente (`E_DDT_ORDINE_NOT_FOUND`) e in stato evadibile
   `CONFERMATO`/`PARZIALMENTE_EVASO` (`E_DDT_ORDINE_STATO_NON_EVADIBILE`).
2. **Testata DDT** `DRAFT`: `sorgente_tipo_id = ORDINE_VENDITA` (**non** DDT_VENDITA: è la
   condizione perché `trgfn_ddt_normalize` erediti billing/utility/valuta), `sorgente_uid = ordini.uid`,
   destinatario = `ordini.soggetto_ruolo_id`. Il `numero` **non** si assegna in DRAFT.
3. **Righe (snapshot A-2)**: per ogni riga con residuo > 0 copia `prezzo_unitario`/`sconto_percentuale`/`iva_id`;
   `qta_operativa` = qta da evadere (il trigger `qta_from_operativa` deriva `quantita` base). Padre
   composito: prezzo placeholder 0, ricalcolato dai componenti.
4. **Componenti CASO A (A-2)**: copia 1:1 `ordini_righe_componenti → ddt_righe_componenti` senza
   resolver; i trigger `m50_calcola_quantita` (qta figlio) e `z90_ricalcola_padre` (prezzo padre)
   scalano sul parziale.
5. **Fulfillment**: `ordini_righe_fulfillment(ordine_riga_id, ddt_riga_id, qta_evasa)`. L'over-shipping
   è bloccato dal guard `trgfn_ordini_ful_guard_consistenza` (`E_QTA_SUPERA_RESIDUO`) — **nessuna
   logica di residuo duplicata** nella madre.
6. **Idempotenza**: via residuo (niente token). Se non resta nulla → `E_DDT_NIENTE_DA_EVADERE`
   (rollback della testata orfana).
7. **Proiezione stato ordine**: residuo pieno → `CONFERMATO`, `0 < residuo < pieno` →
   `PARZIALMENTE_EVASO`, residuo 0 → `EVASO` (predicato `fn_ordine_ha_residuo_evasione`, atomico).

### Note

* **Multi-DDT (A-1)**: un ordine può generare più DDT (consegne parziali). L'unicità del legame è
  sul fulfillment `(ordine_riga_id, ddt_riga_id)`, non sulla testata.
* **Refresh MV** `mv_ddt_ordini`: fuori dalla funzione (job `dbops.fn_refresh_mv_ddt_ordini`).
* **DDT standalone** (senza ordine): non usa questa funzione, solo la CRUD BE (testata con
  `billing_account` proprio, senza `sorgente_uid`).
