# API Invito Operatore al Primo Accesso

## Scopo

Permette all'admin di invitare un operatore via email. L'operatore riceve un link
e attiva la sua **veste operatore**: sceglie la password se non ne ha ancora una,
altrimenti conferma con un clic. Nessuna password viene scelta dall'admin né
comunicata.

## Contesto

L'invito operatore è il building block unico d'invito delle vesti
(`apps/core/services/invito_veste.py`, porta `PORTA_OPERATORE`), lo stesso di
portale e shop: la regola è quella dell'analisi accessi §4.2
([catalogo BB backend](../../../dev/backend/catalogo-building-block-backend.md),
sezione «Invito e attivazione di una veste»).

- La **creazione** dell'operatore fa nascere la veste OPERATORE **spenta**
  (madre `anagrafiche.fn_crea_operatore_v2`, P-2) e una credenziale nuova col
  segnaposto non utilizzabile; se l'email è già di una credenziale, la si
  riusa (la risposta lo dice: `credenziale_riusata`, `username`).
- L'**invito** non tocca mai la password della credenziale (fino al
  2026-09-25 la sovrascriveva con una temporanea: A-1).
- L'**attivazione** consuma il token e **accende la veste** nella stessa
  transazione (A-3).
- ⭐ L'invito è anche **l'unica strada per riattivare** un operatore spento
  (D-3, 2026-10-04): la riattivazione diretta (`operatori/{id}/riattiva/`,
  PATCH `attivo: true`) è ritirata. Il gesto dell'amministratore riapre la
  **risorsa umana** (il rapporto), la veste la accende la persona attivando:
  nessuna veste torna attiva senza che la persona lo sappia.

---

## Flusso completo

```text
1. Admin crea l'operatore → veste OPERATORE spenta
   (oppure: operatore disabilitato → veste spenta, risorsa umana chiusa)
   |
2. Admin apre il drawer → «Invia invito» (visibile quando can_invite del DB)
   POST /amm-software/operatori/{id}/invita/
   → fn_check_operatore_invitabile (veste spenta, nella finestra, email)
   → la veste OPERATORE spenta della credenziale (una sola)
   → risorsa umana riaperta se chiusa (attivo=true, valido_al=NULL,
     valido_dal intatto), nella transazione del token (D-3)
   → token: INVITO_OPERATORE se la credenziale non ha una password vera,
     ATTIVAZIONE_OPERATORE_CROSS se ce l'ha (72 ore, meta con identita_id)
   → email con link {FRONTEND_URL}/attivazione/{token}
   → invito_inviato_at sulla veste (solo se l'email e' partita)
   → Response: { inviato, email: "m***@azienda.it", is_cross }
   |
3. GET /auth/attivazione-validate/{token}/
   → { valid, token_type, requires_password }
   |
4. POST /auth/attivazione/ { token [, new_password, new_password_confirm] }
   → (con password) validata PRIMA del consumo
   → consumo + (password) + veste accesa, in una transazione
   |
5. Login con il nome utente (D-9) e la password
```

---

## Endpoint Admin

Base path: `/api/v1/amm-software/`
Autenticazione: JWT + ruolo `SUPER_ADMIN` (`AdminAPIView`)

### Invia invito

```http
POST /api/v1/amm-software/operatori/{auth_user_id}/invita/
```

Body vuoto. L'endpoint verifica automaticamente se l'operatore e' invitabile.

**Condizioni per essere invitabile** (le decide `script.fn_check_operatore_invitabile`,
rev P-2 `20260925-43`, D-8; il drawer le legge come `can_invite` / `invite_reason`):

