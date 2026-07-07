# API Dashboard Competenza — Lente 1 (Django)

## Scopo

Espone la Lente 1 Competenza dei cruscotti fatturazione a due lenti: aggregata
annuale del funnel commessa → fattura per mese di competenza (4 stadi + breakdown
per stato documento fiscale), drill-down paginato a grana attività e lista degli
errori vivi di fatturazione (blocco 4).

## Contesto

Fase 1 BE del brief
[brief-design-fatturazione-due-lenti](../../../dev/work-in-progress/brief-design-fatturazione-due-lenti.md)
(substrato DB in
[brief-db-fatturazione-due-lenti](../../../dev/work-done/brief-db-fatturazione-due-lenti.md),
migrations `20260706-01..15`): tre endpoint GET **sottili** sopra le proiezioni
read-only `vendite.vw_dash_competenza_mensile` (aggregata formato lungo),
`vendite.vw_dash_competenza_attivita` (grana attività) e
`vendite.vw_dash_competenza_errori` (union task in errore + fatture critical).
Nessuna logica di dominio in Python: stadi, ritardo e competenza vivono nelle
viste (DB-first); il service fa solo il **pivot** del formato lungo. Livello area
`LETTURA` sufficiente; nessuna azione di processo.

```text
GET /api/v1/vendite/dashboard-competenza/            (ApiDashboardCompetenza)
GET /api/v1/vendite/dashboard-competenza/attivita/   (ApiDashboardCompetenzaAttivita)
GET /api/v1/vendite/dashboard-competenza/errori/     (ApiDashboardCompetenzaErrori)
```

Catena: view (`views_dashboard_competenza.py`) →
`vendite_service.fn_dash_competenza_{mensile,attivita,errori}` →
`VenditeRepository.list_dash_competenza_{mensile,attivita,errori}` +
`count_dash_competenza_errori_mensile`.

## Input

### `GET /dashboard-competenza/`

- `anno` (opzionale, int): anno di competenza. Default: anno corrente.
  Range ammesso 2000–2100 (`E_VENDITE_VALIDATION` fuori range,
  `E_VALIDATION_INPUT` se non numerico).

### `GET /dashboard-competenza/attivita/`

- `competenza_mese` (obbligatorio, date ISO): mese di competenza; qualsiasi
  giorno viene normalizzato al 1° del mese.
- `stadio` (opzionale): `DA_APPROVARE | DA_EMETTERE | EMESSA_NON_FATTURATA |
  FATTURATA` (case-insensitive; fuori whitelist → `E_VENDITE_VALIDATION`;
  assente = tutti gli stadi).
- `solo_ritardo` (opzionale, bool): se `true` solo le attività emesse in ritardo
  (`emessa_in_ritardo IS TRUE` — recuperi tardivi, §7 del design).
- `page` / `page_size` (opzionali): paginazione standard (default 1/50, max 200).

### `GET /dashboard-competenza/errori/`

- `competenza_mese` (opzionale, date ISO, normalizzato al 1°): assente = errori
  vivi di tutti i mesi.
- `page` / `page_size` (opzionali): paginazione standard.

## Output

### Aggregata annuale

```json
{
  "data": {
    "anno": 2026,
    "mesi": [
      { "competenza_mese": "2026-01-01",
        "stadi": [
          { "stadio": "FATTURATA", "n_attivita": 7, "valore": "3000.00",
            "valore_fatturato": "3000.50", "valore_display": "3000.50",
            "n_in_ritardo": 1, "valore_in_ritardo": "100.00",
            "stati_fattura": [
              { "stato_fattura_codice_interno": "DRAFT",
                "stato_fattura_codice": "DRAFT", "n_attivita": 3,
                "valore": "1000.00", "valore_fatturato": "990.00",
                "n_in_ritardo": 1, "valore_in_ritardo": "100.00" }
            ] }
        ],
        "totali": { "valore_teorico": "3300.00", "valore_fatturato": "3000.50",
                    "valore_da_fatturare": "300.00", "n_in_ritardo": 1 },
        "n_errori": 1 }
    ]
  }
}
```

- **12 mesi sempre presenti**, ognuno con i **4 stadi in ordine funnel** fisso:
  `DA_APPROVARE, DA_EMETTERE, EMESSA_NON_FATTURATA, FATTURATA` (completamento a
  griglia nel service, stesso contratto D-5 della dashboard 5-card). Eventuali
  stadi **fuori whitelist** emessi in futuro dalla vista vengono **accodati dopo
  i 4 noti**, mai persi in silenzio (fail-visible, stesso principio anti-drift
  di `config.motivi_fermo`): aggregata e drill-down non possono divergere senza
  segnale.
