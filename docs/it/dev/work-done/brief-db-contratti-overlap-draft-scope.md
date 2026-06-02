# Brief DB — Overlap contratti: escludere i DRAFT dal vincolo (esclusività solo all'attivazione)

> **Branch**: `dev/db-tid`. **Destinatario**: team DB.
> **Natura**: brief di **logica e requisiti**, NON specifica implementativa. Qui c'è
> *cosa* serve e *perché*; la **strada (firme, nomi colonna/snapshot, struttura changeset)
> la sceglie il team DB**.
> **Origine**: follow-up di [refactor-overlap.md §3.4](refactor-overlap.md) +
> [refactor-overlap-v2.md](refactor-overlap-v2.md). Decisione funzionale chiusa da Tid
> (2026-06-02): vedi §0.
> **Vincolo**: ZeroErp NON in produzione → breaking change ammessi.

---

## 0. Decisione funzionale (chiusa da Tid, 2026-06-02)

Due punti aperti del brief overlap, ora risolti:

1. **§2.4 — chiave del vincolo**: COMMERCIO e COMMODITY sullo stesso
   `billing_account + istanza_utility + utility + periodo` **possono legittimamente
   coesistere**. → `ambito` **resta** nella chiave dell'EXCLUDE. **Nessuna modifica**,
   solo conferma/documentazione. (Era la diagnosi del falso allarme CNT0000027/0033.)

2. **§3.4 — scope DRAFT**: l'esclusività "niente forniture sovrapposte" deve valere
   **solo all'attivazione**. I contratti in **DRAFT vanno ESCLUSI** dal vincolo. Cioè:
   - due contratti **DRAFT** sovrapposti sulla stessa quadrupla → **ammessi**;
   - un **DRAFT** sovrapposto a un contratto **attivo** → **ammesso** (puoi *preparare*
     in bozza il contratto della successione);
   - l'overlap è bloccato **solo** quando il contratto **non è più DRAFT** (attivazione
     o stati successivi che rappresentano una fornitura reale).

   Questo abilita il flusso di successione: preparo il nuovo contratto in bozza
   sovrapposto all'incumbent, e al momento di **attivarlo** devo prima chiudere
   l'incumbent (`valido_al`) — l'EXCLUDE scatta sull'attivazione, non sulla bozza.

---

## 1. Stato attuale (baseline verificata su codice)

- **EXCLUDE** `ex_contratti_no_overlap` (migration `20260521-03`):
  `EXCLUDE USING gist (billing_account_id WITH =, istanza_utility_id WITH =,
  utility_id WITH =, ambito WITH =, validita WITH &&) WHERE (NOT is_abortito_snapshot)`.
  → oggi un DRAFT **è incluso** (non è abortito) ⇒ blocca le bozze sovrapposte.
- **Snapshot di supporto** `vendite.contratti.is_abortito_snapshot` (colonna,
  migration `20260521-01`) sincronizzata dal trigger BEFORE
  `trgfn_contratti_sync_is_abortito_snapshot` (`20260521-02`, fase z90, evento
  `INSERT OR UPDATE OF stato_doc_contratto_id`) leggendo `config.stati_doc_contratti`.
  È il pattern da riusare: l'EXCLUDE può referenziare **solo colonne della stessa riga**,
  quindi lo stato DRAFT va materializzato come snapshot, non risolto via JOIN nel `WHERE`.
- **Framework** `dbops.automazione_overlap`: riga `vendite.contratti` registrata
  (`20260602-10`) con `where_predicate = 'NOT is_abortito_snapshot'`, `active=true`,
  `constraint_name='ex_contratti_no_overlap'`. Il runner notturno `automations_overlap`
  ri-crea il constraint da questa riga → **va aggiornata** o il predicato vecchio
  tornerebbe alla prima auto-guarigione.
