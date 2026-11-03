## 📘 Documentazione Concettuale – Funzione `vendite.fn_genera_ddt_da_ordine`

> **Ultimo aggiornamento**: 3 novembre 2026

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

### La riga-onere passa intera, una volta sola (rev 2026-11-03)

Dal giro 1 degli oneri come righe del documento (`20261103-36`, brief-db-addebito-trasporto-ordine §8.2,
K-4/K-5) l'ordine può portare articoli-onere. La copia li tratta così:

* la riga-onere (`script.fn_natura_e_merce(natura_vendita_id)` falso, sulla natura **congelata**) entra
  nella **prima** bolla anche se `p_righe` non la nomina, e sempre **intera**: `qta_da_evadere` per lei
  non conta. La natura congelata viaggia come per le altre righe;
* il legame è il fulfillment, con la quantità intera: è il suo «già passato». La bolla dopo trova
  residuo 0 e la salta; annullando la bolla il legame si ritira e l'onere torna copiabile;
* «nulla da evadere» (passo 6) conta la sola **merce**: una bolla che porterebbe solo oneri è
  `E_DDT_NIENTE_DA_EVADERE` (un addebito senza merce si fa in commessa, K-2).

La regola «intero» non sta qui: la tiene il guard del legame
([`vendite.trgfn_ordini_ful_guard_consistenza`](/dbzero/vendite/funzioni/trgfn_ordini_ful_guard_consistenza)).
Presidio: `db/pgtap/vendite/test-ordine-onere-copia-push-v1.sql`.

### Note

* **Multi-DDT (A-1)**: un ordine può generare più DDT (consegne parziali). L'unicità del legame è
  sul fulfillment `(ordine_riga_id, ddt_riga_id)`, non sulla testata.
* **Legame testata↔testata**: si ricava da `vendite.ordini_righe_fulfillment` (riga↔riga) oppure da `vendite.ddt.sorgente_uid`. Fino al 2026-08-05 esisteva anche la vista materializzata `mv_ddt_ordini`, **ritirata** (changeSet `20260805-21/-22`) perché nessuno la leggeva e nessuno la aggiornava.
* **DDT standalone** (senza ordine): non usa questa funzione, solo la CRUD BE (testata con
  `billing_account` proprio, senza `sorgente_uid`).
