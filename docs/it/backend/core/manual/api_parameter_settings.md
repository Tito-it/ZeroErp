# API Parametri di sistema — Impostazioni (Django)

> ⚠️ **Il parametro dell'IVA di default si chiama `DEFAULT_IVA` dal 2026-08-31**,
> e porta il **`codice_interno`** dell'aliquota — non il suo id. Si chiamava
> `DEFAULT_IVA_ID` e valeva `16`.
> ⛔ **Non si fa `int()` sul suo valore**: il `codice_interno` è `22`, cioè un
> numero, quindi il cast **non fallirebbe** — darebbe l'**id 22**, che oggi in
> `config.iva` non esiste ma che il modello ammette eccome. Si risolve col
> lookup su `config.iva.codice_interno`
> ([api_catalogo](../../catalogo/manual/api_catalogo.md), form-defaults articolo).

## Scopo

Esporre via HTTP la gestione dei parametri di sistema con risoluzione override multi-livello (user, categoria cliente, group, emittente fiscale) e CRUD override (personale, emittente, categoria cliente).

## Contesto

I parametri di sistema (`config.parameters`) definiscono valori di configurazione globali (es. `DEFAULT_IVA`, `UI_THEME`). Ogni parametro puo' essere sovrascritto a piu' livelli tramite `config.parameter_overrides`, con catena di priorita':

```
utente > categoria cliente > gruppo > emittente fiscale > sessione > funzione > default
```

La risoluzione e' gestita dalla funzione DB `script.fn_get_parameter_full()`. La lista completa con tutti i livelli e' fornita da `script.fn_list_parameters_for_user()`.

**Tre profili di accesso:**

| Profilo | Cosa puo' fare |
|---------|----------------|
| Utente | Vede tutti i parametri, crea/modifica/elimina solo i propri override (`scope=user`, `django_user_id = self`) |
| Amministratore (`IsAdminZeroERP`: superuser o binding SUPER_ADMIN) | Come utente + override `scope=emittente` e `scope=categoria_cliente` |
| Superuser | Nessun trattamento speciale nella risoluzione: vede i propri override, gruppi ed emittente reali come ogni altro utente |

---

## Endpoint

### 1. Risoluzione parametri (valori finali)

- Metodo: `GET`
- Path: `/api/v1/core/parameters/defaults/`
- Auth: JWT, `skip_area_check = True`
- Query param:
  - `codes` (string) — codici separati da virgola (es. `DEFAULT_IVA,DEFAULT_CURRENCY`). Se assente o vuoto la risposta e' `200` con `data: {}`. Oltre 20 codici l'eccedenza viene scartata in silenzio
- Output `200`:
```json
{
  "data": {
    "DEFAULT_IVA": "22",
    "DEFAULT_CURRENCY": "EUR"
  },
  "meta": { "request_id": "..." }
}
```
- Regole:
  - Risoluzione con override user → categoria cliente → group → emittente → default, identica per ogni utente (superuser compreso); la categoria cliente qui non viene passata, quindi quel livello non scatta
  - Codici non trovati vengono esclusi dal risultato (nessun errore)
  - Limite massimo 20 codici per richiesta (protezione DOS): i successivi vengono ignorati

---

### 2. Lista parametri con livelli override

- Metodo: `GET`
- Path: `/api/v1/core/parameters/settings/`
- Auth: JWT, `skip_area_check = True`
- Query params (tutti opzionali):
  - `categoria_cliente_id` (smallint) — attiva il livello `categoria_cliente` nella cascata visualizzata (fra `user` e `group`). Valorizza `categoria_cliente_value` e `categoria_cliente_override_id` nelle righe risposta. Non numerico o ≤ 0 → 400 `E_VALIDATION_INPUT`, come `billing_account_id`.
  - `billing_account_id` (int) — alternativa al precedente: il BE deriva la categoria dal BA col BB `categoria_cliente_da_query`. Non numerico o ≤ 0 → 400 `E_VALIDATION_INPUT`; BA inesistente **o fuori dallo scope** dell'operatore (la RLS di `anagrafiche.billing_account` non lo restituisce) → 404 `E_ANAG_NOT_FOUND`, senza distinguere i due casi. Ignorato se `categoria_cliente_id` esplicito è presente (priorità all'esplicito).
