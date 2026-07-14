# Guida — Gestione Ordini di vendita

> **Ultima revisione**: 14 giugno 2026 — modello completo: ordine come documento
> del ciclo attivo (testata + righe + componenti BoM), nascita per **conversione**
> da preventivo (smistamento merce riga-per-riga, 1:N) o da offerta (1:1, in mutua
> esclusività con il contratto) oppure manuale, azioni **data-driven** via
> `fn_available_actions_ordine` con matrice transizioni in `config.transizioni_stati_ordini`,
> conferma = emissione documentale (`/emetti/`), push a commessa per la fatturazione
> (che a esito completato porta l'ordine a `EVASO`), cliente immutabile dopo la creazione.
>
> **Destinatari**: analisti funzionali, operatori commerciali, sviluppatori
> backend/frontend, DBA.
>
> **Vedi anche** — schemi DB:
>
> * [vendite.ordini](/dbzero/vendite/tabelle/ordini) / [vendite.ordini_righe](/dbzero/vendite/tabelle/ordini_righe) / [vendite.ordini_righe_componenti](/dbzero/vendite/tabelle/ordini_righe_componenti)
> * [vendite.ordini_righe_fulfillment](/dbzero/vendite/tabelle/ordini_righe_fulfillment) / [vendite.ordini_indirizzi](/dbzero/vendite/tabelle/ordini_indirizzi) / [vendite.note_ordini](/dbzero/vendite/tabelle/note_ordini)
> * [config.stati_doc_ordini](/dbzero/config/tabelle/stati_doc_ordini) / [config.transizioni_stati_ordini](/dbzero/config/tabelle/transizioni_stati_ordini)
> * [vendite.vw_ordini_lista](/dbzero/vendite/manual/vw_ordini_lista) / [vendite.vw_ordini_riepilogo_iva_dettaglio](/dbzero/vendite/manual/vw_ordini_riepilogo_iva_dettaglio)
> * [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — BoM versionata immutabile
>
> **Vedi anche** — funzioni e trigger DB:
>
> * [script.fn_available_actions_ordine](/dbzero/script/funzioni/fn_available_actions_ordine) — azioni disponibili sullo stato corrente
> * [vendite.trgfn_ordini_guard_transizione](/dbzero/vendite/funzioni/trgfn_ordini_guard_transizione) — enforcement del grafo stati + precondizione "≥1 riga" sulla conferma
> * [vendite.fn_push_preventivo_a_ordine](/dbzero/vendite/funzioni/fn_push_preventivo_a_ordine) — smistamento delle righe merce del preventivo verso un ordine
> * [vendite.fn_offerta_righe_espanse](/dbzero/vendite/funzioni/fn_offerta_righe_espanse) — espansione delle righe dell'offerta in fase di conversione
> * [vendite.fn_ordine_riga_componenti_init](/dbzero/vendite/funzioni/fn_ordine_riga_componenti_init) / [vendite.fn_ordine_riga_componenti_preview](/dbzero/vendite/funzioni/fn_ordine_riga_componenti_preview) — componenti BoM (creazione / anteprima)
> * [vendite.fn_list_ordini_da_pushare](/dbzero/vendite/funzioni/fn_list_ordini_da_pushare) — righe eleggibili al push a commessa
> * [vendite.fn_ricalcola_totali_ordine](/dbzero/vendite/funzioni/fn_ricalcola_totali_ordine) — totali di testata e riepilogo IVA per aliquota
> * [vendite.trgfn_ordini_gen_codice](/dbzero/vendite/funzioni/trgfn_ordini_gen_codice) — numero ordine auto-generato e immutabile
> * [vendite.trgfn_ordini_default_emittente](/dbzero/vendite/funzioni/trgfn_ordini_default_emittente) / [vendite.trgfn_ordini_guard_emittente_ba](/dbzero/vendite/funzioni/trgfn_ordini_guard_emittente_ba) — emittente fiscale di default e coerenza con il cliente
>
> **Vedi anche** — API e service backend:
>
> * [API Ordini](/backend/vendite/manual/api_ordini)
> * [API Preventivi](/backend/vendite/manual/api_preventivi) — conversione preventivo → ordine (§6c smistamento)
> * [API Offerte](/backend/vendite/manual/api_offerte) — conversione offerta → ordine
> * [API Pricing (resolver + limiti L2)](/backend/vendite/manual/api_pricing)
>
> **Vedi anche** — guide correlate:
>
> * [Gestione Preventivi](/guide/gestione-preventivi) — la sorgente principale dell'ordine (split per natura)
> * [Gestione Offerte commerciali](/guide/gestione-offerte-commerciali) — l'altra sorgente (1:1, XOR contratto)
> * [Gestione Contratti](/guide/gestione-contratti) — il "gemello ricorrente": l'offerta genera contratto **oppure** ordine, mai entrambi
> * [Gestione DDT](/guide/gestione-ddt) — il documento di consegna: l'ordine confermato si **evade** in uno o più DDT (residuo per riga)
> * [Gestione Commesse](/guide/gestione-commesse) — la destinazione del push (attività fatturabili)
> * [Fatturazione end-to-end](/guide/fatturazione) — il push a commessa avvia la pipeline di fatturazione
> * [Documenti e stampe](/guide/documenti-e-stampe) — generazione del PDF di conferma d'ordine
> * [Gestione Listini e Pricing v5](/guide/gestione-listini) — risoluzione dei prezzi

---

## 1. Cosa è un ordine di vendita

Un ordine di vendita è il **documento operativo** del ciclo attivo: raccoglie le
righe articolo che l'azienda si è impegnata a **consegnare e fatturare** a un
cliente. Risponde alla domanda: *"Cosa consegniamo e fatturiamo a questo cliente,
in quali quantità e a quali prezzi?"*

A differenza di preventivo e offerta — che sono **proposte** (un "se accettassi…")
— l'ordine è un **impegno confermato**. È il punto in cui la trattativa diventa
lavoro da svolgere: una volta confermato, l'ordine alimenta la **commessa** che a
sua volta apre la pipeline di fatturazione.

Caratteristiche di base:

- è intestato a un **cliente** (billing account, con il relativo soggetto) e,
  facoltativamente, a una **utility** (Gas, Energia, Idrico, oppure "Base" per il
  commercio)
- raccoglie **righe** (articolo, quantità, prezzo, IVA) ed eventuali **componenti
  BoM** per gli articoli compositi
- ha un **ciclo di vita** semplice: bozza → confermato → evaso (oppure annullato)
- nasce quasi sempre per **conversione** da un preventivo accettato o da un'offerta
  accettata, ma può anche essere creato a mano
- alla conferma può produrre il **PDF di conferma d'ordine**
- una volta confermato viene **spinto in commessa** (push), che lo collega alla
  fatturazione

Il numero documento è auto-generato (trigger `trgfn_ordini_gen_codice`) ed è
**immutabile**: viene assegnato già alla nascita della bozza e non si modifica più.

> **Differenza chiave con preventivo/offerta.** L'ordine **non ha revisioni** e
> **non ha un listino in testata**: i prezzi delle righe sono già "fotografati"
> (arrivano dalla trattativa a monte o vengono inseriti a mano). Mentre il
> preventivo si "revisiona" finché non è accettato, l'ordine, se va corretto,
> finché è in bozza si modifica liberamente; dopo la conferma è bloccato.

---

## 2. Dove si colloca nel flusso commerciale

L'ordine è il passaggio dalla **proposta** alla **operatività**. Le due sorgenti
naturali sono il preventivo e l'offerta, con due logiche diverse di conversione.

```text
                       ┌──────────────────────────┐
   PREVENTIVO ACCETTATO │ smistamento per riga     │
   (articoli "una tantum)│  → solo le righe MERCE   │── 1:N ──┐
                       └──────────────────────────┘         │
                                                             ▼
   OFFERTA ACCETTATA   ┌──────────────────────────┐    ┌────────────┐  push   ┌──────────┐
   (condizioni in blocco)│ conversione 1:1 in blocco │──▶│   ORDINE   │────────▶│ COMMESSA │──▶ Fattura
                       │  XOR contratto            │    │  DRAFT →   │         │ (attività│
                       └──────────────────────────┘    │ CONFERMATO │         │ fatturab.)│
                                                        │  → EVASO   │         └──────────┘
                                                        └────────────┘
   CREAZIONE MANUALE ──────────────────────────────────────▲
   (ordine "diretto")
```

### 2.1 Dal preventivo: smistamento per riga (1:N)

Un preventivo raccoglie articoli di **natura mista**. Quando viene accettato, le
sue righe non finiscono tutte nello stesso posto:

- le righe di **merce** (natura con destinazione "ORDINE") vengono **smistate in un
  ordine di vendita**;
- i **servizi una tantum** vanno invece in **commessa** (push commessa);
- i **servizi ricorrenti** non possono nemmeno stare su un preventivo: si gestiscono
  con un'offerta che genera un contratto (vedi [Gestione Offerte §1.2](/guide/gestione-offerte-commerciali)).

Lo smistamento è **riga-per-riga e selettivo**: l'operatore, dal *Pannello
Smistamento* del preventivo, sceglie quali righe merce mandare a ordine. Per questo
il legame preventivo → ordine è **1:N**: dallo stesso preventivo possono nascere
più ordini (per esempio consegne in momenti diversi). Ogni riga di preventivo,
però, può essere smistata **una sola volta** (idempotenza di riga): se si riprova a
smistare una riga già allocata, viene semplicemente saltata.

> Quando non resta più nulla da smistare su **nessun** ramo (né merce né servizi),
> il preventivo passa automaticamente da ACCETTATO a **EVASO** (gate EVASO).

### 2.2 Dall'offerta: conversione 1:1, in alternativa al contratto

L'offerta commerciale propone **condizioni in blocco**. Quando viene convertita in
ordine, l'ordine eredita **tutte** le righe dell'offerta in una volta sola: il
legame è **1:1**. Una stessa offerta genera **al massimo un ordine**: un secondo
tentativo viene rifiutato (`E_ORD_OFFERTA_GIA_CONVERTITA`).

C'è di più: un'offerta accettata può diventare **o** un contratto (fornitura
ricorrente) **o** un ordine (vendita una tantum), **mai tutti e due**. È la regola
di **mutua esclusività** offerta → (contratto XOR ordine): la prima conversione
"consuma" l'offerta verso una delle due strade.

### 2.3 Creazione manuale

È sempre possibile creare un ordine **da zero**, scegliendo cliente e righe a mano.
In questo caso l'ordine nasce senza riferimento a un documento di origine.

---

## 3. Le entità in gioco

### 3.1 Testata `ordini`

Contiene il contesto del documento:

- **chi** (`billing_account_id` + `soggetto_ruolo_id`) — il cliente. Se si indica il
  billing account, il soggetto viene derivato da sé.
- **chi emette** (`emittente_fiscale_id`) — l'emittente fiscale; se omesso lo
  imposta un trigger (vedi §7).
- **per cosa** (`utility_id`) — opzionale.
- **quando** (`data`) — default alla data odierna.
- **come si paga** (`modalita_pagamento_id`, `termine_pagamento_id`, `valuta_id`,
  `tasso_cambio`).
- **quando fatturare** (`fatturazione_trigger`: `CONFERMATO` | `SPEDITO` |
  `CONSEGNATO`) — governa il *momento* del push a commessa. Il default è ereditato
  dal cliente; oggi il valore operativo è `CONFERMATO`.
- **da dove arriva** (`canale_origine`: `ADMIN` | `PORTALE` | `SHOP`) — in
  back-office è sempre `ADMIN` e non si cambia.
- **chi ha venduto** (`agente_soggetto_ruolo_id`) — agente/venditore, opzionale.
- **origine documentale** (`documento_origine_tipo` ∈ {`PREVENTIVO`, `OFFERTA`} +
  `documento_origine_id`) — valorizzata in automatico dalla conversione; NULL se
  l'ordine è creato a mano.
- **identità e stato** (`numero`/`serie`/`anno`, `uid`, `stato_doc_ordine_id`) e i
  **totali** (`imponibile_tot`, `iva_tot`, `totale_doc`), tenuti aggiornati dai
  trigger.

### 3.2 Righe `ordini_righe`

Ogni riga è una voce da consegnare/fatturare:

- **articolo** (`articolo_id`) e **descrizione**
- **quantità** in doppia unità: quella **operativa** scelta dall'operatore
  (`qta_operativa` + `uom_operativa_id`) e quella **base** (`quantita`) calcolata
  automaticamente dal fattore di conversione (`factor_to_base`)
- **prezzo** (`prezzo_unitario`), **sconto** percentuale, **IVA** (`iva_id`)
- **`attivo`** — una riga disattivata non concorre ai totali
- **`preventivo_riga_id`** — il legame con la riga del preventivo da cui è nata
  (presente solo per gli ordini da smistamento); è ciò che garantisce
  l'idempotenza di riga.

Vincoli per l'operatore: **quantità > 0** e **prezzo ≥ 0** (un omaggio è quantità
positiva con prezzo zero).

### 3.3 Componenti BoM `ordini_righe_componenti`

Quando una riga punta a un **articolo composito** (distinta base), il sistema
genera in automatico un componente per ogni pezzo della BoM. Come nel resto della
famiglia vendite, il prezzo del padre è la **somma pesata** dei figli e non si
inserisce a mano. La composizione (quali componenti, in quali proporzioni) è
**immutabile**: si possono cambiare i prezzi, non i pezzi.

### 3.4 Note `note_ordini`

L'ordine supporta le **note partizionate** (di testata o di singola riga), con lo
stesso comportamento di preventivi, offerte e contratti.

> **Nota sull'ambito attuale.** Entrambe le tabelle sono ora **gestite**:
> `ordini_indirizzi` alimenta la sezione indirizzi del documento (UX v2), e
> `ordini_righe_fulfillment` registra l'**evasione** dell'ordine in uno o più
> **DDT** (residuo per riga, append-only). Vedi [Gestione DDT](/guide/gestione-ddt).

---

## 4. Ciclo di vita e stati

### 4.1 Stati

Il catalogo `config.stati_doc_ordini` prevede più stati, ma **oggi ne sono attivi
solo tre**. Gli altri sono predisposti per il futuro (magazzino/DDT/finanza) e non
vengono raggiunti da alcun processo sull'ordine.

| Stato | Significato | Modificabile? | Terminale? | In uso oggi |
|---|---|---|---|---|
| `DRAFT` | Bozza in preparazione | Sì: testata e righe | No | ✅ |
| `CONFERMATO` | Ordine confermato, pronto per il push a commessa | No | No | ✅ |
| `EVASO` | Righe inviate a commessa (push completato): il giro è chiuso | No | Sì | ✅ |
| `ANNULLATO` | Bozza annullata | No | Sì | ✅ |
| `ALLOCATO` / `SPEDITO` / `CONSEGNATO` / `FATTURATO` | Fasi logistiche/finanziarie future | — | — | ⏳ non ancora raggiunti |

### 4.2 Transizioni ammesse

Le transizioni sono governate dalla matrice `config.transizioni_stati_ordini`, che
per gli ordini è anche la **fonte unica di verità**: la stessa tabella decide sia
cosa mostrare in interfaccia, sia cosa il database accetta davvero.

```text
DRAFT ──(conferma)──▶ CONFERMATO ──(push commessa completato)──▶ EVASO (terminale)
  │
  └──(annulla)──▶ ANNULLATO  (terminale)

CONFERMATO ┄┄(annulla)┄┄▶ ANNULLATO     (presente ma DISABILITATO)
```

- **DRAFT → CONFERMATO** (*conferma*): richiede **almeno una riga**.
- **DRAFT → ANNULLATO** (*annulla*): sempre consentito — una bozza non ha nulla da
  evadere.
- **CONFERMATO → EVASO** (*automatica*): scatta da sé quando il **push a commessa**
  si conclude con esito **completato** (vedi §10). Non è un pulsante: è una
  transizione automatica che chiude il giro. `EVASO` è **terminale**.
- **CONFERMATO → ANNULLATO**: la riga esiste in matrice ma è **disabilitata**. Un
  ordine confermato **non si annulla con un click**: la riabilitazione arriverà
  insieme alla regola "annullabile solo se non ancora evaso/fatturato".

> **Il push a commessa non è una transizione "a pulsante".** Il push crea le entità
> a valle (attività fatturabili); se va a buon fine **per intero**, porta poi
> l'ordine a `EVASO` in automatico. Se il push è solo parziale o fallisce, l'ordine
> **resta `CONFERMATO`** ed è possibile ripeterlo.

### 4.3 La doppia difesa

Le regole di transizione valgono a **due livelli**:

1. **In interfaccia**: la funzione `fn_available_actions_ordine` legge la matrice e
   restituisce solo le azioni davvero disponibili — così i pulsanti che non hanno
   senso semplicemente non compaiono.
2. **Nel database**: il trigger `trgfn_ordini_guard_transizione` rifiuta qualsiasi
   cambio di stato non previsto (`E_ORDINE_TRANSIZIONE_NON_AMMESSA`) e blocca la
   conferma di un ordine senza righe (`E_ORDINE_CONFERMA_SENZA_RIGHE`).

---

## 5. Azioni disponibili

Le azioni eseguibili in ogni momento sono calcolate dal database
(`fn_available_actions_ordine`) ed esposte all'interfaccia come elenco di
*capability*, così il frontend non deve replicare la logica degli stati.

Per ogni stato la funzione indica le azioni e alcuni flag utili:

| Flag | Vero quando |
|---|---|
| `can_edit_testata` / `can_edit_righe` | l'ordine è in `DRAFT` |
| `can_push_commessa` | l'ordine è `CONFERMATO`, `fatturazione_trigger = CONFERMATO` e c'è almeno una riga eleggibile |
| `can_push_commessa_reason` / `_reason_key` | (se il push non è possibile) il motivo, mostrato come tooltip |
| `non_editable_fields` | l'elenco dei campi bloccati (es. cliente, numero) |

In sintesi:

- **In `DRAFT`**: si può **modificare** testata e righe, **confermare** (azione
  *conferma*) o **annullare** (azione *annulla*).
- **In `CONFERMATO`**: testata e righe sono **in sola lettura**; l'azione
  disponibile è il **push a commessa** (quando le precondizioni sono soddisfatte).
  A push completato l'ordine passa a `EVASO`.
- **In `EVASO`** o **in `ANNULLATO`**: nessuna azione, sola lettura. Su un ordine
  `EVASO` il push non è più proponibile (motivo `ORDINE_GIA_EVASO`): l'invio a
  commessa è **unico**.

---

## 6. Creazione di un ordine

### 6.1 Da preventivo (smistamento merce)

Dal preventivo accettato, l'operatore apre il *Pannello Smistamento*, seleziona le
righe **merce** e lancia lo smistamento. Il sistema:

1. crea un ordine in `DRAFT` copiando il contesto dal preventivo;
2. copia **solo** le righe selezionate di natura merce, con i loro prezzi e i
   componenti BoM;
3. registra su ogni riga il legame con la riga di preventivo di origine
   (idempotenza);
4. valorizza l'origine documentale come `PREVENTIVO`.

Se tutte le righe merce sono già state smistate, l'operazione segnala che non c'è
nulla da convertire (`E_VENDITA_PREVENTIVO_NESSUNA_RIGA_ORDINE`). Se il preventivo
non è in stato accettato, l'operazione è rifiutata
(`E_VENDITA_PREVENTIVO_PUSH_STATO_NON_AMMESSO`).

### 6.2 Da offerta (conversione 1:1)

Dall'offerta accettata, la conversione genera **un solo** ordine `DRAFT` con
**tutte** le righe espanse dell'offerta (prezzi negoziati e override preservati).
Vincoli:

- l'offerta deve essere **accettata**;
- non deve essere già stata convertita in ordine (`E_ORD_OFFERTA_GIA_CONVERTITA`);
- non deve aver già generato un contratto (mutua esclusività).

### 6.3 Manuale

1. **Nuovo ordine** → scegli il cliente (billing account), eventualmente l'utility,
   la data e le condizioni di pagamento.
2. L'ordine nasce in `DRAFT` con numero già assegnato.
3. **Aggiungi le righe**: cerca l'articolo, indica quantità e — se serve — prezzo e
   sconto. Se ometti il prezzo, il sistema lo propone tramite il pricing (vedi §8).
4. Per gli **articoli compositi**, un dialog mostra l'anteprima dei componenti e ne
   propone i prezzi; alla conferma i componenti vengono salvati.

> **Bozza "usa e getta".** La creazione salva subito una bozza per poter aggiungere
> le righe. Se l'operatore esce senza inserirne nessuna, quella bozza vuota può
> essere eliminata. Un ordine **con righe**, invece, non si cancella: si **annulla**.

---

## 7. Cliente ed emittente fiscale

### 7.1 Cliente immutabile

Una volta creato l'ordine, il **cliente non si cambia più**: i campi
`billing_account_id` e `soggetto_ruolo_id` sono bloccati. Tentare di modificarli dà
`E_ORD_CLIENTE_IMMUTABILE`. La regola è semplice: **cambiare cliente = nuovo
ordine**. È una protezione dagli errori (la ricerca del cliente è frequente, il
cambio è raro e avrebbe pesanti riflessi contabili). Il blocco è applicato sia dal
backend sia, in modo autoritativo, dal database.

### 7.2 Emittente fiscale

Se l'operatore **non** indica un emittente fiscale, lo imposta automaticamente il
trigger `trgfn_ordini_default_emittente`, in base all'emittente associato
all'utente che sta operando. Inoltre, se l'ordine ha un cliente, l'emittente deve
essere **coerente** con quel cliente: a questo pensa il trigger
`trgfn_ordini_guard_emittente_ba`, che rifiuta combinazioni incoerenti. In pratica
l'operatore raramente deve preoccuparsene, ma se l'utente non ha un emittente
assegnato la creazione viene bloccata con un errore parlante.

---

## 8. Prezzi e totali

### 8.1 Come si determina il prezzo

Il prezzo delle righe arriva da una di queste vie:

- **conversione**: nei percorsi da preventivo/offerta il prezzo è già quello
  negoziato a monte e viene "fotografato" sull'ordine;
- **inserimento manuale**: l'operatore digita il prezzo;
- **proposta automatica**: se il prezzo è assente (e l'articolo non è composito), il
  sistema lo risolve dal listino tramite il *PricingService*.

> **Niente gate prezzi L2/L3 sull'ordine.** A differenza di offerte e contratti,
> l'ordine **non** applica le soglie e l'escalation di approvazione prezzo: è una
> scelta di modello (pricing "stile preventivo" — si risolve il prezzo e si usa
> quello del chiamante). Le eventuali approvazioni sono già avvenute a monte.

### 8.2 Totali e IVA

I totali di testata (imponibile, IVA, totale documento) sono **calcolati e tenuti
aggiornati dal database** ad ogni modifica delle righe (`fn_ricalcola_totali_ordine`
e i relativi trigger): l'operatore li vede aggiornarsi senza dover fare nulla.

L'IVA è calcolata **per gruppo di aliquota** (non riga per riga), secondo la regola
fiscale standard. Il *Riepilogo IVA* dell'ordine mostra una riga per aliquota con
imponibile, imposta, arrotondamento e totale.

---

## 9. Conferma e stampa

Nella famiglia vendite **confermare equivale a emettere il documento**. Il percorso
principale dell'operatore è l'azione **Emetti**:

1. dall'ordine in `DRAFT` si lancia l'emissione;
2. il sistema **conferma** l'ordine (`DRAFT → CONFERMATO`) e, nella **stessa
   operazione atomica**, **genera il PDF** di conferma d'ordine;
3. si possono allegare file opzionali.

Se la generazione del PDF fallisce, **anche la conferma viene annullata**: l'ordine
resta in `DRAFT` e non si crea alcun documento "monco".

Cosa contiene il PDF: numero e data ordine, cliente, emittente, eventuale
provenienza (da preventivo/offerta), righe con quantità/prezzo/sconto, totali per
aliquota IVA e note.

> **Anteprima vs documento definitivo.** In `DRAFT` è disponibile solo
> l'**anteprima** del PDF. Il documento "vero" (persistito, scaricabile,
> ristampabile) nasce con la conferma. Per la stampa serve che esista un **template
> "ORDINE_VENDITA" pubblicato** (vedi [Documenti e stampe](/guide/documenti-e-stampe)).

---

## 10. Push a commessa

Quando l'ordine è `CONFERMATO` (e `fatturazione_trigger = CONFERMATO`), l'azione
**push a commessa** chiude il giro: le righe eleggibili dell'ordine generano le
**attività fatturabili** su una commessa, che a sua volta alimenta la pipeline di
fatturazione.

Sono eleggibili le righe attive, con quantità positiva, non ancora inviate a una
commessa. Se non c'è alcuna riga eleggibile, l'azione non è disponibile e
l'interfaccia ne spiega il motivo.

**L'invio a commessa è unico.** Se il push si conclude **completato**, l'ordine
passa automaticamente da `CONFERMATO` a **`EVASO`** (stato terminale): da lì non si
ri-pusha più. Se invece il push è **parziale** o **fallisce**, l'ordine **resta
`CONFERMATO`** e si può ripetere finché non è completo.

> **Il push autorizza anche la fatturazione.** Dato che un ordine `CONFERMATO` è già
> autorizzato, al termine del push le commesse toccate vengono rese **emittibili**
> (attività approvate + testata "pronta per la fatturazione"), senza un passaggio di
> approvazione aggiuntivo. Il dettaglio è in [Gestione Commesse](/guide/gestione-commesse)
> e [Fatturazione](/guide/fatturazione).

---

## 11. Lista ordini

La lista ordini è una **lista configurabile** (l'utente può scegliere colonne e
ordinamento). Mostra di norma numero, data, cliente, utility, totale, stato e
trigger di fatturazione; sono disponibili in opzione colonne aggiuntive (importi di
dettaglio, pagamento, emittente, origine documentale, agente, ecc.).

Filtri principali: ricerca testuale (numero, ragione sociale, codice cliente, codice
fiscale/P.IVA), stato, cliente, utility, intervallo di date. La lista rispetta
automaticamente lo **scope dell'emittente** dell'utente: ognuno vede solo i propri
ordini.

Dalla lista si aprono il dettaglio, l'export (CSV/XLSX) e la gestione dei documenti
generati.

---

## 12. Casi d'uso operativi

### 12.1 Ordine di sola merce da un preventivo

1. Il preventivo viene **accettato**.
2. Apri il *Pannello Smistamento* → seleziona le righe **merce** → "Smista
   selezionate".
3. Nasce un ordine in `DRAFT` con quelle righe. (I servizi una tantum del
   preventivo seguono il loro percorso verso la commessa.)
4. "Emetti" → l'ordine passa a `CONFERMATO` e si genera il PDF.
5. "Push a commessa" → parte la fatturazione.

### 12.2 Consegne parziali dallo stesso preventivo

1. Primo smistamento: seleziona solo una parte delle righe merce → primo ordine.
2. Più tardi: torna sul preventivo e smista le righe residue → secondo ordine.
3. Quando non resta più nulla da smistare su nessun ramo, il preventivo passa a
   **EVASO** da sé.

### 12.3 Ordine da offerta

1. L'offerta viene **accettata**.
2. "Genera ordine" → nasce **un** ordine con tutte le righe dell'offerta.
3. Da quel momento l'offerta non potrà più generare un contratto (mutua
   esclusività), e un secondo "Genera ordine" verrà rifiutato.

