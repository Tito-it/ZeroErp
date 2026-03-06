# Guida – Gestione Pratiche e Workflow

> (latest review 06-03-26)
>
> Destinatari: sviluppatori database, backend e analisti funzionali
>
> Questa guida descrive il motore pratiche di Zero ERP: modello dati, ciclo di vita, flussi operativi, giornale di bordo e integrazione cross-dominio.
>
> Vedi anche
>
> * [Guida Soggetti e Ruoli Anagrafici](/guide/soggetti-e-ruoli-anagrafici)
> * [Mappa Concentrica](/mappa-concentrica)
> * [Analisi Tracciamento Processi e Job](/guide/Analisi-tracciamento-processi-e-job)

---

## Introduzione

In Zero ERP **tutto e' una pratica**. Ogni operazione — dall'onboarding di un cliente alla gestione di un reclamo, dalla revisione di un contratto alla lavorazione di un ordine — transita dal motore pratiche.

Il sistema opera su due modalita':

* **Con flussi vincolanti**: controllo sequenza e prerequisiti attivi, workflow completo con handler automatizzati
* **Senza flussi vincolanti**: giornale di bordo con tracciabilita' totale, senza vincoli di sequenza

**Cosa troverai in questa guida:**

* L'architettura del modello pratica/flusso e la sua posizione nel modello concentrico
* Come funzionano i tipi prestazione, i template flussi e i prerequisiti
* Il ciclo di vita di pratiche e flussi con le transizioni di stato
* Il giornale di bordo immutabile e come viene alimentato
* La generazione cross-pratica e il registry handler Django
* Le sospensioni: come congelare e riattivare pratiche e flussi
* Le formule tempo e i calcoli tempo: misurazione automatica delle durate e soglie di allerta
* La macchina a stati rigida: transizioni validate dal database
* Gli endpoint API e la struttura backend

---

## Posizione nel modello concentrico

Il modulo pratiche si colloca come **anello infrastrutturale** (Anello 2) nel modello concentrico:

```text
Anello 0: core, dbops, maintenance (infrastruttura)
Anello 1: config, anagrafiche, catalogo (dati di base)
Anello 2: pratiche (workflow engine)
Anello 3: vendite, acquisti, magazzino (operazioni)
```

