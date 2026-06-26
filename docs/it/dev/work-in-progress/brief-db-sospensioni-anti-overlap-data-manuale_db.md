# Brief DB — Sospensioni pratiche: anti-overlap + guard data manuale

> **Branch**: `dev/db-tid`. **Destinatario**: team DB.
> **Natura**: brief di **logica e requisiti**, NON specifica implementativa. Qui c'è
> *cosa* serve e *perché*; la **strada** (firme, nomi changeset, numerazione NN,
> tolleranze) la sceglie il team DB secondo template e convenzioni del repo.
> **Origine**: nuova UI di gestione sospensioni/riattivazioni pratiche con
> **data/ora inserita manualmente** (anche retroattiva). Decisione di prodotto
> (Tid, 2026-06-26): soluzione completa e difesa a DB, niente guard solo applicativo.
> **Vincolo**: ZeroErp NON in produzione → breaking change ammessi.
> **Data**: 2026-06-26 · **Stato**: ✅ **FATTO** (DB applicato, pgTAP verdi — 2026-06-26)
> **Scope**: solo DB. Il backend (parametrizzazione date, mappatura errori) è
> follow-up fuori da questo brief (vedi §3 lato BE e §7).

---

## 0. Sintesi della decisione

La UI consente all'operatore di **specificare data/ora di sospensione e
riattivazione**, anche retroattive (registra a posteriori una sospensione
realmente avvenuta). Questo apre due buchi di modello che le difese attuali NON
coprono e che vanno chiusi **a DB** (DB-first, il DB resta l'autorità):

1. **Anti-overlap storico**: due periodi di sospensione dello **stesso scope** non
   devono potersi sovrapporre, nemmeno tra righe chiuse o tra una retroattiva e una
   già chiusa.
2. **Niente date nel futuro**: una sospensione non può iniziare né finire nel
   futuro (la pianificazione è un altro concetto, vedi §3).

**Punto chiave architetturale**: l'anti-overlap **non si scrive a mano**. Esiste già
il framework dichiarativo `dbops.automazione_overlap` + `fn_apply_automazione_overlap`
(usato da listini, promo, contratti, categorie, template documenti). Lo riusiamo.

---

## 1. Stato attuale (baseline verificata su codice)

Tabella [`pratiche.sospensioni`](../../dbzero/pratiche/tabelle/sospensioni.md), due
livelli: pratica (`flusso_id IS NULL`), flusso (`flusso_id IS NOT NULL`).

**Colonna periodo già presente e mantenuta**:
- `periodo_sospensione tstzrange NOT NULL`, derivata dal trigger BEFORE
  [`trgfn_sospensioni_set_periodo`](../../dbzero/pratiche/funzioni/trgfn_sospensioni_set_periodo.md)
  (fase `a20`): `tstzrange(data_inizio, COALESCE(data_fine,'infinity'), '[)')`.
  Bound **`[)`** confermati; `data_fine NULL` ⇒ aperta a `infinity`.

**Difese esistenti (insufficienti per le date manuali)**:

| Difesa | Copre | NON copre |
|---|---|---|
| `uq_sospensioni_attiva_pratica` (unique parz. `WHERE data_fine IS NULL AND flusso_id IS NULL`) | due sospensioni **attive** stesso livello pratica | overlap tra periodi **storici** o retroattiva↔chiusa |
| `uq_sospensioni_attiva_flusso` (analoga, livello flusso) | idem livello flusso | idem |
| `chk_sospensioni_data_fine` (`data_fine IS NULL OR data_fine > data_inizio`) | coerenza interna del singolo intervallo | sovrapposizioni tra intervalli; date nel futuro |
| `trgfn_sospensioni_set_periodo` | deriva `periodo_sospensione` | niente: è solo derivazione, nessun vincolo la usa |

**Trigger event-based già montati** (rilevanti per §3 "cosa NON cambia"):
- `a10` `trgfn_sospensioni_guard_coerenza_flusso` (BEFORE INS/UPD)
- `a20` `trgfn_sospensioni_set_periodo` (BEFORE INS/UPD)
- `z90` `trgfn_sospensioni_giornale_ins` (AFTER INS), `trgfn_sospensioni_giornale_riattivazione` (AFTER UPD), `trgfn_sospensioni_propaga` (AFTER INS), `trgfn_sospensioni_riattiva` (AFTER UPD)
- `z90` `trgfn_storico_generic('sospensioni_id')` (BEFORE UPD/DEL → storico)

**Framework anti-overlap già esistente** (da riusare):
- [`dbops.automazione_overlap`](../../dbzero/dbops/tabelle/automazione_overlap.md) —
  registro dichiarativo. **PK `(target_schema, target_table)` ⇒ una sola riga per
  tabella.**
- [`dbops.fn_apply_automazione_overlap`](../../dbzero/dbops/funzioni/fn_apply_automazione_overlap.md) —
  genera l'`EXCLUDE USING gist`. Codepath `range_col`: `%I WITH &&` (compatibile
  `tstzrange`). Chiavi = `key_columns` (validate+quotate) + `key_expressions`
  (iniettate as-is). Parziale via `where_predicate` (NULL = totale). Idempotente.
