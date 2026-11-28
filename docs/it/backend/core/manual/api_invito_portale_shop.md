# API Invito + Attivazione — Portale e Shop

## Scopo

Documenta i flussi end-to-end di **onboarding self-service** delle vesti
non-operatore (`CLIENTE_PORTALE`, `FORNITORE_PORTALE`, `SHOP_CUSTOMER`).
L'admin invia un invito email partendo dal cliente o fornitore
anagrafico; l'utente clicca il link e attiva la propria veste — il flow
distingue automaticamente:

- **INVITO** (l'utente non ha ancora una password vera: email nuova, o
  invitato che non ha mai attivato): l'utente sceglie la password
- **CROSS** (l'utente ha gia' una password vera: operatore o altra veste
  attivata): one-click, password preesistente invariata

Il discriminante e' la **credenziale**, non «l'utente esiste gia'»
(`AuthRepository.auth_user_ha_password`): un `auth_user` creato da un invito
nasce col segnaposto `!`, password non utilizzabile, e lo resta finche' l'invito
non si attiva. ⛔ In **entrambi** i flussi l'identita' nasce `attivo=false` e si
attiva solo al consumo del token. ⭐ La credenziale decide anche **all'attivazione**
(`richiede_password`): se nel frattempo ha una password vera, un token INVITO vale
come un clic e quella password non si sovrascrive.

⭐ **Una strada per tutte le vesti** (2026-09-25, L-3): emissione, reinvio, email e
attivazione sono il building block `apps/core/services/invito_veste.py`, lo stesso
dell'operatore ([api_invito_operatore.md](api_invito_operatore.md)); fra le vesti
cambia solo la **porta** (`PORTA_PORTALE`, `PORTA_SHOP`).

Esiste anche un endpoint **autenticato cross-veste** che consente a un
`CLIENTE_PORTALE` gia' loggato di aggiungersi la veste `SHOP_CUSTOMER`
sullo stesso `auth_user`, senza email/token.

## Contesto

| Building block | Note |
| --- | --- |
| `InvitoPortaleService` (gestisce tutte e 3 le vesti) | Parte della veste: entità → `soggetto_ruolo_id`, credenziale e veste spenta |
| `InvitoVeste` · `attiva_veste` · `PORTA_PORTALE` / `PORTA_SHOP` | Building block unico (`apps/core/services/invito_veste.py`): token, reinvio, email, attivazione; la porta porta tipi token, template, link, codici |
| `TokenService` | Token monouso tipo `INVITO_PORTALE` / `ATTIVAZIONE_PORTALE_CROSS` / `INVITO_SHOP` / `ATTIVAZIONE_SHOP_CROSS`, scadenza 72h |
| `EmailDispatchService` | Template `INVITO_PORTALE` (clienti/fornitori) e `INVITO_SHOP` (shop customer); nel flusso CROSS `INVITO_PORTALE_CROSS` / `INVITO_SHOP_CROSS` |
| `apply_new_password` | Set password + reset flag `deve_cambiare_password` in transazione |
| `AuthRepository.auth_user_ha_password` | Discriminante dei due flussi: l'`auth_user` ha una password utilizzabile? |
| `AuthRepository.attiva_identita` | UPDATE `attivo=true` su `identita_digitali` al consumo del token (entrambi i flussi), col guard su credenziale e porta |
| `AuthRepository.find_auth_user_id_per_email` (dal 2026-10-06; prima `PortaleRepository.find_auth_user_by_email`) | `script.fn_get_auth_user_id_for_email`: la credenziale dell'email senza maiuscole (P-2); email doppie → `E_CREDENZIALE_EMAIL_AMBIGUA` |
| `PermissionResolver.get_ruolo_applicativo` | Filtro veste corrente per `ProfileActivateShopView` |
| GUC `app.soggetto_ruolo_id` | Letto da `ProfileActivateShopView` per legare la nuova identita allo stesso `soggetto_ruolo` del portale corrente |

