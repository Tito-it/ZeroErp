# Pratiche workflow v2 — analisi e decisioni

> **Tipo documento**: analisi di modello (linguaggio volutamente semplice, con
> esempi). **Data**: 2026-06-11 · **Stato**: ✅ **D1..D4 RATIFICATE da Tid il
> 2026-06-11** — sviluppo DB in corso (questo branch, `dev/db-tid`); BE/FE
> seguiranno nei rispettivi branch. **Agg. 2026-06-11**: aggiunta la
> [§7 Analisi critica della parte DB](#7-analisi-critica-della-parte-db-verifica-contro-il-codice-vivo),
> verifica delle affermazioni di modello contro il codice DB **vivo** (doc
> auto-gen `dbzero/pratiche`). Alcune affermazioni di §5 sono risultate
> ottimistiche e vanno lette insieme a quella sezione. Con la ratifica sono
> adottate anche le proposte operative di §7/§8: D3 → "ultima istanza" =
> `MAX(id)` e blocco anche con ultima istanza ancora aperta; D1 → la lente
> canonica vive a **DB** (funzione di lista), coda lavoro non toccata;
> D4 → guard di chiusura su `obbligatorio` con esclusione del ramo morto.
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

Solo l'esercizio: zero regole seedate, zero smoke.

> ⚠️ **Correzione dopo verifica codice vivo (vedi §7).** La frase originale
> «tutta la macchina c'è già» è **troppo ottimistica**. La verifica contro
> `fn_genera_pratica_da_flusso` e `trgfn_flussi_generazione` ha trovato quattro
> buchi reali nel motore di generazione: `pratica_padre_id` mai popolato,
> nessuna idempotenza, `template_flusso_dest_id` ignorato, contesto
> ruolo/istanza non propagato. Tema 5 **non** è "solo esercizio": prima degli
> smoke servono fix DB mirati. Dettaglio in §7.B.

---

## 6. Riepilogo decisioni — ✅ ratificate il 2026-06-11

| ID | Decisione (ratificata) | Costo se fosse stata rinviata |
|---|---|---|
| D1 | Vista canonica per nodo di contesto (ruolo / istanza / interna) | ogni nuova schermata "pratiche di X" inventa la sua lente |
| D2 | Niente "ruolo operatore": interne = contesto vuoto + assegnazione | doppia verità sull'assegnazione |
| D3 | Regola di ripetibilità sul template (MAI / SE_NON_POSITIVO / SEMPRE) | flussi unici rieseguibili per errore; nessun governo dei retry |
| D4 | Bivi via prerequisiti esito-aware + resa del ramo morto + caso validato | "condizionale" resta una capacità dichiarata ma mai provata |

(Il tema 5 non ha decisioni di modello: serve solo il primo consumatore — il
ticket assistenza è il candidato naturale e coinciderebbe con la Fase F,
secondo consumatore del motore.)

---

## 7. Analisi critica della parte DB (verifica contro il codice vivo)

> **Metodo.** Ogni affermazione di modello delle sezioni 1–5 è stata verificata
> contro la definizione **viva** degli oggetti DB (doc auto-gen
> `docs/it/dbzero/pratiche/`, che riflette l'oggetto reale nel database), non
> contro gli YAML di migration (potenzialmente stale). Sotto, per ogni tema:
> cosa il codice fa **davvero**, e dove il documento era impreciso.

### 7.A — Vista per contesto (D1): le colonne ci sono, la lettura no — e tocca due punti, non uno

Confermato che le colonne di contesto esistono su `pratiche.pratiche`
(`soggetto_ruolo_id`, `istanza_utility_id`, più `soggetto_id`) e sono
indicizzabili. Ma il documento tratta D1 come "aggiungere filtri a una lista".
La verifica mostra **due read distinti**, non uno:

1. **Lista pratiche** — lo schema `pratiche` **non ha viste** (cartella
   `dbzero/pratiche/views` vuota): oggi la lista pratiche vive in una query del
   repository BE. La lente canonica D1 deve quindi atterrare da qualche parte
   *di nuovo*: o come funzione/vista DB (preferibile per riuso e per coerenza
   DB-first), o come query BE parametrica. **Va deciso dove vive la verità del
   filtro** — non è un semplice WHERE aggiunto a qualcosa che già esiste.
2. **Coda di lavoro** — `fn_coda_lavoro_operatore(p_risorsa_umana_id,
   p_emittente_fiscale_id)` ha **solo** quei due parametri: nessun filtro di
   contesto. E lavora a livello **flussi**, non pratiche. "Filtrare la coda per
   contesto" (§7-A del piano originale) richiede di **estenderne la firma** (o
   una funzione gemella), non un filtro a valle. Inoltre va deciso se il
   contesto sulla coda ha senso (la coda è per-operatore; il contesto è
   per-cliente: probabilmente serve solo sulla lista, non sulla coda).

→ **Conseguenza sul piano**: D1 è giusto come decisione, ma il deliverable DB
non è "indici + filtro": è **una funzione/vista di lista pratiche per contesto**
(ruolo / istanza / interna) come punto unico di verità, e una decisione
esplicita su *se* la coda lavoro va resa contesto-aware.

### 7.B — Generazione cross-pratica (tema 5): NON è "pronto", è abbozzato (4 buchi reali)

Questo è lo scarto più grande. §5 dice che è «la parte più pronta… tutta la
macchina c'è già». La lettura di `fn_genera_pratica_da_flusso` e
`trgfn_flussi_generazione` racconta un'altra storia:

1. **`pratica_padre_id` non viene MAI popolato.** Un `grep` su tutte le
   migration trova la colonna solo nel `CREATE TABLE`: nessun `INSERT`/`UPDATE`
   la valorizza. `fn_genera_pratica_da_flusso` imposta **solo**
   `flusso_origine_id`. La genealogia padre→figlio è ricostruibile solo
   indirettamente (`flusso_origine_id → flussi.pratica_id`); la colonna dedicata
   è **codice morto**. → §5 afferma «porta `pratica_padre` e `flusso_origine`
   come colonne vere, non solo come annotazione»: **falso per `pratica_padre`**.

2. **Nessuna idempotenza — ed è peggio di un'omissione, è un bug latente.**
   Il trigger `trg_flussi_z90_generazione_upd` è `AFTER UPDATE` (su *qualsiasi*
   colonna), e `trgfn_flussi_generazione` controlla solo che lo stato **nuovo**
   sia `COMPLETATO`: **non** verifica `OLD.stato_id IS DISTINCT FROM
   NEW.stato_id`, né l'esistenza di un figlio già generato. Conseguenza: ogni
   `UPDATE` su un flusso già `COMPLETATO` (es. l'operatore corregge
   `note_esito`) **rigenera una pratica figlia**. Lo `UNIQUE` su
   `regole_generazione` protegge dai duplicati di *regola*, non di *figlio*.
   → §5/§8-D parlano di «verificare che la generazione sia idempotente» come se
   lo fosse: in realtà l'idempotenza **va implementata**, non solo testata.

3. **`template_flusso_dest_id` è ignorato.** La regola può dichiarare il flusso
   iniziale della pratica figlia (documentato in `regole_generazione`), ma
   `fn_genera_pratica_da_flusso` **non lo legge** e non crea alcun flusso: la
   figlia nasce in `BOZZA` senza percorso. Feature documentata, non implementata.

4. **Il contesto non viene propagato — D1 e tema 5 NON sono indipendenti.**
   La figlia copia `soggetto_id` ma **non** `soggetto_ruolo_id` né
   `istanza_utility_id`. Se (D1) il contesto ruolo/istanza diventa la lente
   canonica, **le pratiche generate cadono fuori da quelle viste**. Il documento
   tratta A e D come blocchi paralleli indipendenti: questo punto li accoppia.

### 7.C — Ripetibilità (D3): placement giusto, ma due ambiguità di modello irrisolte

Confermata la diagnosi: nessuna colonna di ripetibilità su `template_flussi`,
nessun `UNIQUE (pratica_id, template_flusso_id)` su `flussi` → oggi N istanze
libere. Il guard naturale è `BEFORE INSERT` su `flussi`, accanto a
`trg_flussi_a10_guard_prerequisiti_ins`. Ma il documento glissa su due scelte:

- **Cos'è "l'ultima istanza".** §3/§8-B dicono «lo stesso criterio già usato dal
  percorso». Ma il percorso ordina per `flussi.sequenza` (default `0` = posizione
  nel template, **non** recency). Per istanze ripetute dello stesso template la
  recency affidabile è `id` / `data_insert`, non `sequenza`. **Va scelto
  esplicitamente** (proposta: `id` DESC, monotòno e immune ai default).

- **L'ultima istanza ancora aperta.** I tre valori ragionano sull'*esito*
  dell'ultima istanza, ma non sul caso «ultima istanza ancora APERTA (esito
  `NULL`, stato `DA_ESEGUIRE`/`IN_CORSO`)». `SE_NON_POSITIVO` così com'è
  permetterebbe una seconda istanza **mentre la prima è ancora aperta** → due
  appuntamenti aperti insieme. Quasi certamente indesiderato: la regola deve
  bloccare anche con ultima istanza non chiusa (positiva *o* ancora in corso).

