## 📘 Documentazione Concettuale – Tabella `config.stati_doc_reso`

> 👀 **Vedi anche**
>
> [config.transizioni_stati_reso](/dbzero/config/tabelle/transizioni_stati_reso) ·
> [config.stati_doc_ddt](/dbzero/config/tabelle/stati_doc_ddt) (mirror) ·
> [vendite.resi](/dbzero/vendite/tabelle/resi)

---

### 🎯 Scopo Principale

(rev 2026-07-13)

Stati del **documento reso**, mirror di `stati_doc_ddt` **senza** le colonne `pdf_*` (i resi sono
fuori dal motore stampa in questa slice).

| `codice_interno` | note |
| --- | --- |
| `DRAFT` | bozza (righe editabili, numero NULL) |
| `CONFERMATO` | effetti applicati, numero assegnato |
| `ANNULLATO` | terminale (storno via `fn_annulla_reso`) |

Lo stato `ACCREDITATO` arriverà con la slice nota di credito (solo un seed, non un rework). La
logica usa **sempre** `codice_interno` (immutabile), mai `codice`.
