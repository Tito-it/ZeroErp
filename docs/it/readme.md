# ZeroERP

**ERP open-source per aziende italiane, progettato con approccio DB-first e sviluppo concentrico.**

ZeroERP nasce da esperienza diretta su sistemi gestionali in contesti utilities e PMI.
L'obiettivo e` ridurre la complessita` superflua mantenendo rigore su dati, regole e tracciabilita`.

---

## Stato progetto

> **Sviluppo attivo — backend e frontend operativi su domini core, catalogo, vendite, anagrafiche, pratiche.**
>
> DB e API backend operativi su 13 schemi. Frontend Vue operativo su: layout applicativo,
> gestione soggetti (PF/PG/ENTE), gestione geografica (7 tab CRUD), pannello configurazione (67 tabelle),
> amministrazione software (operatori, profili reparto, permessi, audit log),
> gestione clienti/fornitori (drawer end-to-end con sotto-drawer),
> gestione pratiche v2 (dashboard, flussi, note, allegati, giornale),
> catalogo articoli (CRUD, UoM, BoM, note) **completato**,
> listini vendita v3 **completato** (pricing completo, rettifica controllata, alert scadenze,
> variazione % massa, riallineamento/variazione prezzo commessa),
> migrazione `daterange` nativo PostgreSQL **completata** (18 tabelle, trigger generico, ottimizzazione backend),
> impostazioni parametri di sistema con override personali ed emittente,
> integrazione AI (11 tool: pratiche, soggetti, clienti, articoli, operatori),
> autenticazione completa (email, token, reset pw, invito operatore).
> 1231 test backend. Non ancora rilasciato per produzione.

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

Fotografia sintetica (12 aprile 2026):

- Database core: operativo (13 schemi, 200+ tabelle, trigger, funzioni, viste, **daterange nativo**)
- API backend: operativo (1231 test, 90+ endpoint)
- Motore pratiche: operativo (workflow, giornale, sospensioni, macchina a stati, note, allegati)
- Sistema permessi: operativo a 2 livelli
  - Livello 1: area funzionale (TUTTO/LETTURA/BLOCCATO) — sidebar, route guard, CSS protect
  - Livello 2: azioni processo (abilitata/negata) — prop `action` su componenti, backend 403
- Autenticazione: completa (JWT, email BB, token monouso, reset pw, invito, cambio pw obbligatorio)
- Parametri di sistema: lista impostazioni con override multi-scope
  - Default → Emittente → Gruppo → Utente con risoluzione deterministica
  - Drawer admin con selettore scope (Personale/Emittente), check `IsAdminZeroERP`
  - Fallback emittente "gestore di default" via `is_default = true`
- Catalogo: **completato e testato**
  - Articoli CRUD con UoM operative, distinta base, note (19 endpoint, 49 test)
  - Unita' di misura CRUD (backend + frontend)
  - Documentazione consolidata in [work-done/gestione-articoli.md](./dev/work-done/gestione-articoli.md)
- Listini vendita v3: **completato** (Sprint B-v3 chiuso)
  - Versioni, righe prezzo, associazioni, test resolver, clone, auto-close (25 endpoint, 42 test listini)
  - Variazione % massa su BOZZA con dry_run, alert scadenze con widget, rettifica controllata con lock FOR UPDATE
  - Pricing commesse: riallineamento prezzo, variazione eccezionale, sblocco (3 endpoint, 9 test commesse)
  - Trigger DB defense-in-depth `trgfn_listini_righe_guard_stato`
  - Documentazione: [sviluppo-listini-v3.md](./dev/work-in-progress/sviluppo-listini-v3.md), API: [api_listini.md](./backend/vendite/manual/api_listini.md), [api_commesse_pricing.md](./backend/vendite/manual/api_commesse_pricing.md)
- Migrazione `daterange` nativo PostgreSQL: **completata**
  - 18 tabelle migrate (Fase 0-3), infrastruttura `script.trgfn_set_validita()`, linee guida SQL §7b
  - Backend ottimizzato: `validita @>` al posto dei doppi confronti `valido_dal`/`valido_al`
  - Analisi: [migrazione-daterange.md](./dev/work-in-progress/migrazione-daterange.md)
