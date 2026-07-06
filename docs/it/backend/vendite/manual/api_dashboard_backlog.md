# API Dashboard Backlog — Lente 2 (Django)

## Scopo

Espone la Lente 2 Backlog dei cruscotti fatturazione a due lenti: contatori per
classe di azionabilità e lista paginata dei documenti non-collegati non-verdi,
ordinata per anzianità (i più vecchi prima).

## Contesto

Fase 2 BE del brief
[brief-design-fatturazione-due-lenti](../../../dev/work-in-progress/brief-design-fatturazione-due-lenti.md)
§5 (substrato DB in
[brief-db-fatturazione-due-lenti](../../../dev/work-in-progress/brief-db-fatturazione-due-lenti.md)
§5, migrations `20260706-01..15`): due endpoint GET **sottili** sopra le
proiezioni read-only `vendite.vw_dash_backlog_riepilogo` (contatori
classe × area) e `vendite.vw_dash_backlog_documenti` (union dei 5 resolver
filtrata al non-verde + LEFT JOIN `config.motivi_fermo`). Nessuna logica di
dominio in Python: popolazione, classi (mappatura statica `motivo_fermo →
classe`, DL-6/7), anzianità (`data_riferimento`, v1 proxy data documento) e
regola fail-visible (motivo non mappato ⇒ ANOMALIA) vivono nelle viste.
Livello area `LETTURA` sufficiente; nessuna azione di processo.

```text
GET /api/v1/vendite/dashboard-backlog/            (ApiDashboardBacklog)
GET /api/v1/vendite/dashboard-backlog/documenti/  (ApiDashboardBacklogDocumenti)
```

Catena: view (`views_dashboard_backlog.py`) →
`vendite_service.fn_dash_backlog_{riepilogo,documenti}` →
`VenditeRepository.list_dash_backlog_{riepilogo,documenti}`.

## Input

### `GET /dashboard-backlog/`

Nessun parametro.

### `GET /dashboard-backlog/documenti/`

- `classe` (opzionale, case-insensitive; assente = tutte): vocabolario del
  CHECK di `config.motivi_fermo` (`RECUPERABILE | SOLLECITO_CLIENTE |
  ANOMALIA`). **Non whitellistato di proposito** (coerenza fail-visible col
  riepilogo, che accoda le classi fuori whitelist): una classe futura resta
  drillabile senza toccare il BE; una classe sconosciuta (o `FISIOLOGICO`,
  escluso a monte dalla vista) dà lista vuota, mai 400.
- `area` (opzionale): `PREVENTIVI | ORDINI | OFFERTE | CONTRATTI | COMMESSE`
  (case-insensitive; fuori whitelist → `E_VENDITE_VALIDATION`; assente = tutte).
- `page` / `page_size` (opzionali): paginazione standard (default 1/50, max 200).

## Output

### Riepilogo

```json
{
  "data": {
    "classi": [
      { "classe": "RECUPERABILE", "n_documenti": 5,
        "valore_fermo_tot": "2000.50", "unita_ferme_tot": 7,
        "anzianita_max_giorni": 90,
        "aree": [
          { "area": "PREVENTIVI", "n_documenti": 3, "valore_fermo_tot": "1500.00",
            "unita_ferme_tot": 5, "anzianita_max_giorni": 40 }
        ] }
    ]
  }
}
```

- **3 classi sempre presenti** nell'ordine di esposizione UI del design
  (🟠 `RECUPERABILE` · 🔵 `SOLLECITO_CLIENTE` · 🔴 `ANOMALIA`), con zeri
  espliciti e `aree` vuota quando la classe non ha documenti. Eventuali classi
  **fuori whitelist** (estensione futura del CHECK di `config.motivi_fermo`)
  vengono **accodate dopo le 3 note**, mai perse in silenzio.
- Totali per classe = somma delle aree (valore su Decimal, `anzianita_max_giorni`
  = massimo); `valore_fermo_tot` serializzato come stringa, `"0"` se solo aree
  a conteggi.

