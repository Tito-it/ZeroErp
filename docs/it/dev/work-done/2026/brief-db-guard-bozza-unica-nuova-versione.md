# Brief DB — Definizioni workflow: `nuova-versione` guarda lo stato sorgente + invariante «≤1 BOZZA per scope»

> **✅ RISOLTO (2026-07-04)** dal team DB (`test-definizione-bozza-unica.sql`) — **soluzione
> completa adottata**: indice parziale `uq_workflow_definizioni_bozza (tipo, emittente) WHERE
> stato='BOZZA'` (NULLS NOT DISTINCT); guard fail-fast in `fn_fork_definizione`
> (`DEFINIZIONE_BOZZA_ESISTENTE`) e `fn_nuova_versione_definizione` (`DEFINIZIONE_NO_PUBBLICATA`
> se la sorgente non è PUBBLICATA + `DEFINIZIONE_BOZZA_ESISTENTE` per l'invariante). **BE
> allineato**: marker `DEFINIZIONE_BOZZA_ESISTENTE` (`"una bozza di edizione workflow"`) +
> `DEFINIZIONE_NO_PUBBLICATA` (`"Nuova versione non ammessa"`) in `_KNOWN_DB_ERROR_MARKERS`
> + 2 test service. **Validato E2E** sul server reale (non-distruttivo): i tre casi (fork con
> BOZZA, nuova-versione da BOZZA, nuova-versione con BOZZA aperta) tornano il marker parlante.
> pgTAP team: `test-definizione-bozza-unica.sql`.
>
> **Per**: team DB (`dev/db-tid`). · **Da**: backend/frontend agent. · **Priorità**: 🟠 MEDIA
> (rifinitura di modello emersa validando E2E Slice 1b: nessuna rottura in produzione — non
> siamo in produzione — ma un bug logico del ciclo di vita). · **Data**: 2026-07-04.
> **Origine**: smoke E2E lifecycle edizioni (fork→pubblica→nuova-versione→pubblica) contro
> il server reale; osservata proliferazione di BOZZE parallele nello stesso scope.
> **Correlato**: `brief-db-step-dominio-e-definizioni-versionate.md` (Parte 2, fn ciclo di
> vita); `brief-design-workflow-definizioni-versionate.md` (design-of-record); fn
> `fn_nuova_versione_definizione` / `fn_fork_definizione` / `fn_copia_definizione`.

---

## Contesto

Le edizioni di workflow versionate hanno il ciclo `BOZZA` (editabile) → `PUBBLICATA`
(istanziabile, **unica per scope** = `tipo_prestazione + emittente`) → `RITIRATA`. Le tre
fn di ciclo di vita sono ora esposte dal BE (Slice 1b, `SECURITY DEFINER`, E2E verde).

L'unicità è garantita **solo sulla PUBBLICATA** (indice parziale
`uq_workflow_definizioni_pubblicata (tipo, emittente) WHERE stato='PUBBLICATA'`). **Non
esiste alcun vincolo sul numero di BOZZE per scope.**

## Problema — 🟠 bug logico del ciclo di vita

Validando l'E2E ho osservato due incoerenze, entrambe riconducibili all'assenza
dell'invariante «una sola edizione in lavorazione (BOZZA) per scope»:

1. **`fn_nuova_versione_definizione` non guarda lo stato della sorgente.** Legge solo
   `emittente_fiscale_id` della `p_definizione_id` e chiama
   `fn_copia_definizione(source, emittente, false)`. Passandole una **BOZZA** come
   sorgente, crea una **seconda BOZZA** dello stesso scope (osservato: `nuova-versione(414
   BOZZA)` → `415 BOZZA v3`). Semanticamente la fn dovrebbe derivare la nuova versione
   **dalla PUBBLICATA corrente dello scope** («per editare una PUBBLICATA senza toccarla»,
   dal suo stesso COMMENT), non da una bozza arbitraria. Peggio: se lo scope **non ha
   alcuna PUBBLICATA**, "nuova versione" non ha significato eppure oggi riesce.

