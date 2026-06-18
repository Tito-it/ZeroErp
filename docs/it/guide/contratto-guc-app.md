# Contratto GUC `app.*` — PRD per Backend

> **Destinatari:** backend Django (authentication class, middleware), autori di funzioni DB e policy RLS
>
> **Prerequisiti:** [Architettura Multi-Face Auth v2.0](/guide/architettura-multi-face-auth), [Architettura Permessi e Autorizzazioni §6.4](/guide/architettura-permessi-e-autorizzazioni#64-propagazione-identita-al-db-jwt-gu-c)
>
> **Stato:** contratto normativo — 20-04-2026

---

## 1. Cosa sono i GUC `app.*`

I **GUC** (grand unified configuration) sono parametri di sessione PostgreSQL
settati via `SET LOCAL` all'interno di una transazione. ZeroErp usa i GUC
nel namespace `app.*` per propagare l'identita della sessione HTTP fino
al database, dove policy RLS, trigger e funzioni scope possono leggerli
e applicare enforcement fail-closed.

Il backend Django scrive i GUC dentro la authentication class (ogni
request autenticata) — il DB li legge via `current_setting('app.xxx', true)`.

**Natura del contratto:**

* I GUC sono **locali alla transazione**: `SET LOCAL` li scopera automaticamente
  a fine commit/rollback. Nessuna pool pollution.
* I GUC sono **obbligatori per ogni request autenticata**: senza GUC il DB e' in
  stato "identita sconosciuta" e la RLS fail-closed.
* I GUC sono **propagati verso il basso**: il BE li scrive, il DB li legge. Mai
  il contrario (non esiste "DB che chiede al BE chi e' l'utente").
* I GUC **non sono storage**: non persistono, non sono audit log, non sono
  cache. Sono un canale di sessione.

---

## 2. I 5 GUC

Cinque GUC in due gruppi: identita multi-face (tripla obbligatoria) + legacy
(compatibilita').

### 2.1 Tripla multi-face auth (obbligatoria post refactor)

| GUC | Tipo valore | Sorgente | Esempio |
| --- | --- | --- | --- |
| `app.current_identita_id` | `bigint` | Claim JWT `identita_id` | `108` |
| `app.ruolo_applicativo` | `text` (valore ENUM) | `identita_digitali.ruolo_applicativo` | `CLIENTE_PORTALE` |
| `app.soggetto_ruolo_id` | `bigint` | `identita_digitali.soggetto_ruolo_id` | `55` |

**Invariante tutto-o-niente:** i 3 GUC sono popolati insieme oppure nessuno
di loro e' popolato. Non e' mai lecito avere `current_identita_id` settato
e `ruolo_applicativo` vuoto.

### 2.2 GUC legacy (invariati, retrocompatibilita')

| GUC | Tipo valore | Sorgente | Uso |
| --- | --- | --- | --- |
| `app.current_user_id` | `integer` | `auth_user.id` | Trigger audit `user_insert`/`user_update` |
| `app.jwt_user` | `text` | `auth_user.username` | Audit log legacy |

Questi due esistono da prima del refactor multi-face. Restano in uso dai
trigger audit generici; non sono coinvolti nelle policy RLS.

---

## 3. Chi popola cosa, quando

**Sorgente unica:** l'authentication class `JwtAuditAuthentication`
(`backend/apps/core/authentication.py`). Nessun altro codice backend
deve settare direttamente i GUC. Nessun service, nessun middleware, nessuna
view.

**Sequenza per ogni request autenticata:**

1. DRF riceve la request con header `Authorization: Bearer <jwt>`
2. `JwtAuditAuthentication.authenticate()` valida il JWT
3. Legge claim `identita_id` dal JWT
4. Interroga `anagrafiche.identita_digitali` per ottenere
   `(ruolo_applicativo, soggetto_ruolo_id, attivo)`
5. Se identita non attiva → `AuthenticationFailed('E_IDENTITA_NON_ATTIVA')` (401)
6. Esegue **un'unica query** che setta tutti i GUC in transazione:

```sql
SELECT
    set_config('app.current_user_id',      %s, false),
    set_config('app.current_identita_id',  %s, false),
    set_config('app.ruolo_applicativo',    %s, false),
    set_config('app.soggetto_ruolo_id',    %s, false),
    set_config('app.jwt_user',             %s, false);
```

Parametri positional: `auth_user.id`, `identita.id`, `identita.ruolo_applicativo`,
`identita.soggetto_ruolo_id`, `auth_user.username`. Il flag `false` del
`set_config` indica `is_local = false` — ma in pratica Django wrappa in
transazione atomic, quindi la vita del GUC e' quella della transazione.

> **Nota implementativa:** se la request non e' atomic by default (es. API non
> write), e' responsabilita' del middleware `ATOMIC_REQUESTS` (o decorator
> `@transaction.atomic` sulla view) garantire il confinamento transazionale.
> Altrimenti usare `set_config(..., true)` con `is_local = true` (piu'
> sicuro ma richiede essere dentro una transazione).

**Request anonime.** Se non c'e' JWT valido (endpoint pubblici dello shop,
registrazione), i GUC **non vengono settati**. Il DB vede valori vuoti,
`fn_current_identita_context()` restituisce NULL-tuple, le policy RLS
fail-closed.

**Processi di sistema headless (canale batch).** I management command / cron che
operano via un ruolo `zeroerp_batch_<job>` (`BYPASSRLS` — vedi
[provisioning-db-roles](/dev/backend/provisioning-db-roles)) **non settano i GUC
d'identita'** (`current_identita_id` / `ruolo_applicativo` / `soggetto_ruolo_id`):
non hanno una veste applicativa e la RLS e' bypassata **a livello di ruolo**, non via
GUC. Possono settare il solo `app.jwt_user` (es. `BATCH_FATTURAZIONE`) per dare un
attore riconoscibile ai trigger audit. Questo canale e' riservato ai processi headless:
**mai** usarlo per servire richieste web (guard fail-open statico+runtime, vedi
`dev/work-done/brief-db-contesto-sistema-batch-fatturazione-rls.md` §5.6).

---

## 4. Chi legge cosa

### 4.1 Policy RLS

Ogni policy RLS legge i GUC tramite `current_setting(..., true)`. Il
secondo parametro `true` evita eccezione se il GUC non e' settato:
restituisce stringa vuota. Pattern standard:

```sql
CREATE POLICY rls_fatture_ba_ownership ON vendite.fatture
    FOR SELECT
    USING (
        current_setting('app.ruolo_applicativo', true) IN ('CLIENTE_PORTALE', 'SHOP_CUSTOMER')
        AND script.fn_scope_ba_ownership(
                NULLIF(current_setting('app.current_identita_id', true), '')::bigint,
                billing_account_id
            )
    );
```

**Pattern di conversione sicura:**

```sql
-- Da stringa vuota a NULL, poi cast tipizzato. NULL fa fail-closed.
NULLIF(current_setting('app.current_identita_id', true), '')::bigint
```

### 4.2 Helper `fn_current_identita_context`

Funzione DB `script.fn_current_identita_context()` leggibile da qualunque
funzione/policy che serve la tripla. Restituisce una tupla `(identita_id,
ruolo_applicativo, soggetto_ruolo_id)` oppure `NULL-tuple` se **anche uno
solo** dei 3 GUC non e' popolato o non e' castabile.

**Uso tipico:**

```sql
SELECT identita_id, ruolo_applicativo, soggetto_ruolo_id
FROM script.fn_current_identita_context();
-- Se identita_id IS NULL, l'intera tripla e' considerata non popolata
```

### 4.3 Trigger audit

I trigger generici `script.trgfn_audit_data_user_generic()` continuano a
leggere `app.jwt_user` come fanno oggi. Non sono stati modificati dal
refactor multi-face.

---

## 5. Fail-closed: cosa succede se i GUC mancano

### 5.1 Caso: identita non popolata

**Sintomo:** `current_setting('app.current_identita_id', true) = ''`

**Effetto:**

* `fn_scope_ba_ownership(NULL, ...)` → `false` (short-circuit su identita inesistente)
* `fn_scope_cliente_ownership(NULL, ...)` → `false`
* `fn_scope_ef_whitelist(NULL, ...)` → `false`
* Policy RLS: `USING` clause falsa → **nessuna riga visibile**
* Tabelle sotto RLS FORCE: `SELECT` ritorna 0 righe, `INSERT/UPDATE/DELETE` falliscono

Risultato: l'utente non vede nulla, non puo' scrivere nulla. **Fail-closed
corretto.**

### 5.2 Caso: tripla parzialmente popolata

**Sintomo:** `current_identita_id = '108'` ma `ruolo_applicativo = ''`

**Effetto:**

* Le policy RLS che gate su `ruolo_applicativo` (es. `IN ('CLIENTE_PORTALE',...)`)
  falliscono il gate → nessuna riga visibile
* Le policy che leggono solo `current_identita_id` potrebbero passare: **questo
  e' un bug potenziale** se la policy e' mal scritta
* `fn_current_identita_context()` restituisce NULL-tuple se anche una sola
  componente e' mancante

**Responsabilita' BE:** l'authentication class **non deve mai** settare
parzialmente la tripla. Se la lettura di `identita_digitali` fallisce per
qualunque motivo, nessun GUC del gruppo multi-face viene settato.

### 5.3 Caso: identita disattivata a mezza sessione

**Sintomo:** il JWT e' ancora valido ma `identita_digitali.attivo = false`
(es. admin ha disattivato la veste durante la sessione).

**Effetto desiderato:** la request successiva deve essere respinta.

**Meccanismo:** l'authentication class esegue il check `attivo = true`
**ad ogni request**, non solo al login. Se l'identita e' disattivata →
`AuthenticationFailed('E_IDENTITA_NON_ATTIVA')` (401). Il client deve
reloggare.

> **Importante:** non si puo' affidarsi a `auth_user.is_active = true` per
> questo check. `is_active` e' OR sulle identita dell'user (vedi
> [Multi-Face Auth §9](/guide/architettura-multi-face-auth#9-sync-auth_user-is_active-generalizzata)):
> l'user potrebbe essere globalmente attivo ma con la veste specifica
> disattivata.

---

## 6. Invariante tutto-o-niente: implementazione difensiva

### 6.1 Lato BE

```python
# apps/core/authentication.py (concettuale)
class JwtAuditAuthentication(AuditJWTAuthentication):
    def authenticate(self, request):
        user, token = super().authenticate(request)
        identita_id = token.get('identita_id')

        if not identita_id:
            # Grace window per JWT legacy pre-multi-face
            identita_id = self._fallback_legacy_identita(user)
            if not identita_id:
                raise AuthenticationFailed('E_JWT_SENZA_IDENTITA')

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT ruolo_applicativo, soggetto_ruolo_id
                FROM anagrafiche.identita_digitali
                WHERE id = %s AND attivo = true
            """, [identita_id])
            row = cursor.fetchone()
            if not row:
                raise AuthenticationFailed('E_IDENTITA_NON_ATTIVA')

            ruolo_applicativo, sr_id = row

            # SET atomico della tripla + legacy: tutto o niente
            cursor.execute("""
                SELECT
                    set_config('app.current_user_id',     %s, false),
                    set_config('app.current_identita_id', %s, false),
                    set_config('app.ruolo_applicativo',   %s, false),
                    set_config('app.soggetto_ruolo_id',   %s, false),
                    set_config('app.jwt_user',            %s, false)
            """, [
                str(user.id), str(identita_id),
                ruolo_applicativo, str(sr_id),
                user.username,
            ])

        return user, token
```

**Caratteristiche critiche:**

* Fail-fast su ogni step (401 esplicito, no fallback silenzioso)
* `SET` atomico in un'unica query: il DB non puo' essere in stato parziale
* Nessuna cattura di eccezione generica che masca i problemi

### 6.2 Lato DB

```sql
-- Helper fail-closed per funzioni/policy che serve la tripla coerente
CREATE OR REPLACE FUNCTION script.fn_current_identita_context()
RETURNS TABLE (
    identita_id bigint,
    ruolo_applicativo text,
    soggetto_ruolo_id bigint
)
LANGUAGE sql STABLE AS $$
    WITH raw AS (
        SELECT
            NULLIF(current_setting('app.current_identita_id', true), '')::bigint AS iid,
            NULLIF(current_setting('app.ruolo_applicativo',   true), '')         AS rap,
            NULLIF(current_setting('app.soggetto_ruolo_id',   true), '')::bigint AS sri
    )
    SELECT
        CASE WHEN iid IS NULL OR rap IS NULL OR sri IS NULL THEN NULL ELSE iid END,
        CASE WHEN iid IS NULL OR rap IS NULL OR sri IS NULL THEN NULL ELSE rap END,
        CASE WHEN iid IS NULL OR rap IS NULL OR sri IS NULL THEN NULL ELSE sri END
    FROM raw;
$$;
```

**Comportamento fail-closed:** se anche uno solo dei 3 e' NULL, la tupla
restituita e' `(NULL, NULL, NULL)`. Chi la consuma sa che la tripla non
e' utilizzabile.

---

## 7. Consumatori noti

### 7.1 Funzioni scope (`script`)

* `fn_scope_ef_whitelist(identita_id, emittente_sr_id)` — legge `current_identita_id` via policy argument, non il GUC direttamente
* `fn_scope_ba_ownership(identita_id, billing_account_id)` — idem
* `fn_scope_cliente_ownership(identita_id, cliente_sr_id)` — idem
* `fn_scope_fornitore_ownership(identita_id, fornitore_sr_id)` — idem
* `fn_scope_ba_ownership_via_fattura(identita_id, fattura_id)` — idem

Le scope function ricevono `identita_id` come parametro, non leggono GUC. E'
la **policy RLS** che passa il GUC alla scope function via
`current_setting(...)::bigint`.

### 7.2 Helper resolver (`script`)

* `fn_get_profili_accesso_applicabili(auth_user_id)` — riceve user_id esplicito
* `fn_is_super_admin(auth_user_id)` — idem
* `fn_get_uo_id_for_user(auth_user_id)` — idem

Questi **non leggono GUC**: ricevono parametri espliciti dal resolver Python.

### 7.3 Policy RLS

Ogni CREATE POLICY ha una USING clause che legge i GUC direttamente con il
pattern `NULLIF(current_setting(..., true), '')::tipo`. Vedi [Multi-Face Auth §6.4](/guide/architettura-multi-face-auth#64-tracciabilita-canale-sui-dati-transazionali)
per l'elenco delle 7+ policy dormienti/attive.

### 7.4 Trigger audit

* `script.trgfn_audit_data_user_generic()` — legge `app.jwt_user` per popolare `user_insert`/`user_update`

---

## 8. Troubleshooting

### 8.1 "L'utente vede 0 righe in lista fatture, ma dovrebbe vederne N"

Sequenza di verifica:

1. Verifica JWT del client contiene claim `identita_id` (debugger browser, tab
   Network, decode JWT)
2. Verifica `app.current_identita_id` sul DB: apri connessione con lo stesso
   user Django, `SELECT current_setting('app.current_identita_id', true)` —
   deve restituire un bigint
3. Verifica identita attiva: `SELECT * FROM anagrafiche.identita_digitali
   WHERE id = <identita_id>` — `attivo` deve essere `true`
4. Verifica policy RLS: `SELECT * FROM pg_policies WHERE tablename = 'fatture'` —
   policy con USING clause coerente
5. Verifica che le RLS siano ENABLE: `SELECT relrowsecurity, relforcerowsecurity
   FROM pg_class WHERE relname = 'fatture'`. Dal giugno 2026 le tabelle dello
   scope emittente OPERATORI (fatture/scadenze/lotti/ordini/preventivi/contratti/
   offerte/documenti_generati/pratiche/billing_account) hanno
   `relrowsecurity = true` (Ondata 1+2; `FORCE` non usato → owner/BYPASSRLS
   esenti). Se su quelle tabelle è `false`, la RLS **non** è attiva lì (problema
   di migrazione/auto-guarigione del framework `automazione_overlap`/runner). Le
   tabelle delle branch **portale/shop** restano invece `false` (dry-run). Vedi
   `dev/work-done/analisi-attivazione-rls-operatori.md`.

### 8.2 "Login riuscito ma prima request autenticata restituisce 401"

Il grace JWT legacy non sta funzionando. Verificare:

* `authenticate()` gestisce token senza claim `identita_id` con fallback
* L'user ha almeno un'identita attiva da mappare

### 8.3 "Trigger audit salva NULL su `user_insert`"

`app.jwt_user` non settato. Verificare che la request sia passata per
`JwtAuditAuthentication` e non per path anonimo. Gli INSERT da management
command o da shell Django non hanno request → `app.jwt_user` vuoto → il
trigger usa default (`CURRENT_USER` PostgreSQL = ruolo DB connesso).

---

## 9. Evoluzioni future

* **GUC `app.tenant_id`** — se ZeroErp diventa multi-tenant, un sesto GUC per
  discriminare il tenant corrente. Si aggiunge alla tripla senza romperla.
* **Shortcut `app.is_super_admin`** — oggi il check richiede
  `fn_is_super_admin(auth_user_id)` query. Per performance si potrebbe
  propagare un boolean precomputato al login. Non urgente — la fn e' STABLE
  e inlineable.
* **Audit `app.request_id`** — gia' presente ma gestito dal middleware
  `RequestLogMiddleware`, non dall'authentication class. Potrebbe essere
  unificato sotto un unico contratto GUC.

---

{% include-markdown "signature-core.md" %}
