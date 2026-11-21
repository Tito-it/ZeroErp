# Brief BE/FE — Emissione fattura mirata per gruppo fatturabile

> **Tipo**: brief operativo BE + FE · **Target**: `dev/backend-tid` ·
> **Data**: 2026-07-27 → **chiuso 2026-07-28** · **Owner**: Tid · **Stato**: ✅ **CHIUSO** — codice completo, validato a schermo da Tid
> · **Priorità**: 🟠 MEDIA
>
> **Origine**: [analisi-emissione-fattura-ondemand.md](analisi-emissione-fattura-ondemand.md)
> §8 punti 3-6 · contratto DB in
> [brief-db-emissione-fattura-per-documento-sorgente.md](brief-db-emissione-fattura-per-documento-sorgente.md)
> §8-bis.
>
> **Prerequisito DB**: ✅ **completo, applicato e testato** (Fase A + Fase B,
> 4 file pgTAP, 52 asserzioni verdi). Non è più bloccante
> ([[feedback_be_fe_attende_prerequisiti_db]]).

---

## 1. Cosa consegna questa slice, in una frase

L'operatore apre il cockpit Competenza, clicca la card **Da emettere**, vede
l'elenco dei **gruppi fatturabili** del mese (un documento sorgente *oppure* gli
oneri di una commessa), ne seleziona uno o più, preme **Fattura** e ottiene i
lotti in stato **EMESSA**, con un aggancio diretto per andarci a numerare.

---

## 2. Il contratto DB già consegnato (cosa NON va reinventato)

| Oggetto DB | Firma / colonne rilevanti |
|---|---|
| `vendite.fn_build_gruppo_fatturabile_key(bigint, text, bigint)` | `RETURNS text` — unica fonte della chiave. **Mai costruirla a mano lato BE/FE.** |
| `vendite.fatturazione_lotti_gruppi` | `(lotto_id FK CASCADE, gruppo_key TEXT)`, UNIQUE `(lotto_id, gruppo_key)` |
| `fn_emit_attivita_fatturabili_da_commessa(..., p_gruppi text[])` | filtro sul **pull** |
| `fn_select_attivita_fatturabili(..., p_gruppi text[])` | filtro sulle **AF già esistenti** (chiude la falla F8) |
| `fn_list_emittibili_lane(..., p_gruppi text[])` | discovery terne ristretta |
| `fn_list_commesse_emittibili(..., p_gruppi text[])` | discovery commesse ristretta |
| `vw_dash_competenza_gruppi` | una riga per `(competenza_mese, gruppo_key)`: `tipo_gruppo`, `area_documento`, `riferimento`, `cliente_display`, `commessa_*`, `stadio`, `n_attivita`, `valore`, `ha_oneri`, `data_attivita_min/max` |
| `vw_dash_competenza_gruppi_riepilogo` | `n_gruppi`, `n_attivita`, `valore`, `n_gruppi_oneri` per `(competenza, stadio, emittente)` |

**Assenza / `NULL` di `p_gruppi` = comportamento odierno invariato.** Nessun
percorso esistente va adattato.

### Le 4 trappole del contratto (§8-bis del brief DB)

1. **Il criterio non è un parametro di chiamata: è uno stato del lotto.** Gli
   step ricevono solo `lotto_id` e ricostruiscono tutto da `LottoContext`. Il BE
   deve scrivere `fatturazione_lotti_gruppi` **alla creazione del lotto, nella
   stessa transazione**.
2. **L'esito è una LISTA di lotti**, non uno (righe con `tipo_doc_fiscale`
   diverso → terne diverse → lotti diversi).
3. La fermata a **EMESSA non richiede lavoro**: è già `fino_a_stato`.
4. **Nessun `billing_account_id` forzato** sul lotto (D-8).

---

## 3. Reperti sul codice vivo che cambiano il piano

Rilevati leggendo il codice il 2026-07-27, **prima** di scrivere una riga.

### R1 — la chiave di idempotenza della coda annullerebbe la 2ª emissione mirata

