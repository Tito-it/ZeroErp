# AGENTS.md

## Quick Start per AI Agent

- Progetto: ERP Django + PostgreSQL, open-source GPL v3
- Stack: Python 3.14, Django 6.01, Liquibase 5, PostgreSQL 18, pgTAP per test DB
- Prima di implementare: leggi docs in `docs/it/` pertinenti
- Struttura: backend in `backend/`, DB migrations in `db/changelog/migrations_v2/`
- Filosofia: **DB-first** — la logica di business sta in PostgreSQL; Django orchestra e espone API; Vue (futuro) solo presentazione
- **Metodologia di sviluppo**: seguire sempre il modello concentrico descritto in:
  - `docs/it/sviluppo-concentrico.md` — principi e fasi dello sviluppo concentrico
  - `docs/it/mappa-concentrica.md` — mappa delle dipendenze e ordine di costruzione

## Scope

- Repo: ZeroErp
- Default language: it-IT (docs, commenti Python e SQL)
- Follow docs in `docs/it/linee-guida-sql.md`, `docs/it/linee-guida-trigger.md`, `docs/it/liquibase-setup-workflow.md`

## Dipendenze e versioni runtime

- Prima di sviluppare, consultare le dipendenze correnti:
  - **Backend Python**: `backend/requirements.in` (dipendenze dirette) e `backend/requirements.txt` (lock file generato)
  - **Strumenti dev**: `requirements.txt` nella root (mkdocs, pre-commit, ecc.)
- **Liquibase 5** + **PostgreSQL 18**: usare sintassi e funzionalità compatibili con queste versioni (es. SQL/JSON standard ISO, funzioni PG 18)
- Non aggiungere dipendenze Python senza conferma dell'utente

## Ambiente di sviluppo

- **Due server separati**: un server DB (PostgreSQL) e un server backend (Django, accessibile via VSCode SSH)
- Il branch centrale di integrazione è `Tito-dev`; i branch di lavoro sono `dev/db-tid` (DB) e `dev/backend-tid` (backend)
- Le PR vanno da branch di lavoro → `Tito-dev` → poi a `main`
- Non eseguire migrazioni DB senza conferma esplicita dell'utente (vedi Workflow Safety)

## Versione Python

- **Fonte unica di verità**: `.python-version` nella root del repo (es. `3.14.2`)
- CI (`ci.yaml`, `ci-validate.yaml`) leggono da `.python-version` automaticamente
- `Dockerfile` usa `ARG PYTHON_VERSION` passato dalla CI; default nell'ARG allineato alla major.minor
- `backend/requirements.txt` è generato da pip-compile: editare `backend/requirements.in` e rieseguire:
  `pip-compile backend/requirements.in --output-file backend/requirements.txt`
- `requirements.txt` radice = strumenti dev (mkdocs, pre-commit…), gestito con `pip freeze` via `scripts/update-venv.sh`
- Per aggiornare la versione Python: modificare solo `.python-version`, poi rigenerare `backend/requirements.txt`

## Backend (Django)

- Codice backend in `backend/`
- **Documento di riferimento obbligatorio**: `docs/it/dev/api.md` — leggere PRIMA di qualsiasi intervento su endpoint, repository o service
- Versioni: Python 3.14, Django 6.01
- Evitare API/metodi deprecati; seguire best practice Django
- Accesso webserver configurato: test migrazione solo su richiesta
- Per i file Python **generati** aggiungere sempre l'header standard in `templates/python-header.txt`.
- Per ogni nuovo file Python (non generato da Django) aggiungere l'header standard di `templates/python-header.txt` e un breve commento iniziale sullo scopo.
- Nei file Python aggiungere un commento sintetico (`# Scopo: ...`) prima di ogni funzione/metodo (`def`/`async def`), in italiano.
- Per funzioni/metodi che orchestrano processi complessi (pipeline, transazioni, dispatch task, integrazioni esterne), rendere il commento `Scopo` iniziale piu` dettagliato: obiettivo, perimetro e risultato atteso.
- Nei file Python aggiungere commenti sintetici nei blocchi non banali (orchestrazione, transazioni, mapping task/SQL), scritti in italiano.
- Dopo un `ErrorManager.require(... is not None ...)` aggiungere sempre l'`assert` corrispondente per aiutare il type checker.
- Dopo `row = cursor.fetchone()` aggiungere guard (`if not row`) oppure `assert row is not None` prima di usare `row[...]`.
- Nei servizi/classi Python usare nomi metodo espliciti e orientati al dominio (es. `run_pipeline`), evitando nomi generici/ambigui come `run`.
- Per error handling servizi/API usare helper centralizzato in `apps/core/services/error_manager.py`, evitando logica duplicata nei moduli dominio.
- Il mapping `codice errore -> HTTP status -> azione UI` deve essere centralizzato in `apps/core/services/error_policies.py`.
- Struttura consigliata: project config in `backend/zeroerp_backend/`, app in `backend/apps/`
- App per dominio (es. `vendite`, `anagrafiche`), non per dettaglio tecnico; se uno schema DB coincide con un dominio stabile, la cartella app puo` allinearsi allo schema
- Orchestrazione in `apps/<dominio>/services/` (o `usecases/`); accesso DB/SQL in `apps/<dominio>/db/` o `repositories/`
- API in `apps/<dominio>/api/` o `views.py` + `urls.py`; modelli ORM solo dove utili, altrimenti `managed = False`

