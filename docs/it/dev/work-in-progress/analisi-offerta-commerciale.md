# Analisi iniziale — Offerta commerciale come dominio separato

> **Stato**: ANALISI INIZIALE — nessuna decisione operativa, nessun codice toccato.
>
> **Scope**: valutare l'introduzione di un'entità `offerta_commerciale` (proposta di
> condizioni quadro) come predecessore tracciato del contratto, distinta dal preventivo
> (proposta di transazione puntuale).
>
> **Origine**: sessione 2026-05-15 nel contesto del refactor contratti
> ([`refactor-contratti-modalita.md`](../work-done/refactor-contratti-modalita.md)). Discutendo il
> modello prezzi dei preventivi (snapshot riga-per-riga) vs contratti (snapshot della
> versione listino, decisione §3-bis-A) è emersa la domanda: "ma forse il preventivo più
> che in un contratto dovrebbe andare in un'offerta commerciale o sbaglio?". Questo doc
> raccoglie le prime riflessioni per una decisione futura — non è in scope del refactor
> contratti corrente.

---

## 1. Stato attuale ZeroERP

### 1.1 Cosa esiste

- **Preventivo** (`vendite.preventivi` + `preventivi_righe`): proposta puntuale al cliente
  per articoli/prezzi specifici. Stato BOZZA → EMESSO → ACCETTATO. L'accettato genera una
  **commessa** via `push_a_commessa` ([preventivi_service.py:1910](../../../backend/apps/vendite/services/preventivi_service.py#L1910)),
  che entra nella pipeline fatturazione.
- **Contratto** (`vendite.contratti` + `contratti_righe` + `contratti_utilities`): relazione
  duratura cliente↔listino con eventuali variazioni/eccezioni. Stato DRAFT → ATTIVO →
  CESSATO. **Nasce direttamente dall'operatore**, senza essere preceduto da nessuna
  proposta formalizzata.

### 1.2 Cosa NON esiste

- Entità `offerta_commerciale` — nessuna tabella, service, view, doc.
- Flusso `push_a_contratto` (specchio di `push_a_commessa`) — non esiste perché manca il
  predecessore.
- Relazione tracciata fra preventivo e contratto — il preventivo va a commessa, mai a
  contratto.

### 1.3 Conseguenza operativa attuale

Quando un operatore tratta condizioni quadro con un cliente ("ti propongo listino X con
sconto Y per 12 mesi"), la negoziazione **non è tracciata** nel sistema:

- Niente documento di proposta
- Niente stato "in attesa di accettazione"
- Quando il cliente accetta, l'operatore crea direttamente il contratto in DRAFT
- L'unica traccia documentale è eventualmente un PDF/email allegato fuori sistema

---

## 2. La distinzione concettuale: preventivo vs offerta commerciale

Sotto il profilo del dominio commerciale "classico", i due artefatti hanno **scopo e
contenuto strutturalmente diversi**:

| Aspetto | Preventivo (esistente) | Offerta commerciale (proposta) |
| --- | --- | --- |
| **Cosa propone** | "Ti vendo questi 5 articoli a questi prezzi totale €X" | "Ti propongo di essere mio cliente al listino LST-001 con sconto 5% per 12 mesi" |
| **Scope temporale** | Una transazione puntuale | Condizioni quadro durature |
| **Cosa contiene** | Lista articoli + quantità + prezzi snapshottati | Listino di riferimento + variazione globale + eventuali eccezioni (OVERRIDE/ESCLUSIONE/AGGIUNTA proposti) |
| **Snapshot del prezzo** | Riga-per-riga (`prezzo_unitario` materializzato per articolo) | Versione del listino fissata (le righe non-eccezione leggono dinamicamente) |
| **Accettato diventa** | Commessa singola → fattura una tantum | Contratto attivo → pipeline fatturazione ricorrente |
| **Vita del documento** | Si chiude all'accettazione/scadenza | Resta come traccia storica della negoziazione del contratto |
| **Revisioni** | Già supportate (`fn_crea_revisione_preventivo`) | Stesso bisogno (rinegoziazione condizioni prima dell'accettazione) |

In altre parole: i **modelli di snapshot** che abbiamo isolato durante il refactor contratti
(§3-bis-A) sono in realtà già **specchio** della differenza fra i due artefatti:

- Snapshot riga-per-riga = chiude una transazione → preventivo → commessa
- Snapshot della versione listino = fissa una relazione → offerta commerciale → contratto

Il modello che stiamo costruendo per il contratto **postula implicitamente** l'esistenza
di una "proposta di condizioni" da cui nasce. Oggi quella proposta non è formalizzata,
ma il modello la presuppone.

---

## 3. Tre strade possibili

### 3.1 Opzione (a) — Restare come oggi

Il contratto nasce direttamente dall'operatore. Nessuna entità nuova, nessun flusso di
proposta. Eventuali documenti di trattativa restano fuori sistema (PDF, email).

**Pro**: zero lavoro. Lavora già così.

**Contro**:

- Negoziazione non tracciata → niente audit "perché abbiamo dato sconto 8% a questo cliente"
- Nessuna gestione di proposte rifiutate (oggi non esistono come oggetto)
- Asimmetria nel modello: il preventivo ha il suo flusso tracciato, il contratto no, anche
  se la negoziazione di un contratto è in genere più complessa di quella di un preventivo

### 3.2 Opzione (b) — Allegare il preventivo al contratto

Compromesso minimale: aggiungere una FK opzionale `contratti.preventivo_riferimento_id` per
permettere all'operatore di "citare" un preventivo come proposta di partenza del contratto.

**Pro**:

- Lavoro minimo (una colonna FK + campo UI)
- Qualche tracciabilità in più rispetto a (a)

**Contro**:

- Uso semanticamente improprio del preventivo: il preventivo è una proposta di transazione
  puntuale, non di condizioni quadro. Allegarlo a un contratto è una forzatura
- Non risolve il problema del **contenuto**: un preventivo lista articoli, un contratto è
  un quadro condizioni. Sono cose diverse, anche al netto della FK
- Diventa un'eccezione al modello dominio ("il preventivo a volte non va in commessa ma in
  contratto") che complica i flussi
- Il preventivo nel suo flusso normale va a commessa: che succede a un preventivo "allegato
  a un contratto"? È stato accettato sì/no? Va anche a commessa? Bivio non chiaro

### 3.3 Opzione (c) — Introdurre `offerta_commerciale` come entità separata

Nuovo dominio specchio del preventivo, ma per le condizioni quadro:

- Tabella `vendite.offerte_commerciali` (testata): `billing_account_id`, `utility_id`,
  `listino_proposto_id`, `valore_variazione_globale_proposta`, `validita_proposta`, stato,
  ecc.
- Eventuale tabella `vendite.offerte_commerciali_eccezioni` per OVERRIDE/ESCLUSIONE/AGGIUNTA
  proposti, simmetrica a `contratti_righe`
- Stati: BOZZA → EMESSA → ACCETTATA / RIFIUTATA / SCADUTA
- All'accettazione: `push_a_contratto` (specchio di `push_a_commessa`) — crea il contratto
  in DRAFT con i dati dell'offerta; l'operatore può attivarlo subito o raffinarlo
- Revisioni offerta come per i preventivi (stessa pattern `fn_crea_revisione_*`)

**Pro**:

- Modello dominio pulito e simmetrico:
  - Preventivo → Commessa (transazione puntuale)
  - Offerta commerciale → Contratto (relazione duratura)
- Tracciabilità completa della negoziazione, anche per offerte rifiutate
- Riusa il pattern preventivi (stati, revisioni, accettazione, push) — molto codice è
  trasponibile
- Si appoggia naturalmente al modello §3-bis-A dei contratti: l'offerta propone una
  versione listino di riferimento + eccezioni; alla creazione del contratto, lo snapshot
  della versione corrente è coerente con la decisione già presa

**Contro**:

- Lavoro consistente: nuovo dominio completo (schema + service + view + drawer + i18n + doc)
- Servono decisioni di modello che oggi non sono prese (vedi §5)

---

## 4. Mia preferenza preliminare

Sul merito del dominio commerciale, **(c) è la strada giusta**:

- Il preventivo è già al posto suo (transazione puntuale → commessa) e non va disturbato
- Il contratto presuppone una proposta di condizioni: oggi non c'è, va creata
- Il pattern preventivo è già rodato e riusabile per scaffolding rapido dell'offerta
- La simmetria del modello rende il sistema più prevedibile per l'operatore (e per gli
  sviluppatori futuri)

(b) viene scartata perché è una pezza semantica che non risolve il problema vero.

(a) è ammissibile **solo come stato transitorio** finché (c) non viene affrontata.

---

## 5. Decisioni di modello da prendere prima di scrivere brief DB

Queste sono le domande aperte che (c) richiede di chiudere:

### 5.1 Granularità dell'offerta

- L'offerta commerciale è **per (BA, utility)** come il contratto, o può essere **per
  cliente generale** (proposta di condizioni multiple utilities in un colpo solo)?
- Se cliente generale, può generare **più contratti** all'accettazione (uno per utility)?
  Modello 1:N tra offerta e contratti, complicazione non banale.

### 5.2 Contenuto delle "eccezioni proposte"

- L'offerta propone gli OVERRIDE/ESCLUSIONE/AGGIUNTA, o solo il listino + variazione
  globale e gli override sono dettaglio operativo del contratto?
- Se l'offerta propone anche le eccezioni: la tabella `offerte_commerciali_eccezioni`
  esiste, simmetrica a `contratti_righe`. Alla `push_a_contratto`, le eccezioni vengono
  copiate riga-per-riga in `contratti_righe`.
- Se solo testata: l'offerta è più leggera, l'operatore aggiungerà eccezioni post-creazione
  del contratto in DRAFT.

### 5.3 Listino di riferimento mobile prima dell'accettazione

- L'offerta cita una versione listino specifica al momento dell'emissione, o "qualunque
  versione attiva alla data di accettazione"?
- Conservativo: l'offerta fissa la versione listino corrente all'emissione (così il
  cliente sa esattamente cosa sta accettando). All'accettazione, se la versione listino
  è cambiata, **deve essere riemessa** (revisione offerta).
- Alternativa: l'offerta è "al listino corrente alla data di accettazione" → flessibile
  ma poco tracciabile (il cliente accetta condizioni che possono cambiare).

### 5.4 Workflow di accettazione

- Chi può accettare un'offerta? Solo l'operatore registrando l'accettazione del cliente,
  o esiste un meccanismo cliente-facing (futuro shop B2C / portal)?
- L'offerta accettata genera contratto DRAFT (operatore lo attiva quando pronto) o
  contratto ATTIVO immediatamente?

### 5.5 Cessazione retroattiva dell'offerta

- Se un'offerta è ACCETTATA ma il cliente recede entro N giorni (legge), il contratto
  generato va cessato. L'offerta resta nello storico come ACCETTATA o si rinegozia?
- Probabilmente: l'offerta è uno storico immutabile post-accettazione; il contratto
  generato segue il suo flusso normale di cessazione.

### 5.6 Numerazione e validità

- Numerazione delle offerte: serie dedicata (`OFC-*`) come per preventivi (`PRV-*`)?
- Validità dell'offerta: data scadenza obbligatoria? Default da parametro? Trigger DB di
  transizione SCADUTA via job notturno (pattern già usato per contratti cessazione data-driven)?

### 5.7 Relazione con preventivo

- Un preventivo può "evolvere" in offerta commerciale? (Caso: cliente chiede preventivo
  per acquisto puntuale, conversazione si evolve in proposta di condizioni quadro.)
- Probabilmente: no, sono entità separate. Se il cliente vuole condizioni quadro, si emette
  una nuova offerta. Il preventivo resta per la sua vita transazionale.

---

## 6. Cosa è fuori scope di questa analisi

- **Modello dati dettagliato**: non è una progettazione DB, è un'analisi di opportunità.
  Quando si decide di procedere, si scrive un brief DB separato.
- **Decisione su quando affrontarla**: questa analisi non implica priorità. Può restare in
  attesa finché altre priorità sono più calde.
- **Implicazioni sul refactor contratti corrente**: nessuna. Il refactor contratti chiude
  il modello "modalità A/B/C → unificato + delta + versione listino"; quel modello è
  preparato per ricevere un push da offerta in futuro, ma non lo richiede oggi.

---

## 7. Stato e prossimi passi

- ⏳ **APERTO** — analisi iniziale, nessuna decisione presa.
- Decisione di percorrere o no l'opzione (c) → da prendere in sessione dedicata con Tid,
  non bloccante per altri lavori.
- Quando si vuole procedere:
  - Chiusura §5 (decisioni di modello)
  - Brief DB con schema + funzioni
  - Piano operativo (BE + FE + doc) sul pattern preventivi-like
  - Doc `modello-offerta-commerciale.md` come reference del nuovo dominio

## 8. Riferimenti incrociati

- [`refactor-contratti-modalita.md`](../work-done/refactor-contratti-modalita.md) — refactor contratti
  corrente; questa analisi è uscita dalla sua §3-bis-A
- [`recap-contratti-post-componenti.md`](../work-done/recap-contratti-post-componenti.md) — recap bug
  contratti post-componenti, contesto operativo
- `api_preventivi.md` — modello preventivi esistente, riferimento per pattern riusabile
- `push_a_commessa` ([preventivi_service.py:1910](../../../backend/apps/vendite/services/preventivi_service.py#L1910)) —
  flusso accettazione che ispira `push_a_contratto`
