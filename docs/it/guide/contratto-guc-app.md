# Guida — Contratto GUC `app.*`

> **Ultimo aggiornamento**: 25 ottobre 2026
>
> **Destinatari**: backend Django (authentication class, middleware), autori di funzioni DB e policy RLS
>
> **Vedi anche** — funzioni e trigger DB:
>
> * [script.fn_current_identita_context](/dbzero/script/funzioni/fn_current_identita_context) — la tripla letta dal DB in un colpo solo, o `NULL` se incompleta
> * [script.fn_scope_ba_ownership](/dbzero/script/funzioni/fn_scope_ba_ownership) · [script.fn_scope_ef_whitelist](/dbzero/script/funzioni/fn_scope_ef_whitelist) · [script.fn_check_user_emittente_scope](/dbzero/script/funzioni/fn_check_user_emittente_scope) — gli scope che le policy interrogano
> * [script.trgfn_audit_data_user_generic](/dbzero/script/funzioni/trgfn_audit_data_user_generic) — il trigger audit che firma le righe con questi GUC
>
> **Vedi anche** — guide correlate:
>
> * [Architettura Permessi e Autorizzazioni §6.4](/guide/architettura-permessi-e-autorizzazioni#64-propagazione-identita-al-db-jwt-guc) — la propagazione dell'identità al DB
> * [Architettura Multi-Face Auth](/guide/architettura-multi-face-auth) — le identità digitali, le vesti e il claim `identita_id`
> * [Risorse umane e accessi](/guide/risorse-umane-e-accessi) — la sync di `auth_user.is_active`

---

## 1. Cosa sono i GUC `app.*`

I **GUC** (grand unified configuration) sono parametri di sessione PostgreSQL. Zero ERP usa
i GUC nel namespace `app.*` per propagare l'identità della sessione HTTP fino al database,
dove policy RLS, trigger e funzioni di scope li leggono con
`current_setting('app.xxx', true)` e applicano l'enforcement fail-closed.

Il backend Django li scrive nella authentication class, a ogni richiesta autenticata.

**Natura del contratto:**

* I GUC sono **di sessione, non di transazione.** `set_config(nome, valore, false)` — cioè
  `is_local = false` — li lega alla **connessione**, non al commit. È voluto, e c'è un
  lettore che dipende da questo: la riga di `dbops.request_log` si scrive **dopo** la
  risposta, quando la transazione di lavoro ha già chiuso, e prende l'emittente proprio da
  `app.current_emittente_id`. Con lo scope di transazione sarebbe già sparita.
* ⛔ **Proprio per questo c'è un reset a inizio richiesta.** Una GUC di sessione vive sulla
  connessione del pool: senza reset, la richiesta successiva — di un **altro** utente —
  erediterebbe l'identità (e l'eventuale impersonazione) di quella prima. Chi protegge dal
  riuso della connessione **non è il commit**: è il middleware, e se il reset fallisce la
  richiesta viene rifiutata (500, fail-closed).
* I GUC sono **obbligatori per ogni richiesta autenticata**: senza GUC il DB è in stato
  «identità sconosciuta» e la RLS fail-closed.
* I GUC sono **propagati verso il basso**: li scrive il BE, li legge il DB. Mai il contrario
  — non esiste «il DB che chiede al BE chi è l'utente».
* I GUC **non sono storage**: non persistono, non sono audit log, non sono cache. Sono un
  canale di sessione.

> ⚠️ Nel namespace `app.*` **convivono altre GUC che non fanno parte di questo contratto**:
> le scrive una funzione o un processo per il tempo della propria transazione, come parametri
> di contesto (`app.cessazione_automatica`, `app.registrazione_tardiva_riga_id`). Non sono
> identità e non vanno confuse con quelle della tabella qui sotto.

---

## 2. I 6 GUC d'identità

L'elenco canonico è **una tupla nel codice**, non questo documento:
`JWT_IDENTITY_GUCS` in `backend/apps/core/api/jwt_audit_authentication.py`. Da lì si deriva
il reset (`JWT_GUC_RESET_SQL`), e lì si aggiunge o si toglie una GUC.

