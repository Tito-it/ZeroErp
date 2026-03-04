# Piano di Sviluppo — Modulo Gestione Pratiche

> Riferimento tecnico: [sviluppo-gestione-pratiche.md](sviluppo-gestione-pratiche.md)
>
> Approccio: sviluppo concentrico — dal nucleo DB verso l'esterno (backend, API).
> Ogni fase ha prerequisiti espliciti. Non iniziare una fase senza aver completato i prerequisiti.

---

## Nota Importante — Automazioni DB

I trigger standard **NON vanno creati manualmente**. Il framework `dbops.fn_run_automations()`
li applica automaticamente a tutte le tabelle via CI pipeline (`90_end/ci_apply/`).

Trigger gestiti dall'automazione (non includere nel piano):

| Parte | Trigger automatico | Descrizione |
|-------|-------------------|-------------|
| `AUDIT_UPDATE` | `trgfn_audit_data_user_generic` | Campi `data_insert/user_insert/data_update/user_update` |
| `TX_ID` | `trgfn_tx_id_managed` | Generazione `tx_id` su INSERT/UPDATE |
| `STORICO` | `trgfn_storico_generic` | Storicizzazione BEFORE UPDATE/DELETE |
| `LOCK_COLUMNS` | `trgfn_lock_columns` | Blocco colonne immutabili (codice, codice_interno) |
| `ATTIVO` | `trgfn_prevent_deactivate_if_children` / `trgfn_child_requires_active_parent` | Protezione disattivazione/richiesta parent attivo |

