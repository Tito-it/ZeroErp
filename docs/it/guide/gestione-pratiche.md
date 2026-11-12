# Guida — Gestione Pratiche e Workflow

> **Ultimo aggiornamento**: 12 novembre 2026
>
> **Destinatari**: sviluppatori database, backend e analisti funzionali
>
> **Vedi anche** — tabelle di configurazione (schema `config`):
>
> * [config.stati_pratiche](/dbzero/config/tabelle/stati_pratiche) — gli stati della pratica (BOZZA, APERTA, SOSPESA, CHIUSA, ANNULLATA)
> * [config.stati_flussi_pratiche](/dbzero/config/tabelle/stati_flussi_pratiche) — gli stati del flusso (DA_ESEGUIRE, IN_CORSO, COMPLETATO, SOSPESO, ANNULLATO, ERRORE)
> * [config.priorita_pratiche](/dbzero/config/tabelle/priorita_pratiche) — i livelli di priorità, con ordinamento
> * [config.tipi_nota](/dbzero/config/tabelle/tipi_nota) — le tipologie di nota
> * [config.tipi_allegato](/dbzero/config/tabelle/tipi_allegato) — le tipologie di allegato
> * [config.canali_pratiche](/dbzero/config/tabelle/canali_pratiche) — i canali di visibilità esterna
>
> **Vedi anche** — tabelle del motore (schema `pratiche`):
>
> * [pratiche.tipi_prestazione](/dbzero/pratiche/tabelle/tipi_prestazione) — il catalogo dei tipi di pratica
> * [pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi) — la configurazione del workflow
> * [pratiche.template_flussi_prerequisiti](/dbzero/pratiche/tabelle/template_flussi_prerequisiti) — il grafo delle dipendenze tra step
> * [pratiche.template_flussi_canali](/dbzero/pratiche/tabelle/template_flussi_canali) — M:N tra template flussi e canali
> * [pratiche.template_flussi_handler_eventi](/dbzero/pratiche/tabelle/template_flussi_handler_eventi) — gli handler agganciati agli eventi del flusso
> * [pratiche.template_flussi_avanzamento_proiezione](/dbzero/pratiche/tabelle/template_flussi_avanzamento_proiezione) — l'avanzamento su esito proiettato
> * [pratiche.workflow_definizioni](/dbzero/pratiche/tabelle/workflow_definizioni) — le definizioni versionate del workflow
> * [pratiche.handler_flussi](/dbzero/pratiche/tabelle/handler_flussi) — le chiavi di dispatch verso gli handler Django
> * [pratiche.azioni_ui](/dbzero/pratiche/tabelle/azioni_ui) — le azioni offerte all'operatore
> * [pratiche.competenze_flussi](/dbzero/pratiche/tabelle/competenze_flussi) — quali competenze servono per un flusso
> * [pratiche.regole_generazione](/dbzero/pratiche/tabelle/regole_generazione) — la generazione cross-pratica
> * [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) — l'istanza operativa (testata)
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi) — lo step operativo (riga)
> * [pratiche.pratiche_sorgenti](/dbzero/pratiche/tabelle/pratiche_sorgenti) — l'aggancio al documento di origine
> * [pratiche.note_pratiche](/dbzero/pratiche/tabelle/note_pratiche) · [pratiche.note_flussi](/dbzero/pratiche/tabelle/note_flussi) — note su testata e flusso
> * [pratiche.allegati_pratiche](/dbzero/pratiche/tabelle/allegati_pratiche) · [pratiche.allegati_flussi](/dbzero/pratiche/tabelle/allegati_flussi) — documenti su testata e flusso
> * [pratiche.giornale](/dbzero/pratiche/tabelle/giornale) — l'audit trail immutabile
> * [pratiche.sospensioni](/dbzero/pratiche/tabelle/sospensioni) — i periodi di fermo di pratica o flusso
> * [pratiche.formule_tempo](/dbzero/pratiche/tabelle/formule_tempo) — i tempi attesi tra coppie di flussi
> * [pratiche.calcoli_tempo](/dbzero/pratiche/tabelle/calcoli_tempo) — i tempi netti, calcolati dai trigger
> * [pratiche.reconcile_errori](/dbzero/pratiche/tabelle/reconcile_errori) — gli errori di riconciliazione
>
> **Vedi anche** — funzioni e trigger DB:
>
> * [pratiche.fn_check_prerequisiti_flusso](/dbzero/pratiche/funzioni/fn_check_prerequisiti_flusso) — verifica i prerequisiti, senza sollevare
> * [pratiche.fn_guard_prerequisiti_flusso](/dbzero/pratiche/funzioni/fn_guard_prerequisiti_flusso) — li verifica e si ferma se non sono soddisfatti
> * [pratiche.fn_genera_pratica_da_flusso](/dbzero/pratiche/funzioni/fn_genera_pratica_da_flusso) — la generazione cross-pratica
> * [pratiche.fn_calcola_tempo_netto_da_a](/dbzero/pratiche/funzioni/fn_calcola_tempo_netto_da_a) · [pratiche.fn_valuta_tempo_esecuzione_da_a](/dbzero/pratiche/funzioni/fn_valuta_tempo_esecuzione_da_a) — i tempi netti e il semaforo
> * [pratiche.trgfn_pratiche_giornale_ins](/dbzero/pratiche/funzioni/trgfn_pratiche_giornale_ins) — il giornale, alimentato dai trigger (una funzione per evento)
>
> **Vedi anche** — API e service backend:
>
> * [API dettaglio pratica](/backend/pratiche/manual/api_pratica_detail) · [API giornale](/backend/pratiche/manual/api_pratica_giornale) · [API stato flusso](/backend/pratiche/manual/api_flusso_stato) · [API genera pratica](/backend/pratiche/manual/api_genera_pratica)
>
> **Vedi anche** — guide correlate:
>
> * [Configurazione delle pratiche](/guide/gestione-pratiche-configurazione) — l'appendice: cataloghi, stati, azioni
> * [Risorse umane e accessi](/guide/risorse-umane-e-accessi) — le risorse umane e le competenze usate nelle assegnazioni
> * [Documenti e sorgenti](/guide/sorgente-polimorfa) — l'aggancio di una pratica al documento di origine
> * [Tracciamento Processi e Job](/guide/analisi-tracciamento-processi-e-job) — dove finiscono i job e le pipeline
> * [Mappa Concentrica](/mappa-concentrica) — dove sta questo motore rispetto agli altri anelli

---

## Introduzione

In Zero ERP **tutto e' una pratica**. Ogni operazione — dall'onboarding di un cliente alla gestione di un reclamo, dalla revisione di un contratto alla lavorazione di un ordine — transita dal motore pratiche.

Il sistema opera su due modalita':

* **Con flussi vincolanti**: controllo sequenza e prerequisiti attivi, workflow completo con handler automatizzati
* **Senza flussi vincolanti**: giornale di bordo con tracciabilita' totale, senza vincoli di sequenza

**Cosa troverai in questa guida:**

* L'architettura del modello pratica/flusso e la sua posizione nel modello concentrico
* Come funzionano i tipi prestazione, i template flussi e i prerequisiti
* La macchina a stati rigida e il ciclo di vita di pratiche e flussi
* Il giornale di bordo immutabile e come viene alimentato
* Le sospensioni: come congelare e riattivare pratiche e flussi, con esempi operativi
* Le formule tempo e i calcoli tempo: misurazione automatica delle durate e soglie di allerta
* La generazione cross-pratica e il registry handler Django
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

Il catalogo e' **condiviso** tra tutti gli emittenti fiscali. La segregazione multi-company avviene sulla tabella `pratiche.pratiche` tramite `emittente_fiscale_id`.

> Un tipo prestazione e' vincolante o libero non tramite un flag, ma tramite la configurazione dei prerequisiti. Se non esistono righe in `template_flussi_prerequisiti` per un tipo prestazione, i flussi si creano liberamente in qualsiasi ordine. La presenza di prerequisiti obbligatori e' il meccanismo che rende il workflow sequenziale.