| GUC                        | Tipo valore          | Da dove viene                                                                     | Chi lo legge                                              |
| -------------------------- | -------------------- | --------------------------------------------------------------------------------- | --------------------------------------------------------- |
| `app.current_identita_id`  | `bigint`             | claim JWT `identita_id`, validato su `identita_digitali`                          | policy RLS, funzioni di scope                             |
| `app.ruolo_applicativo`    | `text` (valore ENUM) | `identita_digitali.ruolo_applicativo`                                             | policy RLS (il gate sulla veste)                          |
| `app.soggetto_ruolo_id`    | `bigint`             | `identita_digitali.soggetto_ruolo_id`                                             | policy RLS                                                |
| `app.current_emittente_id` | `bigint`             | claim dell'emittente attivo (`emittenti_fiscali.id`), rivalidato a ogni richiesta | policy RLS dello **scope emittente**, `dbops.request_log` |
| `app.current_user_id`      | `integer`            | `auth_user.id`                                                                    | trigger audit                                             |
| `app.jwt_user`             | `text`               | `auth_user.username`                                                              | trigger audit                                             |

**La tripla** (`current_identita_id`, `ruolo_applicativo`, `soggetto_ruolo_id`) è
**tutto-o-niente**: la scrive una sola query, e se la coppia `(auth_user, identità)` non è
valida le tre colonne escono **vuote insieme**. Non è mai lecito avere
`current_identita_id` valorizzato e `ruolo_applicativo` vuoto.

⚠️ **L'emittente non fa parte della tripla**, e la differenza conta: può essere **vuoto
mentre la tripla è piena** — è il caso di chi non ha un emittente attivo selezionato (un
SUPER_ADMIN globale, o un job che gira senza emittente). La tripla invece o c'è tutta o non
c'è. Le due condizioni si leggono separatamente.

Gli ultimi due sono **legacy**: nascono prima del refactor multi-face e restano in uso dai
trigger audit generici. Non entrano nelle policy RLS.

---

## 3. Chi popola cosa, quando

**Due attori, e solo due**, entrambi in `apps/core`:

| Attore                                      | Cosa fa                                               | Dove                                           |
| ------------------------------------------- | ----------------------------------------------------- | ---------------------------------------------- |
| `JwtAuditMiddleware`                        | **azzera** tutte le GUC d'identità a inizio richiesta | `apps/core/middleware/jwt_audit_middleware.py` |
| `JwtAuditAuthentication` → `set_jwt_gucs()` | **scrive** le GUC coi valori reali                    | `apps/core/api/jwt_audit_authentication.py`    |

Nessun service, nessuna view, nessun altro middleware deve settare i GUC d'identità.

**Sequenza di una richiesta autenticata:**

1. Il middleware di reset ripulisce le 6 GUC. Azzera **solo** se la connessione è già aperta
   (una connessione nuova nasce pulita) e **solo** sui path `/api/`. Se il reset fallisce, la
   richiesta **non viene servita**: 500 `E_GUC_RESET_FAILED`. È un fail-closed dichiarato —
   meglio un errore che servire dati con uno scope ereditato.
2. DRF riceve la request con header `Authorization: Bearer <jwt>`.
3. `JwtAuditAuthentication.authenticate()` valida il JWT e legge i claim `identita_id`,
   `ruolo_applicativo` e l'emittente attivo.
