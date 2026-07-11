# CRM, Ticketing e Pratiche — Documento di integrazione

> **Stato**: bozza operativa
> **Data**: 29 marzo 2026
> **Prerequisiti**: Pratiche v2 completato (almeno fase 2 backend)
> **Riferimenti**:
>
> - [Guida Gestione Pratiche](/guide/gestione-pratiche)
> - [Gestione Pratiche v2](../work-done/gestione-pratiche-v2.md) (WIP)
> - Integrazione CRM & Ticketing (bozza ago 2025) — doc `Analisi_varie/Progetti-idee-sviluppo/integrazione-con-crm-e-ticketing.md`
> - [Mappa Concentrica](/mappa-concentrica)

---

## Obiettivi

1. **Definire il percorso** per integrare un sistema di ticketing (assistenza) con il motore pratiche esistente
2. **Chiarire il ruolo** di ciascun modulo: il ticket e' il punto di ingresso, la pratica e' il motore di processo
3. **Rispettare lo sviluppo concentrico**: pratiche (Anello 2) resta agnostico; il ticketing (Anello 3) si appoggia al motore senza modificarlo
4. **Indicare la via per il CRM** senza svilupparlo ora — posizionamento architetturale e dipendenze
5. **Mappare i gap** DB/backend/frontend necessari per la completa integrazione

---

## Vantaggi dell'integrazione

| Vantaggio | Dettaglio |
|-----------|-----------|
| **Processo unico** | Ogni richiesta di assistenza che richiede un workflow strutturato transita dal motore pratiche: stessi stati, stessi SLA, stesso giornale |
| **Tracciabilita' end-to-end** | Dal ticket iniziale alla fattura finale, ogni passaggio e' registrato nel giornale immutabile |
| **Generazione cross-pratica** | Un ticket che richiede intervento tecnico genera automaticamente una pratica di preventivazione/intervento via `regole_generazione` |
| **SLA unificati** | I calcoli tempo e le soglie di allerta (OK/WARNING/CRITICO/SFORATO) si applicano anche ai ticket trasformati in pratica |
| **Nessuna duplicazione di logica** | Il ticketing non reimplementa stati, transizioni o giornale — usa quelli del motore pratiche |
| **Multi-company** | Il ticket eredita la segregazione `emittente_fiscale_id` gia' presente nelle pratiche |
| **Ponte verso fatturazione** | Le attivita' svolte sul ticket (worklog, materiali) fluiscono verso `vendite.attivita_fatturabili` per la fatturazione |

---

## Posizione nel modello concentrico

```text
Anello 0: core, dbops, maintenance (infrastruttura)
Anello 1: config, anagrafiche, catalogo (dati di base)
Anello 2: pratiche (workflow engine)                    <-- motore generico, agnostico
Anello 3: vendite, acquisti, magazzino                  <-- operazioni
Anello 3: assistenza (ticketing)                        <-- NUOVO, stesso livello di vendite
Anello 3: crm (pipeline commerciale)                    <-- FUTURO, stesso livello di vendite
```

**Regola fondamentale**: gli schemi di Anello 3 puntano verso Anello 2, mai il contrario.
`assistenza.ticket` avra' FK verso `pratiche.pratiche`, ma `pratiche.pratiche` non conosce il concetto di "ticket".

---

## Il processo ticket — scenario operativo

### Scenario tipo: richiesta di assistenza che diventa intervento tecnico

