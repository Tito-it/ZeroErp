# Brief DB — Le mail si vedono per ambito, non solo per emittente

> **Chi scrive:** backend/frontend (`dev/backend-tid`), 2026-09-25. **A chi:**
> Tid (decisioni, §4), poi team DB (`dev/db-tid`).
> **Origine:** [piano-be-fe-endpoint-senza-porta.md](piano-be-fe-endpoint-senza-porta.md)
> §3. Il 2026-09-25 Tid ha scelto la strada **(a)**: gli operatori devono poter
> vedere le mail del loro perimetro, a partire dalla sola lista.
> **Stato:** ✅ **D-1 → D-5 decise da Tid il 2026-09-25** (§4, §4.1).
> 🟡 **DB scritto il 2026-09-25, NON applicato** (§6): changeSet
> `20260925-63..-70` e cinque pgTAP. **Tocca a Tid**: apply e corsa pgTAP
> (§6.3). Poi tocca al **BE**, che ha tre richieste (§6.4), una delle quali
> rompe un test Django finché non la si fa. ⛔ È il **prerequisito della
> schermata operatore**: il BE/FE non parte finché questo brief non è chiuso.
> **Da leggere per primo: §6.**
>
> **In una riga:** il modello dichiara che una mail di ambito `OPERATORE` la vede
> **solo chi l'ha creata** e una di ambito `REPARTO` **solo il suo reparto**. La
> RLS applica solo l'**emittente**: oggi un operatore leggerebbe le mail di
> ambito `OPERATORE` di un collega dello stesso emittente. Il difetto è rimasto
> nascosto perché al log arrivava solo chi ha l'area `config`. Aprire la
> schermata lo renderebbe raggiungibile.

---

## 1. Cosa dice il modello

Sede: [config.email_log (manual)](../../dbzero/config/manual/email_log.md)
§«Ambito di visibilita'», stessa tabella in `work-done/gestione-autenticazioni.md`
§1.1.4 per `config.email_outbox`.

| Ambito | Chi la vede |
| --- | --- |
| `SISTEMA` | solo admin |
| `REPARTO` | gli operatori dell'unità organizzativa + admin |
| `OPERATORE` | solo chi l'ha creata + admin |

Più una regola: *le mail con `pratica_id` sono visibili dalla scheda pratica,
indipendentemente dall'ambito.*

Il modello **ammette** tutti e tre gli ambiti: `chk_email_log_ambito` e il
gemello sull'outbox li accettano, e `EmailPrepareView` riceve `ambito` dalla
richiesta. Non conta quante righe `REPARTO`/`OPERATORE` ci siano oggi (regola
zero): il ramo è nel contratto.

## 2. Cosa applica la RLS

`rls_email_log_ambito` (`20260905-43`) e `rls_email_outbox_ambito`
(`20260905-33`) hanno due rami:

* `ambito = 'SISTEMA'` → super admin (più, sul solo log, l'identità di
  `send_pending_emails`) — ✅ coerente col modello;
* **tutto il resto** → `fn_scope_ef_whitelist(utente, emittente_fiscale_id)`.

