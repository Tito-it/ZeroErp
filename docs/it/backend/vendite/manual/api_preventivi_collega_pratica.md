# API preventivi collega-pratica (Django)

## Scopo

Aggancia un preventivo come **ROOT** a una pratica (`pratiche_sorgenti`). Usato a
PREVENTIVAZIONE sul percorso pratica-first PREVENTIVI: è la **fonte di verità** del
legame preventivo↔pratica da cui l'handler `vendita.push_preventivo` e l'endpoint
M2 (`approvazione-flusso`) risolvono il preventivo.

## Contesto

Delega a `preventivi_service.collega_pratica` → `PraticheRepository.upsert_pratica_sorgente`
(`sorgente_codice='PREVENTIVO'`, `ruolo_link='ROOT'`, `sorgente_uid = preventivo.uid`).
Idempotente (ON CONFLICT). Direzione dipendenze `vendite→pratiche`, import lazy.

## Input

- Metodo: `POST`
- Path canonico: `/api/v1/vendite/preventivi/<preventivo_id>/collega-pratica/`
- Header: `Content-Type: application/json`, `Authorization: Bearer <access_token>`
- Body:
  - `pratica_id` (int positivo, **obbligatorio**): assente o non valido → 400
    `E_PREV_VALIDAZIONE` col campo (2026-10-20: prima un 500)
  - `flusso_id` (int positivo, opzionale): ancora il ROOT al flusso d'origine
    (aggancio per-flusso; il guard DB verifica che il flusso sia della pratica).
    Omesso = link non da flusso

## Output

### 200:
```json
{ "data": { "preventivo_id": 4711, "pratica_id": 200, "flusso_id": 900, "uid": "..." } }
```

`flusso_id` è `null` se non inviato.

- `400`: `pratica_id`/`flusso_id` non validi (`E_PREV_VALIDAZIONE`); codice sorgente non in `config.sorgenti` (`E_PRATICA_SORGENTE_TIPO_INVALIDO`).
- `404`: preventivo non trovato (`E_PREV_NOT_FOUND`).
- `401`: JWT mancante o non valido.

## Regole

- Idempotente: ri-chiamata sullo stesso `(pratica, preventivo, ROOT)` = no-op.
- Permission: `cambia_stato_preventivi` (area `vendite`).
- La FE lo chiama al primo `saved` del `PreventiviDrawer` aperto in contesto
  pratica (guard con flag per non ripetere sui salvataggi successivi).

## Dipendenze DB

- `pratiche.pratiche_sorgenti` (UNIQUE `pratica_id, sorgente_tipo_id, sorgente_uid, ruolo_link`)
- `config.sorgenti` (`codice_interno='PREVENTIVO'`)
- `vendite.preventivi` (`uid`)
