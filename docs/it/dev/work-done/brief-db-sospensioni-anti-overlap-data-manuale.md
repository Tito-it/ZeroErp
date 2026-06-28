# Brief — Sospensioni pratiche: anti-overlap + guard data manuale

> **Tipo documento**: brief operativo originato per il team DB (canale
> `dev/db-tid`), ora **esteso col piano di sviluppo applicativo BE/FE**.
>
> **Data**: 2026-06-26 · **Stato**: ✅ **COMPLETATO** (DB + BE/FE + smoke E2E manuale
> fatti; test BE verdi, build FE verde)
>
> **Origine**: nuova UI di gestione sospensioni/riattivazioni pratiche con
> **data/ora inserita manualmente** (anche retroattiva). Decisione di prodotto
> (Tid, 2026-06-26): la soluzione dev'essere completa e difesa a DB, niente
> guard solo applicativo.

---

## 0. Stato e roadmap del cantiere

| Fase | Cosa | Stato |
|---|---|---|
| **DB** | EXCLUDE `ex_sospensioni_no_overlap` (framework `dbops.automazione_overlap`, scope `(pratica_id, COALESCE(flusso_id,-1))`, totale) + trigger `a10` `trgfn_sospensioni_guard_data_non_futura` (tolleranza 2 min) + codici `E_SOSPENSIONE_OVERLAP` (498) / `E_SOSPENSIONE_DATA_FUTURA` (499) + pgTAP | ✅ **FATTO** — vedi [brief-db-…_db.md](brief-db-sospensioni-anti-overlap-data-manuale_db.md) |
| **FE-1** | Tab "Sospensioni" di sola visualizzazione (storico) tra Allegati e Giornale | ✅ **FATTO** (no dipendenza DB) — `PraticaSospensioniTab.vue` |
| **BE** | Parametrizzazione date + mapping errori DB + API + test (253 verdi) | ✅ **FATTO** (§6.A) |
| **FE-2** | `SospensionePraticaDialog` (AppDialog) condiviso + wiring pulsanti Sospendi/Riattiva + refresh tab + i18n | ✅ **FATTO** (§6.B) |
| **Smoke** | E2E manuale: retroattiva ok / overlap 409 / data futura 422 | ✅ **FATTO** (§6.C) |

> ⚠️ Rispetto all'ipotesi iniziale di questo brief, il team DB ha cambiato due
> cose (vedi brief `_db`): l'anti-overlap è un **EXCLUDE unico via framework**
> (non due parziali speculari) e la violazione è un **native `23P01`** (non un
> raise custom) → il BE la mappa per **nome constraint**, come `ex_contratti_no_overlap`.

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

> **NB**: le sezioni §1–§2 sopra documentano i requisiti DB originali. La sezione
> §6 sotto è il **piano di sviluppo applicativo reale** (approvato Tid 2026-06-26)
> che sostituisce la vecchia bozza "lato backend". I vincoli DB descritti sono già
> implementati (vedi §0 + brief `_db`).

---

## 6. Piano di sviluppo applicativo BE/FE (approvato — IN CORSO)

### 6.A Backend

**1. Repository** [`pratiche_repository.py`](../../../../backend/apps/pratiche/db/pratiche_repository.py)
— parametrizzare le date (oggi `NOW()` hardcoded), default `None` retro-compatibile:
- `create_sospensione(..., data_inizio: str | None = None)` →
  `VALUES (..., COALESCE(%s::timestamptz, NOW()), ...)`.
- `chiudi_sospensione(sospensione_id, data_fine: str | None = None)` →
  `SET data_fine = COALESCE(%s::timestamptz, NOW())`.

**2. Service** [`pratiche_service.py`](../../../../backend/apps/pratiche/services/pratiche_service.py):
- `sospendi_pratica(..., data_inizio=None)` e `riattiva_pratica(..., data_fine=None)`:
  passano la data al repository.