`_accoda_job_fatturazione` (`api/views.py`) compone la chiave di **business**
`{job_type}:{competenza}:{scope_key}` per deduplicare i job **vivi**. Due
emissioni mirate sullo stesso mese e scope ma con **gruppi diversi** cadrebbero
sullo stesso job: la seconda verrebbe silenziosamente assorbita dalla prima.

→ **La chiave deve includere un digest dei gruppi.** Senza gruppi il digest è
assente e la chiave resta **identica a oggi** (nessuna regressione sul giro di
massa).

### R2 — l'esito del giro butta via proprio i `lotto_id`

`fatturazione_giro_handler` fa `{k: v for k, v in summary.items() if k != "esiti"}`:
la lista per-terna — che contiene il `lotto_id`, **il dato del «vai al lotto»** —
non arriva mai al FE.

→ Il `result` del job conserva una **lista compatta** `lotti: [{lotto_id,
tipo_doc_fiscale_id, competenza_mese}]`. Compatta, non l'array `esiti` intero:
finisce in un `jsonb` di coda.

### R3 — corsia e gruppo non si parlano *(il nodo vero)*

Il giro on-demand è cablato su `modalita='differita'` →
`p_fatturazione_immediata = false` nella discovery. Un gruppo che appartiene a
una commessa con flag `true`:

- **compare** nella lista `Da emettere` (la vista non conosce la corsia);
- ma l'emissione mirata restituirebbe **zero lotti, in silenzio**.

Non è teorico: i timer del batch non sono ancora schedulati, quindi righe di
corsia immediata ferme sono lo stato normale oggi.

→ **Decisione Tid 2026-07-27: nuova corsia `mirata`** = `('MASSIVO', None,
'EMESSA')`. La selezione esplicita dell'operatore **ignora la corsia** — il
perimetro lo fa `p_gruppi`, che è più preciso di qualunque instradamento
automatico. Ferma a EMESSA come la differita (gate fiscale I-7 invariato).

> Le corsie `immediata` e `differita` restano **bit-identiche**: la corsia
> `mirata` è additiva e non è raggiungibile dal cron (nessun argparse la espone
> come default).

---

## 4. Decisioni prese (2026-07-27, Tid)

| # | Decisione | Motivo |
|---|---|---|
| **BF-1** | Corsia **`mirata`** (`p_fatturazione_immediata = NULL`) | R3 — nessun gruppo selezionabile può sparire in silenzio |
| **BF-2** | **Riuso** di `POST /vendite/fatturazione/run/` con `gruppi[]` opzionale, non un endpoint nuovo | Invariante I-1 (un solo core, un solo verbo); simmetrico alla convenzione DB «assenza = comportamento odierno» |
| **BF-3** | Perimetro FE: **solo** la card `Da emettere` scende sui gruppi | È esattamente ciò che il DB ha abilitato. `Fatturate` → fatture/lotti resta voce separata |
| **BF-4** | I **3 difetti cockpit** (D1, D2, D3) entrano in questa slice | Toccano gli stessi verbi e le stesse card |
| **BF-5** | Il flag `fatturazione_immediata` viene esposto su **ordini, contratti, DDT** | Chiude la Fase B che il DB ha già consegnato |
| **BF-6** | La **riga di totali** viene dal DB (`vw_dash_competenza_gruppi_riepilogo`), non sommata lato FE | Sommare la pagina corrente mostra un parziale che sembra un totale |

---

## 5. Garanzie attese (BE/FE)

