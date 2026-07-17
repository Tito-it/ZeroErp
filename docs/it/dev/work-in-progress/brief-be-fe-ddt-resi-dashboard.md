# Brief BE/FE — DDT e resi nelle lenti + coda accrediti sui fatti

> **Tipo**: brief operativo BE/FE · **Target**: `dev/backend-tid` · **Data**: 2026-07-16 · **Owner**: Tid
> **Stato**: ☐ DA REALIZZARE — **spec scritta a DB non ancora applicato**
> **Design-of-record**: [brief-design-fatturazione-due-lenti.md](brief-design-fatturazione-due-lenti.md)
> §6-quater, decisioni **DL-19..26**.
> **Prerequisito DB**: [brief-db-fatturazione-ddt-resi.md](brief-db-fatturazione-ddt-resi.md).
> **Gate**: BE/FE partono a **oggetti DB applicati** ([[feedback_be_fe_attende_prerequisiti_db]]).
> **Contesto**: non siamo in produzione ([[project_no_produzione_solo_sviluppo]]) → breaking
> secchi, nessuna compat.
> **Parte da**: le tre viste vive e committate (Lente 1 Competenza, Lente 2 Backlog,
> Situazione aperta v2 — `6daf0a65d` + `8887f4113`).

---

## 0. Scopo in una riga

