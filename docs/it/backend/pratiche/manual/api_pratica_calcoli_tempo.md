# API pratica_calcoli_tempo (Django)

## Scopo

Esporre via HTTP i calcoli tempo (prestazione da/a) di una pratica.

## Contesto

Endpoint di sola lettura che delega a `pratiche_service.get_calcoli_tempo`. Restituisce i record di `pratiche.calcoli_tempo` per una pratica specifica, arricchiti con `stato_tempo` e `giorni_rimanenti` calcolati in tempo reale dalla funzione DB `fn_valuta_tempo_esecuzione_da_a`. Ogni record traccia il tempo trascorso tra due flussi (da/a), con giorni lordi, sospensione e netti calcolati dal trigger DB.

## Input

- Metodo: `GET`
- Path canonico: `/api/v1/pratiche/<pratica_id>/calcoli-tempo/`
- Header: `Authorization: Bearer <access_token>`
- Nessun parametro query.

## Output

### 200:
```json
{
  "data": {
    "results": [
      {
        "id": 1,
        "pratica_id": 1,
        "flusso_da_id": 10,
        "flusso_a_id": 20,
        "formula_tempo_id": 5,
        "data_inizio_calcolo": "2026-03-01",
        "data_fine_calcolo": "2026-03-06",
        "giorni_lordi": 5,
        "giorni_sospensione": 1,
        "giorni_netti": 4,
        "giorni_formula": 30,
        "sforato": false,
        "giorni_rimanenti": 26,
        "stato_tempo": "OK"
      }
    ]
  }
}
```

- `401`: JWT mancante o non valido

## Regole

- Sola lettura, nessun side-effect.
- I record vengono creati automaticamente dal trigger DB al completamento di un flusso che corrisponde a una formula tempo.
- `data_inizio_calcolo`: data completamento flusso_da (o data apertura pratica se flusso_da e' il primo).
- `data_fine_calcolo`: data completamento flusso_a. NULL se il flusso_a non e' ancora completato.
- `giorni_lordi`, `giorni_sospensione`, `giorni_netti`: calcolati solo quando `data_fine_calcolo` e' valorizzata.
- `sforato`: `true` se `giorni_netti > giorni_formula`.
- `giorni_rimanenti`: giorni restanti prima dello sforamento (calcolati live da `fn_valuta_tempo_esecuzione_da_a`). NULL se non esiste formula applicabile.
- `stato_tempo`: valutazione live del semaforo: `OK`, `WARNING`, `CRITICO`, `SFORATO`. NULL se non esiste formula applicabile.
- Permission: area `pratiche` (lettura implicita).
- Endpoint v1 richiede JWT.

## Dipendenze DB

- `pratiche.calcoli_tempo` (SELECT con filtro pratica_id)
- `pratiche.fn_valuta_tempo_esecuzione_da_a` (LEFT JOIN LATERAL per stato_tempo e giorni_rimanenti live)
- `pratiche.formule_tempo` (giorni_esecuzione come riferimento formula)

## Note di migrazione

- I calcoli tempo sono inseriti e aggiornati esclusivamente dai trigger DB; il backend li espone in sola lettura.
