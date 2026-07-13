## 📘 Documentazione Concettuale – Vista `vendite.vw_resi_da_accreditare`

> 👀 **Vedi anche**
>
> [vendite.resi_righe](/dbzero/vendite/tabelle/resi_righe) ·
> [config.tipi_reso](/dbzero/config/tabelle/tipi_reso) ·
> [vendite.vw_resi_da_riconsegnare](/dbzero/vendite/views/vw_resi_da_riconsegnare) (gemella)

---

### 🎯 Scopo Principale

(rev 2026-07-13)

**Coda di lavoro** delle righe reso *a credito* confermate, da accreditare via nota di credito. In
questa slice è **solo predisposizione**: la vista è interrogabile, la generazione NC arriva con una
slice successiva.

### Regole chiave

- Grana = **riga reso**. Filtro `stato = CONFERMATO` **AND `tipi_reso.riapre_residuo = false`**
  (credito, **data-driven** — non si hardcoda il codice) AND riga attiva.
- Riferimenti per la futura NC: DDT/riga DDT origine, billing account, emittente, articolo/quantità.
- **`security_invoker=on`** + RLS sulla base; espone `emittente_fiscale_id` per il filtro
  applicativo BE.
