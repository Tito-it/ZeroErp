# Brief BE/FE — DDT e resi nelle lenti + coda accrediti sui fatti

> **Tipo**: brief operativo BE/FE · **Target**: `dev/backend-tid` · **Data**: 2026-07-16
> · **Rev**: 2026-07-17 — allineato alla rifondazione a **contatore** del brief DB
> (DL-27/28 + emendamenti DL-21/23/24/26): motivo rinominato, coda accrediti con quantità,
> card Ordini mista, nuovo gate solo-trasporto, punto "riga non fatturabile" superato.
> · **Owner**: Tid
> **Stato**: 🟢 **REALIZZATO** (2026-07-18, non committato) — DB applicato (PR #1002),
> BE+FE sviluppati, 1782 test vendite+core verdi, build Vite verde, lint pulito,
> gunicorn ricaricato. Restano: **seed lista 10** (mini-brief companion
> [brief-db-seed-lista-coda-accrediti-contatore.md](../work-done/brief-db-seed-lista-coda-accrediti-contatore.md)
> — le 4 colonne nuove della coda compaiono all'apply, BE/FE già pronti) e
> **validazione in-app** Tid. Consuntivo in fondo (§7).
> **Design-of-record**: [brief-design-fatturazione-due-lenti.md](brief-design-fatturazione-due-lenti.md)
> §6-quater, decisioni **DL-19..28**.
> **Prerequisito DB**: [brief-db-fatturazione-ddt-resi.md](../work-done/brief-db-fatturazione-ddt-resi.md).
> **Gate**: BE/FE partono a **oggetti DB applicati** ([[feedback_be_fe_attende_prerequisiti_db]]).
> **Contesto**: non siamo in produzione ([[project_no_produzione_solo_sviluppo]]) → breaking
> secchi, nessuna compat.
> **Parte da**: le tre viste vive e committate (Lente 1 Competenza, Lente 2 Backlog,
> Situazione aperta v2 — `6daf0a65d` + `8887f4113`).

---

## 0. Scopo in una riga

Far comparire **DDT** e **RESI** nelle due lenti a monte, adeguare la **coda accrediti** alla
sua nuova forma (popolazione = differenza negativa del contatore, con la **quantità**
dell'accredito dovuto) e gestire il nuovo **gate solo-trasporto** nel drawer DDT (DL-28).

## 1. La buona notizia: quasi tutto è zero-touch

Il grosso del lavoro è **DB**. Le lenti sono già data-driven e fail-visible: il riepilogo
accoda le aree sconosciute invece di dare 400, la misura euro/conteggi la decide il BE nel
payload (`valore_* = null` → area a conteggi, DL-11) e il FE **legge, non ri-decide**, i motivi
si decodificano con `labelOrCode` (fallback al codice grezzo). Quindi **niente lavoro
strutturale**: le card nuove comparirebbero da sole.

Anche la **grana (reso × motivo)** del ramo resi (un reso misto = due righe di backlog,
deroga dichiarata in DL-24/brief DB §4d) è zero-touch: verificato 2026-07-17, le DataTable di
Backlog e Situazione aperta **non usano `dataKey`** proprio perché la union è cross-area
(`documento_id` si ripete già tra aree — c'è il commento nel template). Righe duplicate per
documento non rompono nulla.

Ma da sole le card comparirebbero **male**, e sono queste le cose da toccare davvero: fuori
ordine di funnel, senza etichetta tradotta e — la sola vera rottura — **non drillabili**.

## 2. Backend

### BE-1 — Whitelist aree: il punto che romperebbe (`db/vendite_repository.py`)

⚠️ **Il filtro `area` del Backlog è fail-closed**, a differenza del filtro `classe` che fu
de-whitellistato apposta il 2026-07-06 (nota Fase 2 del design doc). Verificato nel codice:
`fn_dash_backlog_documenti` valida `area` con `allowed=DASH_FATTURAZIONE_AREE` →
**un'area non in whitelist dà 400**. Senza questo step le card DDT/RESI comparirebbero nel
riepilogo (fail-visible) ma il drill-down andrebbe in errore: **card che non si aprono**.

| Costante | Oggi | Diventa |
| --- | --- | --- |
| `DASH_FATTURAZIONE_AREE` | `PREVENTIVI, ORDINI, OFFERTE, CONTRATTI, COMMESSE` | **+ `DDT`, + `RESI`** (nell'ordine del funnel: DDT dopo ORDINI; RESI in coda) |
| `DASH_FATTURAZIONE_AREE_EURO` | `PREVENTIVI, ORDINI, COMMESSE` | **+ `DDT`** (ha importi). **NO `RESI`** → conteggi, DL-24 |
| `DASH_APERTO_AREE` | `PREVENTIVI, ORDINI, OFFERTE, CONTRATTI` | **+ `DDT`** (5 aree). **NO `RESI`** (DL-24: REVERSE_FLOW, non serbatoio) |

Aggiornare anche i commenti sopra le costanti: dicono "le 4 aree documento" e "Usate dalla
Lente 2 Backlog (che include COMMESSE)".

### BE-2 — Coda accrediti (`db/resi_repository.py`, `services/resi_service.py`)

`vw_resi_da_accreditare` **cambia popolazione e forma** (brief DB §3c, DL-27). Breaking secco,
nessun doppio binario:

- **Popolazione** = differenza **negativa** del contatore (`fatturati − tenuti > 0`), qualunque
  tipo di reso — non più il filtro `riapre_residuo = false`. Chi ha differenza ≤ 0 esce.
- ⚠️ **La coda ora espone una QUANTITÀ** — l'accredito dovuto (`fatturati − tenuti`) — non solo
  l'elenco delle righe. È una colonna in più nel contratto API, **e la slice NC ci si
  appoggerà**: va esposta nel payload con nome stabile, non trattata come dettaglio di lista.
- **Il tipo di reso resta come ETICHETTA** dovuta/facoltativa (a credito = dovuta, per
  ri-consegna = facoltativa), non come criterio di popolamento.
- Adeguare la SELECT e la config lista (`vendite.resi_da_accreditare`, id 10) alle colonne
  nuove (le colonne esatte arrivano dal team DB — §5).
- ❓ **Filtro dovuta/facoltativa**: raccomandazione **colonna + filtro opzionale** whitelisted —
  l'operatore lavora le dovute, ma deve poter vedere le facoltative per esercitare la scelta
  DL-26 (che vive proprio su questa coda, fino alla ri-spedizione).
- Test: la popolazione cambia → gli assert sulla vecchia regola per tipo **vanno riscritti,
  non ritoccati**.

### BE-3 — Gate solo-trasporto (DL-28): `error_policies.py`

Il DB introduce un **blocco all'emissione** del DDT: causale fatturabile + almeno una riga
attiva senza prezzo **risolvibile** → errore parlante (codice nuovo, comunicato dal team DB).

- Registrare la policy in `core/services/error_policies.py` (409, `show_error_banner` —
  famiglia `E_DDT_*`).
- **Lookup causali: niente da fare** — verificato 2026-07-17: `config.causali_trasporto` è già
  nella whitelist lookup BE (`dbops_repository.py`) e già registrata in `core/config-tables.js`
  FE. La colonna `fatturabile` viaggia da sola nel lookup generico.

### BE-4 — Cosa NON cambia (per non cercarlo)

- `dashboard-aperto` / `dashboard-backlog`: endpoint, envelope, paginazione, ordinamento,
  filtri classe/fase → **invariati**. Il resolver DDT entra dalla union, il BE è passthrough.
- **Ordine al residuo (DL-23 emendato)** e **popolazione DDT (DL-21 emendato)**: li fanno le
  **viste**. Il BE non calcola nulla e non filtra nulla.
- **Nessuna esposizione "riga DDT non fatturabile"**: il punto è **superato** dalla
  rifondazione a contatore (brief DB §8) — la ri-consegna è derivata, niente colonna, niente
  da esporre.
- Nessun endpoint nuovo.

### BE-5 — Test

- `test_dashboard_backlog_*`: `?area=DDT` e `?area=RESI` **non danno più 400** e inoltrano al
  repo (è la regressione che BE-1 previene).
- `test_dashboard_aperto_*`: `DDT` nel vocabolario aree del riepilogo, `RESI` **assente**.
- Misura: `DDT` con `valore_totale` valorizzato, `RESI` con `valore_fermo` **null** (mai 0).
- Coda accrediti: quantità accredito dovuto nel payload, etichetta dovuta/facoltativa.

## 3. Frontend

### FE-1 — `vendite/dashboardAree.js` (il file che le due lenti condividono)

Estratto il 2026-07-06 proprio per evitare il drift su nuova area — **è qui che si aggiunge**,
non nelle view:

```js
DDT:   { route: '/vendite/ddt',   severity: statoDdtSeverity  }   // dopo ORDINI
RESI:  { route: '/vendite/resi',  severity: statoResoSeverity }   // in coda
```

Entrambe le funzioni severity **esistono già** (`core/utils/severity.js`: `statoDdtSeverity`,
`statoResoSeverity`) — niente da scrivere. L'ordine delle chiavi è l'ordine funnel e **deve
restare allineato a `DASH_FATTURAZIONE_AREE`** (lo dice il commento del file).

`buildApriDocumentoAction` funziona da sé per entrambe (rotte esistenti, ricerca universale
`?search=`).

### FE-2 — i18n (`dash_comune`, it + en)

- Aree: `area_ddt`, `area_resi`
- Motivi (`motivo_fermo.*`): `IN_ATTESA_DDT`, `IN_TRANSITO`, `RICONSEGNA_NON_ESEGUITA`,
  **`MERCE_RESA_GIA_FATTURATA`** (⚠️ non `NC_DOVUTA`: rinominato in DL-24 emendato — il motivo
  nomina il *fatto*, non il rimedio, perché le NC non sono ancora definite) + le rispettive
  azioni suggerite
- Senza queste chiavi non si rompe nulla (`labelOrCode` mostra il codice grezzo) — ma è
  esattamente il "comparire male" del §1.

### FE-3 — Situazione aperta: la card Ordini diventa MISTA (DL-23 emendato)

⚠️ Non è un ritocco di etichetta, ed è **cambiato rispetto alla prima stesura di questo
brief**: la misura netta ("valore ancora da spedire") vale **solo per gli ordini il cui
veicolo di billing è il DDT** (`trigger ∈ {SPEDITO, CONSEGNATO}`); gli ordini con
`trigger = CONFERMATO` — la configurazione di **default** — restano al **valore pieno**
(fatturano alla conferma: non c'è doppio conteggio da evitare, e la misura netta li
mostrerebbe a 0 € creando un nuovo buco cieco).

Conseguenza FE: la card Ordini è una **somma mista** (pieno per i CONFERMATO + da-spedire per
gli altri). Il calcolo è tutto DB-side; al FE resta l'onestà dell'etichetta/tooltip — non
promettere né "valore dell'aperto" né "da spedire" secchi. Proposta: tooltip che spiega la
regola in una riga («ordini a fatturazione su consegna: conta solo il non spedito»). La guida
(Fase 4) lo recepisce.

Nota parallela per la guida, nessun lavoro FE: la **card DDT** mostra solo i DDT **con ruolo
di fatturazione** (DL-21 emendato — esclusi gli order-backed di ordini CONFERMATO e i
solo-trasporto): un DDT visibile nella lista DDT può legittimamente non comparire nei
cruscotti.

Per il resto la view è zero-touch: la card DDT compare dal riepilogo, il donut per fase la
disegna da sé.

### FE-4 — Coda accrediti (`vendite/resi/components/ResiCodaTable.vue`)

Segue BE-2: colonne nuove, tra cui la **quantità dell'accredito dovuto** (è l'informazione
centrale della coda: «fatturata per 10, tenuta 7» → accredito 3) e la **distinzione visiva
dovuta/facoltativa** (le facoltative non sono arretrato: sono un'opzione dell'operatore,
DL-26). Il componente è già su `usePagedDashFetch` con `loaded`/empty-state onesto → si tocca
solo il contenuto.

**Nessuna azione "emetti NC"**: non esiste il ramo NC. Non predisporre UI morta.

### FE-5 — Drawer DDT: gate solo-trasporto (DL-28)

- Il **nuovo errore all'emissione** («righe senza prezzo su causale fatturabile») arriva dal
  DB via `cambia-stato`/`emetti` → messaggio i18n mappato sulla policy di BE-3, resa standard
  a banner. Nessuna logica FE che replichi il gate ([[feedback_bug_logici_modello]] non si
  applica: la fonte è il DB, il FE mostra).
- **Causale obbligatoria all'emissione**: se il team DB conferma l'obbligo (raccomandato nel
  brief DB), segnare il campo causale nel `DdtForm` come richiesto-per-emissione (asterisco /
  hint), senza guard FE duro — il fail-fast resta al DB.

### FE-6 — Backlog: zero-touch

Card, filtri classe/area, drill-down, kebab: tutto data-driven. Con FE-1 + FE-2 le due aree
nuove funzionano. La grana (reso × motivo) non richiede nulla (§1).

## 4. Cosa aspetta risposte dal team DB (brief DB §8)

Da chiudere prima di partire, non da indovinare:

1. Le colonne finali di `vw_resi_da_accreditare` — in particolare **il nome della colonna
   quantità** (accredito dovuto) e come è espressa l'etichetta dovuta/facoltativa → BE-2, FE-4.
2. Il **codice del nuovo errore** del gate solo-trasporto + la conferma dell'obbligo causale
   all'emissione → BE-3, FE-5.
3. Eventuali altri codici errore → `error_policies.py`.

~~La forma di "questa riga DDT non fattura"~~ — **superato** (brief DB §8): nessuna colonna,
la ri-consegna è derivata dal contatore.

## 5. Fuori perimetro

- **Lente 1 (Competenza)**: invariata (decisione Tid).
- **Emissione nota di credito**: slice NC. Qui solo la coda che la alimenta (che però già
  espone la quantità su cui la NC si appoggerà — BE-2).
- **`vw_stato_sorgente_ddt`/`_reso`** (brief DB step 6b): proiezione DB consumata da
  `pratiche.fn_stato_sorgente` — nessun lavoro BE/FE in questa slice.
- **Guida utente**: Fase 4 del design doc (recepirà FE-3, card mista e popolazione DDT).

## 6. Avanzamento

| # | Step | Stato |
| --- | --- | --- |
| 1 | BE-1 — whitelist aree (`DASH_FATTURAZIONE_AREE` +DDT+RESI · `_EURO` +DDT · `DASH_APERTO_AREE` +DDT) + commenti | ✅ 2026-07-18 |
| 2 | FE-1 — `dashboardAree.js`: DDT + RESI (severity già esistenti) | ✅ 2026-07-18 |
| 3 | FE-2 — i18n `dash_comune`: 2 aree + 4 motivi (`MERCE_RESA_GIA_FATTURATA`, non `NC_DOVUTA`), it+en | ✅ 2026-07-18 |
| 4 | FE-3 — card Ordini: hint tooltip per la misura **mista** (netta solo su trigger S/C) — icona ⓘ + `card_ordini_hint`, CSS `app-dash-card-hint` | ✅ 2026-07-18 |
| 5 | BE-2 + FE-4 — coda accrediti: order_cols nuove + filtro `etichetta` whitelisted (repo/service/view+export) · FE slot `accredito_dovuto`/`etichetta` Tag/`tenuti`/`fatturati`/`ddt_numero` "—" + Select etichetta + store/export · `etichettaAccreditoSeverity` | ✅ 2026-07-18 — seed lista 10 **applicato dal team DB 2026-07-19** (+ preset per le 3 liste resi, deviazione motivata nel [mini-brief](../work-done/brief-db-seed-lista-coda-accrediti-contatore.md)); i18n `col_*` create e config verificata end-to-end live |
| 6 | BE-3 + FE-5 — gate solo-trasporto: policy 544/545 in `error_policies.py` (messaggio dal DB via translator) + asterisco-tooltip causale nel `DdtForm` (obbligatoria all'emissione, non al create) | ✅ 2026-07-18 |
| 7 | BE-5 — test: aperto 5 aree (DDT euro, RESI assente), backlog DDT/RESI validi (anti-regressione 400), coda etichetta (passthrough/whitelist/default) — 100 test moduli toccati | ✅ 2026-07-18 |
| 8 | Suite `apps.vendite` + `apps.core` **1782 verdi**, build FE ok, lint pulito, `kill -HUP` gunicorn, doc api (aperto/backlog/resi) | ✅ 2026-07-18 |
| 9 | Validazione in-app Tid | ☐ **in corso** — vedi §6-bis: 3 rilievi emersi e già chiusi |

### 6-bis. Rilievi emersi durante la validazione (2026-07-19/20) — tutti chiusi

La validazione ha già prodotto e chiuso tre difetti collaterali; il giro
complessivo resta da completare:

1. **Reason push DDT falsa (catch-all)** — su DDT0000326/ORD0000580 il banner
   diceva «dev'essere spedito o consegnato» a DDT già consegnato. Brief dedicato
   **chiuso end-to-end** (DB fonte unica `fn_ddt_push_diagnosi` + capability,
   FE tooltip su pulsante disabilitato):
   [brief-db-ddt-reason-push-catch-all.md](../work-done/brief-db-ddt-reason-push-catch-all.md).
   Rivalidato in-app su ORD0000608/DDT0000337 (2026-07-20).
2. **Readonly-leak nei drawer impilati dai «Passaggi»** — un ordine aperto dal
   pannello lineage di un DDT post-DRAFT ereditava il lock-di-stato del DDT e
   perdeva TUTTE le azioni (incluso «Invia a commessa» legittimo). Fix:
   `LineagePassaggiPanel` resetta `READONLY_KEY` fornendo ai drawer impilati il
   readonly PURO del chiamante (permessi area sì, lock del padre no); cablati i
   7 embed (ordini/ddt/preventivi/offerte/contratti/resi/commessa). Copre anche
   il `PraticaDrawer` aperto dallo stesso pannello.
3. **Liste stantie al rientro (KeepAlive)** — lo stato ordine cambiato come
   effetto collaterale (evasione da DDT → EVASO) non compariva rientrando nella
   lista cachata: refresh solo su `saved` del proprio drawer. Fix in
   `useSearchTable.onActivated` (vale per TUTTE le liste): refetch idempotente
   della pagina corrente alla ri-attivazione (filtri/offset invariati, skip al
   primo mount, guard `hasSearched`/`loading`) — pattern
   [[feedback_keepalive_onactivated]] applicato alla freshness.

⚠️ Nota per il seguito della validazione: **tutti i 42 BA di dev hanno
`fatturazione_ordini = CONFERMATO`** — il percorso push-da-DDT (reason
`merce_in_viaggio`, `gia_inviato` da DDT) non è esercitabile finché non si
imposta un BA di prova a `SPEDITO`/`CONSEGNATO` e si crea un ordine NUOVO per
quel BA (il trigger si eredita alla creazione).

## 7. Consuntivo (2026-07-18) — realizzato, non committato

File toccati — **BE**: `db/vendite_repository.py` (whitelist 7/4+DDT/5 aree),
`db/resi_repository.py` (order_cols contatore + filtro `etichetta` in `_list_coda`),
`services/resi_service.py` (whitelist etichetta via `validate_enum_param`),
`api/views_resi.py` (query param `etichetta` list+export, `qp_str_upper`),
`core/services/error_policies.py` (544/545). **FE**: `vendite/dashboardAree.js`
(DDT+RESI), `core/utils/severity.js` (`etichettaAccreditoSeverity`),
`vendite/views/SituazioneApertaView.vue` (hint card Ordini), `assets/main.css`
(`app-dash-card-hint`), `vendite/resi/stores/resiCoda.js` (+`etichetta`),
`vendite/resi/components/ResiCodaTable.vue` (Select + 5 slot),
`vendite/ddt/components/DdtForm.vue` (asterisco causale), `locales/it+en.json`.
**Test**: aperto (rinominato `test_cinque_aree…` + DDT euro + indice extra),
backlog (`test_documenti_aree_ddt_resi_valide`), resi service
(`ResiCodaAccreditareTests`, 3 test) + api (etichetta propagata upper).
**Doc**: `api_dashboard_aperto.md` (5 aree, misura mista ordini),
`api_dashboard_backlog.md` (7 aree, rami resi), `api_resi.md` (coda forma
contatore + filtro etichetta). Zero-touch confermati: Backlog view, donut,
riepiloghi (aree accodate data-driven).

**Review critica 2026-07-18 (8 finder, 10 fix applicati)**: parità list/export
della coda per costruzione (`_extract_accredito_filters` unico + etichetta nel
blocco "filtri applicati" dell'export + OpenAPI export); builder `_list_coda`
reso neutro (condizioni vista-specifiche dal wrapper, via lo special-case
etichetta); Tag etichetta fail-visible (`labelOrCode`) + vocabolario
`ETICHETTA_ACCREDITO` in `resi/constants.js`; store riconsegne senza filtro
no-op (factory con `extraFilters`); hint card per-area in `DASH_AREA_CONFIG`
(`apertoHintKey`) + icona accessibile (focus/aria-label); asterisco causale
solo a campo editabile; descrizioni OpenAPI/commenti "4 aree" allineati in 4
file BE; `subTest` nei loop test. **Su segnalazione Tid**: `_list_coda` a
**UNA valutazione** della vista per pagina (`COUNT(*) OVER()` con fallback
COUNT solo su pagina-oltre-l'ultima — le code si auto-svuotano, il caso è
reale); SQL validato live su entrambe le viste. 1782 test verdi. ⚠️ Candidata
regola del 2 dichiarata, in attesa di ok: il pattern paginazione-una-valutazione
ora vive in 2 forme (`_query_paged_view` con clamp SQL nei cruscotti · COUNT
OVER con fallback in core/email/dbops e qui) — unificabile in BB core come
task dedicato. → **ESTRATTA (ok Tid, 2026-07-18)**: BB core in
`apps/core/db/_helpers.py` — `extract_paginated` (promosso da anagrafiche, 6
repo ripuntati al core), `fetch_paged_with_total` (una valutazione + fallback
pagina-stantia; adottato da `_list_coda` resi), `query_paged_view` (variante
clamp promossa da `VenditeRepository._query_paged_view`, che resta delegatore
per aperto/backlog/errori). Catalogo BB aggiornato con la distinzione di
semantica (pagina richiesta vs pagina effettiva) e la nota sui ~15 siti
inline storici core/amm adottabili come allineamento dedicato. Validazione
live dei tre percorsi + suite vendite/core/anagrafiche (2 flaky preesistenti
in `test_soggetti_export_api`, ordine-dipendenti da throttle: falliscono
identici anche senza il diff — controprova stash).
