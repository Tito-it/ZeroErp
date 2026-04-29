# API Amministrazione Software

## Scopo

Documentazione completa delle API REST del modulo **Amm. Software** (Amministrazione).
Questi endpoint gestiscono utenti (operatori), permessi individuali, profili reparto
e lookup di supporto.

## Contesto

Il modulo Amm. Software e' il pannello di controllo per l'amministratore di sistema.
Permette di creare operatori, assegnare ruoli, configurare override di permessi per
singolo utente e definire profili di accesso per reparto (unita' organizzativa).

Tutti gli endpoint richiedono autenticazione JWT con ruolo **ADMIN** (`AdminAPIView`).
Post-cutover multi-face il check ADMIN delega a `PermissionResolver.is_super_admin`
(binding `SUPER_ADMIN` su `config.profili_accesso_bindings`, profilo seed id 9100).
L'endpoint lista utenti ha throttling search attivo (`is_search_endpoint = True`).

Le risposte seguono l'envelope standard `{ "data": {...}, "meta": {...} }`.

Base URL: `/api/v1/amm-software/`

> **Note di evoluzione 2026-04-29 (Fasi 0-2 multi-face)**:
>
> - **Fase 0** (LANDED): nuovo endpoint summary mapping BA in `anagrafiche`
>   (vedi [api_emittenti_fiscali.md §5.4](../../anagrafiche/manual/api_emittenti_fiscali.md)).
>   Niente impatto su `amm-software`.
> - **Fase 1** (BE LANDED, attesa fn DB `script.fn_get_operatore_detail`):
>   - PATCH/POST `/operatori/`: contratto pubblico **rifiuta** `ruolo_sistema`
>     legacy → usa `is_super_admin` + `attivo` (vedi §1.2 e §1.4).
>   - GET dettaglio: 6 nuovi campi capability (`can_invite`/`invite_reason`,
>     `can_disable`/`disable_reason`, `can_demote_super_admin`/`demote_reason`)
>     piu' `is_super_admin`, `ruolo_applicativo`, `last_login`,
>     `invito_inviato_at`, `deve_cambiare_password`, `emittenti_descrizione`.
>   - Endpoint `disabilita`: nuovo errore `E_PROFILO_ULTIMO_SUPER_ADMIN`
>     (HTTP 409) tradotto dal trigger DB.
>   - Nuovo endpoint `riattiva` (vedi §1.6).
> - **Fase 2** (LANDED): scope emittenti dichiarativo via
>   `script.fn_get_user_emittenti_scope` / `fn_change_user_emittenti_scope`
>   (vedi §2.5/§2.6). Shape `{scope_mode, emittenti_ids, ...capability}`,
>   `MULTI` chiuso applicativamente post Q2.
> - **Fase 3** (LANDED): form-defaults emittente fiscale via `ParameterService`
>   (cascata user->group->emittente->default). Nuovi endpoint:
>   `GET /emittenti-fiscali/form-defaults/` (§5.1) +
>   `GET /lookup/rounding-modes/` (§4.5). Seed `config.parameters` 3 chiavi:
>   `EMITTENTE_DEFAULT_BOLLO_AUTO`/`_BOLLO_SOGLIA`/`_ROUNDING_POLICY`. Il
>   campo `attivo` non passa per parameters (default DB gia' `true`).
>   Pattern allineato a `ApiArticoliFormDefaults` (catalogo Fase 8).

---

## 1. Utenti

### 1.1 GET /api/v1/amm-software/operatori/ -- Lista utenti

Restituisce la lista paginata degli operatori con filtri opzionali.

**Parametri query string:**

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `search` | string | no | Ricerca libera su username, nome, cognome, email (ILIKE) |
| `ruolo_sistema` | string | no | Filtra per ruolo: `ADMIN`, `OPERATIVO`, `DISABILITATO` |
| `unita_organizzativa_id` | int | no | Filtra per unita' organizzativa |
| `is_active` | bool | no | Filtra per stato attivo (`true`/`false`/`1`/`0`) |
| `limit` | int | no | Numero massimo risultati (default 50, max 200) |
| `offset` | int | no | Offset per paginazione (default 0) |
| `order_by` | string | no | Colonna di ordinamento: `last_name`, `username`, `ruolo_sistema`, `is_active`, `unita_organizzativa_nome`, `data_insert` |
| `order_dir` | string | no | Direzione ordinamento: `ASC` o `DESC` |

**Risposta:**

```json
{
  "data": {
    "count": 42,
    "results": [
      {
        "auth_user_id": 1,
        "username": "mtitini",
        "email": "m.titini@example.com",
        "first_name": "Michele",
        "last_name": "Titini",
        "ruolo_sistema": "ADMIN",
        "is_active": true,
        "unita_organizzativa_id": 2,
        "unita_organizzativa_nome": "Sviluppo",
        "risorsa_umana_id": 5,
        "attivo": true,
        "valido_al": null,
        "data_insert": "2026-01-15 10:30:00+00"
      }
    ]
  },
  "meta": { "request_id": "..." }
}
```

**Esempio curl:**

```bash
curl -H "Authorization: Bearer <token>" \
  "https://host/api/v1/amm-software/operatori/?search=titini&ruolo_sistema=ADMIN&limit=10"
```

---

### 1.2 POST /api/v1/amm-software/operatori/ -- Crea utente

Crea un nuovo operatore completo: utente Django, soggetto persona fisica, risorsa umana.
La creazione e' orchestrata dalla funzione DB `anagrafiche.fn_crea_operatore`.

**Contract Fase 1 multi-face**: il payload accetta `is_super_admin` (booleano).
Il campo legacy `ruolo_sistema` e' **rifiutato** con `E_AMM_VALIDAZIONE`. Il
service traduce internamente `is_super_admin` -> `ruolo_sistema` legacy per
la fn DB `fn_crea_operatore` (compat layer interno mentre il refactor write-path
DB e' in transizione).

**Payload JSON:**

| Campo | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `cognome` | string | si* | Cognome operatore (*solo se `soggetto_id` non valorizzato) |
| `nome` | string | si* | Nome operatore (*solo se `soggetto_id` non valorizzato) |
| `codice_fiscale` | string | si* | Codice fiscale italiano (*solo se `soggetto_id` non valorizzato) |
| `username` | string | si | Username per login |
| `email` | string | si | Email operatore |
| `password` | string | si | Password in chiaro (viene hashata lato backend) |
| `qualifica_id` | int | si | ID qualifica (da lookup) |
| `is_super_admin` | bool | no | `true` per binding profilo SUPER_ADMIN, default `false` |
| `soggetto_id` | UUID | no | Se valorizzato: associa soggetto esistente (flusso B). Se assente: crea soggetto PF nuovo (flusso A) |
| `unita_organizzativa_id` | int | no | ID unita' organizzativa di appartenenza |
| `data_nascita` | string | no | Data nascita (formato `YYYY-MM-DD`) |
| `sesso` | string | no | `M` o `F` (default `M`) |
| `valido_dal` | string | no | Data inizio validita' (default data corrente) |
| `valido_al` | string | no | Data fine validita' |
| `comune_nascita_id` | int | no | ID comune di nascita |
| `indirizzo_resid_dettaglio_id` | int | no | ID dettaglio indirizzo residenza |
| `indirizzo_domfisc_dettaglio_id` | int | no | ID dettaglio indirizzo domicilio fiscale |

**Note sul contract**:

- **Niente `ruolo_sistema`**: il payload con la chiave legacy viene rifiutato
  prima di chiamare il repo. La promotion ad ADMIN passa da `is_super_admin: true`.
- **Niente `attivo` su POST**: l'operatore e' sempre creato attivo. La
  disabilitazione passa dal comando dedicato `/disabilita/` (vedi §1.5).
- **Niente `ruolo_applicativo`**: per il drawer admin-software e' implicitamente
  `OPERATORE`. Le vesti `CLIENTE_PORTALE`, `FORNITORE_PORTALE`, `SHOP_CUSTOMER`
  nascono da flussi di invito dedicati (vedi `api_invito_portale_shop.md`).

**Risposta:** dettaglio utente creato (stesso formato di GET dettaglio §1.3).

**Esempio curl:**

```bash
curl -X POST -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "cognome": "Rossi",
    "nome": "Mario",
    "codice_fiscale": "RSSMRA85M01H501Z",
    "username": "mrossi",
    "email": "m.rossi@example.com",
    "password": "SecurePass123!",
    "qualifica_id": 1,
    "is_super_admin": false,
    "unita_organizzativa_id": 2
  }' \
  "https://host/api/v1/amm-software/operatori/"
```

---

### 1.3 GET /api/v1/amm-software/operatori/{id}/ -- Dettaglio utente

Restituisce il dettaglio completo di un utente, inclusi conteggi override
permessi, emittenti associati, **stato multi-face** (Fase 1) e **6 campi
capability** data-driven per le azioni del drawer.

Il dettaglio e' generato da `script.fn_get_operatore_detail(p_auth_user_id)`
(single source of truth lato DB, idioma lookup-by-id: 0 righe per id non valido).

**Parametri path:** `id` (int) -- auth_user_id dell'utente.

**Risposta:**

```json
{
  "data": {
    "auth_user_id": 1,
    "username": "mtitini",
    "email": "m.titini@example.com",
    "first_name": "Michele",
    "last_name": "Titini",
    "soggetto_cognome": "Titini",
    "soggetto_nome": "Michele",
    "soggetto_id": "8a1f...uuid",
    "ragione_sociale_completa": "Titini Michele",
    "codice_fiscale": "TTNMHL75A01H501Z",
    "ruolo_sistema": "ADMIN",
    "is_super_admin": true,
    "ruolo_applicativo": "OPERATORE",
    "is_active": true,
    "attivo": true,
    "unita_organizzativa_id": 2,
    "unita_organizzativa_nome": "Sviluppo",
    "risorsa_umana_id": 5,
    "valido_dal": "2026-01-15",
    "valido_al": null,
    "last_login": "2026-04-29T08:30:00+00:00",
    "invito_inviato_at": "2026-01-15T09:15:00+00:00",
    "deve_cambiare_password": false,
    "override_aree_count": 3,
    "override_azioni_count": 1,
    "emittenti_count": 2,
    "emittenti_descrizione": "Azienda SRL, Sede Roma",
    "can_invite": false,
    "invite_reason": "Operatore gia' attivato (last_login valorizzato).",
    "can_disable": false,
    "disable_reason": "E' l'unico super admin attivo del sistema.",
    "can_demote_super_admin": false,
    "demote_reason": "E' l'unico super admin attivo del sistema."
  },
  "meta": { "request_id": "..." }
}
```

**Campi multi-face (Fase 1):**

| Campo | Tipo | Descrizione |
|---|---|---|
| `is_super_admin` | bool | `true` se l'identita ha binding `SUPER_ADMIN` attivo (`config.profili_accesso_bindings`, profilo seed id 9100) |
| `ruolo_applicativo` | string | `OPERATORE` / `CLIENTE_PORTALE` / `FORNITORE_PORTALE` / `SHOP_CUSTOMER` / `API_CLIENT` / `DISABILITATO` |
| `last_login` | timestamptz \| null | Ultimo login (`auth_user.last_login`); NULL se mai loggato |
| `invito_inviato_at` | timestamptz \| null | Quando e' stato spedito l'ultimo invito (`identita_digitali.invito_inviato_at`) |
| `deve_cambiare_password` | bool | Force-reset password al prossimo login |
| `emittenti_descrizione` | string \| null | Lista descrizioni emittenti scope, concatenate con virgola+spazio |

**Capability data-driven (Fase 1):**

| Campo | Tipo | Descrizione |
|---|---|---|
| `can_invite` | bool | True se l'operatore e' invitabile (mai loggato, attivo, email valida). Delega a `script.fn_check_operatore_invitabile` |
| `invite_reason` | string \| null | Motivo it-IT free-form quando `can_invite=false`; NULL altrimenti |
| `can_disable` | bool | False se e' l'unico super admin attivo. Preview di `script.fn_check_ultimo_super_admin_attivo`; **non e' una garanzia** (race tra sessioni: il trigger DB resta l'autorita') |
| `disable_reason` | string \| null | Motivo quando `can_disable=false` |
| `can_demote_super_admin` | bool \| null | Stesso check di `can_disable` ma per la rimozione del binding SUPER_ADMIN. **NULL** se l'operatore non e' SUPER_ADMIN (azione non applicabile -> il FE nasconde l'azione) |
| `demote_reason` | string \| null | Motivo quando `can_demote_super_admin=false` |

> **Nota sui reason it-IT free-form**: i campi `*_reason` sono stringhe
> visualizzabili direttamente come tooltip dal FE. Coerente col pattern
> esistente di `fn_check_operatore_invitabile`. Eventuale futura migrazione
> a codici stabili (es. `E_LAST_SUPER_ADMIN_DISABLE`) richiederebbe un
> passaggio coordinato BE+DB+FE.

**Esempio curl:**

```bash
curl -H "Authorization: Bearer <token>" \
  "https://host/api/v1/amm-software/operatori/1/"
```

---

### 1.4 PATCH /api/v1/amm-software/operatori/{id}/ -- Aggiorna utente

Aggiorna i campi modificabili di un utente. Solo i campi presenti nel payload vengono modificati.
Dopo la modifica, la cache permessi dell'utente viene invalidata.

**Contract Fase 1 multi-face**: il payload accetta `is_super_admin` + `attivo`.
Il campo legacy `ruolo_sistema` e' **rifiutato** con `E_AMM_VALIDAZIONE`. Il
service traduce internamente la coppia in `ruolo_sistema` legacy per il repo
(compat layer interno) secondo la regola:

- `attivo=False` → `DISABILITATO` (a prescindere da `is_super_admin`)
- `attivo=True, is_super_admin=True` → `ADMIN`
- `attivo=True, is_super_admin=False` → `OPERATIVO`
- payload senza `is_super_admin` ne' `attivo` → NO-OP sul ruolo (solo altri campi)

**Parametri path:** `id` (int) -- auth_user_id dell'utente.

**Payload JSON (tutti opzionali):**

| Campo | Tipo | Descrizione |
|---|---|---|
| `email` | string | Nuovo indirizzo email |
| `first_name` | string | Nuovo nome (auth_user) |
| `last_name` | string | Nuovo cognome (auth_user) |
| `is_super_admin` | bool | `true` per binding profilo SUPER_ADMIN, `false` per rimuoverlo |
| `attivo` | bool | Stato attivo identita digitale + risorsa umana |
| `unita_organizzativa_id` | int | Nuova unita' organizzativa |
| `valido_al` | string | Data fine validita' (formato `YYYY-MM-DD`) |

**Regole:**

- Il payload con `ruolo_sistema` viene rifiutato con `E_AMM_VALIDAZIONE` (HTTP 400).
- Se la modifica equivale alla rimozione dell'**ultimo super admin attivo**,
  il trigger DB `trgfn_profili_accesso_bindings_guard_ultimo_super_admin`
  blocca con `E_PROFILO_ULTIMO_SUPER_ADMIN` (HTTP 409) — vedi sezione "Errori".
- Se `is_super_admin` o `attivo` vengono modificati, viene chiamata
  `anagrafiche.fn_sync_auth_user_is_active` per sincronizzare `auth_user.is_active`
- La cache permessi dell'utente viene invalidata dopo ogni modifica

**Risposta:** dettaglio utente aggiornato (stesso formato di GET §1.3).

**Esempio curl:**

```bash
curl -X PATCH -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"is_super_admin": true, "attivo": true, "unita_organizzativa_id": 3}' \
  "https://host/api/v1/amm-software/operatori/1/"
```

---

### 1.5 POST /api/v1/amm-software/operatori/{id}/disabilita/ -- Disabilita utente

Disabilita un utente: identita digitale `attivo=false`, `ruolo_applicativo='DISABILITATO'`,
risorsa umana `attivo=false`+`valido_al=oggi`. Sincronizza `auth_user.is_active`,
invalida la cache permessi e inserisce tutti i token JWT dell'utente nella
blacklist (SimpleJWT), impedendo ulteriori accessi.

**Parametri path:** `id` (int) -- auth_user_id dell'utente.

**Payload:** nessuno.

**Guard "ultimo super admin"**: il preview lato Python legge `can_disable`
dal detail (Fase 1) ed evita il round-trip se l'utente e' l'unico SA attivo
(short-circuit con `E_PROFILO_ULTIMO_SUPER_ADMIN`). In caso di race tra
sessioni, il trigger DB `trgfn_profili_accesso_bindings_guard_ultimo_super_admin`
e' l'autorita' finale: il service traduce il `DatabaseError` in
`ServiceError(E_PROFILO_ULTIMO_SUPER_ADMIN)` preservando il code per
l'envelope errore (HTTP 409).

**Regole:**

- Ordine disattivazione: figlio (`identita_digitali`) prima del padre
  (`risorse_umane`) per rispettare il framework ATTIVO del DB.
- Chiama `anagrafiche.fn_sync_auth_user_is_active` per sincronizzare
  `auth_user.is_active`.
- Invalida la cache permessi dell'utente.
- Blacklist di tutti i token JWT outstanding (best-effort).

**Risposta:** dettaglio utente aggiornato (con `is_active=false`,
`attivo=false`, `ruolo_applicativo="DISABILITATO"`).

**Esempio curl:**

```bash
curl -X POST -H "Authorization: Bearer <token>" \
  "https://host/api/v1/amm-software/operatori/1/disabilita/"
```

---

### 1.6 POST /api/v1/amm-software/operatori/{id}/riattiva/ -- Riattiva utente

Riattiva un utente precedentemente disabilitato. Ordine inverso rispetto
a `/disabilita/`: padre (`risorse_umane`) prima del figlio
(`identita_digitali`) per rispettare il framework ATTIVO (un figlio attivo
richiede padre attivo).

**Parametri path:** `id` (int) -- auth_user_id dell'utente.

**Payload:** nessuno.

**Regole:**

- `risorse_umane`: `attivo=true`, `valido_dal=oggi`, `valido_al=NULL`.
- `identita_digitali`: `attivo=true`, `ruolo_applicativo='OPERATORE'`.
- Sync `auth_user.is_active`.
- Invalida la cache permessi dell'utente.
- **Non riattiva il binding SUPER_ADMIN**: se l'utente era stato
  precedentemente promosso e poi disabilitato, l'eventuale binding va
  ri-impostato via PATCH `is_super_admin: true` (azione esplicita).

**Risposta:** dettaglio utente aggiornato (con `is_active=true`,
`attivo=true`, `ruolo_applicativo="OPERATORE"`).

**Esempio curl:**

```bash
curl -X POST -H "Authorization: Bearer <token>" \
  "https://host/api/v1/amm-software/operatori/1/riattiva/"
```

---

## 2. Permessi utente

### 2.1 GET /api/v1/amm-software/operatori/{id}/override-aree/ -- Lista override aree

Restituisce gli override del livello di accesso alle aree funzionali per un utente.
Gli override permettono di aumentare o ridurre il livello di accesso rispetto al
profilo del reparto di appartenenza.

**Parametri path:** `id` (int) -- auth_user_id dell'utente.

**Risposta:**

```json
{
  "data": {
    "results": [
      {
        "id": 10,
        "area_id": 3,
        "area_codice": "VENDITE",
        "area_descrizione": "Gestione vendite",
        "livello": "COMPLETO",
        "motivo": "Responsabile vendite",
        "valido_dal": "2026-01-01",
        "valido_al": null
      }
    ]
  },
  "meta": { "request_id": "..." }
}
```

**Esempio curl:**

```bash
curl -H "Authorization: Bearer <token>" \
  "https://host/api/v1/amm-software/operatori/1/override-aree/"
```

---

### 2.2 PUT /api/v1/amm-software/operatori/{id}/override-aree/ -- Salva override aree

Sostituisce completamente gli override aree di un utente (semantica replace: cancella
tutti gli esistenti e inserisce i nuovi). Invalida la cache permessi.

**Parametri path:** `id` (int) -- auth_user_id dell'utente.

**Payload JSON:**

```json
{
  "items": [
    {
      "area_id": 3,
      "livello": "COMPLETO",
      "motivo": "Responsabile vendite",
      "valido_dal": "2026-01-01",
      "valido_al": null
    }
  ]
}
```

| Campo item | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `area_id` | int | si | ID area funzionale |
| `livello` | string | si | Livello accesso (tipo enum `config.livello_accesso`) |
| `motivo` | string | no | Motivazione dell'override |
| `valido_dal` | string | no | Data inizio validita' |
| `valido_al` | string | no | Data fine validita' |

**Risposta:** lista aggiornata degli override aree (stesso formato del GET).

**Esempio curl:**

```bash
curl -X PUT -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"items": [{"area_id": 3, "livello": "COMPLETO", "motivo": "Promozione"}]}' \
  "https://host/api/v1/amm-software/operatori/1/override-aree/"
```

---

### 2.3 GET /api/v1/amm-software/operatori/{id}/override-azioni/ -- Lista override azioni

Restituisce gli override sulle singole azioni di processo per un utente.
Permette di abilitare o disabilitare specifiche azioni indipendentemente dal
profilo del reparto.

**Parametri path:** `id` (int) -- auth_user_id dell'utente.

**Risposta:**

```json
{
  "data": {
    "results": [
      {
        "id": 5,
        "azione_id": 12,
        "permission_codename": "fattura.emetti",
        "azione_descrizione": "Emetti fattura",
        "area_codice": "VENDITE",
        "abilitata": true,
        "motivo": "Delega temporanea",
        "valido_dal": "2026-03-01",
        "valido_al": "2026-06-30"
      }
    ]
  },
  "meta": { "request_id": "..." }
}
```

**Esempio curl:**

```bash
curl -H "Authorization: Bearer <token>" \
  "https://host/api/v1/amm-software/operatori/1/override-azioni/"
```

---

### 2.4 PUT /api/v1/amm-software/operatori/{id}/override-azioni/ -- Salva override azioni

Sostituisce completamente gli override azioni di un utente (semantica replace).
Invalida la cache permessi.

**Parametri path:** `id` (int) -- auth_user_id dell'utente.

**Payload JSON:**

```json
{
  "items": [
    {
      "azione_id": 12,
      "abilitata": true,
      "motivo": "Delega temporanea",
      "valido_dal": "2026-03-01",
      "valido_al": "2026-06-30"
    }
  ]
}
```

| Campo item | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `azione_id` | int | si | ID azione processo |
| `abilitata` | bool | si | `true` per abilitare, `false` per disabilitare |
| `motivo` | string | no | Motivazione dell'override |
| `valido_dal` | string | no | Data inizio validita' |
| `valido_al` | string | no | Data fine validita' |

**Risposta:** lista aggiornata degli override azioni (stesso formato del GET).

**Esempio curl:**

```bash
curl -X PUT -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"items": [{"azione_id": 12, "abilitata": true, "motivo": "Delega"}]}' \
  "https://host/api/v1/amm-software/operatori/1/override-azioni/"
```

---

### 2.5 GET /api/v1/amm-software/operatori/{id}/emittenti-scope/ -- Scope emittenti dichiarativo

**Contract Fase 2 multi-face**. Restituisce lo scope emittenti dichiarativo
dell'utente con capability data-driven. Sostituisce il vecchio shape "lista
grezza" che lasciava al FE l'interpretazione (vuoto = tutti, 1+ = whitelist).

Sorgente: `script.fn_get_user_emittenti_scope(p_auth_user_id)`. Single-row.

**Parametri path:** `id` (int) -- auth_user_id dell'utente.

**Risposta:**

```json
{
  "data": {
    "scope_mode": "SINGLE",
    "emittenti_ids": [42],
    "emittente_descrizione": "Sede Roma",
    "allowed_scope_modes": ["GLOBAL", "SINGLE"],
    "can_change_scope": true,
    "change_scope_reason": null
  },
  "meta": { "request_id": "..." }
}
```

**Campi risposta:**

| Campo | Tipo | Descrizione |
|---|---|---|
| `scope_mode` | enum | `GLOBAL` (vede tutti gli emittenti) o `SINGLE` (vede solo `emittenti_ids[0]`). `MULTI` chiuso architetturalmente post Q2 (`UNIQUE(auth_user_id)` su `config.user_emittenti_fiscali`) |
| `emittenti_ids` | array[int] | `[]` se GLOBAL, `[id]` se SINGLE. Array per simmetria payload (preparazione futura) |
| `emittente_descrizione` | string \| null | Descrizione emittente quando SINGLE; NULL se GLOBAL |
| `allowed_scope_modes` | array[string] | Sempre `["GLOBAL", "SINGLE"]` post Q2. Il FE mostra solo i radio ammessi |
| `can_change_scope` | bool | False sse l'operatore e' SUPER_ADMIN e l'unico attivo (delega a `fn_check_ultimo_super_admin_attivo`). Preview UX, non garanzia |
| `change_scope_reason` | string \| null | Motivo it-IT free-form quando `can_change_scope=false` |

**Esempio curl:**

```bash
curl -H "Authorization: Bearer <token>" \
  "https://host/api/v1/amm-software/operatori/1/emittenti-scope/"
```

---

### 2.6 PUT /api/v1/amm-software/operatori/{id}/emittenti-scope/ -- Cambia scope

**Contract Fase 2 multi-face**. Cambio scope atomico via
`script.fn_change_user_emittenti_scope`. Sostituisce il vecchio payload
`{emittente_ids: [...]}` con shape dichiarativo `{scope_mode, emittenti_ids}`.

**Parametri path:** `id` (int) -- auth_user_id dell'utente.

**Payload JSON:**

```json
{
  "scope_mode": "SINGLE",
  "emittenti_ids": [42]
}
```

| Campo | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `scope_mode` | enum | si | `GLOBAL` o `SINGLE`. Altri valori (incluso `MULTI`) -> `E_AMM_SCOPE_NON_AMMESSO` (HTTP 400) |
| `emittenti_ids` | array[int] | dipende | Vuoto/omesso se GLOBAL. Esattamente 1 elemento int>0 se SINGLE. Lista con 0 o ≥2 elementi su SINGLE -> `E_AMM_SCOPE_NON_AMMESSO` |

**Regole:**

- `GLOBAL`: `emittenti_ids` viene ignorato e normalizzato a `[]` lato service.
- `SINGLE`: `emittenti_ids` deve contenere esattamente 1 int positivo.
- **Guard ultimo super admin**: integrato nella fn DB
  `fn_change_user_emittenti_scope`. Se l'operatore e' SUPER_ADMIN globale e
  l'unico attivo, il cambio scope -> SINGLE viene rifiutato con
  `E_PROFILO_ULTIMO_SUPER_ADMIN` (HTTP 409). Il preview `can_change_scope`
  lato detail e' fast-path UX, non garanzia (race tra sessioni).
- Invalida la cache permessi dell'utente.

**Risposta:** stesso shape del GET §2.5 con i valori post-change (rilettura
da `fn_get_user_emittenti_scope` per consistenza).

**Esempio curl — cambio a GLOBAL:**

```bash
curl -X PUT -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"scope_mode": "GLOBAL"}' \
  "https://host/api/v1/amm-software/operatori/1/emittenti-scope/"
```

**Esempio curl — cambio a SINGLE su emittente 42:**

```bash
curl -X PUT -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"scope_mode": "SINGLE", "emittenti_ids": [42]}' \
  "https://host/api/v1/amm-software/operatori/1/emittenti-scope/"
```

---

## 3. Reparti

### 3.1 GET /api/v1/amm-software/reparti/ -- Lista reparti

Restituisce la lista delle unita' organizzative attive con conteggi di configurazione.

**Parametri:** nessuno.

**Risposta:**

```json
{
  "data": {
    "results": [
      {
        "id": 2,
        "codice": "DEV",
        "descrizione": "Sviluppo",
        "attivo": true,
        "profilo_aree_count": 5,
        "profilo_azioni_count": 12,
        "operatori_count": 8
      }
    ]
  },
  "meta": { "request_id": "..." }
}
```

**Esempio curl:**

```bash
curl -H "Authorization: Bearer <token>" \
  "https://host/api/v1/amm-software/reparti/"
```

---

### 3.2 GET /api/v1/amm-software/reparti/{uo_id}/profilo/ -- Profilo reparto

Restituisce il profilo permessi completo di un reparto: aree funzionali con livello
di accesso e azioni processo con stato abilitazione.

**Parametri path:** `uo_id` (int) -- ID unita' organizzativa.

**Risposta:**

```json
{
  "data": {
    "aree": [
      {
        "id": 1,
        "area_id": 3,
        "area_codice": "VENDITE",
        "area_descrizione": "Gestione vendite",
        "livello": "COMPLETO"
      }
    ],
    "azioni": [
      {
        "id": 1,
        "azione_id": 12,
        "permission_codename": "fattura.emetti",
        "azione_descrizione": "Emetti fattura",
        "area_codice": "VENDITE",
        "abilitata": true
      }
    ]
  },
  "meta": { "request_id": "..." }
}
```

**Esempio curl:**

```bash
curl -H "Authorization: Bearer <token>" \
  "https://host/api/v1/amm-software/reparti/2/profilo/"
```

---

### 3.3 PUT /api/v1/amm-software/reparti/{uo_id}/profilo/ -- Salva profilo reparto

Sostituisce completamente il profilo permessi di un reparto (aree + azioni, semantica
replace). Invalida la cache permessi di **tutti gli operatori** del reparto.

**Parametri path:** `uo_id` (int) -- ID unita' organizzativa.

**Payload JSON:**

```json
{
  "aree": [
    { "area_id": 3, "livello": "COMPLETO" },
    { "area_id": 5, "livello": "LETTURA" }
  ],
  "azioni": [
    { "azione_id": 12, "abilitata": true },
    { "azione_id": 15, "abilitata": false }
  ]
}
```

| Campo aree | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `area_id` | int | si | ID area funzionale |
| `livello` | string | si | Livello accesso (tipo enum `config.livello_accesso`) |

| Campo azioni | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `azione_id` | int | si | ID azione processo |
| `abilitata` | bool | si | `true` per abilitare, `false` per disabilitare |

**Regole:**

- La modifica impatta tutti gli operatori che appartengono al reparto
- La cache permessi viene invalidata per l'intero reparto (`invalidate_department`)

**Risposta:** profilo reparto aggiornato (stesso formato del GET).

**Esempio curl:**

```bash
curl -X PUT -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "aree": [{"area_id": 3, "livello": "COMPLETO"}],
    "azioni": [{"azione_id": 12, "abilitata": true}]
  }' \
  "https://host/api/v1/amm-software/reparti/2/profilo/"
```

---

## 4. Lookup

Endpoint di supporto per popolare dropdown e selettori nell'interfaccia di amministrazione.

### 4.1 GET /api/v1/amm-software/lookup/unita-organizzative/

Lista di tutte le unita' organizzative (anche inattive) per filtri e dropdown.

```json
{
  "data": {
    "results": [
      { "id": 2, "descrizione": "Sviluppo", "parent_id": 1 }
    ]
  }
}
```

**Esempio curl:**

```bash
curl -H "Authorization: Bearer <token>" \
  "https://host/api/v1/amm-software/lookup/unita-organizzative/"
```

---

### 4.2 GET /api/v1/amm-software/lookup/aree-funzionali/

Lista delle aree funzionali attive, ordinate per ordinamento e codice.

```json
{
  "data": {
    "results": [
      { "id": 3, "codice": "VENDITE", "descrizione": "Gestione vendite", "ordinamento": 10 }
    ]
  }
}
```

**Esempio curl:**

```bash
curl -H "Authorization: Bearer <token>" \
  "https://host/api/v1/amm-software/lookup/aree-funzionali/"
```

---

### 4.3 GET /api/v1/amm-software/lookup/azioni-processo/

Lista delle azioni processo attive con area di appartenenza.

```json
{
  "data": {
    "results": [
      {
        "id": 12,
        "permission_codename": "fattura.emetti",
        "descrizione": "Emetti fattura",
        "pericolosa": false,
        "area_id": 3,
        "area_codice": "VENDITE"
      }
    ]
  }
}
```

**Esempio curl:**

```bash
curl -H "Authorization: Bearer <token>" \
  "https://host/api/v1/amm-software/lookup/azioni-processo/"
```

---

### 4.4 GET /api/v1/amm-software/lookup/emittenti-fiscali/

Lista degli emittenti fiscali attivi per la configurazione scope utente.

```json
{
  "data": {
    "results": [
      { "id": 10, "codice": "EMT001", "descrizione": "Azienda SRL" }
    ]
  }
}
```

**Esempio curl:**

```bash
curl -H "Authorization: Bearer <token>" \
  "https://host/api/v1/amm-software/lookup/emittenti-fiscali/"
```

### 4.5 GET /api/v1/amm-software/lookup/rounding-modes/ -- (Fase 3)

Lookup statico dei modi di arrotondamento ammessi per `anagrafiche.emittenti_fiscali.rounding_policy`. Allineati al CHECK constraint `chk_emittenti_fiscali_rounding_policy`: 4 codici fissi (UP, DOWN, HALF_UP, HALF_DOWN). **Niente HALF_EVEN** (a differenza del lookup catalogo `/catalogo/lookup/rounding-modes/` che ne ha 5: UoM operativa ammette anche banker's rounding).

Single source of truth lato Python: `apps/amm_software/services/amm_software_service.py::_ROUNDING_MODE_VALIDI_EMITTENTE` + `_ROUNDING_MODE_DESCRIZIONI_EMITTENTE`. Nessuna tabella DB.

**Response shape**: `data` e' lista nuda (non envelope `{count, results}`).

```json
{
  "data": [
    { "codice": "HALF_UP",   "descrizione": "Arrotondamento meta' su (5 va su)",       "ordering": 1 },
    { "codice": "HALF_DOWN", "descrizione": "Arrotondamento meta' giu' (5 va giu')",  "ordering": 2 },
    { "codice": "UP",        "descrizione": "Arrotondamento sempre su (verso infinito)", "ordering": 3 },
    { "codice": "DOWN",      "descrizione": "Arrotondamento sempre giu' (verso zero)",  "ordering": 4 }
  ]
}
```

**Consumer FE**: `frontend/src/amministrazione/components/EmittenteRoundingModeSelect.vue` (wrapper riusabile cached con `useGlobalLookup('amm.emittenti_rounding_modes')`). Usato da `EmittenteFiscaleDrawer.vue` (campo `rounding_policy` testata) e `EmittenteFiscaleUtilitiesTab.vue` (campo `metodo_arrotondamento_importi` per riga utility).

**Esempio curl:**

```bash
curl -H "Authorization: Bearer <token>" \
  "https://host/api/v1/amm-software/lookup/rounding-modes/"
```

---

## 5. Form-defaults emittente fiscale (Fase 3)

### 5.1 GET /api/v1/amm-software/emittenti-fiscali/form-defaults/

Defaults pre-compilazione del form di creazione anagrafica emittente fiscale. Centralizza il consumo di `config.parameters` (`EMITTENTE_DEFAULT_BOLLO_AUTO`, `EMITTENTE_DEFAULT_BOLLO_SOGLIA`, `EMITTENTE_DEFAULT_ROUNDING_POLICY`) con cast tipi gia' applicato lato BE: il FE non duplica il cast generico di `/core/parameters/defaults/`. Pattern allineato a `ApiArticoliFormDefaults` (catalogo Fase 8 -- A5).

**Cascata**: user -> group -> emittente -> default via `script.fn_get_parameter_full`. In creazione `emittente_fiscale_id` e' `None` (cascata effettiva user->group->default).

**Cast applicati**:

| Campo response | Codice parameter | Cast | Convenzione |
|---|---|---|---|
| `defaults.bollo_auto` | `EMITTENTE_DEFAULT_BOLLO_AUTO` | `bool` | `'true'`/`'false'` case-insensitive; altro -> `false` (default-safe) |
| `defaults.bollo_soglia` | `EMITTENTE_DEFAULT_BOLLO_SOGLIA` | `Decimal` o `null` | Stringa vuota = nessuna soglia -> `null`; non parsabile -> `null` (best-effort) |
| `defaults.rounding_policy` | `EMITTENTE_DEFAULT_ROUNDING_POLICY` | `str` o `null` | Validato vs `_ROUNDING_MODE_VALIDI_EMITTENTE` (4 valori, no HALF_EVEN); fuori enum -> `null` |

**Note**:

- Il campo `attivo` **non** passa per `parameters`: la colonna `anagrafiche.emittenti_fiscali.attivo` ha gia' `DEFAULT true`. Il FE non lo include nei defaults.
- `non_editable_fields` ritornato statico oggi (`['codice', 'soggetto_id']`). In attesa che `dbops.vw_non_editable_fields` (Fase 5) includa anche le tabelle anagrafiche, il FE legge gia' la chiave per non avere breaking change quando la fonte diventera' DB-driven.
- Best-effort sui cast: parameters mancanti, malformati o fuori enum non sollevano errore. Il form mostra comunque, l'utente compila/seleziona manualmente.

**Response:**

```json
{
  "data": {
    "defaults": {
      "bollo_auto": false,
      "bollo_soglia": null,
      "rounding_policy": "HALF_UP"
    },
    "non_editable_fields": ["codice", "soggetto_id"]
  }
}
```

**Esempio curl:**

```bash
curl -H "Authorization: Bearer <token>" \
  "https://host/api/v1/amm-software/emittenti-fiscali/form-defaults/"
```

---

## Regole trasversali

- **Autenticazione**: tutti gli endpoint richiedono JWT Bearer token con ruolo `ADMIN`
- **Cache permessi**: ogni PUT su permessi (override aree, override azioni, emittenti scope, profilo reparto) invalida la cache permessi dell'utente o del reparto interessato
- **Semantica replace**: le PUT su permessi cancellano tutti i record esistenti e inseriscono i nuovi (non e' un merge/patch)
- **Ordinamento lista utenti**: whitelist di colonne ammesse (`last_name`, `username`, `ruolo_sistema`, `is_active`, `unita_organizzativa_nome`, `data_insert`); colonne non valide vengono ignorate
- **Throttling**: l'endpoint lista utenti ha throttling search attivo

## Errori

| Codice | HTTP | Quando |
|---|---|---|
| `E_AMM_VALIDAZIONE` | 400 | Campi obbligatori mancanti, `ruolo_sistema` legacy nel payload (Fase 1), validazioni domain |
| `E_AMM_OPERATORE_NOT_FOUND` | 404 | Operatore non trovato (dettaglio, aggiorna, disabilita, riattiva, scope) |
| `E_AMM_SCOPE_NON_AMMESSO` | 400 | (Fase 2) `scope_mode` non in `['GLOBAL','SINGLE']`, oppure `SINGLE` con array vuoto/multi-elemento |
| `E_PROFILO_ULTIMO_SUPER_ADMIN` | 409 | (Fase 1) L'operazione (disabilita, demote, cambio scope) lascerebbe il sistema senza super admin attivi. Trigger DB `trgfn_profili_accesso_bindings_guard_ultimo_super_admin` |

## Dipendenze DB

| Funzione/Tabella | Schema | Ruolo |
|---|---|---|
| `fn_get_operatore_detail(INTEGER)` | `script` | **Fase 1**. Single source of truth per dettaglio operatore + capability (`can_invite/can_disable/can_demote_super_admin`). Idioma lookup-by-id (0 righe = id non valido) |
| `fn_check_operatore_invitabile(INTEGER)` | `script` | **Fase 1**. Calcola `can_invite/invite_reason` per il dettaglio |
| `fn_check_ultimo_super_admin_attivo(INTEGER)` | `script` | **Fase 1**. Check "e' l'unico SA attivo?" usato da `can_disable/can_demote` e da `can_change_scope` (Fase 2) |
| `fn_is_super_admin(INTEGER)` | `script` | Verifica binding profilo SUPER_ADMIN per l'utente. Gated su `app.ruolo_applicativo` GUC (post 2026-04-21): contesti non-OPERATORE ritornano false fail-closed |
| `fn_get_user_emittenti_scope(INTEGER)` | `script` | **Fase 2**. Single-row con `scope_mode/emittenti_ids/allowed_scope_modes/can_change_scope` |
| `fn_change_user_emittenti_scope(INTEGER, BIGINT[])` | `script` | **Fase 2**. Cambio scope atomico con guard `fn_check_ultimo_super_admin_attivo` integrato. Solleva `E_AMM_SCOPE_NON_AMMESSO` o `E_PROFILO_ULTIMO_SUPER_ADMIN` |
| `fn_get_parameter_full(...)` | `script` | **Fase 3**. Cascata risoluzione parameter user -> group -> emittente -> session -> default. Usata da `ParameterService.get_defaults` per il form-defaults emittente fiscale |
| Seed `config.parameters` `EMITTENTE_DEFAULT_*` | `config` | **Fase 3**. 3 chiavi: `BOLLO_AUTO=false`, `BOLLO_SOGLIA=''` (= NULL applicativo), `ROUNDING_POLICY=HALF_UP`. Tutti `text NOT NULL`, cast a Python a carico del BE (helpers `_cast_param_bool`/`_cast_param_decimal`) |
| `chk_emittenti_fiscali_rounding_policy` | `anagrafiche` | **Fase 3**. CHECK constraint sulla colonna `emittenti_fiscali.rounding_policy`: ammette **4 valori** (`UP`, `DOWN`, `HALF_UP`, `HALF_DOWN`). Niente `HALF_EVEN` (a differenza di catalogo UoM operativa). E' il riferimento per `_ROUNDING_MODE_VALIDI_EMITTENTE` lato Python |
| `fn_crea_operatore(...)` | `anagrafiche` | Orchestratore creazione operatore (auth_user + soggetto PF + risorsa umana) |
| `fn_sync_auth_user_is_active(INTEGER)` | `anagrafiche` | Sincronizza `auth_user.is_active` con stato identita digitale + risorsa umana |
| `trgfn_profili_accesso_bindings_guard_ultimo_super_admin` | `config` | Trigger DB autorita' finale per anti-lockout: blocca DELETE/UPDATE binding SUPER_ADMIN se ultimo attivo. Solleva con marker `E_PROFILO_ULTIMO_SUPER_ADMIN` |
| `auth_user` | Django | Tabella autenticazione utenti |
| `identita_digitali` | `anagrafiche` | **Fase 1 multi-face**. Bridge `soggetti_ruoli ↔ auth_user` con `ruolo_applicativo`, `attivo`, `invito_inviato_at`, `deve_cambiare_password`. Sostituisce il legacy `risorse_umane_auth_user` (kept per retrocompat lettura) |
| `profili_accesso_bindings` | `config` | Binding profili accesso (incluso SUPER_ADMIN id 9100) sull'identita digitale |
| `risorse_umane` | `anagrafiche` | Dati operatore (qualifica, UO, validita') |
| `risorse_umane_auth_user` | `anagrafiche` | DEPRECATO post-cutover §4.6.H.2: vista read-only su `identita_digitali`. Retrocompat lettura `ruolo_sistema` |
| `unita_organizzative` | `config` | Reparti / unita' organizzative |
| `user_override_aree` | `config` | Override livello accesso aree per utente |
| `user_override_azioni` | `config` | Override azioni processo per utente |
| `user_override_oggetti` | `config` | Override permessi v2 per singolo model (`app_label.model_name`) |
| `user_emittenti_fiscali` | `config` | Scope emittenti fiscali per utente. Post-Q2: `UNIQUE(auth_user_id)` (max 1 riga) |
| `aree_funzionali` | `config` | Catalogo aree funzionali |
| `azioni_processo` | `config` | Catalogo azioni processo |
| `area_model_overrides` | `config` | Catalogo (app_label, model_name) ammessi per override v2 |
| `profili_reparto_aree` | `config` | Profilo aree per reparto |
| `profili_reparto_azioni` | `config` | Profilo azioni per reparto |
| `emittenti_fiscali` | `anagrafiche` | Catalogo emittenti fiscali |

## File backend

| File | Ruolo |
|---|---|
| `apps/amm_software/api/views.py` | View API (AdminAPIView) -- 12 classi view (Fase 3: +`EmittentiFormDefaultsView`, +`EmittenteRoundingModesLookupView`) |
| `apps/amm_software/api/urls_v1.py` | Routing: 14 rotte sotto `/api/v1/amm-software/` |
| `apps/amm_software/services/amm_software_service.py` | Service layer -- validazione, orchestrazione, invalidazione cache. **Fase 3**: `_ROUNDING_MODE_VALIDI_EMITTENTE` + `_cast_param_bool` + `_cast_param_decimal` + `get_emittente_form_defaults` + `list_emittente_rounding_modes` |
| `apps/amm_software/db/amm_software_repository.py` | Repository -- accesso DB diretto (SQL raw) |
| `apps/amm_software/types.py` | TypedDict per righe utente |
| `apps/core/services/permissions_cache.py` | `invalidate_user()`, `invalidate_department()` |
| `apps/core/services/parameter_service.py` | `ParameterService.get_defaults` (cascata user->group->emittente->default via `fn_get_parameter_full`). Usato da Fase 3 form-defaults emittente |
| `apps/core/api/views_parameters.py` | `get_user_context(request, svc)` -- helper riusato dalle view form-defaults |
| `apps/amm_software/tests/api/test_operatori_views.py` | Test lista e dettaglio operatori |
| `apps/amm_software/tests/api/test_crea_operatore.py` | Test creazione operatore |
| `apps/amm_software/tests/api/test_override_permessi.py` | Test override aree/azioni/emittenti |
| `apps/amm_software/tests/api/test_profili_reparto.py` | Test profili reparto |
| `apps/amm_software/tests/api/test_emittenti_form_defaults_views.py` | **Fase 3**: smoke test API form-defaults + lookup rounding-modes |
| `apps/amm_software/tests/services/test_amm_software_service.py` | Test service layer (incluso Fase 3: cast helpers, form-defaults, rounding modes coverage) |
