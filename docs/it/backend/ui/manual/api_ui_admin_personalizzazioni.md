# API UI Admin — Gestione personalizzazioni liste (Django)

## Scopo

Esporre via HTTP la gestione amministrativa dei **preset** di lista
(`ui.lista_preset` + composizione `ui.lista_preset_colonna`) e dei
**permessi colonna** (`ui.lista_colonna_permesso`) per il refactor
personalizzazioni liste — Blocco F Fase 1 — e, in Fase 2, la gestione
tecnica delle **definizioni** di lista e delle loro **colonne**
(`ui.lista_definizione`, `ui.lista_colonna`, solo SUPER_ADMIN). Le
operazioni di Fase 1 le consuma la pagina `/config/personalizzazioni-liste`
(`GestionePersonalizzazioniListeView`: tenant admin con azione di processo
abilitata, o SUPER_ADMIN); quelle di Fase 2 la pagina
`/amm-software/personalizzazioni-liste-tecniche`
(`PersonalizzazioniListeTecnicheView`).

## Contesto

Strato amministrativo del refactor `sviluppo-personalizzazioni-liste.md`
(Blocco F atterrato 2026-05-08). Estende il modulo `apps.ui` esistente
(Blocco C runtime) con:

- repository admin `apps.ui.db.ui_admin_repository.UiAdminRepository`
  (CRUD diretto su 5 tabelle dello schema `ui` + display fields via
  JOIN su `config.profili_accesso` e `anagrafiche.emittenti_fiscali`);
- 4 service admin in `apps.ui.services/`:
  - `ListaDefinizioneAdminService` (Select header lista corrente +
    catalogo colonne grezzo in Fase 1; CRUD delle definizioni in Fase 2);
  - `ListaColonnaAdminService` (CRUD delle colonne di una definizione,
    Fase 2);
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

Il check OR-azioni del Select header (`_require_any_action` in
`views_admin.py`) riusa la cache permessi della richiesta via
`cache_permessi_richiesta(request)` (il context manager che legge quella di
`ZeroERPPermission`), per evitare round-trip DB ridondanti
(`is_super_admin` + 2 `check_azione`). Il superuser Django
(`user.is_superuser`) salta il controllo prima ancora di aprire la cache.

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
| 21 | `DELETE /admin/colonne/{id}/` | admin | Cancella (409 se un preset la compone) |

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
      "pagina_dimensione": 25,
      "ordinamento_default": [{"col": "ragione_sociale", "dir": "asc"}],
      "attivo": true,
      "colonne_count": 14,
      "nata_dal_seed": true,
      "campi_del_software": ["lista_id", "codice", "ambito", "profilo_accesso_id", "emittente_fiscale_id"],
      "non_editable_fields": ["lista_id", "ambito", "profilo_accesso_id", "emittente_fiscale_id"],
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

`nata_dal_seed` / `campi_del_software` — la superficie del seed di primo
impianto (dal 2026-11-20, R-UI-sup del §16.15 di
brief-db-seed-primo-impianto-non-si-riscrive), letta da
`dbops.fn_seed_superficie` in `LEFT JOIN LATERAL`. Le portano anche le
liste e i dettagli di definizioni e colonne (rotte 12, 14, 17, 19). Su una
riga nata dal seed `campi_del_software` elenca le colonne che il programma
stabilisce (il guard rifiuta di cambiarle); altrimenti è vuoto, mai `null`.
⭐ Nessun elenco di colonne nel backend: lo dà il DB, e il frontend spegne il
cestino e quei campi col motivo.

