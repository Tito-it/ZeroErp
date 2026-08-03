# Brief BE → DB — impersonazione di scope emittente per SUPER_ADMIN

**Chi scrive:** BE (`dev/backend-tid`), 2026-08-03.
**A chi:** team DB (`dev/db-tid`).
**Cos'è:** oggi un SUPER_ADMIN vede *tutti* gli emittenti e non ha modo di
lavorare «dentro» uno di essi. Vogliamo dargli un **emittente attivo di
sessione**, scelto da una combo in topbar, che restringe l'applicazione
esattamente a ciò che vedrebbe un operatore di quell'emittente — liste, RLS in
lettura e write-guard compresi — con una voce «Tutti gli emittenti» per tornare
onnisciente.
**Decisione presa da Tid** (2026-08-03): impersonazione **di scope**, non
semplice «contesto di lavoro». Motivo: la variante debole (default di creazione
sì, liste no) lascia un'asimmetria silenziosa — lavori «su X» ma i parametri
risolvono sul gestore globale e le liste mostrano tutto. È il tipo di
incoerenza che si scopre su una fattura sbagliata.
**Correlati:** [fn_check_user_emittente_scope](/dbzero/script/funzioni/fn_check_user_emittente_scope) ·
[fn_get_emittenti_scope_pk_ids](/dbzero/script/funzioni/fn_get_emittenti_scope_pk_ids) ·
[fn_resolve_emittente_for_user](/dbzero/script/funzioni/fn_resolve_emittente_for_user) ·
guida [architettura-multi-face-auth](/guide/architettura-multi-face-auth)

---

## 1. Com'è oggi

L'associazione operatore ↔ emittente è `config.user_emittenti_fiscali`
(`UNIQUE(auth_user_id)`, modello 1‑a‑1; zero righe = admin globale). Da lì
scendono **quattro** catene distinte:

| # | Catena | Entry point | Comportamento SUPER_ADMIN |
| --- | --- | --- | --- |
| 1 | Filtri lista (BE) | `fn_get_emittenti_scope_pk_ids` / `_sr_ids` | `NULL` = vede tutto |
| 2 | RLS in lettura | `fn_scope_ef_whitelist` (+ `_via_sr`, `_via_fattura`) → **`fn_check_user_emittente_scope`** | `true` = vede tutto |
| 3 | Write-guard | `trgfn_guard_emittente_scope` → **`fn_check_user_emittente_scope`** | `true` = scrive ovunque |
| 4 | Resolver 1‑a‑1 | `fn_resolve_emittente_for_user` | `NULL` (nessuna riga) |

Il lavoro fatto nel 2026‑06‑01 ci aiuta molto: **`fn_check_user_emittente_scope`
è già la sede unica read+write**, e gli adapter RLS le delegano senza duplicare
la regola. Toccandola si propaga a lettura e scrittura insieme.

---

## 2. Il principio, prima delle richieste

> **La selezione è solo restringente, mai allargante.**

Non esiste percorso in cui l'emittente attivo *aggiunga* visibilità a chi non
ce l'ha. Formalmente, per ogni utente `u` ed emittente `e`:

```
accesso_effettivo(u, e)  =  accesso_attuale(u, e)  AND  (attivo IS NULL OR attivo = e)
```

Ne discende che un operatore che riuscisse a forzare il valore (via client
malevolo, se il BE avesse un buco) non guadagna nulla: al massimo si
auto‑restringe. Questa è la proprietà che rende accettabile mettere il valore
in una GUC di sessione invece che in una tabella di permessi.

---

## 3. Il contratto: la GUC `app.current_emittente_id`

Il BE la propaga come **sesta** GUC di identità, accanto alle cinque già
esistenti (`app.jwt_user`, `app.current_user_id`, `app.current_identita_id`,
`app.ruolo_applicativo`, `app.soggetto_ruolo_id`), con la stessa meccanica:
`set_config(..., false)`, popolata in `set_jwt_gucs()` e **azzerata dal
middleware a fine richiesta** insieme alle altre.

| Valore GUC | Significato |
| --- | --- |
| assente / stringa vuota | Nessuna impersonazione → comportamento **identico a oggi** |
| `<emittente_fiscale_id>` | Emittente attivo: restringe come da §2 |

Convenzione: **PK reale** (`anagrafiche.emittenti_fiscali.id`), coerente con la
canonica `_pk_ids`. La lettura è sempre
`NULLIF(current_setting('app.current_emittente_id', true), '')::bigint` —
la forma già usata da `trgfn_guard_emittente_scope` per `app.current_user_id`.

