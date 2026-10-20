# API UI Admin — Gestione personalizzazioni liste (Django)

## Scopo

Esporre via HTTP la gestione amministrativa dei **preset** di lista
(`ui.lista_preset` + composizione `ui.lista_preset_colonna`) e dei
**permessi colonna** (`ui.lista_colonna_permesso`) per il refactor
personalizzazioni liste — Blocco F Fase 1. Le operazioni vengono
consumate da una pagina condivisa accessibile sia da
`/config/personalizzazioni-liste` (tenant admin con azione di processo
abilitata) sia da `/amm-software/personalizzazioni-liste` (SUPER_ADMIN
con bypass totale).

## Contesto

Strato amministrativo del refactor `sviluppo-personalizzazioni-liste.md`
(Blocco F atterrato 2026-05-08). Estende il modulo `apps.ui` esistente
(Blocco C runtime) con:

- repository admin `apps.ui.db.ui_admin_repository.UiAdminRepository`
  (CRUD diretto su 5 tabelle dello schema `ui` + display fields via
  JOIN su `config.profili_accesso` e `anagrafiche.emittenti_fiscali`);
- 3 service admin in `apps.ui.services/`:
  - `ListaDefinizioneAdminService` (read-only — Select header lista
    corrente + catalogo colonne grezzo);
  - `ListaPresetAdminService` (CRUD testata + replace atomico
    composizione);
  - `ListaColonnaPermessoAdminService` (UPSERT/DELETE permessi);
- 12 view in `apps.ui.api.views_admin`: le 8 di Fase 1 su `DomainAPIView`
  con `skip_area_check = True` (lo schema `ui` non e' un'area
  funzionale di business — meta-API trasversale), le 4 di Fase 2
  (definizioni e colonne, §12-§21) su `AdminAPIView` (solo SUPER_ADMIN).

Permessi (defense-in-depth):

| Endpoint | Auth richiesta |
| --- | --- |
| Select header (lista definizioni, `/admin/liste/`) | SUPER_ADMIN OR azione `ui_preset_manage` OR azione `ui_permesso_manage` |
| Catalogo colonne grezzo (`/admin/liste/{id}/colonne/`) | azione `ui_preset_manage` |
| CRUD preset (`/admin/liste/{id}/preset/`, `/admin/preset/{id}/`, `/admin/preset/{id}/colonne/`) | azione `ui_preset_manage` |
| CRUD permessi colonna (`/admin/liste/{id}/permessi/`, `/admin/permessi/`, `/admin/permessi/{id}/`) | azione `ui_permesso_manage` |

Le 2 azioni di processo (`ui_preset_manage`, `ui_permesso_manage`) sono
seedate in `config.azioni_processo` con area `config` (id `9`). Decisione
operativa 2B (2026-05-07): nessun profilo riceve di default le 2 azioni —
SUPER_ADMIN bypassa via `script.fn_is_super_admin`, il super-admin
abilita manualmente le azioni sui profili `REPARTO_*` da Amm. Software.

Il check OR-azioni del Select header riusa la cache permessi di
`ZeroERPPermission._get_cache(request)` per evitare round-trip DB
ridondanti (`is_super_admin` + 2 `check_azione`).

---

## Endpoint

Path base: `/api/v1/ui/admin/...`. Gli envelope di risposta seguono il
pattern standard `{ "data": ..., "meta": { "request_id": "..." } }`.

