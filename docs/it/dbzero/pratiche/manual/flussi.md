## 📘 Documentazione Concettuale – Tabella `pratiche.flussi`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche)
> [pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi)
> [pratiche.template_flussi_prerequisiti](/dbzero/pratiche/tabelle/template_flussi_prerequisiti)
> [pratiche.regole_generazione](/dbzero/pratiche/tabelle/regole_generazione)
> [pratiche.giornale](/dbzero/pratiche/tabelle/giornale)
> [config.stati_flussi_pratiche](/dbzero/config/tabelle/stati_flussi_pratiche)

---
### 🎯 Scopo Principale
La tabella `pratiche.flussi` contiene le **istanze operative dei flussi** di una pratica. Ogni flusso e' uno step del workflow, creato da un template (opzionale) o manualmente, con stato, esito e assegnazione propri.

---

### Ruolo nel processo

* Ogni pratica ha uno o piu' flussi che ne compongono il workflow.
* I flussi con `template_flusso_id NOT NULL` sono istanze di template configurati; quelli con `NULL` sono step manuali (bypassano i guard prerequisiti e ripetibilita').
* Il template del flusso deve appartenere alla **stessa edizione di workflow** pinnata dalla pratica (`definizione_id`): guard [trgfn_flussi_guard_definizione](trgfn_flussi_guard_definizione.md) BEFORE INSERT (508). Coerenza pin↔step del versionamento (V6).
* Al completamento (transizione stato → COMPLETATO), l'`esito` viene registrato e puo' attivare la **generazione cross-pratica** (se esistono regole matching con `auto = true`).
* I **prerequisiti** (configurati in `template_flussi_prerequisiti`, esito-aware) sono verificati dal trigger guard BEFORE INSERT: e' il meccanismo che esprime anche i **bivi condizionali** (D4).
* La **ripetibilita'** (`template_flussi.ripetibilita`, D3) e' verificata dal guard BEFORE INSERT `trg_flussi_a10_guard_ripetibilita_ins`: governa quante istanze dello stesso template possono nascere nella stessa pratica (l'ultima istanza = `MAX(id)`, escluse le ANNULLATO).

---

### Colonne specifiche

| Colonna | Note |
|---------|------|
| `template_flusso_id` | INTEGER nullable. NULL = flusso manuale (non derivato da template). |
| `flusso_padre_id` | BIGINT nullable. Self-reference per sotto-flussi. ON DELETE SET NULL. |
| `sequenza` | INTEGER DEFAULT 0. Ordine di esecuzione nel workflow della pratica. |
| `esito` | VARCHAR(20), FK → `config.esiti_flussi_pratiche(codice_interno)` (dal `20260701-02`, non più CHECK). Registrato al completamento; la **classe** ammessa (verdetto vs esito di ramo) dipende dalla `modalita_esito` del template — guard [trgfn_flussi_guard_esito_classe](trgfn_flussi_guard_esito_classe.md) (504). |
| `note_esito` | TEXT nullable. Note libere sull'esito. |
| `data_scadenza` | DATE nullable. Scadenza prevista per lo step. |

---

### Vincoli e regole

* **FK esito**: `config.esiti_flussi_pratiche(codice_interno)`; la classe (verdetto/ramo) è vincolata al completamento in base alla `modalita_esito` del template (guard 504).
* **Guard definizione** (Fase 1): BEFORE INSERT, il template deve appartenere alla definizione pinnata dalla pratica (508).
* **Guard prerequisiti** (DB-5): BEFORE INSERT verifica che tutti i prerequisiti del template siano completati.
* **Generazione cross-pratica** (DB-5): AFTER UPDATE, se stato → COMPLETATO, cerca regole matching e genera pratiche.
* **FK differita**: la FK `pratiche.flusso_origine_id → flussi.id` e' definita in questo changeSet perche' crea una dipendenza circolare (pratiche → flussi → pratiche).

---

### Convenzioni

* PK BIGINT IDENTITY (tabella operativa ad alto volume).
* `storicizza = true` per tracciamento modifiche.
* Trigger standard applicati automaticamente dai runner del framework di automazione (`dbops.fn_run_automations_<tipo>`).
* Trigger business-specific (guard prerequisiti, giornale, generazione) in DB-5.

---

{% include-markdown "signature-core.md" %}
