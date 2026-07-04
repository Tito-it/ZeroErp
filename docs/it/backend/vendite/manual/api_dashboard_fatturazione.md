# API Dashboard Fatturazione (Django)

## Scopo

Espone la Dashboard Fatturazione (controllo del transito per competenza): matrice
annuale area × mese e drill-down paginato degli elementi fermi.

## Contesto

Fase 2 BE del brief
[brief-design-dashboard-fatturazione](../../../dev/work-in-progress/brief-design-dashboard-fatturazione.md):
due endpoint GET **sottili** sopra le proiezioni read-only
`vendite.vw_dash_fatturazione_mensile` (aggregata area × mese) e
`vendite.vw_dash_fatturazione_documenti` (union dei 5 resolver, grana documento × mese).
Nessuna logica di dominio in Python: la semantica totale/transitato/fermo/abortito
vive nelle viste (DB-first). Livello area `LETTURA` sufficiente; nessuna azione di
processo.

```text
GET /api/v1/vendite/dashboard-fatturazione/            (ApiDashboardFatturazione)
GET /api/v1/vendite/dashboard-fatturazione/fermi/      (ApiDashboardFatturazioneFermi)
```

Catena: view (`views_dashboard_fatturazione.py`) →
`vendite_service.fn_dash_fatturazione_mensile` / `fn_dash_fatturazione_fermi` →
`VenditeRepository.list_dash_fatturazione_mensile` / `list_dash_fatturazione_fermi`.

## Input

### `GET /dashboard-fatturazione/`

- `anno` (opzionale, int): anno di competenza. Default: anno corrente.
  Range ammesso 2000–2100 (`E_VENDITE_VALIDATION` fuori range,
  `E_VALIDATION_INPUT` se non numerico).

### `GET /dashboard-fatturazione/fermi/`

- `competenza_mese` (obbligatorio, date ISO): mese di competenza; qualsiasi
  giorno viene normalizzato al 1° del mese.
- `area` (obbligatorio): `PREVENTIVI | ORDINI | OFFERTE | CONTRATTI | COMMESSE`
  (case-insensitive; fuori whitelist → `E_VENDITE_VALIDATION`).
- `page` / `page_size` (opzionali): paginazione standard (default 1/50, max 200).

## Output

### Matrice mensile

```json
{
  "data": {
    "anno": 2026,
    "mesi": [
      { "competenza_mese": "2026-01-01",
        "aree": [
          { "area": "PREVENTIVI", "valore_totale": "1500.00",
            "valore_transitato": "1200.00", "n_documenti": 4,
            "n_transitati": 3, "n_fermi": 1, "n_abortiti": 0 }
        ] }
    ]
  }
}
```

- **12 mesi sempre presenti** (decisione D-5): i mesi/aree senza dati arrivano con
  zeri (LEFT JOIN su `generate_series` nel repository) — nessuna logica calendario
  nel FE.
- Aree in **ordine funnel** fisso: PREVENTIVI, ORDINI, OFFERTE, CONTRATTI, COMMESSE.
- `valore_*` è l'**imponibile** (decisione D-4), serializzato come stringa; per le
  aree a conteggi (OFFERTE, CONTRATTI — decisioni D-2/D-3) è sempre `null`; per le
  aree in euro senza dati è `"0"`.

### Drill-down fermi

Envelope paginato standard (`count/page/page_size/total_pages/results`); ogni riga:
`documento_id`, `documento_uid`, `codice`, `cliente_display` (ragione sociale del
cliente, nullable), `valore_totale`, `valore_transitato`, `unita_totali`,
`unita_transitate`, `motivo_fermo` (vocabolario chiuso, decodifica i18n lato FE —
vedi doc vista), `stato_codice_interno`, `stato_codice`, `fase`.
Ordinamento: `valore_totale DESC NULLS LAST, codice, documento_id`.

## Regole

- **Fermo** = `NOT is_transitato AND NOT is_abortito` (predicato applicato dal
  repository sulla vista documenti). Gli abortiti (esito NEGATIVO) sono fuori dal
  confronto e contati a parte in `n_abortiti` (decisione D-6).
- **Denominatore COMMESSE — solo attività computabili** (dal 20260703-61): il
  resolver commesse esclude dal totale/unità/transito le attività *void*
  (`stato_emissione = ANNULLATA`, `stato_approvazione = RIFIUTATA`, salvo
  `EMESSA + RIFIUTATA` già transitata), simmetrico all'`attivo = true` sulle righe
  ordine. Evita che un'attività annullata gonfi il totale e tenga la commessa ferma
  in eterno. Le altre 4 aree escludono già i void a livello documento
  (`esito = NEGATIVO`) / riga (`attivo`).
- **Scope emittente — interamente DB-side** (dal 20260703-60): le 4 aree documento
  (preventivi/ordini/offerte/contratti) sono filtrate dalla RLS (viste invoker);
  l'area **COMMESSE**, fuori RLS by design (tabella di pipeline scritta anche da
  batch/non-web), è filtrata **dentro il resolver** `vw_dash_fatturazione_commesse`
  via `script.fn_get_emittenti_scope_sr_ids(app.current_user_id)` letto da GUC
  (NULL = vede tutto, `'{}'` = niente, array = whitelist). Così **matrice e
  drill-down concordano** su ogni operatore; il BE **non** passa più alcun
  `auth_user_id` (nessun filtro applicativo).
- ⚠️ Fail-closed COMMESSE: il filtro-in-vista non è aggirato da `BYPASSRLS` →
  senza GUC operatore valorizzata (psql ad-hoc, batch, superuser fuori dal ciclo
  web) il resolver commesse restituisce 0 righe. Accettabile: la dashboard è
  solo-web e `JwtAuditAuthentication` popola sempre `app.current_user_id`.
- GET-only, nessun side-effect, nessuna Idempotency-Key.

## Dipendenze DB

- `vendite.vw_dash_fatturazione_mensile` (aggregata) — doc:
  `docs/it/dbzero/vendite/manual/vw_dash_fatturazione_mensile.md`
- `vendite.vw_dash_fatturazione_documenti` (union resolver) — doc:
  `docs/it/dbzero/vendite/manual/vw_dash_fatturazione_documenti.md` (incluso
  vocabolario `motivo_fermo`)
- `script.fn_get_emittenti_scope_sr_ids` (scope applicativo area COMMESSE)
- Indici di supporto: `ix_commesse_attivita_segment_key`,
  `ix_commesse_attivita_sorgente_competenza` (migration `20260703-58`)

## Note di migrazione

- Fase 1 DB applicata con migrations `20260703-51..59` (pgTAP
  `test-vw-dash-fatturazione-v1.sql` 19/19). L'eventuale futura materializzazione
  dell'aggregata non cambia il contratto verso questi endpoint.
- Test: `apps/vendite/tests/api/test_dashboard_fatturazione_api.py` (12 casi) +
  `apps/vendite/tests/services/test_dashboard_fatturazione_service.py` (10 casi),
  tutti con mock (CI-safe).
