# ZeroERP

**ERP open-source per aziende italiane, progettato con approccio DB-first e sviluppo concentrico.**

ZeroERP nasce da esperienza diretta su sistemi gestionali in contesti utilities e PMI.
L'obiettivo e` ridurre la complessita` superflua mantenendo rigore su dati, regole e tracciabilita`.

---

## Stato progetto

> **Sviluppo attivo — DB, backend e frontend operativi sui domini core, anagrafiche, catalogo, vendite (preventivi, offerte, contratti, ordini, DDT), pratiche e documenti. Non ancora rilasciato per produzione.**
>
> La fotografia dettagliata, lo stato per componente e la roadmap sono mantenuti in
> un'unica fonte: la [Mappa Concentrica](./mappa-concentrica.md) (stato per anello +
> sezione Roadmap), con la storia datata nel suo
> [changelog](./dev/mappa-concentrica-changelog.md). Qui sotto solo uno snapshot.

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
| Tooling docs/dev   | Zensical + preprocess docs, pre-commit, Docker |

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
- `documenti`
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

Snapshot (giugno 2026). Per il dettaglio per componente, lo stato per anello e la
roadmap aggiornata fa fede la [Mappa Concentrica](./mappa-concentrica.md); la storia
datata è nel suo [changelog](./dev/mappa-concentrica-changelog.md).

- **Database core**: operativo (14 schemi, 200+ tabelle, trigger/funzioni/viste, `daterange` nativo + PG18)
- **API backend**: operativo sui domini core, anagrafiche, catalogo, vendite e pratiche
- **Motore pratiche**: operativo e **validato dal primo consumatore reale** (pratica PREVENTIVI)
- **Vendite**: preventivi, offerte commerciali, contratti (modello unificato), ordini e DDT (documento di trasporto: evasione ordine→DDT, stampa PDF, indirizzi documento UX v2) sviluppati DB+BE+FE
- **Permessi**: operativi a 2 livelli (area funzionale + azioni di processo)
- **Autenticazione**: completa (JWT, email, token monouso, reset/invito/cambio pw); RLS operatori attiva
- **Frontend Vue**: operativo sui domini core, anagrafiche, catalogo, vendite, pratiche, documenti
- **Integrazione AI v1**: operativa (11 tool, widget conversazionale, glossario IT)
- **In test UI / consolidamento**: motore documentale, contratti/offerte BE+FE, suite UI documenti

> Lavori in corso e previsti: vedi la [Roadmap nella Mappa Concentrica](./mappa-concentrica.md#roadmap).

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

La roadmap (lavori in corso, breve/medio/lungo termine) è mantenuta in un'unica fonte
nella [Mappa Concentrica → Roadmap](./mappa-concentrica.md#roadmap). Lì le voci sono
solo quelle aperte; la storia di ciò che è stato completato vive nel
[changelog della mappa](./dev/mappa-concentrica-changelog.md).

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

---

{% include-markdown "signature-core.md" %}
