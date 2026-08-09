# Brief DB — Dominio `vendite.offerte_commerciali` (Step di sviluppo)

> **Stato**: ✅ CHIUSO — tutti gli step 1-9 applicati e testati. Vedere §8.
>
> **Progressi al 2026-05-25 (branch `dev/db-tid`)**:
>
> - **Step 1 ✅ APPLICATO** — seed `config.sorgenti` (`OFFERTA_COMMERCIALE`),
>   `config.stati_doc_offerte` (6 righe incl. `ANNULLATA`), `config.messaggi_errore`
>   (6 codici). FK index policy registrata per le 4 FK delle note.
> - **Step 2 ✅ APPLICATO** — `vendite.offerte_commerciali` testata (migration
>   `20260524-03`) + addendum `motivazione_rifiuto` / `data_annullamento`
>   (migration `20260524-10`).
> - **Step 3 ✅ APPLICATO** — `offerte_commerciali_eccezioni` (`20260524-05`),
>   `offerte_commerciali_utilities` (`20260524-06`), partizione
>   `note_offerte_commerciali` + trigger note (`20260524-07`, `20260524-08`,
>   `20260524-09`). Documentazione manuale DB creata in `docs/it/dbzero/vendite/manual/`.
> - **Step 4 ✅ APPLICATO** — DDL `config.stati_doc_offerte_transizioni`
>   (`20260524-21`), seed 5 transizioni addendum A2 (`20260524-22`),
>   trigger guard `trgfn_offerte_commerciali_guard_transizione` (`20260524-23`).
>   Fix VARIADIC in `fn_log_and_raise_error`: `20260525-04`.
> - **Step 5 ✅ APPLICATO** — riga `offerta_commerciale`/`OFC` aggiunta in
>   `config.sistema_codici` (id=17, migration `20260524-25`).
>   Fix sequenza mancante + trigger `sync_gen_codice` aggiornato: `20260525-03`.
> - **Step 6 ✅ APPLICATO** — `trgfn_offerte_commerciali_revisione` AFTER INSERT
>   `_z90_` (migration `20260524-26`). Nota O4 analizzata: UPDATE su riga diversa,
>   no DEFERRABLE necessario.
> - **Step 7 ✅ APPLICATO** — `fn_crea_revisione_offerta(p_offerta_id, p_user)`
>   RETURNS BIGINT (migration `20260524-27`).
> - **Step 8 ✅ APPLICATO** — ALTER `vendite.contratti`: +`offerta_id` UNIQUE,
>   +`sorgente_tipo_id`, +`sorgente_uid` (migration `20260525-01`).
>   `fn_push_offerta_a_contratto` (migration `20260525-02`). UPSERT
>   `contratti_utilities`.
> - **Step 9 ✅ CHIUSO** — Suite pgTAP completa in
>   `db/pgtap/vendite/offerte_commerciali/` (9 file, tutti i test passati
>   2026-05-25).
>
> **Revisione 2026-05-24 (brief originale)**: corretti i problemi bloccanti
> B1/B2/B3 e gli importanti I1/I2/I3/I4 emersi dall'analisi critica. Le
> correzioni **riallineano il brief alla decisione §5.1 dell'analisi** (offerta
> 1:1 contratto, mono-utility, grana fine): una precedente stesura aveva
> reintrodotto erroneamente l'offerta multi-utility (Opzione B), scartata in
> §5.1. Vedi §0 changelog.
>
> **Addendum 2026-05-24 (da piano applicativo BE+FE rev. c)**: tre rifiniture
> recepite e già applicate alle migration — vedi §0.1.
>
> **Owner concettuale**: Tid (Michele Carlo Titini)
>
> **Sorgente di verità del modello**: [analisi-offerta-commerciale.md](analisi-offerta-commerciale.md)
> — decisioni §5 tutte chiuse 2026-05-23. Questo brief implementa quel modello,
> nient'altro.
>
> **Cosa NON è questo documento**:
>
> - non riscrive il modello — se durante l'implementazione emerge un dubbio di
>   modello, va sollevato in
>   [analisi-offerta-commerciale.md](analisi-offerta-commerciale.md) e chiuso
>   lì prima di toccare lo schema
> - non è un piano BE/FE — il piano applicativo è in coda al documento di
>   analisi (sezione successiva, non ancora scritta al momento di questo brief)
>
> **Riferimenti incrociati obbligatori prima di partire**:
>
> - [analisi-offerta-commerciale.md](analisi-offerta-commerciale.md) §5
>   (decisioni di modello tutte chiuse), in particolare §5.1 (1:1 mono-utility)
>   e §5.1-bis (direzione FK, grana fine)
> - [analisi-pratiche-domini-anello3.md](../work-in-progress/analisi-pratiche-domini-anello3.md)
>   §6.9 (convenzione idempotenza cross-dominio) e §11.2.4 (forma idempotenza
>   `push_a_contratto`)
> - `docs/it/linee-guida-sql.md`, `docs/it/linee-guida-trigger.md`,
>   `docs/it/liquibase-setup-workflow.md` (workflow autorizzativo team DB)
> - `docs/it/dbzero/vendite/manual/contratti.md` (specchio strutturale per
>   `offerte_commerciali` testata + `contratti_righe` per `offerte_commerciali_eccezioni`)
> - `docs/it/dbzero/vendite/manual/preventivi.md` (pattern revisioni
>   `fn_crea_revisione_*`, riusabile per offerte)

---

## 0. Changelog correzioni

### 0.1 Addendum 2026-05-24 (da piano applicativo BE+FE rev. c)

Tre rifiniture recepite dal piano applicativo BE+FE rev. c, già applicate alle
migration su `dev/db-tid`. Non cambiano strutture già applicate, solo addizioni.

| Rif. | Punto | Recepimento DB |
| ---- | ----- | -------------- |
| A1 | `motivazione_rifiuto TEXT NULL` sulla testata: testo libero motivo chiusura negativa (RIFIUTATA o ANNULLATA). Primo cittadino: visibile in lista, filtrabile, non in `meta`. | Aggiunto in migration `20260524-10`. |
| A2 | Sesto stato `ANNULLATA` (terminale, ritiro da parte nostra). Transizioni: `BOZZA→ANNULLATA` (unica via negativa da bozza), `EMESSA→RIFIUTATA` (no del cliente). Rimossa `BOZZA→RIFIUTATA` (incongrua: RIFIUTATA è semanticamente "no del cliente"). | `ANNULLATA` aggiunto in `stati_doc_offerte.csv`. `data_annullamento TIMESTAMPTZ NULL` aggiunto in `20260524-10`. Transizioni seed corrette in §3 step 4. |
| A3 | Conferma mirror fedele `offerte_commerciali_utilities`: tutti i campi business inclusi (`tipo_utenza_id`, `classe_utenza_id`, `param_*`, `istanza_dati_precontrattuali_id`, `meta`). Push 1:1 trasporta tutto. | Confermato — `20260524-06` include tutti i campi. Nessuna migration aggiuntiva. |

### 0.2 Correzioni brief originale (revisione 2026-05-24)