### 2. I template flussi: la configurazione del workflow

Ogni tipo prestazione ha un insieme di **template flussi** che definiscono gli step operativi previsti:

* **sequenza**: ordine logico (0, 10, 20...). Il controllo effettivo e' sui prerequisiti espliciti
* **direzione**: caratterizza il flusso rispetto all'esterno (ENTRATA, USCITA, INTERNA)
* **handler_id**: NULL = step manuale, NOT NULL = step automatizzato (Django dispatch)
* **handler_params**: JSONB con parametri operativi per l'handler (es. invio_sms_conferma)
* **obbligatorio**: se il flusso e' richiesto per completare la pratica
* **modalita_esito**: come si registra l'esito dello step — `MANUALE` (default: l'operatore avvia, poi sceglie l'esito a mano), `AUTOMATICO` (lo step si avvia e si chiude da solo con un esito predefinito, senza scelta umana), `CONTESTUALE` (l'operatore avvia e conferma l'esito in un'unica azione, con un valore gia' pre-impostato e modificabile)
* **esito_default**: l'esito predefinito applicato (AUTOMATICO) o pre-selezionato (CONTESTUALE). Obbligatorio quando `modalita_esito` non e' `MANUALE`. `AUTOMATICO` e' ammesso **solo** per gli step a direzione INTERNA: un esito automatico su uno step ENTRATA/USCITA equivarrebbe a fabbricare la risposta di una controparte esterna

> 📖 **Come si configura nel concreto** (creare uno step, scegliere la modalità esito,
> automazioni, esempi): [Pratiche — Configurazione e opzioni del workflow](gestione-pratiche-configurazione.md).
> Appendice operativa che cresce con le funzionalità di configurazione.

### 3. I prerequisiti: il grafo del workflow

La tabella [`template_flussi_prerequisiti`](/dbzero/pratiche/tabelle/template_flussi_prerequisiti) definisce le dipendenze tra flussi:

* Supporta rami **paralleli**, **convergenze** e flussi **opzionali**
* **obbligatorio**: `true` = bloccante, `false` = consigliato (warning senza blocco)
* CHECK: nessun self-reference (`template_flusso_id <> prerequisito_flusso_id`)

La funzione DB [`fn_check_prerequisiti_flusso()`](/dbzero/pratiche/funzioni/fn_check_prerequisiti_flusso) verifica se un flusso puo' essere avviato. La guard [`fn_guard_prerequisiti_flusso()`](/dbzero/pratiche/funzioni/fn_guard_prerequisiti_flusso) blocca l'INSERT se i prerequisiti non sono soddisfatti.

### 4. La pratica: l'istanza operativa

Una **pratica** e' l'istanza concreta, la testata. Contiene:

| Campo                    | Tipo    | Note                                                       |
| ------------------------ | ------- | ---------------------------------------------------------- |
| `emittente_fiscale_id`   | BIGINT  | Segregazione multi-company                                 |
| `soggetto_id`            | UUID    | FK a `anagrafiche.soggetti`                                |
| `stato_id`               | INTEGER | FK a `config.stati_pratiche`                               |
| `priorita_id`            | INTEGER | FK a `config.priorita_pratiche`                            |
| `tipo_prestazione_id`    | INTEGER | FK a `pratiche.tipi_prestazione`                           |
| `risorsa_umana_id`       | BIGINT  | Operatore assegnato                                        |
| `unita_organizzativa_id` | INTEGER | Reparto assegnato                                          |
| `pratica_padre_id`       | BIGINT  | Per sotto-pratiche (self-reference)                        |
| `flusso_origine_id`      | BIGINT  | Tracciabilita' cross-pratica                               |
| `canale_origine_id`      | INTEGER | Sorgente esterna, informativo (NULL = creata internamente) |
| `codice`                 | TEXT    | Generato da trigger                                        |
| `descrizione`            | TEXT    | Descrizione libera                                         |
| `data_scadenza`          | DATE    | Scadenza prevista                                          |

### 5. Il flusso: lo step operativo

Un **flusso** e' una fase operativa dentro una pratica. Contiene:

* `template_flusso_id`: NULL per flussi aggiunti manualmente su pratiche libere
* `stato_id`: FK a `config.stati_flussi_pratiche`
* `sequenza`: ordine esecuzione nel workflow
* `esito`: POSITIVO, NEGATIVO, PARZIALE, NON_APPLICABILE (impostato al completamento)
* `note_esito`: note libere sull'esito
* `meta`: JSONB con dati estensibili specifici dell'istanza (default `{}`). Usato dagli handler Django per ricevere informazioni di contesto (vedi [Contratto handler](#contratto-handler))
* `data_fine`: timestamp di completamento del flusso (impostato dal trigger al passaggio a COMPLETATO). Usato dai calcoli tempo per determinare la durata
* `flusso_padre_id`: per albero di sotto-flussi (self-reference)

### Canali e visibilita' esterna

La visibilita' di un flusso verso l'esterno si configura interamente sul template, non sull'istanza pratica:

* **`template_flussi.direzione`** (ENTRATA, USCITA, INTERNA): descrive il verso del flusso rispetto al canale
* **`template_flussi_canali`** (M:N): associa i canali abilitati a ciascun template flusso. Un flusso senza associazioni e' de facto interno
* **`canale_origine_id`** sulla pratica: campo informativo che registra da quale ingresso e' arrivata la richiesta (NULL = creata internamente). Usato per reportistica, non come vincolo operativo

---

## Macchina a stati

Le transizioni di stato di pratiche e flussi sono governate da due tabelle di configurazione:

* [`config.transizioni_stati_pratiche`](/dbzero/config/tabelle/transizioni_stati_pratiche) — definisce le coppie (stato_da, stato_a) ammesse per le pratiche
* [`config.transizioni_stati_flussi_pratiche`](/dbzero/config/tabelle/transizioni_stati_flussi_pratiche) — definisce le coppie (stato_da, stato_a) ammesse per i flussi

Un trigger BEFORE UPDATE su `pratiche.pratiche` e su `pratiche.flussi` verifica che la transizione richiesta sia presente nella tabella di configurazione. Se non lo e', il trigger rifiuta l'operazione con un errore esplicito (`PRATICHE_TRANSIZIONE_NON_AMMESSA` o `FLUSSI_TRANSIZIONE_NON_AMMESSA`).

**Transizioni ammesse per le pratiche:**

```text
BOZZA       → APERTA, ANNULLATA
APERTA      → SOSPESA, CHIUSA, ANNULLATA
SOSPESA     → APERTA
```

**Transizioni ammesse per i flussi:**

```text
DA_ESEGUIRE → IN_CORSO, ANNULLATO, SOSPESO
IN_CORSO    → COMPLETATO, SOSPESO, ERRORE
SOSPESO     → IN_CORSO, DA_ESEGUIRE
ERRORE      → IN_CORSO (retry), ANNULLATO (abbandono)
```

La transizione `DA_ESEGUIRE → SOSPESO` e' necessaria per la propagazione: quando una pratica viene sospesa, il trigger mette in SOSPESO anche i flussi DA_ESEGUIRE (oltre a quelli IN_CORSO). La transizione `SOSPESO → DA_ESEGUIRE` e' il percorso inverso: alla riattivazione, i flussi che erano DA_ESEGUIRE vengono ripristinati al loro stato originale.

> **ERRORE** e' prodotto esclusivamente da handler automatici (mai da operatori). Non blocca la pratica: gli altri flussi continuano normalmente. La risoluzione richiede intervento esplicito: retry (→ IN_CORSO) o abbandono (→ ANNULLATO).

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

