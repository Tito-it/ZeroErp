# ZeroErp — Contesto di Progetto per Sessioni AI

> Questo file è pensato per essere letto all'inizio di ogni sessione Claude Code,
> su qualsiasi server (DB o backend). Integra AGENTS.md con lo stato corrente del progetto.
>
> Ultima revisione: 2026-11-08.

## Identità del Progetto

- Nome: ZeroErp
- Tipo: ERP open-source (AGPL v3, doppia licenza con licenza commerciale), progetto serio orientato alla produzione
- Autore: Tid (Michele Carlo Titini) — 30+ anni di esperienza ERP (AS/400)
- Repo: https://github.com/Tito-it/ZeroErp
- Lingua doc/commenti: it-IT

## Filosofia Architetturale (NON negoziabile)

1. **DB-first**: tutta la logica di business vive in PostgreSQL (funzioni, trigger, viste)
2. **Django**: orchestrazione, API REST, e logica che non può stare nel DB
3. **Vue**: SOLO presentazione — zero logica business nel frontend
4. **No logica duplicata** tra livelli: se è nel DB non va replicata in Python, e viceversa
5. ⛔ **Si progetta sul modello, mai su una fotografia**: le misure sui *dati* del DB
   di sviluppo (`count(*)`, «zero righe in quello stato», «N su M») non decidono
   nulla — decide ciò che il modello **ammette**. Le misure sulla *struttura*
   (nullabilità, CHECK, RLS, GRANT, corpo di una funzione) sì: quelle sono il
   progetto, non il contenuto. Regola completa, con il corollario sui test, in
   [AGENTS.md § «Regola zero — le misure non disegnano il progetto»](AGENTS.md)

## Stack Tecnico

| Componente | Versione | Note |
|---|---|---|
| Python | da `.python-version` | Fonte unica di verità per la versione |
| Django | da `backend/requirements.in` | DRF, SimpleJWT, drf-spectacular; versioni esatte nel lock `requirements.txt` |
| PostgreSQL | 18 (CI) | PostGIS 3.6, pgTAP, pgAgent |
| Liquibase | 5 Community | Migrazioni YAML in `db/changelog/migrations_v2/` |
| Frontend Vue | da `frontend/package.json` | **Fonte unica di verità per le versioni** (Vue, Vite, PrimeVue, Pinia, Vue Router, vue-i18n, Axios; Node in `engines.node`): ⛔ non ricopiarle qui. Standard: `docs/it/dev/frontend/frontend-standards.md` + catalogo BB FE |

## Infrastruttura di Sviluppo

- **Server DB**: PostgreSQL su server dedicato
- **Server backend**: Django, accessibile via VSCode SSH
- **Branch centrale**: `Tito-dev` (integrazione); branch di lavoro: `dev/db-tid` e `dev/backend-tid`
- **Flusso PR**: branch lavoro → `Tito-dev` → `main`
- **CI**: due workflow — `ci.yaml` (build+docker+docs) e `ci-validate.yaml` (test backend+DB)

## Struttura Repository