Far comparire **DDT** e **RESI** nelle due lenti a monte e adeguare la **coda accrediti** alla
sua nuova popolazione (righe la cui merce è già fatturata, di qualunque tipo — non più "le
righe a credito").

## 1. La buona notizia: quasi tutto è zero-touch

Il grosso del lavoro è **DB**. Le lenti sono già data-driven e fail-visible: il riepilogo
accoda le aree sconosciute invece di dare 400, la misura euro/conteggi la decide il BE nel
payload (`valore_* = null` → area a conteggi, DL-11) e il FE **legge, non ri-decide**, i motivi
si decodificano con `labelOrCode` (fallback al codice grezzo). Quindi **niente lavoro
strutturale**: le card nuove comparirebbero da sole.

Ma da sole comparirebbero **male**, e sono queste le uniche cose che vanno toccate davvero:
fuori ordine di funnel, senza etichetta tradotta e — la sola vera rottura — **non
drillabili**.

## 2. Backend

### BE-1 — Whitelist aree: il punto che romperebbe (`db/vendite_repository.py`)

⚠️ **Il filtro `area` del Backlog è fail-closed**, a differenza del filtro `classe` che fu
de-whitellistato apposta il 2026-07-06 (nota Fase 2 del design doc). Verificato nel codice:
`fn_dash_backlog_documenti` valida `area` con `allowed=DASH_FATTURAZIONE_AREE` →
**un'area non in whitelist dà 400**. Senza questo step le card DDT/RESI comparirebbero nel
riepilogo (fail-visible) ma il drill-down andrebbe in errore: **card che non si aprono**.

| Costante | Oggi | Diventa |
|---|---|---|
| `DASH_FATTURAZIONE_AREE` | `PREVENTIVI, ORDINI, OFFERTE, CONTRATTI, COMMESSE` | **+ `DDT`, + `RESI`** (nell'ordine del funnel: DDT dopo ORDINI; RESI in coda) |
| `DASH_FATTURAZIONE_AREE_EURO` | `PREVENTIVI, ORDINI, COMMESSE` | **+ `DDT`** (ha importi). **NO `RESI`** → conteggi, DL-24 |
| `DASH_APERTO_AREE` | `PREVENTIVI, ORDINI, OFFERTE, CONTRATTI` | **+ `DDT`** (5 aree). **NO `RESI`** (DL-24: REVERSE_FLOW, non serbatoio) |

Aggiornare anche i commenti sopra le costanti: dicono "le 4 aree documento" e "Usate dalla
Lente 2 Backlog (che include COMMESSE)".

### BE-2 — Coda accrediti (`db/resi_repository.py`, `services/resi_service.py`)

`vw_resi_da_accreditare` **cambia popolazione e forma** (brief DB §3c): non più
`riapre_residuo = false` ma *«la merce è già impegnata in fatturazione»*, **qualunque tipo di
reso**, con il distinguo **NC dovuta / NC facoltativa**. Breaking secco, nessun doppio binario.

- Adeguare la SELECT e la config lista (`vendite.resi_da_accreditare`, id 10) alle colonne
  nuove.
- **Esporre il distinguo dovuta/facoltativa** — la forma esatta arriva dal team DB (brief DB
  §8): se è una colonna, passthrough; se serve un filtro, aggiungerlo whitelisted.
- ❓ **Da decidere quando il DB risponde**: il filtro dovuta/facoltativa è un query-param o si
  rende solo come colonna? Raccomandazione: **colonna + filtro opzionale** (l'operatore lavora
  le dovute, ma deve poter vedere le facoltative per esercitare la scelta DL-26).
- Test: adeguare `test_resi_*`; la popolazione cambia → gli assert sulla vecchia regola per
  tipo **vanno riscritti, non ritoccati**.

### BE-3 — Cosa NON cambia (per non cercarlo)

- `dashboard-aperto` / `dashboard-backlog`: endpoint, envelope, paginazione, ordinamento,
  filtri classe/fase → **invariati**. Il resolver DDT entra dalla union, il BE è passthrough.
- **Ordine al residuo (DL-23)**: lo fa la **vista**. Il BE non calcola nulla.
- Nessun endpoint nuovo.

### BE-4 — Test

- `test_dashboard_backlog_*`: `?area=DDT` e `?area=RESI` **non danno più 400** e inoltrano al
  repo (è la regressione che BE-1 previene).
- `test_dashboard_aperto_*`: `DDT` nel vocabolario aree del riepilogo, `RESI` **assente**.
- Misura: `DDT` con `valore_totale` valorizzato, `RESI` con `valore_fermo` **null** (mai 0).

## 3. Frontend

### FE-1 — `vendite/dashboardAree.js` (il file che le due lenti condividono)

Estratto il 2026-07-06 proprio per evitare il drift su nuova area — **è qui che si aggiunge**,
non nelle view:

```
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
  `NC_DOVUTA` + le rispettive azioni suggerite
- Senza queste chiavi non si rompe nulla (`labelOrCode` mostra il codice grezzo) — ma è
  esattamente il "comparire male" del §1.

### FE-3 — Situazione aperta: la card Ordini cambia significato (DL-23)

⚠️ Non è un ritocco di etichetta: **è un cambio di semantica**. La card Ordini passa da
*"valore dell'aperto"* a **"valore ancora da spedire"**, ed è l'**unica area con misura
netta** (le altre restano lorde). Va detto nell'etichetta/tooltip, altrimenti l'utente legge
un numero più basso di ieri senza sapere perché. La guida (Fase 4) lo recepisce.

Per il resto la view è zero-touch: la card DDT compare dal riepilogo, il donut per fase la
disegna da sé.

### FE-4 — Coda accrediti (`vendite/resi/components/ResiCodaTable.vue`)

Segue BE-2: colonne nuove e **distinzione visiva dovuta/facoltativa** (le facoltative non sono
arretrato: sono un'opzione dell'operatore, DL-26). Il componente è già su
`usePagedDashFetch` con `loaded`/empty-state onesto → si tocca solo il contenuto.

**Nessuna azione "emetti NC"**: non esiste il ramo NC. Non predisporre UI morta.

### FE-5 — Backlog: zero-touch

Card, filtri classe/area, drill-down, kebab: tutto data-driven. Con FE-1 + FE-2 le due aree
nuove funzionano.

## 4. Cosa aspetta risposte dal team DB (brief DB §8)

Da chiudere prima di partire, non da indovinare:

1. La forma di *"questa riga DDT non fattura"* (colonna vs predicato) — se è colonna, il BE la
   espone nel dettaglio DDT.
2. Le colonne finali di `vw_resi_da_accreditare` e **come** è espresso il distinguo
   dovuta/facoltativa → BE-2, FE-4.
3. Eventuali nuovi codici errore → `error_policies.py`.

## 5. Fuori perimetro

- **Lente 1 (Competenza)**: invariata (decisione Tid).
- **Emissione nota di credito**: slice NC. Qui solo la coda che la alimenta.
- **Guida utente**: Fase 4 del design doc (recepirà FE-3).

## 6. Avanzamento

| # | Step | Stato |
|---|---|---|
| 1 | BE-1 — whitelist aree (`DASH_FATTURAZIONE_AREE` +DDT+RESI · `_EURO` +DDT · `DASH_APERTO_AREE` +DDT) + commenti | ☐ |
| 2 | FE-1 — `dashboardAree.js`: DDT + RESI (severity già esistenti) | ☐ |
| 3 | FE-2 — i18n `dash_comune`: 2 aree + 4 motivi, it+en | ☐ |
| 4 | FE-3 — card Ordini: etichetta/tooltip "ancora da spedire" (misura netta) | ☐ |
| 5 | BE-2 + FE-4 — coda accrediti alla nuova popolazione + distinguo dovuta/facoltativa | ☐ |
| 6 | BE-4 — test (drill-down DDT/RESI senza 400, RESI fuori dal serbatoio, misura a conteggi) | ☐ |
| 7 | Suite `apps.vendite` + `apps.core` verde, build FE, `kill -HUP` gunicorn ([[project_backend_gunicorn_reload]]) | ☐ |
| 8 | Validazione in-app Tid | ☐ |
