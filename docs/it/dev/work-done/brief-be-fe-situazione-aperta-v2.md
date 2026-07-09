# Brief BE/FE — Situazione aperta v2: serbatoio pre-commessa (donut per fase + filtro ritardo)

> **Tipo**: brief operativo BE/FE (`dev/backend-tid`) · **Data**: 2026-07-08 · **Owner**: Tid
> **Design-of-record**: [brief-design-fatturazione-due-lenti.md](../work-in-progress/brief-design-fatturazione-due-lenti.md)
> §6-ter (DL-14..18). **Prerequisito DB**:
> [brief-db-situazione-aperta-v2.md](brief-db-situazione-aperta-v2.md) — viste ristrette agli
> aperti-non-chiusi + drop colonne transitato. **Gate**: BE/FE partono a **viste v2 applicate**
> (memoria `feedback_be_fe_attende_prerequisiti_db`). Parte da ciò che PR #938 ha già consegnato
> (endpoint `dashboard-aperto/{,documenti/}`, `SituazioneApertaView`, store `dashboardAperto`).

---

## 0. Scopo in una riga

Trasformare la Situazione aperta v1 (stock per fase con misura *transitato* + toggle
`solo_aperti`) nel **serbatoio pre-commessa v2**: card con **donut a spicchi per fase** dei soli
aperti-non-chiusi, drill-down con filtro **"aperti da oltre N giorni"** (solo lista), **via** il
concetto transitato e il toggle solo_aperti.

## 1. Backend (`apps/vendite`)

### BE-1 — Costanti/tipi

- `DASH_APERTO_FASI`: da 4 a **3** fasi (rimuovere `CHIUSO`): `('APERTO','IN_ATTESA','IN_CORSO')`.
  L'ordine è la *maturità verso la commessa* (bozza → cliente → da lavorare).
- `DashApertoRiepilogoRow`: rimuovere `n_aperti`, `valore_transitato`. Restano `area, fase,
  n_documenti, valore_totale`.
- `DashApertoDocumentoRow`: rimuovere `is_transitato`, `is_aperto`, `valore_transitato`,
  `unita_transitate`. Aggiungere `anzianita_giorni` (derivata BE da `data_riferimento`, come il
  Backlog: `GREATEST((current_date - data_riferimento), 0)`).

### BE-2 — Repository (`vendite_repository.py`)

- `list_dash_aperto_riepilogo`: adegua la SELECT alle colonne v2 (via transitato/n_aperti).
- `list_dash_aperto_documenti`: **rimuovere il parametro `solo_aperti`** (il perimetro è nella
  vista). **Aggiungere `ritardo_giorni: int | None`**: se valorizzato, `WHERE d.data_riferimento
  <= current_date - make_interval(days => %s)` (parametrizzato). Esporre `anzianita_giorni`
  (`GREATEST((current_date - d.data_riferimento), 0)` nella SELECT, come il gemello backlog).
  Continua a usare `_query_paged_view` (clamp offset + pagina effettiva — BB già estratto).

### BE-3 — Service (`vendite_service.py`)

- `fn_dash_aperto_riepilogo`: il pivot resta `area × fase` ma su **3 fasi** e senza
  `n_aperti`/`valore_transitato`. Il vocabolario `fasi` top-level resta (alimenta i filtri FE).
  Le aree/fasi extra fail-visible restano (anti-drift). `_cella_aperto_fields`: via i campi
  transitato.
- `fn_dash_aperto_documenti`: **via `solo_aperti`**; **dentro `ritardo_giorni`** (opzionale,
  intero > 0 — validare con `E_VENDITE_VALIDATION` se presente e non-positivo). Passa al repo.

### BE-4 — View (`views_dashboard_aperto.py`)

- Drill-down: **rimuovere** il query-param `solo_aperti` (+ `qp_bool_optional`). **Aggiungere**
  `ritardo_giorni` via `qp_int_optional` (strict: presente-ma-non-numerico → 400). Aggiornare
  `@extend_schema` (parametri + response senza campi transitato, + `anzianita_giorni`).

### BE-5 — Test

- `test_dashboard_aperto_service.py`: rimuovere gli assert su `n_aperti`/`valore_transitato`/
  `solo_aperti`; aggiungere: filtro `ritardo_giorni` inoltrato al repo, `ritardo_giorni` non
  positivo → `E_VENDITE_VALIDATION`, 3 fasi nel vocabolario, `anzianita_giorni` nel passthrough.
- `test_dashboard_aperto_api.py`: `?ritardo_giorni=60` inoltrato; via i test `solo_aperti`.
- Doc `api_dashboard_aperto.md`: riscrivere Output (colonne v2), Input (`ritardo_giorni`, via
  `solo_aperti`), Regole (perimetro serbatoio DL-15, card = fotografia / filtro solo-lista DL-17).

## 2. Frontend (`src/vendite`, `src/core`)

### FE-1 — Grafico: donut per fase (il pezzo più grosso)

`DonutTransito` è a **2 spicchi** (transitato vs fermo, con percentuale centrale) ed è cablato
sulla semantica binaria in ogni punto (props scalari `transitato`/`fermo`, palette a 2 var
`--app-chart-transitato/-fermo`, centro `pctTransitato`, `mode="fraction"` n/n). Ha un **secondo
consumatore vivo**: [DashboardCompetenzaView.vue](../../../../frontend/src/vendite/views/DashboardCompetenzaView.vue)
(Lente 1, copertura mese). La v2 serve invece un donut a **N spicchi = fasi** (2-3) con palette
`faseDocumentoSeverity` e **nessun rapporto a due vie** al centro (il centro % di DonutTransito non
si applica alle fasi).

