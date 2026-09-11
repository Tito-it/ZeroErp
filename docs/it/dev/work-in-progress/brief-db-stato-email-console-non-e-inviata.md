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

*Brief del 2026-09-11. Le misure sono letture del dbdev e della macchina
`backend-dev` di quel giorno: valgono come controesempio, non come motivo. Il
motivo sta sul modello, ed è che «non ho potuto spedire» e «ho consegnato» sono
due fatti opposti e oggi si scrivono con la stessa parola.*