⛔ `REPARTO` e `OPERATORE` cadono nello stesso `ELSE`, e lì l'unico cancello è
l'emittente. Né `unita_organizzativa_id` né `auth_user_id` (sul log) o il
creatore (sull'outbox) vengono letti. Il `pgTAP`
`db/pgtap/rls/test-rls-email-log-ambito.sql` usa righe `OPERATORE` ma prova solo
l'asse emittente (*mia/altrui* = emittente mio/altrui).

⚠️ **Sull'outbox è peggio che sul log**: la bozza `OPERATORE` di un collega
dello stesso emittente si può **leggere, modificare e spedire** (`FOR ALL`).
Oggi lo impedisce solo l'area `config` sulle view (D15, 2026-09-12).

⛔ **Il filtro non va aggiunto nel backend.** Il repository ha già i parametri
`ambito` e `unita_organizzativa_id`. Ma usarli nella view creerebbe una
**seconda sede** della regola, e varrebbe solo per chi passa da quella view
(piano §1.1). La sede è la policy.

## 3. La richiesta

Stessa forma su **`config.email_log` e `config.email_outbox`**: stessa regola,
due tabelle, nello stesso giro.

1. **Ramo `OPERATORE`**: chi ha creato la riga = `app.current_user_id`, oppure
   admin (§4 D-2). Sul log la colonna è `auth_user_id`. ⚠️ **Sull'outbox le
   colonne utente sono due**, `auth_user_id` e `creato_da_user_id`: prima di
   scrivere il ramo va detto nel `COMMENT` quale delle due significa
   «di chi è la bozza».
2. **Ramo `REPARTO`**: `unita_organizzativa_id =
   script.fn_get_uo_id_for_user(app.current_user_id)`, oppure admin. Il
   building block esiste già. ⚠️ Se l'utente non ha UO la funzione rende
   `NULL`, il confronto è falso e la riga non si vede: fail-closed, va bene
   così.
3. **Emittente**: resta in `AND` sui due rami nuovi (§4 D-1).
4. **Stessa regola in `USING` e in `WITH CHECK`**: una riga `OPERATORE` si scrive
   solo col proprio utente, una `REPARTO` solo per il proprio reparto.
5. **Le colonne che reggono il ramo devono essere un'affermazione**. È la stessa
   trappola del default `SISTEMA`, già scritta in
   `work-done/brief-db-processi-automatici-residui-be.md`. Da verificare sulla doc
   auto-gen, ed eventualmente da aggiungere come `CHECK`:
   * `ambito = 'REPARTO'` ⇒ `unita_organizzativa_id IS NOT NULL` (dichiarato nel
     modello dell'outbox: c'è anche sul log?);
   * `ambito = 'OPERATORE'` ⇒ creatore `IS NOT NULL`.
6. **pgTAP**: costruire i casi, non leggerli dai dati. Per ciascuna tabella:
   * `OPERATORE`: mia ✅, di un collega dello stesso emittente ⛔;
   * `REPARTO`: del mio reparto ✅, di un altro reparto ⛔, utente senza UO ⛔;
   * admin ✅ su tutte.

### 3.1 ⚠️ Il punto da non rompere: `send_pending_emails`

Il processo **legge e aggiorna** anche le righe non `SISTEMA`: ripesca
`PENDING`/`FAILED`/`RETRY` e ne chiude lo stato. Oggi le vede attraverso il ramo
emittente. Ma la sua identità non è né il creatore né un membro del reparto:
**con i rami nuovi, una mail `OPERATORE` o `REPARTO` fallita non verrebbe più
ritentata, e non lo direbbe nessuno.** È la stessa lezione di `20260905-43`:
*portare è leggere*.

⇒ Il ramo `fn_scope_identita_processo(…, 'send_pending_emails')` va aggiunto
anche ai rami `OPERATORE` e `REPARTO` del **log**. Sull'**outbox** no, perché
nessun processo la legge (`20260905-33`). E va coperto da un pgTAP: il processo
vede una riga `OPERATORE` di un emittente del suo scope.

## 4. Decisioni — ✅ tutte decise da Tid il 2026-09-25

| # | Decisione |
| --- | --- |
| **D-1** | ✅ **`AND`**: l'emittente resta un cancello in più anche sui rami `OPERATORE`/`REPARTO` |
| **D-2** | ✅ «+ admin» = **super admin** (`script.fn_is_super_admin`), come sul ramo `SISTEMA` |
| **D-3** | ✅ **Rimandata**: la regola della scheda pratica **non** entra in questo giro. Resta scritta nel modello e si apre con la scheda pratica |
| **D-4** | ✅ **Sì**: `config.email_allegato` entra nello stesso giro, con un ramo per padre (log / outbox) sull'asse dell'ambito. Alla chiusura va tolta la riga 60 da `rls_perimetro_debito.csv` |

Le domande e le raccomandazioni com'erano scritte prima della decisione:

| # | Domanda | Raccomandazione |
| --- | --- | --- |
| **D-1** | Sui rami `OPERATORE`/`REPARTO` l'emittente resta un cancello in più (`AND`), o basta il reparto/creatore? | **`AND`**: fail-closed. Una mail di un emittente che l'operatore non ha più in scope non si vede, anche se l'ha scritta lui |
| **D-2** | «+ admin» nel modello: chi è l'admin? | **Il super admin**, come sul ramo `SISTEMA`. Un amministratore «d'area» sarebbe un secondo concetto di admin dentro una policy |
| **D-3** | La regola «visibile dalla scheda pratica indipendentemente dall'ambito»: la si scrive ora nella policy (chi vede la pratica vede la mail) o si rimanda? | **Rimandare, dichiarandolo**: la schermata che la userebbe è la scheda pratica, non questa lista. Scritta ora sarebbe un permesso che nessun codice esercita |
| **D-4** | `config.email_allegato` (debito registrato `rls_perimetro_debito` id 60, «cantiere email»): nello stesso giro? | **Sì**: gli allegati di una mail `OPERATORE` sono leggibili quanto la mail, e il registro dice già che la policy va sull'asse dell'ambito, con un ramo per padre |

## 4.1 Ricognizione DB (team DB, 2026-09-25) — ⛔ una premessa del §3 non regge

Letto dal catalogo di dbdev (policy da `pg_policy`, vincoli da `pg_constraint`)
e dal codice che scrive le due tabelle:

* **Policy in vigore**: `rls_email_log_ambito` (`20260905-43`) e
  `rls_email_outbox_ambito` (`20260905-32`/`-33`) sono quelle descritte al §2.
  RLS attiva su log e outbox, **spenta su `config.email_allegato`**, che non ha
  nessuna policy.
* **CHECK già presenti**: sull'outbox `chk_email_outbox_reparto_uo`
  (`REPARTO` ⇒ UO) c'è. ⛔ **Sul log manca**, e manca su entrambe la
  coppia `OPERATORE` ⇒ creatore.
* **Outbox — «di chi è la bozza» = `creato_da_user_id`.** `EmailPrepareView`
  lo scrive con `request.user.id`, e il controllo d'accesso della view
  (`_check_outbox_access`) usa quella colonna. `auth_user_id` è un'altra cosa: arriva
  dal payload ed è **l'utente di cui parla la mail**. Viene copiato sul log
  all'invio.
* ⛔ **Log — `auth_user_id` NON è il creatore.** È l'utente a cui si riferisce
  la mail: l'operatore invitato (`invito_operatore_service`), l'utente del
  reset password, oppure quello che era sulla bozza (`email_outbox_service`
  riga 160). **Sul log non esiste una colonna «chi l'ha creata».** Un ramo
  `OPERATORE` scritto su `auth_user_id` darebbe la mail al **destinatario** e
  la negherebbe a chi l'ha scritta. È il contrario del modello. ⇒ **D-5**.
* **Allegati**: dopo l'invio, `copy_allegati_to_log` fa `UPDATE … SET
  email_log_id` sulla stessa riga. Un allegato può quindi avere **entrambi** i
  padri valorizzati, e la policy va scritta in `OR` sui due padri, non «uno
  solo per riga» come dice il registro (id 60). Un allegato senza padri è
  ammesso dal modello (nessun CHECK), e con la policy nuova non lo vedrebbe
  nessuno: fail-closed.
* ⚠️ **A margine, non in questo giro**: la FK `email_allegato → email_outbox` è
  `ON DELETE CASCADE`. Se si cancella una bozza già spedita, spariscono anche
  gli allegati che il log ancora referenzia.
* **Fatto datato, non motivo** (2026-09-25, dbdev, letto come app con un super
  admin): esistono solo righe `SISTEMA`. Nessuna riga smentisce i CHECK nuovi.

**D-5 — ✅ decisa da Tid il 2026-09-25: colonna nuova.** Si aggiunge
`config.email_log.creato_da_user_id`, gemella di quella dell'outbox, con FK
verso `django.auth_user` e il CHECK `OPERATORE` ⇒ `NOT NULL`. **La valorizza il
BE**, non un DEFAULT preso dal GUC: dalla bozza si copia
`outbox.creato_da_user_id`, negli invii diretti si usa `request.user`. Un
DEFAULT avrebbe scritto chi preme «invia» al posto di chi ha scritto la bozza:
un super admin che spedisce la bozza di un altro ne diventerebbe l'autore.
Scartate anche «derivare l'autore dalla bozza» (una mail OPERATORE spedita
senza bozza non la vedrebbe nessuno) e «usare `auth_user_id`» (darebbe la mail
al destinatario).

## 5. Cosa succede dopo (BE/FE, non in questo brief)

Quando la policy è chiusa, il piano riparte dal §2.3. Resta aperta una scelta
**BE**: con la RLS che porta tutto il perimetro, la **lista** del log (sola
lettura) può uscire dall'area `config`. L'**outbox** (spedire) resta sotto
`config` finché non esiste l'azione di processo `invia_email` (D15).

## 6. Consegna DB (2026-09-25) — scritto, provato, NON applicato

### 6.1 I changeSet

⚠️ La numerazione parte da `-63`: il 25-09 era occupato fino a `-62`, e l'unico
buco (`-35`/`-36`) non bastava per otto file. Finché non sono applicati,
rinumerarli costa poco.

| # | File | Cosa fa |
| --- | --- | --- |
| 63 | `00_schema/config/…-add-column-email-log-creato-da-user-id` | colonna `email_log.creato_da_user_id` (D-5); `COMMENT` sulle due `auth_user_id` («l'utente di cui la mail parla») e su `email_outbox.creato_da_user_id` («di chi è la bozza») |
| 64 | `00_schema/config/…-add-check-email-ambito-colonne-del-ramo` | `chk_email_log_reparto_uo`, `chk_email_log_operatore_creatore`, `chk_email_outbox_operatore_creatore` (§3.5) |
| 65 | `20_code/script/…-create-fn-scope-email-ambito` | ⭐ `script.fn_scope_email_ambito`: **sede unica della regola** per le due policy, in `USING` e in `WITH CHECK`. Con `%TYPE` nella firma, nel `COMMENT` e nel `GRANT` |
| 66 | `00_schema/config/…-update-policy-rls-email-log-ambito` | la policy del log chiama la funzione passando `'send_pending_emails'` (§3.1) |
| 67 | `00_schema/config/…-update-policy-rls-email-outbox-ambito` | la policy dell'outbox chiama la funzione **senza processo** |
| 68 | `00_schema/config/…-create-policy-rls-email-allegato-ambito` | policy sugli allegati e RLS accesa. Un `EXISTS` per padre, in `OR`: ogni `EXISTS` passa dalla policy del padre, quindi la regola non si ricopia (D-4) |
| 69 | `80_data/changelog/…-delete-debito-rls-email-allegato` | toglie la riga 60 dal registro del debito (anche dal CSV) |
| 70 | `90_end/…-fk-config-email-log-creato-da-user-id-django-auth-user` | FK verso `django.auth_user` sotto `MARK_RAN`, come le sorelle. Riga `consentito=false` in `fk_index_policy_auth_user.csv`, e lista di rollback di `20260921-13` estesa |

**La regola, com'è scritta in `fn_scope_email_ambito`:**

| Ambito | Chi la vede |
| --- | --- |
| `SISTEMA` | super admin; sul log anche il processo |
| `REPARTO` | (super admin **o** stesso reparto **o** processo) **e** emittente nel perimetro |
| `OPERATORE` | (super admin **o** chi l'ha creata **o** processo) **e** emittente nel perimetro |

* Il processo entra solo sul **log**. Sui rami REPARTO e OPERATORE passa anche
  lui dal cancello emittente (D-1): legge le mail delle aziende del suo roster.
* ⛔ **Utente vuoto = niente.** `fn_check_user_emittente_scope(NULL, …)` risponde
  *true* («job batch»), ma nei rami nuovi è sempre in `AND` con una condizione
  che per NULL è falsa. In più c'è un `COALESCE` finale a `false`.

### 6.2 Le prove fatte (senza toccare dbdev)

Tutto su `zeroerp_ci`, come owner, in un solo `BEGIN … ROLLBACK` con l'SQL
**estratto** dai changeSet 63–69. La FK del 70 è scritta a mano, perché è un
change Liquibase e non SQL.

* ⭐ **La RLS provata da owner**: `ALTER TABLE … FORCE ROW LEVEL SECURITY` sulle
  tre tabelle, dentro la stessa transazione. Così l'owner subisce le policy come
  l'app. Con il `test-rls-email-ambito-reparto-operatore.sql` nuovo: **22/22 ok**.
* ⭐ **Il test sa vedere il difetto.** Lo stesso file sulle policy **vecchie**
  (solo 63–65): **14 rossi su 22**, esattamente sui rami del difetto (5–9, 14–18,
  20–22, e l'1 perché gli allegati non avevano RLS). Restano verdi i CHECK, il
  super admin e il processo sul log, che già passava dalla whitelist: lì sono
  presidi di non-regressione.
* **I pgTAP esistenti toccati**, prima e dopo l'SQL estratto, da owner:
  * `rls/test-rls-email-log-ambito`: 3 e 4 verdi dopo (prima morivano sulla
    colonna mancante). 1 e 2 sono **rossi da owner per costruzione**: l'owner
    salta la RLS. Sono verdi come app;
  * `rls/test-rls-email-outbox-ambito` 3/3, `config/test-fn-email-sistema`
    12/12, `dbops/test-presidi-debito-dichiarato` 8/8,
    `rls/test-rls-perimetro-scoperto` 8/8;
  * `config/test-fk-auth-user-ponte-django-v1`: sullo scratch **salta** (ponte
    assente), come in CI. ⚠️ Con la FK scritta a mano era 0/3: artefatto della
    prova, perché una sola FK fa credere al test che il ponte ci sia. Su dbdev
    il test 1 (l'invariante) **pretende** la FK del `-70`, ed è giusto così.
* Cancelli statici verdi: `runOnChange`, preambolo pgTAP, letterali SQL,
  timestamp, preCondition/seed, DDL su trigger, GRANT batch.

### 6.3 Per Tid: apply e test

1. Apply (dbdev, e lo scratch se serve).
2. pgTAP da lanciare:
   * `db/pgtap/rls/test-rls-email-ambito-reparto-operatore.sql` (**nuovo**, 22);
   * `db/pgtap/rls/test-rls-email-log-ambito.sql` (3 e 4 riscritti con l'autore);
   * `db/pgtap/rls/test-rls-email-outbox-ambito.sql` (solo l'intestazione:
     diceva «RLS spenta»);
   * `db/pgtap/config/test-fn-email-sistema.sql` (l'`INSERT` OPERATORE porta
     l'autore);
   * `db/pgtap/dbops/test-presidi-debito-dichiarato.sql` (test 2: con il
     proprietario, così il `23514` viene da **un** solo vincolo);
   * `db/pgtap/rls/test-rls-perimetro-scoperto.sql` (la riga 60 esce);
   * `db/pgtap/config/test-fk-auth-user-ponte-django-v1.sql` (invariante sulla
     colonna nuova).

### 6.4 Richieste al BE

1. ⛔ **Test Django che si rompe**: `apps/core/tests/db/test_ricerca_email_db.py`
   (`_costruisci`) scrive una mail `OPERATORE` sul log **senza**
   `creato_da_user_id`. In CI i test girano come `zeroerp_app`, quindi la
   ferma il `WITH CHECK` (42501). Da owner la fermerebbe il CHECK (23514).
   Deve portare l'autore, cioè l'utente del contesto. Poi rileggerà la riga
   come suo autore.
2. **Scrivere `email_log.creato_da_user_id`** in `insert_log`. `send_raw` lo
   copia da `outbox.creato_da_user_id`; negli invii diretti usa l'utente
   della richiesta. Senza, ogni mail `OPERATORE` scritta sul log viene
   respinta.
3. **Togliere la seconda sede della regola.** Oggi la stessa regola vive anche
   in due punti delle view. `_check_outbox_access` confronta
   `creato_da_user_id` con `request.user`. `EmailOutboxListView` filtra
   `creato_da_user_id = request.user.id`, e quel filtro nasconderebbe le bozze
   di REPARTO ai colleghi. Con la policy chiusa, la sede è la policy (§2).
   Va fatto insieme al §5.

### 6.5 A margine, fuori da questo giro

* La FK `email_allegato → email_outbox` è `ON DELETE CASCADE`: cancellare una
  bozza già spedita porta via gli allegati che il log referenzia ancora (§4.1).

---

*Brief DB, 2026-09-25. Scritto dal team BE/FE aprendo la strada (a) del piano
endpoint-senza-porta. §4.1 e §6 scritti dal team DB lo stesso giorno.*
