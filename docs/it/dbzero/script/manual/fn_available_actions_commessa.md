## 📘 Documentazione Concettuale – Funzione `script.fn_available_actions_commessa`
### 🎯 Scopo Principale
(latest review 16-06-2026)
Espone le **capability del ciclo di vita di una commessa** per il detail/stato API:
quali azioni di stato l'utente può eseguire e cosa può modificare. Mirror del pattern
`fn_available_actions_ordine` / `_offerta` / `_contratto` / `_preventivo`, **senza azioni
applicative** (il push è *verso* la commessa, non un'azione della commessa).

---

### Regole applicate

* `available_actions`: transizioni **utente** ammesse dallo stato corrente, lette da
  `vendite.transizioni_stati_commessa` in modo **data-driven** dal `meta`
  (`action_key`, `label_key`, `severity`, `icon`, `requires_confirm`, `outlined`).
* Filtri: `stato_da_id = stato corrente`, `attivo`, `meta.manuale = true`, presenza di
  `action_key` + `label_key` (simmetrico al CHECK `ck_transizioni_stati_comm_meta_ui`).
* Le transizioni **automatiche** (`manuale=false`, ponte push/emittibilità) **non**
  compaiono tra le azioni utente.
* `can_change_state`: `true` se esiste ≥1 transizione manuale ammessa.
* `can_edit_righe`: flag `vendite.stati_commessa.modificabile` dello stato corrente.
* `is_emittibile`: flag `vendite.stati_commessa.emittibile` dello stato corrente (informativo).
* `stato_codice`: `codice_interno` dello stato corrente.
* Gli stati terminali (`CHIUSA`, `ANNULLATA`) non hanno transizioni manuali in uscita e
  hanno `modificabile=false` → `available_actions=[]`, `can_change_state=false`,
  `can_edit_righe=false`.
* L'**enforcement** della transizione resta su `vendite.trgfn_commesse_guard_transizione`
  (via `fn_cambia_stato_commessa`); questa funzione è di sola lettura (capability), non
  esegue la transizione.
* Fallback sicuro: ritorna `NULL` se la commessa non esiste.

---

### Output (jsonb)

* `available_actions` — array di `{ key, target_state, label_key, severity, icon, requires_confirm, outlined }`
* `can_change_state` — bool
* `can_edit_righe` — bool
* `is_emittibile` — bool
* `stato_codice` — text

---

{% include-markdown "signature-core.md" %}
