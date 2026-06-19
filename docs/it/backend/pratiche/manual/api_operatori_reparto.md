# API operatori_reparto (Django)

## Scopo

Esporre via HTTP l'elenco degli **operatori (risorse umane attive) di un reparto**, per
alimentare il picker di assegnazione di un flusso a un operatore specifico del reparto
(vedi [api_flusso_assegnazione](api_flusso_assegnazione.md)).

## Contesto

Endpoint di sola lettura. Delega a `pratiche_service.list_operatori_reparto` →
`PraticheRepository.list_operatori_reparto`, che filtra `anagrafiche.risorse_umane` per
`unita_organizzativa_id` + `attivo = true` e ricava il display dalla ragione sociale del
soggetto collegato (JOIN `soggetti_ruoli` → `soggetti`).

## Input

- Metodo: `GET`
- Path canonico: `/api/v1/pratiche/operatori/`
- Header: `Authorization: Bearer <access_token>`
- Query params:
  - `unita_organizzativa_id` (int, obbligatorio) — ID del reparto

## Output

### 200:
```json
{
  "data": {
    "results": [
      { "id": 3, "display": "Rossi Mario" }
    ]
  }
}
```

### Errori

- `400`: `unita_organizzativa_id` mancante o non numerico (`E_INVALID_ID` / validazione query)
- `401`: JWT mancante o non valido

## Regole

- Ritorna solo risorse umane **attive** (`attivo = true`) del reparto indicato.
- Ordinamento per ragione sociale del soggetto + `id` (tiebreaker deterministico).
- Permission: area `pratiche` (LETTURA).
- Endpoint v1 richiede JWT.

## Dipendenze DB

- `anagrafiche.risorse_umane` (filtro `unita_organizzativa_id` + `attivo`)
- `anagrafiche.soggetti_ruoli`, `anagrafiche.soggetti` (display = `ragione_sociale_completa`)

## Note di migrazione

- Nessuna modifica DB: usa colonne esistenti (`risorse_umane.unita_organizzativa_id`,
  FK `fk_risorse_umane_unita_organizzative`).
