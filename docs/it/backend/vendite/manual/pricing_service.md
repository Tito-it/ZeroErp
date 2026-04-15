# Pricing Service (resolver prezzi v5)

## Scopo

Wrapper Python su due funzioni DB del pricing v5:

* `vendite.fn_resolve_prezzo_listino_v2` — resolver 3 stadi (promo → contratto
  → matrice categoria)
* `vendite.fn_resolve_prezzo_composito` — BoM ibrido A/B1/B2 per articoli
  compositi

Il servizio **non duplica** la logica di pricing (vive nel DB). Fa solo:

* validazione tipizzata dell'input (UUID, positive int, date)
* delega alla funzione DB
* traduzione delle `DatabaseError` (P0001 via `script.fn_log_and_raise_error`)
  in `ServiceError` preservando il codice di dominio originale quando
  riconosciuto

Riferimenti:
* [fn_resolve_prezzo_listino_v2](/dbzero/vendite/manual/fn_resolve_prezzo_listino_v2)
* [fn_resolve_prezzo_composito](/dbzero/vendite/manual/fn_resolve_prezzo_composito)

## Contesto

Il chiamante tipico del servizio e' la pipeline di creazione commessa
attivita' / fatturazione che deve calcolare il prezzo unitario di una
riga e salvare lo snapshot su `commesse_attivita` /
`attivita_fatturabili`. `emittente_soggetto_ruolo_id` e'
derivato dal JWT dell'operatore (mapping 1-a-1) **dal chiamante**, non
dal service. Il service riceve l'id gia' risolto.

## Input

### `PricingService.resolve_prezzo(...)`

| Parametro | Tipo | Obbligatorio | Regola |
|---|---|---|---|
| `articolo_id` | UUID \| str | si | UUID valido (coercito a str normalizzata) |
| `uom_id` | int | si | > 0 |
| `data_riferimento` | date | si | oggetto `datetime.date` (no stringa ISO) |
| `ba_id` | int | si | > 0 |
| `utility_id` | int | si | > 0 |
| `emittente_soggetto_ruolo_id` | int | si | > 0 |
| `classe_utenza_id` | int \| None | no | > 0 se presente |

### `PricingService.resolve_prezzo_composito(...)`

Stessi parametri di `resolve_prezzo`, ma `prodotto_id` al posto di `articolo_id`.

## Output

### `resolve_prezzo` → `dict`

Schema coerente con `fn_resolve_prezzo_listino_v2`:

```json
{
  "prezzo_finale": "12.5000",
  "prezzo_base_snapshot": "10.0000",
  "tipo_variazione_applicata": "PERCENTUALE",
  "valore_variazione_applicata": "25.0000",
  "origine": "CATEGORIA",
  "listino_id": 42,
  "listino_versione_id": 7,
  "listino_riga_id": 1001,
  "contratto_id": null,
  "promo_id": null,
  "categoria_cliente_listino_id": 15
}
```

### `resolve_prezzo_composito` → `list[dict]`

Schema coerente con `fn_resolve_prezzo_composito`. Ritorna N righe (CASO A)
o 1 riga (CASO B1/B2) secondo la presenza di componenti esposti nel BoM:

```json
[
  {
    "componente_id": "019bac81-...",
    "uom_id": 3,
    "prezzo_unitario": "5.0000",
    "iva_id": 1,
    "descrizione_fattura": "Componente X",
    "esposto_in_fattura": true
  }
]
```

## Regole

### Mapping errori DB → ServiceError

Quando la funzione DB solleva un errore applicativo (P0001 via
`fn_log_and_raise_error`), il service cerca un marker noto nel MESSAGE:

| MESSAGE (substring) | Codice applicativo preservato |
|---|---|
| "Nessun prezzo listino risolto" | `E_PREZZO_LISTINO_NON_TROVATO` |
| "Nessuna mappa categoria" | `E_CATEGORIA_LISTINO_NON_MAPPATA` |
| "Riga listino non trovata" | `E_PREZZO_LISTINO_RIGA_NON_TROVATA` |
| "non negoziato" | `E_ARTICOLO_NON_NEGOZIATO_SU_CONTRATTO_C` |

Se nessun marker matcha: fallback `E_VENDITE_PRICING_FAILED`. Il MESSAGE
originale viene sempre propagato in `detail` del ServiceError, cosi' il
frontend puo' mostrarlo se ha `DJANGO_API_EXPOSE_TECHNICAL_DETAILS=1`.

### Validazione input

Tutti i parametri sono validati prima della chiamata DB:

* UUID: coercito via `uuid.UUID(value)` — errore → `E_VENDITE_VALIDATION`
* `uom_id`/`ba_id`/`utility_id`/`emittente_soggetto_ruolo_id`: int > 0
  stretto (rifiuta bool e stringhe). Usa `PayloadValidator.guard_positive_int`.
* `data_riferimento`: deve essere `datetime.date`. Le stringhe ISO vanno
  parsate dal chiamante via `parse_iso_date`.
* `classe_utenza_id`: opzionale; se presente deve essere int > 0.

### Logging

Il validator e' istanziato con `log_to_db=True`: ogni errore di validazione
viene loggato su `script.log_errori` con `function_name="pricing_service"`.
Gli errori propagati dal DB hanno invece `function_name=fn_resolve_prezzo_*`
al livello del trigger che li ha sollevati.

## Dipendenze DB

* `vendite.fn_resolve_prezzo_listino_v2(uuid, bigint, date, bigint, integer, bigint, integer)`
* `vendite.fn_resolve_prezzo_composito(uuid, bigint, date, bigint, integer, bigint, integer)`
* `script.fn_log_and_raise_error` (helper errori DB)
* Tabelle consultate dalle funzioni: `vendite.promo_articoli`,
  `vendite.contratti`, `vendite.contratti_righe`, `vendite.listini*`,
  `anagrafiche.categorie_clienti_listini`, `anagrafiche.billing_account`

## Note di migrazione

F2-BE-09 + F2-BE-10 chiusi insieme perche' `resolve_prezzo_composito`
internamente chiama `resolve_prezzo_listino_v2` per i componenti; testarli
in isolamento sarebbe fragile.

Cleanup post-F2 (F1-DB-24..28): la vecchia `fn_resolve_prezzo_listino` e
`listini_associazioni` sono ancora referenziate in
[listini_repository.py](../../../../backend/apps/vendite/db/listini_repository.py)
`search_resolve_prezzo`. F2-BE-13 rimuovera' quel path prima che il DB
faccia `DROP FUNCTION` del wrapper deprecato. Sequenza documentata nel
[piano v5](/dev/work-in-progress/sviluppo-listini-v5) sezione "Coordinamento
cleanup".
