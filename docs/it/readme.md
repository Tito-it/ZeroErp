# ZeroERP

**ERP open-source per aziende italiane, progettato con approccio DB-first e sviluppo concentrico.**

ZeroERP nasce da esperienza diretta su sistemi gestionali in contesti utilities e PMI.
L'obiettivo e` ridurre la complessita` superflua mantenendo rigore su dati, regole e tracciabilita`.

---

## Stato progetto

> **Sviluppo attivo — DB, backend e frontend operativi sui domini core, anagrafiche, catalogo, vendite (preventivi, offerte, contratti, ordini), pratiche e documenti. Non ancora rilasciato per produzione.**
>
> La fotografia dettagliata e datata dello stato e` mantenuta in un'unica sezione:
> [Stato dello Sviluppo](#stato-dello-sviluppo). Per la vista per anelli (dipendenze,
> ordine di costruzione, stato per componente) vedere la [Mappa Concentrica](./mappa-concentrica.md).

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

Fotografia sintetica (11 giugno 2026):

- Database core: operativo (14 schemi, 200+ tabelle, trigger, funzioni, viste, **daterange nativo**)
- API backend: operativo; conteggio test complessivo da rigenerare dopo la chiusura della suite UI documenti
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
- Refactor catalogo: **completato** (28 aprile 2026)
  - Fasi 1-8 DB+BE+FE chiuse; lookup/defaults/capability spostati su contratti API/backend quando necessario
  - Riferimento: [analisi-refactor.frontend-catalogo.md](./dev/work-done/analisi-refactor.frontend-catalogo.md)
- Refactor amm-software: **completato** (29-30 aprile 2026)
  - Operatori, permessi, emittenti fiscali, matrici e policy admin riallineati agli standard frontend/backend
  - Riferimento: [analisi-refactor.frontend-amm-software.md](./dev/work-done/analisi-refactor.frontend-amm-software.md)
- Listini vendita v3: **completato** (Sprint B-v3 chiuso)
  - Versioni, righe prezzo, associazioni, test resolver, clone, auto-close (25 endpoint, 42 test listini)
  - Variazione % massa su BOZZA con dry_run, alert scadenze con widget, rettifica controllata con lock FOR UPDATE
  - Pricing commesse: riallineamento prezzo, variazione eccezionale, sblocco (3 endpoint, 9 test commesse)
  - Trigger DB defense-in-depth `trgfn_listini_righe_guard_stato`
  - Documentazione: [sviluppo-listini-v3.md](./dev/work-in-progress/sviluppo-listini-v3.md), API: [api_listini.md](./backend/vendite/manual/api_listini.md), [api_commesse_pricing.md](./backend/vendite/manual/api_commesse_pricing.md)
- Refactor vendite: **completato** (1 maggio 2026)
  - DB+BE+FE chiusi; lookup, form-defaults, capability e azioni data-driven documentati
  - Riferimento: [analisi-refactor.frontend-vendite.md](./dev/work-done/analisi-refactor.frontend-vendite.md)
- Preventivi rev2: **completato** (2-3 maggio 2026)
  - `emittente_fiscale_id` persistito e immutabile, `istanza_utility_id` obbligatoria, guard coerenza utility/istanza
  - Revisioni preventivo e riepilogo IVA chiusi end-to-end; generazione PDF agganciata al motore documentale in test UI
  - Riferimento: [risposta-db-brief-preventivi-rev2.md](./dev/work-done/risposta-db-brief-preventivi-rev2.md)
- Contratti — modello unificato: **completato a DB, BE+FE in consolidamento** (15-21 maggio 2026)
  - Drop modalità A/B/C; eccezioni di riga `tipo_eccezione` (OVERRIDE/ESCLUSIONE/AGGIUNTA); snapshot `listino_versione_id` all'attivazione; lock post-attivazione; stato ANNULLATO con overlap parziale
  - Componenti BoM su righe composite; gate prezzo L1/L2/L3
  - Guida: [gestione-contratti.md](./guide/gestione-contratti.md)
- Offerte commerciali: **sviluppate DB+BE+FE, in consolidamento** (24-29 maggio 2026)
  - Documento pre-contrattuale (proposta di condizioni quadro), simmetrico ai contratti: eccezioni delta-listino, componenti BoM, utility
  - 6 stati (BOZZA→EMESSA→ACCETTATA→push contratto; RIFIUTATA/ANNULLATA/SUPERATA), revisioni, azioni data-driven
  - `fn_push_offerta_a_contratto` idempotente (legame 1:1), generazione documento offerta con allegati, risoluzione prezzo come contratti
  - Guida: [gestione-offerte-commerciali.md](./guide/gestione-offerte-commerciali.md)
- Valuta su documenti vendite: **completato a DB** (29 maggio 2026)
  - `valuta_id` su offerte/contratti/preventivi, default da resolver (catena billing account → gestore). Follow-up: resolver lato backend
- Gate prezzi L1/L2/L3 esteso alle offerte: **completato** (2 giugno 2026)
  - Stesso orchestratore dei contratti (`resolve_or_check_override_prezzo`); banner L2 e fix gap L1 sui componenti
  - Riferimento: [refactor-prezzi.md](./dev/work-done/refactor-prezzi.md)
- Ordini di vendita: **sviluppati DB+BE+FE** (3-8 giugno 2026)
  - CRUD con lista configurabile, azioni data-driven, conferma, stato EVASO con transizione automatica
  - Stampa PDF ordine (modulo stampa generico), riepilogo IVA, unificazione sconto righe
  - Conversione upstream preventivo→ordine e offerta→ordine (prezzi negoziati, `fn_offerta_righe_espanse`); univocita' offerta→(contratto XOR ordine)
  - Lock cliente post-creazione (`E_ORD_CLIENTE_IMMUTABILE`)
  - Riferimenti: [analisi-ordini-vendita.md](./dev/work-in-progress/analisi-ordini-vendita.md), API: [api_ordini.md](./backend/vendite/manual/api_ordini.md)
- Pratica PREVENTIVI — prima validazione del motore pratiche con consumatore reale: **completata** (9-12 giugno 2026)
  - Handler `CONFERMA_VENDITA` con split per natura: merce→ordine (`fn_push_preventivo_a_ordine`), servizi/ricorrente→commessa; gate EVASO
  - Smistamento merce→ordine riga-per-riga; commesse multi-sorgente (1 ROOT + N COLLEGATO) con push idempotente
  - Workflow pratiche v2: ripetibilita' flussi, bivi condizionali, lenti contesto, guard chiusura; contesto pratica a 3 livelli (soggetto → ruolo → istanza)
  - Natura di vendita amministrabile da applicazione (filtro catalogo per destinazione)
  - Riferimenti: [analisi-pratiche-workflow-v2.md](./dev/work-done/analisi-pratiche-workflow-v2.md), [analisi-pratiche-domini-anello3.md](./dev/work-in-progress/analisi-pratiche-domini-anello3.md)
- Regola del 2 — estrazione building block cross-dominio: **eseguita su core/anagrafiche FE+BE** (3-5 giugno 2026)
  - Convergenza store Pinia su factory `createCrudStore`, famiglia guard-versione (`useFetchVersion`), stack geografico, util condivise
  - Tracker: [regola-del-due-core-fe.md](./dev/work-done/regola-del-due-core-fe.md)
- Motore documentale parametrico: **completato tecnicamente, test UI in corso** (4 maggio 2026)
  - Schema `documenti`, modelli documenti, versioni, asset documentali, documenti generati e file persistenti
  - Backend: render Jinja2 + WeasyPrint, storage parametrico, endpoint template/asset e endpoint preventivo `genera`/`anteprima`/`lista`/`download`
  - Frontend: Configurazione documenti, modelli, asset, pulsante "Genera PDF" nel drawer preventivo e lista documenti generati
  - Riferimenti: [sviluppo-documenti.md](./dev/work-done/sviluppo-documenti.md), [sviluppo-documenti-test-ui.md](./dev/work-done/sviluppo-documenti-test-ui.md)
- Migrazione `daterange` + PG18 STORED generated: **completata**
  - Fase 0-3 (apr 2026): 19 tabelle migrate a `daterange`, `script.trgfn_set_validita()`, linee guida SQL §7b
  - Fase PG18 (mag 2026): `validita` → `GENERATED ALWAYS STORED` su 20 tabelle; 3 tabelle con temporal UNIQUE (`WITHOUT OVERLAPS`); temporal FK `listini_righe_componenti → articoli_componenti`; `trgfn_set_validita` droppata
  - Backend ottimizzato: `validita @>` al posto dei doppi confronti `valido_dal`/`valido_al`
  - Piano PG18: [piano-miglioramenti-db-pg18.md](./dev/work-done/piano-miglioramenti-db-pg18.md)
  - ✅ **Regressione Step 2b risolta** (2026-06-02): i 5 vincoli `ex_*_no_overlap` parziali, ricreati per errore come `CREATE INDEX` (non enforçanti), sono stati **ripristinati a `EXCLUDE` reali** e ora **governati dal framework** `dbops.automazione_overlap` (colonne `where_predicate`/`key_expressions` + runner notturno `automations_overlap` per l'auto-guarigione). Lato contratti aggiunto il **DRAFT-scope** (esclusività solo all'attivazione, colonna generata `partecipa_overlap_snapshot`). Dettagli: [refactor-overlap.md](./dev/work-done/refactor-overlap.md) + [refactor-overlap-v2.md](./dev/work-done/refactor-overlap-v2.md).
- Rettifiche prezzi (DB-L4): estratte in [work-in-progress/sviluppo-rettifiche.md](./dev/work-in-progress/sviluppo-rettifiche.md), **da implementare**
- Integrazione AI v1: operativa, **11 tool** registrati
  - Pratiche (cerca, dettaglio, flussi)
  - Anagrafica soggetti (cerca soggetti, dettaglio soggetto)
  - Anagrafica clienti / billing account (cerca\_billing\_account — sinonimo "cliente" in italiano)
  - Catalogo articoli (cerca\_articoli)
  - Operatori (cerca\_operatori)
  - System prompt con glossario di dominio italiano (cliente=BA, articolo=catalogo)
  - Widget flottante, contesto documentale statico, multi-tool chaining, 61 test
- Frontend Vue: operativo su domini core, anagrafiche, catalogo, vendite, pratiche, documenti
  - Layout applicativo (sidebar morfica, content tabs, split view, breadcrumb, ricerca universale)
  - Amm. Software completa: operatori, profili reparto, permessi riepilogo, audit log, email
    - Drawer dedicato gestione permessi richiamabile dalla riga lista (`OperatorePermessiTab` riusabile)
  - Gestione soggetti: PF/PG/ENTE end-to-end, ruoli, contatti, indirizzi, CF validator IT
  - Gestione geografica: 7 tab CRUD
  - Gestione clienti/fornitori: drawer con sotto-drawer contatti/indirizzi/conti
  - Gestione pratiche v2: dashboard, flussi, note, allegati, giornale; pratica PREVENTIVI operativa (contesto a 3 livelli, dialog accettazione, BB informazioni pratica)
  - Catalogo articoli: lista, drawer con 3 tab (UoM, BoM, note), `ArticoloLookup` BB cross-dominio
  - Listini v3: lista, drawer con versioni/associazioni, sub-drawer righe, test resolver, dialog variazione %, widget alert scadenze, dialog programma chiusura
  - Vendite preventivi: refactor data-driven, revisioni, riepilogo IVA e generazione PDF preventivo in test UI
  - Vendite ordini: lista configurabile, drawer, conferma/EVASO, stampa PDF, conversione da preventivo/offerta
  - Configurazione documenti: modelli documenti e asset documentali con drawer/lista standard
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
16. ~~Refactor catalogo / amm-software / vendite verso API metadata-driven~~ — fatto
17. ~~Preventivi rev2 (emittente persistito, istanza obbligatoria, revisioni, riepilogo IVA)~~ — fatto
18. Motore documentale parametrico (modelli, asset, generazione PDF preventivo) — completato tecnicamente, test UI in corso
19. ~~Contratti modello unificato (eccezioni delta-listino, snapshot versione, lock post-attivazione)~~ — completato a DB, BE+FE in consolidamento
20. ~~Offerte commerciali (proposta condizioni quadro → push 1:1 a contratto, componenti BoM, documento + allegati)~~ — sviluppate DB+BE+FE, in consolidamento
21. ~~Valuta su documenti vendite (offerte/contratti/preventivi)~~ — completato a DB; resolver BE da fare
22. ~~Ordini di vendita (CRUD, conferma, EVASO, stampa PDF, conversioni preventivo/offerta→ordine)~~ — fatto (giugno 2026)
23. ~~Integrazione vendite→pratiche: pratica PREVENTIVI end-to-end (primo consumatore reale del motore pratiche)~~ — fatto (giugno 2026); secondo consumatore pianificato
24. Test UI reali su pratiche, clienti, fornitori, parametri e documenti — in corso
25. **Rettifiche prezzi DB-L4** (motore delta, canali manuale/automatico, audit) — pianificato in WIP dedicato
26. ~~Permessi v2 (livello oggetto)~~ — fatto; v3 (sotto-oggetti padre/figlio) in pianificazione
27. Moduli verticali e integrazione pratiche sugli altri processi

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
