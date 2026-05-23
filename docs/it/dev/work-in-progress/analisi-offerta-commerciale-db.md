# Brief DB — Dominio `vendite.offerte_commerciali` (Step di sviluppo)

> **Stato**: BRIEF in attesa del team DB. Nessuna migration ancora scritta.
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
>   (decisioni di modello tutte chiuse)
> - [analisi-pratiche-domini-anello3.md](analisi-pratiche-domini-anello3.md)
>   §6.9 (convenzione idempotenza cross-dominio) e §11.2.4 (forma idempotenza
>   `push_a_contratto`)
> - `docs/it/linee-guida-sql.md`, `docs/it/linee-guida-trigger.md`,
>   `docs/it/liquibase-setup-workflow.md` (workflow autorizzativo team DB)
> - `docs/it/dbzero/vendite/manual/contratti.md` (specchio strutturale per
>   `offerte_commerciali` testata + `contratti_righe` per `offerte_commerciali_eccezioni`)
> - `docs/it/dbzero/vendite/manual/preventivi.md` (pattern revisioni
>   `fn_crea_revisione_*`, riusabile per offerte)

---

## 1. Inquadramento del lavoro

### 1.1 Obiettivo

Introdurre nello schema `vendite` il dominio dell'offerta commerciale come
**predecessore tracciato del contratto**, asimmetrico al preventivo
(preventivo→commessa/ordine = transazione puntuale; offerta→contratto =
condizioni quadro). Il dominio deve essere immediatamente capace di:

1. Emettere offerte numerate `OFC-*` per `(billing_account_id, scope)`.
2. Tracciare la negoziazione con stati BOZZA → EMESSA → ACCETTATA / RIFIUTATA.
3. Congelare la versione del listino di riferimento all'emissione (decisione
   §5.3 dell'analisi: scartata l'opzione "listino mobile alla data di
   accettazione").
4. Portare le proprie eccezioni proposte (OVERRIDE / ESCLUSIONE / AGGIUNTA)
   come tabella mirror di `contratti_righe` (decisione §5.2).
5. Eseguire il push 1:1 a contratto DRAFT con **idempotenza per costruzione**
   (pattern A §6.9.3 del documento pratiche, partial UNIQUE su
   `contratti(sorgente_uid)` per sorgente `OFFERTA_COMMERCIALE`).
6. Supportare revisioni come per i preventivi (`fn_crea_revisione_*`), con
   transizione automatica della precedente a `SUPERATA` (decisione §5.3:
   "rev.2 supera rev.1").

### 1.2 Cosa NON deve fare in v1 (predisposizioni future)

In coerenza con manifesto §7 e §5.1-bis dell'analisi, **non vanno introdotti in
v1**:

- **Pacchetto commerciale multi-contratto**: `vendite.pacchetti_commerciali`
  non esiste in v1. La FK predisposta `offerte_commerciali.pacchetto_id` non
  va inserita ora (sarebbe una colonna senza dominio). Il refactor futuro
  l'aggiungerà come step additivo (mezza giornata, vedi §5.1-bis dell'analisi).
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

---

## 2. Inventario complessivo delle modifiche

Riepilogo di tutto ciò che il brief introduce, distinto per categoria. Gli
**step §3** atomizzano queste modifiche in ordine di applicabilità.

### 2.1 Tabelle nuove

| Schema    | Tabella                                | Scopo                                                                     |
| --------- | -------------------------------------- | ------------------------------------------------------------------------- |
| `vendite` | `offerte_commerciali`                  | Testata offerta (BA, scope, listino + versione fissata, validità, stato)  |
| `vendite` | `offerte_commerciali_eccezioni`        | Mirror funzionale di `contratti_righe` per OVERRIDE / ESCLUSIONE / AGGIUNTA |
| `vendite` | `offerte_commerciali_utilities`        | 1:N tra offerta e utilities (mirror funzionale di `contratti_utilities`)  |

### 2.2 ALTER su tabelle esistenti

