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

---

### La porta: non sta più qui (2026-10-25)

Fino al 2026-10-25 questo guard aveva una seconda regola, la porta del magazzino: sui resi che fanno
rientrare merce, conferma e annullo del confermato si facevano solo dai verbi
(`E_RESO_STATO_SOLO_DA_VERBO`, ritirato). Oggi ogni cambio di stato del reso, con o senza merce, passa
dalla porta comune
[script.trgfn_doc_stato_solo_dal_verbo](/dbzero/script/funzioni/trgfn_doc_stato_solo_dal_verbo)
(`E_DOC_STATO_SOLO_DAL_VERBO`), che la contiene. Qui resta la matrice.

