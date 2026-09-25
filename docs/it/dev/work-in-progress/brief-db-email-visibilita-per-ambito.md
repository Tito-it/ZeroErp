# Brief DB — Le mail si vedono per ambito, non solo per emittente

> **Chi scrive:** backend/frontend (`dev/backend-tid`), 2026-09-25. **A chi:**
> Tid (decisioni, §4), poi team DB (`dev/db-tid`).
> **Origine:** [piano-be-fe-endpoint-senza-porta.md](piano-be-fe-endpoint-senza-porta.md)
> §3. Il 2026-09-25 Tid ha scelto la strada **(a)**: gli operatori devono poter
> vedere le mail del loro perimetro, a partire dalla sola lista.
> **Stato:** ✅ **D-1 → D-4 decise da Tid il 2026-09-25** (§4): tocca al team
> DB. ⛔ È il **prerequisito della schermata operatore**: il BE/FE non parte
> finché questo brief non è chiuso.
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

## 5. Cosa succede dopo (BE/FE, non in questo brief)

Quando la policy è chiusa, il piano riparte dal §2.3. Resta aperta una scelta
**BE**: con la RLS che porta tutto il perimetro, la **lista** del log (sola
lettura) può uscire dall'area `config`. L'**outbox** (spedire) resta sotto
`config` finché non esiste l'azione di processo `invia_email` (D15).

---

*Brief DB, 2026-09-25. Scritto dal team BE/FE aprendo la strada (a) del piano
endpoint-senza-porta.*