### Lista documenti

Envelope paginato standard (`count/page/page_size/total_pages/results`); ogni
riga: `area`, `competenza_mese` (proxy, può essere NULL), chiavi documento
(`documento_id`, `documento_uid`, `codice`), `cliente_display`, `valore_fermo`
(NULL per aree a conteggi), `unita_ferme`, `motivo_fermo` (vocabolario
`config.motivi_fermo`, decodifica i18n lato FE), `classe`, `azione` (hint
operativo dalla lookup), `data_riferimento` ("fermo da…", v1 proxy data
documento), `anzianita_giorni`, `stato_codice_interno`, `stato_codice`, `fase`.
**Ordinamento BE-side** (le viste non garantiscono ORDER):
`data_riferimento ASC NULLS LAST` (colonna base, ordine identico ad
anzianità DESC ma più amichevole per il planner), poi `valore_fermo DESC
NULLS LAST, area, documento_id`. `anzianita_giorni` è clampata a `>= 0`
(`GREATEST`): una `data_riferimento` futura non produce "fermo da -N gg".
Nel riepilogo `anzianita_max_giorni` è `null` quando nessuna riga della
classe ha una data nota (età sconosciuta ≠ 0 giorni).

## Regole

- **Popolazione = non-verde** (DL-7): la vista espone solo `motivo_fermo NOT
  NULL` con classe ≠ `FISIOLOGICO` — regola unica senza casi speciali per area
  (contratti assenti finché manca il push ricorrente; offerte solo
  `FIGLIO_ABORTITO` 🔴 / `IN_ATTESA_ACCETTAZIONE` 🔵).
- **Anti-drift fail-visible** (DB-3): motivo non mappato nella lookup ⇒
  `classe = 'ANOMALIA'` (COALESCE in vista), mai perso; simmetricamente il
  service accoda le classi sconosciute nel riepilogo.
- **Anzianità v1 = proxy data documento** (`data_riferimento` per area:
  data preventivo/ordine, catena emissione offerte, mese esploso contratti,
  competenza commesse). Il timestamp di transito (DL-5) non serve al backlog:
  i suoi elementi non sono ancora transitati.
- **Scope emittente — interamente DB-side**: RLS invoker sulle 4 aree
  documentali (post fix V-1 `20260706-15`) + filtro GUC nel resolver commesse.
  Il BE **non** passa alcun `auth_user_id`.
- `COUNT(*) OVER()` nella query dati (la union dei resolver è la parte
  costosa: una sola valutazione per pagina); COUNT separato solo come fallback
  per offset oltre l'ultima pagina.
- GET-only, nessun side-effect, nessuna Idempotency-Key.

## Dipendenze DB

- `vendite.vw_dash_backlog_documenti` — doc:
  `docs/it/dbzero/vendite/manual/vw_dash_backlog_documenti.md`
- `vendite.vw_dash_backlog_riepilogo` — doc:
  `docs/it/dbzero/vendite/manual/vw_dash_backlog_riepilogo.md`
- `config.motivi_fermo` (lookup classi, DL-6) — doc:
  `docs/it/dbzero/config/manual/motivi_fermo.md`
- `vendite.vw_dash_fatturazione_documenti` + colonna `data_riferimento`
  (migrations `20260706-03..08`)

## Note di migrazione

- Substrato DB applicato con migrations `20260706-01..15` (pgTAP
  `test-vw-dash-backlog-v1.sql` plan 14 verde).
- Test: `apps/vendite/tests/api/test_dashboard_backlog_api.py` (8 casi) +
  `apps/vendite/tests/services/test_dashboard_backlog_service.py` (9 casi),
  tutti con mock (CI-safe).
- FE (Fase 2): rotta `/vendite/dashboard-backlog` (`DashboardBacklogView.vue`,
  store `dashboardBacklog.js`, severity `classeBacklogSeverity`); vocabolario
  i18n `motivo_fermo` e label aree condivisi con la dashboard 5-card.
