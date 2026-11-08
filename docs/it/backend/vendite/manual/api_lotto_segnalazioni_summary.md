# API lotto_segnalazioni_summary (Django)

## Scopo

Esporre via HTTP il riepilogo segnalazioni attive di un lotto, con indicazione di blocco avanzamento step.

## Contesto

Endpoint di consultazione che invoca `fn_get_lotto_segnalazioni_summary` in `apps/vendite/services/pipeline_service.py`,
il quale delega a `LottoSegnalazioniService.evaluate_lotto_status`.

View in `apps/vendite/api/views.py`: `ApiLottoSegnalazioniSummary` (riepilogo),
`ApiLottoSegnalazioniRows` (elenco paginato), `ApiLottoSegnalazioniExport`.

## Input

- Metodo: `GET`
- Path canonico: `/api/v1/vendite/lotti/{lotto_id}/segnalazioni/`
- Header sicurezza: `Authorization: Bearer <access_token>`
- Path params: `lotto_id` (int)
- Nessun query param. ⚠️ Il parametro `livello` e l'elenco `segnalazioni[]`
  non stanno più qui: l'elenco è su `segnalazioni/rows/` (sotto).

## Output

- `200`:

```json
{
  "data": {
    "lotto_id": 42,
    "critical_count": 0,
    "warning_count": 2,
    "attention_count": 1,
    "is_error": false,
    "blocks_next_step": false,
    "summary": {
      "fatture_critical_count": 0,
      "fatture_warning_count": 2,
      "lotto_critical_count": 0,
      "lotto_warning_count": 0,
      "lotto_info_count": 1,
      "fatture_stato_esecuzione_errore_count": 0,
      "documenti_bloccanti_count": 0,
      "documenti_presi_in_carico_count": 2,
      "critiche_giro_count": 0,
      "esiti_stato_esecuzione_errore_count": 0,
      "fermo": false
    }
  },
  "meta": { ... }
}
```

- `400 E_PIPELINE_VALIDATION`: `lotto_id` ≤ 0
- `404 E_LOTTO_NON_TROVATO`: lotto inesistente o fuori perimetro — la testata
  si legge prima dei conteggi. ⚠️ 2026-10-20: prima rispondeva zeri, cioè
  «lotto pulito»

## Elenco paginato — `GET lotti/{lotto_id}/segnalazioni/rows/`

`vendite.fn_list_lotto_segnalazioni`: le due origini (log di fattura via ponte
del lotto, log di lotto) in un elenco solo, stessa fonte dei conteggi.

Query param (tutti opzionali):

| Parametro | Note |
|---|---|
| `livello` | `C` · `W` · `I`; assente = tutti. Vocabolario validato dalla funzione DB |
| `origine` | `FATTURA` · `LOTTO`; assente = tutte |
| `solo_attive` | bool, default `true` (le ritirate non si mostrano) |
| `solo_job_corrente` | bool, default `false` |
| `limit` / `offset` | `limit` default `25`, max `500` (`LOTTO_LISTE_PAGINA_MAX`); `offset` default `0`. Fuori limiti → 400 `E_VALIDATION_INPUT` (`limit_fuori_limiti_1_500`, `offset_negativo`). ⛔ `page`/`page_size` sono un 400 dal 2026-10-21 (prima erano il contratto di questa lista) |
| `order_by` | passato alla funzione DB, che possiede la whitelist |
| `order_dir` | `asc` \| `desc`, default `desc` |

Risposta: `{lotto_id, count, page, page_size, total_pages, fuori_job_count,
results}`. `fuori_job_count` = quante segnalazioni restano fuori dall'ultima
corsa: senza, un elenco filtrato e uno vuoto si leggono uguali.