1. la credenziale esiste e ha almeno una veste OPERATORE;
2. **nessuna** veste OPERATORE è già attiva (motivo `Veste OPERATORE gia' attiva`:
   l'accesso c'è già, per una password dimenticata c'è il reset);
3. la veste è nella sua finestra di validità (`valido_dal`/`valido_al`);
4. la credenziale ha un indirizzo email.

**Riapertura del rapporto (D-3, 2026-10-04).** Nella stessa transazione
dell'emissione, prima del token, la risorsa umana della veste che si sta
invitando (la stessa `identita_id` del token) si riapre se è chiusa:
`attivo = true`, e `valido_al = NULL` solo se è già arrivata (oggi o prima,
come la scrive «Disabilita»); una fine rapporto **futura** resta.
`valido_dal` non si tocca (è l'inizio del rapporto). Su un operatore mai
attivato è già aperta e non si scrive niente. Riaprire il padre prima che la
persona accenda il figlio è l'ordine che il DB chiede (api.md §«Disattivazione
record»). Sede: `RisorseUmaneCoreRepository.riapri_risorsa_umana_della_veste`.

⛔ Non contano più `last_login` (D-8) né `is_active` (derivato dalle vesti:
falso per costruzione finché la veste è spenta). Il service invita **l'unica**
veste OPERATORE spenta: se la credenziale ne ha più d'una, rifiuta
(`E_INVITO_OPERATORE`, intervento manuale) invece di sceglierne una a caso.

#### Output (successo)

```json
{ "data": { "inviato": true, "email": "m***@azienda.it", "is_cross": false } }
```

`is_cross = true`: la persona ha già una password (per esempio è cliente del
portale) e attiverà con un clic.

L'email e' mascherata per sicurezza (solo primo carattere + `***@dominio`).

`inviato` e' l'esito **dell'email**: `false` se non e' partita (SMTP fallito, canale
non configurato, template o account mancanti). La chiamata **non** fallisce — il token
e' stato emesso e resta valido, l'invito si recupera col reinvio — ma il fallimento si
logga (logger `security`, il motivo e' nel giornale email) e `invito_inviato_at` non si
aggiorna. In console mode (`DEBUG`) la mail e' stampata e vale come partita. Fino al
2026-09-28 la risposta era `inviato: true` anche a email fallita (F-3 dell'
[analisi difetti](../../../dev/work-done/analisi-be-difetti-emersi-verifica-doc-api-core.md)).
Dal 2026-09-25 anche `invita`, come `reinvia-invito`, invalida i token pendenti della
veste nella transazione del nuovo — vale un link solo.

#### Errori

| Codice | HTTP | Causa |
| --- | --- | --- |
| `E_AMM_OPERATORE_NOT_FOUND` | 404 | L'`auth_user_id` non nomina un operatore: credenziale inesistente o senza veste OPERATORE (motivi `UTENTE_NON_TROVATO` / `SENZA_VESTE_OPERATORE` di `fn_check_operatore_invitabile`, nel `context.reason`). Dal 2026-10-08; prima 400 `E_INVITO_OPERATORE` |
| `E_INVITO_OPERATORE` | 400 | Operatore non invitabile per gli altri motivi (veste gia' attiva, fuori finestra, senza email, piu' vesti spente): `reason` e `reason_key` nel contesto |

### Reinvia invito

```http
POST /api/v1/amm-software/operatori/{auth_user_id}/reinvia-invito/
```

Invalida i token pendenti **della veste** e ne genera uno nuovo **nella stessa
transazione** (prima l'invalidazione era una scrittura separata: se l'emissione
falliva l'operatore restava senza link, A-4), poi rinvia l'email. È la stessa
strada di `invita`, riapertura della risorsa umana compresa: è il pulsante con
cui l'amministratore riattiva un operatore disabilitato (D-3).

---

## Endpoint Pubblico — Validazione Token Invito

```http
GET /api/v1/auth/attivazione-validate/{token}/
```

**Non autenticato** (`AllowAny`). Verifica se un token invito e' ancora valido senza consumarlo.
Usato dal frontend per mostrare il form di attivazione o un messaggio di errore/scadenza.

### Output

```json
{ "data": { "valid": true, "token_type": "INVITO_OPERATORE", "requires_password": true } }
```

`requires_password` lo decide la **credenziale adesso**: un token
`INVITO_OPERATORE` su una credenziale che nel frattempo ha una password vera
(ha attivato un'altra veste) vale come un clic, e quella password non si
sovrascrive.

oppure:

```json
{ "data": { "valid": false, "message": "Token non valido, scaduto o gia' utilizzato." } }
```

---

## Endpoint Pubblico — Attivazione

```http
POST /api/v1/auth/attivazione/
```

**Non autenticato** (`AllowAny`). Rate limiting: `ConfermaTokenRateThrottle`, 10 richieste / 15 minuti per IP
(contatore proprio delle conferme con link; fino al 2026-10-02 era il 3/15m della richiesta).

### Input

```json
{
  "token": "a1b2c3d4...",
  "new_password": "password-scelta",
  "new_password_confirm": "password-scelta"
}
```

Con `requires_password = false` basta `{ "token": … }`: una password nel
payload si **ignora**.

### Validazioni (ordine critico)

1. `token` non vuoto
2. Token valido di uno dei due tipi della porta — **validato senza consumare**
3. utente del token esistente
4. `identita_id` (la veste) nel meta del token (obbligatorio: un token senza non attiva niente)
5. (solo con password) `new_password` non vuota, `new_password == new_password_confirm`,
   poi i validators di `AUTH_PASSWORD_VALIDATORS`
6. **Solo dopo**: il token viene consumato

> Se la password e' troppo debole (es. "12345678"), il token resta valido
> e l'operatore puo' riprovare con una password piu' forte.

`new_password` e `new_password_confirm` non vengono ripulite dagli spazi: si
salva la password digitata, e il login non la ripulisce (S-5, 2026-09-27).

### Azioni (atomiche)

1. consumo del token
2. (con password) `apply_new_password`: password + cambio obbligatorio spento
   (della credenziale, D-7)
3. **la veste si accende** (`AuthRepository.attiva_identita`, guard su
   credenziale e porta); se non c'è più, tutto si annulla

### Output

```json
{
  "data": {
    "message": "Account attivato con successo. Effettua il login con la nuova password.",
    "token_type": "INVITO_OPERATORE"
  }
}
```

Nel flusso cross (`token_type` `ATTIVAZIONE_OPERATORE_CROSS`, o credenziale che ha
gia' una password) il messaggio e' «Accesso operatore attivato. Effettua il login
con le tue credenziali esistenti.».

> L'operatore deve fare login manualmente dopo l'attivazione.

### Errori

| Codice | HTTP | Causa |
| --- | --- | --- |
| `E_ATTIVAZIONE` | 400 | Token assente, non valido, scaduto o gia' usato; utente inesistente; token senza veste; veste non più disponibile; password vuota, mismatch, troppo semplice |
| `E_TOKEN` | 400 | Il token era valido alla verifica ma il consumo non riesce (es. consumato in parallelo) |

---

## Sicurezza

- **Nessuna password dell'admin**: la credenziale nuova nasce col segnaposto non utilizzabile; solo il token viaggia nell'email
- **La veste nasce spenta**: prima dell'attivazione non si entra (una credenziale riusata riceve `E_VESTE_NON_ATTIVA`)
- **Token SHA-256**: solo hash in DB, token in chiaro solo nell'email
- **Scadenza 72 ore**: l'operatore ha 3 giorni per attivare
- **Invalidazione**: ogni invito (primo o reinvio) invalida i token pendenti della veste nella stessa transazione del nuovo
- **Validate-before-consume**: la password viene validata PRIMA di consumare il token — password debole non brucia il token
- **Rate limiting**: 10/15min per IP sull'endpoint attivazione (`ConfermaTokenRateThrottle`)
- **IP tracking**: l'attivazione registra l'IP di chi consuma il token
- **Operazioni atomiche**: consumo + password + veste in `transaction.atomic()`, email invito fuori transazione (non blocca il flusso)
- **Email mascherata**: la response all'admin mostra solo `m***@dominio`

## Dipendenze DB

| Oggetto | Scopo |
| --- | --- |
| `script.fn_check_operatore_invitabile(auth_user_id)` | Invitabilità (veste spenta, finestra, email) |
| `anagrafiche.fn_crea_operatore_v2` | Creazione: credenziale riusata o nuova, veste spenta |
| `config.token_monouso` | Token invito con scadenza 72h |
| `anagrafiche.identita_digitali.invito_inviato_at` | Timestamp ultimo invito |
| `anagrafiche.identita_digitali.attivo` | La veste: spenta fino all'attivazione |

## File Python

| File | Scopo |
| --- | --- |
| `apps/core/services/invito_veste.py` | Building block: porta, emissione, spedizione, attivazione |
| `apps/core/api/attivazione_veste_views.py` | Le due view pubbliche generiche |
| `apps/anagrafiche/services/invito_operatore_service.py` | Parte dell'operatore: check del DB, veste da invitare |
| `apps/amm_software/api/invito_views.py` | 2 endpoint admin (invita, reinvia) |
| `apps/core/api/attivazione_view.py` | Le view pubbliche sulla porta OPERATORE |
| `apps/core/db/auth_repository.py` | `find_identita_per_ruolo`, `auth_user_ha_password`, `attiva_identita`, `set_invito_inviato_at` |
