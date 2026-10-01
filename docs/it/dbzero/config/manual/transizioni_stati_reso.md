## 📘 Documentazione Concettuale – Tabella `config.transizioni_stati_reso`

> 👀 **Vedi anche**
>
> [config.stati_doc_reso](/dbzero/config/tabelle/stati_doc_reso) ·
> [vendite.trgfn_resi_guard_transizione](/dbzero/vendite/funzioni/trgfn_resi_guard_transizione) (enforcement) ·
> [script.fn_available_actions_reso](/dbzero/script/funzioni/fn_available_actions_reso) (read-side)

---

### 🎯 Scopo Principale

(rev 2026-07-13)

**Matrice** delle transizioni ammesse tra stati del reso, mirror di `transizioni_stati_ddt`. È
insieme il **grafo** validato dal guard (`trgfn_resi_guard_transizione`) e la **fonte metadati UI**
(`meta.ui`: `action_key`, `label_key`, `requires_confirm`, `outlined`, `manuale`) per le
azioni data-driven. Icona e colore (`severity`) non stanno nel `meta`: il frontend li
sceglie dall'`action_key`.

### Seed (tutte manuali)

| da | a | azione |
| --- | --- | --- |
| `DRAFT` | `CONFERMATO` | conferma |
| `DRAFT` | `ANNULLATO` | annulla |
| `CONFERMATO` | `ANNULLATO` | annulla (storno) |

`CHECK`: una transizione **manuale** deve avere `action_key` + `label_key` (le automatiche —
`manuale=false` — ne sono esonerate e sono escluse dai pulsanti in `fn_available_actions_reso`).