- **`btree_gist` già installato** (baseline `001-01-create-extensions` + ribadito in
  `listini-core`): nessuna `CREATE EXTENSION` da aggiungere.
- ⚠️ Il runner **non è schedulato per OVERLAP** in pipeline: la sola registrazione
  nel registro **non crea** il vincolo. Come per listini/contratti servono **due**
  deliverable (migration esplicita che crea + seed che registra per anti-regressione).

---

## 2. Cosa serve (requisiti)

### 2.1 Vincolo anti-overlap — via framework, EXCLUDE unico con scope `COALESCE`

Impedire due righe dello **stesso scope** con `periodo_sospensione` sovrapposti.
La PK del registro è una-riga-per-tabella ⇒ **niente due parziali speculari**: si usa
un **EXCLUDE unico** con espressione di scope che separa pratica e flusso:

```
target_schema   = 'pratiche'
target_table    = 'sospensioni'
key_columns     = ['pratica_id']
key_expressions = ['COALESCE(flusso_id, -1)']     -- scope: pratica vs flusso indipendenti
range_col       = 'periodo_sospensione'           -- tstzrange già mantenuto
where_predicate = NULL                             -- VINCOLO TOTALE: ogni riga conta (vedi nota)
constraint_name = 'ex_sospensioni_no_overlap'
```

**Perché funziona (semantica)**:
- righe di **pratica** (`flusso_id IS NULL`) → scope `(pratica_id, -1)`;
- righe di **flusso** (`flusso_id > 0`) → scope `(pratica_id, flusso_id)`;
- `-1` non collide mai con un `flusso_id` reale (bigint identity > 0) ⇒ **pratica e
  flusso sono assi indipendenti by-design** (overlap cross-livello ammesso, §5).
- Periodo aperto (`data_fine NULL` → `[data_inizio, infinity)`) rientra
  correttamente nell'`&&`: una sospensione aperta risulta sovrapposta a qualunque
  periodo successivo dello stesso scope.

> **Vincolo TOTALE (`where_predicate = NULL`), non parziale.** Su `sospensioni` ogni
> riga è una sospensione reale e deve contare per l'overlap. Niente filtro: `storicizza`
> accende solo la copia nello schema `storico` (`trgfn_storico_generic`), non indica
> una riga "morta"; e la tabella **non ha** colonna `attivo` (il soft-delete del
> progetto si fa con `attivo`, qui assente). Quindi nessuna riga va esclusa.

**Codice errore**: la violazione è un native **`23P01` exclusion_violation** sul
constraint `ex_sospensioni_no_overlap` (NON un raise custom). Il BE mappa il nome
constraint → `E_SOSPENSIONE_OVERLAP` → HTTP **409**, esattamente come fa già
`ex_contratti_no_overlap` → `E_VENDITE_CONTRATTO_OVERLAP`. Nessun raise lato DB.

### 2.2 Guard data nel futuro — trigger `a10` dedicato

Una sospensione non può **iniziare** né **finire** nel futuro.
- Nuova trigger function `trgfn_sospensioni_guard_data_non_futura`, fase **`a10`**
  (gira prima di `a20 set_periodo`), **BEFORE INSERT OR UPDATE**.
- Rifiuta `NEW.data_inizio > now()` **e** `NEW.data_fine > now()`.
- Tolleranza clock-skew: **finestra di 2 minuti** — rifiuta solo se
  `> now() + interval '2 minutes'` (assorbe lo sfasamento tra orologio client e
  server; una data realmente futura resta bloccata). Decisa con Tid (2026-06-26).
- Raise via `script.fn_log_and_raise_error` con codice registrato (convenzione
  progetto, niente `E_GENERICO`): proposto `SOSPENSIONE_DATA_FUTURA`. Il BE lo mappa
  su HTTP **422**. Registrare il messaggio in `config.messaggi_errore`.

### 2.3 Pre-flight dati esistenti (prima dell'EXCLUDE)

`ADD CONSTRAINT EXCLUDE` **fallisce** se i dati attuali contengono già overlap nello
stesso scope. Col vecchio flusso `NOW()`-based sono improbabili (chiusure sequenziali
nel tempo reale) ma non impossibili (aggiustamenti clock, edit manuali). Prima del
deploy girare una **query di rilevazione** overlap per scope
(`(pratica_id, COALESCE(flusso_id,-1))` con `periodo_sospensione &&`, su **tutte** le
righe — vincolo totale). Se vuota → si procede; altrimenti bonifica preventiva.

