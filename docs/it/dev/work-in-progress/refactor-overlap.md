# Refactor overlap — enforcement no-sovrapposizione contratti/listini/promo

> **Data analisi:** 2026-06-02
> **Natura:** analisi + indicazioni. **NESSUNO script/DDL qui** — le azioni DB
> sono materia del team DB ([[feedback_db_actions_passaggio_team]]). Questo
> documento spiega *da dove nasce il problema*, *cosa è stato analizzato* e *cosa
> conviene fare*; firme/strada implementativa le sceglie il team DB.
> **Origine:** segnalazione utente — due contratti attivi sovrapposti per lo
> stesso cliente/utility (CNT0000027 `16/05→27/05` e CNT0000033 `20/05→25/05`),
> generati nonostante "dovrebbe esserci un controllo".
> **Convenzione:** `[VERIFICATO]` su codice/migration attuali; `[DA VERIFICARE
> SU DB]` = introspezione runtime non disponibile dall'analisi (psql non
> raggiungibile dal sandbox).

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

Il declassamento è avvenuto durante il refactor di metà maggio 2026 "`validita`
→ STORED GENERATED" (`20260514-*`): trasformando `validita` in colonna generata
stored, l'`EXCLUDE` esistente è stato **droppato e ricreato come `CREATE INDEX`**
(tampone), perdendo silenziosamente l'enforcement. Per confronto, nel **catalogo**
lo stesso problema (`articoli_componenti`) è stato risolto bene migrando a un
**UNIQUE temporale PG18 (SQL:2011)** in `20260514-08`, mantenendo l'enforcement.
Su vendite, invece, due oggetti sono rimasti col tampone a indice.

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

| Oggetto | Tabella | DDL reale (ultima migration) | Enforça? |
|---|---|---|---|
| `ex_contratti_no_overlap` | `vendite.contratti` | `ADD CONSTRAINT ... EXCLUDE` (`20260521-03`) | ✅ dovrebbe |
| `ex_listini_versioni_no_overlap` | `vendite.listini_versioni` | `ADD CONSTRAINT ... EXCLUDE` | ✅ sì |
| `ex_listini_associazioni_no_overlap` | `vendite.listini_associazioni` | `ADD CONSTRAINT ... EXCLUDE` | ✅ sì |
| `ex_listini_righe_comp_no_overlap` | `vendite.listini_righe_componenti` | `CREATE INDEX` (`20260513-18`/`20260514-04`) | ❌ **NO** |
| `ex_promo_articoli_no_overlap` | `vendite.promo_articoli` | declassato a `CREATE INDEX` (`20260514-30`) | ❌ **NO** |

### 2.3 Preventivi e Offerte commerciali

**Nessun** vincolo no-overlap, ed è **corretto by design**: sono *proposte*, non
forniture esclusive. Più preventivi/offerte per lo stesso cliente/utility/periodo
possono coesistere (proposte concorrenti / revisioni). Nessun bug, niente da
aggiungere.

### 2.4 Il caso contratti (sintomo dell'utente) — diagnosi aperta

La migration `20260521-03` crea un `EXCLUDE` reale su `contratti`. Quindi il
vincolo **dovrebbe** bloccare l'overlap. Il fatto che CNT0000027/0033 coesistano
ha **tre spiegazioni possibili**, tutte da verificare a DB `[DA VERIFICARE SU DB]`:

- **H1 — vincolo non presente** su quella istanza DB (migration non applicata o
  successivamente alterata);
- **H2 — le due righe non confliggono** perché differiscono su una colonna chiave
  del vincolo: `(billing_account_id, istanza_utility_id, utility_id, ambito)`
  (es. istanza/PDP diversa, oppure `COMMODITY` vs `COMMERCIO`). In tal caso, per
  il modello, **non** sono un overlap — ma va capito se la percezione "stesso
  cliente/utility" nasconde un'istanza diversa;
- **H3 — una delle due è `is_abortito_snapshot = true`** (ANNULLATO): il vincolo
  è parziale `WHERE (NOT is_abortito_snapshot)`, quindi una riga abortita non
  conflitta e non blocca.