```
ZeroErp/
├── backend/                  # Django project
│   ├── zeroerp_backend/      # Config Django (settings, urls, wsgi)
│   ├── apps/                 # App per dominio — 17, elenco COMPLETO (2026-09-09)
│   │   ├── core/             # Utilities trasversali (error_manager, middleware, throttling)
│   │   ├── ai_assistant/     # Assistente AI: 18 tool, provider pluggabile. Dietro AI_ENABLED
│   │   ├── amm_software/     # Amministrazione software (AdminAPIView, SUPER_ADMIN)
│   │   ├── anagrafiche/
│   │   ├── catalogo/
│   │   ├── config/
│   │   ├── documenti/        # Motore documentale parametrico + ristampa fedele
│   │   ├── pagamenti/
│   │   ├── portale/          # Veste CLIENTE_PORTALE / FORNITORE_PORTALE (auth + attivazione)
│   │   ├── pratiche/         # Motore di workflow versionato
│   │   ├── shop/             # Veste SHOP_CUSTOMER (auth + attivazione)
│   │   ├── ui/               # Liste configurabili: la configurazione è DATO, non DDL
│   │   ├── vendite/          # App più attiva — pipeline fatturazione
│   │   ├── acquisti/         # 🔵 PROSSIMO CANTIERE (Tid, 2026-09-11) — modello a DB, comportamento da scrivere
│   │   ├── magazzino/        # 🔵 CANTIERE APERTO (idem) — Lotti 1-2 chiusi; Lotti 3 e 3-bis fatti, da collaudare a video
│   │   ├── storico/          # ⚠️ scheletro (13 file, 23 righe, 0 test) — nessuna decisione presa
│   │   └── contabilita/      # ⛔ scheletro vuoto — schema DB vuoto, fuori perimetro per decisione
│   ├── requirements.in       # Dipendenze dirette (editare qui)
│   └── requirements.txt      # Generato da pip-compile (non editare)
├── db/
│   └── changelog/migrations_v2/  # Tutte le migrazioni Liquibase
│       ├── 00_schema/        # DDL tabelle
│       ├── 20_code/          # Funzioni, trigger, viste
│       ├── 80_data/          # Seed dati
│       └── 90_end/           # Indici FK (apply_fk_index_policy)
├── db/pgtap/                 # Test DB con pgTAP
├── docs/it/                  # Documentazione MkDocs
│   ├── linee-guida-sql.md    # prima di scrivere SQL: titoli, poi le sezioni toccate
│   ├── linee-guida-trigger.md
│   ├── guide/                # Guide operative (fatturazione, pagamenti, ecc.)
│   ├── dbzero/<schema>/      # Doc auto-generata (NON modificare)
│   └── dbzero/<schema>/manual/  # Doc manuale (modificare qui)
├── .codex/AGENTS.md          # Istruzioni per agenti AI
├── .codex/PROJECT_CONTEXT.md # Questo file
└── .python-version           # Fonte unica versione Python
```

## Schemi DB

| Schema | Scopo |
|---|---|
| `anagrafiche` | Soggetti, indirizzi, contatti, ruoli, emittenti fiscali |
| `catalogo` | Articoli, UoM, distinte base |
| `config` | Dati di riferimento (stati, nazioni, termini pagamento, regimi fiscali…) e credenziali |
| `vendite` | Ciclo vendite: preventivi→ordini→DDT→fatture + pipeline fatturazione |
| `acquisti` | Ciclo acquisti |
| `magazzino` | Movimenti, giacenze, lotti, seriali |
| `pagamenti` | Scadenze, riconciliazioni, contabili |
| `documenti` | Motore documentale: template versionati, documenti generati, ristampa fedele |
| `pratiche` | Motore di workflow versionato |
| `ui` | Liste configurabili (la configurazione è dato) |
| `shop` | Veste SHOP_CUSTOMER |
| `contabilita` | ⛔ **VUOTO e fuori perimetro**: zero tabelle, funzioni e viste. Se servirà sarà un **aggancio a una contabilità esterna**, con la forma dettata dal sistema di destinazione |
| `storico` | Audit temporale (storicizzazione tabelle) |
| `dbops` | Strumenti DBA, registry task, presidi, FK policy |
| `script` | Viste e funzioni applicative riusabili (building block, risoluzione permessi) |
| `maintenance` | Job schedulati (pgAgent) |
| `django` | Tabelle di Django (auth, sessioni) |
| `public` | Estensioni (`dblink`, `unaccent`, `postgis`, `plpgsql_check`, `btree_gist`), **nessuna tabella**. Per la versione applicata: `DATABASECHANGELOG` |

Schemi non applicativi presenti su dbdev: `topology` (PostGIS), `pgagent` (scheduler),
`data_conversion`, `internal`, `test`.

## Struttura App Django (pattern per ogni dominio)

```
apps/<dominio>/
├── api/
│   ├── views.py       # ViewSet / APIView
│   └── urls.py        # Route
├── services/          # Orchestrazione business logic
├── db/ o repositories/ # Accesso DB/SQL (cursor, funzioni PG)
├── models.py          # Minimale, managed=False dove possibile
└── tests/
    ├── api/
    └── services/
```

## Pattern Backend Chiave

### Error handling
```python
# In services: usa ServiceError
from apps.core.services.error_manager import ErrorManager, ServiceError

# Guard su valori richiesti:
ErrorManager.require(value is not None, "CODICE_ERRORE", "messaggio")
assert value is not None  # sempre dopo require, per il type checker (mypy, in CI dal 2026-10-08)

# In views: NON catturare Exception generici
# Il middleware apps/core/middleware/api_exception_middleware.py gestisce il fallback
```

