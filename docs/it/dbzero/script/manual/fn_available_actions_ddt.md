## 📘 Documentazione Concettuale – Funzione `script.fn_available_actions_ddt`

> 👀 **Vedi anche**
>
> Tabelle:
> [config.transizioni_stati_ddt](/dbzero/config/tabelle/transizioni_stati_ddt)
> [vendite.ddt](/dbzero/vendite/tabelle/ddt)
>
> Funzioni:
> [script.fn_available_actions_ordine](/dbzero/script/funzioni/fn_available_actions_ordine) (mirror)
> [vendite.trgfn_ddt_guard_transizione](/dbzero/vendite/funzioni/trgfn_ddt_guard_transizione)
> [vendite.fn_list_ddt_da_pushare](/dbzero/vendite/funzioni/fn_list_ddt_da_pushare)

---

### 🎯 Scopo Principale

(rev 2026-07-09)

**`script.fn_available_actions_ddt(p_ddt_id) → jsonb`**: capabilities del DDT per il detail API
(drawer). Mirror di `fn_available_actions_ordine`, `STABLE`. È il **lato lettura** simmetrico al
guard `vendite.trgfn_ddt_guard_transizione` (stessa matrice `config.transizioni_stati_ddt`).

### Output (jsonb)

| Chiave | Contenuto |
|---|---|
| `available_actions` | transizioni manuali disponibili per lo stato corrente (da `meta.ui`: `key`/`label_key`/`severity`/`icon`/`requires_confirm`/`outlined`) → il FE non hardcoda i pulsanti |
| `can_change_state` | esiste almeno una transizione disponibile |
| `can_edit_testata` / `can_edit_righe` | `true` solo in `DRAFT` |
| `can_push_commessa` (+ `_reason`/`_reason_key`) | eleggibile se il DDT ha righe pushabili (riuso `fn_list_ddt_da_pushare`, tipicamente SPEDITO/CONSEGNATO) — nessuna logica pushable duplicata |
| `non_editable_fields` | campi bloccati (in DRAFT: sorgente/billing/numero; fuori DRAFT: tutta la testata) |
| `stato_codice` | `codice_interno` dello stato corrente |

Fallback sicuro: `NULL` se il DDT non esiste.