> **Chiusura guidata dal workflow.** La transizione a **CHIUSA** non e' un'azione
> manuale dell'operatore: la pratica si auto-chiude (trigger
> `trgfn_flussi_autochiusura_pratica`) al completamento dei flussi. Per i tipi
> prestazione che hanno un **flusso di chiusura** dedicato, la chiusura scatta al
> completamento di quel flusso; altrimenti scatta quando non restano flussi
> obbligatori bloccanti. Il flag che marca il flusso di chiusura e'
> [`template_flussi.chiude_pratica`](/dbzero/pratiche/tabelle/template_flussi)
> (al massimo un template di chiusura per tipo prestazione — indice unico
> parziale `uq_template_flussi_chiusura`), configurabile dal **pannello di
> configurazione** (`pratiche.template_flussi`).

### Flusso

```text
DA_ESEGUIRE --> IN_CORSO --> COMPLETATO (con esito)
    |   ^          |
    |   |          +--> SOSPESO --> IN_CORSO
    |   |          |        |
    |   +----------+--------+  (riattivazione ripristina stato originale)
    |              |
    |              +--> ERRORE --> IN_CORSO  (retry)
    |                        |
    |                        +--> ANNULLATO (abbandono)
    |
    +--> SOSPESO (propagazione da pratica)
    |
    +--> ANNULLATO
```

* Un flusso nasce in stato **DA_ESEGUIRE**
* Viene **avviato** (IN_CORSO), poi **completato** con esito obbligatorio
* Da IN_CORSO puo' essere **sospeso** (SOSPESO) e poi ripreso (torna IN_CORSO)
* Da DA_ESEGUIRE puo' passare a **SOSPESO** per propagazione da sospensione pratica
* Da SOSPESO puo' tornare a **DA_ESEGUIRE** (se era DA_ESEGUIRE prima della sospensione) o a **IN_CORSO** (se era IN_CORSO). Il trigger di riattivazione consulta il giornale per ripristinare lo stato originale
* Da IN_CORSO puo' andare in **ERRORE** (errore tecnico/handler). ERRORE non blocca la pratica: gli altri flussi continuano. Da ERRORE si puo' fare **retry** (→ IN_CORSO) o **abbandonare** il flusso (→ ANNULLATO)
* Da DA_ESEGUIRE puo' essere **ANNULLATO** direttamente
* Al completamento con `auto = true`, il trigger DB puo' generare automaticamente nuove pratiche

> **Modalita' di registrazione dell'esito** (configurate sul template, vedi §2). Per
> impostazione predefinita (`MANUALE`) avvio ed esito restano due momenti distinti. Un
> template `AUTOMATICO` collassa i due momenti senza intervento umano (lo step si chiude
> da solo con `esito_default`), ammesso **solo** per gli step INTERNA. Un template
> `CONTESTUALE` li collassa mantenendo la conferma umana dell'esito (un solo Salva, valore
> pre-impostato), senza vincolo di direzione. In tutti i casi l'esito al COMPLETATO resta
> **obbligatorio**: la rete di sicurezza `trgfn_flussi_guard_esito_completato` e'
> invariata, e il percorso resta `DA_ESEGUIRE -> IN_CORSO -> COMPLETATO` (nessuna
> transizione diretta `DA_ESEGUIRE -> COMPLETATO`). La logica applicativa (azione unica
> "Avvia e completa") arriva col lavoro BE/FE; il DB fornisce le colonne e le invarianti.

<!-- -->

> **Nota**: la macchina a stati e' implementata come **rigida** nel DB tramite la tabella `config.transizioni_stati_pratiche` / `config.transizioni_stati_flussi_pratiche` e trigger di validazione. Le transizioni non ammesse vengono rifiutate dal DB. La sospensione temporanea (con data di riattivazione e job pgAgent) e' implementata: il flusso SOSPESO torna al suo stato precedente alla riattivazione manuale o automatica.

---

## Il giornale di bordo

Il giornale ([`pratiche.giornale`](/dbzero/pratiche/tabelle/giornale)) e' un log **immutabile** alimentato automaticamente via trigger. Non si modifica, non si cancella.

Ogni riga registra:

* **azione**: uno degli 11 eventi (PRATICA_CREATA, STATO_CAMBIATO, ASSEGNAZIONE_CAMBIATA, PRIORITA_CAMBIATA, FLUSSO_CREATO, FLUSSO_STATO_CAMBIATO, NOTA_AGGIUNTA, ALLEGATO_AGGIUNTO, PRATICA_GENERATA, SOSPENSIONE_REGISTRATA, SOSPENSIONE_CHIUSA)
* **origine**: SISTEMA, UTENTE, HANDLER, SCHEDULER
* **dettaglio**: JSONB con valori precedenti/nuovi per ricostruzione completa
* **tx_id**: correlazione con la transazione per tracciabilita' cross-tabella

Django **non deve loggare**: il DB lo fa da solo tramite 12 trigger functions dedicate.

### Approccio generico delle azioni

Le azioni STATO_CAMBIATO e FLUSSO_STATO_CAMBIATO sono **generiche**: coprono tutte le transizioni di stato senza moltiplicare i tipi azione. Che la pratica passi da APERTA a SOSPESA, da SOSPESA a APERTA, o da APERTA ad ANNULLATA, l'azione registrata e' sempre `STATO_CAMBIATO`. Lo stesso vale per i flussi.

