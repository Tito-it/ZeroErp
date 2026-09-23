# CLAUDE.md

## ⛔ Regola zero — da leggere prima di tutto

> **Le misure servono a trovare gli errori, non a disegnare il progetto.**
> Un dato del DB può solo **smentire** una regola: non decide mai la forma, il
> perimetro o la priorità di ciò che si costruisce.
> **Si sviluppa sul modello, non sulle righe di oggi.**

Se in un brief sto per scrivere *«misurato X, quindi facciamo così»*, la misura
sta guidando il progetto: la misura entra come **fatto datato**, mai come
**motivo**. Casi, corollari e argomenti da rifiutare — «non è un caso di
nicchia», «oggi non capita mai», «il test è verde» — nella sezione di apertura di
[.codex/AGENTS.md](.codex/AGENTS.md).

## Istruzioni obbligatorie per ogni sessione

All'inizio di ogni conversazione leggi il **contesto comune**, poi **solo** i
documenti del perimetro della sessione. Non chiedere conferma.

### Contesto comune (sempre)

1. [.codex/AGENTS.md](.codex/AGENTS.md) — regole trasversali, e la mappa «dove sta cosa»
2. [.codex/PROJECT_CONTEXT.md](.codex/PROJECT_CONTEXT.md) — architettura, stato progetto, priorità aperte

### Poi, secondo il perimetro

| Sessione | Si riconosce da | Si legge |
| --- | --- | --- |
| **DB** | branch `dev/db-tid`, o un task su changeSet, funzioni, trigger, pgTAP, brief `brief-db-*` | [linee-guida-sql.md](docs/it/linee-guida-sql.md) e, se si toccano trigger, [linee-guida-trigger.md](docs/it/linee-guida-trigger.md) |
| **Backend / Frontend** | branch `dev/backend-tid`, o un task su endpoint, service, view, componenti | [api.md](docs/it/dev/api.md), [frontend-standards.md](docs/it/dev/frontend/frontend-standards.md), [catalogo BB backend](docs/it/dev/backend/catalogo-building-block-backend.md), [catalogo BB frontend](docs/it/dev/frontend/catalogo-building-block-frontend.md) — **tutti e quattro**: un task BE fa emergere spesso una lista o un drawer, e viceversa |

⛔ **In una sessione DB NON si leggono api.md, frontend-standards né i cataloghi BB.**
Il perimetro DB non tocca `backend/` né `frontend/`: quella lettura costa
contesto e non serve. Se un lavoro DB ha una ricaduta sul BE o sul FE, la si
**scrive nel brief** come richiesta al team, e si apre **solo** la sezione
precisa che serve (per esempio §Tassonomia errori di api.md per un codice
nuovo), non il documento intero.

Il catalogo BB resta la prima difesa contro le duplicazioni **nel suo lato**
(regola del 2, in [.codex/AGENTS.md](.codex/AGENTS.md)): lato DB i building block
si cercano negli schemi `script`/`dbops` e nella doc auto-generata.
