# PR-B — Cambio modello: shop B2C canale autonomo + SSO multi-veste

> **Stato:** handoff attivo (20-04-2026) — PR-B in corso su `dev/backend-tid`
>
> **Destinatari:** tid (DB), backend PR-B, frontend PR-B
>
> **Prerequisiti da leggere (in ordine):**
>
> 1. [architettura-multi-face-auth v2.0](../../guide/architettura-multi-face-auth.md) — modello SSO multi-veste, invariante tutto-o-niente GUC, canale_origine, namespace login
> 2. [contratto-guc-app.md](../../guide/contratto-guc-app.md) — PRD del contratto GUC `app.*` per BE (authentication class, SET atomico, fail-closed)
> 3. [architettura-permessi-e-autorizzazioni.md §6, §9.2, §13](../../guide/architettura-permessi-e-autorizzazioni.md) — enforcement Django aggiornato: 3 permission class per namespace, diagramma ER post-cutover, SUPER_ADMIN come profilo
>
> **Tracciamento parallelo:** [sviluppo-multi-face-auth.md](./sviluppo-multi-face-auth.md) — aggiornare stato fasi §4, §5, §6 dopo merge

---

## 0. Changes a colpo d'occhio (scan rapido per BE/FE)

> Sezione dedicata a chi deve recepire velocemente. Dettaglio completo in §2-§4.

### 0.1 Breaking changes — BE (devono essere corretti, PR-B non passa senza)

* ❗ **`identita_digitali` NON piu' 1:1 con `auth_user`** — un `auth_user` puo' avere N identita attive. Tutti gli ORM query/filter che assumono `auth_user.identita` singolare vanno corretti con `.filter(ruolo_applicativo=X, attivo=True).first()` o simile.
* ❗ **Endpoint login unico `/api/token/` → 3 endpoint separati** per namespace: `/api/admin/token/`, `/api/portale/token/`, `/api/shop/token/`. Discriminano quale identita attivare per l'utente autenticato.
* ❗ **JWT deve includere claim `identita_id`** (custom). Il refresh preserva il claim.
* ❗ **`JwtAuditAuthentication` popola 3 GUC nuovi** (`app.current_identita_id`, `app.ruolo_applicativo`, `app.soggetto_ruolo_id`) in aggiunta ai 2 legacy. SET atomico in un'unica query, fail-fast se step parziale. Dettaglio completo: [Contratto GUC app.*](../../guide/contratto-guc-app.md).
* ❗ **`fn_sync_auth_user_is_active(auth_user_id)`** — semantica **OR** (almeno 1 identita utilizzabile). I test che assumono AND sul vecchio modello falliscono.
* ❗ **`InvitoPortaleService`** — se email gia' esiste, NON creare nuovo `auth_user`: aggiungere solo `identita_digitali(CLIENTE_PORTALE, attivo=false)` sullo stesso user + token `ATTIVAZIONE_PORTALE_CROSS`.

### 0.2 Additions — BE (stub ora, implementazione completa PR-C)

