# Piano BE/FE — satelliti della fattura (indirizzi + piano rate)

> ⚠️ **REVISIONE 2026-07-30 — leggere prima
> [piano-db-satelliti-fattura.md](piano-db-satelliti-fattura.md).**
> La verifica critica sui due brief ha cambiato alcune premesse di questo piano:
>
> | § di qui | Cosa cambia | Rif. |
> |---|---|---|
> | §4 Fase 2 | Il **fallback «transitorio»** del context builder alla vista live **non si scrive**: non siamo in produzione, le 7 fatture di test si cancellano e rigenerano. Era codice che nasceva già da rimuovere | §3.8 |
> | §4 Fase 5 | Cade la **bonifica/esclusione** delle fatture storiche prima di accendere il guard `FATT`, per lo stesso motivo | §3.8 |
> | §4 Fase 4 | Il follow-up temuto sui **«gruppi con termini misti» non serve**: un gruppo fatturabile è **un solo** documento sorgente (o gli oneri di **una** commessa), quindi porta un solo termine per costruzione. D-7 non può spaccarlo. Resta vero che una corsa su tutto il mese può produrre **più fatture** di prima: è lo smoke §3.3 a sorvegliarlo | C-10 |
> | §4 Fase 1 | Il mixin `IndirizziDocumentoRepositoryMixin` va **ripuntato** su `script.fn_resolve_indirizzo_documento`: oggi `find_indirizzo_ruolo_per_tipi` preferisce l'indirizzo generico e **ignora l'istanza** del documento. È una **correzione**, non un refactor estetico | C-14c |
> | **nuovo** | La riforma **D-I** elimina due campi dal `ClienteDrawer` (`tipo_gg_scadenza_ft`, `nr_giorni_scadenza`) con le 4 opzioni `opt_gg_*` e le relative chiavi i18n. Lavoro FE non previsto qui | D-I |
> | **nuovo** | Fase 6 DB aggiunge un verbo al `LottoDrawer` (ritorno a DRAFT / estrazione fattura) e una **lista «estratte»** nel cockpit | D-N-bis |
>
> **Revisione 2026-07-30 (seconda passata) — riallineamento dei perimetri.**
> Verifica richiesta da Tid: *«il DB non si è preso carico di attività che avevamo
> definito BE?»*. Esito: **nessuna sovrapposizione** (nessun doppio lavoro), ma
> **quattro blocchi applicativi vivono solo dentro fasi del piano DB** e uno
> **spostamento di responsabilità** (la catena indirizzi passa in SQL) genera
> lavoro BE che nessuno dei due piani conteneva. Recepiti qui: **§0** (nuova
> fase), **§4-bis** (i blocchi dentro le fasi DB) e **§9** (cosa non facciamo).
> Da qui in avanti **questo** è l'unico elenco del lavoro applicativo: il piano DB
> ci rimanda e non lo duplica.
>
> **Owner:** BE (`dev/backend-tid`)
> **Stato (2026-07-31 notte):** Fasi 0, 1 e **2** ✅ · 4-bis: D-Q ✅, DB 2.3 ✅
> (incl. riallineamento al wrapper rinominato `fn_snapshot_fattura_lotto`),
> 3a.7 ✅ (anticipata, residui chiusi) · Fasi 3-4 in attesa del brief scadenze ·
> Fase 5 = 2.5/I.4 lato DB · aperto: giro pipeline reale post-rinomina (§3.1)
> **Prerequisiti (bloccanti):**
> [brief-db-snapshot-indirizzi-fattura.md](brief-db-snapshot-indirizzi-fattura.md) ·
> [brief-db-generazione-scadenze-fattura.md](brief-db-generazione-scadenze-fattura.md)
>
> Questo documento è il **piano di lavoro applicativo**: cosa si tocca, in quale
> ordine, e come si verifica. Le decisioni di dominio e le richieste al team DB
> stanno nei due brief, non qui (regola: modello / brief / piano separati).

---

## 1. Perché serve un piano e non si parte "a sentimento"

Il lavoro applicativo è **cablaggio**, non logica: due handler di pipeline, due
wrapper di repository, un mixin da agganciare, un context builder da ripuntare.
Poche ore di codice. Il valore sta tutto in **tre cose che vanno decise prima**:

1. **l'ordine**, perché una sequenza sbagliata blocca la fatturazione (il guard di
   obbligatorietà `FATT` acceso prima che il popolamento funzioni ferma la pipeline);
2. **cosa consideriamo "fatto"**, perché i satelliti sono esattamente il tipo di
   cosa che «sembra funzionare» e invece è vuota — ce lo siamo già trovati due
   volte (la stampa fattura a trattini, `fn_generate_fatture_righe` mai eseguita);
3. **le regressioni attese**, perché D-7 (termine in chiave di aggregazione)
   **cambia il numero di fatture generate**: va sorvegliato, non scoperto.

## 2. Cosa NON si può anticipare (e va detto)

| Attività | Perché è bloccata |
|---|---|
| Handler + wrapper repository | Devono chiamare funzioni DB di cui non conosciamo ancora nome e firma definitivi |
| Codice degli smoke | Le asserzioni sono già definite (§3), ma il codice tocca le firme reali: scriverlo ora vorrebbe dire riscriverlo |
| Context builder PDF sullo snapshot | Richiede che `fatture_indirizzi` sia popolata, altrimenti la stampa peggiora invece di migliorare |
| Endpoint gestione indirizzi fattura | Dipende da una decisione FE ancora aperta (§7) |

Niente di sostanziale è anticipabile: è cablaggio su superfici che il DB deve
ancora creare. **L'unica cosa utile da fare adesso è questo piano.**

---

## 3. Definizione di «fatto»: gli smoke di accettazione

Sono il **criterio di collaudo del brief DB**, non un complemento del BE: oggi
sarebbero **rossi**, dopo l'apply devono essere verdi. Vanno scritti come primo
atto del lavoro applicativo, prima degli handler, perché descrivono cosa stiamo
cercando di ottenere.

Passano **dalla pipeline reale** (non chiamano le funzioni DB direttamente): così
verificano la catena intera, che è il punto in cui abbiamo già trovato due volte
codice morto con i test verdi.

### 3.1 `smoke-fattura-indirizzi-snapshot.py`

| # | Asserzione |
|---|---|
| 1 | Dopo un giro DRAFT, ogni fattura del lotto ha **almeno la riga `FATT`** in `fatture_indirizzi` |
| 2 | Lo `snapshot` ha lo shape canonico (`intestazione, via, cap, citta, prov, stato, display`) e **non è vuoto** |
| 3 | `origine_indirizzo_id` valorizzato quando l'indirizzo viene dall'anagrafica (tracciabilità della provenienza) |
| 4 | I tipi opzionali (`CON`, `FORNITURA`, `RES`) **non fanno fallire** il giro se assenti |
| 5 | **Ristampa conforme**: il PDF stampa l'indirizzo dello **snapshot**; modificando l'indirizzo in anagrafica e ristampando, il documento **non cambia** ⟵ *l'asserzione che giustifica tutto il lavoro* |
| 6 | Idempotenza: rigenerando il giro non nascono righe duplicate |