Riepilogo delle correzioni rispetto alla stesura precedente. La radice comune
di B1/B2/B3/I2 è una sola: **l'offerta deve essere uno specchio fedele del
contratto, non una versione "migliorata".** Ogni volta che il brief introduceva
una struttura diversa dal contratto (multi-utility, FK al posto di enum, FK al
posto di VARCHAR) rompeva la copia 1:1 del push, che è il cuore del modello
(§5.2).

| Rif. | Problema                                                                  | Correzione applicata                                                                                                  |
| ---- | ------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| B1   | `offerte_commerciali_utilities` dichiarata 1:N (offerta multi-utility)    | **Riportata a 1:1**, specchio fedele di `contratti_utilities` (che ha `UNIQUE (contratto_id)`). Riallineamento a §5.1 |
| B2   | `istanza_utility_id` / `utility_id` mancanti dalla testata offerta        | **Aggiunti NOT NULL** sulla testata `offerte_commerciali`, come su `vendite.contratti`. Il push li copia direttamente |
| B3   | `tipo_eccezione_id` modellato come FK a lookup                            | **Riuso dell'enum esistente** `vendite.tipo_eccezione_contratto` su `offerte_commerciali_eccezioni`. Push triviale    |
| I1   | Wording push "ACCETTATA o RIFIUTATA" contraddittorio coi test             | **Guard corretta: push solo da ACCETTATA.** RIFIUTATA → errore                                                        |
| I2   | `tipo_variazione_globale_id` modellato come FK                            | **Allineato a `vendite.contratti`: VARCHAR + CHECK** (`chk_offerte_tipo_variazione_globale`), non FK                  |
| I3   | CHECK di `contratti_righe` non replicati nel mirror eccezioni             | **Elencati esplicitamente** in Step 3: i 5 CHECK vanno replicati con nomi propri                                      |
| I4   | `stato_approvazione_prezzo` / `pratica_approvazione_prezzo_id` nel mirror | **Esclusi dall'offerta**; il push li inserisce NULL in `contratti_righe` (campi nullable, verificato)                 |

> **Nota di metodo**: la direzione della FK (`contratti.offerta_id`) e
> l'idempotenza pattern A erano **già corrette** nella stesura precedente e
> **non** sono state toccate (§5.1-bis, non negoziabile).

---

## 1. Inquadramento del lavoro

### 1.1 Obiettivo

Introdurre nello schema `vendite` il dominio dell'offerta commerciale come
**predecessore tracciato del contratto**, asimmetrico al preventivo
(preventivo→commessa/ordine = transazione puntuale; offerta→contratto =
condizioni quadro). Il dominio deve essere immediatamente capace di:

1. Emettere offerte numerate `OFC-*` per `(billing_account_id, istanza_utility)`
   — **una offerta, una utility** (§5.1).
2. Tracciare la negoziazione con stati BOZZA → EMESSA → ACCETTATA / RIFIUTATA.
3. Congelare la versione del listino di riferimento all'emissione (decisione
   §5.3 dell'analisi: scartata l'opzione "listino mobile alla data di
   accettazione").
4. Portare le proprie eccezioni proposte (OVERRIDE / ESCLUSIONE / AGGIUNTA)
   come tabella mirror di `contratti_righe` (decisione §5.2).
5. Eseguire il push **1:1** a contratto DRAFT con **idempotenza per
   costruzione** (pattern A §6.9.3 del documento pratiche, partial UNIQUE su
   `contratti(sorgente_uid)` per sorgente `OFFERTA_COMMERCIALE`).
6. Supportare revisioni come per i preventivi (`fn_crea_revisione_*`), con
   transizione automatica della precedente a `SUPERATA` (decisione §5.3:
   "rev.2 supera rev.1").

### 1.2 Cosa NON deve fare in v1 (predisposizioni future)

In coerenza con manifesto §7 e §5.1-bis dell'analisi, **non vanno introdotti in
v1**:

- **Pacchetto commerciale multi-contratto / multi-utility**:
  `vendite.pacchetti_commerciali` non esiste in v1. La capacità "offerta che
  copre più utility del cliente" **non** si modella come offerta multi-utility
  (errore della stesura precedente, vedi B1): si modella in futuro come
  *raggruppamento* di N offerte mono-utility 1:1. La FK predisposta
  `offerte_commerciali.pacchetto_id` non va inserita ora (sarebbe una colonna
  senza dominio). Il refactor futuro l'aggiungerà come step additivo (mezza
  giornata, vedi §5.1-bis dell'analisi).
- **Auto-attivazione contratto**: il push genera sempre DRAFT, mai ATTIVO. Il
  parametro di policy resta lato pratiche (`handler_params` su template
  `ATTIVAZIONE_CONTRATTO`), non lato DB.
- **Macchinari di scadenza che cambiano stato**: la scadenza è attributo
  calcolato + segnalazione UI, mai automatismo che muta `stato_id` (decisione
  §5.6). Niente job pgAgent v1.
- **Riapertura post-accettazione**: l'offerta ACCETTATA è immutabile. Il
  recesso si gestisce come cessazione del contratto generato con causale
  `RECESSO` (decisione §5.5).

### 1.3 Vincolo strutturale chiave da §5.1-bis

**La FK del legame offerta→contratto sta su `vendite.contratti`**, non su
`vendite.offerte_commerciali`. Concretamente:

```text
ALTER TABLE vendite.contratti
  ADD COLUMN offerta_id BIGINT NULL REFERENCES vendite.offerte_commerciali(id);
ALTER TABLE vendite.contratti
  ADD CONSTRAINT uq_contratti_offerta_id UNIQUE (offerta_id);
```

