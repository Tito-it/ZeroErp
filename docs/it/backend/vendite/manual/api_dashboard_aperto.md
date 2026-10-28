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
[brief-design-fatturazione-due-lenti](../../../dev/work-done/brief-design-fatturazione-due-lenti.md)
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
GET /api/v1/vendite/dashboard-aperto/                    (ApiDashboardAperto)
GET /api/v1/vendite/dashboard-aperto/documenti/          (ApiDashboardApertoDocumenti)
GET /api/v1/vendite/dashboard-aperto/documenti/export/   (ApiDashboardApertoDocumentiExport)
```

L'export (`?formato=csv|xlsx`, default csv) prende gli stessi filtri e lo
stesso ordinamento del drill-down; colonne e ordine dal catalogo
`vendite.dash_aperto_documenti` (configurazione dell'operatore), tetto 10.000
righe. Drill-down ed export dichiarano `lista_codice =
"vendite.dash_aperto_documenti"`: il cancello di perimetro emittente può
rispondere `422 E_UI_LISTA_EMITTENTE_DA_SCEGLIERE`.

Catena: view (`views_dashboard_aperto.py`) →
`vendite_service.fn_dash_aperto_{riepilogo,documenti}` →
`VenditeRepository.list_dash_aperto_{riepilogo,documenti}`.

## Input

### `GET /dashboard-aperto/`

Nessun parametro.

### `GET /dashboard-aperto/documenti/`

- `area` (opzionale, case-insensitive; assente = tutte): `PREVENTIVO |
  ORDINE_VENDITA | DDT_VENDITA | OFFERTA_COMMERCIALE | CONTRATTO`.
> ⭐ **Dal 2026-10-20 l'`area` è il codice della sorgente** (`config.sorgenti.codice_interno`): `PREVENTIVO`, `ORDINE_VENDITA`, `DDT_VENDITA`, `OFFERTA_COMMERCIALE`, `CONTRATTO`, `COMMESSA`, `RESO_VENDITA`. Il plurale (`ORDINI`, `RESI`…) è ritirato col sotto-giro 2d di [brief-db-grammatica-unica-documenti](../../../dev/work-done/brief-db-grammatica-unica-documenti.md) (G-6).
 **Validata sul vocabolario del modello, non sulla whitelist del pivot**:
  un codice che non è una sorgente è **400 `E_VENDITE_VALIDATION`** sul campo
  `area` (dal 2026-10-20; prima era lista vuota, e un client rimasto al
  plurale non riceveva nessun segnale). Una sorgente vera fuori dalle cinque
  resta drillabile: è la card «extra» che il riepilogo accoda (fail-visible).
  `COMMESSA`, esclusa dal WHERE della vista (coperta dalla Lente 1), è un
  codice vero e dà lista vuota.
- `fase` (opzionale, case-insensitive; assente = tutte): vocabolario
  `config.stati_doc_*.fase` — `APERTO | IN_ATTESA | IN_CORSO | CHIUSO`
  (specchio `FASI_DOCUMENTO` del CHECK, presidiato). Fuori vocabolario è
  **400 `E_VENDITE_VALIDATION`**. Le fasi vive del serbatoio sono le prime tre:
  `CHIUSO` è ammessa ma la vista non la contiene (lista vuota).
- `ritardo_giorni` (opzionale, intero > 0; assente = nessuna soglia): filtro
  **"aperti da oltre N giorni"** su data documento (`data_riferimento <= oggi −
  N`, DL-17). Soglia del **solo drill-down**: le card del riepilogo restano la
  fotografia completa. **Strict**: non numerico → 400 (`qp_int_optional`);
  intero `<= 0` → 400 (`E_VENDITE_VALIDATION`, niente normalizzazione
  silenziosa); `N` che porti `oggi − N` prima del parametro
  `VENDITE_DASHBOARD_RITARDO_DATA_MINIMA` → 400 (`E_VENDITE_VALIDATION`, il
  `detail` dice il massimo di oggi). Vale anche per l'export.
- `order_by` / `order_dir` (opzionali): **ordinamento colonne server-side**
  (convenzione delle liste standard, es. clienti/soggetti). `order_by` in
  whitelist — `anzianita_giorni` (default, "aperto da") | `area` | `codice` |
  `cliente_display` | `fase` | `stato_codice` | `valore_totale` |
  `emittente_ragione_sociale`
  (`area`/`fase`/`stato_codice` aggiunte il 2026-08-03: erano colonne a video
  che non ordinavano, e `stato_codice` lasciava scoperto il nucleo *stato*);
  `order_dir` = `asc` | `desc`. Con `order_by` e senza `order_dir`: le colonne
  data (per nome, `e_chiave_data`) partono DESC, le altre ASC — nessuna colonna
  di questa whitelist è una data, quindi qui è sempre ASC (anche
  `anzianita_giorni`, che è un numero di giorni). Server-side perché
  la lista è paginata: l'ordine è corretto su **tutte** le pagine, non solo su
  quella visibile. Colonna fuori whitelist o direzione ≠ asc/desc → 400
  (`E_VENDITE_VALIDATION`, whitelist definita una volta nel service). Tiebreak
  stabile `(area, documento_id)` per paginazione deterministica.
- `limit` / `offset` (opzionali): paginazione standard (`pagina_da_query`:
  `limit` default 25, max 200; `offset` default 0; non interi, `limit` fuori
  da 1..200 o `offset` negativo → 400 `E_VALIDATION_INPUT`). ⛔ `page`/`page_size` sono
  un 400 `E_VALIDATION_INPUT` dal 2026-10-21 (prima erano il contratto di
  questa lista).

## Output

### Riepilogo

```json
{
  "data": {
    "aree": [
      { "area": "PREVENTIVO", "n_documenti": 5, "valore_totale": "2000.50",
        "fasi": [
          { "fase": "APERTO", "n_documenti": 3, "valore_totale": "1500.00" }
        ] }
    ],
    "fasi": ["APERTO", "IN_ATTESA", "IN_CORSO"]
  }
}
```

- **5 aree sempre presenti** nell'ordine del funnel (`PREVENTIVO, ORDINE_VENDITA,
  DDT_VENDITA, OFFERTA_COMMERCIALE, CONTRATTO`), ognuna con la **griglia delle 3 fasi vive sempre
  presenti** nell'ordine della maturità verso la commessa (`APERTO, IN_ATTESA,
  IN_CORSO`) e zeri espliciti — DL-13: la griglia è neutra, il FE decide quali
  card mostrare. Aree o fasi **fuori whitelist** emesse dalla vista vengono
  **accodate dopo le note**, mai perse in silenzio; il vocabolario `fasi`
  top-level alimenta i filtri FE (nessuna copia FE, nessun contrabbando dalla
  griglia di un'area); un'area extra che porta **valori** li espone (decisione
  data-driven, non la whitelist euro statica).
- Totali per area = somma delle fasi (su Decimal). Misura mista (DL-11/16,
  conferma D-2/D-3/D-4): aree euro (`PREVENTIVO`/`ORDINE_VENDITA`/`DDT_VENDITA`) con
  `valore_totale` come stringa (`"0"` se vuote); aree a conteggi
  (`OFFERTA_COMMERCIALE`/`CONTRATTO`) con `valore_totale` `null` (il FE le legge da
  `valore_totale !== null`).
- ⚠️ **Misura MISTA dell'area ORDINE_VENDITA** (DL-23 emendato, `20260718-13`): gli
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
`valido_dal` per i contratti), `emittente_ragione_sociale`. **Ordinamento BE-side** (le viste non
garantiscono ORDER): default per `data_riferimento ASC NULLS LAST`, poi
`valore_totale DESC NULLS LAST, area, documento_id`; con `order_by`/`order_dir`
(vedi Input) l'ORDER BY diventa `<colonna whitelist> ASC NULLS FIRST` oppure
`DESC NULLS LAST` (il vuoto vale come minimo, `sql_order_direction`) +
tiebreak `area ASC, documento_id <stessa direzione della colonna>`. Colonna e
direzione **whitelistate** (mai input grezzo nell'ORDER BY).

⚠️ **Il tiebreak `documento_id` segue la direzione** dal 2026-08-03: ordinando
DESC, a parità di valore viene prima il documento più recente. `area` resta
invece ASC perché raggruppa, non spareggia. La paginazione deterministica non
è toccata: dipende dall'univocità del tiebreak, non dal suo verso. Vedi
`sql_tiebreak_direction` nel catalogo BB backend.

## Regole

- **Popolazione = serbatoio pre-commessa** (§6-ter, DL-14/15): union **5** aree
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
- **Scope emittente — interamente DB-side**: RLS invoker sulle **5** aree
  documento (`security_invoker=on` su entrambe le viste v2, verificato con guard
  pgTAP su `pg_class.reloptions`). Il BE **non** passa alcun `auth_user_id`.
  📌 *Diceva «4 aree» in due punti — un residuo del 2026-07-08, quando l'area
  DDT non c'era ancora (è entrata il 2026-07-18, DL-21). Corretto il 2026-08-31,
  misurando `pg_class.relrowsecurity`: `preventivi`, `ordini`,
  `offerte_commerciali`, `contratti` **e `ddt`** hanno tutte la RLS.*
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

- 2026-10-21: la lista documenti legge la finestra come `limit`/`offset`
  (`pagina_da_query`); `page`/`page_size` in query diventano un 400. Envelope
  invariato.
- **v2 (serbatoio pre-commessa)** su v1: eliminato il concetto *transitato*
  (in una vista senza asse temporale totalizzava dalla notte dei tempi roba
  già passata, non azionabile). Rimossi dagli endpoint il toggle `solo_aperti`
  e i campi `n_aperti`/`valore_transitato`/`unita_transitate`/`is_transitato`/
  `is_aperto`; aggiunti il filtro `ritardo_giorni` e il campo `anzianita_giorni`.
- Substrato DB v2 applicato con changeset `20260708-03/04` (PR #944): viste
  ristrette agli aperti-non-chiusi + drop colonne transitato (DROP+CREATE
  ordinato, non `CREATE OR REPLACE`), pgTAP `test-vw-dash-security-invoker.sql`
  (plan 14, verdi). ⚠️ Quel file è stato **ritirato il 2026-09-07**: il presidio
  non elenca più le viste per nome ma chiede *«esiste una vista che tocca dati
  protetti e non gira col perimetro di chi legge?»*, e vive in
  `db/pgtap/rls/test-rls-viste-security-invoker.sql`. La riga qui sopra resta
  perché racconta cosa fu fatto allora.
- Test: `apps/vendite/tests/api/test_dashboard_aperto_api.py` (9 casi) +
  `apps/vendite/tests/services/test_dashboard_aperto_service.py` (16 casi),
  tutti con mock (CI-safe).
- FE (Fase 3): rotta `/vendite/situazione-aperta` (`SituazioneApertaView.vue`,
  store `dashboardAperto.js`, severity `faseDocumentoSeverity`, donut per fase
  `DonutFasi` su `DonutBase`); vocabolari i18n nel gruppo condiviso
  `dash_comune` (riusato dal Backlog).