| Tabella             | ALTER                                                                  | Motivazione                                                  |
| ------------------- | ---------------------------------------------------------------------- | ------------------------------------------------------------ |
| `vendite.contratti` | `ADD COLUMN offerta_id BIGINT NULL` + `UNIQUE (offerta_id)`            | §5.1-bis: idempotenza pattern A                              |
| `vendite.contratti` | `ADD COLUMN sorgente_tipo_id BIGINT NULL` + `ADD COLUMN sorgente_uid UUID NULL` | Verificato 2026-05-23 su `dbzero/vendite/tabelle/contratti.md`: i due campi NON esistono. Aggiungerli per simmetria con `vendite.ordini` / `vendite.commesse_sorgenti` |

> **Verifica DB pre-brief (2026-05-23)**: l'introspezione di
> `dbzero/vendite/tabelle/contratti.md` ha confermato che `vendite.contratti`
> ha solo `uid` (UNIQUE) e `parent_contratto_id` (FK self per relazioni
> contratto-padre/figlio), ma **non** ha `sorgente_tipo_id` né `sorgente_uid`.
> Gli ALTER del brief li aggiungono. Il campo `parent_contratto_id` esistente
> ha semantica diversa (contratto interno padre→figlio) e non va confuso col
> push da offerta.

### 2.3 Funzioni e trigger nuovi

| Oggetto                                           | Tipo            | Step | Scopo                                                                                |
| ------------------------------------------------- | --------------- | ---- | ------------------------------------------------------------------------------------ |
| `vendite.fn_crea_revisione_offerta`               | Function        | 7    | Pattern preventivi: rev.N+1 eredita, rev.N va in SUPERATA                            |
| `vendite.fn_push_offerta_a_contratto`             | Function        | 8    | Crea contratto DRAFT, copia eccezioni 1:1, idempotente per costruzione               |
| `vendite.trgfn_offerte_commerciali_guard_transizione` | Trigger fn  | 4    | State machine BOZZA→EMESSA→ACCETTATA/RIFIUTATA (immutabile post-accettazione)        |
| `vendite.trgfn_offerte_commerciali_revisione`     | Trigger fn      | 6    | Quando crea rev.N+1, marca rev.N come SUPERATA automaticamente                       |
| `vendite.trgfn_offerte_commerciali_gen_codice`    | Trigger fn      | 5    | Generato automaticamente da `script.fn_generate_codice()` via `sistema_codici`       |
| Guard listino versione attiva all'emissione       | Trigger fn      | 4    | Check `version_listino_id` ATTIVA al passaggio BOZZA→EMESSA                          |

### 2.4 Seed

| Tabella                                   | Riga(e) da seedare                                                         | Step |
| ----------------------------------------- | -------------------------------------------------------------------------- | ---- |
| `config.sorgenti`                         | `OFFERTA_COMMERCIALE` (singolare maiuscolo, convenzione §6.3 pratiche)     | 1    |
| `config.sistema_codici`                   | Riga `offerta_commerciale` con prefisso `OFC` (analogo a `PRV` preventivi) | 5    |
| `config.messaggi_errore`                  | 5 codici nuovi (vedi §4)                                                   | 1    |
| `config.stati_doc_offerte`                | 5 righe: BOZZA, EMESSA, ACCETTATA, RIFIUTATA, SUPERATA                     | 2    |
| `config.stati_doc_offerte_transizioni`    | Tabella delle transizioni ammesse (vedi §3 step 4)                         | 4    |

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

