## 📘 Documentazione Trigger Function – `pratiche.trgfn_tipi_prestazione_bootstrap_definizione`

> 👀 **Vedi anche**
>
Funzioni collegate:
>
[pratiche.fn_risolvi_definizione](fn_risolvi_definizione.md)
>
Tabelle:
>
[pratiche.workflow_definizioni](workflow_definizioni.md)
> [pratiche.tipi_prestazione](tipi_prestazione.md)

---
### 🎯 Scopo Principale

**Bootstrap del preset**: alla creazione di un tipo prestazione crea la sua definizione
workflow **preset v1 PUBBLICATA** (emittente NULL). Garantisce l'invariante di Fase 0:

> ogni tipo di prestazione ha **sempre** un preset risolvibile da
> `fn_risolvi_definizione`.

Effetti pratici: su DB fresco i **seed dei tipi generano i preset da soli** (niente
seed CSV a id fissi per `workflow_definizioni`); le fixture pgTAP che creano tipi
sintetici restano invariate; l'auto-default dei template e l'auto-pin delle pratiche
trovano sempre l'edizione.

---

### Trigger associato

| Trigger | Timing | Evento | Tabella |
|---|---|---|---|
| `trg_tipi_prestazione_z90_bootstrap_definizione_ins` | AFTER | INSERT | `pratiche.tipi_prestazione` |

Fase `_z90_` (side-effect finale, non guard).

---

### Regole

* **Idempotente**: `ON CONFLICT` sull'indice unico parziale «una sola PUBBLICATA per
  scope» (`uq_workflow_definizioni_pubblicata`) → `DO NOTHING`.
* Il preset bootstrap nasce **PUBBLICATA e vuoto** (i template arrivano dopo, dai
  seed): è la fotografia della realtà pre-fork, dove il set corrente di template del
  tipo *è* la definizione. La validazione «pubblicabile solo con ≥ 1 template» riguarda
  `fn_pubblica_definizione` (Fase 2), non il bootstrap.
* Propaga `tx_id` dalla riga del tipo.
* Scatta **solo su INSERT**: i tipi esistenti (nati prima del trigger) sono coperti dal
  backfill Fase 0 (`20260702-25`, che copre anche eventuali tipi sintetici residui).

---

### Note operative

* Introdotta con `20260702-22` (brief-db-step-dominio-e-definizioni-versionate,
  Parte 2 / Fase 0, raffinamento §2.1).
* Test: `db/pgtap/pratiche/test-workflow-definizioni-fase0.sql` (caso 1).
