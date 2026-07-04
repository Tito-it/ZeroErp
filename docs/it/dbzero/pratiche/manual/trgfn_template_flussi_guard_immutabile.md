## 📘 Documentazione Trigger Function – `pratiche.trgfn_template_flussi_guard_immutabile`

> 👀 **Vedi anche**
>
Funzioni collegate:
>
[pratiche.fn_check_definizione_struttura_bloccata](fn_check_definizione_struttura_bloccata.md)
> [pratiche.fn_check_definizione_congelata](fn_check_definizione_congelata.md)
> [pratiche.trgfn_template_flussi_figli_guard_immutabile](trgfn_template_flussi_figli_guard_immutabile.md)
> [pratiche.trgfn_workflow_definizioni_guard](trgfn_workflow_definizioni_guard.md)
>
Tabelle:
>
[pratiche.template_flussi](template_flussi.md)

---
### 🎯 Scopo Principale

**Immutabilità strutturale «Leggera»** dei template su un'edizione forkata già
emessa. Solo i **fork** si bloccano, il **preset** (emittente NULL) e le **BOZZA**
restano editabili. **Strategia C** (freeze *modifica* ≠ freeze *cancellazione*):

| Operazione | Bloccata quando | Predicato | Errore |
|---|---|---|---|
| **INSERT** | edizione **emessa** (fork PUBBLICATA **o RITIRATA**) | [`struttura_bloccata`](fn_check_definizione_struttura_bloccata.md) | `TEMPLATE_DEFINIZIONE_CONGELATA` (514) |
| **UPDATE** | edizione **emessa** e cambia una colonna **diversa da `descrizione`** | [`struttura_bloccata`](fn_check_definizione_struttura_bloccata.md) | `TEMPLATE_DEFINIZIONE_CONGELATA` (514) |
| **DELETE** | edizione **PUBBLICATA** soltanto (in uso) | [`congelata`](fn_check_definizione_congelata.md) | `TEMPLATE_DEFINIZIONE_CONGELATA` (514) |

Conseguenza: una **RITIRATA-emittente** non è **editabile** (INSERT/UPDATE bloccati:
ha ancora pratiche pinnate alla sua versione) ma resta **cancellabile** (DELETE
consentito, housekeeping). `descrizione` è l'**unico campo display correggibile a
caldo** (contratto C4), su PUBBLICATA e RITIRATA.

---

### Trigger associato

| Trigger | Timing | Evento | Tabella |
|---|---|---|---|
| `trg_template_flussi_a10_guard_immutabile_iud` | BEFORE | INSERT OR UPDATE OR DELETE | `pratiche.template_flussi` |

Ordine `_a10_`: `default_definizione` (risolve `NEW.definizione_id` su INSERT) fira
**prima**; `guard_immutabile` fira prima di `guard_modalita_esito`, `audit`,
`gen_tx_id`, `z90_storico`.

---

### Regole

* **UPDATE robusto ai nuovi campi**: il confronto è su `to_jsonb(NEW/OLD)` meno una
  **allowlist esplicita** (`descrizione` + audit tecnici `tx_id`, `data_/user_insert`,
  `data_/user_update`). Conseguenza fail-safe: una **futura colonna strutturale** è
  congelata **di default**; una futura colonna display va aggiunta esplicitamente
  all'allowlist.
* **Re-parent** (`definizione_id` cambiato in UPDATE): se la definizione di partenza
  **o** di destinazione è struttura-bloccata, il cambio ricade nel diff → bloccato
  (non si sposta uno step dentro/fuori un'edizione emessa).
* Le due verità sono centralizzate nei predicati puri
  [fn_check_definizione_struttura_bloccata](fn_check_definizione_struttura_bloccata.md)
  (INSERT/UPDATE, PUBBLICATA o RITIRATA) e
  [fn_check_definizione_congelata](fn_check_definizione_congelata.md) (DELETE,
  PUBBLICATA): questo guard non ripete le regole `stato`/`emittente`.

---

### Note operative

* **Complementare** al guard di Fase 1
  [trgfn_workflow_definizioni_guard](trgfn_workflow_definizioni_guard.md) (blindava
  header e transizioni della definizione): qui si blinda la **struttura** (i template).
* Per modificare un fork emesso → nuova versione:
  [fn_nuova_versione_definizione](fn_nuova_versione_definizione.md) → BOZZA → modifica →
  [fn_pubblica_definizione](fn_pubblica_definizione.md) (ritira la precedente); le
  pratiche in volo restano pinnate (V6).
* **Teardown**: un fork **PUBBLICATO** non è smantellabile (il guard blocca il DELETE)
  → va prima `RITIRATA` (`PUBBLICATA→RITIRATA` via
  [trgfn_workflow_definizioni_guard](trgfn_workflow_definizioni_guard.md)); da RITIRATA
  i template/figli sono cancellabili (strategia C). Vale per manutenzione e cleanup pgTAP.
* Introdotto con `20260703-11` (Fase 2b, D2-9); **strategia C** (freeze modifica ≠
  cancellazione, RITIRATA editabile=no/cancellabile=sì) con `20260704-03`.
* Test: `db/pgtap/pratiche/test-workflow-definizioni-fase2b.sql` (PUBBLICATA, casi 5–8, 12–14)
  e `test-definizione-ritirata-edit-freeze.sql` (RITIRATA: edit bloccato, delete consentito).

---
{% include-markdown "signature-core.md" %}
