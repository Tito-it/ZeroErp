## 📘 Documentazione Concettuale – Tabella `vendite.resi_righe`

> 👀 **Vedi anche**
>
> Tabelle:
> [vendite.resi](/dbzero/vendite/tabelle/resi)
> [vendite.resi_righe_riconsegne](/dbzero/vendite/tabelle/resi_righe_riconsegne) (ponte ri-consegna)
> [vendite.ddt_righe](/dbzero/vendite/tabelle/ddt_righe) (riga sorgente)
> [config.tipi_reso](/dbzero/config/tabelle/tipi_reso)

---

### 🎯 Scopo Principale

(rev 2026-07-13)

Righe del reso: **cosa** rientra e con **quale intento**, riga per riga. Ogni riga linka la riga
DDT sorgente ed è tipizzata come *a credito* o *per ri-consegna*.

### Regole chiave

- **`ddt_riga_id` `NOT NULL`**: la riga DDT consegnata da cui proviene il rientro. `ordine_riga_id`
  è **nullable** (DDT standalone senza ordine) e alimenta l'addendo residuo quando presente.
- **Snapshot articolo/UoM** dalla riga DDT (immutabili: il reso non inventa articoli). Unità
  operativa come su `ddt_righe`: `qta_operativa` → `quantita` (base) calcolata da
  `script.trgfn_qta_from_operativa`.
- **`tipo_reso_id` `NOT NULL`** (`config.tipi_reso`, per riga): il flag `riapre_residuo` pilota il
  motore (nessun `IF` hardcoded).
- **Guard quantità** `trgfn_resi_righe_guard_quantita` (`a20`, dopo il calcolo base, lock
  `FOR UPDATE`): Σ quantità resa non-ANNULLATA sulla stessa `ddt_riga` ≤ quantità consegnata
  (`E_RESO_QTA_SUPERA_CONSEGNATO`). «Non si rende più di quanto consegnato».
- **Aggancio ri-consegna**: NON è una colonna qui, ma la tabella-ponte `resi_righe_riconsegne`
  (ri-spedizione parziale/multipla; stato ri-consegna **derivato** dalla copertura).
- Righe editabili solo con testata in DRAFT (enforcement applicativo BE via `can_edit_righe`).