```text
FASE 1 — RICEZIONE
  Un cliente chiama/scrive per un problema.
  L'operatore crea un TICKET nello schema assistenza.
  Il ticket registra: soggetto, canale, categoria, priorita', descrizione.

FASE 2 — TRIAGE
  L'operatore valuta la richiesta:
  a) Risolvibile subito → risolve, chiude il ticket. Fine.
  b) Richiede valutazione tecnica → apre una PRATICA.

FASE 3 — APERTURA PRATICA
  Il sistema crea una pratica con tipo_prestazione = "ASSISTENZA_TECNICA".
  Il collegamento ticket → pratica viene registrato nella tabella ponte.
  La pratica eredita il contesto anagrafico dal ticket:
    soggetto_id, soggetto_ruolo_id, istanza_utility_id.

FASE 4 — WORKFLOW PRATICA (gestito dal motore pratiche)
  I flussi previsti dal template "ASSISTENZA_TECNICA" si eseguono in sequenza:

  Flusso 1: VALUTAZIONE
    L'operatore di primo livello documenta il problema.
    Esito: POSITIVO (proseguire) o NEGATIVO (non risolvibile).

  Flusso 2: ASSEGNAZIONE_TECNICO
    Dispatch al tecnico competente (manuale o via handler).
    Il flusso registra risorsa_umana_id e unita_organizzativa_id.

  Flusso 3: DIAGNOSI_TECNICA
    Il tecnico verifica il problema sul campo.
    Esito: POSITIVO (risolvibile), NEGATIVO (serve intervento strutturato).

  Se esito POSITIVO:
    Flusso 4: RISOLUZIONE
    Il tecnico risolve, registra worklog e materiali.
    Worklog → vendite.attivita_fatturabili (ponte fatturazione).
    Pratica → CHIUSA.

  Se esito NEGATIVO (serve intervento strutturato):
    GENERAZIONE CROSS-PRATICA (automatica via regole_generazione)

FASE 5 — CROSS-PRATICA: PREVENTIVAZIONE
  Il motore genera automaticamente una nuova pratica:
    tipo_prestazione = "PREVENTIVAZIONE" (o "INTERVENTO_PROGRAMMATO")
    pratica_padre_id = pratica assistenza originale
    flusso_origine_id = flusso DIAGNOSI_TECNICA che ha generato

  Flussi previsti:
    1. REDAZIONE_PREVENTIVO → genera preventivo in vendite
    2. INVIO_CLIENTE → notifica/portale
    3. APPROVAZIONE_CLIENTE → attesa risposta
    4. ESECUZIONE_LAVORO → worklog + materiali → attivita_fatturabili
    5. VERIFICA_COMPLETAMENTO → collaudo
    6. FATTURAZIONE → genera fattura

FASE 6 — CHIUSURA
  La pratica di preventivazione si chiude.
  Il ticket originale viene aggiornato con lo stato di chiusura.
  Il giornale della pratica contiene l'intera storia: dal ticket alla fattura.
```

### Diagramma di flusso

```text
                    ┌──────────────┐
                    │   TICKET     │  (schema assistenza)
                    │  ricezione   │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │    TRIAGE    │
                    └──┬───────┬───┘
                       │       │
              risolvibile    serve pratica
                       │       │
              ┌────────▼──┐  ┌─▼──────────────────────┐
              │  CHIUSO   │  │  PRATICA                │ (schema pratiche)
              │  (ticket) │  │  tipo: ASSISTENZA_TECNICA│
              └───────────┘  └─┬──────────────────────┘
                               │
                   ┌───────────┼───────────┐
                   │           │           │
            ┌──────▼──┐ ┌─────▼────┐ ┌────▼──────────┐
            │VALUTAZ. │ │ASSEGNAZ. │ │DIAGNOSI_TECN. │
            │         │ │TECNICO   │ │               │
            └─────────┘ └──────────┘ └────┬──────────┘
                                          │
                              ┌───────────┼──────────┐
                              │                      │
                       esito POSITIVO          esito NEGATIVO
                              │                      │
                       ┌──────▼──────┐     ┌─────────▼─────────┐
                       │ RISOLUZIONE │     │ CROSS-PRATICA     │
                       │ worklog +   │     │ PREVENTIVAZIONE   │
                       │ materiali   │     │ (nuova pratica)   │
                       └──────┬──────┘     └─────────┬─────────┘
                              │                      │
                              │            ┌─────────┼──────────┐
                              │            │         │          │
                              │     ┌──────▼──┐ ┌───▼───┐ ┌───▼──────┐
                              │     │PREVENTIV│ │APPROV.│ │ESECUZIONE│
                              │     │         │ │CLIENTE│ │LAVORO    │
                              │     └─────────┘ └───────┘ └───┬──────┘
                              │                                │
                              ▼                                ▼
                    ┌─────────────────┐              ┌─────────────────┐
                    │ attivita_       │              │ attivita_       │
                    │ fatturabili     │              │ fatturabili     │
                    │ (vendite)       │              │ (vendite)       │
                    └────────┬────────┘              └────────┬────────┘
                             │                                │
                             └────────────┬───────────────────┘
                                          │
                                   ┌──────▼──────┐
                                   │  FATTURA    │
                                   └─────────────┘
```