- Output `200`:
```json
{
  "data": [
    {
      "code": "DEFAULT_IVA",
      "description": "Aliquota IVA predefinita per documenti",
      "default_value": "22",
      "emittente_value": "10",
      "emittente_override_id": 7,
      "group_value": null,
      "categoria_cliente_value": null,
      "categoria_cliente_override_id": null,
      "user_value": "5",
      "user_override_id": 42,
      "resolved_value": "5"
    },
    {
      "code": "VENDITE_MAX_SCONTO_PCT",
      "description": "Sconto massimo percentuale ammesso senza approvazione",
      "default_value": "10",
      "emittente_value": "12",
      "emittente_override_id": 8,
      "group_value": "20",
      "categoria_cliente_value": "5",
      "categoria_cliente_override_id": 314,
      "user_value": null,
      "user_override_id": null,
      "resolved_value": "5"
    }
  ],
  "meta": { "request_id": "..." }
}
```
- Regole:
  - Restituisce **tutti** i parametri di `config.parameters`
  - Per ogni parametro: valore a ciascun livello di scope + valore risolto finale
  - Cascata di risoluzione (post brief DB 2026-05-19, migration `20260519-01-recreate-fn-list-parameters-for-user-categoria-cliente-mctit`): `user > categoria_cliente > group > emittente > default`
  - `user_override_id` / `emittente_override_id` / `categoria_cliente_override_id`: ID dei rispettivi override (null se assente), da usare nel DELETE con lo `scope` corrispondente. `categoria_cliente_override_id` è **bigint** (non integer) per coerenza con `config.parameter_overrides.id` (derivato via `%TYPE`).
  - `emittente_fiscale_id` risolto automaticamente: whitelist personale `config.user_emittenti_fiscali`, altrimenti gestore globale da `anagrafiche.emittenti_fiscali_billing_account` (riga con `billing_account_id` NULL e `is_default`)
  - `billing_account_id` che non risulta (inesistente o fuori scope): 404 `E_ANAG_NOT_FOUND` (dal 2026-10-08; prima la categoria restava NULL senza errore)
  - `categoria_cliente_value` / `categoria_cliente_override_id` sono SEMPRE presenti come chiavi nello shape della risposta; restano `null` se la richiesta non ha passato né `categoria_cliente_id` né `billing_account_id`
  - Delega a `script.fn_list_parameters_for_user(p_django_user_id, p_group_ids, p_emittente_fiscale_id, p_categoria_cliente_id)` (firma 4-arg)

---

### 3. Crea o aggiorna override

- Metodo: `POST`
- Path: `/api/v1/core/parameters/settings/override/`
- Auth: JWT, `skip_area_check = True`
- Body JSON:
  - `parameter_code` (string, **obbligatorio**) — codice parametro da sovrascrivere
  - `value` (string) — nuovo valore dell'override. ⚠️ Dichiarato obbligatorio, ma il codice non lo verifica: assente o `null` → override con stringa vuota, risposta 200 (difetto noto)
  - `scope` (string, opzionale, default `"user"`) — uno fra:
    - `"user"` — override personale (default, qualunque utente)
    - `"emittente"` — override per emittente fiscale (admin-only; EF derivato dal profilo utente)
    - `"categoria_cliente"` — override per categoria cliente (admin-only; richiede `categoria_cliente_id` esplicito, Phase B 2026-05-19)
  - `categoria_cliente_id` (int, **obbligatorio se `scope="categoria_cliente"`**) — ID smallint della categoria; il BE rifiuta valori non-positivi