I dettagli specifici (stato precedente, stato nuovo, esito se applicabile) sono nel campo JSONB
`dettaglio` ([esempio](#area-tecnica-esempi)).

Questo design mantiene il CHECK sulla colonna `azione` stabile nel tempo: non serve aggiungere nuovi valori per nuove transizioni. La ricostruzione di cosa e' successo avviene sempre leggendo il `dettaglio`.

---

## Sospensioni

Una **sospensione** rappresenta un periodo in cui una pratica o un flusso sono fermi per cause esterne (attesa documenti, attesa risposta cliente, attesa tecnico). Durante la sospensione il conteggio dei tempi si blocca.

| Campo                         | Significato                                                                      |
| ----------------------------- | -------------------------------------------------------------------------------- |
| `pratica_id`                  | Pratica a cui si riferisce la sospensione                                        |
| `flusso_id`                   | NULL = sospensione sull'intera pratica, NOT NULL = sospensione su singolo flusso |
| `data_inizio`                 | Inizio del fermo (impostato automaticamente a NOW())                             |
| `data_fine`                   | Fine del fermo (NULL = sospensione attiva, impostata a NOW() alla riattivazione) |
| `data_riattivazione_prevista` | Data oltre la quale il job pgAgent riattiva automaticamente                      |
| `motivo`                      | Motivazione obbligatoria (testo libero)                                          |

### Sospensione pratica vs sospensione flusso

* **Sospensione pratica** (`flusso_id IS NULL`): blocca tutto. Il trigger DB cambia lo stato di tutti i flussi IN_CORSO e DA_ESEGUIRE a SOSPESO. E' l'equivalente del "metti in pausa" su tutta la lavorazione
* **Sospensione flusso** (`flusso_id IS NOT NULL`): blocca solo uno step. Gli altri flussi della stessa pratica continuano normalmente. Utile quando un singolo step e' in attesa ma il resto del lavoro puo' procedere

### Vincolo di unicita'

Una pratica può avere al massimo una sospensione attiva (`data_fine IS NULL`) alla volta, e lo stesso
vale per ogni singolo flusso. Il vincolo sta nel database, con **due indici unici parziali**: uno su
`pratica_id` per le sospensioni dell'intera pratica, uno su `(pratica_id, flusso_id)` per quelle di un
flusso — entrambi limitati a `data_fine IS NULL`. Sono elencati nella scheda della tabella
([pratiche.sospensioni](/dbzero/pratiche/tabelle/sospensioni)).

Non si può sospendere qualcosa che è già sospeso: il database rifiuta l'`INSERT` con una violazione
di unicità.

### Esempio: sospensione pratica con propagazione

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
    Flusso #456 VERIFICA_DATI   stato: SOSPESO    (era IN_CORSO, propagato dal trigger)
    Flusso #457 PRIMO_CONTATTO  stato: SOSPESO    (era IN_CORSO, propagato dal trigger)
    Flusso #458 SOPRALLUOGO     stato: SOSPESO    (era DA_ESEGUIRE, propagato dal trigger)

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
    Flusso #456 VERIFICA_DATI   stato: IN_CORSO     (ripristinato — era IN_CORSO)
    Flusso #457 PRIMO_CONTATTO  stato: IN_CORSO     (ripristinato — era IN_CORSO)
    Flusso #458 SOPRALLUOGO     stato: DA_ESEGUIRE  (ripristinato — era DA_ESEGUIRE)

Sospensione chiusa:
  id: 50, data_fine: 20 marzo 08:00
```

Il giornale registra automaticamente 4 eventi: STATO_CAMBIATO per la pratica e FLUSSO_STATO_CAMBIATO per ciascun flusso toccato, sia alla sospensione che alla riattivazione.

### Esempio: sospensione singolo flusso

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

### Riattivazione automatica via pgAgent

Se la sospensione ha una `data_riattivazione_prevista`, il job pgAgent controlla periodicamente (ogni ora o ogni giorno, a seconda della configurazione) se esistono sospensioni con data prevista scaduta. Se ne trova, le chiude automaticamente e ripristina gli stati.

Questo evita che una pratica resti dimenticata in stato SOSPESA: alla scadenza prevista torna attiva e l'operatore riceve la notifica nella sua agenda.

---

## Formule tempo e calcoli tempo

Questa sezione copre il meccanismo di controllo temporale del workflow: la configurazione delle soglie (formule tempo) e la misurazione automatica delle durate (calcoli tempo).

### Formule tempo: la configurazione

Una **formula tempo** definisce quanto tempo deve passare tra il completamento di un flusso e il completamento di un altro. Ogni formula collega due template flussi appartenenti allo stesso tipo prestazione:

| Campo                   | Significato                                              |
| ----------------------- | -------------------------------------------------------- |
| `template_flusso_da_id` | Lo step che avvia il conteggio (es. PRESA_CARICO)        |
| `template_flusso_a_id`  | Lo step che chiude il conteggio (es. SOPRALLUOGO)        |
| `giorni_esecuzione`     | Tempo massimo concesso in giorni lavorativi              |
| `giorni_warning`        | Soglia warning (es. 80% del tempo — sfondo giallo in UI) |
| `giorni_critico`        | Soglia critica (es. 90% del tempo — sfondo rosso in UI)  |

Le formule sono **configurazione statica**: una volta definite per un tipo prestazione, si applicano automaticamente a tutte le pratiche di quel tipo.

Si possono configurare piu' formule sullo stesso tipo prestazione, anche con sovrapposizioni — ogni coppia da/a e' indipendente:

```text
Formula 1: PRESA_CARICO → ANALISI         ( 5 giorni) — tempo analisi
Formula 2: ANALISI → SOPRALLUOGO          (10 giorni) — tempo programmazione
Formula 3: PRESA_CARICO → SOPRALLUOGO     (15 giorni) — tempo complessivo
Formula 4: SOPRALLUOGO → RISPOSTA_CLIENTE ( 3 giorni) — tempo risposta
```

Ogni formula genera il proprio record in `calcoli_tempo`. La UI puo' mostrare tutti i semafori sulla stessa pratica, evidenziando quale tratto e' in ritardo.

### Calcoli tempo: la misurazione automatica

Quando un flusso viene completato, il trigger DB verifica se esiste una formula tempo in cui quel flusso e' il `template_flusso_da` o il `template_flusso_a`. Se si', crea o aggiorna un record nella tabella `calcoli_tempo`:

| Campo                 | Significato                                                        |
| --------------------- | ------------------------------------------------------------------ |
| `flusso_da_id`        | ID del flusso concreto che ha avviato il conteggio                 |
| `flusso_a_id`         | ID del flusso concreto che ha chiuso il conteggio                  |
| `data_inizio_calcolo` | Data di completamento del flusso_da                                |
| `data_fine_calcolo`   | Data di completamento del flusso_a (NULL se non ancora completato) |
| `giorni_lordi`        | Giorni totali tra inizio e fine                                    |
| `giorni_sospensione`  | Giorni in cui la pratica/flusso era sospesa                        |
| `giorni_netti`        | giorni_lordi - giorni_sospensione                                  |
| `giorni_formula`      | Giorni previsti dalla formula (copiati per storicizzazione)        |
| `sforato`             | `true` se giorni_netti > giorni_formula                            |

**Quali sospensioni contano**: la funzione [`fn_calcola_tempo_netto_da_a`](/dbzero/pratiche/funzioni/fn_calcola_tempo_netto_da_a) sottrae **solo le sospensioni a livello pratica** (`flusso_id IS NULL`) che ricadono nel periodo di calcolo. Le sospensioni su singolo flusso **non** vengono considerate. Questo e' un design intenzionale: i calcoli tempo misurano la durata complessiva della pratica, e solo un fermo totale (sospensione pratica) giustifica l'esclusione dal conteggio.

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

Se il sopralluogo fosse stato completato il 25 marzo invece del 16:

```text
25 marzo: Sopralluogo completato           → calcolo aggiornato:
                                               giorni_lordi: 24
                                               giorni_sospensione: 3
                                               giorni_netti: 21
                                               giorni_formula: 15
                                               sforato: true (21 > 15)
```

---

## Generazione cross-pratica

> Vedi anche: [Analisi Tracciamento Processi e Job](./analisi-tracciamento-processi-e-job) per il monitoraggio dei job di generazione

Le [`regole_generazione`](/dbzero/pratiche/tabelle/regole_generazione) configurano la creazione automatica di nuove pratiche al completamento di un flusso:

| Campo                        | Funzione                                                      |
| ---------------------------- | ------------------------------------------------------------- |
| `template_flusso_origine_id` | Il flusso che scatena la generazione                          |
| `tipo_prestazione_dest_id`   | Il tipo pratica da generare                                   |
| `template_flusso_dest_id`    | Il flusso iniziale della pratica generata (NULL = nessuno)    |
| `esito_richiesto`            | POSITIVO, NEGATIVO, QUALSIASI                                 |
| `auto`                       | Se true, generazione automatica al completamento (trigger DB) |

La funzione [`fn_genera_pratica_da_flusso()`](/dbzero/pratiche/funzioni/fn_genera_pratica_da_flusso) copia emittente, soggetto e priorita' dalla pratica sorgente. La pratica generata ha `flusso_origine_id` per tracciabilita'.

**Esempio concreto** — completamento flusso con generazione automatica:

```text
Regola configurata:
  template_flusso_origine_id = PRIMO_CONTATTO (tipo ONBOARDING_CLIENTE)
  tipo_prestazione_dest_id   = SOPRALLUOGO_TECNICO
  template_flusso_dest_id    = PROGRAMMAZIONE (primo step del tipo destinazione)
  esito_richiesto            = POSITIVO
  auto                       = true

Stato iniziale:
  Pratica #123 (ONBOARDING_CLIENTE, emittente 32, soggetto uuid-mario)
    Flusso #457 PRIMO_CONTATTO  stato: IN_CORSO

L'operatore completa il flusso #457 con esito POSITIVO:
  UPDATE pratiche.flussi SET stato_id = 3, esito = 'POSITIVO' WHERE id = 457;

Il trigger DB (trgfn_flussi_generazione):
  1. Trova la regola con auto=true e esito_richiesto=POSITIVO
  2. Chiama fn_genera_pratica_da_flusso()
  3. Crea:
     Pratica #789 (SOPRALLUOGO_TECNICO, emittente 32, soggetto uuid-mario)
       flusso_origine_id = 457  (tracciabilita' cross-pratica)
       stato: BOZZA
       Flusso #890 PROGRAMMAZIONE  stato: DA_ESEGUIRE

Giornale registra:
  pratica #123: FLUSSO_STATO_CAMBIATO (flusso #457, IN_CORSO → COMPLETATO)
  pratica #789: PRATICA_CREATA
  pratica #789: FLUSSO_CREATO (flusso #890)
```

Se l'esito fosse stato NEGATIVO, la regola non si sarebbe attivata (`esito_richiesto = POSITIVO`).

---

## Avanzamento su esito proiettato (GUIDA)

Alcuni milestone di una pratica non sono decisi dall'operatore *dentro* la pratica, ma
**seguono lo stato di un documento** (un preventivo, un'offerta…). Esempio classico:
l'`APPROVAZIONE_CLIENTE` di una pratica commerciale è "completa" quando il **preventivo
collegato viene accettato** — indipendentemente da *dove* è avvenuta l'accettazione.

Il modello **GUIDA** rende questo avanzamento **automatico e uniforme**: quando il documento
raggiunge un **verdetto** (POSITIVO/NEGATIVO/PARZIALE/NON_APPLICABILE, la "proiezione" del suo
stato), il milestone che lo attende passa a **COMPLETATO** con quel verdetto. Vale su
**qualsiasi** percorso: dall'interno della pratica **oppure** dal drawer standalone del
documento (prima, in quest'ultimo caso, il milestone restava aperto e le due macchine
divergevano).

**Come si configura** (additivo — senza questi due elementi, nessun avanzamento automatico):

1. Sul template step si dichiara **quale tipo documento** attende:
   [`template_flussi.attende_sorgente_tipo_id`](/dbzero/pratiche/tabelle/template_flussi) →
   [`config.sorgenti`](/dbzero/config/tabelle/sorgenti).
2. Si aggiunge un **binding di avanzamento**
   ([`template_flussi_avanzamento_proiezione`](/dbzero/pratiche/tabelle/template_flussi_avanzamento_proiezione)):
   «avanza con esito X» (o «qualsiasi verdetto»).

**Come funziona** (tutto DB-side):

* Un **trigger** sulla tabella-documento
  ([`trgfn_documento_reconcile_proiezione`](/dbzero/pratiche/funzioni/trgfn_documento_reconcile_proiezione))
  scatta ad ogni cambio-stato e chiama il motore
  [`fn_reconcile_sorgente`](/dbzero/pratiche/funzioni/fn_reconcile_sorgente), che completa i
  milestone in attesa (facendo poi scattare la generazione a valle come un completamento
  manuale).
* Il **documento è sovrano**: se la riconciliazione fallisce, il cambio-stato del documento
  **non** viene annullato; l'errore è tracciato in
  [`reconcile_errori`](/dbzero/pratiche/tabelle/reconcile_errori) (osservabilità).
* È **idempotente** (un milestone già completato non riavanza) e ignora gli step **DOMINIO**
  (l'esito lì è di ramo, calcolato dal dominio — vedi asse esito).

**Projection-driven vs handler-driven**: uno step o **segue la proiezione** del documento
(GUIDA) **o** esegue un handler server-side al COMPLETATO
([handler-eventi](#handler-django-registry-pattern)), **mai entrambi** — un guard config-time
lo impedisce (altrimenti l'avanzamento automatico salterebbe l'handler, perdendo l'azione di
dominio). Il primo caso reale è il **ritiro** di `vendita.accetta_preventivo`: il pulsante
«Accetta» in pratica chiama il servizio standalone del preventivo e il milestone avanza per
proiezione.

**Inversione piena (accetta *e* rifiuta)**: sul preventivo il binding è configurato su
«qualsiasi verdetto» (non solo POSITIVO), così il milestone `APPROVAZIONE_CLIENTE` si completa
sia sull'accettazione (POSITIVO) sia su ogni esito terminale-negativo — rifiutato / scaduto /
annullato (tutti NEGATIVO). Nel caso negativo il completamento non "fa proseguire" la pratica:
i passi a valle (es. SMISTAMENTO) hanno prerequisiti **esito-aware** che richiedono
`APPROVAZIONE_CLIENTE = POSITIVO`, quindi con NEGATIVO diventano **ramo morto** (non bloccano)
e la pratica **si chiude pulita**. Prima, con l'avanzamento solo su POSITIVO, un preventivo
rifiutato lasciava il milestone aperto e la pratica appesa: l'inversione piena chiude la
divergenza in **entrambe** le direzioni.

---

## Handler Django (registry pattern)

> Vedi anche: [Messaggi di Errore e Generazione Log](./Messaggi-di-Errore-e-Generazione-Log) per il sistema di error handling usato dagli handler

La tabella [`handler_flussi`](/dbzero/pratiche/tabelle/handler_flussi) contiene le chiavi di dispatch
(`handler_key`). Django mantiene un mapping statico `handler_key -> classe Handler` nel codice Python,
nel file `apps/pratiche/services/handler_registry.py` ([esempio](#area-tecnica-esempi)). Due regole:

* Nessun path Python nel DB. Il DB valida solo l'esistenza della chiave
* Il dispatch avviene via `pratiche_service.dispatch_handler(flusso_id)`

### Contratto handler

Ogni handler implementa il protocollo `BaseFlussoHandler` con un unico metodo,
`execute(flusso_id, pratica_id, meta, handler_params)`, che restituisce un `dict`
([firma](#area-tecnica-esempi)).

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
* ⚠️ Il dispatch degli **eventi** di un flusso, invece, è fail-fast: un binding attivo la cui `handler_key` non ha un handler registrato nel backend fa fallire il completamento del flusso con `E_HANDLER_NON_REGISTRATO`. Binding a catalogo e handler Python arrivano quindi insieme; un test del backend (`test_handler_registro_coerente_db`) confronta il registro del database con gli handler registrati

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

I trigger standard (audit, lock codice_interno, attivo protection, tx_id, storicizzazione) sono gestiti automaticamente dai runner del [framework di automazione](/guide/automazione-db) (`dbops.fn_run_automations_<tipo>`), che la convergenza di ogni migrate e i job pgAgent chiamano nell'ordine di [dbops.processi](/dbzero/dbops/tabelle/processi). Qui sono elencati **solo** i trigger del dominio pratiche, con la relativa trigger function.

#### Su `pratiche.pratiche`

| Trigger                                      | Funzione                                                                                                 | Evento                      | Descrizione                                                                                                                      |
| -------------------------------------------- | -------------------------------------------------------------------------------------------------------- | --------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `trg_pratiche_a10_valida_transizione`        | [`trgfn_pratiche_guard_transizione`](/dbzero/pratiche/funzioni/trgfn_pratiche_guard_transizione)         | BEFORE UPDATE OF stato_id   | Guard: verifica transizione ammessa via [`config.transizioni_stati_pratiche`](/dbzero/config/tabelle/transizioni_stati_pratiche) |
| `trg_pratiche_z90_giornale_ins`              | [`trgfn_pratiche_giornale_ins`](/dbzero/pratiche/funzioni/trgfn_pratiche_giornale_ins)                   | AFTER INSERT                | Registra PRATICA_CREATA nel giornale                                                                                             |
| `trg_pratiche_z90_giornale_stato_upd`        | [`trgfn_pratiche_giornale_stato`](/dbzero/pratiche/funzioni/trgfn_pratiche_giornale_stato)               | AFTER UPDATE OF stato_id    | Registra STATO_CAMBIATO                                                                                                          |
| `trg_pratiche_z90_giornale_assegnazione_upd` | [`trgfn_pratiche_giornale_assegnazione`](/dbzero/pratiche/funzioni/trgfn_pratiche_giornale_assegnazione) | AFTER UPDATE OF risorsa/uo  | Registra ASSEGNAZIONE_CAMBIATA                                                                                                   |
| `trg_pratiche_z90_giornale_priorita_upd`     | [`trgfn_pratiche_giornale_priorita`](/dbzero/pratiche/funzioni/trgfn_pratiche_giornale_priorita)         | AFTER UPDATE OF priorita_id | Registra PRIORITA_CAMBIATA                                                                                                       |

#### Su `pratiche.template_flussi`

| Trigger                                                | Funzione                                                                                                             | Evento                                                            | Descrizione                                                                                                                                                                                                                              |
| ------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `trg_template_flussi_a10_guard_modalita_esito_ins_upd` | [`trgfn_template_flussi_guard_modalita_esito`](/dbzero/pratiche/funzioni/trgfn_template_flussi_guard_modalita_esito) | BEFORE INSERT OR UPDATE OF modalita_esito/esito_default/direzione | Guard parlante: `esito_default` obbligatorio se `modalita_esito` non e' MANUALE (errore `TEMPLATE_FLUSSO_ESITO_DEFAULT_OBBLIGATORIO`); `AUTOMATICO` ammesso solo su direzione INTERNA (errore `TEMPLATE_FLUSSO_AUTOMATICO_SOLO_INTERNA`) |

#### Su `pratiche.flussi`

| Trigger                                 | Funzione                                                                                                         | Evento                    | Descrizione                                                                                                                                    |
| --------------------------------------- | ---------------------------------------------------------------------------------------------------------------- | ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| `trg_flussi_a10_valida_transizione`     | [`trgfn_flussi_guard_transizione`](/dbzero/pratiche/funzioni/trgfn_flussi_guard_transizione)                     | BEFORE UPDATE OF stato_id | Guard: verifica transizione ammessa via [`config.transizioni_stati_flussi_pratiche`](/dbzero/config/tabelle/transizioni_stati_flussi_pratiche) |
| `trg_flussi_a10_guard_prerequisiti_ins` | [`trgfn_flussi_guard_prerequisiti`](/dbzero/pratiche/funzioni/trgfn_flussi_guard_prerequisiti)                   | BEFORE INSERT             | Guard: blocca INSERT se prerequisiti non soddisfatti                                                                                           |
| `trg_flussi_z90_giornale_ins`           | [`trgfn_flussi_giornale_ins`](/dbzero/pratiche/funzioni/trgfn_flussi_giornale_ins)                               | AFTER INSERT              | Registra FLUSSO_CREATO                                                                                                                         |
| `trg_flussi_z90_giornale_stato_upd`     | [`trgfn_flussi_giornale_stato`](/dbzero/pratiche/funzioni/trgfn_flussi_giornale_stato)                           | AFTER UPDATE OF stato_id  | Registra FLUSSO_STATO_CAMBIATO                                                                                                                 |
| `trg_flussi_z90_generazione_upd`        | [`trgfn_flussi_generazione`](/dbzero/pratiche/funzioni/trgfn_flussi_generazione)                                 | AFTER UPDATE (COMPLETATO) | Genera pratiche cross-pratica da regole con `auto = true`                                                                                      |
| `trg_flussi_z91_calcoli_tempo_upd`      | [`trgfn_flussi_calcolo_tempo_completamento`](/dbzero/pratiche/funzioni/trgfn_flussi_calcolo_tempo_completamento) | AFTER UPDATE (COMPLETATO) | Crea/aggiorna record in [`calcoli_tempo`](/dbzero/pratiche/tabelle/calcoli_tempo) se esiste formula tempo applicabile                          |

#### Su `pratiche.sospensioni`

| Trigger                              | Funzione                                                                                                                                                                                  | Evento                    | Descrizione                                                                                                               |
| ------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `trg_sospensioni_a10_guard_coerenza` | [`trgfn_sospensioni_guard_coerenza_flusso`](/dbzero/pratiche/funzioni/trgfn_sospensioni_guard_coerenza_flusso)                                                                            | BEFORE INSERT             | Guard: verifica che `flusso_id` appartenga alla stessa `pratica_id`                                                       |
| `trg_sospensioni_z90_after_ins`      | [`trgfn_sospensioni_propaga`](/dbzero/pratiche/funzioni/trgfn_sospensioni_propaga) + [`trgfn_sospensioni_giornale`](/dbzero/pratiche/funzioni/trgfn_sospensioni_giornale_ins)             | AFTER INSERT              | Propaga sospensione ai flussi DA_ESEGUIRE/IN_CORSO (se `flusso_id IS NULL`), registra SOSPENSIONE_REGISTRATA nel giornale |
| `trg_sospensioni_z90_after_upd`      | [`trgfn_sospensioni_riattiva`](/dbzero/pratiche/funzioni/trgfn_sospensioni_riattiva) + [`trgfn_sospensioni_giornale`](/dbzero/pratiche/funzioni/trgfn_sospensioni_giornale_riattivazione) | AFTER UPDATE OF data_fine | Ripristina stati flussi dal giornale, registra SOSPENSIONE_CHIUSA nel giornale                                            |

#### Su `pratiche.calcoli_tempo`

| Trigger                                  | Funzione                                                                                                 | Evento        | Descrizione                                                                                |
| ---------------------------------------- | -------------------------------------------------------------------------------------------------------- | ------------- | ------------------------------------------------------------------------------------------ |
| `trg_calcoli_tempo_a10_guard_immutabili` | [`trgfn_calcoli_tempo_guard_immutabili`](/dbzero/pratiche/funzioni/trgfn_calcoli_tempo_guard_immutabili) | BEFORE UPDATE | Guard: impedisce UPDATE su colonne immutabili (pratica_id, formula_tempo_id, flusso_da_id) |

#### Su note e allegati

| Trigger                                  | Funzione                                                                                         | Evento       | Descrizione                |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------ | ------------ | -------------------------- |
| `trg_note_pratiche_z90_giornale_ins`     | [`trgfn_note_pratiche_giornale`](/dbzero/pratiche/funzioni/trgfn_note_pratiche_giornale)         | AFTER INSERT | Registra NOTA_AGGIUNTA     |
| `trg_note_flussi_z90_giornale_ins`       | [`trgfn_note_flussi_giornale`](/dbzero/pratiche/funzioni/trgfn_note_flussi_giornale)             | AFTER INSERT | Registra NOTA_AGGIUNTA     |
| `trg_allegati_pratiche_z90_giornale_ins` | [`trgfn_allegati_pratiche_giornale`](/dbzero/pratiche/funzioni/trgfn_allegati_pratiche_giornale) | AFTER INSERT | Registra ALLEGATO_AGGIUNTO |
| `trg_allegati_flussi_z90_giornale_ins`   | [`trgfn_allegati_flussi_giornale`](/dbzero/pratiche/funzioni/trgfn_allegati_flussi_giornale)     | AFTER INSERT | Registra ALLEGATO_AGGIUNTO |

---

## Funzioni DB

| Funzione                                                                                       | Tipo              | Scopo                                                                                                   |
| ---------------------------------------------------------------------------------------------- | ----------------- | ------------------------------------------------------------------------------------------------------- |
| [`fn_check_prerequisiti_flusso`](/dbzero/pratiche/funzioni/fn_check_prerequisiti_flusso)       | check (pura)      | Verifica prerequisiti, ritorna tabella con flag `soddisfatto`                                           |
| [`fn_guard_prerequisiti_flusso`](/dbzero/pratiche/funzioni/fn_guard_prerequisiti_flusso)       | guard (fail-fast) | RAISE se prerequisiti non soddisfatti                                                                   |
| [`fn_genera_pratica_da_flusso`](/dbzero/pratiche/funzioni/fn_genera_pratica_da_flusso)         | operativa         | Genera nuova pratica da flusso completato secondo regola                                                |
| [`fn_calcola_tempo_netto_da_a`](/dbzero/pratiche/funzioni/fn_calcola_tempo_netto_da_a)         | calcolo (STABLE)  | Calcola giorni netti tra due flussi, sottraendo solo le sospensioni pratica-level (`flusso_id IS NULL`) |
| [`fn_valuta_tempo_esecuzione_da_a`](/dbzero/pratiche/funzioni/fn_valuta_tempo_esecuzione_da_a) | calcolo (STABLE)  | Ritorna giorni_netti, giorni_esecuzione, giorni_rimanenti, stato_tempo (OK/WARNING/CRITICO/SFORATO)     |

> Per la documentazione dettagliata di ogni funzione e trigger function, vedi le pagine in `docs/it/dbzero/pratiche/manual/`.

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

| Metodo | Endpoint                              | Descrizione                                  |
| ------ | ------------------------------------- | -------------------------------------------- |
| GET    | `/api/v1/pratiche/`                   | Lista pratiche con filtri e paginazione      |
| POST   | `/api/v1/pratiche/`                   | Crea nuova pratica (stato iniziale: BOZZA)   |
| GET    | `/api/v1/pratiche/{id}/`              | Dettaglio pratica                            |
| PATCH  | `/api/v1/pratiche/{id}/`              | Aggiorna campi modificabili                  |
| POST   | `/api/v1/pratiche/{id}/stato/`        | Cambio stato pratica                         |
| POST   | `/api/v1/pratiche/{id}/assegnazione/` | Assegna risorsa umana / unita' organizzativa |
| GET    | `/api/v1/pratiche/{id}/giornale/`     | Giornale di bordo paginato                   |

#### Flussi

| Metodo | Endpoint                                           | Descrizione                                   |
| ------ | -------------------------------------------------- | --------------------------------------------- |
| GET    | `/api/v1/pratiche/{id}/flussi/`                    | Lista flussi della pratica                    |
| POST   | `/api/v1/pratiche/{id}/flussi/`                    | Crea nuovo flusso                             |
| GET    | `/api/v1/pratiche/{id}/flussi/{fid}/`              | Dettaglio flusso                              |
| POST   | `/api/v1/pratiche/{id}/flussi/{fid}/stato/`        | Cambio stato flusso (con esito se COMPLETATO) |
| GET    | `/api/v1/pratiche/{id}/flussi/{fid}/prerequisiti/` | Prerequisiti del flusso                       |
| GET    | `/api/v1/pratiche/{id}/flussi/{fid}/canali/`       | Canali abilitati per il flusso                |

#### Sospensioni pratica e flusso

| Metodo | Endpoint                                       | Descrizione                                   |
| ------ | ---------------------------------------------- | --------------------------------------------- |
| POST   | `/api/v1/pratiche/{id}/sospendi/`              | Sospende pratica intera (motivo obbligatorio) |
| POST   | `/api/v1/pratiche/{id}/riattiva/`              | Riattiva pratica sospesa                      |
| GET    | `/api/v1/pratiche/{id}/sospensioni/`           | Lista sospensioni pratica (attive e chiuse)   |
| POST   | `/api/v1/pratiche/{id}/flussi/{fid}/sospendi/` | Sospende singolo flusso                       |
| POST   | `/api/v1/pratiche/{id}/flussi/{fid}/riattiva/` | Riattiva singolo flusso                       |

#### Tempi e formule

| Metodo | Endpoint                                                | Descrizione                                           |
| ------ | ------------------------------------------------------- | ----------------------------------------------------- |
| GET    | `/api/v1/pratiche/formule-tempo/?tipo_prestazione_id=N` | Formule tempo attive per tipo prestazione             |
| GET    | `/api/v1/pratiche/{id}/calcoli-tempo/`                  | Calcoli tempo con stato_tempo live e giorni_rimanenti |

#### Generazione

| Metodo | Endpoint                                                 | Descrizione                          |
| ------ | -------------------------------------------------------- | ------------------------------------ |
| GET    | `/api/v1/pratiche/{id}/flussi/{fid}/regole-generazione/` | Regole di generazione applicabili    |
| POST   | `/api/v1/pratiche/{id}/flussi/{fid}/genera/`             | Genera pratica manualmente da regola |
| GET    | `/api/v1/pratiche/{id}/flussi/{fid}/pratiche-generate/`  | Pratiche generate dal flusso         |

### Service come API interna cross-dominio

Il `pratiche_service` è progettato come **API interna** che altri domini importano e usano: una
chiamata a `crea_pratica()` con emittente, tipo prestazione, soggetto e priorità
([esempio](#area-tecnica-esempi)).

### File coinvolti

| Layer      | File                                                           |
| ---------- | -------------------------------------------------------------- |
| Types      | `apps/pratiche/types.py`                                       |
| Repository | `apps/pratiche/db/pratiche_repository.py`                      |
| Repository | `apps/pratiche/db/generazione_repository.py`                   |
| Service    | `apps/pratiche/services/pratiche_service.py`                   |
| Service    | `apps/pratiche/services/generazione_service.py`                |
| Handler    | `apps/pratiche/services/handler_registry.py`                   |
| API        | `apps/pratiche/api/views.py`                                   |
| URL        | `apps/pratiche/api/urls_v1.py`                                 |
| Test       | `apps/pratiche/tests/services/test_pratiche_service.py`        |
| Test       | `apps/pratiche/tests/services/test_pratiche_service_flussi.py` |
| Test       | `apps/pratiche/tests/services/test_generazione_service.py`     |
| Test       | `apps/pratiche/tests/services/test_handler_registry.py`        |
| Test       | `apps/pratiche/tests/api/test_pratiche_api.py`                 |
| Test       | `apps/pratiche/tests/api/test_flussi_api.py`                   |
| Test       | `apps/pratiche/tests/services/test_sospensioni_service.py`     |
| Test       | `apps/pratiche/tests/api/test_sospensioni_api.py`              |
| Smoke      | `scripts/smoke-test-sospensioni.sh`                            |

---

## Integrazione cross-dominio

> Vedi anche: [Guida Risorse Umane e Accessi](./risorse-umane-e-accessi) per il modello `risorsa_umana_id` usato nelle assegnazioni

### Il giornale come infrastruttura trasversale

> **Nota**: questa sezione descrive il **design architetturale** dell'integrazione cross-dominio. L'infrastruttura (`pratiche_service`, trigger DB, giornale) e' operativa, ma nessun dominio di Anello 3 (vendite, acquisti, magazzino) la consuma ancora. Gli esempi seguenti illustrano come l'integrazione funzionera' quando i domini saranno collegati.

Il modulo pratiche non e' solo un workflow engine autonomo: e' l'anello infrastrutturale che gli altri domini dell'ERP useranno per tracciare i propri processi.

**Principio**: ogni evento significativo di dominio (nuovo cliente, nuovo ordine, modifica contratto) transitera' dal giornale di bordo attraverso la creazione/aggiornamento di una pratica. Il giornale cattura automaticamente il ciclo di vita via trigger DB.

| Evento dominio       | tipo_prestazione    | Cosa succedera'                                    |
| -------------------- | ------------------- | -------------------------------------------------- |
| Nuovo cliente creato | ONBOARDING_CLIENTE  | Pratica creata con soggetto_id, flussi configurati |
| Nuovo ordine vendita | GESTIONE_ORDINE     | Pratica creata con meta referencing l'ordine       |
| Modifica contratto   | REVISIONE_CONTRATTO | Pratica creata, flussi di approvazione/notifica    |
| Reclamo ricevuto     | RECLAMO             | Pratica creata da canale WEB_CLIENTI               |

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

Inserire i dati di seed nelle tabelle catalogo: il tipo prestazione, i template flussi con la loro
sequenza, i prerequisiti che formano il grafo e — se servono — i canali di visibilità
([esempio](#area-tecnica-esempi)).

### 2. Backend Django (opzionale: handler automatizzato)

Se uno step è automatizzato servono **due registrazioni**, una per lato: la chiave in
`pratiche.handler_flussi` (che il database valida) e il mapping in `HANDLER_MAP` dentro
`apps/pratiche/services/handler_registry.py` ([esempio](#area-tecnica-esempi)). Il database
controlla che la chiave esista: non che esista un handler che la sappia eseguire.

### 3. Integrazione dal dominio

Dal service del dominio si importa `pratiche_service` e si chiama `crea_pratica()`: i trigger del
database registrano `PRATICA_CREATA` nel giornale, e i flussi li crea l'operatore o
l'automazione ([esempio](#area-tecnica-esempi)).

Non serve toccare il nucleo pratiche: tutto avviene per configurazione.

---

## Sviluppi aperti

**Il pattern previsto per i dati strutturati dei flussi (`ext_*`).** Nessuna di queste tabelle esiste
ancora. L'idea è che un tipo di flusso con campi propri — un appuntamento, un sopralluogo, una
spedizione — non li aggiunga a `pratiche.flussi` (che è il nucleo, uguale per tutti) ma in una
tabella di estensione con FK verso `pratiche.flussi(id)`:

* `pratiche.ext_appuntamento` — fascia oraria, data/ora, esito, risorsa assegnata
* `pratiche.ext_preventivo` — importi, voci, stato accettazione
* `pratiche.ext_sopralluogo` — dati tecnici, foto, misurazioni
* `pratiche.ext_comunicazione` — canale, destinatario, contenuto, conferma ricezione
* `pratiche.ext_spedizione` — corriere, tracking, stato consegna

Gli altri pezzi non ancora arrivati in fondo sono le ultime righe della tabella qui sotto
(handler concreti, endpoint manuale di generazione, agenda operativa).

---

## Stato dei componenti

La tabella riporta fin dove arriva ogni pezzo, perché la risposta a «posso usarlo?» non è la stessa per
una tabella e per un endpoint. La colonna **Stato** distingue tra:

* **DB**: tabella, funzioni e trigger deployati e testati con pgTAP
* **DB + Backend + API**: anche endpoint Django funzionante
* **Solo DB**: logica nel database, **nessun endpoint API** — la UI/backend non puo' ancora consumare questi dati

| Componente                        | Scopo                                    | Stato                  | Note                                                                                                                                                                 |
| --------------------------------- | ---------------------------------------- | ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Tabella `pratiche.sospensioni`    | Periodi di fermo pratica/flusso          | **DB + Backend + API** | Endpoint sospendi/riattiva operativi                                                                                                                                 |
| Tabella `pratiche.formule_tempo`  | Soglie warning/critico per semafori      | **DB + Backend + API** | Endpoint GET per tipo_prestazione                                                                                                                                    |
| Tabella `pratiche.calcoli_tempo`  | Calcolo tempi netti da/a                 | **DB + Backend + API** | Trigger automatico + endpoint GET con stato_tempo                                                                                                                    |
| `fn_calcola_tempo_netto_da_a`     | Calcolo giorni netti                     | **DB + Backend + API** | Usata internamente da `fn_valuta_tempo_esecuzione_da_a`                                                                                                              |
| `fn_valuta_tempo_esecuzione_da_a` | Semaforo OK/WARNING/CRITICO/SFORATO      | **DB + Backend + API** | Consumata dall'endpoint calcoli-tempo per il semaforo UI                                                                                                             |
| Riattivazione automatica          | Job pgAgent per riattivazione a scadenza | **DB + job pgAgent**   |                                                                                                                                                                      |
| Macchina a stati rigida           | Transizioni validate da trigger DB       | **DB**                 | Enforced su tutte le operazioni, non richiede backend dedicato                                                                                                       |
| Generazione cross-pratica         | Trigger auto + fn_genera_pratica         | **DB**                 | Trigger auto funzionante; endpoint manuale da sviluppare                                                                                                             |
| Handler Django registry           | Dispatch automatico flussi               | **Design**             | Pattern infrastrutturale pronto (`BaseFlussoHandler`, `get_handler()`, dispatch nel service). Registry vuoto: gli handler concreti arrivano con i domini di Anello 3 |
| Agenda attivita'                  | Vista operativa per operatore/reparto    | **Analisi**            | Non ancora progettata                                                                                                                                                |

Le funzionalita' implementate appartengono all'**anello infrastrutturale** (Anello 2) e si appoggiano sul nucleo senza modificarlo.

---

## Checklist operativa

### Per configurare un nuovo tipo prestazione

1. INSERT in `pratiche.tipi_prestazione` (codice, categoria)
2. INSERT in `pratiche.template_flussi` per ogni step del workflow
3. INSERT in `pratiche.template_flussi_prerequisiti` per il grafo di dipendenze
4. (opzionale) INSERT in `pratiche.template_flussi_canali` per visibilita' esterna
5. (opzionale) INSERT in `pratiche.handler_flussi` + registrare handler in `HANDLER_MAP` Django
6. (opzionale) INSERT in `pratiche.regole_generazione` per generazione cross-pratica
7. (opzionale) INSERT in `pratiche.formule_tempo` per soglie temporali tra coppie di flussi

### Per integrare un dominio esterno

1. Importare `pratiche_service` nel service del dominio
2. Chiamare `crea_pratica()` con tipo_prestazione, soggetto, emittente
3. Il giornale DB registra tutto automaticamente — nessun logging applicativo

### Per aggiungere un nuovo handler automatizzato

1. Creare classe che implementa `BaseFlussoHandler.execute()`
2. Registrare `handler_key` in `pratiche.handler_flussi` (DB)
3. Aggiungere mapping in `HANDLER_MAP` (Python)
4. Associare `handler_id` al template flusso desiderato

---

## Area tecnica — esempi

**Il `dettaglio` di un cambio di stato** — l'azione resta `STATO_CAMBIATO`, i due stati viaggiano
qui dentro:

```json
{
  "stato_precedente": "APERTA",
  "stato_nuovo": "SOSPESA",
  "tx_id": "a1b2c3..."
}
```

**Chiamare il motore da un altro dominio** — la chiamata che un service di Anello 3 fa per aprire
una pratica:

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

**Il giornale di una pratica** — cosa è successo, in ordine, con lo stato di partenza e di arrivo:

```sql
SELECT data_insert, azione, origine,
       dettaglio->>'stato_precedente' AS da,
       dettaglio->>'stato_nuovo'      AS a
FROM pratiche.giornale
WHERE pratica_id = :pratica_id
ORDER BY data_insert DESC
LIMIT 50;
```

**Le sospensioni in corso** — l'intervallo calcolato serve proprio a questa domanda:

```sql
SELECT flusso_id, data_inizio, motivo
FROM pratiche.sospensioni
WHERE pratica_id = :pratica_id
  AND periodo_sospensione @> now()
ORDER BY data_inizio DESC;
```

**La mappa degli handler** — lato Django: chiave di dispatch e classe che la esegue. Sta in
`apps/pratiche/services/handler_registry.py`:

```python
# apps/pratiche/services/handler_registry.py
HANDLER_MAP: dict[str, type[BaseFlussoHandler]] = {
    # "APPUNTAMENTO": AppuntamentoHandler,
    # "SOPRALLUOGO": SopralluogoHandler,
}
```

**La firma del contratto handler** — l'unico metodo che un handler deve implementare:

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

**Registrare un handler nuovo** — le due registrazioni, una per lato; il database valida la chiave,
Django la sa eseguire solo se il mapping esiste:

```sql
INSERT INTO pratiche.handler_flussi (handler_key, descrizione)
VALUES ('INVIO_RISPOSTA_RECLAMO', 'Invio email risposta reclamo');
```

```python
# apps/reclami/handlers/risposta_handler.py
class InvioRispostaReclamoHandler:
    def execute(self, flusso_id, pratica_id, meta, handler_params):
        # handler_params: configurazione statica dal template
        # meta: dati specifici dell'istanza flusso
        return {"email_inviata": True}

# apps/pratiche/services/handler_registry.py
HANDLER_MAP["INVIO_RISPOSTA_RECLAMO"] = InvioRispostaReclamoHandler
```

**Aggiungere un dominio: il catalogo** — tipo prestazione, i suoi step con la sequenza, il grafo dei
prerequisiti e i canali di visibilità:

```sql
-- Tipo prestazione
INSERT INTO pratiche.tipi_prestazione (codice, descrizione, categoria)
VALUES ('RECLAMO', 'Gestione reclamo cliente', 'COMMERCIALE');

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

**Aggiungere un dominio: il service che lo usa** — l'integrazione vista dal lato del dominio:

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
    # I trigger registrano PRATICA_CREATA nel giornale.
    # I flussi li crea l'operatore o l'automazione.
    return pratica_id
```

---

{% include-markdown "signature-core.md" %}