---

## Modello dati: schema `assistenza`

### assistenza.ticket

Tabella principale dei ticket di assistenza.

```sql
CREATE TABLE assistenza.ticket (
    id              BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    emittente_fiscale_id BIGINT NOT NULL
        REFERENCES anagrafiche.emittenti_fiscali(id),
    soggetto_id     UUID
        REFERENCES anagrafiche.soggetti(id),
    soggetto_ruolo_id BIGINT
        REFERENCES anagrafiche.soggetti_ruoli(id),
    istanza_utility_id BIGINT
        REFERENCES anagrafiche.istanze_utilities(id),
    canale_id       INTEGER
        REFERENCES config.canali_pratiche(id),           -- riuso tabella config esistente
    categoria_id    INTEGER
        REFERENCES assistenza.categorie_ticket(id),
    priorita_id     INTEGER NOT NULL
        REFERENCES config.priorita_pratiche(id),          -- riuso tabella config esistente
    stato_id        INTEGER NOT NULL
        REFERENCES assistenza.stati_ticket(id),
    assegnato_a_id  BIGINT
        REFERENCES anagrafiche.risorse_umane(id),
    titolo          VARCHAR(200) NOT NULL,
    descrizione     TEXT,
    sla_ore         INTEGER,                              -- tempo massimo atteso in ore
    meta            JSONB NOT NULL DEFAULT '{}',
    storicizza      BOOLEAN NOT NULL DEFAULT true,
    tx_id           UUID,
    data_insert     TIMESTAMPTZ NOT NULL DEFAULT now(),
    user_insert     TEXT NOT NULL DEFAULT CURRENT_USER,
    data_update     TIMESTAMPTZ NOT NULL DEFAULT now(),
    user_update     TEXT NOT NULL DEFAULT CURRENT_USER
);
```

**Note progettuali:**