| # | Verbo + Path | Auth | Scopo |
| --- | --- | --- | --- |
| 1 | `GET /admin/liste/` | OR | Lista definizioni attive (Select header) |
| 2 | `GET /admin/liste/{id}/colonne/` | preset | Catalogo colonne grezzo |
| 3 | `GET /admin/liste/{id}/preset/` | preset | Lista preset di una lista |
| 4 | `POST /admin/liste/{id}/preset/` | preset | Crea preset (testata) |
| 5 | `PATCH /admin/preset/{id}/` | preset | Aggiorna campi mutabili |
| 6 | `DELETE /admin/preset/{id}/` | preset | Cancella preset |
| 7 | `GET /admin/preset/{id}/colonne/` | preset | Composizione preset |
| 8 | `PUT /admin/preset/{id}/colonne/` | preset | Replace atomico composizione |
| 9 | `GET /admin/liste/{id}/permessi/` | permesso | Permessi colonna di una lista |
| 10 | `POST /admin/permessi/` | permesso | UPSERT permesso colonna |
| 11 | `DELETE /admin/permessi/{id}/` | permesso | Cancella permesso |
| 12 | `GET /admin/definizioni/` | admin | Lista completa definizioni (incluse disattivate) |
| 13 | `POST /admin/definizioni/` | admin | Crea definizione lista |
| 14 | `GET /admin/definizioni/{id}/` | admin | Dettaglio definizione |
| 15 | `PATCH /admin/definizioni/{id}/` | admin | Aggiorna campi mutabili |
| 16 | `DELETE /admin/definizioni/{id}/` | admin | Cancella (RESTRICT su FK) |
| 17 | `GET /admin/definizioni/{id}/colonne/` | admin | Lista colonne admin (full) |
| 18 | `POST /admin/definizioni/{id}/colonne/` | admin | Crea colonna |
| 19 | `GET /admin/colonne/{id}/` | admin | Dettaglio colonna |
| 20 | `PATCH /admin/colonne/{id}/` | admin | Aggiorna campi mutabili |
| 21 | `DELETE /admin/colonne/{id}/` | admin | Cancella (soft-block preferenze) |

Legenda Auth: `OR` = SUPER_ADMIN OR `ui_preset_manage` OR
`ui_permesso_manage`; `preset` = SUPER_ADMIN OR `ui_preset_manage`;
`permesso` = SUPER_ADMIN OR `ui_permesso_manage`; `admin` = SUPER_ADMIN
unico (Fase 2 DEF-5b, `IsAdminZeroERP`).

---

### 1. Lista definizioni attive (Select header)

#### Input

- Metodo: `GET`
- Path canonico: `/api/v1/ui/admin/liste/`
- Header sicurezza: `Authorization: Bearer <access_token>`

#### Output

- `200`:

```json
{
  "data": [
    {
      "id": 1,
      "codice": "anagrafiche.clienti",
      "descrizione": "Clienti",
      "schema_dati": "anagrafiche",
      "attivo": true
    }
  ],
  "meta": {"request_id": "..."}
}
```

Errori:

- `401` — JWT mancante o non valido
- `403` — utente non SUPER_ADMIN e privo di entrambe le azioni di
  processo richieste

---

### 2. Catalogo colonne grezzo

#### Input

- Metodo: `GET`
- Path canonico: `/api/v1/ui/admin/liste/{lista_id}/colonne/`
- Header sicurezza: `Authorization: Bearer <access_token>`
- Path parameter: `lista_id` (int) — PK di `ui.lista_definizione`

#### Output

- `200`: lista di colonne attive ordinate per
  `(gruppo_ordine, gruppo, ordine_default, id)`. Stessi campi di
  `ui.lista_colonna` (`id`, `codice`, `etichetta`, `etichetta_estesa`,
  `tipo_colonna`, `tipo_dato`, `gruppo`, `gruppo_ordine`,
  `ordine_default`, `larghezza_default`, `attivo`).

A differenza del runtime (Blocco C, [api_ui_liste.md](api_ui_liste.md)
§2), questo endpoint **non filtra** le colonne BLOCCATE: l'amministratore
deve poter assegnare permessi anche a colonne sensibili.

Errori:

- `401`, `403` (azione `ui_preset_manage` mancante)
- `404` `E_UI_LISTA_NON_TROVATA` — `lista_id` inesistente o `attivo=false`

---

### 3. Lista preset di una lista

#### Input

- Metodo: `GET`
- Path canonico: `/api/v1/ui/admin/liste/{lista_id}/preset/`
- Header sicurezza: `Authorization: Bearer <access_token>`

#### Output

- `200`:

```json
{
  "data": {
    "results": [
    {
      "id": 12,
      "lista_id": 1,
      "codice": "default",
      "descrizione": "Default sistema",
      "ambito": "sistema",
      "profilo_accesso_id": null,
      "profilo_accesso_codice": null,
      "profilo_accesso_descrizione": null,
      "emittente_fiscale_id": null,
      "emittente_fiscale_codice": null,
      "emittente_ragione_sociale": null,
      "is_default": true,
      "pagina_dimensione": 25,
      "ordinamento_default": [{"col": "ragione_sociale", "dir": "asc"}],
      "filtri_default": {"attivo": true},
      "attivo": true,
      "colonne_count": 14,
      "data_insert": "2026-05-07T10:30:00",
      "user_insert": "tid",
      "data_update": null,
      "user_update": null
    }
    ],
    "count": 1
  },
  "meta": {"request_id": "..."}
}
```

`count` viene da una query sua (non da `len(results)`): non impagina, dichiara
quante righe esistono.

Ordine: `ambito ASC, codice ASC, id ASC` (lex sull'enum `ui.ambito_preset`
→ `emittente_fiscale` < `ruolo` < `sistema`).

Display fields (`profilo_accesso_*`, `emittente_fiscale_*`) sono
denormalizzati via LEFT JOIN: `null` se l'ambito non li valorizza.

`colonne_count` e' il numero di righe in `ui.lista_preset_colonna` per
quel preset (subquery nello stesso ROUND-TRIP).

Errori:

- `401`, `403` (azione `ui_preset_manage` mancante)
- `404` `E_UI_LISTA_NON_TROVATA`

---

### 4. Crea preset (testata)

#### Input

- Metodo: `POST`
- Path canonico: `/api/v1/ui/admin/liste/{lista_id}/preset/`
- Header sicurezza:
  - `Authorization: Bearer <access_token>`
  - `Idempotency-Key: <uuid-stringa>` — **obbligatorio**
- Body JSON:

```json
{
  "codice": "default",
  "descrizione": "Default sistema",
  "ambito": "sistema",
  "profilo_accesso_id": null,
  "emittente_fiscale_id": null,
  "is_default": true,
  "pagina_dimensione": 25,
  "ordinamento_default": [{"col": "ragione_sociale", "dir": "asc"}],
  "filtri_default": {"attivo": true},
  "attivo": true
}
```

Whitelist payload: `lista_id`, `codice`, `descrizione`, `ambito`,
`profilo_accesso_id`, `emittente_fiscale_id`, `is_default`,
`pagina_dimensione`, `ordinamento_default`, `filtri_default`, `attivo`.
`lista_id` viene dal path: il valore in body e' sovrascritto dalla view.

Vincoli:

- `codice` (string) — obbligatorio, max 80 char; UNIQUE per `(lista_id, codice)`
- `descrizione` (string) — obbligatorio, max 200 char
- `ambito` (string) — obbligatorio, uno tra `sistema`, `emittente_fiscale`,
  `ruolo`. Coerenza con i refs garantita dal CHECK
  `chk_ui_lista_preset_ambito_refs`:
  - `sistema` → `profilo_accesso_id` e `emittente_fiscale_id` NULL
  - `ruolo` → `profilo_accesso_id` NOT NULL, `emittente_fiscale_id` NULL
  - `emittente_fiscale` → `emittente_fiscale_id` NOT NULL,
    `profilo_accesso_id` NULL
- `is_default` (bool stretto) — default `false`. Partial UNIQUE su
  `(lista_id, ambito, COALESCE(profilo_accesso_id,0), COALESCE(emittente_fiscale_id,0))
   WHERE is_default = TRUE` permette **un solo** default per scope
- `pagina_dimensione` (int o `null` = «il default») — una delle misure del
  catalogo `ui.misure_pagina`. Il backend ne controlla solo la forma: una
  misura fuori catalogo la rifiuta il DB (guard + FK) con
  `400 E_UI_MISURA_PAGINA_NON_AMMESSA`. ⛔ Fino al 2026-09-30 il service
  applicava un suo tetto a `500`. Il drawer la sceglie da un `Select` sulle
  misure del catalogo, e la manda sempre (anche `null`: e' il modo di tornare
  al default)
- `ordinamento_default` (lista o null) / `filtri_default` (oggetto o
  null) — formato trasparente al BE