### Endpoint API (pattern uniforme)
```python
from apps.core.api.endpoint_helpers import handle_post_json

# Usa handle_post_json per parsing input + error envelope uniforme
```

### Accesso DB
```python
# Dopo fetchone() aggiungere sempre guard:
row = cursor.fetchone()
if not row:
    raise ServiceError(...)
# oppure: assert row is not None
```

### Commenti Python (obbligatori)
```python
# Scopo: descrizione sintetica della funzione/metodo
def nome_metodo(self, ...):
    ...

# Per metodi complessi (pipeline, transazioni, dispatch):
# Scopo: obiettivo, perimetro e risultato atteso dettagliati
```

## Stato del Progetto — cantieri

> Lo stato reale sta nei documenti di `docs/it/dev/work-in-progress/` e nel repo; qui solo
> le decisioni di rotta e una riga per cantiere aperto.

### ⛔ Fermo dei temi trasversali sui documenti di vendita (Tid, 2026-10-21; allentato il 2026-10-25)

Il modello del documento di vendita è scritto:
[guida del modello](../docs/it/guide/modello-documento-di-vendita.md). Il fermo resta, **allentato**
(Tid, 2026-10-25, scelta C):

- ✅ un tema nuovo che tocca tutti i documenti di vendita (preventivo, offerta, contratto, ordine,
  DDT, reso, commessa, fattura, listino) è ammesso **se poggia su un pezzo comune già fatto** (un
  building block montato su tutte le testate, come la nascita nello stato iniziale) e rispetta la
  guida;
- ⛔ resta fermo il tema che andrebbe **ricopiato documento per documento** (nelle capability, nei
  guard, nei verbi di ciascuno): aspetta che il cantiere porti quei documenti al modello.

Si correggono i difetti; i brief già in esecuzione arrivano in fondo. Il perché, con i fatti datati,
sta nel §1 di `work-done/brief-modello-documento-vendita.md`. La regola generale «un tema, un
brief» è in `.codex/AGENTS.md`.

### 🔵 Il cantiere principale — `acquisti` e `magazzino` (decisione di Tid, 2026-09-11)

Le due app sono il cantiere in corso (voce D11 di
[migliorie-generali-BE-FE-da-test-valutazione.md](../docs/it/dev/work-done/migliorie-generali-BE-FE-da-test-valutazione.md)).
`magazzino` ha il comportamento dei Lotti 1-2; `acquisti` ha il solo modello DB.

⭐ **Ogni decisione presa su `vendite` è presa anche per `acquisti`** — envelope,
capability di riga, scope emittente, ordinamento, export, drawer autonomi,
`ListaConfigurabile`. Quando un'asimmetria fra i due domini emerge, si chiude
**subito**, non in una «fase due».

⚠️ `storico` **resta senza decisione** e `contabilita` resta **fuori perimetro**:
non sono la stessa cosa e non vanno letti insieme ai due sopra.

- **Magazzino, Lotti 1 e 2: chiusi** (`work-done/brief-db-magazzino-lotto-1-terreno-vuoto.md`,
  `work-done/brief-db-magazzino-lotto-2-motore.md`, `work-done/piano-be-fe-magazzino-lotto-2-motore.md`;
  API in `docs/it/backend/magazzino/manual/api_magazzino.md`). ⏳ Collaudo a video di Tid:
  `work-in-progress/collaudo-in-app-magazzino-inventario-e-rettifica.md`.
- ⏳ **Magazzino, Lotti 3 e 3-bis — la merce esce con la bolla e rientra col reso**: DB applicato
  (28/29-09), BE/FE fatto il 2026-10-13; i due brief DB **chiusi il 2026-10-14**
  (`work-done/brief-db-magazzino-lotto-3-scarico-da-ddt.md`, `work-done/brief-db-magazzino-lotto-3-bis-carico-da-reso.md`).
  Aperto in un solo documento, `work-in-progress/piano-be-fe-magazzino-lotto-3.md` (§5 i residui: CI da zero,
  vista della merce in viaggio, pgTAP kit/seriali col runner); ⏳ collaudo a video di Tid:
  `work-in-progress/collaudo-in-app-magazzino-bolla-e-reso.md`. Il difetto DB dei motivi della «Conferma» del reso
  è chiuso il 2026-10-14 (`work-done/brief-db-reso-motivi-conferma-con-valori.md`), a video al §5.3/§5.7 del collaudo.
