# ZeroERP — Schema `pratiche` — Motore Workflow

> Documento concettuale di sviluppo. La fonte di verita' per DDL, funzioni e trigger
> e' nelle migrazioni Liquibase in `db/changelog/migrations_v2/`.
> Questo documento descrive architettura, regole e decisioni progettuali.

## Filosofia

Tutto e' una pratica. Ogni operazione in ZeroERP transita dal motore pratiche.
Chi configura prestazioni e flussi ottiene un workflow engine con controllo sequenza rigoroso.
Chi non configura ottiene comunque un giornale di bordo completo con tracciabilita' totale.

### Allineamento con lo Sviluppo Concentrico

Il modulo pratiche si colloca come **anello infrastrutturale** nel modello concentrico:

- Si appoggia sugli anelli interni: `anagrafiche` (soggetti, risorse umane), `config` (stati, unita' organizzative)
- Parla lo stesso linguaggio: audit fields, tx_id, storicizzazione, error handling centralizzato
- Gli anelli esterni (vendite, acquisti, magazzino) potranno appoggiarsi su pratiche
  tramite le tabelle di estensione (`ext_*`) senza rompere la coerenza del nucleo

---

## Diagramma Dipendenze

```
config.stati_pratiche
config.stati_flussi_pratiche
config.priorita_pratiche
config.tipi_nota
config.tipi_allegato
config.canali_pratiche
         |
         v
tipi_prestazione (catalogo condiviso)
    |
    +-- template_flussi ---- template_flussi_prerequisiti
    |       |       |
    |       |       +-- template_flussi_canali (M:N → config.canali_pratiche)
    |       |
    |       +-- handler_flussi (registry)
    |       |
    |       +-- regole_generazione (cross-pratica)
    |
    v
pratiche -------------------- note_pratiche
    |                         allegati_pratiche
    |
    +-- flussi -------------- note_flussi
    |     |                   allegati_flussi
    |     +-- flussi (padre -> figlio)
    |
    +-- giornale (immutabile, alimentato da trigger)
```

---

## 0. Prerequisiti — Tabelle Config

> Migrazioni: `db/changelog/migrations_v2/00_schema/config/`

### 0.1 config.stati_pratiche

Stati del ciclo di vita della pratica. Pattern standard config (id, codice, codice_interno UNIQUE, descrizione, attivo, meta, audit).

Seed: BOZZA, APERTA, SOSPESA, CHIUSA, ANNULLATA.

### 0.2 config.stati_flussi_pratiche

Stati del flusso/step operativo. Stesso pattern standard config.

Seed: DA_ESEGUIRE, IN_CORSO, COMPLETATO, SOSPESO, ANNULLATO, ERRORE.

### 0.3 config.priorita_pratiche

Livelli di priorita' con ordinamento esplicito via campo `sequenza` INTEGER (UNIQUE).

Seed: BASSA (seq 10), NORMALE (seq 20), ALTA (seq 30), URGENTE (seq 40).

### 0.4 config.tipi_nota

Tipologie di nota, condivise tra moduli. Pattern standard config.

Seed: GENERALE, INTERNA, CLIENTE, TECNICA, LEGALE.

### 0.5 config.tipi_allegato

Tipologie di allegato, condivise tra moduli. Pattern standard config.

Seed: DOCUMENTO, IMMAGINE, MODULO, CONTRATTO, FATTURA, VERBALE, CERTIFICATO, ALTRO.

### 0.6 config.canali_pratiche

Canali di visibilita' dei flussi (es. WEB_CLIENTI, APP_TECNICA, PORTALE_FORNITORI).
Non e' un booleano sulla pratica ma una tabella di registry per configurazione flessibile.

Seed: WEB_CLIENTI, APP_TECNICA, PORTALE_FORNITORI.

### Note trigger config

I trigger standard (audit, lock codice_interno, attivo protection) sono gestiti automaticamente
da `dbops.fn_run_automations()` — non servono migrazioni manuali.

---

## 1. Catalogo — Configurazione

> Migrazioni: `db/changelog/migrations_v2/00_schema/pratiche/`
>
> Il catalogo e' **condiviso** tra tutti gli emittenti fiscali.
> La segregazione multi-company avviene sulla tabella `pratiche.pratiche` tramite `emittente_fiscale_id`.

### 1.1 pratiche.tipi_prestazione

Catalogo dei tipi di prestazione. Macro-categorie di attivita' gestibili.

- **categoria**: raggruppamento libero (es. UTILITIES, COMMERCIALE, AMMINISTRATIVO)
- **flussi_vincolanti**: `true` = controllo sequenza/prerequisiti attivo, `false` = giornale senza vincoli

### 1.2 pratiche.handler_flussi

Registry degli handler Django per flussi automatizzati.
Segue il pattern `implementation_key` del sistema (no path Python nel template).

- **handler_key**: chiave univoca usata da Django per il dispatch (es. `APPUNTAMENTO`, `SOPRALLUOGO`)
- Django mantiene un mapping `handler_key → classe Handler` nel codice, non nel DB
- Il DB valida solo l'esistenza della chiave

### 1.3 pratiche.template_flussi

Template dei flussi previsti per ogni tipo di prestazione.

- **sequenza**: ordine logico (0, 10, 20...). Il controllo effettivo e' sui prerequisiti espliciti
- **direzione**: caratterizza il tipo di flusso rispetto all'esterno (ENTRATA, USCITA, INTERNA). Default INTERNA
- **handler_id**: NULL = step manuale (completato dall'utente), NOT NULL = step automatizzato (Django dispatch)
- **handler_params**: JSONB — parametri operativi passati all'handler Django (es. stampa_foglio, invio_sms_conferma)
- **meta**: dati estensibili (JSONB, pattern standard del sistema)
- UNIQUE su `(tipo_prestazione_id, codice)`

### 1.4 pratiche.template_flussi_prerequisiti

Prerequisiti espliciti tra flussi. Supporta paralleli e convergenze.

- **obbligatorio**: `true` = bloccante, `false` = consigliato (warning senza blocco)
- Solo `data_insert/user_insert`: tabella di relazione, non aggiornabile (si cancella e ricrea)
- CHECK: `template_flusso_id <> prerequisito_flusso_id` (no self-reference)

### 1.5 pratiche.regole_generazione

Configurazione cross-pratica: definisce quale flusso completato puo' generare una nuova pratica.

- **template_flusso_origine_id**: il flusso che scatena la generazione
- **tipo_prestazione_dest_id**: il tipo pratica da generare
- **template_flusso_dest_id**: il flusso iniziale della pratica generata (NULL = nessun flusso auto)
- **esito_richiesto**: CHECK (POSITIVO, NEGATIVO, QUALSIASI) — l'esito che attiva la generazione
- **auto**: se true, la generazione e' automatica al completamento del flusso (trigger DB)
- UNIQUE su `(template_flusso_origine_id, tipo_prestazione_dest_id, esito_richiesto)`

### 1.6 pratiche.template_flussi_canali

Relazione M:N tra template flussi e canali di visibilita'.

- FK → `pratiche.template_flussi(id)` e `config.canali_pratiche(id)`
- Solo `data_insert/user_insert` (relazione immutabile: si cancella e ricrea)
- UNIQUE su `(template_flusso_id, canale_id)`

---

## 2. Esecuzione — Istanze Operative

### 2.1 pratiche.pratiche

Istanza concreta di una pratica. Testata.

- **emittente_fiscale_id**: BIGINT NOT NULL — segregazione multi-company
- **soggetto_id**: UUID — FK a `anagrafiche.soggetti`
- **stato_id**: INTEGER NOT NULL — FK a `config.stati_pratiche`. Nessun default: il chiamante deve impostarlo
- **priorita_id**: INTEGER NOT NULL — FK a `config.priorita_pratiche`
- **risorsa_umana_id**: BIGINT — operatore assegnato (FK a `anagrafiche.risorse_umane`)
- **unita_organizzativa_id**: INTEGER — reparto assegnato (FK a `config.unita_organizzative`)
- **pratica_padre_id**: BIGINT — per sotto-pratiche e pratiche collegate (self-reference)
- **flusso_origine_id**: BIGINT — tracciabilita' cross-pratica: il flusso che ha generato questa pratica (FK differita a `pratiche.flussi`)
- **canale_origine_id**: INTEGER — FK a `config.canali_pratiche`: sorgente esterna (NULL = creata internamente)
- **solo_interna**: BOOLEAN NOT NULL DEFAULT false — se true, la pratica non abilita configurazione canali sui flussi
- **codice**: TEXT — codice pratica (generato da trigger)
- **descrizione**: TEXT — descrizione libera
- **data_scadenza**: DATE
- **meta** / **storicizza** / **tx_id**: pattern standard del sistema

### 2.2 pratiche.flussi

Step/fase operativa dentro una pratica. Riga.

- **pratica_id**: BIGINT NOT NULL — FK a `pratiche.pratiche`
- **template_flusso_id**: INTEGER — NULL per flussi aggiunti manualmente su pratiche libere
- **stato_id**: INTEGER NOT NULL — FK a `config.stati_flussi_pratiche`
- **flusso_padre_id**: BIGINT — albero di attivita'/sotto-flussi (self-reference)
- **risorsa_umana_id** / **unita_organizzativa_id**: assegnazione del flusso
- **sequenza**: INTEGER NOT NULL DEFAULT 0 — ordine esecuzione nel workflow
- **esito**: VARCHAR(20) CHECK (POSITIVO, NEGATIVO, PARZIALE, NON_APPLICABILE)
- **note_esito**: TEXT — note libere sull'esito
- **data_scadenza**: DATE — scadenza prevista per il flusso
- **meta** / **storicizza** / **tx_id**: pattern standard del sistema

> La FK `pratiche.flusso_origine_id → flussi.id` e' definita nel changeset flussi (FK differita per dipendenza circolare).

---

## 3. Documentale — Note e Allegati

### 3.1 pratiche.note_pratiche

Note associate alla testata pratica. Modificabili (4 audit fields).

- FK a `pratiche.pratiche` e `config.tipi_nota`
- **visibile_esterno**: se visibile su portale/cliente

### 3.2 pratiche.note_flussi

Note associate al singolo flusso. Stessa struttura delle note pratica.

### 3.3 pratiche.allegati_pratiche

Documenti e immagini allegati alla testata pratica.
Immutabili: nuova versione = nuova riga con `allegato_padre_id`.

- Solo `data_insert/user_insert`: gli allegati sono immutabili
- **hash_file**: SHA-256 per integrita' e deduplicazione storage
- **allegato_padre_id**: versione precedente dello stesso documento
- **percorso**: path nello storage (filesystem o object storage tipo S3/MinIO)

### 3.4 pratiche.allegati_flussi

Allegati al singolo flusso. Stessa struttura degli allegati pratica.

---

## 4. Giornale di Bordo — Audit Trail

### 4.1 pratiche.giornale

Log immutabile di ogni azione. Alimentato automaticamente via trigger.
Non si modifica, non si cancella.

- Solo `data_insert/user_insert`: immutabile, nessun update/delete
- **azione**: VARCHAR(50) — CHECK con 9 azioni: PRATICA_CREATA, STATO_CAMBIATO, ASSEGNAZIONE_CAMBIATA, PRIORITA_CAMBIATA, FLUSSO_CREATO, FLUSSO_STATO_CAMBIATO, NOTA_AGGIUNTA, ALLEGATO_AGGIUNTO, PRATICA_GENERATA
- **origine**: VARCHAR(20) — CHECK: SISTEMA, UTENTE, HANDLER, SCHEDULER. Default 'SISTEMA'
- **dettaglio**: JSONB NOT NULL — valori precedenti/nuovi per ricostruzione completa
- **tx_id**: UUID — correlazione con tx_id di transazione per tracciabilita' cross-tabella

### Indici espliciti (non-FK)

- `ix_pratiche_giornale_data_insert` (BTREE) — ricerca per data
- `ix_pratiche_giornale_azione` (BTREE) — filtro per tipo azione

> Gli indici FK (pratica_id, flusso_id) sono gestiti da `dbops.apply_fk_index_policy()`.

---

## 5. Funzioni DB

> Migrazioni: `db/changelog/migrations_v2/20_code/pratiche/`

### 5.1 pratiche.fn_check_prerequisiti_flusso

Funzione **check** (pura, STABLE): verifica prerequisiti di un template flusso per una pratica.
Ritorna una riga per ogni prerequisito con flag `soddisfatto` (boolean). Non fa RAISE.

- Input: `p_pratica_id`, `p_template_flusso_id`
- Output: TABLE(prerequisito_id, codice, descrizione, soddisfatto)
- Un prerequisito e' soddisfatto se esiste un flusso COMPLETATO per lo stesso template nella pratica

### 5.2 pratiche.fn_guard_prerequisiti_flusso

Funzione **guard** (fail-fast): chiama `fn_check` e fa RAISE via `script.fn_log_and_raise_error`
se esistono prerequisiti non soddisfatti. Codice errore: `PRATICHE_PREREQUISITI_NON_SODDISFATTI`.

- Input: `p_pratica_id`, `p_template_flusso_id`
- Raccoglie i codici dei prerequisiti non soddisfatti con `string_agg`

### 5.3 pratiche.trgfn_flussi_guard_prerequisiti

Trigger function wrapper: invoca la guard su INSERT di flussi con template (non manuali).

### 5.4 pratiche.fn_genera_pratica_da_flusso

Genera una nuova pratica a partire da un flusso completato, secondo la regola configurata
in `regole_generazione`. Copia emittente, soggetto, priorita' dalla pratica sorgente.
Imposta `flusso_origine_id` sulla pratica generata. Stato iniziale: BOZZA.

- Input: `p_flusso_id`, `p_regola_id`
- Output: id della pratica generata
- Guard: validazione parametri NULL / <= 0

### 5.5 pratiche.trgfn_flussi_generazione

Trigger function AFTER UPDATE su flussi: se stato diventa COMPLETATO, cerca regole matching
in `regole_generazione` con `auto = true` e invoca `fn_genera_pratica_da_flusso`.

### 5.6 Trigger functions giornale

10 trigger functions dedicate per alimentare il giornale:

- `trgfn_pratiche_giornale_ins` — PRATICA_CREATA
- `trgfn_pratiche_giornale_stato` — STATO_CAMBIATO (su pratiche)
- `trgfn_pratiche_giornale_assegnazione` — ASSEGNAZIONE_CAMBIATA
- `trgfn_pratiche_giornale_priorita` — PRIORITA_CAMBIATA
- `trgfn_flussi_giornale_ins` — FLUSSO_CREATO
- `trgfn_flussi_giornale_stato` — FLUSSO_STATO_CAMBIATO
- `trgfn_note_pratiche_giornale` — NOTA_AGGIUNTA (su note pratiche)
- `trgfn_note_flussi_giornale` — NOTA_AGGIUNTA (su note flussi)
- `trgfn_allegati_pratiche_giornale` — ALLEGATO_AGGIUNTO (su allegati pratiche)
- `trgfn_allegati_flussi_giornale` — ALLEGATO_AGGIUNTO (su allegati flussi)

---

## 6. Trigger Business-Specific

> I trigger standard (audit, tx_id, storico, lock, attivo) sono gestiti automaticamente
> da `dbops.fn_run_automations()` via CI pipeline. NON sono elencati qui.
>
> Gli indici FK sono gestiti da `dbops.apply_fk_index_policy()` in `90_end/`.
>
> Qui sono elencati SOLO i trigger business-specific del dominio pratiche.

### pratiche.pratiche (4 trigger business)

| Nome | Timing | Evento | Funzione |
|------|--------|--------|----------|
| `trg_pratiche_z90_giornale_ins` | AFTER | INSERT | `pratiche.trgfn_pratiche_giornale_ins()` |
| `trg_pratiche_z90_giornale_stato_upd` | AFTER | UPDATE OF stato_id | `pratiche.trgfn_pratiche_giornale_stato()` |
| `trg_pratiche_z90_giornale_assegnazione_upd` | AFTER | UPDATE OF risorsa_umana_id, unita_organizzativa_id | `pratiche.trgfn_pratiche_giornale_assegnazione()` |
| `trg_pratiche_z90_giornale_priorita_upd` | AFTER | UPDATE OF priorita_id | `pratiche.trgfn_pratiche_giornale_priorita()` |

### pratiche.flussi (4 trigger business)

| Nome | Timing | Evento | Funzione |
|------|--------|--------|----------|
| `trg_flussi_a10_guard_prerequisiti_ins` | BEFORE | INSERT | `pratiche.trgfn_flussi_guard_prerequisiti()` |
| `trg_flussi_z90_giornale_ins` | AFTER | INSERT | `pratiche.trgfn_flussi_giornale_ins()` |
| `trg_flussi_z90_giornale_stato_upd` | AFTER | UPDATE OF stato_id | `pratiche.trgfn_flussi_giornale_stato()` |
| `trg_flussi_z90_generazione_upd` | AFTER | UPDATE (WHEN stato → COMPLETATO) | `pratiche.trgfn_flussi_generazione()` |

### note_pratiche / note_flussi (1 ciascuno)

| Nome | Timing | Evento | Funzione |
|------|--------|--------|----------|
| `trg_note_pratiche_z90_giornale_ins` | AFTER | INSERT | `pratiche.trgfn_note_pratiche_giornale()` |
| `trg_note_flussi_z90_giornale_ins` | AFTER | INSERT | `pratiche.trgfn_note_flussi_giornale()` |

### allegati_pratiche / allegati_flussi (1 ciascuno)

| Nome | Timing | Evento | Funzione |
|------|--------|--------|----------|
| `trg_allegati_pratiche_z90_giornale_ins` | AFTER | INSERT | `pratiche.trgfn_allegati_pratiche_giornale()` |
| `trg_allegati_flussi_z90_giornale_ins` | AFTER | INSERT | `pratiche.trgfn_allegati_flussi_giornale()` |

---

## 7. Riepilogo Tabelle

### Schema `config` (prerequisiti)

| # | Tabella | Ruolo |
|---|---------|-------|
| 0a | `stati_pratiche` | Stati pratica |
| 0b | `stati_flussi_pratiche` | Stati flusso |
| 0c | `priorita_pratiche` | Livelli priorita' |
| 0d | `tipi_nota` | Tipi nota (condivisi) |
| 0e | `tipi_allegato` | Tipi allegato (condivisi) |
| 0f | `canali_pratiche` | Canali visibilita' flussi |

### Schema `pratiche` (nucleo)

| # | Tabella | Ruolo | PK | Relazioni principali |
|---|---------|-------|----|---------------------|
| 1 | `tipi_prestazione` | Catalogo tipi pratica | INTEGER | → template_flussi |
| 2 | `handler_flussi` | Registry handler Django | INTEGER | ← template_flussi |
| 3 | `template_flussi` | Template flussi con regole | INTEGER | → tipi_prestazione, → handler |
| 4 | `template_flussi_prerequisiti` | Prerequisiti tra flussi | INTEGER | → template_flussi (2x) |
| 5 | `regole_generazione` | Regole generazione cross-pratica | BIGINT | → template_flussi (2x), → tipi_prestazione |
| 6 | `template_flussi_canali` | M:N template ↔ canali | BIGINT | → template_flussi, → canali_pratiche |
| 7 | `pratiche` | Istanza operativa (testata) | BIGINT | → tipi_prestazione, → stati, → emittenti, → soggetti |
| 8 | `flussi` | Step operativo (riga) | BIGINT | → pratiche, → template, → stati_flussi |
| 9 | `note_pratiche` | Note su testata | BIGINT | → pratiche, → tipi_nota |
| 10 | `note_flussi` | Note su flusso | BIGINT | → flussi, → tipi_nota |
| 11 | `allegati_pratiche` | Documenti testata | BIGINT | → pratiche, → tipi_allegato |
| 12 | `allegati_flussi` | Documenti flusso | BIGINT | → flussi, → tipi_allegato |
| 13 | `giornale` | Audit trail immutabile | BIGINT | → pratiche, → flussi |

**Totale: 6 tabelle config + 13 tabelle nucleo + 5 funzioni DB + 2 trigger functions generazione**

---

## 8. Integrazione Cross-Dominio

### Il giornale come infrastruttura trasversale

Il modulo pratiche non e' solo un workflow engine autonomo: e' l'**anello infrastrutturale**
che gli altri domini dell'ERP usano per tracciare i propri processi.

**Principio**: ogni evento significativo di dominio (nuovo cliente, nuovo ordine, modifica contratto)
transita dal giornale di bordo attraverso la creazione/aggiornamento di una pratica.
Il giornale cattura automaticamente il ciclo di vita via trigger DB.

### Pattern di integrazione

```
Domini esterni (anagrafiche, vendite, acquisti, ...)
    |
    |  Django service chiama pratiche_service
    v
pratiche_service.crea_pratica(tipo_prestazione=..., soggetto_id=..., meta={dominio_ref: ...})
    |
    v
DB trigger → giornale (PRATICA_CREATA, STATO_CAMBIATO, ...)
```

**Esempi concreti**:

| Evento dominio | tipo_prestazione | Cosa succede |
|---|---|---|
| Nuovo cliente creato | ONBOARDING_CLIENTE | Pratica creata con soggetto_id, flussi configurati (verifica dati, primo contatto, ...) |
| Nuovo ordine vendita | GESTIONE_ORDINE | Pratica creata con meta referencing l'ordine, flussi per evasione |
| Modifica contratto | REVISIONE_CONTRATTO | Pratica creata, flussi di approvazione/notifica |
| Reclamo ricevuto | RECLAMO | Pratica creata da canale WEB_CLIENTI, flussi di gestione |

### Cosa NON transita dal giornale pratiche

Le operazioni **massive/batch** con struttura propria di esecuzione:

- `vendite.fatturazione_pipeline` → ha `fatturazione_lotti_task_runs` e log dedicati
- Future pipeline batch → avranno la propria infrastruttura di tracking

La distinzione e':
- **Processo unitario** (un cliente, un ordine, un reclamo) → **pratica + giornale**
- **Processo massivo** (lotto fatturazione, import massivo, riconciliazione batch) → **pipeline dedicata**

### Implicazioni per il backend

Il `pratiche_service` deve essere progettato come **API interna cross-dominio**:

- Altre app Django (vendite, anagrafiche, acquisti) importano e usano `pratiche_service`
- Il service espone metodi con interfaccia stabile e versionata
- I TypedDict in `types.py` sono progettati per riuso cross-app
- Il `handler_registry` permette a ogni dominio di registrare i propri handler

---

## 9. Estensioni Future (non incluse in questa fase)

Tabelle specifiche per tipo di flusso, da implementare progressivamente.
Ogni estensione avra' FK verso `pratiche.flussi(id)` e vivra' autonomamente.

- **pratiche.ext_appuntamento**: fascia oraria, data/ora, esito, risorsa_umana assegnata
- **pratiche.ext_preventivo**: importi, voci, stato accettazione
- **pratiche.ext_sopralluogo**: dati tecnici, foto, misurazioni
- **pratiche.ext_comunicazione**: canale, destinatario, contenuto, conferma ricezione
- **pratiche.ext_spedizione**: corriere, tracking, stato consegna

Ogni `ext_*` deve:

- Avere PK BIGINT e FK verso `pratiche.flussi(id)`
- Includere audit fields standard (`data_insert/user_insert/data_update/user_update`)
- Includere `tx_id UUID` e `storicizza BOOLEAN` dove appropriato
- Registrare le proprie azioni nel `giornale` tramite trigger

---

## 10. Note Architetturali

### Business logic nel DB

La funzione `fn_guard_prerequisiti_flusso` centralizza il controllo nel database.
Nessun bypass possibile, ne' da interfaccia ne' da API esterna.
Gli errori usano `script.fn_log_and_raise_error` con codici da `config.messaggi_errore`.

### Giornale via trigger

I trigger su pratiche, flussi, note e allegati alimentano automaticamente
il giornale. Django non deve preoccuparsi di loggare: il DB lo fa da solo.
Il `tx_id` nel giornale consente la correlazione con le transazioni cross-tabella.

### Handler Django (registry pattern)

La tabella `handler_flussi` contiene le chiavi di dispatch (`handler_key`).
Django mantiene un mapping `handler_key → classe Handler` nel codice Python.
Nessun path Python nel DB. Il DB valida solo l'esistenza della chiave.

### Multi-company

Il campo `emittente_fiscale_id` su `pratiche.pratiche` garantisce la segregazione dati.
Le query filtrano sempre per emittente.
Il catalogo (tipi_prestazione, template_flussi, handler_flussi) e' condiviso.

### Transaction ID e Storicizzazione

Le tabelle operative (`pratiche`, `flussi`) includono `tx_id UUID` e `storicizza BOOLEAN`,
gestiti rispettivamente da `dbops.trgfn_tx_id_managed()` e `script.trgfn_storico_generic()`.
Questo garantisce coerenza transazionale e audit trail storico completo.

### Indici FK

Tutti gli indici sulle FK sono gestiti da `dbops.apply_fk_index_policy()` nello step `90_end/`.
NON creare indici FK manualmente. Solo gli indici non-FK (performance, giornale) vanno creati esplicitamente.

### Versionamento allegati

Il campo `allegato_padre_id` mantiene lo storico versioni senza sovrascrivere.
L'hash SHA-256 previene duplicati a livello storage.

### Flussi paralleli

I prerequisiti espliciti permettono rami paralleli, convergenze e flussi opzionali.
Il numero di sequenza resta come ordine logico/visivo, non come vincolo.

### Generazione cross-pratica

Le `regole_generazione` configurano la creazione automatica di nuove pratiche
al completamento di un flusso (trigger AFTER UPDATE). La generazione manuale
(regole con `auto = false`) e' disponibile per l'utente via API.

---

## 11. Seed Data

### config.stati_pratiche

| codice | codice_interno | descrizione |
|--------|----------------|-------------|
| BOZZA | BOZZA | Pratica in bozza |
| APERTA | APERTA | Pratica aperta |
| SOSPESA | SOSPESA | Pratica sospesa |
| CHIUSA | CHIUSA | Pratica chiusa |
| ANNULLATA | ANNULLATA | Pratica annullata |

### config.stati_flussi_pratiche

| codice | codice_interno | descrizione |
|--------|----------------|-------------|
| DA_ESEGUIRE | DA_ESEGUIRE | Flusso da eseguire |
| IN_CORSO | IN_CORSO | Flusso in corso |
| COMPLETATO | COMPLETATO | Flusso completato |
| SOSPESO | SOSPESO | Flusso sospeso |
| ANNULLATO | ANNULLATO | Flusso annullato |
| ERRORE | ERRORE | Flusso in errore |

### config.priorita_pratiche

| codice | codice_interno | sequenza | descrizione |
|--------|----------------|----------|-------------|
| BASSA | BASSA | 10 | Priorita' bassa |
| NORMALE | NORMALE | 20 | Priorita' normale |
| ALTA | ALTA | 30 | Priorita' alta |
| URGENTE | URGENTE | 40 | Priorita' urgente |

### config.tipi_nota

| codice | codice_interno | descrizione |
|--------|----------------|-------------|
| GENERALE | GENERALE | Nota generale |
| INTERNA | INTERNA | Nota interna |
| CLIENTE | CLIENTE | Nota per il cliente |
| TECNICA | TECNICA | Nota tecnica |
| LEGALE | LEGALE | Nota legale |

### config.tipi_allegato

| codice | codice_interno | descrizione |
|--------|----------------|-------------|
| DOCUMENTO | DOCUMENTO | Documento generico |
| IMMAGINE | IMMAGINE | Immagine |
| MODULO | MODULO | Modulo/template |
| CONTRATTO | CONTRATTO | Contratto |
| FATTURA | FATTURA | Fattura |
| VERBALE | VERBALE | Verbale |
| CERTIFICATO | CERTIFICATO | Certificato |
| ALTRO | ALTRO | Altro tipo |

### config.canali_pratiche

| codice | codice_interno | descrizione |
|--------|----------------|-------------|
| WEB_CLIENTI | WEB_CLIENTI | Portale web clienti |
| APP_TECNICA | APP_TECNICA | Applicazione tecnica |
| PORTALE_FORNITORI | PORTALE_FORNITORI | Portale fornitori |

### config.messaggi_errore

| codice | causa | soluzione |
|--------|-------|-----------|
| PRATICHE_PREREQUISITI_NON_SODDISFATTI | Prerequisiti obbligatori non completati | Completare i flussi prerequisito prima di procedere |

---

## 12. Evoluzione: Sospensione e Tempi

> Stato: **analisi**. Queste tabelle non sono ancora nello schema.
> Prerequisiti: nucleo pratiche completo (13 tabelle + 5 funzioni), seed stati con SOSPESO.
> Documento di analisi: `docs/it/dev/work-in-progress/analisi-gestione-operativa-attivita.md`

### 12.1 pratiche.sospensioni

Registra i periodi di fermo di una pratica o di un singolo flusso.
Ogni riga e' un intervallo aperto (data_fine NULL = sospensione ancora attiva).

| Colonna | Tipo | Note |
| ------- | ---- | ---- |
| `id` | BIGINT PK | GENERATED ALWAYS AS IDENTITY |
| `pratica_id` | BIGINT NOT NULL | FK a `pratiche.pratiche` |
| `flusso_id` | BIGINT | FK a `pratiche.flussi` (NULL = sospensione intera pratica) |
| `data_inizio` | TIMESTAMPTZ NOT NULL | Inizio sospensione |
| `data_fine` | TIMESTAMPTZ | Fine sospensione (NULL = attiva) |
| `data_riattivazione_prevista` | DATE | Per riattivazione automatica via job pgAgent |
| `motivo` | TEXT NOT NULL | Motivazione obbligatoria |
| `data_insert` | TIMESTAMPTZ | audit |
| `user_insert` | TEXT | audit |

**Vincoli:**

- CHECK: `data_fine IS NULL OR data_fine > data_inizio`
- CHECK: `flusso_id IS NULL OR pratica_id = (SELECT pratica_id FROM pratiche.flussi WHERE id = flusso_id)` — coerenza pratica/flusso
- Un solo record con `data_fine IS NULL` per combinazione pratica_id + flusso_id (UNIQUE parziale)

**Trigger:**

- AFTER INSERT: se `flusso_id IS NULL` (sospensione pratica), tutti i flussi attivi (DA_ESEGUIRE, IN_CORSO) passano a SOSPESO automaticamente. Il giornale registra STATO_CAMBIATO per la pratica e FLUSSO_STATO_CAMBIATO per ogni flusso coinvolto.
- AFTER UPDATE OF data_fine (riattivazione): se `flusso_id IS NULL`, i flussi precedentemente sospesi tornano allo stato che avevano prima della sospensione (salvato nel `dettaglio` JSONB del giornale). La pratica torna ad APERTA.

**Job pgAgent:**

- Job schedulato giornaliero: cerca sospensioni con `data_riattivazione_prevista <= CURRENT_DATE` e `data_fine IS NULL`, imposta `data_fine = NOW()`. Il trigger di riattivazione fa il resto.
- Pattern: `fn_run_and_log` come da guida tracciamento processi.

### 12.2 pratiche.formule_tempo

Soglie temporali per semafori warning/critico, configurabili per tipo prestazione e/o template flusso.

| Colonna | Tipo | Note |
| ------- | ---- | ---- |
| `id` | INTEGER PK | GENERATED ALWAYS AS IDENTITY |
| `tipo_prestazione_id` | INTEGER NOT NULL | FK a `pratiche.tipi_prestazione` |
| `template_flusso_id` | INTEGER | FK a `pratiche.template_flussi` (NULL = formula sulla pratica intera) |
| `giorni_warning` | INTEGER NOT NULL | Soglia giallo (giorni rimanenti) |
| `giorni_critico` | INTEGER NOT NULL | Soglia rosso (giorni rimanenti) |
| `attivo` | BOOLEAN NOT NULL DEFAULT true | |
| `descrizione` | TEXT | |
| `meta` | JSONB NOT NULL DEFAULT '{}' | |
| `data_insert` | TIMESTAMPTZ | audit |
| `user_insert` | TEXT | audit |
| `data_update` | TIMESTAMPTZ | audit |
| `user_update` | TEXT | audit |

**Vincoli:**

- CHECK: `giorni_warning > giorni_critico` (warning scatta prima del critico)
- CHECK: `giorni_warning > 0 AND giorni_critico > 0`
- UNIQUE su `(tipo_prestazione_id, template_flusso_id)` — una formula per combinazione

### 12.3 Funzione fn_calcola_tempo_netto

Funzione **check** (pura, STABLE): calcola i giorni netti trascorsi per un flusso o una pratica, escludendo i periodi di sospensione.

- Input: `p_pratica_id BIGINT`, `p_flusso_id BIGINT DEFAULT NULL`
- Output: `INTEGER` (giorni netti)
- Logica: `(data corrente - data_insert) - SUM(periodi sospensione chiusi) - (eventuale sospensione aperta)`

### 12.4 Attivita' backend Django

| Attivita' | Prerequisito | File coinvolti |
| --------- | ------------ | -------------- |
| Aggiungere `SospensioneRow` a `types.py` | DDL sospensioni | `apps/pratiche/types.py` |
| Aggiungere `FormulaTempoRow` a `types.py` | DDL formule_tempo | `apps/pratiche/types.py` |
| Metodo `sospendi_pratica(pratica_id, motivo, data_riattivazione)` | DDL + trigger | `apps/pratiche/services/pratiche_service.py` |
| Metodo `riattiva_pratica(pratica_id)` | DDL + trigger | `apps/pratiche/services/pratiche_service.py` |
| Metodo `sospendi_flusso(flusso_id, motivo, data_riattivazione)` | DDL + trigger | `apps/pratiche/services/pratiche_service.py` |
| Metodo `riattiva_flusso(flusso_id)` | DDL + trigger | `apps/pratiche/services/pratiche_service.py` |
| Repository: INSERT/UPDATE sospensioni, SELECT formule_tempo | DDL | `apps/pratiche/db/pratiche_repository.py` |
| Endpoint `POST /api/v1/pratiche/{id}/sospendi/` | Service + repository | `apps/pratiche/api/views.py`, `urls_v1.py` |
| Endpoint `POST /api/v1/pratiche/{id}/riattiva/` | Service + repository | `apps/pratiche/api/views.py`, `urls_v1.py` |
| Endpoint `POST /api/v1/pratiche/{id}/flussi/{fid}/sospendi/` | Service + repository | `apps/pratiche/api/views.py`, `urls_v1.py` |
| Endpoint `POST /api/v1/pratiche/{id}/flussi/{fid}/riattiva/` | Service + repository | `apps/pratiche/api/views.py`, `urls_v1.py` |
| Test unitari service (sospendi/riattiva pratica e flusso) | Service | `apps/pratiche/tests/services/` |
| Test unitari API (4 endpoint) | Views | `apps/pratiche/tests/api/` |

**Ordine di implementazione:**

1. DDL `sospensioni` + seed (Liquibase)
2. DDL `formule_tempo` + seed (Liquibase)
3. Trigger sospensione pratica → propagazione flussi (Liquibase `20_code/`)
4. Trigger riattivazione → ripristino stati (Liquibase `20_code/`)
5. Funzione `fn_calcola_tempo_netto` (Liquibase `20_code/`)
6. Test pgTAP per sospensione/riattivazione e calcolo tempo
7. Backend: types, repository, service, endpoint, test Django
8. Job pgAgent riattivazione automatica

---

## 13. Evoluzione: Macchina a Stati Rigida

> Stato: **da implementare**. Approccio scelto: guard nel DB (coerente con filosofia DB-first).
> Prerequisiti: nucleo pratiche completo, seed stati con tutti i codici_interni.

### 13.1 Problema

Oggi le transizioni di stato di pratiche e flussi non sono validate ne' dal DB ne' dal service.
Il codice `cambia_stato_flusso(flusso_id, nuovo_stato)` accetta qualsiasi stringa.
Nulla impedisce transizioni prive di senso come COMPLETATO → DA_ESEGUIRE o ANNULLATO → IN_CORSO.

### 13.2 Transizioni ammesse

#### Pratica

```text
BOZZA      → APERTA, ANNULLATA
APERTA     → SOSPESA, CHIUSA, ANNULLATA
SOSPESA    → APERTA
CHIUSA     → (terminale)
ANNULLATA  → (terminale)
```

#### Flusso

```text
DA_ESEGUIRE  → IN_CORSO, ANNULLATO
IN_CORSO     → COMPLETATO, SOSPESO, ERRORE
SOSPESO      → IN_CORSO, DA_ESEGUIRE
ERRORE       → (terminale)
COMPLETATO   → (terminale)
ANNULLATO    → (terminale)
```

> **Nota**: SOSPESO → DA_ESEGUIRE e' previsto per la riattivazione automatica (job pgAgent, sezione 12).
> SOSPESO → IN_CORSO e' per la ripresa manuale da parte dell'operatore.

### 13.3 Implementazione DB (Opzione A — scelta)

Trigger function BEFORE UPDATE OF stato_id su `pratiche.pratiche` e `pratiche.flussi`.
La matrice di transizioni e' codificata in una tabella config o direttamente nel trigger.

#### Opzione tabella config (consigliata)

Due tabelle config per le transizioni ammesse:

**config.transizioni_stati_pratiche**

| Colonna | Tipo | Note |
| ------- | ---- | ---- |
| `id` | INTEGER PK | GENERATED ALWAYS AS IDENTITY |
| `stato_da_id` | INTEGER NOT NULL | FK a `config.stati_pratiche` |
| `stato_a_id` | INTEGER NOT NULL | FK a `config.stati_pratiche` |
| `attivo` | BOOLEAN NOT NULL DEFAULT true | Disattivabile senza deploy |

- UNIQUE su `(stato_da_id, stato_a_id)`
- CHECK: `stato_da_id <> stato_a_id`

**config.transizioni_stati_flussi_pratiche**

Stessa struttura, FK a `config.stati_flussi_pratiche`.

#### Trigger function

```sql
-- pratiche.trgfn_pratiche_guard_transizione()
-- Scopo: blocca transizioni di stato non ammesse per le pratiche.
CREATE OR REPLACE FUNCTION pratiche.trgfn_pratiche_guard_transizione()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.stato_id = NEW.stato_id THEN
        RETURN NEW;  -- nessuna transizione, niente da validare
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM config.transizioni_stati_pratiche
        WHERE stato_da_id = OLD.stato_id
          AND stato_a_id = NEW.stato_id
          AND attivo = true
    ) THEN
        PERFORM script.fn_log_and_raise_error(
            'PRATICHE_TRANSIZIONE_NON_AMMESSA',
            format('Transizione pratica non ammessa: %s → %s',
                   OLD.stato_id, NEW.stato_id)
        );
    END IF;
    RETURN NEW;
END;
$$;
```

Stessa logica per `pratiche.trgfn_flussi_guard_transizione()` con la tabella flussi.

#### Trigger

| Nome | Timing | Tabella | Evento |
| ---- | ------ | ------- | ------ |
| `trg_pratiche_a10_guard_transizione_upd` | BEFORE | `pratiche.pratiche` | UPDATE OF stato_id |
| `trg_flussi_a10_guard_transizione_upd` | BEFORE | `pratiche.flussi` | UPDATE OF stato_id |

Fase `_a10_`: guard, eseguito prima dei trigger giornale (`_z90_`).

### 13.4 Seed data

Tabella `config.transizioni_stati_pratiche` (6 righe):

| da | a |
| -- | - |
| BOZZA | APERTA |
| BOZZA | ANNULLATA |
| APERTA | SOSPESA |
| APERTA | CHIUSA |
| APERTA | ANNULLATA |
| SOSPESA | APERTA |

Tabella `config.transizioni_stati_flussi_pratiche` (7 righe):

| da | a |
| -- | - |
| DA_ESEGUIRE | IN_CORSO |
| DA_ESEGUIRE | ANNULLATO |
| IN_CORSO | COMPLETATO |
| IN_CORSO | SOSPESO |
| IN_CORSO | ERRORE |
| SOSPESO | IN_CORSO |
| SOSPESO | DA_ESEGUIRE |

### 13.5 Messaggi errore

| codice | causa | soluzione |
| ------ | ----- | --------- |
| PRATICHE_TRANSIZIONE_NON_AMMESSA | Transizione stato pratica non consentita | Verificare la sequenza di stati corretta per la pratica |
| FLUSSI_TRANSIZIONE_NON_AMMESSA | Transizione stato flusso non consentita | Verificare la sequenza di stati corretta per il flusso |

### 13.6 Attivita' backend Django

| Attivita' | Prerequisito | File coinvolti |
| --------- | ------------ | -------------- |
| Test pgTAP: transizioni ammesse e bloccate | DDL + trigger + seed | `db/pgtap/pratiche/` |
| Gestione errore transizione nel middleware | Codice errore registrato | `apps/core/services/error_policies.py` |
| Test unitari: verifica che ServiceError corretta arrivi dall'API | Middleware | `apps/pratiche/tests/api/` |

### 13.7 Vantaggi dell'approccio tabella config

- **Configurabile senza deploy**: aggiungere/disattivare transizioni e' un UPDATE su config
- **Impossibile bypassare**: vale per API, service, query dirette, migration
- **Auditabile**: le transizioni ammesse sono dati, non codice
- **Coerente** con il pattern config del progetto (stati, priorita', tipi sono tutti in config)

### 13.8 Ordine di implementazione

1. DDL `config.transizioni_stati_pratiche` + `config.transizioni_stati_flussi_pratiche` (Liquibase)
2. Seed data transizioni (Liquibase `80_data/`)
3. Seed messaggi errore in `config.messaggi_errore` (Liquibase `80_data/`)
4. Trigger functions guard (Liquibase `20_code/`)
5. Trigger su pratiche e flussi (Liquibase `20_code/`)
6. Test pgTAP: ogni transizione ammessa passa, ogni transizione vietata solleva errore
7. Backend: error policy + test API

---

*Documento di sviluppo — Schema `pratiche` — ZeroERP (marzo 2026)*