---

## 3. Cosa NON cambia

- `data_riattivazione_prevista` (`date`) **resta libera nel futuro**: è una
  *previsione* (riattivazione automatica via pgAgent), non il timestamp effettivo.
  Il guard §2.2 **non la tocca**.
- `chk_sospensioni_data_fine` resta com'è.
- `trgfn_sospensioni_set_periodo` resta invariato: i vincoli nuovi si appoggiano alla
  colonna già mantenuta.
- I trigger event-based `z90` (giornale, propaga, riattiva, storico) **restano
  invariati**. ⚠️ Nota per il futuro (non in questo brief): oggi
  `trgfn_sospensioni_giornale_riattivazione` e `trgfn_sospensioni_riattiva`
  interpretano **ogni UPDATE come riattivazione**. Quando in v2 si aprirà la UI alle
  *correzioni* di righe storiche andranno resi "correction-aware" — **questo brief
  NON tocca quel layer**: i vincoli §2.1/§2.2 sono predicati, non lock di
  immutabilità, e non bloccano né abilitano le correzioni.
- Nessun lock di immutabilità su UPDATE/DELETE: la "non correzione" della UI v1 è
  scelta applicativa, non garanzia DB (lo storico `trgfn_storico_generic` continua a
  versionare ogni UPD/DEL).

---

## 4. Piano di sviluppo (deliverable DB) — ✅ FATTO

Tutti i deliverable realizzati e applicati; pgTAP verdi (2026-06-26). File reali:

1. ✅ **`00_schema/pratiche/20260626-01-alter-sospensioni-add-exclude-no-overlap`** —
   `EXCLUDE ex_sospensioni_no_overlap USING gist (pratica_id WITH =, (COALESCE(flusso_id,-1)) WITH =, periodo_sospensione WITH &&)` — **totale, nessun `WHERE`**.
   Pre-flight §2.3 + btree_gist + idempotenza nelle preCondition (HALT).
2. ✅ **`20_code/pratiche/20260626-02-create-trgfn-sospensioni-guard-data-non-futura`** —
   `trgfn_sospensioni_guard_data_non_futura` (plpgsql, `%TYPE` nella DECLARE) +
   `CREATE TRIGGER trg_sospensioni_a10_guard_data_non_futura_ins_upd` fase `a10`
   BEFORE INSERT OR UPDATE OF data_inizio, data_fine. Tolleranza 2 min. Raise
   `E_SOSPENSIONE_DATA_FUTURA`.
3. ✅ **`config.messaggi_errore`** — codici `E_SOSPENSIONE_OVERLAP` (id 498, BE→409 sul
   native `23P01`) e `E_SOSPENSIONE_DATA_FUTURA` (id 499, BE→422). **Nessun nuovo
   changeset**: le righe sono state aggiunte al CSV `80_data/sql/config/messaggi_errore.csv`
   e ricaricate dai changeset `loadUpdateData` esistenti (`runOnChange: true`).
4. ✅ **`80_data/changelog/20260626-04-insert-automazione-overlap-sospensioni`** —
   UPSERT idempotente in `dbops.automazione_overlap` (`('pratiche','sospensioni')`,
   `key_columns={pratica_id}`, `key_expressions={COALESCE(flusso_id,-1)}`,
   `range_col=periodo_sospensione`, `where_predicate=NULL`, `active=true`).
   Anti-regressione. *(NN 03 lasciato libero: era il changeset messaggi_errore poi
   scartato — vedi punto 3.)*
5. ✅ **`db/pgtap/pratiche/test-sospensioni-anti-overlap-data-futura.sql`** (nuovo file,
   12 test — matrice §5).
6. ✅ **Rigenerazione `changelog-autogen.yaml`** (gitignored, per-ambiente) + doc
   autogen dopo apply. Manuale funzione scritto a mano:
   `docs/it/dbzero/pratiche/manual/trgfn_sospensioni_guard_data_non_futura.md`.

**Ordine di applicazione**: 1 (con pre-flight) → 2 → 4 → 5. Le fasi Liquibase
garantiscono `00_schema`/`20_code` prima di `80_data`.

---

## 5. Test pgTAP (matrice attesa)

Estendere i test sospensioni. Fixture: una pratica con ≥1 flusso (riusare il setup
`TEST_SOSP` esistente). Casi:

