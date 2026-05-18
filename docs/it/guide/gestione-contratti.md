# Guida — Gestione Contratti vendita

> **Ultima revisione**: 15 maggio 2026 — modello unificato post-refactor
> (drop modalità A/B/C, `tipo_eccezione` su `contratti_righe`, snapshot
> `listino_versione_id` all'attivazione, lock post-attivazione).
>
> **Destinatari**: analisti funzionali, sviluppatori backend/frontend, DBA.
>
> **Vedi anche** — schemi DB:
>
> * [vendite.contratti](/dbzero/vendite/tabelle/contratti) / [vendite.contratti_righe](/dbzero/vendite/tabelle/contratti_righe) / [vendite.contratti_righe_componenti](/dbzero/vendite/tabelle/contratti_righe_componenti)
> * [vendite.contratti_utilities](/dbzero/vendite/tabelle/contratti_utilities)
> * [config.stati_doc_contratti](/dbzero/config/tabelle/stati_doc_contratti) / [config.transizioni_stati_contratti](/dbzero/config/tabelle/transizioni_stati_contratti)
> * [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — BoM versionata immutabile
>
> **Vedi anche** — funzioni e trigger DB:
>
> * [vendite.fn_resolve_prezzo_listino_v2](/dbzero/vendite/funzioni/fn_resolve_prezzo_listino_v2) — resolver pricing bundle-aware, STADIO 1
> * [vendite.trgfn_contratti_freeze_listino_versione](/dbzero/vendite/manual/trgfn_contratti_freeze_listino_versione) — snapshot versione listino a DRAFT→ATTIVO
> * [vendite.trgfn_contratti_lock_post_attivazione](/dbzero/vendite/manual/trgfn_contratti_lock_post_attivazione) — blocco testata post-attivazione
> * [vendite.trgfn_contratti_righe_lock_post_attivazione](/dbzero/vendite/manual/trgfn_contratti_righe_lock_post_attivazione) — blocco righe post-attivazione
> * [vendite.trgfn_contratti_righe_guard_aggiunta_fuori_listino](/dbzero/vendite/manual/trgfn_contratti_righe_guard_aggiunta_fuori_listino) — guard AGGIUNTA già in listino
> * [vendite.fn_contratto_riga_componenti_init](/dbzero/vendite/manual/fn_contratto_riga_componenti_init) — popola componenti BoM su riga padre composito
> * [vendite.fn_contratto_riga_componenti_preview](/dbzero/vendite/manual/fn_contratto_riga_componenti_preview) — suggerimento prezzi pre-save
>
> **Vedi anche** — guide correlate:
>
> * [Gestione Listini e Pricing v5](/guide/gestione-listini) — cascata promo → contratto → categoria
> * [Gestione Preventivi](/guide/gestione-preventivi) — proposta puntuale (→ commessa); modello simmetrico
> * [Fatturazione end-to-end](/guide/fatturazione) — la pipeline a valle del contratto
> * [Modello componenti BoM](/dev/manual/modello-componenti-bom) — simmetria cross-dominio

---

## 1. Cosa è un contratto

Un contratto è la **relazione commerciale duratura** fra l'azienda e un cliente
per una specifica utility (Gas, Energia, Idrico, ecc.). Risponde alla domanda:
*"Quali condizioni di prezzo si applicano a questo cliente su questo servizio
nel periodo di validità?"*

Caratteristiche di base:

- è intestato a un **billing account** (cliente) e a una **utility** (servizio)
- definisce il **listino di riferimento** (opzionale) e un'eventuale **variazione
  globale** (sconto o maggiorazione applicata a tutto il listino)
- può contenere **eccezioni puntuali** per singoli articoli (prezzi personalizzati,
  esclusioni, articoli fuori listino)
- ha un **ciclo di vita** con stati da bozza a attivo, fino alla cessazione
- quando **attivato**, viene usato come primo stadio (STADIO 1) del resolver
  pricing per determinare il prezzo applicabile a ogni articolo del BA

Il numero documento è auto-generato (prefisso `CNT`) e non modificabile.

### 1.1 Il modello unificato (post-refactor maggio 2026)

Prima del refactor esistevano tre "modalità" esplicite (A/B/C) che l'operatore
sceglieva all'apertura del form. Le modalità sono state eliminate: il contratto
ha ora un **modello unico**, e la sua "forma" è derivata automaticamente dai
dati compilati:

| Forma derivata | Condizione | Significato commerciale |
|---|---|---|
| **Con listino** | `listino_id NOT NULL` | Il cliente ha un listino di partenza (con o senza variazione globale e con o senza eccezioni puntuali) |
| **Senza listino** | `listino_id NULL` | Tutto negoziato puntualmente — le righe sono l'unica fonte di prezzo |

La variazione globale è un campo opzionale della testata. Le eccezioni sulle righe
sono compatibili con la variazione globale: un contratto con listino può avere
sia variazione globale che override su singoli articoli — non c'è contraddizione.

---

## 2. Le entità in gioco

### 2.1 Testata `contratti`

Contiene il contesto commerciale e i parametri di pricing:

- **chi** (`billing_account_id`, `istanza_utility_id`)
- **per cosa** (`utility_id`, `ambito`: COMMODITY / COMMERCIO)
- **quando** (`data`, `valido_dal`, `valido_al`)
- **listino** (`listino_id` nullable, `listino_versione_id` nullable — fissato all'attivazione)
- **variazione globale** (`tipo_variazione_globale`, `valore_variazione_globale`) — opzionale;
  si applica a tutte le righe listino salvo override puntuale
- **stato** corrente (`stato_doc_contratto_id`)
- **categoria cliente** al momento della creazione (`categoria_cliente_id`) — snapshot
  congelato, non segue variazioni anagrafica

I campi `listino_id`, `listino_versione_id`, `tipo_variazione_globale`,
`valore_variazione_globale` diventano **immutabili** al passaggio in ATTIVO
(lock post-attivazione — vedi §6).

### 2.2 Eccezioni `contratti_righe`

Contiene le **eccezioni puntuali** al listino. Una riga non è un "articolo da
ordinare" come in un preventivo, ma un **modificatore** che sovrascrive o
integra il listino per un articolo specifico. Il campo `tipo_eccezione` (ENUM
NOT NULL) qualifica esplicitamente il tipo:

| `tipo_eccezione` | Significato | `prezzo_unitario` |
|---|---|---|
| `OVERRIDE` | Prezzo personalizzato per articolo **presente nel listino** — la variazione globale non si applica; l'override è il prezzo finale | NOT NULL |
| `ESCLUSIONE` | Articolo del listino **non disponibile** per questo cliente — il resolver solleva errore se richiesto | NULL |
| `AGGIUNTA` | Articolo **non presente nel listino**, aggiunto al contratto — valido anche su contratti senza listino | NOT NULL |

Constraint DB:

- OVERRIDE e ESCLUSIONE: al massimo una riga per `(contratto, articolo)` (unique parziale)
- AGGIUNTA: al massimo una riga per `(contratto, articolo)` (unique parziale separato)
- CHECK: `prezzo_unitario NOT NULL` se OVERRIDE o AGGIUNTA; NULL obbligatorio se ESCLUSIONE
- Guard: una AGGIUNTA è bloccata se l'articolo è già nel listino fissato al contratto
  (si deve usare OVERRIDE)

Operativamente: in DRAFT le righe sono liberamente modificabili; dopo l'attivazione
ogni INSERT / UPDATE / DELETE è bloccato dal trigger di lock.

### 2.3 Utility `contratti_utilities`

Riga 1:1 con l'utility del contratto. Porta i parametri specifici della fornitura:
tipo utenza, classe utenza, dati PDP (punto di prelievo/consegna), parametri
precontrattuali. È creata contestualmente alla testata.

### 2.4 Componenti BoM `contratti_righe_componenti`

Quando una riga punta a un articolo `is_composito = TRUE`, il sistema genera
automaticamente un record per ogni **componente** della BoM. Il prezzo del padre
(OVERRIDE o AGGIUNTA) è la **somma pesata** dei prezzi figli — mai inserita a
mano.

I componenti portano:

- riferimento al componente del catalogo + UoM + quantità (= padre × `coeff_qta`)
- prezzo unitario (modificabile con autorizzazioni)
- snapshot del coefficiente al momento della creazione
- origine prezzo (CONTRATTO_OVERRIDE / CONTRATTO_AGGIUNTA / CONTRATTO_LISTINO / CATEGORIA)

La struttura BoM (quali componenti, in che quantità relative) è **immutabile per
contratto**: si possono cambiare i prezzi, non la composizione.

---

## 3. Ciclo di vita e stati

### 3.1 Stati e transizioni

Gli stati sono governati da `config.stati_doc_contratti` e le transizioni ammesse
da `config.transizioni_stati_contratti`:

| Stato | Significato | Modificabile? |
|---|---|---|
| `DRAFT` | Bozza in costruzione | Sì: testata, righe, utility |
| `ATTIVO` | Contratto in vigore — usato dal resolver pricing | No (lock post-attivazione) |
| `CESSATO` | Contratto scaduto o terminato | No (terminale) |

La transizione `ATTIVO → CESSATO` può essere **automatica** (job notturno quando
`valido_al < CURRENT_DATE`) o **manuale** (operatore che chiude anticipatamente).

Non esiste revisione come nei preventivi: se le condizioni cambiano, si cessa il
contratto corrente e se ne crea uno nuovo.

### 3.2 Cosa succede alla transizione DRAFT → ATTIVO

Il trigger `trgfn_contratti_freeze_listino_versione` interviene BEFORE UPDATE
sulla colonna `stato_doc_contratto_id`. In sequenza:

1. **Guard negoziato puro senza righe**: se `listino_id IS NULL` e non ci sono
   righe AGGIUNTA (o OVERRIDE) in `contratti_righe`, solleva
   `E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE` (451). Un contratto senza listino
   e senza eccezioni non ha senso — non c'è nessun prezzo da applicare.
2. **Snapshot versione listino**: se il contratto ha `listino_id` valorizzato,
   cerca la versione attiva alla data corrente e scrive `listino_versione_id`.
   Da quel momento la versione è **congelata** (§4.2 per le implicazioni runtime).
3. **Lock**: da ATTIVO in poi, testata e righe sono immutabili (§6).

---

## 4. Il modello di pricing del contratto

### 4.1 Il contratto come STADIO 1 del resolver

Il resolver prezzi `fn_resolve_prezzo_listino_v2` valuta tre stadi in cascata:

```
STADIO 0: promo_articoli (overlay)
STADIO 1: contratto attivo (OVERRIDE / ESCLUSIONE / AGGIUNTA + listino con versione fissata)
STADIO 2: matrice categorie_clienti_listini (listino categoria)
```

Il contratto è **STADIO 1**: se esiste un contratto ATTIVO per il BA alla data
richiesta, i prezzi vengono risolti da lì prima di guardare la categoria cliente.

### 4.2 Versione listino fissata all'attivazione

In DRAFT il contratto "segue" la versione corrente del listino: ogni volta che
si legge la preview righe, il resolver usa la versione attiva alla data odierna.

Alla transizione DRAFT → ATTIVO il trigger **fissa** `listino_versione_id`:

- da quel momento il contratto legge **sempre quella versione specifica** del
  listino, anche se nel frattempo ne esce una v6, v7, ecc.
- il cliente ha un prezzo prevedibile per tutta la durata del contratto
- gli articoli non presenti nella versione fissata (aggiunti in versioni
  successive) **non** sono automaticamente disponibili nel contratto

**Conseguenza in DRAFT**: se durante la lavorazione della bozza viene pubblicata
una nuova versione del listino, la preview si aggiorna automaticamente ai nuovi
prezzi. Gli OVERRIDE e AGGIUNTA già inseriti restano validi (puntano all'articolo,
non alla versione). Il banner UI segnala il drift: "Il listino è stato aggiornato
alla v6 — le tue eccezioni fanno ancora riferimento alla v5, rivedi prima di
attivare".

### 4.3 Logica di risoluzione prezzo (STADIO 1)

Dato un articolo richiesto per il contratto, il resolver cerca in `contratti_righe`:

1. **Riga ESCLUSIONE** → `E_ARTICOLO_ESCLUSO_DA_CONTRATTO` (453). L'articolo non è
   fatturabile per questo cliente con questo contratto.
2. **Riga OVERRIDE** → usa `prezzo_unitario` come prezzo finale (`origine =
   CONTRATTO_OVERRIDE`). La variazione globale **non** si applica; l'override è
   il prezzo negoziato definitivo.
3. **Riga AGGIUNTA** → usa `prezzo_unitario` (`origine = CONTRATTO_AGGIUNTA`).
   Vale anche se il contratto non ha listino.
4. **Nessuna eccezione + listino presente** → legge il prezzo dalla versione
   listino fissata e applica eventuale `tipo_variazione_globale` + `valore_variazione_globale`
   (`origine = CONTRATTO_LISTINO`).
5. **Nessuna eccezione + nessun listino** → `E_ARTICOLO_NON_NEGOZIATO_SU_CONTRATTO_C`.

Se il contratto non è trovato (nessun contratto ATTIVO per BA+utility+data), il
resolver scende a STADIO 2 (categoria cliente).

### 4.4 Variazione globale — comportamento

La variazione globale (`tipo_variazione_globale` + `valore_variazione_globale`) si
applica **solo alle righe che non hanno un OVERRIDE puntuale**. Un articolo con
OVERRIDE riceve esattamente il prezzo negoziato, senza variazione globale.

| `tipo_variazione_globale` | Formula                                                          |
|---------------------------|------------------------------------------------------------------|
| `PERCENTUALE`             | `prezzo_listino * (1 + valore / 100)` — valore negativo = sconto |

> Decisione 2026-05-18 (§3-bis-E refactor contratti modalita'): a livello testata
> è ammessa **solo** la variazione PERCENTUALE. `VALORE_FISSO` globale è vietato
> perché un delta in euro insensibile alla magnitudine del listino opacizza la
> natura della variazione e la rende fragile a evoluzioni del catalogo. Resta
> ammesso `VALORE_FISSO` come **OVERRIDE** su singola riga (semantica esplicita
> di "prezzo fisso sostitutivo per quell'articolo"). Il lookup FE espone solo
> PERCENTUALE; il service rifiuta con messaggio parlante eventuali tentativi
> via curl/API esterna.

---

## 5. Articoli compositi e BoM

### 5.1 Cosa succede quando aggiungi un composito

Aggiungendo una riga con articolo `is_composito = TRUE` (come OVERRIDE o AGGIUNTA),
il sistema chiama `fn_contratto_riga_componenti_init`:

1. apre il dialog di **anteprima componenti** che pre-popola i prezzi dei figli
   via `fn_contratto_riga_componenti_preview`
2. l'operatore conferma (o modifica i prezzi suggeriti) e salva
3. il backend crea in transazione atomica:
   - una riga padre in `contratti_righe` (OVERRIDE o AGGIUNTA)
   - N righe figlie in `contratti_righe_componenti` (una per ogni figlio attivo
     nella BoM valida alla data del contratto)
4. il trigger DB ricalcola il prezzo padre come SUM(figli × `coeff_qta_snapshot`)

Se la BoM del padre non ha figli validi, il sistema solleva
`E_DOC_COMPOSITO_BOM_VUOTA`.

### 5.2 Composito OVERRIDE vs composito AGGIUNTA

- **OVERRIDE composito**: il padre è un articolo del listino con prezzo personalizzato.
  I figli BoM leggono la BoM del bundle sulla versione listino fissata al contratto.
  Il resolver usa `p_articolo_padre_contesto` per attivare lo STADIO BUNDLE.
- **AGGIUNTA composita**: il padre è un articolo fuori listino aggiunto al contratto.
  Stessa inizializzazione figli, ma il contesto è autonomo (non dipende dal listino).

### 5.3 Cosa può modificare l'operatore

- ✅ **prezzi unitari** dei componenti, con controlli di autorizzazione (gate L1/L2/L3)
- ✅ **IVA** del componente (deve restare coerente col padre)
- ❌ **non** può aggiungere o rimuovere componenti dalla composizione
- ❌ **non** può cambiare `coeff_qta` (snapshot immutabile)
- ❌ **nessuna modifica** dopo l'attivazione (lock post-attivazione)

---

## 6. Lock post-attivazione e immutabilità

### 6.1 Campi testata bloccati

Da ATTIVO in poi, il trigger `trgfn_contratti_lock_post_attivazione` blocca
qualsiasi UPDATE sui campi:

- `listino_id`
- `listino_versione_id`
- `tipo_variazione_globale`
- `valore_variazione_globale`

Ogni tentativo di modifica solleva `E_CONTRATTO_CAMPI_BLOCCATI_POST_ATTIVAZIONE` (452).

### 6.2 Righe bloccate

Il trigger `trgfn_contratti_righe_lock_post_attivazione` blocca qualsiasi
INSERT, UPDATE o DELETE su `contratti_righe` se il contratto associato è in stato
ATTIVO. Lo stesso errore 452 viene sollevato.

**Conseguenza operativa**: se il cliente rinegozia le condizioni, non si "modifica"
il contratto — si **cessa** quello esistente e si crea un nuovo contratto con le
condizioni aggiornate.

### 6.3 Rimozione listino con eccezioni

Se in DRAFT l'operatore tenta di rimuovere il `listino_id` da un contratto che
ha eccezioni OVERRIDE o ESCLUSIONE, l'API risponde 422 con
`E_CONTRATTO_LISTINO_RIMOZIONE_CON_ECCEZIONI`. Gli OVERRIDE e ESCLUSIONE perdono
significato senza un listino di riferimento. Le AGGIUNTA non bloccano (sono
articoli fuori listino, compatibili con entrambe le forme).

---

## 7. Gate prezzo (L1 / L2 / L3)

Lo stesso meccanismo dei preventivi si applica agli override/variazioni del
contratto. Un operatore che tenta di inserire un prezzo OVERRIDE (o una
variazione globale) passa per tre gate:

- **L1 — Permesso "variare prezzi"**: se l'utente non ha questo permesso,
  il campo variazione e le azioni di override/esclusione/aggiunta sono
  disabilitati in UI e il BE rifiuta in PATCH.
- **L2 — Soglia**: il delta rispetto al prezzo suggerito dal resolver non può
  eccedere le soglie configurate (cascata parametri: user → categoria_cliente →
  group → emittente → default). Oltre il limite, 403 retryable.
- **L3 — Escalation**: l'operatore può richiedere approvazione al superiore
  tramite pratica `APPROVAZIONE_PREZZO`. La riga / variazione resta `PENDING`
  finché approvata o rifiutata. Il contratto non può essere attivato con
  approvazioni pendenti.

---

## 8. Workflow end-to-end

### 8.1 Flusso tipico

```text
   ┌──────────────────┐
   │ Nuovo contratto  │
   │ (operatore crea  │
   │  da zero)        │
   └────────┬─────────┘
            │
   ┌────────▼──────────┐
   │      DRAFT        │
   │ Operatore compila │
   │ testata + utility │
   │ + eccezioni righe │
   └────────┬──────────┘
            │
            │ DRAFT→ATTIVO: trigger fissa listino_versione_id
            │               blocca testata e righe
            │
   ┌────────▼──────────┐
   │      ATTIVO       │
   │ Resolver prezzi   │
   │ usa STADIO 1      │
   └────────┬──────────┘
            │
            │ valido_al scaduto (job notturno) oppure cessazione manuale
            │
   ┌────────▼──────────┐
   │      CESSATO      │
   │ (terminale)       │
   └───────────────────┘
```

### 8.2 Condizioni di attivazione

L'attivazione fallisce (oltre alle guard trigger) se:

- il contratto è in overlap temporale con un altro contratto ATTIVO per la stessa
  quadrupla `(ba, istanza_utility, utility, ambito)` nel periodo `(valido_dal, valido_al)`
  — vincolo EXCLUDE `ex_contratti_no_overlap`
- il contratto è "negoziato puro" (senza listino) e non ha nessuna riga AGGIUNTA/OVERRIDE
- ci sono approvazioni prezzo PENDING non risolte

---

## 9. Casi d'uso operativi

### 9.1 Cliente con listino standard e sconto globale

1. Crea nuovo contratto → seleziona BA, utility, ambito
2. Sezione Pricing: seleziona il listino → inserisci variazione globale (es. `-5%`)
3. Salva testata in DRAFT
4. Sezione Righe: preview mostra tutti gli articoli del listino con sconto 5% applicato
5. Nessuna eccezione necessaria → clicca "Attiva"
6. Trigger fissa versione listino corrente — il cliente mantiene i prezzi della v5
   anche quando viene pubblicata la v6

### 9.2 Cliente VIP con override su articoli specifici

1. Crea contratto con listino (opzionale: variazione globale 0%)
2. Nella vista righe, seleziona articolo → "Modifica prezzo" → inserisci prezzo negoziato
3. L'eccezione viene salvata come `tipo_eccezione = OVERRIDE` in `contratti_righe`
4. Al momento del pricing, il resolver usa quel prezzo; la variazione globale (se presente)
   non viene applicata su quell'articolo
5. Se il delta supera la soglia L2 → gate L3 → pratica approvazione

### 9.3 Cliente senza listino di riferimento (tutto negoziato)

1. Crea contratto **senza** listino (campo vuoto)
2. Nella vista righe, aggiungi articoli uno per uno ("Aggiungi articolo fuori listino")
3. Ogni riga viene salvata come `tipo_eccezione = AGGIUNTA` con prezzo esplicito
4. Tentativo di attivare senza righe → blocco `E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE`
5. Aggiunte almeno le righe necessarie → attivazione OK

### 9.4 Articolo escluso per cliente specifico

1. Contratto con listino già in DRAFT
2. Nella vista righe, seleziona articolo → "Escludi"
3. Riga salvata come `tipo_eccezione = ESCLUSIONE` (prezzo NULL)
4. Da quel momento, il resolver per quel BA + articolo solleva
   `E_ARTICOLO_ESCLUSO_DA_CONTRATTO` invece di restituire un prezzo

### 9.5 Condizioni rinegozia­te post-attivazione

Il contratto attivo è blindato: nessun campo è modificabile.

1. Cessa il contratto corrente (data cessazione = oggi o data concordata)
2. Crea un nuovo contratto DRAFT con le condizioni aggiornate
3. Attiva il nuovo contratto

Non esiste "modifica" di un contratto attivo. Il nuovo contratto sostituirà il
vecchio quando `valido_dal` del nuovo coincide con la cessazione del vecchio.

### 9.6 Kit composto (articolo bundle) in contratto

1. Nella vista righe aggiungi un articolo con `is_composito = TRUE`
2. Si apre il dialog componenti con prezzi pre-popolati (resolver bundle-aware)
3. Conferma (o modifica prezzi figli con eventuale approvazione L3)
4. La riga padre è salvata come AGGIUNTA o OVERRIDE; i figli in
   `contratti_righe_componenti`; il prezzo padre è ricalcolato automaticamente

---

## 10. Errori principali

Codici sollevati dal dominio contratti (registrati in `config.messaggi_errore`):

| Codice | ID | HTTP | Quando |
|---|---|---|---|
| `E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO` | 450 | 422 | AGGIUNTA su articolo già presente nel listino fissato — usare OVERRIDE |
| `E_CONTRATTO_NEGOZIATO_PURO_SENZA_RIGHE` | 451 | 422 | Attivazione contratto senza listino e senza righe AGGIUNTA/OVERRIDE |
| `E_CONTRATTO_CAMPI_BLOCCATI_POST_ATTIVAZIONE` | 452 | 422 | Tentativo modifica testata o righe su contratto ATTIVO |
| `E_ARTICOLO_ESCLUSO_DA_CONTRATTO` | 453 | 422 | Resolver chiede prezzo per articolo con ESCLUSIONE attiva |
| `E_CONTRATTO_LISTINO_RIMOZIONE_CON_ECCEZIONI` | 454 | 422 | Tentativo rimozione listino con OVERRIDE/ESCLUSIONE presenti |
| `E_ARTICOLO_NON_NEGOZIATO_SU_CONTRATTO_C` | — | 422 | Contratto senza listino e nessuna eccezione per l'articolo |
| `E_LISTINO_VERSIONE_NON_ATTIVA` | 448 | 422 | Attivazione con listino che non ha versione attiva alla data corrente |
| `E_DOC_COMPOSITO_BOM_VUOTA` | — | 400 | Composito senza figli BoM validi alla data del contratto |

---

## 11. Pattern e principi di design

### 11.1 Il contratto come delta del listino

Il contratto non importa le righe del listino: nella tabella `contratti_righe`
vivono **solo le eccezioni**. Il listino è un riferimento esterno letto in runtime
dal resolver. Questo mantiene la tabella snella e la semantica delle righe sempre
chiara: se una riga esiste, è un'eccezione intenzionale.

### 11.2 Snapshot della versione e immutabilità

La fissazione di `listino_versione_id` all'attivazione è l'equivalente contrattuale
degli snapshot riga-per-riga dei preventivi: la fotografia dei prezzi viene congelata
al momento della firma. La versione listino, già immutabile per design
(`valido_dal/valido_al` non modificabili sulle righe), garantisce che il contratto
non risenta di modifiche future al catalogo prezzi.

Parallelo con i preventivi:

| Artefatto | Snapshot di | Destinazione |
|---|---|---|
| Preventivo | Prezzo riga-per-riga (materializzato in `prezzo_unitario`) | Commessa → fattura una tantum |
| Contratto | Versione listino (snap di `listino_versione_id`) | Pipeline fatturazione ricorrente |

### 11.3 Trigger DB come ultima difesa

I lock post-attivazione, il guard negoziato puro, il guard AGGIUNTA-già-in-listino
sono trigger DB: anche se il backend non fa le verifiche, il DB rifiuta. Il backend
ha controlli equivalenti per messaggi di errore parlanti prima del roundtrip, ma la
fonte di verità è sempre il trigger.

### 11.4 BoM modello cross-dominio

Lo stesso modello componenti BoM (`*_righe_componenti`) è condiviso tra preventivi,
contratti, ordini e ddt. Guards, trigger di ricalcolo padre e UI del dialog componenti
sono gli stessi in tutti i domini. Vedi [modello componenti BoM](/dev/manual/modello-componenti-bom).

---

## 12. Glossario rapido

| Termine | Significato |
|---|---|
| **Contratto** | Relazione commerciale duratura con un BA per una utility. Stato DRAFT → ATTIVO → CESSATO |
| **Forma derivata** | "Con listino" / "Senza listino" — derivata dai dati, non scelta dall'operatore |
| **OVERRIDE** | Eccezione di riga: prezzo personalizzato per articolo del listino. Variazione globale non si applica |
| **ESCLUSIONE** | Eccezione di riga: articolo del listino non disponibile per il cliente |
| **AGGIUNTA** | Eccezione di riga: articolo fuori listino aggiunto al contratto |
| **Versione listino fissata** | `listino_versione_id` snapshot all'attivazione. Il contratto legge sempre quella versione |
| **Drift listino** | In DRAFT, se esce una nuova versione del listino mentre si lavorano le eccezioni, il banner UI avverte |
| **Lock post-attivazione** | Da ATTIVO in poi, testata e righe sono immutabili — trigger DB enforced |
| **Negoziato puro** | Contratto senza listino: tutte le righe sono AGGIUNTA, nessun listino di riferimento |
| **STADIO 1** | Posizione del contratto nella cascata del resolver pricing v5 (dopo promo, prima di categoria) |
| **L1/L2/L3** | Livelli di autorizzazione pricing: Permesso / Soglia / Workflow approvazione |

---

## Nota — Il collegamento mancante: offerta commerciale → contratto

Il ciclo di vita attuale del contratto ha un **inizio non tracciato**: il contratto
nasce direttamente dall'operatore in DRAFT, senza un documento precedente che
formalizzi la proposta di condizioni al cliente.

Questa asimmetria è intenzionale e consapevole: il refactor contratti corrente
ha preparato il modello per riceverla in futuro senza richiedere modifiche strutturali.
Il collegamento mancante è l'**offerta commerciale** — una proposta di condizioni
quadro (listino + variazione + eccezioni proposte) distinta dal preventivo (che è
invece una proposta di transazione puntuale).

Il parallelo nel modello:

| Proposta | Accettazione genera | Tipo di fornitura |
|---|---|---|
| **Preventivo** (`PRV-*`) | Commessa → fattura | Transazione puntuale |
| **Offerta commerciale** (`OFC-*`, non ancora esistente) | Contratto in DRAFT → attivazione | Relazione ricorrente duratura |

Perché i due documenti esisterebbero separati e non si userebbe il preventivo
come proposta di contratto? Il preventivo è una fotografia riga-per-riga a un
dato istante (snapshot materializzato, articoli + quantità + prezzi specifici).
L'offerta commerciale è una proposta di **condizioni quadro** (listino + variazione +
delta), e il suo "snapshot" è la versione del listino — la stessa struttura già
implementata per il contratto in §3-bis-A. La simmetria del modello implica che
i due artefatti abbiano snapshot strutturalmente diversi, e usare il preventivo
come offerta commerciale sarebbe una forzatura semantica.

L'analisi di dettaglio (tre opzioni, decisioni da prendere, modello dati proposto)
è in [`Analisi-iniziale-offerta-commerciale.md`](/dev/work-in-progress/Analisi-iniziale-offerta-commerciale).
La decisione di procedere con l'opzione (c) — entità separata `offerte_commerciali`
con flusso `push_a_contratto` — è raccomandata nel documento ma non ancora presa
operativamente. Non è bloccante per il refactor contratti corrente né per il backend
che segue.

*Per il dettaglio tecnico delle API REST, formati payload e codici errore vedi
[API Contratti](/backend/vendite/manual/api_contratti). Per le decisioni di modello
del refactor vedi
[refactor-contratti-modalita](/dev/work-done/refactor-contratti-modalita).*
