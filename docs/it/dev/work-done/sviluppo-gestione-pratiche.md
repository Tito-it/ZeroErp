# ZeroERP — Schema `pratiche` — Motore Workflow

> **STATO: COMPLETATO (v1)** — Spostato in work-done.
> Il completamento del modulo (collegamento ruolo/istanza, display fields, note, allegati,
> codice prefisso) e' nel piano v2: `work-done/gestione-pratiche-v2.md`
>
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
- **pre_attivazione**: BOOLEAN NOT NULL DEFAULT true — la prestazione e' applicabile nella fase precedente all'attivazione del cliente/servizio
- **post_attivazione**: BOOLEAN NOT NULL DEFAULT true — la prestazione e' applicabile nella fase successiva all'attivazione

Le quattro combinazioni coprono tutti gli scenari operativi:

| pre_attivazione | post_attivazione | Significato | Esempio |
| --------------- | ---------------- | ----------- | ------- |
| true | true | Universale, applicabile sempre | Reclamo, Richiesta informazioni |
| true | false | Solo pre-attivazione | Sopralluogo iniziale, Preventivo |
| false | true | Solo post-attivazione | Manutenzione, Lettura contatore |
| false | false | Pratica interna, non legata al cliente | Audit interno, Manutenzione impianto |

> **Default entrambi `true`**: tutto l'esistente funziona senza modifiche.

**Regole di applicabilita' (guard lato service/API):**

La validazione avviene nel service Django alla creazione della pratica, in base allo stato
del billing_account (BA) del soggetto associato:

| Combinazione | Condizione di ammissibilita' |
| ------------ | ---------------------------- |
| `pre_attivazione = true` | Il soggetto non ha BA attivo per l'emittente, oppure il BA ha `data_attivazione IS NULL` (cliente non ancora attivato) |
| `post_attivazione = true` | Il soggetto ha un BA attivo per l'emittente con `data_attivazione IS NOT NULL` (cliente attivato) |
| `false / false` | Nessun vincolo sul soggetto — la pratica e' interna, il soggetto puo' essere NULL |

> Il guard e' nel service, non nel DB: la logica dipende dallo stato del BA che e' in
> `anagrafiche.billing_account`, e un trigger cross-schema sarebbe fragile.
> Il service deve verificare la coerenza prima dell'INSERT e restituire errore chiaro.

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
- **canale_origine_id**: INTEGER — FK a `config.canali_pratiche`: sorgente esterna, informativo per reportistica (NULL = creata internamente)
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

> Stato: **da implementare**. Queste tabelle non sono ancora nello schema.
> Prerequisiti: nucleo pratiche completo (13 tabelle + 5 funzioni), seed stati con SOSPESO.
> Documento di analisi: `docs/it/dev/work-in-progress/analisi-gestione-operativa-attivita.md`
>
> Review conformita' (06-03-2026): allineato a standard progetto — vedi note sotto ogni tabella.

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
| `storicizza` | BOOLEAN NOT NULL DEFAULT false | Pattern standard tabelle operative |
| `tx_id` | UUID | Transaction ID — pattern standard tabelle operative |
| `data_insert` | TIMESTAMPTZ | audit |
| `user_insert` | TEXT | audit |
| `data_update` | TIMESTAMPTZ | audit |
| `user_update` | TEXT | audit |

> **Note conformita':**
>
> - Aggiunti `data_update`/`user_update`: la tabella e' aggiornabile (riattivazione imposta `data_fine`).
>   Con soli 2 campi audit si perdeva traccia dell'aggiornamento.
> - Aggiunto `tx_id UUID`: coerenza con le tabelle operative del nucleo (`pratiche`, `flussi`).
> - Aggiunto `storicizza BOOLEAN`: coerenza con il pattern del nucleo pratiche.

**Vincoli:**

- CHECK: `data_fine IS NULL OR data_fine > data_inizio`
- Un solo record con `data_fine IS NULL` per combinazione pratica_id + flusso_id (UNIQUE parziale)

**Trigger guard coerenza pratica/flusso (fase `_a10_`):**

> Il vincolo originale era una CHECK con subquery
> (`flusso_id IS NULL OR pratica_id = (SELECT pratica_id FROM pratiche.flussi WHERE id = flusso_id)`).
> PostgreSQL **non ammette CHECK con subquery** — deve essere implementato come trigger
> BEFORE INSERT/UPDATE.

```sql
-- pratiche.trgfn_sospensioni_guard_coerenza_flusso()
-- Scopo: verifica che flusso_id appartenga alla stessa pratica_id della sospensione.
CREATE OR REPLACE FUNCTION pratiche.trgfn_sospensioni_guard_coerenza_flusso()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    v_pratica_flusso BIGINT;
BEGIN
    IF NEW.flusso_id IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT pratica_id INTO v_pratica_flusso
    FROM pratiche.flussi WHERE id = NEW.flusso_id;

    IF v_pratica_flusso IS NULL OR v_pratica_flusso <> NEW.pratica_id THEN
        PERFORM script.fn_log_and_raise_error(
            'SOSPENSIONI_FLUSSO_NON_COERENTE',
            format('Il flusso %s non appartiene alla pratica %s',
                   NEW.flusso_id, NEW.pratica_id)
        );
    END IF;
    RETURN NEW;
END;
$$;
```

| Nome trigger | Timing | Evento | Funzione |
| ------------ | ------ | ------ | -------- |
| `trg_sospensioni_a10_guard_coerenza_flusso_ins_upd` | BEFORE | INSERT, UPDATE OF flusso_id | `pratiche.trgfn_sospensioni_guard_coerenza_flusso()` |

**Trigger business-specific:**

| Nome trigger | Timing | Evento | Funzione | Scopo |
| ------------ | ------ | ------ | -------- | ----- |
| `trg_sospensioni_a10_guard_coerenza_flusso_ins_upd` | BEFORE | INSERT, UPDATE OF flusso_id | `trgfn_sospensioni_guard_coerenza_flusso()` | Coerenza pratica/flusso |
| `trg_sospensioni_z90_propaga_sospensione_ins` | AFTER | INSERT | `trgfn_sospensioni_propaga()` | Propaga sospensione ai flussi attivi |
| `trg_sospensioni_z90_propaga_riattivazione_upd` | AFTER | UPDATE OF data_fine | `trgfn_sospensioni_riattiva()` | Ripristina stati precedenti alla riattivazione |
| `trg_sospensioni_z90_giornale_ins` | AFTER | INSERT | `trgfn_sospensioni_giornale_ins()` | Registra SOSPENSIONE_REGISTRATA nel giornale |
| `trg_sospensioni_z90_giornale_riattivazione_upd` | AFTER | UPDATE OF data_fine | `trgfn_sospensioni_giornale_riattivazione()` | Registra SOSPENSIONE_CHIUSA nel giornale |

