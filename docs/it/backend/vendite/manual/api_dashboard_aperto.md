# API Situazione aperta (Django)

## Scopo

Espone la Situazione aperta dei cruscotti fatturazione: riepilogo dello stock
di documenti per `area × fase` normalizzata (senza asse temporale) e lista
paginata dei documenti, ordinata per "in essere da" (i più vecchi prima).

## Contesto

Fase 3 BE del brief
[brief-design-fatturazione-due-lenti](../../../dev/work-in-progress/brief-design-fatturazione-due-lenti.md)
§6-bis (substrato DB in
[brief-db-situazione-aperta](../../../dev/work-done/brief-db-situazione-aperta.md),
migrations `20260707-03..06`): due endpoint GET **sottili** sopra le
proiezioni read-only `vendite.vw_dash_aperto_riepilogo` (celle `area × fase`)
e `vendite.vw_dash_aperto_documenti` (union dei resolver, 4 aree documento,
`NOT is_abortito`, **tutte le fasi** — DL-13: perimetro unico di card e
drill-down, il BE non replica filtri). Sostituisce i 2 endpoint
`dashboard-fatturazione/{,fermi/}` della 5-card (asse mensile dismesso).
Nessuna logica di dominio in Python: popolazione, `fase` (da
`config.stati_doc_*`), `is_aperto` (`is_transitato IS DISTINCT FROM true`: il
giudizio **sospeso** dei contratti conta aperto, DL-12) vivono nelle viste.
Livello area `LETTURA` sufficiente; nessuna azione di processo.

```text
GET /api/v1/vendite/dashboard-aperto/            (ApiDashboardAperto)
GET /api/v1/vendite/dashboard-aperto/documenti/  (ApiDashboardApertoDocumenti)
```

Catena: view (`views_dashboard_aperto.py`) →
`vendite_service.fn_dash_aperto_{riepilogo,documenti}` →
`VenditeRepository.list_dash_aperto_{riepilogo,documenti}`.

## Input

### `GET /dashboard-aperto/`

Nessun parametro.

### `GET /dashboard-aperto/documenti/`

- `area` (opzionale, case-insensitive; assente = tutte): `PREVENTIVI |
  ORDINI | OFFERTE | CONTRATTI`. **Non whitellistato di proposito** (coerenza
  fail-visible col riepilogo, che accoda le aree fuori whitelist e le rende
  card cliccabili): un'area futura resta drillabile senza toccare il BE;
  un'area sconosciuta — o `COMMESSE`, esclusa dal WHERE della vista (coperta
  dalla Lente 1) — dà lista vuota, mai 400.
- `fase` (opzionale, case-insensitive; assente = tutte): vocabolario
  `config.stati_doc_*.fase` (`APERTO | IN_ATTESA | IN_CORSO | CHIUSO`).
  **Non whitellistato di proposito** (coerenza fail-visible col riepilogo, che
  accoda le fasi fuori whitelist): una fase futura resta drillabile senza
  toccare il BE; una fase sconosciuta dà lista vuota, mai 400.
- `solo_aperti` (opzionale, default `true`): solo documenti non completamente
  transitati (`is_aperto`). `false` = fotografia completa dello stock
  (inclusi i transitati/chiusi). **Strict**: un token non riconosciuto dà 400
  (`qp_bool_optional`, niente coercion silenziosa a true).
- `page` / `page_size` (opzionali): paginazione standard (default 1/50, max 200).

## Output

### Riepilogo

```json
{
  "data": {
    "aree": [
      { "area": "PREVENTIVI", "n_documenti": 5, "n_aperti": 4,
        "valore_totale": "2000.50", "valore_transitato": "300.00",
        "fasi": [
          { "fase": "APERTO", "n_documenti": 3, "n_aperti": 3,
            "valore_totale": "1500.00", "valore_transitato": "0" }
        ] }
    ],
    "fasi": ["APERTO", "IN_ATTESA", "IN_CORSO", "CHIUSO"]
  }
}
```

