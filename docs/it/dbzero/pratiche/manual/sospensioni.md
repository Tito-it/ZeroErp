## 📘 Documentazione Concettuale – Tabella `pratiche.sospensioni`

> 👀 **Vedi anche**
>
Tabelle:
>
[pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche)
> [pratiche.flussi](/dbzero/pratiche/tabelle/flussi)
> [pratiche.giornale](/dbzero/pratiche/manual/giornale)
>
Funzioni:
>
[trgfn_sospensioni_guard_coerenza_flusso](/dbzero/pratiche/manual/trgfn_sospensioni_guard_coerenza_flusso)
> [trgfn_sospensioni_propaga](/dbzero/pratiche/manual/trgfn_sospensioni_propaga)
> [trgfn_sospensioni_riattiva](/dbzero/pratiche/manual/trgfn_sospensioni_riattiva)

---
### 🎯 Scopo Principale
Registra i periodi di fermo di una pratica o di un singolo flusso. Ogni riga e' un intervallo aperto (`data_fine NULL` = sospensione ancora attiva).

---

### Campi chiave (semantica)

| Colonna                      | Note                                                                 |
| ---------------------------- | -------------------------------------------------------------------- |
| `pratica_id`                 | FK a `pratiche.pratiche` — sempre valorizzata.                       |
| `flusso_id`                  | FK a `pratiche.flussi`. NULL = sospensione intera pratica.           |
| `data_inizio`                | Inizio sospensione (default `now()`).                                |
| `data_fine`                  | Fine sospensione. NULL = ancora attiva.                              |
| `periodo_sospensione`        | `tstzrange` calcolato dal trigger da `data_inizio`/`data_fine`. Bounds `[)`. Query: `@> ts`. |
| `data_riattivazione_prevista`| DATE per riattivazione automatica via job pgAgent.                   |
| `motivo`                     | Motivazione obbligatoria (TEXT NOT NULL).                            |

---

### Vincoli

* **CHECK** `data_fine IS NULL OR data_fine > data_inizio`
* **UNIQUE parziale** su `pratica_id` WHERE `data_fine IS NULL AND flusso_id IS NULL` — un solo record attivo a livello pratica.
* **UNIQUE parziale** su `(pratica_id, flusso_id)` WHERE `data_fine IS NULL AND flusso_id IS NOT NULL` — un solo record attivo per flusso.

---

### 🚨 Trigger

| Nome                                               | Fase   | Evento                | Scopo                                           |
| -------------------------------------------------- | ------ | --------------------- | ----------------------------------------------- |
| `trg_sospensioni_a10_guard_coerenza_flusso_ins_upd` | BEFORE | INSERT, UPDATE OF flusso_id | Coerenza flusso_id/pratica_id                |
| `trg_sospensioni_z90_propaga_sospensione_ins`       | AFTER  | INSERT                | Propaga sospensione ai flussi attivi             |
| `trg_sospensioni_z90_propaga_riattivazione_upd`     | AFTER  | UPDATE OF data_fine   | Ripristina stati precedenti alla riattivazione   |
| `trg_sospensioni_z90_giornale_ins`                  | AFTER  | INSERT                | SOSPENSIONE_REGISTRATA nel giornale              |
| `trg_sospensioni_z90_giornale_riattivazione_upd`    | AFTER  | UPDATE OF data_fine   | SOSPENSIONE_CHIUSA nel giornale                  |

---

### Note operative

* Sospensione a livello pratica (`flusso_id IS NULL`): propaga SOSPESO a tutti i flussi attivi (DA_ESEGUIRE, IN_CORSO).
* Riattivazione: ripristina lo stato precedente dei flussi leggendolo dal giornale.
* Job pgAgent giornaliero: cerca sospensioni con `data_riattivazione_prevista <= CURRENT_DATE` e `data_fine IS NULL`, imposta `data_fine = NOW()`.

---

{% include-markdown "signature-core.md" %}
