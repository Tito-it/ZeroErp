# Guida – Gestione Listini Prezzo

> (latest review 09-04-26 — refactor invariante univocita listini_associazioni Fase 1+2 completate)
>
> Destinatari: sviluppatori database, backend e analisti funzionali
>
> Vedi anche
>
> * Analisi e decisioni operative listini — decisioni architetturali, roadmap DB, integrazione commessa
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

Questa guida spiega **come funziona il sistema listini** — quali entita lo compongono, come si relazionano, come il resolver determina il prezzo e quali regole governano il processo. La logica e la stessa sia per l'ambito utility (gas, energia, idrico) sia per l'ambito commercio (servizi, manifatturiero).

**Cosa troverai in questa guida:**

* Le entita coinvolte e il loro ruolo nel processo
* Il ciclo di vita di un listino (dalla creazione alla chiusura)
* Come funziona la risoluzione deterministica del prezzo (7 livelli di precedenza)
* Le regole di tie-break quando piu listini concorrono
* L'integrazione con commesse e fatturazione
* Le garanzie di coerenza offerte dal database

### Il modello e generico, non solo per le utility

La struttura listini funziona per qualsiasi tipo di azienda. Il campo `utility_id` sul listino (FK a `config.utilities`, NOT NULL) classifica il servizio erogante: gas, energia, idrico, teleriscaldamento oppure "Base" per i listini di puro commercio. L'architettura sottostante — versioni, righe, associazioni, resolver — e identica in tutti i casi.

In pratica:

* **Azienda utility**: listini con `utility_id` specifico (Gas, Energia, Idrico), dimensioni righe BA + utility + emittente, prezzi ad alta precisione per consumi minimi
* **Azienda non-utility**: listini con `utility_id = 5` (Base), dimensioni BA (o senza contesto), pricing standard per servizi/prodotti