Dettaglio comportamento:

- **AFTER INSERT**: se `flusso_id IS NULL` (sospensione pratica), tutti i flussi attivi (DA_ESEGUIRE, IN_CORSO) passano a SOSPESO automaticamente. I trigger giornale dei flussi registrano FLUSSO_STATO_CAMBIATO per ogni flusso coinvolto.
- **AFTER UPDATE OF data_fine** (riattivazione): se `flusso_id IS NULL`, i flussi precedentemente sospesi tornano allo stato che avevano prima della sospensione (salvato nel `dettaglio` JSONB del giornale). La pratica torna ad APERTA.

**Nuove azioni giornale:**

> Il giornale necessita di due nuove azioni nel CHECK della colonna `azione`:
>
> - `SOSPENSIONE_REGISTRATA` — traccia creazione sospensione con motivo e date nel dettaglio JSONB
> - `SOSPENSIONE_CHIUSA` — traccia chiusura sospensione con data_fine nel dettaglio JSONB
>
> Le azioni STATO_CAMBIATO / FLUSSO_STATO_CAMBIATO coprono gia' le transizioni di stato
> propagate dalla sospensione, ma le nuove azioni permettono di tracciare direttamente
> l'evento sospensione con il suo motivo e la data di riattivazione prevista.

**Job pgAgent:**

- Job schedulato giornaliero: cerca sospensioni con `data_riattivazione_prevista <= CURRENT_DATE` e `data_fine IS NULL`, imposta `data_fine = NOW()`. Il trigger di riattivazione fa il resto.
- Pattern: `fn_run_and_log` come da guida tracciamento processi.

### 12.2 pratiche.formule_tempo

Soglie temporali e tempo massimo di esecuzione, configurabili per tipo prestazione
con coppia di template flusso **da/a**. Le formule misurano il tempo impiegato
per passare dal completamento di un flusso (flusso_da) al completamento di un altro (flusso_a),
e servono a due scopi:

- **Semafori**: segnalare warning/critico quando i giorni rimanenti alla scadenza
  scendono sotto le soglie configurate
- **Tempo massimo**: definire il numero di giorni previsti per transitare
  da flusso_da COMPLETATO a flusso_a COMPLETATO. Al completamento del flusso_a
  il trigger calcola automaticamente il tempo netto impiegato e lo confronta con `giorni_esecuzione`

| Colonna | Tipo | Note |
| ------- | ---- | ---- |
| `id` | INTEGER PK | GENERATED ALWAYS AS IDENTITY |
| `tipo_prestazione_id` | INTEGER NOT NULL | FK a `pratiche.tipi_prestazione` |
| `template_flusso_da_id` | INTEGER NOT NULL | FK a `pratiche.template_flussi` — flusso di partenza (il suo COMPLETATO avvia il conteggio) |
| `template_flusso_a_id` | INTEGER NOT NULL | FK a `pratiche.template_flussi` — flusso di arrivo (il suo COMPLETATO chiude il conteggio) |
| `giorni_esecuzione` | INTEGER NOT NULL | Tempo massimo previsto in giorni (al netto delle sospensioni) |
| `giorni_warning` | INTEGER NOT NULL | Soglia giallo (giorni rimanenti rispetto a `giorni_esecuzione`) |
| `giorni_critico` | INTEGER NOT NULL | Soglia rosso (giorni rimanenti rispetto a `giorni_esecuzione`) |
| `attivo` | BOOLEAN NOT NULL DEFAULT true | |
| `descrizione` | TEXT | |
| `meta` | JSONB NOT NULL DEFAULT '{}' | |
| `data_insert` | TIMESTAMPTZ | audit |
| `user_insert` | TEXT | audit |
| `data_update` | TIMESTAMPTZ | audit |
| `user_update` | TEXT | audit |

**Vincoli:**

- CHECK: `giorni_esecuzione > 0`
- CHECK: `giorni_warning > giorni_critico` (warning scatta prima del critico)
- CHECK: `giorni_warning > 0 AND giorni_critico > 0`
- CHECK: `giorni_warning < giorni_esecuzione` (la soglia warning deve stare dentro il tempo massimo)
- CHECK: `template_flusso_da_id <> template_flusso_a_id` (no self-reference: i due flussi devono essere distinti)
- UNIQUE su `(tipo_prestazione_id, template_flusso_da_id, template_flusso_a_id)` — una formula per combinazione da/a

### 12.3 pratiche.calcoli_tempo

Tabella di calcolo persistente collegata alla testata pratica. Misura il tempo impiegato
per transitare dal completamento di un flusso (flusso_da) al completamento di un altro (flusso_a),
alimentata automaticamente da trigger a due fasi:

- **Fase avvio**: quando il flusso_da va COMPLETATO, il trigger crea la riga con
  `data_inizio_calcolo = data_fine` del flusso_da e snapshot di `giorni_formula`
- **Fase completamento**: quando il flusso_a va COMPLETATO, il trigger popola
  `data_fine_calcolo = data_fine` del flusso_a, calcola i tempi e imposta `sforato`

> **Nota concettuale:** non si misura il tempo di esecuzione di un singolo flusso,
> ma il tempo trascorso **tra** il completamento del flusso_da e il completamento del flusso_a.
> Questo permette di tracciare performance end-to-end di sotto-processi
> (es. "dal completamento della Verifica al completamento dell'Installazione").

