# API Parametri di sistema — Impostazioni (Django)

## Scopo

Esporre via HTTP la gestione dei parametri di sistema con risoluzione override multi-livello (user, group, emittente fiscale) e CRUD override personale operatore.

## Contesto

I parametri di sistema (`config.parameters`) definiscono valori di configurazione globali (es. `DEFAULT_IVA_ID`, `UI_THEME`). Ogni parametro puo' essere sovrascritto a piu' livelli tramite `config.parameter_overrides`, con catena di priorita':

```
utente > gruppo > emittente fiscale > sessione > funzione > default
```

La risoluzione e' gestita dalla funzione DB `script.fn_get_parameter_full()`. La lista completa con tutti i livelli e' fornita da `script.fn_list_parameters_for_user()`.

**Tre profili di accesso:**

| Profilo | Cosa puo' fare |
|---------|----------------|
| Operatore | Vede tutti i parametri, crea/modifica/elimina solo i propri override (`django_user_id = self`) |
| Responsabile emittente | Come operatore + override a livello emittente (futuro, richiede permesso Django) |
| Admin (superuser) | Vede i default globali senza filtro scope |

---

## Endpoint

### 1. Risoluzione parametri (valori finali)

- Metodo: `GET`
- Path: `/api/v1/core/parameters/defaults/`
- Auth: JWT, `skip_area_check = True`
- Query param:
  - `codes` (string, **obbligatorio**) — codici separati da virgola (es. `DEFAULT_IVA_ID,DEFAULT_CURRENCY`), max 20
- Output `200`:
```json
{
  "data": {
    "DEFAULT_IVA_ID": "22",
    "DEFAULT_CURRENCY": "EUR"
  },
  "meta": { "request_id": "..." }
}
```
- Regole:
  - Superuser: nessun filtro scope (riceve i default globali)
  - Operatore: risoluzione con override user → group → emittente → default
  - Codici non trovati vengono esclusi dal risultato (nessun errore)
  - Limite massimo 20 codici per richiesta (protezione DOS)

---

### 2. Lista parametri con livelli override

- Metodo: `GET`
- Path: `/api/v1/core/parameters/settings/`
- Auth: JWT, `skip_area_check = True`
- Output `200`:
```json
{
  "data": [
    {
      "code": "DEFAULT_IVA_ID",
      "description": "Aliquota IVA predefinita per documenti",
      "default_value": "22",
      "emittente_value": "10",
      "group_value": null,
      "user_value": "5",
      "user_override_id": 42,
      "resolved_value": "5"
    },
    {
      "code": "UI_THEME",
      "description": "Tema interfaccia utente",
      "default_value": "light",
      "emittente_value": null,
      "group_value": null,
      "user_value": null,
      "user_override_id": null,
      "resolved_value": "light"
    }
  ],
  "meta": { "request_id": "..." }
}
```
- Regole:
  - Restituisce **tutti** i parametri di `config.parameters`
  - Per ogni parametro: valore a ciascun livello di scope + valore risolto finale
  - `user_override_id`: ID dell'override personale dell'utente (null se non esiste), usato per DELETE
  - `emittente_fiscale_id` risolto automaticamente dal bridge HR dell'utente
  - Delega a `script.fn_list_parameters_for_user()`

---

### 3. Crea o aggiorna override personale

- Metodo: `POST`
- Path: `/api/v1/core/parameters/settings/override/`
- Auth: JWT, `skip_area_check = True`
- Body JSON:
  - `parameter_code` (string, **obbligatorio**) — codice parametro da sovrascrivere
  - `value` (string, **obbligatorio**) — nuovo valore dell'override
- Output `200`:
```json
{
  "data": {
    "override_id": 42
  },
  "meta": { "request_id": "..." }
}
```
- Regole:
  - Esegue UPSERT su `config.parameter_overrides` con `django_user_id = utente corrente`
  - Tutti gli altri scope (emittente, group, session, function) sono NULL — solo override personale
  - Se l'override esiste gia', aggiorna il valore e `data_update`
  - Se il `parameter_code` non esiste in `config.parameters`, il DB lancia errore (NOT NULL su parameter_id)
