# API Situazione aperta — serbatoio pre-commessa (Django)

## Scopo

Espone la **Situazione aperta v2** (serbatoio pre-commessa) dei cruscotti
fatturazione: i documenti **aperti-non-chiusi** che, se conclusi, andrebbero
in commessa/fatturazione ma non ci sono ancora arrivati. Riepilogo dello stock
per `area × fase` normalizzata (senza asse temporale) e lista paginata dei
documenti, ordinata per "in essere da" (i più vecchi prima), con soglia
opzionale **"aperti da oltre N giorni"** sul solo drill-down.

## Contesto

Fase 3 BE del brief
[brief-design-fatturazione-due-lenti](../../../dev/work-in-progress/brief-design-fatturazione-due-lenti.md)
**§6-ter (DL-14..18)** (substrato DB v2 in
[brief-db-situazione-aperta-v2](../../../dev/work-done/brief-db-situazione-aperta-v2.md),
changeset `20260708-03/04`, PR #944): due endpoint GET **sottili** sopra le
proiezioni read-only `vendite.vw_dash_aperto_riepilogo` (celle `area × fase`)
e `vendite.vw_dash_aperto_documenti` (union dei resolver, 5 aree documento —
DDT dal 2026-07-18, §6-quater DL-21: popolazione ristretta ai DDT con ruolo
di fatturazione; i RESI restano fuori per costruzione, DL-24).
**Perimetro serbatoio interamente DB-side** (DL-15): la vista v2 filtra
`is_transitato IS DISTINCT FROM true AND fase <> 'CHIUSO'` — perimetro unico di
card e drill-down, il BE **non** replica filtri (via il vecchio toggle
`solo_aperti`). Nessuna logica di dominio in Python: popolazione, `fase` (da
`config.stati_doc_*`), esclusione transitati/chiusi vivono nelle viste.
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
  ORDINI | DDT | OFFERTE | CONTRATTI`. **Non whitellistato di proposito** (coerenza
  fail-visible col riepilogo, che accoda le aree fuori whitelist e le rende
  card cliccabili): un'area futura resta drillabile senza toccare il BE;
  un'area sconosciuta — o `COMMESSE`, esclusa dal WHERE della vista (coperta
  dalla Lente 1) — dà lista vuota, mai 400.
- `fase` (opzionale, case-insensitive; assente = tutte): vocabolario
  `config.stati_doc_*.fase` — **3 fasi vive** `APERTO | IN_ATTESA | IN_CORSO`
  (via `CHIUSO`: fuori perimetro serbatoio). **Non whitellistato di proposito**
  (coerenza fail-visible col riepilogo): una fase futura resta drillabile senza
  toccare il BE; una fase sconosciuta dà lista vuota, mai 400.
- `ritardo_giorni` (opzionale, intero > 0; assente = nessuna soglia): filtro
  **"aperti da oltre N giorni"** su data documento (`data_riferimento <= oggi −
  N`, DL-17). Soglia del **solo drill-down**: le card del riepilogo restano la
  fotografia completa. **Strict**: non numerico → 400 (`qp_int_optional`);
  intero `<= 0` → 400 (`E_VENDITE_VALIDATION`, niente normalizzazione
  silenziosa).
- `order_by` / `order_dir` (opzionali): **ordinamento colonne server-side**
  (convenzione delle liste standard, es. clienti/soggetti). `order_by` in
  whitelist — `anzianita_giorni` (default, "aperto da") | `codice` |
  `cliente_display` | `valore_totale`; `order_dir` = `asc` | `desc` (default
  `desc` su `anzianita_giorni`: i più "in essere da" prima). Server-side perché
  la lista è paginata: l'ordine è corretto su **tutte** le pagine, non solo su
  quella visibile. Colonna fuori whitelist o direzione ≠ asc/desc → 400
  (`E_VENDITE_VALIDATION`, whitelist definita una volta nel service). Tiebreak
  stabile `(area, documento_id)` per paginazione deterministica.
- `page` / `page_size` (opzionali): paginazione standard (default 1/50, max 200).

## Output

### Riepilogo

```json
{
  "data": {
    "aree": [
      { "area": "PREVENTIVI", "n_documenti": 5, "valore_totale": "2000.50",
        "fasi": [
          { "fase": "APERTO", "n_documenti": 3, "valore_totale": "1500.00" }
        ] }
    ],
    "fasi": ["APERTO", "IN_ATTESA", "IN_CORSO"]
  }
}
```

- **5 aree sempre presenti** nell'ordine del funnel (`PREVENTIVI, ORDINI,
  DDT, OFFERTE, CONTRATTI`), ognuna con la **griglia delle 3 fasi vive sempre
  presenti** nell'ordine della maturità verso la commessa (`APERTO, IN_ATTESA,
  IN_CORSO`) e zeri espliciti — DL-13: la griglia è neutra, il FE decide quali
  card mostrare. Aree o fasi **fuori whitelist** emesse dalla vista vengono
  **accodate dopo le note**, mai perse in silenzio; il vocabolario `fasi`
  top-level alimenta i filtri FE (nessuna copia FE, nessun contrabbando dalla
  griglia di un'area); un'area extra che porta **valori** li espone (decisione
  data-driven, non la whitelist euro statica).
- Totali per area = somma delle fasi (su Decimal). Misura mista (DL-11/16,
  conferma D-2/D-3/D-4): aree euro (`PREVENTIVI`/`ORDINI`/`DDT`) con
  `valore_totale` come stringa (`"0"` se vuote); aree a conteggi
  (`OFFERTE`/`CONTRATTI`) con `valore_totale` `null` (il FE le legge da
  `valore_totale !== null`).
- ⚠️ **Misura MISTA dell'area ORDINI** (DL-23 emendato, `20260718-13`): gli
  ordini con `fatturazione_trigger ∈ {SPEDITO, CONSEGNATO}` portano il **valore
  ancora da spedire** (il DDT prende in carico il resto); quelli con trigger
  `CONFERMATO` restano al valore pieno. Il calcolo vive nel resolver DB, il BE
  è passthrough; il FE lo dichiara con un hint sulla card.

### Lista documenti

Envelope paginato standard (`count/page/page_size/total_pages/results`); ogni
riga: `area`, chiavi documento (`documento_id`, `documento_uid`, `codice`),
`cliente_display`, `fase`, `stato_codice_interno`, `stato_codice`,
`valore_totale` (NULL per aree a conteggi), `unita_totali`, **`anzianita_giorni`**
(derivata BE in SELECT: `GREATEST(current_date − data_riferimento, 0)`, come il
gemello Backlog — alimenta la colonna "aperto da N gg" e allinea la lettura al
filtro `ritardo_giorni`), `motivo_fermo` (può essere NULL: qui è un hint, non il
criterio di popolazione), `data_riferimento` ("in essere da": data documento,
`valido_dal` per i contratti). **Ordinamento BE-side** (le viste non
garantiscono ORDER): default per `data_riferimento ASC NULLS LAST`, poi
`valore_totale DESC NULLS LAST, area, documento_id`; con `order_by`/`order_dir`
(vedi Input) l'ORDER BY diventa `<colonna whitelist> <asc|desc> NULLS LAST` +
tiebreak `area, documento_id`. Colonna e direzione **whitelistate** (mai input
grezzo nell'ORDER BY).

## Regole

- **Popolazione = serbatoio pre-commessa** (§6-ter, DL-14/15): union 4 aree
  documento con perimetro **aperti-non-chiusi** — `is_transitato IS DISTINCT
  FROM true` (esce l'accettato-già-smistato, transitato-non-chiuso) **AND**
  `fase <> 'CHIUSO'` (esce il preventivo EVASO-con-riga-residua,
  chiuso-non-transitato); abortiti esclusi a monte (`NOT is_abortito`). È il
  pezzo **a monte** della Lente 1 Competenza (che parte dalla commessa); resta
  distinto dalla Lente 2 Backlog (stesso insieme, tagli diversi: Backlog = cosa
  sbloccare ora; Situazione aperta = dove sono tutti gli aperti, per fase).
- **Card = fotografia completa; filtro solo-lista** (DL-17): il riepilogo NON è
  toccato da `ritardo_giorni` (le card fotografano tutto il serbatoio); la
  soglia "aperti da oltre N giorni" agisce solo sul drill-down.
- **Contratti** (DL-18): giudizio di transito sospeso → restano sempre aperti
  (`DRAFT` + `ATTIVO`; `CESSATO` esce con `fase <> CHIUSO`). `ATTIVO` figura
  come `IN_CORSO` (astrazione fase normalizzata).
- **Anti-drift fail-visible**: fasi/aree sconosciute accodate nel riepilogo e
  **passthrough su entrambi i filtri** `area`/`fase` del drill-down (mai 400,
  mai perse: la card accodata resta drillabile).
- **Scope emittente — interamente DB-side**: RLS invoker sulle 4 aree documento
  (`security_invoker=on` su entrambe le viste v2, verificato con guard pgTAP su
  `pg_class.reloptions`). Il BE **non** passa alcun `auth_user_id`.
- Una **sola valutazione della union** per pagina (`_query_paged_view`: CTE
  materializzata + `COUNT(*) OVER()` + **offset clampato all'ultima pagina in
  SQL**). Il rientro da una pagina stantia (lista ridotta da altri utenti) non
  costa più un secondo giro: il BE serve subito l'ultima pagina reale e
  l'envelope dichiara la **pagina effettiva**, che `usePagedDashFetch` adotta.
- GET-only, nessun side-effect, nessuna Idempotency-Key.

## Dipendenze DB

- `vendite.vw_dash_aperto_documenti` (v2) — doc:
  `docs/it/dbzero/vendite/manual/vw_dash_aperto_documenti.md`
- `vendite.vw_dash_aperto_riepilogo` (v2) — doc:
  `docs/it/dbzero/vendite/manual/vw_dash_aperto_riepilogo.md`

## Note di migrazione

- **v2 (serbatoio pre-commessa)** su v1: eliminato il concetto *transitato*
  (in una vista senza asse temporale totalizzava dalla notte dei tempi roba
  già passata, non azionabile). Rimossi dagli endpoint il toggle `solo_aperti`
  e i campi `n_aperti`/`valore_transitato`/`unita_transitate`/`is_transitato`/
  `is_aperto`; aggiunti il filtro `ritardo_giorni` e il campo `anzianita_giorni`.
- Substrato DB v2 applicato con changeset `20260708-03/04` (PR #944): viste
  ristrette agli aperti-non-chiusi + drop colonne transitato (DROP+CREATE
  ordinato, non `CREATE OR REPLACE`), pgTAP `test-vw-dash-security-invoker.sql`
  (plan 14, verdi).
- Test: `apps/vendite/tests/api/test_dashboard_aperto_api.py` (9 casi) +
  `apps/vendite/tests/services/test_dashboard_aperto_service.py` (16 casi),
  tutti con mock (CI-safe).
- FE (Fase 3): rotta `/vendite/situazione-aperta` (`SituazioneApertaView.vue`,
  store `dashboardAperto.js`, severity `faseDocumentoSeverity`, donut per fase
  `DonutFasi` su `DonutBase`); vocabolari i18n nel gruppo condiviso
  `dash_comune` (riusato dal Backlog).
