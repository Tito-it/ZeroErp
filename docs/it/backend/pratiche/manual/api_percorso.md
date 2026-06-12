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
        "esito": "POSITIVO",
        "ripetibile_adesso": false,
        "completato": true,
        "percorribile": true,
        "bloccante": false,
        "ramo": "COMPLETATO"
      },
      {
        "template_flusso_id": 9004,
        "template_flusso_codice": "CONFERMA",
        "sequenza": 40,
        "has_handler": true,
        "flusso_id": null,
        "stato_codice_interno": null,
        "esito": null,
        "ripetibile_adesso": true,
        "completato": false,
        "percorribile": false,
        "bloccante": false,
        "ramo": "FUTURO"
      }
    ]
  }
}
```

- `flusso_id = null` → step non ancora creato (`has_handler=true` → step automatico).
- `400`: `pratica_id` non valido (`E_INVALID_ID`).
- `401`: JWT mancante o non valido.

### Campi workflow v2 (2026-06-12, D3/D4 analisi-pratiche-workflow-v2)

- `ripetibile_adesso` (bool, da `fn_check_ripetibilita_flusso`) — una NUOVA
  istanza dello step è creabile ora, secondo la regola del template
  (`MAI` / `SE_NON_POSITIVO` / `SEMPRE`) e l'ultima istanza (`MAX(id)`).
  Il FE mostra "Ripeti" solo se `true` **e** esiste già un'istanza.
- `completato` / `percorribile` / `bloccante` (bool, da
  `fn_check_chiusura_pratica`) — fotografia chiusura: `bloccante=true` =
  obbligatorio, non completato, ancora percorribile (impedisce CHIUSA,
  guard DB 485).
- `ramo` (string) — sintesi per la resa visiva, 4 stati:
  - `COMPLETATO` — almeno un'istanza chiusa;
  - `PERCORRIBILE` — prerequisiti soddisfatti, eseguibile ora;
  - `FUTURO` — prerequisiti non ancora decisi (step a valle);
  - `RAMO_CHIUSO` — un prerequisito è stato DECISO (istanza COMPLETATO)
    ma mai con l'esito richiesto: il bivio ha preso l'altra strada. Stato
    "attuale": un retry del predecessore (se ripetibile) può riaprirlo.
  La verità esito-aware resta nella fn DB `fn_check_prerequisiti_flusso`
  (riusata nella query, nessuna regola duplicata lato BE).

## Regole

- Ordine per `sequenza, template_flusso_id`.
- Un solo flusso per template nel risultato (l'ultimo per id), anche se ne
  esistono più d'uno (con la regola di ripetibilità D3 le istanze multiple
  sono legittime: vince la più recente per `MAX(id)`).
- La creazione del flusso template-bound avviene via
  `POST /api/v1/pratiche/<id>/flussi/` con `template_flusso_id`; i guard DB
  BEFORE INSERT rifiutano se lo step non è abilitato (prerequisiti
  esito-aware) o non è ripetibile (`409 PRATICHE_FLUSSO_NON_RIPETIBILE`,
  catalogo DB id 483).
- Permission: area `pratiche` (lettura).

## Dipendenze DB

- `pratiche.template_flussi` (catalogo del `tipo_prestazione`)
- `pratiche.flussi` (istanze) + `config.stati_flussi_pratiche`
- `pratiche.fn_check_ripetibilita_flusso` (D3 — `ripetibile_adesso`)
- `pratiche.fn_check_chiusura_pratica` (D4 — `completato`/`percorribile`/`bloccante`)
- `pratiche.fn_check_prerequisiti_flusso` (distinzione `RAMO_CHIUSO`/`FUTURO`)
