# Mappa Concentrica — Changelog

> Cronologia datata degli aggiornamenti della [Mappa Concentrica](../mappa-concentrica.md).
> La mappa mostra solo lo **stato corrente** per anello; questo documento conserva la storia,
> per non gonfiare il documento principale.
>
> Registra solo evidenze presenti nel repository: commit e documentazione
> `docs/it/dev/work-done/` o `docs/it/dev/work-in-progress/`. Dove la documentazione indica
> test UI o working tree non ancora consolidato, lo stato resta esplicitamente marcato come tale.

---

## 12 luglio 2026

**Anello 3 (vendite) — Indirizzi documento UX v2 (building block cross-dominio).**
Nuovo BB condiviso per gli indirizzi dei documenti di vendita: una sezione inline
(mostra l'indirizzo di **consegna** di default + contatore "+N altri") e un drawer
di gestione (scelta dall'anagrafica del cliente "usa questo" o indirizzo libero
una-tantum), con **snapshot congelato** all'emissione. Lato BE, factory indirizzi
documento parametrica su una `IndirizziDocumentoConfig` per dominio + endpoint
CRUD (`/<dominio>/<id>/indirizzi/`) su **tutti e 5 i domini**
(preventivi/offerte/contratti/ordini/DDT) e **auto-assegnazione** dell'indirizzo
di default (indirizzo di ruolo `CON`, fallback `FATT`) in create + fallback
post-push. Pilota sul DDT, poi rollout ai 4 drawer. Vedi
[brief-design-indirizzi-documenti-vendita.md](work-in-progress/brief-design-indirizzi-documenti-vendita.md).

**Anello 3 (vendite) — Riepilogo IVA DDT + colonna Emittente lista.** Vista
derivata `vw_ddt_riepilogo_iva_dettaglio` (una riga per aliquota, righe con prezzo
NULL escluse: un DDT di solo trasporto non ha riepilogo) esposta dal drawer via
`RiepilogoIvaTable` (componente cross-dominio). Seed opt-in della colonna
"Emittente" nel catalogo lista DDT (parità con le altre 4 liste documento). Vedi
[brief-db-ddt-riepilogo-iva.md](work-done/brief-db-ddt-riepilogo-iva.md),
[brief-db-ddt-colonna-emittente-catalogo.md](work-done/brief-db-ddt-colonna-emittente-catalogo.md).

## 11 luglio 2026

**Anello 2 (documenti) — Stampa PDF DDT: quinto dominio del motore documentale.**
Il DDT diventa il 5° consumatore del motore documenti parametrico: template
`DDT_VENDITA` pubblicato + builder del contesto documentale del DDT (testata,
trasporto, righe, totali, note). L'anteprima in bozza e il documento definitivo
all'emissione seguono il pattern degli altri domini (`pdf_mode` data-driven da
`stati_doc_ddt`). Export lista DDT (CSV/XLSX) allineato agli ordini.

**Anello 3 (vendite) — 2 refactor BB (regola del 2).** (1) Factory
`build_documenti_sorgente_views` per generare le 7 view "documenti per sorgente"
di ogni dominio (~80 righe/dominio); (2) `add_emittente_scope_condition`
(`apps/core/db/emittente_scope_helpers`) che risolve l'array di scope emittente
**una volta** in Python (era 2×/query in 5 repository). Vedi
[brief-be-ddt-vendita.md](work-done/brief-be-ddt-vendita.md) §13.

## 10 luglio 2026

**Anello 3 (vendite) — DDT di vendita (DB + BE + FE).** Nuovo documento del ciclo
attivo: il documento di trasporto. Testata (dati di trasporto: causale, aspetto
beni, vettore, mittente, colli/pesi/volume, targa, autista, tracking) + righe
(prezzo/IVA **opzionali** → DDT di solo trasporto) + componenti BoM condivisi.
Nascita per **evasione** di un ordine confermato — legame **1:N** con **residuo
per riga** (`ordini_righe_fulfillment` append-only: l'evasione aggiunge la
quantità evasa, non la sottrae) — oppure **standalone** manuale. Stati
**data-driven** `DRAFT → EMESSO → SPEDITO → CONSEGNATO` (+ `RESO`/`ANNULLATO`) via
matrice `config.transizioni_stati_ddt` + `fn_available_actions_ddt`. **Numero
assegnato all'emissione** (non alla nascita, `trgfn_ddt_gen_numero_emesso`) e poi
immutabile. Cliente/destinatario immutabili post-creazione. Push a commessa
(sorgente `DDT_VENDITA`) per la fatturazione. Componenti BoM estesi al 5° dominio.
Guida operativa: [gestione-ddt.md](../guide/gestione-ddt.md). Vedi
[brief-db-ddt-vendita-evasione-e-stati.md](work-done/brief-db-ddt-vendita-evasione-e-stati.md),
[brief-be-ddt-vendita.md](work-done/brief-be-ddt-vendita.md),
[brief-fe-ddt-vendita.md](work-done/brief-fe-ddt-vendita.md).