| # | Deve essere vero |
|---|---|
| **B1** | Senza `gruppi`, il giro on-demand si comporta **esattamente** come oggi (stessa corsia, stessa chiave di dedup, stesso esito) |
| **B2** | Con `gruppi`, le righe di `fatturazione_lotti_gruppi` sono scritte **nella stessa transazione** della creazione del lotto |
| **B3** | Un **rerun/avanza step** su un lotto mirato **non allarga** il perimetro (il criterio è persistito, non ricalcolato) |
| **B4** | Due emissioni mirate consecutive con gruppi diversi, stesso mese/scope → **due job distinti** |
| **B5** | L'esito riporta **tutti** i lotti prodotti, non il primo |
| **B6** | La lista gruppi e l'emissione usano la **stessa chiave**, senza mapping |
| **B7** | `gruppi` malformato (non lista, elementi non stringa, stringa vuota) → **400** parlante, mai un perimetro vuoto silenzioso |
| **F1** | La riga di totali coincide con la card del funnel (viene dallo stesso `stadio`) |
| **F2** | Nessun verbo visibile senza permesso **e** senza qualcosa da fare (D1) |
| **F3** | Il flag documenti è **readonly** dopo il push (il guard DB lo respinge: il FE non deve offrire un campo inerte) |

---

## 6. Piano a step

> ⬜ da fare · 🟡 in corso · ✅ fatto

### Backend

| # | Stato | File | Contenuto |
|---|---|---|---|
| **BE-1** | ✅ | `db/pipeline_repository.py`, `services/pipeline_runner.py` | `LottoContext.gruppi`; `set_lotto_gruppi` / lettura in `get_lotto_context`; `LottoPipelineParams.gruppi`; scrittura in `_resolve_lotto` **dentro** l'`atomic()` esistente e **solo alla creazione** (un `lotto_id` passato = rerun: il perimetro c'è già) |
| **BE-2** | ✅ | `db/pipeline_repository.py`, `db/commesse_repository.py`, `services/pipeline_step_executor.py` | `p_gruppi` su `fn_select_attivita_fatturabili`, `fn_emit_attivita_fatturabili_da_commessa`, `fn_list_commesse_emittibili`, `fn_list_emittibili_lane`; il pull legge i gruppi dal `context` |
| **BE-3** | ✅ | `services/fatturazione_driver_service.py` | Corsia `mirata` in `_MODALITA`; parametro `gruppi` propagato a discovery e pipeline; `summary["lotti"]` compatto (R2) |
| **BE-4** | ✅ | `services/fatturazione_giro_handler.py`, `api/views.py` | Payload job `gruppi`; corsia scelta dalla presenza dei gruppi; digest nella chiave business (R1); validazione payload |
| **BE-5** | ✅ | `db/vendite_repository.py`, `services/vendite_service.py`, `api/views_dashboard_competenza.py`, `api/urls_v1.py` | `GET /vendite/dashboard-competenza/gruppi/` — lista paginata + `riepilogo` nella stessa risposta |
| **BE-6** | ✅ | ordini / contratti / DDT (repo + service + view) | `fatturazione_immediata` in create/update/detail/lista. ⚠️ Il ✅ della prima consegna era **parziale e silenzioso** sui contratti: vedi registro 2026-07-28 |
| **BE-7** | ✅ | `tests/services/`, `docs/it/backend/vendite/manual/` | Test service + manuali API |

### Frontend

| # | Stato | File | Contenuto |
|---|---|---|---|
| **FE-1** | ✅ | `vendite/api/dashboardCompetenza.js`, `vendite/api/lotti.js`, `vendite/stores/dashboardCompetenza.js` | `listDashboardCompetenzaGruppi`; `runFatturazione(mese, {gruppi})`; sezione paginata `gruppi` + riepilogo nello store |
| **FE-2** | ✅ | `vendite/views/DashboardCompetenzaView.vue` | Drill-down `Da emettere` = tabella gruppi (selezione multipla via `useSelezioneToggle`), verbo **Fattura** su riga e su selezione, riga di totali, esito con **N** «vai al lotto» |
| **FE-3** | ✅ | `CommessaGestioneDrawer.vue`, `DashboardCompetenzaView.vue` | D1 (visibilità Approva), D2 (verbo numera sulla card giusta), D3 (presentazione residui) |
| **FE-4** | ✅ | drawer ordini / contratti / DDT | Campo flag, disabilitato dopo il push |
| **FE-5** | ✅ | `locales/it.json`, `locales/en.json` | Chiavi nuove |

---