- 📝 **Magazzino: tutte le scritture dal verbo**
  (`work-in-progress/brief-db-magazzino-tutte-le-scritture-dal-verbo.md`): bozza, cinque decisioni di Tid (§3).
- **`acquisti`**: le due date di `acquisti.ordini_righe` sono a DB **senza consumatore** (nessun
  repository di righe, nessuna chiave i18n). Alla ripartenza: quali articoli ammettono le righe
  d'acquisto è rinviato a `work-done/brief-db-articoli-ammessi-per-documento.md` §8.4 (D-5).

⭐ **I domini nuovi nascono con il permesso applicato dal DB**
(`work-done/brief-db-permesso-nel-verbo-di-scrittura.md`, D-1 → D-5 di Tid). Il modello è
«una scrittura = un verbo»: una funzione DB che nella prima riga chiama un guard —
`script.fn_guard_azione` (azione di processo), `script.fn_guard_livello` (livello sull'oggetto)
o `script.fn_guard_super_admin` (gestione accessi) — e l'app che perde la scrittura diretta sulle
tabelle che il verbo protegge (guida `architettura-permessi-e-autorizzazioni.md` §7.4-7.5).
`magazzino` e `acquisti` nascono così; gli altri domini ci passano quando un cantiere tocca le loro
scritture. Il limite è scritto: il modello protegge da un backend che **sbaglia**, non da uno
**manomesso** (l'identità la dichiara il backend). Già su verbo: le poste di inventario e
rettifica (`registra_magazzino`), il pannello di configurazione (`config.fn_pannello_scrivi`, lista
in `config.tabelle_gestibili`; `config.aree_funzionali` in sola lettura per l'app).

### 🟡 Altri cantieri aperti

- **Accessi: una credenziale, più vesti** (`work-in-progress/piano-be-fe-accessi-credenziale-e-vesti.md`):
  resta R-4, che vuole un brief DB non ancora scritto. ✅ L-6 (date della veste) fatto il 2026-10-07,
  DB e BE/FE (`work-done/brief-db-veste-utilizzabile.md`; giro 3 chiuso: «Valido al» del drawer operatore
  modificabile, spento col motivo per l'ultimo SUPER_ADMIN senza data di fine, `null` toglie la data): la regola «veste
  utilizzabile» sta in un BB a DB (`script.fn_veste_utilizzabile`), letto da tutte le sedi DB e dai
  cinque punti del BE; per l'operatore contano anche le date del rapporto; l'ultimo SUPER_ADMIN non
  scade e il batch notturno accende oltre che spegnere. ✅ L-4 fatto il 2026-10-06: portale e shop entrano con
  l'email, il reset accetta nome utente o email. Chiuso il 2026-10-03
  `work-done/brief-db-credenziale-verbi-amministratore.md` (motivo del blocco dal DB, verbi
  dell'amministratore che rifiutano le credenziali di sistema).
- 📝 **Dove si addebita il trasporto di un ordine fatturato alla conferma**
  (`work-in-progress/brief-db-addebito-trasporto-ordine.md`, da A-9 di
  `work-done/brief-db-articoli-ammessi-per-documento.md`): in corso dal 2026-11-03; chi riparte è in testa al brief.
- 📝 **La catena delle istanze su un PDP** (`work-in-progress/brief-db-catena-istanze-pdp.md`, D18 del registro DB):
  proposta da analizzare, cinque decisioni di Tid.
- **GUIDA roll-out multi-dominio** (`work-in-progress/brief-design-guida-rollout-multidominio.md`):
  deciso, si parte da OFFERTA.
- **PrimeVue 5** (`work-in-progress/piano-migrazione-primevue-5.md`): leggere prima il §1-bis, il
  cambio di licenza.
- 📝 **Gli stati del documento dal vocabolario** (`work-in-progress/brief-db-stati-documento-dal-vocabolario.md`):
  decisioni prese, aspetta il via.
- ⏳ **La provenienza del prezzo segue il prezzo** (`work-in-progress/brief-db-provenienza-prezzo-segue-il-prezzo.md`,
  decisione B di Tid del 2026-10-09): la riga di listino si cita solo se il prezzo viene davvero da lì. BE in attesa.

> I cantieri **chiusi** non stanno qui: ognuno ha il suo documento in `docs/it/dev/work-done/`, e ciò che ha
> lasciato aperto è una voce di § «Aperto — Media priorità». Alla chiusura di un brief la sua voce si **toglie**
> da questa lista, non si marca ✅.

### Aperto — Media priorità

> Qui c'è **una riga per residuo**: il titolo e, per i residui di un brief, i titoli delle sue voci. Il dettaglio
> (da dove viene, le strade, chi decide) sta nel
> [registro dei residui aperti](../docs/it/dev/work-in-progress/registro-residui-aperti.md), alla voce con lo
> **stesso titolo**: si apre quando il lavoro tocca quel punto. Un residuo nuovo si scrive nel registro e si
> aggiunge qui la sua riga; uno chiuso si toglie da tutti e due.

- **Briciole lasciate aperte da brief chiusi**: D31 resta aperta per ORARIO e CONSUMO; collaudo a video dei form di DDT e ordine; il «perché» nel tooltip di `RIGA_NON_AMMESSA`; D24, il presidio C2 non vede i BB trigger col codice in `TG_ARGV`; la sorgente sugli acquisti; i residui del cliente manuale
- **Residui di `work-done/brief-db-contratto-righe-periodiche-in-commessa.md`**: il collaudo a video; la colonna «Periodicità» della lista 37; gli smoke non lanciati nel giro BE
- **Residui di `work-done/brief-db-scadenza-preventivi.md`**: `validita_al` dice due cose; il verbo di chiusura del listino
- **Residui di `work-done/brief-modello-documento-vendita.md`**: i permessi `emetti_offerta`, `emetti_contratto`, `emetti_ordine`, `attiva_listino` ai profili; due rami del preventivo senza strada dall'interfaccia; `DocumentoDrawerHost` tace sul drawer che non si carica
- **Residui di `work-done/collaudo-in-app-capability-annidata-e-prezzi-autorizzati.md`**: il reset del rifiuto sta solo nel BE del preventivo; la riga `test-preventivi-approvazione-prezzo.sql`
- **Residui di `work-done/brief-db-modelli-documento-standard.md`**: il giro degli smoke su `dev.smoke`; B-8, la matrice utility dell'emittente; la numerazione della versione nuova; `vendite.fatture.utility_id NOT NULL`
- **Residui di `work-done/brief-db-presidio-job-run-a-chi-tocca.md`**: errori lato client senza SQLSTATE; `SMOKE_GIRO_FALLITO`; `error_detail` con la riga `CONTEXT:`; il `%TYPE` mancato del giro 1
- **Residui di `work-done/brief-db-dati-fiscali-e-societari-del-soggetto.md`**: D-4, che cosa registra il titolo IVA `COOPERATIVA`; censimento dei titoli IVA fuori regola; `SGT-0000121` con `cliente_pa = 'S'`; `anagrafiche.fornitori.split_payment`
- **La commessa vuota lasciata dal push batch** [DB + BE]
- **Residui di `work-done/brief-db-istanza-nasce-col-ba.md`**: collaudo a video delle pratiche
- **La coerenza tra codice fiscale e sesso ha una sede sola, e parziale** [DB + BE]
- **La corsa appesa non è «in corso» nella liveness del BE** [BE/FE]
- **La lista dei processi non dice se un processo gira adesso**
- **Presidi, i residui del brief dei testi per chi agisce**: D-4, le quattro misure larghe per costruzione; la postura in sola lettura di `dbops.presidi` per l'app
- **`HTML_MARKDOWN_BLOCKS` si sceglie ma non fa niente** [BE]
- **Le versioni pubblicate stampano coi margini delle colonne (15 mm), non coi 18/16 mm del loro CSS**
- 🟡 **L'editor dei workflow perde le righe in compilazione senza chiedere** [FE]
- **`E_ATTIVO_REQUIRE` è TECNICO anche quando il dato l'ha scelto una persona** [DB, `dbops`]
- 🟡 **IVA per cassa: i residui del cantiere** [DB]
- 🟡 **Le variabili di una versione di template non si validano alla pubblicazione** [DB + BE]
- ⏳ **«Annulla» e «Porta a Bozza» sulle distinte non manuali: spenti col motivo** [DB poi BE/FE]
- 🟡 **Colori PrimeVue ancora scritti nei componenti** [FE]
- 🟡 **`djangorestframework-simplejwt` senza un manutentore certo** [BE]
- ❓ **Le FK verso `django.auth_user` non nascono su un'installazione nuova** [DB]
- 🟡 **Tetto d'area dei permessi — due decisioni residue di Tid**
- **Il `codice` delle sei famiglie di documento di seed si perde al migrate** [DB]
- **Righe di listino: la gamba dei compositi bundle non è provata sul DB** [BE]
- **La matrice di `stato_lotto` in due sedi che dissentono** [BE + DB]
- **La porta dell'esito ancora aperta** [DB]
- **`zeroerp_log` in CI non ha `USAGE` su `dbops`: ogni test Django lavora con `tx_id = uuid_nil`** [DB+CI]
- **La distinta del fondo fattura fuori lotto** [DB]
- **`runOnChange` + `dbms:` in `80_data`/`90_end`: la ri-esecuzione una-tantum** [DB]
- **La scala di `vendite_contabili_righe.importo`** [DB]
- **Su quale documento si può registrare un incasso** [DB]
- **«Riavvia» un servizio dall'interfaccia** [DB + deploy + BE]
- **Il Giornale eventi non è multi-emittente** [DB]
- **Tendine del lookup generico senza `page_size`** [FE]
- **Registry runtime Python multi-dominio**
- **Builder XML SDI** (sospeso per decisione di Tid, 2026-08-05)
- **Persistenza esito SDI**
- **Pratica di approvazione prezzo su revisione superata** [BE]
- **L'L3 dei componenti non esiste** [DB + BE]
- **`user_update` nullable su nove tabelle senza audit** [DB]
- **Residui della roadmap fatturazione**: Esercizio fiscale come entità; Vista push; Alerting sui dati; Diagrammi di stato; Preview di fatturazione del contratto

### Note operative
- `config.stati_doc_fiscale.chiude_lotto = true` → unico meccanismo di chiusura lotto (nessun hardcode)
- Reset lotto MASSIVO: ammesso in DRAFT; la DEFINITIVA fa resume per fattura (non reset globale)
- L'orchestrazione della pipeline è in Django (`run_lotto_pipeline`), non in una procedura SQL

## File Django Chiave (vendite)

```
apps/vendite/
├── services/
│   ├── pipeline_runner.py          # LottoPipelineRunner — orchestrazione step pipeline
│   ├── pipeline_step_executor.py   # Esecuzione singolo step + dispatch task
│   └── fatture_righe_service.py    # Generazione righe fattura
├── db/
│   └── pipeline_repository.py      # Lookup registry DB, fn SQL
├── types.py                        # TypedDict per pipeline/lotto
└── tests/
    ├── services/
    │   ├── test_pipeline_runner.py
    │   └── test_pipeline_step_executor.py
    └── api/
        ├── test_pipeline_api.py
        └── test_reset_lotto_*.py
```

## Comandi Utili

```bash
# Test Django (dalla root backend/)
./manage-test.sh apps.vendite.tests.services -v 2
./manage-test.sh apps.vendite.tests.api -v 2
./manage-test.sh apps.core.tests.api -v 2

# Test DB (pgtap)
scripts/testpgtap.sh db/pgtap/<schema>/<test-file>.sql

# Aggiornare dipendenze backend
pip-compile backend/requirements.in --output-file backend/requirements.txt

# Aggiornare strumenti dev (mkdocs, pre-commit, ecc.)
scripts/update-venv.sh

# Liquibase: wrapper scripts/liquibase5.sh (procedura in docs/it/liquibase-setup-workflow.md).
# ⛔ Le migrazioni le applica Tid: l'hook guardrail_no_db_migrate.py le blocca all'agente.
```

## Documentazione di Riferimento Rapido

- Convenzioni SQL: `docs/it/linee-guida-sql.md`
- Convenzioni trigger: `docs/it/linee-guida-trigger.md`
- Guida fatturazione: `docs/it/guide/fatturazione.md`
- WIP pipeline: `docs/it/dev/work-done/fatturazione-attivita-progetto.md`
- Domini engine (archiviato 2026-08-22, con la verifica dei concetti in testa): `docs/it/dev/work-done/pipeline-domini-engine.md`
- Template doc backend: `docs/it/backend/_templates/manual-standard.md`