- `attivo` (bool stretto) — default `true`

#### Output

- `200`: dettaglio preset appena creato (vedi §3 — singolo oggetto, no
  array).

Errori:

- `400` `E_IDEMPOTENCY_KEY_REQUIRED` — header mancante
- `400` `E_UI_PRESET_VALIDAZIONE` — payload invalido (chiavi extra,
  tipi non corretti, ambito sconosciuto, refs incoerenti con CHECK,
  UNIQUE codice violato, partial UNIQUE default violato)
- `404` `E_UI_LISTA_NON_TROVATA`

---

### 5. Aggiorna preset (PATCH testata)

#### Input

- Metodo: `PATCH`
- Path canonico: `/api/v1/ui/admin/preset/{preset_id}/`
- Header sicurezza: `Authorization: Bearer <access_token>`
- Body JSON: subset dei campi mutabili presenti nel payload.

Whitelist update: `codice`, `descrizione`, `is_default`,
`pagina_dimensione`, `ordinamento_default`, `filtri_default`, `attivo`.

Campi **immutabili** (rifiutati con `E_UI_PRESET_VALIDAZIONE` se
presenti nel payload, prima della validazione altri campi):
`lista_id`, `ambito`, `profilo_accesso_id`, `emittente_fiscale_id`.
Per cambiare ambito o riferimenti si crea un nuovo preset.

#### Output

- `200`: dettaglio preset aggiornato (vedi §3).

Errori:

- `400` `E_UI_PRESET_VALIDAZIONE` — payload invalido o campi immutabili
- `400` — payload vuoto (`Nessun campo aggiornabile presente`)
- `404` `E_UI_PRESET_NON_TROVATO`

---

### 6. Cancella preset

#### Input

- Metodo: `DELETE`
- Path canonico: `/api/v1/ui/admin/preset/{preset_id}/`
- Header sicurezza: `Authorization: Bearer <access_token>`

#### Output

- `200`: `{"data": {"deleted": true, "id": <preset_id>}, "meta": {...}}`.

Effetti collaterali (FK):

- `ui.lista_preset_colonna` (composizione) → `ON DELETE CASCADE` →
  cancellata in cascata
- `ui.lista_preferenza_utente.preset_base_id` → `ON DELETE SET NULL`
  (DB-2 atterrato 2026-05-07) → la preferenza utente sopravvive senza
  riferimento; il badge "preset aggiornato" (DEF-2) sparisce e
  l'utente lavora direttamente sul catalogo grezzo finche' non
  applica un altro preset

Errori:

- `404` `E_UI_PRESET_NON_TROVATO`

---

### 7. Composizione preset (read)

#### Input

- Metodo: `GET`
- Path canonico: `/api/v1/ui/admin/preset/{preset_id}/colonne/`
- Header sicurezza: `Authorization: Bearer <access_token>`

#### Output

- `200`:

```json
{
  "data": [
    {
      "preset_id": 12,
      "colonna_id": 5,
      "codice": "ragione_sociale",
      "etichetta": "Ragione sociale",
      "tipo_colonna": "identificatore",
      "ordine": 10,
      "larghezza": 240,
      "visibile": true,
      "fissata": true
    }
  ],
  "meta": {"request_id": "..."}
}
```

Ordine: `ordine ASC, colonna.id ASC`. Display fields (`codice`,
`etichetta`, `tipo_colonna`) via JOIN su `ui.lista_colonna`: il FE
non deve fare lookup separato.

Errori:

- `404` `E_UI_PRESET_NON_TROVATO` se `preset_id` inesistente
  (anche con `attivo=false` ammesso, perche' la riga esiste)

---

### 8. Replace atomico composizione preset

#### Input

- Metodo: `PUT`
- Path canonico: `/api/v1/ui/admin/preset/{preset_id}/colonne/`
- Header sicurezza: `Authorization: Bearer <access_token>`
- Body JSON:

```json
{
  "colonne": [
    {"colonna_id": 5, "ordine": 10, "larghezza": 240, "visibile": true, "fissata": true},
    {"colonna_id": 7, "ordine": 20, "larghezza": 130, "visibile": true, "fissata": false}
  ]
}
```

Whitelist root payload: `colonne`. Whitelist riga: `colonna_id`,
`ordine`, `larghezza`, `visibile`, `fissata`.

Vincoli:

- `colonne` (lista, anche vuota) — replace integrale
- `colonna_id` (int positivo, FK su `ui.lista_colonna.id`) — obbligatorio;
  duplicati in payload rifiutati con `E_UI_PRESET_VALIDAZIONE` (PK
  `(preset_id, colonna_id)` farebbe scattare un IntegrityError, ma
  filtriamo presto per messaggio parlante)
- `ordine` (int positivo) — obbligatorio
- `larghezza` (int positivo) — opzionale, default null
- `visibile`, `fissata` (bool stretto) — opzionali; default `visibile=true`,
  `fissata=false`

Implementazione: in transazione `transaction.atomic()` esegue
`DELETE FROM ui.lista_preset_colonna WHERE preset_id = ?` seguito da
`INSERT ... VALUES (...)` multi-row con tutte le righe del payload.

#### Output

- `200`: `{"data": {"preset_id": 12, "inserted": 2}, "meta": {...}}`.

Errori:

- `400` `E_UI_PRESET_VALIDAZIONE` — payload invalido o duplicato colonna
- `404` `E_UI_PRESET_NON_TROVATO`

---

### 9. Permessi colonna di una lista

#### Input

- Metodo: `GET`
- Path canonico: `/api/v1/ui/admin/liste/{lista_id}/permessi/`
- Header sicurezza: `Authorization: Bearer <access_token>`

#### Output

- `200`:

```json
{
  "data": {
    "results": [
    {
      "id": 42,
      "colonna_id": 7,
      "colonna_codice": "partita_iva",
      "colonna_etichetta": "Partita IVA",
      "colonna_gruppo": "Anagrafica fiscale",
      "profilo_accesso_id": 9001,
      "profilo_accesso_codice": "CLIENTE_PORTALE_STANDARD",
      "profilo_accesso_descrizione": "Profilo standard cliente portale",
      "livello_accesso": "BLOCCATO",
      "data_insert": "2026-05-08T11:00:00",
      "user_insert": "tid",
      "data_update": null,
      "user_update": null
    }
    ],
    "count": 1
  },
  "meta": {"request_id": "..."}
}
```

Ordine: `colonna.ordine_default ASC, colonna.codice ASC, profilo.codice ASC, id ASC`.
Display fields via INNER JOIN su `ui.lista_colonna` e
`config.profili_accesso`.

Errori:

- `404` `E_UI_LISTA_NON_TROVATA`

---

### 10. UPSERT permesso colonna

#### Input

- Metodo: `POST`
- Path canonico: `/api/v1/ui/admin/permessi/`
- Header sicurezza:
  - `Authorization: Bearer <access_token>`
  - `Idempotency-Key: <uuid-stringa>` — **obbligatorio**
- Body JSON:

```json
{
  "colonna_id": 7,
  "profilo_accesso_id": 9001,
  "livello_accesso": "BLOCCATO"
}
```

Whitelist payload: `colonna_id`, `profilo_accesso_id`, `livello_accesso`.

Vincoli:

- `colonna_id` (int positivo, FK su `ui.lista_colonna.id`) — obbligatorio
- `profilo_accesso_id` (int positivo, FK su `config.profili_accesso.id`)
  — obbligatorio
- `livello_accesso` (string enum `config.livello_accesso`) — uno tra
  `TUTTO`, `LETTURA`, `BLOCCATO`

Implementazione: INSERT con `ON CONFLICT ON CONSTRAINT
uq_ui_lista_colonna_permesso_col_profilo DO UPDATE SET
livello_accesso = EXCLUDED.livello_accesso, ...`. Una sola riga per
coppia `(colonna_id, profilo_accesso_id)`: il POST e' di fatto
idempotente verso la coppia (semantica UPSERT).

#### Output

- `200`:

```json
{
  "data": {
    "id": 42,
    "colonna_id": 7,
    "profilo_accesso_id": 9001,
    "livello_accesso": "BLOCCATO"
  },
  "meta": {"request_id": "..."}
}
```

`id` e' il PK risultante (nuovo se INSERT, esistente se UPDATE).

Errori:

- `400` `E_IDEMPOTENCY_KEY_REQUIRED`
- `400` `E_UI_PERMESSO_VALIDAZIONE` — payload invalido (livello sconosciuto,
  FK non valida, chiavi extra)

---

### 11. Cancella permesso colonna

#### Input

- Metodo: `DELETE`
- Path canonico: `/api/v1/ui/admin/permessi/{permesso_id}/`
- Header sicurezza: `Authorization: Bearer <access_token>`

#### Output

- `200`: `{"data": {"deleted": true, "id": <permesso_id>}, "meta": {...}}`.

Effetto: il permesso viene rimosso → la colonna torna al
default deny-list/allow-list applicato da `ui.fn_resolve_lista_config`.

Errori:

- `404` `E_UI_PERMESSO_NON_TROVATO` (404 esplicito anche se la riga non
  esisteva: il FE che chiama DELETE su id immaginario merita feedback netto)


### 12-21. Definizioni e colonne (Fase 2, SUPER_ADMIN)

Tutte su `AdminAPIView` (solo SUPER_ADMIN, nessuna azione di processo).
Service: `ListaDefinizioneAdminService`, `ListaColonnaAdminService`.

**Regole comuni.** Il payload passa dalla whitelist del service: una chiave
fuori da `CREATE_KEYS` / `UPDATE_KEYS` è un `400` (`…_VALIDAZIONE`), mai
ignorata. I booleani devono essere booleani JSON. Il `PATCH` vuole almeno un
campo (`require_campi_da_aggiornare`) e lavora per delta. `POST` con
`Idempotency-Key` obbligatoria. Create e `PATCH` rispondono il dettaglio;
`DELETE` risponde `{"deleted": true, "id": <id>}`.

| # | Rotta | Corpo / risposta | Errori |
| --- | --- | --- | --- |
| 12 | `GET /admin/definizioni/` | `{"results": [...], "count": n}`: tutte, disattivate comprese, `attivo DESC, codice, id` | — |
| 13 | `POST /admin/definizioni/` | `CREATE_KEYS`: `codice`, `descrizione`, `schema_dati` (obbligatori), `vista_sql`, `note`, `attivo` (default `true`) | `E_UI_DEFINIZIONE_VALIDAZIONE` (anche codice duplicato, campo `codice`), `E_UI_VISTA_SQL_NON_TROVATA` |
| 14 | `GET /admin/definizioni/{id}/` | la definizione completa | 404 `E_UI_DEFINIZIONE_NON_TROVATA` |
| 15 | `PATCH /admin/definizioni/{id}/` | `UPDATE_KEYS` = `CREATE_KEYS` (⛔ `multi_emittente` non è scrivibile) | come 13, più 404 |
| 16 | `DELETE /admin/definizioni/{id}/` | — | 404; 409 `E_UI_DEFINIZIONE_IN_USO` se ha colonne, preset o preferenze (FK RESTRICT): l'alternativa è `PATCH attivo=false` |
| 17 | `GET /admin/definizioni/{id}/colonne/` | `{"results": [...], "count": n}`: tutte le colonne, disattivate comprese | 404 `E_UI_DEFINIZIONE_NON_TROVATA` |
| 18 | `POST /admin/definizioni/{id}/colonne/` | `CREATE_KEYS`: `codice`, `etichetta`, `etichetta_estesa`, `etichetta_i18n_key`, `campo_sorgente`, `tipo_colonna`, `tipo_dato`, `formato`, `larghezza_default`, `ordine_default`, `allineamento` (`left`/`right`/`center`), `gruppo`, `gruppo_ordine`, `filtrabile`, `ordinabile`, `esportabile`, `ricercabile_full`, `sensibile`, `attivo`; `lista_id` dal path | `E_UI_COLONNA_VALIDAZIONE` (codice duplicato nella lista, colonna `azione` esportabile, …), `E_UI_CAMPO_SORGENTE_NON_TROVATO`, 404 definizione |
| 19 | `GET /admin/colonne/{id}/` | la colonna completa | 404 `E_UI_COLONNA_NON_TROVATA` |
| 20 | `PATCH /admin/colonne/{id}/` | `UPDATE_KEYS` = `CREATE_KEYS` (`lista_id` immutabile) | come 18, più 404 |
| 21 | `DELETE /admin/colonne/{id}/` | — | 404; 409 `E_UI_COLONNA_IN_USO` se una preferenza utente la nomina (soft-block applicativo); preset e permessi della colonna vanno via in CASCADE |

---

## Codici errore

Lo status segue la classe a catalogo (`error_policies_generated.py`):

| Codice | HTTP | UI action |
| --- | --- | --- |
| `E_UI_LISTA_NON_TROVATA` | 404 | show_empty_state |
| `E_UI_PRESET_VALIDAZIONE` | 400 | highlight_form_fields |
| `E_UI_PRESET_NON_TROVATO` | 404 | show_empty_state |
| `E_UI_PERMESSO_VALIDAZIONE` | 400 | highlight_form_fields |
| `E_UI_PERMESSO_NON_TROVATO` | 404 | show_empty_state |
| `E_UI_DEFINIZIONE_VALIDAZIONE` | 400 | highlight_form_fields |
| `E_UI_DEFINIZIONE_NON_TROVATA` | 404 | show_empty_state |
| `E_UI_DEFINIZIONE_IN_USO` | 409 | show_error_banner |
| `E_UI_COLONNA_VALIDAZIONE` | 400 | highlight_form_fields |
| `E_UI_COLONNA_NON_TROVATA` | 404 | show_empty_state |
| `E_UI_COLONNA_IN_USO` | 409 | show_error_banner |
| `E_UI_VISTA_SQL_NON_TROVATA` · `E_UI_CAMPO_SORGENTE_NON_TROVATO` | 400 | guard DB su `vista_sql` / `campo_sorgente` |
| `E_UI_MULTI_EMITTENTE_NON_SCRIVIBILE` | 403 | guard DB: `multi_emittente` non si scrive da qui |
| `E_IDEMPOTENCY_KEY_REQUIRED` | 400 | show_error_banner |

## Regole

- **Defense-in-depth**: il route guard FE nasconde la voce sidebar a chi
  non ha alcuna delle 2 azioni; il backend rifiuta comunque (403)
  qualunque chiamata diretta senza permesso adeguato. Niente trust al
  FE.
- **Idempotency-Key obbligatoria** su ogni POST: §4 (preset), §10
  (permesso), §13 (definizione), §18 (colonna). Pattern allineato a `api.md`. Genera la chiave lato FE con
  `crypto.randomUUID()`.
- **Skip area check**: tutte le 12 view lo saltano (`skip_area_check = True`
  sulle 8 di Fase 1, implicito in `AdminAPIView` sulle 4 di Fase 2)
  perche' lo schema `ui` non e' un'area funzionale di business. Il check
  e' invece sull'azione di processo (`<method>_permission`) o sulla
  combinazione OR-azioni (`_require_any_action`, vedi §1).
- **Audit fields**: `user_insert`/`user_update` derivati dall'utente
  autenticato via helper centralizzato `apps.ui.services._audit.user_label`
  (fallback `'system'` per anonimi/test).
- **Drift risk** documentato sui set `_AMBITI_AMMESSI` e `_LIVELLI_AMMESSI`:
  duplicano gli enum DB (`ui.ambito_preset`, `config.livello_accesso`)
  per filtrare presto con messaggio parlante; il DB resta single source
  di verita' (FK enum garantisce la guard finale).

## Dipendenze DB

Tabelle:

- `ui.lista_definizione` — read-only (lookup Select header + 404 guard)
- `ui.lista_colonna` — read-only (catalogo grezzo)
- `ui.lista_preset` — CRUD (testata preset)
- `ui.lista_preset_colonna` — replace atomico (composizione)
- `ui.lista_colonna_permesso` — UPSERT/DELETE (permessi colonna)
- `ui.lista_preferenza_utente` — non modificata, ma impattata dal
  DELETE preset via `ON DELETE SET NULL` su `preset_base_id` (DB-2)

Lookup whitelist:

- `config.profili_accesso` nella lista del lookup generico
  (`config.tabelle_gestibili`, colonna `lookup`) per popolare i Select profilo nei
  drawer admin via lookup generico
  `GET /api/v1/core/lookup/codici/?rel=config.profili_accesso`.

ENUM coinvolti:

- `ui.ambito_preset` (`sistema` / `emittente_fiscale` / `ruolo`) →
  Python `_AMBITI_AMMESSI`
- `config.livello_accesso` (`TUTTO` / `LETTURA` / `BLOCCATO`) →
  Python `_LIVELLI_AMMESSI` + FE `LIVELLO_ACCESSO`

Vincoli rilevanti (tutti enforced lato DB):

- `uq_ui_lista_preset_lista_codice` — UNIQUE codice per lista
- `uq_ui_lista_preset_default` — partial UNIQUE 1 default per scope
- `chk_ui_lista_preset_ambito_refs` — coerenza ambito ↔ refs
- `uq_ui_lista_colonna_permesso_col_profilo` — UNIQUE coppia colonna/profilo

Azioni di processo (seedate in `config.azioni_processo` 2026-05-08):

- `ui_preset_manage` (id 16, area `config`)
- `ui_permesso_manage` (id 17, area `config`)

## Note di migrazione

- Blocco F Fase 1: implementati i 2 CRUD operativi (preset + permessi
  colonna).
- **Blocco F Fase 2 (DEF-5b, 2026-05-10)**: implementati i CRUD su
  `ui.lista_definizione` e `ui.lista_colonna`. SUPER_ADMIN-only
  (`AdminAPIView` + `IsAdminZeroERP`), niente nuove azioni di processo.
  Workflow draft per registrare liste con vista SQL non ancora atterrata:
  creare con `attivo=false` (o `vista_sql=null`), il trigger
  `trgfn_ui_lista_definizione_a10_valida_vista_sql` skippa la
  validazione. Cancellazione bloccata da FK RESTRICT
  (`E_UI_DEFINIZIONE_IN_USO` / `E_UI_COLONNA_IN_USO`) e da soft-block
  applicativo per preferenze utente (count JSONB
  `configurazione->colonne` per codice). UX vincolo: forzato
  `esportabile=false` quando `tipo_colonna='azione'` (CHECK
  `chk_ui_lista_colonna_azione_non_esportabile`). Pagina FE:
  `/amm-software/personalizzazioni-liste-tecniche`, voce sidebar
  `adminOnly: true`. Voce sidebar separata da `/config/personalizzazioni-liste`
  (Fase 1, operativa). Endpoint nuovi: §12-§21 della tabella sopra.
- **Pagina FE: solo `/config/personalizzazioni-liste`** in Fase 1.
  Decisione 2026-05-08: la doppia voce sidebar ipotizzata in §11/Blocco F
  del WIP (config + amm-software) e' stata semplificata a una sola
  entry-point in `config`. Motivazione: in Fase 1 i tab Fase 2
  (Definizioni / Catalogo colonne) sono solo placeholder, quindi la
  voce duplicata in amm-software era cosmeticamente confusa per il
  super-admin. Tenant admin con azione abilitata e SUPER_ADMIN entrano
  dallo stesso path. Quando atterra Fase 2 si crea una view dedicata
  sotto `/amm-software/personalizzazioni-liste-tecniche` con i 2 tab
  amministrativi reali (CRUD `lista_definizione` + `lista_colonna`),
  separata semanticamente dalla pagina operativa di config.
- DEF-5 ("Admin UI per gestione preset e catalogo") in
  `sviluppo-personalizzazioni-liste_def.md` viene assorbito da Blocco F:
  aggiornare DEF-5 quando Fase 2 atterra.
- L'EmittenteFiscaleField del drawer preset ramo `emittente_fiscale`
  e' ancora un `InputNumber`. Switch al building block
  `EmittenteFiscaleField` rinviato a Fase 2 (la prop-set auto-adaptive
  del component non e' immediato per il caso preset di sistema).