- `canale_id` e `priorita_id` riusano le tabelle config gia' esistenti (`config.canali_pratiche`, `config.priorita_pratiche`) — nessuna duplicazione
- Il contesto anagrafico a 3 livelli (soggetto → ruolo → istanza) e' lo stesso pattern di `pratiche.pratiche` v2
- `stato_id` punta a una tabella dedicata `assistenza.stati_ticket` (il ciclo di vita del ticket e' diverso da quello della pratica)
- `categoria_id` e' specifico del ticketing (es. GUASTO, INFORMAZIONE, RECLAMO, RICHIESTA_MODIFICA)

### assistenza.stati_ticket

```sql
CREATE TABLE assistenza.stati_ticket (
    id              INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    codice          VARCHAR(50) NOT NULL UNIQUE,
    codice_interno  VARCHAR(50) NOT NULL UNIQUE,
    descrizione     TEXT NOT NULL,
    attivo          BOOLEAN NOT NULL DEFAULT true,
    chiude_ticket   BOOLEAN NOT NULL DEFAULT false,       -- flag chiusura
    meta            JSONB NOT NULL DEFAULT '{}',
    data_insert     TIMESTAMPTZ NOT NULL DEFAULT now(),
    user_insert     TEXT NOT NULL DEFAULT CURRENT_USER,
    data_update     TIMESTAMPTZ NOT NULL DEFAULT now(),
    user_update     TEXT NOT NULL DEFAULT CURRENT_USER
);
-- Seed: APERTO, IN_LAVORAZIONE, IN_ATTESA, ESCALATO, RISOLTO, CHIUSO
```

### assistenza.categorie_ticket

```sql
CREATE TABLE assistenza.categorie_ticket (
    id              INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    codice          VARCHAR(50) NOT NULL UNIQUE,
    codice_interno  VARCHAR(50) NOT NULL UNIQUE,
    descrizione     TEXT NOT NULL,
    attivo          BOOLEAN NOT NULL DEFAULT true,
    meta            JSONB NOT NULL DEFAULT '{}',
    data_insert     TIMESTAMPTZ NOT NULL DEFAULT now(),
    user_insert     TEXT NOT NULL DEFAULT CURRENT_USER,
    data_update     TIMESTAMPTZ NOT NULL DEFAULT now(),
    user_update     TEXT NOT NULL DEFAULT CURRENT_USER
);
-- Seed: GUASTO, INFORMAZIONE, RECLAMO, RICHIESTA_MODIFICA, ATTIVAZIONE, DISATTIVAZIONE
```

### assistenza.ticket_pratiche (tabella ponte)

Collegamento M:N tra ticket e pratiche. Un ticket puo' generare piu' pratiche
(es. una di assistenza tecnica e poi una di preventivazione).
Una pratica potrebbe nascere da piu' ticket (aggregazione).

```sql
CREATE TABLE assistenza.ticket_pratiche (
    id              BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    ticket_id       BIGINT NOT NULL
        REFERENCES assistenza.ticket(id) ON DELETE NO ACTION,
    pratica_id      BIGINT NOT NULL
        REFERENCES pratiche.pratiche(id) ON DELETE NO ACTION,
    ruolo           VARCHAR(30) NOT NULL DEFAULT 'ORIGINE',  -- ORIGINE, CORRELATA, FOLLOW_UP
    note            TEXT,
    data_insert     TIMESTAMPTZ NOT NULL DEFAULT now(),
    user_insert     TEXT NOT NULL DEFAULT CURRENT_USER,
    CONSTRAINT uq_ticket_pratiche UNIQUE (ticket_id, pratica_id)
);
```

**Scelta architetturale**: tabella ponte in `assistenza` (Anello 3), non FK su `pratiche.pratiche`.
Il motore pratiche resta pulito e agnostico. La relazione e' gestita dallo schema chiamante.

### assistenza.ticket_worklog (tempo lavorato)

```sql
CREATE TABLE assistenza.ticket_worklog (
    id              BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    ticket_id       BIGINT NOT NULL
        REFERENCES assistenza.ticket(id) ON DELETE RESTRICT,
    risorsa_umana_id BIGINT NOT NULL
        REFERENCES anagrafiche.risorse_umane(id),
    data            DATE NOT NULL,
    inizio          TIMESTAMPTZ,
    fine            TIMESTAMPTZ,
    minuti          INTEGER NOT NULL CHECK (minuti > 0),
    articolo_id     UUID NOT NULL
        REFERENCES catalogo.articoli(id),                 -- servizio da catalogo
    approvato       BOOLEAN NOT NULL DEFAULT false,
    note            VARCHAR(500),
    meta            JSONB NOT NULL DEFAULT '{}',
    tx_id           UUID,
    data_insert     TIMESTAMPTZ NOT NULL DEFAULT now(),
    user_insert     TEXT NOT NULL DEFAULT CURRENT_USER,
    data_update     TIMESTAMPTZ NOT NULL DEFAULT now(),
    user_update     TEXT NOT NULL DEFAULT CURRENT_USER
);
```

### assistenza.ticket_materiali (materiali utilizzati)

```sql
CREATE TABLE assistenza.ticket_materiali (
    id              BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    ticket_id       BIGINT NOT NULL
        REFERENCES assistenza.ticket(id) ON DELETE RESTRICT,
    risorsa_umana_id BIGINT NOT NULL
        REFERENCES anagrafiche.risorse_umane(id),
    data            DATE NOT NULL,
    articolo_id     UUID NOT NULL
        REFERENCES catalogo.articoli(id),                 -- materiale da catalogo
    quantita        NUMERIC(12,3) NOT NULL CHECK (quantita > 0),
    approvato       BOOLEAN NOT NULL DEFAULT false,
    note            VARCHAR(500),
    meta            JSONB NOT NULL DEFAULT '{}',
    tx_id           UUID,
    data_insert     TIMESTAMPTZ NOT NULL DEFAULT now(),
    user_insert     TEXT NOT NULL DEFAULT CURRENT_USER,
    data_update     TIMESTAMPTZ NOT NULL DEFAULT now(),
    user_update     TEXT NOT NULL DEFAULT CURRENT_USER
);
```

---

## Ponte verso fatturazione

Il ponte tra ticketing e fatturazione riusa il meccanismo gia' descritto nella
bozza CRM/Ticketing (doc `Analisi_varie/Progetti-idee-sviluppo/integrazione-con-crm-e-ticketing.md`):
le righe approvate di `ticket_worklog` e `ticket_materiali` fluiscono in
`vendite.attivita_fatturabili` tramite campi fonte.

### Modifiche a vendite.attivita_fatturabili

Aggiungere (se non presenti):

```sql
ALTER TABLE vendite.attivita_fatturabili
    ADD COLUMN fonte_tipo     VARCHAR(32),        -- TICKET_WORKLOG, TICKET_MATERIALE, MANUALE
    ADD COLUMN fonte_id       BIGINT,             -- ticket_id
    ADD COLUMN fonte_riga_id  BIGINT;             -- worklog.id o materiali.id

CREATE UNIQUE INDEX uq_attivita_fonte_riga
    ON vendite.attivita_fatturabili (fonte_tipo, fonte_riga_id)
    WHERE fonte_riga_id IS NOT NULL;
```

**Flusso**: `worklog/materiale.approvato = true` → trigger o job pgAgent →
INSERT in `attivita_fatturabili` con `fonte_tipo + fonte_id + fonte_riga_id`.

---

## Configurazione pratiche per il ticketing

### Tipi prestazione da creare (seed)

| codice | codice_interno | descrizione | categoria | pre_attivazione | post_attivazione |
|--------|----------------|-------------|-----------|-----------------|------------------|
| `ASSISTENZA_TECNICA` | `ASSISTENZA_TECNICA` | Assistenza tecnica da ticket | ASSISTENZA | false | true |
| `PREVENTIVAZIONE` | `PREVENTIVAZIONE` | Preventivazione da diagnosi tecnica | COMMERCIALE | false | true |
| `INTERVENTO_PROGRAMMATO` | `INTERVENTO_PROGRAMMATO` | Intervento tecnico programmato | ASSISTENZA | false | true |

### Template flussi — ASSISTENZA_TECNICA

| sequenza | codice | descrizione | obbligatorio | direzione | handler_id |
|----------|--------|-------------|--------------|-----------|------------|
| 10 | `VALUTAZIONE` | Valutazione iniziale della richiesta | true | ENTRATA | NULL (manuale) |
| 20 | `ASSEGNAZIONE_TECNICO` | Assegnazione al tecnico competente | true | INTERNA | possibile handler |
| 30 | `DIAGNOSI_TECNICA` | Verifica tecnica sul campo | true | INTERNA | NULL (manuale) |
| 40 | `RISOLUZIONE` | Risoluzione del problema | false | INTERNA | NULL (manuale) |

### Template flussi — PREVENTIVAZIONE

| sequenza | codice | descrizione | obbligatorio | direzione | handler_id |
|----------|--------|-------------|--------------|-----------|------------|
| 10 | `REDAZIONE_PREVENTIVO` | Redazione del preventivo | true | INTERNA | possibile handler |
| 20 | `INVIO_CLIENTE` | Invio preventivo al cliente | true | USCITA | possibile handler |
| 30 | `APPROVAZIONE_CLIENTE` | Attesa approvazione cliente | true | ENTRATA | NULL (manuale) |
| 40 | `ESECUZIONE_LAVORO` | Esecuzione intervento | true | INTERNA | NULL (manuale) |
| 50 | `VERIFICA_COMPLETAMENTO` | Collaudo e verifica | false | INTERNA | NULL (manuale) |
| 60 | `FATTURAZIONE` | Generazione fattura | true | USCITA | handler fatturazione |

### Regole generazione cross-pratica

| template_flusso_origine | tipo_prestazione_dest | esito_richiesto | auto | descrizione |
|-------------------------|-----------------------|-----------------|------|-------------|
| ASSISTENZA_TECNICA.DIAGNOSI_TECNICA | PREVENTIVAZIONE | NEGATIVO | true | Diagnosi negativa → apre preventivazione automatica |
| ASSISTENZA_TECNICA.DIAGNOSI_TECNICA | INTERVENTO_PROGRAMMATO | POSITIVO | false | Diagnosi positiva → possibilita' di aprire intervento (manuale) |

### Prerequisiti flussi

**ASSISTENZA_TECNICA:**

```text
ASSEGNAZIONE_TECNICO richiede VALUTAZIONE (obbligatorio)
DIAGNOSI_TECNICA richiede ASSEGNAZIONE_TECNICO (obbligatorio)
RISOLUZIONE richiede DIAGNOSI_TECNICA (obbligatorio)
```

**PREVENTIVAZIONE:**

```text
INVIO_CLIENTE richiede REDAZIONE_PREVENTIVO (obbligatorio)
APPROVAZIONE_CLIENTE richiede INVIO_CLIENTE (obbligatorio)
ESECUZIONE_LAVORO richiede APPROVAZIONE_CLIENTE (obbligatorio)
VERIFICA_COMPLETAMENTO richiede ESECUZIONE_LAVORO (consigliato)
FATTURAZIONE richiede ESECUZIONE_LAVORO (obbligatorio)
```

---

## Gap analysis — cosa manca per l'integrazione

### Prerequisito: Pratiche v2 completate

Prima di sviluppare il ticketing, le fasi 2-5 di [gestione-pratiche-v2.md](../work-done/gestione-pratiche-v2.md)
devono essere completate. In particolare:

- G4-G6: Backend con display fields e nuovi campi (soggetto_ruolo_id, istanza_utility_id)
- G8: Frontend aggiornato per i nuovi campi
- G11-G12: API note e allegati

### DB — Schema `assistenza` (nuovo)

| # | Oggetto | Tipo | Dipendenze | Note |
|---|---------|------|------------|------|
| D1 | `CREATE SCHEMA assistenza` | DDL | — | Nuovo schema Anello 3 |
| D2 | `assistenza.stati_ticket` | Tabella config | D1 | Ciclo vita ticket |
| D3 | `assistenza.categorie_ticket` | Tabella config | D1 | Tipologie ticket |
| D4 | `assistenza.ticket` | Tabella operativa | D1, D2, D3 | FK a config, anagrafiche, pratiche |
| D5 | `assistenza.ticket_pratiche` | Tabella ponte | D4 | Collegamento M:N ticket ↔ pratica |
| D6 | `assistenza.ticket_worklog` | Tabella operativa | D4 | Tempo lavorato |
| D7 | `assistenza.ticket_materiali` | Tabella operativa | D4 | Materiali utilizzati |
| D8 | Trigger guard contesto anagrafico su ticket | Trigger | D4 | Stesso pattern di `pratiche.trgfn_pratiche_guard_contesto` |
| D9 | Trigger guard transizioni stato ticket | Trigger | D2, D4 | Macchina a stati del ticket |
| D10 | Trigger giornale ticket (opzionale) | Trigger | D4 | Audit trail dedicato o riuso `pratiche.giornale` con scope esteso |
| D11 | Seed stati_ticket | Data | D2 | APERTO, IN_LAVORAZIONE, IN_ATTESA, ESCALATO, RISOLTO, CHIUSO |
| D12 | Seed categorie_ticket | Data | D3 | GUASTO, INFORMAZIONE, RECLAMO, RICHIESTA_MODIFICA, ecc. |
| D13 | Seed tipi_prestazione per assistenza | Data | Schema pratiche | ASSISTENZA_TECNICA, PREVENTIVAZIONE, INTERVENTO_PROGRAMMATO |
| D14 | Seed template_flussi per i nuovi tipi | Data | D13 | Flussi e prerequisiti come descritto sopra |
| D15 | Seed regole_generazione | Data | D14 | Cross-pratica da diagnosi tecnica |

### DB — Modifiche a schemi esistenti

| # | Oggetto | Schema | Tipo | Note |
|---|---------|--------|------|------|
| D16 | Campi fonte su `attivita_fatturabili` | vendite | ALTER | `fonte_tipo`, `fonte_id`, `fonte_riga_id` + unique parziale |
| D17 | Trigger/job import attivita' | vendite | Trigger o pgAgent | `approvato = true` → INSERT in attivita_fatturabili |

> **Nota**: nessuna modifica allo schema `pratiche`. Il motore rimane intatto.

### Backend — App `assistenza` (nuova)

| # | Componente | File | Dipendenze |
|---|------------|------|------------|
| B1 | App Django `assistenza` | `backend/apps/assistenza/` | Struttura standard |
| B2 | Repository ticket CRUD | `assistenza/db/assistenza_repository.py` | D4 |
| B3 | Repository worklog/materiali CRUD | `assistenza/db/assistenza_repository.py` | D6, D7 |
| B4 | Service ticket | `assistenza/services/assistenza_service.py` | B2, B3 |
| B5 | Service creazione pratica da ticket | `assistenza/services/assistenza_service.py` | B4 + pratiche_service |
| B6 | API ticket CRUD | `assistenza/api/views.py` | B4 |
| B7 | API worklog/materiali CRUD | `assistenza/api/views.py` | B4 |
| B8 | API escalation (ticket → pratica) | `assistenza/api/views.py` | B5 |
| B9 | TypedDict per ticket, worklog, materiali | `assistenza/types.py` | — |
| B10 | Test Django (unit + API) | `assistenza/tests/` | B1-B8 |
| B11 | Smoke test | `backend/scripts/smoke-test-assistenza.sh` | B6-B8 |

### Backend — Modifiche a moduli esistenti

| # | Componente | File | Note |
|---|------------|------|------|
| B12 | Handler "crea_pratica_da_ticket" | `pratiche/services/` o `assistenza/services/` | Orchestrazione: crea pratica + collegamento ponte |
| B13 | Endpoint attivita_fatturabili (se non esiste) | `vendite/api/` | Per il ponte worklog → fatturazione |

### Frontend — Modulo `assistenza` (nuovo)

| # | Componente | File | Note |
|---|------------|------|------|
| F1 | Store ticket | `src/assistenza/stores/ticketStore.js` | CRUD + lookup |
| F2 | TicketSearchTable | `src/assistenza/components/TicketSearchTable.vue` | Lista ticket con filtri |
| F3 | TicketDrawer | `src/assistenza/components/TicketDrawer.vue` | Creazione + dettaglio |
| F4 | Tab Worklog nel drawer | `src/assistenza/components/TicketWorklogTab.vue` | Lista + form inline |
| F5 | Tab Materiali nel drawer | `src/assistenza/components/TicketMaterialiTab.vue` | Lista + form inline |
| F6 | Tab Pratiche collegate | `src/assistenza/components/TicketPraticheTab.vue` | Lista pratiche da ponte |
| F7 | Azione "Escalation" nel drawer | Bottone nel drawer | Crea pratica da ticket |
| F8 | Navigazione sidebar | `src/core/navigation.js` | Voce "Assistenza" |
| F9 | i18n | `src/locales/it.json`, `en.json` | Chiavi per assistenza |

### Frontend — Modifiche a moduli esistenti

| # | Componente | File | Note |
|---|------------|------|------|
| F10 | PraticaDrawer — tab "Ticket origine" | `src/pratiche/components/` | Mostra ticket collegati via ponte (opzionale, lettura) |

---

## Ordine di sviluppo consigliato

```text
Prerequisito: Pratiche v2 completate (fasi 2-5)
              │
              v
Fase A — DB assistenza (D1-D15)
  A.1: Schema + tabelle config (D1-D3, D11-D12)
  A.2: Tabella ticket + trigger guard (D4, D8, D9)
  A.3: Tabelle ponte + worklog + materiali (D5-D7)
  A.4: Seed tipi_prestazione + template_flussi + regole (D13-D15)
  A.5: Trigger giornale ticket (D10)
              │
              v
Fase B — DB vendite ponte (D16-D17)
  B.1: ALTER attivita_fatturabili (campi fonte)
  B.2: Trigger/job import attivita'
              │
              v
Fase C — Backend assistenza (B1-B11)
  C.1: App + types + repository (B1-B3, B9)
  C.2: Service + API ticket CRUD (B4, B6)
  C.3: Service + API worklog/materiali (B7)
  C.4: Service escalation ticket → pratica (B5, B8, B12)
  C.5: Test + smoke test (B10, B11)
              │
              v
Fase D — Frontend assistenza (F1-F9)
  D.1: Store + SearchTable + Drawer base (F1-F3, F8, F9)
  D.2: Tab worklog + materiali (F4, F5)
  D.3: Tab pratiche collegate + escalation (F6, F7)
  D.4: PraticaDrawer — tab ticket origine (F10, opzionale)
```

---

## CRM — posizionamento architetturale (sviluppo futuro)

Il CRM non viene sviluppato ora, ma la sua collocazione e' gia' definita:

### Posizione

- **Schema**: `crm` (Anello 3, come `assistenza` e `vendite`)
- **Tabelle principali**: `crm.opportunita`, `crm.opportunita_prodotti`
- **Collegamento a pratiche**: stessa logica del ticketing — tabella ponte `crm.opportunita_pratiche`

### Flusso CRM → Vendite

```text
crm.opportunita (pipeline commerciale)
    │
    ├── stadio "Offerta" → vendite.preventivi + preventivi_righe
    │                       (da opportunita_prodotti)
    │
    └── stadio "Vinto"  → vendite.contratti + contratti_righe
                           (con tipo_erogazione, periodicita')
```

### Dipendenze

Il CRM dipende da:

1. **Anello 1**: `anagrafiche` (soggetti, billing_account), `catalogo` (articoli)
2. **Anello 2**: `pratiche` (per workflow strutturati su opportunita' complesse)
3. **Anello 3**: `vendite` (preventivi, contratti, attivita_fatturabili)

### Relazione CRM ↔ Ticketing

```text
CRM (pre-vendita)                    Ticketing (post-vendita)
  opportunita                          ticket
      │                                    │
      ├── genera preventivo                ├── genera pratica assistenza
      ├── genera contratto                 ├── genera pratica preventivazione
      └── genera pratica (opzionale)       └── genera attivita' fatturabili
```

I due moduli sono **indipendenti** ma condividono:

- Lo stesso contesto anagrafico (soggetto → ruolo → istanza)
- Lo stesso motore pratiche per workflow strutturati
- Lo stesso ponte verso `vendite.attivita_fatturabili` per la fatturazione
- Le stesse tabelle config (`priorita_pratiche`, `canali_pratiche`)

---

## Riepilogo decisioni

1. **Il ticket e' il punto di ingresso, la pratica e' il motore di processo** — il ticket cattura la richiesta raw, la pratica gestisce il workflow strutturato
2. **Tabella ponte M:N** (`assistenza.ticket_pratiche`) — nessuna FK su `pratiche.pratiche` verso il ticketing
3. **Riuso config esistente** — `canali_pratiche`, `priorita_pratiche` condivisi tra pratiche e ticket
4. **Stati ticket dedicati** — il ciclo di vita del ticket e' piu' semplice di quello della pratica
5. **Contesto anagrafico a 3 livelli** — il ticket eredita lo stesso pattern della pratica v2
6. **Cross-pratica per escalation** — la generazione automatica di pratiche da ticket usa `regole_generazione`
7. **Ponte fatturazione** — worklog/materiali → `attivita_fatturabili` via campi fonte
8. **CRM posizionato, non sviluppato** — stesso modello architetturale, sviluppo futuro indipendente
9. **Nessuna modifica al motore pratiche** — Anello 2 resta intatto e agnostico

---

*Documento di integrazione CRM, Ticketing e Pratiche — ZeroERP (29 marzo 2026)*