- **Contratto simmetrico** (concentrico DL-8): ogni cella-stadio ha sempre tutti i
  campi; `valore_fatturato` è significativo solo su FATTURATA, `n_in_ritardo`
  solo sugli stadi emessi, `stati_fattura` è popolata solo su FATTURATA (breakdown
  3a, righe nell'ordine `config.stati_doc_fiscale.ordine`).
- **Misura "fatturato" = `imponibile_riga`** (decisione DB-6, Tid 2026-07-06):
  la regola vive **una volta sola nel BE** come `valore_display` per cella
  (= `valore_fatturato` su FATTURATA, teorico `valore` altrove) e nel blocco
  `totali` del mese (`valore_teorico` / `valore_fatturato` /
  `valore_da_fatturare` = teorico dei non fatturati / `n_in_ritardo`). Il FE
  rende `valore_display` e `totali` senza scegliere la misura. Importi
  serializzati come stringhe.
- `n_errori` = errori vivi del mese (blocco 4), per semaforo/badge senza seconda
  chiamata.

### Drill-down attività

Envelope paginato standard (`count/page/page_size/total_pages/results`); ogni riga:
chiavi (`commessa_attivita_id`, `commessa_id`, `commessa_codice`),
`cliente_display`, articolo decodificato via JOIN (`articolo_id`,
`articolo_codice`, `articolo_descrizione`), `data_attivita`, `quantita`, `stadio`,
assi grezzi (`stato_approvazione`, `stato_emissione`), `valore`,
`data_emissione` (= `attivita_fatturabili.data_insert`, DL-5), `emessa_in_ritardo`
(NULL se non emessa), flag AF (`sospesa`, `posticipa_al`), aggancio fattura
(`fattura_id/anno/serie/numero`, `stato_fattura_codice_interno/codice`,
`valore_fatturato`, `fattura_critical`).
Ordinamento: `valore DESC NULLS LAST, commessa_codice, commessa_attivita_id`.

### Errori vivi

Envelope paginato standard; ogni riga: `tipo_evento`
(`TASK_ERRORE | FATTURA_CRITICA`), `competenza_mese`, `lotto_id/lotto_codice/
stato_lotto`, `fattura_id/anno/serie/numero`, `task_code`, `error_code`,
`messaggio`, `data_evento`. Ordinamento: `data_evento DESC NULLS LAST` +
tiebreaker deterministico su chiavi naturali (la union non ha PK).

## Regole

- **Stadio** = CASE della vista attività: `DA_APPROVARE` (non emessa, non
  approvata) → `DA_EMETTERE` (approvata, non emessa) → `EMESSA_NON_FATTURATA`
  (AF senza `fattura_riga_id`) → `FATTURATA`.
- **Void esclusi** (parità predicato `20260703-61`): attività `ANNULLATA` /
  `RIFIUTATA` (salvo `EMESSA + RIFIUTATA`) e commesse `ANNULLATA` fuori da tutte
  le proiezioni.
- **Recupero tardivo** = `date_trunc('month', af.data_insert) > competenza_mese`
  (DL-5: `data_insert` validata come data-emissione affidabile; caveat C1
  documentato nel manuale della vista).
- **Errori vivi**: task run `ERRORE` attivo non superato da un run `COMPLETATO`
  sulla stessa chiave; fatture `critical = true`. Competenza per gli errori
  fattura: lotto → mesi AF → fallback mese data fattura (DB-7). Il bucket
  mensile (conteggio e filtro) è normalizzato con `date_trunc('month', …)`:
  `fatturazione_lotti.competenza_mese` non ha un CHECK primo-del-mese e una
  competenza a metà mese renderebbe l'errore invisibile alla griglia.
- **Scope emittente — interamente DB-side** (DB-8): le tre viste applicano il
  filtro `script.fn_get_emittenti_scope_sr_ids(app.current_user_id)` da GUC,
  fail-closed (senza GUC ⇒ 0 righe). Il BE **non** passa alcun `auth_user_id`.
- GET-only, nessun side-effect, nessuna Idempotency-Key.

## Dipendenze DB

- `vendite.vw_dash_competenza_attivita` — doc:
  `docs/it/dbzero/vendite/manual/vw_dash_competenza_attivita.md` (incluso caveat
  C1 e GUC fail-closed)
- `vendite.vw_dash_competenza_mensile` — doc:
  `docs/it/dbzero/vendite/manual/vw_dash_competenza_mensile.md`
- `vendite.vw_dash_competenza_errori` — doc:
  `docs/it/dbzero/vendite/manual/vw_dash_competenza_errori.md`
- `config.stati_doc_fiscale` (decode etichetta + ordine breakdown 3a)
- `catalogo.articoli` (decode articolo nel drill-down)
- Indice `ix_attivita_fatturabili_competenza_mese` (migration `20260706-14`)

## Note di migrazione

- Substrato DB applicato con migrations `20260706-01..15` (pgTAP
  `test-vw-dash-competenza-v1.sql` plan 15 verde). L'eventuale futura
  materializzazione dell'aggregata non cambia il contratto verso questi endpoint.
- Test: `apps/vendite/tests/api/test_dashboard_competenza_api.py` (14 casi) +
  `apps/vendite/tests/services/test_dashboard_competenza_service.py` (18 casi),
  tutti con mock (CI-safe).
- FE (Fase 1): rotta `/vendite/dashboard-competenza`
  (`DashboardCompetenzaView.vue`, store `dashboardCompetenza.js`).
