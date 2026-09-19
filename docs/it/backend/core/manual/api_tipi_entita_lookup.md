# API Lookup Tipi di Entità — il vocabolario di `config.tipi_entita`

## Scopo

Restituire i **tipi di entità vivi** del catalogo `config.tipi_entita` —
`codice`, `etichetta_key` (l'indirizzo i18n che il DB dichiara per ciascuno),
`key_selector` — per i filtri e i picker che nominano *su quale cosa* è
successo qualcosa. Primo consumatore: la tendina «Entità» del giornale
trasversale (`GiornaleListView`, pezzo G dell'osservabilità).

## Contesto

`config.tipi_entita` ha PK `codice` (testo) e **non ha `id` né
`descrizione`**: il lookup generico (`GET /core/lookup/codici/?rel=…`)
pretende un id intero e non la può servire. E ciò che il client vuole non è
una descrizione: è l'**indirizzo della traduzione** che il catalogo dichiara
riga per riga (`etichetta_key`), da risolvere nei locales con `labelOrCode` —
lo stesso patto dei tre livelli scritto in frontend-standards §Multilingua.

⭐ **Perché nasce (2026-09-19).** La tendina del giornale si era ricopiata
**sette** codici a mano; il catalogo ne aveva già **nove** (`FLUSSO` e
`DEFINIZIONE_WORKFLOW` mancavano, senza nessun errore). Un vocabolario del DB
si legge, non si specchia: il decimo tipo comparirà nella tendina il giorno
del suo seed, senza toccare il frontend.

⚠️ `bersagli.js` (il resolver «Apri …» dei bersagli di errore) porta ancora la
propria copia delle `etichettaKey` per tipo: è dichiarato lì, e questo lookup
è la sede da cui potrà leggerle.

## Endpoint

```http
GET /api/v1/core/lookup/tipi-entita/
```

View: `LookupTipiEntitaView` (`apps.core.api.views_lookup`), `DomainAPIView`
con **`skip_area_check = True`** — cross-dominio: lo consumano `vendite`,
`amm-software` e il `core`. Nessun parametro.

## Input

Nessuno. Solo JWT.

## Output

Envelope di lookup **`{"data": {"results": [...]}}`** — mai la lista nuda
(api.md §L'ENVELOPE DI UN LOOKUP: `useGlobalLookup` legge `r.data.data.results`).

```json
{
  "data": {
    "results": [
      { "codice": "COMMESSA", "etichetta_key": "config.tipi_entita.commessa", "key_selector": "id" },
      { "codice": "FATTURA",  "etichetta_key": "config.tipi_entita.fattura",  "key_selector": "id" },
      { "codice": "LOTTO",    "etichetta_key": "config.tipi_entita.lotto",    "key_selector": "id" }
    ]
  },
  "meta": { "request_id": "…" }
}
```

## Regole

- Solo i tipi **vivi** (`obsoleto_dal IS NULL`): un tipo ritirato resta a
  catalogo per leggere il diario, non per essere scelto in un filtro.
- Ordine per `codice`; nessuna paginazione (popolazione limitata per catalogo).
- Il testo **non** viaggia: viaggia la chiave, il frontend traduce con ripiego
  sul codice (`labelOrCode`).
- Lato FE si consuma con `useGlobalLookup('config.tipi_entita', lookupTipiEntita)`:
  cache condivisa per chiave, una fetch per sessione.

## Dipendenze DB

- `config.tipi_entita` (seed `80_data/sql/config/tipi_entita.csv`).

## Test

- `apps/core/tests/api/test_lookup_tipi_entita_api.py` — porta (401), forma
  dell'envelope con repository finto, e **una lettura sul DB provvisto**
  (colonne per nome, tipi vivi = `count(*)` del catalogo).
