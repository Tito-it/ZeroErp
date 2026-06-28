# Brief DB — Sospensioni pratiche: anti-overlap + guard data manuale

> **Tipo documento**: brief operativo **per il team DB** (canale `dev/db-tid`).
> Spiega *cosa* fare e *perché*; **non contiene DDL pronto** (lo scrive il team
> DB nel changelog liquibase, secondo template e convenzioni del repo).
>
> **Data**: 2026-06-26 · **Stato**: 🔴 **DA FARE**
>
> **Origine**: nuova UI di gestione sospensioni/riattivazioni pratiche con
> **data/ora inserita manualmente** (anche retroattiva). Decisione di prodotto
> (Tid, 2026-06-26): la soluzione dev'essere completa e difesa a DB, niente
> guard solo applicativo.

---

## 1. Contesto

La tabella `pratiche.sospensioni` registra lo storico delle sospensioni a due
livelli (pratica: `flusso_id IS NULL`; flusso: `flusso_id IS NOT NULL`). Oggi il
backend inserisce la sospensione con `data_inizio = NOW()` e la chiude con
`data_fine = NOW()` (INSERT/UPDATE diretti nel repository, nessuna funzione DB).

Stiamo introducendo una UI che consente all'operatore di **specificare data e ora
della sospensione e della riattivazione** (caso d'uso: l'operatore registra a
posteriori una sospensione realmente avvenuta in passato). Questo rende possibili
**date retroattive arbitrarie**.

### Il buco di modello da chiudere

La protezione attuale è insufficiente per le date manuali:

| Difesa esistente | Cosa copre | Cosa NON copre |
|---|---|---|
| `uq_sospensioni_attiva_pratica` (unique parziale `WHERE data_fine IS NULL AND flusso_id IS NULL`) | Due sospensioni **attive** contemporanee a livello pratica | Sovrapposizione tra periodi **storici** (chiusi) o tra una nuova retroattiva e una già chiusa |
| `uq_sospensioni_attiva_flusso` (analoga a livello flusso) | Idem a livello flusso | Idem |
| `chk_sospensioni_data_fine` (`data_fine IS NULL OR data_fine > data_inizio`) | Coerenza interna del singolo intervallo | Sovrapposizioni tra intervalli diversi; date nel futuro |
| `trgfn_sospensioni_set_periodo` | Mantiene `periodo_sospensione tstzrange` da `data_inizio`/`data_fine` | Niente: è solo derivazione, non un vincolo |

Con date libere si può creare una sospensione il cui periodo **si sovrappone** a
una sospensione già chiusa dello stesso scope → stato logicamente incoerente
(la pratica risulterebbe "sospesa due volte" nello stesso istante). La colonna
`periodo_sospensione tstzrange` esiste proprio per supportare il check via
operatori di range, ma **nessun vincolo la usa per impedire l'overlap**.

---

## 2. Cosa serve dal DB

### 2.1 Vincolo anti-overlap (EXCLUDE GiST) — priorità ALTA

Impedire che due righe dello **stesso scope** abbiano `periodo_sospensione`
sovrapposti.

- Scope = stessa pratica per le sospensioni di pratica (`flusso_id IS NULL`);
  stessa coppia (pratica, flusso) per le sospensioni di flusso.
- Tecnicamente: `EXCLUDE USING gist (... WITH =, periodo_sospensione WITH &&)`.
  Richiede l'estensione **`btree_gist`** per l'operatore `=` sulle colonne id.
- Suggerimento implementativo (a discrezione del team DB): due vincoli/indici
  EXCLUDE **parziali** speculari ai due unique esistenti — uno
  `WHERE flusso_id IS NULL` su `pratica_id`, uno `WHERE flusso_id IS NOT NULL`
  su `(pratica_id, flusso_id)` — così il livello pratica e il livello flusso
  non interferiscono tra loro. In alternativa un solo EXCLUDE con
  `COALESCE(flusso_id, 0)` nello scope. Scelta lasciata al team DB.