> **Stato 2026-07-31 (notte): 8/8 verde, caso 8 ACCESO con la Fase 2** — il
> ciclo D-Q completo (errore → marcatura → correzione → rilancio → ritiro
> segnalazioni) più la ristampa conforme vera: contesto ancorato ai **valori
> congelati** (display della riga `FATT` + `emittente_snapshot`, non solo
> confrontato con sé stesso — due letture live sarebbero uguali fra loro anche
> senza snapshot), poi deriva anagrafica → contesto **identico**
> (`identici_post_deriva=True`). Dal rinominarsi del wrapper mostra anche
> `intestazioni_scritte` (1 alla correzione, 0 al terzo giro: l'intestazione è
> idempotente come le righe).
>
> ⚠️ **Due lezioni di fixture, pagate sul campo.**
>
> 1. **Non si cancellano righe di `anagrafiche.indirizzi`.** La fase «errore»
>    toglieva al cliente il tipo `FATT` con una DELETE; il 2026-07-31 ha smesso
>    di funzionare perché un DDT aveva **congelato quell'indirizzo** come
>    `origine_indirizzo_id`, e la FK ha fatto morire lo smoke *nella fixture*,
>    non in un'asserzione. Ora le righe si **ri-puntano a un tipo di
>    parcheggio** — ammesso al ruolo ma fuori dall'ambito `FATTURE` — così la
>    riga sopravvive alla FK e la catena non trova comunque `FATT`. Due
>    finezze uscite dalla review critica, entrambe misurate sul DB: (a) la
>    selezione del parcheggio rispecchia il guard della matrice **per intero**
>    (`attivo` E finestra `valido_dal/valido_al` — solo-attivo passerebbe la
>    selezione e morirebbe sul guard); (b) **un solo tipo basta per tutte le
>    righe**: le unique di `anagrafiche.indirizzi` sono parziali — `(sr, tipo)`
>    con istanza NULL, `(sr, istanza, tipo)` altrimenti — quindi la generica è
>    al più una e le altre non collidono mai fra loro. Vale per qualunque smoke
>    futuro: più snapshot congeliamo, meno i dati anagrafici sono cancellabili,
>    anche dentro una transazione che fa rollback.
> 2. **Passa dal wrapper, non dallo step** (rilievo del team DB, §10.7 del brief
>    intestazione). Finché lo smoke chiama `run_snapshot_indirizzi_lotto_task`
>    direttamente, dimostra la catena wrapper → funzione DB → D-Q → contesto di
>    stampa, **non** che la pipeline invochi quel wrapper. Ora che l'armamento
>    c'è, va rifatto un giro reale — o modificato lo smoke perché esegua lo
>    step. **Unico aperto del cantiere indirizzi.**

### 3.2 `smoke-fattura-scadenze.py`

| # | Asserzione |
|---|---|
| 1 | Dopo un giro EMESSA, ogni fattura ha **almeno una rata** in `fatture_scadenze` |
| 2 | `Σ importo` delle rate **quadra** con `fatture.totale_a_pagare` (base corretta, non `totale_doc`) |
| 3 | Su un piano non divisibile (es. 100,00 / 3) la differenza è **sull'ultima rata** |
| 4 | `numero_rata` progressivo da 1, nessun buco |
| 5 | `meta.modalita_codice` popolato — è il campo che il contesto PDF legge già |
| 6 | Testata: `termine_pagamento_id`, `modalita_pagamento_id`, `termine_pagamento_snapshot` **valorizzati** |
| 7 | Il **PDF stampa il piano rate** (sezione non vuota, date e importi presenti) |
| 8 | Percorso coppia legacy (cliente con giorni): **una sola rata**, data = data fattura + giorni, spostata a fine mese quando previsto |
| 9 | Idempotenza: doppia esecuzione → stesse rate, nessun duplicato |

### 3.3 `smoke-fattura-aggregazione-termini.py` — il presidio di D-7

Lo smoke **più importante**, perché D-7 cambia quante fatture nascono:

| # | Asserzione |
|---|---|
| 1 | Due attività dello stesso BA con **termini diversi** → **due fatture** |
| 2 | Due attività dello stesso BA con **termine uguale** → **una fattura** |
| 3 | Riesecuzione del giro → **nessuna fattura in più** (chiave e lookup allineati) |
| 4 | Due attività con **utility diverse** → due fatture (regressione sul bug chiave/lookup del brief §4.2) |

Modello per tutti e tre: `backend/scripts/tests/smoke-fatturazione-aggregazione-righe.py`
(fixture in transazione + `set_rollback(True)`, nessun dato persistito).

---

## 4. Fasi, in ordine obbligato

### Fase 0 — Ripuntamento del mixin indirizzi ✅ **FATTA (2026-07-31)**

> **Sbloccata** dal push del team DB fino al punto 2 del piano DB: verificato sul
> DB vivo che esistono `script.fn_resolve_indirizzo_documento`,
> `script.fn_snapshot_indirizzo_soggetto` e
> `vendite.trgfn_fattura_satellite_guard_congelamento`, mentre
> `fn_snapshot_indirizzi_fattura`/`_lotto` (2.1/2.2) **non** ci sono ancora —
> quindi la Fase 0 è arrivata **prima** della 2.1, come doveva.
>
> **Cosa è stato fatto**
>
> | File | Modifica |
> |---|---|
> | `db/_indirizzi_repo_mixin.py` | nuovo `resolve_indirizzo_documento(*, soggetto_ruolo_id, istanza_utility_id, tipo_codice)` che delega alla funzione DB; **rimossi** `find_indirizzo_ruolo_per_tipi` e `find_snapshot_soggetto_per_tipi` (la catena non è più duplicata in Python); nuovo `get_ancora_indirizzi_documento` → coppia `(soggetto_ruolo, istanza)` in **una** query, con `get_soggetto_ruolo_documento` che ora vi delega (un solo SQL da mantenere); nuovo attributo `_indirizzi_doc_istanza_column` |
> | `services/_indirizzi_documento_helpers.py` | `auto_assegna_indirizzo_default` passa l'**istanza del documento** e usa le origini restituite dal DB. Resta **best-effort**: politica d'errore invariata per i 5 domini interattivi |
> | `db/{preventivi,offerte,contratti}_repository.py` | `_indirizzi_doc_istanza_column = "istanza_utility_id"` — i soli **precontrattuali** hanno l'istanza in testata; ordini/DDT/fatture la ricavano dal BA (invariante 1:1 della guida istanze) |
> | `tests/services/test_indirizzi_documento_helpers.py` | **nuovo, 9 test.** Questo percorso girava su 5 domini **senza un solo test**: è il motivo per cui il difetto dell'istanza è vissuto inosservato |
> | `scripts/tests/smoke-indirizzi-documento-catena.py` | **nuovo, 9 casi** sul DB reale (3, 3b, 3c: precedenza istanza, senza istanza, cross-istanza) |
>
> **Esito delle verifiche:** 2062 test verdi · smoke catena **9/9** · smoke
> render-stampa e contatore-note verdi (nessuna regressione) · rollback pulito ·
> **validazione in-app di Tid (2026-07-31)**: la creazione documento continua a
> popolare lo slot indirizzo come prima — chiuso l'unico residuo (il tratto
> `crea_<documento>` → helper dei 5 service, che la fase non toccava).
> **Fase 0 chiusa senza riserve.**
>
> **La prova che il difetto è chiuso** è il caso 3 dello smoke: con due indirizzi
> dello stesso tipo — uno generico e uno per istanza — ora vince **quello
> dell'istanza** (col vecchio `NULLS FIRST` vinceva il generico), e un documento
> **senza** istanza continua a prendere il generico (caso 3b).
>
> **Due scoperte da riportare al team DB** (§4-ter).

