# Brief DB — Una mail stampata a video non è una mail inviata

> **Chi scrive:** backend (`dev/backend-tid`), 2026-09-11.
> **Che cosa si chiede:** **un valore in più** nel `CHECK chk_email_log_stato` di
> `config.email_log`. Nient'altro.
> **Urgenza:** bassa — il caso pericoloso è già chiuso lato backend (§3). Questo
> chiude il residuo, che vive solo sugli host in `DEBUG`.

---

## 1. Come è nato, e non è un'ipotesi

Il 2026-09-10, chiudendo il cantiere dei presidi, il digest è stato dichiarato
**inviato** su un host dove la mail non era partita. Tre fatti insieme:

| | |
| --- | --- |
| `DJANGO_DEBUG` | `False` — host di esercizio, non sviluppo |
| `config.email_account.smtp_host` dell'account `SISTEMA` | `smtp.example.com`, cioè **il placeholder del seed** |
| `config.email_log.stato` della riga prodotta | **`SENT`** |

⛔ Nessuno se ne sarebbe accorto. Il giornale delle email diceva «inviata», il
pulsante «prova connessione» dell'amministrazione rispondeva **OK**, e nessun
presidio guarda oltre lo stato. L'unico modo di scoprirlo era **non vedere
arrivare la posta** — che è esattamente il guasto-per-assenza da cui nasce il
cantiere dei presidi.

⭐ È stato trovato di rimbalzo, provando la connessione SMTP prima di accendere
il digest. Non da un test, non da un allarme: da una persona che stava
guardando un'altra cosa.

## 2. Il difetto, in una riga di codice

`EmailDispatchService` aveva **due** canali — SMTP e «console» — e in «console»
cadevano **due situazioni opposte**:

* `DEBUG = True`: si stampa a video **di proposito**, perché lo sviluppo deve
  girare senza SMTP;
* host col placeholder su un host di esercizio: **configurazione che manca**.

Entrambe finivano su `update_log_stato(log_id, "SENT", …)`.

> **Un valore che dice «consegnata» su una cosa che non è partita non è un
> dettaglio di log: è la forma in cui un'assenza si traveste da esito.**

## 3. Che cosa ha già fatto il backend (2026-09-11)

I canali sono **tre**, e il terzo non aggiunge un caso: **separa** due casi che
c'erano già.

| Canale | Quando | Che cosa scrive |
| --- | --- | --- |
| `SMTP` | host reale, `DEBUG = False` | l'esito vero |
| `CONSOLE` | `DEBUG = True` | stampa a video, e **oggi scrive ancora `SENT`** ← il residuo |
| `NON_CONFIGURATO` | host vuoto/placeholder **fuori** da `DEBUG` | **`FAILED`** + il motivo in `errore`, e non stampa niente |

Chiusi con valori **già ammessi** dal `CHECK`, quindi senza aspettare nessuno:

* il ramo pericoloso scrive `FAILED` con un messaggio che dice **dove si
  rimedia** («Configurare l'account da Amm. Software → Email accounts»);
* `test_connection` **non risponde più OK** a un account che non può spedire —
  era il verde che ha ingannato una persona vera;
* `retry_log_entry` non ritenta contro un placeholder: sarebbe lo stesso guasto
  una seconda volta;
* il predicato del placeholder aveva una **seconda sede** in
  `email_views._derive_test_capability`, sotto un commento che dichiarava di
  averla centralizzata: ora è uno solo (`smtp_non_configurato`);
* sette test nuovi, **provati per mutazione**: spegnendo la correzione cadono
  tutti e sette.

## 4. 🔵 Che cosa si chiede — un valore, e la ragione

`chk_email_log_stato` ammette oggi **quattro** valori:
`PENDING`, `RETRY`, `SENT`, `FAILED`.

Nessuno dei quattro dice *«stampata a video invece che spedita»*:

* `SENT` afferma una consegna che non c'è stata — è il difetto;
* `FAILED` afferma un guasto che non c'è: in `DEBUG` quel comportamento è
  **voluto**, e marcarlo fallito riempirebbe di rossi finti ogni ambiente di
  sviluppo — cioè insegnerebbe a ignorare i rossi;
* `PENDING`/`RETRY` la rimetterebbero in coda all'infinito.

⇒ **Serve un quinto valore.** Proposta: **`CONSOLE`**.

```
-- forma proposta, il changeSet lo scrive il team DB
ALTER TABLE config.email_log DROP CONSTRAINT chk_email_log_stato;
ALTER TABLE config.email_log ADD CONSTRAINT chk_email_log_stato
  CHECK (stato = ANY (ARRAY['PENDING','RETRY','SENT','FAILED','CONSOLE']));
```

⚠️ **Sul NOME non ho una preferenza forte, e la decisione è vostra**: `CONSOLE`
dice il *canale*, mentre gli altri quattro dicono lo *stato del tentativo*.
L'alternativa coerente col resto del vocabolario sarebbe `NON_SPEDITA`. Quello
che conta è che **non sia `SENT`**.

⛔ **Nessun backfill.** Le righe storiche marcate `SENT` in console mode restano
come sono: riscrivere il passato direbbe che si sa quali lo erano, e non si sa.

## 5. Che cosa NON si chiede

* nessuna colonna nuova — il motivo sta già in `errore`, che è nullable;
* nessuna modifica alla RLS di `config.email_log`;
* nessun cambio a `config.email_account`: il placeholder del seed **resta**, ed
  è giusto che resti — è il modo in cui un'installazione nuova dichiara di non
  avere ancora un SMTP. Il difetto non era il placeholder: era chi lo leggeva.

## 5-bis. ⚠️ NOTA — non è una richiesta, ed è utile saperlo mentre decidete

In revisione è emerso che la `SELECT` di `send_pending_emails` ripesca anche i
`FAILED`, e vale la pena scriverlo qui perché tocca la riga di cui stiamo
parlando — **ma non chiede niente al team DB**.

```sql
WHERE (stato = 'PENDING'
       OR (stato IN ('FAILED', 'RETRY')
           AND tentativi < max_tentativi
           AND (prossimo_tentativo IS NULL OR prossimo_tentativo <= now())))
```

⭐ **E il ripescaggio è un BENE, non un difetto**: `tentativi` viene incrementato
dall'UPDATE dell'esito su **entrambe** le strade — `update_log_stato` e, per
l'ambito SISTEMA, `config.fn_chiudi_email_sistema` (che lo fa *«perche' lo faceva
update_log_stato: instradare dev'essere un cambio di indirizzo, non di
comportamento»*, come dice il suo `COMMENT`). Quindi con `max_tentativi = 3` la
riga si ferma da sé dopo tre giri — e **se l'SMTP viene configurato entro quei
tre tick la mail parte da sola**. È il recupero, ed è esattamente il caso
capitato il 2026-09-11, dove il digest era stato accodato prima dell'SMTP.

⛔ **Perciò NON serve poter scrivere `tentativi`/`prossimo_tentativo` per
chiudere subito la riga**: sarebbe la richiesta sbagliata — spegnerebbe il
recupero per risparmiare due tentativi che non costano niente (il ramo non apre
nemmeno una connessione).

⚠️ **Il limite vero sta a valle, ed è PREESISTENTE a questa modifica**: esaurito
il terzo tentativo la riga è terminale, e un rilancio a mano non esiste —
`retry_log_entry` ha un chiamante solo (quel command, che non la ripesca più) e su
`config.email_log` non c'è nessuna rotta di scrittura. Vale per **qualunque** mail
fallita, non per il solo placeholder: è la politica di retry del giornale.
⇒ Il rimedio, se lo si vuole, è un **verbo «rilancia»** sul giornale email: il
service esiste già, manca la rotta. **È lavoro di backend**, e lo registriamo
come tale — non come una vostra pendenza.

