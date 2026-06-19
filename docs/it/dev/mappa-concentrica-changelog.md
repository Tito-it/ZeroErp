# Mappa Concentrica — Changelog

> Cronologia datata degli aggiornamenti della [Mappa Concentrica](../mappa-concentrica.md).
> La mappa mostra solo lo **stato corrente** per anello; questo documento conserva la storia,
> per non gonfiare il documento principale.
>
> Registra solo evidenze presenti nel repository: commit e documentazione
> `docs/it/dev/work-done/` o `docs/it/dev/work-in-progress/`. Dove la documentazione indica
> test UI o working tree non ancora consolidato, lo stato resta esplicitamente marcato come tale.

---

## 20 giugno 2026

Anello 3 (vendite): **batch fatturazione automatico end-to-end operativo**. Driver CRON
`run-until-done` con discovery a **corsie** `(emittente, tipo_doc_fiscale, utility)`
(`fn_list_emittibili_lane` + lane utility-id), **sync dello stato documentale della fattura
per-step** (`1→2→8`: l'IVA è certificata in EMESSA prima della numerazione in DEFINITIVA;
fix asimmetria di orchestrazione, matrice e guard invariati), registrazione delle run
headless in `job_run_log` (`script.fn_job_run_start/end`), contesto sistema/RLS per il batch.
Hardening commesse→fatturazione: **normalize + guard `tipo_doc_fiscale` emittibile**
(invariante di riga `APPROVATA + NON_EMESSA ⇒ tipo_doc NOT NULL`, codice 497 + CHECK backstop
— evita "fatturato perso in silenzio"), snapshot pricing v5 nel push commesse, fan-out
compositi multi-sorgente, capability azioni stato commessa (`fn_available_actions_commessa`),
pull commessa→`attivita_fatturabili` agganciata agli step DRAFT. La **pipeline fatturazione
passa da "operativa (manuale)" a batch automatico end-to-end**. Vedi
[piano-fix-stato-fattura-pipeline-per-step.md](work-in-progress/piano-fix-stato-fattura-pipeline-per-step.md),
[brief-db-emittibili-lane-tipo-doc-fiscale.md](work-in-progress/brief-db-emittibili-lane-tipo-doc-fiscale.md),
[brief-db-guard-tipo-doc-attivita.md](work-in-progress/brief-db-guard-tipo-doc-attivita.md).

## 13-19 giugno 2026

Anello 2 (pratiche): estensioni workflow v2 del motore (validato sul primo consumatore,
vendite). Arco completo del periodo:

- **Completamento flusso event-driven**: rimosso l'endpoint manuale M2; il completamento è
  guidato dagli eventi del workflow.
- **Azione di completamento flusso data-driven**: l'azione che chiude lo step è risolta da
  configurazione, non cablata.
- **Aggancio documento↔flusso** (ROOT per-flusso): il documento sorgente (es. preventivo) si
  àncora a uno **specifico flusso** della pratica, non alla sola testata; guard di coerenza
  flusso↔pratica (codice 493).
- **Contesto pratica del preventivo a 3 livelli**: `soggetto → ruolo → istanza`
  (derivata/filtrata), con guard di coerenza.
- **Chiusura pratica workflow-driven**: la pratica si chiude solo a flussi obbligatori
  completati; il flusso `chiude_pratica` va eseguito per ultimo (guard 485/492).
- **Esito configurabile dei flussi**: modalità **MANUALE / AUTOMATICO / CONTESTUALE** con
  `esito_default` (guard 494/495: AUTOMATICO solo su step a direzione INTERNA).
- **Giornale più parlante** + appendice di configurazione workflow nella documentazione.
- **Audit utente reale** su `pratiche.*`: `user_update`/`data_update` valorizzati
  dall'operatore reale + trigger insert-only/append-only sul giornale.
- **Assegnazione del singolo flusso a operatore/reparto** con policy **reparto-first**
  (`flussi.risorsa_umana_id` / `unita_organizzativa_id`; eligibilità A/B/C/D — skill-lock,
  competenza, reparto anagrafico, libero; codice 496) tramite `fn_prendi_in_carico_flusso`.
- **Coda lavoro operatore** a 4 livelli (`fn_coda_lavoro_operatore`:
  ASSEGNATO > COMPETENZA > REPARTO > LIBERO) e **consumer FE pannello "Le mie attività"** +
  gating del permesso di assegnazione.

Vedi [analisi-pratiche-workflow-v2.md](work-done/analisi-pratiche-workflow-v2.md),
[brief-design-esito-configurabile-flussi.md](work-in-progress/brief-design-esito-configurabile-flussi.md),
[brief-db-assegnazione-flusso.md](work-in-progress/brief-db-assegnazione-flusso.md),
[brief-design-coda-lavoro-mie-attivita.md](work-in-progress/brief-design-coda-lavoro-mie-attivita.md).

## 11 giugno 2026

