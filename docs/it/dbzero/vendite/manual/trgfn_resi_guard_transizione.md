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

### La porta del magazzino (dal 2026-09-28, Lotto 3-bis)

Seconda regola: su un reso che **fa rientrare merce**, i due passaggi che toccano il magazzino —
la conferma (`DRAFT → CONFERMATO`, carico) e l'annullo di un reso confermato
(`CONFERMATO → ANNULLATO`, storno) — si fanno solo dalle operazioni
[vendite.fn_conferma_reso](/dbzero/vendite/funzioni/fn_conferma_reso) e
[vendite.fn_annulla_reso](/dbzero/vendite/funzioni/fn_annulla_reso), che scrivono i movimenti
nella stessa transazione. Una modifica diretta dello stato è rifiutata con
`E_RESO_STATO_SOLO_DA_VERBO`: il reso risulterebbe confermato senza la sua merce.

La forma è la stessa della porta della bolla
([trgfn_ddt_guard_transizione](/dbzero/vendite/funzioni/trgfn_ddt_guard_transizione)): un
segnale che vale solo nella transazione dell'operazione, e l'operazione che gira come
proprietario delle tabelle. I resi che non muovono merce, e l'annullo di una bozza, restano
fuori dalla porta.

