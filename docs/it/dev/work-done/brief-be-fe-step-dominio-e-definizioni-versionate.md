# Brief BE/FE — Consumi motore pratiche: step `DOMINIO` + definizioni versionate

> **✅ CHIUSO (2026-07-04)** — Parte 1 (step `DOMINIO`) + Fase 0/1 + Fase 2 Slice 1a/1b
> (admin edizioni) + Slice 2 anelli 1-3 (dettaglio lettura + editing step BOZZA) fatti,
> test verdi, E2E validato in-app. **Residuo (nuovo brief quando si parte)**: Slice 2
> anelli 4/5 (write figli per-nodo + archi), FE-2.4 banner drift operatore, Fase 3 editor
> UI (cantiere V4/V5). API BE documentate in
> [api_definizioni_workflow](../../backend/pratiche/manual/api_definizioni_workflow.md).
>
> **Per**: team backend (`dev/backend-tid`) e frontend. · **Da**: backend/frontend agent
> (analisi congiunta 2026-07-02). · **Data**: 2026-07-02.
> **Companion DB** (fonte delle decisioni di modello):
> [brief-db-step-dominio-e-definizioni-versionate.md](brief-db-step-dominio-e-definizioni-versionate.md).
> Le sezioni marcate **lockstep** vanno rilasciate insieme al deliverable DB indicato.

---

## Parte 1 — Step a esito di dominio (`modalita_esito = 'DOMINIO'`) — **lockstep con DB Parte 1**

Il DB introduce il valore `DOMINIO` su `template_flussi.modalita_esito` e il guard runtime
`FLUSSI_ESITO_NON_AMMESSO` (id 504): al completamento, step DOMINIO ⇒ esito con
`is_verdetto = false`; step non-DOMINIO ⇒ verdetto. SMISTAMENTO (9012) passa a DOMINIO via
seed. Il BE deve consumare il nuovo valore in 3 punti + test; il FE in 1 punto.

### BE-1.1 Marker errore DB → ServiceError parlante

`backend/apps/pratiche/services/pratiche_service.py`, tupla `_KNOWN_DB_ERROR_MARKERS`
(righe 31–73): aggiungere l'entry — sottostringa stabile concordata col catalogo DB
(messaggio: `Esito %s non ammesso per lo step %s: richiesto un esito di %s.`):

```python
("FLUSSI_ESITO_NON_AMMESSO", "non ammesso per lo step"),
```

I percorsi `completa_flusso` / `avvia_e_completa_flusso` / `cambia_stato_flusso` passano già
da `_raise_known_db_error` → nessun altro cablaggio.

### BE-1.2 `avvia_flusso`: escludere DOMINIO dall'auto-completamento

`pratiche_service.py` righe 544–551 — condizione attuale:

```python
if result is not None or modalita == "AUTOMATICO":
    repo.update_stato_flusso(flusso_id, "COMPLETATO", esito=auto_esito)
```

Bug latente: uno step DOMINIO con handler di avvio che restituisce un risultato verrebbe
auto-completato con `auto_esito = esito_default or "POSITIVO"` → per DOMINIO
`esito_default` è NULL (guard DB Inv3) → scriverebbe `POSITIVO` → oggi passerebbe, col
guard DB esploderebbe a runtime. Fix (fail-safe prima del DB):

```python
if modalita != "DOMINIO" and (result is not None or modalita == "AUTOMATICO"):
```

Uno step DOMINIO su `avvia_flusso` si limita quindi a `IN_CORSO` (come MANUALE); il
completamento arriva solo dal BB di dominio (`completa_step_pratica`).

### BE-1.3 Pre-guard sul percorso operatore (errore parlante prima del DB)

`ApiPraticaFlussoStato.post` (`backend/apps/pratiche/api/views.py`, ramo
`nuovo_stato == "COMPLETATO"`, righe 441–480): oggi chiama solo
`require_esito_selezionabile_operatore` (blocca gli esiti di ramo scelti a mano, **non** i
verdetti su step DOMINIO). Aggiungere un guard service simmetrico, chiamato dalla view
accanto a quello esistente:

```python
# pratiche_service.py — Scopo: vieta il completamento manuale di uno step il cui
# esito e' calcolato dal dominio (modalita_esito = DOMINIO).
def require_completamento_operatore_ammesso(flusso_id: int, repo: PraticheRepository | None = None) -> None:
    config = (repo or PraticheRepository()).get_flusso_esito_config(flusso_id)
    modalita = config[0] if config else "MANUALE"
    ErrorManager.require(
        modalita != "DOMINIO",
        code="E_FLUSSO_VALIDATION",
        message="Esito calcolato dal dominio: completare lo step con l'azione di dominio dedicata.",
    )
```