### Naming convention repository e service per app dominio

Ogni app puo' contenere piu' repository e service. La regola di naming e' basata sul **perimetro semantico**:

| Tipo | Nome file | Contenuto |
| --- | --- | --- |
| Generico schema | `<schema>_repository.py` | List, query, CRUD su entita' dello schema senza logica specifica (es. `vendite_repository.py`) |
| Sottodominio specializzato | `<sottodominio>_repository.py` | Operazioni di un processo autonomo con logica propria (es. `pipeline_repository.py`) |
| Generico schema | `<schema>_service.py` | Facade per operazioni generiche (es. `vendite_service.py`) |
| Sottodominio specializzato | `<sottodominio>_service.py` | Facade per il sottodominio (es. `pipeline_service.py`) |

**Regola pratica:**

- Usare `<schema>` (es. `vendite`) per operazioni che non appartengono a nessun sottodominio specifico: elenchi, ricerche, lettura stato entita'.
- Creare un file `<sottodominio>_*` **solo** quando il sottodominio ha logica orchestrata autonoma (runner, executor, tracing, saga): non per singoli metodi.
- Non frammentare in file per ogni entita': tre metodi su `fatture` e due su `lotti` stanno in `vendite_repository.py`, non in file separati.
- Esempio per `vendite`: `vendite_repository.py` (list lotti, list fatture, decodifiche), `pipeline_repository.py` (step, task run, job stato, pipeline config).
- Per endpoint API usare il pattern core `handle_post_json(...)` (`apps/core/api/endpoint_helpers.py`) per parsing/error envelope uniforme.
- Evitare `try/except Exception` generici nelle view API dominio: usare `ServiceError` nei service e lasciare fallback al middleware `apps/core/middleware/api_exception_middleware.py`.
- Il middleware eccezioni API si applica solo a `/api/*` e resta disattivabile via `DJANGO_API_EXCEPTION_MIDDLEWARE_ENABLED`.
- Per nuove API lista/search applicare la policy `docs/it/dev/Policy-ricerca-e-paginazione(API-DB).md` e usare gli helper core (`apps/core/api/pagination.py`, `apps/core/api/search_validators.py`).
- Per endpoint search impostare `is_search_endpoint = True` per attivare throttling DRF (`apps/core/api/throttling.py`).

## Frontend (Vue)

- Codice frontend in `frontend/`
- **Documento di riferimento obbligatorio**: `docs/it/dev/frontend/frontend-standards.md` — leggere PRIMA di qualsiasi intervento sul frontend
- **Guida sviluppo frontend**: `docs/it/dev/work-in-progress/frontend/guida-sviluppo-frontend.md` — convenzioni componenti, composable, routing, CSS, pattern operativi
- Stack: Vue 3.5, Vite 7, PrimeVue 4.5, Pinia 3, Vue Router 5, vue-i18n 10, Axios
- Runtime: Node.js 24 LTS (gestito via nvm)
- Dipendenze: `frontend/package.json`
- Non aggiungere dipendenze npm senza conferma dell'utente
- Filosofia: **zero logica business nel frontend** — solo presentazione, validazione UX e orchestrazione chiamate API
- Struttura cartelle allineata ai domini DB (es. `src/vendite/`, `src/anagrafiche/`)
- Moduli condivisi in `src/core/` — mai duplicare configurazioni, costanti o liste tra componenti
- La navigazione (domini, icone, rotte sidebar) e' centralizzata in `src/core/navigation.js`
- Le costanti UI (larghezze drawer, durata toast, paginazione) sono in `src/core/constants.js`
- Sicurezza: route guard su tutte le rotte (default protette), token refresh automatico, no `window.location` per redirect
- Multilingua: ogni testo visibile all'utente usa `$t()` — mai stringhe hardcoded nei componenti
- Build: `./node_modules/.bin/vite build` (richiede nvm per caricare Node)

