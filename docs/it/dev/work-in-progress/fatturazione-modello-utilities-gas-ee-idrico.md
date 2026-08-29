# Modello Fatturazione Utilities (Gas, Energia Elettrica, Idrico)

## 1) Scopo

Definire il modello architetturale per la fatturazione delle utilities (gas, energia elettrica,
idrico) all'interno della pipeline commessa → attivita fatturabili → fatturazione.

Il processo di fatturazione utilities e radicalmente diverso dai documenti commerciali
(preventivi, ordini): un singolo consumo genera N componenti fatturabili (consumo per fascia,
canoni fissi, oneri di sistema, accise, trasporto, ecc.).
Questo documento descrive come gestire questa complessita senza rompere il modello unificato.

Riferimenti correlati:

- `docs/it/dev/work-done/gestione-commesse-v2.md`
- `docs/it/dev/work-in-progress/sviluppo-listini.md`
- `docs/it/dev/work-done/pipeline-domini-engine.md`

---

## 2) Contesto: differenza sorgenti commerciali vs utilities

### 2.1 Sorgenti commerciali (preventivi, ordini)

Mapping diretto e deterministico:

- 1 riga documento → 1 `commesse_attivita` → 1 `attivita_fatturabili`
- `articolo_id`, `prezzo`, `quantita` arrivano dalla riga sorgente
- L'handler e un semplice "pipe" che passa dati

### 2.2 Sorgenti utilities (gas, energia, idrico)

Mapping a fan-out:

- 1 consumo → **N componenti fatturabili**:
  - Consumo per fascia oraria (energia: F1, F2, F3; gas: monofascia; idrico: monofascia/scaglioni)
  - Canone fisso contatore
  - Oneri di sistema
  - Dispacciamento (energia)
  - Accise e addizionali
  - Trasporto e distribuzione
  - Eventuali crediti (bonus sociale)
- Ogni componente ha il proprio `articolo_id`, UoM, quantita, prezzo
- Si applicano suddivisioni temporali per fasce listini
- I prezzi vengono sempre da listino (`fn_resolve_prezzo_listino`)
- L'handler contiene la logica di calcolo (utility-specific)

---

## 3) Vincolo architetturale: la commessa e obbligatoria

Dalla struttura di `vendite.attivita_fatturabili`:

- `commessa_id`: **NOT NULL** (FK)
- `commessa_attivita_id`: **NOT NULL** (FK + UNIQUE `uq_attivita_fatturabili_commessa_attivita`)

Questo vincolo impone che:

1. OGNI riga `attivita_fatturabili` DEVE avere esattamente una riga `commesse_attivita` (1:1)
2. OGNI riga `attivita_fatturabili` DEVE appartenere a una `commessa`
3. Non e possibile inserire direttamente su `attivita_fatturabili` senza passare dalla commessa

Questo vincolo e un **asset architetturale**, non un limite:

- La commessa diventa il **dossier fatturazione** per un BA + utility + periodo
- I componenti calcolati sono **revisionabili e approvabili** prima della fatturazione
- Il ricalcolo e **idempotente** grazie al vincolo `(commessa_id, segment_key)` su `commesse_attivita`
- Tutte le sorgenti **convergono in un unico punto auditabile**

---

## 4) Flusso operativo