## 7. Cosa NON è in questa slice

- **`Fatturate` → fatture/lotti** (§5.5): resta lista commesse. Voce separata.
- **Numerazione dal flusso mirato**: si ferma a EMESSA (gate I-7). Si numera dal
  `LottoDrawer` raggiunto col «vai al lotto», o col verbo di perimetro.
- **Filtri di perimetro** (utility/cliente/emittente) sulla lista gruppi: la
  selezione esplicita li rende meno urgenti; si aggiungono quando servono.
- **Deploy dei timer batch** (§8 punto 7).

---

## 8. Registro attività

### 2026-07-27 · Avvio

- Letto il contratto DB §8-bis e il codice vivo di driver/pipeline/cockpit.
- **3 reperti** che cambiano il piano (§3), di cui uno (R3) è un buco logico che
  avrebbe reso non azionabili i gruppi di corsia immediata.
- Decisioni **BF-1…BF-6** chiuse con Tid.

### 2026-07-27 · BE + FE realizzati ✅

**Consuntivo**

| | Prodotto |
|---|---|
| **File BE toccati** | 21 (repo/service/api/types/error_policies) |
| **File FE toccati** | 11 (api, store, view cockpit, 3 drawer documento, 2 form, BB paginato, CSS, i18n ×2) |
| **Test** | `test_emissione_mirata.py`, **20 asserzioni verdi** |
| **Non-regressione** | baseline `apps.vendite` su HEAD = 17 fail + 84 error; dopo le modifiche **identica** (1321 → 1341 test) |
| **Build FE** | ✓ verde |
| **Doc** | `api_fatturazione`, `api_dashboard_competenza`, catalogo BB backend + frontend, questo brief |

**Deviazioni dal piano, motivate**

1. **`fatturazione_immediata` NON in create contratto.** La fn madre
   `vendite.fn_create_contratto` costruisce l'INSERT da una whitelist sua che
   non contiene la colonna: passarla l'avrebbe **scartata in silenzio**. Il
   flag si imposta con la PATCH in DRAFT — che copre il caso d'uso per intero
   (la corsia va decisa prima del push, e in DRAFT il contratto non è
   pushabile). Estendere la whitelist è una modifica DB, passata al team:
   [brief-db-fatturazione-immediata-create-contratto.md](brief-db-fatturazione-immediata-create-contratto.md)
   (chiuso 2026-07-28).
2. **Nessun campo «flag bloccato» esposto.** Si pensava servisse un indicatore
   «documento già pushato → flag readonly». Verificato sulle capability: la
   testata è editabile solo in DRAFT (ordini, DDT) e la whitelist di patch per
   stato ammette in ATTIVO solo `valido_al`/`meta` (contratti). La finestra di
   modifica e quella del push **non si sovrappongono**: `can_edit_testata`
   basta, e il guard DB resta la difesa finale.
3. **`usePagedDashFetch` esteso con `onPayload`** (additivo, default assente):
   serviva per il `riepilogo` di perimetro. Agganciarlo fuori dal BB — tappando
   la promise nel `fetchPage` del caller — lo avrebbe applicato **anche alle
   risposte scartate dal guard di versione**, con la riga di totali a
   raccontare un contesto diverso dalla lista sopra di sé.

**Difetti cockpit — cosa è stato corretto e su quale evidenza**

- **D1** — `CommessaGestioneDrawer`: i verbi Approva erano `v-if="canApprova"`
  (solo permesso) e restavano a video disabilitati su commessa già pronta. Ora
  la visibilità include `total_non_approvate > 0`.
- **D2** — **confermato sul modello** leggendo il `CASE` di
  `vw_dash_competenza_attivita`: `FATTURATA` = riga *con* `fattura_riga_id`,
  quindi le fatture ancora EMESSA — quelle che «Rendi definitive» numera —
  stanno lì, non in `EMESSA_NON_FATTURATA`. Il verbo è stato spostato sulla
  card `FATTURATA` con condizione sul dato vero (`nDaNumerare`, dal breakdown
  stati fattura), non sul contatore della card sbagliata.