| Colonna                       | Tipo                | Obbligatoria      | Note di modello                                                                                   |
| ----------------------------- | ------------------- | ----------------- | ------------------------------------------------------------------------------------------------- |
| `id`                          | BIGINT IDENTITY PK  | sì                | Tecnico                                                                                           |
| `uid`                         | UUID UNIQUE         | sì                | Per FK `contratti.sorgente_uid` (pattern §6.3 pratiche, naturale per push)                        |
| `codice`                      | TEXT                | sì (auto, step 5) | Generato `OFC-0000001` da `sistema_codici` (step 5)                                               |
| `emittente_fiscale_id`        | BIGINT FK           | sì                | Coerente con preventivi/contratti                                                                 |
| `billing_account_id`          | UUID FK             | sì                | Scope cliente (vincolo §5.1: 1 offerta per scope)                                                 |
| `listino_id`                  | BIGINT FK           | sì                | Listino di riferimento                                                                            |
| `listino_versione_id`         | BIGINT FK           | sì                | **Versione fissata all'emissione** (§5.3). NOT NULL dopo EMESSA, NULL ammesso solo in BOZZA       |
| `valore_variazione_globale`   | NUMERIC             | no                | Variazione % globale proposta (default 0)                                                         |
| `tipo_variazione_globale_id`  | BIGINT FK           | no                | FK a tabella tipi variazione (specchio contratti)                                                 |
| `validita_dal`                | DATE                | sì                | Validità dell'offerta proposta al cliente                                                         |
| `validita_al`                 | DATE                | no                | Scadenza dell'offerta (segnalazione, non bloccante §5.6)                                          |
| `stato_doc_offerta_id`        | BIGINT FK           | sì                | Default BOZZA. FK a `config.stati_doc_offerte` (step 4)                                           |
| `revisione_numero`            | INTEGER             | sì                | Default 1; +1 per revisione (step 7)                                                              |
| `revisione_padre_id`          | BIGINT FK self      | no                | NULL su rev.1, FK a rev.N-1 su rev.N+1                                                            |
| `data_emissione`              | TIMESTAMPTZ         | no                | Valorizzata al passaggio BOZZA→EMESSA (trigger step 4)                                            |
| `data_accettazione`           | TIMESTAMPTZ         | no                | Valorizzata al passaggio EMESSA→ACCETTATA                                                         |
| `data_rifiuto`                | TIMESTAMPTZ         | no                | Valorizzata al passaggio EMESSA→RIFIUTATA                                                         |
| `note`                        | TEXT                | no                | Note libere offerta                                                                               |
| `meta`                        | JSONB               | sì                | Default `'{}'` per estensioni future controllate                                                  |
| Audit fields                  | (standard)          | sì                | `tx_id`, `data_insert`, `user_insert`, `data_update`, `user_update`                               |

**Vincoli**:

- `UNIQUE (uid)` (per FK pattern A da contratti).
- `CHECK (stato_id IN BOZZA OR listino_versione_id IS NOT NULL)` non
  esprimibile direttamente con CHECK (richiede subquery): da implementare come
  trigger guard in step 4.
- Nessun UNIQUE su `(billing_account_id, ...)` in v1: la decisione "1 offerta
  attiva alla volta per BA" è di policy, non strutturale. Si valuta dopo
  l'introduzione del pacchetto commerciale (§5.1-bis).

**Test**: pgTAP `test_offerte_commerciali_struttura.sql` verifica esistenza
tabella + colonne + FK + UNIQUE su uid.

### Step 3 — Tabelle `offerte_commerciali_eccezioni` + `offerte_commerciali_utilities`

**Scopo**: introdurre i dettagli dell'offerta speccchiando `contratti_righe`
e `contratti_utilities`.

**`offerte_commerciali_eccezioni`** (mirror di `vendite.contratti_righe`):

Il team DB allinea **una a una** le colonne strutturali di `contratti_righe`
sostituendo `contratto_id` con `offerta_id`. Includere almeno:

- `offerta_id` (FK NOT NULL)
- `articolo_id`
- `tipo_eccezione_id` (FK: OVERRIDE / ESCLUSIONE / AGGIUNTA)
- prezzo unitario / quantità / sconto / variazione, secondo modello contratti
- audit fields standard

Decisione di modello (richiamo §5.2): copia 1:1 a push_a_contratto, **senza
reinterpretazione**. Le due tabelle hanno la stessa semantica delle eccezioni;
sono separate fisicamente per ovvi motivi di FK ma la struttura colonne è
identica (eccetto la FK al padre).

**`offerte_commerciali_utilities`** (mirror di `vendite.contratti_utilities`):