La direzione è **non negoziabile** (vedi §5.1-bis dell'analisi: è la
disciplina che rende il futuro pacchetto un'aggiunta additiva). Se durante
l'implementazione la direzione viene messa in discussione, il dubbio torna in
`analisi-offerta-commerciale.md` §5.1-bis, non si risolve nel brief.

### 1.4 Vincolo di granularità da §5.1 (cardine delle correzioni B1/B2)

**Un'offerta riguarda una sola utility, come il contratto.** Verifica diretta
sulle strutture esistenti (2026-05-24):

- `vendite.contratti` ha `istanza_utility_id` e `utility_id` **NOT NULL** sulla
  testata.
- `vendite.contratti_utilities` ha `UNIQUE (contratto_id)` → è una tabella di
  **estensione 1:1** (un record per contratto), non una ponte 1:N.

Di conseguenza, per garantire che il push 1:1 produca un contratto valido:

- la testata `offerte_commerciali` porta `istanza_utility_id` + `utility_id`
  NOT NULL (B2);
- `offerte_commerciali_utilities` è 1:1 (`UNIQUE (offerta_id)`), specchio fedele
  di `contratti_utilities` (B1).

Il caso "cliente con più utility" si gestisce con N offerte distinte (una per
utility), eventualmente raggruppate in futuro (§1.2, §5.1-bis). **Mai** con una
singola offerta multi-utility: spezzerebbe l'idempotenza `UNIQUE (offerta_id)`
sul contratto (un'offerta multi-utility dovrebbe generare N contratti, ma
`UNIQUE (offerta_id)` ne ammette uno solo).

---

## 2. Inventario complessivo delle modifiche

Riepilogo di tutto ciò che il brief introduce, distinto per categoria. Gli
**step §3** atomizzano queste modifiche in ordine di applicabilità.

### 2.1 Tabelle nuove

| Schema    | Tabella                         | Scopo                                                                          |
| --------- | ------------------------------- | ------------------------------------------------------------------------------ |
| `vendite` | `offerte_commerciali`           | Testata offerta (BA, **utility**, listino + versione fissata, validità, stato) |
| `vendite` | `offerte_commerciali_eccezioni` | Mirror fedele di `contratti_righe` per OVERRIDE / ESCLUSIONE / AGGIUNTA        |
| `vendite` | `offerte_commerciali_utilities` | **Estensione 1:1** offerta↔utility (mirror fedele di `contratti_utilities`)    |

> **Correzione B1**: `offerte_commerciali_utilities` è **1:1**, non 1:N.
> `contratti_utilities` ha `UNIQUE (contratto_id)`; il mirror replica
> `UNIQUE (offerta_id)`. Un record per offerta.

### 2.2 ALTER su tabelle esistenti

| Tabella             | ALTER                                                                           | Motivazione                                                                                                                                                            |
| ------------------- | ------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `vendite.contratti` | `ADD COLUMN offerta_id BIGINT NULL` + `UNIQUE (offerta_id)`                     | §5.1-bis: idempotenza pattern A                                                                                                                                        |
| `vendite.contratti` | `ADD COLUMN sorgente_tipo_id BIGINT NULL` + `ADD COLUMN sorgente_uid UUID NULL` | Verificato 2026-05-23 su `dbzero/vendite/tabelle/contratti.md`: i due campi NON esistono. Aggiungerli per simmetria con `vendite.ordini` / `vendite.commesse_sorgenti` |

> **Verifica DB pre-brief (2026-05-23)**: l'introspezione di
> `dbzero/vendite/tabelle/contratti.md` ha confermato che `vendite.contratti`
> ha solo `uid` (UNIQUE) e `parent_contratto_id` (FK self per relazioni
> contratto-padre/figlio), ma **non** ha `sorgente_tipo_id` né `sorgente_uid`.
> Gli ALTER del brief li aggiungono. Il campo `parent_contratto_id` esistente
> ha semantica diversa (contratto interno padre→figlio) e non va confuso col
> push da offerta.
>
> **Verifica utility (2026-05-24)**: `vendite.contratti` ha `istanza_utility_id`
> e `utility_id` NOT NULL sulla testata; `vendite.contratti_utilities` ha
> `UNIQUE (contratto_id)` (1:1). Questo vincola la forma dell'offerta (§1.4).

### 2.3 Funzioni e trigger nuovi

| Oggetto                                               | Tipo       | Step | Scopo                                                                            |
| ----------------------------------------------------- | ---------- | ---- | -------------------------------------------------------------------------------- |
| `vendite.fn_crea_revisione_offerta`                   | Function   | 7    | Pattern preventivi: rev.N+1 eredita, rev.N va in SUPERATA                        |
| `vendite.fn_push_offerta_a_contratto`                 | Function   | 8    | Crea contratto DRAFT, copia eccezioni + utility 1:1, idempotente per costruzione |
| `vendite.trgfn_offerte_commerciali_guard_transizione` | Trigger fn | 4    | State machine BOZZA→EMESSA→ACCETTATA/RIFIUTATA (immutabile post-accettazione)    |
| `vendite.trgfn_offerte_commerciali_revisione`         | Trigger fn | 6    | Quando crea rev.N+1, marca rev.N come SUPERATA automaticamente                   |
| `vendite.trgfn_offerte_commerciali_gen_codice`        | Trigger fn | 5    | Generato automaticamente da `script.fn_generate_codice()` via `sistema_codici`   |
| Guard listino versione attiva all'emissione           | Trigger fn | 4    | Check `listino_versione_id` ATTIVA al passaggio BOZZA→EMESSA                     |

### 2.4 Seed

| Tabella                                | Riga(e) da seedare                                                         | Step |
| -------------------------------------- | -------------------------------------------------------------------------- | ---- |
| `config.sorgenti`                      | `OFFERTA_COMMERCIALE` (singolare maiuscolo, convenzione §6.3 pratiche)     | 1    |
| `config.sistema_codici`                | Riga `offerta_commerciale` con prefisso `OFC` (analogo a `PRV` preventivi) | 5    |
| `config.messaggi_errore`               | 6 codici nuovi (vedi §4)                                                   | 1    |
| `config.stati_doc_offerte`             | 6 righe: BOZZA, EMESSA, ACCETTATA, RIFIUTATA, SUPERATA, ANNULLATA (A2)     | 2    |
| `config.stati_doc_offerte_transizioni` | 5 transizioni (vedi §3 step 4, aggiornate per A2)                          | 4    |

> **Naming stati documenti — chiarito 2026-05-23**: il pattern esistente in
> `config/tabelle` distingue:
>
> - `stati_doc_*` per **documenti commerciali** (preventivi, contratti, ordini,
>   ddt, fiscale)
> - `stati_*` per **altre entità** (pratiche, cliente, asset, fornitore)
>
> L'offerta commerciale è un documento commerciale → seguono il pattern
> `stati_doc_offerte` + `stati_doc_offerte_transizioni`. Coerente con
> `stati_doc_contratti` esistente. Il team DB può rivedere il naming esatto
> (es. `transizioni_stati_doc_offerte` se preferisce l'ordine alternativo già
> usato per preventivi e pratiche), ma il **prefisso `stati_doc_`** è
> vincolante per coerenza.
>
> **Causale `RECESSO` rimossa dal brief offerta** (decisione operativa
> 2026-05-23): la tabella `config.causali_cessazione_contratto` **non esiste
> oggi** (verifica diretta su `dbzero/config/tabelle/`); la cessazione
> contratto è gestita data-driven via `vendite.contratti.validita` daterange
> + `is_abortito_snapshot`. La decisione §5.5 dell'analisi presuppone una
> tabella che richiede un **brief separato** (introduzione causali +
> colonna `contratti.causale_cessazione_id` + retrofitting del meccanismo
> esistente). Per non gonfiare il brief offerta di scope creep, la causale
> RECESSO è esclusa e l'analisi offerta §5.5 sarà annotata con la
> dipendenza esplicita su quel brief futuro.

### 2.5 Test pgTAP

Suite `db/pgtap/vendite/offerte_commerciali/` con almeno i test elencati in §5.

---

## 3. Step di sviluppo (ordine di applicazione)

Ogni step è atomico: chiude prima di partire il successivo. La numerazione
**non corrisponde** ai numeri di migration files: ogni step può richiedere più
file `YYYYMMDD-NN-*.yaml` (a discrezione del team DB) ma deve restare
applicabile come singolo gruppo.

### Step 1 — Seed minimi e codici errore (prerequisiti senza dipendenze)

**Scopo**: introdurre i dati di riferimento senza creare ancora tabelle dominio.

**Deliverable**:

- Seed `config.sorgenti`: aggiungere riga `OFFERTA_COMMERCIALE` (`codice`,
  `descrizione`, `attivo=true`). Verificare prima che non esista.
- Seed `config.messaggi_errore.csv`: aggiungere i codici di §4.

**Test**: nessun pgTAP dedicato. Test indiretti negli step successivi.

**Note**:

- Nessuna dipendenza con step successivi → applicabile per primo. La causale
  `RECESSO` originariamente prevista è stata spostata a un brief separato
  (vedi §2.4 nota): la tabella `config.causali_cessazione_contratto` non
  esiste oggi e introdurla è scope creep rispetto al brief offerta.

### Step 2 — Tabella `vendite.offerte_commerciali` (testata)

**Scopo**: introdurre la testata dell'offerta, con i campi minimi richiesti
dalle decisioni §5 dell'analisi.

**Colonne richieste** (il team DB decide il nome esatto e i tipi PG18-coerenti
in base alle convenzioni):

| Colonna                     | Tipo               | Obbligatoria      | Note di modello                                                                                         |
| --------------------------- | ------------------ | ----------------- | ------------------------------------------------------------------------------------------------------- |
| `id`                        | BIGINT IDENTITY PK | sì                | Tecnico                                                                                                 |
| `uid`                       | UUID UNIQUE        | sì                | Per FK `contratti.sorgente_uid` (pattern §6.3 pratiche, naturale per push)                              |
| `codice`                    | TEXT               | sì (auto, step 5) | Generato `OFC-0000001` da `sistema_codici` (step 5)                                                     |
| `emittente_fiscale_id`      | BIGINT FK          | sì                | Coerente con preventivi/contratti                                                                       |
| `billing_account_id`        | BIGINT FK          | sì                | Scope cliente (vincolo §5.1: 1 offerta per (BA, utility)). Tipo `bigint`, specchio di `contratti`       |
| `istanza_utility_id`        | BIGINT FK          | **sì**            | **B2**: l'offerta riguarda una sola utility (specchio `contratti.istanza_utility_id` NOT NULL)          |
| `utility_id`                | BIGINT FK          | **sì**            | **B2**: specchio `contratti.utility_id` NOT NULL. Il push li copia direttamente sul contratto           |
| `listino_id`                | BIGINT FK          | sì                | Listino di riferimento                                                                                  |
| `listino_versione_id`       | BIGINT FK          | sì                | **Versione fissata all'emissione** (§5.3). NOT NULL dopo EMESSA, NULL ammesso solo in BOZZA             |
| `valore_variazione_globale` | NUMERIC            | no                | Variazione % globale proposta (default 0)                                                               |
| `tipo_variazione_globale`   | VARCHAR            | no                | **I2**: VARCHAR + CHECK `chk_offerte_tipo_variazione_globale`, specchio di `vendite.contratti` (NON FK) |
| `validita_dal`              | DATE               | sì                | Validità dell'offerta proposta al cliente                                                               |
| `validita_al`               | DATE               | no                | Scadenza dell'offerta (segnalazione, non bloccante §5.6)                                                |
| `stato_doc_offerta_id`      | BIGINT FK          | sì                | Default BOZZA. FK a `config.stati_doc_offerte` (step 4)                                                 |
| `revisione_numero`          | INTEGER            | sì                | Default 1; +1 per revisione (step 7)                                                                    |
| `revisione_padre_id`        | BIGINT FK self     | no                | NULL su rev.1, FK a rev.N-1 su rev.N+1                                                                  |
| `data_emissione`            | TIMESTAMPTZ        | no                | Valorizzata al passaggio BOZZA→EMESSA (trigger step 4)                                                  |
| `data_accettazione`         | TIMESTAMPTZ        | no                | Valorizzata al passaggio EMESSA→ACCETTATA                                                               |
| `data_rifiuto`              | TIMESTAMPTZ        | no                | Valorizzata al passaggio EMESSA→RIFIUTATA (no del cliente)                                              |
| `data_annullamento`         | TIMESTAMPTZ        | no                | **A2**: valorizzata al passaggio BOZZA→ANNULLATA (ritiro da parte nostra). Distinta da `data_rifiuto`   |
| `motivazione_rifiuto`       | TEXT               | no                | **A1**: testo libero motivo chiusura negativa (RIFIUTATA o ANNULLATA). Primo cittadino, non in `meta`   |
| `meta`                      | JSONB              | sì                | Default `'{}'` per estensioni future controllate                                                        |
| Audit fields                | (standard)         | sì                | `tx_id`, `data_insert`, `user_insert`, `data_update`, `user_update`                                     |

> **Note libere offerta**: le note testuali dell'offerta non stanno in una
> colonna `note TEXT` sulla testata ma nella partizione `vendite.note_offerte_commerciali`
> (partition di `vendite.note` FOR VALUES IN (`'OFFERTA'`)). Stessa struttura di
> `note_contratto` / `note_preventivo` con ancoraggio DOCUMENTO (nota testata)
> e RIGA (nota su singola eccezione). FK `target_id → offerte_commerciali`,
> `target_riga_id → offerte_commerciali_eccezioni`. Applicata in Step 3.

**Correzione I2**: `tipo_variazione_globale` è **VARCHAR + CHECK**, allineato
alla convenzione di `vendite.contratti.tipo_variazione_globale`
(`chk_contratti_tipo_variazione_globale`), **non** una FK a tabella tipi.
Stessi valori ammessi del contratto, così il push copia il valore senza
conversione.

**Vincoli**:

- `UNIQUE (uid)` (per FK pattern A da contratti).
- `CHECK chk_offerte_tipo_variazione_globale` sui valori ammessi di
  `tipo_variazione_globale`, **identico** al CHECK omonimo di `contratti`.
- Il vincolo "in BOZZA `listino_versione_id` può essere NULL, da EMESSA in poi
  no" non è esprimibile con CHECK semplice (richiede confronto con lo stato):
  da implementare come trigger guard in step 4.
- Nessun UNIQUE su `(billing_account_id, istanza_utility_id, ...)` in v1: la
  decisione "1 offerta attiva alla volta per (BA, utility)" è di policy, non
  strutturale. Si valuta dopo l'introduzione del pacchetto commerciale
  (§5.1-bis).

**Test**: pgTAP `test_offerte_commerciali_struttura.sql` verifica esistenza
tabella + colonne (incluse `istanza_utility_id`, `utility_id`,
`tipo_variazione_globale`) + FK + UNIQUE su uid + CHECK variazione globale.

### Step 3 — Tabelle `offerte_commerciali_eccezioni` + `offerte_commerciali_utilities`

**Scopo**: introdurre i dettagli dell'offerta speccchiando **fedelmente**
`contratti_righe` e `contratti_utilities`.

**`offerte_commerciali_eccezioni`** (mirror fedele di `vendite.contratti_righe`):

Il team DB allinea **una a una** le colonne strutturali di `contratti_righe`
sostituendo `contratto_id` con `offerta_id`. Includere:

- `offerta_id` (FK NOT NULL a `offerte_commerciali`)
- `articolo_id`
- `tipo_eccezione` — **tipo enum `vendite.tipo_eccezione_contratto`**
  (OVERRIDE / ESCLUSIONE / AGGIUNTA), **lo stesso enum del contratto**
- prezzo unitario / quantità / sconto / variazione, secondo modello contratti
- `fonte_quantita_attesa` (NOT NULL in `contratti_righe` → NOT NULL anche qui,
  vedi I3)
- campi fonte/erogazione/canone secondo il modello contratti
- audit fields standard

> **Correzione B3**: `tipo_eccezione` riusa l'**enum PostgreSQL esistente**
> `vendite.tipo_eccezione_contratto`, NON una FK `tipo_eccezione_id` a tabella
> di lookup (che non esiste). Il nome dell'enum resta `*_contratto` anche
> sull'offerta: leggermente improprio ma **intenzionale**, perché rende la
> copia 1:1 a push triviale (stesso tipo, nessuna conversione). Documentare la
> scelta nel manuale. In alternativa il team DB può rinominare l'enum in
> `vendite.tipo_eccezione` (neutro) con `ALTER TYPE ... RENAME`, ma allora va
> verificato l'impatto su trigger/CHECK esistenti di `contratti_righe`: scelta
> a discrezione del team DB, default = riuso senza rename.

> **Correzione I3 — CHECK constraint da replicare**: `contratti_righe` ha 5
> CHECK che validano la coerenza interna della riga. Sono parte della semantica
> "specchio" e vanno replicati con nomi propri (`chk_offecc_*`), **stessa
> logica**, altrimenti un'eccezione valida nell'offerta potrebbe rimbalzare al
> push perché il contratto la rifiuta:
>
> | CHECK su `contratti_righe`              | Equivalente su `offerte_commerciali_eccezioni` |
> | --------------------------------------- | ---------------------------------------------- |
> | `chk_contrighe_coerenza_canone`         | `chk_offecc_coerenza_canone`                   |
> | `chk_contrighe_coerenza_fonte_erogazione` | `chk_offecc_coerenza_fonte_erogazione`       |
> | `chk_contrighe_fonte_qta`               | `chk_offecc_fonte_qta`                         |
> | `chk_contrighe_prezzo_per_tipo_eccezione` | `chk_offecc_prezzo_per_tipo_eccezione`       |
> | `chk_contrighe_tipo_erog`               | `chk_offecc_tipo_erog`                         |

> **Correzione I4 — campi di approvazione prezzo esclusi**: `contratti_righe`
> ha `stato_approvazione_prezzo` (enum) e `pratica_approvazione_prezzo_id` (FK).
> **Non** vanno replicati sull'offerta (una proposta non ha ancora
> un'approvazione prezzo). Al push, la copia inserisce questi campi come **NULL**
> in `contratti_righe`. Verificato che entrambi sono nullable in
> `contratti_righe`; il team DB conferma in fase di implementazione che nessun
> CHECK/NOT NULL lo impedisca.

Decisione di modello (richiamo §5.2): copia 1:1 a push_a_contratto, **senza
reinterpretazione**. Le due tabelle hanno la stessa semantica delle eccezioni;
sono separate fisicamente per ovvi motivi di FK ma la struttura colonne è
identica (eccetto la FK al padre e i campi di approvazione prezzo esclusi, I4).

**`offerte_commerciali_utilities`** (mirror fedele di `vendite.contratti_utilities`):

Tabella di estensione **1:1** offerta↔utility, **identica** a
`contratti_utilities`:

- `offerta_id` (FK NOT NULL a `offerte_commerciali`)
- `UNIQUE (offerta_id)` — **un solo record per offerta** (specchio di
  `UNIQUE (contratto_id)` su `contratti_utilities`)
- restanti colonne identiche a `contratti_utilities`

> **Correzione B1**: questa tabella è **1:1**, non 1:N. Una precedente stesura
> la dichiarava ponte 1:N (offerta multi-utility), in contrasto con §5.1 e con
> la struttura reale di `contratti_utilities`. Alla push 1:1 il contratto
> eredita l'unico record utility dall'offerta senza loop.

**Test**: pgTAP `test_offerte_commerciali_eccezioni_struttura.sql` (verifica
colonne + tipo enum `tipo_eccezione` + i 5 CHECK + esclusione campi I4) +
`test_offerte_commerciali_utilities_struttura.sql` (verifica colonne +
`UNIQUE (offerta_id)`).

### Step 4 — State machine offerte (trigger guard + transizioni)

**Scopo**: rendere `vendite.offerte_commerciali.stato_doc_offerta_id`
config-driven, allineato al pattern già usato per preventivi e contratti
(vedi `stati_doc_contratti` + relative transizioni esistenti).

**Deliverable**:

- Seed `config.stati_doc_offerte` con **6 righe** (**già applicato in Step 1**):
  - `BOZZA` (iniziale, editabile)
  - `EMESSA` (proposta al cliente, immutabile sui dati propri)
  - `ACCETTATA` (terminale positivo, immutabile)
  - `RIFIUTATA` (terminale negativo — no del cliente, immutabile)
  - `SUPERATA` (terminale tecnico, valorizzato dal trigger revisione step 6)
  - `ANNULLATA` (terminale — ritiro da parte nostra prima/durante bozza, **addendum A2**)
- Seed `config.stati_doc_offerte_transizioni` (**DA FARE**) con le sole
  transizioni ammesse (**aggiornate per addendum A2** — rimossa `BOZZA→RIFIUTATA`):

  | Da       | A          | Note                                                |
  | -------- | ---------- | --------------------------------------------------- |
  | BOZZA    | EMESSA     | Il trigger congela `listino_versione_id`            |
  | BOZZA    | ANNULLATA  | Ritiro interno; `BOZZA→RIFIUTATA` rimossa (A2)      |
  | EMESSA   | ACCETTATA  | Innesca push a contratto                            |
  | EMESSA   | RIFIUTATA  | No del cliente                                      |
  | EMESSA   | SUPERATA   | Trigger revisione (step 6)                          |

  Nessuna transizione uscente da ACCETTATA, RIFIUTATA, SUPERATA, ANNULLATA
  (tutti terminali immutabili).

- Trigger `trgfn_offerte_commerciali_guard_transizione` BEFORE UPDATE OF
  `stato_doc_offerta_id` ON `vendite.offerte_commerciali` (**DA FARE**):
  - Verifica transizione in `config.stati_doc_offerte_transizioni`
  - Valorizza timestamp corrispondente al passaggio:
    `data_emissione` (→EMESSA), `data_accettazione` (→ACCETTATA),
    `data_rifiuto` (→RIFIUTATA), `data_annullamento` (→ANNULLATA, **A2**)
  - Su `motivazione_rifiuto`: obbligatorio o opzionale a scelta del team DB;
    il campo è già presente per i passaggi negativi (RIFIUTATA, ANNULLATA, **A1**)
  - Guard BOZZA→EMESSA: `listino_versione_id` NOT NULL + versione ATTIVA (§5.3)
  - Errori via `script.fn_log_and_raise_error()` con codici §4
- Trigger fase `_a10_` (guard, vedi linee-guida-trigger.md)

**Test**: `test_offerte_commerciali_state_machine.sql`:

- transizione BOZZA→EMESSA con listino_versione_id NULL → fallisce
  `E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO`
- transizione BOZZA→EMESSA con versione listino NON ATTIVA → fallisce
  `E_OFFERTA_EMISSIONE_VERSIONE_LISTINO_NON_ATTIVA`
- transizione EMESSA→BOZZA → fallisce `E_OFFERTA_TRANSIZIONE_NON_AMMESSA`
- transizione ACCETTATA→qualunque → fallisce
- transizione EMESSA→ACCETTATA → successo + `data_accettazione` valorizzata

### Step 5 — Numerazione `OFC-*` via `sistema_codici`

**Scopo**: codice offerta generato automaticamente, riusando il meccanismo
standard.

**Deliverable**:

- Aggiungere riga in `80_data/sql/config/sistema_codici.csv`:
  - chiave: `offerta_commerciale`
  - prefisso: `OFC`
  - formato: equivalente a `PRV-0000001`
- Il trigger
  `trg_sistema_codici_z90_sync_gen_codice_ins_upd_dlt` crea automaticamente:
  - sequenza `vendite.offerte_commerciali_codice_seq`
  - trigger function `vendite.trgfn_offerte_commerciali_gen_codice()`
  - trigger `trg_offerte_commerciali_a10_gen_codice_ins_upd`

**Test**: `test_offerte_commerciali_codice.sql`:

- INSERT senza `codice` esplicito → trigger genera `OFC-0000001`
- INSERT successivo → genera `OFC-0000002`
- UPDATE con `codice` modificato manualmente → guard immutabilità (se il
  pattern di sistema_codici lo gestisce, altrimenti aggiungere)

### Step 6 — Trigger revisione (rev.N → SUPERATA automatico)

**Scopo**: quando viene creata una revisione successiva (rev.N+1 con
`revisione_padre_id = rev.N`), la rev.N va automaticamente in SUPERATA. La
funzione che CREA la revisione è step 7; questo step prepara solo il trigger
"reattivo".

**Deliverable**:

- Trigger fn `trgfn_offerte_commerciali_revisione` AFTER INSERT ON
  `vendite.offerte_commerciali`:
  - Se `NEW.revisione_padre_id IS NOT NULL`:
    - UPDATE `vendite.offerte_commerciali` SET `stato_doc_offerta_id = SUPERATA`
      WHERE `id = NEW.revisione_padre_id`
  - Trigger fase `_z90_` (vedi linee-guida-trigger.md)
  - **Nota concorrenza (O4)**: questo AFTER INSERT fa UPDATE sulla **stessa
    tabella**, e quell'UPDATE riattiva il guard di state machine `_a10_` (la
    transizione EMESSA→SUPERATA deve essere ammessa in
    `stati_doc_offerte_transizioni` — lo è, vedi step 4). Verificare se il
    trigger vada dichiarato `DEFERRABLE INITIALLY DEFERRED` per evitare
    contese in scenari INSERT+UPDATE concorrenti sulla stessa tabella nella
    stessa transazione.