- **D3** — stesso `CASE`: `EMESSA_NON_FATTURATA` = AF **senza**
  `fattura_riga_id`, cioè residui (sospese/posticipate/rimaste indietro), non
  lavoro in transito. Aggiunta la nota «Residui, non lavoro in transito» con
  tooltip esplicativo.

> ⚠️ D2/D3 restano **verificati sul modello, non osservati sui dati**: le viste
> sono `security_invoker` e fuori dal contesto operatore tornano vuote. La
> conferma a schermo è il passo successivo.

### 2026-07-27 · Revisione critica del proprio diff

Rilettura riga per riga alla ricerca di bug, fragilità, duplicazione e
hardcoded. **9 rilievi, tutti corretti.**

| # | Rilievo | Sintomo che avrebbe prodotto |
|---|---|---|
| BE-1 | `set_lotto_gruppi` inseriva la chiave NON strippata (lo strip era solo nel filtro) | chiave con spazi → non combacia mai con `fn_build_gruppo_fatturabile_key` → filtra zero righe **in silenzio**. Return corretto a `rowcount` (dichiarava «registrati» contando i «richiesti») |
| BE-2 | `None if x is None else list(x)` in 4 punti | tupla vuota → `'{}'::text[]` → `= ANY('{}')` sempre falso → **perimetro vuoto invece di nessun perimetro**, l'opposto della convenzione DB |
| BE-3 | `_MODALITA_SCHEDULABILI` elenco parallelo scritto a mano | disallineamento silenzioso alla prima corsia aggiunta → ora **derivato** da `_MODALITA` |
| BE-4 | letterale `"mirata"` duplicato driver ↔ handler | ora importato dal driver (`MODALITA_MIRATA`), owner unico |
| BE-5 | lista gruppi senza clamp dell'offset | pagina stantia → righe vuote con `count > 0` mentre l'envelope dichiarava la pagina effettiva → il FE ripiegava sulla **pagina 1** |
| BE-6 | tiebreak sulla sola `gruppo_key` | la vista raggruppa anche per `stadio` e il filtro stadio è **opzionale**: stesso gruppo su più righe → ordine indefinito → paginazione non deterministica |
| FE-7 | `toggleAll` del BB su lista **paginata** | «seleziona tutto» in pagina 2 **cancellava** la selezione di pagina 1, silenziosamente. Il BB nasce per liste intere: qui il seleziona-tutto opera solo sulla pagina corrente (BB non toccato — 4 consumer) |
| FE-8 | empty-state su `count === 0 && !loading` | «Nessun gruppo fatturabile» mostrato **prima della prima risposta e dopo un errore di rete**: vuoto per ignoranza, non per assenza di lavoro. Ora gated su `loaded` |
| FE-9 | selezione/lotti azzerati solo in `selezionaStadio` | fragile: bastava un percorso futuro che riapre la lista senza passarci per fatturare i gruppi del mese precedente |

**Estrazioni (regola del 2, ok Tid)**

- `useSortState(defaultBy)` nello store competenza: `applyCommesseSort` e
  `applyGruppiSort` erano due copie identiche salvo la colonna di default.

**Bonifica del pattern paginato dei cruscotti (ok Tid)**

Il sondaggio ha separato due cose che sembravano la stessa:

- il *boilerplate* `conditions`/`params`/mapping **non è duplicazione**: filtri
  e proiezioni divergono davvero per endpoint, e forzarci sopra un'astrazione
  avrebbe peggiorato le cose;
- l'**incoerenza di semantica della paginazione**, invece, era un difetto vero.
  Su 6 liste dei cruscotti, 4 clampavano l'offset all'ultima pagina reale e 2
  no. E `list_dash_competenza_commesse` aveva la combinazione **contraddittoria**:
  il service dichiarava la pagina *effettiva* mentre il repository serviva
  quella *richiesta* → envelope «pagina 2» con zero righe, e il frontend che
  ripiegava sulla pagina 1. Lo stesso identico difetto che avevo appena
  corretto nel mio codice, già presente in casa.

