## 📘 Documentazione Concettuale – Vista `vendite.vw_resi_da_riconsegnare`

> 👀 **Vedi anche**
>
> [vendite.resi_righe_riconsegne](/dbzero/vendite/tabelle/resi_righe_riconsegne) (ponte) ·
> [vendite.fn_genera_ddt_riconsegna](/dbzero/vendite/funzioni/fn_genera_ddt_riconsegna) ·
> [vendite.vw_resi_da_accreditare](/dbzero/vendite/views/vw_resi_da_accreditare) (gemella)

---

### 🎯 Scopo Principale

(rev 2026-07-26)

**Coda di lavoro** delle righe reso *per ri-consegna* confermate ancora da ri-spedire. Alimenta
l'azione `fn_genera_ddt_riconsegna`. Si **auto-svuota** man mano che la copertura raggiunge la
quantità resa.

### Regole chiave

- Grana = **riga reso**. Filtro `stato = CONFERMATO` **AND `tipi_reso.riapre_residuo = true`**
  (data-driven) AND copertura incompleta (`qta_residua > 0`).
- Espone la **copertura residua** — dal 2026-07-26 calcolata dall'helper unico
  [`fn_resi_riga_residuo_riconsegna`](/dbzero/vendite/funzioni/fn_resi_riga_residuo_riconsegna),
  cioè `qta_resa − Σ riconsegnate − Σ rinunciate` — e lo **`stato_riconsegna` DERIVATO**
  come colonna virtuale (nessuna colonna di stato fisica):

  | stato | significato |
  | --- | --- |
  | `DA_RICONSEGNARE` | nulla lavorato |
  | `PARZIALE` | qualcosa lavorato, residuo ancora > 0 |
  | `RINUNCIATA` | residuo 0 **con** almeno una rinuncia: chiusa definitivamente |
  | `COMPLETATA` | residuo 0 **senza** rinunce: tutto ri-spedito |

- **Le righe chiuse escono da sole dalla coda** (rev 2026-07-26): una quota dichiarata
  definitiva porta il residuo a 0 e la `WHERE` la esclude. Era il punto della slice — prima
  restava in elenco indistinguibile da una lavorabile.
  ⚠️ Per questo `RINUNCIATA` e `COMPLETATA` non si vedono *interrogando la coda*: restano
  per chi legge la vista per `resi_riga_id` (es. il consuntivo in dialog).
- Espone `qta_rinunciata` accanto a `qta_riconsegnata`: consuntivo delle due uscite.
- Coda **per-reso, agganciata al DDT** → funziona anche per i resi standalone (senza ordine).
- **`security_invoker=on`** + RLS sulla base; espone `emittente_fiscale_id` per il filtro BE.