### 7.D — Bivi condizionali (D4): la capacità c'è davvero; il timore sulla chiusura è mal posto

Confermato: `fn_check_prerequisiti_flusso` è esito-aware
(`tfp.esito_richiesto IS NULL OR f.esito = tfp.esito_richiesto`) e
`template_flussi_prerequisiti.esito_richiesto` esiste con `CHECK`. **I bivi sono
esprimibili oggi, senza codice nuovo**: §4 è corretto.

Ma il timore di §4/§8-C — «che la chiusura della pratica non sia ostacolata da
rami mai percorsi» — è mal posto. `trgfn_pratiche_guard_transizione` controlla
**solo** la matrice `config.transizioni_stati_pratiche`: **non esiste alcun
guard** che richieda flussi completati per chiudere. Quindi la chiusura non è
ostacolata — ma per **assenza totale di controllo**, non per design. Il rischio
reale è l'opposto: una pratica può chiudere anche con flussi `obbligatorio=true`
non eseguiti (la colonna `obbligatorio` esiste su `template_flussi` ma **nessuno
la fa valere** in chiusura). → Il pgTAP D4 va riformulato: non «verifica che i
rami morti non blocchino», ma «definisci e verifica la semantica di chiusura
rispetto a `obbligatorio` + ramo morto» (un ramo non percorso perché l'esito ha
preso l'altra strada **non** deve contare come obbligatorio-non-fatto).

### 7.E — Nota onesta: `flusso_padre_id` esiste già

§5 dice «le regole generano pratiche, non flussi dentro la stessa pratica… ma
probabilmente non serve». Per correttezza: `flussi.flusso_padre_id` (FK self)
**esiste già**. L'aggancio strutturale flusso→flusso c'è, solo inutilizzato.
La conclusione "non ora" resta valida, ma il motivo non è "manca il modello":
il modello c'è, manca l'uso.

### 7.F — Sintesi: priorità rivista

| Tema | Stato dichiarato | Stato reale (codice vivo) | Lavoro DB vero |
|---|---|---|---|
| 1 — Contesto (D1) | "dato sì, vista no" | corretto, ma **2 read** e nessuna vista pratiche | funzione/vista lista per contesto (punto di verità unico) |
| 3 — Ripetibilità (D3) | "il buco vero" | corretto; 2 ambiguità di modello | colonna template + guard `BEFORE INSERT` con ordinamento e stato-aperto definiti |
| 4 — Bivi (D4) | "c'è già" | **vero**; timore chiusura mal posto | solo seed+pgTAP, ma con semantica `obbligatorio`/ramo-morto decisa |
| 5 — Generazione | "la più pronta" | **abbozzata: 4 buchi** | fix `fn_genera_*` (padre, dest, contesto) + idempotenza nel trigger, *poi* seed/smoke |

**Riordino di priorità rispetto a §8.** Il documento mette A e B come "pronti a
partire" e C/D "in sequenza dopo". La verifica suggerisce: **B (ripetibilità)**
resta il blocco più pulito e indipendente — parte subito. **A (contesto)**
richiede prima una micro-decisione (vista DB vs query BE) ma è indipendente da
B. **D (generazione)** è stato **promosso da "solo esercizio" a "fix +
esercizio"**: i 4 buchi di §7.B vanno chiusi prima di dichiararlo supportato, e
il fix idempotenza è il più urgente perché è un bug latente già oggi in produzione
potenziale. **C (bivi)** resta il più economico (seed+pgTAP) ma va fatto dopo
aver deciso la semantica di chiusura.

---

## 8. Piano di sviluppo

> Ordine consigliato: **DB → BE → FE** per ciascun blocco, come sempre.
> I blocchi A (contesto) e B (ripetibilità) sono indipendenti e possono
> procedere in parallelo; C (bivi) e D (generazione) convengono in sequenza
> dopo B, perché gli smoke si costruiscono uno sull'altro.

### Team DB — la logica richiesta (il *come* è scelta vostra)

> **Numerazione changeset.** L'ultimo file della giornata è
> `20260611-01-update-trgfn-pratiche-guard-contesto-istanza-senza-ruolo`.
> Il nuovo lavoro parte da `20260611-02` e prosegue in **sequenza globale per
> data** tra tutte le cartelle. Un changeSet per file, `logicalFilePath` sempre.
> Per i `CREATE OR REPLACE` di funzioni/trigger esistenti: copiare il corpo
> **dalla doc auto-gen** (oggetto vivo), applicarvi la modifica, nuovo file con
> numerazione successiva (mai editare changelog già mergiati).

**B. Ripetibilità (D3) — blocco indipendente, parte subito**

- Colonna nuova su `template_flussi`, es. `ripetibilita varchar` con `CHECK IN
  ('MAI','SE_NON_POSITIVO','SEMPRE')` e `DEFAULT 'SE_NON_POSITIVO'` (create
  column con default → backfill automatico dei template esistenti).
- `fn_check_ripetibilita_flusso(p_pratica_id, p_template_flusso_id)` →
  boolean puro + `fn_guard_ripetibilita_flusso(...)` fail-fast con codice errore
  registrato (es. `PRATICHE_FLUSSO_NON_RIPETIBILE`). Estendere
  `trgfn_flussi_guard_prerequisiti` **oppure** un nuovo trigger gemello
  `trg_flussi_a10_guard_ripetibilita_ins` (preferibile: separazione di
  responsabilità). **Solo `BEFORE INSERT`**.
- **Due scelte di modello da fissare nel brief** (vedi §7.C):
  1. "Ultima istanza" = `MAX(id)` tra i flussi dello stesso `template_flusso_id`
     nella pratica (non `sequenza`, che è la posizione nel template).
  2. `SE_NON_POSITIVO` blocca se l'ultima istanza è `POSITIVO` **oppure ancora
     aperta** (stato `DA_ESEGUIRE`/`IN_CORSO`, esito `NULL`). Permette solo se
     l'ultima è chiusa con esito non positivo (`NEGATIVO`/`PARZIALE`/`NON_APPLICABILE`).
- Seed: `CONFERMA_VENDITA` → `MAI`; restanti step catena PREVENTIVI →
  `SE_NON_POSITIVO`. Messaggio errore in `80_data` (CSV).
- **pgTAP** `db/pgtap/pratiche/test-ripetibilita-flussi.sql`: MAI → 2ª istanza
  rifiutata; SE_NON_POSITIVO con ultima NEGATIVO → 2ª ammessa; con ultima
  POSITIVO → rifiutata; con ultima aperta → rifiutata; SEMPRE → sempre ammessa.
- Changeset stimati: `20260611-02..06` circa (alter, fn_check, fn_guard,
  trigger, seed) + messaggio errore.

**A. Vista per contesto (D1) — indipendente da B, ma prima una micro-decisione**

- **Decisione preliminare** (§7.A): la lente vive come **funzione/vista DB**
  (`vw_pratiche_per_contesto` o `fn_lista_pratiche_per_contesto(...)`) — scelta
  preferita per DB-first e riuso — oppure come query BE parametrica. Il
  documento assume "filtro a una lista esistente": **non esiste** una vista
  pratiche oggi, va creata.
- La lente risponde a tre domande sulla **lista pratiche**: per
  `soggetto_ruolo_id`, per `istanza_utility_id`, "interne" (i tre contesti NULL).
  Parametri mutuamente alternativi.
- **Coda lavoro**: decidere se renderla contesto-aware. `fn_coda_lavoro_operatore`
  ha firma `(risorsa_umana_id, emittente_fiscale_id)` e lavora a livello flussi:
  estenderla è un cambio di firma, non un filtro a valle. **Proposta: non
  toccare la coda** (è per-operatore; il contesto è per-cliente) salvo esigenza
  reale.
- Indici: valutare `ix_pratiche_soggetto_ruolo` / `ix_pratiche_istanza_utility`
  (FK index policy, **non** crearli a mano: registrare in `dbops.fk_index_policy`).
- **pgTAP** `db/pgtap/pratiche/test-lista-pratiche-contesto.sql`: 3 lenti
  ritornano gli insiemi attesi; "interne" esclude pratiche con qualunque contesto.

**D. Generazione cross-pratica (tema 5) — PROMOSSO: fix prima dell'esercizio**

Non è "solo seed+smoke". Prima i fix DB (§7.B):

- **D-fix1 — idempotenza (urgente, bug latente).** In `trgfn_flussi_generazione`:
  (a) guardia `OLD.stato_id IS DISTINCT FROM NEW.stato_id` per generare solo
  alla *transizione* a COMPLETATO, non su ogni UPDATE; (b) dedup: non generare
  se esiste già una pratica figlia per quel `flusso_origine_id` + regola.
  In alternativa/aggiunta, vincolo che renda strutturalmente impossibile il
  doppio figlio.
- **D-fix2 — `pratica_padre_id`.** `fn_genera_pratica_da_flusso` deve
  valorizzare `pratica_padre_id` = pratica sorgente del flusso (oggi è codice
  morto).
- **D-fix3 — flusso iniziale.** Leggere `regole_generazione.template_flusso_dest_id`
  e, se valorizzato, creare il flusso iniziale nella pratica figlia (oggi
  ignorato).
- **D-fix4 — propagazione contesto.** Copiare anche `soggetto_ruolo_id` e
  `istanza_utility_id` sulla figlia, altrimenti cade fuori dalle viste D1.
- **Solo dopo i fix**: seed regola di test (flusso X esito NEGATIVO → tipo Y,
  auto) + **pgTAP** `db/pgtap/pratiche/test-generazione-cross-pratica.sql`:
  figlia creata con `pratica_padre_id` **e** `flusso_origine_id` valorizzati,
  contesto propagato, flusso iniziale creato; **idempotenza**: doppio UPDATE su
  flusso completato → **un solo** figlio.

**C. Bivi condizionali (D4) — il più economico, ma con semantica di chiusura decisa prima**

- Nessuna struttura nuova: i prerequisiti esito-aware bastano (verificato §7.D).
- **Decisione preliminare**: semantica di chiusura rispetto a `obbligatorio` +
  ramo morto. Oggi **nessun guard** lega la chiusura ai flussi (la chiusura
  passa solo dalla matrice transizioni). Decidere se introdurre un guard
  "non chiudere con flussi `obbligatorio=true` non completati", **escludendo**
  i rami resi non percorribili dall'esito (ramo morto ≠ obbligatorio-non-fatto).
- Seed: un tipo prestazione di test con bivio (step abilitato da esito POSITIVO
  + step alternativo da esito NEGATIVO dello stesso predecessore).
- **pgTAP** `db/pgtap/pratiche/test-bivi-condizionali.sql`: esito POSITIVO →
  ramo positivo eseguibile, ramo negativo bloccato dal guard prerequisiti (e
  viceversa); pratica chiudibile con il ramo morto presente.

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
- ⚠️ **Dipende dai fix DB §8-D** (idempotenza, `pratica_padre_id`, contesto):
  non esercitare gli endpoint finché i fix non sono atterrati, altrimenti lo
  smoke valida un comportamento bacato.
- Gli endpoint esistono già (`/genera/`, `/pratiche-generate/`): verificarli
  runtime nello smoke (oggi mai esercitati); la pratica figlia deve
  comparire nella coda giusta, con link alla pratica padre funzionante (oggi
  `pratica_padre_id` è nullo → il link non può funzionare prima del fix).

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

---

## 9. Stato deliverable DB (2026-06-11) — ✅ APPLICATI, TEST VERDI

Changeset su `dev/db-tid` (numerazione globale `20260611-03..16`, con buchi
voluti: vedi nota seed). **Migration applicate al DB di sviluppo e tutti i
pgTAP pratiche eseguiti con esito verde (2026-06-11)**. Doc auto-gen
rigenerata; doc manuale (`dbzero/pratiche/manual/`) creata/aggiornata per
tutti gli oggetti nuovi o modificati (vedi elenco in fondo alla sezione).

> **Nota seed (regola di progetto, ribadita da Tid)**: per i CSV già coperti
> da changeset `loadUpdateData` con `runOnChange: true` (es.
> `messaggi_errore.csv`, `template_flussi.csv`) NON si creano nuovi changeset
> upsert per ogni aggiunta: basta modificare il CSV, i changeset esistenti si
> ri-eseguono da soli. I codici 483/484/485 e la colonna `ripetibilita` nel
> seed template viaggiano quindi **solo come righe/colonne CSV**. Un changeset
> nuovo serve solo per CSV nuovi (qui: `fk_index_policy_pratiche.csv`, `-14`).
> Il riferimento "seed 20260611-02" nel commento di `20260611-01` (mergiato)
> è superato da questa regola: il codice 308 è caricato dai runOnChange.

| Blocco | Changeset | Contenuto |
|---|---|---|
| B ripetibilità | `-03` (00_schema) | `template_flussi.ripetibilita` (MAI/SE_NON_POSITIVO/SEMPRE, default SNP) + CHECK |
| | `-04`, `-05`, `-06` (20_code) | `fn_check_ripetibilita_flusso` + `fn_guard_*` + `trg_flussi_a10_guard_ripetibilita_ins` (BEFORE INSERT) |
| | CSV | errore 483 in `messaggi_errore.csv`; classificazione in `template_flussi.csv` (CONFERMA=MAI, resto catena=SNP) |
| D generazione | `-09` (00_schema) | `uq_pratiche_flusso_origine_tipo` (parziale) + bonifica doppioni |
| | `-10` (20_code) | `fn_genera_pratica_da_flusso`: idempotenza, `pratica_padre_id`, contesto, flusso iniziale da `template_flusso_dest_id` |
| | `-11` (20_code) | `trgfn_flussi_generazione`: solo transizione stato; trigger ricreato `AFTER UPDATE OF stato_id` |
| A lente contesto | `-12` (20_code) | `fn_lista_pratiche_per_contesto` (ruolo/istanza/interne/tutte, bucket RUOLO/ISTANZA/SOGGETTO/INTERNA, guard mutua esclusività) |
| | `-14` (80_data) + CSV | errore 484 in CSV; `fk_index_policy_pratiche.csv` nuovo (`ix_pratiche_soggetto_ruolo_id`, `ix_pratiche_istanza_utility_id`, parziali) |
| C chiusura/bivi | `-15` (20_code) | `fn_check_chiusura_pratica` (completato/percorribile/bloccante; ramo morto non blocca) |
| | `-16` (20_code) + CSV | `trg_pratiche_a10_guard_chiusura_flussi_upd` (CHIUSA bloccata con obbligatori percorribili non completati); errore 485 in CSV |

**pgTAP — tutti verdi (2026-06-11)**: `test-ripetibilita-flussi.sql` (nuovo,
14 test), `test-generazione-cross-pratica.sql` (riscritto, 11 test:
padre/contesto/flusso iniziale/idempotenza), `test-lista-pratiche-contesto.sql`
(nuovo, 8 test), `test-bivi-condizionali.sql` (nuovo, 10 test: bivio in
entrambe le direzioni + ramo morto in chiusura). Adattati al nuovo guard
ripetibilità: `test-coda-lavoro-presa-carico.sql` e
`test-prerequisiti-esito-aware.sql` (template di test → `SEMPRE`).

**Documentazione manuale** (`docs/it/dbzero/pratiche/manual/`):

- **Nuovi**: `fn_check_ripetibilita_flusso`, `fn_guard_ripetibilita_flusso`,
  `trgfn_flussi_guard_ripetibilita`, `fn_lista_pratiche_per_contesto`,
  `fn_check_chiusura_pratica`, `trgfn_pratiche_guard_chiusura_flussi`.
- **Aggiornati**: `template_flussi` (colonna `ripetibilita`, semantica
  `obbligatorio` in chiusura), `fn_genera_pratica_da_flusso` (idempotenza,
  genealogia, contesto, flusso iniziale; codici errore corretti),
  `trgfn_flussi_generazione` (guard transizione, nota bug pre-rev),
  `regole_generazione` (`template_flusso_dest_id` implementato, dedup),
  `pratiche` (contesto a due rami, genealogia, indici notevoli; rimossa
  colonna `solo_interna` documentata ma inesistente nella tabella viva),
  `flussi` (guard ripetibilità, bivi).

**Prossimi passi (BE, su `dev/backend-tid`)**: envelope per 483/484/485;
percorso con `ripetibile adesso` (da `fn_check_ripetibilita_flusso`) e stato
ramo `percorribile / completato / ramo chiuso` (da `fn_check_chiusura_pratica`);
lista per contesto via `fn_lista_pratiche_per_contesto`; smoke generazione
cross-pratica (endpoint `/genera/`, `/pratiche-generate/`).

⚠️ **Tech debt rilevato a margine**: `messaggi_errore.csv` ha id duplicati
preesistenti (320: `E_UTENTE_NON_ATTIVO` / `FLUSSI_PRESA_CARICO_STATO_ERRATO`;
321: `E_UTENTE_SCADUTO` / `FLUSSI_GIA_ASSEGNATO`) — con upsert `primaryKey: id`
le coppie si sovrascrivono a vicenda: da bonificare con id nuovi.

---

*Analisi pratiche workflow v2 — ZeroERP (2026-06-11). **Decisioni D1..D4
ratificate il 2026-06-11**, incluse le proposte operative di §7 (D3: ultima
istanza = `MAX(id)`, blocco anche con istanza aperta; D1: lente a DB, coda non
toccata; D4: guard chiusura su `obbligatorio` con esclusione ramo morto). La §7
(analisi critica DB) ha verificato il modello contro il codice vivo: tema 5
promosso da "esercizio" a "fix + esercizio" (4 buchi reali, idempotenza in
testa). Deliverable DB (§9): **B → D-fix → A → C** consegnati, **applicati e
con pgTAP tutti verdi il 2026-06-11**; doc auto-gen rigenerata e doc manuale
allineata. Lato DB il lavoro è CHIUSO. BE/FE a seguire su `dev/backend-tid`.*
