## 📘 Documentazione Trigger Function – `pratiche.trgfn_template_flussi_guard_immutabile`

> 👀 **Vedi anche**
>
Funzioni collegate:
>
[pratiche.fn_check_definizione_congelata](fn_check_definizione_congelata.md)
> [pratiche.trgfn_template_flussi_figli_guard_immutabile](trgfn_template_flussi_figli_guard_immutabile.md)
> [pratiche.trgfn_workflow_definizioni_guard](trgfn_workflow_definizioni_guard.md)
>
Tabelle:
>
[pratiche.template_flussi](template_flussi.md)

---
### 🎯 Scopo Principale

**Immutabilità strutturale «Leggera»** dei template su un'edizione forkata
**pubblicata** (congelata, vedi
[fn_check_definizione_congelata](fn_check_definizione_congelata.md)). Chiude la
domanda aperta #3 del brief design con la strategia «Leggera» (decisa 2026-07-03):
solo i **fork** si congelano alla pubblicazione, il **preset** resta editabile.

| Operazione | Su edizione congelata (fork PUBBLICATA) | Errore |
|---|---|---|
| **INSERT** | sempre vietato (aggiungere uno step a un'edizione emessa) | `TEMPLATE_DEFINIZIONE_CONGELATA` (514) |
| **DELETE** | sempre vietato (rimuovere uno step) | `TEMPLATE_DEFINIZIONE_CONGELATA` (514) |
| **UPDATE** | vietato se cambia una colonna **diversa da `descrizione`** | `TEMPLATE_DEFINIZIONE_CONGELATA` (514) |

`descrizione` è l'**unico campo display correggibile a caldo** (contratto C4). Il
preset (`emittente_fiscale_id NULL`) e le edizioni `BOZZA`/`RITIRATA` non sono
congelati → INSERT/UPDATE/DELETE liberi.

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
  **o** di destinazione è congelata, il cambio ricade nel diff → bloccato (non si
  sposta uno step dentro/fuori un'edizione congelata).
* La verità "congelata" è centralizzata in
  [fn_check_definizione_congelata](fn_check_definizione_congelata.md): questo guard
  non ripete la regola `PUBBLICATA + emittente NOT NULL`.

---

### Note operative

* **Complementare** al guard di Fase 1
  [trgfn_workflow_definizioni_guard](trgfn_workflow_definizioni_guard.md) (blindava
  header e transizioni della definizione): qui si blinda la **struttura** (i template).
* Per modificare un fork emesso → nuova versione:
  [fn_nuova_versione_definizione](fn_nuova_versione_definizione.md) → BOZZA → modifica →
  [fn_pubblica_definizione](fn_pubblica_definizione.md) (ritira la precedente); le
  pratiche in volo restano pinnate (V6).
* **Teardown**: un fork pubblicato non è smantellabile finché resta `PUBBLICATA` (il
  guard blocca anche i DELETE) → va prima `RITIRATA`. Vale per manutenzione e per il
  cleanup pgTAP.
* Introdotto con `20260703-11` (Parte 2 / Fase 2b, D2-9).
* Test: `db/pgtap/pratiche/test-workflow-definizioni-fase2b.sql` (casi 5–8, 12–14).

---
{% include-markdown "signature-core.md" %}