**Era la fase più delicata di tutto il piano BE**, perché è l'unica che
**cambia il comportamento di cinque flussi già in esercizio**.

Il piano DB (2.0-b) crea `script.fn_resolve_indirizzo_documento`, che assorbe in
SQL la catena di risoluzione oggi implementata nel mixin Python. La scelta è
corretta (era la seconda implementazione della stessa regola, e quella Python ha
un difetto reale), ma la conseguenza è nostra:

| Punto di intervento | Cosa |
|---|---|
| `backend/apps/vendite/db/_indirizzi_repo_mixin.py` | `find_indirizzo_ruolo_per_tipi` + `find_snapshot_soggetto_per_tipi` → **una sola** chiamata a `script.fn_resolve_indirizzo_documento` (SQL fuori dal mixin). Il metodo deve passare l'**istanza utility** del documento |
| `backend/apps/vendite/services/_indirizzi_documento_helpers.py` | `auto_assegna_indirizzo_default` si adegua alla nuova firma. Resta **best-effort** per i fratelli: la politica d'errore non si tocca, si riusa solo la catena (C-14d) |

⚠️ **Perché è delicata.** Il mixin è montato su **preventivi, offerte, ordini, DDT
e contratti**. Oggi la catena ordina `istanza_utility_id NULLS FIRST`, quindi
**preferisce l'indirizzo generico e ignora l'istanza del documento**; dopo il
ripuntamento preferirà quello dell'istanza. Per quei cinque domini **cambia
l'indirizzo che viene proposto**. È la correzione che vogliamo, ma va trattata
come modifica funzionale, non come refactor:

- test di **regressione** sui cinque domini (creazione documento → slot default
  popolato) **prima** e **dopo**, per vedere la differenza invece di scoprirla;
- un caso mirato: soggetto con due istanze e indirizzi `FATT` diversi → ogni
  documento prende quello della **propria** istanza (è l'asserzione che oggi
  fallirebbe);
- verifica che il layer SOGGETTO continui a produrre `origine_indirizzo_id` NULL
  con `origine_soggetto_ruolo_id` valorizzato: è ciò che distingue «derivato
  dall'anagrafica del soggetto» da un una-tantum digitato a mano.

Senza questa fase la Fase 1 gira su una catena diversa da quella dei fratelli, ed
è esattamente il problema che il piano DB voleva chiudere.

### Fase 1 — Task snapshot indirizzi ✅ **FATTA (2026-07-31)** — con la metà applicativa di D-Q

> Sbloccata dal push DB fino a 2.4 (2.0-2.2 applicate, 2.3 parte inerte
> seminata, pgTAP verdi). Realizzato in un passaggio unico il cablaggio del
> task E i **tre punti della nota D-Q** (§4-bis):
>
> | Pezzo | Dove |
> |---|---|
> | Wrapper `run_snapshot_indirizzi_lotto_task` (5 contatori; **6 dal 2026-07-31 sera**: la funzione DB è diventata `fn_snapshot_fattura_lotto` e aggiunge `intestazioni_scritte` — vedi la riga «DB 2.3» del §4-bis) + voce in `ALLOWED_TASK_FUNCTIONS` + **`disattiva_segnalazioni_lotto_be`** | `db/pipeline_repository.py` |
> | Handler `_handle_snapshot_indirizzi_lotto_task` + **`TaskEsitoParziale`**: `failed_rows > 0` → task_run **ERRORE senza sollevare** (D-Q p.3 — con COMPLETATO il rilancio darebbe SKIP; con un raise il rollback cancellerebbe il lavoro delle fatture sane) | `services/pipeline_step_executor.py` |
> | **Gate D-Q p.1**: il blocco critico vale per l'**avanzamento**; il **rilancio dello stesso step è ammesso**. A fine step con fatture in errore il lotto va in ERRORE (abilita il rerun); il **ritiro bandiere BE** (p.2, errori runner + fotografie esito derivate) avviene a inizio step dentro la transazione — rollback-safe = «solo al successo» | `services/pipeline_runner.py` |
> | Driver `until_done`: si ferma con `BLOCCATO_CRITICITA` + errore strutturato su step con fatture in errore; **prosegue** dopo un rilancio riuscito (flusso «correggo → premo una volta → finisce») | `services/pipeline_runner.py` |
>
> **Verifiche:** 2073 test verdi (**9 nuovi**: 4 executor, 5 runner) · smoke
> §3.1 **attivo e verde** (`smoke-fattura-indirizzi-snapshot.py`: ciclo D-Q
> reale — errore → C log + ponte ERRORE → correzione → rilancio → **ritiro
> segnalazioni** → idempotenza; caso ristampa in SKIP fino alla Fase 2) ·
> 4 smoke esistenti senza regressioni.
>
> **Palla al DB**: armamento 2.3 parte 2 (il nodo nei `processi` DRAFT di
> entrambe le corsie) → poi 2.5 (guard `FATT`). I tre prerequisiti BE citati
> nel loro piano sono chiusi.

(Contenuto originale della fase, realizzato come sopra:)