Tabella ponte 1:N offerta → utility, identica a `contratti_utilities`.
Necessaria perché un'offerta può scope-are su una o più utility del cliente,
e alla push 1:1 il contratto eredita lo stesso scope utility.

**Test**: pgTAP `test_offerte_commerciali_eccezioni_struttura.sql` +
`test_offerte_commerciali_utilities_struttura.sql`. Verifica strutturale.

### Step 4 — State machine offerte (trigger guard + transizioni)

**Scopo**: rendere `vendite.offerte_commerciali.stato_doc_offerta_id`
config-driven, allineato al pattern già usato per preventivi e contratti
(vedi `stati_doc_contratti` + relative transizioni esistenti).

**Deliverable**:

- Seed `config.stati_doc_offerte` con 5 righe:
  - `BOZZA` (iniziale, editabile)
  - `EMESSA` (proposta al cliente, immutabile sui dati propri)
  - `ACCETTATA` (terminale positivo, immutabile)
  - `RIFIUTATA` (terminale negativo, immutabile)
  - `SUPERATA` (terminale tecnico, valorizzato dal trigger revisione step 6)
- Seed `config.stati_doc_offerte_transizioni` (oppure
  `config.transizioni_stati_doc_offerte` a scelta del team DB per coerenza con
  i naming già scelti su preventivi/pratiche) con le sole transizioni ammesse:
  - BOZZA → EMESSA, BOZZA → RIFIUTATA (annullamento bozza)
  - EMESSA → ACCETTATA, EMESSA → RIFIUTATA, EMESSA → SUPERATA
  - Nessuna transizione uscente da ACCETTATA, RIFIUTATA, SUPERATA (immutabili)
- Trigger `trgfn_offerte_commerciali_guard_transizione` BEFORE UPDATE OF
  `stato_doc_offerta_id` ON `vendite.offerte_commerciali`:
  - Verifica transizione in `config.stati_doc_offerte_transizioni`
  - Valorizza `data_emissione`/`data_accettazione`/`data_rifiuto` al passaggio
  - Guard: in BOZZA→EMESSA verifica che `listino_versione_id` non sia NULL
    e che la versione listino sia ATTIVA al momento dell'emissione (decisione
    §5.3)
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
    - UPDATE `vendite.offerte_commerciali` SET `stato_id = SUPERATA`
      WHERE `id = NEW.revisione_padre_id`
  - Trigger fase `_z90_` (deferred, vedi linee-guida-trigger.md)

**Test**: `test_offerte_commerciali_revisione_trigger.sql`:

- INSERT offerta rev.2 con `revisione_padre_id = rev.1.id` → rev.1 passa a
  SUPERATA
- INSERT offerta rev.1 con `revisione_padre_id = NULL` → nessuno stato altrui
  cambia

### Step 7 — `fn_crea_revisione_offerta`

**Scopo**: funzione di alto livello che crea rev.N+1 ereditando da rev.N
(testata + eccezioni + utilities), come pattern già fatto per preventivi.

**Deliverable**:

- Function `vendite.fn_crea_revisione_offerta(p_offerta_id BIGINT, p_motivazione TEXT) RETURNS BIGINT`
- Logica:
  - Carica rev.N (parametro). Errore se non in EMESSA (rev.N+1 si fa solo per
    offerte EMESSE, non ACCETTATE/RIFIUTATE/SUPERATE/BOZZA).
  - INSERT testata rev.N+1: nuovo uid, nuovo codice (via sistema_codici),
    `revisione_numero = rev.N.revisione_numero + 1`, `revisione_padre_id =
    p_offerta_id`, stato BOZZA, dati copiati da rev.N (listino,
    variazione, validità ricalcolata).
  - Copia eccezioni rev.N → eccezioni rev.N+1.
  - Copia utilities rev.N → utilities rev.N+1.
  - Trigger step 6 reagisce all'INSERT e marca rev.N come SUPERATA.
  - Restituisce id della rev.N+1.
- Errori semantici (vedi §4):
  - rev.N non in EMESSA: `E_OFFERTA_REVISIONE_STATO_NON_AMMESSO`