---

## Endpoint admin (invio invito)

### POST `/api/v1/anagrafiche/clienti/{cliente_id}/invita-portale/`

Invita il cliente come `CLIENTE_PORTALE`. Auth: JWT operatore con livello
area `anagrafiche` = `TUTTO`; la view dichiara `model_permission =
("anagrafiche", "cliente")` (`("anagrafiche", "fornitore")` per gli endpoint
fornitore), e il POST senza `post_permission` chiede `METHOD_REQUIRES['POST'] =
'add'`. Lo stesso vale per tutti gli inviti e le disattivazioni qui sotto; lo
stato accessi chiede lo stesso `model_permission` in lettura.

`reinvio` e' opzionale (default `false`) e deve essere un **booleano JSON**:
`"false"`, `0` → 400 `E_VALIDATION_INPUT` col campo (2026-10-20: prima si
accettavano anche stringhe).

**Body**:

```json
{
  "email": "destinatario@example.com",
  "reinvio": false
}
```

**Chi e' invitato** lo dice l'email: la veste si cerca per (credenziale
dell'email, ruolo anagrafico, tipo), dal 2026-11-28 (giro 4 del
brief-db-accessi-area-clienti, D-M7). Un'email nuova sullo stesso cliente
aggiunge un **referente**, con la sua veste spenta; l'email di un referente gia'
invitato e' il suo reinvio; una veste gia' **accesa** di quella credenziale e'
`E_INVITO_PORTALE` («ha gia' accesso»). ⚠️ Fino a quel giorno la veste si
cercava per (ruolo, tipo), e la veste di un'altra persona sullo stesso cliente
era un errore («gia' collegata a un altro utente»): era il divieto «un referente
per cliente» che D-M7 ha ritirato.

Ogni invito, con `reinvio` `true` o `false`, invalida i token pendenti **della
veste** (i due tipi della porta, con quell'`identita_id` nel meta) nella stessa
transazione del nuovo: vale un link solo. ⭐ Per veste e non per credenziale:
cliente e fornitore portale della stessa persona condividono i tipi, e
l'invito dell'uno non spegne quello dell'altro (fino al 2026-09-25 lo spegneva:
la creazione del token invalidava per tipo e credenziale).

Il reinvio a chi non ha mai attivato resta nel flow **INVITO** (token con scelta
della password): l'`auth_user` esiste, ma la sua password non e' ancora
utilizzabile. ⚠️ Fino al 2026-09-24 il primo invito creava l'identita' gia'
`attivo=true` con una password temporanea, e il flusso si sceglieva da «l'utente
e' stato appena creato»: il reinvio cadeva nel CROSS ed era rifiutato con
`E_INVITO_PORTALE` («ha gia' accesso»), cioe' **impossibile** (M-3 della
[analisi difetti](../../../dev/work-done/2026/analisi-be-difetti-emersi-verifica-doc-api-core.md)).

**Semantica transazionale del reinvio (fix analisi-fix-transazioni #17, 2026-07-08).**
L'invalidazione dei token precedenti e la ri-emissione identita/token avvengono nella
**stessa** transazione (`transaction.atomic()`): se la ri-emissione fallisce, anche
l'invalidazione rolla → l'utente **conserva i token vecchi** e non resta mai senza
alcun token valido (prima l'invalidazione era una scrittura separata committata prima).
L'invio email resta **fuori** dalla transazione, best-effort. Vale su **tutte e tre le
vesti** — CLIENTE_PORTALE, FORNITORE_PORTALE e **SHOP_CUSTOMER** (simmetria ripristinata:
lo shop aveva ancora l'invalidazione fuori-atomic).

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

`inviato` e' l'esito **dell'email** (dal 2026-09-28, F-3 dell'
[analisi difetti](../../../dev/work-done/2026/analisi-be-difetti-emersi-verifica-doc-api-core.md)):
`false` se non e' partita. La chiamata non fallisce — veste e token ci sono, l'invito si
recupera col reinvio — ma `invito_inviato_at` non si aggiorna e il fallimento si logga.
Partita la mail, `invito_inviato_at` lo scrive il verbo del DB `anagrafiche.fn_segna_invito_inviato`, col
permesso di chi invita (dal 2026-11-27: l'app non aggiorna piu' le vesti). Un suo rifiuto arriva come errore
della chiamata e non si ingoia: il permesso l'ha gia' chiesto l'emissione, nella stessa richiesta.
Stesso contratto per le tre vesti (la strada e' una: `InvitoVeste.spedisci`).

`is_cross=true` quando l'`auth_user` ha gia' una password vera: viene aggiunta
una **2a identita** in attesa di attivazione cross. `nuovo_utente` dice solo se
l'`auth_user` e' stato creato ora. In **tutti** i casi l'identita' e'
`attivo=false`, `deve_cambiare_password=false`, e nessuna password viene scritta:
la accende il consumo del token (e nel flow INVITO l'utente sceglie la password
nello stesso gesto).

---

### POST `/api/v1/anagrafiche/fornitori/{fornitore_id}/invita-portale/`

Simmetrico al precedente per `FORNITORE_PORTALE`.

---

### POST `/api/v1/anagrafiche/clienti/{cliente_id}/invita-shop/`

Invita il cliente come `SHOP_CUSTOMER` (B1 §13.7). Riusa lo stesso flow
del portale ma con tipi token `INVITO_SHOP` / `ATTIVAZIONE_SHOP_CROSS`,
template `INVITO_SHOP` (`INVITO_SHOP_CROSS` nel flusso CROSS) e link `{FRONTEND_URL}/attivazione-shop/{token}`.

`SHOP_CUSTOMER` e `CLIENTE_PORTALE` condividono il ruolo anagrafico `CL`
del soggetto: la nuova identita vive sullo stesso `soggetto_ruolo` del
cliente, mai su uno nuovo.

I fornitori **non** hanno un endpoint `invita-shop/`: lo shop e' B2C
consumer per design, non di pertinenza dei fornitori.

---

### GET `/api/v1/anagrafiche/clienti/{cliente_id}/stato-accessi/`

I **referenti** del cliente, per tipo di veste: `portale` (`CLIENTE_PORTALE`) e
`shop` (`SHOP_CUSTOMER`), ciascuno un elenco con una voce per veste, anche spenta,
in ordine di nascita. Elenco vuoto: nessuno invitato. Usato dall'admin UI per
proporre, per referente, invia / reinvia / disattiva, e l'invito di un referente
in piu'. Auth: JWT operatore area anagrafiche ≥ LETTURA.

⭐ Elenchi dal 2026-11-28 (giro 4 del brief-db-accessi-area-clienti, D-M7): un
cliente o un fornitore ha piu' referenti, ognuno con la sua veste. Prima era una
veste per tipo, e lo stato `NESSUNO` lo scriveva il BE.

**Response**:

```json
{
  "data": {
    "portale": [
      {
        "identita_id": 500,
        "auth_user_id": 10,
        "username": "mario.rossi",
        "email": "mario.rossi@example.com",
        "stato": "ATTIVO",
        "utilizzabile": true,
        "attivo": true,
        "valido_dal": "2026-04-20",
        "valido_al": null,
        "invito_inviato_at": "2026-04-20T14:30:00Z",
        "token_scade_at": null
      },
      {
        "identita_id": 512,
        "auth_user_id": 14,
        "username": "anna.bianchi",
        "email": "anna.bianchi@example.com",
        "stato": "PENDING",
        "utilizzabile": false,
        "attivo": false,
        "valido_dal": "2026-11-28",
        "valido_al": null,
        "invito_inviato_at": "2026-11-28T09:00:00Z",
        "token_scade_at": "2026-12-01T09:00:00Z"
      }
    ],
    "shop": [],
    "email_suggerita": "mario.rossi@example.com"
  }
}
```

`utilizzabile` viene da `script.fn_veste_utilizzabile`: dice se la veste **oggi**
apre la porta. Lo stato e `utilizzabile` rispondono a due domande (D-G3-1,
2026-11-27): una veste `ATTIVO` fuori dalle sue date, o col soggetto spento, ha
`utilizzabile = false`, e il pannello lo dice sotto il referente.

`email_suggerita`: l'email con cui il pannello precompila l'invito — il primo
referente che ne ha una (per il cliente prima il portale, poi lo shop), poi il
contatto PRINCIPALE del ruolo, poi il predefinito; o `null`.

`stato` ∈ `{PENDING, NON_SPEDITO, ATTIVO, REVOCATA, DISATTIVO}`, di
`script.fn_stato_veste`:

| Stato | Significato |
| --- | --- |
| `PENDING` | identita `attivo=false` + token non consumato non scaduto, **e** l'email d'invito e' partita dopo la sua emissione (`invito_inviato_at >= data_insert` del token) |
| `NON_SPEDITO` | come `PENDING`, ma l'email di quel token **non e' partita** (`invito_inviato_at` nullo o precedente al token): la persona non ha il link, si reinvia |
| `ATTIVO` | identita `attivo=true` |
| `REVOCATA` | identita `attivo=false` col segno della revoca dell'amministratore (`revocata_at`): non si riaccende, nemmeno con un token in volo, finche' un nuovo invito non toglie il segno. La UI propone «Invia invito» |
| `DISATTIVO` | identita `attivo=false`, senza segno di revoca e nessun token pending (invito scaduto) |

`token_scade_at` e' la scadenza piu' lontana fra i token vivi della veste (invito
+ cross) — usato dalla UI per mostrare "scade tra N ore". E' valorizzato ogni
volta che un token vivo esiste, quindi anche su `ATTIVO`.

Dopo un invito, in entrambi i flussi, la veste e' **`PENDING`** fino
all'attivazione — **`NON_SPEDITO`** se l'email non e' partita (dal 2026-09-28, F-3
dell'[analisi difetti](../../../dev/work-done/2026/analisi-be-difetti-emersi-verifica-doc-api-core.md):
prima un link pendente bastava a dire «invito inviato»). La regola e' la funzione
pura `stato_veste` di `portale_repository.py`. ⚠️ Fino al 2026-09-24 l'invito con email nuova creava l'identita'
gia' attiva, e quel cliente risultava `ATTIVO` prima di aver scelto la password
(M-3).

---

### GET `/api/v1/anagrafiche/fornitori/{fornitore_id}/stato-accessi/`

Simmetrico al precedente ma per fornitori: restituisce solo l'elenco
`portale` (niente shop), con la stessa forma delle voci.

```json
{
  "data": {
    "portale": [{ "identita_id": 600, "stato": "PENDING", "utilizzabile": false, ... }],
    "email_suggerita": null
  }
}
```

---

### POST disattivazione veste (3 endpoint simmetrici)

- `POST /api/v1/anagrafiche/clienti/{cliente_id}/disattiva-portale/`
- `POST /api/v1/anagrafiche/clienti/{cliente_id}/disattiva-shop/`
- `POST /api/v1/anagrafiche/fornitori/{fornitore_id}/disattiva-portale/`

Revoca della veste di **un referente**, dal verbo del DB `anagrafiche.fn_revoca_veste`
(dal 2026-11-26): la spegne e ci scrive il segno della revoca, **anche se era
gia' spenta** con l'invito pendente, e invalida i token pendenti (invito +
cross) **della veste**. Una veste revocata si riapre solo con un nuovo invito
dell'amministratore, che toglie il segno. **Idempotente**: se la veste e' gia'
revocata, la chiamata succede senza errore (`disattivato=false`).

**Body**: la veste da spegnere, una voce dell'elenco dello stato accessi (dal
2026-11-28, D-M7: con piu' referenti «la veste del cliente» non dice quale).

```json
{ "identita_id": 500 }
```

`identita_id` assente o non intero positivo → 400 `E_VALIDATION_INPUT`. Una veste
che non e' **di questo soggetto e di questo tipo** (l'id di un altro cliente, la
veste shop sull'endpoint del portale) → 404 `E_VESTE_NON_TROVATA`, e non si
revoca niente: il verbo del DB controlla il permesso, il perimetro lo controlla
la scheda.

**Response**:

```json
{
  "data": {
    "disattivato": true,
    "stato": "REVOCATA",
    "identita_id": 500
  }
}
```

- `disattivato: true` se la veste era accesa
- `disattivato: false` + `stato="REVOCATA"` se era gia' spenta (il segno si mette lo stesso)

**Effetti collaterali**:

- Se c'era un invito pendente (`PENDING`), il link email smette di
  funzionare: chiunque clicca il link vede "Token non valido o scaduto".
- Le sessioni **della veste** vanno in blacklist (refresh JWT col claim
  `identita_id` di quella veste) e la cache permessi si invalida a commit
  avvenuto, nella stessa transazione dello spegnimento; anche su una veste
  gia' spenta (idempotente). Le sessioni delle altre vesti della stessa
  credenziale restano aperte (A-5, D-5, 2026-10-02 — prima nessuna chiusura).
  L'access gia' emesso vive fino a scadenza, ma ogni richiesta risponde 401
  `E_IDENTITA_NON_ATTIVA` e il refresh 401 (veste spenta,
  [api_multi_veste_token.md](api_multi_veste_token.md) §2-bis).

**Riattivazione**: non c'e' un endpoint "riattiva" dedicato per evitare
ambiguita. Per rimettere in linea un accesso disattivato, l'admin
**rinvia un invito**: flow CROSS se l'utente ha una password vera (aveva gia'
attivato), INVITO se non l'ha mai scelta. L'identita' esistente resta disattivata
e la riattiva il consumo del token nuovo (`AuthRepository.attiva_identita`).

---

## Endpoint pubblici (attivazione)

I 4 endpoint seguenti **non richiedono JWT** (`AllowAny`,
`authentication_classes = []`). I due `conferma` sono throttled tramite
`ConfermaTokenRateThrottle` (10 richieste / 15 minuti per IP; fino al 2026-10-02
condividevano il 3/15m della richiesta di reset); i due `validate` non hanno
throttling dedicato.

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
`requires_password=true` solo per `INVITO_PORTALE` **e** credenziale ancora senza
password vera, decisa al momento della verifica (`richiede_password`).

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

⚠️ Esiste anche `POST /api/v1/shop/register/check-email/`, ma **oggi e' uno stub
che risponde 501** con codice `E_SHOP_NON_DISPONIBILE`: e' il buco lasciato apposta per la registrazione autonoma
(PR-C), che dovra' distinguere tre casi da una sola email — nuova (onboarding
guest), gia' `auth_user` (cross-shop), gia' `SHOP_CUSTOMER` (login). Il body non
viene nemmeno letto, perche' nessuna logica dipende ancora dall'input: chiamarlo
non fa danni e non fa niente.

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
3. La veste `SHOP_CUSTOMER` si cerca per (credenziale della sessione,
   `soggetto_ruolo`, tipo): quella di un altro referente dello stesso cliente
   non e' di chi chiede, e non si trova (dal 2026-11-28, D-M7; prima era un
   400 «Veste shop gia' collegata a un altro utente»)

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
| `E_CLIENTE_NON_TROVATO` | 404 | `cliente_id` (PK di `anagrafiche.clienti`) inesistente: invito, reinvio, stato accessi, disattivazione (dal 2026-10-08; prima 400 `E_INVITO_PORTALE`) |
| `E_FORNITORE_NON_TROVATO` | 404 | `fornitore_id` (PK di `anagrafiche.fornitori`) inesistente, stessi endpoint |
| `E_INVITO_PORTALE` | 400 | Validazione lato admin (email assente, veste della stessa credenziale gia' accesa, veste non supportata). Un altro auth_user sullo stesso cliente non e' piu' un errore: e' un referente in piu' (D-M7, 2026-11-28) |
| `E_VESTE_NON_TROVATA` | 404 | Disattivazione: l'`identita_id` del corpo non e' una veste di questo soggetto e di questo tipo |
| `E_ATTIVAZIONE_PORTALE` | 400 | Token portale assente/invalido/scaduto, password mismatch, meta senza identita_id, riga identita rimossa tra invio e conferma |
| `E_ATTIVAZIONE_SHOP` | 400 | Stesso perimetro di `E_ATTIVAZIONE_PORTALE` per i 2 endpoint shop |
| `E_ATTIVAZIONE_SHOP_CROSS` | 400 | Cross-veste self-service: ruolo non CLIENTE_PORTALE, GUC vuota |

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
in anticipo: `risolvi_token(porta, token)` prova i due tipi della porta.

---

## Le porte (`PortaInvito`)

In [invito_veste.py](../../../../../backend/apps/core/services/invito_veste.py)
ogni porta dice cio' che distingue un invito dall'altro:

| Campo | `PORTA_PORTALE` (CLIENTE_ e FORNITORE_PORTALE) | `PORTA_SHOP` (SHOP_CUSTOMER) |
| --- | --- | --- |
| `token_invito` | `INVITO_PORTALE` | `INVITO_SHOP` |
| `token_cross` | `ATTIVAZIONE_PORTALE_CROSS` | `ATTIVAZIONE_SHOP_CROSS` |
| `template` | `INVITO_PORTALE` | `INVITO_SHOP` |
| `template_cross` | `INVITO_PORTALE_CROSS` | `INVITO_SHOP_CROSS` |
| `link_path` | `/attivazione-portale` | `/attivazione-shop` |
| `codice_invito` / `codice_attivazione` | `E_INVITO_PORTALE` / `E_ATTIVAZIONE_PORTALE` | `E_INVITO_PORTALE` / `E_ATTIVAZIONE_SHOP` |
| `scadenza_ore` | 72 | 72 |

**Aggiungere una veste** = un ruolo in una porta esistente, o una porta nuova
(con le sue due view, sottoclassi di `AttivazioneVesteValidateView` /
`AttivazioneVesteView`).

---

## Test di riferimento

- **Service unit**: [test_invito_portale_service.py](../../../../../backend/apps/portale/tests/services/test_invito_portale_service.py)
- **Building block**: [test_invito_veste.py](../../../../../backend/apps/core/tests/services/test_invito_veste.py) — emissione, reinvio, email, attivazione, verifica
- **API portale**: [test_attivazione_portale_view.py](../../../../../backend/apps/portale/tests/api/test_attivazione_portale_view.py) — cablaggio sulla porta e `ProfileActivateShop`
- **API shop**: [test_attivazione_shop_view.py](../../../../../backend/apps/shop/tests/api/test_attivazione_shop_view.py) — cablaggio sulla porta

---

## Dipendenza DB

Il template email `INVITO_SHOP` deve essere seedato in
`config.email_template`. Proposta SQL idempotente disponibile in
[backend/scripts/db-proposals/PROPOSTA_seed_email_invito_shop.sql](../../../../../backend/scripts/db-proposals/PROPOSTA_seed_email_invito_shop.sql)
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
- [sviluppo-multi-face-auth.md](../../../dev/work-done/2026/sviluppo-multi-face-auth.md) — WIP architetturale
- [pr-b-shop-b2c-cambio-modello.md](../../../dev/work-done/2026/pr-b-shop-b2c-cambio-modello.md) — Sprint PR-B
