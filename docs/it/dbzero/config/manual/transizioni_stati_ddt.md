## 📘 Documentazione Concettuale – Tabella `config.transizioni_stati_ddt`

> 👀 **Vedi anche**
>
> Tabelle:
> [config.stati_doc_ddt](/dbzero/config/tabelle/stati_doc_ddt)
> [config.transizioni_stati_ordini](/dbzero/config/tabelle/transizioni_stati_ordini)
> [vendite.ddt](/dbzero/vendite/tabelle/ddt)
>
> Funzioni:
> [vendite.trgfn_ddt_guard_transizione](/dbzero/vendite/funzioni/trgfn_ddt_guard_transizione)
> [script.fn_available_actions_ddt](/dbzero/script/funzioni/fn_available_actions_ddt)

---

### 🎯 Scopo Principale

(rev 2026-07-09)

**`config.transizioni_stati_ddt`** è la **matrice data-driven** delle transizioni ammesse
tra stati del DDT di vendita. È il mirror di `config.transizioni_stati_ordini`: stessa forma,
stesso doppio uso (enforcement + UI).

* **Lato scrittura (enforcement)**: il trigger `vendite.trgfn_ddt_guard_transizione`
  (`BEFORE UPDATE OF stato_doc_ddt_id`) ammette una transizione **solo** se la coppia
  `(stato_da_id, stato_a_id)` è presente e **`attivo = true`** in questa tabella
  (`E_STATO_DDT_TRANSIZIONE_NON_VALIDA`).
* **Lato lettura (UI)**: `script.fn_available_actions_ddt` costruisce le azioni disponibili
  del drawer dal payload `meta` → il FE non hardcoda i pulsanti.

### Colonne chiave

| Colonna | Ruolo |
|---|---|
| `stato_da_id` / `stato_a_id` | FK a `config.stati_doc_ddt` (coppia della transizione) |
| `attivo` | se `false`, la riga **documenta il grafo** ma la transizione è bloccata/non esposta |
| `meta` (jsonb) | payload UI: `action_key`, `label_key`, `severity`, `icon`, `requires_confirm`, `outlined`, `manuale` |

### Vincoli

* `UNIQUE (stato_da_id, stato_a_id)` — una sola riga per coppia.
* `CHECK stato_da_id <> stato_a_id`.
* `CHECK meta_ui`: se `manuale` è `true` (default), `action_key` e `label_key` sono **obbligatori**
  (defense-in-depth per rendere il pulsante).
* Trigger `child_requires_active_parent` su entrambi i lati verso `stati_doc_ddt`.

### Matrice seed (2026-07-09)

```
DRAFT → EMESSO (emetti, gate componenti) | DRAFT → ANNULLATO
EMESSO → SPEDITO (spedisci) | EMESSO → ANNULLATO
SPEDITO → CONSEGNATO (consegna) | SPEDITO → RESO
CONSEGNATO → RESO
CONSEGNATO → ANNULLATO   (attivo=false: annullo post-consegna da valutare)
```