| Colonna | Tipo | Note |
| ------- | ---- | ---- |
| `id` | BIGINT PK | GENERATED ALWAYS AS IDENTITY |
| `pratica_id` | BIGINT NOT NULL | FK a `pratiche.pratiche` (testata) — immutabile |
| `flusso_da_id` | BIGINT NOT NULL | FK a `pratiche.flussi` — flusso di partenza (il suo COMPLETATO avvia il conteggio) — immutabile |
| `flusso_a_id` | BIGINT NOT NULL | FK a `pratiche.flussi` — flusso di arrivo (il suo COMPLETATO chiude il conteggio) — immutabile |
| `formula_tempo_id` | INTEGER NOT NULL | FK a `pratiche.formule_tempo` — snapshot della formula applicata — immutabile |
| `data_inizio_calcolo` | TIMESTAMPTZ NOT NULL | `data_fine` del flusso_da (quando il flusso_da e' andato COMPLETATO) |
| `data_fine_calcolo` | TIMESTAMPTZ | `data_fine` del flusso_a (quando il flusso_a e' andato COMPLETATO). NULL = in corso |
| `giorni_lordi` | INTEGER | Giorni di calendario totali (`data_fine_calcolo - data_inizio_calcolo`). NULL mentre in corso |
| `giorni_sospensione` | INTEGER | Giorni totali di sospensione della pratica nel periodo da/a. NULL mentre in corso |
| `giorni_netti` | INTEGER | `giorni_lordi - giorni_sospensione`. NULL mentre in corso |
| `giorni_formula` | INTEGER NOT NULL | Snapshot di `formule_tempo.giorni_esecuzione` al momento dell'avvio — immutabile |
| `sforato` | BOOLEAN | `true` se `giorni_netti > giorni_formula`. NULL mentre in corso |
| `tx_id` | UUID | Transaction ID |
| `data_insert` | TIMESTAMPTZ | audit |
| `user_insert` | TEXT | audit |
| `data_update` | TIMESTAMPTZ | audit |
| `user_update` | TEXT | audit |

**Vincoli:**

- CHECK: `data_fine_calcolo IS NULL OR data_fine_calcolo > data_inizio_calcolo`
- CHECK: `giorni_formula > 0`
- CHECK: `flusso_da_id <> flusso_a_id` (i due flussi devono essere distinti)
- UNIQUE su `(pratica_id, flusso_da_id, flusso_a_id, formula_tempo_id)` — un solo calcolo per combinazione da/a

**Immutabilita' dei riferimenti:**

I campi `pratica_id`, `flusso_da_id`, `flusso_a_id`, `formula_tempo_id`, `giorni_formula`
e `data_inizio_calcolo` sono immutabili dopo l'inserimento. Un trigger guard `_a10_` blocca
UPDATE su queste colonne.

| Nome trigger | Timing | Evento | Funzione | Scopo |
| ------------ | ------ | ------ | -------- | ----- |
| `trg_calcoli_tempo_a10_guard_immutabili_upd` | BEFORE | UPDATE OF pratica_id, flusso_da_id, flusso_a_id, formula_tempo_id, giorni_formula, data_inizio_calcolo | `trgfn_calcoli_tempo_guard_immutabili()` | Blocca modifica dei campi di riferimento |

> I soli campi aggiornabili sono: `data_fine_calcolo`, `giorni_lordi`, `giorni_sospensione`,
> `giorni_netti`, `sforato`, `tx_id` e i campi audit.

### 12.4 Funzioni DB

#### 12.4.1 pratiche.fn_calcola_tempo_netto_da_a

Funzione **check** (pura, STABLE): calcola i giorni netti trascorsi tra due flussi di una pratica,
escludendo i periodi di sospensione. Non misura il tempo di un singolo flusso, ma il tempo
intercorso dal completamento del flusso_da al momento corrente (o al completamento del flusso_a).

- Input: `p_pratica_id BIGINT`, `p_flusso_da_id BIGINT`, `p_flusso_a_id BIGINT`
- Output: `INTEGER` (giorni netti)
- Logica:
  - Recupera `data_fine` del flusso_da come punto di partenza
  - Se il flusso_a e' gia' COMPLETATO, usa `data_fine` del flusso_a come punto di arrivo;
    altrimenti usa `NOW()`
  - Calcola giorni lordi = punto_arrivo - punto_partenza
  - Sottrae i giorni di sospensione della pratica ricadenti nel periodo (da tabella `sospensioni`)
  - Restituisce `giorni_lordi - giorni_sospensione`

#### 12.4.2 pratiche.fn_valuta_tempo_esecuzione_da_a

Funzione **check** (pura, STABLE): confronta il tempo netto trascorso tra due flussi
con la formula tempo configurata. Restituisce lo stato temporale corrente.

- Input: `p_pratica_id BIGINT`, `p_flusso_da_id BIGINT`, `p_flusso_a_id BIGINT`
- Output: `TABLE(giorni_netti INTEGER, giorni_esecuzione INTEGER, giorni_rimanenti INTEGER, stato_tempo TEXT)`
- `stato_tempo`: `OK`, `WARNING`, `CRITICO`, `SFORATO`
- Logica:
  - Recupera la formula matching in `formule_tempo` per `tipo_prestazione_id` + `template_flusso_da_id` + `template_flusso_a_id`
  - Chiama `fn_calcola_tempo_netto_da_a` per i giorni netti
  - `giorni_rimanenti = giorni_esecuzione - giorni_netti`
  - Se `giorni_rimanenti <= 0` → `SFORATO`
  - Se `giorni_rimanenti <= giorni_critico` → `CRITICO`
  - Se `giorni_rimanenti <= giorni_warning` → `WARNING`
  - Altrimenti → `OK`
- Se non esiste formula configurata, restituisce NULL (nessuna valutazione)

#### 12.4.3 Trigger di tracciamento tempo (due fasi — modello da/a)

Un unico trigger AFTER UPDATE OF stato_id su `pratiche.flussi` (WHEN NEW = COMPLETATO)
gestisce entrambe le fasi del ciclo di vita dei calcoli tempo. Quando un flusso va COMPLETATO,
il trigger verifica se quel flusso e' referenziato come `flusso_da` o `flusso_a`
nelle formule configurate:

| Nome trigger | Timing | Evento | Funzione | Scopo |
| ------------ | ------ | ------ | -------- | ----- |
| `trg_flussi_z90_calcolo_tempo_completamento_upd` | AFTER | UPDATE OF stato_id (WHEN NEW = COMPLETATO) | `trgfn_flussi_calcolo_tempo_completamento()` | Crea e/o chiude righe in `calcoli_tempo` secondo il modello da/a |

**Logica della trigger function** (`trgfn_flussi_calcolo_tempo_completamento`):

Il flusso appena COMPLETATO puo' essere referenziato come partenza (flusso_da) e/o
come arrivo (flusso_a) in formule diverse. Il trigger gestisce entrambi i casi:

1. **Il flusso COMPLETATO e' un flusso_da** (avvio conteggio):
   - Cerca in `formule_tempo` tutte le formule con `template_flusso_da_id` = template del flusso appena completato
     e `tipo_prestazione_id` = tipo della pratica, con `attivo = true`
   - Per ogni formula trovata: cerca nella stessa pratica il flusso corrispondente al `template_flusso_a_id`
   - Se il flusso_a esiste: INSERT in `calcoli_tempo` con `data_inizio_calcolo = data_fine` del flusso_da,
     `giorni_formula` = snapshot di `formule_tempo.giorni_esecuzione`
   - Se il flusso_a non esiste ancora nella pratica: nessuna azione (il calcolo partira' quando il flusso_a verra' creato — vedi nota sotto)

2. **Il flusso COMPLETATO e' un flusso_a** (chiusura conteggio):
   - Cerca la riga aperta in `calcoli_tempo` per `pratica_id` + `flusso_a_id` con `data_fine_calcolo IS NULL`
   - Se esiste: UPDATE con `data_fine_calcolo = data_fine` del flusso_a, calcola `giorni_lordi`
     (`data_fine_calcolo - data_inizio_calcolo`), `giorni_sospensione` (da tabella `sospensioni`
     per il periodo da/a), `giorni_netti`, `sforato`
   - Se non esiste riga: nessuna azione
   - Registra nel giornale come dettaglio JSONB arricchito:
     `{"flusso_da_id": X, "flusso_a_id": Y, "giorni_netti": N, "giorni_lordi": L, "giorni_sospensione": S, "giorni_formula": M, "sforato": true/false}`

> **Nota — Ordine dei completamenti**
>
> Il modello da/a presuppone che il flusso_da si completi prima del flusso_a.
> Se il flusso_a viene completato prima che esista una riga in `calcoli_tempo`
> (perche' il flusso_da non era ancora completato), il trigger non registra nulla.
> Quando successivamente il flusso_da sara' completato, il trigger (punto 1) creera'
> la riga di avvio ma il flusso_a risultera' gia' COMPLETATO: in questo caso il trigger
> deve anche chiudere immediatamente la riga calcolando i tempi dal `data_fine` del flusso_da
> al `data_fine` del flusso_a.
>
> **Nota — Evoluzione futura: calcolo dinamico scadenze e segnalazioni**
>
> In una fase successiva si prevede di implementare:
>
> - Vista operativa che legge da `calcoli_tempo` le righe con `data_fine_calcolo IS NULL`
>   e ricalcola dinamicamente `giorni_netti` e `stato_tempo` tramite `fn_valuta_tempo_esecuzione_da_a`,
>   per alimentare la dashboard agenda attivita' (vedi `analisi-gestione-operativa-attivita.md`)
> - Segnalazioni automatiche (notifiche/alert) quando lo stato_tempo passa da OK a WARNING
>   o da WARNING a CRITICO, tramite job pgAgent periodico
> - Queste funzionalita' si appoggiano interamente su `calcoli_tempo`, `formule_tempo` e
>   sulle funzioni definite in questa sezione, senza modificarle

### 12.5 Attivita' backend Django

| Attivita' | Prerequisito | File coinvolti |
| --------- | ------------ | -------------- |
| Aggiungere `SospensioneRow` a `types.py` | DDL sospensioni | `apps/pratiche/types.py` |
| Aggiungere `FormulaTempoRow` a `types.py` | DDL formule_tempo | `apps/pratiche/types.py` |
| Aggiungere `CalcoloTempoRow` a `types.py` | DDL calcoli_tempo | `apps/pratiche/types.py` |
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

#### Ordine di implementazione

> Sostituito dal piano strutturato nella sezione 14. Questa lista resta come riferimento sintetico.

1. DDL `sospensioni` + seed (Liquibase)
2. DDL `formule_tempo` + seed (Liquibase)
3. Trigger sospensione pratica — propagazione flussi (Liquibase `20_code/`)
4. Trigger riattivazione — ripristino stati (Liquibase `20_code/`)
5. Funzione `fn_calcola_tempo_netto` (Liquibase `20_code/`)
6. Test pgTAP per sospensione/riattivazione e calcolo tempo
7. Backend: types, repository, service, endpoint, test Django
8. Job pgAgent riattivazione automatica

---

## 13. Evoluzione: Macchina a Stati Rigida

> Stato: **da implementare**. Approccio scelto: guard nel DB (coerente con filosofia DB-first).
> Prerequisiti: nucleo pratiche completo, seed stati con tutti i codici_interni.
>
> Review conformita' (06-03-2026): allineato a standard progetto — vedi note sotto ogni tabella.

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
DA_ESEGUIRE  → IN_CORSO, ANNULLATO, SOSPESO
IN_CORSO     → COMPLETATO, SOSPESO, ERRORE
SOSPESO      → IN_CORSO, DA_ESEGUIRE
ERRORE       → IN_CORSO (retry), ANNULLATO (abbandono)
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

#### config.transizioni_stati_pratiche

| Colonna | Tipo | Note |
| ------- | ---- | ---- |
| `id` | INTEGER PK | GENERATED ALWAYS AS IDENTITY |
| `stato_da_id` | INTEGER NOT NULL | FK a `config.stati_pratiche` |
| `stato_a_id` | INTEGER NOT NULL | FK a `config.stati_pratiche` |
| `attivo` | BOOLEAN NOT NULL DEFAULT true | Disattivabile senza deploy |
| `meta` | JSONB NOT NULL DEFAULT '{}' | Pattern standard config |
| `data_insert` | TIMESTAMPTZ | audit |
| `user_insert` | TEXT | audit |
| `data_update` | TIMESTAMPTZ | audit |
| `user_update` | TEXT | audit |

- UNIQUE su `(stato_da_id, stato_a_id)`
- CHECK: `stato_da_id <> stato_a_id`

> **Note conformita':** aggiunti audit fields (4 campi) e `meta JSONB` per coerenza
> con il precedente `config.stati_doc_fiscale_transizioni` che ha la stessa struttura.

#### config.transizioni_stati_flussi_pratiche

Stessa struttura, FK a `config.stati_flussi_pratiche`.

#### Trigger function

```sql
-- pratiche.trgfn_pratiche_guard_transizione()
-- Scopo: blocca transizioni di stato non ammesse per le pratiche.
-- Risolve i codici interni degli stati per messaggi di errore leggibili.
CREATE OR REPLACE FUNCTION pratiche.trgfn_pratiche_guard_transizione()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    v_codice_da config.stati_pratiche.codice_interno%TYPE;
    v_codice_a  config.stati_pratiche.codice_interno%TYPE;
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
        SELECT codice_interno INTO v_codice_da
        FROM config.stati_pratiche WHERE id = OLD.stato_id;

        SELECT codice_interno INTO v_codice_a
        FROM config.stati_pratiche WHERE id = NEW.stato_id;

        PERFORM script.fn_log_and_raise_error(
            'PRATICHE_TRANSIZIONE_NON_AMMESSA',
            format('Transizione pratica non ammessa: %s -> %s',
                   v_codice_da, v_codice_a)
        );
    END IF;
    RETURN NEW;
END;
$$;
```

Stessa logica per `pratiche.trgfn_flussi_guard_transizione()` con la tabella flussi
e `config.stati_flussi_pratiche`.

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
| DA_ESEGUIRE | SOSPESO |
| IN_CORSO | COMPLETATO |
| IN_CORSO | SOSPESO |
| IN_CORSO | ERRORE |
| SOSPESO | IN_CORSO |
| SOSPESO | DA_ESEGUIRE |
| ERRORE | IN_CORSO |
| ERRORE | ANNULLATO |

### 13.5 Messaggi errore

| codice | causa | soluzione |
| ------ | ----- | --------- |
| PRATICHE_TRANSIZIONE_NON_AMMESSA | Transizione stato pratica non consentita | Verificare la sequenza di stati corretta per la pratica |
| FLUSSI_TRANSIZIONE_NON_AMMESSA | Transizione stato flusso non consentita | Verificare la sequenza di stati corretta per il flusso |
| SOSPENSIONI_FLUSSO_NON_COERENTE | Il flusso indicato non appartiene alla pratica della sospensione | Verificare che flusso_id e pratica_id siano coerenti |

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

## 14. Piano di Implementazione Strutturato

> Aggiornato: 06-03-2026
> Prerequisiti globali: nucleo pratiche completo (13 tabelle + 5 funzioni + trigger business),
> seed stati con SOSPESO, backend app `pratiche` con service/repository/api funzionanti.

### Ordine complessivo

L'implementazione segue due blocchi paralleli (13 e' indipendente da 12) piu' un blocco finale condiviso.

```text
Blocco 0 (ALTER tipi_prestazione)             Blocco A (Sezione 13 — Macchina a stati)
============================================  ============================================
O1. ALTER tipi_prestazione (+2 boolean)       A1. DDL tabelle transizioni config
                                              A2. Seed transizioni (80_data/)
                                              A3. Seed messaggi errore (80_data/)
                                              A4. Trigger functions guard
                                              A5. Trigger su pratiche e flussi
                                              A6. Test pgTAP transizioni

Blocco B (Sezione 12 — Sospensioni e Tempi da/a)
============================================
B1. Aggiornare CHECK giornale (+2 azioni)
B2. DDL tabella sospensioni
B3. DDL tabella formule_tempo (modello da/a)
B4. Seed messaggi errore sospensioni
B5. Trigger guard coerenza flusso
B6. Trigger propagazione sospensione
B7. Trigger riattivazione
B8. Trigger giornale sospensione
B9. DDL tabella calcoli_tempo (modello da/a)
B10. Trigger guard immutabili calcoli_tempo
B11. Funzione fn_calcola_tempo_netto_da_a
B12. Funzione fn_valuta_tempo_esecuzione_da_a
B13. Trigger calcolo tempo completamento (unico, modello da/a)
B14. Test pgTAP sospensione/calcoli/tempo
B15. Job pgAgent riattivazione automatica

                Blocco C (Backend Django — dopo A e B)
                ============================================
                C1. Types (TypedDict)
                C2. Repository (sospensioni, formule, transizioni)
                C3. Service (sospendi/riattiva pratica/flusso)
                C4. Error policies
                C5. Endpoint API
                C6. Test unitari service
                C7. Test unitari API
```

---

### Blocco O — ALTER tipi_prestazione

| Step | Tipo | Descrizione | File Liquibase | Prerequisiti |
| ---- | ---- | ----------- | -------------- | ------------ |
| O1 | `00_schema` | ALTER `pratiche.tipi_prestazione`: aggiungere `pre_attivazione BOOLEAN NOT NULL DEFAULT true`, `post_attivazione BOOLEAN NOT NULL DEFAULT true` | `YYYYMMDD-NN-alter-tipi_prestazione_attivazione.yaml` | Tabella `pratiche.tipi_prestazione` esistente |

---

### Blocco A — Macchina a Stati Rigida (DB)

| Step | Tipo | Descrizione | File Liquibase | Prerequisiti |
| ---- | ---- | ----------- | -------------- | ------------ |
| A1 | `00_schema` | DDL `config.transizioni_stati_pratiche` + `config.transizioni_stati_flussi_pratiche` (PK INTEGER, FK, UNIQUE, CHECK, audit 4 campi, meta JSONB) | `YYYYMMDD-NN-create-transizioni_stati_pratiche.yaml` + `..._flussi_pratiche.yaml` | Tabelle `config.stati_pratiche` e `config.stati_flussi_pratiche` esistenti |
| A2 | `80_data` | Seed transizioni pratiche (6 righe) + flussi (7 righe) | `YYYYMMDD-NN-seed-transizioni_stati_pratiche.yaml` | A1 |
| A3 | `80_data` | Seed messaggi errore: `PRATICHE_TRANSIZIONE_NON_AMMESSA`, `FLUSSI_TRANSIZIONE_NON_AMMESSA` | `YYYYMMDD-NN-seed-messaggi_errore_transizioni.yaml` | `config.messaggi_errore` esistente |
| A4 | `20_code` | Trigger functions: `trgfn_pratiche_guard_transizione()`, `trgfn_flussi_guard_transizione()` | `YYYYMMDD-NN-create-trgfn_guard_transizione.yaml` | A1, A3 |
| A5 | `20_code` | Trigger: `trg_pratiche_a10_guard_transizione_upd`, `trg_flussi_a10_guard_transizione_upd` | `YYYYMMDD-NN-create-trg_guard_transizione.yaml` | A4 |
| A6 | pgTAP | Test: ogni transizione ammessa passa, ogni transizione vietata solleva errore | `db/pgtap/pratiche/test_transizioni_stati.sql` | A1-A5 |

---

### Blocco B — Sospensioni e Tempi da/a (DB)

| Step | Tipo | Descrizione | File Liquibase | Prerequisiti |
| ---- | ---- | ----------- | -------------- | ------------ |
| B1 | `20_code` | ALTER CHECK su `pratiche.giornale.azione`: aggiungere `SOSPENSIONE_REGISTRATA`, `SOSPENSIONE_CHIUSA` | `YYYYMMDD-NN-alter-giornale_azione_check.yaml` | Tabella `pratiche.giornale` esistente |
| B2 | `00_schema` | DDL `pratiche.sospensioni` (PK BIGINT, FK, UNIQUE parziale, CHECK data_fine, audit 4 campi, tx_id, storicizza) | `YYYYMMDD-NN-create-sospensioni.yaml` | Tabelle `pratiche.pratiche` e `pratiche.flussi` esistenti |
| B3 | `00_schema` | DDL `pratiche.formule_tempo` (PK INTEGER, FK x2 template_flusso_da/a, UNIQUE su tipo+da+a, CHECK giorni + da<>a, audit 4 campi, attivo, meta) | `YYYYMMDD-NN-create-formule_tempo.yaml` | Tabelle `pratiche.tipi_prestazione` e `pratiche.template_flussi` esistenti |
| B4 | `80_data` | Seed messaggio errore: `SOSPENSIONI_FLUSSO_NON_COERENTE` | `YYYYMMDD-NN-seed-messaggi_errore_sospensioni.yaml` | `config.messaggi_errore` esistente |
| B5 | `20_code` | Trigger function + trigger: `trgfn_sospensioni_guard_coerenza_flusso()` + `trg_sospensioni_a10_guard_coerenza_flusso_ins_upd` | `YYYYMMDD-NN-create-trgfn_sospensioni_guard.yaml` | B2, B4 |
| B6 | `20_code` | Trigger function + trigger: `trgfn_sospensioni_propaga()` + `trg_sospensioni_z90_propaga_sospensione_ins` | `YYYYMMDD-NN-create-trgfn_sospensioni_propaga.yaml` | B2, Blocco A (richiede macchina a stati per transizione SOSPESO) |
| B7 | `20_code` | Trigger function + trigger: `trgfn_sospensioni_riattiva()` + `trg_sospensioni_z90_propaga_riattivazione_upd` | `YYYYMMDD-NN-create-trgfn_sospensioni_riattiva.yaml` | B2, Blocco A |
| B8 | `20_code` | Trigger functions giornale: `trgfn_sospensioni_giornale_ins()`, `trgfn_sospensioni_giornale_riattivazione()` + trigger | `YYYYMMDD-NN-create-trgfn_sospensioni_giornale.yaml` | B1, B2 |
| B9 | `00_schema` | DDL `pratiche.calcoli_tempo` (PK BIGINT, FK flusso_da_id + flusso_a_id, UNIQUE su pratica+da+a+formula, CHECK da<>a, audit 4 campi, tx_id) | `YYYYMMDD-NN-create-calcoli_tempo.yaml` | B2, B3 |
| B10 | `20_code` | Trigger guard immutabilita': `trgfn_calcoli_tempo_guard_immutabili()` + `trg_calcoli_tempo_a10_guard_immutabili_upd` — blocca UPDATE su pratica_id, flusso_da_id, flusso_a_id, formula_tempo_id, giorni_formula, data_inizio_calcolo | `YYYYMMDD-NN-create-trgfn_calcoli_tempo_guard.yaml` | B9 |
| B11 | `20_code` | Funzione `pratiche.fn_calcola_tempo_netto_da_a(p_pratica_id, p_flusso_da_id, p_flusso_a_id)` — check pura STABLE, calcolo giorni netti tra due flussi | `YYYYMMDD-NN-create-fn_calcola_tempo_netto_da_a.yaml` | B2 |
| B12 | `20_code` | Funzione `pratiche.fn_valuta_tempo_esecuzione_da_a(p_pratica_id, p_flusso_da_id, p_flusso_a_id)` — check pura STABLE, confronto con formula da/a | `YYYYMMDD-NN-create-fn_valuta_tempo_esecuzione_da_a.yaml` | B3, B11 |
| B13 | `20_code` | Trigger function + trigger: `trgfn_flussi_calcolo_tempo_completamento()` + `trg_flussi_z90_calcolo_tempo_completamento_upd` — unico trigger WHEN COMPLETATO, gestisce sia avvio (flusso_da) sia chiusura (flusso_a) nel modello da/a | `YYYYMMDD-NN-create-trgfn_flussi_calcolo_tempo_completamento.yaml` | B9, B12 |
| B14 | pgTAP | Test: sospensione pratica/flusso, riattivazione, propagazione, calcoli_tempo da/a (avvio + completamento + ordine invertito), fn_calcola_tempo_netto_da_a, fn_valuta_tempo_esecuzione_da_a, guard immutabili, giornale | `db/pgtap/pratiche/test_sospensioni.sql` | B1-B13 |
| B15 | pgAgent | Job riattivazione automatica: cerca sospensioni con `data_riattivazione_prevista <= CURRENT_DATE` e `data_fine IS NULL` | `85_pgagent/YYYYMMDD-NN-job-riattivazione_sospensioni.yaml` | B2, B7 |

> **Nota dipendenza B6/B7 da Blocco A**: la propagazione della sospensione cambia lo stato dei flussi
> a SOSPESO. Con la macchina a stati rigida attiva, queste transizioni devono essere ammesse.
> Implementare prima il Blocco A garantisce che i trigger di propagazione non vengano bloccati.

---

### Blocco C — Backend Django (dopo A e B)

| Step | Descrizione | File coinvolti | Prerequisiti |
| ---- | ----------- | -------------- | ------------ |
| C1 | Aggiungere `SospensioneRow`, `FormulaTempoRow`, `CalcoloTempoRow`, `TransizioneStatoRow` a types | `apps/pratiche/types.py` | DDL completato (A1, B2, B3, B9) |
| C2 | Repository: INSERT/UPDATE sospensioni, SELECT formule_tempo, SELECT calcoli_tempo, SELECT transizioni | `apps/pratiche/db/pratiche_repository.py` | C1 |
| C3 | Service: `sospendi_pratica()`, `riattiva_pratica()`, `sospendi_flusso()`, `riattiva_flusso()` | `apps/pratiche/services/pratiche_service.py` | C2 |
| C4 | Error policy: mappare `PRATICHE_TRANSIZIONE_NON_AMMESSA`, `FLUSSI_TRANSIZIONE_NON_AMMESSA`, `SOSPENSIONI_FLUSSO_NON_COERENTE` | `apps/core/services/error_policies.py` | A3, B4 |
| C5 | Endpoint API: `POST .../sospendi/`, `POST .../riattiva/` (pratica e flusso) | `apps/pratiche/api/views.py`, `urls_v1.py` | C3, C4 |
| C6 | Test unitari service: sospendi/riattiva pratica e flusso, con mock DB | `apps/pratiche/tests/services/test_sospensioni_service.py` | C3 |
| C7 | Test unitari API: 4 endpoint sospensione/riattivazione | `apps/pratiche/tests/api/test_sospensioni_api.py` | C5 |

---

### Riepilogo deliverable

| Ambito | Nuovi oggetti |
| ------ | ------------- |
| ALTER tabelle | `pratiche.tipi_prestazione` (+`pre_attivazione`, +`post_attivazione`) |
| Tabelle config | `transizioni_stati_pratiche`, `transizioni_stati_flussi_pratiche` |
| Tabelle pratiche | `sospensioni`, `formule_tempo` (modello da/a), `calcoli_tempo` (modello da/a) |
| Funzioni DB | `fn_calcola_tempo_netto_da_a`, `fn_valuta_tempo_esecuzione_da_a` |
| Trigger functions | `trgfn_pratiche_guard_transizione`, `trgfn_flussi_guard_transizione`, `trgfn_sospensioni_guard_coerenza_flusso`, `trgfn_sospensioni_propaga`, `trgfn_sospensioni_riattiva`, `trgfn_sospensioni_giornale_ins`, `trgfn_sospensioni_giornale_riattivazione`, `trgfn_calcoli_tempo_guard_immutabili`, `trgfn_flussi_calcolo_tempo_completamento` |
| Trigger | 2 guard transizioni + 5 trigger sospensioni + 1 guard immutabili calcoli + 1 trigger calcolo tempo (unico COMPLETATO, modello da/a) |
| Seed data | 6+7 transizioni, 3 messaggi errore |
| Azioni giornale | +2 (`SOSPENSIONE_REGISTRATA`, `SOSPENSIONE_CHIUSA`) |
| Test pgTAP | 2 file (transizioni + sospensioni/tempi da/a) |
| Backend Django | types, repository, service, error policies, 4 endpoint API, test |
| pgAgent | 1 job riattivazione automatica |

---

## 15. Da Approfondire: Codice Pratica con Prefisso Dominio

> Stato: **da approfondire**. Concetto definito, dettagli implementativi da finalizzare.

### 15.1 Problema

Oggi il campo `codice` su `pratiche.pratiche` e' generato da trigger senza contesto semantico.
Non e' possibile distinguere a colpo d'occhio se una pratica riguarda un cliente, un ordine,
un soggetto generico o un'attivita' interna.

### 15.2 Proposta: prefisso dominio a 3 caratteri

Il codice pratica segue il formato: `<PREFISSO>-<ANNO>-<SEQUENZA>`

Esempi:

- `CLI-2026-000001` — pratica legata a un cliente
- `SOG-2026-000042` — pratica legata a un soggetto generico
- `ORD-2026-000003` — pratica generata da un ordine
- `INT-2026-000010` — pratica interna (false/false)

#### Prefissi candidati

| Prefisso | Dominio | Quando si usa |
| -------- | ------- | ------------- |
| `CLI` | Cliente | Soggetto con ruolo cliente attivo |
| `SOG` | Soggetto | Soggetto generico senza ruolo cliente |
| `ORD` | Ordini | Pratica generata dal ciclo ordini |
| `FOR` | Fornitori | Pratica legata a un fornitore |
| `INT` | Interno | Pratica interna (pre/post = false/false, soggetto NULL) |

> La lista dei prefissi e' indicativa. Il prefisso potrebbe derivare dalla `categoria`
> del tipo prestazione o da un campo dedicato sul tipo prestazione stesso.

### 15.3 Assegnazione automatica del prefisso

Il prefisso non e' inserito manualmente dall'utente ma determinato automaticamente:

- Se `soggetto_id IS NULL` → `INT`
- Se il soggetto ha ruolo cliente attivo per l'emittente → `CLI`
- Se il soggetto ha ruolo fornitore → `FOR`
- Altrimenti → `SOG`
- Se la pratica e' generata cross-dominio (es. da ordine) → prefisso del dominio origine

La logica di risoluzione del prefisso potrebbe stare:

- Nel trigger DB (se rimane nello schema `pratiche` + lookup su `anagrafiche`)
- Nel service Django (se la logica cross-schema e' troppo complessa per un trigger)

### 15.4 Integrazione con la numerazione esistente

Il progetto usa gia' una funzione standard per la generazione di codici con sequenza
(pattern `fn_gen_codice` / contatori). L'integrazione prevede di:

- Aggiungere il prefisso come parametro alla funzione di numerazione
- Mantenere un contatore separato per ogni combinazione `prefisso + anno`
- Il formato finale `<PREFISSO>-<ANNO>-<SEQUENZA>` con sequenza a 6 cifre zero-padded

> **Da decidere:**
>
> - Dove memorizzare il prefisso: campo dedicato su `tipi_prestazione` vs derivazione automatica
> - Dove vive la logica di risoluzione: trigger DB vs service Django
> - Se il contatore e' per prefisso+anno o per prefisso+anno+emittente
> - Interazione con la funzione `fn_gen_codice` esistente (estensione vs nuova funzione)

---

## 16. Da Fare: Punti Aperti dalla Revisione della Guida Operativa

> Stato: **FATTO** (07-03-2026). Decisioni prese e implementate. Emersi dalla revisione di `docs/it/guide/gestione-pratiche.md`.

### 16.1 Stato ERRORE — non terminale, con recovery

**Decisione**: ERRORE e' uno stato **di attesa intervento**, non terminale.
E' prodotto esclusivamente da handler automatici (mai da operatori).
Non blocca la pratica: gli altri flussi continuano normalmente.

Servono due transizioni in uscita:

| Transizione | Semantica |
| --- | --- |
| `ERRORE → IN_CORSO` | Retry: l'operatore o un job riprende il flusso dopo aver risolto la causa |
| `ERRORE → ANNULLATO` | Abbandono: il flusso viene scartato, la pratica prosegue |

**Implementato:**

| Tipo | Oggetto | Stato |
| ---- | ------- | ----- |
| Seed data | 2 righe in `config.transizioni_stati_flussi_pratiche` (CSV) | FATTO |
| Guida | Macchina a stati + ciclo di vita flusso | FATTO |
| Test pgTAP | Estendere test transizioni flussi | Da fare |

### 16.2 `flussi_vincolanti` — rimosso dal modello

**Decisione**: il campo `flussi_vincolanti` su `tipi_prestazione` **non viene implementato**.
Il concetto "workflow vincolante vs libero" e' gia' espresso interamente dalla configurazione
dei prerequisiti:

| Configurazione | Comportamento risultante |
| --- | --- |
| Tipo prestazione senza righe in `template_flussi_prerequisiti` | De facto libero: i flussi si creano in qualsiasi ordine |
| Tipo prestazione con prerequisiti obbligatori | Vincolante: il guard blocca se i prerequisiti non sono soddisfatti |
| Tipo prestazione con prerequisiti non obbligatori | Advisory: warning senza blocco |

Un flag separato sarebbe ridondante e non aggiunge potere espressivo.
Il guard prerequisiti (`trgfn_flussi_guard_prerequisiti`) scatta solo per flussi template-based
con prerequisiti configurati — se non ce ne sono, il workflow e' di fatto libero.

**FATTO**: menzioni rimosse dalla guida (catalogo, esempio SQL, checklist).
Nessuna migrazione DB necessaria (il campo non esiste).

### 16.3 `solo_interna` — rimosso dal modello

**Decisione**: il campo `pratiche.solo_interna` viene **rimosso** dal DB.

La visibilita' di un flusso verso l'esterno si configura interamente sul template,
non sull'istanza pratica:

- `template_flussi.direzione` (ENTRATA/USCITA/INTERNA) descrive il verso rispetto al canale
- `template_flussi_canali` (M:N) abilita i canali per ogni template flusso
- Un flusso senza associazioni in `template_flussi_canali` e' de facto interno

`canale_origine_id` sulla pratica resta come campo informativo: registra da quale
ingresso e' arrivata la richiesta (NULL = creata internamente).

**Implementato:**

| Tipo | Oggetto | Stato |
| ---- | ------- | ----- |
| Changeset | `migrations_v2/00_schema/pratiche/` | FATTO — `ALTER TABLE pratiche.pratiche DROP COLUMN solo_interna` |
| Guida | Tabella campi pratica + sezione Canali | FATTO |
| Backend | Vedi sezione 16.5 | FATTO |

**Discovery per canale** (funzionalita' futura):

```sql
-- Tipi prestazione che accettano richieste da un canale specifico
SELECT DISTINCT tp.*
FROM pratiche.tipi_prestazione tp
JOIN pratiche.template_flussi tf ON tf.tipo_prestazione_id = tp.id
JOIN pratiche.template_flussi_canali tfc ON tfc.template_flusso_id = tf.id
WHERE tfc.canale_id = :canale_id AND tf.direzione = 'ENTRATA';
```

Endpoint da aggiungere in fase successiva:
`GET /api/v1/pratiche/tipi-prestazione/?canale_id=N&direzione=ENTRATA`

### 16.4 Endpoint generazione manuale flusso

Nella guida operativa e' documentato un endpoint per la generazione manuale
di un flusso a partire da una pratica esistente:

```
POST /api/v1/pratiche/{pratica_id}/flussi/{flusso_id}/genera/
```

Questo endpoint **non e' ancora sviluppato**. Serve per i casi in cui un operatore
vuole attivare manualmente un flusso che non e' stato generato automaticamente
dalle regole di generazione.

**Da implementare:**

- Endpoint API con validazione: pratica esistente, flusso compatibile, prerequisiti soddisfatti
- Service layer che richiami la logica di generazione esistente (`generazione_service`)
- Registrazione nel giornale con azione dedicata
- Permessi: verificare quale azione processo (`config.azioni_processo`) associare

**Oggetti coinvolti:**

| Tipo | Oggetto |
| ---- | ------- |
| Backend API | `POST /api/v1/pratiche/{id}/flussi/{fid}/genera/` |
| Service | Estensione `generazione_service` o metodo dedicato |
| Permessi | Nuova azione processo o riuso di azione esistente |
| Test | Test API + test service |

### 16.5 Backend — rimozione `solo_interna` da tutti i layer

**FATTO.** La colonna `pratiche.pratiche.solo_interna` rimossa dal DB (changeset creato)
e da tutti i layer backend.

**File modificati:**

| File | Modifiche |
| ---- | --------- |
| `apps/pratiche/types.py` | Rimuovere campo `solo_interna: bool` da `PraticaRow` |
| `apps/pratiche/services/pratiche_service.py` | Rimuovere parametro `solo_interna` da `crea_pratica()` e dalla dict passata al repository. Rimuovere parametro `solo_interna` da `cerca_pratiche()` e dal passaggio a `repo.list_pratiche()` |
| `apps/pratiche/db/pratiche_repository.py` | Rimuovere parametro `solo_interna` da `list_pratiche()` e relativo filtro WHERE. Rimuovere `p.solo_interna` dalle SELECT in `list_pratiche()`, `get_pratica()`. Rimuovere `solo_interna` dalla INSERT in `create_pratica()` (colonna, placeholder, parametro). Aggiornare `_map_pratica_row()`: rimuovere `"solo_interna": bool(r[11])` e scalare gli indici successivi (da r[12]→r[11], r[13]→r[12], ecc.) |
| `apps/pratiche/db/generazione_repository.py` | Rimuovere `p.solo_interna` dalla SELECT in `get_pratiche_generate_da_flusso()` (il mapper e' condiviso con `PraticheRepository._map_pratica_row`) |
| `apps/pratiche/api/views.py` | Rimuovere `OpenApiParameter(name="solo_interna")` dalla lista GET. Rimuovere parsing `solo_interna_raw` dal metodo `get()`. Rimuovere passaggio `solo_interna=...` alla chiamata `cerca_pratiche()`. Rimuovere `"solo_interna": serializers.BooleanField(...)` dalla request POST. Rimuovere passaggio `solo_interna=...` alla chiamata `crea_pratica()` |
| `apps/pratiche/tests/services/test_pratiche_service.py` | Rimuovere `"solo_interna": False` dal dict mock in `test_crea_pratica`. Rimuovere intero test `test_crea_pratica_solo_interna` e aggiornare l'indice test nel commento iniziale |
| `apps/pratiche/tests/api/test_pratiche_api.py` | Rimuovere `"solo_interna": False` dal dict mock |
| `scripts/smoke-test-pratiche.sh` | Rimuovere `"solo_interna": true` dal payload JSON |
| `scripts/smoke-test-sospensioni.sh` | Rimuovere `"solo_interna": true` dal payload JSON |

**Attenzione:** il mapper `_map_pratica_row` mappa le colonne per posizione (indice).
Dopo la rimozione di `solo_interna` (che era all'indice 11), tutti gli indici successivi
scalano di 1:

```text
Prima:  r[10]=canale_origine_id, r[11]=solo_interna, r[12]=codice, r[13]=descrizione, ...
Dopo:   r[10]=canale_origine_id, r[11]=codice, r[12]=descrizione, r[13]=data_scadenza, ...
```

---

*Documento di sviluppo — Schema `pratiche` — ZeroERP (marzo 2026)*
