## 📘 Documentazione Concettuale – Trigger function `vendite.trgfn_resi_guard_transizione`

> 👀 [config.transizioni_stati_reso](/dbzero/config/tabelle/transizioni_stati_reso) ·
> [script.fn_available_actions_reso](/dbzero/script/funzioni/fn_available_actions_reso) (read-side) ·
> [vendite.trgfn_ddt_guard_transizione](/dbzero/vendite/funzioni/trgfn_ddt_guard_transizione) (mirror)

---

### 🎯 Scopo Principale

(rev 2026-07-13)

`BEFORE UPDATE OF stato_doc_reso_id` su `vendite.resi` (fase `a10`). Enforcement DB-first del **grafo
transizioni**: la coppia `(vecchio, nuovo)` stato è ammessa solo se presente e **attiva** in
`config.transizioni_stati_reso` (`E_STATO_RESO_TRANSIZIONE_NON_VALIDA`). No-op se lo stato non cambia.
Nessun grafo hardcodato — mirror di `trgfn_ddt_guard_transizione`.
