# API Parametri di Sistema

> ⚠️ **Il parametro dell'IVA di default si chiama `DEFAULT_IVA` dal 2026-08-31**,
> e porta il **`codice_interno`** dell'aliquota — non il suo id. Si chiamava
> `DEFAULT_IVA_ID` e valeva `16`.
> ⛔ **Non si fa `int()` sul suo valore**: il `codice_interno` è `22`, cioè un
> numero, quindi il cast **non fallirebbe** — darebbe l'**id 22**, che oggi in
> `config.iva` non esiste ma che il modello ammette eccome. Si risolve col
> lookup su `config.iva.codice_interno`
> ([api_catalogo](../../catalogo/manual/api_catalogo.md), form-defaults articolo).

## Scopo

Espone la gestione dei parametri di sistema (`config.parameters`) con risoluzione
override multi-livello per l'utente autenticato. Supporta:

1. **Risoluzione N parametri** — per pre-caricare default nel frontend (es. IVA default)
2. **Lista parametri con livelli** — per la schermata Impostazioni con visualizzazione
   dei valori a ogni livello di scope
3. **CRUD override personale** — l'utente puo' personalizzare i propri parametri

## Contesto

Il sistema parametri si basa su due tabelle DB:

- `config.parameters` — catalogo parametri con `default_value`
- `config.parameter_overrides` — override contestuali con scope multipli

La funzione DB `script.fn_get_parameter_full` applica la catena di precedenza:
**user → group → emittente_fiscale → session → function → default**.

La funzione DB `script.fn_list_parameters_for_user` restituisce la lista completa
con i valori a ogni livello di scope.

Il layer Python (`ParameterService` + `ParameterRepository`) wrappa queste funzioni
e aggiunge validazione, conversione tipo e error handling uniforme.

## Autenticazione

Tutti gli endpoint richiedono JWT. Il contesto utente (user_id, group_ids,
emittente_fiscale_id) viene risolto automaticamente dalla request.

---

## Endpoint 1: Risoluzione N parametri

```http
GET /api/v1/core/parameters/defaults/
```

### Input

Query string:

| Parametro | Tipo   | Obbligatorio | Default | Note |
|-----------|--------|:------------:|---------|------|
| `codes`   | string | Si           | —       | Codici parametro separati da virgola (es. `DEFAULT_IVA,DEFAULT_CURRENCY`). Max 20. |

### Output

```json
{
  "data": {
    "DEFAULT_IVA": "22",
    "DEFAULT_CURRENCY": "EUR"
  },
  "meta": {"request_id": "..."}
}
```

### Regole

- I codici non trovati o senza valore vengono esclusi silenziosamente dal risultato.
- Max 20 codici per chiamata (difesa contro abuse).
- Superuser: riceve i valori default globali (nessun override applicato).
- Operatore: override applicati nella catena user → group → emittente → default.

### Uso frontend

```javascript
import { fetchParameterDefaults } from '../apiCore'
import { useParameterDefaults } from '../composables/useParameterDefaults'

// Composable riutilizzabile
const { defaults, load } = useParameterDefaults(['DEFAULT_IVA'])
load()
// defaults.value.DEFAULT_IVA → "22"  (codice_interno, NON un id)
```

---

## Endpoint 2: Lista parametri con livelli override

```http
GET /api/v1/core/parameters/settings/
```

### Input

Nessun parametro. Il contesto utente viene risolto dal JWT.

### Output

```json
{
  "data": [
    {
      "code": "DEFAULT_IVA",
      "description": "ID IVA di default per creazione clienti",
      "default_value": "16",
      "emittente_value": "10",
      "group_value": null,
      "user_value": "22",
      "user_override_id": 42,
      "resolved_value": "22"
    },
    {
      "code": "DEFAULT_CURRENCY",
      "description": "Valuta di default per le transazioni",
      "default_value": "EUR",
      "emittente_value": null,
      "group_value": null,
      "user_value": null,
      "user_override_id": null,
      "resolved_value": "EUR"
    }
  ],
  "meta": {"request_id": "..."}
}
```

### Campi risultato