Verifiche minime per il team DB:
- `\d vendite.contratti` → il constraint `ex_contratti_no_overlap` è di tipo
  `EXCLUDE` (contype `x`) ed esiste?
- sui due contratti: valori di `billing_account_id, istanza_utility_id,
  utility_id, ambito, is_abortito_snapshot, validita`.

> Collaterale già emerso: se l'overlap nasce dal push con successione, va anche
> verificato che `fn_push_offerta_a_contratto` **chiuda l'incumbent prima** di
> inserire il nuovo (stessa transazione), altrimenti sotto un EXCLUDE immediato
> il push fallirebbe o (senza vincolo) lascerebbe l'overlap. Nel caso utente
> CNT0000027 risulta NON chiuso (`27/05`), il che fa pensare a successione non
> avvenuta o a creazione manuale.

---

## 3. Indicazioni su cosa fare (per il team DB)

> Principio: l'invariante "niente forniture sovrapposte" deve vivere come
> **vincolo DB** (ultima difesa, vale per ogni strada: push, creazione manuale,
> edit, batch), non solo come check applicativo reattivo
> ([[feedback_normalize_guard_simmetrico]] — normalize/guard a livelli).

### 3.1 Ripristino enforcement dove manca (priorità)

`vendite.listini_righe_componenti` e `vendite.promo_articoli`: riportare
`ex_*_no_overlap` a un vincolo **che enforça davvero**. Due opzioni (scelta del
team):
- `EXCLUDE USING gist (<chiavi> WITH =, validita WITH &&) WHERE (<filtro attivo>)`
  — come gli altri `ex_*` di vendite ancora sani;
- oppure **UNIQUE temporale PG18 (SQL:2011)** `WITHOUT OVERLAPS`, come già fatto
  per `catalogo.articoli_componenti` in `20260514-08` (coerenza col precedente
  più recente del progetto, e gestisce bene la colonna `validita` generata).

**Prerequisito (entrambe le opzioni):** bonificare gli overlap già presenti in
quelle tabelle, altrimenti la creazione del vincolo fallisce sulle righe in
violazione. Serve un censimento preventivo delle righe sovrapposte.

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

### 3.4 Decisione di modello (per Tid + DB)

Lo scope del filtro parziale: includere i **DRAFT** nel vincolo (oggi su
contratti il filtro è `WHERE NOT is_abortito_snapshot`, quindi DRAFT incluso)?
Se si vuole poter **preparare** un contratto futuro sovrapposto in DRAFT prima
della successione, un EXCLUDE immediato lo vieta → valutare lo scope o un
constraint `DEFERRABLE`. Da chiarire con il flusso di successione.

### 3.5 Anti-regressione (per non ricascarci)

Il declassamento EXCLUDE→indice è passato silenzioso perché:
- il nome `ex_*` resta identico tra vincolo e indice;
- il doc dbzero non distingue (§2.1);
- il BE mappava un errore che non arrivava più.

Indicazione: un **test pgTAP** che asserisca, per ogni `ex_*_no_overlap` atteso,
che esista un vincolo di tipo esclusione/temporale (es. `pg_constraint.contype
IN ('x')` o l'equivalente UNIQUE temporale) — non un semplice indice. Trasforma
il bug in un cancello CI. In subordine, far emergere gli `EXCLUDE` anche nel
generatore doc dbzero (sezione "Vincoli").

---

## 4. Sintesi operativa

| Azione | Dominio | Tipo | Owner |
|---|---|---|---|
| Diagnosi overlap CNT0000027/0033 (H1/H2/H3) | contratti | verifica | DB |
| Ripristino vincolo enforcing | `listini_righe_componenti` | DDL (post-bonifica) | DB |
| Ripristino vincolo enforcing | `promo_articoli` | DDL (post-bonifica) | DB |
| Verifica ordine close/insert nel push | `fn_push_offerta_a_contratto` | verifica | DB |
| Guard applicativo overlap su create/attivazione manuale | contratti | BE/DB | DB+BE |
| Test pgTAP "ex_* è davvero un vincolo" | tutte | test | DB |
| Decisione scope DRAFT / deferrable | contratti | modello | Tid+DB |

**Non in scope (corretti così):** preventivi e offerte commerciali — nessun
vincolo no-overlap, by design.
