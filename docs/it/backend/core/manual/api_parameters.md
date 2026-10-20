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
3. **CRUD override** — l'utente personalizza i propri parametri (`scope=user`); gli
   amministratori gestiscono anche gli override per emittente e per categoria cliente

## Contesto

Il sistema parametri si basa su due tabelle DB:

- `config.parameters` — catalogo parametri con `default_value`
- `config.parameter_overrides` — override contestuali con scope multipli

La funzione DB `script.fn_get_parameter_full` applica la catena di precedenza:
**user → categoria_cliente → group → emittente_fiscale → session → function → default**.

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
| `codes`   | string | No           | —       | Codici parametro separati da virgola (es. `DEFAULT_IVA,DEFAULT_CURRENCY`). Assente o vuoto → `200` con `data: {}`. Max 20. |

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
- Max 20 codici per chiamata (difesa contro abuse): i successivi vengono scartati in silenzio.
- Override applicati nella catena user → group → emittente → default, identica per
  ogni utente, superuser compreso (il livello categoria cliente qui non scatta: la
  categoria non viene passata).

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

Il contesto utente viene risolto dal JWT. Query string opzionale:

| Parametro              | Tipo | Note |
|------------------------|------|------|
| `categoria_cliente_id` | int  | Attiva il livello categoria cliente (fra user e group). Non numerico o ≤ 0 → 400 `E_VALIDATION_INPUT` (2026-10-20: prima la doc indicava `E_PARAMETER_VALIDATION`) |
| `billing_account_id`   | int  | Alternativa: la categoria si deriva dal BA (BB `categoria_cliente_da_query`). Ignorato se c'e' `categoria_cliente_id`. Non numerico o ≤ 0 → 400 `E_VALIDATION_INPUT`; BA inesistente o fuori scope (RLS) → 404 `E_ANAG_NOT_FOUND`, senza distinguere i due casi |

### Output