**Addendum SCOPE §15 — emittente memorizzato + RLS su DDT.** Colonna
`vendite.ddt.emittente_fiscale_id` (NOT NULL) memorizzata sul documento (mirror
ordini/preventivi), ereditata dall'ordine sorgente in evasione o risolta dal
billing account per lo standalone (`trgfn_ddt_normalize`), con policy RLS
`rls_ddt_ef_whitelist` e guard di scope in scrittura: un operatore non emette DDT
fuori dal proprio scope emittente. `vw_ddt_lista` espone `emittente_fiscale_id`
per il filtro applicativo (mirror `vw_ordini_lista`).

## 28 giugno 2026

**Qualità di modello — convenzione `codice_interno` / `codice` (cross-anello).** Bonifica
della coppia di colonne delle tabelle `config.*`/lookup (`codice_interno` **immutabile** per
la logica, `codice` **mutabile** per il display), in due interventi complementari:

- **Mislabel alias** `codice_interno AS *_codice` (alias bugiardo che esponeva l'immutabile
  col nome del mutabile): sweep completo DB (viste/funzioni liste contratti/clienti/fornitori/
  coda, indirizzi/istanze, search-detail) + migrazione consumer BE/FE a `*_codice_interno` +
  guardrail CI catalog-based bloccante. Vedi
  [brief-naming-stato-codice-interno.md](work-done/brief-naming-stato-codice-interno.md).
- **Hardcode contro la colonna mutabile** (`WHERE codice = 'X'` dove la logica doveva usare
  `codice_interno`): audit multi-superficie, **21 BUG_DUAL + 7 CANDIDATE** corretti. DB: 16
  oggetti della pipeline commesse→push→fatturazione (`fn_list_*_da_pushare`, `config.sorgenti`,
  `stati_doc_*`) + fix di un **bug reale** in `fn_lookup_utilities_per_ba` (ritornava 0 righe
  perché `codice ≠ codice_interno`). BE: render engine documenti, lookup documenti/sorgenti,
  approvazioni prezzo, super-admin riconosciuto via enum `tipo`, categorie clienti. Estratto il
  BB `resolve_config_id_by_codice_interno` (regola del 2) e corretti **2 bug di create**
  emersi in review (colonna `codice_interno NOT NULL` aggiunta senza default → INSERT rotto su
  categorie clienti ed email account). Vedi
  [analisi-hardcoded-codice.md](work-done/analisi-hardcoded-codice.md).

**Anello 3 (vendite) — gate EVASO ramo commessa.** Corretta l'asimmetria logica col ramo
ordine nel gate EVASO della pratica (bug logico del modello), applicata e **verificata
runtime** (smoke preventivo→EVASO al push, evento `DOMINIO_PREVENTIVO_EVASO`, re-push su EVASO
bloccato). Avviato lo smoke E2E push commesse→fatturazione. Vedi
[brief-db-gate-evaso-commessa-asimmetria.md](work-done/brief-db-gate-evaso-commessa-asimmetria.md),
[a-test-push-commesse-fatturazione.md](work-done/a-test-push-commesse-fatturazione.md).

**Anello 2 (pratiche) — sospensioni anti-overlap + guard data manuale.** Anti-sovrapposizione
delle sospensioni pratica + guard sulla data manuale (DB + piano BE/FE). Vedi
[brief-db-sospensioni-anti-overlap-data-manuale.md](work-done/brief-db-sospensioni-anti-overlap-data-manuale.md).

**Sicurezza AI/agenti.** Revisione critica del documento di considerazioni sicurezza AI
(2026-06-26) tradotta in piano di allineamento documentale/operativo. Vedi
[analisi-sicurezza-aggiornata.md](work-done/analisi-sicurezza-aggiornata.md).

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
