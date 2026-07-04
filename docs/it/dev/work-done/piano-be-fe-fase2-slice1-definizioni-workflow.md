# Piano BE/FE — Fase 2 Slice 1: admin edizioni workflow (lista + drift + azioni)

> **✅ CHIUSO (2026-07-04)** — Slice 1 completata (lista + drift + azioni fork/nuova-versione/
> pubblica, BE+FE, test verdi, E2E in-app). Proseguita in Slice 2 anelli 1-3 (dettaglio +
> editing step BOZZA). Residuo tracciato nel companion
> `brief-be-fe-step-dominio-e-definizioni-versionate` (anelli 4/5, Fase 3 editor UI).
>
> **Da**: backend/frontend agent · **Data**: 2026-07-03 · **Stato**: 🟡 contratto congelato,
> pronto al via.
> **Dipende da**: (1) decisione owner sul **gate app-layer** (AdminAPIView vs permesso di
> processo) — vedi §4; (2) per le **azioni write**, conversione DB delle 3 fn a
> `SECURITY DEFINER` in lockstep (vedi `brief-db-accesso-be-definizioni-workflow.md` §P1).
> Le **letture sono già sbloccate** (GRANT SELECT fatto) → la parte lista+drift è costruibile
> subito una volta scelto il gate.
> **Companion**: `brief-be-fe-step-dominio-e-definizioni-versionate.md` BE-2.3/FE-2.4.

---

## 1. Perimetro Slice 1

Gestione delle **edizioni** di un workflow (per tipo prestazione, scope emittente): elenco
con stato + drift; azioni di ciclo di vita (fork, nuova versione, pubblica). **NON** include
l'editing strutturale di una BOZZA (step/grafo) → Slice 2.

## 2. Contratto API (BE, sotto `/api/v1/pratiche/definizioni/`)

### 2.1 `GET /` — lista edizioni (READ — già sbloccato)
Query: `tipo_prestazione_id` (opz.), `emittente_fiscale_id` (opz.; assente = tutte, inclusi preset).
Fonte: `pratiche.workflow_definizioni` + LEFT JOIN `pratiche.vw_definizioni_drift`.
Item response:
```json
{
  "id": 7,
  "tipo_prestazione_id": 9004,
  "tipo_prestazione_descrizione": "Pratica preventivi",
  "emittente_fiscale_id": null,
  "emittente_display": "— (preset)",
  "versione": 1,
  "stato": "PUBBLICATA",
  "descrizione": "...",
  "preset_origine_id": null,
  "versione_origine": null,
  "drift": { "versioni_indietro": 0, "preset_corrente_id": 7, "versione_preset_corrente": 1 }
}
```
Envelope standard `{ data, meta }`; ordinamento per `tipo_prestazione_id, emittente_fiscale_id NULLS FIRST, versione DESC`.

### 2.2 Azioni (WRITE — lockstep con conversione DEFINER)
| Endpoint | Body | fn DB | Ritorno |
| --- | --- | --- | --- |
| `POST /<id>/fork/` | `{ emittente_fiscale_id }` | `fn_fork_definizione(id, emittente)` | `{ definizione_id }` (BOZZA) |
| `POST /<id>/nuova-versione/` | — | `fn_nuova_versione_definizione(id)` | `{ definizione_id }` (BOZZA) |
| `POST /<id>/pubblica/` | — | `fn_pubblica_definizione(id)` | `{ definizione_id }` (PUBBLICATA; precedente → RITIRATA) |

- Tutte `Idempotency-Key` (write-once) come da standard.
- Marker `_KNOWN_DB_ERROR_MARKERS`: mappare i codici errore parlanti che le fn sollevano
  (es. guard emittente su fork, definizione congelata su pubblica) — da concordare col DB in
  lockstep (§P1 del brief accesso).

## 3. FE — `amministrazione`
- `DefinizioniWorkflowListView.vue` (dominio `amministrazione`): `<ListaConfigurabile>` o
  DataTable con colonne Tipo · Emittente · Versione · Stato (Tag) · **Drift** (badge
  "preset aggiornato" se `versioni_indietro > 0`, pattern DEF-2 `ui.lista_preset`).
- Azioni riga via `RowActionsMenu`:
  - **Fork** (visibile su una PUBBLICATA preset/emittente) → chiede emittente.
  - **Nuova versione** (visibile su PUBBLICATA) → crea BOZZA.
  - **Pubblica** (visibile su BOZZA) → conferma.
- api client + store Pinia (`userScoped: true`).

## 4. Decisione aperta — gate app-layer
- **AdminAPIView (SUPER_ADMIN)** — *raccomandato Slice 1*: zero permessi nuovi, coerente col
  dominio amministrazione; reversibile.
- **Permesso di processo dedicato** (`DomainAPIView` + codename, es. `gestisci_definizioni_workflow`):
  necessario se un **admin d'emittente** deve gestire in self-service la **sua** edizione.
- La scelta determina la base view BE e il gating FE; **non** cambia il contratto endpoint.
  Innesca il lockstep con la conversione DEFINER delle 3 azioni.

## 5. Ordine di rilascio
1. **1a (subito, su gate scelto)**: `GET /` + list-view + drift. Read-only, letture già aperte.
2. **1b (lockstep DB)**: 3 azioni write + conversione fn a `SECURITY DEFINER`+`search_path`
   (strada B) rilasciate insieme al gate.
3. Slice 2 (separato): editing strutturale BOZZA.
