# Brief DB — Le mail si vedono per ambito, non solo per emittente

> **Chi scrive:** backend/frontend (`dev/backend-tid`), 2026-09-25. **A chi:**
> Tid (decisioni, §4), poi team DB (`dev/db-tid`).
> **Origine:** [piano-be-fe-endpoint-senza-porta.md](piano-be-fe-endpoint-senza-porta.md)
> §3. Il 2026-09-25 Tid ha scelto la strada **(a)**: gli operatori devono poter
> vedere le mail del loro perimetro, a partire dalla sola lista.
> **Stato:** ✅ **D-1 → D-5 decise da Tid il 2026-09-25** (§4, §4.1).
> ✅ **Lato DB chiuso il 2026-09-25** (§6): changeSet `20260925-63..-70`
> applicati, pgTAP senza regressioni, commit fatto (Tid).
> ✅ **Secondo giro DB chiuso il 2026-09-25 sera** (§8): «una mail si tocca
> solo in bozza», changeSet `20260925-71..-74`, applicati, pgTAP verdi (Tid).
> **Lato DB non resta niente.** **Cosa resta** (§7): le richieste al **BE**
> (§6.4 e §8.4; una rompe un test Django finché non la si fa), poi il §5. Il
> brief va in `work-done/` quando il BE ha chiuso le sue richieste. ⛔ È il **prerequisito della
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
  * `config/test-fk-auth-user-ponte-django-v1`: con la FK del `-70` era 0/3.
    ⛔ **L'avevo scritto come «artefatto della prova», ed era sbagliato**: è
    esattamente il rosso che lo scratch ha dato dopo l'apply (§6.5).
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

**Esito (Tid, 2026-09-25):** migrazione applicata, **nessuna regressione**
pgTAP, commit fatto.

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

### 6.5 ⛔ Dopo l'apply: `test-fk-auth-user-ponte-django-v1` rosso solo su `zeroerp_ci`

Tid, 2026-09-25 sera. Letto dal `databasechangelog` e da `pg_constraint` dello
scratch:

* le undici FK del ponte (`20260921-02..-12`) sono **`MARK_RAN`**. Lo scratch è
  stato ricostruito da zero, e in quel momento `django.auth_user` non esisteva;
* poi il migrate di Django ha creato la tabella, e il `-70` è arrivato dopo con
  un update incrementale. Ha trovato la tabella: **`EXECUTED`**;
* ⇒ sullo scratch c'è **una** FK del ponte su dodici. Il test pretende «tutto
  il ponte o niente»: con una FK sola decide che il ponte c'è, e trova le altre
  undici mancanti. Fa quello per cui è scritto.

**Dove vale, e dove no:**

* **CI (GitHub)**: ricostruisce da zero a ogni corsa, quindi anche il `-70` è
  `MARK_RAN` e il test salta. Nessuna regressione;
* **dbdev**: il ponte c'è intero (`EXECUTED`), e il test è verde con la tredicesima;
* **scratch**, e ⚠️ **qualunque installazione fatta come lui** (Liquibase da
  zero, poi Django, poi aggiornamenti): ogni FK del ponte aggiunta dopo
  l'installazione nasce, mentre le vecchie no. Il `-70` è solo la prima a farlo
  vedere. Il difetto sta nel `MARK_RAN` del ponte: segna le FK come fatte e non
  torna più a crearle.

**Le due strade** — decisione di Tid:

1. **Niente di strutturale**: il rosso resta solo sullo scratch, e sparisce alla
   prossima ricostruzione da zero (il `-70` diventa `MARK_RAN` come le altre).
   Costo zero, ma il difetto delle installazioni reali resta.
2. **Convergenza del ponte**: un changeSet di `90_end` `runAlways` che, se
   `django.auth_user` esiste, crea le FK del ponte mancanti (idempotente, dopo
   un controllo degli orfani). Ripara lo scratch e ogni installazione. È
   lavoro della voce V-7 (valutazione-modello-di-dominio-db), non di questo
   brief.

### 6.6 A margine, fuori da questo giro