⭐ **Una riga di metodo, perché è il genere di cosa che questo progetto raccoglie.**
Il commento in `_registra_non_configurato` aveva scritto l'opposto — «non torna in
coda» — perché si fidava del commento in testa a `send_pending_emails`, che nomina
«PENDING o RETRY» e **omette `FAILED`**. La `SELECT` vera dice altro. *Un commento
non è una fonte, nemmeno quando è nello stesso repository.*

## 6. Il giorno dell'apply — il verso di ritiro è già armato

`_EMAIL_LOG_STATI_VALIDI` (backend) era un **mirror non presidiato**: niente lo
confrontava col `CHECK`. Dal 2026-09-11 c'è
`apps/amm_software/tests/db/test_email_log_stati_guardrail.py`, che lo confronta
via il BB `db_e2e.valori_check`.

⇒ **Appena applicate il changeSet quel test diventa rosso** e dice di allineare
il backend: il valore nuovo va aggiunto al `frozenset` **e** alla tabella delle
descrizioni (che alimenta il filtro del giornale email nel frontend), poi il ramo
`CANALE_CONSOLE` di `email_service` smette di scrivere `SENT`. Sono tre righe,
guidate dal presidio — non serve ricordarsele.

---

# Risposta del team DB — 2026-09-11

> **Chi scrive:** DB (`dev/db-tid`), 2026-09-11, dopo la revisione del brief
> aggiornato (§5-bis inclusa).
> **Esito:** ✅ **si fa**, e il valore si aggiunge.
> ⛔ **Ma NON è «un valore e nient'altro»: i cancelli sono due, non uno** (§7.2).

## 7.1 🔵 Le tre decisioni

| La domanda | La decisione |
| --- | --- |
| Come si chiama il quinto valore | **`SIMULATA`** |
| `inviato_at` sul ramo nuovo | resta **NULL** |
| `config.email_outbox` ha lo stesso difetto | si allarga **anche il suo `CHECK`**, in questo cantiere |

Il perché di ciascuna, qui sotto.

**Il nome — `SIMULATA`, e non `CONSOLE`.** La vostra obiezione al vostro stesso
nome era quella giusta: `CONSOLE` dice il **canale**, e ogni lettore della
colonna fa invece una domanda sull'**esito** — il cron chiede «la ripesco?»,
l'operatore chiede «è arrivata?», il filtro del giornale chiede «mostrami quelle
che non sono arrivate». ⛔ E lega il valore a **una** implementazione del
non-invio: `_send_console` è *un* modo di non spedire, e un secondo modo (un
capture di test, un file) chiederebbe un sesto valore per lo stesso fatto.

⚠️ Scartata anche `NON_SPEDITA`, che pure è sull'asse giusto: è un negativo che
**non discrimina** — anche `PENDING`, `RETRY` e `FAILED` sono «non spedite», e
il nome tace proprio sulle due cose che distinguono questo stato, cioè che è
**terminale** e che è **voluto**.

⭐ Sull'italiano non c'è nessun ostacolo, ed è il motivo per cui non abbiamo
tenuto un nome inglese per forza: `dbops.coda_lavori` ammette
`PENDING, IN_CORSO, FATTO, ERRORE, ANNULLATO`, e i tre esiti del digest sono
`NON_RICHIESTO / NON_CONFIGURATO / ACCODATO`. Il vocabolario misto esiste già, ed
è il vostro.

**`inviato_at` — NULL.** Oggi il ramo console scrive `inviato_at = now()`. Con
uno stato che dichiara il non-invio, quella colonna **sposterebbe la bugia di una
casella** invece di toglierla: resta l'unico campo che data una consegna, ed è
proiettato sia nella lista sia nel dettaglio del giornale. Il momento della
stampa c'è già in `data_insert`.
⭐ **Non serve niente dal DB**: `fn_chiudi_email_sistema` fa
`inviato_at = COALESCE(p_inviato_at, l.inviato_at)`, quindi su una riga appena
accodata basta che il backend passi `None` e la colonna resta NULL.
⛔ Non mettiamo un `CHECK` che lo imponga: sarebbe un vincolo nuovo, fuori dalla
vostra richiesta, e la sede della decisione è il ramo che scrive.