2. **`fork` + `nuova-versione` possono accumulare BOZZE illimitate** nello stesso scope.
   Ogni chiamata prende `versione = max+1` e inserisce una nuova BOZZA. Due bozze parallele
   sono ambigue: quale rappresenta "la prossima versione"? Entrambe pubblicherebbero
   ritirando la base dell'altra.

> Non è estetica: è il tipo di asimmetria di modello che va chiusa con la simmetria piena
> subito, non rinviata (memoria `feedback_simmetria_modello_no_meta_scope`).

## Cosa serve (accesso/semantica, non implementazione specifica)

L'invariante di dominio da rendere vero: **al più una BOZZA per scope
(`tipo_prestazione`, `emittente`) in ogni istante**, e la nuova versione si deriva **dalla
PUBBLICATA corrente dello scope**. Il *come* è vostra scelta; proposta coerente con lo
stile dei guard esistenti (cfr. i guard stato in `fn_pubblica_definizione`):

* **Vincolo (defense-in-depth)**: indice parziale
  `uq_workflow_definizioni_bozza ON (tipo_prestazione_id, emittente_fiscale_id) WHERE stato='BOZZA'`
  (con `NULLS NOT DISTINCT`, come gli altri unique dello scope), così il preset stesso
  (`emittente NULL`) rientra nell'invariante.
* **Guard fail-fast in `fn_fork_definizione`**: se lo scope destinazione ha già una BOZZA,
  errore parlante (marker dedicato, es. `DEFINIZIONE_BOZZA_ESISTENTE`) invece del
  `unique_violation` grezzo — così il BE lo mappa a un banner pulito, non a `E_DATABASE`.
* **Guard fail-fast in `fn_nuova_versione_definizione`**:
  1. richiede che lo scope abbia una **PUBBLICATA** (altrimenti `DEFINIZIONE_NO_PUBBLICATA`
     — «prima pubblica un'edizione, poi creane una nuova versione»);
  2. richiede che lo scope **non abbia già una BOZZA** (stesso `DEFINIZIONE_BOZZA_ESISTENTE`);
  3. copia sorgente = **la PUBBLICATA corrente dello scope** (non `p_definizione_id` se
     questa non è la PUBBLICATA). In alternativa, imporre che `p_definizione_id` **sia** la
     PUBBLICATA dello scope (guard `stato='PUBBLICATA'`) e rifiutare altrimenti — più
     semplice, stesso effetto.

> Se preferite il solo floor minimo richiesto in review (guard `stato='PUBBLICATA'` sulla
> sorgente di `nuova-versione`), va bene, **ma** senza l'invariante `≤1 BOZZA` resta il buco
> "due `nuova-versione` sulla stessa PUBBLICATA → due BOZZE". Raccomando la soluzione
> completa (memoria `feedback_no_quick_fix_soluzione_assoluta`).

## Nota BE post-fix

I nuovi marker (`DEFINIZIONE_BOZZA_ESISTENTE`, `DEFINIZIONE_NO_PUBBLICATA`) vanno aggiunti a
`pratiche_service._KNOWN_DB_ERROR_MARKERS` perché il BE li traduca in `ServiceError`
parlanti (oggi solo `DEFINIZIONE_NON_PUBBLICABILE` è mappato). Nessun altro cambio di
contratto endpoint.

## Criteri di accettazione

1. `fork` su uno scope che ha già una BOZZA → errore dominio dedicato (non `unique_violation`).
2. `nuova-versione` su uno scope **senza PUBBLICATA** → errore dominio dedicato.
3. `nuova-versione` su uno scope **con una BOZZA già aperta** → errore dominio dedicato.
4. Il flusso pulito resta verde: `fork → pubblica → nuova-versione → pubblica` (v1→RITIRATA,
   v2→PUBBLICATA), con **al più una BOZZA per scope** in ogni istante.
5. pgTAP aggiornato: fixture che tenta la doppia BOZZA (via fork e via nuova-versione) e
   asserisce il rifiuto; fixture nuova-versione senza PUBBLICATA → rifiuto.

## Fuori scope

* Editing strutturale della BOZZA (Slice 2) — vedi
  `brief-db-accesso-write-editing-strutturale-bozza.md`.
* Perimetro dell'immutabilità su PUBBLICATA/RITIRATA (idem, brief Slice 2).