- **Overlap** = native `23P01 IntegrityError` su `ex_sospensioni_no_overlap` →
  mappato con `map_integrity_error` (mappa `{ "ex_sospensioni_no_overlap":
  (E_SOSPENSIONE_OVERLAP, msg) }`), **stesso pattern di `ex_contratti_no_overlap`**.
- **Data futura** = `DatabaseError` dal trigger `a10` → nuovo marker in
  `_KNOWN_DB_ERROR_MARKERS` (`"non puo' essere nel futuro"` →
  `E_SOSPENSIONE_DATA_FUTURA`), riusa `_raise_known_db_error` esistente.

**3. error_policies** [`error_policies.py`](../../../../backend/apps/core/services/error_policies.py)
— registrare `E_SOSPENSIONE_OVERLAP` (409) e `E_SOSPENSIONE_DATA_FUTURA` (422) + UI action.

**4. Views** [`views.py`](../../../../backend/apps/pratiche/api/views.py) —
`ApiPraticaSospendi`/`ApiPraticaRiattiva`: campi opzionali `data_inizio`/`data_fine`
nel payload + `inline_serializer`/`@extend_schema`.

**5. Test service** (`apps/pratiche/tests/services/`): overlap→409, data_futura→422,
passthrough date, default `NOW()` invariato (mock `IntegrityError`/`DatabaseError`
come i test contratti).

### 6.B Frontend

**6. `SospensionePraticaDialog.vue`** (nuovo, `pratiche/components/`, su **AppDialog**)
— dialog condiviso precaricato con data/ora attuale:
- modo **sospendi**: `motivo` (Textarea), `data_inizio` (DatePicker `showTime`,
  default adesso), `data_riattivazione_prevista` (DatePicker data, opz.);
- modo **riattiva**: `data_fine` (DatePicker `showTime`, default adesso);
- `@saved` → `store.sospendi`/`store.riattiva` con payload ISO.

**7. [`PraticaDrawer.vue`](../../../../frontend/src/pratiche/components/PraticaDrawer.vue)**
— i pulsanti **Sospendi/Riattiva** della `DrawerActionsBar` **aprono il dialog**
(non più chiamata diretta con `NOW()`); su `@saved` ricarica dettaglio + rinfresca tab.

**8. [`PraticaSospensioniTab.vue`](../../../../frontend/src/pratiche/components/PraticaSospensioniTab.vue)**
— refresh della lista dopo un'azione (key/metodo esposto), storico subito aggiornato.

**9. i18n** it/en — etichette dialog + validazioni.

### 6.C Smoke manuale finale
Sospendi con data retroattiva → ok; riattiva → ok; tentativo overlap → **409**;
tentativo data futura → **422**; `data_riattivazione_prevista` futura → ok.

---

## 7. Decisioni chiuse / fuori scope

- **Overlap cross-livello** (pratica vs flusso): **ammesso** by-design (assi
  indipendenti). Chiuso col team DB (brief `_db` §6.1).
- **Warning ridondanza pratica↔flusso**: avviso UX non bloccante quando si sospende
  un flusso già coperto da una sospensione di pratica. Riguarda la UI **flusso**,
  non questo dialog pratica-level → **follow-up applicativo separato** (brief `_db` §7).
- **Modifica di righe storiche** (edit/delete sospensioni): **non in v1**. I vincoli
  DB le validano comunque; richiederebbe trigger AFTER UPDATE "correction-aware".

---

## Appendice — Test pgTAP attesi (storico, già implementati dal team DB)

- INSERT sovrapposta a chiusa stesso scope → `23P01` (`E_SOSPENSIONE_OVERLAP`).
- INSERT flusso sovrapposta a pratica stesso periodo → ammessa (assi indipendenti).
- `data_inizio`/`data_fine` futura → `E_SOSPENSIONE_DATA_FUTURA`.
- storiche non sovrapposte → ok; `data_riattivazione_prevista` futura → ok.