Campi di riga: `riga_key` (`<origine>:<id>`, chiave di riga e tiebreak),
`origine`, `data_ora`, `livello`, `messaggio` (la frase del database, non
riscritta), `error_code`, `fase` (solo origine `LOTTO`), `fattura_id`,
`documento_display` e `importo` (`null` sulle righe di lotto), `disabilitato`,
`job_corrente`, `target` (bersagli `[{type, id}]`), `gruppo_key` (il documento
di cui parla la riga; `null` = critica del giro), `uscita_blocco_reason` /
`uscita_blocco_reason_key` (perché «Togli dal giro» è spento, da
`script.fn_check_documento_escludibile_da_giro`), `riferimento` (il documento
come lo legge una persona; per un documento senza numero, i consumi, è il
codice della commessa di cui parla la segnalazione, dalla colonna
`fatturazione_lotti_log.commessa_id` che il pull per commessa scrive dal
2026-11-08: V-7-bis, brief-db-sorgente-documento-e-riga §8.23).

Errori: `400 E_PIPELINE_VALIDATION` (`lotto_id`, `order_dir`); `400
E_VALIDATION_INPUT` (la finestra: `limit`/`offset` non interi, `limit` fuori
da 1..500, `offset` negativo, `page`/`page_size` presenti — dal 2026-10-21 il
service non ripete il controllo con `E_PIPELINE_VALIDATION`);
`404 E_LOTTO_NON_TROVATO` come il riepilogo.

## Export — `GET lotti/{lotto_id}/segnalazioni/export/?formato=csv|xlsx`

Stessi filtri e ordinamento dell'elenco (`livello`, `origine`, `solo_attive`,
`solo_job_corrente`, `order_by`, `order_dir`), senza paginazione; colonne dal
catalogo `vendite.lotto_segnalazioni`. Oltre `EXPORT_MAX_ROWS` →
`422 E_UI_EXPORT_LIMIT_EXCEEDED`. Stesso `404`.

## Regole

- `lotto_id` obbligatorio e > 0 (validato dal servizio con `ErrorManager.require`).
- `critical_count` = somma `fatture_critical_count` + `lotto_critical_count`.
- `warning_count` = somma `fatture_warning_count` + `lotto_warning_count`.
- `attention_count` = `lotto_info_count` (livello "I" — info operativa).
- `is_error = blocks_next_step = summary.fermo` — ⭐ **dal 2026-09-19 il
  verdetto nasce a DB** (changeSet `20260919-01/-02`, decisione D-V1 di Tid
  «la regola va a DB», brief `brief-db-osservabilita-lotto-fermo-r6-indici`
  P-1): `fermo` è l'**undicesima** colonna di `fn_get_lotto_segnalazioni_summary`,
  che dal 19-09 è un lettore di `vendite.vw_lotti_segnalazioni_summary` — la
  **sede unica** dei dieci conteggi e del verdetto, letta anche dal presidio
  `dbops.vw_lotti_fermi_da_guardare` (digest, pannello «Processi automatici»,
  pallino della topbar). La formula è la stessa di prima — `(fatture_critical +
  lotto_critical) > 0 OR fatture_stato_esecuzione_errore > 0 OR
  esiti_stato_esecuzione_errore > 0` — ma il backend **la legge e non la
  ricalcola**: fino a quel giorno `LottoSegnalazioniService` la sommava in
  Python, cioè due sedi per un verdetto, e al primo addendo nuovo banner e
  digest avrebbero detto cose diverse senza che nessun test lo vedesse. Un
  addendo nuovo si aggiunge **nella vista**, e arriva qui da solo.
  ⚠️ Il **rilancio dello stesso step** resta ammesso: è la via d'uscita, e per
  il terzo addendo è l'unica (il pull rivede il documento e scrive l'esito nuovo).
  ⚠️ I dieci conteggi restano per la **frase** (banner, `detail` del rifiuto
  `E_PIPELINE_LOTTO_CRITICAL`, payload di `PIPELINE_COMPLETED`), non per la
  decisione. Su un lotto fuori perimetro la vista darebbe zeri e `fermo =
  false`, ma il cancello è la testata (`404`): quegli zeri non arrivano a video.