**Decisione (regola del 2, dichiarata e approvata da Tid — strada (c)):** i due donut non
condividono la *semantica* ma il *substrato*, quindi si **estrae il substrato**, non si fondono i
significati (scartata (a): forka i rami + rischio Lente 1 in-place; scartata (b): copincolla ~30
righe della macchina palette/tema, la parte col footgun `<Chart>` destroy+reinit).

- **`DonutBase.vue`** (`core/components/charts/`) — possiede SOLO il substrato riusabile: wrapper
  chart.js via PrimeVue `<Chart>` doughnut, cache-palette module-level + `getComputedStyle`
  per-tema + watch dark/light, anello neutro "nessun dato", mini-legenda (dot+label+valore),
  **options statiche** (solo `data` reattivo → niente destroy+reinit). API: `segments:[{label,
  color, value, formatted}]`, `size`, slot `center`. Scopo strettamente su ciò che transitato+fasi
  già richiedono (no knob speculativi, no YAGNI).
- **`DonutTransito.vue`** — riscritto come skin sottile su `DonutBase` (2 segmenti + `%` al centro
  via slot). **API pubblica invariata 1:1** → i due caller (SituazioneAperta, Competenza) non
  cambiano una riga; ri-validare a video la card Competenza.
- **`DonutFasi.vue`** — skin su `DonutBase`: N segmenti-fase, colore da `faseDocumentoSeverity`,
  centro = totale (o vuoto).

Segmenti = le fasi con `n_documenti > 0` dell'area; valore = `valore_totale` per aree euro,
`n_documenti` per aree a conteggi (DL-11/16). Legenda con label fase (`dashFaseLabel`) + valore.

### FE-2 — View (`SituazioneApertaView.vue`)

- Card: sostituire `DonutTransito` (donut/fraction transitato) con il donut-per-fase. Rimuovere
  il calcolo `isEuro`/residuo/`vive`-senza-CHIUSO (non serve più: il perimetro BE è già
  aperti-non-chiusi; l'area euro/count si legge da `valore_totale !== null`). Le **chip per fase**
  diventano ridondanti col donut → valutare se toglierle o tenerle come dettaglio numerico.
- Toolbar lista: **rimuovere il toggle "Solo aperti"** (`ToggleSwitch`); **aggiungere** un
  `Select` "Aperti da oltre" con preset (es. Tutti / 30 / 60 / 90 gg) legato a `ritardoGiorni`.
- Colonna lista: `anzianita_giorni` ("aperto da N gg", tooltip su `data_riferimento`) al posto
  della sola data — allinea la lettura al filtro. Via eventuali colonne transitato.
- **Card = fotografia completa**: il filtro `ritardo_giorni` NON tocca `fetchRiepilogo` (DL-17),
  solo `fetchDocumenti`.

### FE-3 — Store (`stores/dashboardAperto.js`)

- Rimuovere `soloAperti` (+ dal `clearUserState` e dal return). Aggiungere `ritardoGiorni`
  (default null = tutti) nel `documentiFetch` params e nel `clearUserState`. Il cambio
  `ritardoGiorni` → `resetDocumenti()` + `fetchDocumenti()` (NON `fetchRiepilogo`).
- `fasi`/`aree` dal riepilogo invariati (via BB `useDashRiepilogo`).

### FE-4 — i18n (`dash_comune` + `situazione_aperta`, it+en)

- Rimuovere le chiavi legate al transitato/solo-aperti non più usate (`label_transitato`,
  `label_aperto`, `solo_aperti`, `n_aperti`). Aggiungere: `filtro_ritardo_label` ("Aperti da
  oltre"), preset (`ritardo_tutti`/`_30`/`_60`/`_90` o valori parametrici), `col_aperto_da`
  ("Aperto da"), eventuale titolo donut. Parità it/en (verifica automatica).

## 3. Invarianti / cosa NON cambia

- Perimetro **DB-side** (le viste v2 filtrano aperti-non-chiusi): il BE **non** ri-filtra il
  perimetro, aggiunge solo `ritardo_giorni` sul drill-down.
- Scope emittente interamente DB-side (RLS invoker): nessun `auth_user_id` dal BE.
- BB già estratti restano: `usePagedDashFetch` (clamp/pagina effettiva), `useDashRiepilogo`,
  `DashEmptyState`, `dashAreaLabel`/`dashFaseLabel`, `faseDocumentoSeverity`, `dashboardAree.js`.
- Distinzione dal Backlog (DL, §6-ter): resta netta — non toccare le viste/endpoint Backlog.

## 4. Verifica

- Suite `apps.vendite.tests` + `apps.core.tests` verde; build FE ok; `kill -HUP` gunicorn
  ([[project_backend_gunicorn_reload]]).
- Validazione in-app Tid: donut per fase leggibile, filtro "oltre N giorni" sulla sola lista,
  contratti ATTIVO presenti in IN_CORSO, un preventivo EVASO-con-riga-residua (chiuso-non-
  transitato) / un accettato-smistato (transitato-non-chiuso) **assenti** — vedi correzione
  §2 del brief DB v2 (l'"offerta superata" è NEGATIVO=abortita, esclusa a monte).

---

*A chiusura: `api_dashboard_aperto.md` + cataloghi BB (nuovo `DonutFasi` se strada (b)) +
questo brief in `work-done`. Poi **Fase 4 — guida utente**.*