- Verificare che `periodo_sospensione` con `data_fine NULL` (bound a `infinity`)
  rientri correttamente nell'EXCLUDE: una sospensione aperta deve risultare
  sovrapposta a qualunque periodo successivo dello stesso scope.

**Codice errore**: nuovo `E_SOSPENSIONE_OVERLAP` → HTTP **409** (suffisso
`_OVERLAP`/conflitto). Registrare in `config.messaggi_errore` + mappare in
`apps/core/services/error_policies.py` (lo faccio io lato BE una volta noto il
nome definitivo). Messaggio business-safe tipo "Esiste già una sospensione che
copre questo periodo per la pratica/flusso."

### 2.2 Guard data nel futuro — priorità ALTA

Una sospensione non può **iniziare** né **finire** nel futuro (non si può
sospendere qualcosa "da domani" con questa azione; la pianificazione è un altro
concetto, vedi 2.3).

- Guard BEFORE INSERT/UPDATE (fase `_a10_`) che rifiuta `data_inizio > now()` e
  `data_fine > now()`. Tolleranza di clock skew a discrezione del team DB (es.
  qualche minuto), oppure nessuna.
- **Codice errore**: `E_SOSPENSIONE_DATA_FUTURA` → HTTP **422**.

### 2.3 Cosa NON cambiare

- `data_riattivazione_prevista` (tipo `date`) **resta libera nel futuro**: è una
  *previsione*, non il timestamp effettivo. Il guard 2.2 non la tocca.
- `chk_sospensioni_data_fine` resta com'è (già garantisce `data_fine >
  data_inizio`): nessuna modifica.
- La derivazione `periodo_sospensione` (`trgfn_sospensioni_set_periodo`) resta
  invariata: i nuovi vincoli si appoggiano alla colonna già mantenuta.

---

## 3. Lato backend (lo faccio io dopo l'OK DB — qui solo per contesto)

Non è lavoro del team DB, ma spiega perché servono i vincoli sopra:

- `pratiche_repository.create_sospensione`: `data_inizio` diventa parametro
  (default `NOW()` se non passato) invece di `NOW()` hardcoded.
- `pratiche_repository.chiudi_sospensione`: `data_fine` diventa parametro.
- `pratiche_service.sospendi_pratica` / `riattiva_pratica`: accettano e validano
  `data_inizio` / `data_fine` ISO; mappano gli errori DB
  (`E_SOSPENSIONE_OVERLAP`, `E_SOSPENSIONE_DATA_FUTURA`) sul codice/HTTP.
- API `sospendi/` e `riattiva/`: nuovi campi opzionali nel payload.

La validazione applicativa è **difesa in profondità**, non sostituisce i vincoli
DB (DB-first): il DB resta l'autorità.

---

## 4. Test attesi (pgTAP)

- INSERT sospensione che si sovrappone a una già chiusa stesso scope → errore
  `E_SOSPENSIONE_OVERLAP`.
- INSERT sospensione di **flusso** sovrapposta a una di **pratica** stesso
  periodo → **ammessa** (scope diversi: sono due assi indipendenti) — confermare
  che questo è il comportamento voluto con Tid se in dubbio.
- INSERT con `data_inizio` futura → `E_SOSPENSIONE_DATA_FUTURA`.
- UPDATE `data_fine` futura → `E_SOSPENSIONE_DATA_FUTURA`.
- INSERT due sospensioni storiche **non** sovrapposte stesso scope → ok.
- `data_riattivazione_prevista` futura → ok (non bloccata).

---

## 5. Aperto / da confermare con Tid

- **Modifica di righe storiche**: la UI v1 non prevede edit/delete di sospensioni
  già registrate (solo crea sospensione + chiudi/riattiva). Se in futuro
  serviranno correzioni a posteriori, i vincoli 2.1/2.2 le copriranno comunque.
- **Overlap cross-livello** (pratica vs flusso sullo stesso istante): assunto
  **ammesso** (assi indipendenti). Confermare.
