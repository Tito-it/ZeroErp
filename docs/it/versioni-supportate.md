# 📄 Versioni supportate e Licenze dei componenti utilizzati

> **Ultimo aggiornamento**: 15 novembre 2026

Zero ERP utilizza esclusivamente componenti **open‑source** o **gratuiti**, coperti da licenze permissive o copyleft compatibili con la distribuzione del progetto. L’obiettivo è garantire:

* massima trasparenza tecnologica,
* assenza di vincoli commerciali,
* piena verificabilità del codice,
* facilità di manutenzione da parte della comunità.

Tutti i componenti adottati provengono da ecosistemi maturi, ampiamente supportati e con una storia consolidata di stabilità e sicurezza.

---

## 📦 Stack software principale

⛔ **I numeri di versione non si scrivono qui**: ogni componente ha una **fonte** nel repository, ed è
quella che vale (la leggono anche la CI e il `Dockerfile`). Un numero ricopiato in un documento è il
primo a diventare falso.

| Componente | Licenza principale | La versione si legge da |
| --- | --- | --- |
| **Python** | PSF License | `.python-version` |
| **Django** e **Django REST Framework** | BSD 3‑Clause | `backend/requirements.in` (il lock in `backend/requirements.txt`) |
| **WeasyPrint** (PDF) | BSD 3‑Clause | `backend/requirements.in`; le librerie di sistema che vuole sono nel `Dockerfile` |
| **Redis** (cache del backend) | server: AGPL v3 (dalla 8); client Python `redis`: MIT | il client in `backend/requirements.in`; il server è quello della distribuzione |
| **PostgreSQL** | PostgreSQL License | l'immagine `postgis/postgis` dei workflow in `.github/workflows/` |
| **PostGIS** | GPL v2+ | idem |
| **pgAgent**, **pgTAP** | PostgreSQL License | pacchetti della distribuzione, per la versione di PostgreSQL |
| **plpgsql_check** | MIT | idem |
| **Liquibase** (Community) | Apache License 2.0 | `scripts/liquibase-versioni.env` |
| **Driver JDBC PostgreSQL** | BSD 2‑Clause | `scripts/liquibase-versioni.env` |
| **Java** (OpenJDK, per Liquibase) | GPL v2 con Classpath Exception | i workflow di CI (`actions/setup-java`) |
| **Node.js** | MIT | `engines.node` in `frontend/package.json` (via nvm) |
| **Vue 3**, **Vite**, **Pinia**, **Vue Router** | MIT | `frontend/package.json` |
| **PrimeVue** | MIT fino alla 4.x | `frontend/package.json` — ⚠️ dalla 5 la licenza è PrimeUI: si resta sulla 4.x |
| **Zensical** (documentazione) | MIT | `requirements.txt` in radice |
| **Docker CE** | Apache 2.0 / MIT | non vincolata: serve solo a costruire l'immagine |

Le estensioni di PostgreSQL che il database usa, e i pacchetti da installare sul server, sono in
[estensioni utilizzate](postgresql/estensioni-utilizzate.md). Come si installa ciascun pezzo:
[Installazione](installazione.md).

Tutti i componenti sono impiegati in conformità con le rispettive licenze.

---

## 🔍 Dettaglio: Liquibase OSS

A partire dalla versione **5.x**, Liquibase introduce un modello di distribuzione basato su tre edizioni: **OSS**, **Pro** ed **Enterprise**.

Zero ERP utilizza esclusivamente la **Liquibase OSS Edition**, distribuita sotto licenza **Apache License 2.0**, completamente open‑source e liberamente utilizzabile anche in contesti commerciali.

Caratteristiche dell’edizione OSS:

* tutte le funzionalità core per la gestione delle migrazioni database,
* compatibilità completa con PostgreSQL,
* parsing più robusto e modello tecnico aggiornato.

Non sono inclusi componenti proprietari delle edizioni Pro/Enterprise (es. reportistica avanzata, controlli aggiuntivi, changeType commerciali).

⚠️ Il **driver JDBC** non si installa con il package manager di Liquibase (LPM): la CI lo scarica da
Maven Central perché LPM falliva la verifica dei checksum. Liquibase e driver li installa
`scripts/installa-liquibase.sh`, nelle versioni fissate in `scripts/liquibase-versioni.env` e con la
verifica dello SHA-256: le stesse che usa la CI.

---
{% include-markdown "signature-core.md" %}
