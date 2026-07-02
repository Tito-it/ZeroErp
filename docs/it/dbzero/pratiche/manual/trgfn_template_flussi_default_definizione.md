## 📘 Documentazione Trigger Function – `pratiche.trgfn_template_flussi_default_definizione`

> 👀 **Vedi anche**
>
Funzioni collegate:
>
[pratiche.fn_risolvi_definizione](fn_risolvi_definizione.md)
> [pratiche.trgfn_pratiche_default_definizione](trgfn_pratiche_default_definizione.md)
>
Tabelle:
>
[pratiche.workflow_definizioni](workflow_definizioni.md)
> [pratiche.template_flussi](template_flussi.md)

---
### 🎯 Scopo Principale

**Auto-default del re-parent**: un template inserito **senza** `definizione_id`
appartiene al **preset** del suo tipo (`fn_risolvi_definizione(tipo, NULL)`). È la
fotografia della realtà pre-fork: chi lavora su un'edizione specifica (fork/BOZZA,
Fase 2) passa `definizione_id` **esplicito**.

Mantiene invariati **seed CSV e fixture pgTAP** (INSERT senza la colonna) anche dopo il
`SET NOT NULL` di Fase 0.

---

### Trigger associato

| Trigger | Timing | Evento | Tabella |
|---|---|---|---|
| `trg_template_flussi_a10_default_definizione_ins` | BEFORE | INSERT | `pratiche.template_flussi` |

Fase `_a10_` con descrizione `default` — in ordine lessicografico gira **prima** dei
guard della tabella (`..._a10_default_...` < `..._a10_guard_...`).

---

### Regole

* Interviene **solo** quando `NEW.definizione_id IS NULL`; un valore esplicito passa
  intatto (la FK composita `(definizione_id, tipo_prestazione_id)` garantisce già la
  coerenza col tipo).
* Se il tipo non ha un preset PUBBLICATA (caso anomalo: bootstrap+backfill lo
  impediscono), la risoluzione fallisce **parlante** con `DEFINIZIONE_NON_TROVATA` (507).
* Prospettiva Fase 1: il guard di immutabilità della PUBBLICATA intercetterà comunque i
  tentativi di aggiungere step a un'edizione pubblicata, default incluso → il flusso di
  configurazione passerà dalle BOZZE.

---

### Note operative

* Introdotta con `20260702-23` (brief-db-step-dominio-e-definizioni-versionate,
  Parte 2 / Fase 0, raffinamento §2.1).
* Test: `db/pgtap/pratiche/test-workflow-definizioni-fase0.sql` (casi 2, 5, 7, 8).