- Output `200`:
```json
{
  "data": {
    "override_id": 42,
    "scope": "categoria_cliente"
  },
  "meta": { "request_id": "..." }
}
```
- Regole:
  - Esegue UPSERT su `config.parameter_overrides` di un override per **un** ambito, la sola dimensione dello scope valorizzata:
    - `user` → `django_user_id = utente corrente`
    - `emittente` → `emittente_fiscale_id = EF utente`
    - `categoria_cliente` → `categoria_cliente_id = <id>`
    Che le altre dimensioni siano NULL lo garantisce il DB (`chk_parameter_overrides_un_ambito`, dal 2026-10-07): le righe miste non esistono. Fino ad allora il perimetro lo teneva il repository (F-5 dell'[analisi difetti](../../../dev/work-done/analisi-be-difetti-emersi-verifica-doc-api-core.md)).
  - Se l'override esiste gia' sullo stesso ambito, aggiorna il valore e `data_update` e lo **riattiva** (`attivo = true`): impostare un override vuol dire volerlo in vigore. L'upsert e' un `INSERT … ON CONFLICT ON CONSTRAINT uq_overrides_full_scope_v5 DO UPDATE` (unicita' `NULLS NOT DISTINCT`): due richieste concorrenti sullo stesso ambito non creano un doppione e non rispondono errore, la seconda aggiorna (dal 2026-10-07; prima il vincolo v4 non scattava e il doppione era possibile). Fino al 2026-09-28 una riga spenta (`attivo` false o NULL) veniva aggiornata e restava spenta — risposta con l'id, ma override ignorato dalla risoluzione e assente dalla lista, che leggono solo `attivo = true`
  - Se il `parameter_code` non esiste in `config.parameters` → **404 `E_PARAMETER_NOT_FOUND`**, niente scritto (dal 2026-09-28, E-9: prima `E_DATABASE` 400 dalla violazione del NOT NULL)
- Errori:
  - `E_PARAMETER_VALIDATION` (400) — codice parametro vuoto, `scope` non ammesso, `categoria_cliente_id` mancante/non-positivo per scope categoria, emittente non risolvibile per scope emittente
  - `E_PERMISSION_DENIED` (403) — scope `emittente` o `categoria_cliente` da non-admin
  - `E_PARAMETER_NOT_FOUND` (404) — `parameter_code` inesistente

---

### 4. Rimuovi override

- Metodo: `DELETE`
- Path: `/api/v1/core/parameters/settings/override/<override_id>/`
- Auth: JWT, `skip_area_check = True`
- Path param:
  - `override_id` (int, **obbligatorio**) — ID dell'override da rimuovere (ottenuto da endpoint 2: `user_override_id` / `categoria_cliente_override_id` / equivalente per emittente)
- Query param:
  - `scope` (string, opzionale, default `"user"`) — coerente col POST: `user` / `emittente` / `categoria_cliente`
  - `categoria_cliente_id` (int, **obbligatorio se `scope="categoria_cliente"`**)
- Output `200`:
```json
{
  "data": {
    "deleted": true,
    "scope": "categoria_cliente"
  },
  "meta": { "request_id": "..." }
}
```
- Regole:
  - Si cancella l'override per id **e** scope: l'id di un altro proprietario non basta:
  - `user` → `django_user_id = self`
  - `emittente` → `emittente_fiscale_id = EF utente` (admin-only)
  - `categoria_cliente` → `categoria_cliente_id = <id query param>` (admin-only). Difesa anti-tampering: niente cancellazione cross-categoria.
- Errori:
  - `E_PARAMETER_NOT_FOUND` (404) — override non trovato o non appartenente allo scope
  - `E_PARAMETER_VALIDATION` (400) — ID override non valido, `scope` non ammesso o `categoria_cliente_id` mancante/non-positivo
  - `E_PERMISSION_DENIED` (403) — scope `emittente` o `categoria_cliente` da non-admin

---

## Dipendenze DB

| Risorsa | Tipo | Uso |
|---------|------|-----|
| `config.parameters` | Tabella | Definizione parametri (code, default_value, description) |
| `config.parameter_overrides` | Tabella | Override per scope (user, group, emittente, session, function) |
| `script.fn_get_parameter_full()` | Funzione | Risoluzione singolo parametro con catena di priorita' |
| `script.fn_list_parameters_for_user()` | Funzione | Lista completa parametri con valori a ogni livello per l'utente |
| `anagrafiche.emittenti_fiscali_billing_account` | Tabella | Ripiego della risoluzione `emittente_fiscale_id`: gestore globale (`billing_account_id` NULL, `is_default`) |
| `config.user_emittenti_fiscali` | Tabella | Risoluzione `emittente_fiscale_id` dell'utente (`get_emittente_fiscale_id_for_user`; ⚠️ fino al 2026-09-12 questa riga nominava la vista `risorse_umane_auth_user`, nome vecchio del ponte in ritiro (analisi-software-per-dati-morti §2.1), e `risorse_umane` non ha una colonna `emittente_fiscale_id`) |

## Codici errore

| Codice | HTTP | Descrizione |
|--------|------|-------------|
| `E_PARAMETER_NOT_FOUND` | 404 | Parametro o override non trovato |
| `E_PARAMETER_VALIDATION` | 400 | Valore parametro non valido o parametri di input mancanti |

## Architettura backend

```
views_parameters.py (4 APIView)
    |
    ├── get_user_context(request, svc) — helper condiviso estrazione contesto
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
    ├── upsert_{user,emittente,categoria_cliente}_override() → INSERT … ON CONFLICT ON CONSTRAINT uq_overrides_full_scope_v5 DO UPDATE
    ├── delete_{user,emittente,categoria_cliente}_override() → DELETE con verifica di appartenenza allo scope
    └── get_emittente_fiscale_id_for_user() → whitelist personale, poi gestore globale
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