**Test**: `test_offerte_commerciali_revisione_trigger.sql`:

- INSERT offerta rev.2 con `revisione_padre_id = rev.1.id` → rev.1 passa a
  SUPERATA
- INSERT offerta rev.1 con `revisione_padre_id = NULL` → nessuno stato altrui
  cambia

### Step 7 — `fn_crea_revisione_offerta`

**Scopo**: funzione di alto livello che crea rev.N+1 ereditando da rev.N
(testata + eccezioni + utility), come pattern già fatto per preventivi.

**Deliverable**:

- Function `vendite.fn_crea_revisione_offerta(p_offerta_id BIGINT, p_motivazione TEXT) RETURNS BIGINT`
- Logica:
  - Carica rev.N (parametro). Errore se non in EMESSA (rev.N+1 si fa solo per
    offerte EMESSE, non ACCETTATE/RIFIUTATE/SUPERATE/BOZZA).
  - INSERT testata rev.N+1: nuovo uid, nuovo codice (via sistema_codici),
    `revisione_numero = rev.N.revisione_numero + 1`, `revisione_padre_id =
    p_offerta_id`, stato BOZZA, dati copiati da rev.N (listino, **utility**,
    variazione, validità ricalcolata).
  - Copia eccezioni rev.N → eccezioni rev.N+1.
  - Copia utility rev.N → utility rev.N+1 (1:1).
  - Trigger step 6 reagisce all'INSERT e marca rev.N come SUPERATA.
  - Restituisce id della rev.N+1.