## Liquibase v2 Workflow

- New work only in `db/changelog/migrations_v2/`
- File extension: `.yaml` only
- File naming: `YYYYMMDD-NN-<tipo>-<descrizione>.yaml`
- One changeSet per file
- Always set `logicalFilePath`
- `00_schema` and `20_code` are included via `migrations_v2/changelog-autogen.yaml` (autogen script)
- `80_data`, `85_pgagent`, `90_end` are included via `includeAll` in master
- **MAI modificare changelog già mergiati/pushati su GitHub** — si rompe la sequenza Liquibase dei checksum. Per aggiornare funzioni/trigger con `runOnChange: true`, creare SEMPRE un nuovo file con numerazione successiva (es. `20260225-37-update-...`). Ripristinare (`git checkout --`) i file originali se modificati per errore.

## Regole Documentazione

- I contenuti concettuali principali sono nella documentazione dell'area tecnica (guide).
- Prima di strutturare una soluzione, consultare le guide pertinenti (es. soggetti → guida soggetti e ruoli anagrafici).
- Gli script aggiornati per tabelle/views/funzioni si trovano in `<schema>/tabelle`, `<schema>/views`, `<schema>/funzioni`.
- Non modificare questi file auto-generati: servono solo come riferimento.
- Scrivere o aggiornare solo la documentazione concettuale in `<schema>/manual`.
- Per la documentazione backend (Django), usare sempre una struttura standard nei file manuali:
  - Scopo
  - Contesto
  - Input
  - Output
  - Regole
  - Dipendenze DB
  - Note di migrazione (se applicabile)
- Template di riferimento: `docs/it/backend/_templates/manual-standard.md`

### Build docs (Zensical) - prerequisiti obbligatori

