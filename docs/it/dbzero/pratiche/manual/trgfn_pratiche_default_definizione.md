## 📘 Documentazione Trigger Function – `pratiche.trgfn_pratiche_default_definizione`

> 👀 **Vedi anche**
>
Funzioni collegate:
>
[pratiche.fn_risolvi_definizione](fn_risolvi_definizione.md)
> [pratiche.trgfn_template_flussi_default_definizione](trgfn_template_flussi_default_definizione.md)
>
Tabelle:
>
[pratiche.workflow_definizioni](workflow_definizioni.md)
> [pratiche.pratiche](pratiche.md)

---
### 🎯 Scopo Principale

**Auto-pin dell'edizione di workflow** alla nascita della pratica (V6): se
`definizione_id` è NULL lo risolve con `fn_risolvi_definizione(tipo, emittente della
pratica)` — l'edizione **PUBBLICATA dell'emittente** (fork, Fase 2) vince sul
**preset**. Il pin è per sempre: le pratiche in volo restano sull'edizione con cui sono
nate, qualunque cosa accada alle definizioni dopo.

DB-first: il BE (`create_pratica`, INSERT senza la colonna) **resta invariato** — è il
motivo per cui l'auto-pin è stato anticipato dalla Fase 1 alla Fase 0 (senza, il
`SET NOT NULL` del backfill avrebbe rotto la creazione pratiche).

---

### Trigger associato

| Trigger | Timing | Evento | Tabella |
|---|---|---|---|
| `trg_pratiche_a10_default_definizione_ins` | BEFORE | INSERT | `pratiche.pratiche` |

Fase `_a10_` con descrizione `default` — gira prima dei guard della tabella.

---

### Regole

* Interviene **solo** quando `NEW.definizione_id IS NULL`; un pin esplicito passa
  intatto (coerenza tipo garantita dalla FK composita). I guard su scope/stato del pin
  esplicito e l'**immutabilità del pin** (no UPDATE) arrivano con la Fase 1.
* Risoluzione fallita (tipo senza alcuna PUBBLICATA — caso anomalo) → errore parlante
  `DEFINIZIONE_NON_TROVATA` (507), la pratica non nasce.

---

### Note operative

* Introdotta con `20260702-24` (brief-db-step-dominio-e-definizioni-versionate,
  Parte 2 / Fase 0, raffinamento §2.1 punto 1 — fix del bug di sequenza del brief).
* Test: `db/pgtap/pratiche/test-workflow-definizioni-fase0.sql` (caso 3).