- **4 aree sempre presenti** nell'ordine del funnel (`PREVENTIVI, ORDINI,
  OFFERTE, CONTRATTI`), ognuna con la **griglia delle 4 fasi sempre presenti**
  nell'ordine del ciclo di vita (`APERTO, IN_ATTESA, IN_CORSO, CHIUSO`) e zeri
  espliciti — DL-13: la griglia è neutra, il FE decide quali card mostrare.
  Aree o fasi **fuori whitelist** emesse dalla vista vengono **accodate dopo le
  note**, mai perse in silenzio; il vocabolario `fasi` top-level alimenta i
  filtri FE (nessuna copia FE, nessun contrabbando dalla griglia di un'area);
  un'area extra che porta **valori** li espone (decisione data-driven, non la
  whitelist euro statica).
- Totali per area = somma delle fasi (su Decimal). Misura mista (DL-11,
  conferma D-2/D-3/D-4): aree euro (`PREVENTIVI`/`ORDINI`) con
  `valore_totale`/`valore_transitato` come stringa (`"0"` se vuote); aree a
  conteggi (`OFFERTE`/`CONTRATTI`) con valori `null`. Il valore residuo aperto
  è `valore_totale − valore_transitato` (i documenti completamente transitati
  contribuiscono 0).

### Lista documenti

Envelope paginato standard (`count/page/page_size/total_pages/results`); ogni
riga: `area`, chiavi documento (`documento_id`, `documento_uid`, `codice`),
`cliente_display`, `fase`, `stato_codice_interno`, `stato_codice`,
`valore_totale`/`valore_transitato` (NULL per aree a conteggi),
`unita_totali`/`unita_transitate`, `is_transitato` (**NULL = giudizio
sospeso**, contratti fino al push ricorrente), `is_aperto`, `motivo_fermo`
(può essere NULL: qui è un hint, non il criterio di popolazione),
`data_riferimento` ("in essere da": data documento, `valido_dal` per i
contratti). **Ordinamento BE-side** (le viste non garantiscono ORDER):
`data_riferimento ASC NULLS LAST`, poi `valore_totale DESC NULLS LAST, area,
documento_id`.

## Regole

- **Popolazione = stock documenti vivi** (§6-bis): union 4 aree documento,
  esclusi gli abortiti (`NOT is_abortito` — l'esclusione D-6 vive nella vista
  stock: i resolver non-contratti *marcano* soltanto), **tutte le fasi**
  incluse le 🟢 fisiologiche che il Backlog esclude. Complementare alle due
  lenti: Lente 1 = mese di competenza, Lente 2 = lavoro da sbloccare,
  Situazione aperta = fotografia della pipeline.
- **Contratti = consistenza pura** (DL-12): resolver de-esploso (1 riga per
  contratto vivo), giudizio di transito sospeso (`is_transitato`/`motivo_fermo`
  NULL) finché non esiste il push ricorrente — un contratto conta sempre
  aperto, mai "fermo" (falso-allarme perenne evitato).
- **Anti-drift fail-visible**: fasi/aree sconosciute accodate nel riepilogo e
  **passthrough su entrambi i filtri** `area`/`fase` del drill-down (mai 400,
  mai perse: la card accodata resta drillabile).
- **Scope emittente — interamente DB-side**: RLS invoker sulle 4 aree
  documento (fix V-1 `20260706-15`; il `security_invoker` perso dal resolver
  contratti col `20260707-03` è stato **ripristinato e verificato** — brief DB
  §5, con guard pgTAP su `pg_class.reloptions`). Il BE **non** passa alcun
  `auth_user_id`.
- Una **sola valutazione della union** per pagina (`_query_paged_view`: CTE
  materializzata + `COUNT(*) OVER()` + **offset clampato all'ultima pagina in
  SQL**). Il rientro da una pagina stantia (lista ridotta da altri utenti) non
  costa più un secondo giro: il BE serve subito l'ultima pagina reale e
  l'envelope dichiara la **pagina effettiva**, che `usePagedDashFetch` adotta.
- GET-only, nessun side-effect, nessuna Idempotency-Key.

## Dipendenze DB

- `vendite.vw_dash_aperto_documenti` — doc:
  `docs/it/dbzero/vendite/manual/vw_dash_aperto_documenti.md`
- `vendite.vw_dash_aperto_riepilogo` — doc:
  `docs/it/dbzero/vendite/manual/vw_dash_aperto_riepilogo.md`
- `vendite.vw_dash_fatturazione_contratti` de-esploso (migration `20260707-03`)
- `vendite.vw_dash_fatturazione_mensile` **dismessa** (migration `20260707-06`)

## Note di migrazione

- Sostituisce `api_dashboard_fatturazione.md` (endpoint
  `dashboard-fatturazione/{,fermi/}` ritirati insieme a
  `views_dashboard_fatturazione.py`, `fn_dash_fatturazione_*`,
  `list_dash_fatturazione_*` e relativi test).
- Substrato DB applicato con migrations `20260707-03..06` (pgTAP
  `test-vw-dash-aperto-v1.sql` plan 10 + `test-vw-dash-fatturazione-v1.sql`
  rimaneggiato plan 28, verdi).
- Test: `apps/vendite/tests/api/test_dashboard_aperto_api.py` (9 casi) +
  `apps/vendite/tests/services/test_dashboard_aperto_service.py` (12 casi),
  tutti con mock (CI-safe).
- FE (Fase 3): rotta `/vendite/situazione-aperta` (`SituazioneApertaView.vue`,
  store `dashboardAperto.js`, severity `faseDocumentoSeverity`); vocabolari
  i18n `motivo_fermo`/`area_*`/`fase_*` ricollocati nel gruppo condiviso
  `dash_comune` (riusato dal Backlog).
