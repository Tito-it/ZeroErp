# Brief — Il perimetro delle email, e come parte una email di sistema

> **Destinatario:** team DB (`dev/db-tid`) e backend.
>
> **Che cos'è.** L'**unico filo ancora aperto** del cantiere «nessun processo
> senza operatore». Tutto il resto è chiuso e archiviato in `work-done/`:
> l'analisi, il brief del disegno DB, gli otto residui e il piano BE/FE.
>
> ⭐ **Perché esce da lì.** Viveva nel §1-octies di un documento da 1.400 righe
> intitolato «gli otto residui», sette dei quali chiusi. Un filo vivo dentro un
> archivio non si legge: si perde.
>
> **Stato:** 🟢 **DB completo e applicato** (`20260906-01`, `-02`), test verdi —
> §6. ⇒ Resta **solo** il pezzo del §5: un punto del backend, e i due percorsi
> tornano a funzionare.

---

## 1. La decisione, e non è più in discussione

✅ **Chi legge le email di ambito `SISTEMA`** (reset password, alert — il loro
contenuto vale quanto una credenziale):

| | |
| --- | --- |
| fra le **persone** | solo il **super admin** |
| fra le **macchine** | l'**identità tecnica del processo che spedisce** |

⭐ Nel database *portare è leggere*: non esiste un modo di spedire una riga senza
vederla. Il postino non ha titolo a leggere la lettera, e deve comunque portarla.

✅ **E la mail di sistema parte SUBITO** (decisione di Tid, 2026-09-05). Non si
accoda in attesa del giro successivo del worker: un reset password che arriva un
minuto dopo è un reset password che l'utente ha già chiesto due volte.

---

## 2. Che cosa c'è già, e funziona

| | |
| --- | --- |
| `config.email_log` | RLS **accesa**, policy che ramifica su `ambito` (`20260905-41`…`-44`) |
| `config.email_outbox` | idem (`20260905-32`, `-37`) |
| `config.fn_accoda_email_sistema` | `SECURITY DEFINER`, scrive **solo** `ambito='SISTEMA'` con emittente `NULL` — ⭐ non è parametrica apposta: non è una porta per aggirare la policy. ✅ Dal `20260906-01` accetta anche `unita_organizzativa_id`, `destinatari_cc` e `pratica_id` |
| `config.fn_chiudi_email_sistema` | ✅ **nuova** (`20260906-02`): la gemella che scrive l'ESITO dell'invio. Tocca **solo** righe `SISTEMA` e **solo** i campi dell'esito |
| `script.fn_scope_identita_processo` | il ramo che fa leggere le `SISTEMA` all'identità tecnica di `send_pending_emails` |
| lato BE | `ambito` non ha più default in nessuna firma; `create_outbox` valorizza l'emittente; `send_pending_emails` gira col roster, un'azienda alla volta |

---

## 3. 🔴 Che cosa era rotto, misurato — *e che cosa manca perché non lo sia più*

> ⚠️ **Rilettura del 2026-09-06**: la tabella qui sotto è ancora vera, ma **non è
> più un vicolo cieco**. Le due porte che mancavano ci sono (§6): dal momento in
> cui il backend le usa (§5), il percorso senza sessione passa e le due righe
> rosse diventano verdi. Non serve altro dal database.

Chi riesce a scrivere una riga `SISTEMA` su `config.email_log`:

| percorso | esito |
| --- | --- |
| **nessuna sessione** — reset password (endpoint non autenticato) | ⛔ write-guard |
| **operatore non super admin** — invita un operatore o un utente portale | ⛔ policy |
| super admin | ✅ |
| identità tecnica di `send_pending_emails` | ✅ |
| `config.fn_accoda_email_sistema` senza sessione | ✅ |

⇒ **Reset password e inviti non funzionano.** Il rimedio esiste a metà.

---

## 4. Che cosa serve dal DB

### 4.1 ⛔ La metà mancante: l'invio, non solo l'accodamento

`fn_accoda_email_sistema` si chiama **accoda** e scrive `stato = 'PENDING'`. Ma la
decisione del §1 è che la mail **parta subito**: il backend, dopo aver scritto la
riga, tenta l'invio e poi deve **aggiornarne lo stato** (`SENT` / `FAILED`,
`tentativi`, `inviato_at`).

⛔ Quell'`UPDATE` è bloccato dalla stessa policy, per lo stesso motivo: chi
spedisce un reset password non ha una sessione.

**Che cosa serve.** Un modo, per il percorso senza sessione, di **chiudere** la
riga che ha appena scritto — l'esito dell'invio che ha appena tentato.

⚠️ **E non deve diventare una porta di servizio**: il pregio di
`fn_accoda_email_sistema` è che sa scrivere una cosa sola. La sua gemella
dovrebbe poter toccare **solo** una riga `SISTEMA` e **solo** i campi dell'esito.
La forma la decidete voi.

### 4.2 ⚠️ La funzione perde tre colonne che i chiamanti passano

`fn_accoda_email_sistema` non accetta `unita_organizzativa_id`,
`destinatari_cc`, `pratica_id`. Misurato: **tutti e tre** i chiamanti di sistema
passano `unita_organizzativa_id` (reset password × 2, invito operatore, invito
portale).

