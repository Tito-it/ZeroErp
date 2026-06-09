# API percorso (Django)

## Scopo

Restituisce il **percorso suggerito** di una pratica = i `template_flussi` del suo
`tipo_prestazione` (in ordine), ciascuno con lo stato di istanziazione. Alimenta
la roadmap FE (`PraticaPercorso.vue`).

## Contesto

I flussi **non** sono materializzati alla creazione della pratica (percorsi
condizionali, §6 brief FE): si creano progressivamente. Questo endpoint mostra il
percorso completo dal catalogo e, per ogni step, se esiste già un flusso
istanziato (l'**ultimo** per quel template, via `LEFT JOIN LATERAL`).

Delega a `pratiche_service.get_percorso` → `PraticheRepository.get_percorso_pratica`.

## Input

- Metodo: `GET`
- Path canonico: `/api/v1/pratiche/<pratica_id>/percorso/`
- Header: `Authorization: Bearer <access_token>`

## Output

### 200:
```json
{
  "data": {
    "results": [
      {
        "template_flusso_id": 9001,
        "template_flusso_codice": "RICHIESTA_CLIENTE",
        "template_flusso_descrizione": "Richiesta del cliente",
        "sequenza": 10,
        "obbligatorio": true,
        "direzione": "ENTRATA",
        "has_handler": false,
        "flusso_id": 50,
        "stato_codice_interno": "COMPLETATO",
        "esito": "POSITIVO"
      },
      {
        "template_flusso_id": 9004,
        "template_flusso_codice": "CONFERMA",
        "sequenza": 40,
        "has_handler": true,
        "flusso_id": null,
        "stato_codice_interno": null,
        "esito": null
      }
    ]
  }
}
```

- `flusso_id = null` → step non ancora creato (`has_handler=true` → step automatico).
- `400`: `pratica_id` non valido (`E_INVALID_ID`).
- `401`: JWT mancante o non valido.

## Regole

- Ordine per `sequenza, template_flusso_id`.
- Un solo flusso per template nel risultato (l'ultimo per id), anche se ne
  esistono più d'uno (robustezza contro doppia creazione).
- La creazione del flusso template-bound avviene via
  `POST /api/v1/pratiche/<id>/flussi/` con `template_flusso_id`; il guard
  prerequisiti DB (esito-aware, BEFORE INSERT) rifiuta se lo step non è abilitato.
- Permission: area `pratiche` (lettura).

## Dipendenze DB

- `pratiche.template_flussi` (catalogo del `tipo_prestazione`)
- `pratiche.flussi` (istanze) + `config.stati_flussi_pratiche`
