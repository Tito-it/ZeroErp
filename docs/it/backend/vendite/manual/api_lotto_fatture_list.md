# API list_lotto_fatture (Django)

## Scopo

Esporre via HTTP l'elenco paginato delle fatture appartenenti a un lotto, con decodifiche FK, filtri opzionali e ordinamento configurabile.

## Contesto

Endpoint di sola lettura che interroga `vendite.fatturazione_lotti_fatture` con INNER JOIN su `vendite.fatture`, `anagrafiche.billing_account`, `anagrafiche.vw_soggetti_ruoli_dettaglio` e LEFT JOIN su `config.stati_sdi`, `config.stati_doc_fiscale`. Nessuna funzione SQL intermedia: query raw nel repository.

## Input

- Metodo: `GET`
- Path canonico: `/api/v1/vendite/lotti/{lotto_id}/fatture/`
- Header sicurezza: `Authorization: Bearer <access_token>`
- Path param:
  - `lotto_id` (int) — id del lotto; obbligatorio
- Query param (tutti opzionali; assente o vuoto = nessun filtro):
  - `stato_esecuzione` (string) — filtro esito tecnico fattura nel lotto (`OK` | `ERRORE`)
  - `esclusa` (bool) — filtro fatture escluse (`true` | `false`); assente = tutte
  - `sort_by` (string) — colonna ordinamento: `fattura_id` (default), `nominativo`, `totale_doc`
  - `sort_dir` (string) — direzione: `asc` (default) | `desc`
  - `page` (int) — numero pagina, default `1`
  - `page_size` (int) — righe per pagina, default `50`, max `200`

## Output

- `200`:
```json
{
  "data": {
    "count": 1,
    "page": 1,
    "page_size": 50,
    "total_pages": 1,
    "results": [
      {
        "id": 15,
        "lotto_id": 42,
        "fattura_id": 101,
        "stato_sdi_id": null,
        "stato_sdi_descrizione": null,
        "stato_doc_fiscale_id": 3,
        "stato_doc_fiscale_descrizione": "Fattura emessa",
        "stato_doc_fiscale_codice": "EMESSA",
        "stato_esecuzione": "OK",
        "esclusa": false,
        "numero": 234,
        "serie": null,
        "data": "2026-02-01",
        "billing_account_id": 8,
        "totale_doc": "1234.560000",
        "totale_a_pagare": "1234.560000",
        "soggetto_id": 55,
        "ragione_sociale_completa": "Mario Rossi Srl",
        "id_fiscale_univoco_cf_piva": "01234567890"
      }
    ]
  },
  "meta": { "request_id": "..." }
}
```
- `400`: parametri non validi (`E_VENDITE_VALIDATION`)
- `401`: JWT mancante o non valido

## Regole

- `lotto_id` proviene dal path URL; il WHERE `fllf.lotto_id = :lotto_id` e' sempre presente.
- Filtri opzionali: assenza equivale a nessun filtro; `esclusa` accetta `true`/`false`.
- `sort_by` accetta solo valori nella whitelist (`fattura_id`, `nominativo`, `totale_doc`); valore non valido → 400.
- `sort_dir` accetta solo `asc` o `desc`; valore non valido → 400.
- Quando `sort_by != fattura_id` viene aggiunto `fllf.fattura_id ASC` come tiebreaker deterministico.
- `page` deve essere >= 1; `page_size` deve essere compreso tra 1 e 200.
- `is_search_endpoint = True` sulla view: attiva throttling `SearchBurstRateThrottle`.
- `stato_doc_fiscale_codice` = `config.stati_doc_fiscale.codice_interno` (chiave stabile):
  e' il campo su cui il FE basa i gate (es. reset fattura solo su `DRAFT`) — mai la
  `descrizione`, che e' display e puo' cambiare.
- Endpoint di sola lettura: nessun `Idempotency-Key` richiesto.
- Endpoint v1 richiede JWT.

## Dipendenze DB

- `vendite.fatturazione_lotti_fatture` (tabella principale)
- `vendite.fatture` (INNER JOIN — billing_account_id, numero, serie, data, totali)
- `anagrafiche.billing_account` (INNER JOIN — recupero soggetto_ruolo_id)
- `anagrafiche.vw_soggetti_ruoli_dettaglio` (INNER JOIN — ragione_sociale_completa, id_fiscale_univoco_cf_piva)
- `config.stati_sdi` (LEFT JOIN — decodifica stato SDI)
- `config.stati_doc_fiscale` (LEFT JOIN — decodifica stato documento fiscale)

## Note di migrazione

- Query raw nel repository (`VenditeRepository.list_lotto_fatture`); nessuna funzione SQL dedicata.
- Due query per request: `COUNT(*)` + dati con `LIMIT/OFFSET` (pattern offset pagination).
- L'ordinamento per colonne diverse da `fattura_id` usa la whitelist `_SORT_COLUMNS` nel repository; mai interpolazione diretta di input utente nel SQL.
