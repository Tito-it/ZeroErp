# Guida – Gestione Listini Prezzo

> (latest review 05-04-26)
>
> Destinatari: sviluppatori database, backend e analisti funzionali
>
> Vedi anche
>
> * [Analisi e decisioni operative listini](/dev/work-in-progress/gestione-listini) — decisioni architetturali, roadmap DB, integrazione commessa
> * [vendite.listini](/dbzero/vendite/tabelle/listini)
> * [vendite.listini_versioni](/dbzero/vendite/tabelle/listini_versioni)
> * [vendite.listini_righe](/dbzero/vendite/tabelle/listini_righe)
> * [vendite.listini_associazioni](/dbzero/vendite/tabelle/listini_associazioni)
> * [vendite.fn_resolve_prezzo_listino](/dbzero/vendite/funzioni/fn_resolve_prezzo_listino)
> * [API REST Listini](/backend/vendite/manual/api_listini)
> * [Guida Fatturazione](/guide/fatturazione) — pipeline fatturazione a lotti
> * [Guida Gestione Commesse](/guide/gestione-commesse) — integrazione prezzo in commessa

---

## Introduzione

In Zero ERP il **listino** non e un semplice elenco prezzi: e un sistema multi-livello che risponde alla domanda *"quanto costa questo articolo, per questo contesto, in questa data?"* tenendo conto di chi compra, quale utility eroga il servizio e chi emette la fattura.

Questa guida spiega **come funziona il sistema listini** — quali entita lo compongono, come si relazionano, come il resolver determina il prezzo e quali regole governano il processo. La logica e la stessa sia per il dominio utility (gas, energia, idrico) sia per il dominio commercio (servizi, manifatturiero).

**Cosa troverai in questa guida:**

* Le entita coinvolte e il loro ruolo nel processo
* Il ciclo di vita di un listino (dalla creazione alla chiusura)
* Come funziona la risoluzione deterministica del prezzo (7 livelli di precedenza)
* Le regole di tie-break quando piu listini concorrono
* L'integrazione con commesse e fatturazione
* Le garanzie di coerenza offerte dal database

### Il modello e generico, non solo per le utility

La struttura listini funziona per qualsiasi tipo di azienda. Il campo `dominio` sul listino (`UTILITY` o `COMMERCIO`) classifica il perimetro, ma l'architettura sottostante — versioni, righe, associazioni, resolver — e identica in entrambi i casi.

In pratica:

* **Azienda utility**: listini con dimensioni BA + utility + emittente, prezzi ad alta precisione per consumi minimi
* **Azienda non-utility**: listini con dimensioni BA (o senza contesto), pricing standard per servizi/prodotti

---

## Tabelle coinvolte

