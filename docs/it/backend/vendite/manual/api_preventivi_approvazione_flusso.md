# API preventivi approvazione-flusso (Django)

## Scopo

Esporre via HTTP l'accoppiamento **M2** (brief BE §8.3): sul percorso pratica, il
completamento del flusso `APPROVAZIONE_CLIENTE` **guida** l'accettazione del
preventivo collegato, in un'unica transazione.

## Contesto

Endpoint di scrittura del dominio vendite. Delega a
`preventivi_service.completa_approvazione_da_flusso`, che in `@transaction.atomic`:

1. completa il flusso pratica (`pratiche_service.completa_flusso`, esito
   obbligatorio — vincolo DB `COMPLETATO ⇒ esito NOT NULL`);
2. su esito `POSITIVO`, porta il preventivo collegato a `ACCETTATO` con politica
   di fatturazione **neutra** (`fatturazione_immediata=false`, `competenza_mese`
   = mese corrente). L'autorità sulla politica, sul percorso pratica, è l'handler
   `vendita.push_preventivo` al flusso `CONFERMA`, che la sovrascrive dalla
   configurazione (c7-2). Esito `NEGATIVO`: solo completamento del flusso (il
   preventivo resta `EMESSO`, gestione manuale — v1).

Direzione delle dipendenze `vendite→pratiche` (consentita); import lazy di
`pratiche_service`.

## Input

- Metodo: `POST`
- Path canonico: `/api/v1/vendite/preventivi/approvazione-flusso/` (collection-level:
  nessun id in path; il preventivo è risolto a BE dal legame `pratiche_sorgenti`
  ROOT della pratica)
- Header: `Content-Type: application/json`, `Authorization: Bearer <access_token>`
- Body:
  - `pratica_id` (int, **obbligatorio**) — pratica del flusso (da cui si risolve il preventivo ROOT)
  - `flusso_id` (int, **obbligatorio**) — id del flusso `APPROVAZIONE_CLIENTE` da completare
  - `esito` (string, **obbligatorio**) — `POSITIVO` | `NEGATIVO` | `PARZIALE` | `NON_APPLICABILE`
  - `note_esito` (string, opzionale)

## Output

### 200:
```json
{
  "data": {
    "preventivo_id": 4711,
    "flusso_esito": "POSITIVO",
    "preventivo": { "stato": "ACCETTATO" }
  }
}
```

- `preventivo` è `null` se l'esito non è `POSITIVO`.
- `400`: `flusso_id`/`preventivo_id` non validi (`E_PREV_VALIDAZIONE`), esito non
  valido (`E_FLUSSO_VALIDATION`), transizione preventivo non ammessa, nessun
  preventivo ROOT collegato alla pratica (`E_VENDITA_PREVENTIVO_NON_COLLEGATO`,
  su esito POSITIVO).
- `401`: JWT mancante o non valido.

## Regole

- Una sola transazione: se l'accettazione del preventivo fallisce, anche il
  completamento del flusso rolla (non possono divergere).
- La FE invoca questo endpoint **solo** per `APPROVAZIONE_CLIENTE` di una pratica
  `PREVENTIVI_*`; per gli altri flussi usa il generico
  `/api/v1/pratiche/<id>/flussi/<id>/stato/`.
- Re-invocazione: se il preventivo è già `ACCETTATO`, `cambia_stato` è no-op
  (idempotente).
- Permission: `cambia_stato_preventivi` (area `vendite`).

## Dipendenze

- `preventivi_service.completa_approvazione_da_flusso`
- `pratiche_service.completa_flusso` → `pratiche.flussi` (transizione + vincolo esito)
- `vendite.fn_cambia_stato_preventivo` (EMESSO/ACCETTATO → ACCETTATO)

## Note

- La politica neutra scritta qui è transitoria: l'handler `vendita.push_preventivo`
  la sovrascrive a `CONFERMA`. Vedi `push_preventivo_handler.md`.