```json
{
  "data": [
    {
      "code": "DEFAULT_IVA",
      "description": "Aliquota IVA predefinita (codice_interno)",
      "default_value": "22",
      "emittente_value": "10",
      "emittente_override_id": 7,
      "group_value": null,
      "categoria_cliente_value": null,
      "categoria_cliente_override_id": null,
      "user_value": "4",
      "user_override_id": 42,
      "resolved_value": "4"
    },
    {
      "code": "DEFAULT_CURRENCY",
      "description": "Valuta di default per le transazioni",
      "default_value": "EUR",
      "emittente_value": null,
      "emittente_override_id": null,
      "group_value": null,
      "categoria_cliente_value": null,
      "categoria_cliente_override_id": null,
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
| `emittente_override_id` | int/null | ID dell'override emittente (per delete con `scope=emittente`) |
| `group_value`        | string/null | Override livello gruppo Django |
| `categoria_cliente_value` | string/null | Override livello categoria cliente (null se la categoria non e' stata passata) |
| `categoria_cliente_override_id` | int/null | ID dell'override di categoria (per delete con `scope=categoria_cliente`) |
| `user_value`         | string/null | Override personale dell'utente |
| `user_override_id`   | int/null    | ID dell'override utente (per delete) |
| `resolved_value`     | string      | Valore finale dopo applicazione catena precedenza |

### Regole

- Restituisce **tutti** i parametri di sistema, non solo quelli con override.
- La catena di precedenza per `resolved_value`: user → categoria_cliente → group → emittente → default.
- `user_override_id` c'e' sempre come chiave: `null` se l'utente non ha un override personale attivo.

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
| `value`          | string | Si (non verificato) | Nuovo valore dell'override. ⚠️ Il codice non ne verifica la presenza: assente o `null` → override con stringa vuota, risposta 200 (difetto noto) |
| `scope`          | string | No           | `user` (default), `emittente` (admin), `categoria_cliente` (admin) |
| `categoria_cliente_id` | int | Se `scope=categoria_cliente` | Intero positivo |

### Output

```json
{
  "data": {
    "override_id": 42,
    "scope": "user"
  },
  "meta": {"request_id": "..."}
}
```

### Regole

- Usa UPSERT: se esiste gia' un override per quel parametro nello stesso scope, lo aggiorna.
- `scope=user`: override personale sul `django_user_id` dell'utente autenticato.
- `scope=emittente`: emittente derivato dall'utente; `scope=categoria_cliente`: id
  dal body. Entrambi riservati agli amministratori (superuser o SUPER_ADMIN),
  altrimenti `E_PERMISSION_DENIED` (403).
- Il `parameter_code` deve esistere in `config.parameters`: se manca, **404
  `E_PARAMETER_NOT_FOUND`** e non si scrive niente (dal 2026-09-28; prima l'INSERT
  violava il NOT NULL su `parameter_id` ed usciva `E_DATABASE` 400 — E-9 dell'
  [analisi difetti](../../../dev/work-done/analisi-be-difetti-emersi-verifica-doc-api-core.md)).
- Errore `E_PARAMETER_VALIDATION` se `parameter_code` vuoto, `scope` non ammesso o
  `categoria_cliente_id` mancante/non positivo.

---

## Endpoint 4: Rimuovi override personale

```http
DELETE /api/v1/core/parameters/settings/override/{override_id}/
```

### Input

Path parameter:

| Parametro     | Tipo | Note |
|---------------|------|------|
| `override_id` | int  | ID dell'override da rimuovere (da `user_override_id` / `emittente_override_id` / `categoria_cliente_override_id` nella lista) |

Query string: `scope` (`user` default, `emittente`, `categoria_cliente`) e, per
`scope=categoria_cliente`, `categoria_cliente_id`.

### Output

```json
{
  "data": {
    "deleted": true,
    "scope": "user"
  },
  "meta": {"request_id": "..."}
}
```

### Regole

- `scope=user`: l'utente puo' rimuovere solo i propri override (`django_user_id` verificato).
- `scope=emittente` / `categoria_cliente`: solo amministratori, altrimenti `E_PERMISSION_DENIED` (403).
- Errore `E_PARAMETER_NOT_FOUND` se l'override non esiste o non appartiene allo scope.

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
  ├── upsert_{user,emittente,categoria_cliente}_override()   CRUD override
  ├── delete_{user,emittente,categoria_cliente}_override()   CRUD override
  └── get_emittente_fiscale_id_for_user()
         │
parameter_repository.py (Repository)
  ├── get_parameter()               → script.fn_get_parameter_full
  ├── get_parameters()              → script.fn_get_parameter_full (loop)
  ├── list_for_user()               → script.fn_list_parameters_for_user
  ├── upsert_*_override()           → INSERT … ON CONFLICT ON CONSTRAINT uq_overrides_full_scope_v5 DO UPDATE
  ├── delete_*_override()           → DELETE con check di appartenenza allo scope
  └── get_emittente_fiscale_id_for_user()  → whitelist personale, poi gestore globale
```

## Dipendenze DB

| Funzione/Tabella | Schema | Scopo |
|------------------|--------|-------|
| `script.fn_get_parameter_full` | script | Risolve parametro con catena override |
| `script.fn_list_parameters_for_user` | script | Lista parametri con valori per livello |
| `config.parameters` | config | Catalogo parametri |
| `config.parameter_overrides` | config | Override contestuali |
| `anagrafiche.emittenti_fiscali_billing_account` | anagrafiche | Ripiego di `get_emittente_fiscale_id_for_user`: gestore globale (`billing_account_id` NULL, `is_default`) |
| `config.user_emittenti_fiscali` | config | Utente → emittente fiscale (`get_emittente_fiscale_id_for_user`; ⚠️ fino al 2026-09-12 questa riga nominava la vista `risorse_umane_auth_user`, che il repository non legge) |

## Codici errore

| Codice                    | HTTP | Causa |
|---------------------------|------|-------|
| `E_PARAMETER_NOT_FOUND`   | 404  | Parametro non trovato (anche nell'upsert di un override) o override non esistente |
| `E_PARAMETER_VALIDATION`  | 400  | Valore non valido, codice vuoto, scope non ammesso, id categoria non positivo |
| `E_PERMISSION_DENIED`     | 403  | Scope `emittente` / `categoria_cliente` da non amministratore |