**Anti-overlap (`ex_sospensioni_no_overlap`, atteso `23P01`)**
1. INSERT sospensione di **pratica** sovrapposta a una **già chiusa** stesso scope → **`23P01`**.
2. INSERT due sospensioni storiche **non** sovrapposte stesso scope → **ok**.
3. INSERT sospensione sovrapposta a una **aperta** (`data_fine NULL`) stesso scope → **`23P01`**.
4. **Contiguità** `[A,B)` poi `[B,C)` stesso scope (chiudo a B, ri-sospendo a B) → **ammessa** (bound `[)`).
5. INSERT sospensione di **flusso** sovrapposta a una di **pratica** stesso periodo → **ammessa** (scope `COALESCE(flusso_id,-1)` diversi → assi indipendenti).
6. INSERT due sospensioni dello **stesso flusso** sovrapposte → **`23P01`**.
7. INSERT riga con `storicizza=true` sovrapposta a un'altra stesso scope → **`23P01`** (vincolo totale: `storicizza` non esenta).

**Guard data futura (`SOSPENSIONE_DATA_FUTURA`)**
8. INSERT `data_inizio` futura → errore `SOSPENSIONE_DATA_FUTURA`.
9. UPDATE `data_fine` futura → errore `SOSPENSIONE_DATA_FUTURA`.
10. `data_riattivazione_prevista` futura (con date inizio/fine valide) → **ok** (non bloccata).
11. Chiusura normale con `data_fine = now()` → **ok** (non è "futura").

**Anti-regressione framework**
12. Dopo `DROP CONSTRAINT ex_sospensioni_no_overlap` + `dbops.fn_apply_automazione_overlap('SCHEDULED', false)` → il constraint si **ricrea** con scope e predicato identici (test idempotenza/fonte-di-verità).

---

## 6. Domande aperte (da confermare con Tid)

> **CHIUSA — predicato del vincolo**: `where_predicate = NULL` (vincolo **totale**).
> Su `sospensioni` ogni riga conta per l'overlap. `storicizza` accende solo la copia
> nello schema `storico`, non è un soft-delete; il soft-delete del progetto usa
> `attivo`, colonna **assente** qui. Nessuna riga va esclusa (deciso 2026-06-26).
>
> **CHIUSA — tolleranza clock-skew**: finestra di **2 minuti**
> (`> now() + interval '2 minutes'`), vedi §2.2 (deciso 2026-06-26).

1. **Overlap cross-livello (pratica vs flusso stesso istante)**: **ammesso** by-design
   (assi indipendenti — la propagazione va solo pratica→flussi, mai flusso→pratica:
   `trgfn_sospensioni_propaga` esce su `flusso_id IS NOT NULL`). Il DB non blocca e
   non deve. **DECISO (2026-06-26)**: si vuole un **warning UX** (non un blocco) quando
   si sospende un flusso già coperto da una sospensione di pratica in corso
   (ridondanza, non incoerenza). → **Follow-up FE/BE, fuori da questo brief DB**: il
   warning si calcola lato applicativo (esiste una sospensione pratica aperta che
   copre il periodo del flusso?), il DB resta invariato.

2. **Correzioni di righe storiche**: la UI v1 NON le prevede. Confermato che **non è
   lavoro di questo brief**. Se in v2 serviranno, i vincoli §2.1/§2.2 le validano (non
   le impediscono); il lavoro vero sarà rendere "correction-aware" i trigger AFTER
   UPDATE `giornale_riattivazione`/`riattiva` (vedi §3). Da pianificare separatamente.

---

## 7. Follow-up applicativo (FE/BE) — fuori scope DB, annotato qui per tracciabilità

> Non è lavoro del team DB: il DB resta invariato. Annotato perché emerso insieme a
> questo brief e da pianificare lato applicativo.

**Warning di ridondanza pratica↔flusso** (DECISO 2026-06-26).
Quando l'operatore sospende un **singolo flusso** mentre è già attiva una
**sospensione dell'intera pratica** che copre quel periodo, mostrare un **avviso
informativo non bloccante** (l'operatore può procedere comunque). Esempio messaggio:

> "Questa pratica è già sospesa per intero nel periodo indicato: sospendere anche il
> singolo flusso è ridondante."

- **Direzione unica**: il caso si presenta solo flusso-coperto-da-pratica (la
  propagazione va pratica→flussi, non viceversa). Nessun avviso nel verso opposto.
- **Calcolo lato applicativo**: verificare se esiste una sospensione di pratica
  (`flusso_id IS NULL`) con `periodo_sospensione` che copre il periodo del flusso che
  si sta sospendendo. Nessun supporto DB aggiuntivo necessario (la colonna
  `periodo_sospensione` e gli scope esistono già).
- **Non è un vincolo**: resta un hint UX; il DB continua ad ammettere la coesistenza
  (assi indipendenti, §6.1).