Migrate entrambe a `_query_paged_view` + `fn_dash_competenza_attivita`
allineata alla pagina effettiva: **6/6 clampano, 6/6 dichiarano la pagina
effettiva**. Per `commesse` sparisce anche una seconda scansione della vista
(il `COUNT` con lo stesso `GROUP BY` è ora il `COUNT(*) OVER ()` della CTE).
`fn_list_lotti` / `fn_list_lotto_fatture` restano fuori di proposito: non sono
cruscotti e usano `fetch_paged_with_total`, che serve la pagina *richiesta*.

**Verifiche**: 1341 test `apps.vendite`, baseline invariata (17 fail + 84 error,
identici a HEAD); 45 test dashboard competenza verdi; build FE verde.

### 2026-07-27 · Filtro «tipo documento/sorgente» sulla lista gruppi (BF-7)

Richiesta Tid a valle della revisione. **Nessun lavoro DB**: `tipo_gruppo` è già
una colonna di `vw_dash_competenza_gruppi`.

**Decisioni**

- **Asse = `tipo_gruppo`, non `area_documento`.** La vista espone entrambi, ma
  `area_documento` è `NULL` per gli oneri di commessa (non sono documenti):
  filtrando per area, il caso più interessante da isolare sarebbe
  irraggiungibile. `tipo_gruppo` è `COALESCE(codice_interno, 'ONERI_COMMESSA')`.
- **Opzioni dai DATI (facet), non da `config.sorgenti`** — che pure è già in
  whitelist lookup e avrebbe funzionato subito. Due difetti: offre 15 righe di
  cui 5 `*_RIGA` `ROW_VALIDATOR` + `FATTURA`/`ATTIVITA`/`RESO_VENDITA`, che non
  possono mai essere un gruppo fatturabile; e **non contiene `ONERI_COMMESSA`**.
- **Le facet NON seguono il filtro**, i totali sì. Regola di faceting: se le
  voci seguissero la selezione, scegliendo «Preventivi» le altre sparirebbero e
  l'operatore resterebbe chiuso dentro il filtro appena messo.
- **Perimetro: solo la lista gruppi.** Le card del funnel restano i conteggi
  veri del mese: filtrarle cambierebbe il significato del funnel.

**Conseguenza sul riepilogo**: non legge più
`vw_dash_competenza_gruppi_riepilogo` (che aggrega per
`(competenza, stadio, emittente)` e **non espone `tipo_gruppo`**, quindi non
saprebbe seguire il filtro) ma aggrega `vw_dash_competenza_gruppi` con lo
**stesso predicato della lista** (`_where_gruppi`). I numeri sono identici — è
l'aggregazione della stessa vista di dettaglio — ma ora la sorgente è
letteralmente quella delle righe mostrate. La vista di riepilogo resta valida
per altri consumatori.

Cambio filtro → pagina 1 **e selezione azzerata**: le righe selezionate
potrebbero non essere più a video, e fatturare una selezione invisibile è
esattamente la sorpresa da evitare.

**Test**: 6 casi nuovi in `test_dashboard_competenza_service` (32 verdi), di cui
il più importante è quello che verifica che la facet **non** riceva il filtro.

### 2026-07-28 · BE-6 riaperto e chiuso davvero — difetto trovato dal team DB

Lo step BE-6 era dichiarato ✅ ma **non funzionava sui contratti**, e il modo in
cui non funzionava è il peggiore: la PATCH dal drawer rispondeva **200 con
«contratto salvato» senza persistere il flag**. Il payload conteneva comunque
altri campi, quindi il guard «nessun campo aggiornabile» non scattava e non c'era
nulla a video che lo tradisse.

**La causa**: il contratto è l'unico dei tre documenti con **mapper espliciti**
(`_build_create_data_testata` / `_build_update_data_testata`), che copiano campo
per campo. Ordini e DDT usano una dict-comprehension sul payload, dove estendere
la whitelist *è* sufficiente. Lo stesso gesto su tre file ha dato **due successi
e un no-op**. Il difetto non stava in nessuna whitelist ma **fra** whitelist e
repository: nessuna revisione delle liste l'avrebbe trovato.

