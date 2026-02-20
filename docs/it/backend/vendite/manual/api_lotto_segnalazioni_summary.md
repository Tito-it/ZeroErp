# API lotto_segnalazioni_summary (Django)

## Scopo

Esporre via HTTP il riepilogo segnalazioni attive di un lotto, con indicazione di blocco avanzamento step.

## Contesto

Endpoint di consultazione che invoca `fn_get_lotto_segnalazioni_summary` in `apps/vendite/services/pipeline_service.py`,
il quale delega a `LottoSegnalazioniService.evaluate_lotto_status`.

View in `apps/vendite/api/views.py`:

- `ApiLottoSegnalazioniSummary`
- `ApiLottoSegnalazioniSummaryV1`

## Input

- Metodo: `GET`
- Path canonico: `/api/v1/vendite/lotti/{lotto_id}/segnalazioni/`
- Header sicurezza: `Authorization: Bearer <access_token>`
- Path params: `lotto_id` (int)

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
      "lotto_info_count": 1
    }
  },
  "meta": { ... }
}
```

- `400`: `lotto_id` non valido o <= 0
- `500`: errore applicativo gestito dal middleware

## Regole

- `lotto_id` obbligatorio e > 0 (validato dal servizio con `ErrorManager.require`).
- `critical_count` = somma `fatture_critical_count` + `lotto_critical_count`.
- `warning_count` = somma `fatture_warning_count` + `lotto_warning_count`.
- `attention_count` = `lotto_info_count` (livello "I" — info operativa).
- `is_error = true` se `critical_count > 0`.
- `blocks_next_step = true` se `is_error = true` (nessun avanzamento pipeline ammesso).
- Endpoint di sola lettura: nessun `Idempotency-Key` richiesto.
- Endpoint v1 richiede JWT.

## Dipendenze DB

- `vendite.fn_get_lotto_segnalazioni_summary` (funzione SQL)
- `vendite.fatture_log` (sorgente segnalazioni fattura)
- `apps.vendite.services.lotto_segnalazioni_service.LottoSegnalazioniService`

## Note di migrazione

- Endpoint introdotto per supporto UI nella visualizzazione stato segnalazioni prima di avanzare step pipeline.
