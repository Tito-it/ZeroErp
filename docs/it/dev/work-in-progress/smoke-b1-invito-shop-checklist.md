# Smoke e2e B1 §13.7 — Invito shop admin-driven + regression multi-veste

> Checklist operativa post-B1 (sessione 21-04 PM). Valida end-to-end:
>
> 1. Guard FE portale multi-veste (i 7 check skipped in §8.3.9)
> 2. Flow invito shop admin-driven INVITO (email nuova)
> 3. Flow invito shop admin-driven CROSS (email gia' esistente)
> 4. Cross-veste self-service da profilo portale
> 5. Multi-veste isolation `/me/` (kill test del blocker resolver risolto)
> 6. Edge cases / guard
> 7. Regressioni automatiche (full suite BE + pgTAP diagnostico)
>
> **Tempo stimato totale: 45-60 min**. Spunta le caselle man mano. Al
> termine archivia il file (rinomina in `smoke-b1-invito-shop-done-YYYYMMDD.md`
> o eliminarlo se tutto verde).

---

## Prerequisiti

Verifica prima di iniziare — 5 minuti.

* [X] **Gunicorn riavviato** dopo il merge delta B1 (nuovo codice BE
  caricato): `sudo systemctl restart zeroerp-gunicorn.service`
* [X] **Seed DB `INVITO_SHOP` applicato** sul branch `dev/db-tid`
  (verifica: `psql -c "SELECT codice FROM config.email_template WHERE codice='INVITO_SHOP'"` → 1 riga)
* [ ] **Commit delta B1** su `dev/backend-tid` (oppure attesa commit,
  smoke possibile anche in working tree uncommitted)
* [X] **Utenti fixture disponibili** nel DB di test:
  * `tid` — OPERATORE SUPER_ADMIN + CLIENTE_PORTALE gia' attiva (multi-veste)
  * Almeno 1 **utente portale puro** (solo CLIENTE_PORTALE, no OPERATORE)
    — se manca, l'invito shop di un cliente nuovo in Test B lo creera'
* [X] **Password tid** a portata di mano
* [X] **Browser + terminale** aperti (smoke misto UI + curl)

---

## Blocco A — Guard FE portale multi-veste (§8.3.9 residuo)

Tempo: **10-15 min**. Browser-driven. I 7 check skipped ora sono
eseguibili grazie al fix resolver DB 20260421-03/04.

Contesto: tid ha OPERATORE + CLIENTE_PORTALE attive. Post-fix, `/me/` in
contesto PORTALE ritorna correttamente `ruolo_applicativo=CLIENTE_PORTALE`
e il guard FE §8.5.4 puo' distinguere le vesti.

* [X] **A1. Login UI canale PORTALE con tid** → redirect `/portale`
  (non piu' `/` come pre-fix). `/me/` (DevTools Network) deve mostrare
  `ruolo_applicativo: "CLIENTE_PORTALE"`, `is_super_admin: false`,
  `permessi_area: {}` (o subset portale).
* [ ] **A2. `/portale/profile`** — ProfileView visibile, dati portale
  di tid (email, identita CLIENTE_PORTALE attiva).
* [ ] **A3. Click "Attiva accesso shop"** in ProfileView — **post B1
  non piu' 501**: atteso toast success con messaggio "Accesso shop
  attivato. Effettua il login dal canale shop con le stesse credenziali."
  (e bottone disabilitato post-click). Chiamata secondaria: refresh
  ProfileView dovrebbe mostrare "Attivo" anche sulla veste shop.
* [ ] **A4. Digita manualmente `/vendite/listini` nell'URL** — grace
  redirect → `/portale` (guard namespace blocca l'accesso admin in
  contesto portale).
* [ ] **A5. Logout** → LoginView pre-seleziona radio canale **PORTALE**
  (STORAGE_KEYS.LOGIN_CHANNEL persistito).
* [ ] **A6. Login ADMIN con tid + digita `/portale` nell'URL** →
  grace redirect → `/` (dashboard admin). Guard opposto a A4.
* [ ] **A7. Dopo 5-10 min di inattivita, azione che triggera refresh
  token** (es. click qualsiasi link admin) → Network tab: refresh va
  su `/api/v1/admin/token/refresh/` (non `/portale/token/refresh/`).

**Se tutti verdi**: marcare §8.3.9 gate 10 definitivamente chiuso nel
file `pr-b-shop-b2c-cambio-modello.md` (righe 1018-1024, `[~]` → `[x]`).

---

## Blocco B — Flow INVITO shop admin-driven (email nuova)

Tempo: **8-10 min**. Admin invita → email nuova → attiva → login.

* [ ] **B1. Crea (o scegli) un cliente di test** con email **mai vista**
  nel DB (es. `shop-test-001@example.com`). Da UI admin: `Anagrafiche
  → Clienti → Nuovo` oppure pick cliente esistente + aggiorna email del
  soggetto con un'email garantita-nuova.
* [ ] **B2. Drawer cliente → sezione "Accesso shop" → click "Invia
  invito shop"**. Dialog conferma: `Verrà inviata un'email di attivazione
  shop a shop-test-001@example.com` → Accetta.
  * Response atteso: toast success "Invito shop inviato".
  * Log BE (`tail -f /var/log/zeroerp/gunicorn.log` o simile):
    `security.invito_portale_inviato user_id=<NEW> ruolo=SHOP_CUSTOMER
    ... created_user=True is_cross=False identita_id=<N>`.
* [ ] **B3. Verifica DB**:
  ```sql
  SELECT id, ruolo_applicativo, attivo, valido_dal FROM anagrafiche.identita_digitali
   WHERE auth_user_id = (SELECT id FROM django.auth_user WHERE email='shop-test-001@example.com');
  ```
  Atteso: 1 riga `ruolo_applicativo='SHOP_CUSTOMER'`, `attivo=true`,
  `valido_dal=CURRENT_DATE`.
  ```sql
  SELECT tipo, utilizzato, scadenza FROM config.token_monouso
   WHERE auth_user_id = (SELECT id FROM django.auth_user WHERE email='shop-test-001@example.com')
   ORDER BY id DESC LIMIT 1;
  ```
  Atteso: 1 riga `tipo='INVITO_SHOP'`, `utilizzato=false`, `scadenza ≈ now() + 72h`.
* [ ] **B4. Recupera il token** (log BE oppure DB: il link completo non
  si trova in chiaro, solo `token_hash`; per il test recupera il link
  dall'email inviata oppure inserisci un breakpoint temporaneo). In
  alternativa usa il token visibile sul log gunicorn in formato
  `link=http://localhost:5173/attivazione-shop/<TOKEN>`.
* [ ] **B5. Apri browser su `http://localhost:5173/attivazione-shop/<TOKEN>`**.
  Atteso: pagina "Attivazione account shop", form password (flow INVITO,
  `token_type=INVITO_SHOP`, `requires_password=true`).
* [ ] **B6. Imposta password (rispetta policy complessita): `Strong#Pass1`**
  → submit. Atteso: success "Account shop attivato", redirect a `/login`
  dopo 2s.
* [ ] **B7. Login canale SHOP** con email+password appena scelta.
  Atteso: redirect post-login (oggi probabilmente `/` senza layout shop
  dedicato, ma ritorna 200 con JWT valido). Verifica `/me/` in DevTools:
  `ruolo_applicativo: "SHOP_CUSTOMER"`.
* [ ] **B8. Verifica token consumato**:
  ```sql
  SELECT utilizzato, utilizzato_at, ip_utilizzo FROM config.token_monouso
   WHERE tipo='INVITO_SHOP'
     AND auth_user_id=(SELECT id FROM django.auth_user WHERE email='shop-test-001@example.com');
  ```
  Atteso: `utilizzato=true`, `utilizzato_at=now()`, `ip_utilizzo='127.0.0.1'` (o IP reale client).

---

## Blocco C — Flow CROSS shop admin-driven (email esistente)

Tempo: **5-8 min**. Admin invita shop a un cliente la cui email e'
gia' nota come operatore (es. tid stesso).

* [ ] **C1. Trova un cliente di test** il cui `soggetto.email` sia
  `tid@example.com` (stessa email di tid operatore). Se non esiste:
  UPDATE soggetto per forzare la coincidenza, o crea un nuovo cliente
  con email di tid.
* [ ] **C2. Drawer cliente (diverso da B1) → "Invia invito shop"** →
  Conferma → atteso toast success.
  * Log BE: `is_cross=True`, `created_user=False`, `identita_id=<N>`
    (identita SHOP_CUSTOMER nuova su auth_user di tid).
  * **Nessun nuovo auth_user** creato.
* [ ] **C3. Verifica DB**:
  ```sql
  SELECT id, ruolo_applicativo, attivo FROM anagrafiche.identita_digitali
   WHERE auth_user_id=(SELECT id FROM django.auth_user WHERE username='tid')
   ORDER BY id DESC;
  ```
  Atteso: 3 righe (OPERATORE id=19 attivo, CLIENTE_PORTALE id=24 attivo,
  **SHOP_CUSTOMER nuovo attivo=false** in attesa di attivazione).
  ```sql
  SELECT tipo FROM config.token_monouso
   WHERE auth_user_id=(SELECT id FROM django.auth_user WHERE username='tid')
     AND utilizzato=false
   ORDER BY id DESC LIMIT 1;
  ```
  Atteso: `tipo='ATTIVAZIONE_SHOP_CROSS'`.
* [ ] **C4. Apri link shop** `/attivazione-shop/<TOKEN>`. Atteso:
  pagina di conferma one-click (`requires_password=false`), **nessun
  form password**. Messaggio: "Stai per attivare l'accesso allo shop
  con le tue credenziali esistenti. Non è richiesta una nuova password."
* [ ] **C5. Click "Attiva accesso shop"** → success "Accesso shop
  attivato. Effettua il login dal canale shop con le tue credenziali
  esistenti." Redirect `/login`.
* [ ] **C6. Login canale SHOP con tid** (username `tid` + password
  esistente, NON la password shop del Blocco B): 200 + JWT. `/me/`
  ritorna `ruolo_applicativo: "SHOP_CUSTOMER"` (non OPERATORE, grazie
  al fix resolver).
* [ ] **C7. Verifica**: la password di tid non e' stata toccata
  (logout + login ADMIN con stessa password → OK).

---

## Blocco D — Cross-veste self-service da profilo portale

Tempo: **3-5 min**. Cliente portale loggato attiva shop senza email.

**Prerequisito**: un utente CLIENTE_PORTALE puro (senza veste shop). Se
tid ha gia' la veste shop dal Blocco C, usa l'utente portale creato
nel §8.4.7 precedente (oppure disattiva temp l'identita shop di tid).

* [ ] **D1. Login PORTALE** con l'utente portale puro → `/portale/profile`.
* [ ] **D2. Click "Attiva accesso shop"** (bottone
  `AttivaAccessoShopButton.vue`). Atteso:
  * Toast success "Accesso shop attivato. Effettua il login dal canale
    shop con le stesse credenziali."
  * Bottone disabilitato post-click.
  * Network DevTools: `POST /api/v1/portale/profile/activate-shop/` →
    200 con `{activated: true, identita_id: <N>, message: "..."}`.
* [ ] **D3. Verifica DB**: la nuova identita `SHOP_CUSTOMER` esiste
  `attivo=true`, `deve_cambiare_password=false`, sullo stesso
  `soggetto_ruolo_id` della veste CLIENTE_PORTALE dell'utente.
* [ ] **D4. Logout → login canale SHOP** con le stesse credenziali.
  200 + JWT, `/me/` ritorna `SHOP_CUSTOMER`.
* [ ] **D5. Idempotenza**: ritorna nel portale profile dello stesso
  utente, click "Attiva accesso shop" di nuovo. Atteso: stesso toast
  success + response `{already_active: true, ...}`.

---

## Blocco E — Multi-veste isolation `/me/` (kill test blocker resolver)

Tempo: **5 min**. Kill test del fix DB §13.7 che ha risolto il blocker.

Prerequisito: tid ora ha 3 vesti attive (OPERATORE id=19,
CLIENTE_PORTALE id=24, SHOP_CUSTOMER creato in C o D).

Per ogni canale, login + `curl -H 'Authorization: Bearer $TOKEN'
http://localhost:8000/api/v1/core/me/ | jq '.data | {ruolo_applicativo,
is_super_admin, permessi_area}'`.

* [ ] **E1. Canale ADMIN** → `/me/` ritorna:
  * `ruolo_applicativo: "OPERATORE"`
  * `is_super_admin: true` (tid e' super admin operatore)
  * `permessi_area`: tutte le aree a `"TUTTO"`
* [ ] **E2. Canale PORTALE** → `/me/` ritorna:
  * `ruolo_applicativo: "CLIENTE_PORTALE"`
  * `is_super_admin: false` ⚠ kill test: pre-fix era `true` (aggregava
    OPERATORE+SUPER_ADMIN)
  * `permessi_area`: vuoto `{}` o subset portale (non "TUTTO" ovunque)
* [ ] **E3. Canale SHOP** → `/me/` ritorna:
  * `ruolo_applicativo: "SHOP_CUSTOMER"`
  * `is_super_admin: false`
  * `permessi_area`: profilo `SHOP_CUSTOMER_STANDARD` (LETTURA su
    vendite + pagamenti) oppure vuoto se il seed profilo non
    esiste/non e' stato bindato
* [ ] **E4. Guard cross-namespace**: prendi l'access token ADMIN e
  chiama `/api/v1/admin/token/refresh/` con il refresh token PORTALE
  → atteso **401** (cross-veste rifiutato).

**Se E1/E2/E3 verdi**: il fix resolver multi-veste e' confermato
end-to-end — il blocker §0 originale e' realmente risolto.

---

## Blocco F — Edge cases / guard

Tempo: **5 min**. Verifica che i guard BE blocchino i casi anomali.

* [ ] **F1. Fornitore portale NON puo' attivare shop**. Login come
  utente FORNITORE_PORTALE (se esiste), `/portale/profile` → il bottone
  "Attiva accesso shop" **non deve essere visibile** (il panel in
  `PortaleAccessoPanel` e' gia' filtrato su `entitaTipo=cliente` per
  admin, ma su self-service `ProfileView` — verifica). In subordine,
  chiamata diretta:
  ```bash
  curl -sX POST http://localhost:8000/api/v1/portale/profile/activate-shop/ \
    -H "Authorization: Bearer $FORNITORE_TOKEN" | jq
  ```
  Atteso: 400 `error.code=E_ATTIVAZIONE_SHOP_CROSS`, message "Solo i
  clienti portale possono attivare l'accesso shop."
* [ ] **F2. Token shop invalido/scaduto** → `/shop/attivazione/<FAKE>`:
  form mostra "Il link non è valido o è scaduto." (generic, no
  enumeration). Stessa risposta per token scaduto vs inesistente vs
  gia' usato.
* [ ] **F3. Reinvio invalida token precedente**. Admin → drawer cliente
  → "Reinvia invito shop" (danger dialog) → Accetta. Atteso: toast
  "Invito shop reinviato", e il token precedente viene invalidato:
  ```sql
  SELECT tipo, utilizzato FROM config.token_monouso
   WHERE auth_user_id=<ID_UTENTE> AND tipo LIKE '%SHOP%'
   ORDER BY id DESC LIMIT 3;
  ```
  Atteso: token vecchio `utilizzato=true` (invalidato), token nuovo
  `utilizzato=false`.
* [ ] **F4. Guard auth_user divergente (anti-tampering)**. Scenario
  manuale: esiste identita SHOP_CUSTOMER per `soggetto_ruolo_X` ma
  collegata ad `auth_user_A`; un secondo utente `auth_user_B` (loggato
  portale come cliente associato a `soggetto_ruolo_X`) clicca "Attiva
  accesso shop". Atteso: 400 `E_ATTIVAZIONE_SHOP_CROSS` "Veste shop
  gia' collegata a un altro utente". Scenario raro, skip-able se
  fixture non disponibile.

---

## Blocco G — Regressioni automatiche

Tempo: **2-3 min**. CLI-driven.

* [ ] **G1. Full suite BE verde**:
  ```bash
  redis-cli -n 0 EVAL "for _, k in ipairs(redis.call('keys', ARGV[1])) do redis.call('del', k) end" 0 'zeroerp:*throttle*'
  cd backend && ./manage-test.sh -v 0 | tail -4
  ```
  Atteso: `Ran 1593 tests ... OK`. (Il redis-cli reset throttle evita
  falsi 429 tra test `AttivazionePortaleView` / `AttivazioneShopView`.)
* [ ] **G2. pgTAP diagnostico sync transizionale**:
  ```bash
  scripts/testpgtap.sh backend/anagrafiche/test-fn-sync-auth-user-is-active-or-transizione.sql
  ```
  Atteso: 4/4 OK (fn_sync + trigger OK).
* [ ] **G3. Vite build**:
  ```bash
  cd frontend && ./node_modules/.bin/vite build | tail -3
  ```
  Atteso: `✓ built in <1s`.

---

## Gate uscita smoke

Quando tutti i blocchi A-G sono verdi:

* [ ] Aggiornare `pr-b-shop-b2c-cambio-modello.md` §8.3.9 (righe 1018-1024):
  i 7 check `[~]` → `[x]`.
* [ ] Aggiornare `handoff_20260421_b1_invito_shop_done.md` marcando lo
  smoke come superato + archiviare il file nel repo.
* [ ] Commit e push delta B1 su `dev/backend-tid` + apertura PR verso
  `Tito-dev` (se non gia' fatto).
* [ ] Scegliere il prossimo task Stage D §13.7 (vedi handoff per le 5
  direzioni possibili: §5.6 self-register, §5.9 API shop, §6.6 UI shop
  pubblica, §5.10.4-5 audit+headers, §4.9.7-9 RLS).

---

## Se qualcosa non va

1. **Email non parte** → verifica seed `INVITO_SHOP` (prerequisito D) +
   SMTP account configurato. Il flow BE funziona comunque (token emesso,
   identita creata), solo l'email manca: recupera il link dal log
   gunicorn (log `security.invito_portale_inviato` + query
   `config.token_monouso` per trovare `token_hash` — ma il token in
   chiaro non e' recuperabile post-emissione; se l'email manca, rigenera
   via "Reinvia invito").
2. **/me/ ritorna ancora OPERATORE in canale PORTALE** → verifica DB
   migrations 20260421-03/04 applicate (`SELECT pg_get_functiondef('script.fn_get_user_permissions_map'::regproc)`
   deve contenere `current_setting('app.ruolo_applicativo'...)`).
3. **Tid lockout in sessione** → controllo
   `anagrafiche.identita_digitali` per tid (tutte e 3 le vesti attive +
   finestra temporale valida). Vedi handoff precedente per fix
   `auth_user.is_active=false` post-disattivazione.
