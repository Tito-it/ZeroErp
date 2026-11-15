# ZeroERP

> **Last updated**: 15 November 2026

**Open-source ERP for Italian companies, designed with a DB-first and concentric development approach.**

ZeroERP is built from hands-on experience in enterprise software for utilities and SMEs.
The goal is to reduce unnecessary complexity while preserving rigor in data, rules, and traceability.

---

## Project Status

> **Active development — DB, backend and frontend operational on core, master data, catalog, the
> full sales cycle (quotes, offers, contracts, orders, delivery notes, returns, invoices, job orders),
> workflow, documents and configurable presentation. Not yet released for production.**
>
> The detailed picture, the state per component and the roadmap live in one place: the
> [Concentric Map](../it/mappa-concentrica.md) (Italian), with its dated
> [changelog](../it/dev/mappa-concentrica-changelog.md). Below is only a snapshot.

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
Frontend Vue 3 (presentation only, no business logic)
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

| Component | Technology | The version is read from |
| --- | --- | --- |
| Database | PostgreSQL, with PostGIS, pgTAP, pgAgent, plpgsql_check | the CI workflows (`.github/workflows/`) |
| DB versioning | Liquibase Community (Java 17) | `scripts/liquibase-versioni.env` |
| Backend | Django + Django REST Framework, Redis as cache, WeasyPrint for PDFs | `backend/requirements.in` |
| Backend language | Python | `.python-version` |
| Frontend | Vue 3, Vite, PrimeVue, Pinia | `frontend/package.json` (Node in `engines.node`) |
| Docs/dev tooling | Zensical + docs preprocessing, pre-commit, Docker | `requirements.txt` at the repository root |

⛔ Version numbers are not copied here: a number written in two places always has one stale copy,
and the unguarded one is the document.

---

## Database Structure

The database is organized into main functional schemas:

- `anagrafiche`
- `catalogo`
- `acquisti`
- `vendite`
- `magazzino`
- `pagamenti`
- `contabilita` (⛔ schema name only, empty and out of scope)
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

A snapshot to get oriented; the [Concentric Map](../it/mappa-concentrica.md) is authoritative.

- **Foundations**: DB-native job queue, errors as a catalogued contract, pgTAP tests in CI that run
  **as the application** (RLS enforced on every run)
- **Access and master data**: authentication (JWT, multiple roles per credential, second factor),
  three-level permissions with operator RLS per fiscal issuer, master data, catalog with versioned
  bills of materials and unit conversions
- **Sales cycle**: quotes, offers, contracts (including recurring fees), orders, delivery notes,
  returns, invoices and credit notes — DB + backend + frontend, one model for every sales document
  (every state change through a DB verb, issued from a single point, state meanings from the
  vocabulary)
- **Billing**: batch pipeline with lanes, lots and an operational cockpit
- **Workflow engine**: operational and validated by its first real consumer
- **Document engine**: versioned templates, per-issuer assets, PDF, faithful reprint
- **Warehouse**: delivery notes unload and returns reload stock, through a stock ledger that does not
  know its consumers
- **Open areas**: payments collection, SDI e-invoicing, purchasing; accounting is out of scope (if
  ever needed, it will be a link to an external accounting system)

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

The roadmap is kept in one place, in the [Concentric Map §3](../it/mappa-concentrica.md#3-roadmap)
(Italian): work in progress (each item with its living document), planned work, open decisions and
declared debt. Completed work lives in the map's
[changelog](../it/dev/mappa-concentrica-changelog.md).

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