⇒ Instradando lì senza allargarla, quell'informazione **si perde in silenzio**
sulle email di sistema — che è peggio di un errore. O la funzione le accetta, o
si dichiara che su una `SISTEMA` non servono e si toglie dai chiamanti.

---

## 5. Che cosa fa il backend, quando arriva

Un punto solo — `EmailRepository.create_log` — instrada su
`fn_accoda_email_sistema` quando `ambito = 'SISTEMA'`, e `update_log_stato` sulla
gemella dell'esito. ⭐ Tutti e quattro i chiamanti passano di lì: non si tocca
nessuna delle quattro chiamate.

⚠️ Da fare **insieme** al §4.1: instradare solo l'`INSERT` sposterebbe la
rottura di due righe più in là, sull'`UPDATE`.

---

## 6. ✅ Risposta del team DB (2026-09-06)

> Fatte tutte e due. **Non serve altro dal database.**

### ✅ §4.1 — `config.fn_chiudi_email_sistema` (`20260906-02`)

La gemella che **chiude** la riga: `stato`, `errore`, `inviato_at`,
`tentativi + 1`. ⭐ Avete ragione che sono una cosa sola — instradare solo
l'`INSERT` avrebbe spostato la rottura di due righe più in là.

⛔ **E non è una porta di servizio**, in due modi che non si possono dimenticare:

* tocca **solo** righe di ambito `SISTEMA` — sta nella `WHERE`, non in un
  controllo che qualcuno può saltare;
* tocca **solo** i campi dell'esito. Non il destinatario, non il corpo, non
  l'ambito, non l'emittente.

⛔ **`PENDING` non è un esito ammesso**: questa chiude, non rimette in coda.
Ammetterlo vorrebbe dire poter **resuscitare** una email già chiusa.

⚠️ **E se la riga non è quella giusta, alza la voce** — un `UPDATE` che non trova
niente è muto per natura, e chi chiama crederebbe di aver chiuso qualcosa. I due
casi hanno **parole diverse**, perché hanno significati diversi:

| | |
| --- | --- |
| la riga non esiste | un identificativo sbagliato |
| esiste ma **non** è `SISTEMA` | ⛔ qualcuno sta usando la porta di sistema per una email di un'azienda |

⭐ Il secondo è il caso pericoloso, ed è l'**unico momento** in cui lo si può
notare: dirlo con la stessa frase del primo l'avrebbe sprecato.

⚠️ `tentativi + 1` lo fa la funzione **perché lo faceva `update_log_stato`**:
instradare dev'essere un cambio di indirizzo, non di comportamento. Se il
conteggio cambiasse, ve ne accorgereste dai numeri e non da un errore.

### ✅ §4.2 — le tre colonne: **si accettano** (`20260906-01`)

`unita_organizzativa_id`, `destinatari_cc`, `pratica_id`.

⭐ Delle due strade che lasciavate aperte abbiamo preso quella di allargare, e il
motivo è che **non sono perimetro, sono contesto**: l'unità organizzativa di un
invito dice a chi apparteneva la persona invitata, e serve a chi legge il
giornale — non a chi decide i permessi.

⛔ Toglierle dai chiamanti avrebbe voluto dire buttare via un'informazione che
qualcuno aveva deciso di scrivere: una decisione di dominio, presa per comodità
nostra.

⚠️ **Nota tecnica**: è stato un `DROP` + `CREATE`, non un aggiornamento. Tre
parametri nuovi con valore di default avrebbero reso **ambigua** la chiamata a
tre argomenti — le due forme sarebbero state entrambe valide. La firma vecchia
non esiste più.

### I test

| | |
| --- | --- |
| `db/pgtap/config/test-fn-email-sistema.sql` | **8** — le due porte, compreso il tentativo di chiudere una email di un'azienda |
| `db/pgtap/rls/test-rls-email-log-ambito.sql` | **6** — gira **come l'applicazione**, con la RLS attiva: l'operatore non vede le `SISTEMA`, scrive le proprie, e una di un'altra azienda si ferma **spiegando** |

⚠️ Il secondo file dichiara ciò che **non** prova: che l'identità tecnica veda
davvero le righe — servirebbe girare nei suoi panni. Prova che il ramo **ci sia**,
perché se sparisse la posta di sistema smetterebbe di partire in silenzio. Che
funzioni livello per livello lo prova `test-fn-scope-identita-processo.sql`.

### 🔵 Che cosa resta, ed è tutto vostro

Il §5: **un punto solo** — `EmailRepository.create_log` instrada su
`fn_accoda_email_sistema` quando `ambito = 'SISTEMA'`, e `update_log_stato` su
`fn_chiudi_email_sistema`. ⚠️ Insieme, come dite voi.

---

## 6-bis. 📌 Fuori tema: la programmazione dei job (2026-09-06)

> ⚠️ **Questo non è del cantiere email.** Sta qui perché è stato fatto lo stesso
> giorno e Tid ha chiesto di registrarlo, non perché c'entri.
> ⭐ Se cresce merita un brief suo — è la lezione scritta in cima a questo stesso
> documento: *un filo vivo dentro un documento che parla d'altro non si legge, si
> perde*.

