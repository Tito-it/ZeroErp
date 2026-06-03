# Refactor overlap — enforcement no-sovrapposizione contratti/listini/promo

> **Data analisi:** 2026-06-02 · **Verifiche DB + migration correttive:** 2026-06-02 (lato DB)
> **Natura:** analisi + verifica runtime + piano correttivo **eseguito lato DB**.
> Le verifiche su DB e le migration correttive sono ora incluse (§5): siamo lato
> DB, qui si fanno le verifiche e si generano le modifiche.
> **Origine:** segnalazione utente — due contratti percepiti come sovrapposti per
> lo stesso cliente/utility (CNT0000027 `16/05→27/05` e CNT0000033 `20/05→25/05`),
> generati nonostante "dovrebbe esserci un controllo". **Esito:** falso allarme —
> differiscono su `ambito` (COMMERCIO vs COMMODITY), nessun bug del vincolo (§2.4).
> **Convenzione:** `[VERIFICATO]` su codice/migration; `[VERIFICATO SU DB]` =
> confermato via introspezione su dev (PG 18.4, 2026-06-02).

---

## 0. In una frase

Su alcune tabelle a periodo di validità il vincolo "niente sovrapposizioni"
(`ex_*_no_overlap`) **non è un vero `EXCLUDE` constraint ma un semplice
`CREATE INDEX ... USING gist`** → **non enforça nulla**. Un indice GiST accelera
le query di overlap ma non impedisce l'inserimento di righe sovrapposte: serve
un `EXCLUDE USING gist (... WITH &&)` (o, su PG18, un UNIQUE temporale).

---

## 1. Da dove nasce il problema

### 1.1 Il sintomo

L'utente ha generato un contratto la cui validità si accavalla con un contratto
preesistente per lo stesso cliente/utility. La protezione attesa "i contratti
non si sovrappongono, semmai vanno in successione" non ha bloccato la cosa.

### 1.2 La radice tecnica

Le tabelle a validità temporale usano una colonna `validita daterange` e un
oggetto chiamato `ex_<tabella>_no_overlap`. Il nome (`ex_` = exclusion) e il
codice BE lasciano intendere un **vincolo di esclusione** che solleva su
overlap. Ma per **alcune** di queste tabelle l'oggetto reale è un **indice
semplice**, non un constraint. Un `CREATE INDEX ... USING gist (...)`:

- **NON** ha gli operatori di esclusione (`WITH =`, `WITH &&`);
- quindi **NON** impedisce due righe con `validita` sovrapposte sulla stessa
  chiave: è solo una struttura di supporto alle query.

Il declassamento è **sistematico** ed è avvenuto durante il refactor di metà
maggio 2026 "`validita` → STORED GENERATED" (`20260514-*`), pianificato in
[[piano-miglioramenti-db-pg18]] (Step 2b). Per ogni tabella con periodo: il
`DROP COLUMN validita CASCADE` droppava l'`EXCLUDE` e lo step "ricrea l'indice"
scriveva **`CREATE INDEX ... USING gist (chiavi, validita) WHERE (...)`** invece
di `ADD CONSTRAINT ... EXCLUDE USING gist (chiavi WITH =, validita WITH &&)
WHERE (...)`. Colonne e `WHERE` preservati, ma **persi gli operatori di
esclusione (`WITH =`, `WITH &&`) e la natura di constraint**. Nome `ex_*`
identico → silenzioso.