```
[Input grezzi: letture contatore, import CSV/API, inserimento manuale]
    |
    v
vendite.attivita_consumi
    (dossier consumo: BA, periodo, totale, meta con dettagli)
    (stato_calcolo: OK | WARNING | ERRORE)
    |
    v
vendite.fn_list_consumi_da_pushare(...)
    (identifica consumi con stato_calcolo = OK, non ancora emessi)
    (output: 1 riga per consumo, articolo_id = NULL, valuta_id = NULL)
    |
    v
Handler Python (utility-specific via implementation_key)
    |-- gas_v1: monofascia, accise gas, oneri trasporto
    |-- energia_v1: fasce F1/F2/F3, dispacciamento, accise EE
    |-- idrico_v1: monofascia/scaglioni, canoni acquedotto/depurazione
    |
    | Per ogni consumo:
    |   1. Legge dossier (attivita_consumi + meta)
    |   2. Risolve articoli per componente (da config mapping)
    |   3. Per ogni componente:
    |      - Calcola quantita (da meta/fasce/scaglioni)
    |      - Risolve prezzo (fn_resolve_prezzo_listino)
    |   4. Chiama fn_get_or_create_commessa (1 volta, AUTO)
    |   5. Chiama fn_upsert_commessa_attivita x N (1 per componente)
    |   6. Registra ROOT in commesse_sorgenti
    v
vendite.commesse (AUTO, per BA + utility + periodo)
    |
vendite.commesse_attivita (N righe, 1 per componente fatturabile)
    |
    v
vendite.fn_emit_attivita_fatturabili_da_commessa(...)
    (standard, invariato — emette N righe AF)
    |
    v
vendite.attivita_fatturabili (N righe, ognuna con attivita_consumi_id)
    |
    v
Pipeline fatturazione (standard, invariata)
    |
    v
vendite.fatture_righe
```

---

## 5) Pattern segment_key per consumi

La chiave di idempotenza segue il pattern `CONS:<consumo_uid>:COMP:<codice_componente>`:

```
'CONS:a1b2c3d4-...:COMP:ENERGIA_F1'
'CONS:a1b2c3d4-...:COMP:ENERGIA_F2'
'CONS:a1b2c3d4-...:COMP:ENERGIA_F3'
'CONS:a1b2c3d4-...:COMP:CANONE_FISSO'
'CONS:a1b2c3d4-...:COMP:ONERI_SISTEMA'
'CONS:a1b2c3d4-...:COMP:DISPACCIAMENTO'
'CONS:a1b2c3d4-...:COMP:ACCISE'
'CONS:a1b2c3d4-...:COMP:ADDIZIONALI'
'CONS:a1b2c3d4-...:COMP:TRASPORTO'
'CONS:a1b2c3d4-...:COMP:BONUS_SOCIALE'
```

Il vincolo `uq_commesse_attivita_commessa_segment` su `(commessa_id, segment_key)` garantisce che
un ricalcolo con gli stessi segment_key aggiorni (UPSERT) anziche duplicare.

### Confronto pattern per sorgente

| Sorgente | Pattern segment_key | Cardinalita |
|----------|-------------------|-------------|
| Preventivi | `PREV:<uid>:R:<riga_id>` | 1 riga → 1 CA |
| Ordini | `ORD:<uid>:R:<riga_id>` | 1 riga → 1 CA |
| Consumi | `CONS:<uid>:COMP:<componente>` | 1 consumo → N CA |

---

## 6) Tracciabilita

### 6.1 Da attivita_fatturabili al consumo sorgente

`attivita_fatturabili.attivita_consumi_id` (FK nullable, gia esistente) collega ogni AF
alla testata consumo sorgente. Permette query dirette:

```sql
SELECT af.*
FROM vendite.attivita_fatturabili af
WHERE af.attivita_consumi_id = :consumo_id;
```

### 6.2 Da commessa alla sorgente

`commesse_sorgenti` con `ruolo_link = 'ROOT'` e `sorgente_tipo_id = ATTIVITA_CONSUMI (12)`
collega la commessa AUTO al consumo sorgente.

### 6.3 Segment_key come audit trail

Il `segment_key` su `commesse_attivita` contiene sia il riferimento al consumo (`CONS:<uid>`)
che il codice componente (`COMP:<codice>`). Questo rende ogni riga auto-documentante e
tracciabile anche senza join.

---

## 7) Ruolo di `attivita_consumi`

### 7.1 Stato attuale: bozza di testata

La tabella `vendite.attivita_consumi` e attualmente una **bozza di testata** per il calcolo
consumi. E stata creata come placeholder per il modello e contiene solo i campi minimi:

| Campo | Scopo |
|-------|-------|
| `billing_account_id` | Identificazione BA |
| `competenza_mese` | Periodo di riferimento |
| `periodo_dal` / `periodo_al` | Range temporale consumo |
| `consumo_totale` | Dato grezzo aggregato |
| `uom_id` | Unita di misura del consumo totale |
| `stato_calcolo` | Stato processo (OK, WARNING, ERRORE) |
| `meta` | JSONB per dettagli aggiuntivi |