- Rettifiche prezzi (DB-L4): estratte in [work-in-progress/sviluppo-rettifiche.md](./dev/work-in-progress/sviluppo-rettifiche.md), **da implementare**
- Integrazione AI v1: operativa, **11 tool** registrati
  - Pratiche (cerca, dettaglio, flussi)
  - Anagrafica soggetti (cerca soggetti, dettaglio soggetto)
  - Anagrafica clienti / billing account (cerca\_billing\_account — sinonimo "cliente" in italiano)
  - Catalogo articoli (cerca\_articoli)
  - Operatori (cerca\_operatori)
  - System prompt con glossario di dominio italiano (cliente=BA, articolo=catalogo)
  - Widget flottante, contesto documentale statico, multi-tool chaining, 61 test
- Frontend Vue: operativo su domini core, anagrafiche, catalogo, vendite, pratiche
  - Layout applicativo (sidebar morfica, content tabs, split view, breadcrumb, ricerca universale)
  - Amm. Software completa: operatori, profili reparto, permessi riepilogo, audit log, email
    - Drawer dedicato gestione permessi richiamabile dalla riga lista (`OperatorePermessiTab` riusabile)
  - Gestione soggetti: PF/PG/ENTE end-to-end, ruoli, contatti, indirizzi, CF validator IT
  - Gestione geografica: 7 tab CRUD
  - Gestione clienti/fornitori: drawer con sotto-drawer contatti/indirizzi/conti
  - Gestione pratiche v2: dashboard, flussi, note, allegati, giornale
  - Catalogo articoli: lista, drawer con 3 tab (UoM, BoM, note), `ArticoloLookup` BB cross-dominio
  - Listini v3: lista, drawer con versioni/associazioni, sub-drawer righe, test resolver, dialog variazione %, widget alert scadenze, dialog programma chiusura
  - Impostazioni parametri: lista multi-scope con drawer override (`PARAMETER_SCOPE` come unica fonte di verita')
  - Pannello configurazione: 67 tabelle CRUD generiche
  - Logo brand: nuovo PNG ottimizzato 256x256 (frontend) + favicon PNG/ICO + master 512x512 in `docs/assets/images/`
  - Building block riutilizzabili: 25+ composable, 20+ componenti core, LookupSelect generico, CSS utility classes
- Documentazione: frontend-standards, catalogo-building-block (frontend + backend), mappa concentrica

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
6. ~~Amm. Software (operatori, profili, permessi, audit)~~ — fatto
7. ~~Sistema permessi 2 livelli (area + azioni processo)~~ — fatto
8. ~~Gestione Clienti/Fornitori (CRUD, drawer, sotto-drawer)~~ — fatto, v2 pianificata
9. ~~Gestione Pratiche v2 (dashboard, flussi, note, allegati, giornale)~~ — fatto, in test UI
10. ~~Autenticazione completa (email, token, reset pw, invito)~~ — fatto, 2FA pianificato
11. ~~Integrazione AI v1 (11 tool, widget conversazionale, glossario IT)~~ — fatto, v2 in corso
12. ~~Catalogo articoli + UoM + BoM + note~~ — **completato** (work-done)
13. ~~Listini vendita v3 (pricing completo, rettifica, alert, variazione massa)~~ — **completato**
14. ~~Migrazione `daterange` nativo PostgreSQL (18 tabelle, backend ottimizzato)~~ — **completato**
15. ~~Parametri di sistema multi-scope (drawer admin con scope user/emittente)~~ — fatto
16. Test UI reali su pratiche, clienti, fornitori, parametri — in corso
17. **Rettifiche prezzi DB-L4** (motore delta, canali manuale/automatico, audit) — pianificato in WIP dedicato
18. Permessi v2 (livello oggetto) — pianificato
19. Integrazione vendite/pratiche e moduli verticali

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
