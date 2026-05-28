# CLAUDE.md

## Istruzioni obbligatorie per ogni sessione

**SEMPRE**, all'inizio di ogni conversazione o task, leggi questi file prima di qualsiasi altra azione:

### Contesto progetto (sempre)

1. [.codex/AGENTS.md](.codex/AGENTS.md) — regole operative, convenzioni codice, workflow, dipendenze
2. [.codex/PROJECT_CONTEXT.md](.codex/PROJECT_CONTEXT.md) — architettura, stato progetto, priorità aperte

### Backend (sempre, anche se il task sembra solo FE — un endpoint può emergere)

1. [docs/it/dev/api.md](docs/it/dev/api.md) — linee guida API, base view, envelope, routing, codici errore
2. [docs/it/dev/backend/catalogo-building-block-backend.md](docs/it/dev/backend/catalogo-building-block-backend.md) — inventario completo helper/service/repository riusabili lato BE

### Frontend (sempre, anche se il task sembra solo BE — un drawer/lista può emergere)

1. [docs/it/dev/frontend/frontend-standards.md](docs/it/dev/frontend/frontend-standards.md) — standard componenti, composable, CSS, i18n, pattern operativi
2. [docs/it/dev/frontend/catalogo-building-block-frontend.md](docs/it/dev/frontend/catalogo-building-block-frontend.md) — inventario completo BB FE (componenti, composable, store)

Non chiedere conferma: leggili automaticamente. Sono il contesto minimo per operare su questo progetto. Il fatto che un task "sembri" solo BE o solo FE non esonera dall'altra metà: capita spesso di toccare entrambi i lati in cascata, e il catalogo BB è la prima difesa contro duplicazioni (memoria `feedback_regola_del_2_estrai_bb`).
