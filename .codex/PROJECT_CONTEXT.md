# ZeroErp — Contesto di Progetto per Sessioni AI

> Questo file è pensato per essere letto all'inizio di ogni sessione Claude Code,
> su qualsiasi server (DB o backend). Integra AGENTS.md con lo stato corrente del progetto.

## Identità del Progetto

- Nome: ZeroErp
- Tipo: ERP open-source (GPL v3), progetto serio orientato alla produzione
- Autore: Tid (Michele Carlo Titini) — 30+ anni di esperienza ERP (AS/400)
- Repo: https://github.com/Tito-it/ZeroErp
- Lingua doc/commenti: it-IT

## Filosofia Architetturale (NON negoziabile)

1. **DB-first**: tutta la logica di business vive in PostgreSQL (funzioni, trigger, viste)
2. **Django**: orchestrazione, API REST, e logica che non può stare nel DB
3. **Vue** (futuro): SOLO presentazione — zero logica business nel frontend
4. **No logica duplicata** tra livelli: se è nel DB non va replicata in Python, e viceversa

## Stack Tecnico

| Componente | Versione | Note |
|---|---|---|
| Python | 3.14 (da `.python-version`) | Fonte unica di verità per versione |
| Django | 6.01 | DRF 3.16, SimpleJWT, drf-spectacular |
| PostgreSQL | 18 (CI) | PostGIS 3.6, pgTAP, pgAgent |
| Liquibase | 5 Community | Migrazioni YAML in `db/changelog/migrations_v2/` |
| Vue 3 | placeholder | Non ancora sviluppato |

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
│   ├── apps/                 # App per dominio
│   │   ├── core/             # Utilities trasversali (error_manager, middleware, throttling)
│   │   ├── acquisti/
│   │   ├── anagrafiche/
│   │   ├── catalogo/
│   │   ├── config/
│   │   ├── contabilita/
│   │   ├── magazzino/
│   │   ├── pagamenti/
│   │   ├── storico/
│   │   └── vendite/          # App più attiva — pipeline fatturazione
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
│   ├── linee-guida-sql.md    # LEGGERE prima di scrivere SQL
│   ├── linee-guida-trigger.md
│   ├── guide/                # Guide operative (fatturazione, pagamenti, ecc.)
│   ├── dbzero/<schema>/      # Doc auto-generata (NON modificare)
│   └── dbzero/<schema>/manual/  # Doc manuale (modificare qui)
├── .codex/AGENTS.md          # Istruzioni per agenti AI
├── .codex/PROJECT_CONTEXT.md # Questo file
└── .python-version           # Fonte unica versione Python
```

## Schemi DB (13 totali)

| Schema | Scopo |
|---|---|
| `anagrafiche` | Soggetti, indirizzi, contatti, ruoli |
| `catalogo` | Articoli, listini, UoM, distinte base |
| `config` | Dati di riferimento (stati, nazioni, termini pagamento) |
| `vendite` | Ciclo vendite: preventivi→ordini→DDT→fatture + pipeline fatturazione |
| `acquisti` | Ciclo acquisti |
| `magazzino` | Movimenti, giacenze, lotti, seriali |
| `pagamenti` | Scadenze, riconciliazioni, contabili |
| `contabilita` | Piano conti, registrazioni, partite |
| `storico` | Audit temporale (storicizzazione tabelle) |
| `dbops` | Strumenti DBA, registry task, FK policy |
| `script` | Viste e funzioni applicative riusabili (incl. risoluzione permessi) |
| `maintenance` | Job schedulati (pgAgent) |
| `public` | Oggetti pubblici (version_info) |

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
assert value is not None  # sempre dopo require, per il type checker

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

## Stato Attuale del Progetto (aprile 2026)

### Completato ✅
- Refactor permessi (08-03-2026): 9 funzioni risoluzione permessi spostate da `config` a `script` — migrations `20260308-01..12`, Python backend + pgTAP test + doc aggiornati
- Pipeline fatturazione: `vendite.fatturazione_pipeline` + runner Django (`LottoPipelineRunner`)
- Lotti massivi e giornalieri con stati (DRAFT→EMESSA→DEFINITIVA)
- Registry task DB multi-dominio (`dbops.domini_task`, `pipeline_task_registry`, `pipeline_task_registry_impl`)
- Dispatch task con `implementation_key` controllato (no dynamic import)
- Log fatture e flag `critical` (`vendite.fatture_log`)
- Refactor fondi fattura (contabili/righe)
- Refactor saldo fattura (residuo + saldo contabile postabile)
- Payload SDI preparato (`fn_prepare_sdi_payload`)
- Runtime task tracing: `vendite.fatturazione_pipeline_task_policy` + `vendite.fatturazione_lotti_task_runs`
- Test pgtap runtime task + test Django pipeline runner
- **Listini v3 completo** (12-04-2026): Sprint B-v3 — N8a variazione % massa, N2 alert scadenze, N6 rettifica controllata, N5 riallineamento prezzo, N7 variazione eccezionale + sblocco, trigger DB guard, 6 endpoint API, 24 test, doc API
- **Migrazione daterange** (12-04-2026): 18 tabelle migrate a `daterange`/`tstzrange` nativo, `script.trgfn_set_validita()`, backend ottimizzato con `@>`, linee guida SQL §7b
- **Pricing commesse** (12-04-2026): riallineamento prezzo, variazione eccezionale, sblocco — 3 endpoint API con lock FOR UPDATE e audit trail

### Aperto — Media priorità
- **Registry runtime Python multi-dominio**: modello DB pronto, ma la mappa Python per tutti i domini non è completa
- **Builder XML SDI**: payload pronto, ma generazione file FatturaPA non ancora implementata
- **Persistenza esito SDI**: `vendite.fatture_sdi` e `vendite.fatture_sdi_eventi` da popolare

### Note operative
- `config.stati_doc_fiscale.chiude_lotto = true` → unico meccanismo di chiusura lotto (nessun hardcode)
- Reset lotto MASSIVO: ammesso in DRAFT; la DEFINITIVA fa resume per fattura (non reset globale)
- La procedura SQL `pr_run_lotto_pipeline` è deprecata e in fase di rimozione lato DB; l'orchestrazione è in Django (`run_lotto_pipeline`)

## File Django Chiave (vendite)

```
apps/vendite/
├── services/
│   ├── pipeline_runner.py          # LottoPipelineRunner — orchestrazione step pipeline
│   ├── pipeline_step_executor.py   # Esecuzione singolo step + dispatch task
│   └── fatture_righe_service.py    # Generazione righe fattura
├── db/ o repositories/
│   └── vendite_pipeline_repository.py  # Lookup registry DB, fn SQL
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

# Liquibase locale
make db-migrate       # applica migrazioni
make db-ci-apply      # applica automazioni CI
make db-setup         # entrambi
```

## Documentazione di Riferimento Rapido

- Convenzioni SQL: `docs/it/linee-guida-sql.md`
- Convenzioni trigger: `docs/it/linee-guida-trigger.md`
- Guida fatturazione: `docs/it/guide/fatturazione.md`
- WIP pipeline: `docs/it/dev/work-done/fatturazione-attivita-progetto.md`
- WIP domini engine: `docs/it/dev/work-in-progress/pipeline-domini-engine.md`
- Template doc backend: `docs/it/backend/_templates/manual-standard.md`