* La FK `email_allegato → email_outbox` è `ON DELETE CASCADE`: cancellare una
  bozza già spedita porta via gli allegati che il log referenzia ancora (§4.1).
  **Riletto il 2026-09-25 con Tid** («una mail inviata non si cancella, si
  annulla solo in bozza»):
  * **dall'applicazione non succede**: nessun codice fa `DELETE` di una bozza.
    «Annulla» scrive `CANCELLED`, e il BE lo permette solo da `DRAFT`. Una
    bozza in `DRAFT` non ha ancora un log, perché il log nasce all'invio: in
    bozza il problema non esiste;
  * ⚠️ **ma la regola «solo in bozza» vive solo nel BE.** Il database
    non la conosce: `zeroerp_app` ha `DELETE` sulle tre tabelle, e nessun guard
    lo ferma;
  * ⛔ **e il problema esiste già in un'altra forma, raggiungibile dall'API.**
    Rimuovere un allegato (`DELETE` sull'allegato →
    `EmailOutboxService.remove_attachment`) controlla solo che l'operatore
    possa accedere alla bozza, **non che sia in `DRAFT`**. Dopo l'invio lo
    stesso allegato è legato anche al log: rimuoverlo lo toglie dalla storia
    della mail spedita, e ne cancella il file.
  * **Proposta** (da decidere, è un cantiere suo): la regola «si toccano solo
    le bozze» va nel database, con un guard su `email_allegato` (niente
    `DELETE` né cambio di padre se la bozza non è `DRAFT` o se c'è un log) e
    su `email_outbox` (niente `DELETE` fuori da `DRAFT`). Il BE tiene il suo
    controllo come messaggio all'utente.

## 7. Cosa resta (2026-09-25, a DB chiuso)

| # | Cosa | Di chi | Stato |
| --- | --- | --- | --- |
| 1 | `test_ricerca_email_db.py`: la mail `OPERATORE` deve portare l'autore (§6.4.1) | BE | ⛔ aperto: il test Django è rosso finché non si fa |
| 2 | `insert_log` e `send_raw` scrivono `email_log.creato_da_user_id` (§6.4.2) | BE | aperto: finché manca, una mail `OPERATORE` sul log viene respinta |
| 3 | Togliere la regola dalle view: `_check_outbox_access` e il filtro della lista bozze (§6.4.3) | BE | aperto, insieme al §5 |
| 4 | Ponte django parziale sullo scratch (§6.5) | Tid | ✅ **deciso il 2026-09-25: si lascia così**. Il rosso sparisce alla prossima ricostruzione dello scratch; non tocca la CI |
| 5 | Regola della scheda pratica (D-3) | DB, con le pratiche | ✅ confermata rimandata al cantiere pratiche (Tid, 2026-09-25) |
| 6 | Allegati di una mail già spedita (§6.6) | DB | ✅ **chiuso** (§8, `20260925-71..-74`): applicato, pgTAP verdi (Tid, 2026-09-25) |
| 7 | La lista del log esce dall'area `config` (§5) | BE/FE | parte dopo i punti 1–3 |
| 8 | Richieste BE del secondo giro (§8.4) | BE | aperto |

## 8. Secondo giro DB — «una mail si tocca solo in bozza» (2026-09-25 sera)

Decisione di Tid: *«una mail inviata non si cancella, la cancellazione si fa
solo in bozza»*, e il guard sta in questo brief (non in uno nuovo).

### 8.1 La regola, com'è scritta

| Cosa | Quando si può | Quando no |
| --- | --- | --- |
| **eliminare una bozza** (`email_outbox`) | solo se è `DRAFT` | spedita, simulata, in partenza, annullata: resta. Codice `E_DELETE_DOC_NON_BOZZA` |
| **aggiungere, modificare, togliere un allegato** | solo se la sua bozza è `DRAFT` | altrimenti `E_EMAIL_ALLEGATO_NON_BOZZA`, con il verbo tentato |
| **agganciare un allegato al log** (UPDATE del solo `email_log_id`) | sempre: è l'invio (bozza `READY`), e il nuovo tentativo dopo un fallimento | — |
| allegato **senza bozza ma con un log** | mai: è storia | `E_EMAIL_ALLEGATO_NON_BOZZA` |

* ⭐ **Invio fallito**: il BE riporta la bozza a `DRAFT` tenendo il log del
  tentativo. La bozza torna modificabile, allegati compresi, e il tentativo
  successivo li riaggancia al log nuovo. Il guard lo permette ed è provato
  (test 9).
* **Il CASCADE** bozza → allegati: in un `BEFORE DELETE` di allegato innescato
  dal cascade la bozza risulta già cancellata. Il guard dell'allegato passa, e
  a decidere è il guard della bozza, che il cascade lo ammette solo da `DRAFT`.

### 8.2 I changeSet

| # | File | Cosa fa |
| --- | --- | --- |
| 71 | `20_code/script/…-update-fn-get-stato-testata-documento-email-bozza` | il lettore `SECURITY DEFINER` dello stato impara `EMAIL_BOZZA`. La bozza ha la RLS, e un guard invoker non distinguerebbe «non c'è» da «non la vedo» |
| 72 | `20_code/vendite/…-update-trgfn-doc-guard-delete-solo-bozza-email` | ⭐ il **building block** «un documento si cancella solo in bozza» adotta la bozza email: stesso significato, stessa frase, stesso rimedio (regola del 2) |
| 73 | `20_code/config/…-create-trgfn-email-allegato-guard-solo-bozza` | il guard degli allegati |
| 74 | `20_code/config/…-create-trigger-email-guard-solo-bozza` | i due trigger, fascia `_a10_` |
| — | `80_data/sql/config/messaggi_errore.csv` (id 1139), `codici_errore.csv` | `E_EMAIL_ALLEGATO_NON_BOZZA`, `CONFLITTO_STATO`. La nota di `E_DELETE_DOC_NON_BOZZA` nomina la terza porta |

⚠️ **Perché non il BB delle righe** (`trgfn_doc_righe_lock_fuori_bozza`): la prima
metà del significato è la stessa, ma l'allegato ha un **secondo padre** (il log)
e un aggancio legittimo fuori dalla bozza. Il BB fermerebbe l'invio.
Allargarlo vorrebbe dire insegnare a un guard dei documenti di vendita
un'eccezione che nessun documento di vendita ha. Il **lettore** invece è
condiviso.
⚠️ Il BB della cancellazione vive in `vendite` ed è montato su una tabella di
`config`. È una dipendenza fra schemi, dichiarata nel changeSet: se il BB
crescerà ancora, la sua sede giusta sarà `script`.

### 8.3 Le prove (scratch, transazione annullata, SQL estratto)

* `config/test-email-guard-solo-bozza.sql` (**nuovo**): **13/13**. Senza i
  trigger (solo 71–73) dà **8 rossi**, esattamente sui rifiuti: il test vede
  l'assenza del guard.
* I due CSV sono emulati con due `INSERT` nella stessa transazione, perché il
  mirror gira solo al migrate.
* ⛔ **Alla corsa di Tid (applicato) il test 1 era rosso**: confrontava i nomi
  da `::regclass::text` / `::regproc::text`, che **tolgono lo schema** quando
  è nel `search_path`, e il runner ha `config` nel suo. La mia prova girava
  senza quel `search_path` e non lo vedeva. Riscritto coi nomi letti dal
  catalogo (`pg_namespace`), e riprovato sullo scratch con
  `SET search_path = config, …`: 13/13.
* Toccati e verdi prima e dopo: `rls/test-rls-email-ambito-reparto-operatore`
  22/22 (con FORCE), `vendite/test-delete-righe-documento-bozza-v1` 10/10,
  `vendite/test-trgfn-doc-righe-lock-fuori-bozza-v1` 21/21,
  `config/test-fn-resolve-email-account` 7/7, `config/test-fn-email-sistema`
  12/12, `dbops/test-presidi-debito-dichiarato` 8/8.
* **Due pgTAP riscritti**:
  * `config/test-fn-resolve-email-account`: per liberare l'account di sistema
    **cancellava** le sue mail. Su dbdev ci sono mail di sistema già spedite, e
    dal `-74` quel `DELETE` morirebbe. Ora le **stacca**
    (`email_account_id = NULL`): al test serve un account senza figli, non
    una storia cancellata. ⚠️ Sullo scratch non ci sono mail spedite: il caso
    di dbdev si vedrà alla corsa di Tid;
  * `rls/test-rls-email-ambito-reparto-operatore`: l'allegato «del log» nasce
    sulla bozza e si aggancia al log, come nell'applicazione. Il test 14 ora
    prova anche il ramo «log» della policy degli allegati: il processo vede
    solo l'allegato agganciato al log.
* `plpgsql_check`: il guard nuovo è pulito. Sul BB della cancellazione, provato
  contro `email_outbox`, esce `OLD.numero` del ramo DDT: il presidio lo
  classifica `FP_RAMO_ALTRA_TABELLA` (la funzione è montata su tre tabelle, e
  l'errore compare su una sola).

**Esito (Tid, 2026-09-25 sera):** migrazione applicata, pgTAP verdi (dopo la
correzione del test 1).

### 8.4 Richieste al BE (secondo giro)

1. **`remove_attachment`** non controlla che la bozza sia `DRAFT`. Ora lo ferma
   il DB, con un messaggio leggibile. Il BE può lasciarlo al DB, oppure
   spegnere il pulsante di rimozione sulle mail non in bozza, che è la cosa
   giusta per l'operatore.
2. ⚠️ **L'invio non allega i file.** `email_service` costruisce il messaggio
   con solo testo e HTML, e né `send_raw` né `send_pending_emails` leggono
   `config.email_allegato`. Gli allegati si salvano e si agganciano al log, ma
   non partono. Da verificare: è fuori dal perimetro DB.
3. **`cancel_draft`** cancella i file fisici degli allegati ma lascia le righe:
   dopo l'annullamento le righe puntano a file che non esistono. Col guard
   nuovo quelle righe non si possono più togliere (la bozza è `CANCELLED`).
   Se le righe vanno tolte, si tolgono **prima** di scrivere `CANCELLED`.

---

*Brief DB, 2026-09-25. Scritto dal team BE/FE aprendo la strada (a) del piano
endpoint-senza-porta. §4.1 e §6 scritti dal team DB lo stesso giorno.*
