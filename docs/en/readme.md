# ZeroERP

> **Last updated**: 2 November 2026

**Open-source ERP for Italian companies, designed with a DB-first and concentric development approach.**

ZeroERP is built from hands-on experience in enterprise software for utilities and SMEs.
The goal is to reduce unnecessary complexity while preserving rigor in data, rules, and traceability.

---

## Project Status

> **Active development (core phase).**
>
> The project is under construction: the database layer is the most advanced area,
> Django APIs are evolving, and there is no public frontend release yet.

---

## Table of Contents

- [Philosophy](#philosophy)
- [Concentric Development](#concentric-development)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Database Structure](#database-structure)
- [Workflow Engine](#workflow-engine)
- [Development Status](#development-status)
- [Installation](#installation)
- [Repository Structure](#repository-structure)
- [Roadmap](#roadmap)
- [Documentation](#documentation)
- [License](#license)

---

## Philosophy

ZeroERP follows a **DB-first** model:

- critical rules live in the database (constraints, functions, triggers);
- Django orchestrates processes and exposes APIs;
- the UI is an outer layer, not where domain coherence is decided.

Guiding principles:

- end-to-end operational traceability;
- coherent data language across domains;
- incremental growth without duplicating rules across layers.

---

## Concentric Development

Concentric development is a design proposal: consolidate a shared core and grow through successive rings.

Key points:

- the core is stable but evolvable when real limits emerge;
- outer layers depend on inner layers, not the opposite;
- integrations are reduced and simplified through a shared protocol.

Further reading:

- [Manifesto (EN)](./sviluppo-concentrico.md)
- [Manifesto (IT)](../it/sviluppo-concentrico.md)

---

## Architecture

```
Frontend (future)
    |
Django REST API (orchestration, permissions, endpoints)
    |
PostgreSQL (domain core: rules, workflow, audit)
```

Architectural choices:

- critical business logic in the DB;
- application orchestration in the backend;
- per-organization instance isolation (not shared multi-tenant).

---

## Technology Stack

| Component | Technology |
| --- | --- |
| Database | PostgreSQL 18 |
| DB versioning | Liquibase 5 |
| Backend | Django 6.01 + DRF |
| Backend language | Python 3.14 |
| Frontend | Vue.js (target), still being defined |
| Docs/dev tooling | MkDocs, pre-commit, Docker |

---

## Database Structure

The database is organized into main functional schemas:

- `anagrafiche`
- `catalogo`
- `acquisti`
- `vendite`
- `magazzino`
- `pagamenti`
- `contabilita`
- `config`
- `storico`
- `script`, `dbops`, `maintenance`, `internal`

Current migrations are maintained in `db/changelog/migrations_v2/`.

---

## Workflow Engine

The workflow engine is the operational core:

- models processes and states;
- handles prerequisites and step progression;
- maintains audit trail and traceability.

The model is designed to support non-linear flows and multi-department operations.

---

## Development Status

Snapshot (March 2026):

- Core database: advanced
- Backend APIs: in development
- Workflow engine: being consolidated
- Frontend: not started for public release
- Documentation: continuously updated

---

## Installation

ZeroERP does not yet have a stable production release.
For development setup, follow:

- [Installation (IT)](../it/installazione.md)
- [Liquibase Setup & Workflow (IT)](../it/liquibase-setup-workflow.md)

Note: before applying DB migrations locally, follow your team workflow rules.

---

## Repository Structure

Essential structure:

- `backend/` -> Django project and domain apps
- `db/changelog/migrations_v2/` -> current Liquibase changelogs
- `docs/` -> technical documentation (IT/EN)
- `frontend/` -> frontend area
- `scripts/` -> dev/CI support utilities

---

## Roadmap

1. Consolidate DB core and workflow engine
2. Expand domain APIs (master data, sales, workflow)
3. Deliver first internal-use frontend
4. Evolve integrations and vertical modules

---

## Documentation

Main documentation entry points:

- [Documentation Index (EN)](./index.md)
- [Documentation Index (IT)](../it/index.md)

---

## License

ZeroERP is dual-licensed: **GNU AGPL v3 or later**, or a commercial license (see `LICENSE.md`).

References:

- [LICENSE (EN)](./LICENSE.md)
- [LICENSE (IT)](../it/LICENSE.md)

---

## Author

**Michele Carlo**

Software developer with over 30 years of enterprise software experience.

> Zero unnecessary complexity. Concentric growth. Operational coherence.
