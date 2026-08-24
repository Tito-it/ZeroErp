# API lotto_segnalazioni_summary (Django)

## Scopo

Esporre via HTTP il riepilogo segnalazioni attive di un lotto, con indicazione di blocco avanzamento step.

## Contesto

Endpoint di consultazione che invoca `fn_get_lotto_segnalazioni_summary` in `apps/vendite/services/pipeline_service.py`,
il quale delega a `LottoSegnalazioniService.evaluate_lotto_status`.

View in `apps/vendite/api/views.py`:

- `ApiLottoSegnalazioniSummary`
- `ApiLottoSegnalazioniSummary`

## Input

- Metodo: `GET`
- Path canonico: `/api/v1/vendite/lotti/{lotto_id}/segnalazioni/`
- Header sicurezza: `Authorization: Bearer <access_token>`
- Path params: `lotto_id` (int)
- Query param: `livello` — `C` critiche (default) · `W` avvisi · `I` attenzioni.
  Normalizzato (trim + maiuscolo) dalla view; fuori vocabolario → `400`.
  ⚠️ Nome italiano come gli altri query param di dominio, e mai `format` o altri
  nomi che DRF intercetta.

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
      "fatture_stato_esecuzione_errore_count": 0
    },
    "livello": "C",
    "segnalazioni": [
      {
        "riga_key": "FATTURA:3284",
        "origine": "FATTURA",
        "livello": "C",
        "messaggio": "Non si può numerare il documento 15353: …",
        "data_ora": "2026-08-21T17:39:39.675+02:00",
        "codice": "E_FATTURA_RETTIFICATA_SENZA_NUMERO",
        "fase": null,
        "fattura_id": 15353,
        "ragione_sociale_completa": "Azienda PG Test Natura",
        "totale_doc": "-20.740000"
      }
    ]
  },
  "meta": { ... }
}
```

- `400`: `lotto_id` non valido o <= 0, oppure `livello` fuori vocabolario

## L'elenco, non solo i conteggi (2026-08-21)

I conteggi dicono **quante** segnalazioni ci sono; `segnalazioni[]` dice **cosa
sono**, per il livello richiesto.

⭐ **Stessa fonte e stessi filtri dei conteggi**, e va tenuto così:
`fatture_log` attraverso il ponte del lotto **+** `fatturazione_lotti_log`,
entrambe con `disabilitato IS FALSE` — esattamente ciò che somma
`fn_get_lotto_segnalazioni_summary`. Un elenco che leggesse una fonte sola
mostrerebbe «1 critica» nel banner e zero righe nella scheda, e la divergenza
fra un contatore e il suo dettaglio è peggio del dettaglio assente.
📌 Verificato sul lotto 6034: **C=1 → 1 riga · W=2 → 2 righe · I=11 → 11 righe**.

⚠️ Il livello `I` esiste **solo** sulle segnalazioni di LOTTO (il riepilogo
conta `lotto_info_count` e non ha il gemello per le fatture): il ramo fatture
resta nella query e per `I` semplicemente non produce righe.

⭐ **Perché conteggi ed elenco viaggiano insieme**: li legge la stessa scheda e
devono raccontare lo stesso istante. Due chiamate separate potrebbero cadere a
cavallo di un giro e mostrare «2 critiche» sopra un elenco di tre.

⚠️ **`riga_key` è la chiave di riga** (`<origine>:<id>`), e serve: `data_ora`
**non è univoco** — misurato, sei segnalazioni con lo stesso microsecondo,
scritte dallo stesso giro — e il solo `id` nemmeno, perché le due tabelle hanno
sequenze indipendenti. È anche il tiebreak dell'`ORDER BY`: a parità di istante
l'ordine dev'essere deterministico, o due letture della stessa pagina si
scambiano righe.

⚠️ **Nessuna paginazione, per ora**: cap a 500 righe con `logger.warning` sul
troncamento — un elenco tagliato somiglia in tutto a uno completo, e sopra c'è
un contatore che direbbe un numero diverso. La paginazione arriva con il
catalogo lista (`ui.lista_definizione`), prerequisito DB.

⚠️ **`messaggio` non si riscrive**: contiene la frase del database, l'unica che
nomina il documento bloccante e la via d'uscita. `ragione_sociale_completa` e
`totale_doc` si **affiancano** — un id interno non è visibile da nessuna parte
nell'interfaccia, quindi senza nome e importo «documento 835» non identifica
niente. Sulle segnalazioni di LOTTO sono `null` e il consumer mostra `fase`.
- `500`: errore applicativo gestito dal middleware

## Regole

- `lotto_id` obbligatorio e > 0 (validato dal servizio con `ErrorManager.require`).
- `critical_count` = somma `fatture_critical_count` + `lotto_critical_count`.
- `warning_count` = somma `fatture_warning_count` + `lotto_warning_count`.
- `attention_count` = `lotto_info_count` (livello "I" — info operativa).
- `is_error = true` se `critical_count > 0` oppure se `fatture_stato_esecuzione_errore_count > 0`.
- `blocks_next_step = true` se `is_error = true` (nessun avanzamento pipeline ammesso).
- `summary.fatture_stato_esecuzione_errore_count` — conteggio fatture del lotto con `stato_esecuzione = 'ERRORE'`; restituito direttamente da `fn_get_lotto_segnalazioni_summary` (6ª colonna).
- Endpoint di sola lettura: nessun `Idempotency-Key` richiesto.
- Endpoint v1 richiede JWT.

## Dipendenze DB

- `vendite.fn_get_lotto_segnalazioni_summary` (funzione SQL)
- `vendite.fatture_log` (sorgente segnalazioni fattura)
- `apps.vendite.services.lotto_segnalazioni_service.LottoSegnalazioniService`

## Note di migrazione

- Endpoint introdotto per supporto UI nella visualizzazione stato segnalazioni prima di avanzare step pipeline.