**Non chiediamo al DB di validare la GUC contro lo scope reale**: per §2 non
serve, e un check aggiuntivo dentro una funzione chiamata dalla RLS costerebbe
su ogni riga. La validazione «l'emittente scelto esiste ed è attivo» la fa il BE
al momento dello switch, una volta.

---

## 4. Cosa chiediamo

### 4.1 🔴 `fn_check_user_emittente_scope` — l'AND restringente

È la canonica read+write: qui la regola entra una volta sola e copre RLS e
trigger. L'ordine dei rami è la parte delicata, perché **il ramo super admin
oggi ritorna `true` prima di qualunque altra cosa**:

```text
1. p_auth_user_id IS NULL            -> true            (job batch, invariato)
2. v_attivo := GUC emittente attivo
   IF v_attivo IS NOT NULL
      AND p_emittente_fiscale_id IS DISTINCT FROM v_attivo
   THEN RETURN false                                     <-- NUOVO, prima del bypass SA
3. fn_is_super_admin                 -> true            (invariato)
4. no identita OPERATORE attiva      -> false           (invariato)
5. whitelist vuota                   -> true            (invariato)
6. EXISTS match whitelist                               (invariato)
```

Il punto 2 **deve** precedere il 3: è tutto il senso della richiesta. Nota che
si applica a chiunque, non solo al super admin — un operatore con la GUC settata
sul proprio emittente passa comunque dal punto 6, e con la GUC su un altro
emittente si auto‑esclude. Coerente con §2.

⚠️ `IS DISTINCT FROM` e non `<>`: `p_emittente_fiscale_id` può arrivare `NULL`
dagli adapter (`_via_sr` con SR non mappato, `_via_fattura` con fattura
inesistente). Con la GUC attiva quel caso deve restare **fail‑closed**.

### 4.2 🔴 `fn_get_emittenti_scope_pk_ids` — l'intersezione

Stessa regola in versione array, applicata **in coda**, dopo i rami esistenti:

| Caso | Ritorno oggi | Ritorno con GUC = `X` |
| --- | --- | --- |
| No identità OPERATORE | `'{}'` | `'{}'` (invariato: la GUC non allarga) |
| Super admin | `NULL` | `'{X}'` |
| Whitelist `{A,B}` | `{A,B}` | `{A,B} ∩ {X}` → `{X}` se X∈{A,B}, altrimenti `'{}'` |
| Whitelist vuota (→ `NULL`) | `NULL` | `'{X}'` |

Cioè: `NULL ∩ {X} = {X}` (NULL = universo), e l'array vuoto resta vuoto.

`fn_get_emittenti_scope_sr_ids` **eredita gratis** — è un wrapper e il
pass‑through dei sentinel continua a funzionare: con la GUC attiva la canonica
non ritorna più `NULL`, quindi il wrapper entra nella mappatura PK → SR, che è
esattamente ciò che vogliamo.

### 4.3 🟠 `fn_resolve_emittente_for_user` — l'emittente «di lavoro»

Se la GUC è valorizzata, **ritornarla**; altrimenti comportamento attuale
(lookup in `user_emittenti_fiscali`).

Serve perché è la fn che decide a quale emittente si aggancia ciò che si crea:
la chiama `trgfn_billing_account_link_ef` per l'auto‑link del BA alla creazione.
Un super admin che crea un cliente mentre impersona X deve produrre un BA di X,
non del gestore globale. Senza questo pezzo l'impersonazione sarebbe di sola
lettura, e sarebbe peggio del non averla: vedi X, ma crei altrove.

⚠️ Questa fn è chiamata anche da contesti senza GUC (job, trigger in batch): lì
il comportamento resta identico a oggi.

### 4.4 🟠 Audit — «e se il super admin impazzisce?»

Due pezzi, entrambi piccoli:

1. **Colonna `emittente_attivo_id bigint NULL` su `dbops.request_log`.** Il
   middleware BE scrive già una riga per ogni `/api/*` con `auth_user_id`,
   `path`, `status_code`: aggiungendo la colonna otteniamo *cosa ha fatto, e in
   che veste*, senza infrastruttura nuova. FK verso `emittenti_fiscali` a vostra
   discrezione (la tabella è un log ad alto volume con `cleanup_at`).
2. **Log del cambio veste.** Serve una riga append‑only per ogni switch: `chi`,
   `quando`, `da → a`, esito. Non c'è una sede naturale — `vendite.event_log` è
   di dominio, `dbops.audit_log` è per esecuzioni di funzioni SQL. Proponiamo
   una tabella dedicata (`config.user_emittente_attivo_log`, append‑only con lo
   stesso trigger `trgfn_*_append_only` di `event_log`), ma **la sede la
   scegliete voi**: se preferite estendere una tabella esistente, per noi è
   indifferente — l'importante è che l'evento esista e non sia cancellabile.

