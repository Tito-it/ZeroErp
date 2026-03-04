# 🪵 ZeroERP

**The open-source ERP for Italian companies, built with concentric development.**

ZeroERP is born from thirty years of experience in the Italian enterprise software world — utilities, multi-service companies, SMEs — with one clear goal: eliminate unnecessary complexity while keeping everything that truly matters. The name "Zero" is not a number: it is a philosophy. Zero unnecessary complexity, zero superstructures, zero compromises on substance.

---

> **Project status: active development — core phase**
>
> ZeroERP is under active construction. The database (the central ring) is in an advanced stage
> with multi-functional schemas, electronic invoicing and the workflow engine designed.
> Django REST APIs are under development. There is no frontend interface yet
> nor a usable release. If you arrive now, you will find an open construction site:
> the foundations are solid, the walls are going up.

---

## Table of Contents

- [🪵 ZeroERP](#-zeroerp)
  - [Table of Contents](#table-of-contents)
  - [Philosophy](#philosophy)
  - [Concentric Development](#concentric-development)
  - [Architecture](#architecture)
  - [Tech Stack](#tech-stack)
  - [Database Structure](#database-structure)
  - [The Workflow Engine](#the-workflow-engine)
    - [How it works](#how-it-works)
    - [Structure (13 core tables)](#structure-13-core-tables)
    - [Key features](#key-features)
    - [Example: Technical ticket with quotation](#example-technical-ticket-with-quotation)
  - [Development Status](#development-status)
  - [Installation](#installation)
    - [Prerequisites](#prerequisites)
    - [Quick setup](#quick-setup)
  - [Repository Structure](#repository-structure)
  - [Roadmap](#roadmap)
    - [Phase 1 — Core (in progress)](#phase-1--core-in-progress)
    - [Phase 2 — Operations](#phase-2--operations)
    - [Phase 3 — Specialization](#phase-3--specialization)
    - [Phase 4 — Growth](#phase-4--growth)
  - [Documentation](#documentation)
  - [License](#license)
  - [Author](#author)

---

## Philosophy

Traditional ERPs grow by accumulation: modules added over time, forced integrations, layers of complexity that no one dares touch anymore. ZeroERP reverses this approach.

Every feature grows from a stable central core and expands organically, like the rings of a tree trunk. The heartwood is the densest and the strongest. Every new ring rests on the inner ones, reinforcing them. The result is a system that grows without losing coherence.

**Core principles:**

- Business logic lives in the database, not scattered across application code
- Every operation is traceable: the system is a permanent logbook
- Configuration over customization: it adapts without rewriting
- Native multi-company for corporate groups: one group, multiple fiscal entities, one system. Not multi-tenant by design: each organization gets its own instance, its own data, its own security perimeter
- Built for Italy: SDI electronic invoicing, ARERA regulations, Italian tax compliance

---

## Concentric Development

> *Concentric Development — a methodology born from practice, not theory.*

Concentric development is the model with which ZeroERP is designed and built. It is not agile, it is not waterfall, it is not traditional modular development.

**How it works:**

The core is designed with absolute rigor. Every new feature is added as an outer ring that rests on the inner ones. There are no integrations between modules because everything already speaks through the center. Growth is incremental but the structure is coherent from day one.

When an outer ring reveals that the core is not strong enough, you go back to the center and fix it there — not with an adapter, not with a connector, not with a shortcut. You rewrite the inner ring and propagate the change through every layer above. It is painful, it is slow, but it is honest. In a real tree trunk cross-section, the darker rings are the ones that worked the hardest, compressed by the weight of growth. They are not mistakes: they are the strongest wood.

**Why it is different:**

- **Agile** works in sprints but does not guarantee structural coherence
- **Waterfall** plans everything upfront but cannot handle change
- **Modular development** builds separate pieces and then integrates them with connectors
- **Concentric development** starts from the heart and grows while maintaining integrity at every step. When the center changes, everything changes together, all the way through

**The metaphor:**

Like a tree trunk. The heartwood is the oldest and the hardest. Every ring is a year of growth. If you cut the trunk you can read the entire history — exactly like the system's logbook. The dark rings are not scars: they are proof of the craftsman's work, going back to the center to make it better.

```
        ╭─────────────────────────╮
       │    portal / external API  │
      │  ╭─────────────────────╮  │
      │ │   SDI invoicing       │  │
      │ │  ╭─────────────────╮ │  │
      │ │ │   master data     │ │  │
      │ │ │  ╭─────────────╮ │ │  │
      │ │ │ │  WORKFLOW     │ │ │  │
      │ │ │ │  (core)       │ │ │  │
      │ │ │  ╰─────────────╯ │ │  │
      │ │  ╰─────────────────╯ │  │
      │  ╰─────────────────────╯  │
       ╰─────────────────────────╯
```

*The concept of Concentric Development was born on March 2, 2026, during the design of ZeroERP.*
*Read the [full Manifesto](docs/concentric_development_manifesto.md) — available in [English](docs/concentric_development_manifesto.md) and [Italian](docs/manifesto_sviluppo_concentrico.md).*

---

## Architecture

ZeroERP follows a three-tier architecture with business logic centralized in the database:

```
┌──────────────────────────────────┐
│          Frontend (SPA)          │
│     Vue.js / React (TBD)        │
├──────────────────────────────────┤
│        Backend (REST API)        │
│      Django REST Framework       │
│   Authentication / Permissions / │
│   Flow handlers / Orchestrator   │
├──────────────────────────────────┤
│         Database (core)          │
│          PostgreSQL              │
│  Functions / Triggers / Rules /  │
│  Validations / Flow control      │
└──────────────────────────────────┘
```

**Key architectural decisions:**

- **Business logic in the DB**: validations, sequence controls, and the logbook are managed by PostgreSQL functions and triggers. No bypass possible, neither from the UI nor from external APIs
- **Orchestrator pattern**: complex operations (e.g. billing push, flow advancement) are coordinated by an orchestrator that invokes DB functions in the correct sequence
- **Handler per flow type**: each flow type has a Django handler that implements its specific logic. The DB core remains agnostic to the implementation
- **Multi-company for corporate groups**: the `azienda_id` field distinguishes fiscal entities within the same group (e.g. a multi-utility with gas, water, and services companies). Not multi-tenant: each organization has its own instance, by deliberate choice for security and data isolation

---

## Tech Stack

| Component        | Technology              | Notes                                   |
| ---------------- | ----------------------- | --------------------------------------- |
| Database         | PostgreSQL 16+          | System core, centralized business logic |
| DB versioning    | Liquibase               | XML changelogs for all migrations       |
| Backend          | Django 5+ / DRF         | REST API, authentication, flow handlers |
| Frontend         | TBD (Vue.js / React)    | SPA with operator interface/dashboard   |
| Languages        | Python 3.12+ / SQL      |                                         |
| Containerization | Docker / Docker Compose | Development and deployment environment  |

---

## Database Structure

The database is organized into PostgreSQL functional schemas, each with clear responsibilities:

| Schema        | Responsibility                                     |
| ------------- | -------------------------------------------------- |
| `pratiche`    | **Central core** — workflow engine, flows, logbook |
| `anagrafiche` | Subjects, roles, addresses, contacts               |
| `vendite`     | Sales cycle, orders, contracts                     |
| `acquisti`    | Procurement cycle, supplier orders                 |
| `catalogo`    | Products, services, price lists                    |
| `config`      | System configuration, parameters                   |
| `contabilita` | Chart of accounts, journal entries, sub-ledger     |
| `magazzino`   | Inventory, movements, batches                      |
| `pagamenti`   | Collections, payments, due dates                   |
| `storico`     | Historical data archiving                          |
| `core`        | Cross-cutting functions, utilities, permissions    |

---

## The Workflow Engine

The heart of ZeroERP. **Everything is a case.** Every operation flows through the workflow engine, which works as a lightweight but rigorous workflow manager.

### How it works

Those who configure service types and flows get a workflow with sequence control, prerequisites, assignments to different departments, and monitored timelines. Those who do not configure still get a complete logbook with full traceability.

### Structure (13 core tables)

**Catalog (configuration):**
- `tipo_prestazione` — case categories (e.g. Activation, Order, Complaint)
- `template_flusso` — expected sequence of steps for each type
- `template_flusso_prerequisito` — dependencies between flows (parallel branches and convergences)
- `template_flusso_azione` — automatic rules: "flow X with outcome Y generates flow Z"

**Execution (operational instances):**
- `pratica` — case header with status, priority, subject, dates
- `flusso` — single step with status, outcome, assigned operator, department

**Document management:**
- `nota_pratica` / `nota_flusso` — typed notes (general, internal, customer, technical, legal)
- `allegato_pratica` / `allegato_flusso` — documents and images with versioning and SHA-256 hash

**Traceability:**
- `giornale` — immutable audit trail automatically fed via triggers
- `sospensione` — suspension periods with automatic impact calculation on the timeline
- `formula_tempo` — KPI and SLA definitions between flows, net of suspensions

### Key features

- **Non-linear flows**: support for parallel branches, convergences, and optional flows through explicit prerequisites
- **Flows that generate flows**: a completed flow can automatically generate sub-flows assigned to other departments
- **Sequence control**: minimum prerequisites (you cannot do it too early) and maximum limits (you cannot do it too late)
- **Configurable handlers**: each flow type can have a specific Django handler
- **Open to the outside**: an external system or customer portal interacts with two operations: "open case" and "advance flow"
- **Batch processes kept separate**: massive operations (billing, meter readings) have dedicated registers. Only anomalies generate cases for human intervention

### Example: Technical ticket with quotation

```
Ticket received (Technical dept.)
    |
    v
Technical assessment (Technical dept.)
    |-- outcome: quotation needed
    |
    v (automatic action)
Quotation preparation (Commercial dept.)
    |
    v
Send to customer (Commercial dept.)
    |
    v
Awaiting acceptance
    |-- outcome: accepted
    |
    v (automatic action)
Schedule intervention (Technical dept.)
    |
    v
Execution and closure
```

Everything tracked in the logbook. Every handoff between departments recorded. The customer sees the status from the portal.

---

## Development Status

ZeroERP is a project under active construction. This is the current snapshot:

| Component              | Status           | Notes                                               |
| ---------------------- | ---------------- | --------------------------------------------------- |
| Database architecture  | 🟢 Advanced       | Multi-functional schema, stable structure           |
| SDI invoicing          | 🟢 Advanced       | Complete data model                                 |
| Workflow engine        | 🟡 In design      | 13 core tables defined, implementation pending      |
| Permission system      | 🟢 Advanced       | Three-level model per functional area               |
| REST API (invoicing)   | 🟡 In development | Django REST Framework, endpoints under construction |
| REST API (master data) | 🔴 Not started    | Depends on workflow model completion                |
| REST API (workflow)    | 🔴 Not started    | Awaiting DB schema implementation                   |
| Frontend               | 🔴 Not started    | Vue.js / React choice still open                    |
| Operator dashboard     | 🔴 Not started    | Requires frontend and workflow APIs                 |
| Customer portal        | 🔴 Not started    | Phase 3 of the roadmap                              |
| Documentation          | 🟡 In progress    | Technical guides under construction                 |

**Legend**: 🟢 Advanced / stable — 🟡 In progress / under development — 🔴 Not started

---

## Installation

> ⚠️ ZeroERP does not have a usable release yet. The following instructions are for those who want to explore the source code and contribute to development.

### Prerequisites

- PostgreSQL 16+
- Python 3.12+
- Liquibase 4.x
- Docker and Docker Compose (optional but recommended)

### Quick setup

```bash
# Clone the repository
git clone https://github.com/[username]/zeroerp.git
cd zeroerp

# Start services with Docker Compose
docker-compose up -d

# Apply database migrations
liquibase update

# Start the Django backend
cd backend
pip install -r requirements.txt
python manage.py runserver
```

*Detailed instructions in the full documentation.*

---

## Repository Structure

```
zeroerp/
├── README.md
├── LICENSE
├── docker-compose.yml
├── db/
│   ├── changelog/              # Liquibase changelog files
│   │   ├── pratiche/           # Workflow schema
│   │   ├── anagrafiche/        # Master data schema
│   │   ├── vendite/            # Sales schema
│   │   ├── ...                 # Other schemas
│   │   └── master-changelog.xml
│   └── functions/              # PostgreSQL functions
├── backend/
│   ├── manage.py
│   ├── zeroerp/                # Django project
│   ├── pratiche/               # Workflow app
│   ├── anagrafiche/            # Master data app
│   └── ...                     # Other apps
├── frontend/                   # SPA (TBD)
└── docs/                       # Technical documentation
```

---

## Roadmap

### Phase 1 — Core (in progress)
- Complete database schema for all modules
- Operational workflow engine with all 13 tables
- REST APIs for workflow and master data

### Phase 2 — Operations
- Operator dashboard with activity management by department
- Sales cycle: orders, invoicing, collections
- Procurement cycle: suppliers, purchasing, payments

### Phase 3 — Specialization
- Utility-specific modules (meter readings, consumption, tariffs)
- Customer/supplier portal
- External integrations (distributor flows, ARERA)

### Phase 4 — Growth
- Business intelligence and reporting
- Mobile app for field operators
- Extension marketplace

---

## Documentation

- **ZeroERP Docs**: [github.com/[username]/zeroerp-docs](https://github.com/[username]/zeroerp-docs) — functional and technical documentation
- **ZeroERP Logo**: [github.com/[username]/zeroerp-logo](https://github.com/[username]/zeroerp-logo) — graphic assets and brand guidelines

---

## License

This project is distributed under [TO BE DEFINED] license.

See the [LICENSE](LICENSE) file for full details.

---

## Author

**Michele Carlo**

Developer with over 30 years of experience in enterprise software, specialized in ERP systems for Italian utilities and SMEs. ZeroERP is born from the conviction that complexity is not a feature, it is a design failure.

> *"Zero unnecessary complexity. Concentric growth. Everything recorded in the rings."*

---

<p align="center">
  <strong>ZeroERP</strong> — Concentric Development / Sviluppo Concentrico<br>
  <em>Every ring tells the story</em><br><br>
  🪵
</p>