- `summary.fatture_stato_esecuzione_errore_count` — conteggio fatture del lotto con `stato_esecuzione = 'ERRORE'`; restituito direttamente da `fn_get_lotto_segnalazioni_summary` (6ª colonna).
- `summary.documenti_bloccanti_count` · `documenti_presi_in_carico_count` ·
  `critiche_giro_count` — i tre numeri del **banner** (2026-09-08): contano
  **gesti**, non allarmi, e **non** entrano nel verdetto.
- `summary.esiti_stato_esecuzione_errore_count` — ⭐ **il decimo numero, e
  questo entra nel verdetto** (2026-09-12, changeSet `20260912-16`, brief
  `brief-db-rilancio-step-non-rivede-le-proprie-commesse` D2): i documenti
  presi in carico il cui **ultimo** esito in `fatturazione_lotti_esiti` è
  `ERRORE`. `ESCLUSO` non conta — è la via d'uscita, l'operatore ha dichiarato
  che quel documento esce dal giro.
  ⚠️ **Può essere > 0 con `critical_count = 0`**: il runner ritira le proprie
  bandiere all'avvio di ogni rerun, e se il giro non rivede un documento
  nessuno le rialza — prima di D2 quel lotto usciva `COMPLETATO` per
  sottrazione. ⇒ Il client legge il verdetto da `blocks_next_step`, **non** lo
  ricalcola da `critical_count`: `LottoDrawer` lo fa dal 2026-09-12 (gate di
  «Numera»/«Avanza» e banner), e la frase del banner ha un ramo dedicato che
  manda l'operatore sulla scheda **«Presi in carico»** (la lista degli esiti:
  se il pull è fallito una fattura non è mai nata, quindi su «Documenti» quella
  riga non c'è), dove la riga in `ERRORE` porta `ErroreRigaInfo` e il verbo
  «Togli dal giro».
  ⚠️ Si **sovrappone** ai tre del banner (un documento con critica viva ha anche
  l'esito `ERRORE`): non si somma a `documenti_bloccanti_count`.
- Endpoint di sola lettura: nessun `Idempotency-Key` richiesto.
- Endpoint v1 richiede JWT.

## Dipendenze DB

- `vendite.fn_get_lotto_segnalazioni_summary` (funzione SQL, lettrice di
  `vendite.vw_lotti_segnalazioni_summary` dal `20260919-02`)
- `vendite.vw_lotti_segnalazioni_summary` (la sede dei conteggi e del verdetto
  `fermo`, una riga per lotto, `security_invoker`)
- `vendite.fatture_log` (sorgente segnalazioni fattura)
- `apps.vendite.services.lotto_segnalazioni_service.LottoSegnalazioniService`

## Note di migrazione

- Endpoint introdotto per supporto UI nella visualizzazione stato segnalazioni prima di avanzare step pipeline.
- 2026-09-19 (pezzo V di `piano-be-fe-osservabilita-pallino-e-superfici`):
  `summary.fermo` in coda e `is_error`/`blocks_next_step` letti da lì. Nessun
  cambio per il client: `scegliRamoBanner` legge `blocks_next_step` come prima.
  Presidi: `test_lotto_segnalazioni_service` (il service non ricalcola),
  `test_pipeline_repository` (la colonna per nome, il tipo booleano),
  `test_discovery_riceve_l_identita_del_giro` test 4 (la colonna esiste sulla
  funzione vera). Il collaudo di parità DB ⇔ vecchia somma Python
  (`test_parita_verdetto_lotto_fermo_transitorio.py`) è **transitorio** e si
  toglie con la PR successiva.
- 2026-10-21: `rows/` legge la finestra come `limit`/`offset` (`pagina_da_query`,
  max 500); `page`/`page_size` in query diventano un 400. Envelope invariato.