* ➕ Endpoint `POST /api/shop/register/check-email/` — pre-check email esistente
* ➕ Endpoint `POST /api/portale/profile/activate-shop/` — genera token, invia email
* ➕ Endpoint `GET /api/shop/activate/<token>/` — attiva identita SHOP_CUSTOMER
* ➕ Permission class `PortaleBasePermission` + `ShopPermission` (stub se non esistono gia')
* ➕ `/me/` restituisce SOLO identita del JWT corrente (no "tutte le identita")

### 0.3 Breaking changes — FE

* ❗ **Login unico** → **login con switch canale** (admin / portale / shop), determina endpoint chiamato
* ❗ **Store Pinia auth** deve gestire `identita_id` + `ruolo_applicativo` (non solo `user`)
* ❗ **Routing guard per namespace** — `/portale/*` rifiuta se `ruolo_applicativo = OPERATORE`, e viceversa
* ❗ **Gestione errore 403 `E_VESTE_NON_ATTIVA`** generico (no enumeration di vesti esistenti)

### 0.4 Additions — FE

* ➕ Pulsante "Attiva accesso shop" nel profilo portale (`/portale/profile/`)
* ➕ Stub routing `/shop/*` (vuoto, implementazione PR-C)

### 0.5 DB (gia' pianificato, verrà consegnato da `dev/db-tid`)

* ✅ Piano 11 migration `20260420-01..50` — vedi [§2 Piano DB](#2-piano-db--migration-in-ordine)
* ✅ Ordine: rilassamento vincoli → ENUM canale → colonne → schema shop → policy RLS → scope function ruolo-aware → sync OR → resolver → trigger
* ✅ Nessun dato esistente viola i nuovi vincoli (safe)

### 0.6 Dipendenze tra i tre team

```text
┌──────────────────────────────────────────────────────────┐
│  DB (dev/db-tid) — DEVE MERGIARE PER PRIMO              │
│  Migration 20260420-01..50                              │
└──────────────────────────────────────────────────────────┘
         │
         ├────────────────────────┬────────────────────────┐
         ▼                        ▼                        ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  BE (PR-B)       │    │  FE (PR-B)       │    │  Doc (fatto)     │
│  authentication  │◄──►│  switch canale   │    │  guida v2.0      │
│  JWT + GUC       │    │  store Pinia     │    │  contratto GUC   │
│  3 token endpoint│    │  routing guard   │    │  permessi §6-13  │
│  InvitoService   │    │  attiva-shop btn │    │                  │
└──────────────────┘    └──────────────────┘    └──────────────────┘
```

**Checkpoint:** BE e FE possono sviluppare in parallelo SOLO dopo merge DB. Senza le nuove migration, il BE non ha le tabelle/funzioni giuste; il FE dipende dal contratto BE.

---

## 1. Contesto

Le decisioni di dominio prese il 20-04-2026 hanno richiesto di rivedere il modello
multi-face auth **prima** che PR-B (backend portali MVP) finalizzi i suoi contratti.
La guida architetturale e' stata riscritta (v2.0). Questo documento traduce le
decisioni in: (a) piano DB ordinato, (b) contratti BE da rispettare in PR-B,
(c) contratti FE da rispettare in PR-B.

### 1.1 Le 4 decisioni

1. **Shop e' canale B2C autonomo** — non vetrina del portale B2B
2. **Un `auth_user`, N identita** — SSO-style, email uniche globali, veste
   scelta dal namespace di login
3. **Portale vede tutto, shop vede solo shop** — asimmetria di visibilita' sui
   dati transazionali
4. **Shop emette ricevute consumer** — mai fatture elettroniche; ricevute su
   `shop.ricevute`, BA separati per canale

### 1.2 Invarianti di modello (post decisioni)

* Al massimo 1 identita attiva per `(auth_user, ruolo_applicativo)`
* Al massimo 1 identita attiva per `(soggetto_ruolo, ruolo_applicativo)`
* `auth_user.is_active = true` iff almeno 1 identita utilizzabile (OR)
* `canale_origine` immutabile post INSERT su ordini/fatture/BA
* 3 GUC `app.*` popolati insieme o nessuno (tutto-o-niente)
* `fn_current_identita_context()` fail-closed se tripla incoerente

---

## 2. Piano DB — migration in ordine

Branch: `dev/db-tid`. Numerazione continua da `20260420-01`. Tutte le migration
sono **non distruttive sui dati**: ALTER ADD COLUMN con default, DROP INDEX /
CREATE INDEX parziale, CREATE TABLE nuovi schemi, ALTER POLICY.

### 2.1 Rilassamento vincoli `identita_digitali`

**Migration `20260420-01-alter-identita-digitali-unique-multi-veste-mctit.yaml`**

```sql
-- DROP UNIQUE su auth_user_id (era 1:1, ora 1:N)
ALTER TABLE anagrafiche.identita_digitali
    DROP CONSTRAINT uq_identita_digitali_auth_user;

-- ADD UNIQUE parziale su (auth_user_id, ruolo_applicativo) per identita attive
CREATE UNIQUE INDEX uq_identita_digitali_auth_user_ruolo_attivo
    ON anagrafiche.identita_digitali (auth_user_id, ruolo_applicativo)
    WHERE attivo = true;

-- DROP UNIQUE parziale vecchio su (soggetto_ruolo_id)
DROP INDEX anagrafiche.uq_identita_digitali_soggetto_ruolo_attivo;

-- CREATE UNIQUE parziale nuovo su (soggetto_ruolo_id, ruolo_applicativo)
CREATE UNIQUE INDEX uq_identita_digitali_sr_ruolo_attivo
    ON anagrafiche.identita_digitali (soggetto_ruolo_id, ruolo_applicativo)
    WHERE attivo = true;
```

**Rischio:** zero dati esistenti violano i nuovi vincoli (oggi UNIQUE su
`auth_user_id` garantisce 1:1, quindi l'unicita' per `(user, ruolo)` e' banale;
stesso per SR). Safe.

### 2.2 Nuovo ENUM `config.canale_origine`

**Migration `20260420-02-create-canale-origine-enum-mctit.yaml`**

```sql
CREATE TYPE config.canale_origine AS ENUM (
    'ADMIN',
    'PORTALE',
    'SHOP'
);
```

### 2.3 Aggiunta colonna `canale_origine`

**Migration `20260420-03-add-canale-origine-columns-mctit.yaml`**

ALTER TABLE con `DEFAULT 'ADMIN' NOT NULL` su:
* `anagrafiche.billing_account`
* `vendite.ordini`
* `vendite.fatture`

(non serve su `vendite.fatture_scadenze`: si eredita via join a `fatture_id`.
Non serve su `acquisti.*`: la decisione 1 dice "acquisti sono tutti ADMIN".)

**Trigger immutabilita':**

```sql
-- trgfn_guard_canale_origine_immutable su UPDATE, applicato alle 3 tabelle
CREATE OR REPLACE FUNCTION script.trgfn_guard_canale_origine_immutable()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.canale_origine IS DISTINCT FROM OLD.canale_origine THEN
        PERFORM script.fn_log_and_raise_error('E_CANALE_ORIGINE_IMMUTABILE', ...);
    END IF;
    RETURN NEW;
END;
$$;
```

Trigger `trg_<tab>_a10_canale_origine_immutable_upd` su ciascuna tabella.

**Rischio:** backfill su dati esistenti.
* `vendite.ordini` / `vendite.fatture`: tutte le righe esistenti sono pre-refactor,
  quindi `ADMIN` (default) e' semanticamente corretto
* `anagrafiche.billing_account`: idem, esistono solo BA creati da operatore

### 2.4 Nuovo schema `shop` + tabella `ricevute`

**Migration `20260420-04-create-schema-shop-mctit.yaml`**

```sql
CREATE SCHEMA shop;
COMMENT ON SCHEMA shop IS 'Canale self-service B2C — ricevute consumer, ordini shop';
```

**Migration `20260420-05-create-shop-ricevute-mctit.yaml`**

```sql
CREATE TABLE shop.ricevute (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    numero              VARCHAR NOT NULL,      -- numerazione dedicata shop
    data_emissione      DATE NOT NULL,
    soggetto_ruolo_id   BIGINT NOT NULL REFERENCES anagrafiche.soggetti_ruoli(id),
    billing_account_id  BIGINT NOT NULL REFERENCES anagrafiche.billing_account(id),
    ordine_shop_id      UUID REFERENCES vendite.ordini(id),  -- nullable
    totale_lordo        NUMERIC(15,2) NOT NULL,
    totale_iva          NUMERIC(15,2) NOT NULL,
    pagamento_metodo    VARCHAR NOT NULL,     -- carta, contanti, ecc.
    pagamento_esito     VARCHAR NOT NULL,     -- OK, KO, PENDING
    meta                JSONB NOT NULL DEFAULT '{}',
    -- audit/tx_id automatici via framework
);
-- Guard: BA deve avere canale_origine = 'SHOP'
-- UNIQUE (numero, data_emissione) per anno fiscale
```

Schema futuro: `shop.ordini` (o riuso di `vendite.ordini` con
`canale_origine='SHOP'` — decisione rimandata, per ora si usa vendite.ordini).

### 2.5 Policy RLS da aggiornare

**Migration `20260420-10..16` — una per tabella.**

Le 6 policy dormienti di PR1.5 vanno adeguate al nuovo modello:

| #   | Policy                                    | Cambio                                                                                                   |
| --- | ----------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| 10  | `rls_fatture_ba_ownership`                | nessun cambio USING — portale vede tutto (caso 2)                                                        |
| 11  | `rls_fatture_ef_whitelist`                | nessun cambio                                                                                            |
| 12  | `rls_ordini_cliente_ownership`            | split in 2: `rls_ordini_portale` (no filtro canale) + `rls_ordini_shop` (filtro `canale_origine='SHOP'`) |
| 13  | `rls_fatture_scadenze_ba_ownership`       | nessun cambio                                                                                            |
| 14  | `rls_acquisti_ordini_fornitore_ownership` | nessun cambio                                                                                            |
| 15  | `rls_acquisti_ddt_fornitore_ownership`    | nessun cambio                                                                                            |
| 16  | `rls_billing_account_self_ownership`      | split in 2: `rls_ba_portale` (no filtro canale) + `rls_ba_shop` (filtro `canale_origine='SHOP'`)         |

**Nuova policy per `shop.ricevute`** (`20260420-17`):

```sql
CREATE POLICY rls_ricevute_shop_self_ownership ON shop.ricevute
    FOR SELECT
    USING (
        current_setting('app.ruolo_applicativo', true) = 'SHOP_CUSTOMER'
        AND script.fn_scope_cliente_ownership(
                NULLIF(current_setting('app.current_identita_id', true), '')::bigint,
                soggetto_ruolo_id
            )
    );

-- Policy operatore admin per customer care shop
CREATE POLICY rls_ricevute_shop_admin ON shop.ricevute
    FOR ALL
    USING (
        current_setting('app.ruolo_applicativo', true) = 'OPERATORE'
        AND script.fn_scope_ef_whitelist(...)  -- stessa whitelist operatore
    );
```

**Stato:** tutte le policy restano **DRY-RUN** (no ENABLE/FORCE) fino alla
migration di attivazione post-PR-B (§4.9.7-9 del WIP multi-face).

### 2.6 Irrobustimento `fn_scope_ba_ownership` ruolo-aware

**Migration `20260420-20-update-fn-scope-ba-ownership-ruolo-aware-mctit.yaml`**
(runOnChange)

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ba_ownership(
    p_identita_id bigint,
    p_billing_account_id bigint
)
RETURNS boolean LANGUAGE sql STABLE AS $$
    SELECT EXISTS (
        SELECT 1
          FROM anagrafiche.identita_digitali id
          JOIN anagrafiche.billing_account  ba
            ON ba.soggetto_ruolo_id = id.soggetto_ruolo_id
         WHERE id.id     = p_identita_id
           AND id.attivo = true
           AND id.ruolo_applicativo IN ('CLIENTE_PORTALE', 'SHOP_CUSTOMER')
           AND ba.id     = p_billing_account_id
    );
$$;
```

Aggiunge filtro `ruolo_applicativo IN (...)` dentro la fn, elevando la regola
dal livello policy al livello scope. Difesa-in-profondita coerente con §V
sviluppo-concentrico.

**Rischio:** nessuno. Oggi la fn e' gia' invocata **solo** dalle policy gated
sui 2 ruoli CL — il filtro nuovo e' idempotente.

### 2.7 Generalizzazione `fn_sync_auth_user_is_active` — OR

**Migration `20260420-30-update-fn-sync-auth-user-is-active-or-mctit.yaml`**
(runOnChange)

Algoritmo:

```text
bool_or over identita_digitali del user:
  - id.attivo = true
  - id.ruolo_applicativo != 'DISABILITATO'
  - CURRENT_DATE BETWEEN id.valido_dal AND COALESCE(id.valido_al, CURRENT_DATE)
  - se OPERATORE: AND risorse_umane.attivo (vincolo legacy)

Se bool_or -> auth_user.is_active = true
Altrimenti -> auth_user.is_active = false
```

### 2.8 Adeguamento funzioni resolver

Le funzioni esistenti che accettano `auth_user_id` e oggi assumono 1:1 vanno
riviste per funzionare con 1:N:

* `fn_is_super_admin(auth_user_id)` → oggi cerca un'unica identita, domani
  cerca l'identita **`OPERATORE`** specifica (aggiungere filtro
  `ruolo_applicativo='OPERATORE'` nella JOIN)
* `fn_has_identita_attiva(auth_user_id)` → semantica OR (true se almeno una)
* `fn_get_profili_accesso_applicabili(auth_user_id)` → deve accettare
  `auth_user_id` + `ruolo_applicativo` (o leggere il GUC). Oggi legge 1 identita
  per user; domani deve sapere quale delle N usare.
* `fn_current_identita_context()` → fail-closed se i 3 GUC non sono coerenti
  (uno NULL, tutti NULL)

**Migration `20260420-40..45`** — una per funzione (runOnChange).

### 2.9 Trigger di sync

**Migration `20260420-50-update-trg-identita-sync-auth-user-active-mctit.yaml`**
(runOnChange)

Il trigger `trg_identita_digitali_z90_sync_auth_user_active_ins_upd` gia' esiste:
chiama `fn_sync_auth_user_is_active(NEW.auth_user_id)`. Con la nuova fn OR, il
trigger automaticamente ricalcola l'OR. Nessun cambio al trigger.

**Serve invece aggiungere** un trigger su ogni UPDATE/INSERT/DELETE di
`identita_digitali` per **qualsiasi `auth_user_id`** toccato, in modo che la
disattivazione di una veste aggiorni `is_active` via OR. Il trigger esistente
lo fa gia' (chiamata per NEW.auth_user_id). Verifica: se DELETE, serve
`OLD.auth_user_id` — check in post-implementazione.

---

## 3. Contratti Backend (PR-B)

### 3.1 Quello che PR-B gia' stava facendo e resta valido

* Service `InvitoPortaleService` per creare identita portale
* Namespace API `/api/portale/*` dedicato
* Permission class `PortaleBasePermission`
* Uso GUC `app.current_identita_id` + `app.ruolo_applicativo` + `app.soggetto_ruolo_id`

### 3.2 Quello che PR-B deve correggere

**3.2.1 Creazione identita portale — no creazione auth_user se email esistente**

Il flusso invito portale oggi crea sempre `auth_user + identita`. Post-cambio:

```python
def invita_portale(cliente_sr_id, email, ...):
    existing_user = AuthUser.objects.filter(email=email).first()
    if existing_user:
        # Caso: email gia' registrata (altro ruolo applicativo)
        # Crea SOLO l'identita CLIENTE_PORTALE sullo stesso auth_user
        identita = IdentitaDigitale.objects.create(
            auth_user=existing_user,
            soggetto_ruolo_id=cliente_sr_id,
            ruolo_applicativo='CLIENTE_PORTALE',
            attivo=False,  # attivata da link invito
        )
        # NON chiede password (gia' esistente), solo conferma attivazione
        token = TokenMonouso.issue(tipo='ATTIVAZIONE_PORTALE_CROSS', user=existing_user)
    else:
        # Caso: email nuova
        # Crea auth_user + identita come oggi
        ...
```

**3.2.2 Endpoint login discriminato per namespace**

Oggi probabilmente `/api/token/` unico. PR-B deve produrre 3 endpoint distinti:

* `POST /api/admin/token/` — cerca identita OPERATORE
* `POST /api/portale/token/` — cerca identita CLIENTE_PORTALE o FORNITORE_PORTALE
* `POST /api/shop/token/` — cerca identita SHOP_CUSTOMER (stub per PR-C)

Ciascuno:
1. Autentica `auth_user` con email+password
2. Cerca `identita_digitali(auth_user=X, ruolo_applicativo IN (...), attivo=true)`
3. Se trovata → emette JWT con claim custom `identita_id`
4. Se non trovata → 403 con codice `E_VESTE_NON_ATTIVA`

**3.2.3 JWT claim `identita_id`**

Override di `TokenObtainPairSerializer`:

```python
class MultiVesteTokenSerializer(AuditTokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user, identita):
        token = super().get_token(user)
        token['identita_id'] = identita.id
        token['ruolo_applicativo'] = identita.ruolo_applicativo
        return token
```

Il refresh token preserva i claim custom (SimpleJWT lo fa di default se settato
`UPDATE_LAST_LOGIN` + claim custom propagati).

**3.2.4 `JwtAuditAuthentication` — popolamento GUC a tripla**

Middleware/authentication class popola 3 GUC dal JWT:

```python
def authenticate(self, request):
    user, token = super().authenticate(request)
    identita_id = token.get('identita_id')
    if not identita_id:
        raise AuthenticationFailed('E_JWT_SENZA_IDENTITA')
    # Lettura identita per popolare i 3 GUC
    with connection.cursor() as c:
        c.execute("""
            SELECT id, ruolo_applicativo, soggetto_ruolo_id
            FROM anagrafiche.identita_digitali
            WHERE id = %s AND attivo = true
        """, [identita_id])
        row = c.fetchone()
        if not row:
            raise AuthenticationFailed('E_IDENTITA_NON_ATTIVA')
        c.execute("""
            SELECT set_config('app.current_identita_id', %s, false),
                   set_config('app.ruolo_applicativo', %s, false),
                   set_config('app.soggetto_ruolo_id', %s, false)
        """, [str(row[0]), row[1], str(row[2])])
    return user, token
```

**Invariante tutto-o-niente:** se uno dei 3 GUC non si popola, fail con 401.

**3.2.5 `/me/` endpoint**

Restituisce **solo** l'identita del JWT corrente, non tutte le identita
dell'user. Esempio payload:

```json
{
    "auth_user": {"id": 42, "email": "mario@rossi.it"},
    "identita": {
        "id": 108,
        "ruolo_applicativo": "CLIENTE_PORTALE",
        "soggetto_ruolo_id": 55
    },
    "permessi_area": {...},
    "azioni_processo": {...}
}
```

**3.2.6 Endpoint "Attiva accesso shop" (pannello profilo portale)**

```
POST /api/portale/profile/activate-shop/
    -> genera token ATTIVAZIONE_SHOP, invia email

GET /api/shop/activate/<token>/
    -> crea identita SHOP_CUSTOMER(attiva=true) su stesso auth_user
    -> ritorna redirect a /shop
```

Stub in PR-B, implementazione completa in PR-C.

**3.2.7 Pre-check email shop (per caso 8.2.2 guida)**

```
POST /api/shop/register/check-email/
    body: {"email": "..."}
    -> {"available": true}                -> flusso 8.2.1 standard
    -> {"available": false, "reason": "existing"}  -> redirect login+attiva
```

Stub in PR-B. Implementazione completa in PR-C.

### 3.3 Cosa PR-B puo' ignorare (rimanda a PR-C/PR-D)

* Endpoint shop registrazione `/api/shop/register/` — PR-C
* Schema `shop.ricevute` ORM models — PR-C
* Attivazione RLS (ENABLE/FORCE) — PR-C
* Admin UI "Abilita accesso portale" FE — PR-B cliente+fornitore
* Riscrittura completa corpo guide §7.4 — PR-D

### 3.4 Test BE da adeguare in PR-B

* Test che oggi assumono `auth_user.identita_digitali` OneToOne (vanno resi
  compatibili con ManyToMany logicamente, o con filter `ruolo_applicativo=X`)
* Test su `fn_is_super_admin` — passare solo OPERATORE user
* Test sync is_active — verificare OR su piu' identita

---

## 4. Contratti Frontend (PR-B)

### 4.1 Routing namespace

Il frontend mono-build ha gia' namespace `/portale/*` previsto. Va aggiunto:

* `/login` — pagina login unica, con switch canale (admin/portale/shop)
* `/portale/*` — UI clienti/fornitori portale
* `/shop/*` — stub redirect (PR-C)
* (admin resta su root senza namespace per compatibilita' esistente)

**Login unico con switch canale:**

```
┌─────────────────────────────┐
│  Login ZeroErp              │
│  [ Admin | Portale | Shop ] │
│                             │
│  Email:    [______________] │
│  Password: [______________] │
│                             │
│  [ Accedi ]                 │
└─────────────────────────────┘
```

Lo switch canale determina quale endpoint chiamare:
* Admin → `POST /api/admin/token/`
* Portale → `POST /api/portale/token/`
* Shop → `POST /api/shop/token/` (PR-C)

### 4.2 Store Pinia auth

Lo store salva `identita_id`, `ruolo_applicativo` dal `/me/`, e li usa per:

* Switch della navigazione (menu diverso per operatore vs portale)
* Abilitazione/disabilitazione azioni (composable `useActionPermission` gia' esistente)
* Routing guard (blocca accesso admin se `ruolo_applicativo IN (CLIENTE_PORTALE,...)`)

### 4.3 UI profilo — pulsante "Attiva accesso shop"

In PR-B aggiungere nella UI portale (`/portale/profile/`) un pulsante:

```
┌──────────────────────────────────────┐
│ Il tuo profilo                       │
│                                      │
│ [x] Accesso portale B2B (attivo)     │
│ [ ] Accesso shop                     │
│                                      │
│ [ Attiva accesso shop ]              │
└──────────────────────────────────────┘
```

Click → chiama `POST /api/portale/profile/activate-shop/`, mostra messaggio
"Ti abbiamo inviato un'email di conferma".

### 4.4 Gestione 403 "veste non attiva"

Se il login su un namespace restituisce 403 `E_VESTE_NON_ATTIVA`, mostrare:

> *"Non hai accesso a questo canale. Prova con un altro canale o contatta
> l'amministratore."*

Non rivelare quali vesti esistono (security — enumerazione).

### 4.5 Cosa PR-B puo' ignorare (rimanda a PR-C)

* UI shop (`/shop/*`)
* Form registrazione shop (`/shop/register`)
* Flusso attivazione shop via link (`/shop/activate/<token>`)

---

## 5. Sequenza di rilascio

1. **DB**: migration `20260420-01..50` su branch `dev/db-tid` → PR separata su
   `Tito-dev`, mergiata **prima** di BE/FE PR-B
2. **BE**: PR-B su `dev/backend-tid` aggiorna secondo §3, test verdi
3. **FE**: PR-B include frontend mono-build con §4, navigazione portale
4. **Merge congiunto** BE+FE su `Tito-dev`, smoke test e2e su stage
5. **PR-C separata** per shop (non include PR-B perche' shop e' canale autonomo
   con flussi propri)

---

## 6. Rischi identificati

| Rischio                                                             | Probabilita' | Mitigazione                                                                                                                                        |
| ------------------------------------------------------------------- | ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| JWT esistenti senza claim `identita_id` dopo deploy                 | Media        | Grace period: authentication class tollera JWT legacy per N giorni, popola identita da `auth_user_id` 1:1 (dato pre-cambio). Scade con il refresh. |
| Test BE che assumono 1:1 user↔identita falliscono                   | Alta         | Grep dei test prima di merge, aggiornare fixture                                                                                                   |
| Login operatore regredisce dopo split namespace                     | Alta         | Smoke test `/api/admin/token/` in CI                                                                                                               |
| RLS policy dormienti non coprono `shop.ricevute`                    | Bassa        | Policy creata dry-run nella stessa migration della tabella                                                                                         |
| `fn_is_super_admin(auth_user_id)` si confonde se user ha piu' vesti | Alta         | Aggiungere filtro `ruolo_applicativo='OPERATORE'` esplicito nella fn                                                                               |
| Popolamento GUC fallisce silenziosamente                            | Media        | Middleware verifica tripla popolata con `SHOW app.*`; fail 401 se incompleta                                                                       |

---

## 7. Checklist pre-merge DB

> Le checklist BE/FE sono consolidate nel §8 come task list per sub-PR
> (§8.3 PR-B1, §8.4 PR-B2, §8.5 PR-B3, §8.6 PR-B4) + changelog in §8.9.

### 7.1 DB

* [x] 11 migration numerate correttamente (`20260420-01..11`)
* [x] pgTAP aggiornato per nuovi vincoli (almeno 5 casi: unicita', immutabilita' canale, OR sync, ruolo-aware scope, fail-closed GUC)
* [x] Doc manual aggiornata per `identita_digitali`, `billing_account`, `shop.ricevute`, `fn_scope_ba_ownership`, `fn_sync_auth_user_is_active`
* [x] WIP `sviluppo-multi-face-auth.md` aggiornato con stato fasi

Aggiunte
2 codici errore aggiunti a messaggi_errore.csv (E_CANALE_ORIGINE_IMMUTABILE 385, E_SHOP_RICEVUTA_BA_CANALE_INVALIDO 386)
Guide aggiornate (potrebbero essere in §7.2/§7.3, ma oggi non c'è una voce dedicata):
architettura-multi-face-auth v2.0
architettura-permessi-e-autorizzazioni §6/§9.2/§10/§13
Nuova contratto-guc-app.md (PRD GUC per BE — dovrebbe essere in §7.2 checklist BE perché è il contratto che il BE implementa)
pgTAP aggiornato PR1.5 test-rls-policies-structure.sql (test 4 e 28 post-split)
Mappa concentrica aggiornata (non la terrei in §7.1, più logica come cross-tutte)

---

## 8. Piano sprint BE/FE — decisioni operative (20-04-2026)

> Aggiunto dopo la chiusura del piano DB (migration `20260420-01..11`
> mergiate su `Tito-dev`). Traduce §3 e §4 in un'esecuzione ordinata
> e spezzata in sub-PR per limitare il blast radius.

### 8.1 Decisioni Q1–Q4 chiuse

| Domanda                        | Scelta                                                              | Motivo                                                                                  |
| ------------------------------ | ------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| **Q1 — Grace period JWT**      | 0 giorni                                                            | Ambiente dev, nessun costo di rollover; codice pulito da subito, no rami compat.        |
| **Q2 — Rename endpoint login** | `/api/v1/auth/token/` → `/api/v1/admin/token/` (breaking, no alias) | Coerenza con `/portale/` e `/shop/`, debito tecnico zero.                               |
| **Q3 — Ordine BE/FE**          | Sequenziale (BE prima, FE dopo)                                     | Solo developer (Tid) — meno context switching, contract BE stabile prima di toccare UI. |
| **Q4 — Spezzare PR-B**         | Sì, 4 sub-PR                                                        | Blast radius contenuto, rollback chirurgico, smoke isolato per feature.                 |

### 8.2 Prerequisito soddisfatto

DB migration `20260420-01..11` applicate e mergiate su `Tito-dev`. Il
backend puo' iniziare lo sviluppo del nuovo modello 1:N.

### 8.3 PR-B1 — BE foundation auth multi-veste (breaking)

**Obiettivo:** adeguare l'infrastruttura di autenticazione al modello 1:N
user↔identita. Niente feature business qui — solo fondamenta.

**File da toccare:**

* `backend/zeroerp_backend/urls.py` — rename `auth/token/` → `admin/token/`, aggiunta `portale/token/` e `shop/token/`
* `backend/apps/core/api/auth_views.py` — split `AuditTokenObtainPairView` in 3 subclass namespace-discriminate; serializer `MultiVesteTokenSerializer` con claim `identita_id`
* `backend/apps/core/api/jwt_audit_authentication.py` — legge `identita_id` dal JWT, popola 3 GUC atomicamente, fail 401 su tripla incoerente
* `backend/apps/core/api/me_view.py` — ritorna solo identita del JWT corrente (filtra per `identita_id`)
* `backend/apps/core/services/permissions_resolver.py` — `is_super_admin` filtra su `ruolo_applicativo='OPERATORE'`, `get_ruolo_applicativo` legge da GUC (gia' fatto Stage B), verifica coerenza
* `backend/apps/amm_software/db/amm_software_repository.py` — query che filtrano identita: aggiungere `ruolo_applicativo='OPERATORE'` esplicito
* `backend/apps/portale/db/portale_repository.py` — verifica che `find_identita_portale` filtri gia' per ruolo (fatto)
* Test: codemod su ~15 test che mockano `auth_user.identita` 1:1 → filter `ruolo_applicativo=X`

**Task list:**

* [x] 8.3.1 Rename `/api/v1/auth/token/` → `/api/v1/admin/token/` + update smoke + grep FE (breaking, zero alias)
* [x] 8.3.2 Nuovo serializer `MultiVesteTokenSerializer`: post-autenticazione cerca identita per `ruolo_applicativo` del namespace, aggiunge claim `identita_id` + `ruolo_applicativo` al JWT
* [x] 8.3.3 Nuove view `AdminTokenView`, `PortaleTokenView`, `ShopTokenView` (stub): filtrano identita per `ruolo_applicativo IN (...)`, 403 `E_VESTE_NON_ATTIVA` se assente
* [x] 8.3.4 `JwtAuditAuthentication.authenticate()`: legge `identita_id` dal token, verifica identita attiva, popola 3 GUC in singola query CTE, fail 401 su step mancante
* [x] 8.3.5 Refresh token preserva claim custom (verificare SimpleJWT config).
  Sub-task: aggiungere guard opzionale sulla view refresh che verifica che
  il `ruolo_applicativo` nel refresh token sia coerente con il namespace
  del path (oggi tutte e 3 le route refresh puntano allo stesso
  `AuditTokenRefreshView` senza check — non c'e' escalation perche' il
  claim veste viene dal token stesso, ma e' rumore semantico da chiudere).
* [x] 8.3.6 `/me/` restituisce solo identita del JWT corrente
* [x] 8.3.7 `PermissionResolver.is_super_admin` aggiunge filtro `ruolo_applicativo='OPERATORE'` in query
* [x] 8.3.8 Grep test `identita_digitali` — aggiornare assumption 1:1
* [ ] 8.3.9 Run `./manage-test.sh` verde (1533 baseline + aggiornamenti mirati)

**Gate uscita:**

* Login admin con tid funziona via `/api/v1/admin/token/`
* JWT decodificato contiene `identita_id` + `ruolo_applicativo`
* `/me/` risponde con una sola identita
* Grep `auth_user\.identita[^_]` = 0 match nei test attivi

**Stima:** 1-2 giornate. Commit target: `pr-b1-be-foundation-auth`.

### 8.4 PR-B2 — BE feature invito portale cross-veste + stub shop

**Obiettivo:** aggiornare il servizio invito portale al nuovo modello 1:N
e preparare gli stub endpoint shop che verranno riempiti in PR-C.

**File da toccare:**

* `backend/apps/portale/services/invito_portale_service.py` — branching email nuova / esistente, token types
* `backend/apps/portale/db/portale_repository.py` — helper per creazione identita `attivo=false`
* `backend/apps/portale/api/views.py` — endpoint attivazione supporta 2 token types
* `backend/apps/portale/api/urls.py` — 3 nuovi stub endpoint
* `backend/apps/core/services/error_policies.py` — codici errore nuovi: `E_VESTE_NON_ATTIVA`, `E_JWT_SENZA_IDENTITA`, `E_IDENTITA_NON_ATTIVA`

**Task list:**

* [ ] 8.4.1 `InvitoPortaleService._ensure_auth_user` distingue email nuova (crea user + identita attivo=true + token `INVITO_PORTALE`) da esistente (SOLO identita attivo=false + token `ATTIVAZIONE_PORTALE_CROSS`, niente password).
  Sub-task debito 1:1 (emerso da §8.3.8): quando si tocca il service,
  aggiornare anche `AuthRepository.get_deve_cambiare_password`,
  `set_invito_inviato_at`, `set_deve_cambiare_password` — oggi fanno
  query `WHERE auth_user_id=%s AND attivo=true LIMIT 1` (assumption
  1:1) e col modello 1:N restituiscono/aggiornano un'identita
  arbitraria. Non critico (flag UX), ma va aggiunto parametro
  `identita_id` per puntare la veste specifica del flusso corrente
  (pattern gia' usato in `set_jwt_gucs` §8.3.4 e
  `get_identita_dettaglio` §8.3.6).
* [ ] 8.4.2 Endpoint `AttivazionePortaleView` gestisce 2 token types: `INVITO_PORTALE` (setta password + attiva) vs `ATTIVAZIONE_PORTALE_CROSS` (solo attiva identita, no password)
* [ ] 8.4.3 Stub `POST /api/v1/portale/profile/activate-shop/` (restituisce 501 Not Implemented con hint PR-C)
* [ ] 8.4.4 Stub `GET /api/v1/shop/activate/<token>/` (501)
* [ ] 8.4.5 Stub `POST /api/v1/shop/register/check-email/` (501)
* [ ] 8.4.6 Registrazione errori `E_VESTE_NON_ATTIVA`, `E_JWT_SENZA_IDENTITA`, `E_IDENTITA_NON_ATTIVA` in `error_policies.py`
* [ ] 8.4.7 Test: caso email esistente (no auth_user nuovo, identita `attivo=false`, token CROSS), caso email nuova (invariato), caso attivazione cross

**Gate uscita:**

* Invitare a portale un email gia' presente come operatore: crea 2a identita `CLIENTE_PORTALE` `attivo=false` + token CROSS
* Attivazione con token CROSS attiva identita senza toccare password
* Curl `POST /api/v1/portale/profile/activate-shop/` → 501 coerente

**Stima:** 1 giornata. Commit target: `pr-b2-be-invito-cross-stub-shop`.

### 8.5 PR-B3 — FE foundation login + store + guard

**Obiettivo:** UI pronta a gestire il modello 1:N — login per canale,
store Pinia con identita, router guard per namespace.

**File da toccare:**

* `frontend/src/core/views/LoginView.vue` — aggiunta switch canale (radio 3 opzioni)
* `frontend/src/stores/auth.js` — salva `identita_id` + `ruolo_applicativo` dal `/me/`; `login()` accetta canale
* `frontend/src/core/api.js` — endpoint chiamato dipende dal canale
* `frontend/src/router/index.js` — guard `/portale/*` rifiuta OPERATORE, root admin rifiuta non-OPERATORE, stub routing `/shop/*`
* `frontend/src/locales/it.json` — chiavi login switch, errore veste non attiva

**Task list:**

* [ ] 8.5.1 `LoginView`: radio button Admin / Portale / Shop (default Admin per retrocompat operatore)
* [ ] 8.5.2 Store `auth.login(username, password, canale)` chiama endpoint corretto (`/admin/token/` | `/portale/token/` | `/shop/token/`)
* [ ] 8.5.3 Store salva `identita_id` + `ruolo_applicativo` (gia' fatto Stage B per ruolo_applicativo, aggiungi identita_id)
* [ ] 8.5.4 Router guard nuovo: se `/portale/*` e `ruolo_applicativo !== 'CLIENTE_PORTALE' && !== 'FORNITORE_PORTALE'` → redirect `/forbidden`
* [ ] 8.5.5 Router guard: se admin root e `ruolo_applicativo !== 'OPERATORE'` → redirect `/forbidden` (grace path: /portale per clienti)
* [ ] 8.5.6 Stub route `/shop/*` → pagina placeholder "Shop in arrivo"
* [ ] 8.5.7 Gestione errore 403 `E_VESTE_NON_ATTIVA`: messaggio generico "Non hai accesso a questo canale" (no enumeration)
* [ ] 8.5.8 vite build OK + smoke login admin via UI

**Gate uscita:**

* Login admin funziona via switch canale Admin
* Login portale funziona (con utente portale creato in PR-B2)
* Un portale user che tenta `/admin/...` viene redirezzato
* 403 `E_VESTE_NON_ATTIVA` mostra messaggio generico

**Stima:** 1-2 giornate. Commit target: `pr-b3-fe-login-multi-canale`.

### 8.6 PR-B4 — FE pulsante activate-shop + stub routing shop

**Obiettivo:** completare l'UI PR-B con il pulsante "Attiva accesso shop"
nel profilo portale + stub routing per canale shop.

**File da toccare:**

* `frontend/src/portale/views/ProfileView.vue` — nuova view profilo portale
* `frontend/src/portale/components/AttivaAccessoShopButton.vue` — componente pulsante
* `frontend/src/portale/api/portaleProfileApi.js` — chiamata `activate-shop`
* `frontend/src/router/index.js` — route `/portale/profile`
* `frontend/src/locales/it.json` — chiavi `portale.profile.*`

**Task list:**

* [ ] 8.6.1 Crea `ProfileView` portale con card "Il tuo profilo" + 2 toggle stato (portale attivo, shop non ancora)
* [ ] 8.6.2 Pulsante "Attiva accesso shop" chiama `POST /portale/profile/activate-shop/` (oggi 501), gestisce errore con messaggio "funzione in arrivo"
* [ ] 8.6.3 Route `/portale/profile` registrata, accessibile solo da portale user
* [ ] 8.6.4 Stub pagina `/shop/attivazione/:token` (vuoto, dice "Attivazione shop — PR-C")
* [ ] 8.6.5 vite build OK + smoke manuale (pulsante cliccabile, 501 gestito)

**Gate uscita PR-B (finale):**

* Checklist §7 completa
* Smoke e2e: invito portale cross-veste funziona (admin invita email gia' operatore → email con link → attivazione SENZA cambio password → login portale OK)
* Tutti i test BE verdi
* Vite build verde

**Stima:** 0.5 giornate. Commit target: `pr-b4-fe-profilo-shop-stub`.

### 8.7 Dipendenze tra sub-PR

```text
DB 20260420-01..11 (merged)
       │
       ▼
  PR-B1 BE foundation ──────┐
       │                    │
       ▼                    │
  PR-B2 BE features ────────┤
       │                    │ (FE non parte senza contract BE stabile)
       ▼                    │
  PR-B3 FE foundation ◄─────┘
       │
       ▼
  PR-B4 FE features
       │
       ▼
  Gate finale (§7) → merge PR-B su Tito-dev
       │
       ▼
  PR-C Shop MVP (fuori scope PR-B)
```

### 8.8 Rischi specifici sprint

| Rischio                                                            | Mitigazione                                                                           |
| ------------------------------------------------------------------ | ------------------------------------------------------------------------------------- |
| Rename `/auth/token/` → `/admin/token/` rompe smoke bash esistenti | Grep `backend/scripts/` + aggiornare tutti gli smoke-test-*.sh prima del commit PR-B1 |
| Test Django fixture con identita 1:1 rompono in blocco             | PR-B1 8.3.8 codemod sistematico, non lasciare test rossi tra sub-PR                   |
| FE store `auth.js` post-rename perde sessioni correnti             | Accettabile: dev-only, tutti fanno logout/login dopo merge PR-B1                      |
| Stub 501 portale/shop confonde lo smoke e2e                        | Documentare chiaramente in `api.md` quali endpoint sono ancora in PR-C                |

### 8.9 Changelog sprint (da aggiornare incrementalmente)

* **[ ] PR-B1** — BE foundation (commit `...`, data `...`)
* **[ ] PR-B2** — BE features invito + stub shop (commit `...`, data `...`)
* **[ ] PR-B3** — FE login multi-canale (commit `...`, data `...`)
* **[ ] PR-B4** — FE profilo + stub routing (commit `...`, data `...`)

---

{% include-markdown "signature-core.md" %}