- Errori semantici (vedi §4):
  - rev.N non in EMESSA: `E_OFFERTA_REVISIONE_STATO_NON_AMMESSO`

**Test**: `test_fn_crea_revisione_offerta.sql`:

- creazione rev.2 da rev.1 EMESSA → rev.1 SUPERATA, rev.2 BOZZA, eccezioni +
  utility copiate
- creazione rev.2 da rev.1 ACCETTATA → fallisce
- creazione rev.2 da rev.1 BOZZA → fallisce (non si revisiona una bozza, la si
  modifica direttamente)

### Step 8 — `fn_push_offerta_a_contratto` (idempotente per costruzione)

**Scopo**: alla `ACCETTAZIONE` di un'offerta, crea il contratto in DRAFT
copiando eccezioni e utility 1:1. **Idempotenza obbligatoria**: doppia
invocazione → seconda invocazione fallisce con errore semantico, nessun
contratto duplicato.

**Deliverable**:

- ALTER `vendite.contratti`:
  - `ADD COLUMN offerta_id BIGINT NULL REFERENCES vendite.offerte_commerciali(id)`
  - `ADD CONSTRAINT uq_contratti_offerta_id UNIQUE (offerta_id)` (idempotenza
    pattern A §6.9.3 pratiche)
- Verifica `sorgente_tipo_id` + `sorgente_uid` su `vendite.contratti`
  (vedi §2.2 nota). Se mancanti, aggiungerli.