### 12.4 Ordine manuale con articolo composito

1. Nuovo ordine → cliente → "Aggiungi riga" con un articolo composito.
2. Il dialog mostra i componenti e propone i prezzi → conferma.
3. Il prezzo della riga è la somma dei componenti; aggiusta i prezzi se serve.
4. "Emetti" → conferma + PDF.

### 12.5 Bozza creata per errore

1. Ordine ancora in `DRAFT` **senza righe** → eliminabile.
2. Ordine in `DRAFT` **con righe** → non si elimina: usa "Annulla" (→ `ANNULLATO`).

---

## 13. Errori principali

Codici sollevati dal dominio ordini (registrati in `config.messaggi_errore` /
`error_policies`):

| Codice | Quando |
|---|---|
| `E_ORD_NOT_FOUND` | Ordine (o riga/componente) inesistente o fuori dal proprio scope emittente |
| `E_ORD_VALIDAZIONE` | Payload non valido (cliente mancante, campi vuoti, valori non numerici…) |
| `E_ORD_CLIENTE_IMMUTABILE` | Tentativo di cambiare il cliente di un ordine già creato |
| `E_ORD_STATO_TRANSIZIONE` | Operazione non ammessa nello stato (es. modifica fuori da `DRAFT`, oppure delete di una bozza con righe → va annullata) |
| `E_ORD_NESSUNA_RIGA` | Conferma/push senza righe eleggibili (controllo applicativo) |
| `E_ORD_OFFERTA_GIA_CONVERTITA` | Conversione offerta → ordine già avvenuta (univocità 1:1) |
| `E_OFFERTA_CONTRATTO_GIA_GENERATO` | L'offerta ha già generato un contratto: non può generare anche un ordine (mutua esclusività XOR) |
| `E_ORD_ORIGINE_NON_CONVERTIBILE` | Conversione da un'offerta non in stato convertibile (non ACCETTATA) |
| `E_ORDINE_TRANSIZIONE_NON_AMMESSA` | Cambio di stato non previsto/attivo nella matrice transizioni (guard DB) |
| `E_ORDINE_CONFERMA_SENZA_RIGHE` | Conferma di un ordine senza righe (guard DB, gemello di `E_ORD_NESSUNA_RIGA`) |
| `E_VENDITA_PREVENTIVO_PUSH_STATO_NON_AMMESSO` | Smistamento da un preventivo non accettato |
| `E_VENDITA_PREVENTIVO_NESSUNA_RIGA_ORDINE` | Smistamento senza righe merce residue (tutte già allocate o nessuna di natura merce) |
| `E_DOCUMENTI_*` | Stampa: template/versione non risolti, input invalido o render fallito |

