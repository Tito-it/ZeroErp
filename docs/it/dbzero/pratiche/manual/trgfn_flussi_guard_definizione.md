## 📘 Documentazione Trigger Function – `pratiche.trgfn_flussi_guard_definizione`

> 👀 **Vedi anche**
>
Funzioni collegate:
>
[pratiche.trgfn_pratiche_guard_pin_immutabile](trgfn_pratiche_guard_pin_immutabile.md)
> [pratiche.trgfn_workflow_definizioni_guard](trgfn_workflow_definizioni_guard.md)
> [pratiche.fn_genera_pratica_da_flusso](fn_genera_pratica_da_flusso.md)
>
Tabelle:
>
[pratiche.flussi](flussi.md)
> [pratiche.template_flussi](template_flussi.md)
> [pratiche.workflow_definizioni](workflow_definizioni.md)

---
### 🎯 Scopo Principale

Guard di **coerenza pin↔step** (V6/versionamento): un flusso appartiene a una pratica,
e il suo template deve stare nella **stessa edizione di workflow** che la pratica ha
**pinnato alla nascita** (`pratiche.definizione_id`). Impedisce che una pratica accolga
uno step di un'altra definizione — altro tipo, oppure (dalla Fase 2) un'altra
edizione/fork dello stesso tipo.

> `template.definizione_id` ≠ `pratica.definizione_id` → `FLUSSI_TEMPLATE_FUORI_DEFINIZIONE` (508)

---

### Trigger associato

| Trigger | Timing | Evento | Tabella |
|---|---|---|---|
| `trg_flussi_a10_guard_definizione_ins` | BEFORE | INSERT | `pratiche.flussi` |

Fase `_a10_`, descrizione `guard_definizione` → in ordine lessicografico è il **primo**
dei guard BEFORE INSERT su `flussi` (`guard_definizione` < `guard_esito_classe` < …).
Solo INSERT: `pratica_id`/`template_flusso_id` sono di fatto immutabili dopo la creazione
del flusso (coerente coi guard sorella `_prerequisiti`/`_ripetibilita`).

---

### Regole

* Confronto netto: entrambe le colonne `definizione_id` (su `pratiche` e su
  `template_flussi`) sono NOT NULL dalla Fase 0.
* **Compatibile per costruzione** con:
  * pgTAP e seed esistenti — template e pratica sono sempre dello stesso tipo → stessa
    definizione preset;
  * **seed CSV di istanze `pratiche.flussi`** (dati demo/collaudo): idem, se pratica e
    template sono coerenti; un seed incoerente è un errore di dato e va rifiutato;
  * la **generazione cross-pratica** —
    [fn_genera_pratica_da_flusso](fn_genera_pratica_da_flusso.md) rimappa il template
    destinazione per codice nella definizione pinnata della figlia, così il flusso
    inserito soddisfa questo guard.

---

### Note operative

* Errore: `FLUSSI_TEMPLATE_FUORI_DEFINIZIONE` (508), con codice template, definizione del
  template e definizione della pratica.
* Introdotto con `20260703-01` (brief-db-step-dominio-e-definizioni-versionate, Parte 2 /
  Fase 1, D2-7).
* Test: `db/pgtap/pratiche/test-workflow-definizioni-fase1.sql` (casi 2–3, coerente/incoerente).
