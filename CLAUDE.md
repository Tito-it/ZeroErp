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
| **Backend / Frontend** | branch `dev/backend-tid`, o un task su endpoint, service, view, componenti | **Per intero, prima di scrivere logica nuova** (non all'avvio: una sessione che solo legge, allinea il branch o corregge un punto non li apre), gli indici dei building block del lato che si sta per toccare: [indice BB backend](docs/it/dev/backend/indice-building-block-backend.md), [indice BB frontend](docs/it/dev/frontend/indice-building-block-frontend.md) — **tutti e due** quando un task BE fa emergere una lista o un drawer, e viceversa. **Per sezione** [api.md](docs/it/dev/api.md) e [frontend-standards.md](docs/it/dev/frontend/frontend-standards.md): si legge l'elenco dei titoli (`grep -n '^##'`) e si aprono le sezioni che il task tocca |

⚠️ **I quattro documenti BE/FE non si leggono interi, e non va finto di averlo
fatto**: insieme non entrano in una sessione. Dei cataloghi BB
([backend](docs/it/dev/backend/catalogo-building-block-backend.md),
[frontend](docs/it/dev/frontend/catalogo-building-block-frontend.md)) si legge
l'**indice**, che porta una riga per building block col numero di riga `L<n>`
del catalogo: quando una voce dell'indice somiglia a ciò che si sta per
scrivere, si apre **quella riga** del catalogo (`sed -n '<n>p'`), dove stanno
firma, regole d'uso e storia. Cercare nel catalogo per parola trova solo ciò di
cui si indovina il nome: l'indice si legge prima, la ricerca viene dopo.

L'indice è **generato** dal catalogo (`python3 scripts/gen_indice_bb.py`) e non
si modifica a mano: chi aggiunge o ritira un building block corregge il catalogo
e rigenera nello stesso giro. Il pre-commit rifiuta un indice non allineato.

⛔ **In una sessione DB NON si leggono api.md, frontend-standards né i cataloghi BB.**
Il perimetro DB non tocca `backend/` né `frontend/`: quella lettura costa
contesto e non serve. Se un lavoro DB ha una ricaduta sul BE o sul FE, la si
**scrive nel brief** come richiesta al team, e si apre **solo** la sezione
precisa che serve (per esempio §Tassonomia errori di api.md per un codice
nuovo), non il documento intero.

Il catalogo BB resta la prima difesa contro le duplicazioni **nel suo lato**
(regola del 2, in [.codex/AGENTS.md](.codex/AGENTS.md)): lato DB i building block
si cercano negli schemi `script`/`dbops` e nella doc auto-generata.
