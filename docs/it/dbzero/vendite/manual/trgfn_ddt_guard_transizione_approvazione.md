## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_ddt_guard_transizione_approvazione`

> 👀 **Vedi anche**
>
> Tabelle:
> [vendite.ddt_righe_componenti](/dbzero/vendite/tabelle/ddt_righe_componenti)
> [config.stati_doc_ddt](/dbzero/config/tabelle/stati_doc_ddt)
>
> Funzioni:
> [vendite.trgfn_ddt_guard_transizione](/dbzero/vendite/funzioni/trgfn_ddt_guard_transizione)

---

### 🎯 Scopo Principale

(rev 2026-07-09)

**Gate emissione** del DDT (BoM CASO A). Trigger function agganciata a `vendite.ddt` come
`trg_ddt_a10_guard_approvazione_upd` (`BEFORE UPDATE OF stato_doc_ddt_id`). Si auto-gatta a
**EMESSO** (`RETURN NEW` se lo stato non è EMESSO).

Alla transizione a EMESSO blocca se, sulle righe del DDT, esistono componenti CASO A:

* con `stato_approvazione_prezzo = 'PENDING'` → `E_COMPONENTE_PREZZO_PENDENTE`;
* attivi con `prezzo_unitario IS NULL` → `E_DOC_COMPONENTI_PENDING_VALORIZZAZIONE`.

Simmetrico al guard testata del preventivo e al guard approvazione degli ordini. Convive con il
guard grafo transizioni (`trg_ddt_a10_guard_transizione_upd`): concern diverso, nessuna
sovrapposizione di regola.

> **Nota storica**: la funzione era definita ma non agganciata (analisi §2.1); di fatto sul DB non
> esisteva. Il changeSet `20260709-05` la crea (dalla doc auto-gen) e la aggancia.