* Si appoggia sugli anelli interni: `anagrafiche` (soggetti, risorse umane), `config` (stati, unita' organizzative)
* Parla lo stesso linguaggio: audit fields, tx_id, storicizzazione, error handling centralizzato
* Gli anelli esterni (vendite, acquisti, magazzino) si appoggiano su pratiche tramite le tabelle di estensione (`ext_*`) senza rompere la coerenza del nucleo

---

## Tabelle coinvolte

**Configurazione (schema `config`):**

* `config.stati_pratiche` — stati del ciclo di vita pratica (BOZZA, APERTA, SOSPESA, CHIUSA, ANNULLATA)
* `config.stati_flussi_pratiche` — stati del flusso (DA_ESEGUIRE, IN_CORSO, COMPLETATO, SOSPESO, ANNULLATO, ERRORE)
* `config.priorita_pratiche` — livelli di priorita' con ordinamento (BASSA, NORMALE, ALTA, URGENTE)
* `config.tipi_nota` — tipologie di nota (GENERALE, INTERNA, CLIENTE, TECNICA, LEGALE)
* `config.tipi_allegato` — tipologie di allegato (DOCUMENTO, IMMAGINE, MODULO, CONTRATTO, ...)
* `config.canali_pratiche` — canali di visibilita' (WEB_CLIENTI, APP_TECNICA, PORTALE_FORNITORI)

**Nucleo (schema `pratiche`):**

* `pratiche.tipi_prestazione` — catalogo dei tipi di pratica
* `pratiche.handler_flussi` — registry handler Django per dispatch automatico
* `pratiche.template_flussi` — template dei flussi per ogni tipo prestazione
* `pratiche.template_flussi_prerequisiti` — prerequisiti espliciti tra flussi
* `pratiche.template_flussi_canali` — relazione M:N tra template flussi e canali
* `pratiche.regole_generazione` — regole generazione cross-pratica
* `pratiche.pratiche` — istanza operativa (testata)
* `pratiche.flussi` — step operativo (riga)
* `pratiche.note_pratiche` / `pratiche.note_flussi` — note su testata/flusso
* `pratiche.allegati_pratiche` / `pratiche.allegati_flussi` — documenti su testata/flusso
* `pratiche.giornale` — audit trail immutabile
* `pratiche.sospensioni` — periodi di fermo pratica/flusso
* `pratiche.formule_tempo` — configurazione tempi attesi tra coppie di flussi
* `pratiche.calcoli_tempo` — tracciamento tempi netti (calcolati da trigger)

---

## Il modello in sintesi

```text
tipi_prestazione (catalogo condiviso)
    |
    +-- template_flussi ---- template_flussi_prerequisiti
    |       |       |
    |       |       +-- template_flussi_canali (M:N -> canali_pratiche)
    |       |
    |       +-- handler_flussi (registry)
    |       |
    |       +-- regole_generazione (cross-pratica)
    |
    +-- formule_tempo (coppie flusso_da / flusso_a con giorni attesi)
    |
    v
pratiche -------------------- note_pratiche
    |                         allegati_pratiche
    |
    +-- flussi -------------- note_flussi
    |     |                   allegati_flussi
    |     +-- flussi (padre -> figlio)
    |
    +-- sospensioni (periodi di fermo, con propagazione ai flussi)
    |
    +-- calcoli_tempo (tempi netti da/a, calcolati da trigger)
    |
    +-- giornale (immutabile, alimentato da trigger)
```

---

## Componenti del modello

### 1. Il tipo prestazione: il catalogo

Un **tipo prestazione** e' una macro-categoria di attivita' gestibile: ONBOARDING_CLIENTE, GESTIONE_ORDINE, RECLAMO, REVISIONE_CONTRATTO.

* **categoria**: raggruppamento libero (es. UTILITIES, COMMERCIALE, AMMINISTRATIVO)
* **flussi_vincolanti**: `true` = controllo sequenza/prerequisiti attivo, `false` = giornale senza vincoli

Il catalogo e' **condiviso** tra tutti gli emittenti fiscali. La segregazione multi-company avviene sulla tabella `pratiche.pratiche` tramite `emittente_fiscale_id`.

### 2. I template flussi: la configurazione del workflow

Ogni tipo prestazione ha un insieme di **template flussi** che definiscono gli step operativi previsti:

* **sequenza**: ordine logico (0, 10, 20...). Il controllo effettivo e' sui prerequisiti espliciti
* **direzione**: caratterizza il flusso rispetto all'esterno (ENTRATA, USCITA, INTERNA)
* **handler_id**: NULL = step manuale, NOT NULL = step automatizzato (Django dispatch)
* **handler_params**: JSONB con parametri operativi per l'handler (es. invio_sms_conferma)
* **obbligatorio**: se il flusso e' richiesto per completare la pratica

### 3. I prerequisiti: il grafo del workflow

La tabella `template_flussi_prerequisiti` definisce le dipendenze tra flussi:

* Supporta rami **paralleli**, **convergenze** e flussi **opzionali**
* **obbligatorio**: `true` = bloccante, `false` = consigliato (warning senza blocco)
* CHECK: nessun self-reference (`template_flusso_id <> prerequisito_flusso_id`)

La funzione DB `fn_check_prerequisiti_flusso()` verifica se un flusso puo' essere avviato. La guard `fn_guard_prerequisiti_flusso()` blocca l'INSERT se i prerequisiti non sono soddisfatti.

### 4. La pratica: l'istanza operativa

Una **pratica** e' l'istanza concreta, la testata. Contiene:

| Campo | Tipo | Note |
| --- | --- | --- |
| `emittente_fiscale_id` | BIGINT | Segregazione multi-company |
| `soggetto_id` | UUID | FK a `anagrafiche.soggetti` |
| `stato_id` | INTEGER | FK a `config.stati_pratiche` |
| `priorita_id` | INTEGER | FK a `config.priorita_pratiche` |
| `tipo_prestazione_id` | INTEGER | FK a `pratiche.tipi_prestazione` |
| `risorsa_umana_id` | BIGINT | Operatore assegnato |
| `unita_organizzativa_id` | INTEGER | Reparto assegnato |
| `pratica_padre_id` | BIGINT | Per sotto-pratiche (self-reference) |
| `flusso_origine_id` | BIGINT | Tracciabilita' cross-pratica |
| `canale_origine_id` | INTEGER | Sorgente esterna (NULL = interna) |
| `solo_interna` | BOOLEAN | Se true, niente canali su flussi |
| `codice` | TEXT | Generato da trigger |
| `descrizione` | TEXT | Descrizione libera |
| `data_scadenza` | DATE | Scadenza prevista |

### 5. Il flusso: lo step operativo

Un **flusso** e' una fase operativa dentro una pratica. Contiene:

* `template_flusso_id`: NULL per flussi aggiunti manualmente su pratiche libere
* `stato_id`: FK a `config.stati_flussi_pratiche`
* `sequenza`: ordine esecuzione nel workflow
* `esito`: POSITIVO, NEGATIVO, PARZIALE, NON_APPLICABILE (impostato al completamento)
* `note_esito`: note libere sull'esito
* `flusso_padre_id`: per albero di sotto-flussi (self-reference)

### 6. Le formule tempo: i semafori del workflow

Una **formula tempo** definisce quanto tempo deve passare tra il completamento di un flusso e il completamento di un altro. E' il meccanismo di controllo temporale del workflow.

Ogni formula tempo collega due template flussi appartenenti allo stesso tipo prestazione:

| Campo | Significato |
| --- | --- |
| `template_flusso_da_id` | Lo step che avvia il conteggio (es. PRESA_CARICO) |
| `template_flusso_a_id` | Lo step che chiude il conteggio (es. SOPRALLUOGO) |
| `giorni_esecuzione` | Tempo massimo concesso in giorni lavorativi |
| `giorni_warning` | Soglia warning (es. 80% del tempo — sfondo giallo in UI) |
| `giorni_critico` | Soglia critica (es. 90% del tempo — sfondo rosso in UI) |

**Esempio concreto** — tipo prestazione ONBOARDING_CLIENTE con 3 step:

```text
Formula 1: PRESA_CARICO → ANALISI_DATI    (10 giorni, warning a 7, critico a 9)
Formula 2: ANALISI_DATI → PRIMO_CONTATTO   (5 giorni, warning a 3, critico a 4)
Formula 3: PRESA_CARICO → PRIMO_CONTATTO   (15 giorni, warning a 12, critico a 14)
```

La formula 3 misura il tempo complessivo dall'inizio alla fine. Le formule 1 e 2 misurano i singoli tratti. Si possono avere piu' formule sullo stesso tipo prestazione, anche con sovrapposizioni: ogni coppia da/a e' indipendente.

Le formule sono **configurazione statica**: una volta definite per un tipo prestazione, si applicano automaticamente a tutte le pratiche di quel tipo. Il calcolo effettivo avviene nella tabella `calcoli_tempo` (vedi sezione successiva).

### 7. Le sospensioni: il fermo controllato

Una **sospensione** rappresenta un periodo in cui una pratica o un flusso sono fermi per cause esterne (attesa documenti, attesa risposta cliente, attesa tecnico). Durante la sospensione il conteggio dei tempi si blocca.

| Campo | Significato |
| --- | --- |
| `pratica_id` | Pratica a cui si riferisce la sospensione |
| `flusso_id` | NULL = sospensione sull'intera pratica, NOT NULL = sospensione su singolo flusso |
| `data_inizio` | Inizio del fermo (impostato automaticamente a NOW()) |
| `data_fine` | Fine del fermo (NULL = sospensione attiva, impostata a NOW() alla riattivazione) |
| `data_riattivazione_prevista` | Data oltre la quale il job pgAgent riattiva automaticamente |
| `motivo` | Motivazione obbligatoria (testo libero) |

La distinzione tra sospensione **pratica** e sospensione **flusso** e' fondamentale:

* **Sospensione pratica**: blocca tutto. Il trigger DB cambia lo stato di tutti i flussi IN_CORSO a SOSPESO. E' l'equivalente del "metti in pausa" su tutta la lavorazione
* **Sospensione flusso**: blocca solo uno step. Gli altri flussi della stessa pratica continuano normalmente. Utile quando un singolo step e' in attesa ma il resto del lavoro puo' procedere

**Vincolo di unicita'**: una pratica puo' avere al massimo una sospensione attiva (`data_fine IS NULL`) alla volta. Lo stesso vale per ogni singolo flusso. Non si puo' sospendere qualcosa che e' gia' sospeso.

### 8. I calcoli tempo: la misurazione automatica

Quando un flusso viene completato, il trigger DB verifica se esiste una formula tempo in cui quel flusso e' il `template_flusso_da` o il `template_flusso_a`. Se si', crea o aggiorna un record nella tabella `calcoli_tempo`.

| Campo | Significato |
| --- | --- |
| `flusso_da_id` | ID del flusso concreto che ha avviato il conteggio |
| `flusso_a_id` | ID del flusso concreto che ha chiuso il conteggio |
| `data_inizio_calcolo` | Data di completamento del flusso_da |
| `data_fine_calcolo` | Data di completamento del flusso_a (NULL se non ancora completato) |
| `giorni_lordi` | Giorni totali tra inizio e fine |
| `giorni_sospensione` | Giorni in cui la pratica/flusso era sospesa |
| `giorni_netti` | giorni_lordi - giorni_sospensione |
| `giorni_formula` | Giorni previsti dalla formula (copiati per storicizzazione) |
| `sforato` | `true` se giorni_netti > giorni_formula |

**Esempio concreto** — pratica ONBOARDING con formula PRESA_CARICO → PRIMO_CONTATTO (15 giorni):

```text
1 marzo:  Presa in carico completata       → calcolo creato (data_inizio = 1 marzo)
5 marzo:  Pratica sospesa (attesa documenti)
8 marzo:  Pratica riattivata                → 3 giorni di sospensione
12 marzo: Primo contatto completato         → calcolo aggiornato:
                                               giorni_lordi = 11
                                               giorni_sospensione = 3
                                               giorni_netti = 8
                                               giorni_formula = 15
                                               sforato = false (8 < 15)
```

Se il primo contatto fosse stato completato il 25 marzo invece del 12:

```text
25 marzo: Primo contatto completato         → calcolo aggiornato:
                                               giorni_lordi = 24
                                               giorni_sospensione = 3
                                               giorni_netti = 21
                                               giorni_formula = 15
                                               sforato = true (21 > 15)
```

Il flag `sforato` e' l'informazione che la UI usa per mostrare il semaforo rosso. I campi `giorni_warning` e `giorni_critico` dalla formula tempo permettono alla UI di mostrare giallo o rosso anche prima dello sforamento effettivo.

### 9. La macchina a stati: il controllo rigido

Le transizioni di stato di pratiche e flussi sono governate da due tabelle di configurazione:

* `config.transizioni_stati_pratiche` — definisce le coppie (stato_da, stato_a) ammesse per le pratiche
* `config.transizioni_stati_flussi` — definisce le coppie (stato_da, stato_a) ammesse per i flussi

Un trigger BEFORE UPDATE su `pratiche.pratiche` e su `pratiche.flussi` verifica che la transizione richiesta sia presente nella tabella di configurazione. Se non lo e', il trigger rifiuta l'operazione con un errore esplicito (`E_PRATICHE_TRANSIZIONE_NON_AMMESSA` o `E_FLUSSI_TRANSIZIONE_NON_AMMESSA`).

**Transizioni ammesse per le pratiche:**

```text
BOZZA       → APERTA, ANNULLATA
APERTA      → SOSPESA, CHIUSA, ANNULLATA
SOSPESA     → APERTA
```

**Transizioni ammesse per i flussi:**

```text
DA_ESEGUIRE → IN_CORSO, ANNULLATO
IN_CORSO    → COMPLETATO, SOSPESO, ERRORE
SOSPESO     → IN_CORSO
```

Questo approccio ha tre vantaggi rispetto a validare le transizioni nel codice applicativo:

1. **Nessun bypass**: anche un UPDATE diretto via SQL rispetta le regole
2. **Configurabilita'**: aggiungere una nuova transizione e' un INSERT nella tabella config, senza deploy
3. **Coerenza**: tutte le applicazioni (Django, job pgAgent, script di manutenzione) rispettano le stesse regole

---

## Ciclo di vita

### Pratica

```text
BOZZA --> APERTA --> CHIUSA
  |         |
  |         +--> SOSPESA --> APERTA
  |         |
  |         +--> ANNULLATA
  |
  +--> ANNULLATA
```

* Una pratica nasce in stato **BOZZA**
* Da BOZZA puo' passare ad **APERTA** o essere **ANNULLATA**
* Da APERTA puo' essere **SOSPESA**, **CHIUSA** o **ANNULLATA**
* Da SOSPESA puo' tornare **APERTA**

### Flusso

```text
DA_ESEGUIRE --> IN_CORSO --> COMPLETATO (con esito)
    |              |
    |              +--> SOSPESO --> IN_CORSO
    |              |
    |              +--> ERRORE
    |
    +--> ANNULLATO
```

* Un flusso nasce in stato **DA_ESEGUIRE**
* Viene **avviato** (IN_CORSO), poi **completato** con esito obbligatorio
* Da IN_CORSO puo' essere **sospeso** (SOSPESO) e poi ripreso (torna IN_CORSO)
* Da IN_CORSO puo' andare in **ERRORE** (errore tecnico/handler)
* Da DA_ESEGUIRE puo' essere **ANNULLATO** direttamente
* Al completamento con `auto = true`, il trigger DB puo' generare automaticamente nuove pratiche

> **Nota**: la macchina a stati e' implementata come **rigida** nel DB tramite la tabella `config.transizioni_stati_pratiche` / `config.transizioni_stati_flussi` e trigger di validazione. Le transizioni non ammesse vengono rifiutate dal DB. La sospensione temporanea (con data di riattivazione e job pgAgent) e' implementata: il flusso SOSPESO torna IN_CORSO alla riattivazione manuale o automatica.

---

## Il giornale di bordo

Il giornale (`pratiche.giornale`) e' un log **immutabile** alimentato automaticamente via trigger. Non si modifica, non si cancella.

Ogni riga registra:

* **azione**: uno dei 9 eventi (PRATICA_CREATA, STATO_CAMBIATO, ASSEGNAZIONE_CAMBIATA, PRIORITA_CAMBIATA, FLUSSO_CREATO, FLUSSO_STATO_CAMBIATO, NOTA_AGGIUNTA, ALLEGATO_AGGIUNTO, PRATICA_GENERATA)
* **origine**: SISTEMA, UTENTE, HANDLER, SCHEDULER
* **dettaglio**: JSONB con valori precedenti/nuovi per ricostruzione completa
* **tx_id**: correlazione con la transazione per tracciabilita' cross-tabella

Django **non deve loggare**: il DB lo fa da solo tramite 10 trigger functions dedicate.

### Approccio generico delle azioni

Le azioni STATO_CAMBIATO e FLUSSO_STATO_CAMBIATO sono **generiche**: coprono tutte le transizioni di stato senza moltiplicare i tipi azione. Che la pratica passi da APERTA a SOSPESA, da SOSPESA a APERTA, o da APERTA ad ANNULLATA, l'azione registrata e' sempre `STATO_CAMBIATO`. Lo stesso vale per i flussi.

I dettagli specifici (stato precedente, stato nuovo, esito se applicabile) sono nel campo JSONB `dettaglio`:

```json
{
  "stato_precedente": "APERTA",
  "stato_nuovo": "SOSPESA",
  "tx_id": "a1b2c3..."
}
```

Questo design mantiene il CHECK sulla colonna `azione` stabile nel tempo: non serve aggiungere nuovi valori per nuove transizioni. La ricostruzione di cosa e' successo avviene sempre leggendo il `dettaglio`.

---

## Sospensioni in azione

La sospensione e' una delle operazioni piu' comuni nella gestione quotidiana delle pratiche. Ogni volta che una lavorazione si blocca per cause esterne, l'operatore sospende e il sistema congela i tempi.

### Esempio 1: sospensione pratica con propagazione

Un'azienda gestisce un onboarding cliente. La pratica ha due flussi attivi in parallelo: VERIFICA_DATI (IN_CORSO) e PRIMO_CONTATTO (IN_CORSO). Il cliente comunica che sara' assente per due settimane.

```text
Stato iniziale:
  Pratica #123           stato: APERTA
    Flusso #456 VERIFICA_DATI   stato: IN_CORSO
    Flusso #457 PRIMO_CONTATTO  stato: IN_CORSO
    Flusso #458 SOPRALLUOGO     stato: DA_ESEGUIRE

L'operatore sospende la pratica con motivo "Cliente assente fino al 20 marzo"

Dopo la sospensione:
  Pratica #123           stato: SOSPESA
    Flusso #456 VERIFICA_DATI   stato: SOSPESO    (propagato dal trigger)
    Flusso #457 PRIMO_CONTATTO  stato: SOSPESO    (propagato dal trigger)
    Flusso #458 SOPRALLUOGO     stato: DA_ESEGUIRE (non toccato — non era IN_CORSO)

Sospensione creata:
  id: 50, pratica_id: 123, flusso_id: NULL
  data_inizio: 6 marzo 10:00
  data_fine: NULL (attiva)
  motivo: "Cliente assente fino al 20 marzo"
  data_riattivazione_prevista: 20 marzo
```

Alla riattivazione (manuale o automatica via pgAgent il 20 marzo):

```text
Dopo la riattivazione:
  Pratica #123           stato: APERTA
    Flusso #456 VERIFICA_DATI   stato: IN_CORSO   (ripristinato dal trigger)
    Flusso #457 PRIMO_CONTATTO  stato: IN_CORSO   (ripristinato dal trigger)
    Flusso #458 SOPRALLUOGO     stato: DA_ESEGUIRE (invariato)

Sospensione chiusa:
  id: 50, data_fine: 20 marzo 08:00
```

Il giornale registra automaticamente 4 eventi: STATO_CAMBIATO per la pratica e FLUSSO_STATO_CAMBIATO per ciascun flusso toccato, sia alla sospensione che alla riattivazione.

### Esempio 2: sospensione singolo flusso

Nella stessa pratica di onboarding, il flusso SOPRALLUOGO e' stato avviato (IN_CORSO) ma il tecnico incaricato e' malato. L'operatore sospende **solo** quel flusso senza fermare il resto:

```text
Stato iniziale:
  Pratica #123           stato: APERTA
    Flusso #456 VERIFICA_DATI   stato: COMPLETATO
    Flusso #457 PRIMO_CONTATTO  stato: COMPLETATO
    Flusso #458 SOPRALLUOGO     stato: IN_CORSO

L'operatore sospende il flusso #458 con motivo "Tecnico assente"

Dopo la sospensione:
  Pratica #123           stato: APERTA           (invariata)
    Flusso #458 SOPRALLUOGO     stato: SOSPESO

Sospensione creata:
  id: 51, pratica_id: 123, flusso_id: 458
  motivo: "Tecnico assente"
```

La pratica resta APERTA. Eventuali altri flussi nuovi possono essere creati e avviati normalmente. Solo il flusso sospeso e' bloccato.

### Esempio 3: riattivazione automatica via pgAgent

Se la sospensione ha una `data_riattivazione_prevista`, il job pgAgent controlla periodicamente (ogni ora o ogni giorno, a seconda della configurazione) se esistono sospensioni con data prevista scaduta. Se ne trova, le chiude automaticamente e ripristina gli stati.

Questo evita che una pratica resti dimenticata in stato SOSPESA: alla scadenza prevista torna attiva e l'operatore riceve la notifica nella sua agenda.

---

## Calcoli tempo in azione

I calcoli tempo sono il cuore del monitoraggio SLA e della reportistica temporale. Funzionano in modo completamente automatico: il backend e la UI li consultano in sola lettura.

### Esempio: onboarding con formula tempo e sospensione

Configurazione formula tempo per tipo prestazione ONBOARDING_CLIENTE:

```text
Formula: PRESA_CARICO → SOPRALLUOGO
  giorni_esecuzione: 15
  giorni_warning: 12
  giorni_critico: 14
```

Sequenza operativa:

```text
1 marzo (giorno 0):
  Flusso PRESA_CARICO completato
  → trigger DB crea calcolo_tempo:
    flusso_da_id: 456 (PRESA_CARICO)
    flusso_a_id: NULL (SOPRALLUOGO non ancora completato)
    data_inizio_calcolo: 1 marzo
    giorni_formula: 15

5 marzo (giorno 4):
  Pratica sospesa per "attesa documenti catastali"
  → il conteggio dei giorni netti si congela

8 marzo (giorno 7):
  Pratica riattivata
  → 3 giorni di sospensione registrati

16 marzo (giorno 15, ma 12 netti):
  Flusso SOPRALLUOGO completato
  → trigger DB aggiorna calcolo_tempo:
    flusso_a_id: 458 (SOPRALLUOGO)
    data_fine_calcolo: 16 marzo
    giorni_lordi: 15
    giorni_sospensione: 3
    giorni_netti: 12
    giorni_formula: 15
    sforato: false
```

La UI puo' mostrare il semaforo in tempo reale:

* **Giorno 1-11**: verde (sotto warning)
* **Giorno 12**: giallo (raggiunta soglia warning)
* **Giorno 14**: rosso (raggiunta soglia critica)
* **Giorno 15+**: rosso lampeggiante (sforato)

I giorni di sospensione vengono esclusi da tutti i conteggi: un periodo di fermo non penalizza il rispetto degli SLA.

### Formule tempo multiple sulla stessa pratica

E' comune configurare piu' formule sullo stesso tipo prestazione per misurare sia i tratti intermedi che il tempo complessivo:

```text
Formula 1: PRESA_CARICO → ANALISI         ( 5 giorni) — tempo analisi
Formula 2: ANALISI → SOPRALLUOGO          (10 giorni) — tempo programmazione
Formula 3: PRESA_CARICO → SOPRALLUOGO     (15 giorni) — tempo complessivo
Formula 4: SOPRALLUOGO → RISPOSTA_CLIENTE ( 3 giorni) — tempo risposta
```

Ogni formula genera il proprio record in `calcoli_tempo`. La UI puo' mostrare tutti i semafori sulla stessa pratica, evidenziando quale tratto e' in ritardo.

### Endpoint API sospensioni e calcoli tempo

| Endpoint | Metodo | Descrizione |
| --- | --- | --- |
| `/api/v1/pratiche/{id}/sospendi/` | POST | Sospende pratica intera |
| `/api/v1/pratiche/{id}/riattiva/` | POST | Riattiva pratica sospesa |
| `/api/v1/pratiche/{id}/sospensioni/` | GET | Lista sospensioni pratica (attive e chiuse) |
| `/api/v1/pratiche/{id}/calcoli-tempo/` | GET | Calcoli tempo pratica |
| `/api/v1/pratiche/{id}/flussi/{fid}/sospendi/` | POST | Sospende singolo flusso |
| `/api/v1/pratiche/{id}/flussi/{fid}/riattiva/` | POST | Riattiva singolo flusso |

---

## Generazione cross-pratica

Le `regole_generazione` configurano la creazione automatica di nuove pratiche al completamento di un flusso:

| Campo | Funzione |
| --- | --- |
| `template_flusso_origine_id` | Il flusso che scatena la generazione |
| `tipo_prestazione_dest_id` | Il tipo pratica da generare |
| `template_flusso_dest_id` | Il flusso iniziale della pratica generata (NULL = nessuno) |
| `esito_richiesto` | POSITIVO, NEGATIVO, QUALSIASI |
| `auto` | Se true, generazione automatica al completamento (trigger DB) |

La funzione `fn_genera_pratica_da_flusso()` copia emittente, soggetto e priorita' dalla pratica sorgente. La pratica generata ha `flusso_origine_id` per tracciabilita'.

---

## Handler Django (registry pattern)

La tabella `handler_flussi` contiene le chiavi di dispatch (`handler_key`). Django mantiene un mapping statico `handler_key -> classe Handler` nel codice Python:

```python
# apps/pratiche/services/handler_registry.py
HANDLER_MAP: dict[str, type[BaseFlussoHandler]] = {
    # "APPUNTAMENTO": AppuntamentoHandler,
    # "SOPRALLUOGO": SopralluogoHandler,
}
```

* Nessun path Python nel DB. Il DB valida solo l'esistenza della chiave
* Il dispatch avviene via `pratiche_service.dispatch_handler(flusso_id)`

### Contratto handler

Ogni handler implementa il protocollo `BaseFlussoHandler` con un unico metodo:

```python
def execute(
    self,
    flusso_id: int,
    pratica_id: int,
    meta: dict[str, Any],
    handler_params: dict[str, Any],
) -> dict[str, Any]:
    ...
```

**Input ricevuto:**

* `flusso_id` — ID del flusso da processare
* `pratica_id` — ID della pratica padre
* `meta` — JSONB `meta` del flusso (dati estensibili, specifici dell'istanza)
* `handler_params` — JSONB `handler_params` da `template_flussi` (configurazione statica del template)

**Output atteso:**

* Un `dict` con il risultato dell'operazione (struttura libera, dipendente dall'handler)
* Se l'handler non ha nulla da restituire, restituisce `{}`

**Gestione errori:**

* L'handler solleva eccezioni standard Python (es. `ServiceError`)
* Il middleware Django (`api_exception_middleware`) cattura e trasforma in risposta HTTP
* Se l'handler non e' trovato nel registry, `dispatch_handler` restituisce `None` senza errore

### Flusso di dispatch

```text
dispatch_handler(flusso_id)
    |
    +-- Lookup flusso dal DB
    +-- Legge template_flusso_id dal flusso
    +-- Cerca handler_key nel template flusso
    +-- Cerca handler_class in HANDLER_MAP
    +-- Invoca handler.execute(flusso_id, pratica_id, meta, handler_params)
    +-- Restituisce il risultato (o None se nessun handler)
```

`dispatch_handler` recupera sia `handler_key` che `handler_params` dal template flusso e li passa all'handler. In questo modo l'handler riceve sia i dati dell'istanza (`meta` dal flusso) che la configurazione statica (`handler_params` dal template).

---

## Vincoli e trigger

### Trigger business-specific (non standard)

I trigger standard (audit, lock codice_interno, attivo protection, tx_id, storicizzazione) sono gestiti automaticamente da `dbops.fn_run_automations()`. Qui sono elencati **solo** i trigger del dominio pratiche.

#### Su `pratiche.pratiche`

| Trigger | Evento | Funzione |
| --- | --- | --- |
| `trg_pratiche_z90_giornale_ins` | AFTER INSERT | Registra PRATICA_CREATA nel giornale |
| `trg_pratiche_z90_giornale_stato_upd` | AFTER UPDATE OF stato_id | Registra STATO_CAMBIATO |
| `trg_pratiche_z90_giornale_assegnazione_upd` | AFTER UPDATE OF risorsa/uo | Registra ASSEGNAZIONE_CAMBIATA |
| `trg_pratiche_z90_giornale_priorita_upd` | AFTER UPDATE OF priorita_id | Registra PRIORITA_CAMBIATA |

#### Su `pratiche.flussi`

| Trigger | Evento | Funzione |
| --- | --- | --- |
| `trg_flussi_a10_guard_prerequisiti_ins` | BEFORE INSERT | Valida prerequisiti (guard) |
| `trg_flussi_z90_giornale_ins` | AFTER INSERT | Registra FLUSSO_CREATO |
| `trg_flussi_z90_giornale_stato_upd` | AFTER UPDATE OF stato_id | Registra FLUSSO_STATO_CAMBIATO |
| `trg_flussi_z90_generazione_upd` | AFTER UPDATE (COMPLETATO) | Genera pratiche da regole auto |

#### Su `pratiche.sospensioni`

| Trigger | Evento | Funzione |
| --- | --- | --- |
| `trg_sospensioni_z90_after_ins` | AFTER INSERT | Propaga sospensione ai flussi IN_CORSO (se flusso_id IS NULL), registra nel giornale |
| `trg_sospensioni_z90_after_upd` | AFTER UPDATE OF data_fine | Ripristina stati flussi sospesi, registra riattivazione nel giornale |

#### Su `pratiche.flussi` (calcoli tempo)

| Trigger | Evento | Funzione |
| --- | --- | --- |
| `trg_flussi_z91_calcoli_tempo_upd` | AFTER UPDATE (COMPLETATO) | Crea/aggiorna record in `calcoli_tempo` se esiste formula tempo applicabile |

#### Su `pratiche.pratiche` e `pratiche.flussi` (macchina a stati)

| Trigger | Evento | Funzione |
| --- | --- | --- |
| `trg_pratiche_a10_valida_transizione` | BEFORE UPDATE OF stato_id | Verifica transizione ammessa in `config.transizioni_stati_pratiche` |
| `trg_flussi_a10_valida_transizione` | BEFORE UPDATE OF stato_id | Verifica transizione ammessa in `config.transizioni_stati_flussi` |

#### Su note e allegati

Un trigger AFTER INSERT ciascuno per registrare NOTA_AGGIUNTA e ALLEGATO_AGGIUNTO nel giornale (4 trigger in totale).

---

## Funzioni DB

| Funzione | Tipo | Scopo |
| --- | --- | --- |
| `fn_check_prerequisiti_flusso` | check (pura) | Verifica prerequisiti, ritorna tabella con flag `soddisfatto` |
| `fn_guard_prerequisiti_flusso` | guard (fail-fast) | RAISE se prerequisiti non soddisfatti |
| `fn_genera_pratica_da_flusso` | operativa | Genera nuova pratica da flusso completato secondo regola |
| `fn_calcola_giorni_sospensione` | calcolo (pura) | Calcola i giorni di sospensione in un intervallo per una pratica |
| `fn_valida_transizione_pratica` | guard (fail-fast) | RAISE se la transizione di stato non e' nella tabella config |
| `fn_valida_transizione_flusso` | guard (fail-fast) | RAISE se la transizione di stato non e' nella tabella config |

---

## Backend Django

### Architettura a strati

```text
API View (apps/pratiche/api/views.py)
    |
    v
Service (apps/pratiche/services/pratiche_service.py)
    |                  (apps/pratiche/services/generazione_service.py)
    |
    v
Repository (apps/pratiche/db/pratiche_repository.py)
    |                 (apps/pratiche/db/generazione_repository.py)
    |
    v
PostgreSQL (schema pratiche)
```

### Endpoint API

Tutti gli endpoint richiedono autenticazione JWT e sono sotto `/api/v1/pratiche/`.

#### Pratiche

| Metodo | Endpoint | Descrizione |
| --- | --- | --- |
| GET | `/api/v1/pratiche/` | Lista pratiche con filtri e paginazione |
| POST | `/api/v1/pratiche/` | Crea nuova pratica (stato iniziale: BOZZA) |
| GET | `/api/v1/pratiche/{id}/` | Dettaglio pratica |
| PATCH | `/api/v1/pratiche/{id}/` | Aggiorna campi modificabili |
| POST | `/api/v1/pratiche/{id}/stato/` | Cambio stato pratica |
| POST | `/api/v1/pratiche/{id}/assegnazione/` | Assegna risorsa umana / unita' organizzativa |
| GET | `/api/v1/pratiche/{id}/giornale/` | Giornale di bordo paginato |
| POST | `/api/v1/pratiche/{id}/sospendi/` | Sospende pratica (motivo obbligatorio) |
| POST | `/api/v1/pratiche/{id}/riattiva/` | Riattiva pratica sospesa |
| GET | `/api/v1/pratiche/{id}/sospensioni/` | Lista sospensioni pratica |
| GET | `/api/v1/pratiche/{id}/calcoli-tempo/` | Calcoli tempo pratica |

#### Flussi

| Metodo | Endpoint | Descrizione |
| --- | --- | --- |
| GET | `/api/v1/pratiche/{id}/flussi/` | Lista flussi della pratica |
| POST | `/api/v1/pratiche/{id}/flussi/` | Crea nuovo flusso |
| GET | `/api/v1/pratiche/{id}/flussi/{fid}/` | Dettaglio flusso |
| POST | `/api/v1/pratiche/{id}/flussi/{fid}/stato/` | Cambio stato flusso (con esito se COMPLETATO) |
| GET | `/api/v1/pratiche/{id}/flussi/{fid}/prerequisiti/` | Prerequisiti del flusso |
| GET | `/api/v1/pratiche/{id}/flussi/{fid}/canali/` | Canali abilitati per il flusso |
| POST | `/api/v1/pratiche/{id}/flussi/{fid}/sospendi/` | Sospende singolo flusso |
| POST | `/api/v1/pratiche/{id}/flussi/{fid}/riattiva/` | Riattiva singolo flusso |

#### Generazione

| Metodo | Endpoint | Descrizione |
| --- | --- | --- |
| GET | `/api/v1/pratiche/{id}/flussi/{fid}/regole-generazione/` | Regole di generazione applicabili |
| POST | `/api/v1/pratiche/{id}/flussi/{fid}/genera/` | Genera pratica manualmente da regola |
| GET | `/api/v1/pratiche/{id}/flussi/{fid}/pratiche-generate/` | Pratiche generate dal flusso |

### Service come API interna cross-dominio

Il `pratiche_service` e' progettato come **API interna** che altri domini importano e usano:

```python
from apps.pratiche.services import pratiche_service

# Da un service vendite/anagrafiche/acquisti
pratica_id = pratiche_service.crea_pratica(
    emittente_fiscale_id=32,
    tipo_prestazione_id=1,
    soggetto_id="uuid-...",
    priorita_id=2,
    descrizione="Onboarding cliente Mario Rossi",
)
```

### File coinvolti

| Layer | File |
| --- | --- |
| Types | `apps/pratiche/types.py` |
| Repository | `apps/pratiche/db/pratiche_repository.py` |
| Repository | `apps/pratiche/db/generazione_repository.py` |
| Service | `apps/pratiche/services/pratiche_service.py` |
| Service | `apps/pratiche/services/generazione_service.py` |
| Handler | `apps/pratiche/services/handler_registry.py` |
| API | `apps/pratiche/api/views.py` |
| URL | `apps/pratiche/api/urls_v1.py` |
| Test | `apps/pratiche/tests/services/test_pratiche_service.py` |
| Test | `apps/pratiche/tests/services/test_pratiche_service_flussi.py` |
| Test | `apps/pratiche/tests/services/test_generazione_service.py` |
| Test | `apps/pratiche/tests/services/test_handler_registry.py` |
| Test | `apps/pratiche/tests/api/test_pratiche_api.py` |
| Test | `apps/pratiche/tests/api/test_flussi_api.py` |
| Test | `apps/pratiche/tests/services/test_sospensioni_service.py` |
| Test | `apps/pratiche/tests/api/test_sospensioni_api.py` |
| Smoke | `scripts/smoke-test-sospensioni.sh` |

---

## Integrazione cross-dominio

### Il giornale come infrastruttura trasversale

Il modulo pratiche non e' solo un workflow engine autonomo: e' l'anello infrastrutturale che gli altri domini dell'ERP usano per tracciare i propri processi.

**Principio**: ogni evento significativo di dominio (nuovo cliente, nuovo ordine, modifica contratto) transita dal giornale di bordo attraverso la creazione/aggiornamento di una pratica. Il giornale cattura automaticamente il ciclo di vita via trigger DB.

| Evento dominio | tipo_prestazione | Cosa succede |
| --- | --- | --- |
| Nuovo cliente creato | ONBOARDING_CLIENTE | Pratica creata con soggetto_id, flussi configurati |
| Nuovo ordine vendita | GESTIONE_ORDINE | Pratica creata con meta referencing l'ordine |
| Modifica contratto | REVISIONE_CONTRATTO | Pratica creata, flussi di approvazione/notifica |
| Reclamo ricevuto | RECLAMO | Pratica creata da canale WEB_CLIENTI |

### Esempio completo: onboarding cliente

Flusso end-to-end di come un dominio esterno usa il motore pratiche:

```text
1. vendite_service riceve "nuovo cliente"
       |
       v
2. pratiche_service.crea_pratica(
       tipo_prestazione_id = ONBOARDING_CLIENTE,
       soggetto_id = "uuid-cliente",
       priorita_id = NORMALE,
       emittente_fiscale_id = 32
   )
       |  --> DB trigger: giornale registra PRATICA_CREATA
       v
3. pratiche_service.crea_flusso(
       pratica_id = 123,
       template_flusso_id = VERIFICA_DATI   [sequenza 0]
   )
       |  --> DB trigger: guard prerequisiti (nessuno per primo flusso)
       |  --> DB trigger: giornale registra FLUSSO_CREATO
       v
4. Operatore lavora il flusso, poi:
   pratiche_service.completa_flusso(flusso_id=456, esito="POSITIVO")
       |  --> DB trigger: giornale registra FLUSSO_STATO_CAMBIATO
       |  --> DB trigger: cerca regole_generazione con auto=true → nessuna
       v
5. pratiche_service.crea_flusso(
       pratica_id = 123,
       template_flusso_id = PRIMO_CONTATTO   [sequenza 10]
   )
       |  --> DB trigger: guard verifica prerequisito VERIFICA_DATI → soddisfatto
       |  --> DB trigger: giornale registra FLUSSO_CREATO
       v
6. Completamento PRIMO_CONTATTO con esito POSITIVO
       |  --> regola_generazione auto=true: tipo_dest=SOPRALLUOGO
       |  --> fn_genera_pratica_da_flusso() crea nuova pratica collegata
       |  --> giornale registra PRATICA_GENERATA
```

### Cosa NON transita dal giornale pratiche

Le operazioni **massive/batch** con struttura propria di esecuzione:

* `vendite.fatturazione_pipeline` — ha `fatturazione_lotti_task_runs` e log dedicati
* Future pipeline batch — avranno la propria infrastruttura di tracking

La distinzione e':

* **Processo unitario** (un cliente, un ordine, un reclamo) --> **pratica + giornale**
* **Processo massivo** (lotto fatturazione, import massivo) --> **pipeline dedicata**

---

## Multi-company

Il campo `emittente_fiscale_id` su `pratiche.pratiche` garantisce la segregazione dati. Le query filtrano sempre per emittente. Il catalogo (tipi_prestazione, template_flussi, handler_flussi) e' condiviso.

---

## Come estendere a un nuovo dominio

Per integrare un nuovo dominio (es. gestione reclami) con il motore pratiche:

### 1. Configurazione DB (catalogo)

Inserire seed data nelle tabelle catalogo:

```sql
-- Tipo prestazione
INSERT INTO pratiche.tipi_prestazione (codice, descrizione, categoria, flussi_vincolanti)
VALUES ('RECLAMO', 'Gestione reclamo cliente', 'COMMERCIALE', true);

-- Template flussi (3 step con sequenza)
INSERT INTO pratiche.template_flussi
  (tipo_prestazione_id, codice, descrizione, sequenza, obbligatorio, direzione)
VALUES
  (:tp_id, 'PRESA_CARICO',   'Presa in carico reclamo',  0, true, 'ENTRATA'),
  (:tp_id, 'ANALISI',        'Analisi del problema',     10, true, 'INTERNA'),
  (:tp_id, 'RISPOSTA',       'Risposta al cliente',      20, true, 'USCITA');

-- Prerequisiti: ANALISI richiede PRESA_CARICO, RISPOSTA richiede ANALISI
INSERT INTO pratiche.template_flussi_prerequisiti
  (template_flusso_id, prerequisito_flusso_id, obbligatorio)
VALUES
  (:analisi_id, :presa_carico_id, true),
  (:risposta_id, :analisi_id, true);

-- Canali: RISPOSTA visibile su WEB_CLIENTI
INSERT INTO pratiche.template_flussi_canali (template_flusso_id, canale_id)
VALUES (:risposta_id, :canale_web_clienti_id);
```

### 2. Backend Django (opzionale: handler automatizzato)

Se uno step e' automatizzato, registrare l'handler:

```sql
-- Handler DB
INSERT INTO pratiche.handler_flussi (handler_key, descrizione)
VALUES ('INVIO_RISPOSTA_RECLAMO', 'Invio email risposta reclamo');
```

```python
# apps/reclami/handlers/risposta_handler.py
class InvioRispostaReclamoHandler:
    def execute(self, flusso_id, pratica_id, meta, handler_params):
        # handler_params contiene la configurazione statica dal template
        # meta contiene i dati specifici dell'istanza flusso
        return {"email_inviata": True}

# apps/pratiche/services/handler_registry.py
HANDLER_MAP["INVIO_RISPOSTA_RECLAMO"] = InvioRispostaReclamoHandler
```

### 3. Integrazione dal dominio

```python
# apps/reclami/services/reclami_service.py
from apps.pratiche.services import pratiche_service

def gestisci_reclamo(emittente_id, cliente_uuid, descrizione):
    pratica_id = pratiche_service.crea_pratica(
        emittente_fiscale_id=emittente_id,
        tipo_prestazione_id=RECLAMO_ID,
        soggetto_id=cliente_uuid,
        priorita_id=ALTA_ID,
        descrizione=descrizione,
        meta={"canale": "web", "riferimento": "ORD-2026-001"},
    )
    # I trigger DB registrano PRATICA_CREATA nel giornale.
    # I flussi vengono creati dall'operatore o automaticamente.
    return pratica_id
```

Non serve toccare il nucleo pratiche: tutto avviene per configurazione.

---

## Estensioni future (tabelle ext_*)

Tabelle specifiche per tipo di flusso, da implementare progressivamente. Ogni estensione avra' FK verso `pratiche.flussi(id)` e vivra' autonomamente:

* `pratiche.ext_appuntamento` — fascia oraria, data/ora, esito, risorsa assegnata
* `pratiche.ext_preventivo` — importi, voci, stato accettazione
* `pratiche.ext_sopralluogo` — dati tecnici, foto, misurazioni
* `pratiche.ext_comunicazione` — canale, destinatario, contenuto, conferma ricezione
* `pratiche.ext_spedizione` — corriere, tracking, stato consegna

---

## Evoluzioni pianificate

Lo stato di implementazione delle funzionalita' avanzate:

| Componente | Scopo | Stato |
| --- | --- | --- |
| Tabella `pratiche.sospensioni` | Periodi di fermo pratica/flusso per calcolo tempi netti | **Implementato** (DB + Backend + API) |
| Tabella `pratiche.formule_tempo` | Soglie warning/critico per semafori temporali | **Implementato** (DB) |
| Tabella `pratiche.calcoli_tempo` | Calcolo tempi netti da/a (escludendo sospensioni) | **Implementato** (DB + Backend + API) |
| Sospensione automatica flusso | Riattivazione con data prevista + job pgAgent | **Implementato** (DB + job pgAgent) |
| Macchina a stati rigida | Transizioni ammesse validate da trigger DB | **Implementato** (DB trigger + tabelle config) |
| Agenda attivita' | Vista operativa per operatore/reparto/direzione | Analisi |

Le funzionalita' implementate appartengono all'**anello infrastrutturale** (Anello 2) e si appoggiano sul nucleo senza modificarlo.

---

## Note finali

Questa guida e' il prerequisito per comprendere:

* L'integrazione dei moduli dominio (vendite, anagrafiche) con il motore pratiche
* La configurazione di nuovi tipi prestazione e template flussi
* L'implementazione di handler Django per flussi automatizzati

Le altre guide assumono come gia' compreso il modello pratica/flusso/giornale descritto qui.

---

{% include-markdown "signature-core.md" %}
