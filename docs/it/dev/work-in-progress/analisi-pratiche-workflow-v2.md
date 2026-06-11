# Pratiche workflow v2 — analisi e decisioni

> **Tipo documento**: analisi di modello (linguaggio volutamente semplice, con
> esempi). **Data**: 2026-06-11 · **Stato**: 🟡 in discussione — le decisioni
> D1..D4 attendono ratifica di Tid.
>
> **Origine**: riverifica dell'analisi iniziale
> ([analisi-pratiche-domini-anello3](analisi-pratiche-domini-anello3.md),
> [gestione-pratiche-v2](gestione-pratiche-v2.md),
> [crm-ticketing-pratiche](crm-ticketing-pratiche.md)) rispetto a 5 esigenze
> emerse il 2026-06-11, dopo la validazione runtime del giro pratica
> PREVENTIVI. Scopo delle pratiche: **concentrare il più possibile le attività
> al loro interno** — per riuscirci il motore deve diventare un vero workflow.

---

## 0. La fotografia in una tabella

| # | Esigenza | Già previsto? | Cosa manca |
|---|---|---|---|
| 1 | Vedere le pratiche raggruppate per ruolo soggetto (e istanza, e interne) | il **dato** c'è, la **vista** no | filtri e raggruppamento in lista/coda |
| 2 | Pratiche interne e su istanza come eccezioni | sì, già nel modello | solo ratificare: niente "ruolo operatore" |
| 3 | Flussi ripetibili (es. appuntamento andato male) vs flussi unici | non trattato da nessun documento | una regola di ripetibilità sul template |
| 4 | Workflow condizionale (percorsi che cambiano in base all'esito) | esprimibile già oggi, mai usato | semantica dei rami + un caso reale seedato |
| 5 | Flussi che generano altre pratiche in automatico | già operativo a DB, mai esercitato | primo consumatore + verifica runtime |

Il messaggio di fondo: **il motore è stato costruito più completo di quanto i
processi finora gli abbiano chiesto**. Tre delle cinque esigenze sono
soddisfatte (o quasi) dal modello esistente; i veri buchi sono la vista per
contesto (tema 1) e la ripetibilità (tema 3).

---

## 1. Le pratiche viste dal contesto anagrafico

### Il problema, con un esempio

Oggi apro la dashboard e vedo "tutte le pratiche dell'emittente". Ma
l'operatore ragiona così: *"sto lavorando sul **ruolo cliente** di Rossi SRL —
quali pratiche ha aperte **questo cliente**?"*. Oppure: *"sto guardando
l'**istanza utility** del contatore gas di via Verdi — c'è una pratica di
subentro in corso?"*.

Il dato per rispondere esiste già: ogni pratica porta `soggetto`,
`soggetto_ruolo` e `istanza_utility` (con il modello a due rami appena
consegnato: dal soggetto si scende **o** verso il ruolo **o** verso
l'istanza — il prospect puro ha solo istanze, il ruolo cliente nasce col
billing account). Quello che **non esiste** è la domanda: la lista pratiche
oggi filtra solo per soggetto, non per ruolo né per istanza.

### Cosa serve

Tre "lenti" sulla stessa lista, che rispecchiano i tre tipi di pratica:

1. **Pratiche del ruolo** — es. tutte le pratiche del ruolo CLIENTE di Rossi
   SRL (è la vista che servirà ovunque si lavori "dentro" un cliente o un
   fornitore: drawer soggetto, tab pratiche del cliente, ecc.);
2. **Pratiche dell'istanza** — es. tutte le pratiche del contatore di via
   Verdi (vista per chi lavora sulle utenze);
3. **Pratiche interne** — quelle senza alcun contesto cliente (vedi tema 2).

Non è una ristrutturazione: è aggiungere i filtri mancanti e una
visualizzazione raggruppata. Ma va deciso **adesso**, perché ogni nuovo punto
dell'applicazione che mostrerà "le pratiche di…" deve usare la stessa lente.

### D1 — da ratificare

> Il raggruppamento canonico delle pratiche è per **nodo di contesto**:
> ruolo soggetto / istanza utility / interna (nessun contesto). Ogni vista
> "pratiche di X" nell'applicazione usa uno di questi tre filtri, mai
> ricostruzioni ad hoc.

---

## 2. Pratiche interne — e perché NON serve un "ruolo operatore"

### Cosa dice già il modello

`gestione-pratiche-v2.md` lo aveva previsto esplicitamente: tutti i campi di
contesto sono opzionali, *"pratica interna: tutti NULL"*, e il drawer prevede
la creazione "senza soggetto". Quindi le interne non sono un'eccezione da
costruire: sono già un tipo legittimo di pratica.

### La domanda sul ruolo operatore

L'intuizione era: *"interna non è forse un duplicato di una pratica per ruolo
operatore?"*. Risposta dell'analisi: **sì, ed è proprio per questo che non va
creato il concetto**. La dimensione "chi ci lavora" esiste già su **ogni**
pratica, ortogonale al contesto cliente:

- `risorsa_umana_id` — l'operatore assegnato;
- `unita_organizzativa_id` — il reparto;
- `competenze_flussi` + coda lavoro a 3 livelli (ASSEGNATO / COMPETENZA /
  REPARTO) — chi può/deve eseguire i flussi.

Esempio: la pratica interna "inventario di magazzino" non ha cliente, ma ha
un assegnatario e un reparto — e si trova già oggi nella coda lavoro
dell'operatore giusto. Aggiungere un "ruolo operatore" come contesto
duplicherebbe l'assegnazione, creando due verità sulla stessa domanda
("di chi è questa pratica?").

### D2 — da ratificare

> Le pratiche interne restano "contesto vuoto + assegnazione". **Non** si
> introduce un ruolo operatore come contesto anagrafico. Nella vista per
> contesto (D1) le interne sono il terzo bucket.

---

## 3. Ripetibilità dei flussi — il buco vero

### Il problema, con gli esempi

- **Appuntamento**: l'operatore fissa l'appuntamento, il cliente non si
  presenta → esito NEGATIVO. L'appuntamento **va rifatto**: serve una seconda
  istanza dello stesso flusso nella stessa pratica.
- **Conferma vendita**: una volta eseguita (preventivo smistato a
  ordine/commessa), **non deve essere rieseguibile**: è un flusso "una
  volta sola".

Nessuno dei documenti di analisi ha trattato questo punto (trattano
l'*idempotenza* — "se per errore eseguo due volte non duplico l'effetto" —
che è un'altra cosa). E lo stato di fatto, verificato con gli smoke, è il
peggiore dei due mondi: **oggi tutto è ripetibile, illimitatamente, senza
alcun governo**. Si può creare una seconda istanza di qualunque flusso, anche
di uno già chiuso bene. La CONFERMA si salva solo perché il suo handler ha un
guard interno ("già smistato") — ma è una difesa del singolo handler, non una
regola del motore.

### La regola che serve

Una proprietà sul **template** del flusso (è configurazione, non codice), con
tre valori che coprono i casi reali:

| Regola | Significato | Esempio |
|---|---|---|
| `MAI` | una sola istanza, sempre | CONFERMA_VENDITA |
| `SE_NON_POSITIVO` | ripetibile solo se l'ultima istanza non è chiusa bene | APPUNTAMENTO (negativo → si rifà; positivo → basta) |
| `SEMPRE` | ripetibile liberamente | un flusso "contatto telefonico" in una pratica commerciale |

Il default più prudente è `SE_NON_POSITIVO`: è il comportamento che un
operatore si aspetta ("se è andata male riprovo, se è andata bene è fatta").

### D3 — da ratificare

> Si introduce la regola di ripetibilità sul template flusso con i tre valori
> sopra (default `SE_NON_POSITIVO`). Il controllo vive a DB, accanto al guard
> dei prerequisiti, così vale per qualunque chiamante.

---

## 4. Workflow condizionale — c'è già più di quanto sembri

### Cosa il motore sa già fare

Il meccanismo dei prerequisiti è **esito-aware**: ogni step può dichiarare
"divento eseguibile solo se lo step X è completato con esito Y". Finora lo
abbiamo usato solo in linea retta (la catena PREVENTIVI: 10 → 20 → 30 → 40,
tutti su esito POSITIVO). Ma la stessa struttura esprime già i **bivi**:

```text
                              ┌─ esito POSITIVO ──→ CONFERMA_VENDITA
RICHIESTA → PREVENTIVO → APPROVAZIONE
                              └─ esito NEGATIVO ──→ NEGOZIAZIONE
```

Basta seedare lo step NEGOZIAZIONE con prerequisito "APPROVAZIONE con esito
NEGATIVO": il percorso mostra entrambi i rami e solo quello coerente con
l'esito reale diventa eseguibile. **Senza scrivere codice**: è configurazione.

Anche il caso "un flusso apre attività diverse a seconda della condizione" è
già validato: è esattamente quello che fa l'handler della CONFERMA, che
guardando la natura delle righe apre un ordine, una commessa, o entrambi.

### Cosa manca davvero

1. **La semantica del ramo morto**: se l'approvazione è POSITIVA, lo step
   NEGOZIAZIONE resta nel percorso come step "mai eseguibile". Funziona, ma
   l'operatore deve capire a colpo d'occhio che quel ramo è chiuso (resa
   visiva nel percorso) e la pratica deve poter arrivare a CHIUSA anche con
   rami mai eseguiti (oggi gli step non obbligatori non bloccano nulla, ma
   non è mai stato verificato su un percorso a bivi).
2. **Un caso reale**: i bivi non sono mai stati seedati né provati. Prima di
   dichiararli "supportati" serve un tipo prestazione di test con un bivio
   vero e uno smoke che lo percorre in entrambe le direzioni.

### D4 — da ratificare

> I percorsi condizionali si esprimono con i prerequisiti esito-aware
> esistenti (nessuna nuova struttura). Si aggiunge solo: (a) la resa visiva
> del ramo non più percorribile nel percorso; (b) la validazione su un caso
> seedato con bivio POSITIVO/NEGATIVO.

---

## 5. Flussi che generano altri flussi o altre pratiche

### Qui l'analisi iniziale aveva già previsto (quasi) tutto

È la parte più pronta, anche se non è mai stata usata:

- esiste la tabella delle **regole di generazione**: "quando il flusso X
  chiude con esito Y, genera una pratica di tipo Z" — con flag `auto` (la
  genera il motore da solo) o manuale (la propone, l'operatore conferma);
- esiste il trigger che la fa scattare al completamento del flusso, la
  funzione che crea la pratica figlia, e gli endpoint API (`/genera/`,
  `/pratiche-generate/`);
- la pratica generata è **tracciata strutturalmente**: porta `pratica_padre`
  e `flusso_origine` come colonne vere, non solo come annotazione.

L'esempio disegnato in `crm-ticketing-pratiche.md` è il caso d'uso perfetto:
ticket assistenza → flusso DIAGNOSI_TECNICA chiude NEGATIVO ("non riparabile
al telefono") → il motore genera **da solo** una pratica PREVENTIVAZIONE
collegata, figlia del ticket. L'operatore se la trova in coda senza che
nessuno debba ricordarsi di aprirla.

### E i flussi che generano flussi nella stessa pratica?

Le regole generano **pratiche**, non flussi dentro la stessa pratica. Ma
attenzione: probabilmente non serve. Il percorso è già a creazione
progressiva — quando chiudo uno step, il successivo diventa eseguibile e lo
creo con un click. L'unica aggiunta sensata è una comodità: **auto-creare il
prossimo step eseguibile** alla chiusura del precedente (risparmia un click,
non cambia il modello). Da valutare solo dopo l'uso reale, non ora.

### Cosa manca

Solo l'esercizio: zero regole seedate, zero smoke. La validazione costa poco
perché tutta la macchina c'è già.

---

## 6. Riepilogo decisioni da ratificare

| ID | Decisione proposta | Costo se rinviata |
|---|---|---|
| D1 | Vista canonica per nodo di contesto (ruolo / istanza / interna) | ogni nuova schermata "pratiche di X" inventa la sua lente |
| D2 | Niente "ruolo operatore": interne = contesto vuoto + assegnazione | doppia verità sull'assegnazione |
| D3 | Regola di ripetibilità sul template (MAI / SE_NON_POSITIVO / SEMPRE) | flussi unici rieseguibili per errore; nessun governo dei retry |
| D4 | Bivi via prerequisiti esito-aware + resa del ramo morto + caso validato | "condizionale" resta una capacità dichiarata ma mai provata |

(Il tema 5 non ha decisioni di modello: serve solo il primo consumatore — il
ticket assistenza è il candidato naturale e coinciderebbe con la Fase F,
secondo consumatore del motore.)

---

## 7. Piano di sviluppo

> Ordine consigliato: **DB → BE → FE** per ciascun blocco, come sempre.
> I blocchi A (contesto) e B (ripetibilità) sono indipendenti e possono
> procedere in parallelo; C (bivi) e D (generazione) convengono in sequenza
> dopo B, perché gli smoke si costruiscono uno sull'altro.

### Team DB — la logica richiesta (il *come* è scelta vostra)

**A. Vista per contesto (D1)**

- La lista pratiche deve poter rispondere a tre domande: "pratiche di questo
  ruolo soggetto", "pratiche di questa istanza utility", "pratiche interne"
  (= senza soggetto). Oggi la lettura filtra solo per soggetto.
- Serve che queste tre lenti siano efficienti (le colonne esistono già;
  valutate voi se servono indici dedicati) e che la coda di lavoro resti
  coerente quando filtrata per contesto.

**B. Ripetibilità (D3)**

- Ogni template flusso deve dichiarare la propria regola di ripetibilità:
  mai ripetibile / ripetibile solo se l'ultima istanza non è chiusa con
  esito positivo / sempre ripetibile. Default proposto: la regola di mezzo.
- Il controllo deve scattare **alla creazione di una nuova istanza** di
  flusso (stesso punto dove oggi scattano i prerequisiti) e deve fallire con
  un errore parlante quando la regola lo vieta. Conta l'**ultima** istanza
  per quel template nella pratica (lo stesso criterio già usato dal
  percorso).
- I template esistenti vanno classificati nel seed: CONFERMA = mai
  ripetibile; gli altri step della catena PREVENTIVI = ripetibili se non
  positivi.

**C. Bivi condizionali (D4)**

- Nessuna struttura nuova: si tratta di seedare un caso di test con bivio
  (uno step abilitato da esito POSITIVO e uno, alternativo, abilitato da
  esito NEGATIVO dello stesso predecessore) e verificare con pgTAP che i
  guard esistenti abilitino/blocchino i due rami correttamente.
- Da verificare in particolare: che la chiusura della pratica non sia
  ostacolata da rami mai percorsi.

**D. Generazione automatica (tema 5)**

- Anche qui niente strutture nuove: seedare una regola di generazione di
  test (flusso X esito NEGATIVO → genera pratica di tipo Y, auto) e
  verificare con pgTAP che il trigger generi la pratica figlia con
  `pratica_padre` e `flusso_origine` valorizzati, e che la generazione sia
  idempotente (un solo figlio anche in caso di doppio evento).

### Team BE

**A. Vista per contesto**
- Estendere la lista pratiche e la coda lavoro con i filtri
  `soggetto_ruolo_id`, `istanza_utility_id`, `solo_interne` (mutuamente
  alternativi), con test.
- Esporre il conteggio per contesto dove serve al raggruppamento FE.

**B. Ripetibilità**
- Nessuna logica propria (vive a DB): mappare il nuovo codice errore a
  envelope parlante; esporre nel percorso l'informazione "ripetibile adesso
  sì/no" per pilotare il bottone FE.
- Estendere lo smoke pratica: appuntamento-like NEGATIVO → seconda istanza
  ok; CONFERMA → seconda istanza rifiutata dal motore (non più dal solo
  guard dell'handler).

**C. Bivi**
- Il percorso già espone stato+esito per step: verificare che basti per la
  resa del ramo morto; eventualmente aggiungere un campo calcolato
  ("percorribile / completato / ramo chiuso").
- Smoke: percorrere il bivio in entrambe le direzioni.

**D. Generazione automatica**
- Gli endpoint esistono già (`/genera/`, `/pratiche-generate/`): verificarli
  runtime nello smoke (oggi mai esercitati); la pratica figlia deve
  comparire nella coda giusta.

### Team FE

**A. Vista per contesto**
- Dashboard: raggruppamento/filtro per le tre lenti (ruolo / istanza /
  interne).
- Tab "Pratiche" nei punti dove il contesto è già noto (drawer soggetto:
  pratiche del ruolo selezionato; vista istanza: pratiche dell'istanza) —
  riuso del pattern lista esistente con filtro preimpostato.

**B. Ripetibilità**
- Nel percorso: bottone "Ripeti" sullo step quando il BE dice che è
  ripetibile ora (es. appuntamento NEGATIVO); nascosto altrimenti. Errore
  parlante se la regola vieta.

**C. Bivi**
- Resa visiva del percorso a bivi: ramo percorso / ramo eseguibile / ramo
  chiuso (es. attenuato con motivo nel tooltip). È la parte UX più delicata:
  da fare su un caso seedato vero, non su mock.

**D. Generazione automatica**
- Quando una pratica è stata generata da un flusso: mostrarne l'origine
  (link alla pratica padre) e, sulla pratica padre, le pratiche generate
  (endpoint già esistente). Notifica/evidenza in coda lavoro della pratica
  figlia auto-generata.

---

*Analisi pratiche workflow v2 — ZeroERP (2026-06-11). Decisioni D1..D4 in
attesa di ratifica; al via libera, il blocco A/B parte con i brief DB.*
