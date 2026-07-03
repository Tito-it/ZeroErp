## 📘 Documentazione Trigger Function – `pratiche.trgfn_workflow_definizioni_guard`

> 👀 **Vedi anche**
>
Funzioni collegate:
>
[pratiche.trgfn_pratiche_guard_pin_immutabile](trgfn_pratiche_guard_pin_immutabile.md)
> [pratiche.trgfn_flussi_guard_definizione](trgfn_flussi_guard_definizione.md)
>
Tabelle:
>
[pratiche.workflow_definizioni](workflow_definizioni.md)

---
### 🎯 Scopo Principale

Guard del **ciclo di vita dell'edizione di workflow**. Due invarianti a config-time
sulla riga di `pratiche.workflow_definizioni`:

| Inv | Regola | Errore |
|---|---|---|
| **A — transizioni** | cambio di stato ammesso solo `BOZZA→PUBBLICATA` e `PUBBLICATA→RITIRATA` | `DEFINIZIONE_TRANSIZIONE_NON_AMMESSA` (510) |
| **B — header immutabile** | se lo stato di partenza non è `BOZZA`, i campi strutturali (`tipo_prestazione_id`, `emittente_fiscale_id`, `versione`, `preset_origine_id`, `versione_origine`) sono immutabili | `DEFINIZIONE_PUBBLICATA_IMMUTABILE` (509) |

Ogni altro cambio di stato è vietato (`BOZZA→RITIRATA`, `PUBBLICATA→BOZZA`,
`RITIRATA→*`). Una BOZZA da scartare si **cancella** (DELETE), non si ritira.

---

### Trigger associato

| Trigger | Timing | Evento | Tabella |
|---|---|---|---|
| `trg_workflow_definizioni_a10_guard_upd` | BEFORE | UPDATE OF `stato`, `tipo_prestazione_id`, `emittente_fiscale_id`, `versione`, `preset_origine_id`, `versione_origine` | `pratiche.workflow_definizioni` |

---

### Regole

* `descrizione` e `meta` **non** sono nell'evento `UPDATE OF` → restano correggibili
  sempre, anche su PUBBLICATA (contratto C4 "display correggibile"). Un UPDATE che tocca
  solo quelle non fa nemmeno scattare il trigger.
* L'**INSERT non è vincolato**: bootstrap e backfill creano righe già `PUBBLICATA`
  direttamente (coerente con la convenzione "matrice transizioni solo su UPDATE",
  `linee-guida-sql §7c`).

---

### Note operative

* **Perimetro Fase 1**: qui si blindano **solo header e transizioni** della definizione.
  L'immutabilità **strutturale dei template** su PUBBLICATA (no INSERT/UPDATE/DELETE di
  `template_flussi` + figli) è **rinviata alla Fase 2**, strategia **«Leggera»** (decisa
  2026-07-03): il preset resta editabile da seed CSV; si congelano solo le edizioni
  forkate. Motivo del rinvio: in Fase 1 il preset v1 è PUBBLICATA e i seed CSV scrivono i
  template proprio lì.
* In Fase 2 `fn_pubblica_definizione` userà queste transizioni (BOZZA→PUBBLICATA sulla
  nuova, PUBBLICATA→RITIRATA sulla precedente, in transazione).
* Introdotto con `20260703-03` (Parte 2 / Fase 1, D2-9a).
* Test: `db/pgtap/pratiche/test-workflow-definizioni-fase1.sql` (casi 5a–5e).