Analogamente, gli **indici FK** sono gestiti da `dbops.apply_fk_index_policy()` (gia' presente in `90_end` con `runAlways: true`). Non creare indici FK manualmente.

Le fasi DB qui sotto includono **solo trigger business-specific** (giornale, guard prerequisiti, generazione cross-pratica).

---

## Riepilogo Fasi

| Fase | Area | Descrizione | Stato |
|------|------|-------------|-------|
| **DB-1** | DB | Tabelle config prerequisite | FATTO |
| **DB-2** | DB | Schema `pratiche` + tabelle catalogo + regole generazione + canali | FATTO |
| **DB-3** | DB | Tabelle operative (pratiche, flussi) | FATTO |
| **DB-4** | DB | Tabelle documentali (note, allegati) + giornale | FATTO |
| **DB-5** | DB | Funzioni DB + trigger business-specific | FATTO |
| **DB-6** | DB | Seed data e messaggi errore | FATTO |
| **DB-7** | DB | Test pgTAP | FATTO |
| **BE-1** | Backend | Setup app Django `pratiche` | FATTO |
| **BE-2** | Backend | Repository layer (accesso DB) | FATTO |
| **BE-3** | Backend | Services layer (orchestrazione + generazione + canali) | FATTO |
| **BE-4** | Backend | API layer (endpoints REST) | FATTO |
| **BE-5** | Backend | Test Django (services + API) | FATTO |

---

## Fasi DB

---

### DB-1 — Tabelle Config Prerequisite

**Prerequisiti**: nessuno (si appoggia su infrastruttura config esistente)

**Obiettivo**: preparare le tabelle di riferimento necessarie prima dello schema `pratiche`.

#### Migrations (`00_schema/config/`)

| File | Contenuto |
|------|-----------|
| `YYYYMMDD-01-drop-recreate-stati-pratiche-mctit.yaml` | DROP e ricreazione `config.stati_pratiche` (id INTEGER IDENTITY, codice, descrizione, codice_interno UNIQUE, attivo, audit) |
| `YYYYMMDD-02-create-stati-flussi-pratiche-mctit.yaml` | `config.stati_flussi_pratiche` (id, codice, descrizione, codice_interno, attivo, audit) |
| `YYYYMMDD-03-create-priorita-pratiche-mctit.yaml` | `config.priorita_pratiche` (id, codice, descrizione, codice_interno, sequenza INTEGER, attivo, audit) |
| `YYYYMMDD-04-create-tipi-nota-mctit.yaml` | `config.tipi_nota` (id, codice, descrizione, codice_interno, attivo, audit) |
| `YYYYMMDD-05-create-tipi-allegato-mctit.yaml` | `config.tipi_allegato` (id, codice, descrizione, codice_interno, attivo, audit) |
| `YYYYMMDD-06-create-canali-pratiche-mctit.yaml` | `config.canali_pratiche` (id, codice, descrizione, codice_interno UNIQUE, attivo, audit) |

#### Note

- `config.stati_pratiche`: la tabella esiste ma va droppata e ricreata con la struttura standard config (codice_interno, attivo, audit completo). Verificare che nessuna FK esterna punti ad essa prima del drop.
- `config.canali_pratiche`: abilita i canali di visibilita' dei flussi (es. WEB_CLIENTI, APP_TECNICA, PORTALE_FORNITORI). Non e' un booleano sulla pratica ma una tabella di registry per configurazione flessibile.
- Ogni tabella config segue il pattern standard: PK INTEGER IDENTITY, codice UNIQUE, codice_interno UNIQUE + locked, attivo BOOLEAN DEFAULT true, audit fields.
- I trigger standard (audit, lock codice_interno, attivo protection) saranno applicati automaticamente da `dbops.fn_run_automations()`.

---

### DB-2 — Schema `pratiche` + Tabelle Catalogo

**Prerequisiti**: DB-1 completata

**Obiettivo**: creare lo schema e le tabelle di configurazione del workflow engine, incluse regole di generazione cross-pratica e abilitazione canali.

#### Migrations (`00_schema/pratiche/`)

> Nuova directory `00_schema/pratiche/` da creare.

| # | File | Contenuto | Dipendenze |
|---|------|-----------|------------|
| 1 | `YYYYMMDD-10-create-schema-pratiche-mctit.yaml` | `CREATE SCHEMA pratiche` | — |
| 2 | `YYYYMMDD-11-create-tipi-prestazione-mctit.yaml` | `pratiche.tipi_prestazione` | #1 |
| 3 | `YYYYMMDD-12-create-handler-flussi-mctit.yaml` | `pratiche.handler_flussi` | #1 |
| 4 | `YYYYMMDD-13-create-template-flussi-mctit.yaml` | `pratiche.template_flussi` (FK → tipi_prestazione, handler_flussi) | #2, #3 |
| 5 | `YYYYMMDD-14-create-template-flussi-prerequisiti-mctit.yaml` | `pratiche.template_flussi_prerequisiti` (FK → template_flussi x2) | #4 |
| 6 | `YYYYMMDD-15-create-regole-generazione-mctit.yaml` | `pratiche.regole_generazione` | #4 |
| 7 | `YYYYMMDD-16-create-template-flussi-canali-mctit.yaml` | `pratiche.template_flussi_canali` (FK → template_flussi, canali_pratiche) | #4, DB-1 |

#### Dettaglio tabelle nuove

**`pratiche.regole_generazione`** — configurazione cross-pratica:

| Colonna | Tipo | Note |
|---------|------|------|
| `id` | BIGINT IDENTITY | PK |
| `template_flusso_origine_id` | INTEGER NOT NULL | FK → `pratiche.template_flussi(id)` — il flusso che scatena la generazione |
| `tipo_prestazione_dest_id` | INTEGER NOT NULL | FK → `pratiche.tipi_prestazione(id)` — il tipo pratica da generare |
| `template_flusso_dest_id` | INTEGER | FK → `pratiche.template_flussi(id)` — il flusso iniziale della pratica generata (NULL = nessun flusso auto) |
| `esito_richiesto` | VARCHAR(20) | CHECK (POSITIVO, NEGATIVO, QUALSIASI) — l'esito del flusso origine che attiva la generazione |
| `auto` | BOOLEAN NOT NULL DEFAULT false | Se true, la generazione e' automatica al completamento del flusso |
| `attivo` | BOOLEAN NOT NULL DEFAULT true | — |
| `descrizione` | TEXT | Descrizione leggibile della regola |
| `meta` | JSONB NOT NULL DEFAULT '{}' | Dati aggiuntivi per l'handler di generazione |
| `storicizza` | BOOLEAN NOT NULL DEFAULT true | — |
| `tx_id` | UUID | — |
| audit | — | `data_insert/user_insert/data_update/user_update` |

UNIQUE: `(template_flusso_origine_id, tipo_prestazione_dest_id, esito_richiesto)` — una sola regola per combinazione.

**`pratiche.template_flussi_canali`** — M:N tra template flussi e canali:

| Colonna | Tipo | Note |
|---------|------|------|
| `id` | BIGINT IDENTITY | PK |
| `template_flusso_id` | INTEGER NOT NULL | FK → `pratiche.template_flussi(id)` |
| `canale_id` | INTEGER NOT NULL | FK → `config.canali_pratiche(id)` |
| `attivo` | BOOLEAN NOT NULL DEFAULT true | — |
| audit | — | solo `data_insert/user_insert` (relazione immutabile: si cancella e ricrea) |

UNIQUE: `(template_flusso_id, canale_id)` — no duplicati.

#### Note

- `tipi_prestazione`: PK INTEGER, `attivo BOOLEAN`, campo `categoria VARCHAR(50)` libero
- `handler_flussi`: registry con `handler_key` UNIQUE, `attivo BOOLEAN`
- `template_flussi`: FK nullable `handler_id` (NULL = step manuale), `direzione VARCHAR(10) CHECK (ENTRATA, USCITA, INTERNA) DEFAULT 'INTERNA'` — caratterizza il tipo di flusso rispetto all'esterno
- `template_flussi_prerequisiti`: solo `data_insert/user_insert` (relazione immutabile, si cancella e ricrea)
- I trigger standard sono automatici. Solo i trigger business-specific (guard, generazione) vanno in DB-5.

---

### DB-3 — Tabelle Operative (pratiche, flussi)

**Prerequisiti**: DB-1 (config tables), DB-2 (catalogo)

**Obiettivo**: creare le tabelle operative core del workflow.

#### Migrations (`00_schema/pratiche/`)

| # | File | Contenuto | Dipendenze |
|---|------|-----------|------------|
| 8 | `YYYYMMDD-17-create-pratiche-mctit.yaml` | `pratiche.pratiche` | DB-1, DB-2 |
| 9 | `YYYYMMDD-18-create-flussi-mctit.yaml` | `pratiche.flussi` | #8 |

#### Dettaglio FK e tipi

**pratiche.pratiche**:

| Colonna | Tipo | FK verso |
|---------|------|----------|
| `id` | BIGINT IDENTITY | PK |
| `emittente_fiscale_id` | BIGINT NOT NULL | `anagrafiche.emittenti_fiscali(id)` |
| `tipo_prestazione_id` | INTEGER NOT NULL | `pratiche.tipi_prestazione(id)` |
| `soggetto_id` | UUID | `anagrafiche.soggetti(id)` |
| `stato_id` | INTEGER NOT NULL | `config.stati_pratiche(id)` |
| `priorita_id` | INTEGER NOT NULL | `config.priorita_pratiche(id)` |
| `risorsa_umana_id` | BIGINT | `anagrafiche.risorse_umane(id)` |
| `unita_organizzativa_id` | INTEGER | `config.unita_organizzative(id)` |
| `pratica_padre_id` | BIGINT | `pratiche.pratiche(id)` — gerarchia pratica |
| `flusso_origine_id` | BIGINT | `pratiche.flussi(id)` — tracciabilita' cross-pratica: il flusso che ha generato questa pratica |
| `canale_origine_id` | INTEGER | FK → `config.canali_pratiche(id)` — da quale sorgente esterna e' arrivata la richiesta (NULL = creata internamente) |
| `solo_interna` | BOOLEAN NOT NULL DEFAULT false | Se true, la pratica e' solo interna e non abilita configurazione canali sui flussi |
| `codice` | TEXT | Codice pratica (generato da trigger) |
| `descrizione` | TEXT | — |
| `data_scadenza` | DATE | — |
| `meta` | JSONB NOT NULL DEFAULT '{}' | — |
| `storicizza` | BOOLEAN NOT NULL DEFAULT true | — |
| `tx_id` | UUID | — |
| audit | — | `data_insert/user_insert/data_update/user_update` |

**pratiche.flussi**:

| Colonna | Tipo | FK verso |
|---------|------|----------|
| `id` | BIGINT IDENTITY | PK |
| `pratica_id` | BIGINT NOT NULL | `pratiche.pratiche(id)` |
| `template_flusso_id` | INTEGER | `pratiche.template_flussi(id)` (NULL = flusso manuale) |
| `stato_id` | INTEGER NOT NULL | `config.stati_flussi_pratiche(id)` |
| `flusso_padre_id` | BIGINT | `pratiche.flussi(id)` — sotto-flusso |
| `risorsa_umana_id` | BIGINT | `anagrafiche.risorse_umane(id)` |
| `unita_organizzativa_id` | INTEGER | `config.unita_organizzative(id)` |
| `sequenza` | INTEGER NOT NULL DEFAULT 0 | Ordine esecuzione nel workflow |
| `esito` | VARCHAR(20) | CHECK (POSITIVO, NEGATIVO, PARZIALE, NON_APPLICABILE) |
| `note_esito` | TEXT | — |
| `data_scadenza` | DATE | — |
| `meta` | JSONB NOT NULL DEFAULT '{}' | — |
| `storicizza` | BOOLEAN NOT NULL DEFAULT true | — |
| `tx_id` | UUID | — |
| audit | — | `data_insert/user_insert/data_update/user_update` |

---

### DB-4 — Tabelle Documentali + Giornale

**Prerequisiti**: DB-3 (pratiche, flussi esistenti)

**Obiettivo**: aggiungere note, allegati e il giornale di bordo (audit trail).

#### Migrations (`00_schema/pratiche/`)

| # | File | Contenuto | Dipendenze |
|---|------|-----------|------------|
| 10 | `YYYYMMDD-19-create-note-pratiche-mctit.yaml` | `pratiche.note_pratiche` (FK → pratiche, tipi_nota) | DB-3, DB-1 |
| 11 | `YYYYMMDD-20-create-note-flussi-mctit.yaml` | `pratiche.note_flussi` (FK → flussi, tipi_nota) | DB-3, DB-1 |
| 12 | `YYYYMMDD-21-create-allegati-pratiche-mctit.yaml` | `pratiche.allegati_pratiche` (FK → pratiche, tipi_allegato) | DB-3, DB-1 |
| 13 | `YYYYMMDD-22-create-allegati-flussi-mctit.yaml` | `pratiche.allegati_flussi` (FK → flussi, tipi_allegato) | DB-3, DB-1 |
| 14 | `YYYYMMDD-23-create-giornale-mctit.yaml` | `pratiche.giornale` (FK → pratiche, flussi) | DB-3 |

#### Dettaglio giornale

**pratiche.giornale**:

| Colonna | Tipo | Note |
|---------|------|------|
| `id` | BIGINT IDENTITY | PK |
| `pratica_id` | BIGINT NOT NULL | FK → `pratiche.pratiche(id)` |
| `flusso_id` | BIGINT | FK → `pratiche.flussi(id)` (NULL per eventi a livello pratica) |
| `azione` | VARCHAR(50) NOT NULL | CHECK in lista azioni (PRATICA_CREATA, STATO_CAMBIATO, FLUSSO_CREATO, ...) |
| `origine` | VARCHAR(20) NOT NULL DEFAULT 'SISTEMA' | CHECK (SISTEMA, UTENTE, HANDLER, SCHEDULER) |
| `dettaglio` | JSONB NOT NULL DEFAULT '{}' | Dati strutturati dell'evento (vecchio/nuovo stato, ecc.) |
| `tx_id` | UUID | Per connessione con il tx_id di transazione — tracciabilita' cross-tabella |
| `data_insert` | TIMESTAMPTZ NOT NULL DEFAULT now() | — |
| `user_insert` | TEXT NOT NULL DEFAULT CURRENT_USER | — |

Il giornale e' **append-only**: solo `data_insert/user_insert`, no UPDATE, no storicizzazione.

Indici espliciti (non-FK): `ix_giornale_data_insert` (BTREE), `ix_giornale_azione` (BTREE).

#### Note

- Note: 4 audit fields (modificabili)
- Allegati: solo `data_insert/user_insert` (immutabili, versionamento via `allegato_padre_id`)
- I trigger standard (audit) sulle note sono automatici. I trigger giornale (business) vanno in DB-5.

---

### DB-5 — Funzioni DB + Trigger Business-Specific

**Prerequisiti**: DB-3 (tabelle operative), DB-4 (giornale)

**Obiettivo**: creare le funzioni check/guard, le trigger function per il giornale e per la generazione cross-pratica. Applicare i trigger business-specific.

> I trigger standard (audit, tx_id, storico, lock, attivo) NON vanno qui — sono automatici.

#### Migrations (`20_code/pratiche/`)

> Nuova directory `20_code/pratiche/` da creare.

**Funzioni check/guard:**

| # | File | Contenuto | runOnChange |
|---|------|-----------|-------------|
| 1 | `YYYYMMDD-30-create-fn-check-prerequisiti-flusso-mctit.yaml` | `pratiche.fn_check_prerequisiti_flusso()` — pure check, RETURNS TABLE, STABLE | true |
| 2 | `YYYYMMDD-31-create-fn-guard-prerequisiti-flusso-mctit.yaml` | `pratiche.fn_guard_prerequisiti_flusso()` — fail-fast, usa `script.fn_log_and_raise_error` | true |
| 3 | `YYYYMMDD-32-create-trgfn-flussi-guard-prerequisiti-mctit.yaml` | `pratiche.trgfn_flussi_guard_prerequisiti()` — wrapper trigger per guard | true |

**Funzioni giornale:**

| # | File | Contenuto | runOnChange |
|---|------|-----------|-------------|
| 4 | `YYYYMMDD-33-create-trgfn-pratiche-giornale-ins-mctit.yaml` | `pratiche.trgfn_pratiche_giornale_ins()` — logga PRATICA_CREATA | true |
| 5 | `YYYYMMDD-34-create-trgfn-pratiche-giornale-stato-mctit.yaml` | `pratiche.trgfn_pratiche_giornale_stato()` — logga cambi stato pratica | true |
| 6 | `YYYYMMDD-35-create-trgfn-pratiche-giornale-assegnazione-mctit.yaml` | `pratiche.trgfn_pratiche_giornale_assegnazione()` — logga cambi risorsa/UO | true |
| 7 | `YYYYMMDD-36-create-trgfn-pratiche-giornale-priorita-mctit.yaml` | `pratiche.trgfn_pratiche_giornale_priorita()` — logga cambi priorita' | true |
| 8 | `YYYYMMDD-37-create-trgfn-flussi-giornale-ins-mctit.yaml` | `pratiche.trgfn_flussi_giornale_ins()` — logga FLUSSO_CREATO | true |
| 9 | `YYYYMMDD-38-create-trgfn-flussi-giornale-stato-mctit.yaml` | `pratiche.trgfn_flussi_giornale_stato()` — logga cambi stato flusso | true |
| 10 | `YYYYMMDD-39-create-trgfn-note-pratiche-giornale-mctit.yaml` | `pratiche.trgfn_note_pratiche_giornale()` — logga NOTA_AGGIUNTA | true |
| 11 | `YYYYMMDD-40-create-trgfn-note-flussi-giornale-mctit.yaml` | `pratiche.trgfn_note_flussi_giornale()` | true |
| 12 | `YYYYMMDD-41-create-trgfn-allegati-pratiche-giornale-mctit.yaml` | `pratiche.trgfn_allegati_pratiche_giornale()` — logga ALLEGATO_AGGIUNTO | true |
| 13 | `YYYYMMDD-42-create-trgfn-allegati-flussi-giornale-mctit.yaml` | `pratiche.trgfn_allegati_flussi_giornale()` | true |

**Funzione generazione cross-pratica:**

| # | File | Contenuto | runOnChange |
|---|------|-----------|-------------|
| 14 | `YYYYMMDD-43-create-fn-genera-pratica-da-flusso-mctit.yaml` | `pratiche.fn_genera_pratica_da_flusso(p_flusso_id, p_regola_id)` — crea la pratica target secondo la regola configurata, imposta `flusso_origine_id` | true |
| 15 | `YYYYMMDD-44-create-trgfn-flussi-generazione-mctit.yaml` | `pratiche.trgfn_flussi_generazione()` — AFTER UPDATE su flussi: se stato diventa COMPLETATO, cerca regole matching in `regole_generazione` con `auto = true` e invoca `fn_genera_pratica_da_flusso` | true |

**Applicazione trigger business-specific:**

| # | File | Contenuto |
|---|------|-----------|
| 16 | `YYYYMMDD-50-trigger-business-pratiche-mctit.yaml` | Trigger giornale su `pratiche`: ins, stato, assegnazione, priorita' |
| 17 | `YYYYMMDD-51-trigger-business-flussi-mctit.yaml` | Trigger guard prerequisiti + giornale ins/stato + generazione su `flussi` |
| 18 | `YYYYMMDD-52-trigger-business-note-mctit.yaml` | Trigger giornale su `note_pratiche` e `note_flussi` |
| 19 | `YYYYMMDD-53-trigger-business-allegati-mctit.yaml` | Trigger giornale su `allegati_pratiche` e `allegati_flussi` |

#### Matrice trigger business-specific per tabella

**pratiche** (4 trigger business):

| Nome | Timing | Evento |
|------|--------|--------|
| `trg_pratiche_z90_giornale_ins` | AFTER | INSERT |
| `trg_pratiche_z90_giornale_stato_upd` | AFTER | UPDATE (WHEN stato_id cambia) |
| `trg_pratiche_z90_giornale_assegnazione_upd` | AFTER | UPDATE (WHEN risorsa/UO cambia) |
| `trg_pratiche_z90_giornale_priorita_upd` | AFTER | UPDATE (WHEN priorita_id cambia) |

**flussi** (4 trigger business):

| Nome | Timing | Evento |
|------|--------|--------|
| `trg_flussi_a10_guard_prerequisiti_ins` | BEFORE | INSERT |
| `trg_flussi_z90_giornale_ins` | AFTER | INSERT |
| `trg_flussi_z90_giornale_stato_upd` | AFTER | UPDATE (WHEN stato_id cambia) |
| `trg_flussi_z90_generazione_upd` | AFTER | UPDATE (WHEN stato → COMPLETATO) |

**note_pratiche / note_flussi** (1 ciascuno):

| Nome | Timing | Evento |
|------|--------|--------|
| `trg_note_pratiche_z90_giornale_ins` | AFTER | INSERT |
| `trg_note_flussi_z90_giornale_ins` | AFTER | INSERT |

**allegati_pratiche / allegati_flussi** (1 ciascuno):

| Nome | Timing | Evento |
|------|--------|--------|
| `trg_allegati_pratiche_z90_giornale_ins` | AFTER | INSERT |
| `trg_allegati_flussi_z90_giornale_ins` | AFTER | INSERT |

#### Dipendenze esterne

- `script.fn_log_and_raise_error` — gia' esistente
- `config.messaggi_errore` — inserire codice `PRATICHE_PREREQUISITI_NON_SODDISFATTI` (seed in DB-6)

---

### DB-6 — Seed Data e Messaggi Errore

**Prerequisiti**: DB-5 (trigger business-specific applicati)

**Obiettivo**: popolare le tabelle config con i dati iniziali.

#### Migrations (`80_data/`)

| # | File | Contenuto |
|---|------|-----------|
| 1 | `YYYYMMDD-60-seed-config-stati-pratiche-mctit.yaml` | 5 stati: BOZZA, APERTA, SOSPESA, CHIUSA, ANNULLATA |
| 2 | `YYYYMMDD-61-seed-config-stati-flussi-pratiche-mctit.yaml` | 6 stati: DA_ESEGUIRE, IN_CORSO, COMPLETATO, SOSPESO, ANNULLATO, ERRORE |
| 3 | `YYYYMMDD-62-seed-config-priorita-pratiche-mctit.yaml` | 4 priorita': BASSA(10), NORMALE(20), ALTA(30), URGENTE(40) |
| 4 | `YYYYMMDD-63-seed-config-tipi-nota-mctit.yaml` | 5 tipi: GENERALE, INTERNA, CLIENTE, TECNICA, LEGALE |
| 5 | `YYYYMMDD-64-seed-config-tipi-allegato-mctit.yaml` | 8 tipi: DOCUMENTO, IMMAGINE, MODULO, CONTRATTO, FATTURA, VERBALE, CERTIFICATO, ALTRO |
| 6 | `YYYYMMDD-65-seed-config-canali-pratiche-mctit.yaml` | Canali iniziali: WEB_CLIENTI, APP_TECNICA, PORTALE_FORNITORI |
| 7 | `YYYYMMDD-66-seed-config-messaggi-errore-pratiche-mctit.yaml` | Codice `PRATICHE_PREREQUISITI_NON_SODDISFATTI` in `config.messaggi_errore` |

---

### DB-7 — Test pgTAP

**Prerequisiti**: DB-6 (seed data disponibile)

**Obiettivo**: verificare il corretto funzionamento delle funzioni e dei trigger business-specific.

#### File test (`db/pgtap/pratiche/`)

| File | Contenuto |
|------|-----------|
| `test_fn_check_prerequisiti_flusso.sql` | Test fn_check: tipo non vincolante (bypass), prerequisiti mancanti, prerequisiti soddisfatti, sequenza limite |
| `test_fn_guard_prerequisiti_flusso.sql` | Test fn_guard: raise su prerequisiti mancanti, pass su OK |
| `test_trigger_giornale_pratiche.sql` | Test: creazione pratica → entry giornale con tx_id, cambio stato → entry giornale, cambio assegnazione/priorita' |
| `test_trigger_giornale_flussi.sql` | Test: creazione flusso → entry giornale, cambio stato flusso → entry |
| `test_trigger_guard_flussi.sql` | Test: insert flusso con prerequisiti mancanti → errore, insert con prerequisiti OK → successo |
| `test_generazione_cross_pratica.sql` | Test: completamento flusso con regola auto=true → pratica generata con `flusso_origine_id` corretto, regola auto=false → nessuna generazione automatica |
| `test_canali_flussi.sql` | Test: collegamento template_flussi ↔ canali, verifica UNIQUE constraint, filtro solo_interna |

---

## Fasi Backend

---

### BE-1 — Setup App Django `pratiche`

**Prerequisiti**: DB-6 completata (il DB ha tutte le tabelle, funzioni, trigger e seed)

**Obiettivo**: creare la struttura base dell'app Django.

#### Struttura directory

```
backend/apps/pratiche/
├── __init__.py
├── apps.py                    # PraticheConfig
├── models.py                  # Modelli managed=False (minimali)
├── types.py                   # TypedDict per pratica, flusso, prerequisiti, regola generazione
├── api/
│   ├── __init__.py
│   ├── views.py
│   └── urls_v1.py
├── db/
│   ├── __init__.py
│   ├── pratiche_repository.py     # CRUD pratiche + flussi + giornale + prerequisiti + canali
│   └── generazione_repository.py  # Regole generazione + fn_genera_pratica_da_flusso
├── services/
│   ├── __init__.py
│   ├── pratiche_service.py        # Orchestrazione pratiche + flussi + handler dispatch
│   ├── generazione_service.py     # Orchestrazione generazione cross-pratica
│   └── handler_registry.py        # Mapping handler_key → classe Python
└── tests/
    ├── __init__.py
    ├── api/
    │   └── __init__.py
    └── services/
        └── __init__.py
```

> **Naming convention** (da AGENTS.md): i flussi NON sono un sottodominio autonomo
> (sono le righe operative di una pratica), quindi vanno in `pratiche_repository.py`
> e `pratiche_service.py`. Solo `generazione` ha logica orchestrata autonoma e giustifica
> file separati. Riferimento: `apps/vendite/db/vendite_repository.py` (generico schema)
> vs `apps/vendite/db/pipeline_repository.py` (sottodominio specializzato).

#### Attivita'

1. Creare la directory e i file base
2. Registrare `apps.pratiche` in `INSTALLED_APPS` (`backend/zeroerp_backend/settings.py`)
3. Creare `apps.py` con `PraticheConfig`
4. Creare `models.py` con modelli `managed = False` minimali (se necessari per admin/serialization)
5. Creare `types.py` con TypedDict per le strutture dati (inclusi `RegolaGenerazione`, `CanalePratica`)

---

### BE-2 — Repository Layer (Accesso DB)

**Prerequisiti**: BE-1 (app setup)

**Obiettivo**: creare il layer di accesso DB con cursor raw SQL (pattern standard del progetto).

#### File e responsabilita'

**`db/pratiche_repository.py`** — operazioni su pratiche, flussi, giornale, prerequisiti, canali:

- `list_pratiche(emittente_id, filtri)` — lista pratiche con paginazione
- `get_pratica(pratica_id)` — dettaglio pratica
- `create_pratica(data)` → INSERT e ritorno id
- `update_pratica(pratica_id, data)` → UPDATE
- `update_stato_pratica(pratica_id, stato_codice_interno)` → cambio stato
- `get_giornale_pratica(pratica_id)` — log audit della pratica (include tx_id per tracciabilita')
- `list_flussi(pratica_id)` — flussi di una pratica
- `get_flusso(flusso_id)` — dettaglio flusso
- `create_flusso(data)` → INSERT (il trigger DB valida prerequisiti)
- `update_stato_flusso(flusso_id, stato_codice_interno)` → cambio stato
- `check_prerequisiti(pratica_id, template_flusso_id)` → chiama `pratiche.fn_check_prerequisiti_flusso()`
- `get_canali_flusso(template_flusso_id)` → canali abilitati per il template flusso

**`db/generazione_repository.py`** — operazioni di generazione cross-pratica:

- `list_regole_generazione(template_flusso_id)` → regole configurate per un template flusso
- `get_pratiche_generate_da_flusso(flusso_id)` → pratiche generate da un flusso (via `flusso_origine_id`)
- `genera_pratica_manuale(flusso_id, regola_id)` → chiama `pratiche.fn_genera_pratica_da_flusso()` per generazione manuale (regole con `auto = false`)

#### Pattern di riferimento

- Seguire `apps/vendite/db/vendite_repository.py` per lo stile
- Usare `django.db.connection` con cursor raw
- Guard con `ErrorManager.require` dopo ogni `fetchone()`
- Commenti `# Scopo: ...` su ogni metodo

---

### BE-3 — Services Layer (Orchestrazione)

**Prerequisiti**: BE-2 (repository disponibile)

**Obiettivo**: creare i servizi che orchestrano la logica applicativa, incluse generazione cross-pratica e gestione canali.

#### File e responsabilita'

**`services/pratiche_service.py`** — facade per operazioni su pratiche e flussi:

- `crea_pratica(emittente_id, tipo_prestazione_codice, soggetto_id, solo_interna, ...)` — crea pratica con stato iniziale
- `aggiorna_pratica(pratica_id, data)` — aggiornamento campi
- `cambia_stato_pratica(pratica_id, nuovo_stato)` — transizione di stato con validazione
- `assegna_pratica(pratica_id, risorsa_umana_id, unita_organizzativa_id)` — assegnazione
- `cerca_pratiche(emittente_id, filtri)` — ricerca con paginazione
- `crea_flusso(pratica_id, template_flusso_id_or_codice, ...)` — crea flusso (prerequisiti validati dal DB)
- `avvia_flusso(flusso_id)` — transizione DA_ESEGUIRE → IN_CORSO
- `completa_flusso(flusso_id, esito, note_esito)` — transizione → COMPLETATO con esito. La generazione automatica cross-pratica e' gestita dal trigger DB.
- `verifica_prerequisiti(pratica_id, template_flusso_id)` — check prerequisiti (per UI/preview)
- `dispatch_handler(flusso_id)` — invoca handler Django se configurato
- `get_canali_disponibili(template_flusso_id)` — lista canali abilitati per il flusso

> Il service e' progettato come **API interna cross-dominio**: altre app Django
> (vendite, anagrafiche, acquisti) possono importare e usare `pratiche_service`
> per creare/gestire pratiche legate ai propri eventi di dominio.

**`services/generazione_service.py`** — gestione generazione cross-pratica:

- `genera_pratica_manuale(flusso_id, regola_id)` — per regole con `auto = false`, l'utente sceglie quando generare
- `get_regole_applicabili(flusso_id)` — regole configurate per il template del flusso, con indicazione se gia' generate
- `get_pratiche_generate(flusso_id)` — pratiche figlie generate da questo flusso

**`services/handler_registry.py`** — mapping handler_key → classe:

```python
# Scopo: registry degli handler flusso, mappa handler_key a classi Python.
# Il DB contiene le chiavi (pratiche.handler_flussi), Django contiene il mapping.

from typing import Protocol

class BaseFlussoHandler(Protocol):
    def execute(self, flusso_id: int, pratica_id: int, meta: dict) -> dict: ...

HANDLER_MAP: dict[str, type[BaseFlussoHandler]] = {
    # Da popolare man mano che si implementano gli handler
    # "APPUNTAMENTO": AppuntamentoHandler,
    # "SOPRALLUOGO":  SopralluogoHandler,
}
```

#### Pattern di riferimento

- Seguire `apps/vendite/services/pipeline_service.py` per lo stile
- Usare `ServiceError` e `ErrorManager` per error handling
- No `try/except Exception` generici — lasciare al middleware
- Commenti `# Scopo: ...` dettagliati sui metodi orchestratori

---

### BE-4 — API Layer (Endpoints REST)

**Prerequisiti**: BE-3 (services disponibili)

**Obiettivo**: esporre le API REST per il modulo pratiche, inclusi generazione e canali.

#### Endpoints previsti

| Metodo | URL | Descrizione | Service |
|--------|-----|-------------|---------|
| GET | `/api/v1/pratiche/` | Lista pratiche (paginata, filtri) | `pratiche_service.cerca_pratiche` |
| POST | `/api/v1/pratiche/` | Crea pratica | `pratiche_service.crea_pratica` |
| GET | `/api/v1/pratiche/{id}/` | Dettaglio pratica | `pratiche_service` |
| PATCH | `/api/v1/pratiche/{id}/` | Aggiorna pratica | `pratiche_service.aggiorna_pratica` |
| POST | `/api/v1/pratiche/{id}/stato/` | Cambia stato pratica | `pratiche_service.cambia_stato_pratica` |
| POST | `/api/v1/pratiche/{id}/assegnazione/` | Assegna pratica | `pratiche_service.assegna_pratica` |
| GET | `/api/v1/pratiche/{id}/giornale/` | Giornale pratica (con tx_id) | `pratiche_repository.get_giornale_pratica` |
| GET | `/api/v1/pratiche/{id}/flussi/` | Lista flussi pratica | `pratiche_service` |
| POST | `/api/v1/pratiche/{id}/flussi/` | Crea flusso | `pratiche_service.crea_flusso` |
| GET | `/api/v1/pratiche/{id}/flussi/{flusso_id}/` | Dettaglio flusso | `pratiche_service` |
| POST | `/api/v1/pratiche/{id}/flussi/{flusso_id}/stato/` | Cambia stato flusso | `pratiche_service` |
| GET | `/api/v1/pratiche/{id}/flussi/{flusso_id}/prerequisiti/` | Check prerequisiti | `pratiche_service.verifica_prerequisiti` |
| GET | `/api/v1/pratiche/{id}/flussi/{flusso_id}/canali/` | Canali abilitati per il flusso | `pratiche_service.get_canali_disponibili` |
| GET | `/api/v1/pratiche/{id}/flussi/{flusso_id}/regole-generazione/` | Regole generazione applicabili | `generazione_service.get_regole_applicabili` |
| POST | `/api/v1/pratiche/{id}/flussi/{flusso_id}/genera/` | Generazione manuale pratica | `generazione_service.genera_pratica_manuale` |
| GET | `/api/v1/pratiche/{id}/flussi/{flusso_id}/pratiche-generate/` | Pratiche generate dal flusso | `generazione_service.get_pratiche_generate` |

#### File

- `api/views.py` — APIView con `@extend_schema` su ogni metodo HTTP
- `api/urls_v1.py` — routing
- Registrare in `backend/zeroerp_backend/urls.py` sotto `/api/v1/pratiche/`

#### Pattern di riferimento

- Usare `handle_post_json(...)` per endpoint POST (pattern core)
- Paginazione: `apps/core/api/pagination.py`
- Search: `apps/core/api/search_validators.py` con `is_search_endpoint = True` per lista
- `@extend_schema` obbligatorio per drf-spectacular

---

### BE-5 — Test Django

**Prerequisiti**: BE-4 (API completa)

**Obiettivo**: test unitari con mock (compatibili CI senza DB reale).

#### Struttura test

```
backend/apps/pratiche/tests/
├── __init__.py
├── services/
│   ├── __init__.py
│   ├── test_pratiche_service.py
│   ├── test_pratiche_service_flussi.py
│   ├── test_generazione_service.py
│   └── test_handler_registry.py
└── api/
    ├── __init__.py
    ├── test_pratiche_api.py
    └── test_flussi_api.py
```

#### Test services (con mock DB)

| File | Test previsti |
|------|--------------|
| `test_pratiche_service.py` | Creazione pratica (con solo_interna true/false), cambio stato, assegnazione, errori su dati mancanti |
| `test_pratiche_service_flussi.py` | Creazione flusso, avvio, completamento, verifica prerequisiti, dispatch handler, lista canali |
| `test_generazione_service.py` | Generazione manuale OK, generazione con regola inesistente → errore, lista regole applicabili, lista pratiche generate |
| `test_handler_registry.py` | Lookup handler_key esistente, handler_key mancante → errore |

#### Test API (con mock services)

| File | Test previsti |
|------|--------------|
| `test_pratiche_api.py` | GET lista, POST crea, PATCH aggiorna, POST stato, GET giornale (con tx_id) |
| `test_flussi_api.py` | GET lista flussi, POST crea flusso, POST stato flusso, GET prerequisiti, GET canali, POST genera, GET pratiche-generate |

#### Regole CI

- Usare `unittest.TestCase` (non `django.test.TestCase`)
- Mockare ogni accesso DB (`django.db.connection`)
- Pattern: `patcher = patch.object(...)` in `setUp`, `addCleanup(patcher.stop)`
- Esecuzione locale: `./manage-test.sh apps.pratiche.tests -v 2`

---

## Riepilogo Numerazione Migrations

> Le date YYYYMMDD vanno sostituite con la data effettiva di sviluppo.
> La numerazione NN (01, 02, ...) e' progressiva per giorno.

| Area | Range NN | Contenuto |
|------|----------|-----------|
| `00_schema/config/` | 01-06 | Tabelle config (drop/recreate stati_pratiche, nuove config, canali) |
| `00_schema/pratiche/` | 10-23 | Schema + tutte le tabelle (catalogo, operative, documentali) |
| `20_code/pratiche/` | 30-44 | Funzioni check/guard, trigger functions giornale/generazione |
| `20_code/pratiche/` | 50-53 | Trigger business-specific applicati alle tabelle |
| `80_data/` | 60-66 | Seed data e messaggi errore |
| `db/pgtap/pratiche/` | — | Test pgTAP |

**Trigger standard** (audit, tx_id, storico, lock, attivo): gestiti automaticamente da `dbops.fn_run_automations()` via CI.

**Indici FK**: gestiti automaticamente da `dbops.apply_fk_index_policy()` via `90_end`.

**Totale stimato**: ~30 file migration Liquibase + 7 file test pgTAP

---

## Ordine di Esecuzione Consigliato

```
DB-1 ──> DB-2 ──> DB-3 ──> DB-4 ──> DB-5 ──> DB-6 ──> DB-7
                                                          │
                                                          v
                                        BE-1 ──> BE-2 ──> BE-3 ──> BE-4 ──> BE-5
```

Le fasi DB sono sequenziali (ogni fase dipende dalla precedente).
Le fasi Backend partono dopo DB-6 (DB completo con seed).
DB-7 (test pgTAP) puo' procedere in parallelo con BE-1.

---

*Piano di sviluppo — Modulo Gestione Pratiche — ZeroERP (marzo 2026)*