| Punto di intervento | Cosa |
|---|---|
| `backend/apps/vendite/db/vendite_repository.py` | agganciare `IndirizziDocumentoRepositoryMixin` con `_indirizzi_table="vendite.fatture_indirizzi"`, `_indirizzi_fk_documento="fattura_id"`, `_indirizzi_ambito="FATTURE"`, `_indirizzi_documento_table="vendite.fatture"`, `_indirizzi_doc_sr_column=None` (risoluzione via billing account) |
| stesso file | wrapper `run_snapshot_indirizzi_lotto_task(*, lotto_id, batch_size)` |
| `backend/apps/vendite/db/pipeline_repository.py` | voce in `ALLOWED_TASK_FUNCTIONS` |
| `backend/apps/vendite/services/pipeline_step_executor.py` | handler `_handle_snapshot_indirizzi_lotto_task` + entry nel `handler_registry` (modello: `_handle_ricalcola_iva_lotto_task`) |
| `backend/apps/vendite/tests/services/test_pipeline_step_executor.py` | 2 test (esecuzione + skip in dry-run), indice test nel docstring, mappa `ALLOWED_TASK_FUNCTIONS` mockata |

Verifica di fase: smoke §3.1 casi 1-4 e 6 verdi.

### Fase 2 — Ristampa conforme ✅ **FATTA (2026-07-31, sera)**

