# API list_lotto_fatture (Django)

## Scopo

Esporre via HTTP l'elenco paginato delle fatture appartenenti a un lotto, con decodifiche FK, filtri opzionali e ordinamento configurabile.

## Contesto

Endpoint di sola lettura che interroga `vendite.fatturazione_lotti_fatture` con INNER JOIN su `vendite.fatture`, `anagrafiche.billing_account`, `anagrafiche.vw_soggetti_ruoli_dettaglio` e LEFT JOIN su `config.stati_sdi`, `config.stati_doc_fiscale`. Nessuna funzione SQL intermedia: query raw nel repository.

## L'errore attaccato alla riga (2026-08-21)

`stato_esecuzione` dice **che** la fattura è fallita; da sola non dice perché, e
il motivo viveva solo nel toast del momento — cioè in nessun posto, un minuto
dopo. La riga porta ora l'**ultima segnalazione viva** del documento, letta da
`vendite.fatture_log` con un `LEFT JOIN LATERAL` che ne prende **una**.

⭐ **La regola è «l'ultima viva, dalle più gravi»** (D-6), e le due metà contano
entrambe: si guardano **tutti** i livelli — non solo i critici — e a parità
vince la **gravità** prima della data. Un documento con un avviso di ieri e
nessun critico ha qualcosa da dire, e prima non lo diceva; uno con un critico di
ieri e un avviso di oggi deve mostrare il critico, non l'avviso.

| Campo | Cosa |
|---|---|
| `errore_messaggio` | il messaggio del database, quello che dice cosa è successo e la via d'uscita. ⚠️ Dal `T-3b` (2026-08-24) **non nomina più il documento con un id**: *quale* aprire lo dice il bersaglio, che viaggia nel `meta` della riga di log (chiave `bersagli`) e a video diventa un pulsante |
| `errore_codice` | il codice applicativo, da `meta->>'error_code'` — la chiave che scrivono sia le funzioni DB sia il backend (D-7) |
| `errore_quando` | quando: un errore vecchio su una riga già rilavorata si riconosce solo dalla data |
| `errore_livello` | `C`/`W`/`I` — **fuori dal seed**, ma nel payload: senza, il frontend mostrerebbe l'icona rossa anche su un avviso. Stesso ruolo di `natura_doc_codice` |

Tutti `null` (con `errore_bersagli`) quando non c'è errore.

⚠️ **Il `LATERAL` sta fuori dal `COUNT`**: il conteggio delle righe del lotto non
ha bisogno del messaggio, e cercarlo lì sarebbe lavoro per niente a ogni pagina.

⭐ **E chi la abbassa**: il tentativo successivo. `ritira_marcature_fatture_be`
gira **prima del verdetto** della guardia PRE-1 e **fuori** dalla transazione
dello step — la marcatura firmata `origine=BE_PIPELINE` viene ritirata, il ponte
torna `COMPLETED`, e se il giro fallisce di nuovo la marcatura si riscrive.
Vive quindi **una sola** segnalazione per fattura, quella dell'ULTIMO tentativo.
🔴 Senza quel ritiro il primo fallimento chiudeva il lotto per sempre: la
guardia contava la propria marcatura e rispondeva «Lotto bloccato per
segnalazioni critiche attive» anche dopo che l'operatore aveva corretto la
causa. Misurato: con il ritiro dentro la transazione i log critici crescevano
1 → 2 → 3 a ogni tentativo (il rollback annullava il ritiro ma non la scrittura
nuova); fuori, restano 1.

📌 **Chi scrive `stato_esecuzione = 'ERRORE'`**: il runner, nel gestore
d'eccezione **fuori** dalla transazione dello step
(`LottoPipelineRunner._persist_fattura_error_safely`). Dentro, il fail-fast
annullerebbe la riga insieme all'errore che descrive — ed è il motivo per cui
fino al 2026-08-21 il valore `'ERRORE'`, pur ammesso dal CHECK della tabella e
contato dalla summary, **non veniva scritto mai** (misurato: 16 righe su 16 a
`COMPLETED`).

## La capability di riga «riporta in lavorazione» (2026-08-31)

La riga porta la **terna di capability** dell'azione che toglie una fattura dal
lotto, letta da `script.fn_check_fattura_eliminabile_da_lotto` con un
`LEFT JOIN LATERAL` che ne prende il **primo** motivo.