- Errori:
  - `E_PARAMETER_VALIDATION` (400) — codice parametro vuoto o utente non valido

---

### 4. Rimuovi override personale

- Metodo: `DELETE`
- Path: `/api/v1/core/parameters/settings/override/<override_id>/`
- Auth: JWT, `skip_area_check = True`
- Path param:
  - `override_id` (int, **obbligatorio**) — ID dell'override da rimuovere (ottenuto da endpoint 2)
- Output `200`:
```json
{
  "data": {
    "deleted": true
  },
  "meta": { "request_id": "..." }
}
```
- Regole:
  - Verifica che l'override appartenga all'utente corrente (`django_user_id = self`)
  - Non e' possibile eliminare override di altri utenti
- Errori:
  - `E_PARAMETER_NOT_FOUND` (404) — override non trovato o non appartenente all'utente
  - `E_PARAMETER_VALIDATION` (400) — ID override non valido

---

## Dipendenze DB

| Risorsa | Tipo | Uso |
|---------|------|-----|
| `config.parameters` | Tabella | Definizione parametri (code, default_value, description) |
| `config.parameter_overrides` | Tabella | Override per scope (user, group, emittente, session, function) |
| `script.fn_get_parameter_full()` | Funzione | Risoluzione singolo parametro con catena di priorita' |
| `script.fn_list_parameters_for_user()` | Funzione | Lista completa parametri con valori a ogni livello per l'utente |
| `anagrafiche.risorse_umane_auth_user` | Tabella (bridge) | Risoluzione `emittente_fiscale_id` dell'utente |
| `anagrafiche.risorse_umane` | Tabella | Contiene `emittente_fiscale_id` della risorsa umana |

## Codici errore

| Codice | HTTP | Descrizione |
|--------|------|-------------|
| `E_PARAMETER_NOT_FOUND` | 404 | Parametro o override non trovato |
| `E_PARAMETER_VALIDATION` | 400 | Valore parametro non valido o parametri di input mancanti |

## Architettura backend

```
views_parameters.py (4 APIView)
    |
    ├── _get_user_context(request, svc) — helper condiviso estrazione contesto
    |
    v
parameter_service.py (ParameterService)
    |
    v
parameter_repository.py (ParameterRepository)
    |
    ├── get_parameter()       → fn_get_parameter_full()
    ├── get_parameters()      → fn_get_parameter_full() x N
    ├── list_for_user()       → fn_list_parameters_for_user()
    ├── upsert_user_override()→ INSERT ON CONFLICT (upsert)
    ├── delete_user_override()→ DELETE con verifica ownership
    └── get_emittente_fiscale_id_for_user() → query bridge HR
```

## Frontend

| Componente | Percorso | Scopo |
|------------|----------|-------|
| `fetchParameterSettings` | `core/apiCore.js` | GET lista parametri con livelli |
| `upsertParameterOverride` | `core/apiCore.js` | POST upsert override |
| `deleteParameterOverride` | `core/apiCore.js` | DELETE override |
| `useParameterSettings` | `core/composables/useParameterSettings.js` | Composable generico load/save/remove |
| `useParameterDefaults` | `core/composables/useParameterDefaults.js` | Composable risoluzione default per form |
| `ParameterFallback` | `core/components/ParameterFallback.vue` | Visualizzazione catena fallback (riutilizzabile) |
| `resolveParameterLevel` | `core/utils/parameterLevel.js` | Utility livello provenienza parametro |
| `ImpostazioniView` | `config/views/ImpostazioniView.vue` | Pagina principale |
| `ImpostazioniSearchTable` | `config/components/ImpostazioniSearchTable.vue` | DataTable con 7 colonne + azioni |
| `ImpostazioniOverrideDrawer` | `config/components/ImpostazioniOverrideDrawer.vue` | Drawer edit override con catena fallback |
| `useImpostazioniStore` | `config/stores/impostazioni.js` | Store Pinia con filtro client-side |