**Test**: `test_fn_crea_revisione_offerta.sql`:

- creazione rev.2 da rev.1 EMESSA → rev.1 SUPERATA, rev.2 BOZZA, eccezioni
  copiate
- creazione rev.2 da rev.1 ACCETTATA → fallisce
- creazione rev.2 da rev.1 BOZZA → fallisce (non si revisiona una bozza, la si
  modifica direttamente)

### Step 8 — `fn_push_offerta_a_contratto` (idempotente per costruzione)

**Scopo**: alla `ACCETTAZIONE` di un'offerta, crea il contratto in DRAFT
copiando eccezioni e utilities 1:1. **Idempotenza obbligatoria**: doppia
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
  - Carica offerta. Errore se non in ACCETTATA o RIFIUTATA: `E_OFFERTA_PUSH_STATO_NON_AMMESSO`.
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
    - copia `billing_account_id`, `emittente_fiscale_id`, `listino_id`,
      `listino_versione_id`, `valore_variazione_globale`, ecc.
  - Copia `offerte_commerciali_eccezioni` → `contratti_righe` (1:1, senza
    reinterpretazione, §5.2).
  - Copia `offerte_commerciali_utilities` → `contratti_utilities`.
  - Se `p_pratica_id IS NOT NULL`, INSERT in `pratiche.pratiche_sorgenti`
    con `(pratica_id, sorgente_tipo_id=CONTRATTO, sorgente_uid=contratto.uid, ruolo='COLLEGATO')`.
  - Restituisce l'id del contratto creato.
- Trigger AFTER per registrazione giornale pratica se `p_pratica_id` valorizzato
  (delegato a `pratiche_service.log_evento_dominio()` lato applicativo; il DB
  non scrive nel giornale pratica autonomamente).

**Test obbligatorio §6.9.5 pratiche**: `test_fn_push_offerta_a_contratto.sql`:

- push offerta ACCETTATA → contratto in DRAFT, eccezioni copiate, utilities
  copiate, `offerta_id` valorizzato
- **doppia invocazione su stessa offerta → seconda invocazione fallisce con
  `E_OFFERTA_CONTRATTO_GIA_GENERATO`, nessun contratto duplicato**
- push offerta BOZZA/EMESSA/RIFIUTATA → fallisce con `E_OFFERTA_PUSH_STATO_NON_AMMESSO`
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

| Codice                                                 | Severity | Messaggio (it_IT)                                                                        |
| ------------------------------------------------------ | -------- | ---------------------------------------------------------------------------------------- |
| `E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO`           | ERROR    | "Impossibile emettere l'offerta: versione del listino di riferimento non impostata."     |
| `E_OFFERTA_EMISSIONE_VERSIONE_LISTINO_NON_ATTIVA`      | ERROR    | "Impossibile emettere l'offerta: la versione del listino indicata non è ATTIVA."         |
| `E_OFFERTA_TRANSIZIONE_NON_AMMESSA`                    | ERROR    | "Transizione di stato dell'offerta non ammessa: %s → %s."                                |
| `E_OFFERTA_REVISIONE_STATO_NON_AMMESSO`                | ERROR    | "Impossibile creare una revisione: l'offerta deve essere in stato EMESSA."               |
| `E_OFFERTA_PUSH_STATO_NON_AMMESSO`                     | ERROR    | "Impossibile generare il contratto: l'offerta deve essere in stato ACCETTATA."           |
| `E_OFFERTA_CONTRATTO_GIA_GENERATO`                     | ERROR    | "L'offerta %s ha già generato il contratto: invocazione duplicata non consentita."        |

> **Codici aggiuntivi attesi durante implementazione**: il team DB può
> aggiungere codici granulari se durante lo sviluppo emergono guard più fini
> (es. `E_OFFERTA_EMISSIONE_BA_INATTIVO`). La regola è: ogni guard con
> messaggio operativo per l'operatore → un codice in
> `config.messaggi_errore.csv`. Nessuna `RAISE EXCEPTION` libera senza codice.