| Campo                | Tipo        | Note |
|----------------------|-------------|------|
| `code`               | string      | Codice univoco del parametro |
| `description`        | string/null | Descrizione estesa |
| `default_value`      | string      | Valore default globale da `config.parameters` |
| `emittente_value`    | string/null | Override livello emittente fiscale |
| `group_value`        | string/null | Override livello gruppo Django |
| `user_value`         | string/null | Override personale dell'utente |
| `user_override_id`   | int/null    | ID dell'override utente (per delete) |
| `resolved_value`     | string      | Valore finale dopo applicazione catena precedenza |

### Regole

- Restituisce **tutti** i parametri di sistema, non solo quelli con override.
- La catena di precedenza per `resolved_value`: user → group → emittente → default.
- `user_override_id` e' presente solo se l'utente ha un override personale attivo.

---

## Endpoint 3: Crea/aggiorna override personale

```http
POST /api/v1/core/parameters/settings/override/
```

### Input

Body JSON:

| Campo            | Tipo   | Obbligatorio | Note |
|------------------|--------|:------------:|------|
| `parameter_code` | string | Si           | Codice del parametro da sovrascrivere |
| `value`          | string | Si           | Nuovo valore dell'override |

### Output

```json
{
  "data": {
    "override_id": 42
  },
  "meta": {"request_id": "..."}
}
```

### Regole

- Usa UPSERT: se l'utente ha gia' un override per quel parametro, lo aggiorna.
- L'override e' personale: scoped su `django_user_id` dell'utente autenticato.
- Il `parameter_code` deve esistere in `config.parameters` (errore DB se assente).
- Errore `E_PARAMETER_VALIDATION` se `parameter_code` vuoto.

---

## Endpoint 4: Rimuovi override personale

```http
DELETE /api/v1/core/parameters/settings/override/{override_id}/
```

### Input

Path parameter:

| Parametro     | Tipo | Note |
|---------------|------|------|
| `override_id` | int  | ID dell'override da rimuovere (da `user_override_id` nella lista) |

### Output

```json
{
  "data": {
    "deleted": true
  },
  "meta": {"request_id": "..."}
}
```

### Regole

- L'utente puo' rimuovere solo i propri override (`django_user_id` verificato).
- Errore `E_PARAMETER_NOT_FOUND` se l'override non esiste o non appartiene all'utente.

---

## Architettura a tre layer

```text
views_parameters.py (API)
  ├── ParameterDefaultsView       GET  /defaults/
  ├── ParameterSettingsView        GET  /settings/
  ├── ParameterOverrideView        POST /settings/override/
  └── ParameterOverrideDeleteView  DELETE /settings/override/{id}/
         │
parameter_service.py (Service)
  ├── get_parameter(code)           singolo, con errore
  ├── get_parameter_int(code)       singolo, convertito a int
  ├── get_defaults(codes[])         multiplo, silenzioso
  ├── list_parameters_for_user()    lista con livelli
  ├── upsert_user_override()        CRUD override
  ├── delete_user_override()        CRUD override
  └── get_emittente_fiscale_id_for_user()
         │
parameter_repository.py (Repository)
  ├── get_parameter()               → script.fn_get_parameter_full
  ├── get_parameters()              → script.fn_get_parameter_full (loop)
  ├── list_for_user()               → script.fn_list_parameters_for_user
  ├── upsert_user_override()        → INSERT ON CONFLICT
  ├── delete_user_override()        → DELETE con check ownership
  └── get_emittente_fiscale_id_for_user()  → JOIN HR bridge
```

## Dipendenze DB

| Funzione/Tabella | Schema | Scopo |
|------------------|--------|-------|
| `script.fn_get_parameter_full` | script | Risolve parametro con catena override |
| `script.fn_list_parameters_for_user` | script | Lista parametri con valori per livello |
| `config.parameters` | config | Catalogo parametri |
| `config.parameter_overrides` | config | Override contestuali |
| `anagrafiche.risorse_umane_auth_user` | anagrafiche | Bridge utente → emittente fiscale |

## Codici errore

| Codice                    | HTTP | Causa |
|---------------------------|------|-------|
| `E_PARAMETER_NOT_FOUND`   | 404  | Parametro non trovato o override non esistente |
| `E_PARAMETER_VALIDATION`  | 400  | Valore non valido, codice vuoto, ID non numerico |
