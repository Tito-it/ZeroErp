## 📘 Documentazione Concettuale – Funzione `script.fn_available_actions_reso`

> 👀 **Vedi anche**
>
> [config.transizioni_stati_reso](/dbzero/config/tabelle/transizioni_stati_reso) ·
> [vendite.trgfn_resi_guard_transizione](/dbzero/vendite/funzioni/trgfn_resi_guard_transizione) (lato write) ·
> [script.fn_available_actions_ddt](/dbzero/script/funzioni/fn_available_actions_ddt) (mirror)

---

### 🎯 Scopo Principale

(rev 2026-07-13)

Capability del reso per il detail API, **data-driven** da `config.transizioni_stati_reso`. È il
lato-**lettura** simmetrico al guard `trgfn_resi_guard_transizione` (stessa matrice: uno valida, uno
espone), così il FE **non hardcoda** i pulsanti.

`STABLE`, `SECURITY INVOKER`. Ritorna JSONB: `available_actions` (transizioni ammesse col filtro
`manuale`, ordinate), `can_change_state`, `can_edit_testata`/`can_edit_righe` (solo DRAFT),
`non_editable_fields`, `stato_codice`.

### Mirror RIDOTTO del DDT

Rispetto a `fn_available_actions_ddt` **omette** `push_commessa` (nessun push reso in questa slice) e
il blocco `pdf` (i resi sono fuori dal motore stampa). Copia solo matrice→azioni + capability di
editing.