---

## 5. Mappa coperturapgTAP (riepilogo per step)

| Step | File pgTAP                                          | Cosa verifica                                                          |
| ---- | --------------------------------------------------- | ---------------------------------------------------------------------- |
| 2    | `test_offerte_commerciali_struttura.sql`            | Esistenza tabella + colonne + FK + UNIQUE                              |
| 3    | `test_offerte_commerciali_eccezioni_struttura.sql`  | Esistenza tabella + mirror corretto di `contratti_righe`               |
| 3    | `test_offerte_commerciali_utilities_struttura.sql`  | Esistenza tabella + mirror corretto di `contratti_utilities`           |
| 4    | `test_offerte_commerciali_state_machine.sql`        | Tutte le transizioni ammesse e tutte quelle vietate + guard listino    |
| 5    | `test_offerte_commerciali_codice.sql`               | Generazione `OFC-*` via `sistema_codici`                               |
| 6    | `test_offerte_commerciali_revisione_trigger.sql`    | rev.N → SUPERATA al creare rev.N+1                                     |
| 7    | `test_fn_crea_revisione_offerta.sql`                | Creazione rev.N+1 corretta (eccezioni + utilities copiate)             |
| 8    | `test_fn_push_offerta_a_contratto.sql`              | Push corretto + **idempotenza obbligatoria** + copia eccezioni 1:1     |
| 9    | `test_offerte_commerciali_end_to_end.sql`           | Flusso completo BOZZA → EMESSA → ACCETTATA → contratto DRAFT           |

Tutti i test pgTAP devono avere `# Indice test (0..N):` nell'header (regola
AGENTS.md §Test).

---

## 6. Coerenza con altri brief e domini

### 6.1 Con il modello pratiche

- Il dominio offerta è il prerequisito dell'asse `OFFERTA_QUADRO` descritto in
  [analisi-pratiche-domini-anello3.md](analisi-pratiche-domini-anello3.md) §11.2.
- L'idempotenza pattern A di `fn_push_offerta_a_contratto` è **identica** al
  pattern descritto in §6.9.3 di quel documento e già usato per
  `fn_push_preventivo_a_ordine` (decisione §5.3.3).
- Lo step 1 (seed `OFFERTA_COMMERCIALE` in `config.sorgenti`) è citato anche
  in [analisi-pratiche-domini-anello3.md](analisi-pratiche-domini-anello3.md)
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
  standard (vedi `templates/python-header.txt` per backend, e i manual
  esistenti come riferimento per la doc DB).
- **Dubbi di modello**: se durante l'implementazione emerge un dubbio di
  modello (es. "questo CHECK ha senso?"), va sollevato a Tid via
  [analisi-offerta-commerciale.md](analisi-offerta-commerciale.md), non
  risolto unilateralmente nel brief.

---

## 8. Stato del brief

| Step | Stato      | Dipendenze              | Note                                                             |
| ---- | ---------- | ----------------------- | ---------------------------------------------------------------- |
| 1    | Pronto     | nessuna                 | Seed minimi, applicabile per primo                               |
| 2    | Pronto     | 1                       | Testata offerta                                                  |
| 3    | Pronto     | 2                       | Eccezioni + utilities                                            |
| 4    | Pronto     | 2, 3                    | State machine + guard listino                                    |
| 5    | Pronto     | 2                       | Numerazione (verificare prerequisito `sistema_codici` presente)  |
| 6    | Pronto     | 4                       | Trigger reattivo revisione                                       |
| 7    | Pronto     | 6                       | fn_crea_revisione_offerta                                        |
| 8    | Pronto     | 4 (stato ACCETTATA)     | fn_push_offerta_a_contratto + idempotenza obbligatoria           |
| 9    | Pronto     | 1-8 completati          | Suite pgTAP end-to-end                                           |

---

*Brief DB Offerta Commerciale — ZeroErp. Pronto per applicazione team DB su
`dev/db-tid` dopo OK Tid. Documento vivo, da aggiornare a ogni step chiuso.*