| Campo | Cosa |
|---|---|
| `can_reset_fattura` | l'azione è ammessa? ⭐ **Deriva dal motivo** (`reason IS NULL`), non è una seconda risposta: due sorgenti per la stessa domanda sono due risposte che prima o poi differiscono, e la divergenza sarebbe **muta** — un pulsante acceso su un gesto che il DB rifiuta |
| `can_reset_fattura_reason` | il motivo macchina, per il diario |
| `can_reset_fattura_reason_key` | ⭐ la **chiave i18n**, che è ciò che viaggia: il testo lo compone il frontend. Vocabolario `vendite.lotti.azione_reason.*`, reso con `labelOrCode` perché è del DB ed è **aperto** |

Tutti e tre parlano della **stessa** domanda: *«l'azione fallirebbe?»*.

⚠️ **Permesso ⇒ nascondi, stato ⇒ disabilita CON il motivo** (regola di
`api.md`). Qui è sempre il secondo caso: l'azione resta **a video, spenta, col
perché**. Fino al 2026-08-31 spariva e basta, e un pulsante che sparisce non
spiega niente.

⛔ **Fail-closed**: capability assente ⇒ azione **spenta**. Su un verbo che
cancella il documento dal lotto, «non lo so» non può voler dire «vai».

## Input

- Metodo: `GET`
- Path canonico: `/api/v1/vendite/lotti/{lotto_id}/fatture/`
- Header sicurezza: `Authorization: Bearer <access_token>`
- Path param:
  - `lotto_id` (int) — id del lotto; obbligatorio
- Query param (tutti opzionali; assente o vuoto = nessun filtro):
  - `stato_esecuzione` (string) — esito tecnico della fattura nel lotto,
    vocabolario `PENDING` · `RUNNING` · `COMPLETED` · `ERRORE`
    (`STATI_ESECUZIONE_LOTTO`). Fuori vocabolario → `400 E_VENDITE_VALIDATION`
    col campo (2026-10-20: prima lista vuota; `OK` non è mai esistito)
  - `sort_by` (string) — colonna ordinamento da whitelist
    `LOTTO_FATTURE_SORT_COLUMNS` (`backend/apps/vendite/db/vendite_repository.py`):
    `fattura_id` (default), `numero`, `serie`, `data`,
    `ragione_sociale_completa`, `id_fiscale_univoco_cf_piva`,
    `natura_doc_descrizione`, `stato_doc_fiscale_descrizione`,
    `stato_esecuzione`, `totale_doc`, `totale_a_pagare`
  - `sort_dir` (string) — direzione: `asc` (default) | `desc`
  - `page` (int) — numero pagina, default `1`
  - `page_size` (int) — righe per pagina, default `25`, max `200`

## Output

- `200`:
```json
{
  "data": {
    "count": 1,
    "page": 1,
    "page_size": 25,
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
        "stato_esecuzione": "COMPLETED",
        "numero": 234,
        "serie": null,
        "data": "2026-02-01",
        "numero_documento": "234",
        "billing_account_id": 8,
        "totale_doc": "1234.560000",
        "totale_a_pagare": "1234.560000",
        "soggetto_id": 55,
        "ragione_sociale_completa": "Mario Rossi Srl",
        "id_fiscale_univoco_cf_piva": "01234567890",
        "natura_doc_codice_interno": "NOTA_CREDITO",
        "natura_doc_descrizione": "Nota di credito",
        "errore_messaggio": "Non si può numerare il documento: rettifica righe di altri documenti che non risultano ancora numerati. Documenti da numerare prima: 1.",
        "errore_codice": "E_FATTURA_RETTIFICATA_SENZA_NUMERO",
        "errore_quando": "2026-08-21T17:39:39.675+02:00",
        "errore_livello": "C",
        "errore_bersagli": [{"type": "fattura", "id": "99"}],
        "can_reset_fattura": false,
        "can_reset_fattura_reason": "il lotto e' oltre la soglia di congelamento fiscale",
        "can_reset_fattura_reason_key": "vendite.lotti.azione_reason.lotto_congelato"
      }
    ]
  },
  "meta": { "request_id": "..." }
}
```
- `400`: parametri non validi (`E_VENDITE_VALIDATION`: paginazione, `sort_by`
  fuori whitelist, `sort_dir`, `stato_esecuzione` fuori vocabolario;
  `E_VALIDATION_INPUT` per un intero non leggibile)