> **Refactor 2026-04-12**: il vecchio campo `dominio` (enum UTILITY/COMMERCIO) e` stato sostituito dalla FK `utility_id NOT NULL` verso `config.utilities`. La utility "Base" (id=5 nel seed standard) copre i listini commerciali.

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

E il contenitore principale. Identifica un listino con un codice univoco, una descrizione e una utility (`utility_id` NOT NULL, FK a `config.utilities`). Non contiene ne date ne prezzi: questi sono delegati alle entita figlie.

Il listino e pensato come entita stabile nel tempo. Quello che cambia sono le sue versioni e le sue righe prezzo.

### Versione

E la finestra temporale in cui un listino e valido. Ogni versione ha:

* un intervallo di validita (`valido_dal`, `valido_al`)
* uno stato che governa il ciclo di vita (`BOZZA` → `ATTIVA` → `CHIUSA`)

Le versioni con `stato = 'ATTIVA'` dello stesso listino **non possono sovrapporsi** temporalmente (vincolo esclusione `ex_listini_versioni_no_overlap`, fix `20260409-01`). Le BOZZE possono coesistere con la versione ATTIVA per supportare il workflow clone+publish.

> Il campo `listini_versioni.priorita` e stato **rimosso il 2026-04-09 (Fase 2)** insieme al check constraint `chk_listini_versioni_priorita`. Con l'invariante univocita per versione `ATTIVA` (post-fix `20260409-01`) non discriminava piu nulla.

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
* in quale periodo e valida

| Scenario | billing_account_id | utility_id | emittente_id | Significato |
| --- | --- | --- | --- | --- |
| Listino generico | NULL | NULL | NULL | Disponibile per tutti |
| Listino per utility | NULL | 3 | NULL | Solo per utility gas (id=3) |
| Listino per cliente | 42 | NULL | NULL | Solo per BA 42 |
| Listino dedicato | 42 | 3 | 1 | Solo per BA 42, utility gas, emittente 1 |

> **Invariante 2026-04-09**: per ogni triple `(BA, utility, emittente)` — con `NULL` come wildcard discreto — esiste **al massimo una** associazione attiva sull'intervallo temporale, indipendentemente dal listino. Vincolo `ex_listini_associazioni_no_overlap` (EXCLUDE GIST). Le sostituzioni avvengono via *autoclose* (vedi sezione "Workflow di sostituzione" piu sotto).
>
> Il campo `listini_associazioni.priorita` e stato **rimosso il 2026-04-09 (Fase 2)** insieme al check constraint `chk_listini_associazioni_priorita`. Con l'invariante univocita stretta non discriminava piu nulla.

---

## Ciclo di vita di un listino

### Creazione

Un listino nasce con codice, descrizione e utility. E subito attivo (`attivo=true`) ma non ancora operativo: servono almeno una versione e delle righe prezzo.

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

> **Nota sul livello 3 (BA + emittente senza utility):** questo livello e rilevante
> esclusivamente in contesti multi-emittente (tipicamente utility) dove l'emittente
> fiscale e un soggetto distinto dall'azienda erogante. In contesti commercio con
> emittente unico, il livello 3 non produce mai un match differente dal livello 4
> (BA da solo) e puo essere ignorato in fase di configurazione.

### Fase 4 — Tie-break

Con l'invariante univocita stretta (refactor 2026-04-09) il caso "due righe con stesso match_level" e strutturalmente vietato dal database:

* per ogni triple `(BA, utility, emittente)` esiste una sola associazione attiva sull'intervallo (`ex_listini_associazioni_no_overlap`)
* per ogni listino esiste una sola versione `ATTIVA` sull'intervallo (`ex_listini_versioni_no_overlap`)
* per ogni `(versione, articolo, uom, BA, utility, emittente)` esiste una sola riga attiva (`uq_listini_righe_key_attiva`)

Quindi il resolver, dopo aver applicato il `match_level` di specificita (sezione precedente), restituisce **al massimo una riga**. Niente tie-break vero da applicare.

Per **safety paranoid check**, se due righe arrivassero comunque con lo stesso `match_level` (scenario impossibile per costruzione, ma proteggiamo contro bug futuri o disabilitazione manuale di constraint), il resolver genera l'errore `E_PREZZO_LISTINO_AMBIGUO`. Nessun prezzo viene scelto in modo arbitrario.

> **Storia**: prima del refactor 2026-04-09 il resolver applicava una cascata di tie-break su `listini_associazioni.priorita` e `listini_versioni.priorita`. La Fase 1 (`20260409-03`) ha introdotto l'invariante univocita stretta, rendendo quel codice no-op safe. La Fase 2 (`20260409-04/-05`) ha **droppato fisicamente** le colonne `priorita` ed e stato pubblicato un nuovo `fn_resolve_prezzo_listino` (`20260409-04` in `20_code/vendite`) senza piu riferimenti alle colonne. L'`ORDER BY` del resolver si e ridotto a `match_rank`, `valido_dal DESC`, `valido_al ASC` + tie-break tecnico su `id` per determinismo.

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

## Regole univocita per scope (refactor 2026-04-09)

L'invariante centrale del sistema dopo il refactor del 2026-04-09 e:

> **Per ogni triple `(BA, utility, emittente)`** — con `NULL` come valore wildcard discreto — **esiste al massimo una associazione attiva sull'intervallo temporale, indipendentemente dal listino.**

Questo significa che a una data data, per uno scope dato, **un solo listino e responsabile del prezzo**. Niente competizione, niente tie-break tra listini concorrenti, niente "il listino con priorita piu bassa vince".

Il vincolo `ex_listini_associazioni_no_overlap` (EXCLUDE GIST cross-listino) impedisce a livello DB qualsiasi configurazione che violi questa invariante. Se si tenta di inserire un'associazione con scope sovrapposto a una esistente, il database rifiuta l'INSERT con errore esplicito.

### Workflow di sostituzione (autoclose + insert)

Per sostituire un'associazione esistente con una nuova (es. cambio listino di un cliente, cambio annuale, promo temporanea), il pattern operativo e:

1. **Autoclose** della vecchia: `UPDATE listini_associazioni SET valido_al = nuova.valido_dal - 1 WHERE id = vecchia_id`
2. **Insert** della nuova: `INSERT INTO listini_associazioni (..., valido_dal, valido_al) VALUES (..., nuova_valido_dal, nuova_valido_al)`
3. Tutto in **transazione atomica** (`with transaction.atomic()` lato backend)

Stesso pattern gia' adottato per `listini_versioni` (publish di una nuova versione con autoclose della precedente).

### Caso "promo temporanea" (override per periodo limitato)

Per applicare un listino "promo" su un BA per un periodo limitato `[Pmin, Pmax]` senza perdere il listino base prima e dopo:

```text
1. UPDATE listini_associazioni base BA: valido_al = Pmin - 1
2. INSERT listini_associazioni promo BA: scope=(BA), valido_dal=Pmin, valido_al=Pmax
3. INSERT listini_associazioni base BA ripristino: scope=(BA), valido_dal=Pmax+1, valido_al=NULL
Tutto in transazione atomica.
```

Questo workflow potra essere astratto in un endpoint backend dedicato `apply_temporary_pricing(BA, Pmin, Pmax, listino_id)` quando emerge il caso d'uso reale.

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

### No overlap versioni (per listino)

Per ogni listino, le versioni con `stato = 'ATTIVA'` non possono avere intervalli temporali sovrapposti. Il vincolo e implementato con indice di esclusione GIST (`ex_listini_versioni_no_overlap`, fix `20260409-01`). Le BOZZE possono coesistere per supportare il workflow clone+publish.

### Unicita riga per combinazione dimensionale

Per ogni versione, non puo esistere piu di una riga attiva con la stessa combinazione `(articolo, uom, BA, utility, emittente)`. Il vincolo `uq_listini_righe_key_attiva` usa `COALESCE` sulle dimensioni opzionali per gestire i NULL.

### Univocita associazione cross-listino (refactor 2026-04-09)

**Per ogni triple `(BA, utility, emittente)`** — con `NULL` come wildcard discreto — **non possono esistere due righe attive con intervalli temporali sovrapposti, indipendentemente dal listino**. Vincolo: `ex_listini_associazioni_no_overlap` (EXCLUDE GIST con `daterange && daterange`, fix `20260409-02`).

Questa e l'invariante che garantisce univocita del listino responsabile del prezzo per ogni scope dimensionale a ogni data. Vedi sezione "Regole univocita per scope" sopra.

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

## Guida operativa: il "listino post-it"

Il termine "listino post-it" descrive l'uso di un secondo listino piccolo per correggere
il prezzo di un singolo articolo senza toccare il listino base. Come un post-it attaccato
sopra il cartellone grande.

### Quando funziona

Il listino post-it funziona quando il prezzo corretto vale per un **contesto specifico** —
un cliente preciso, una utility precisa. In quel caso la riga nel listino post-it ha il BA
valorizzato (match_level 4) o BA+utility (match_level 2). Il resolver la trova prima della
riga generica del listino base, perche e piu specifica.

### Quando NON funziona

Il listino post-it **non funziona** quando il prezzo corretto deve valere per **tutti i
clienti** (riga generica, match_level 7). Entrambi i listini avrebbero un'associazione
generica (NULL, NULL, NULL) per lo stesso periodo, e il vincolo
`ex_listini_associazioni_no_overlap` lo impedisce a livello DB: non possono esistere due
associazioni con lo stesso scope nello stesso periodo.

### Tabella delle soluzioni

| Situazione | Soluzione corretta |
|---|---|
| Prezzo sbagliato per un cliente specifico, articolo non ancora fatturato | Rettifica controllata N6 sulla riga |
| Prezzo sbagliato per un cliente specifico, articolo gia fatturato | Listino post-it con BA valorizzato sulla riga |
| Prezzo sbagliato per tutti i clienti, articolo non ancora fatturato | Rettifica controllata N6 sulla riga |
| Prezzo sbagliato per tutti i clienti, articolo gia fatturato | Clone listino + correggi la riga + attiva (O1) |
| Aumento prezzi annuale su tutto il listino | Clone + variazione % massa (N8a) + attiva |

### Operazioni disponibili

| Operazione | Contesto | API |
|---|---|---|
| **Rettifica controllata (N6)** | Riga ATTIVA non propagata | `PATCH .../rettifica-controllata/` |
| **Variazione % massa (N8a)** | Righe BOZZA (aumento/riduzione) | `POST .../applica-variazione/` |
| **Clone versione (O1)** | Da qualsiasi stato | `POST .../clona/` |
| **Programma chiusura** | Versione ATTIVA, imposta `valido_al` | `PATCH .../` con `valido_al` |

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

La fase DB-L4 (rettifiche) e ancora da implementare. Il modello dati e il flusso sono definiti nell'analisi operativa interna.

---

## Diagramma ER

````mermaid
%%{init: {'er': {'layoutDirection': 'TB'}}}%%
erDiagram

%% Struttura listini prezzo

    listini                ||--o{ listini_versioni        : ha_versioni
    listini                ||--o{ listini_associazioni    : visibile_per
    listini_versioni       ||--o{ listini_righe           : contiene_prezzi

    utilities              ||--o{ listini                 : classifica_testata
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
