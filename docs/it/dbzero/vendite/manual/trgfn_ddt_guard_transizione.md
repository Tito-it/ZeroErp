## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_ddt_guard_transizione`

> 👀 **Vedi anche**
>
> Tabelle:
> [config.transizioni_stati_ddt](/dbzero/config/tabelle/transizioni_stati_ddt)
> [config.stati_doc_ddt](/dbzero/config/tabelle/stati_doc_ddt)
> [vendite.ddt](/dbzero/vendite/tabelle/ddt)
>
> Funzioni:
> [vendite.trgfn_ordini_guard_transizione](/dbzero/vendite/funzioni/trgfn_ordini_guard_transizione) (mirror)
> [vendite.trgfn_ddt_guard_transizione_approvazione](/dbzero/vendite/funzioni/trgfn_ddt_guard_transizione_approvazione)

---

### 🎯 Scopo Principale

(rev 2026-07-09)

Trigger function di **enforcement DB-first del grafo transizioni** dello stato DDT. Mirror di
`trgfn_ordini_guard_transizione`. Agganciata a `vendite.ddt` come trigger
`trg_ddt_a10_guard_transizione_upd` (`BEFORE UPDATE OF stato_doc_ddt_id`).

* No-op se lo stato non cambia davvero.
* Ammette la transizione `(OLD.stato → NEW.stato)` **solo** se presente e `attivo = true` in
  `config.transizioni_stati_ddt`, altrimenti `E_STATO_DDT_TRANSIZIONE_NON_VALIDA`.
* **Convivenza**: trigger distinto dal gate emissione `trg_ddt_a10_guard_approvazione_upd`
  (concern diverso — componenti BoM PENDING). Entrambi fase `_a10_` su `UPDATE OF stato_doc_ddt_id`.
* L'INSERT non è vincolato dalla matrice (il DDT nasce in `DRAFT`); il guard scatta solo su UPDATE.