Anello 3 (vendite): **ordini di vendita** sviluppati end-to-end DB+BE+FE (CRUD, conferma, stato EVASO, stampa PDF, conversione preventivo/offerta→ordine, univocita' offerta→contratto XOR ordine); **pratica PREVENTIVI** eseguita end-to-end come primo consumatore reale del motore `pratiche` (handler `CONFERMA_VENDITA`, split per natura merce→ordine / servizi→commessa, smistamento riga-per-riga, commesse multi-sorgente) → Anello 2 `pratiche` passa a **validata con primo consumatore**; workflow pratiche v2 (ripetibilita', bivi condizionali, lenti contesto, guard chiusura). Vedi [analisi-pratiche-workflow-v2.md](work-done/analisi-pratiche-workflow-v2.md) e [analisi-ordini-vendita.md](work-in-progress/analisi-ordini-vendita.md).

## 29 maggio 2026

Anello 3 (vendite): contratti passati al modello unificato (drop modalità A/B/C, eccezioni `tipo_eccezione`, snapshot versione listino all'attivazione, lock post-attivazione, stato ANNULLATO); nuovo documento **offerte commerciali** (proposta di condizioni quadro → push 1:1 a contratto) sviluppato DB+BE+FE con generazione PDF e allegati; componenti BoM compositi estesi a offerte; valuta su documenti vendite. Vedi [Gestione Offerte commerciali](../guide/gestione-offerte-commerciali.md) e [Gestione Contratti](../guide/gestione-contratti.md).

## Aggiornamenti ricostruiti dal 26 aprile all'11 giugno 2026

| Data         | Evidenza                                                                                                                                             | Impatto sulla mappa                                                                                    |
| ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| 26 aprile    | `dbops.automazione_chiusura_scadenze` chiuso come framework parametrico dopo due consumatori reali (`vendite.listini_versioni`, `vendite.contratti`) | Anello 0 cresce per uso osservato, non per astrazione preventiva.                                      |
| 27 aprile    | Contratti: Profilo A, immutabilita' post-DRAFT, cessazione data-driven, righe-preview                                                                | Vendite rafforza il sottodominio contratti e consuma il framework di chiusura a scadenza.              |
| 28 aprile    | Refactor frontend/backend catalogo completato Fasi 1-8, test BE 83/83 e build Vite verdi                                                             | Catalogo resta operativo ma con contratti API/metadata piu' maturi.                                    |
| 29-30 aprile | Refactor amm-software completato per matrici, operatori, permessi, emittenti e policy admin                                                          | Anello 1 amministrativo consolidato; le matrici diventano riferimento UI per configurazioni complesse. |
| 1 maggio     | Refactor vendite chiuso DB+BE+FE, modello documentato con 1406 test BE e build Vite verde                                                            | Vendite aggiornata a pattern data-driven per lookup, defaults, capability e azioni.                    |
| 2 maggio     | Preventivi rev2 landed: `emittente_fiscale_id` persistito, `istanza_utility_id` obbligatoria, guard coerenza utility/istanza, 4 codici errore        | Preventivi diventano piu' rigorosi sul contesto emittente/utility.                                     |
| 3 maggio     | Scenario preventivi 2.1 chiuso end-to-end, UI revisioni e riepilogo IVA                                                                              | Vendite avanzata su flusso preventivo operativo.                                                       |
| 3-4 maggio   | Motore documentale parametrico: DB Fase A, backend Tranche A-K, frontend Tranche L-M; test UI dedicato avviato                                       | Nuovo componente `documenti` in Anello 2, operativo tecnicamente ma ancora in test UI.                 |
| 13 maggio    | BoM modello unificato + simmetria listino; componenti BoM (CASO A) estesi a preventivi/ordini/ddt/contratti                                          | I documenti vendite condividono lo stesso modello componenti a 3 livelli (struttura, listino, documento). |
| 15-21 maggio | Refactor contratti: modello unificato (drop modalità A/B/C, eccezioni `tipo_eccezione`, snapshot versione listino all'attivazione, lock post-attivazione, stato ANNULLATO + overlap parziale) | Il sottodominio contratti diventa simmetrico ai preventivi e pronto a ricevere l'offerta come sorgente. |
| 24-27 maggio | Offerte commerciali (DB): testata + eccezioni delta-listino + componenti BoM + utility, 6 stati, `fn_push_offerta_a_contratto` idempotente, vista `is_attiva`, azioni data-driven | Nuovo documento pre-contrattuale in Anello 3 (vendite): la proposta di condizioni quadro che genera il contratto. |
| 28-29 maggio | Offerte commerciali (BE+FE): risoluzione prezzo come contratti, generazione documento offerta con allegati, UI uniformata a contratti                | Offerta operativa end-to-end DB+BE+FE; in consolidamento/test UI.                                       |
| 29 maggio    | Valuta su documenti vendite (`valuta_id` su offerte/contratti/preventivi, default da resolver gestore); guida offerte commerciali pubblicata          | Coerenza valuta cross-documento; documentazione di dominio allineata allo stato reale.                  |
| 2 giugno     | Gate prezzi L1/L2/L3 esteso alle offerte (stesso orchestratore dei contratti); vincoli EXCLUDE anti-overlap ripristinati e governati dal framework `dbops.automazione_overlap` | Coerenza pricing cross-documento; Anello 0 consolida l'anti-overlap parametrico.                        |
| 2-4 giugno   | RLS scope emittente fiscale ATTIVA per operatori: `ENABLE` su 10 tabelle documentali + Ondata 2 scrittura (`FOR ALL` + `WITH CHECK`, migration `20260603-16..25`); reset GUC fail-closed a inizio richiesta lato BE | Multi-Face Auth passa da "infrastruttura predisposta" a RLS operatori attiva; policy portale/shop restano dry-run. |
| 3-4 giugno   | Ordini di vendita DB+BE+FE: vista lista DEF-8, CRUD, conferma, stampa PDF (modulo stampa generico), conversione preventivo/offerta→ordine, lock cliente; regola del 2 su anagrafiche e core (estrazione BB) | Vendite chiude il documento ordine: il ciclo preventivo/offerta→ordine e' percorribile end-to-end.      |
| 5 giugno     | Regola del 2 core FE/BE (factory `createCrudStore`, guard-versione, stack geografico); unificazione sconto righe ordini/fatture; riepilogo IVA documenti non fiscali esteso a ordini | Anello 0/1 frontend consolidano building block condivisi; meno duplicazione cross-dominio.              |
| 8 giugno     | Univocita' offerta→(contratto XOR ordine) con status 409 coerenti; stato ordine EVASO con transizione automatica CONFERMATO→EVASO                     | Il downstream dell'offerta diventa mutuamente esclusivo; il ciclo ordine ha uno stato terminale data-driven. |
| 9-10 giugno  | Pratica PREVENTIVI: handler `CONFERMA_VENDITA` BE+FE (commit `327140116`); `natura_vendita` su preventivi con split merce→ordine / servizi→commessa; smistamento merce→ordine riga-per-riga; commesse multi-sorgente (1 ROOT + N COLLEGATO); natura di vendita amministrabile da applicazione | Vendite diventa il primo consumatore reale del motore pratiche (Anello 2).                               |
| 11-12 giugno | Workflow pratiche v2: ripetibilita' flussi, bivi condizionali, lenti contesto, guard chiusura; contesto pratica a 3 livelli (soggetto → ruolo → istanza derivata/filtrata); BB informazioni pratica; azioni di processo pratiche seedate | `pratiche` passa da "predisposta" a **validata con primo consumatore** (vedi Anello 2).                  |

---

## Sprint storici (marzo – metà aprile 2026)

> Sintesi a livello di milestone delle fondamenta costruite prima del periodo coperto
> dalla tabella sopra. Volutamente **non dettagliata** (niente conteggi test, nomi di
> singoli componenti o numeri di sprint): alcune di queste implementazioni sono state
> in seguito riviste o rifatte diversamente — per lo stato attuale fa fede la
> [mappa](../mappa-concentrica.md), non queste righe. Da fine aprile in poi la cronologia
> prosegue nella tabella sopra.

### Marzo 2026 — fondamenta

- Anello 2 `pratiche`: backend completo (macchina a stati, sospensioni, calcoli tempo), consumabile via REST.
- Anello 0: audit sessioni JWT, request logging, revoca/blacklist token.
- Frontend Sprint 1–7: layout applicativo (sidebar, content tabs, breadcrumb), Amm. Software (operatori, profili reparto, permessi, audit log), building block riutilizzabili (SoggettoForm, autocomplete, composable core), Gestione Geografica (7 tab CRUD), Gestione Soggetti PF/PG/ENTE, pannello config generico, modalita' sola lettura + azioni di processo (permessi livello 1+2), split view, Pratiche v2 frontend.
- Refactor modello concentrico (v3/v4): logica duplicati/CAP/indirizzi/nominativo spostata da frontend a DB/backend.
- Integrazione AI v1 (Anello 4): widget flottante + primi tool lettura/scrittura con conferma.

### Aprile 2026 (fino a metà mese) — domini di vendita e autenticazione

- Gestione Autenticazioni fasi 1–3: email building block, token monouso, reset/invito/cambio password.
- Deprecato il codice errore generico `E_GENERICO` a favore di codici specifici per schema.
- Gestione Clienti v1 + catena automatica istanza fittizia → billing account → cliente.
- Catalogo Articoli + UoM + Listini (DB+BE+FE), poi consolidato e testato.
- Parametri di sistema multi-scope (override personale/emittente).
- Emittenti fiscali CRUD + mapping billing account + matrice utilities; refactor operatore-emittenti 1-a-1 (GUC d'identita').
- Migrazione a `daterange`/`tstzrange` nativo PostgreSQL con vincoli GIST anti-overlap.
- Listini v3: variazioni di massa, alert scadenze, rettifiche controllate; Permessi v2 (`model_permission` a livello oggetto).

---

*Changelog della Mappa Concentrica — ZeroERP. Nuove voci in alto (prosa) o in coda alla tabella del periodo corrispondente.*
