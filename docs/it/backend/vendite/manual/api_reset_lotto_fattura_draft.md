# API reset_lotto_fattura_draft (Django)

## Scopo

Togliere **una** fattura pre-fiscale da un lotto, cancellandola e liberandone le
attività; e, accanto, togliere uno o più **documenti** dal giro
(`documenti/escludi/`), verbo che questa primitiva la compone.

## Contesto

View `ApiResetLottoFatturaDraft` → `fn_elimina_fattura_da_lotto`
(`apps/vendite/services/pipeline_service.py` → `LottoResetService`) → funzione SQL
`vendite.fn_elimina_fattura_da_lotto`. URL e permesso conservano il nome storico
«reset-draft»: sono contratti verso client e catalogo permessi.

## Input

- Metodo: `POST`
- Path: `/api/v1/vendite/lotti/{lotto_id}/fatture/{fattura_id}/reset-draft/`
- Header: `Authorization: Bearer <access_token>`, `Idempotency-Key` (obbligatorio)
- Permesso: `post_permission = "reset_lotto_fattura_draft"`
- Path params: `lotto_id` (int), `fattura_id` (int)
- Body JSON: vuoto

## Output

- `200`:

```json
{
  "data": {
    "updated_attivita": 1,
    "deleted_fatture": 1,
    "deleted_righe": 1,
    "riemesse_attivita": 1
  },
  "meta": { ... }
}
```

  `riemesse_attivita` = attività di commessa tornate `NON_EMESSA`, tenuto separato
  da `updated_attivita` (attività sbloccate).
- `400 E_RESET_LOTTO_FATTURA_VALIDATION`: `lotto_id` o `fattura_id` ≤ 0
- Rifiuti di dominio col codice del **primo** motivo di
  `script.fn_check_fattura_eliminabile_da_lotto` — la stessa funzione da cui la
  lista fatture del lotto legge `can_reset_fattura` e il suo motivo.

## Regole

- Perimetro: lotto **e** fattura pre-fiscali (`DRAFT` o `EMESSA`), validato dal
  DB. Non è un'estrazione: la fattura viene cancellata, righe e satelliti compresi.
- Pattern core `handle_post_json(..., require_idempotency_key=True)`.

## Uscita di documenti dal giro — `POST lotti/{lotto_id}/documenti/escludi/`

- View `ApiEscludiDocumentiDaGiro` → `fn_escludi_documenti_da_giro` → per ogni
  chiave `vendite.fn_escludi_documento_da_giro`.
- Stesso permesso `reset_lotto_fattura_draft`, `Idempotency-Key` obbligatorio.
- Body: `{ "gruppo_keys": ["ORDINE_VENDITA:…", "MAN:45"], "motivo": "…" }`.
  `gruppo_keys` lista non vuota di stringhe non vuote (deduplicata nell'ordine);
  `motivo` testo, **uno** per il giro, obbligatorio (lo impone il DB). La
  `gruppo_key` sta nel body perché contiene i due punti.
- `400 E_PIPELINE_VALIDATION`: `gruppo_keys` assente, vuota o con elementi non
  validi; `motivo` non testo.
- `200` **anche quando falliscono tutti** — è un report:
  `{ "esito", "totale", "ok", "usciti": [ {lotto_id, gruppo_escluso,
  fatture_cancellate, attivita_riemesse, gruppi_riaperti, …} ], "falliti": [
  {gruppo_key, codice, messaggio} ] }`. ⚠️ Una bozza può coprire più documenti:
  `gruppi_riaperti` nomina gli altri documenti tornati «da emettere».
- Il verdetto è di `script.fn_check_documento_escludibile_da_giro` (stessa sede del
  pulsante spento in `segnalazioni/rows/`); i codici per riga distinguono, p.es.,
  `E_LOTTO_DOC_GIA_USCITO` da `E_LOTTO_DOC_NON_IN_ERRORE`.

## Dipendenze DB

- `vendite.fn_elimina_fattura_da_lotto`, `script.fn_check_fattura_eliminabile_da_lotto`
- `vendite.fn_escludi_documento_da_giro`, `script.fn_check_documento_escludibile_da_giro`