* [vendite.listini](/dbzero/vendite/tabelle/listini) — la testata anagrafica del listino
* [vendite.listini_versioni](/dbzero/vendite/tabelle/listini_versioni) — il versionamento temporale
* [vendite.listini_righe](/dbzero/vendite/tabelle/listini_righe) — i prezzi elementari per articolo/UoM
* [vendite.listini_associazioni](/dbzero/vendite/tabelle/listini_associazioni) — chi puo usare questo listino
* [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — gli articoli a catalogo
* [catalogo.unita_misura](/dbzero/catalogo/tabelle/unita_misura) — le unita di misura
* [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — l'account di fatturazione
* [config.utilities](/dbzero/config/tabelle/utilities) — il tipo di servizio

---

## Le entita e il loro significato

### Listino (testata)

E il contenitore principale. Identifica un listino con un codice univoco, una descrizione e un dominio (`UTILITY` o `COMMERCIO`). Non contiene ne date ne prezzi: questi sono delegati alle entita figlie.

Il listino e pensato come entita stabile nel tempo. Quello che cambia sono le sue versioni e le sue righe prezzo.

### Versione

E la finestra temporale in cui un listino e valido. Ogni versione ha:

* un intervallo di validita (`valido_dal`, `valido_al`)
* uno stato che governa il ciclo di vita (`BOZZA` → `ATTIVA` → `CHIUSA`)
* una priorita per il tie-break tra versioni dello stesso listino

Le versioni attive dello stesso listino **non possono sovrapporsi** temporalmente (vincolo esclusione `ex_listini_versioni_no_overlap`).

### Riga prezzo

E il prezzo vero e proprio. Ogni riga e legata a una versione e specifica:

* **articolo + UoM** (obbligatori) — cosa si sta prezzando e in quale unita
* **dimensioni di contesto** (opzionali) — BA, utility, emittente: per chi vale questo prezzo

La combinazione dimensionale determina la **specificita** della riga: piu dimensioni sono valorizzate, piu il prezzo e specifico per quel contesto.

Precisione: `numeric(22,10)` per preservare importi unitari molto piccoli (tipici del dominio utility). L'arrotondamento a 6 decimali avviene solo nel layer `fatture_righe`.

### Associazione

E il filtro di visibilita che risponde alla domanda: *"Questo listino e valido per il contesto X?"*

L'associazione non e un semplice collegamento — e il primo filtro che il resolver applica per determinare quali listini sono candidati. Ogni associazione specifica:

* a quale listino si riferisce (obbligatorio)
* per quale contesto vale (BA, utility, emittente — tutti opzionali)
* con quale priorita in caso di competizione tra listini
* in quale periodo e valida

| Scenario | billing_account_id | utility_id | emittente_id | Significato |
| --- | --- | --- | --- | --- |
| Listino generico | NULL | NULL | NULL | Disponibile per tutti |
| Listino per utility | NULL | 3 | NULL | Solo per utility gas (id=3) |
| Listino per cliente | 42 | NULL | NULL | Solo per BA 42 |
| Listino dedicato | 42 | 3 | 1 | Solo per BA 42, utility gas, emittente 1 |

La **priorita** (`priorita`, default 100) serve quando piu listini matchano lo stesso contesto: il listino con priorita numericamente piu bassa vince.

---

## Ciclo di vita di un listino

### Creazione

Un listino nasce con codice, descrizione e dominio. E subito attivo (`attivo=true`) ma non ancora operativo: servono almeno una versione e delle righe prezzo.

### Pubblicazione di una versione

Le versioni nascono in stato `BOZZA`. In questa fase si possono aggiungere, modificare e rimuovere righe prezzo liberamente. Quando la configurazione e pronta:

1. La versione passa a `ATTIVA` — da questo momento partecipa alla risoluzione prezzi
2. La transizione richiede almeno una riga attiva nella versione (guard DB)
3. Le versioni attive non possono sovrapporsi temporalmente

### Chiusura

Quando una versione non serve piu, passa a `CHIUSA`. Non partecipa piu alla risoluzione prezzi ma resta nel database per tracciabilita storica.

```text
BOZZA ──────→ ATTIVA ──────→ CHIUSA
 (editing)     (operativa)    (storica)
```

### Disattivazione

Un listino puo essere disattivato (`attivo=false`) per escluderlo completamente dalla risoluzione prezzi senza cancellarlo. La disattivazione e bloccata se esistono versioni o associazioni attive (guard trigger).

---

## Architettura del resolver prezzo

Il resolver (`vendite.fn_resolve_prezzo_listino`) e il cuore del sistema listini. Dato un contesto operativo, determina in modo **deterministico** quale prezzo applicare.

### Input

| Parametro | Obbligatorio | Descrizione |
| --- | --- | --- |
| `p_articolo_id` | si | L'articolo da prezzare |
| `p_uom_id` | si | L'unita di misura richiesta |
| `p_data_riferimento` | si | La data per cui serve il prezzo |
| `p_billing_account_id` | no | Il billing account del cliente |
| `p_utility_id` | no | La utility del servizio |
| `p_emittente_soggetto_ruolo_id` | no | L'emittente fiscale |

### Flusso di risoluzione

```text
Input: articolo + UoM + data + (opzionale: BA, utility, emittente)
  |
  v
1. ASSOCIAZIONI: filtra listini candidati per contesto
  |
  v
2. VERSIONI: filtra per data_riferimento + stato ATTIVA
  |
  v
3. RIGHE: cerca match per specificita dimensionale (7 livelli)
  |
  v
4. TIE-BREAK: match_level → associazione.priorita → versione.priorita → data
  |
  v
Output: prezzo + riferimenti (listino_id, versione_id, riga_id, associazione_id)
```

### Fase 1 — Selezione listini candidati

Il resolver parte dalle **associazioni attive** la cui finestra di validita comprende `p_data_riferimento`. Le dimensioni di contesto dell'associazione (BA, utility, emittente) vengono confrontate con i parametri in input.

Un'associazione con dimensioni NULL e compatibile con qualsiasi contesto (listino generico). Un'associazione con dimensioni specifiche matcha solo il contesto corrispondente.

### Fase 2 — Filtro versioni

Per ogni listino candidato, il resolver seleziona le versioni:

* con stato `ATTIVA`
* la cui finestra `[valido_dal, valido_al]` comprende `p_data_riferimento`
* appartenenti a listini attivi (`attivo=true`)

### Fase 3 — Match righe per specificita

Il resolver cerca le righe delle versioni candidate che matchano `articolo_id + uom_id`, assegnando un **livello di specificita** basato sulle dimensioni di contesto valorizzate:

| Livello | Dimensioni matchate | Significato |
| --- | --- | --- |
| 1 | BA + utility + emittente | Match piu specifico possibile |
| 2 | BA + utility | Specifico per cliente e servizio |
| 3 | BA + emittente | Specifico per cliente ed emittente (non-utility) |
| 4 | BA | Specifico per cliente |
| 5 | utility + emittente | Specifico per servizio ed emittente |
| 6 | utility | Specifico per tipo servizio |
| 7 | articolo + uom (fallback) | Prezzo base senza contesto |

**Vince la riga con livello piu basso** (piu specifica). Il resolver cerca il match piu stretto: se esiste un prezzo specifico per BA + utility + emittente, quello prevale sul prezzo generico.

### Fase 4 — Tie-break

Se piu righe hanno lo stesso livello di specificita, il resolver applica una cascata di tie-break:

1. **Priorita associazione** (`listini_associazioni.priorita`) — valore minore vince
2. **Priorita versione** (`listini_versioni.priorita`) — valore minore vince
3. **Validita piu specifica/recente** — data inizio validita piu recente

Se dopo tutti i tie-break restano righe equivalenti, il resolver genera l'errore `AMBIGUOUS_PRICE_MATCH`. Questo comportamento e intenzionale: nessun prezzo viene scelto in modo arbitrario.

### Output

| Campo | Tipo | Descrizione |
| --- | --- | --- |
| `listino_id` | UUID | Il listino selezionato |
| `listino_versione_id` | UUID | La versione selezionata |
| `listino_riga_id` | UUID | La riga prezzo selezionata |
| `listino_associazione_id` | UUID | L'associazione usata |
| `prezzo` | numeric(22,10) | Il prezzo risolto |
| `match_level` | integer | Il livello di specificita del match (1-7) |

### Comportamento in caso di errore

| Situazione | Errore | Significato |
| --- | --- | --- |
| Nessun match trovato | `E_PREZZO_LISTINO_NON_TROVATO` | Non esiste un prezzo applicabile per il contesto e la data |
| Match ambiguo | `E_PREZZO_LISTINO_AMBIGUO` | Piu righe equivalenti dopo tutti i tie-break |
| Parametro invalido | `E_PARAMETRO_INVALIDO` | Input mancante o non valido (es. data NULL, ID <= 0) |

Non esiste fallback silenzioso: se il resolver non trova un prezzo univoco, l'errore e esplicito e tracciabile.

---

## Regole multi-listino

Un concetto chiave del sistema e che la risoluzione opera **su tutti i listini candidati contemporaneamente**, non selezionando prima un listino vincente e poi cercando il prezzo al suo interno.

In pratica:

1. Le associazioni determinano quali listini sono candidati per il contesto
2. Le righe di **tutti** i listini candidati competono tra loro per specificita
3. La priorita dell'associazione interviene **solo come tie-break** tra righe di pari specificita

Questo significa che un listino con associazione a priorita alta (valore basso) non batte automaticamente un listino con priorita bassa ma con una riga piu specifica.

**Esempio:**

* Listino A: associazione priorita 10, riga con solo articolo+UoM (livello 7)
* Listino B: associazione priorita 50, riga con BA+utility+emittente (livello 1)

Vince il Listino B perche il match di livello 1 e piu specifico del livello 7, indipendentemente dalla priorita dell'associazione.

---

## Integrazione con commessa e fatturazione

Il prezzo risolto dal listino non viene usato direttamente in fattura. Il percorso completo e:

```text
Resolver listino
  |
  v
commesse_attivita (snapshot prezzo)
  |
  v
attivita_fatturabili (prezzo propagato)
  |
  v
fatture_righe (arrotondamento a 6 decimali)
```

### Snapshot in commessa

Quando un'attivita viene creata in commessa, il prezzo risolto viene salvato come snapshot:

* `listino_versione_id` — quale versione era attiva al momento
* `prezzo_snapshot` — il prezzo congelato
* `prezzo_bloccato` — se TRUE, il prezzo non viene ricalcolato dal resolver
* `pricing_mode` — `FIXED` in v1 (predisposto per `FORMULA`/`SCAGLIONI` in v2)

### Override manuale del prezzo

Se un documento (preventivo, ordine) riporta un prezzo manuale diverso dal listino:

* `prezzo_snapshot` = prezzo del documento
* `prezzo_bloccato = TRUE`
* `listino_versione_id` = versione risolta alla data (per audit comparativo)

Il prezzo manuale prevale sempre sul listino. La versione listino viene comunque salvata per permettere confronti e analisi.

### Propagazione verso attivita fatturabili

Il flag `prezzo_bloccato` viene propagato da `commesse_attivita` a `attivita_fatturabili` tramite la funzione di emissione. Lo step 1 della pipeline fatturazione legge il flag direttamente su `attivita_fatturabili`, evitando join sul dominio commessa durante la fase fiscale.

### Policy precisione prezzo

| Layer | Precisione | Note |
| --- | --- | --- |
| `listini_righe` | numeric(22,10) | Massima precisione |
| `commesse_attivita` | numeric(22,10) | Snapshot senza arrotondamento |
| `attivita_fatturabili` | numeric(22,10) | Propagazione fedele |
| `fatture_righe` | numeric(22,6) | Arrotondamento per esposizione fiscale |

La riduzione a 6 decimali avviene **solo** nel layer fatture. Nessuna funzione intermedia introduce arrotondamenti anticipati.

---

## Vincoli e regole di coerenza

### No overlap versioni

Per ogni listino, le versioni con stato `ATTIVA` non possono avere intervalli temporali sovrapposti. Il vincolo e implementato con indice di esclusione GIST (`ex_listini_versioni_no_overlap`).

### Unicita riga per combinazione dimensionale

Per ogni versione, non puo esistere piu di una riga attiva con la stessa combinazione `(articolo, uom, BA, utility, emittente)`. Il vincolo `uq_listini_righe_key_attiva` usa `COALESCE` sulle dimensioni opzionali per gestire i NULL.

### Unicita associazione

Per ogni listino, non puo esistere piu di un'associazione attiva con la stessa combinazione `(contesto + valido_dal)`. Vincolo: `uq_listini_associazioni_key_attiva`.

### Coerenza attivazione/disattivazione

I trigger garantiscono una catena di attivazione coerente:

* Non si puo disattivare un listino che ha versioni o associazioni attive
* Non si puo attivare una versione di un listino disattivato
* Non si puo creare righe su una versione di un listino disattivato
* Per attivare una versione (BOZZA → ATTIVA) deve avere almeno una riga attiva

### Coerenza referenziale

* Le righe verificano che articolo, UoM, utility e emittente siano attivi
* Le associazioni verificano che il listino parent sia attivo
* Tutti i vincoli operano tramite trigger (guard phase `_a10_`)

---

## Trigger e funzioni coinvolte

### Ordine di esecuzione (visione rapida)

```text
INSERT/UPDATE listini
  +-- guard: blocco disattivazione se figli attivi
  +-- tx_id + audit

INSERT/UPDATE listini_versioni
  +-- guard: parent listino attivo
  +-- guard: no overlap temporale tra attive
  +-- guard: almeno 1 riga per attivazione
  +-- tx_id + audit

INSERT/UPDATE listini_righe
  +-- guard: parent versione e listino attivi
  +-- guard: articolo, UoM attivi
  +-- guard: utility, emittente attivi (se valorizzati)
  +-- tx_id + audit

INSERT/UPDATE listini_associazioni
  +-- guard: parent listino attivo
  +-- tx_id + audit
```

### Funzione resolver

| Funzione | Scopo |
| --- | --- |
| [`vendite.fn_resolve_prezzo_listino`](/dbzero/vendite/funzioni/fn_resolve_prezzo_listino) | Risoluzione deterministica prezzo per articolo + UoM + data + contesto |

---

## Garanzia transazionale

Tutte le operazioni di creazione e modifica su listini, versioni, righe e associazioni avvengono all'interno di transazioni PostgreSQL. I vincoli di esclusione (no overlap, unicita dimensionale) sono verificati in tempo reale dal motore database.

Cosa significa in pratica:

* Se un vincolo viene violato (es. overlap date, riga duplicata), l'operazione viene annullata
* **Non esistono stati parziali**: i constraint sono applicati atomicamente
* Il resolver opera in lettura consistente: non puo vedere dati intermedi di una transazione in corso

---

## Rettifiche prezzi (previste, non ancora implementate)

Il sistema prevede un meccanismo di rettifica per gestire modifiche retroattive ai prezzi senza riscrivere le fatture emesse.

### Principio

Nessuna riscrittura distruttiva di fatture emesse. Le rettifiche producono **documenti correttivi** (delta positivo o negativo) tramite una pipeline dedicata.

### Canali

* **Manuale**: l'operatore avvia l'analisi su richiesta
* **Automatica**: un job schedulato rileva modifiche retroattive ai listini e avvia l'analisi degli impatti

Entrambi i canali usano lo stesso motore di ricerca impatti e lo stesso algoritmo delta.

### Stato attuale

La fase DB-L4 (rettifiche) e ancora da implementare. Il modello dati e il flusso sono definiti nell'[analisi operativa](/dev/work-in-progress/gestione-listini).

---

## Diagramma ER

````mermaid
%%{init: {'er': {'layoutDirection': 'TB'}}}%%
erDiagram

%% Struttura listini prezzo

    listini                ||--o{ listini_versioni        : ha_versioni
    listini                ||--o{ listini_associazioni    : visibile_per
    listini_versioni       ||--o{ listini_righe           : contiene_prezzi

    articoli               ||--o{ listini_righe           : prezzato_in
    unita_misura           ||--o{ listini_righe           : unita_di

    billing_account        ||--o{ listini_righe           : opzionale
    billing_account        ||--o{ listini_associazioni    : opzionale
    utilities              ||--o{ listini_righe           : opzionale
    utilities              ||--o{ listini_associazioni    : opzionale
    soggetti_ruoli         ||--o{ listini_righe           : emittente_opzionale
    soggetti_ruoli         ||--o{ listini_associazioni    : emittente_opzionale
````

---

## Diagramma del flusso di risoluzione

````mermaid
flowchart TD
    A[Input: articolo + UoM + data + contesto] --> B[Fase 1: Associazioni]
    B --> C{Listini candidati trovati?}
    C -- No --> ERR1[Errore: PREZZO_NON_TROVATO]
    C -- Si --> D[Fase 2: Versioni ATTIVE per data]
    D --> E{Versioni trovate?}
    E -- No --> ERR1
    E -- Si --> F[Fase 3: Match righe per specificita]
    F --> G{Righe trovate?}
    G -- No --> ERR1
    G -- Si --> H[Fase 4: Tie-break]
    H --> I{Vincitore unico?}
    I -- Si --> OK[Output: prezzo + riferimenti]
    I -- No --> ERR2[Errore: PREZZO_AMBIGUO]
````

---

{% include-markdown "signature-core.md" %}