### La domanda

*«Come ci assicuriamo che tutti i lavori abbiano una programmazione per essere
avviati?»* — l'unico buco che il cantiere dei processi automatici aveva lasciato
**dichiarato e scoperto**: i presidi guardano le **corse**, e un lavoro che
nessuno sveglia non ne produce.

### ⭐ La risposta non è dichiarare la cadenza: è confrontare due fonti

pgAgent sa **quando un job ha girato e quando girerà**. Il nostro giornale sa
**che cosa ha fatto**. ⇒ Quando le due cose non coincidono, **il job è girato e
non l'ha detto** — la firma esatta di R-12.

⛔ Dichiarare la cadenza su `dbops.processi` sarebbe stata una **seconda
scrittura** di ciò che pgAgent già sa, e due scritture prima o poi dissentono.

**`dbops.vw_processi_programmazione`** (`20260906-03`…`-05`, `-08`): per ogni
processo attivo — chi lo sveglia, quando girerà, quando ha girato secondo
pgAgent e secondo il giornale, e uno `stato` che dice se concordano.

| | |
| --- | --- |
| **11** | `OK` |
| **8** | `FUORI_PORTATA` — COMMAND e CODA: la loro sveglia vive fuori dal database |
| **3** | `GIRA_E_NON_REGISTRA` |

⚠️ `FUORI_PORTATA` **non significa «tutto bene»**: significa che il database non
può saperlo. Dirlo `OK` sarebbe una bugia rassicurante, ed è il modo più efficace
di non far guardare più nessuno.

### 🔴 Che cosa ha trovato, appena accesa

* **`apply_storicizza_weekly`** — R-12 confermato dal verso opposto: pgAgent dice
  che ha girato il 5 settembre, il giornale è fermo al **21 febbraio**. ⇒ Le corse
  ci sono state **tutte**: fallivano, e il `RAISE` cancellava il verbale.
* **`chiusura_scadenze_daily`** — ⛔ **buco mio**: il `20260905-25`, trasformandolo
  da esecutore a sveglia, ha messo una `SELECT` diretta e ha perso il wrapper.
  Il lavoro veniva accodato bene; della sveglia non restava traccia. ⚠️ Nessun
  test poteva prenderlo: guardavano tutti che il lavoro fosse accodato, e lo era.
* **`sync_auth_user_expired_daily`** — così da sempre: non ha **mai** scritto una
  riga di corsa.

⇒ I due wrapper mancanti sono stati scritti (`-06`, `-07`). ⚠️ I tre restano a
video finché non girano di nuovo: la vista riporta l'**ultima corsa nota**. Se
sabato mattina il panorama è verde, R-12 è chiuso anche sul campo.

### ⚠️ E un difetto che ho introdotto io, trovato da un presidio

`fn_get_pgagent_job_stato` era `SECURITY INVOKER`, con tanto di motivazione
scritta: *«chi legge deve avere il diritto, non glielo si presta»*. ⛔ Il
principio è giusto in generale; qui rendeva **la vista illeggibile proprio da chi
l'ha chiesta** — `zeroerp_app` non ha `USAGE` su `pgagent`.

⭐ L'ha trovato `test-riferimenti-morti-v1`, che compila le funzioni con
`plpgsql_check`. **Nessuna delle mie prove l'aveva visto**, perché giravano tutte
da `titodb`, che quei permessi ce li ha.

⇒ `-08` la porta a `SECURITY DEFINER` — porta stretta: tre campi innocui di un
job nominato. ⛔ Scartato il `GRANT` sullo schema `pgagent` all'applicazione:
avrebbe aperto anche `pga_joblog`, che contiene l'**output dei comandi eseguiti**.

⚠️ E resta un falso positivo **strutturale**, registrato con il suo perché
(`-09`): `plpgsql_check` compila col ruolo di chi lancia la suite, quindi **ogni**
`SECURITY DEFINER` che legge uno schema non concesso al chiamante darà lo stesso
errore. Chi ne troverà un altro sa che è questo.

### ⛔ Che cosa resta scoperto

**Il lavoro che non parte affatto, sui canali che pgAgent non sveglia.** Otto
processi su ventidue: `COMMAND` programmati da crontab, `CODA` svegliati dal
backend. Il panorama li nomina `FUORI_PORTATA` invece di darli per buoni — che è
tutto quello che il database può onestamente fare.

---

## 7. Da dove viene

Tutti in `work-done/`, archiviati il 2026-09-05:

* `analisi-db-be-processi-automatici-identita-e-perimetro.md` — le decisioni e il perché
* `brief-db-processi-automatici-identita-e-perimetro.md` — il disegno DB, sette fasi
* `brief-db-processi-automatici-residui-be.md` — gli otto residui: questo filo era il §1-octies
* `brief-db-storicizzazione-bersagli-spariti.md` — R-12, il job fermo da sei mesi
* `piano-be-fe-processi-automatici-identita-e-perimetro.md` — i lotti BE/FE