**L'outbox — si allarga anche quello.** In console mode
`EmailOutboxService.send_from_outbox` riceve `success = True` e scrive
`config.email_outbox.stato = 'SENT'`: **la stessa parola, la stessa bugia, una
tabella più in là**, e le due righe sono legate da `email_log_id`, quindi la
divergenza sarebbe leggibile a occhio nudo.
⛔ E non si può dire «l'outbox parla del ciclo della bozza, non della consegna»:
lo smentisce il ramo accanto, che su fallimento SMTP riporta la bozza a `DRAFT`
perché l'operatore riprovi. Quella colonna **parla di consegna**.
⭐ Allargarlo ora non aspetta nessuno e non rompe niente: è un widening puro, e
lato backend **non esiste** nessun mirror Python degli stati outbox da allineare
(verificato il 2026-09-11 — `AMBITI_OUTBOX` specchia l'*ambito*, non lo stato).
⚠️ L'adeguamento di `email_outbox_service` resta lavoro vostro, ma il vocabolario
non parte già diviso in due.

## 7.2 ⛔ Il secondo cancello — quello che il brief non vede

**`chk_email_log_stato` non è l'unica whitelist di `email_log.stato`.** Ce n'è
una seconda, nel corpo di `config.fn_chiudi_email_sistema`:

```sql
IF p_stato IS NULL OR p_stato NOT IN ('SENT', 'FAILED', 'RETRY') THEN
    ... 'E_VALIDAZIONE' ... 'stato ammesso solo fra SENT, FAILED e RETRY');
```

⚠️ §5-bis cita questa funzione per il `tentativi + 1` — cioè ne ha letto il
`COMMENT`, non il corpo. Letta dal dbdev il 2026-09-11:
`whitelist viva: 'SENT', 'FAILED', 'RETRY'`.

🔴 **E non è un ramo laterale: è la porta del digest.** Il ramo `CANALE_CONSOLE`
chiama `update_log_stato(log_id, <stato>, ambito=ambito)`, e
`EmailRepository.update_log_stato` instrada **ogni** chiusura di ambito `SISTEMA`
sulla funzione invece che sull'`UPDATE` diretto — giustamente, perché la RLS lo
rifiuterebbe. Il digest dei presidi e il reset password **sono** `SISTEMA`.

> ⇒ Allargato il solo `CHECK`, in `DEBUG` ogni email di sistema solleverebbe
> `E_VALIDAZIONE` invece di scrivere lo stato nuovo. Su **ogni** host di
> sviluppo, e proprio sul caso da cui nasce il brief.

⭐ **E l'invariante fra i due cancelli non è l'uguaglianza.** La funzione esclude
`PENDING` di proposito («questa chiude, non rimette in coda»). La regola vera è:

```
whitelist di fn_chiudi_email_sistema  =  valori di chk_email_log_stato  \  {PENDING}
```

È così che va scritto il presidio: un pgTAP che pretendesse l'uguaglianza secca
nascerebbe rosso e verrebbe spento il giorno dopo.

## 7.3 Il censimento dei lettori — fatto sul database, non sul repository

`pg_proc` + `pg_views` sul dbdev, 2026-09-11: **due** oggetti nominano
`config.email_log`.

| Oggetto | Cosa fa con `stato` | Tocca? |
| --- | --- | --- |
| `config.fn_accoda_email_sistema` | scrive il letterale `'PENDING'` all'INSERT | **no** |
| `config.fn_chiudi_email_sistema` | **whitelist propria** sugli esiti | 🔵 **sì** (§7.2) |

Nessuna vista, nessuna vista materializzata, nessun trigger che legga `stato`,
nessuna riga in `dbops.presidi` che nomini le email, nessun seed `ui.*` che
enumeri i valori (il filtro del giornale è alimentato dal vostro lookup, non dal
CSV: `ui.lista_colonna` proietta `stato` come stringa e `ui.lista_preset` non ci
filtra sopra).
✅ Il `CHECK` è già normalizzato dal catalogo in `= ANY (ARRAY[...])`, quindi il
vostro `db_e2e.valori_check` lo legge senza modifiche, scritto `IN` o `ARRAY`.

## 7.4 Il piano — tre changeSet, un pgTAP, la doc

| # | File | Che cosa fa |
| --- | --- | --- |
| 1 | `00_schema/config/20260911-06-alter-chk-email-log-stato-simulata-mctit.yaml` | `DROP`/`ADD` di `chk_email_log_stato` con il quinto valore |
| 2 | `00_schema/config/20260911-07-alter-chk-email-outbox-stato-simulata-mctit.yaml` | idem su `chk_email_outbox_stato` |
| 3 | `20_code/config/20260911-08-update-fn-chiudi-email-sistema-simulata-mctit.yaml` | `CREATE OR REPLACE` della funzione: **il secondo cancello** (§7.2) |

⚠️ **I numeri sono `06/07/08` e non `01/02/03`**, e vale la pena dire perche':
scritti i file col primo numero libero, `20260911-01..05` risultavano **gia'
occupati** dal cantiere RLS degli arrotondamenti, comparso sul ramo nel
frattempo. *Il numero changeSet «libero» scade nel minuto in cui lo si legge*: si
riguarda prima di salvare, non prima di iniziare.

⚠️ **L'ordine conta e non è cosmetico**: la funzione va **dopo** i due `CHECK`.
Al contrario, fra il changeSet 3 e il changeSet 1 esisterebbe una finestra in cui
la funzione accetta un valore che la tabella rifiuta — l'errore si sposterebbe da
`P0001` a `23514`, cioè da un messaggio di dominio a una violazione di vincolo
grezza a video.

**pgTAP** — `db/pgtap/config/test-fn-email-sistema.sql`, da `plan(8)` a `plan(11)`:

* **8.** la gemella **accetta** `SIMULATA` e chiude la riga;
* **8-bis.** e lo fa **senza scrivere `inviato_at`** — è la decisione di §7.1
  resa asserzione, sull'unica strada che il backend percorre per le righe di
  sistema;
* **9.** ⭐ l'**invariante** di §7.2: whitelist della funzione = valori del
  `CHECK` **meno** `PENDING`. È il presidio che mancava, ed è il motivo per cui
  il difetto era invisibile;
* **10.** `config.email_outbox` accetta `SIMULATA` (prova funzionale con una
  riga: su quella tabella la RLS è spenta, quindi la fixture non ha costo).

⚠️ I test 1..7 restano **intatti**: nessuno di essi pinna il numero dei valori
ammessi, quindi l'allargamento non li tocca. In particolare il **test 5**
(`PENDING` non è un esito) resta vero e diventa più importante, perché ora è
l'unica cosa che distingue le due liste.

**Documentazione** — `docs/it/dbzero/config/manual/email_log.md`:

* il ciclo di vita prende il ramo nuovo (`PENDING → SIMULATA`, terminale);
* ⚠️ e si corregge una riga **già sbagliata oggi**: dice che
  `send_pending_emails` «processa le email PENDING e RETRY», mentre la `SELECT`
  che avete citato in §5-bis ripesca anche i `FAILED`. È lo stesso commento
  stantio che ha ingannato `_registra_non_configurato` — *un commento non è una
  fonte*, e questa è la sua terza copia.

⛔ **Non si applica niente**: i changeSet si scrivono e si provano con l'SQL
estratto, l'`update` lo lancia Tid.

## 7.5 🔵 PASSAGGIO AL BACKEND — l'apply e' avvenuto, tocca a voi

> **Stato al 2026-09-11 11:43: il database ammette `SIMULATA` e nessuno lo
> scrive.** Il vocabolario c'è, il comportamento no — ed è la condizione voluta,
> non un lavoro a metà.

⇒ **Il vostro `test_email_log_stati_guardrail` è rosso adesso**, per costruzione,
e dice la prima cosa da fare. Oltre alle tre righe che il §6 già elenca:

1. 🔵 **`inviato_at` sul ramo `CANALE_CONSOLE`**: passare `None`, non `now()`
   (§7.1). Sono i **due** siti che scrivono l'esito in console —
   `send_raw` e `retry_log_entry`.
2. 🔵 **`EmailOutboxService.send_from_outbox`**: in console mode la bozza non è
   `SENT`. Il `CHECK` ammetterà `SIMULATA` dal giorno dell'apply.
3. ⚠️ **Il terzo mirror, che nessun presidio guarda**:
   `frontend/src/amministrazione/constants.js` mappa stato → severity del tag e
   ha un fallback `return 'info'`. ⛔ Quindi il valore nuovo **non si rompe: esce
   identico a `PENDING`**, cioè «in lavorazione», dopo tutto il lavoro fatto per
   non dire «consegnata». Serve un ramo suo (`secondary`/`contrast`) e la chiave
   i18n. Il commento «I 4 codici» in `EmailLogStatoSelect.vue` va con lui.
   ⭐ Il vostro guardrail nuovo copre il `frozenset` e le descrizioni: **si ferma
   al backend**, e questa è la riga che resta scoperta.

### ⚠️ Due cose da sapere prima di scrivere il codice

**Il nome è `SIMULATA` e non `CONSOLE`**, e la ragione sta in §7.1. Avete scritto
che la decisione era nostra e che l'unica cosa che conta è che non sia `SENT`:
l'abbiamo presa. ⛔ Se non vi convince, si riapre **adesso** — un valore si
rinomina con un changeSet finché nessuno lo scrive, e da domani no.

**La whitelist di `config.fn_chiudi_email_sistema` è la seconda sede del
vocabolario** (§7.2), ed è quella che il brief non vedeva. Ora è allineata e c'è
un pgTAP che le tiene insieme, ma vale come regola: *chi aggiunge un valore a
`chk_email_log_stato` deve aggiungerlo anche lì*, o quel valore resta
irraggiungibile per le righe di ambito `SISTEMA`.

### ✅ Come si verifica che il giro è chiuso

Non da un test verde: da un giro vero su un host in `DEBUG`.

1. far partire una email di sistema (un reset password, o `digest_presidi`);
2. `SELECT stato, inviato_at FROM config.email_log ORDER BY id DESC LIMIT 1`
   → deve dire **`SIMULATA` / `NULL`**, non `SENT` e non una data;
3. il giornale email deve mostrarla con un tag **suo**, non con quello di
   `PENDING` — è il punto 3 qui sopra, ed è l'unico che non ha un presidio.

## 7.6 Che cosa NON facciamo, e perché

* **Nessun backfill** — d'accordo con §4, e con una ragione in più: nemmeno
  `email_account_id` distinguerebbe le righe storiche, perché il placeholder sta
  sull'account `SISTEMA` che può essere stato configurato dopo.
* **Nessun codice errore nuovo**: `E_VALIDAZIONE` sulla funzione resta giusto
  anche col vocabolario allargato — lì c'è davvero un parametro fuori dai valori.
* **Nessun tocco a RLS, policy o guard**: `rls_email_log_ambito` ramifica
  sull'**ambito**, `trgfn_guard_emittente_scope` sull'**emittente**. Nessuno dei
  due legge `stato`.
* **Nessuna colonna nuova**, nessun `CHECK` che leghi `stato` a `inviato_at`,
  nessuna riga di seed.
* **Niente sul ripescaggio dei `FAILED`**: §5-bis ha ragione, è il recupero. E
  il «verbo rilancia» sul giornale è lavoro vostro — il DB non ha una pendenza lì.

## 7.7 ✅ Fatto — 2026-09-11

**Costruito.** Tre changeSet (`20260911-06`, `-07`, `-08`), il pgTAP da `plan(8)`
a `plan(12)`, e la doc manuale di `config.email_log` e `config.email_outbox`.

**Provato, con l'SQL ESTRATTO dagli YAML e non riscritto**, dentro
`BEGIN`/`ROLLBACK` sul dbdev:

| Cosa | Esito |
| --- | --- |
| I tre changeSet applicano e si ritirano puliti | ✅ |
| `fn_chiudi_email_sistema(id, 'SIMULATA')` chiude la riga | ✅ `stato=SIMULATA` |
| e **non** scrive `inviato_at` | ✅ `inviato_at=NULL`, `tentativi=1` |
| `PENDING` resta rifiutato, con la frase aggiornata | ✅ |
| un valore inventato lo ferma il `CHECK` | ✅ `23514` |
| `config.email_outbox` accetta `SIMULATA` | ✅ |
| invariante `whitelist = CHECK \ {PENDING}` | ✅ |
| I dodici test pgTAP | ✅ `ok 1..12` |
| I sei guardrail statici della CI | ✅ |

⭐ **E provato per MUTAZIONE, che e' la parte che conta.** Applicati i soli due
`CHECK` — cioe' **esattamente la richiesta letterale del brief**, «un valore,
nient'altro» — la suite non e' verde: cadono **quattro** test.

```
not ok  5. PENDING non e' un esito ammesso, e la frase elenca quelli che lo sono
not ok  8. SIMULATA e' un esito ammesso: la porta di sistema lo scrive
        died: P0001: Validazione fallita: stato ammesso solo fra SENT, FAILED e RETRY
not ok  8-bis. e la riga non porta la data di una consegna che non c'e' stata
not ok  9. la whitelist della funzione e' il CHECK meno PENDING
        have: {FAILED,RETRY,SENT}
        want: {FAILED,RETRY,SENT,SIMULATA}
```

⇒ Non e' una conferma di comodo: e' la prova che §7.2 descriveva un guasto reale
e non un'ipotesi. Il test 10 (outbox) resta verde, correttamente — quel valore
dipende dal suo `CHECK` e non dalla funzione.

✅ **Verificato anche l'ordinamento**: la preCondition di `20260911-08` vale `0`
sul database di oggi e `1` dopo `20260911-06`. Se qualcuno invertisse l'ordine, il
migrate si ferma con `HALT` invece di lasciare la finestra incoerente.

## 7.8 ✅ APPLICATO — 2026-09-11 11:43, e il lato DB e' CHIUSO

`databasechangelog`, che e' dove si legge se una cosa e' applicata:

```
20260911-06-alter-chk-email-log-stato-simulata       | EXECUTED | 2026-09-11 11:43
20260911-07-alter-chk-email-outbox-stato-simulata    | EXECUTED | 2026-09-11 11:43
20260911-08-update-fn-chiudi-email-sistema-simulata  | EXECUTED | 2026-09-11 11:43
```

Stato vivo, riletto dal catalogo dopo l'apply:

| Sede | Contenuto |
| --- | --- |
| `chk_email_log_stato` | `PENDING, SENT, FAILED, RETRY, SIMULATA` |
| `chk_email_outbox_stato` | `DRAFT, READY, SENT, CANCELLED, SIMULATA` |
| whitelist di `fn_chiudi_email_sistema` | `SENT, FAILED, RETRY, SIMULATA` — cioe' il `CHECK` **meno `PENDING`**, come vuole l'invariante |

**pgTAP: `Files=1, Tests=12, Result: PASS`. Nessuna regressione sulla suite.**

⇒ 🔵 **Da questo momento il vocabolario esiste nel database e nessuno lo scrive
ancora.** La palla e' al backend: §7.5.

---

*Brief del 2026-09-11. Le misure sono letture del dbdev e della macchina
`backend-dev` di quel giorno: valgono come controesempio, non come motivo. Il
motivo sta sul modello, ed è che «non ho potuto spedire» e «ho consegnato» sono
due fatti opposti e oggi si scrivono con la stessa parola.*
