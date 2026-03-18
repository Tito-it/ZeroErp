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
L'endpoint lista utenti ha throttling search attivo (`is_search_endpoint = True`).

Le risposte seguono l'envelope standard `{ "data": {...}, "meta": {...} }`.

Base URL: `/api/v1/amm-software/`

---

## 1. Utenti

### 1.1 GET /api/v1/amm-software/utenti/ -- Lista utenti

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
  "https://host/api/v1/amm-software/utenti/?search=titini&ruolo_sistema=ADMIN&limit=10"
```

---

### 1.2 POST /api/v1/amm-software/utenti/ -- Crea utente

Crea un nuovo operatore completo: utente Django, soggetto persona fisica, risorsa umana.
La creazione e' orchestrata dalla funzione DB `anagrafiche.fn_crea_operatore`.

**Payload JSON:**

| Campo | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `cognome` | string | si | Cognome operatore |
| `nome` | string | si | Nome operatore |
| `codice_fiscale` | string | si | Codice fiscale italiano |
| `username` | string | si | Username per login |
| `email` | string | si | Email operatore |
| `password` | string | si | Password in chiaro (viene hashata lato backend) |
| `qualifica_id` | int | si | ID qualifica (da lookup) |
| `ruolo_sistema` | string | no | `ADMIN` o `OPERATIVO` (default `OPERATIVO`) |
| `unita_organizzativa_id` | int | no | ID unita' organizzativa di appartenenza |
| `data_nascita` | string | no | Data nascita (formato `YYYY-MM-DD`) |
| `sesso` | string | no | `M` o `F` (default `M`) |
| `valido_dal` | string | no | Data inizio validita' (default data corrente) |
| `valido_al` | string | no | Data fine validita' |
| `comune_nascita_id` | int | no | ID comune di nascita |
| `indirizzo_resid_dettaglio_id` | int | no | ID dettaglio indirizzo residenza |
| `indirizzo_domfisc_dettaglio_id` | int | no | ID dettaglio indirizzo domicilio fiscale |

**Risposta:** dettaglio utente creato (stesso formato di GET dettaglio).

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
    "ruolo_sistema": "OPERATIVO",
    "unita_organizzativa_id": 2
  }' \
  "https://host/api/v1/amm-software/utenti/"
```

---

### 1.3 GET /api/v1/amm-software/utenti/{id}/ -- Dettaglio utente

Restituisce il dettaglio completo di un utente, inclusi i conteggi degli override
permessi e degli emittenti associati.

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
    "ruolo_sistema": "ADMIN",
    "is_active": true,
    "unita_organizzativa_id": 2,
    "unita_organizzativa_nome": "Sviluppo",
    "risorsa_umana_id": 5,
    "attivo": true,
    "valido_al": null,
    "data_insert": "2026-01-15 10:30:00+00",
    "override_aree_count": 3,
    "override_azioni_count": 1,
    "emittenti_count": 2
  },
  "meta": { "request_id": "..." }
}
```

**Esempio curl:**

```bash
curl -H "Authorization: Bearer <token>" \
  "https://host/api/v1/amm-software/utenti/1/"
```

---

### 1.4 PATCH /api/v1/amm-software/utenti/{id}/ -- Aggiorna utente

Aggiorna i campi modificabili di un utente. Solo i campi presenti nel payload vengono modificati.
Dopo la modifica, la cache permessi dell'utente viene invalidata.

**Parametri path:** `id` (int) -- auth_user_id dell'utente.

**Payload JSON (tutti opzionali):**

| Campo | Tipo | Descrizione |
|---|---|---|
| `email` | string | Nuovo indirizzo email |
| `first_name` | string | Nuovo nome (auth_user) |
| `last_name` | string | Nuovo cognome (auth_user) |
| `ruolo_sistema` | string | Nuovo ruolo: `ADMIN`, `OPERATIVO`, `DISABILITATO` |
| `unita_organizzativa_id` | int | Nuova unita' organizzativa |
| `attivo` | bool | Stato attivo risorsa umana |
| `valido_al` | string | Data fine validita' (formato `YYYY-MM-DD`) |

**Regole:**

- Se `ruolo_sistema` o `attivo` vengono modificati, viene chiamata `anagrafiche.fn_sync_auth_user_is_active` per sincronizzare `auth_user.is_active`
- La cache permessi dell'utente viene invalidata dopo ogni modifica

**Risposta:** dettaglio utente aggiornato.

**Esempio curl:**

```bash
curl -X PATCH -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"ruolo_sistema": "ADMIN", "unita_organizzativa_id": 3}' \
  "https://host/api/v1/amm-software/utenti/1/"
```

---

### 1.5 POST /api/v1/amm-software/utenti/{id}/disabilita/ -- Disabilita utente

Disabilita un utente impostando `ruolo_sistema = DISABILITATO` e `attivo = false`.
Sincronizza `auth_user.is_active`, invalida la cache permessi e inserisce tutti i
token JWT dell'utente nella blacklist (SimpleJWT), impedendo ulteriori accessi.

**Parametri path:** `id` (int) -- auth_user_id dell'utente.

**Payload:** nessuno.

**Regole:**

- Imposta `ruolo_sistema = DISABILITATO` su `risorse_umane_auth_user`
- Imposta `attivo = false` su `risorse_umane`
- Chiama `anagrafiche.fn_sync_auth_user_is_active` per sincronizzare `auth_user.is_active`
- Invalida la cache permessi dell'utente
- Blacklist di tutti i token JWT outstanding (best-effort)

**Risposta:** dettaglio utente aggiornato (con `is_active = false`).

**Esempio curl:**

```bash
curl -X POST -H "Authorization: Bearer <token>" \
  "https://host/api/v1/amm-software/utenti/1/disabilita/"