`non_editable_fields` — i campi **fermi per modello** della riga (dal
2026-11-22, `/verifica` di brief-db-revisione-ui): le colonne che un trigger
di lock vivo blocca (il `codice` di definizioni e colonne, il «posto» del
preset: `lista_id`, `ambito`, `profilo_accesso_id`, `emittente_fiscale_id`) e
i lock condizionali valutati sulla riga, da `dbops.fn_non_editable_fields`
nella stessa SELECT. Lo portano liste e dettagli delle tre tabelle; vuoto,
mai `null`. Il frontend spegne quei campi in modifica e li toglie dal PATCH
(BB `campoFermo`). ⭐ Anche qui nessun elenco nel backend né nel frontend.

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
  "pagina_dimensione": 25,
  "ordinamento_default": [{"col": "ragione_sociale", "dir": "asc"}],
  "attivo": true
}
```

Whitelist payload: `lista_id`, `codice`, `descrizione`, `ambito`,
`profilo_accesso_id`, `emittente_fiscale_id`,
`pagina_dimensione`, `ordinamento_default`, `attivo`. ⛔ `filtri_default` non
esiste più (Q38 di brief-db-revisione-ui; colonna ritirata dal DB col giro 2,
2026-11-21): i filtri di partenza di una lista sono dello store, e la chiave
nel payload è un `400` della whitelist.
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
- ⛔ `is_default` non esiste più (dal 2026-11-20, Q26 di
  brief-db-revisione-ui): un preset vale se è **acceso**, e la chiave nel
  payload è un `400` della whitelist
- `pagina_dimensione` (int o `null` = «il default») — una delle misure del
  catalogo `ui.misure_pagina`. Il backend ne controlla solo la forma: una
  misura fuori catalogo la rifiuta il DB (guard + FK) con
  `400 E_UI_MISURA_PAGINA_NON_AMMESSA`. ⛔ Fino al 2026-09-30 il service
  applicava un suo tetto a `500`. Il drawer la sceglie da un `Select` sulle
  misure del catalogo, e la manda sempre (anche `null`: e' il modo di tornare
  al default)
- `ordinamento_default` (lista o `null` = il preset non dice l'ordinamento) —
  il backend ne controlla solo che sia una lista; la forma la giudica il DB
  (giro 2 di brief-db-revisione-ui): ogni voce `{col, dir}` con le sole due
  chiavi, `col` il **codice** di una colonna della lista (accesa o spenta, mai
  il campo sorgente: Q40 (b)), unico nell'elenco, `dir` `asc` o `desc`.
  Altrimenti `400 E_UI_CONFIGURAZIONE_FORMA`, con la voce e il motivo
- `attivo` (bool stretto) — default `false`: la bozza nasce spenta, si
  compone e poi si accende. ⭐ Un posto (lista, ambito, profilo, azienda) ha
  al più **un** preset acceso: l'UNIQUE parziale `uq_ui_lista_preset_posto`
  (`NULLS NOT DISTINCT WHERE attivo`) rifiuta il secondo, e il service lo
  traduce in `400 E_UI_PRESET_VALIDAZIONE` sul campo `attivo` («spegni prima
  quello acceso», BE23)

#### Output

- `200`: dettaglio preset appena creato (vedi §3 — singolo oggetto, no
  array).

Errori:

- `400` `E_IDEMPOTENCY_KEY_REQUIRED` — header mancante
- `400` `E_UI_PRESET_VALIDAZIONE` — payload invalido (chiavi extra,
  tipi non corretti, ambito sconosciuto, refs incoerenti con CHECK,
  UNIQUE codice violato, un secondo preset acceso nello stesso posto)
- `404` `E_UI_LISTA_NON_TROVATA`

---

### 5. Aggiorna preset (PATCH testata)

#### Input

- Metodo: `PATCH`
- Path canonico: `/api/v1/ui/admin/preset/{preset_id}/`
- Header sicurezza: `Authorization: Bearer <access_token>`
- Body JSON: subset dei campi mutabili presenti nel payload.

Whitelist update: `codice`, `descrizione`,
`pagina_dimensione`, `ordinamento_default`, `attivo`.

Su un preset nato dal seed, `codice` è una colonna del programma: il guard
risponde `409 E_SEED_COLONNA_DEL_SOFTWARE` col campo acceso (R-UI2).

Campi **immutabili** (rifiutati con `E_UI_PRESET_VALIDAZIONE` se
presenti nel payload, prima della validazione altri campi):
`lista_id`, `ambito`, `profilo_accesso_id`, `emittente_fiscale_id`.
Per cambiare ambito o riferimenti si crea un nuovo preset. ⭐ Dal giro 2b di
brief-db-revisione-ui (U14) il posto lo tiene anche il DB, col lucchetto
`E_UI_PRESET_POSTO_IMMUTABILE` (`409`): la rete per chi scrive senza passare dal
service.

#### Output

- `200`: dettaglio preset aggiornato (vedi §3).

Errori:

- `400` `E_UI_PRESET_VALIDAZIONE` — payload invalido o campi immutabili,
  o un secondo preset acceso nello stesso posto (campo `attivo`)
- `400` `E_UI_CONFIGURAZIONE_FORMA` — `ordinamento_default` fuori forma
  (vedi §4)
- `400` `E_UI_PRESET_VALIDAZIONE` — payload vuoto (`Nessun campo
  aggiornabile presente`)
- `404` `E_UI_PRESET_NON_TROVATO`
- `409` `E_SEED_COLONNA_DEL_SOFTWARE` — una colonna del programma su un
  preset nato dal seed

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
  riferimento, e `ui.trgfn_preferenza_preset_base_snapshot` vede il NULL
  come un cambio di base: azzera lo snapshot. Le chiavi che la preferenza
  non contiene vengono dal preset di base **di oggi** (`ui.fn_preset_di_base`:
  ruolo, poi azienda, poi sistema), e la risoluzione dice
  `preset_base_cambiato = true` (banner «Riallinea»). Dal catalogo grezzo
  si parte solo se nessun preset vale

Errori:

- `404` `E_UI_PRESET_NON_TROVATO`
- `409` `E_SEED_RIGA_NON_CANCELLABILE` — il preset è nato dal seed di primo
  impianto: si spegne, non si cancella (R-UI1)

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

- `colonne` (lista, anche vuota) — **obbligatoria**, replace integrale. Una
  chiave assente, o un valore che non è una lista di oggetti, è un `400
  E_UI_PRESET_VALIDAZIONE` (BB `voci`): la composizione si sostituisce in
  blocco, non si «svuota» per omissione
- `colonna_id` (int positivo, FK su `ui.lista_colonna.id`) — obbligatorio;
  duplicati in payload rifiutati con `E_UI_PRESET_VALIDAZIONE` (PK
  `(preset_id, colonna_id)` farebbe scattare un IntegrityError, ma
  filtriamo presto per messaggio parlante). ⭐ La colonna è **della lista del
  preset**: dal giro 2b di brief-db-revisione-ui (U14) lo garantisce la FK
  composita `fk_ui_lista_preset_colonna_colonna_della_lista`, e il service la
  traduce in `400 E_UI_PRESET_VALIDAZIONE` sul campo `colonne`. Il `lista_id`
  della riga lo scrive il DB dal preset: il backend non lo passa
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

**Righe nate dal seed di primo impianto** (dal 2026-11-20, R-UI1 e R-UI2
del §16.15 di brief-db-seed-primo-impianto-non-si-riscrive). Il `DELETE` di
una definizione o di una colonna di seed è un `409
E_SEED_RIGA_NON_CANCELLABILE` (si spegne con `PATCH attivo=false`); il
`PATCH` di una colonna del programma è un `409 E_SEED_COLONNA_DEL_SOFTWARE`
col campo acceso. Sulla definizione sono `codice`, `descrizione`,
`schema_dati`, `vista_sql`; sulla colonna `codice`, `campo_sorgente`,
`tipo_colonna`, `tipo_dato`, `formato`, i flag di comportamento e
`etichetta_i18n_key` — ma l'elenco vero è `campi_del_software` della riga.
I codici li traduce il middleware dalla policy generata: il service non li
mappa.

| # | Rotta | Corpo / risposta | Errori |
| --- | --- | --- | --- |
| 12 | `GET /admin/definizioni/` | `{"results": [...], "count": n}`: tutte, disattivate comprese, `attivo DESC, codice, id` | — |
| 13 | `POST /admin/definizioni/` | `CREATE_KEYS`: `codice`, `descrizione`, `schema_dati` (obbligatori), `vista_sql`, `note`, `attivo` (default `true`). Il dettaglio porta anche le tre **dichiarazioni** della lista (`multi_emittente`, `perimetro_emittente`, `legge_lineage`), in sola lettura: ⛔ si scrivono solo dal seed | `E_UI_DEFINIZIONE_VALIDAZIONE` (anche codice duplicato, campo `codice`; un testo vuoto sul suo campo), `E_UI_VISTA_SQL_NON_TROVATA` |
| 14 | `GET /admin/definizioni/{id}/` | la definizione completa | 404 `E_UI_DEFINIZIONE_NON_TROVATA` |
| 15 | `PATCH /admin/definizioni/{id}/` | `UPDATE_KEYS` = `CREATE_KEYS` **senza `codice`**: il codice è la chiave con cui la schermata si cerca, e non si cambia (giro 4 di brief-db-revisione-ui, BE12: nel corpo è un `400 E_UI_DEFINIZIONE_VALIDAZIONE` sul campo; a DB il lucchetto `E_UI_LISTA_CODICE_IMMUTABILE`). ⛔ Le tre dichiarazioni non sono scrivibili. Spegnere una lista con colonne e preset accesi **passa** e li sospende senza toccarli (U22, Q13): riaccesa, torna com'era | come 13, più 404; `400 E_UI_LISTA_COLONNE_ORFANE` se il cambio di vista o di schema, o la riaccensione, lascerebbe colonne senza il loro campo (il messaggio le nomina) |
| 16 | `DELETE /admin/definizioni/{id}/` | — | 404; 409 `E_UI_DEFINIZIONE_IN_USO` se ha colonne, preset o preferenze (FK RESTRICT): l'alternativa è `PATCH attivo=false` |
| 17 | `GET /admin/definizioni/{id}/colonne/` | `{"results": [...], "count": n}`: tutte le colonne, disattivate comprese | 404 `E_UI_DEFINIZIONE_NON_TROVATA` |
| 18 | `POST /admin/definizioni/{id}/colonne/` | `CREATE_KEYS`: `codice`, `etichetta`, `etichetta_estesa`, `etichetta_i18n_key`, `campo_sorgente`, `origine_campo` (`VISTA` default / `LINEAGE`: la genealogia dei documenti, solo su una lista che dichiara `legge_lineage`), `tipo_colonna`, `tipo_dato`, `formato`, `larghezza_default`, `ordine_default`, `allineamento` (`left`/`right`/`center`), `gruppo`, `gruppo_ordine`, `filtrabile`, `ordinabile`, `esportabile`, `ricercabile_full`, `sensibile`, `attivo`; `lista_id` dal path. **Obbligatori**: `codice`, `etichetta`, `tipo_colonna` (`identificatore` / `informazione` / `azione`), `tipo_dato` (`string` / `numeric` / `date` / `datetime` / `boolean` / `enum`), `ordine_default`. Tetti: `larghezza_default` ≤ 4000, `ordine_default` e `gruppo_ordine` ≤ 100000. ⭐ I default dei flag seguono il modello, solo per il flag non mandato: senza `campo_sorgente` la colonna nasce non esportabile, una `LINEAGE` non filtrabile né ordinabile. ⛔ Un valore esplicito non si corregge: i vincoli fra campi li giudica il DB (un'azione non ha campo sorgente; senza campo sorgente non si esporta; la genealogia non si filtra, non si ordina, non si cerca) | `E_UI_COLONNA_VALIDAZIONE` sul campo che lo risolve (codice duplicato nella lista, i tre vincoli sopra, …), `E_UI_CAMPO_SORGENTE_NON_TROVATO`, `E_UI_LINEAGE_NON_DICHIARATA`, 404 definizione |
| 19 | `GET /admin/colonne/{id}/` | la colonna completa | 404 `E_UI_COLONNA_NON_TROVATA` |
| 20 | `PATCH /admin/colonne/{id}/` | `UPDATE_KEYS` = `CREATE_KEYS` **senza `codice`** (preferenze e preset cercano la colonna per codice: BE12; a DB `E_UI_COLONNA_CODICE_IMMUTABILE`); `lista_id` e `codice` nel corpo sono un `400` sul campo. Nessun valore derivato: i vincoli fra campi si giudicano sul valore finale della riga | come 18, più 404 |
| 21 | `DELETE /admin/colonne/{id}/` | — | 404; 409 `E_UI_COLONNA_IN_USO` se un preset la compone (il messaggio nomina i preset per codice; le due FK della composizione, `fk_lista_preset_colonna_lista_colonna` e la composita `fk_ui_lista_preset_colonna_colonna_della_lista`, sono NO ACTION e, se scattano lo stesso, danno lo stesso codice). I **permessi** della colonna vanno via in CASCADE, e la voce esce dalle preferenze utente che la nominano (lo fa il DB, `ui.trgfn_voce_ritira_dalle_preferenze`: una preferenza non ferma la cancellazione, Q56 di brief-db-revisione-ui). Una colonna nata dal seed salta il controllo dei preset: risponde il guard del DB, `409 E_SEED_RIGA_NON_CANCELLABILE` (si spegne con `PATCH attivo=false`) |

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
| `E_UI_LINEAGE_NON_DICHIARATA` | 400 | guard DB: colonna `LINEAGE` su una lista che non dichiara `legge_lineage` |
| `E_UI_LISTA_COLONNE_ORFANE` | 400 | guard DB su `vista_sql`: colonne `VISTA` senza il loro campo nella relazione nuova |
| `E_UI_LISTA_CODICE_IMMUTABILE` · `E_UI_COLONNA_CODICE_IMMUTABILE` | 409 | lucchetti DB sul codice (il BE lo rifiuta prima, sul campo) |
| `E_UI_LISTA_DICHIARAZIONE_NON_SCRIVIBILE` | 403 | guard DB: una dichiarazione della lista (`multi_emittente`, `perimetro_emittente`, `legge_lineage`) non si scrive da qui; il messaggio nomina la colonna. Sostituisce `E_UI_MULTI_EMITTENTE_NON_SCRIVIBILE`, ritirato il 2026-11-21 |
| `E_UI_MISURA_PAGINA_NON_AMMESSA` | 400 | guard DB: `pagina_dimensione` del preset fuori dal catalogo `ui.misure_pagina` |
| `E_UI_CONFIGURAZIONE_FORMA` | 400 | guard DB sulla forma della configurazione |
| `E_UI_PRESET_POSTO_IMMUTABILE` | 409 | lucchetto DB sul posto del preset (lista, ambito, profilo, emittente) |
| `E_SEED_RIGA_NON_CANCELLABILE` | 409 | guard DB: una riga nata dal seed di primo impianto si spegne, non si cancella |
| `E_SEED_COLONNA_DEL_SOFTWARE` | 409 | guard DB: un campo della riga di seed che appartiene al software non si modifica |
| `E_IDEMPOTENCY_KEY_REQUIRED` | 400 | show_error_banner |

Per le righe che descrivono un guard, la `ui_action` e' quella della classe:
`show_error_banner` (`error_policies.py`).

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
- **Audit fields**: `user_insert`/`user_update` li scrive il DB, il trigger
  `script.trgfn_audit_data_user_generic`, dall'utente della richiesta (GUC
  `app.jwt_user`). Il repository non li nomina: non c'e' un helper Python.
- **Drift risk** documentato sui set `_AMBITI_AMMESSI` e `_LIVELLI_AMMESSI`:
  duplicano gli enum DB (`ui.ambito_preset`, `config.livello_accesso`)
  per filtrare presto con messaggio parlante; il DB resta single source
  di verita' (FK enum garantisce la guard finale).

## Dipendenze DB

Tabelle:

- `ui.lista_definizione` — lettura in Fase 1 (lookup Select header + 404
  guard), CRUD in Fase 2 (§12-§16)
- `ui.lista_colonna` — lettura in Fase 1 (catalogo grezzo), CRUD in Fase 2
  (§17-§21)
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
- `uq_ui_lista_preset_posto` — un solo preset **acceso** per posto (lista,
  ambito, profilo, emittente; `NULLS NOT DISTINCT WHERE attivo`). Ha preso il
  posto di `uq_ui_lista_preset_default`, ritirato con `is_default` il
  2026-11-20
- `fk_ui_lista_preset_colonna_preset_della_lista` e
  `fk_ui_lista_preset_colonna_colonna_della_lista` — FK composite della
  composizione: preset e colonna devono essere della stessa lista
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
  (`E_UI_DEFINIZIONE_IN_USO`; per le colonne FK NO ACTION della composizione
  dei preset, `E_UI_COLONNA_IN_USO`, anticipata dal controllo dei preset
  che la compongono, §21). Le preferenze utente che nominano la colonna non
  fermano la cancellazione: la voce la toglie il DB (Q56 di
  brief-db-revisione-ui). I vincoli fra campi della colonna
  (azione senza campo sorgente, senza campo non esportabile, genealogia solo
  mostrata) sono CHECK del DB dal giro 4 di brief-db-revisione-ui: il drawer
  spegne ciò che il DB rifiuterebbe, il service non li ricopia. Pagina FE:
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