**La tabella va approfondita e completata.** La struttura attuale e sufficiente come trigger
per il flusso (`fn_list_consumi_da_pushare`) ma non modella adeguatamente la complessita
del calcolo consumi utilities.

### 7.2 Evoluzione prevista

Punti aperti da analizzare:

1. **Dettaglio letture**: servono campi/tabelle per letture contatore (inizio, fine, stimate vs reali)?
2. **Dettaglio fasce**: suddivisione per fasce orarie (F1/F2/F3) va nel `meta` JSONB
   o in una tabella di dettaglio `attivita_consumi_fasce`?
3. **Potenza impegnata**: per energia elettrica, la potenza contrattuale va su `attivita_consumi`
   o su `istanze_utilities`?
4. **Tipo contatore/fornitura**: monofase/trifase, uso domestico/non domestico —
   vanno su `attivita_consumi` o ereditati da configurazione?
5. **Storicizzazione calcoli**: in caso di ricalcolo, serve traccia della versione
   precedente oltre allo storico generico?
6. **Relazione con contratti fornitura**: `attivita_consumi` fa riferimento al contratto
   attivo nel periodo o si limita alla fornitura (istanza_utility)?

### 7.3 Approccio per v1

Per la v1, `attivita_consumi.meta` (JSONB) puo contenere i dettagli non ancora strutturati:

```json
{
  "letture": {"inizio": 12345, "fine": 12500, "tipo": "REALE"},
  "fasce": {"F1": 80, "F2": 50, "F3": 25},
  "potenza_impegnata": 3.0,
  "tipo_contatore": "MONOFASE",
  "fonte_dati": "IMPORT_CSV"
}
```

L'handler Python legge da `meta` e genera i componenti. Questo approccio permette di
validare il flusso end-to-end senza bloccarsi sulla modellazione definitiva della tabella.
La strutturazione in tabelle dedicate potra avvenire una volta stabilizzato il modello.

---

## 8) Handler utility-specific

### 8.1 Architettura handler

L'handler vive in `backend/apps/vendite/services/` e viene dispatchato via
`implementation_key` dalla tabella `dbops.pipeline_task_registry_impl`.

Ogni handler e specializzato per tipo utility:

| implementation_key | Utility | Componenti tipiche |
|-------------------|---------|--------------------|
| `gas_v1` | Gas naturale | consumo (monofascia), accise gas, addizionali regionali, trasporto, stoccaggio, canone contatore |
| `energia_v1` | Energia elettrica | consumo F1/F2/F3, dispacciamento, oneri di sistema, accise EE, addizionali, trasporto/distribuzione, canone potenza |
| `idrico_v1` | Idrico | consumo (monofascia o scaglioni), canone fognatura, canone depurazione, quota fissa acquedotto |

### 8.2 Responsabilita dell'handler

Per ogni consumo ricevuto da `fn_list_consumi_da_pushare`:

1. **Lettura dossier**: legge `attivita_consumi` + `meta` JSONB
2. **Risoluzione componenti**: legge configurazione componenti per tipo utility
   (da tabella config mapping: utility_type → componente → articolo_id + UoM)
3. **Calcolo quantita**: per ogni componente, calcola la quantita basandosi su
   meta (fasce, letture, potenza, scaglioni)
4. **Risoluzione prezzo**: chiama `fn_resolve_prezzo_listino` per ogni componente
   (il resolver gestisce gia il fallback multi-dimensionale)
5. **Creazione commessa**: chiama `fn_get_or_create_commessa` (AUTO, 1 volta per consumo)
6. **Upsert attivita**: chiama `fn_upsert_commessa_attivita` N volte,
   una per componente, con segment_key = `'CONS:<uid>:COMP:<codice>'`
7. **Link sorgente**: registra ROOT in `commesse_sorgenti`
8. **Emissione**: chiama `fn_emit_attivita_fatturabili_da_commessa`

### 8.3 Configurazione componenti