```

---

## 2. Permessi utente

### 2.1 GET /api/v1/amm-software/utenti/{id}/override-aree/ -- Lista override aree

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
  "https://host/api/v1/amm-software/utenti/1/override-aree/"
```

---

### 2.2 PUT /api/v1/amm-software/utenti/{id}/override-aree/ -- Salva override aree

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
  "https://host/api/v1/amm-software/utenti/1/override-aree/"
```

---

### 2.3 GET /api/v1/amm-software/utenti/{id}/override-azioni/ -- Lista override azioni

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
  "https://host/api/v1/amm-software/utenti/1/override-azioni/"
```

---

### 2.4 PUT /api/v1/amm-software/utenti/{id}/override-azioni/ -- Salva override azioni

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
  "https://host/api/v1/amm-software/utenti/1/override-azioni/"
```

---

### 2.5 GET /api/v1/amm-software/utenti/{id}/emittenti-scope/ -- Lista emittenti scope

Restituisce gli emittenti fiscali a cui l'utente ha accesso (whitelist).
Se la lista e' vuota, l'utente ha accesso all'unico emittente attivo (se presente).

**Parametri path:** `id` (int) -- auth_user_id dell'utente.

**Risposta:**

```json
{
  "data": {
    "results": [
      {
        "id": 1,
        "emittente_fiscale_id": 10,
        "emittente_codice": "EMT001",
        "emittente_descrizione": "Azienda SRL"
      }
    ]
  },
  "meta": { "request_id": "..." }
}
```

**Esempio curl:**

```bash
curl -H "Authorization: Bearer <token>" \
  "https://host/api/v1/amm-software/utenti/1/emittenti-scope/"
```

---

### 2.6 PUT /api/v1/amm-software/utenti/{id}/emittenti-scope/ -- Salva emittenti scope

Sostituisce completamente la whitelist emittenti di un utente (semantica replace).
Invalida la cache permessi.

**Parametri path:** `id` (int) -- auth_user_id dell'utente.

**Payload JSON:**

```json
{
  "emittente_ids": [10, 15]
}
```

| Campo | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `emittente_ids` | array[int] | si | Lista ID emittenti fiscali da associare |

**Risposta:** lista aggiornata degli emittenti scope (stesso formato del GET).

**Esempio curl:**

```bash
curl -X PUT -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"emittente_ids": [10, 15]}' \
  "https://host/api/v1/amm-software/utenti/1/emittenti-scope/"
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
| `E_AMM_VALIDAZIONE` | 400 | Campi obbligatori mancanti nella creazione utente |
| `E_AMM_UTENTE_NOT_FOUND` | 404 | Utente non trovato (dettaglio, aggiorna, disabilita) |

## Dipendenze DB

| Funzione/Tabella | Schema | Ruolo |
|---|---|---|
| `fn_crea_operatore(...)` | `anagrafiche` | Orchestratore creazione operatore (auth_user + soggetto PF + risorsa umana) |
| `fn_sync_auth_user_is_active(INTEGER)` | `anagrafiche` | Sincronizza `auth_user.is_active` con stato risorsa umana e ruolo |
| `auth_user` | Django | Tabella autenticazione utenti |
| `risorse_umane_auth_user` | `anagrafiche` | Ponte auth_user - risorsa umana (contiene `ruolo_sistema`) |
| `risorse_umane` | `anagrafiche` | Dati operatore (qualifica, UO, validita') |
| `unita_organizzative` | `config` | Reparti / unita' organizzative |
| `user_override_aree` | `config` | Override livello accesso aree per utente |
| `user_override_azioni` | `config` | Override azioni processo per utente |
| `user_emittenti_fiscali` | `config` | Whitelist emittenti fiscali per utente |
| `aree_funzionali` | `config` | Catalogo aree funzionali |
| `azioni_processo` | `config` | Catalogo azioni processo |
| `profili_reparto_aree` | `config` | Profilo aree per reparto |
| `profili_reparto_azioni` | `config` | Profilo azioni per reparto |
| `emittenti_fiscali` | `anagrafiche` | Catalogo emittenti fiscali |

## File backend

| File | Ruolo |
|---|---|
| `apps/amm_software/api/views.py` | View API (AdminAPIView) -- 10 classi view |
| `apps/amm_software/api/urls_v1.py` | Routing: 12 rotte sotto `/api/v1/amm-software/` |
| `apps/amm_software/services/amm_software_service.py` | Service layer -- validazione, orchestrazione, invalidazione cache |
| `apps/amm_software/db/amm_software_repository.py` | Repository -- accesso DB diretto (SQL raw) |
| `apps/amm_software/types.py` | TypedDict per righe utente |
| `apps/core/services/permissions_cache.py` | `invalidate_user()`, `invalidate_department()` |
| `apps/amm_software/tests/api/test_utenti_views.py` | Test lista e dettaglio utenti |
| `apps/amm_software/tests/api/test_crea_utente.py` | Test creazione operatore |
| `apps/amm_software/tests/api/test_override_permessi.py` | Test override aree/azioni/emittenti |
| `apps/amm_software/tests/api/test_profili_reparto.py` | Test profili reparto |
| `apps/amm_software/tests/services/test_amm_software_service.py` | Test service layer |
