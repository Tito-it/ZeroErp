# API Vendite Form-Defaults (BA-aware e contestuali)

## Scopo

Endpoint **form-defaults** read-only consumati dai drawer FE all'apertura
o al cambio di un campo chiave (BA per contratti/preventivi, sorgente per
clone versione). Centralizzano lato BE la risoluzione di valori di default
oggi cablati o derivati lato FE: `valuta_id`/`termine_pagamento_id` dal
cliente del BA, `categoria_cliente_id_snapshot` dal BA, `default_valido_*`
da `config.parameters`, suffisso codice clone, esistenza di BOZZE.

Riferimento concettuale:
[analisi-refactor.frontend-vendite.md §A5/A8](/dev/work-done/analisi-refactor.frontend-vendite#a5-defaults-contratto-da-form-defaults-backend) (Fase 2.B3-B5).

## Contesto

Single source of truth lato BE: `apps/vendite/services/vendite_form_defaults_service.py`.
Il service combina:

- `BillingAccountRepository.get_lookup_by_id` — categoria_cliente, utility/istanza
- query diretta `anagrafiche.clienti` per la tripletta `(istanza_utility_id,
  soggetto_ruolo_id, utility_id)` — termine_pagamento_id, iva_id,
  modalita_pagamento_id
- `ParameterService.get_defaults` — `VENDITE_*` lead_gg / suffix
- BB centralizzato `resolve_valuta_default` (`apps.anagrafiche.services.valuta_resolver`)
  per la cascata `valuta_id`, allineato 2026-05-29 alla fn DB
  `vendite.fn_get_valuta_id` (single source of truth cross-layer):
  `BA.valuta_id` → EF del BA (catena `fn_get_emittente_fiscale_pk`) →
  EF utente loggato (con fallback gestore globale) → primo
  `anagrafiche.gestori` per id → `{}`
- `ListiniRepository.get_listino` / `get_versione` / `list_versioni` per le
  3 view contestuali alle versioni listino

Tutti gli endpoint richiedono JWT operatore e area `vendite` LETTURA.
Eventuali override personali dei parameter sono applicati passando
l'`auth_user_id` derivato dal JWT.

## Endpoint

### `GET /api/v1/vendite/contratti/form-defaults/` (Fase 2.B3)

Defaults form contratto. `billing_account_id` opzionale.

| Query param | Tipo | Note |
| --- | --- | --- |
| `billing_account_id` | int | Se presente, popola i campi BA-derived (categoria_cliente, utility, valuta). |

Risposta `200`:

```json
{
  "data": {
    "billing_account_id": 123,
    "default_valido_dal": "2026-04-30",
    "default_data": "2026-04-30",
    "categoria_cliente_id_snapshot": 7,
    "categoria_cliente_codice": "STANDARD",
    "categoria_cliente_descrizione": "Standard",
    "utility_id": 1,
    "istanza_utility_id": 100,
    "utility_codice": "GAS",
    "utility_descrizione": "Gas",
    "valuta_id": 1,
    "valuta_codice": "EUR",
    "valuta_descrizione": "Euro"
  }
}
```

`valuta_id` (aggiunto 2026-05-29) segue la catena del BB
`resolve_valuta_default` (sezione preventivi sotto). Senza
`billing_account_id`: campi BA-derived = `null`, presenti solo
`default_valido_dal`, `default_data` e (se EF utente o gestore configurato)
i campi valuta.

Errori: `E_VENDITE_NOT_FOUND` (404) se `billing_account_id` non esiste.

Consumer FE: `ContrattoDrawer.vue`.

### `GET /api/v1/vendite/offerte/form-defaults/` (2026-05-29)

Defaults form offerta commerciale. `billing_account_id` opzionale.
Stesso pattern di contratti (testata + eccezioni, senza termini/iva sul
testata).

| Query param | Tipo | Note |
| --- | --- | --- |
| `billing_account_id` | int | Se presente, popola i campi BA-derived (categoria_cliente, utility, valuta). |

Risposta `200`:

```json
{
  "data": {
    "billing_account_id": 100,
    "categoria_cliente_id_snapshot": 7,
    "categoria_cliente_codice": "STANDARD",
    "categoria_cliente_descrizione": "Standard",
    "utility_id": 3,
    "istanza_utility_id": 200,
    "utility_codice": "GAS",
    "utility_descrizione": "Gas",
    "valuta_id": 1,
    "valuta_codice": "EUR",
    "valuta_descrizione": "Euro"
  }
}
```

Risoluzione `valuta_id`: vedi sezione preventivi sotto (stesso BB).

Errori: `E_VENDITE_NOT_FOUND` (404) se `billing_account_id` non esiste.

Consumer FE: `OffertaDrawer.vue` (integrazione FE pendente).

### `GET /api/v1/vendite/preventivi/form-defaults/` (Fase 2.B4)

Defaults form preventivo BA-aware (valuta + termini + IVA dal cliente).

| Query param | Tipo | Note |
| --- | --- | --- |
| `billing_account_id` | int | Se presente, risolve termini/iva/valuta. |

Risposta `200`:

```json
{
  "data": {
    "billing_account_id": 123,
    "default_validita_al": "2026-05-30",
    "valuta_id": 1,
    "valuta_codice": "EUR",
    "valuta_descrizione": "Euro",
    "termine_pagamento_id": 12,
    "termine_pagamento_codice": "30GG",
    "termine_pagamento_descrizione": "30 giorni",
    "iva_id": 3,
    "iva_codice": "22",
    "iva_descrizione": "IVA 22%",
    "modalita_pagamento_id": 5,
    "modalita_pagamento_codice": "BONIFICO",
    "modalita_pagamento_descrizione": "Bonifico bancario",
    "utility_id": 1,
    "istanza_utility_id": 100,
    "utility_codice": "GAS",
    "utility_descrizione": "Gas"
  }
}
```

Risoluzione `valuta_id` (BB `resolve_valuta_default`, allineato a
`vendite.fn_get_valuta_id` — single source of truth cross-layer
2026-05-29):

1. `billing_account.valuta_id` se valorizzato
2. altrimenti `emittenti_fiscali.valuta_id` dell'EF associato al BA
   (catena `fn_get_emittente_fiscale_pk`)
3. altrimenti `emittenti_fiscali.valuta_id` dell'EF dell'utente loggato
   (proxy form-defaults: il documento non esiste ancora; include fallback
   gestore globale `is_default` via `get_emittente_fiscale_id_for_user`)
4. altrimenti `anagrafiche.gestori.valuta_id` (primo per id) — mirror del
   livello 3 di `fn_get_valuta_id`
5. altrimenti `null` (operatore valorizza)

Risoluzione `termine_pagamento_id` / `iva_id` / `modalita_pagamento_id`:
dal cliente associato al BA via tripletta UNIQUE
`(istanza_utility_id, soggetto_ruolo_id, utility_id)`. Se nessun cliente
combacia (BA fornitore o anagrafica gestita altrove): tutti `null`.

Errori: `E_VENDITE_NOT_FOUND` (404) se `billing_account_id` non esiste.

Consumer FE: `PreventiviDrawer.vue` (watch su `form.billing_account_id`,
sovrascrittura solo dei campi vuoti per non distruggere scelte utente).

### `GET /api/v1/vendite/listini/<listino_id>/versioni/form-defaults/` (Fase 2.B5a)

Defaults per "Nuova versione" listino.

Risposta `200`:

```json
{
  "data": {
    "listino_id": 12,
    "default_codice_versione": "",
    "default_valido_dal": "2026-04-30",
    "default_valido_al": null,
    "min_valido_dal": null,
    "has_existing_draft": true,
    "existing_drafts": [
      {"id": 33, "codice_versione": "v_draft"}
    ]
  }
}
```

`default_valido_dal` = oggi + `VENDITE_LISTINI_NEW_VERSIONE_LEAD_GG`
(default `0`). `existing_drafts` consente al FE di mostrare warning
"esistono gia' bozze" senza dover caricare la lista versioni.

Errori: `E_VENDITE_NOT_FOUND` (404) se il listino non esiste.

Consumer FE: `VersioneFormDrawer.vue`.

### `GET /api/v1/vendite/listini/<listino_id>/versioni/<src_versione_id>/clone-defaults/` (Fase 2.B5b)

Defaults per il clone di una versione esistente.

Risposta `200`:

```json
{
  "data": {
    "listino_id": 12,
    "source_versione_id": 33,
    "source_codice_versione": "v1",
    "source_valido_dal": "2026-01-01",
    "source_valido_al": null,
    "default_codice_versione": "v1-clone",
    "default_valido_dal": "2026-05-01",
    "default_valido_al": null,
    "min_valido_dal": "2026-01-01",
    "is_retroactive_default": false,
    "retroactive_warning_key": "listini.warning_retroattivo"
  }
}
```

`default_codice_versione` = `source_codice_versione` + suffisso parameter
`VENDITE_LISTINI_CLONE_VERSIONE_CODICE_SUFFIX` (default `-clone`).
`default_valido_dal` = oggi + `VENDITE_LISTINI_CLONE_VERSIONE_LEAD_GG`
(default `1`, "domani"). `min_valido_dal` = `source.valido_dal` (vincolo
D2 backend: target non puo' essere antecedente alla sorgente).

Errori: `E_VENDITE_NOT_FOUND` (404) se la versione sorgente non esiste.

Consumer FE: `CloneVersioneDrawer.vue`.

### `GET /api/v1/vendite/listini/<listino_id>/versioni/<versione_id>/close-defaults/` (Fase 2.B5c)

Defaults per la chiusura programmata/immediata di una versione.

Risposta `200`:

```json
{
  "data": {
    "listino_id": 12,
    "versione_id": 33,
    "stato_codice": "ATTIVA",
    "current_valido_al": null,
    "has_existing_chiusura": false,
    "default_valido_al": "2026-04-30",
    "min_valido_al": "2026-04-30"
  }
}
```

`default_valido_al` = `current_valido_al` se gia' programmata (UX
"modifica chiusura"), altrimenti oggi +
`VENDITE_LISTINI_CLOSE_VERSIONE_LEAD_GG` (default `0`).
`min_valido_al` = oggi (no chiusura nel passato lato UX; la cessazione
storica passa per il workflow data-driven sui contratti, non sui listini).

Errori: `E_VENDITE_NOT_FOUND` (404) se la versione non esiste.

Consumer FE: `ChiudiVersioneDialog.vue`.

## Parameter codes consumati

Mantenere i seed e i fallback hardcoded del service allineati ai default
del FE (`paramInt`/`paramString`):

| Codice | Default | Usato da |
| --- | --- | --- |
| `VENDITE_CONTRATTO_DEFAULT_VALIDO_DAL_LEAD_GG` | `0` | contratti form-defaults |
| `VENDITE_CONTRATTO_DEFAULT_DATA_LEAD_GG` | `0` | contratti form-defaults |
| `VENDITE_PREVENTIVO_DEFAULT_VALIDITA_GG` | `30` | preventivi form-defaults |
| `VENDITE_LISTINI_NEW_VERSIONE_LEAD_GG` | `0` | versione new defaults |
| `VENDITE_LISTINI_CLONE_VERSIONE_LEAD_GG` | `1` | versione clone defaults |
| `VENDITE_LISTINI_CLONE_VERSIONE_CODICE_SUFFIX` | `-clone` | versione clone defaults |
| `VENDITE_LISTINI_CLOSE_VERSIONE_LEAD_GG` | `0` | versione close defaults |

Tutti i parameter sono gia' seedati a DB (handoff Fase 2 `2026-04-30`).
La risoluzione applica eventuali override personali utente quando l'auth
user e' presente nel JWT.

## Errori

| HTTP | Codice | Quando |
| --- | --- | --- |
| 400 | `E_VENDITE_VALIDATION` | Query param non intero positivo (es. `?billing_account_id=abc`) |
| 401 | — | JWT mancante o invalido |
| 403 | `E_PERMESSO_NEGATO` | Utente con `vendite = BLOCCATO` |
| 404 | `E_VENDITE_NOT_FOUND` | BA, listino o versione inesistente |

## Test

| Tipo | File | Cosa verifica |
| --- | --- | --- |
| Service | `apps/vendite/tests/services/test_vendite_form_defaults_service.py` | 13 test: payload con/senza BA, fallback parameter, fallback emittente per valuta, existing_drafts, suffisso clone, current_valido_al close, 404 per BA/listino/versione inesistenti |
| API | `apps/vendite/tests/api/test_form_defaults_api.py` | 8 test: smoke 200 per i 5 endpoint, JWT mocked, propagazione query params (billing_account_id) e path params (listino_id/versione_id), 401 senza auth |

## Riferimenti

- Backend service: `apps/vendite/services/vendite_form_defaults_service.py`
- Backend views: `apps/vendite/api/views_form_defaults.py`
- Backend routes: `apps/vendite/api/{preventivi_urls,urls_contratti,urls_listini}.py`
- Frontend client: `frontend/src/vendite/api/formDefaults.js`
- Frontend consumer: `frontend/src/vendite/{components/{VersioneFormDrawer,CloneVersioneDrawer,ChiudiVersioneDialog}.vue,preventivi/components/PreventiviDrawer.vue}`
- Refactor doc: `docs/it/dev/work-done/analisi-refactor.frontend-vendite.md` §A5/A8 + Fase 2 piano (chiuso)