- `401`: JWT mancante o non valido
- `403`: permesso modello `("vendite", "fattura")` mancante
- `404`: `E_LOTTO_NON_TROVATO` — lotto inesistente **o fuori perimetro**: la
  testata si legge prima dell'elenco (`lotto_visibile`). ⚠️ 2026-10-20: prima
  rispondeva `200` con zero righe

## Regole

- `lotto_id` proviene dal path URL; il WHERE `fllf.lotto_id = :lotto_id` e' sempre presente.
- Filtri opzionali: assenza equivale a nessun filtro.
- `sort_by` accetta solo valori nella whitelist `LOTTO_FATTURE_SORT_COLUMNS`; valore non valido → 400.
- `sort_dir` accetta `asc`/`desc` (maiuscole e spazi ammessi); valore non valido → 400.
- Tiebreaker deterministico su `fllf.fattura_id` (`sql_order_clause`).
- `page` deve essere >= 1; `page_size` deve essere compreso tra 1 e 200.
- `is_search_endpoint = True` sulla view: attiva throttling `SearchBurstRateThrottle`.
- `stato_doc_fiscale_codice` = `config.stati_doc_fiscale.codice_interno` (chiave
  stabile) — mai la `descrizione`, che e' display e puo' cambiare. Serve a
  MOSTRARE lo stato.
- ⛔ **Il FE NON basa piu' il gate del reset su questo codice** (dal
  2026-08-31). Fino ad allora `LottoDrawer.vue` teneva una lista
  `PRE_FISCALI = ['DRAFT','EMESSA']`: era la **nona copia** della soglia di
  congelamento, e rispondeva a una domanda diversa da quella che serviva.
  ⚠️ *«L'azione fallirebbe?»* e *«e' congelato?»* oggi danno la stessa risposta,
  ma non devono appoggiarsi l'una sull'altra (regola 3 di `D15`): il giorno che
  una precondizione nuova entra nella check DB, la lista di stati non se ne
  accorge. A rispondere e' `can_reset_fattura`.
- Endpoint di sola lettura: nessun `Idempotency-Key` richiesto.
- Endpoint v1 richiede JWT.

## Dipendenze DB

- `vendite.fatturazione_lotti_fatture` (tabella principale)
- `vendite.fatture` (INNER JOIN — billing_account_id, numero, serie, data, totali)
- `anagrafiche.billing_account` (INNER JOIN — recupero soggetto_ruolo_id)
- `anagrafiche.vw_soggetti_ruoli_dettaglio` (INNER JOIN — ragione_sociale_completa, id_fiscale_univoco_cf_piva)
- `config.stati_sdi` (LEFT JOIN — decodifica stato SDI)
- `config.stati_doc_fiscale` (LEFT JOIN — decodifica stato documento fiscale)
- `script.fn_check_fattura_eliminabile_da_lotto` (LEFT JOIN LATERAL — la
  capability di riga). ⭐ `STABLE` e pura, ritorna l'array ORDINATO dei motivi
  con `{codice, reason, reason_key}`. Il suo `Scopo` dichiara **due**
  consumatori: `fn_elimina_fattura_da_lotto`, che solleva il codice del primo
  motivo, e il BE — «per spiegare invece di far fallire». Il secondo esisteva
  solo sulla carta fino al 2026-08-31.
  ⚠️ Il `LATERAL` sta **fuori dal `COUNT`**, come quello dell'errore.

## Note di migrazione

- Query raw nel repository (`VenditeRepository.list_lotto_fatture`); nessuna funzione SQL dedicata.
- Due query per request: `COUNT(*)` + dati con `LIMIT/OFFSET` (pattern offset pagination).
- L'ordinamento usa la whitelist `LOTTO_FATTURE_SORT_COLUMNS` nel repository; mai interpolazione diretta di input utente nel SQL.

## Export

- `GET /api/v1/vendite/lotti/{lotto_id}/fatture/export/?formato=csv|xlsx`
- Stessi filtri e ordinamento della lista (`stato_esecuzione`, `sort_by`,
  `sort_dir`), senza paginazione; stesso permesso `("vendite", "fattura")` e
  stesso `404` sul lotto non visibile.
- Colonne dal catalogo `vendite.lotto_fatture`; oltre `EXPORT_MAX_ROWS` →
  `422 E_UI_EXPORT_LIMIT_EXCEEDED`.