**Radice istituzionale:** il template è quello di
[linee-guida-sql.md §7b "Pathway 2"](../../linee-guida-sql.md) (intestazione
"EXCLUDE USING gist" ma codice `CREATE INDEX`). Ogni migration dello Step 2b lo
ha copiato. Ironia: la stessa guida, ~50 righe sotto (sezione "stati
annullabili", caso `contratti`), mostra il pattern **corretto** con `ADD
CONSTRAINT ... EXCLUDE ... WITH =, WITH && ... WHERE`.

Per confronto, nel **catalogo** le tabelle **senza** `WHERE`
(`articoli_componenti`, `unita_misura_conversioni`) sono state migrate bene a
**UNIQUE temporale PG18 (SQL:2011)** (`20260514-07/08`), mantenendo
l'enforcement. Le tabelle **con** `WHERE` non possono usare il temporal UNIQUE
(non supporta predicato parziale) e sono tutte finite a indice-civetta.

**Il framework `dbops.automazione_overlap` non ripara il danno** `[VERIFICATO su
codice]`: (a) `fn_seed_automazione_overlap` rileva un indice GiST solo se la sua
definizione contiene `daterange(...)` (indice su espressione) — gli indici dello
Step 2b sono su colonna `validita`, quindi **non rilevati → seedati
`active=false`**; (b) anche se fossero `active=true`,
`fn_apply_automazione_overlap` emette `ADD CONSTRAINT ... EXCLUDE USING gist
(...)` **senza clausola `WHERE`** → per un vincolo parziale produrrebbe un
EXCLUDE *totale*, semanticamente errato. Tutte le 5 tabelle rotte hanno `WHERE`:
nessuna è ripristinabile dal framework. L'unica strada corretta è l'`ADD
CONSTRAINT ... EXCLUDE ... WHERE` esplicito per tabella, come fatto per
`contratti`.

### 1.3 La barriera reattiva non basta

L'unica protezione applicativa è `vendite.fn_contratto_sovrapposto` (predicato
corretto: tutti i non-abortiti, `&&` su `validita`), ma è cablata **solo nel
push offerta→contratto** ([offerte_repository.py:1089](../../../backend/apps/vendite/db/offerte_repository.py#L1089)).
La **creazione/modifica/attivazione manuale** di un contratto **non la chiama**.
Quindi, senza un vincolo DB, le altre strade non hanno alcun controllo. Il
backend mappa già l'IntegrityError di `ex_contratti_no_overlap` su un messaggio
parlante ([contratti_service.py:383](../../../backend/apps/vendite/services/contratti_service.py#L383)):
era previsto che il vincolo DB sollevasse — dove l'oggetto è un indice, quella
mappatura è **codice morto**.

---

## 2. Cosa è stato analizzato

### 2.1 Caveat metodologico importante (correzione in corsa)

**Il generatore dei doc `dbzero` NON rende i vincoli `EXCLUDE` nella sezione
"Vincoli".** `[VERIFICATO]` `vendite.listini_versioni` ha un `EXCLUDE` **reale**
(migration `20260409-01`/`20260224-01`) ma la sua sezione "Vincoli" mostra solo
CHECK/FK/PK/UNIQUE. Quindi nel doc un `EXCLUDE` vero e un indice semplice
appaiono **identici** (entrambi solo come `CREATE INDEX` sotto "Indici").

→ **Conseguenza:** non si può distinguere il caso buono dal caso rotto leggendo
solo il doc dbzero. Per questa analisi la **fonte autoritativa è la migration**
(`ADD CONSTRAINT ... EXCLUDE` vs `CREATE INDEX`). Una prima conclusione basata
sul solo doc (che dava `contratti` come "rotto") è stata corretta proprio grazie
a questo controllo.

### 2.2 Esito per oggetto (da migration) `[VERIFICATO]`

Verifica tracciata **in avanti** fino all'ultima migration che tocca ciascun
oggetto (non alla migration di creazione): è qui che la prima stesura di questo
documento aveva sbagliato su `listini_versioni`, fermandosi alla migration
`20260409`/`20260224` senza vedere il declassamento di `20260514-29`.

| Oggetto | Tabella | DDL reale (ultima migration) | `WHERE`? | Enforça? |
| --- | --- | --- | --- | --- |
| `ex_contratti_no_overlap` | `vendite.contratti` | `ADD CONSTRAINT ... EXCLUDE` (`20260521-03`) | sì | ✅ dovrebbe |
| `ex_listini_associazioni_no_overlap` | `vendite.listini_associazioni` | tabella **non esistente** su dev `[VERIFICATO SU DB]` (rimossa/rinominata) | — | n/a |
| `ex_listini_righe_comp_no_overlap` | `vendite.listini_righe_componenti` | `CREATE INDEX` (`20260513-18` nasce così → `20260514-04`) | sì | ❌ **NO** |
| `ex_promo_articoli_no_overlap` | `vendite.promo_articoli` | declassato a `CREATE INDEX` (`20260514-30`) | sì | ❌ **NO** |
| `ex_listini_versioni_no_overlap` | `vendite.listini_versioni` | declassato a `CREATE INDEX` (`20260514-29`) | sì | ❌ **NO** |
| `ex_categ_cli_listini_no_overlap` | `anagrafiche.categorie_clienti_listini` | declassato a `CREATE INDEX` (`20260514-31`) | sì | ❌ **NO** |
| `ex_template_documenti_versioni_no_overlap_pubblicata` | `documenti.template_documenti_versioni` | declassato a `CREATE INDEX` (`20260514-32`) | sì | ❌ **NO** |

**5 oggetti rotti, non 2.** Lo stesso errore copia-incolla è in tutte le
migration `20260514-04/29/30/31/32` (Step 2b del piano). Nota: per
`listini_righe_componenti` non è un *declassamento* — la tabella **nasce già a
indice** nella sua migration di creazione `20260513-18` (i commenti dicono
"EXCLUDE gist" ma il DDL è `CREATE INDEX`); il refactor `20260514-04` ha solo
preservato un indice mai enforçante.

> ⚠️ Il piano `piano-miglioramenti-db-pg18.md` §6 (tabella Step 2b) dichiara che
> queste migration "**ricreano EXCLUDE**". Le loro DDL ricreano indici semplici:
> il documento di pianificazione descrive male il DDL effettivamente eseguito, ed
> è marcato ✅ COMPLETATO con il difetto dentro.

### 2.3 Preventivi e Offerte commerciali

**Nessun** vincolo no-overlap, ed è **corretto by design**: sono *proposte*, non
forniture esclusive. Più preventivi/offerte per lo stesso cliente/utility/periodo
possono coesistere (proposte concorrenti / revisioni). Nessun bug, niente da
aggiungere.

### 2.4 Il caso contratti (sintomo dell'utente) — RISOLTO: H2 `[VERIFICATO SU DB]`

`vendite.contratti` ha un `EXCLUDE` reale (`ex_contratti_no_overlap`, contype `x`,
`WHERE (NOT is_abortito_snapshot)`) — confermato a runtime. Il vincolo funziona.
La diagnosi dei due contratti chiude su **H2 — non confliggono** perché
differiscono sulla chiave `ambito`:

| numero | billing_account | istanza_utility | utility | **ambito** | abortito | validita |
| --- | --- | --- | --- | --- | --- | --- |
| CNT0000027 | 173 | 197 | 5 | **COMMERCIO** | no | `[2026-05-16,2026-05-28)` |
| CNT0000033 | 173 | 197 | 5 | **COMMODITY** | no | `[2026-05-20,2026-05-26)` |

Stessa quadrupla tranne `ambito` (COMMERCIO ≠ COMMODITY) → per il modello **non
sono un overlap**, l'EXCLUDE (che ha `ambito WITH =`) correttamente non li blocca.
La percezione "stesso cliente/utility" nascondeva due ambiti distinti. **Nessun
bug del vincolo.** (H1 escluso: il constraint esiste. H3 escluso: nessuno dei due
è abortito.)

→ **Azione residua, solo funzionale:** confermare con Tid che una fornitura
COMMERCIO e una COMMODITY *possano* legittimamente sovrapporsi sullo stesso
billing/istanza/utility (atteso sì: sono ambiti di business diversi). Se invece
NON dovessero coesistere, è una questione di **modello** (ridurre la chiave del
vincolo togliendo `ambito`), non di enforcement.

> Collaterale: `fn_push_offerta_a_contratto` con successione deve chiudere
> l'incumbent **prima** dell'INSERT (stessa transazione), per compatibilità con
> l'EXCLUDE immediato. Non è la causa di questo caso (ambiti diversi), ma resta
> una verifica di robustezza sul push.

---

## 3. Indicazioni su cosa fare (per il team DB)

> Principio: l'invariante "niente forniture sovrapposte" deve vivere come
> **vincolo DB** (ultima difesa, vale per ogni strada: push, creazione manuale,
> edit, batch), non solo come check applicativo reattivo
> ([[feedback_normalize_guard_simmetrico]] — normalize/guard a livelli).

### 3.1 Ripristino enforcement dove manca (priorità)

Le **5 tabelle** rotte (§2.2): `vendite.listini_righe_componenti`,
`vendite.promo_articoli`, `vendite.listini_versioni`,
`anagrafiche.categorie_clienti_listini`, `documenti.template_documenti_versioni`.
Riportare ciascun `ex_*_no_overlap` a un vincolo **che enforça davvero**.

**Una sola opzione applicabile:**

```sql
ADD CONSTRAINT ex_<tabella>_no_overlap
    EXCLUDE USING gist (<chiavi> WITH =, validita WITH &&)
    WHERE (<filtro attivo>);
```

Il **temporal UNIQUE PG18 `WITHOUT OVERLAPS` NON è applicabile a nessuna** di
queste 5: tutte hanno una clausola `WHERE` parziale e il temporal UNIQUE non
supporta predicati parziali. (Per `catalogo.articoli_componenti`/
`unita_misura_conversioni` ha funzionato proprio perché *senza* `WHERE`.)

**NON delegare a `dbops.automazione_overlap`:** il framework non emette `WHERE`
(crea EXCLUDE totali) e non rileva gli indici-civetta su colonna → non ripara
nessuna delle 5 (dettaglio in §1.2). Il vincolo va scritto **esplicitamente per
tabella**, come per `contratti` in `20260521-03`.

**Prerequisito — già verificato:** il censimento overlap su dev (§5.1) dà **0
coppie violanti** su tutte e 5 le tabelle → nessuna bonifica necessaria, gli
EXCLUDE si creano puliti. (Da rivalutare se cambiano i dati prima dell'apply.)

### 3.2 Contratti

Prima **diagnosticare** (H1/H2/H3, §2.4). Poi:
- se H1 (vincolo assente) → ricreare l'`EXCLUDE` di `20260521-03` previa bonifica
  dati;
- se H2/H3 → non è un bug del vincolo ma di **dati/percezione**: chiarire col
  funzionale se quelle due forniture sono legittimamente distinte; eventualmente
  correggere i dati (chiusura/annullamento) della riga errata.

### 3.3 Robustezza del push e creazione manuale

- Verificare che `fn_push_offerta_a_contratto` con `chiudi_esistente=true`
  chiuda l'incumbent **prima** dell'INSERT del nuovo, nella stessa transazione
  (compatibilità con EXCLUDE immediato).
- Valutare se la **creazione/attivazione manuale** del contratto debba passare
  per un guard applicativo/trigger che usi `fn_contratto_sovrapposto` +
  `fn_log_and_raise_error` per dare il **messaggio parlante**
  (`E_VENDITE_CONTRATTO_OVERLAP`, oggi mappato ma mai sollevato perché il check
  esiste solo al push). L'EXCLUDE da solo dà un errore generico; il guard
  applicativo migliora la UX, l'EXCLUDE resta la difesa dura (defense-in-depth).

### 3.4 Decisione di modello — CHIUSA e IMPLEMENTATA (2026-06-02)

Lo scope del filtro parziale: i **DRAFT vanno ESCLUSI** dal vincolo (esclusività
solo all'attivazione). Decisione di Tid; spec nel brief "Overlap contratti:
escludere i DRAFT". **Implementato** con `20260602-17..22`:

- flag data-driven `config.stati_doc_contratti.is_bozza` (simmetrico a `is_abortito`);
- snapshot di riga `contratti.is_draft_snapshot` + colonna **GENERATED**
  `partecipa_overlap_snapshot` (`= NOT abortito AND NOT draft`), fonte UNICA del
  predicato per EXCLUDE **e** `fn_contratto_sovrapposto`;
- EXCLUDE → `WHERE (partecipa_overlap_snapshot)`; framework `automazione_overlap`
  allineato (anti-regressione);
- test pgTAP `test-contratti-overlap-draft-escluso-v1` (8/8): due DRAFT sovrapposti
  ammessi, DRAFT vs ATTIVO ammesso, attivazione sovrapposta bloccata (`23P01`).

Niente `DEFERRABLE`: con close-before-activate nella stessa transazione l'EXCLUDE
immediato basta. **Ambito** resta nella chiave (COMMERCIO/COMMODITY coesistono, §2.4).
A valle: guard applicativo BE proattivo (§3.3) ora può usare la semantica nuova.

### 3.5 Anti-regressione (per non ricascarci)

Il declassamento EXCLUDE→indice è passato silenzioso perché:
- il nome `ex_*` resta identico tra vincolo e indice;
- il doc dbzero non distingue (§2.1);
- il BE mappava un errore che non arrivava più;
- **la fonte stessa era il template rotto** di linee-guida-sql §7b "Pathway 2"
  (intestato "EXCLUDE" ma codice `CREATE INDEX`), copiato fedelmente 5 volte;
- il documento di pianificazione lo descriveva come "ricrea EXCLUDE" (§2.2): la
  *narrazione* mascherava il DDL.

Indicazioni (in ordine di efficacia):

1. **Correggere linee-guida-sql §7b "Pathway 2"** — è la radice: il template per
   il caso "con `WHERE`" deve essere `ADD CONSTRAINT ... EXCLUDE USING gist
   (... WITH =, validita WITH &&) WHERE (...)`, **non** `CREATE INDEX`. Va anche
   rimossa la frase contraddittoria "Gestito da `dbops.automazione_overlap`
   (active=true)": il framework non gestisce i parziali (§1.2). Finché il
   template resta sbagliato, ogni nuova tabella con `WHERE` ricasca nel bug.
2. **Test pgTAP** che asserisca, per ogni `ex_*_no_overlap` atteso, che esista un
   vincolo di tipo esclusione/temporale (`pg_constraint.contype IN ('x')` o
   l'equivalente UNIQUE temporale) — **non** un semplice indice. Avrebbe
   catturato tutte e 5 (incluso il falso negativo su `listini_versioni`).
   Trasforma il bug in un cancello CI.
3. In subordine, far emergere gli `EXCLUDE` anche nel generatore doc dbzero
   (sezione "Vincoli"), così che il doc smetta di essere ambiguo (§2.1).

---

## 4. Sintesi operativa

| Azione | Dominio | Tipo | Owner |
| --- | --- | --- | --- |
| **Correggere template linee-guida-sql §7b "Pathway 2"** (`CREATE INDEX`→`EXCLUDE`) | doc/standard | doc | DB+Tid |
| ✅ Diagnosi overlap CNT0000027/0033 → H2 (ambiti diversi, no bug) | contratti | verifica fatta | DB |
| ✅ Conferma funzionale: COMMERCIO+COMMODITY **possono** sovrapporsi (Tid 2026-06-02) → `ambito` resta nella chiave | contratti | modello | Tid |
| ✅ Ripristino vincolo enforcing (EXCLUDE parziale) + **mapping BE `E_VENDITE_LISTINO_RIGA_COMP_OVERLAP`** (gap chiuso 2026-06-02) | `listini_righe_componenti` | DDL `20260602-01` + BE | DB+BE |
| ✅ Ripristino vincolo enforcing (EXCLUDE parziale esplicito) | `promo_articoli` | DDL `20260602-02` | DB |
| ✅ Ripristino vincolo enforcing (EXCLUDE parziale esplicito) | `listini_versioni` | DDL `20260602-03` | DB |
| ✅ Ripristino vincolo enforcing (EXCLUDE parziale esplicito) | `categorie_clienti_listini` | DDL `20260602-04` | DB |
| ✅ Ripristino vincolo enforcing + **armonizzazione BE `E_DOCUMENTI_VERSIONE_OVERLAP`** (409 dedicato, prima 400) | `template_documenti_versioni` | DDL `20260602-05` + BE | DB+BE |
| Verifica ordine close/insert nel push | `fn_push_offerta_a_contratto` | verifica | DB |
| ✅ Guard applicativo overlap su **attivazione** (`emetti()`, nomina incumbent) — pre-check `fn_contratto_sovrapposto` | contratti | BE | BE |
| Test pgTAP "ex_* è davvero un vincolo" | tutte | test | DB |
| ✅ Decisione scope DRAFT: **DRAFT esclusi**, esclusivita' solo all'attivazione (Tid 2026-06-02) → brief [brief-db-contratti-overlap-draft-scope.md](brief-db-contratti-overlap-draft-scope.md), DB `20260602-17..22` | contratti | modello | Tid+DB |

**Non in scope (corretti così):** preventivi e offerte commerciali — nessun
vincolo no-overlap, by design.

---

## 5. Esecuzione lato DB — verifiche e migration correttive (2026-06-02)

Verifiche eseguite su **dev (PG 18.4)** via `psql`. Fonte autoritativa runtime.

### 5.1 Stato confermato `[VERIFICATO SU DB]`

- **Vincoli enforçanti reali:** solo `catalogo.articoli_componenti` +
  `catalogo.unita_misura_conversioni` (temporal UNIQUE) e `vendite.contratti`
  (EXCLUDE parziale). Tutto il resto degli `ex_*_no_overlap` su vendite/anagrafiche/
  documenti è **indice semplice**.
- **5 indici-civetta confermati** (nessun EXCLUDE, nessun `_c` ricreato dal
  framework): `listini_righe_componenti`, `promo_articoli`, `listini_versioni`,
  `categorie_clienti_listini`, `template_documenti_versioni`.
- **`dbops.automazione_overlap`:** tutte le righe `active=false`; le 5 tabelle
  rotte **non sono nemmeno in config** → il framework non le tocca. Coerente con
  `guide/automazione-db.md §4.3`: l'automazione OVERLAP crea EXCLUDE **senza
  `WHERE`** (solo vincoli totali) → **inadatta ai 5 vincoli parziali**, che vanno
  scritti a mano (come `contratti`). `fn_apply_automazione_overlap` è idempotente
  (salta se trova un EXCLUDE sul periodo) → non clobbererà i nuovi vincoli.
- **`vendite.listini_associazioni` non esiste** su dev (riga del §2.2 corretta).
- **Censimento overlap = 0** su tutte e 5 le tabelle (rispettando chiave + `WHERE`)
  → **nessuna bonifica dati necessaria**; gli EXCLUDE si creano senza violazioni
  (validato eseguendo i 5 `ADD CONSTRAINT` sui dati reali).
- **Contratti CNT0000027/0033:** H2, falso allarme (§2.4).

### 5.2 Migration correttive generate (da applicare via Liquibase)

Pattern unico per tabella: `DROP INDEX` civetta → `ADD CONSTRAINT ex_*_no_overlap
EXCLUDE USING gist (<chiavi> WITH =, validita WITH &&) WHERE (<filtro>)`. Richiede
`btree_gist` (presente). preCondition: `btree_gist` + assenza di EXCLUDE omonimo.

| Migration | Schema/Tabella | Predicato `WHERE` |
| --- | --- | --- |
| `20260602-01` | `vendite.listini_righe_componenti` | `attivo = true` |
| `20260602-02` | `vendite.promo_articoli` | `attivo IS TRUE` |
| `20260602-03` | `vendite.listini_versioni` | `attivo AND stato='ATTIVA'` |
| `20260602-04` | `anagrafiche.categorie_clienti_listini` | `attivo IS TRUE` (chiave con `COALESCE(classe_utenza_id,-1)`) |
| `20260602-05` | `documenti.template_documenti_versioni` | `attivo AND stato='PUBBLICATA'` |

**Stato:** ✅ **applicati** su dev (`DATABASECHANGELOG` 2026-06-02). I 5
`ex_*_no_overlap` sono ora EXCLUDE reali (contype `x`).

### 5.3 Follow-up — stato

- ✅ **Evoluzione del framework** per gestire gli EXCLUDE parziali →
  **[refactor-overlap-v2.md](refactor-overlap-v2.md)** completata: Fase 1 (colonna
  `where_predicate`) + Fase 2 (colonna `key_expressions`, registrazione dei **6**
  vincoli con `active=true`, **runner pgagent `automations_overlap`** notturno).
  I vincoli sono ora **governati dal framework**: se un futuro refactor ne droppa
  uno, il job notturno lo **ricrea** (auto-guarigione provata, v2 §4.4).
- ✅ **Cancello CI anti-regressione** — `db/pgtap/dbops/test-anti-overlap-enforcement-gate-v1.sql`:
  asserisce che ogni `ex_*_no_overlap` è un vincolo (contype `x`/`u`), mai un
  indice-civetta. Verde su dev.
- ✅ **Correzione `linee-guida-sql.md §7b Pathway 2`** — template
  `CREATE INDEX`→`EXCLUDE`; nota: il framework ora gestisce i parziali via
  `where_predicate`/`key_expressions`.
- ✅ **Decisione funzionale ambito** COMMERCIO/COMMODITY su contratti (§2.4) —
  **chiusa (Tid 2026-06-02): coesistono legittimamente**, `ambito` resta nella
  chiave. Era il falso allarme CNT0000027/0033.
- ✅ **BE/FE overlap (2026-06-02)** — chiusi tutti i lati applicativi:
  - **mapping mancante `ex_listini_righe_comp_no_overlap`** → nuovo codice
    `E_VENDITE_LISTINO_RIGA_COMP_OVERLAP` (409) in
    `listini_service._translate_integrity_error` con relativa policy (prima
    cadeva nel fallback generico `E_VENDITE_VALIDATION`);
  - **armonizzazione template-versioni** → `E_DOCUMENTI_VERSIONE_OVERLAP` (409
    dedicato, prima `E_DOCUMENTI_VALIDATION` 400);
  - **audit FE banner**: i 6 drawer mostrano tutti il messaggio parlante del 409
    (toast via `useApiHandler`/`extractApiError`), nessuno swallow;
  - **guard proattivo contratti** su `emetti()` (DRAFT→ATTIVO): pre-check
    `fn_contratto_sovrapposto` (wrapper repo `get_contratto_sovrapposto`) che nomina
    l'incumbent prima del backstop EXCLUDE.
- ✅ **Scope DRAFT (§3.4)** — **chiusa (Tid 2026-06-02): DRAFT esclusi**,
  esclusivita' solo all'attivazione → brief
  [brief-db-contratti-overlap-draft-scope.md](brief-db-contratti-overlap-draft-scope.md),
  DB implementato (`20260602-17..22`: flag `is_bozza`, snapshot `is_draft_snapshot`,
  colonna generata `partecipa_overlap_snapshot`, predicato EXCLUDE + framework +
  `fn_contratto_sovrapposto` allineati).