- Function `vendite.fn_push_offerta_a_contratto(p_offerta_id BIGINT, p_pratica_id BIGINT) RETURNS BIGINT`:
  - Carica offerta. **Errore se non in ACCETTATA**: `E_OFFERTA_PUSH_STATO_NON_AMMESSO`.
  - Verifica idempotenza esplicita:

    ```sql
    IF EXISTS (SELECT 1 FROM vendite.contratti
               WHERE offerta_id = p_offerta_id)
    THEN
      RAISE EXCEPTION USING ERRCODE = 'P0001',
        MESSAGE = 'E_OFFERTA_CONTRATTO_GIA_GENERATO',
        DETAIL = format('Offerta %s ha già generato il contratto', p_offerta_id);
    END IF;
    ```

  - INSERT contratto in DRAFT:
    - `sorgente_tipo_id` = id di `OFFERTA_COMMERCIALE` da `config.sorgenti`
    - `sorgente_uid` = `offerta.uid`
    - `offerta_id` = `p_offerta_id`
    - copia `billing_account_id`, `emittente_fiscale_id`,
      **`istanza_utility_id`, `utility_id`** (B2), `listino_id`,
      `listino_versione_id`, `valore_variazione_globale`,
      `tipo_variazione_globale` (VARCHAR, I2), ecc.
  - Copia `offerte_commerciali_eccezioni` → `contratti_righe` (1:1, senza
    reinterpretazione, §5.2). I campi di approvazione prezzo
    (`stato_approvazione_prezzo`, `pratica_approvazione_prezzo_id`) sono
    inseriti **NULL** (I4). Il `tipo_eccezione` passa invariato (stesso enum,
    B3).
  - Copia `offerte_commerciali_utilities` → `contratti_utilities` (1:1, un
    record, B1).
  - Se `p_pratica_id IS NOT NULL`, INSERT in `pratiche.pratiche_sorgenti`
    con `(pratica_id, sorgente_tipo_id=CONTRATTO, sorgente_uid=contratto.uid, ruolo='COLLEGATO')`.
  - Restituisce l'id del contratto creato.