4. `set_jwt_gucs()` esegue **un'unica query** (una CTE) che fa tre cose insieme: valida la
   coppia `(identita_id, auth_user_id)` su `anagrafiche.identita_digitali` con `attivo = true`,
   **rivalida ad ogni richiesta** che l'emittente del claim sia ancora attivo, e scrive i 6 GUC
   con `set_config(..., false)` ([esempio](#area-tecnica-esempi)).
5. Identità non attiva → `E_IDENTITA_NON_ATTIVA` (401): il client deve rifare login.

> ⛔ **Senza `identita_id` esplicito le GUC non vengono toccate affatto.** Non è una
> dimenticanza: un `auth_user` può avere **più identità attive** (una per veste), quindi
> risolvere «la prima» sceglierebbe una veste al posto dell'utente — con la GUC sbagliata,
> in silenzio. Chi non ha l'identità la chiede al client, non la indovina.

**Request anonime.** Su una richiesta senza JWT valido le GUC d'identità **non vengono
scritte** dagli step 2-5, e quelle eventualmente rimaste dalla richiesta precedente sono già
state azzerate al passo 1. Quindi il DB legge valori vuoti: la tripla è `NULL`,
`fn_current_identita_context()` non restituisce niente e le policy RLS fail-closed. Il valore
che rende vera questa frase non è il `COMMIT` — è il reset.

**Processi di sistema headless.** I management command e i cron non hanno un canale a parte:
si collegano come l'applicazione e, se toccano i dati di un'azienda, impostano gli stessi GUC
d'identità di una richiesta web, con l'**utente tecnico** di quell'azienda
([I lavori automatici](/guide/processi-automatici-classe-e-identita)). Nessun utente del
database scavalca la RLS al posto loro ([provisioning-db-roles](/dev/backend/provisioning-db-roles)).

**Canale della coda.** Il worker della coda di lavoro
(`apps/core/services/coda_lavori/context.py`) usa **lo stesso** `JWT_GUC_RESET_SQL` del
middleware per entrare e per uscire: scrive l'identità di chi ha chiesto il giro, esegue, e
azzera nel `finally` — anche quando il giro fallisce o l'identità non è più attiva.

---

## 4. Chi legge cosa

### 4.1 Policy RLS

Ogni policy RLS legge i GUC con `current_setting(..., true)`. Il secondo parametro `true` è
quello che rende la lettura **non eccezionale** quando la GUC non è settata: restituisce
stringa vuota invece di sollevare.

Lo schema è sempre lo stesso, e ha due pezzi:

1. **il gate sulla veste** — `app.ruolo_applicativo` confrontato con i valori ammessi
   (`IN ('CLIENTE_PORTALE', 'SHOP_CUSTOMER')`, e simili);
2. **la chiamata allo scope**, che riceve `NULLIF(current_setting(...), '')::bigint` — la
   conversione da stringa vuota a `NULL` **prima** del cast, perché è il `NULL` a far
   scattare il fail-closed dentro la funzione di scope.

Un esempio completo di policy e la riga di conversione sono in
[Area tecnica](#area-tecnica-esempi).

### 4.2 Helper `fn_current_identita_context`

[`script.fn_current_identita_context()`](/dbzero/script/funzioni/fn_current_identita_context)
serve a chi ha bisogno di **tutta la tripla** e non di una colonna sola: la restituisce come
record tipato, oppure `(NULL, NULL, NULL)` se **anche uno solo** dei tre valori manca o non è
castabile. Chi la consuma non deve quindi ricontrollare i singoli campi: se `identita_id` è
`NULL`, la tripla non è utilizzabile.

### 4.3 Trigger audit

I trigger generici [`script.trgfn_audit_data_user_generic()`](/dbzero/script/funzioni/trgfn_audit_data_user_generic)
leggono `app.jwt_user` e `app.current_user_id`: è la firma delle righe, non un controllo di
accesso. Restano fuori dalle policy RLS.

---

## 5. Fail-closed: cosa succede se i GUC mancano

### 5.1 Caso: identita non popolata

**Sintomo:** `current_setting('app.current_identita_id', true) = ''`

**Effetto:**

* `fn_scope_ba_ownership(NULL, ...)` → `false` (short-circuit su identita inesistente)
* `fn_get_identita_sr_perimetro(NULL, ...)` → `NULL`, e il confronto `fn_scope_sr_perimetro` → `false`
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
> [Multi-Face Auth §9](/guide/architettura-multi-face-auth#9-il-flag-di-login-di-django-auth_useris_active)):
> l'user potrebbe essere globalmente attivo ma con la veste specifica
> disattivata.

---

## 6. L'invariante tutto-o-niente, e come è difesa

L'invariante riguarda **la tripla** (§2): o i tre valori ci sono tutti, o non ce n'è nessuno. È
difesa su **entrambi i lati**, e in nessuno dei due si improvvisa.

* **Lato BE** — le GUC si scrivono in **una sola query**, che valida *e* scrive: se la coppia
  `(auth_user, identità)` non è attiva, le colonne escono vuote invece di uscire sbagliate. Il
  DB non può restare in uno stato parziale perché non esiste un momento in cui è stata scritta
  solo una parte dell'insieme ([esempio](#area-tecnica-esempi)).
* **Lato DB** — chi ha bisogno della tripla non ricompone tre `current_setting` a mano: chiama
  [`script.fn_current_identita_context()`](/dbzero/script/funzioni/fn_current_identita_context),
  che restituisce i tre valori **oppure `(NULL, NULL, NULL)`**. Il `NULL` è la risposta
  fail-closed, e va letto come «questa sessione non ha un'identità utilizzabile».

⛔ **Nessuna cattura generica.** Un errore mentre si legge l'identità non deve diventare
«procedo senza GUC»: o l'identità c'è e si scrive, o la richiesta si ferma.

---

## 7. Chi consuma le GUC

### 7.1 Funzioni di scope (`script`) — non leggono le GUC

Ricevono il valore **come parametro**: è la policy RLS a leggere il GUC e a passarglielo.
Attenzione al **primo parametro**, perché le due famiglie non concordano:

| Famiglia                           | Firma                                                                                                                                                                                                 | Cosa le si passa                                                                                                         |
| ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| ownership (cliente, fornitore, BA) | `fn_get_identita_sr_perimetro(p_identita_id, …)` (il perimetro delle policy) · `fn_scope_ba_ownership(p_identita_id, …)` · `fn_scope_fornitore_ownership(p_identita_id, …)` | `app.current_identita_id`                                                                                                |
| whitelist emittente                | `fn_scope_ef_whitelist(p_auth_user_id, p_emittente_fiscale_id)` · `_via_sr(p_auth_user_id, …)` · `_via_fattura(p_auth_user_id, …)`                                                                    | `app.current_user_id`; delegano a [fn_check_user_emittente_scope](/dbzero/script/funzioni/fn_check_user_emittente_scope) |

⚠️ **Il primo parametro non è lo stesso nelle due famiglie** — `identità` per l'ownership,
`auth_user` per la whitelist emittente — e i due numeri si somigliano abbastanza da passare
inosservati. Scambiarli non solleva: la funzione risponde `false` e la policy **nasconde
righe**, in silenzio.

### 7.2 Helper del resolver (`script`) — non leggono le GUC

`fn_get_profili_accesso_applicabili(auth_user_id)`, `fn_is_super_admin(auth_user_id)`,
`fn_get_uo_id_for_user(auth_user_id)`: ricevono parametri espliciti dal resolver Python.

### 7.3 Policy RLS

Ogni policy legge i GUC con `NULLIF(current_setting(..., true), '')::tipo` e li passa alle
funzioni di sopra ([esempio](#area-tecnica-esempi)). **Quante siano e dove stiano è stato, non
contratto**: si interroga `pg_policies`, non si tiene a mano qui. Il disegno d'insieme è in
[Multi-Face Auth §6.4](/guide/architettura-multi-face-auth#64-il-canale-di-origine-sui-dati-transazionali).

### 7.4 Trigger audit

[`script.trgfn_audit_data_user_generic()`](/dbzero/script/funzioni/trgfn_audit_data_user_generic)
— legge `app.jwt_user` e `app.current_user_id`, e con quelli firma `user_insert` / `user_update`.

---

## 8. Diagnosi

### 8.1 «Vedo zero righe, ma dovrei vederne N»

Cinque cose da guardare, in quest'ordine: il claim `identita_id` nel token che il client sta
mandando davvero (decodifica del JWT); il valore di `app.current_identita_id` sulla connessione;
lo stato dell'identità in `anagrafiche.identita_digitali`; la USING clause della policy; e se la
RLS è **attiva** su quella tabella. Le query sono in [Area tecnica](#area-tecnica-esempi).

⚠️ **Il quinto controllo non si salta.** Una tabella con RLS non attiva non filtra niente,
qualunque cosa dicano le GUC — e «vedo tutto» e «vedo zero» portano a cercare in due posti
diversi.

### 8.2 «Login riuscito, ma la prima richiesta autenticata risponde 401»

Il token non porta il claim `identita_id` (o non porta il `sid`): è `E_JWT_SENZA_IDENTITA`, 401
per scelta. **Non esiste una finestra di compatibilità** per i token emessi prima del refactor:
senza `identita_id` le GUC non vengono toccate affatto (§3), quindi il token si rigenera con un
login nuovo.

### 8.3 «Il trigger audit salva NULL su `user_insert`»

`app.jwt_user` non è settato: la richiesta non è passata dall'authentication class (path
anonimo), oppure l'INSERT arriva da un management command o da una shell Django, dove una
request non esiste. In quel caso il trigger usa il default — `CURRENT_USER` di PostgreSQL, cioè
il ruolo DB connesso.

---

## 9. Sviluppi aperti

* **`app.tenant_id`** — se Zero ERP diventasse multi-tenant servirebbe una GUC per il tenant
  corrente. Non è una modifica al contratto: si aggiunge alla tupla `JWT_IDENTITY_GUCS`, e il
  reset si deriva da lì.
* **Scorciatoia `app.is_super_admin`** — oggi il controllo costa una chiamata a
  `fn_is_super_admin(auth_user_id)`. Propagare al login un booleano precomputato eviterebbe la
  chiamata; la funzione però è `STABLE` e inlineable, quindi il guadagno va misurato prima di
  aggiungere un settimo valore al contratto.
* **`app.request_id`** — l'identificativo di richiesta oggi lo gestisce `RequestLogMiddleware`,
  fuori dall'authentication class. Unificarlo sotto lo stesso contratto è una scelta aperta, non
  una svista.

---

## Area tecnica — esempi

**Scrivere le GUC dell'identità** — una sola query, che valida la coppia `(auth_user, identità)`
*e* rivalida l'emittente attivo, poi scrive le 6 GUC. `false` = scope di sessione (la vita è
quella della connessione, non del commit):

```sql
WITH id_row AS (
    SELECT id, ruolo_applicativo, soggetto_ruolo_id
      FROM anagrafiche.identita_digitali
     WHERE id = %s AND auth_user_id = %s
       AND attivo = true
), ef_row AS (
    SELECT ef.id
      FROM anagrafiche.emittenti_fiscali ef
     WHERE %s::bigint IS NOT NULL
       AND ef.id = %s::bigint
       AND ef.attivo = true
)
SELECT
    set_config('app.jwt_user',             %s, false),
    set_config('app.current_user_id',      %s, false),
    set_config('app.current_identita_id',  COALESCE((SELECT id::text               FROM id_row), ''), false),
    set_config('app.ruolo_applicativo',    COALESCE((SELECT ruolo_applicativo::text FROM id_row), ''), false),
    set_config('app.soggetto_ruolo_id',    COALESCE((SELECT soggetto_ruolo_id::text FROM id_row), ''), false),
    set_config('app.current_emittente_id', COALESCE((SELECT id::text               FROM ef_row), ''), false),
    (SELECT COUNT(*) FROM id_row) AS identita_count;
```

**Azzera­re tutti i GUC d'identità** — il reset di inizio richiesta. Si **deriva** dalla tupla
`JWT_IDENTITY_GUCS`, non è una lista da tenere allineata a mano:

```python
JWT_GUC_RESET_SQL = "SELECT " + ", ".join(
    f"set_config('{guc}', '', false)" for guc in JWT_IDENTITY_GUCS
)
```

**Una policy RLS completa** — il gate sulla veste e la chiamata allo scope, con la conversione
sicura da stringa vuota a `NULL`:

```sql
CREATE POLICY rls_preventivi_ef_whitelist ON vendite.preventivi
    AS PERMISSIVE
    FOR SELECT
    USING (
        current_setting('app.ruolo_applicativo', true) = 'OPERATORE'
        AND script.fn_scope_ef_whitelist(
            NULLIF(current_setting('app.current_user_id', true), '')::integer,
            emittente_fiscale_id
        )
    );
```

**Leggere la tripla in una funzione o in una policy** — un solo posto da cui prenderla, e il
`NULL` significa «sessione senza identità»:

```sql
SELECT identita_id, ruolo_applicativo, soggetto_ruolo_id
FROM script.fn_current_identita_context();
-- identita_id IS NULL → la tripla non è utilizzabile: fail-closed
```

**Diagnosi: la sessione e la postura RLS di una tabella** — il primo dei cinque controlli del
§8.1 visto dal DB:

```sql
-- chi sono, per il database
SELECT current_setting('app.current_identita_id', true) AS identita_id,
       current_setting('app.ruolo_applicativo',   true) AS ruolo,
       current_setting('app.current_emittente_id', true) AS emittente_id;

-- l'identità è ancora attiva?
SELECT id, ruolo_applicativo, attivo
FROM anagrafiche.identita_digitali
WHERE id = NULLIF(current_setting('app.current_identita_id', true), '')::bigint;

-- la RLS è accesa su quella tabella? (e quali policy ha)
SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname = '<tabella>';
SELECT polname, pg_get_expr(polqual, polrelid) AS using_clause
FROM pg_policy
WHERE polrelid = '<schema>.<tabella>'::regclass;
```

---

{% include-markdown "signature-core.md" %}