> **Realizzata la sera stessa dello sblocco.** Perimetro effettivo — piu'
> piccolo del previsto, perche' le chiavi piatte della testata sono il
> contratto condiviso di drawer FE e template PDF, e derivarle **dentro la
> SQL** dagli snapshot lascia builder e FE intatti per costruzione:
>
> | File | Cosa |
> |---|---|
> | `db/vendite_repository.py` (`get_fattura_testata`) | intestazioni delle due parti derivate da `emittente_snapshot`/`cliente_snapshot` (`->>`), indirizzo cliente dalla riga `FATT` di `fatture_indirizzi`; **rimosse** le due subquery su `vw_indirizzi_resolved_ruolo` (con entrambi i difetti §10.3) e le JOIN su `vw_soggetti_ruoli_dettaglio`/`emittenti_fiscali`; esposti anche gli snapshot integrali (shape non contrattuale); ritirata la costante `TIPO_INDIRIZZO_SEDE_LEGALE` |
> | `services/fattura_document_context_builder.py` | **solo commenti**: shape e codice invariati, la sorgente e' cambiata sotto le stesse chiavi |
> | `scripts/tests/smoke-fattura-indirizzi-snapshot.py` | asserzione 8 **accesa**: contesto ancorato ai valori congelati (non solo a se' stesso) + deriva anagrafica → contesto identico |
> | `docs/it/backend/vendite/manual/api_fattura_dettaglio.md` | «Dipendenze DB» riscritte (cadute le 3 JOIN) + nota di provenienza: chiavi invariate, sorgente = snapshot, NULL senza fallback, avvertenza D-P sul BA padre |
>
> **Verifiche:** smoke §3.1 **8/8 verde** (caso 8: `identici_post_deriva=True`)
> · `smoke-fatturazione-render-stampa.py` verde (PDF reale 18KB dal contesto
> nuovo) · suite 2487 verdi. Le fatture **pre**-snapshot stampano intestazione
> vuota: voluto (§9, dati di test — si rigenerano).
>
> **Review critica post-scrittura (2026-08-01)**: tre assunzioni verificate sul
> DB e non sulla fiducia — la subquery scalare `FATT` senza `LIMIT 1` non può
> esplodere (`uq_tipi_indirizzi_codice_interno` × `uq_fatture_indirizzi_uno_per_tipo_`,
> e a vincoli rotti l'errore sarebbe rumoroso, che è il fallimento giusto); il
> confronto `ctx_dopo == ctx_prima` non può flappare (i tre lettori del builder
> hanno ORDER BY deterministici); `jsonb_out` è NULL-preserving (pre-snapshot →
> `null`, non `{}`). Un solo fix: la doc manuale qui sopra, ultimo consumatore
> della vecchia provenienza. **Asimmetria nota e voluta**: la lista fatture del
> `LottoDrawer` mostra la ragione sociale **live**, il dettaglio/PDF quella
> **congelata** — la lista è una vista operativa, il documento è il documento.

(Testo originale della fase:)

> ⚠️ **Estesa il 2026-07-31 — leggere
> [brief-db-snapshot-intestazione-fattura.md](brief-db-snapshot-intestazione-fattura.md)
> prima di scrivere questa fase.** Misurando per rispondere a una domanda di Tid
> («per l'emittente possiamo usare lo storico degli indirizzi?» — no, §2 del
> brief) è emerso che il perimetro qui sotto è **incompleto**: congela
> l'indirizzo del cliente e lascia live la sua ragione sociale e P.IVA, più
> l'intera intestazione dell'emittente. Risultato: incoerenza dentro lo stesso
> blocco stampato.
>
> Due fatti che cambiano la fase:
>
> - la **sede legale dell'emittente non è mai stata stampata**: la subquery di
>   `vendite_repository.py:1600-1605` filtra `tipo_indirizzo_codice = 'SEDELEG'`
>   ma la vista espone in quella colonna il `codice` (`SEDE-LEG`) — 0 match
>   sempre. Il tipo `FATT` funziona solo perché i due codici coincidono per caso;
> - le fatture in tabella sono **8** (conteggio con bypass RLS: senza GUC
>   operatore `vendite.fatture` appare vuota, fail-closed), tutte di test e già
>   dichiarate sacrificabili dal §9 — quindi niente da migrare, ma il numero
>   cresce a ogni giro di prova: la forma definitiva costa oggi meno di
>   qualsiasi giorno futuro.
>
> **Conseguenza operativa:** questa fase si scrive **una volta sola**, sulla
> forma decisa nel brief (snapshot intestazione in testata + indirizzo cliente da
> `fatture_indirizzi`), invece di ripuntare il context builder due volte.
>
> ---
>
> ### ✅ Sbloccata la sera del 2026-07-31 — il DB ha accolto e applicato
>
> Risposta del team DB nel §10 del brief, e **tutto già a DB**: colonne
> `fatture.emittente_snapshot` / `cliente_snapshot` con guard di congelamento
> (`20260731-05`), `fn_snapshot_intestazione_fattura` (`-06`), wrapper
> `fn_snapshot_fattura_lotto` che chiama le due sorelle (`-07`), più
> l'armamento del nodo nelle corsie DRAFT. **Nulla resta da attendere: la Fase 2
> è nostra e basta scriverla.**
>
> **Correzione di merito da recepire (§10.3 del brief): i difetti sono due,
> non uno.** Oltre al confronto `codice`/`codice_interno`, la subquery legge
> `vw_indirizzi_resolved_ruolo`, che per costruzione contiene il **solo layer
> RUOLO** (`WHERE scope = 'RUOLO'`) — e il ruolo `EF` non ha **alcun**
> indirizzo: la sede dell'emittente sta sul layer SOGGETTO. È il secondo a
> spiegare la sede vuota, e vale **identico sulla riga del cliente**. Leggere lo
> snapshot li chiude entrambi in un colpo, perché lo snapshot è composto da
> `fn_resolve_indirizzo_documento`, che i due layer li attraversa già.
>
> **Lo shape contro cui scrivere `_shape_emittente` / `_shape_cliente`**:
> `denominazione`, `codice_fiscale`, `id_fiscale`, `regime_fiscale_rf`, `sede`,
> `rea`, `capitale_sociale`, `forma_giuridica`, `socio_unico`, `liquidazione`;
> lato cliente `codice_sdi`, `pec_fatturazione`, `destinatario_fe`,
> `billing_account_id`/`ba_codice`. Regola dichiarata dal DB: di ogni entità
> referenziata si congela il **valore** e l'id sta **accanto**, non al posto suo
> — un id da solo non è uno snapshot. ⚠️ Lo shape è **interno e non
> contrattuale** finché il builder XML FatturaPA non esiste: aggiungere o
> rinominare chiavi resta lecito senza migrazioni.
>
> ⚠️ **Normalizzare le chiavi mancanti**: il DB **omette** le chiavi nulle e il
> template gira con `StrictUndefined`. Il builder deve proiettare sull'elenco
> completo e ordinato, come fa già `DdtDocumentContextBuilder` con
> `SNAPSHOT_KEYS_ORDERED`.
>
> **Il `billing_account_id` dello snapshot cliente è il BA *padre*** (D-P), non
> il conto di chi ha consumato: non va letto come «il conto del cliente».

| Punto di intervento | Cosa |
|---|---|
| `backend/apps/vendite/db/vendite_repository.py` (`get_fattura_testata`, ~1576-1650) | le **quattro** letture live → snapshot: `emittente_snapshot` e `cliente_snapshot` dalla testata, indirizzo cliente dalla riga `FATT` di `fatture_indirizzi`. **Spariscono** le due subquery su `vw_indirizzi_resolved_ruolo` (e con loro entrambi i difetti del §10.3 del brief) e le JOIN su `vw_soggetti_ruoli_dettaglio` per i dati che ora vivono negli snapshot |
| `backend/apps/vendite/services/fattura_document_context_builder.py` (`_shape_cliente`, ~199-211) | `_shape_cliente` legge lo snapshot + nuovo `_shape_emittente`; proiezione su chiavi complete e ordinate (StrictUndefined) |
| — | modello già fatto: `DdtDocumentContextBuilder` è l'unico context builder che legge gli snapshot |

**Nessun fallback** (rev. 2026-07-30, §9). La prima stesura prevedeva di ricadere
sulla vista live per le fatture senza snapshot, per non rompere la ristampa delle 7
storiche. Non si fa: sono dati di test, si rigenerano. Il lettore legge **solo** lo
snapshot — se manca, manca, ed è giusto che si veda.

Verifica di fase: smoke §3.1 caso 5, il test di conformità (modifico l'anagrafica,
ristampo, il documento non cambia).

### Fase 3 — Task generazione scadenze (dopo apply brief scadenze)

Stessa forma della Fase 1, sui punti di intervento gemelli
(`run_genera_scadenze_lotto_task`, `_handle_genera_scadenze_lotto_task`).

⚠️ **Attenzione all'ordine dentro lo step**: il task va **dopo**
`ricalcola_iva_lotto` (prima i totali non esistono). L'ordine è nel seed DB, ma i
test dell'executor devono asserirlo, non fidarsi.

Verifica di fase: smoke §3.2 completo.

### Fase 4 — Regressioni di D-7 (contestuale alla Fase 3)

Il termine in chiave cambia **quante** fatture nascono. Da sorvegliare:

| Cosa | Azione |
|---|---|
| Test e smoke esistenti che contano le fatture di un lotto | rileggere le aspettative: `smoke-fatturazione-aggregazione-righe.py` oggi assume che le attività dello stesso BA finiscano in una fattura |
| Cockpit / dashboard competenza | i **gruppi fatturabili** e i contatori riflettono l'aggregazione: verificare che il perimetro mostrato resti coerente con le fatture prodotte |
| Emissione mirata per gruppi | ✅ **nessun follow-up** (§9): un gruppo fatturabile è un solo documento sorgente — o gli oneri di una sola commessa — quindi porta un solo termine per costruzione, e D-7 non può spaccarlo |

Verifica di fase: smoke §3.3 + suite completa vendite.

### Fase 5 — Accensione del guard `FATT` obbligatorio (coordinata col DB)

Il guard sta nel brief DB, ma la **sequenza è condivisa**: si accende **solo dopo**
che la Fase 1 gira, altrimenti blocca la pipeline.

Le 7 fatture storiche senza snapshot **non si bonificano** (§9): se inciampano nel
guard si cancellano e si rifà un giro. L'unica verifica che serve è che il task
della Fase 1 popoli davvero le fatture **nuove** — cioè lo smoke §3.1, non un
censimento dello storico.

### Fase 6 — Frontend

| Cosa | Stato |
|---|---|
| Piano rate nel drawer | ✅ **nessun lavoro**: `ScadenzeSintesi` e il campo «Prossima rata» esistono e mostrano `—` finché le rate non arrivano. Dopo la Fase 3 si popolano da soli |
| Campi «Modalità di pagamento» e «Termine» | ✅ già nel drawer, oggi sempre vuoti perché la testata è NULL. Dopo la Fase 3 vanno **verificati a video** (è il primo momento in cui mostrano un valore) |
| Sezione indirizzi nel drawer fattura | ⏸️ decisione aperta, §7 |

---

## 4-bis. Lavoro applicativo dentro le fasi del piano DB (owner: BE)

Queste voci **compaiono solo nel piano DB**, dentro fasi marcate come sue. Il
rischio non è il doppio lavoro — nessuna è anche altrove — ma l'**omissione**: il
team DB non tocca i `.vue` né `types.py`, e noi non guardiamo una fase marcata DB.
Sono elencate qui perché **l'owner è il BE**; la fase DB resta il loro innesco.

| Innesco (piano DB) | Cosa tocca a noi | Quando |
|---|---|---|
| **3a.7** — riforma condizioni di pagamento (D-I) | ✅ **FATTA (2026-07-31, PR #1100), ANTICIPATA rispetto al DROP** — decisione presa con Tid e team DB: le colonne legacy non avevano lettori a valle e il `NOT NULL` ha un `DEFAULT`, quindi anticipare **elimina** l'accoppiamento invece di gestirlo — 3a.5/3a.6 diventano DROP pure, senza deploy FE da sincronizzare. Fatto: `ClienteDrawer.vue` (via i 2 campi + `tipoGgOptions`), 6 chiavi i18n it+en, `clienti_repository` (2 whitelist + SELECT), `clienti_service`, `views_clienti`, `test_clienti_repository`. Verifiche: 1068 test verdi, `check_i18n_keys` pulito, eslint + build Vite ok. **Residui CHIUSI la sera stessa**: `fn_update_cliente` riscritta dal DB (`20260731-08`, con 3a.5) e `E_CLIENTI_GIORNI_SCADENZA_OBBLIGATORI` **ritirato** da `error_policies.py` — il trigger non esiste più, la policy era codice morto; resta il gemello fornitori, che il suo trigger ce l'ha ancora. **3a.7 completamente chiusa** | ~~Contestuale al DROP~~ → anticipata |
| **6.6** — eliminazione del flag `esclusa` (D-M) | **filtro API** e **`types.py`** (il resto è DB) | Con la Fase 6 DB |
| **6.7** — ritorno a DRAFT / estrazione (D-N-bis) | Verbo nel `LottoDrawer` con conferma esplicita di **cosa si perde**, e **lista «estratte»** nel cockpit | Dopo 6.0-6.5 DB |
| **D-L** — rinomina funzioni di reset | **4 righe obbligatorie + ~12 nomi Python** da allineare (vedi sotto): decisione Tid 2026-07-30, si rinomina su **entrambi** gli strati | Contestuale alla rinomina |
| **D-Q** — fattura in errore, lotto non avanza ma si rilancia (decisione Tid 2026-07-31) | **La regola di blocco** (`lotto_segnalazioni_service`) e **il ritiro delle segnalazioni scritte dal BE** (vedi sotto): senza, la via d'uscita definita da Tid non esiste | **Prima** dell'accensione del task in pipeline (DB 2.3) |
| **DB 2.3** — seed del task snapshot indirizzi | ✅ **FATTA** (registrazione + handler in Fase 1; armamento DB applicato il 2026-07-31). **Coda del 2026-07-31 sera**: il DB ha rinominato il wrapper in `fn_snapshot_fattura_lotto` (scrive anche l'intestazione — brief §10.8) e il BE è stato riallineato: valore in `ALLOWED_TASK_FUNCTIONS`, query del wrapper, **sesto contatore `intestazioni_scritte`** già letto. Il `task_code` e il nome del metodo Python restano `snapshot_indirizzi_lotto`/`run_snapshot_indirizzi_lotto_task`: l'ancora stabile è il task, non la funzione dietro il wrapper | ~~Prima che il DB armi lo step DRAFT~~ → chiusa |

### D-L: il minimo indispensabile, misurato

Se il DB rinomina (`fn_reset_lotto_draft` → `fn_annulla_lotto_da_draft`,
`fn_reset_lotto_fattura_draft` → `fn_elimina_fattura_draft_da_lotto`), **queste
quattro righe devono seguire**, altrimenti il reset lotto muore con
`42883 function does not exist`:

| File:riga | Cosa |
|---|---|
| `backend/apps/vendite/db/pipeline_repository.py:174` | valore in `ALLOWED_TASK_FUNCTIONS` |
| `backend/apps/vendite/db/pipeline_repository.py:1985` | `FROM vendite.fn_reset_lotto_draft(%s)` |
| `backend/apps/vendite/db/pipeline_repository.py:2006` | `FROM vendite.fn_reset_lotto_fattura_draft(%s, %s)` |
| `backend/apps/vendite/tests/services/test_pipeline_step_executor.py:64` | mappa `ALLOWED_TASK_FUNCTIONS` mockata |

> 🔄 **Rev. 2026-07-30 (decisione Tid, che supera il paragrafo precedente).**
> **Si rinomina su ENTRAMBI gli strati**: i nomi Python vanno resi coerenti con
> quelli DB. La proposta di rinunciare alla rinomina **non è stata accolta**, e
> nemmeno quella di rinominare solo a DB.
>
> **Motivo**: rinominare solo a DB scambia un disallineamento con uno peggiore.
> Un nome che mente ma è coerente ovunque si impara una volta; due nomi diversi
> per la stessa cosa su due strati si sbagliano ogni volta. Il «debito accettato
> consapevolmente» sarebbe stato pagato da chiunque leggesse il codice dopo.

**Oltre alle quattro righe obbligatorie, vanno rinominati anche i nomi Python**
(~12 punti, meccanici):

| File | Cosa |
|---|---|
| `services/pipeline_service.py` | entrypoint `fn_reset_lotto_draft` / `fn_reset_lotto_fattura_draft` → nomi allineati a quelli DB |
| `services/__init__.py` | import e `__all__` |
| `api/views.py` | import e chiamate nelle due view |
| `db/pipeline_repository.py` | i metodi `reset_lotto_draft` / `reset_lotto_fattura_draft` |
| `services/lotto_reset_service.py` | il metodo omonimo |
| test | i `@patch` che puntano ai nomi vecchi |

⚠️ Il **`task_code`** del registry (`reset_lotto_draft`) **resta invariato**: è il
nome del *task* di pipeline, non della funzione, e vive nei CSV di seed.
Rinominarlo sarebbe una migrazione di dati senza guadagno.

> **I punti 2, 3 e 4 di D-L restano il valore vero della decisione** — in
> particolare l'**over-free del `lock_batch_id`** (C-22), che è un bug e va
> corretto comunque, e che non induce nessun lavoro applicativo.

### D-Q: la metà applicativa — 📎 nota del team DB (2026-07-31)

> **Chi scrive:** DB (`dev/db-tid`), scrivendo la Fase 2.2. Simmetrica alla vostra
> §4-ter. **Perché vi riguarda:** la decisione D-Q di Tid è per metà vostra, e
> senza quella metà il disegno non sta in piedi — il lato DB è pronto ma il
> runner non lo lascia partire.

**La regola decisa da Tid** (piano DB §2, D-Q): se una fattura è difettosa, lo
step **si completa lo stesso**, la fattura resta **marcata in errore**, il lotto
**non avanza** allo step successivo. Per uscirne, due strade: **estrarre** il
documento dal lotto, oppure **rilanciare lo stesso step** — *ero su DRAFT
rilancio DRAFT, ero su EMESSA rieseguo EMESSA*.

**Cosa abbiamo già fatto lato DB.** La marcatura per-fattura esiste da sempre e
funziona: log `'C'` su `fatture_log` → `fn_sync_fatture_log_critical_lotto` →
`fn_resolve_stato_esecuzione` (`critical` → `ERRORE`) su
`fatturazione_lotti_fatture`. In `fn_snapshot_indirizzi_lotto` (2.2) abbiamo
aggiunto il pezzo mancante: **al successo il task ritira le proprie segnalazioni
precedenti** (`disabilitato = true`, filtrando su `meta->>'source'`), così il
rilancio dello step riporta davvero a posto la fattura. Il ricalcolo lo fa da sé
il trigger `AFTER UPDATE` su `fatture_log`.

**I due punti che restano a voi.**

| # | Dove | Cosa |
|---|---|---|
| 1 | `services/lotto_segnalazioni_service.py` (`evaluate_lotto_status`) + `services/pipeline_runner.py:410-431` | Oggi `blocks_next_step` è vero se esiste **una** criticità o **una** fattura in `ERRORE`, e il runner rifiuta **qualunque** esecuzione con `E_PIPELINE_LOTTO_CRITICAL`. Va distinto **«non avanzare»** da **«non ripartire»**: il rilancio dello **stesso** step deve essere ammesso, l'avanzamento al successivo no. Finché questa riga non cambia, la via d'uscita di D-Q è vietata dal codice |
| 2 | `services/pipeline_error_logger.py` + `services/pipeline_runner.py:76-86` | Su **qualunque** errore di pipeline il runner scrive un critical di **scope LOTTO**, e **nessuno lo ritira mai**. Quindi anche risolto il punto 1, un lotto che ha avuto un giro fallito resterebbe bloccato per una segnalazione vecchia. Stesso principio che abbiamo applicato a DB: **chi alza la bandiera la abbassa** — al successo dello step, le segnalazioni di lotto scritte dal BE per quello step vanno disattivate |
| 3 | Handler del task (`pipeline_step_executor`, scrittura di `fatturazione_lotti_task_runs`) | 🔴 **Senza questo, il punto 1 non basta.** `fn_resolve_lotto_task_execution_mode` risolve `task_stato = 'COMPLETATO'` → **`SKIP`**. Il nostro task **non solleva** quando una fattura fallisce (per disegno: le altre devono essere lavorate), quindi il `task_run` risulterebbe COMPLETATO e **il rilancio dello step salterebbe il task** — l'anagrafica corretta non verrebbe mai riletta. L'handler deve registrare il `task_run` come **`ERRORE`** quando `failed_rows > 0`: allora la risoluzione dà `RESUME` (la policy è `RESUME_TASK`) e il rilancio funziona. È il motivo per cui `fn_snapshot_indirizzi_lotto` ritorna **cinque** contatori invece di tre: `failed_rows` esiste perché voi possiate distinguere «fatto» da «fatto, ma con rifiuti» |

**Tre fatti verificati il 2026-07-31**, perché non li ridobbiate cercare:

- **nessuno** porta `disabilitato` a `true`, in tutto `backend/apps/` — la colonna
  esiste, i lettori la rispettano, ma non ha scrittori;
- i log critici spariscono **solo** con `fn_cleanup_fatture_by_ids`, cioè
  distruggendo la fattura: oggi l'unica uscita reale è rifare il lotto;
- disattivare un log **basta**: il trigger `AFTER UPDATE` su `fatture_log`
  richiama `fn_sync_fatture_log_critical_lotto`, che conta i soli log con
  `disabilitato IS FALSE` e riallinea `critical` e `stato_esecuzione`. Non serve
  scrivere nient'altro.

> ⚠️ **Sfumatura da non invertire**, vale per entrambi i lati: lo step **corrente
> riprova** le fatture in errore (è la correzione), gli step **a valle le
> saltano** (lì la fattura è un rifiuto). Se il DRAFT le filtrasse, non si
> potrebbe più correggere; se l'EMESSA le riprovasse, una fattura senza
> indirizzo arriverebbe alla numerazione.
>
> 📌 È anche il **punto B dell'analisi 6.0** del piano DB, dove è annotato come
> «rinviato, vedremo». Segnaliamo che **morde prima**: si presenterà al primo
> cliente senza indirizzo di fatturazione, non in Fase 6.

## 4-ter. 📎 Due note per il team DB, emerse scrivendo la Fase 0 (2026-07-31)

Nessuna delle due è un difetto: sono **trappole da fixture** che ho incontrato di
persona collaudando la catena, e che si ripresenteranno scrivendo i pgTAP del
punto **2.4** del piano DB. Riportarle qui fa risparmiare due giri a vuoto.

### (a) `CON` non è ottenibile dal layer RUOLO di un cliente

Misurato sul DB il 2026-07-31:

| Insieme | Tipi |
|---|---|
| Whitelist ambito `FATTURE` (`tipi_indirizzi_allowed`) | `RES`, **`FATT`** (obbligatorio), `FORNITURA`, `CON` |
| Ammessi al **ruolo cliente** (`tipi_ruolo_tipi_indirizzo`, tipo_ruolo 1) | `RES`, `DOMFISC`, `POSTA`, `SPED`, `FATT`, `FORNITURA` — **`CON` assente** |
| Presenti sul layer **SOGGETTO** (dati reali) | `RES`, `DOMFISC`, `SEDELEG`, `POSTA`, `SPED`, `FATT`, **`CON`** |

`CON` è ammesso al solo `tipo_ruolo = 8`. Quindi sul layer RUOLO di un cliente
**non può esistere**, e per una fattura può arrivare solo dal layer SOGGETTO.

Non è un problema di comportamento — D-2 dice che i tipi opzionali mancanti non
generano errore, quindi il task 2.1 fa la sua ricerca e va avanti. Ma ha **due
conseguenze pratiche**:

1. **la fixture pgTAP di 2.4 non può inserire un `CON` sul ruolo cliente**: il
   trigger `trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo` la respinge con
   `E_TIPO_INDIRIZZO_NON_PERMESSO`. Per esercitare `CON` bisogna passare dal
   layer SOGGETTO (o usare un ruolo di tipo 8);
2. vale la pena **decidere consapevolmente** se lo slot `CON` sulla fattura ha
   senso: oggi resterà vuoto in tutti i casi in cui il cliente non ha un
   indirizzo di consegna sul soggetto. Le alternative sono ammettere `CON` al
   ruolo cliente, togliere `CON` dalla whitelist `FATTURE`, o accettarlo come
   slot che si popola solo per via anagrafica indiretta. Non urge, ma meglio
   scritto che scoperto in validazione.

### (b) Gli indirizzi «liberi» hanno un CHECK a quattro campi

`anagrafiche.indirizzi` non ha colonne CAP/città. Per una riga **non
normalizzata** il vincolo `chk_indirizzi_free_requirements` pretende
`indirizzo_libero` **+** `stato_id` **+** la terna
`(locality, postal_box, administrative_area | sublocality)` — oppure la coppia
normalizzata `(comune_id, codice_postale_id)`. Una `INSERT` con il solo
`indirizzo_libero` viene respinta.

È il secondo inciampo che ho avuto: le fixture di 2.4 vanno scritte con la terna
completa (nel mio smoke: `'Roma', '00100', 'RM'` + `stato_id` dell'Italia).

## 5. Verifiche trasversali (a ogni fase)

- `./manage-test.sh apps.vendite.tests apps.core.tests` verde;
- `python3 scripts/check_i18n_keys.py` pulito (se si aggiungono etichette FE);
- build Vite + eslint (solo se si tocca il FE);
- `scripts/pgtap-baseline.sh vendite` — confronto con la baseline, per non
  attribuirsi rossi preesistenti né mascherare regressioni;
- gli smoke §3 **rieseguiti**, non solo la prima volta: sono il presidio contro il
  ritorno del difetto.

## 6. Rischi noti

| Rischio | Mitigazione |
|---|---|
| Guard `FATT` acceso troppo presto → pipeline bloccata | Fase 5 esplicita, con conteggio preventivo |
| Ristampa delle 7 fatture storiche senza snapshot | **rischio accettato** (§9): dati di test, si rigenerano. Nessun fallback in codice |
| D-7 frammenta le fatture più del previsto | smoke §3.3 + revisione delle aspettative sui test esistenti (Fase 4) |
| `fatture_indirizzi` letta nel dettaglio API senza RLS | la tabella **non ha policy**: se la esponiamo, la protezione resta l'ordine «testata prima → 404» già presidiato da `test_note_non_contate_se_testata_none` e gemelli. Valutare l'estensione delle policy satelliti |
| Storicizzazione gonfiata dalle rigenerazioni | `DELETE+INSERT` su `fatture_scadenze` scrive in `storico.fatture_scadenze_id` a ogni giro: atteso, da tenere presente nei conteggi |

## 7. Decisioni FE ancora aperte

1. **L'operatore deve poter correggere un indirizzo su fattura DRAFT?**
   - **Sì** → serve l'endpoint (factory `build_indirizzi_documento_views` già
     pronta) + `stati_modificabili = {"DRAFT"}` + un lettore di stato
     (`get_stato_codice` **assente** su `VenditeRepository`, da scrivere) + montare
     `DocumentoIndirizziSection` nel drawer.
   - **No** → la tabella è scritta solo dalla pipeline; nel drawer gli indirizzi si
     mostrano in sola lettura (o non si mostrano affatto).
2. **Gli indirizzi vanno esposti nel dettaglio fattura?** Se sì, il payload cresce
   di una chiave e vale l'avvertenza RLS del §6.
   ℹ️ *Aggiornamento Fase 2 (2026-07-31)*: il payload del dettaglio espone già
   `emittente_snapshot` e `cliente_snapshot` integrali (additivo, shape non
   contrattuale — brief intestazione §10.2) e `cliente_indirizzo` ora è il
   display della riga `FATT` congelata. La decisione aperta resta quella sulla
   **lista** delle righe di `fatture_indirizzi` (gli slot per tipo), non
   sull'intestazione.
3. **Badge documenti** nella barra azioni del drawer: il payload ha già
   `contatori` come dict proprio per questo — se serve, si aggiunge un contatore
   senza cambiare la shape.

---

## 8. Stima

| Fase | Effort |
|---|---|
| §3 — smoke di accettazione (3 file) | mezza giornata (è la parte che richiede pensiero) |
| **0 — ripuntamento mixin + regressione 5 domini** | **~mezza giornata**: il codice è poco, la verifica sui cinque flussi è il lavoro |
| 1 — task indirizzi | ~2 ore |
| 2 — ristampa conforme | ~2 ore |
| 3 — task scadenze | ~2 ore |
| 4 — regressioni D-7 | variabile, dipende da quanto emerge |
| 6 — FE | 0 se la decisione §7.1 è «No» |
| **4-bis — 3a.7** (drawer cliente + BE condizioni) | ~mezza giornata |
| **4-bis — 6.6 / 6.7** (flag `esclusa`, verbo lotto + lista estratte) | con la Fase 6 DB |
| **4-bis — D-L** | 4 righe, oppure **zero** se il DB rinuncia alla rinomina |

Il grosso del tempo non è scrivere il cablaggio: è **verificare che i satelliti
esistano davvero** e che il documento stampato dica la verità.

---

## 9. Cosa NON facciamo, e perché

Deciso con Tid il 2026-07-30. Serve scritto, perché sono tutte cose che un
lettore diligente cercherebbe e non troverebbe.

| Cosa | Perché non si fa |
|---|---|
| **Rigenerare le 7 fatture storiche** dopo l'accensione dello snapshot | Sono **dati di test**. Non vale un passo di piano: se una vecchia fattura stampa un indirizzo letto live o inciampa nel guard `FATT`, si cancella e si rifà un giro. Nessun codice, nessuna procedura, nessuna bonifica |
| **Fallback del context builder** alla vista live per le fatture senza snapshot | Stessa ragione (piano DB §3.8): sarebbe codice che nasce già da rimuovere |
| **Bonifica/esclusione** delle fatture storiche prima del guard `FATT` | Idem |
| **Rinominare gli entrypoint Python** di D-L (~12 punti) | Sono nomi interni, invisibili al DB. Restano le sole **4 righe** che nominano la funzione SQL (§4-bis) |
| **Follow-up «gruppi con termini misti»** | Non serve: un gruppo fatturabile è **un solo** documento sorgente (o gli oneri di **una** commessa), quindi porta un solo termine per costruzione — D-7 non può spaccarlo (piano DB C-10) |

> **Criterio generale che ne emerge, e che vale oltre questo cantiere:** non siamo
> in produzione. Davanti a un dato di test sbagliato la risposta è **rifare il
> dato**, non scrivere codice che lo tollera. Ogni riga scritta per accomodare
> sette fatture di prova sarebbe debito con la data di scadenza già stampata sopra.

---

## 10. Un'offerta al piano DB: gli smoke coprono anche la 3a

L'autocritica del piano DB (W-2) nota che **le fasi DB non hanno un criterio di
«fatto» end-to-end**: hanno i pgTAP, che verificano le funzioni ma non la catena —
e la 3a è la fase con più superficie e nessun collaudo.

Gli smoke di §3 passano dalla **pipeline reale**, quindi possono chiudere quel
buco senza scrivere niente di nuovo: dopo la riforma delle condizioni di pagamento,
`smoke-fattura-scadenze.py` asserisce già che la testata porta
`termine_pagamento_id` e `modalita_pagamento_id` e che le rate quadrano — cioè che
la catena **risolve** attraverso il catalogo riformato. Se la 3a ha rotto qualcosa,
lo smoke lo dice.

Va aggiunta una sola asserzione: **nessun cliente resta senza condizioni** dopo la
migrazione (3a.4) — un conteggio, non un test complicato.