Rilevato dal team DB lavorando su
[brief-db-fatturazione-immediata-create-contratto](brief-db-fatturazione-immediata-create-contratto.md),
dove vive il dettaglio completo. Qui basti: mapper corretti su **entrambi** i
percorsi (non solo l'update segnalato — anche la create aveva la stessa
trappola), lettura del flag estratta in un metodo unico, **14 test nuovi** sui
tre domini e **3 guardrail** che presidiano gli spazi fra gli anelli:

| Guardrail | Cosa confronta |
|---|---|
| whitelist create testata | BE ↔ `v_testata_allowed` della fn madre (dalla doc auto-gen) |
| whitelist create utility | BE ↔ `v_util_allowed` (stessa struttura fail-open, non presidiata da nessuno) |
| **catena di update** | `_UPDATE_KEYS_TESTATA` → `_build_update_data_testata` → `_UPDATE_WRITE_COLS`, l'anello di mezzo che aveva prodotto il difetto |

**Lezione da portarsi dietro**: quando si estende un campo «su tutti i domini»,
il rischio non è la whitelist dimenticata — quella si vede. È il dominio che ha
una forma diversa dagli altri.

### Prossimo passo

### 2026-07-28 · Validazione a schermo ✅ — brief CHIUSO

Tid ha eseguito la prova sui dati veri. Con questo cade l'ultima voce aperta:
il perimetro §8 punti 3-6 dell'analisi è consegnato per intero.

**Consuntivo della slice**

| | Prodotto |
|---|---|
| **Backend** | emissione mirata per gruppo fatturabile (criterio persistito sul lotto, corsia `mirata`, esito a lista di lotti), endpoint lista gruppi + riepilogo + facet, flag `fatturazione_immediata` sui tre documenti |
| **Frontend** | card «Da emettere» sui gruppi fatturabili con selezione multipagina, filtro tipo documento, riga di totali dal DB, N «vai al lotto», 3 difetti cockpit, flag nei tre drawer |
| **Bonifiche non richieste ma dovute** | 6/6 liste dei cruscotti ora clampano l'offset e dichiarano la pagina effettiva (erano 4/6, con una combinazione contraddittoria) |
| **Guardrail** | 3 sulle whitelist/catene del contratto, nati dal difetto BE-6 |
| **Test** | 20 (emissione mirata) + 6 (facet/filtro) + 14 (flag e catene) = **40 nuovi**, baseline invariata |
| **Doc** | `api_fatturazione`, `api_dashboard_competenza`, `api.md`, catalogo BB backend e frontend |

**Le tre cose che questa slice ha insegnato**, al di là della funzione:

1. **Un criterio che non è un parametro.** Gli step della pipeline ricevono solo
   `lotto_id`: il perimetro doveva diventare *stato del lotto*, scritto nella
   stessa transazione. Chi riprenderà in mano il giro deve saperlo prima di
   toccarlo — è in cima al catalogo BB backend.
2. **I difetti che rispondono 200.** Due dei tre problemi peggiori trovati qui
   (dedup della coda che assorbe la seconda emissione; PATCH contratto che dice
   «salvato» e non salva) non producevano errori. I test che li presidiano sono
   stati tutti provati *rompendo di proposito* ciò che devono intercettare: è
   l'unico modo per sapere che un guardrail guarda.
3. **Il dominio con la forma diversa.** Estendere un campo «su tutti i domini»
   fallisce sul dominio che è fatto diversamente dagli altri, non su quello
   dimenticato.

**Resta fuori perimetro, tracciato altrove**: `Fatturate` → lista fatture/lotti
(BF-3), filtri utility/cliente/emittente sulla lista gruppi, deploy dei timer
batch (§8 punto 7 dell'analisi), variante *fail-loud* della fn madre contratto
(team DB).
