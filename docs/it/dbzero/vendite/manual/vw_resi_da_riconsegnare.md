## 📘 Documentazione Concettuale – Vista `vendite.vw_resi_da_riconsegnare`

> 👀 **Vedi anche**
>
> [vendite.resi_righe_riconsegne](/dbzero/vendite/tabelle/resi_righe_riconsegne) (ponte) ·
> [vendite.fn_genera_ddt_riconsegna](/dbzero/vendite/funzioni/fn_genera_ddt_riconsegna) ·
> [vendite.vw_resi_da_accreditare](/dbzero/vendite/views/vw_resi_da_accreditare) (gemella)

---

### 🎯 Scopo Principale

(rev 2026-07-13)

**Coda di lavoro** delle righe reso *per ri-consegna* confermate ancora da ri-spedire. Alimenta
l'azione `fn_genera_ddt_riconsegna`. Si **auto-svuota** man mano che la copertura raggiunge la
quantità resa.

### Regole chiave

- Grana = **riga reso**. Filtro `stato = CONFERMATO` **AND `tipi_reso.riapre_residuo = true`**
  (data-driven) AND copertura incompleta (`qta_residua > 0`).
- Espone la **copertura residua** (`qta_resa − Σ resi_righe_riconsegne.qta`) e lo **`stato_riconsegna`
  DERIVATO** (`DA_RICONSEGNARE / PARZIALE / COMPLETATA`) come colonna virtuale — nessuna colonna di
  stato fisica.
- Coda **per-reso, agganciata al DDT** → funziona anche per i resi standalone (senza ordine).
- **`security_invoker=on`** + RLS sulla base; espone `emittente_fiscale_id` per il filtro BE.