### 4.5 🟢 pgTAP — i casi che vogliamo vedere verdi

Sono la prova che §2 regge. Sul modello dei test di scope già presenti:

| # | Scenario | Atteso |
| --- | --- | --- |
| 1 | Super admin, **nessuna** GUC | `_pk_ids` = `NULL`, `check(...)` = `true` (nessuna regressione) |
| 2 | Super admin, GUC = X | `_pk_ids` = `{X}`, `check(X)` = `true`, `check(Y)` = **`false`** |
| 3 | Operatore whitelist `{A}`, GUC = **B** | `_pk_ids` = `'{}'`, `check(B)` = `false` — **non allarga** |
| 4 | Operatore whitelist `{A}`, GUC = A | invariato rispetto a oggi |
| 5 | `p_auth_user_id NULL` (batch), GUC = X | `true` — i job non si auto‑bloccano |
| 6 | GUC = X, adapter `_via_sr` con SR non mappato | `false` (fail‑closed, §4.1) |
| 7 | `fn_resolve_emittente_for_user`, super admin, GUC = X | `X` |
| 8 | RLS end‑to‑end: super admin con GUC = X su `vendite.fatture` | vede **solo** le fatture di X |

Il caso **3** è quello che non deve mai diventare rosso: è l'invariante di
sicurezza dell'intera feature.

---

## 5. Cosa NON chiediamo

* **Nessuna modifica alle policy RLS.** Gli adapter delegano già alla canonica:
  cambiando §4.1 lettura e scrittura si allineano insieme. Se scoprite un
  percorso RLS che *non* passa dalla canonica, segnalatecelo — sarebbe un buco
  già oggi, indipendente da questo cantiere.
* **Nessuna riga in `config.user_emittenti_fiscali` per il super admin.** Sarebbe
  la scorciatoia economica, ma renderebbe il super admin `scope_mode='SINGLE'`
  agli occhi di `fn_get_user_emittenti_scope` e del drawer operatori: una
  bugia persistente su una tabella di permessi, per uno stato che è di sessione.
* **Nessun cambio a `fn_get_user_emittenti_scope` / `fn_change_user_emittenti_scope`**:
  restano la configurazione *permanente*, ortogonale all'impersonazione.

---

## 6. Cosa fa il BE (nostra metà)

Inerte finché §4 non atterra — la combo cambierebbe senza che i dati si
restringano, quindi non la esponiamo prima.

1. Claim `emittente_attivo_id` nel JWT + endpoint `/auth/switch-emittente/` che
   riemette access+refresh (validando che l'emittente esista, sia attivo e —
   per un non‑super‑admin — sia nel suo scope).
2. GUC in `set_jwt_gucs()` e, **soprattutto**, nella tupla `JWT_IDENTITY_GUCS`
   di [jwt_audit_authentication.py:40](../../../backend/apps/core/api/jwt_audit_authentication.py#L40):
   il reset di fine richiesta è derivato da quella tupla. Dimenticarla lì
   lascerebbe la GUC appiccicata alla connessione del pool e la **richiesta
   successiva, di un altro utente, erediterebbe l'impersonazione**. È il rischio
   più serio dell'intero cantiere ed è tutto lato nostro.
3. `/me/` espone l'emittente attivo; il FE aggiunge la combo in topbar
   (`AppTopbar.vue`, dove oggi la ragione sociale è testo fisso), la conferma
   preventiva basata su `tabs.hasDirtyTabs()` e il reset delle schede aperte.
4. **Job in background**: la coda lavori gira con `operator_identity_context()`
   e non ha la GUC. L'emittente attivo va **congelato nel payload del job
   all'accodamento** — altrimenti lo stesso lavoro darebbe risultati diversi a
   seconda di quando parte. Nessuna richiesta al DB su questo punto: è nostro.

---

## 7. Definizione di «fatto»

1. §4.1 + §4.2 + §4.3 applicate, con la doc auto‑gen rigenerata.
2. pgTAP §4.5 verdi, **caso 3 compreso**, e baseline aggiornata.
3. §4.4 in piedi (colonna + sede del log dello switch).
4. BE: switch + GUC + reset simmetrico, con test che dimostrano l'azzeramento
   della GUC a fine richiesta.
5. FE: combo + «Tutti gli emittenti» + reset schede.
6. Validazione a video di Tid: impersonare un emittente e verificare che una
   lista fatture mostri solo le sue.