⚠️ **NON** metterlo dentro `completa_flusso`/`avvia_e_completa_flusso`: il percorso di
dominio (`completa_step_pratica` ← `vendite.completa_smistamento`) passa da lì e deve
continuare a funzionare (AC DB #2). Il guard vive solo sul percorso operatore (view), come
`require_esito_selezionabile_operatore`. La difesa autoritativa resta il guard DB.

### BE-1.4 Test

- `tests/services/test_pratiche_service_flussi.py`: nuovo caso "avvia_flusso su step DOMINIO
  con handler result → NON completa" (accanto a `test_avvia_flusso_automatico_*`); casi per
  `require_completamento_operatore_ammesso` (DOMINIO → E_FLUSSO_VALIDATION; MANUALE → pass);
  marker 504 → ServiceError con codice giusto (pattern dei test marker esistenti).
- `tests/api/test_flussi_api.py`: POST stato COMPLETATO su flusso DOMINIO → 400 parlante.
- Test smistamento vendite (`test_preventivi_service.py` 490–606): invariati e verdi.

### FE-1.5 `FlussoDrawer.vue`: gate data-driven su `DOMINIO`

Il payload flussi espone già `template_modalita_esito` (repository `_FLUSSO_SELECT` riga
392). Oggi la soppressione del picker dipende **solo** dal registry
(`getDomainCompletion(template_flusso_codice)`). Renderla fail-closed:

- `showEsitoForm` (righe 120–127): aggiungere `&& flusso?.template_modalita_esito !== 'DOMINIO'`
  — così uno step DOMINIO **senza** entry nel registry non mostra mai il picker verdetti
  (oggi lo mostrerebbe, e il DB risponderebbe 504);
- per il caso "DOMINIO senza entry registry": messaggio informativo i18n
  (`pratiche.flusso_esito_dominio_senza_azione`, tipo "L'esito di questo step è calcolato
  dal processo di dominio") al posto del form;
- nessun cambio a `esitiOptions`: il filtro `selezionabile_operatore` (alias BE di
  `is_verdetto`) è già corretto;
- il registry resta keyed per `template_flusso_codice`: **stabile per costruzione** anche
  con le definizioni versionate (il codice è unico per definizione e sopravvive al fork —
  contratto C5 del companion).

### Cosa NON cambia (Parte 1)

`vendite.completa_smistamento` (service, view, URL `/api/v1/vendite/preventivi/<id>/completa-smistamento/`),
`completa_step_pratica`, il registry di dominio FE, il lookup esiti.

---

## Parte 2 — Definizioni workflow versionate

### BE-2.1 Fase 0 (DB: `workflow_definizioni` + backfill) — nessun intervento

Verifiche di non regressione: `get_percorso_pratica` restituisce le stesse righe (una sola
definizione per tipo ≡ oggi); `create_pratica` funziona senza passare `definizione_id`
(auto-pin via trigger DB in Fase 1; in Fase 0 la colonna è backfillata).

### BE-2.2 Fase 1 — percorso definizione-aware — **lockstep con DB Fase 1**

1. **`get_percorso_pratica`** (`backend/apps/pratiche/db/pratiche_repository.py`,
   righe 606–607) — la join oggi è per tipo:

   ```sql
   JOIN pratiche.template_flussi tf
     ON tf.tipo_prestazione_id = p.tipo_prestazione_id AND tf.attivo
   ```

   diventa per definizione pinnata:

   ```sql
   JOIN pratiche.template_flussi tf
     ON tf.definizione_id = p.definizione_id AND tf.attivo
   ```

   È l'**unico** punto BE che seleziona template per tipo (verificato: gli altri 8 usi in
   `pratiche_repository.py` joinano per `template_flusso_id` o tabelle figlie → invariati).
   Da quando esistono due definizioni dello stesso tipo (fork, Fase 2) la join per tipo
   duplicherebbe le righe: il cambio va rilasciato **entro** la Fase 1.
2. **`create_pratica`**: invariato (il pin lo fa il trigger DB). Opzionale: esporre
   `definizione_id`/`versione` nel dettaglio pratica per la UI admin futura.
3. **Marker nuovi codici DB** in `_KNOWN_DB_ERROR_MARKERS`:
   `DEFINIZIONE_NON_TROVATA` → `"Nessuna definizione workflow pubblicata"`;
   `FLUSSI_TEMPLATE_FUORI_DEFINIZIONE` → `"non appartiene alla definizione"`;
   gli altri (509/510/511) servono solo agli endpoint admin di Fase 2.
4. **Lookup generico** `rel=pratiche.template_flussi`: contratto invariato
   (id/codice/descrizione) — nessun intervento.

### BE-2.3 Fase 2 — endpoint admin (cantiere con V4/V5, spec di massima)

Azioni di dominio sottili sulle fn DB (`fn_fork_definizione`, `fn_nuova_versione_definizione`,
`fn_pubblica_definizione`) + lista definizioni con drift (`vw_definizioni_drift`).
Grammatica URL: `POST /api/v1/pratiche/definizioni/<id>/fork/`, `/pubblica/`,
`GET /api/v1/pratiche/definizioni/`. AdminAPIView o azione di processo dedicata — da
decidere nel brief V4/V5; qui solo il vincolo: **nessuna logica di copia/validazione in
Python** (vive nelle fn DB).

### FE-2.4 Fase 0/1: nulla per gli operatori

Il percorso pratica (`PraticaPercorso.vue`) consuma l'API esistente e non cambia contratto.
Fase 2: banner "preset aggiornato" sul pattern DEF-2 (`ui.lista_preset`) nella UI admin
definizioni — cantiere V4/V5, fuori scope qui.

---

## Sequenza

| Step | Chi | Lockstep con |
| --- | --- | --- |
| 1. BE-1.1 … BE-1.4 + FE-1.5 | BE+FE | DB Parte 1 (stesso rilascio: il pre-guard BE senza guard DB lascia il buco; il guard DB senza BE-1.2 può rompere step DOMINIO con handler di avvio) |
| 2. verifica BE-2.1 | BE | DB Fase 0 (nessun codice) |
| 3. BE-2.2 (percorso + marker) | BE | DB Fase 1 |
| 4. BE-2.3 + FE banner drift | BE+FE | DB Fase 2 + cantiere V4/V5 |

---

## Stato attività (aggiornato 2026-07-03)

### Parte 1 — step `DOMINIO` ✅ COMPLETA (BE+FE, test verdi)

- **BE-1.1** ✅ marker `FLUSSI_ESITO_NON_AMMESSO` in `_KNOWN_DB_ERROR_MARKERS`.
- **BE-1.2** ✅ `avvia_flusso` esclude `DOMINIO` dall'auto-completamento (`modalita != "DOMINIO"`).
- **BE-1.3** ✅ `require_completamento_operatore_ammesso` (service) + chiamata in `ApiPraticaFlussoStato.post`.
- **BE-1.4** ✅ test service (avvio DOMINIO non completa; guard operatore; marker 504) + test API (POST COMPLETATO su DOMINIO → 400).
- **FE-1.5** ✅ `FlussoDrawer`: `showEsitoForm` fail-closed su `template_modalita_esito === 'DOMINIO'` + messaggio `flusso_esito_dominio_senza_azione`.

### Parte 2 Fase 0/1 — definizioni versionate ✅ COMPLETA

- **BE-2.1** ✅ verifica non-regressione (percorso invariato con 1 definizione/tipo).
- **BE-2.2** ✅ `get_percorso_pratica` join per `definizione_id` (non più per tipo) + marker
  `DEFINIZIONE_NON_TROVATA` e `FLUSSI_TEMPLATE_FUORI_DEFINIZIONE`. Fix collaterale: `crea_pratica`
  instrada i `DatabaseError` a `_raise_known_db_error` (marker altrimenti morto).
- **Audit fork-aware** ✅ → `brief-db-fork-gap-chiusura-definizione-aware.md` (2 fn per-tipo residue,
  **corrette dal DB**, verificate).

### Parte 2 Fase 2 — admin edizioni 🟡 Slice 1 fatto, resta editing BOZZA (Slice 2)
Gate scelto: **AdminAPIView (super-admin)**. Prerequisiti DB in
`brief-db-accesso-be-definizioni-workflow.md` (P0 lettura + P1 conversione DEFINER) **chiusi**.

- **Slice 1a** ✅ `GET /api/v1/pratiche/definizioni/` (repository+service+view) + FE list-view
  `amministrazione` con stato e banner drift + rotta/nav/i18n. Test verdi.
- **Slice 1b** ✅ `POST …/{fork,nuova-versione,pubblica}/` (AdminAPIView, idempotenti) + FE azioni
  `RowActionsMenu` + dialog fork (scelta emittente). Test verdi. **Verificato**: la conversione
  DEFINER risolve il permesso (il fork supera "permesso negato"); E2E persistito da fare via app.
- **Slice 2** ⏳ editing strutturale di una BOZZA (`template_flussi` + figli scoped a definizione) —
  richiede accesso write ai guard immutabilità (P1 deferito, nessun consumatore finora).
- **Banner drift operatore** (FE-2.4) ⏳ cantiere V4/V5.

*Consumi BE/FE dei due sviluppi DB (step DOMINIO + definizioni versionate). Ogni modifica qui
elencata è puntuale: file, righe e condizioni citati dal codice vivo al 2026-07-02.*