- Trigger AFTER per registrazione giornale pratica se `p_pratica_id` valorizzato
  (delegato a `pratiche_service.log_evento_dominio()` lato applicativo; il DB
  non scrive nel giornale pratica autonomamente).

> **Correzione I1**: la guard è **solo ACCETTATA**. La stesura precedente
> scriveva "non in ACCETTATA o RIFIUTATA", in contraddizione coi test (che
> richiedono il fallimento anche su RIFIUTATA). Un'offerta RIFIUTATA non
> genera alcun contratto.

**Test obbligatorio §6.9.5 pratiche**: `test_fn_push_offerta_a_contratto.sql`:

- push offerta ACCETTATA → contratto in DRAFT, eccezioni copiate, **utility
  copiata (1 record)**, `istanza_utility_id`/`utility_id` valorizzati sul
  contratto, `offerta_id` valorizzato
- **doppia invocazione su stessa offerta → seconda invocazione fallisce con
  `E_OFFERTA_CONTRATTO_GIA_GENERATO`, nessun contratto duplicato**
- push offerta BOZZA / EMESSA / RIFIUTATA → fallisce con
  `E_OFFERTA_PUSH_STATO_NON_AMMESSO`
- contratto generato ha `sorgente_tipo_id = id_di_OFFERTA_COMMERCIALE` e
  `sorgente_uid = offerta.uid`

### Step 9 — Suite pgTAP completa + verifica copertura

**Scopo**: chiudere la copertura test prima della consegna.

**Deliverable**:

- Tutti i test pgTAP elencati negli step precedenti raccolti in
  `db/pgtap/vendite/offerte_commerciali/`.
- Test integrativo `test_offerte_commerciali_end_to_end.sql`:
  - INSERT offerta BOZZA → editing → EMESSA → ACCETTATA → push contratto
  - INSERT offerta EMESSA → fn_crea_revisione_offerta → rev.2 BOZZA + rev.1
    SUPERATA
  - INSERT offerta EMESSA → RIFIUTATA → tentativo push → fallisce

---

## 4. Codici errore da registrare in `config.messaggi_errore.csv`

| Codice                                            | Severity | Messaggio (it_IT)                                                                    |
| ------------------------------------------------- | -------- | ------------------------------------------------------------------------------------ |
| `E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO`      | ERROR    | "Impossibile emettere l'offerta: versione del listino di riferimento non impostata." |
| `E_OFFERTA_EMISSIONE_VERSIONE_LISTINO_NON_ATTIVA` | ERROR    | "Impossibile emettere l'offerta: la versione del listino indicata non è ATTIVA."     |
| `E_OFFERTA_TRANSIZIONE_NON_AMMESSA`               | ERROR    | "Transizione di stato dell'offerta non ammessa: %s → %s."                            |
| `E_OFFERTA_REVISIONE_STATO_NON_AMMESSO`           | ERROR    | "Impossibile creare una revisione: l'offerta deve essere in stato EMESSA."           |
| `E_OFFERTA_PUSH_STATO_NON_AMMESSO`                | ERROR    | "Impossibile generare il contratto: l'offerta deve essere in stato ACCETTATA."       |
| `E_OFFERTA_CONTRATTO_GIA_GENERATO`                | ERROR    | "L'offerta %s ha già generato il contratto: invocazione duplicata non consentita."   |

> **Codici aggiuntivi attesi durante implementazione**: il team DB può
> aggiungere codici granulari se durante lo sviluppo emergono guard più fini
> (es. `E_OFFERTA_EMISSIONE_BA_INATTIVO`). La regola è: ogni guard con
> messaggio operativo per l'operatore → un codice in
> `config.messaggi_errore.csv`. Nessuna `RAISE EXCEPTION` libera senza codice.

---

## 5. Mappa copertura pgTAP (riepilogo per step)

| Step | File pgTAP                                         | Cosa verifica                                                                               |
| ---- | -------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| 2    | `test_offerte_commerciali_struttura.sql`           | Esistenza tabella + colonne (incl. utility + tipo_variazione VARCHAR) + FK + UNIQUE + CHECK |
| 3    | `test_offerte_commerciali_eccezioni_struttura.sql` | Mirror fedele di `contratti_righe`: enum `tipo_eccezione` + 5 CHECK + esclusione campi I4   |
| 3    | `test_offerte_commerciali_utilities_struttura.sql` | Mirror fedele di `contratti_utilities`: **UNIQUE (offerta_id)** (1:1)                       |
| 4    | `test_offerte_commerciali_state_machine.sql`       | Tutte le transizioni ammesse e tutte quelle vietate + guard listino                         |
| 5    | `test_offerte_commerciali_codice.sql`              | Generazione `OFC-*` via `sistema_codici`                                                    |
| 6    | `test_offerte_commerciali_revisione_trigger.sql`   | rev.N → SUPERATA al creare rev.N+1                                                          |
| 7    | `test_fn_crea_revisione_offerta.sql`               | Creazione rev.N+1 corretta (eccezioni + utility copiate)                                    |
| 8    | `test_fn_push_offerta_a_contratto.sql`             | Push corretto + **idempotenza obbligatoria** + copia eccezioni/utility 1:1                  |
| 9    | `test_offerte_commerciali_end_to_end.sql`          | Flusso completo BOZZA → EMESSA → ACCETTATA → contratto DRAFT                                |

Tutti i test pgTAP devono avere `# Indice test (0..N):` nell'header (regola
AGENTS.md §Test).

---

## 6. Coerenza con altri brief e domini

### 6.1 Con il modello pratiche

- Il dominio offerta è il prerequisito dell'asse `OFFERTA_QUADRO` descritto in
  [analisi-pratiche-domini-anello3.md](../work-in-progress/analisi-pratiche-domini-anello3.md) §11.2.
- L'idempotenza pattern A di `fn_push_offerta_a_contratto` è **identica** al
  pattern descritto in §6.9.3 di quel documento e già usato per
  `fn_push_preventivo_a_ordine` (decisione §5.3.3).
- Lo step 1 (seed `OFFERTA_COMMERCIALE` in `config.sorgenti`) è citato anche
  in [analisi-pratiche-domini-anello3.md](../work-in-progress/analisi-pratiche-domini-anello3.md)
  §11.2.4 come riserva di sorgente — coerente seedare qui in anticipo.

### 6.2 Con il modello contratti

- L'ALTER `vendite.contratti.offerta_id` (§2.2) chiude il ponte logico
  presupposto dal refactor contratti completato 2026-05-16 (vedi
  [refactor-contratti-modalita.md](../work-done/refactor-contratti-modalita.md)),
  che lasciava il contratto pronto a ricevere un push da una sorgente di
  proposta.