---

## 14. Pattern e principi di design

### 14.1 Ordine come "fotografia" operativa

L'ordine non rimanda a un listino né si revisiona: i prezzi sono congelati alla
nascita. È il documento che dice "questo è ciò che facciamo", non "questo è ciò che
proporremmo". Per questo è più semplice di preventivo, offerta e contratto.

### 14.2 Due conversioni, due nature

Preventivo → ordine è **1:N per riga** perché il preventivo è un elenco di articoli
a natura mista. Offerta → ordine è **1:1 in blocco** perché l'offerta è una proposta
unitaria. La stessa offerta, inoltre, sceglie **una** strada — contratto **o**
ordine — mai entrambe.

### 14.3 Matrice transizioni come unica fonte di verità

Per gli ordini la tabella `config.transizioni_stati_ordini` serve **sia** a
costruire i pulsanti in interfaccia **sia** a far rispettare il grafo nel database.
Una sola fonte: ciò che la UI mostra è esattamente ciò che il DB accetta. Per
attivare in futuro gli stati a valle (magazzino/DDT) basterà aggiungere righe a
quella matrice.

### 14.4 Trigger DB come ultima difesa

Cliente immutabile, transizioni ammesse, "almeno una riga" per confermare, coerenza
emittente/cliente, numero immutabile: sono tutte regole presidiate da trigger DB.
Il backend ha controlli equivalenti solo per dare messaggi chiari prima del giro al
database; anche bypassandolo, il database rifiuta comunque le operazioni scorrette.