Serve una tabella di configurazione (da progettare) che mappi:

- tipo utility (gas, energia, idrico)
- codice componente (ENERGIA_F1, CANONE_FISSO, ACCISE, ...)
- articolo_id (quale articolo di `catalogo.articoli` rappresenta quel componente)
- UoM associata
- opzionale: regole di calcolo quantita (formula, scaglione)
- opzionale: obbligatorieta (componente sempre presente vs condizionale)

Possibile collocazione: `config.utility_componenti` (nuova) oppure estensione del
catalogo articoli con metadati utility-aware.

---

## 9) Confronto sorgenti commerciali vs utilities

| Aspetto | Preventivi/Ordini | Consumi (Utilities) |
|---------|------------------|---------------------|
| **Mapping** | 1 riga → 1 CA → 1 AF | 1 consumo → N CA → N AF |
| **articolo_id** | Dalla riga sorgente | Risolto dall'handler (da config mapping) |
| **prezzo** | Dalla riga sorgente o listino | Sempre da listino (ricalcolabile) |
| **valuta_id** | Dal documento sorgente | Risolta dall'handler (da config) |
| **segment_key** | `PREV/ORD:<uid>:R:<id>` | `CONS:<uid>:COMP:<componente>` |
| **Complessita handler** | Minima (pipe dati) | Alta (calcolo componenti, fasce, tasse) |
| **implementation_key** | `default` | `gas_v1`, `energia_v1`, `idrico_v1` |
| **fn_list output** | N righe (1 per riga doc) | 1 riga per consumo (fan-out nell'handler) |
| **prezzo_bloccato** | Dipende da sorgente | FALSE (sempre ricalcolabile da listino) |

### Cosa resta invariato

Tutta l'infrastruttura a valle dell'handler e identica per commerciali e utilities:

- `fn_get_or_create_commessa`: stessa funzione, stessi parametri
- `fn_upsert_commessa_attivita`: stessa funzione, chiamata N volte con segment_key diversi
- `fn_emit_attivita_fatturabili_da_commessa`: stessa funzione
- Pipeline fatturazione (lotti, documenti fiscali): completamente invariata

---

## 10) Best practices

### 10.1 Idempotenza end-to-end

- Il segment_key DEVE essere deterministico: dato lo stesso consumo e lo stesso componente,
  il segment_key prodotto deve essere identico. Questo garantisce che un ricalcolo
  aggiorni (UPSERT) senza duplicare.
- Non usare MAI valori generati a runtime (random, timestamp) nel segment_key.
- Il pattern `CONS:<uid>:COMP:<codice_componente>` usa l'uid del consumo (stabile)
  e il codice componente (stabile da configurazione).

### 10.2 Separazione responsabilita

- `fn_list_consumi_da_pushare`: SOLO selezione/filtro. Non fa calcoli, non risolve prezzi,
  non esplode componenti. Restituisce 1 riga per consumo.
- Handler Python: TUTTA la logica di calcolo. Fan-out 1→N, risoluzione articoli, prezzi,
  quantita per componente.
- Funzioni DB (`fn_upsert_commessa_attivita`, `fn_emit`): SOLO persistenza e workflow.
  Non conoscono la semantica dei componenti utilities.

### 10.3 Atomicita del calcolo

- Un consumo viene processato in una singola transazione DB.
- Se il calcolo di un componente fallisce, TUTTI i componenti di quel consumo vengono rollbackati.
- Non lasciare mai un consumo parzialmente calcolato (3 componenti su 7).
- L'handler deve gestire il calcolo di tutti i componenti in un blocco atomico.

### 10.4 Prezzi da listino, mai hardcoded

- I prezzi vengono SEMPRE da `fn_resolve_prezzo_listino`.
- Nessun prezzo hardcoded nell'handler o nella configurazione componenti.
- La configurazione componenti mappa utility_type → articolo_id. Il prezzo e risolto
  dal listino associato al BA/utility/emittente.
- `prezzo_bloccato = FALSE` su `commesse_attivita`: il prezzo e ricalcolabile
  da listino a ogni riesecuzione.

### 10.5 Configurabilita componenti

- L'elenco dei componenti per utility type DEVE venire da una tabella di configurazione DB,
  non hardcoded nel codice Python.
- L'aggiunta di un nuovo componente (es. "contributo CSEA" per energia) deve richiedere solo:
  un INSERT nella tabella config + un articolo nel catalogo + un prezzo nel listino.
- L'handler legge la configurazione e itera: nessun `if` nel codice per ogni componente specifico.

### 10.6 Tracciabilita completa

- Ogni riga `attivita_fatturabili` generata da un consumo DEVE avere `attivita_consumi_id`
  valorizzato (FK al dossier sorgente).
- Il `segment_key` su `commesse_attivita` DEVE contenere sia il riferimento al consumo
  che il codice componente, rendendo ogni riga auto-documentante.
- Il `meta` JSONB su `commesse_attivita` DEVE contenere i parametri di calcolo usati
  (fascia, percentuale, scaglione applicato) per audit e debug.

### 10.7 Gestione errori e stati

- `attivita_consumi.stato_calcolo`:
  - `OK`: consumo pronto per push — l'handler lo processa.
  - `WARNING`: calcolato con anomalie — l'handler lo processa ma segnala.
  - `ERRORE`: calcolo fallito — `fn_list_consumi_da_pushare` lo esclude.
- Se l'handler fallisce durante il calcolo di un consumo, il consumo rimane nello stato
  precedente (nessuna commessa parziale grazie all'atomicita).
- Non catturare eccezioni generiche nell'handler. Usare `ServiceError` con codici
  specifici (`E_CONSUMI_COMPONENTE_MANCANTE`, `E_CONSUMI_PREZZO_NON_TROVATO`, ecc.).

### 10.8 Implementation_key e estendibilita

- Ogni tipo utility ha il proprio `implementation_key` nel registry task
  (`gas_v1`, `energia_v1`, `idrico_v1`).
- Non mischiare logiche di utility diverse nello stesso handler.
- L'evoluzione di un handler (es. `energia_v2` con scaglioni progressivi) si ottiene
  registrando una nuova implementation, non modificando la v1.
- Il dispatch avviene via `dbops.pipeline_task_registry_impl`, non con `if/elif` nel codice.

### 10.9 Ricalcolo e rettifiche

- Il ricalcolo di un consumo si ottiene rieseguendo l'handler sullo stesso consumo:
  i segment_key idempotenti producono UPSERT su `commesse_attivita`.
- Per rettifiche post-fatturazione, usare il meccanismo delta gia previsto in
  [sviluppo-rettifiche.md](sviluppo-rettifiche.md). Non creare percorsi paralleli.
  > 🔴 **Riferimento corretto il 2026-08-18**: puntava a `sviluppo-listini.md`,
  > che **non esiste piu'** — la specifica e' stata versionata in v1..v6 e il
  > perimetro rettifiche estratto in `sviluppo-rettifiche.md`. La frase «non
  > creare percorsi paralleli» puntava al vuoto.
  >
  > ⚠️ E vale la nota in testa a quel documento: il **come** e' superato. La
  > correzione di **merce** (reso gia' fatturato) non passa di li' — ha il suo
  > modello in [brief-design-note-credito-resi.md](../work-done/brief-design-note-credito-resi.md).
- Un ricalcolo NON modifica righe con `stato_emissione = 'EMESSA'` e `fatturato = TRUE`
  (guard in `fn_upsert_commessa_attivita` e `fn_emit`).

### 10.10 Test e validazione

- Ogni handler deve avere test pgTAP che verifichino:
  - Il numero corretto di componenti generati per un consumo tipo.
  - L'idempotenza: rieseguire lo stesso consumo non produce duplicati.
  - La coerenza prezzi: il prezzo su CA corrisponde a quello restituito da `fn_resolve_prezzo_listino`.
  - L'atomicita: un errore su un componente rollbacka tutti i componenti del consumo.
- Test di integrazione end-to-end: dal consumo alla riga fattura.

---

## 11) Cosa NON fare

### 11.1 NON bypassare la commessa

Mai scrivere direttamente su `attivita_fatturabili` senza passare per `commesse` e
`commesse_attivita`. Il vincolo NOT NULL + UNIQUE su `commessa_attivita_id` lo impedisce
a livello di schema, ma anche concettualmente: la commessa e il punto di convergenza,
audit e approvazione. Non creare percorsi alternativi.

### 11.2 NON rendere commessa_attivita_id nullable

Rendere nullable `commessa_attivita_id` per supportare il bypass sarebbe un errore
architetturale: si perderebbe idempotenza, workflow approvazione, audit trail unificato
e la pipeline diventerebbe biforcata con due percorsi da manutenere.

### 11.3 NON hardcodare componenti nell'handler

L'handler NON deve contenere un elenco hardcoded di componenti (es. `["ENERGIA_F1", "CANONE", ...]`).
I componenti vengono dalla configurazione DB. L'handler itera sulla configurazione.
Altrimenti aggiungere un componente richiede un deploy applicativo.

### 11.4 NON hardcodare prezzi o tariffe

I prezzi vengono SEMPRE dal listino via `fn_resolve_prezzo_listino`.
Le tariffe regolamentate (accise, oneri ARERA) vengono da listini versionati con
`valido_dal/valido_al`, non da costanti nel codice.

### 11.5 NON mischiare logiche utility diverse nello stesso handler

Un handler `energia_v1` non deve contenere logica gas o idrico.
Ogni utility ha le proprie regole (fasce, scaglioni, tassazione). Mischiarle
produce codice fragile e non testabile.

### 11.6 NON fare fan-out nella fn_list

`fn_list_consumi_da_pushare` restituisce 1 riga per consumo, non N righe per componente.
Il fan-out 1→N e responsabilita dell'handler Python. La fn_list e solo il trigger
che identifica i consumi pronti. Se il fan-out va nel DB in futuro, sara una funzione
dedicata (`fn_expand_consumo_componenti`), non una modifica alla fn_list.

### 11.7 NON lasciare consumi parzialmente calcolati

Se il calcolo di un componente fallisce, TUTTI i componenti di quel consumo vanno in
rollback. Non lasciare mai 4 commesse_attivita su 7 previste per un singolo consumo.
Usare transazioni atomiche.

### 11.8 NON calcolare prezzi nell'handler senza listino

L'handler NON deve calcolare prezzi internamente (es. `quantita * tariffa_fissa`).
Ogni prezzo deve transitare per `fn_resolve_prezzo_listino` in modo che:
- sia auditabile (quale listino, versione, riga ha prodotto il prezzo),
- sia riallineabile (ricalcolo periodico),
- rispetti il fallback multi-dimensionale (BA, utility, emittente, articolo, UoM).

### 11.9 NON duplicare il modello commessa per utilities

Non creare tabelle parallele (`commesse_utilities`, `attivita_fatturabili_consumi`, ecc.).
Il modello commessa e gia progettato per gestire qualsiasi sorgente.
Le utilities usano commessa AUTO con handler specifici — nessuna struttura dedicata.

### 11.10 NON ignorare la storicizzazione

Le righe `commesse_attivita` hanno `storicizza = TRUE` e trigger `trgfn_storico_generic`.
Ogni UPSERT (ricalcolo) produce automaticamente una traccia storica.
Non disabilitare la storicizzazione per "velocizzare" il ricalcolo.

---

## 12) Open items per v1

### 12.1 Tabella config mapping componenti

Da progettare: `config.utility_componenti` (o equivalente) che mappi
`utility_type → codice_componente → articolo_id + UoM + obbligatorieta + ordinamento`.
Senza questa tabella l'handler non puo essere configurabile.

### 12.2 Completamento `attivita_consumi`

La tabella attuale e solo una bozza di testata. Da approfondire:

1. Campi mancanti (candidati): `istanza_utility_id`, `contratto_id`, `tipo_fornitura`,
   `potenza_contrattuale`
2. Dettaglio letture: tabella figlio o campi/JSONB?
3. Dettaglio fasce: tabella figlio o JSONB?
4. Relazione con contratto attivo nel periodo
5. Gestione ricalcolo (versioning del calcolo)

Per v1, il JSONB `meta` copre i dettagli non ancora strutturati.
La strutturazione in tabelle dedicate avverra dopo stabilizzazione del flusso end-to-end.

### 12.3 Seed registry

Inserire `implementation_key` in `dbops.pipeline_task_registry_impl`:
- `gas_v1`
- `energia_v1`
- `idrico_v1`

### 12.4 Handler Python

Da implementare in `backend/apps/vendite/services/`:
- Handler base con logica comune (lettura dossier, creazione commessa, loop componenti)
- Handler specializzati per utility type (calcolo quantita per fascia/scaglione)

### 12.5 Test pgTAP

Test DB per validare:
- Idempotenza segment_key
- Coerenza N componenti generati
- Guard su ricalcolo post-emissione
- Atomicita transazionale

---

## 13) Ipotesi struttura calcoli: step con dipendenze (sync/async)

### 13.1 Problema

Il calcolo componenti per un singolo consumo non e un'operazione piatta.
Alcuni passi sono **sequenziali** (il risultato alimenta i passi successivi),
altri sono **indipendenti** e possono essere eseguiti in parallelo.

Esempio per energia elettrica:

```
SYNC ─── Lettura consumo + dati contatore/fornitura
  │
  ↓
SYNC ─── Distribuzione fasce temporali (F1/F2/F3)
  │       (serve il consumo totale + profilo orario)
  │
  ↓ risultato: quantita per fascia
  │
  ├──→ ASYNC ─── Calcolo valore consumi per fascia (prezzo × qta per F1,F2,F3)
  │
  ├──→ ASYNC ─── Calcolo imposte/accise (scaglioni su quantita per fascia)
  │
  ├──→ ASYNC ─── Quote fisse (canone contatore, quota potenza)
  │
  └──→ ASYNC ─── Oneri sistema, trasporto, dispacciamento
         │
         ↓
SYNC ─── Aggregazione componenti → N chiamate fn_upsert_commessa_attivita
```

I passi ASYNC non dipendono l'uno dall'altro ma tutti dipendono dalla
distribuzione fasce (il passaggio SYNC a monte).

### 13.2 Struttura per utility type

Ogni utility ha i propri step con le proprie dipendenze.
La struttura e diversa per tipo, non un modello unico forzato:

**Energia elettrica:**

| Step | Dipende da | Sync/Async | Descrizione |
|------|-----------|------------|-------------|
| `lettura_consumo` | — | sync | Lettura dossier + dati contatore |
| `distribuzione_fasce` | `lettura_consumo` | sync | Ripartizione F1/F2/F3 da profilo orario |
| `valore_consumi` | `distribuzione_fasce` | async | Prezzo × quantita per fascia |
| `imposte_accise` | `distribuzione_fasce` | async | Accise EE a scaglioni su quantita |
| `quote_fisse` | `lettura_consumo` | async | Canone contatore, quota potenza impegnata |
| `oneri_sistema` | `distribuzione_fasce` | async | Oneri ARERA, dispacciamento |
| `trasporto` | `distribuzione_fasce` | async | Trasporto e distribuzione |

**Gas naturale:**

| Step | Dipende da | Sync/Async | Descrizione |
|------|-----------|------------|-------------|
| `lettura_consumo` | — | sync | Lettura dossier + dati fornitura |
| `calcolo_scaglioni` | `lettura_consumo` | sync | Ripartizione consumo annuo su scaglioni normativi |
| `valore_consumi` | `calcolo_scaglioni` | async | Prezzo × quantita per scaglione |
| `imposte_accise` | `calcolo_scaglioni` | async | Accise gas a scaglioni annui |
| `addizionali_regionali` | `calcolo_scaglioni` | async | Addizionali regionali |
| `quote_fisse` | `lettura_consumo` | async | Canone contatore, quota fissa |
| `oneri_sistema` | `calcolo_scaglioni` | async | Oneri QVD, stoccaggio |
| `trasporto` | `calcolo_scaglioni` | async | Trasporto e distribuzione |

**Idrico:**

| Step | Dipende da | Sync/Async | Descrizione |
|------|-----------|------------|-------------|
| `lettura_consumo` | — | sync | Lettura dossier + dati fornitura |
| `calcolo_scaglioni` | `lettura_consumo` | sync | Ripartizione consumo su scaglioni tariffari |
| `valore_consumi` | `calcolo_scaglioni` | async | Prezzo × quantita per scaglione |
| `quota_fissa_acquedotto` | `lettura_consumo` | async | Quota fissa acquedotto |
| `canone_fognatura` | `calcolo_scaglioni` | async | Canone fognatura (su consumo) |
| `canone_depurazione` | `calcolo_scaglioni` | async | Canone depurazione (su consumo) |

### 13.3 Pattern handler con step dichiarativi

Ogni handler dichiara i propri step. L'esecutore li orchestra rispettando le dipendenze:

```python
class EnergiaV1Handler:
    """Ogni step produce una lista di ComponenteCalcolato."""

    steps = [
        # (step_id,               dipendenze,                modo)
        ("lettura_consumo",       [],                         "sync"),
        ("distribuzione_fasce",   ["lettura_consumo"],        "sync"),
        ("valore_consumi",        ["distribuzione_fasce"],    "async"),
        ("imposte_accise",        ["distribuzione_fasce"],    "async"),
        ("quote_fisse",           ["lettura_consumo"],        "async"),
        ("oneri_sistema",         ["distribuzione_fasce"],    "async"),
        ("trasporto",             ["distribuzione_fasce"],    "async"),
    ]


class GasV1Handler:

    steps = [
        ("lettura_consumo",       [],                         "sync"),
        ("calcolo_scaglioni",     ["lettura_consumo"],        "sync"),
        ("valore_consumi",        ["calcolo_scaglioni"],      "async"),
        ("imposte_accise",        ["calcolo_scaglioni"],      "async"),
        ("addizionali_regionali", ["calcolo_scaglioni"],      "async"),
        ("quote_fisse",           ["lettura_consumo"],        "async"),
        ("oneri_sistema",         ["calcolo_scaglioni"],      "async"),
        ("trasporto",             ["calcolo_scaglioni"],      "async"),
    ]
```

### 13.4 Esecutore step

L'esecutore e unico per tutti gli handler. Non conosce la semantica dei componenti:

1. Ordina gli step per dipendenze (topological sort)
2. Esegue gli step sync in sequenza
3. Quando incontra step async senza dipendenze pendenti, li lancia in parallelo
   (`concurrent.futures.ThreadPoolExecutor` o equivalente)
4. Attende il completamento di tutti gli step
5. Raccoglie i componenti prodotti da ogni step
6. Persiste in blocco atomico (transazione unica per consumo):
   - `fn_get_or_create_commessa` (1 volta)
   - `fn_upsert_commessa_attivita` (N volte, 1 per componente)
   - Registrazione ROOT in `commesse_sorgenti`

### 13.5 Strategia v1 → v2

**v1**: tutti gli step vengono eseguiti in sequenza, anche quelli dichiarati `async`.
La struttura a step e identica, ma l'esecutore ignora il flag `async` e procede
sequenzialmente. Questo permette di validare il modello senza complessita di concorrenza.

**v2**: l'esecutore abilita l'esecuzione parallela per gli step `async`.
Nessuna modifica agli handler — solo l'esecutore cambia comportamento.

### 13.6 Vantaggi

1. **Modularita**: ogni step e una funzione testabile in isolamento.
2. **Estendibilita**: aggiungere un componente = aggiungere uno step + config DB.
   Nessun `if/elif` nel codice.
3. **Riusabilita**: step comuni (es. `lettura_consumo`) possono essere condivisi
   tra handler diversi tramite ereditarieta o composizione.
4. **Performance futura**: il parallelismo e opt-in, dichiarato nello step.
   Il passaggio da sequenziale a parallelo non richiede refactor.
5. **Testabilita**: si testa ogni step indipendentemente, poi l'integrazione.

---

*Documento WIP — aggiornare man mano che il modello si consolida.*
