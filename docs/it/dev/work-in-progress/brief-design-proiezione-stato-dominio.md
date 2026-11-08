# Brief Design — Proiezione generica dello stato di dominio nelle pratiche

> **Tipo**: brief di design autorevole (modello + piano DB/BE, FE di consumo) · **Data**: 2026-07-01
> ⚠️ **Allineamento al modello della provenienza (2026-11-08).** Dove questo documento descrive la sorgente
> della pratica come `(sorgente_tipo_id, sorgente_uid)` testuale, con la chiave nativa castata a testo e il
> `key_selector` passato come letterale al trigger del reconcile, oggi vale il modello unico di
> `brief-db-sorgente-documento-e-riga` (lotto P): `pratiche.pratiche_sorgenti` e `pratiche.reconcile_errori` hanno
> le colonne tipizzate (`sorgente_id` bigint o `sorgente_uid` uuid, secondo il tipo, e `sorgente_riga`),
> `pratiche.fn_stato_sorgente` prende tipo, `sorgente_id` e `sorgente_uid`, e il trigger del reconcile riceve il
> solo codice del tipo: la chiave la risolve il catalogo. Il meccanismo è nella guida
> [Sorgente polimorfa](../../guide/sorgente-polimorfa.md). Il resto del modello di proiezione resta valido.
>
> **Owner**: Tid · **Stato**: 🟢 **fase MOSTRA: livello di lettura DB GENERICO su 4 domini;
> BE/FE pilotati e smoke-verdi su PREVENTIVI** (agg. 2026-07-16) —
> ⚠️ *rettifica della dicitura precedente «MOSTRA implementata **su PREVENTIVI**», che sottostimava
> il perimetro*: `script.vw_stato_sorgente` **unisce già 4 domini**
> (`vendite.vw_stato_sorgente_preventivo` / `_offerta` / `_ordine` / `_contratto`), e la Fase 1 BE
> legge quella union tramite il frammento condiviso `_doc_sorgente_lateral` → il livello di lettura
> **non è più solo-preventivi**. Ciò che resta specifico di PREVENTIVI è il **pilota** (validazione
> E2E in-app) e il roll-out di consumo agli altri domini, non la capacità di leggerne lo stato.
> Fase 0 DB ✅ (D1-D3 consegnate dal team DB, [brief chiuso](../work-done/brief-db-proiezione-stato-dominio.md));
> Fase 1 BE ✅ (display fields `doc_*` nei payload **percorso/coda/dettaglio+lista** via
> frammento condiviso `_doc_sorgente_lateral` su `script.vw_stato_sorgente`, ancore
> per-flusso e ROOT; smoke live: PREVENTIVAZIONE COMPLETATO proietta "Preventivo /
> Emesso / IN_ATTESA"); Fase 2 FE ✅ (vista-racconto: Tag stato-documento su card
> ADESSO e sui FATTI finché `doc_terminale=false`; BB `faseSorgenteSeverity` in
> `core/utils/severity.js`; plumbing raw in modalità tecnica). Doc API aggiornata
> (`api_percorso/api_coda_lavoro/api_pratica_detail`).
> **Fase 3 GUIDA (D4) ✅ pilota PREVENTIVI IMPLEMENTATO + E2E verde (2026-07-07)** — inversione
> handler→proiezione, binding NULL (accept+reject auto-avanzano il milestone); design-of-record
> [brief-design-guida-avanza-esito-proiettato](../work-done/brief-design-guida-avanza-esito-proiettato.md) +
> [brief-db-guida-avanza-esito-proiettato](../work-done/brief-db-guida-avanza-esito-proiettato.md) (chiusi).
> **Restano**: validazione E2E in-app di MOSTRA su PREVENTIVI → roll-out MOSTRA+GUIDA agli altri
> domini (offerte/ordini/contratti, brief DB per dominio) → §10.3 azioni nel descrittore.
>
> **Note per il roll-out** (review critica 2026-07-02 · **stato verificato in DB il 2026-07-16**):
> **(a)** 🟡 **parzialmente fatta** — i resolver espongono
> `sorgente_uid` castando la chiave nativa (`preventivi.uid::text`) — il predicato pushdown
> della LATERAL non usa l'indice btree su `uid`: al crescere dei volumi serve un **indice a
> espressione** `((uid::text))` per dominio (voce per il brief DB di roll-out).
> ➡️ **Verifica 2026-07-16**: l'indice **esiste già per 2 domini su 4** —
> `ix_preventivi_uid_text` e `ix_offerte_commerciali_uid_text`. **Mancano `ordini` e `contratti`**:
> restano voce viva per il brief DB di roll-out di quei due domini.
> **(b)** ✅🟡 **IN GRAN PARTE RISOLTA — la strada B è stata scelta e implementata.** La nota
> diceva che i link **COLLEGATO** nascono **senza `flusso_id`** per decisione documentata ("non
> nascono da un flusso"), rimandando la scelta a quando arriveranno i resolver ordine/commessa: se
> valorizzare `flusso_id` sui COLLEGATO (**A**) oppure dare alla LATERAL un **fallback
> pratica-level** (**B**).
> ➡️ **Verifica 2026-07-16, rettificata dopo analisi BE del 2026-07-19** (⚠️ *una revisione
> precedente di questa nota affermava che la scelta fosse ancora aperta e indicava
> `fn_push_preventivo_a_ordine` come sede dell'INSERT: entrambe le affermazioni erano errate*):
>
> - **La strada B è già stata percorsa**: la regola d'ancora è stata promossa alla vista DB
>   condivisa `script.vw_pratica_doc_sorgente` (DISTINCT ON per pratica; ordine: `risolto` →
>   *non*-terminale → ROOT → `id` DESC), che **accende anche i COLLEGATO privi di `flusso_id`**.
>   È la vista che alimenta **dettaglio e lista** (`_PRATICA_JOINS`). Vedi anche nota **(c)**, che
>   chiedeva esattamente questa promozione ed è anch'essa da considerarsi **fatta**.
> - **Resta scoperta solo l'ancora per-flusso** (percorso/coda), che continua a usare
>   `ps.flusso_id = f.id` nel frammento `_doc_sorgente_lateral`: lì un COLLEGATO senza `flusso_id`
>   non si accende. È l'unico residuo reale della nota (b).
> - **Dove nasce davvero il link** (rettifica): sul percorso pratica `crea_ordine_da_preventivo`
>   invoca `fn_push_preventivo_a_ordine` con `pratica_id=None`, quindi il blocco INSERT interno
>   alla fn **non viene mai eseguito**. Il vero autore è `PostSmistamentoHandler` →
>   `PraticheRepository.upsert_pratica_sorgente`, che **accetta già** `flusso_id` (con
>   `ON CONFLICT DO UPDATE SET flusso_id = COALESCE(EXCLUDED.flusso_id, …)`). Il `p_flusso_id`
>   della funzione DB è quindi dormiente **due volte**.
> - ⚠️ **Perché il cablaggio ingenuo sarebbe SBAGLIATO**: l'handler ha in mano il `flusso_id` di
>   **SMISTAMENTO (9012)** — lo step che lo dispatcha — non di **CONFERMA_ORDINE (9013)**. Passarlo
>   così accenderebbe il documento sulla card di SMISTAMENTO, lasciando vuota quella che dovrebbe
>   mostrarlo. Il guard `trgfn_pratiche_sorgenti_guard_coerenza_flusso` non protegge da questo
>   (verifica solo che il flusso sia *della stessa pratica*).
> - ➡️ **Soluzione corretta = D4** «pinning per-step del COLLEGATO, mappa step→sorgente condivisa
>   con GUIDA», già nominata nel commento di `_doc_sorgente_lateral`: è **lavoro di design**, non un
>   cablaggio di due righe.
> - **Scala del beneficio, oggi**: gli step 9013/9014 esistono su **1 sola pratica** (20
>   RICHIESTA_CLIENTE, 19 PREVENTIVAZIONE, 17 APPROVAZIONE_CLIENTE, 16 SMISTAMENTO). **Dati al
>   2026-07-19**: **40 COLLEGATO, 0 con `flusso_id`**; ROOT **14/46**. Nessuna urgenza.
> - **Altri scrittori di COLLEGATO** da considerare al roll-out: `vendite.fn_link_commessa_sorgente`,
>   `vendite.fn_push_offerta_a_contratto` (⚠️ **priva di `p_flusso_id`** — vedi §9-R1) e
>   `preventivi_service._aggancia_commessa_servizi_a_pratica`.
>
> **(c)** ✅ **FATTA — verificato 2026-07-19.** La nota chiedeva: la **regola dell'ancora**
> (ROOT preferito, poi link più recente) oggi vive solo nel frammento Python
> `_doc_sorgente_lateral`: la fase GUIDA (D4) dovrà risolvere la STESSA ancora a livello
> motore → promuoverla a vista DB condivisa (es. `vw_pratica_doc_sorgente`) in quel cantiere.
> ➡️ **La promozione è avvenuta, col nome esatto qui ipotizzato**:
> `script.vw_pratica_doc_sorgente` esiste in DB ed è consumata da `_PRATICA_JOINS`
> (dettaglio/lista). La regola d'ancora implementata è anche **più ricca** di quella descritta:
> `risolto` → *non*-terminale → ROOT → `id` DESC (cioè «documento più vivo della pratica», non solo
> «ROOT poi più recente»). ⚠️ **Resta fuori** l'ancora **per-flusso** (percorso/coda), che continua a
> usare il frammento Python `_doc_sorgente_lateral` con `ps.flusso_id = f.id`: la promozione di
> *quella* è il D4 pinning per-step della nota **(b)**.
>
> **Origine**: voce **V10** e §2.4 di
> [analisi-pratiche-valutazione-stato.md](analisi-pratiche-valutazione-stato.md) — la
> *radice profonda del Problema 1*: pratica e documenti di dominio sono **due macchine a
> stati sovrapposte**, e la pratica non conosce lo stato del documento in corso.
> Cicli di vita **verificati** sui quattro domini reali (§3).
>
> **Documenti collegati**: [brief-fe-percorso-narrativo-operatore.md](../work-done/brief-fe-percorso-narrativo-operatore.md)
> (V1, consuma questa proiezione), [analisi-uniformita-pratica-preventivi.md](../work-done/analisi-uniformita-pratica-preventivi.md)
> (principio "non divergere dallo standalone"), [Guida Gestione Pratiche](../../guide/gestione-pratiche.md).

---

## 1. Problema — due macchine a stati sovrapposte

Le pratiche sono una macchina a stati, ma **anche** preventivo, offerta, contratto e
ordine lo sono, coi propri drawer che *già sanno* avanzare i loro stati. Dentro la
pratica le due si sovrappongono e la pratica è una macchina **grossolana e parallela**
che **non conosce lo stato fine del documento**.

Esempio (pratica PREVENTIVI): il flusso `PREVENTIVAZIONE` si chiude all'**emissione** del
preventivo. Ma da lì il preventivo continua a vivere — comunicato, accettato, magari
revisionato, evaso — e la pratica va **cieca**: l'operatore, per capire *cosa sta
accadendo*, deve **uscire dalla pratica** e aprire il documento. È la causa profonda del
«graficamente non rende» misurato nel brief V1.

## 2. Principio — proiezione, non mirror

- **❌ Mirror** (ogni stato del documento diventa un flusso): duplica la macchina a stati
  su due livelli → **viola la regola #1** (no logica duplicata), le due macchine
  divergono, e l'Anello 2 finisce per conoscere la semantica di dominio. Vietato.
- **✅ Proiezione**: il flusso è un **traguardo (milestone)** che **proietta** lo stato
  vivo del documento. Il **dominio possiede la semantica**; il **motore consuma un
  descrittore normalizzato** e resta agnostico. Read-time, single source of truth = il
  documento (coerente con la risoluzione a read-time già scelta per la versione viva).
- **Regola discriminante** (quali stati diventano milestone): uno stato di documento è un
  **flusso** *solo* se è un punto di **responsabilità o di attesa** (serve
  assegnazione/coda/SLA). Tutto il resto è **status: si mostra, non si trasforma in
  flusso.** Es.: "comunicare al cliente" = responsabilità → milestone; "cliente ha
  visualizzato" = status; "attesa accettazione" = milestone con SLA; "revisione" = loop
  (ripetibilità), mostrato come "rev. N", non nuovo flusso.

## 3. I quattro cicli di vita reali — e la mappa universale

Verificati dai seed `config.stati_doc_*`:

| Dominio | Stati (`codice_interno`) |
|---|---|
| **Preventivo** | DRAFT · EMESSO · ACCETTATO · RIFIUTATO · SCADUTO · EVASO · ANNULLATO *(+ `is_abortito`)* |
| **Offerta** | BOZZA · EMESSA · ACCETTATA · RIFIUTATA · SUPERATA · ANNULLATA |
| **Ordine** | DRAFT · CONFERMATO · EVASO · ALLOCATO · SPEDITO · CONSEGNATO · FATTURATO · ANNULLATO |
| **Contratto** | DRAFT · ATTIVO · CESSATO · ANNULLATO *(+ `is_abortito`)* |

Tutti mappano su un **vocabolario universale** piccolo e stabile (la prova che «funziona
sempre»):

```text
stato di dominio             → fase        esito        terminale
─────────────────────────────────────────────────────────────────
DRAFT / BOZZA                → APERTO      —            no
EMESSO / EMESSA              → IN_ATTESA   —            no   (si aspetta il cliente)
CONFERMATO / ATTIVO          → IN_CORSO    —            no
ALLOCATO/SPEDITO/CONSEGNATO  → IN_CORSO    —            no   (fulfillment)
ACCETTATO / ACCETTATA        → IN_CORSO    POSITIVO     no
RIFIUTAT* / SCADUTO / SUPERATA → CHIUSO    NEGATIVO     sì
EVASO / FATTURATO / CESSATO  → CHIUSO      POSITIVO     sì
ANNULLAT*                    → CHIUSO      NEGATIVO     sì   (is_abortito)
```

> Nota: `is_abortito` esiste **solo** su preventivi/contratti, non su offerte/ordini →
> proprio per questo serve un **asse di normalizzazione uniforme** (§4), non un flag
> sparso.

## 4. Il contratto normalizzato — "lo stato dello stato"

Ogni dominio sa produrre, e la pratica sa consumare, un descrittore **sempre uguale**:

| Campo | Dominio | A cosa serve |
|---|---|---|
| `stato_codice` + `stato_descrizione` | valori nativi del dominio | **Display**: "Emesso", "Accettato" (alimenta la vista-racconto V1) |
| `fase` ∈ `APERTO · IN_CORSO · IN_ATTESA · CHIUSO` | mapping dichiarato dal dominio | **Routing/colore**: il motore ragiona su questo, mai sui nomi di dominio |
| `esito` → `config.esiti_flussi_pratiche` (`—/POSITIVO/NEGATIVO/PARZIALE`) | mapping dichiarato dal dominio | **Verdetto**: fa avanzare il milestone (§6). **Riusa il vocabolario esiti di oggi** |
| `terminale` (bool) | dominio | il documento non evolverà più (auto-chiusura milestone) |
| `azioni` (jsonb, opzionale) | `fn_available_actions_*` | la **prossima azione** suggerita nel documento |

**Punto architetturale**: è il **dominio a dichiarare la mappa** (vendite *sa* che
ACCETTATO=POSITIVO); il motore consuma solo il risultato. Concretamente: un piccolo set
di colonne di normalizzazione (`fase_norm`, `esito_norm`, `terminale`) sulle
`config.stati_doc_*` **owned dal dominio** — `is_abortito` ne è già l'abbozzo.

## 5. Architettura di aggancio (pulita rispetto agli anelli)

```text
pratiche.pratiche_sorgenti  (link pratica↔documento — GIÀ ESISTE)
   │  (sorgente_tipo_id, sorgente_uid)
   ▼
config.sorgenti             (registry per tipo sorgente — GIÀ ESISTE)
   │  resolver_key  (chiave controllata, no dynamic — pattern implementation_key)
   ▼
resolver del dominio        (vendite: vista/funzione normalizzata sui stati_doc_*)
   │
   ▼
descrittore universale (§4) →  la pratica lo MOSTRA / ci ROUTA sopra
```

- Il motore chiama il resolver **per chiave** (come handler / `implementation_key`), a
  **read-time**. Non nomina **mai** uno stato di dominio.
- **Degrada con grazia**: `sorgente_tipo` senza resolver → descrittore `UNKNOWN`, il
  milestone resta un flusso manuale come oggi. **Additivo**, roll-out per dominio (pattern
  `attivo=false`).
- **Layering**: l'Anello 2 non legge `vendite.stati_doc_*`; interroga il resolver che il
  dominio espone. Nessuna dipendenza inversa.

## 6. Le due direzioni (una sola meccanica, tutti i domini)

- **MOSTRA** (il bisogno primario): la pratica proietta `stato_descrizione` + `fase` del
  documento vivo → l'operatore vede *cosa sta accadendo* senza uscire dalla pratica.
- **GUIDA**: quando il documento proietta `esito = POSITIVO` (o `terminale`), il milestone
  avanza. È la **generalizzazione** dell'handler `vendita.accetta_preventivo` (oggi
  per-pratica PREVENTIVI): un solo meccanismo "avanza-su-esito-proiettato" per tutti i
  domini, config-driven. Salda il debito noto in `gestione-pratiche-come-procedere.md §5.3`.

## 7. Cosa esiste già — è *normalizzare*, non greenfield

| Pezzo | Stato | Nota |
|---|---|---|
| `pratiche.pratiche_sorgenti` | ✅ esiste | link pratica↔documento (ROOT/COLLEGATO, `meta`) |
| `config.sorgenti` | ✅ esiste | registry dei tipi sorgente (da estendere con `resolver_key`) |
| `config.stati_doc_*` con `descrizione` | ✅ esiste | display già pronto; `is_abortito` = abbozzo di normalizzazione |
| `fn_available_actions_*` | ✅ preventivo/offerta (ordini parziale) | la "prossima azione" per stato |
| `vw_preventivi_pratiche` | ⚠️ **non verificata** come vista DB | non documentata in `docs/it/dbzero/` né trovata in migration → probabile **join Python ad hoc**, non una proiezione DB pronta (recon 2026-07-01). Non contarci come base |
| `config.esiti_flussi_pratiche` | ✅ 2026-07-01 | il target normalizzato dell'`esito` |
| `template_flussi_handler_eventi` | ✅ esiste | la direzione GUIDA in embrione |

## 8. Deliverable

**DB (brief → team DB):**
- **D1** — colonne di normalizzazione (`fase_norm`, `esito_norm`, `terminale`) sulle
  `config.stati_doc_*` **di ciascun dominio** (il dominio dichiara la mappa §3).
- **D2** — resolver normalizzato per dominio (vendite): vista/funzione che, dato
  `sorgente_uid`, ritorna il descrittore §4 leggendo lo stato corrente + il mapping D1.
- **D3** — `config.sorgenti.resolver_key` + funzione generica di motore
  `pratiche.fn_stato_sorgente(sorgente_tipo_id, sorgente_uid)` che dispatcha per chiave
  (controllata, no dynamic) e ritorna il descrittore.
- **D4** *(GUIDA, fase 2)* — generalizzare "avanza-su-esito-proiettato" (config su
  `template_flussi_handler_eventi` o binding dedicato), sostituendo l'handler accetta
  per-pratica.

**BE:**
- esporre il descrittore nei payload pratica/percorso/coda (display fields) → **alimenta
  V1**. Nessuna logica: solo campi.

**FE:**
- consumo nella vista-racconto (brief V1): "sei qui nella vita del documento".

## 9. Vincoli e non-obiettivi

- **Il motore non nomina stati di dominio**: ragiona su `fase`/`esito` normalizzati.
- **Niente mirror**: non si copiano gli stati del documento in flussi.
- **Read-time**: nessuna duplicazione dello stato (il documento resta l'unica verità).
- **Additivo**: senza resolver, comportamento di oggi. Roll-out per dominio.
- **Non è l'ispettore di configurazione** (V4) né la UI admin: qui è la proiezione
  *runtime* di uno stato che esiste già.

## 10. Domande aperte (decisioni)

1. **Read-time (pull) vs materializzato (push) per le LISTE?** Per il dettaglio pratica la
   `fn` read-time basta; per liste con molte pratiche valutare una **vista** normalizzata
   per dominio (join), o materializzare solo se il profiling lo impone. *Proposta:
   read-time + vista; materializzare solo su evidenza di performance.*
2. **Dove vive il mapping** `fase_norm`/`esito_norm`? Colonne sulle `stati_doc_*`
   (dominio-owned, minimale) vs tabella-mapping centrale. *Proposta: colonne sulle
   `stati_doc_*`.*
3. **`azioni` nel descrittore** subito (riuso `fn_available_actions_*`) o dopo la fase
   MOSTRA? *Proposta: dopo — prima "cosa sta accadendo", poi "cosa fare".*
4. **Struttura esatta di `config.sorgenti`** come registry: verificare colonne prima di
   aggiungere `resolver_key`.

---

## 11. Piano di sviluppo

### 11.1 Esito ricognizione DB (docs/it/dbzero, 2026-07-01) — cosa c'è davvero

| Pezzo | Realtà verificata |
|---|---|
| `pratiche.pratiche_sorgenti` | ✅ `sorgente_tipo_id`, `sorgente_uid`, `ruolo_link` (ROOT/COLLEGATO), `meta`, **`flusso_id`** (àncora il ROOT al flusso d'origine) |
| `config.sorgenti` | ✅ ma **senza `resolver_key`**. Ha `codice_interno`/`codice`/`categoria`/`descrizione`/`scope` + **`target_table`** (regclass) + **`key_selector`** (`id`\|`uid`) + `tipo_doc_fiscale_id`. È un registry descrittivo con polimorfismo `target_table`+`key_selector` |
| `config.stati_doc_{preventivi,offerte,ordini,contratti}` | ✅ tutte con `descrizione`; **`is_abortito` solo su preventivi/contratti**, `is_bozza` solo contratti; **nessuna** colonna di normalizzazione (`fase`/`terminale`/`esito_norm`) → **D1 è nuovo** |
| `fn_available_actions_{preventivo,offerta,ordine,contratto}` | ✅ ritornano `jsonb` capability → per la fase **azioni** (§10.3, dopo) |
| `vw_preventivi_pratiche` | ⚠️ **non verificata** come vista DB (vedi §7): non è una base pronta |
| `config.esiti_flussi_pratiche` | ✅ target dell'`esito` normalizzato |
| dispatch `handler_key` | ✅ `handler_key` (UNIQUE, immutabile) → **registry Python statico** (`HANDLER_MAP`, no dynamic SQL, fail-fast). Modello per la disciplina della chiave |

### 11.2 Decisioni §10 — adottate come da proposta dell'owner

- **§10.1** read-time + **vista** per le liste; materializzare solo su evidenza di performance.
- **§10.2** colonne di normalizzazione **sulle `stati_doc_*`** (dominio-owned, minimale).
- **§10.3** `azioni` nel descrittore **dopo** la fase MOSTRA.
- **§10.4** *(risolto dalla recon)* aggiungere **`resolver_key` su `config.sorgenti`** come
  **chiave controllata** (stessa disciplina di `handler_key`: UNIQUE, immutabile, registrata;
  no dynamic).

### 11.3 Nota architetturale — dove vive il dispatch del resolver

Il pattern `handler_key` dispatcha in **Python** perché gli handler eseguono side-effect
**write-time, uno alla volta**. Il resolver è invece **read-time e proiettato su liste**
(molte pratiche insieme): un dispatch per-riga in Python sarebbe **N+1**. Quindi il resolver
conviene **DB-side** — resolver per dominio come **vista/funzione** + dispatch a **CASE
statico** su `resolver_key` (o vista normalizzata `UNION` per le liste). Coerente col
`fn_stato_sorgente` del §5; la "chiave controllata" mantiene la disciplina di `handler_key`
(niente dynamic SQL). *(È la differenza motivata rispetto al pattern handler: proiezione di
lettura ≠ esecuzione di scrittura.)*

### 11.4 Fasi

- **Fase 0 — Prerequisiti DB** → **brief separato al team DB**
  ([brief-db-proiezione-stato-dominio.md](../work-done/brief-db-proiezione-stato-dominio.md),
  `feedback_db_actions_passaggio_team`): **D1** (colonne norm + seed mapping per dominio),
  **D2** (resolver per dominio: vista/fn che dà il descrittore §4), **D3** (`resolver_key` +
  dispatch `fn_stato_sorgente` / vista normalizzata). **Additivo, roll-out per dominio**:
  senza resolver → descrittore `UNKNOWN`, milestone manuale come oggi. **Partire da
  vendite/PREVENTIVI** (il workflow E2E già validato per V1).
- **Fase 1 — BE** (gated da D1-D3): esporre il descrittore §4 nei payload
  **pratica/percorso/coda** come **display fields** (nessuna logica). Alimenta V1.
- **Fase 2 — FE** (gated da Fase 1): consumo nella **vista-racconto** (brief V1) — "sei qui
  nella vita del documento": `stato_descrizione`+`fase` del documento vivo accanto al passo
  *Adesso*. Riusa `esito_descrizione` già introdotto in V1.
- **Fase 3 — GUIDA (D4)**: generalizzare "avanza-su-esito-proiettato"
  (config su `template_flussi_handler_eventi` o binding dedicato), sostituendo l'handler
  accetta per-pratica. **Solo dopo** che MOSTRA è validato.

**Sequenza**: D1→D2→D3 (DB, su PREVENTIVI) → Fase 1 BE → Fase 2 FE → validazione su
PREVENTIVI → estensione agli altri domini (offerta/ordine/contratto) → Fase 3 GUIDA.
**MOSTRA prima di GUIDA** (§6). Coordinare con **V1**: il descrittore è esattamente ciò che
la vista-racconto deve renderizzare.

---

*Brief vivo: aggiornare lo stato in testa e la riga V10 di
[analisi-pratiche-valutazione-stato.md](analisi-pratiche-valutazione-stato.md) a chiusura.*