- **`fn_contratto_sovrapposto`** (`20260531-02`, STABLE): ritorna l'id del contratto
  **non abortito** sovrapposto (stesso predicato dell'EXCLUDE, senza il filtro DRAFT).
  Usata dal push offerta→contratto e (a breve) come pre-check applicativo lato BE.

---

## 2. Cosa serve (requisiti)

### 2.1 Materializzare lo stato "DRAFT" come snapshot di riga

Serve, sulla riga `vendite.contratti`, un predicato **same-row** che dica "questo
contratto è in DRAFT (non partecipa al vincolo di overlap)". Speculare a
`is_abortito_snapshot`. **Strada a scelta del team DB**, due opzioni equivalenti:

- **opzione A** — nuova colonna snapshot dedicata (es. `is_draft_snapshot`),
  sincronizzata dallo **stesso** trigger `trgfn_contratti_sync_is_abortito_snapshot`
  (già scatta su `stato_doc_contratto_id`): aggiungere il set di
  `is_draft_snapshot = (codice_interno = 'DRAFT')` leggendo `config.stati_doc_contratti`;
- **opzione B** — un unico snapshot "partecipa all'overlap" (es.
  `partecipa_overlap_snapshot = NOT abortito AND NOT draft`) che assorbe entrambi i
  filtri, semplificando il `WHERE` a `WHERE partecipa_overlap_snapshot`.

Vincoli: niente magic-string `'DRAFT'` sparsa — usare `config.stati_doc_contratti`
come fonte (codice_interno, lockato da trigger) come fa già il sync abortito. Il
trigger resta **BEFORE** (le STORED generated, es. `validita_attiva`, sono calcolate
dal NEW finale dei BEFORE — vedi nota in `20260521-02`).

### 2.2 Aggiornare il predicato dell'EXCLUDE

`ex_contratti_no_overlap` deve escludere **sia** abortiti **sia** draft:
- opzione A → `WHERE (NOT is_abortito_snapshot AND NOT is_draft_snapshot)`;
- opzione B → `WHERE (partecipa_overlap_snapshot)`.

Prerequisito dati: **censimento** delle coppie DRAFT↔attivo (e DRAFT↔DRAFT) oggi
*inesistenti perché vietate*; al rilassamento del predicato non si creano violazioni
(si **allenta**, non si stringe) → nessuna bonifica, il `DROP CONSTRAINT`+`ADD` ricostruisce
pulito. Da rivalutare solo se nel frattempo cambia la semantica in senso restrittivo.

### 2.3 Aggiornare la registrazione nel framework (anti-regressione)

Riga `dbops.automazione_overlap` di `vendite.contratti` (`20260602-10`):
`where_predicate` deve combaciare **esattamente** col nuovo predicato dell'EXCLUDE
(opzione A o B), altrimenti il runner notturno `automations_overlap` ricreerebbe il
constraint col predicato vecchio (DRAFT di nuovo incluso). Aggiornare via UPSERT
idempotente sulla PK `(target_schema, target_table)`.

### 2.4 Allineare `fn_contratto_sovrapposto`

La funzione deve riflettere la **stessa** semantica: ignorare i contratti DRAFT
nel set dei conflitti (oltre agli abortiti). Così il **pre-check applicativo** (BE,
in arrivo — guard su create/attivazione manuale) e il **push offerta→contratto**
restano coerenti con l'EXCLUDE: un DRAFT non è un "incumbent" che blocca.

> Sottigliezza per il push: alla **attivazione** del contratto della successione,
> `fn_contratto_sovrapposto` deve vedere l'incumbent attivo e pretendere che sia
> chiuso *prima* (close-before-activate, stessa transazione) — invariato rispetto a
> oggi. Ciò che cambia è solo che un candidato/incumbent **DRAFT** non conta.

### 2.5 Test pgTAP

Estendere/aggiungere ai test contratti la matrice del nuovo scope:
- due DRAFT sovrapposti (stessa quadrupla) → **ammessi** (no `23P01`);
- DRAFT sovrapposto ad attivo → **ammesso**;
- attivazione di un contratto sovrapposto a un attivo → **bloccato** (`23P01`);
- abortito sovrapposto → **ammesso** (invariato);
- `fn_contratto_sovrapposto`: ritorna NULL quando l'unico "conflitto" è un DRAFT;
  ritorna l'incumbent quando è attivo.
- anti-regressione framework: dopo `DROP`+`fn_apply('SCHEDULED', false)` il constraint
  si ricrea col predicato **nuovo** (DRAFT esclusi) — non quello vecchio.

---

## 3. Cosa NON cambia

- `ambito` resta nella chiave (§2.4 confermato).
- Convenzione SR/PK, gli altri 5 EXCLUDE parziali (listini/promo/categorie/template):
  **fuori scope**, già corretti.
- Il backend mappa già `ex_contratti_no_overlap` → `E_VENDITE_CONTRATTO_OVERLAP` (409):
  resta valido, scatterà ora **all'attivazione** invece che alla creazione bozza.

---

## 4. Dipendenza a valle (BE)

Sbloccato questo brief, il backend implementa il **guard proattivo §3.3**: pre-check
`fn_contratto_sovrapposto` su create/attivazione manuale del contratto, con messaggio
che **nomina il contratto in conflitto** (valore aggiunto vs l'IntegrityError già
mappato). Il guard **attende** la nuova semantica (DRAFT esclusi) per non bloccare la
preparazione delle bozze di successione.
