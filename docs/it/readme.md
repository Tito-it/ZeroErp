# ZeroERP

**ERP open-source per aziende italiane, progettato con approccio DB-first e sviluppo concentrico.**

ZeroERP nasce da esperienza diretta su sistemi gestionali in contesti utilities e PMI.
L'obiettivo e` ridurre la complessita` superflua mantenendo rigore su dati, regole e tracciabilita`.

---

## Stato progetto

> **Sviluppo attivo — frontend operativo su aree core.**
>
> DB e API backend operativi. Frontend Vue operativo su: layout applicativo,
> gestione soggetti (PF/PG/ENTE), gestione geografica (7 tab CRUD), pannello configurazione (67 tabelle),
> amministrazione software (operatori, profili reparto, permessi, audit log),
> sistema permessi a 2 livelli (area + azioni processo).
> Non ancora rilasciato per produzione.

---

## Indice

- [ZeroERP](#zeroerp)
  - [Stato progetto](#stato-progetto)
  - [Indice](#indice)
  - [Filosofia](#filosofia)
  - [Sviluppo Concentrico](#sviluppo-concentrico)
  - [Architettura](#architettura)
  - [Stack Tecnologico](#stack-tecnologico)
  - [Struttura del Database](#struttura-del-database)
  - [Motore Pratiche](#motore-pratiche)
  - [Stato dello Sviluppo](#stato-dello-sviluppo)
  - [Installazione](#installazione)
  - [Struttura Repository](#struttura-repository)
  - [Roadmap](#roadmap)
  - [Documentazione](#documentazione)
  - [Licenza](#licenza)
  - [Autore](#autore)

---

## Filosofia

ZeroERP adotta un modello **DB-first**:

- le regole critiche vivono nel database (vincoli, funzioni, trigger);
- Django orchestra i processi e espone API;
- la UI e` uno strato esterno, non il punto dove si decide la coerenza del dominio.

Principi guida:

- tracciabilita` operativa end-to-end;
- linguaggio dati coerente tra domini;
- crescita incrementale senza duplicare regole tra strati.

---

## Sviluppo Concentrico

Lo sviluppo concentrico e` una proposta progettuale: si consolida un nucleo comune e si cresce per anelli successivi.

Punti chiave:

- il nucleo e` stabile ma evolvibile quando emergono limiti reali;
- gli strati esterni dipendono da quelli interni, non il contrario;
- le integrazioni sono ridotte e semplificate tramite protocollo condiviso.

Approfondimento:

- [Manifesto (IT)](./sviluppo-concentrico.md)
- [Manifesto (EN)](../en/sviluppo-concentrico.md)
- [Vocabolario](./sviluppo-concentrico-vocabolario.md)

---

## Architettura

```
Frontend Vue 3 (presentazione, zero logica business)
    |
API REST Django (orchestrazione, permessi, endpoint)
    |
PostgreSQL (nucleo dominio: regole, workflow, audit)
```

Scelte architetturali:

- business logic critica nel DB;
- orchestrazione applicativa nel backend;
- isolamento per istanza organizzativa (non multi-tenant condiviso).

---

## Stack Tecnologico

| Componente         | Tecnologia                      |
| ------------------ | ------------------------------- |
| Database           | PostgreSQL 18                   |
| Versioning DB      | Liquibase 5                     |
| Backend            | Django 6.01 + DRF               |
| Linguaggio backend | Python 3.14                     |
| Frontend           | Vue 3.5, Vite 7, PrimeVue 4.5, Pinia 3 |
| Tooling docs/dev   | MkDocs, pre-commit, Docker      |

---

## Struttura del Database

Il database e` organizzato per schemi funzionali principali:

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

Le migrazioni correnti sono mantenute in `db/changelog/migrations_v2/`.

---

## Motore Pratiche

Il motore pratiche e` il nucleo di workflow operativo:

- modella processi e stati;
- gestisce prerequisiti e avanzamenti;
- mantiene audit trail e tracciabilita`.

Il modello e` pensato per supportare processi non lineari e gestione multi-reparto.

---

## Stato dello Sviluppo

Fotografia sintetica (20 marzo 2026):

- Database core: operativo (13 schemi, 200+ tabelle, trigger, funzioni, viste)
- API backend: operativo (689+ test, 57+ endpoint documentati)
- Motore pratiche: operativo (workflow, giornale, sospensioni, macchina a stati)
- Sistema permessi: operativo a 2 livelli
  - Livello 1: area funzionale (TUTTO/LETTURA/BLOCCATO) — sidebar, route guard, CSS protect
  - Livello 2: azioni processo (abilitata/negata) — prop `action` su componenti, backend 403
- Frontend Vue: operativo su aree core
  - Layout applicativo (sidebar morfica, content tabs, breadcrumb, ricerca universale, shortcut tastiera)
  - Amm. Software completa: operatori, profili reparto, permessi riepilogo, audit log (solo ADMIN)
  - Gestione soggetti: PF/PG/ENTE end-to-end, ruoli, contatti, indirizzi, CF validator IT
  - Gestione geografica: 7 tab CRUD (indirizzi, toponomastica, comuni, CAP, province, regioni, stati)
  - Pannello configurazione: 67 tabelle CRUD generiche con drawer dinamico metadata-driven
  - Building block riutilizzabili: 20+ composable, 15+ componenti core, CSS utility classes
- Documentazione: 57+ endpoint documentati, frontend-standards, mappa concentrica aggiornata

 [Mappa](./mappa-concentrica.md)

---

## Installazione

ZeroERP non ha ancora un rilascio stabile per produzione.
Per setup ambiente di sviluppo, seguire:

- [Installazione](./installazione.md)
- [Liquibase Setup & Workflow](./liquibase-setup-workflow.md)

Nota: prima di applicare migrazioni DB in locale, verificare il workflow del team.

---

## Struttura Repository

Struttura essenziale:

- `backend/` -> progetto Django e app dominio
- `db/changelog/migrations_v2/` -> changelog Liquibase correnti
- `docs/` -> documentazione tecnica (IT/EN)
- `frontend/` -> area frontend
- `scripts/` -> utility di supporto sviluppo/CI

---

## Roadmap

1. ~~Consolidamento nucleo DB e motore pratiche~~ — fatto
2. ~~Espansione API dominio (anagrafiche, vendite, pratiche)~~ — fatto
3. ~~Frontend layout applicativo + building block~~ — fatto
4. ~~Gestione Soggetti (PF/PG/ENTE end-to-end)~~ — fatto, in test UI
5. ~~Gestione Geografica (7 tab CRUD)~~ — fatto
6. ~~Amm. Software (operatori, profili, permessi, audit)~~ — fatto, in test UI
7. ~~Sistema permessi 2 livelli (area + azioni processo)~~ — fatto
8. Test UI reali su aree completate — in corso
9. Seed azioni processo per nuovi domini + integrazione componenti
10. ClienteService Django (orchestrator creazione/subentro/disdetta)
11. Evoluzione integrazioni e moduli verticali

---

## Documentazione

Documentazione tecnica principale:

- [Indice documentazione IT](./index.md)
- [Architettura](./architettura.md)
- [API](./API.md)
- [Versioni supportate](./versioni-supportate.md)

---

## Licenza

ZeroERP e` distribuito con licenza **GNU GPL v3 o successiva**.

Riferimenti:

- [LICENSE (IT)](./LICENSE.md)
- [LICENSE (EN)](../en/LICENSE.md)

---

## Autore

**Michele Carlo**

Sviluppatore con oltre 30 anni di esperienza nel software gestionale.

> Zero complessita` superflua. Crescita concentrica. Coerenza operativa.