---

## 15. Glossario rapido

| Termine | Significato |
|---|---|
| **Ordine di vendita** | Documento operativo del ciclo attivo: righe da consegnare/fatturare. Stati: `DRAFT` → `CONFERMATO` → `EVASO` (oppure `ANNULLATO`) |
| **Smistamento** | Conversione delle righe **merce** di un preventivo accettato in uno o più ordini (1:N, riga per riga) |
| **Conversione 1:1** | Generazione di un singolo ordine da un'offerta accettata, in alternativa al contratto (XOR) |
| **Emetti** | Conferma dell'ordine + generazione del PDF, in un'unica operazione atomica |
| **Push a commessa** | Invio delle righe eleggibili a una commessa, che avvia la fatturazione; a push completato l'ordine passa a `EVASO` (invio unico) |
| **`fatturazione_trigger`** | Quando l'ordine pusha a commessa (oggi: `CONFERMATO`) |
| **Cliente immutabile** | Il cliente non si cambia dopo la creazione: "cambiare cliente = nuovo ordine" |
| **Matrice transizioni** | `config.transizioni_stati_ordini`: fonte unica di verità per UI ed enforcement |

---

*Per il dettaglio tecnico delle API REST, formati payload e codici errore vedi la
[documentazione API Ordini](/backend/vendite/manual/api_ordini). Le decisioni di
modello sono raccolte negli addendum di sviluppo (`dev/work-done/db-brief-ordini-vendita.md`,
`brief-ordini-stampa.md`, `db-brief-ordini-lock-cliente.md`, `brief-preventivi-ordini.md`).*
</content>
</invoke>