- Stack docs corrente: `zensical==0.0.24` (con `deepmerge==2.0`) + tooling Python in `requirements.txt`.
- Non usare piu` `mkdocs build` come comando primario di progetto.
- Build docs locale/CI: `python scripts/build_docs_zensical.py`
  - lo script preprocessa `docs/` in `.tmp/zensical_docs`
  - espande i tag `{% include-markdown "..." %}`
  - riscrive i link markdown root `](/dbzero/...)` in `](/it/dbzero/...)`
  - genera config temporanea `mkdocs.zensical.yml`
  - produce output in `site-zensical/`
- Serve locale docs: `bash scripts/serve_docs.sh`.
  - Comando unico: build + server statico su `127.0.0.1:8010`.
  - La preview locale scrive solo in `/tmp/zeroerp-docs-preview` (non modifica file tracciati del repo).
- Se nei markdown si documenta la sintassi include come esempio, evitare placeholder non reali in forma attiva (es. `"..."`) oppure metterli in blocchi codice, per non generare warning del preprocess.

## SQL Conventions

- Schemas/tables/columns naming per `linee-guida-sql.md`
- Prefer UUID for master entities; SERIAL/IDENTITY for technical tables
- Use `tx_id UUID` when required by transaction-id policy
- Audit fields: `date_insert`, `user_insert`, `date_update`, `user_update`
- Index naming: `ix_<table>_<column>`; check duplicates via `dbops.vw_duplicate_indexes`
- FK index policy applied in `90_end` with `dbops.apply_fk_index_policy()`
- FK index: non crearli manualmente; se necessari, rispettare il naming di policy e registrare in `dbops.fk_index_policy` (consentito true/false) tramite `dbops.fn_seed_fk_index_policy()` o `dbops.fn_populate_fk_index_policy()`
- Per variabili PL/pgSQL che riflettono colonne, usare `%TYPE` della colonna (es. `v_uom_base_id catalogo.unita_misura.id%TYPE`)
- Nei blocchi SQL di funzioni/trigger inserire commenti sintetici sullo scopo e sulle regole principali.
- In script complessi con molti filtri/parametri, e per evitare duplicazioni di logica, e` consentito usare SQL dinamico (con attenzione alla sicurezza).
- **REGOLA OBBLIGATORIA — DDL/definizioni dalla doc auto-gen, MAI dagli YAML.** Per
  capire o **modificare** una tabella/funzione/trigger ESISTENTE, prendere la
  definizione corrente SEMPRE dalla documentazione auto-generata in
  `docs/it/dbzero/<schema>/tabelle/<nome>.md` e `docs/it/dbzero/<schema>/funzioni/<nome>.md`
  (riflette l'oggetto **vivo** nel DB). **NON** ricostruire il DDL/corpo da un file
  YAML di migration: i changeSet `runOnChange: true` (funzioni/trigger) vengono
  superati da changeSet successivi con numerazione più alta, quindi un singolo YAML
  è spesso **stale**. Per un `CREATE OR REPLACE` di una funzione esistente: copiare
  il corpo dalla doc auto-gen, applicarvi sopra la modifica, e creare un nuovo file
  con numerazione successiva. Partire dallo YAML rischia di **regredire** silenziosamente
  le revisioni intermedie.
- Nelle funzioni SQL, per parametri numerici di tipo ID applicare guard di validazione esplicita: errore se `NULL` o `<= 0` (non normalizzare silenziosamente).

## Trigger Conventions

- Trigger name: `trg_<schema_opzionale>_<tabella>_<fase>_<descrizione>_<eventi>`
- Phases: `_a10_` for guard/block, `_z90_` for final/deferrable
- Event suffixes: `_ins/_upd/_dlt` (combine if needed)
- Use `UPDATE OF colonna` when logic is column-specific
- Errors via `script.fn_log_and_raise_error(...)`

## Guard vs Check Functions

- `fn_check_*`: pure checks returning boolean, no raise
- `fn_guard_*`: fail-fast, can raise/log

## Workflow Safety

- Ask before running DB migrations locally
- Avoid destructive commands without explicit approval
- **Bug di dati in sviluppo**: prima di sviluppare fix software per correggere dati errati, chiedere all'utente se è più veloce correggere/cancellare i dati manualmente. I fix software per problemi di dati creano strati di codice inutili che poi vanno rimossi.

## Test (pgtap)

- Test DB: pgtap
- Percorso: `db/pgtap/`
- Nei file di test, all'inizio inserire un indice dei test eseguiti nei commenti.
- Nei file di test Python/Django, inserire all'inizio un breve indice dei test previsti (nome test/caso).
- Negli smoke test bash (`backend/scripts/smoke-test-*.sh`), inserire un blocco `# Indice test (0..N):` dopo l'header, elencando ogni sezione di test.
- Struttura test Django per app: `apps/<schema>/tests/` con sottocartelle minime `api/` e `services/`.
- Esempio esecuzione test Django: `./manage-test.sh apps.core.tests.api -v 2`
- Smoke test API docs/schema: vedi `apps/core/tests/api/test_diagnostics_api.py` (endpoint `/api/docs/` e `/api/schema/`).

### Regole test Django per compatibilità CI

I test Django devono funzionare in CI (GitHub Actions) **senza dipendere da un DB reale accessibile**:

- **Usare `unittest.TestCase`** (o `django.test.SimpleTestCase`) per test unitari con mock. **Non** usare `django.test.TestCase` a meno che il test non necessiti realmente del database.
- **Mockare ogni accesso DB**: se il codice sotto test usa `django.db.connection` (cursor, advisory lock, query dirette), mockare quei metodi nel test. Non fare affidamento sul DB di sviluppo.
- **Pattern consigliato** per metodi che accedono al DB (es. advisory lock, cursor raw):

  ```python
  def setUp(self):
      patcher = patch.object(MyClass, "_metodo_che_usa_db", return_value=valore)
      self._mock = patcher.start()
      self.addCleanup(patcher.stop)
  ```

- **Endpoint API con `@extend_schema`**: ogni `APIView` esposta su `/api/v1/` deve avere il decoratore `@extend_schema` su ogni metodo HTTP pubblico (`get`, `post`), per evitare warning drf-spectacular in CI e generare documentazione OpenAPI corretta.
- **Verifica locale pre-push**: eseguire `./manage-test.sh -v 2` per confermare che tutti i test passano. Per simulare l'ambiente CI (senza DB), usare:

  ```bash
  DB_HOST=localhost DB_PORT=5432 DB_NAME=zeroerp DB_USER=zeroerp DB_PASSWORD=secret \
  DJANGO_SECRET_KEY=ci-placeholder DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1" DJANGO_DEBUG=0 \
  .venv/bin/python manage.py test -v 2
  ```