- Lo snapshot della versione listino sul contratto (decisione §3-bis-A del
  refactor contratti) è ora coerente: l'offerta congela la versione,
  `push_a_contratto` copia il riferimento, il contratto eredita uno snapshot
  pulito.
- **Specchio fedele**: offerta testata, eccezioni e utility replicano la forma
  *esatta* di contratti / contratti_righe / contratti_utilities (stesso enum
  per `tipo_eccezione`, stesso VARCHAR+CHECK per `tipo_variazione_globale`,
  stessa cardinalità 1:1 utility, stessi 5 CHECK). Questa fedeltà è ciò che
  rende `push_a_contratto` una copia 1:1 banale (§5.2). Qualsiasi divergenza
  strutturale fra offerta e contratto è da considerare un bug, non un
  miglioramento.

### 6.3 Con il modello preventivi

- L'offerta NON ha legame con il preventivo (decisione §5.7). I due assi
  restano separati per costruzione.
- Il pattern `fn_crea_revisione_offerta` riusa concettualmente
  `fn_crea_revisione_preventivo` esistente: il team DB può ispirarsi
  all'implementazione preventivi, non c'è codice da inventare ex novo.

---

## 7. Note operative per il team DB

- **Workflow autorizzativo**: questo brief si applica solo su esplicita
  conferma di Tid. Nessuna migration parta in autonomia.
- **Branch**: lavoro su `dev/db-tid` come da prassi.
- **Ordine di applicazione**: rispettare l'ordine §3 (1 → 2 → 3 → 4 → 5 → 6 →
  7 → 8 → 9). Step 1 può essere applicato anche separatamente come prelude;
  step 9 chiude la consegna.
- **Naming Liquibase**: file `YYYYMMDD-NN-<tipo>-<descrizione>.yaml`,
  un changeSet per file, `logicalFilePath` sempre presente (vedi
  AGENTS.md §Liquibase v2 Workflow).
- **Naming trigger**: `trg_<schema_opzionale>_<tabella>_<fase>_<descrizione>_<eventi>`
  (linee-guida-trigger.md). Fase `_a10_` per guard, `_z90_` per
  finali/deferrable.
- **Audit fields**: rispettare convenzione `tx_id`, `data_insert`,
  `user_insert`, `data_update`, `user_update`.
- **FK index policy**: non creare indici FK manualmente, usare
  `dbops.apply_fk_index_policy()` in `90_end` (linee-guida-sql.md §FK index
  policy).
- **Documentazione manuale**: aggiornare/creare a fine implementazione
  `docs/it/dbzero/vendite/manual/offerte_commerciali.md` con la struttura
  standard. Documentare esplicitamente:
  - la ridondanza intenzionale `offerta_id` + `sorgente_uid` sul contratto (O1)
  - il riuso dell'enum `tipo_eccezione_contratto` sull'offerta (B3)
  - l'esclusione intenzionale delle offerte scadute dal framework
    `dbops.automazione_chiusura_scadenze` (O5, decisione §5.6)
- **Dubbi di modello**: se durante l'implementazione emerge un dubbio di
  modello (es. "questo CHECK ha senso?"), va sollevato a Tid via
  [analisi-offerta-commerciale.md](analisi-offerta-commerciale.md), non
  risolto unilateralmente nel brief.

---

## 8. Stato del brief

> **Aggiornamento 2026-05-25**: tutti gli step 1-9 APPLICATI e testati.
> Brief CHIUSO. Suite pgTAP completa, tutti i test passati.
> Due bug fix applicati durante lo Step 9 (`20260525-03`, `20260525-04`).

| Step | Stato | Migration / File | Note |
| ---- | ----- | ---------------- | ---- |
| 1 | APPLICATO | CSV seeds (sorgenti, stati, errori, fk_policy) | 6 stati (A2: +ANNULLATA); 6 errori; sorgente OFFERTA_COMMERCIALE |
| 2 | APPLICATO | `20260524-03`, `20260524-10` | Testata + motivazione_rifiuto / data_annullamento (A1/A2) |
| 3 | APPLICATO | `20260524-05` .. `20260524-09` | Eccezioni + utilities + note partition + FK. Docs manual/ creati |
| 4 | APPLICATO | `20260524-21`, `20260524-22`, `20260524-23`, `20260525-04` | DDL transizioni + seed 5 trans. (A2) + trigger guard. Fix `20260525-04`: VARIADIC arg mancante in `fn_log_and_raise_error` per `E_OFFERTA_EMISSIONE_*` |
| 5 | APPLICATO | CSV `sistema_codici.csv` (id=17), `20260524-25`, `20260525-03` | Riga `offerta_commerciale`/`OFC` aggiunta. Fix `20260525-03`: sequenza `offerte_commerciali_codice_seq` mancante; `sync_gen_codice` aggiornato per crearla |
| 6 | APPLICATO | `20260524-26` (20_code/vendite) | `trgfn_offerte_commerciali_revisione` z90 AFTER INSERT. O4: no DEFERRED |
| 7 | APPLICATO | `20260524-27` (20_code/vendite) | `fn_crea_revisione_offerta(p_offerta_id, p_user)` RETURNS BIGINT |
| 8 | APPLICATO | `20260525-01` (00_schema/vendite) + `20260525-02` (20_code/vendite) | ALTER contratti: +offerta_id UNIQUE, +sorgente_tipo_id, +sorgente_uid. `fn_push_offerta_a_contratto`. UPSERT contratti_utilities |
| 9 | CHIUSO | `db/pgtap/vendite/offerte_commerciali/` (9 file) | Suite pgTAP completa. Tutti i test passati 2026-05-25 |

**File pgTAP**:

| File | Step | Test |
| ---- | ---- | ---- |
| `test_offerte_commerciali_struttura.sql` | 2 | Colonne, FK, UNIQUE uid, CHECK variazione globale |
| `test_offerte_commerciali_eccezioni_struttura.sql` | 3 | Mirror contratti_righe: enum, 5 CHECK, esclusione campi I4 |
| `test_offerte_commerciali_utilities_struttura.sql` | 3 | UNIQUE (offerta_id), mirror contratti_utilities |
| `test_offerte_commerciali_state_machine.sql` | 4 | 10 transizioni: ammesse/vietate + guard listino + timestamp |
| `test_offerte_commerciali_codice.sql` | 5 | Generazione `OFC-*` via `sistema_codici` |
| `test_offerte_commerciali_revisione_trigger.sql` | 6 | rev.N → SUPERATA al creare rev.N+1 |
| `test_fn_crea_revisione_offerta.sql` | 7 | Creazione rev.N+1: eccezioni + utility copiate; guard stati |
| `test_fn_push_offerta_a_contratto.sql` | 8 | Push corretto + idempotenza + copia eccezioni/utility 1:1 |
| `test_offerte_commerciali_end_to_end.sql` | 9 | Flusso completo BOZZA→EMESSA→ACCETTATA→contratto DRAFT |

---

*Brief DB Offerta Commerciale — ZeroErp. Revisione 2026-05-24 (correzioni
B1/B2/B3/I1/I2/I3/I4 + note O1/O4/O5). CHIUSO 2026-05-25: tutti gli step
applicati, suite pgTAP completa, tutti i test passati su `dev/db-tid`.*
