# API Invito + Attivazione — Portale e Shop

## Scopo

Documenta i flussi end-to-end di **onboarding self-service** delle vesti
non-operatore (`CLIENTE_PORTALE`, `FORNITORE_PORTALE`, `SHOP_CUSTOMER`).
L'admin invia un invito email partendo dal cliente o fornitore
anagrafico; l'utente clicca il link e attiva la propria veste — il flow
distingue automaticamente:

- **INVITO** (email nuova): l'utente sceglie la password al primo accesso
- **CROSS** (email gia' nota come operatore o altra veste): one-click,
  password preesistente invariata

Esiste anche un endpoint **autenticato cross-veste** che consente a un
`CLIENTE_PORTALE` gia' loggato di aggiungersi la veste `SHOP_CUSTOMER`
sullo stesso `auth_user`, senza email/token.

## Contesto

| Building block | Note |
| --- | --- |
| `InvitoPortaleService` (gestisce tutte e 3 le vesti) | Mappa `_VESTE_CONFIG` per token tipi + template + link path + scadenza |
| `TokenService` | Token monouso tipo `INVITO_PORTALE` / `ATTIVAZIONE_PORTALE_CROSS` / `INVITO_SHOP` / `ATTIVAZIONE_SHOP_CROSS`, scadenza 72h |
| `EmailDispatchService` | Template `INVITO_PORTALE` (clienti/fornitori) e `INVITO_SHOP` (shop customer) |
| `apply_new_password` | Set password + reset flag `deve_cambiare_password` in transazione |
| `PortaleRepository.riattiva_identita` | UPDATE `attivo=true` su `identita_digitali` |
| `PermissionResolver.get_ruolo_applicativo` | Filtro veste corrente per `ProfileActivateShopView` |
| GUC `app.soggetto_ruolo_id` | Letto da `ProfileActivateShopView` per legare la nuova identita allo stesso `soggetto_ruolo` del portale corrente |

---

## Endpoint admin (invio invito)

### POST `/api/v1/anagrafiche/clienti/{cliente_id}/invita-portale/`

Invita il cliente come `CLIENTE_PORTALE`. Auth: JWT operatore con livello
area `anagrafiche` ≥ `LETTURA`.

**Body**:

```json
{
  "email": "destinatario@example.com",
  "reinvio": false
}
```

`reinvio=true`: invalida i token portale precedenti per quell'auth_user
prima di generare il nuovo invito.

**Response**:

```json
{
  "data": {
    "inviato": true,
    "email": "d***@example.com",
    "auth_user_id": 200,
    "identita_id": 500,
    "nuovo_utente": true,
    "is_cross": false
  }
}
```

`is_cross=true` quando l'email matcha un `auth_user` gia' esistente:
nessun nuovo `auth_user` creato, viene aggiunta una **2a identita**
`attivo=false` in attesa di attivazione cross.

---

### POST `/api/v1/anagrafiche/fornitori/{fornitore_id}/invita-portale/`

Simmetrico al precedente per `FORNITORE_PORTALE`.

---

### POST `/api/v1/anagrafiche/clienti/{cliente_id}/invita-shop/`

Invita il cliente come `SHOP_CUSTOMER` (B1 §13.7). Riusa lo stesso flow
del portale ma con tipi token `INVITO_SHOP` / `ATTIVAZIONE_SHOP_CROSS`,
template `INVITO_SHOP` e link `{FRONTEND_URL}/attivazione-shop/{token}`.

`SHOP_CUSTOMER` e `CLIENTE_PORTALE` condividono il ruolo anagrafico `CL`
del soggetto: la nuova identita vive sullo stesso `soggetto_ruolo` del
cliente, mai su uno nuovo.

I fornitori **non** hanno un endpoint `invita-shop/`: lo shop e' B2C
consumer per design, non di pertinenza dei fornitori.

---

### GET `/api/v1/anagrafiche/clienti/{cliente_id}/stato-accessi/`

Restituisce lo stato aggregato delle vesti non-operatore del cliente
(portale + shop). Usato dall'admin UI per decidere quale azione
proporre (invia / reinvia / disattiva). Auth: JWT operatore area
anagrafiche ≥ LETTURA.

**Response**:

```json
{
  "data": {
    "portale": {
      "stato": "ATTIVO",
      "identita_id": 500,
      "auth_user_id": 10,
      "invito_inviato_at": "2026-04-20T14:30:00Z",
      "token_scade_at": null
    },
    "shop": {
      "stato": "NESSUNO",
      "identita_id": null,
      "auth_user_id": null,
      "invito_inviato_at": null,
      "token_scade_at": null
    }
  }
}
```

`stato` ∈ `{NESSUNO, PENDING, ATTIVO, DISATTIVO}`:

| Stato | Significato |
| --- | --- |
| `NESSUNO` | identita non esiste (mai invitato) |
| `PENDING` | identita `attivo=false` + token non consumato non scaduto |
| `ATTIVO` | identita `attivo=true` |
| `DISATTIVO` | identita `attivo=false`, nessun token pending (revocata o invito scaduto) |

`token_scade_at` valorizzato solo per `PENDING` — usato dalla UI per
mostrare "scade tra N ore".

---

### GET `/api/v1/anagrafiche/fornitori/{fornitore_id}/stato-accessi/`

Simmetrico al precedente ma per fornitori: restituisce solo il blocco
`portale` (niente shop).

```json
{
  "data": {
    "portale": { "stato": "PENDING", "identita_id": 600, ... }
  }
}
```

---

### POST disattivazione veste (3 endpoint simmetrici)

- `POST /api/v1/anagrafiche/clienti/{cliente_id}/disattiva-portale/`
- `POST /api/v1/anagrafiche/clienti/{cliente_id}/disattiva-shop/`
- `POST /api/v1/anagrafiche/fornitori/{fornitore_id}/disattiva-portale/`

Soft-revoke veste non-operatore. Imposta `identita.attivo=false` e
invalida i token pendenti (invito + cross) dell'auth_user. **Idempotente**:
se la veste e' gia' disattiva o non esiste, la chiamata succede senza
errore (`disattivato=false`, stato ritornato coerente).

**Body**: nessuno (POST vuoto).

**Response**:

```json
{
  "data": {
    "disattivato": true,
    "stato": "DISATTIVO",
    "identita_id": 500
  }
}
```

- `disattivato: true` se ha effettivamente flippato `attivo` da `true` a `false`
- `disattivato: false` + `stato="DISATTIVO"` se era gia' disattiva (idempotente)
- `disattivato: false` + `stato="NESSUNO"` se la veste non esiste affatto

**Effetti collaterali**:

- Se c'era un invito pendente (`PENDING`), il link email smette di
  funzionare: chiunque clicca il link vede "Token non valido o scaduto".
- L'utente loggato al momento del revoke non viene disconnesso
  immediatamente (JWT valido fino a scadenza), ma al refresh o al
  prossimo `/me/` il guard namespace FE rifiuta il contesto portale/shop
  (identita non attiva).

**Riattivazione**: non c'e' un endpoint "riattiva" dedicato per evitare
ambiguita. Per rimettere in linea un accesso disattivato, l'admin
**rinvia un invito** (flow INVITO o CROSS a seconda dello stato
auth_user): il service riattiva automaticamente l'identita esistente se
compatibile (vedi `PortaleRepository.riattiva_identita`).

---

## Endpoint pubblici (attivazione)

I 4 endpoint seguenti **non richiedono JWT** (`AllowAny`,
`authentication_classes = []`). Sono throttled tramite
`PasswordResetRateThrottle`.

### Portale

#### GET `/api/v1/portale/attivazione/validate/{token}/`

Verifica un token di attivazione portale **senza consumarlo**. Il FE lo
usa per decidere quale UI mostrare (form password vs conferma one-click).

**Response (token valido)**:

```json
{
  "data": {
    "valid": true,
    "token_type": "INVITO_PORTALE",
    "requires_password": true
  }
}
```

`token_type` ∈ `{"INVITO_PORTALE", "ATTIVAZIONE_PORTALE_CROSS"}`.
`requires_password=true` solo per `INVITO_PORTALE` (email nuova).

**Response (token invalido/scaduto/usato)** — risposta generica per
evitare enumeration:

```json
{
  "data": {
    "valid": false,
    "message": "Token non valido, scaduto o gia' utilizzato."
  }
}
```

#### POST `/api/v1/portale/attivazione/conferma/`

Consuma il token e attiva l'identita. Body:

```json
{
  "token": "...",
  "new_password": "...",
  "new_password_confirm": "..."
}
```

`new_password*` obbligatori solo per `token_type=INVITO_PORTALE`. Per
`ATTIVAZIONE_PORTALE_CROSS` vengono **silenziosamente ignorati** (la
password preesistente dell'utente operatore o altra veste resta valida).

**Response**:

```json
{
  "data": {
    "message": "Account portale attivato con successo. ...",
    "token_type": "INVITO_PORTALE"
  }
}
```

### Shop

#### Endpoint shop

- `GET /api/v1/shop/attivazione/validate/{token}/`
- `POST /api/v1/shop/attivazione/conferma/`

Simmetrici ai precedenti del portale, con tipi token `INVITO_SHOP` /
`ATTIVAZIONE_SHOP_CROSS`. Codice errore distinto: `E_ATTIVAZIONE_SHOP`.

---

## Endpoint cross-veste autenticato

### POST `/api/v1/portale/profile/activate-shop/`

Permette a un utente loggato `CLIENTE_PORTALE` di **aggiungersi la veste
`SHOP_CUSTOMER`** sullo stesso `auth_user`, **immediatamente attiva**
(no email, no token: il consenso e' implicito nel click).

Auth: `PortaleAPIView` (`PortaleBasePermission`). Nessun body richiesto.

**Pre-condizioni** verificate dalla view (in ordine):

1. `ruolo_applicativo` corrente == `CLIENTE_PORTALE` — se
   `FORNITORE_PORTALE` o altro: 400 `E_ATTIVAZIONE_SHOP_CROSS`
2. GUC `app.soggetto_ruolo_id` popolata (settata da
   `JwtAuditAuthentication`) — se vuota: 400
3. **Anti-tampering**: se esiste gia' una identita `SHOP_CUSTOMER` per
   quel `soggetto_ruolo` ma legata ad altro `auth_user`: 400 con
   messaggio "Veste shop gia' collegata a un altro utente"

**Response (idempotente)**:

```json
{
  "data": {
    "already_active": true,
    "identita_id": 555,
    "message": "Accesso shop gia' attivo. ..."
  }
}
```

```json
{
  "data": {
    "activated": true,
    "identita_id": 700,
    "message": "Accesso shop attivato. Effettua il login dal canale shop ..."
  }
}
```

Lo shop si raggiunge poi via `POST /api/v1/shop/token/` con le stesse
credenziali del portale (stesso `auth_user`).

---

## Codici errore

| Codice | HTTP | Quando |
| --- | --- | --- |
| `E_INVITO_PORTALE` | 400 | Validazione lato admin (email assente, cliente/fornitore inesistente, identita gia' attiva, identita gia' su altro auth_user, veste non supportata) |
| `E_ATTIVAZIONE_PORTALE` | 400 | Token portale assente/invalido/scaduto, password mismatch, meta senza identita_id, riga identita rimossa tra invio e conferma |
| `E_ATTIVAZIONE_SHOP` | 400 | Stesso perimetro di `E_ATTIVAZIONE_PORTALE` per i 2 endpoint shop |
| `E_ATTIVAZIONE_SHOP_CROSS` | 400 | Cross-veste self-service: ruolo non CLIENTE_PORTALE, GUC vuota, identita su altro auth_user |

---

## Tipi token in `config.token_monouso`

| `tipo` | Scadenza | Emesso da | Consumato da |
| --- | --- | --- | --- |
| `INVITO_PORTALE` | 72h | `invia_invito_cliente/fornitore` (email NUOVA) | `AttivazionePortaleView` flow INVITO |
| `ATTIVAZIONE_PORTALE_CROSS` | 72h | `invia_invito_cliente/fornitore` (email ESISTENTE) | `AttivazionePortaleView` flow CROSS |
| `INVITO_SHOP` | 72h | `invia_invito_shop_customer` (email NUOVA) | `AttivazioneShopView` flow INVITO |
| `ATTIVAZIONE_SHOP_CROSS` | 72h | `invia_invito_shop_customer` (email ESISTENTE) | `AttivazioneShopView` flow CROSS |

I 4 tipi sono **mutuamente esclusivi**: lo stesso `token_hash` non puo'
esistere su 2 tipi grazie al `UNIQUE (token_hash)` su
`config.token_monouso`. Il caller della validate non deve sapere il tipo
in anticipo: `_resolve_token_in(token, tipi)` itera su un insieme
ammesso.

---

## Mappa `_VESTE_CONFIG` (single source of truth)

In [invito_portale_service.py](../../../../backend/apps/portale/services/invito_portale_service.py)
una mappa `dict[str, _VesteConfig]` (TypedDict) parametrizza il flow
comune `_invia_invito_common` su 5 dimensioni:

| Campo | CLIENTE_PORTALE | FORNITORE_PORTALE | SHOP_CUSTOMER |
| --- | --- | --- | --- |
| `token_invito` | `INVITO_PORTALE` | `INVITO_PORTALE` | `INVITO_SHOP` |
| `token_cross` | `ATTIVAZIONE_PORTALE_CROSS` | `ATTIVAZIONE_PORTALE_CROSS` | `ATTIVAZIONE_SHOP_CROSS` |
| `template` | `INVITO_PORTALE` | `INVITO_PORTALE` | `INVITO_SHOP` |
| `link_path` | `/attivazione-portale` | `/attivazione-portale` | `/attivazione-shop` |
| `scadenza_ore` | 72 | 72 | 72 |

**Aggiungere una nuova veste** = aggiungere una nuova entry alla mappa
piu' il nuovo tipo token nel `SHOP_ATTIVAZIONE_TOKEN_TIPI` (o
equivalente). Nessun'altra modifica al service necessaria.

---

## Test di riferimento

- **Service unit**: [test_invito_portale_service.py](../../../../backend/apps/portale/tests/services/test_invito_portale_service.py) — 14 test (11 portale + 3 shop)
- **API portale**: [test_attivazione_portale_view.py](../../../../backend/apps/portale/tests/api/test_attivazione_portale_view.py) — 15 test (12 attivazione + 3 ProfileActivateShop)
- **API shop**: [test_attivazione_shop_view.py](../../../../backend/apps/shop/tests/api/test_attivazione_shop_view.py) — 6 test (3 validate + 3 conferma)

---

## Dipendenza DB

Il template email `INVITO_SHOP` deve essere seedato in
`config.email_template`. Proposta SQL idempotente disponibile in
[backend/scripts/db-proposals/PROPOSTA_seed_email_invito_shop.sql](../../../../backend/scripts/db-proposals/PROPOSTA_seed_email_invito_shop.sql)
— da applicare su `dev/db-tid` aggiungendo la riga al file CSV
`email_template.csv` (changelog `runOnChange` + UPSERT).

Senza il seed, l'invito shop **funziona comunque end-to-end** (token
emesso, identita creata, response 200) ma **l'email non parte** (si
logga `email_failed` ma il flow non si rompe — `try/except` esplicito
per garantire il recovery via copia manuale del link).

---

## Vedi anche

- [api.md](../../../dev/api.md) — Linee guida API generali
- [api_multi_veste_token.md](api_multi_veste_token.md) — Login/refresh multi-veste (§8.3 PR-B1)
- [api_invito_operatore.md](api_invito_operatore.md) — Invito operatore interno (pattern simmetrico)
- [sviluppo-multi-face-auth.md](../../../dev/work-done/sviluppo-multi-face-auth.md) — WIP architetturale
- [pr-b-shop-b2c-cambio-modello.md](../../../dev/work-done/pr-b-shop-b2c-cambio-modello.md) — Sprint PR-B
