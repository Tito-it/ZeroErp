# Brief DB — Quattro processi che non guarda nessuno

> **✅ CHIUSO — 2026-09-11.** DB (§10.9: otto changeSet `20260911-10..17`, pgTAP
> verdi) · BE (§11.3: i sei punti del §10.7, 4670 test verdi) · revisione
> critica (§11.4). Riletto sul dbdev alla chiusura: il panorama dà **`OK` su
> tutti i sette processi** (`run_fatturazione_batch` `FUORI_PORTATA` per
> decisione), `listen_cambio_reparto` compreso — la sua sessione porta
> `application_name` dal riavvio del servizio (20:06); `fn_conta_presidio` = 0
> sulle due viste nuove. Documento spostato in `work-done`.
>
> ⚠️ **Un residuo dichiarato, del team DB (`dev/db-tid`), una riga di CSV.** Il
> tipo `NOTIFICA_DIGEST_MUTO` risulta `attivo = true` **sul dbdev** (acceso a
> mano da `titodb` il 2026-09-11 alle 20:11, dopo la release dell'handler), ma
> il seed `80_data/sql/dbops/coda_lavori_tipi.csv` dice ancora `false` — nel
> tree, su `origin/Tito-dev` e su `origin/dev/db-tid`. Il mirror è
> `runOnChange`: **al prossimo `liquibase update` la riga torna spenta in
> silenzio** e il guardiano ricomincia a sollevare `E_JOB_TYPE_NON_ATTIVO`
> invece di accodare. ⇒ Va portato a `true` **nel CSV** (e la descrizione, che
> dice ancora «attivo=false FINCHE il backend non ha l handler», va riscritta
> nello stesso gesto): è la regola di AGENTS.md — *i dati di `80_data` si
> cambiano dal CSV, non con `UPDATE` diretti*. Segnalato qui perché non si
> scopra a un `MUTO` non notificato.
>
> **Chi scrive:** backend (`dev/backend-tid`), 2026-09-11. **A chi:** team DB.
> **Origine:** una domanda di Tid a valle del cantiere dei presidi —
> *«per i lavori che girano ogni minuto ci si accorge subito che non girano;
> per gli altri cosa si può fare?»*.
>
> **In una riga:** dei sei processi che il backend dichiara di svegliare, **due**
> hanno un presidio che si accorge se smettono di girare. Gli altri **quattro**
> no, e per tre di loro il rimedio è la stessa vista che esiste già per il primo.
>
> ⛔ **Il backend non può fare niente da solo**: tutte e quattro le mosse sono
> viste e righe di catalogo, cioè database. Ciò che il backend farà appena
> arrivano è al §7.

---

## 1. Come è nato, e la domanda era giusta

Chiuso il cantiere dei presidi (`brief-db-un-destinatario-per-i-presidi.md`),
Tid ha osservato che per i **drenatori** — quelli che girano ogni minuto — un
fermo si nota subito, perché il lavoro che serve non viene fatto.

⭐ **È vero, e c'è di più: quel caso è già presidiato**, e non da una persona.
`dbops.vw_coda_lavori_da_guardare` dice testualmente *«mai preso: il worker non
sta girando»* su un `PENDING` più vecchio di un'ora — natura `ZERO`, cadenza
`GIORNALIERA`, quindi finisce nel digest.

⚠️ **Ma la frequenza non è il criterio, e la prova sta nei fatti di questo
progetto**: `send_pending_emails` gira **ogni 5 minuti** — alta frequenza — ed è
rimasto **non installato** su `backend-dev` senza che nessuno se ne accorgesse
(§11.5 del brief dei presidi). Non perché sia raro: perché **nessuno aspetta una
mail entro un tempo preciso**.

> **Il discriminante non è «ogni quanto gira»: è «qualcuno aspetta l'esito, e in
> quanto tempo se ne accorge?»**

## 2. Il quadro — misurato il 2026-09-11 su `backend-dev`

| Processo | Cadenza | Che cosa lo presidia oggi | |
| --- | --- | --- | --- |
| `draina_coda_lavori` | 1 min | `vw_coda_lavori_da_guardare` + badge liveness | ✅ |
| `draina_coda_stampa` | 2 min | **solo** il badge in topbar — la vista gemella **non esiste** | 🟠 §4 |
| `send_pending_emails` | 5 min | **niente** | ⛔ §5 |
| `digest_presidi:giornaliera` | 1/g | il battito della corsa settimanale | ✅ |
| `digest_presidi:settimanale` | 1/sett | **niente** — il battito sta dentro di lui | ⛔ §6 |
| `listen_cambio_reparto` | sempre acceso | **niente** — scrive un run solo all'avvio | ⛔ §7-bis |
| `run_fatturazione_batch` ×2 | spenti | — | n/a |

I **13 job pgAgent** sono coperti da `vw_processi_programmazione_da_guardare`,
che li vede perché vivono dentro il database. Sui `COMMAND` quella vista dichiara
`FUORI_PORTATA`, ed è corretto: **il database non può vedere systemd**.

## 3. Il criterio: si presidia l'EFFETTO, non lo schedulatore

⭐ È già così che funziona per `draina_coda_lavori`: nessuno chiede a systemd se
il timer è acceso — si guarda **la coda che si accumula**. È più robusto, perché
intercetta anche il caso in cui il processo gira ma sbaglia, e non ha bisogno di
sapere niente dell'host.

⇒ Tre dei quattro buchi si chiudono così. Il quarto (§6) no, ed è il più
interessante.

⭐ **E c'è un effetto collaterale che vale da solo: presidiare l'effetto chiude
anche il buco del §11.5** del brief dei presidi — *«fra dichiarato e installato
non guarda nessuno»*. Un timer mai installato non ha un effetto: la coda si
accumula, le email restano ferme, il digest non arriva. ⇒ Non serve **nessuna**
interfaccia verso systemd per accorgersene: basta guardare il lavoro che non
viene fatto. *La domanda «il timer è acceso?» è tecnica; la domanda «il lavoro si
sta facendo?» è quella che interessa, e ha già una risposta a database.*

---

## 4. 🔵 RICHIESTA 1 — la coda stampa: un'asimmetria che grida

`vendite.fatture_stampa_coda` è la **gemella** di `dbops.coda_lavori`: stessa
forma, stessa bandiera `archiviato`, stesso codice errore, e a database esiste
perfino un pgTAP che confronta colonne, vincoli e trigger delle due *perché la
simmetria non resti una promessa*.

⛔ **Ma il presidio ce l'ha una sola delle due.** Se il drenatore della stampa si
ferma, le fatture restano in coda e il digest non dice niente.

**Serve** `vendite.vw_coda_stampa_da_guardare` con lo stesso predicato della
gemella (`ERRORE`, `IN_CORSO` da troppo, `PENDING` da troppo, e `NOT archiviato`),
più la riga a catalogo.

⚠️ **Due differenze vere fra le due tabelle, che il predicato deve affrontare:**

| | `dbops.coda_lavori` | `vendite.fatture_stampa_coda` |
| --- | --- | --- |
| colonne di tempo | `claimed_at`, `run_after`, `started_at`, `ended_at` | **solo** `data_insert` / `data_update` |
| stati | 5 (con `ANNULLATO`) | 4 |
| **RLS** | **no** | **sì** |

⇒ **D1** e **D2** al §8. E dalla RLS discende il perimetro: **`DEFINER`**.

## 5. 🔵 RICHIESTA 2 — le email che restano in coda

Nessuna vista guarda `config.email_log`. Se `send_pending_emails` non gira, le
email si accumulano in `PENDING` **per sempre**, in silenzio.

⛔ **Non è un'ipotesi: è successo.** Quel timer non era installato, e l'unico
motivo per cui non ci sono state conseguenze è che la coda era vuota.

**Serve** una vista sulle email **vive e vecchie** — `stato IN ('PENDING','RETRY')`
oltre una soglia — natura `ZERO`, cadenza `GIORNALIERA`.

⚠️ `config.email_log` **ha la RLS**: la vista va a perimetro **`DEFINER`**, o il
conteggio risponde zero per cecità — che è esattamente il difetto già pagato
sulle `riferimenti_morti` (§9.4 del brief dei presidi). ⇒ **D3**, **D4**.

## 6. 🔵 RICHIESTA 3 — chi guarda il guardiano

Il digest segnala tutti gli altri. **Se muore lui**, l'unica cosa che lo direbbe
è il battito — che sta **dentro** il digest.

> **Un digest morto non manda il messaggio che dice che è morto**, e l'assenza di
> una mail non si nota.

⭐ **La via d'uscita non passa da systemd**: pgAgent vive **dentro il database**,
cioè in un mondo che non muore insieme al backend. Un job pgAgent che legge
`maintenance.job_run_log` e chiede *«`digest_presidi` ha girato nelle ultime N
ore?»* chiude la ricorsione — è il guardiano dall'altra parte del muro.

⛔ **L'ostacolo è dove vive la soglia.** Oggi `tolleranza_minuti` sta in
`backend/deploy/sveglie.json`, un file sul server backend che pgAgent non può
leggere. Le uscite sono due, e la seconda tocca una decisione già presa:

1. il job pgAgent si porta la soglia **scritta dentro** → è una **seconda sede**
   dello stesso fatto, cioè il difetto che il cantiere delle sveglie ha appena
   tolto (⛔ sconsigliata, e la scriviamo solo per dichiararla scartata);
2. la **tolleranza** va a catalogo, su `dbops.processi`.

⚠️ **La 2 contraddice il §9.2 del brief dei presidi**, dove sta scritto che *«come
li si sveglia è un fatto di deploy e vive dove vive il deploy»* — ed è la ragione
per cui il team DB aveva rifiutato di dichiarare su quella tabella la cadenza dei
job pgAgent.

⭐ **Ma forse la contraddizione è apparente, e la distinzione vale la discussione**:

| Fatto | Natura | Dove |
| --- | --- | --- |
| **cadenza** — *quando* si sveglia | **deploy**: dipende dall'host, dal fuso, dal carico | `sveglie.json`, come oggi |
| **tolleranza** — *entro quanto* è tollerabile che taccia | **modello**: non cambia da macchina a macchina | ⇒ candidata al catalogo |

⇒ **D5**. È la domanda che vale più di tutto questo brief.

## 7-bis. 🔵 RICHIESTA 4 — il listener, che non ha cadenza

`listen_cambio_reparto` non è un timer: è un processo **sempre acceso** in
`LISTEN/NOTIFY`. Scrive **un solo run**, quello di avvio — decisione di Tid del
2026-09-05, con la ragione scritta: *«è vivo adesso?» è una domanda diversa da
«ha girato stanotte?», e ha una sede sua*.

⛔ **Il fatto è che quella sede non è mai stata costruita.** Se il servizio muore
alle 03:00, l'ultimo run resta quello dell'avvio e nessuno se ne accorge finché
qualcuno non cambia reparto a un operatore e la cosa non succede.

Le forme possibili sono due, e **nessuna delle due è gratis**:

* un **battito**: il listener scrive un segno di vita ogni N minuti. ⚠️ Cambia la
  decisione del 2026-09-05 e mette righe periodiche su `job_run_log` — che è il
  giornale delle **corse**, non un heartbeat;
* un **timestamp che si sovrascrive**, su una riga sola (`dbops.processi` o una
  tabella di stato). Non sporca il giornale, ma è un dato nuovo.

⇒ **D6**.

---

## 7. Che cosa fa il backend appena arrivano

| # | Cosa | Dove |
| --- | --- | --- |
| 1 | niente per §4 e §5: il pannello legge le `ZERO` **dal catalogo**, quindi le due viste nuove compaiono **da sole** | `presidi_repository.stato_presidi` |
| 2 | niente per il digest: filtra per **cadenza**, non per elenco di viste | `presidi_digest` |
| 3 | se passa la **D5**: leggere `tolleranza_minuti` dal catalogo invece che da `sveglie.json`, e togliere il campo dal file (una sede sola) | `apps.core.services.sveglie` |
| 4 | se passa la **D6**: il battito del listener | `notify_listener` |

⭐ **I punti 1 e 2 sono la prova che il catalogo era la scelta giusta**: due
presidi nuovi entrano nel pannello e nel digest **senza una riga di backend**.

## 8. 🟠 Domande aperte

| # | Domanda | Perché non la decide il backend |
| --- | --- | --- |
| **D1** | Per la coda stampa, «preso e mai chiuso» su quale colonna? Non c'è `claimed_at`: resta `data_update`, che però cambia **a ogni** update | è la semantica della tabella, e la possiede chi l'ha scritta |
| **D2** | La soglia di **un'ora** della gemella vale anche per la stampa, che gira ogni 2 minuti? Un'ora è 30 giri | dipende da quanto è tollerabile una stampa in ritardo — è dominio |
| **D3** | Per le email, quale soglia? E i `RETRY`, che hanno un **backoff** legittimo, entrano nel presidio o no? | un RETRY in attesa non è un guasto: serve il criterio |
| **D4** | Confermate **`DEFINER`** su entrambe le viste nuove (RLS su `email_log` e `fatture_stampa_coda`)? ⚠️ Conseguenza: il digest mostra il **numero** e non le righe | è la stessa scelta già fatta per `riferimenti_morti` |
| **D5** | ⭐ La **tolleranza di liveness** va a catalogo su `dbops.processi`, separandola dalla cadenza che resta nel deploy? | tocca una decisione già presa in senso opposto (§9.2) |
| **D6** | Il listener deve battere? Con quale cadenza, e su quale sede — `job_run_log` o un timestamp che si sovrascrive? | è una decisione di Tid, e cambia quella del 2026-09-05 |
| **D7** | Le due viste nuove hanno una `colonna_stato`/`stato_atteso` a catalogo, o restano `NULL` come `vw_coda_lavori_da_guardare`? | dipende da come si vuole leggere il conteggio |

## 9. Che cosa NON si chiede

* **nessuna interfaccia verso systemd**: valutata e scartata — `systemctl`
  risponde solo per la macchina che serve la richiesta, quindi con più host
  mostrerebbe «un host a caso», e in un container non esiste affatto. Il
  confronto fra dichiarato e vissuto non ha nessuno dei due problemi;
* **nessuna modifica ai drenatori né alle code**: le tabelle vanno bene come
  sono, mancano solo le viste che le guardano;
* **nessun backfill**: le righe vecchie restano come sono;
* **niente per `run_fatturazione_batch`**: è spento per decisione, e un timer
  spento non ha una liveness da presidiare.

---

# 10. 🔵 Risposta DB — lettura critica e piano, 2026-09-11

> **Chi scrive:** DB (`dev/db-tid`). Letto il brief contro il catalogo vivo del
> dbdev, non contro gli YAML: `dbops.presidi` e i suoi `CHECK`,
> `vw_processi_programmazione`, `maintenance.vw_job_run_da_guardare`, le due
> tabelle di coda, `config.email_log`, `deploy/sveglie.json`, e le decisioni
> già prese nei due brief precedenti (sveglia §8.6, presidi §7.3 / §9.2 / §11.5).

## 10.1 Che cosa regge, e che cosa no

**§1 e §3 reggono, e sono il pezzo migliore del brief.** «Si presidia l'effetto,
non lo schedulatore» è già il criterio della gemella, ed è più forte di
qualunque interfaccia verso systemd: prende anche il processo che gira e sbaglia.
Lo tengo come regola per tutte e quattro le richieste — **compresa la quarta**,
dove il brief non lo applica (§10.5).

**§4 regge, e la D1 non è una domanda: è già scritta nella tabella.** Su
`vendite.fatture_stampa_coda` **ogni** transizione di stato scrive
`data_update = now()` (claim → `IN_CORSO`, esito → `FATTO`/`ERRORE`/`PENDING`,
reaper), e su una riga `PENDING` o `IN_CORSO` nessun altro `UPDATE` è possibile —
`archiviato` è ammesso solo sugli stati terminali (`chk_..._archiviato_non_vivo`).
⇒ **`data_update` è il momento in cui la riga è entrata nello stato in cui si
trova.** Non è un ripiego: è *meglio* di `claimed_at`, perché misura da quando la
riga è tornata `PENDING`, non da quando è nata. ⭐ E il reaper del drenatore la usa
già così (`WHERE stato = 'IN_CORSO' AND data_update < now() - 30 min`): il
predicato del presidio e quello del recupero leggono la stessa colonna.

**§4, D2 — un'ora, come la gemella, e «30 giri» non è un argomento.** Il
`COMMENT` della gemella lo dice per esteso: *«le soglie di un'ora non vengono da
una misura ma dal fatto che il drenatore gira di continuo: una soglia dedotta dai
tempi di oggi si taglierebbe addosso al carico di oggi»*. La soglia del presidio
non è la tolleranza di liveness: è «oltre questo, qualcosa è chiaramente
sbagliato». Una stampa `PENDING` da un'ora con un drenatore ogni due minuti che
prende 500 righe a giro è un drenatore morto o un arretrato che nessuno ha
deciso. Le due soglie uguali tengono anche la promessa del pgTAP di simmetria.

**§5 regge, ma il predicato «viva» è sbagliato — e lo dice il vostro brief
gemello.** `stato IN ('PENDING','RETRY')` non è ciò che `send_pending_emails`
ripesca: §5-bis dell'altro brief ha appena scoperto che ripesca anche i **`FAILED`
con `tentativi < max_tentativi`**, e li ripesca **apposta** (è il recupero). Una
riga `FAILED/1` con l'SMTP configurato un'ora dopo e il cron morto resta lì per
sempre, e il presidio scritto come nel §5 **non la vede**.
⛔ E copiare la `WHERE` del cron nella vista sarebbe la **seconda sede** dello
stesso predicato — il difetto esatto che il §5-bis ha pagato (commento ≠ SELECT).
⇒ La definizione di «email ancora in coda» va scritta **una volta, nel database**:
`config.vw_email_in_coda`. Il presidio la proietta con la soglia; **il cron la
legge** al posto della sua `SELECT` (una riga di backend, §10.7). Da quel giorno
non ci sono più due sedi da tenere allineate.

**D3 — le soglie delle email.** Un'ora, stessa ragione del §4. Ma la colonna del
tempo cambia per stato, perché il backoff è legittimo: `PENDING` misura da
`data_insert` («nessuno l'ha mai presa»); `RETRY` e `FAILED` ripescabili misurano
da **`COALESCE(prossimo_tentativo, data_insert)`** — «era dovuta un'ora fa e
nessuno è passato». Un `RETRY` col prossimo tentativo fra dieci minuti non è un
guasto e non compare. ⚠️ `config.email_log` non ha `data_update`: non c'è una
colonna migliore.

**D4 — `DEFINER` su entrambe, e non è una scelta: è il modello.** Le due tabelle
hanno la RLS attiva. Le viste nascono `security_invoker = true` come le tre
sorelle già a perimetro `DEFINER` (`vw_af_senza_giro`, `vw_eventi_non_dichiarati`,
`vw_riferimenti_morti_da_sanare`): una persona le legge col **suo** perimetro,
`fn_conta_presidio` le conta da proprietario. Il digest porta il numero. ⚠️ Il
`security_invoker` va nel `CREATE VIEW` stesso: un `CREATE OR REPLACE` successivo
senza la clausola lo **azzera** (è già successo).

**D7 — `NULL`.** Sono viste che devono restare vuote; la colonna `motivo` è
informazione per chi legge, non uno stato da confrontare.

**§9 regge tutto.** Niente systemd, niente backfill, niente sulle code.

## 10.2 ⛔ §6 — il brief ha ragione sulla conclusione e sbaglia la premessa

**La premessa sbagliata: «il backend non può fare niente da solo».** Per §6 può.
`apps.core.services.sveglie` + `job_run_log` sono già un building block del
backend (è il badge di liveness dei due drenatori): generalizzarlo a tutte le
sveglie con `tolleranza_minuti` è un `for`, e il pannello dei presidi lo
mostrerebbe a ogni apertura. Zero database.

**Ma il pannello è un canale PULL, e la premessa di tutto il cantiere dei
presidi è che «guardare non è di nessuno».** Un presidio che qualcuno deve
aprire è il difetto da cui il digest è nato. ⇒ Per §6 serve un **push che non
stia dentro il digest**. La forma giusta è la **guardia reciproca**: il digest
guarda tutti; **qualcosa fuori dal backend** guarda il digest. pgAgent è quel
qualcosa — l'avete visto bene: vive dentro il database, e non muore con systemd.

⭐ **E qui la D5 si decide da sola, con una ragione più solida di
«tolleranza è modello»**: il guardiano dall'altra parte del muro **deve sapere
che cosa aspettarsi**, e l'unica cosa che legge è il catalogo. Non è che la
tolleranza *sia* modello in astratto — è che **il lettore che serve sta nel
database, quindi il dato deve stare dove lui legge**. Una sede sola resta una
sede sola: il campo **esce** da `sveglie.json`.

**Sulla distinzione cadenza/tolleranza, una correzione.** Non sono indipendenti:
il vostro stesso JSON scrive `1560 = un giro più due ore`. La lettura che regge
è un'altra: la tolleranza è il **contratto** del processo (*«se sto bene, lascio
un segno almeno ogni N minuti»*); la cadenza è **come il deploy lo onora**. Il
contratto è del software, uguale su ogni installazione ⇒ catalogo. Il modo di
onorarlo è dell'host ⇒ deploy. ⚠️ E il deploy può **violare** il contratto (un
timer più lento della tolleranza): quella è una verifica **vostra**, sul JSON
(§10.7), e non serve al DB.

⛔ **Il limite che D5 porta, e va dichiarato ora.** Il catalogo non sa quali
processi sono **accesi su questo host** (`abilita`). Oggi non morde: ogni sveglia
`abilita: true` è universale, e `run_fatturazione_batch` è spento **per decisione
di prodotto**, non per host — quindi a catalogo ha tolleranza `NULL` (= «non si
presidia»), e il giorno in cui si accende è una release, non un tweak. Il giorno
in cui un processo sarà acceso su un host e spento su un altro, la risposta non
è una colonna nel JSON: è un **registro di silenziamento** a database, come tutti
i debiti dichiarati di questa famiglia. Scritto qui perché non sembri una
dimenticanza.

**Che cosa il catalogo compra, oltre a §6.** Con la tolleranza a catalogo,
`vw_processi_programmazione` smette di dire `FUORI_PORTATA` ai `COMMAND` che
dichiarano un contratto: un `COMMAND` con l'ultima corsa più vecchia della
tolleranza è **`MUTO`**, e finisce in `da_guardare` — cioè nel pannello **e** nel
digest — senza nessuna vista nuova e nessuna riga di catalogo nuova. ⭐ E chiude
il **§11.5 del brief dei presidi** dal lato che il backend aveva lasciato aperto:
un timer dichiarato e mai installato non ha corse ⇒ `MAI_PARTITO` ⇒ presidio.
`maintenance.vw_job_run_da_guardare` lo aveva già scritto nel proprio `COMMENT`:
*«non vede il job che non parte affatto: per quello servirebbe che ogni processo
dichiarasse ogni quanto deve girare, e `dbops.processi` non ce l'ha»*. Adesso ce
l'avrebbe.

**Il push — e il brief non se lo chiede.** pgAgent **non spedisce** e **non
conosce il destinatario**: quello è di deploy (`.env.systemd`, decisione §9.2),
e resta lì. ⇒ Il guardiano non manda una mail: **accoda un lavoro** su
`dbops.coda_lavori` (`fn_accoda_lavoro`, con `idempotency_key` per non
accodarne due). Lo esegue `draina_coda_lavori` — il processo **più vivo** del
backend, ogni minuto, con badge in topbar — che manda la mail col destinatario
**suo**. Nessun indirizzo entra nel database. ⭐ È già un pattern di casa:
`20260905-25` è un job pgAgent che accoda su `coda_lavori`.
**Perimetro del guardiano: SOLO `digest_presidi`.** Tutto il resto lo guarda già
il digest; un guardiano generale sarebbe un secondo allarme sulle stesse cose.

## 10.3 ⛔ §7-bis — il listener ha una terza forma, e costa zero righe

Le due forme del brief (battito su `job_run_log`, timestamp che si sovrascrive)
sono entrambe **un processo che dichiara di essere vivo**. Ma un listener
`LISTEN/NOTIFY` tiene **una connessione aperta al database**, e quella
connessione è visibile in `pg_stat_activity` — con `application_name`,
`usename`, `backend_start`. Verificato sul dbdev: `application_name` si legge
anche **senza** `pg_read_all_stats`, da qualunque ruolo.

⇒ **Il segno di vita del listener è la sua connessione**: se il processo muore,
la sessione sparisce; se sta riconnettendo, non c'è — ed è vero. Non una
dichiarazione, un fatto. Nessuna riga sul giornale, nessuna tabella nuova, e la
decisione del 2026-09-05 (un solo run) **resta**: *«è vivo adesso?»* ha la sua
sede, ed è `pg_stat_activity`.

Costo lato backend: **una riga** — `application_name = 'listen_cambio_reparto'`
in `_get_conninfo()` (§10.7). Costo lato DB: il database deve sapere che per quel
processo il segno di vita è una **sessione** e non una **corsa** — e qui vale
quello che il brief della sveglia §8.6 aveva già scritto: *«che sia un listener
il database non lo sa… se serve, è una colonna»*. Serve.

## 10.4 Le decisioni prese dal DB, in una riga ciascuna

| # | Decisione |
| --- | --- |
| D1 | `data_update`: è l'ingresso nello stato corrente, per costruzione della tabella |
| D2 | un'ora, come la gemella — la soglia non deriva dalla cadenza |
| D3 | un'ora; `PENDING` da `data_insert`, `RETRY`/`FAILED` ripescabili da `COALESCE(prossimo_tentativo, data_insert)`; il predicato «in coda» sta in `config.vw_email_in_coda`, una volta sola |
| D4 | `DEFINER` su entrambe, `security_invoker = true` nel `CREATE VIEW` |
| D7 | `NULL`: viste che devono restare vuote |

## 10.5 🟠 Le domande a Tid — una alla volta, in questo ordine

| # | Domanda | Raccomandazione DB |
| --- | --- | --- |
| **Q1 (= D5)** | `tolleranza_minuti` va a catalogo su `dbops.processi`, e **esce** da `sveglie.json`? | **sì**, per la ragione di §10.2: il guardiano vive nel database e legge solo il catalogo. Col limite dichiarato su `abilita`. ✅ **Deciso da Tid, 2026-09-11: sì** |
| **Q2** | Il guardiano pgAgent del digest **accoda un lavoro** su `coda_lavori` che il drenatore esegue e spedisce col destinatario del backend? | **sì**: nessun indirizzo nel DB, e il canale è il processo più vivo. ✅ **Deciso da Tid, 2026-09-11: sì** |
| **Q3 (= D6)** | Il listener si presidia dalla **sessione** (`pg_stat_activity` + `application_name`), senza battito né tabella? | **sì**: è un fatto, non una dichiarazione, e la decisione del 2026-09-05 resta in piedi. ✅ **Deciso da Tid, 2026-09-11: sì** |

## 10.6 Il piano — due blocchi, il secondo dipende dalle risposte

### Blocco A — le due viste (non aspetta nessuna risposta)

| # | File | Che cosa fa |
| --- | --- | --- |
| A1 | `20_code/dbops/…-create-vw-fatture-stampa-coda-da-guardare` | la gemella: `ERRORE` / `IN_CORSO` > 1h / `PENDING` > 1h su `data_update`, `NOT archiviato`; `security_invoker`; `GRANT SELECT` a `zeroerp_app`; `COMMENT` che dichiara la natura |
| A2 | `20_code/config/…-create-vw-email-in-coda` | **la definizione unica** di «ancora in coda per il cron»: `PENDING`, `RETRY`, e `FAILED` con `tentativi < max_tentativi`, con la colonna `dovuta_dal`; `security_invoker`. ⚠️ **Non è un presidio**: è una vista di dominio, e sta in `config` |
| A3 | `20_code/dbops/…-create-vw-email-da-guardare` | il presidio: A2 con la soglia di un'ora su `dovuta_dal`, più il `motivo` |

⛔ **I presidi stanno in `dbops`, non nello schema della tabella che guardano** —
e il brief lo sbagliava (`vendite.vw_coda_stampa_da_guardare`). Non è una
preferenza: il test 2 di `test-catalogo-presidi-v1` legge il perimetro **dagli
schemi che compaiono nel catalogo**, e pretende che *ogni* vista di quegli schemi
sia a catalogo. Una riga `vendite.vw_…` porterebbe dentro tutte le `vw_*_lista`
di `vendite` — decine di righe `INVENTARIO` da dichiarare per un presidio solo.
È la stessa ragione per cui `vw_af_senza_giro` e `vw_eventi_non_dichiarati`
leggono `vendite.*` e vivono in `dbops`.
| A4 | `80_data/sql/dbops/presidi.csv` | due righe: `ZERO`, `GIORNALIERA`, `DEFINER`, stato `NULL`, nota che dice il perché |
| A5 | pgTAP | `vendite/test-vw-fatture-stampa-coda-da-guardare.sql` **gemello riga per riga** di `dbops/test-vw-coda-lavori-da-guardare.sql` (7 test: i tre motivi, le due soglie, archiviato; ⚠️ niente `ANNULLATO`, che la stampa non ha); `config/test-vw-email-da-guardare.sql` (PENDING vecchia, RETRY con backoff non ancora dovuto **non** compare, FAILED ripescabile compare, FAILED terminale **non** compare, SENT/SIMULATA no); il test del catalogo (`test-catalogo-presidi-v1`) diventa rosso da solo senza A4 — è il verso giusto |
| A6 | doc manuale | `vendite/manual/vw_fatture_stampa_coda_da_guardare.md`, `config/manual/vw_email_in_coda.md`, `config/manual/vw_email_da_guardare.md` |

### Blocco B — il contratto di liveness (se Q1 = sì)

| # | File | Che cosa fa |
| --- | --- | --- |
| B1 | `00_schema/dbops/…-alter-processi-contratto-liveness` | `tolleranza_minuti integer NULL CHECK (> 0)`, ammesso solo su `canale = 'COMMAND'`; `segno_di_vita text NOT NULL DEFAULT 'GIORNALE' CHECK IN ('GIORNALE','SESSIONE')` (se Q3 = sì); `SESSIONE` ⇒ tolleranza `NULL` |
| B2 | `80_data/sql/dbops/processi.csv` | ⚠️ le due colonne nuove entrano nel CSV senza toccare il mirror `20260904-13`: `loadUpdateData` carica ogni colonna dell'intestazione, la lista `columns` è solo un override di tipo (è così che `jobname_pgagent` è arrivato). I valori: `draina_coda_lavori` 10, `draina_coda_stampa` 10, `send_pending_emails` 30, `digest_presidi` 11520 (la più larga delle due corsie, come dice il JSON), `run_fatturazione_batch` `NULL`, `listen_cambio_reparto` `SESSIONE`. ⚠️ E si corregge la descrizione di `send_pending_emails`, che dice ancora «`config.email_outbox`» mentre legge `email_log` (lo dice `processi_bersagli` dal 2026-09-05) |
| B3 | `20_code/dbops/…-update-vw-processi-programmazione-muto` | `COMMAND` con contratto: `OK` / **`MUTO`** / `MAI_PARTITO`; `SESSIONE`: `OK` se esiste una sessione con `application_name = codice`, altrimenti `MUTO`; `FUORI_PORTATA` resta per i `COMMAND` **senza** contratto. `da_guardare` nello stesso `CASE`, come oggi |
| B4 | pgTAP | `dbops/test-vw-processi-programmazione.sql`: il test 7 cambia (un `COMMAND` con contratto **non** è più `FUORI_PORTATA`); tre test nuovi: `MUTO` su corsa vecchia, `OK` su corsa fresca, `SESSIONE` letta da `pg_stat_activity` (la sessione del test stesso, con `SET application_name`) |
| B5 | `80_data/sql/dbops/coda_lavori_tipi.csv` (se Q2 = sì) | tipo `NOTIFICA_DIGEST_MUTO`, `attivo = false` **finché il backend non ha l'handler** — è la regola del binding |
| B6 | `85_pgagent/…-create-pgagent-job-guardiano-digest` (se Q2 = sì) | ogni ora: se `digest_presidi` è `MUTO` sul panorama, `fn_accoda_lavoro('NOTIFICA_DIGEST_MUTO', …, p_idempotency_key => 'guardiano_digest:' || giorno)`. Un lavoro al giorno al massimo. ⚠️ `MARK_RAN` in CI come i fratelli |
| B7 | doc manuale | `dbops/manual/processi.md` (le due colonne e il limite su `abilita`), `dbops/manual/vw_processi_programmazione.md` (`MUTO`) |

### 10.7 Che cosa tocca al backend, a valle

| # | Cosa | Perché |
| --- | --- | --- |
| 1 | `send_pending_emails` legge `config.vw_email_in_coda` al posto della sua `SELECT` | una sede sola per «in coda» — è la lezione del vostro §5-bis |
| 2 | `tolleranza_minuti` **esce** da `sveglie.json`; `apps.core.services.sveglie` la legge dal catalogo | una sede sola (se Q1 = sì) |
| 3 | un test: per ogni sveglia con `oncalendar`, l'intervallo ≤ tolleranza del processo | il deploy non può violare il contratto in silenzio |
| 4 | `application_name = processo_codice` in `notify_listener._get_conninfo()` | una riga (se Q3 = sì) |
| 5 | handler del tipo `NOTIFICA_DIGEST_MUTO`: una mail a `PRESIDI_DIGEST_DESTINATARIO` | il destinatario resta vostro (se Q2 = sì) |
| 6 | niente per §4 e §5 nel pannello e nel digest | le due viste entrano dal catalogo, come avete scritto |

⛔ **Non si applica niente**: i changeSet si scrivono e si provano con l'SQL
estratto in transazione ritirata; l'`update` e i pgTAP li lancia Tid.

## 10.8 ✅ Fatto e APPLICATO — 2026-09-11 12:42

**Otto changeSet** (`20260911-10` … `-17`, numerati dopo il cantiere arrotondamenti
che occupava `01..09`), **tre CSV**, **quattro pgTAP**, **sei pagine di manuale**.
Tid ha applicato mentre i test venivano scritti: `databasechangelog` ha i nove id
`EXECUTED` alle 12:42 e i tre mirror `RERAN`; i seed sono a bordo (due righe in
`presidi`, `guardiano_digest` in `processi`, `NOTIFICA_DIGEST_MUTO` spento nei
tipi, il contratto sui `COMMAND`).

| # | Che cosa | Dove |
| --- | --- | --- |
| A2 | `config.vw_email_in_coda` — la definizione unica, con `dovuta_dal` | `20_code/config/20260911-10` |
| A3 | `dbops.vw_email_da_guardare` — il presidio (soglia 1h) | `20_code/dbops/20260911-11` |
| A1 | `dbops.vw_fatture_stampa_coda_da_guardare` — la gemella | `20_code/dbops/20260911-12` |
| B1 | `dbops.processi.tolleranza_minuti` + `segno_di_vita`, quattro `CHECK` | `00_schema/dbops/20260911-13` |
| B3 | `vw_processi_programmazione`: `MUTO`, contratto, `SESSIONE`, tre colonne in coda | `20_code/dbops/20260911-14` |
| B6 | `dbops.fn_guardiano_digest()` | `20_code/dbops/20260911-15` |
| B6 | `maintenance.proc_guardiano_digest_job()` — passa dal giornale | `20_code/maintenance/20260911-16` |
| B6 | job pgAgent `guardiano_digest`, ogni ora al minuto 20 | `85_pgagent/20260911-17` |
| A4/B2/B5 | `presidi.csv` (+2), `processi.csv` (+2 colonne, +`guardiano_digest`, descrizione di `send_pending_emails` corretta), `coda_lavori_tipi.csv` (+1, `attivo=false`) | `80_data/sql/dbops/` |

**Provato prima dell'apply, con l'SQL estratto in transazione ritirata**: gli otto
changeSet applicano puliti; il panorama dà `OK` / `MUTO` / `MAI_PARTITO` /
`FUORI_PORTATA` come da tabella; una sessione che si presenta col codice del
processo porta il listener a `OK`; il guardiano torna `DIGEST_OK` a digest vivo,
**solleva** `E_JOB_TYPE_NON_ATTIVO` a digest muto col tipo spento, accoda
(`SISTEMA`, chiave del giorno, payload con `muto_da`) col tipo acceso, e dice
`GIA_NOTIFICATO_OGGI` alla seconda chiamata; le email danno i quattro casi
attesi; la stampa i tre; `fn_conta_presidio` conta entrambe le viste nuove. I sei
guardrail statici della CI sono verdi.

### ⚠️ Tre cose emerse costruendo, che il piano non diceva

1. **`pg_stat_activity` è una fotografia per transazione**: la prima lettura la
   fissa, e un `SET application_name` successivo non la aggiorna finché non si
   chiama `pg_stat_clear_snapshot()`. Un lettore vero (pannello, digest) legge in
   una transazione sua e non ha il problema; il pgTAP sì, e lo dichiara.
2. **`data_update` non è un vincolo**: l'audit trigger lo porta a `now()` a ogni
   scrittura, e la D1 regge perché sulle righe vive il drenatore fa **solo**
   transizioni — un comportamento, non un `CHECK`. Una scrittura non di stato
   azzererebbe l'orologio: il presidio tacerebbe un'ora in più, non suonerebbe a
   vuoto. Scritto nel `COMMENT` e nel manuale. ⇒ Il pgTAP della stampa gira da
   owner e **spegne l'audit trigger nella transazione** per retrodatare.
3. **Una riga viva per fattura** (`uq_fatture_stampa_coda_vivo`): la fixture della
   stampa vuole quattro fatture libere dell'operatore, e dove non ci sono lo
   dichiara con `skip()`.

### 🔴 Una riga che il digest mostra da subito — ed è il verso di ritiro

* **`listen_cambio_reparto` → `MUTO`** finché il backend non si presenta con
  `application_name = 'listen_cambio_reparto'` (§10.7 punto 4). Non è un falso
  allarme dal punto di vista del database: *«non vedo nessuna sessione con quel
  nome»* è vero. È la riga che dice al backend che cosa fare.
* ~~`guardiano_digest` → `MAI_PARTITO`~~ — **chiuso da solo**: il job gira ogni
  ora dalle 13:20 (verificato alle 18:20: tre corse consecutive `ok`, `done`),
  e il panorama lo dà `OK`.

## 10.9 ✅ CHIUSO LATO DB — 2026-09-11, sera

Stato vivo, riletto dal dbdev:

| Processo | Stato | |
| --- | --- | --- |
| `digest_presidi` | `OK` | contratto 11520 min |
| `draina_coda_lavori` · `draina_coda_stampa` · `send_pending_emails` | `OK` | contratto 10 · 10 · 30 min |
| `guardiano_digest` | `OK` | PGAGENT, tre corse `ok` |
| `run_fatturazione_batch` | `FUORI_PORTATA` | senza contratto, spento per prodotto |
| `listen_cambio_reparto` | **`MUTO`** | ⇒ backend, §10.7 punto 4 |

`fn_conta_presidio('dbops.vw_email_da_guardare')` = 0 ·
`fn_conta_presidio('dbops.vw_fatture_stampa_coda_da_guardare')` = 0: le due
viste nuove sono vuote come devono. pgTAP verdi, guardrail verdi, guida per le
persone aggiornata (`processi-automatici-classe-e-identita.md`: il limite
«FUORI_PORTATA sui COMMAND» non c'è più, e la tabella delle viste porta le
tre nuove).

**Tutto ciò che resta è del backend, ed è in §10.7.** Il primo rosso che vedrà
è la riga `MUTO` del listener nel digest — una riga di codice la spegne.


### I pgTAP — lanciati da Tid, ✅ verdi (2026-09-11)

Tre correzioni dopo la prima corsa, tutte del test e non del modello: `like` →
`alike` (in pgTAP `like` è una parola chiave), un apostrofo non raddoppiato, e la
fixture della stampa che sul database ricostruito da zero moriva **prima** dello
`skip()` — per due cause distinte, entrambe «CI = database da zero»:
`fn_pgtap_emittente_operatore()` solleva senza emittenti (e un `CASE` in una
query non basta: il pianificatore può eseguire una funzione `STABLE` già in fase
di stima, quindi la chiamata è diventata procedurale dentro un `IF`), e l'audit
trigger nasce da `ci_apply` e sulla CI può non esistere (si spegne solo se c'è,
letto da `pg_trigger`). ⭐ Il file ora arriva allo `skip()` dove i tre fratelli
(`test-coda-archiviazione`, `test-rls-fatture-stampa-coda*`) restano
`ERRORE_FIXTURE` in baseline.

| File | Plan | Runner |
| --- | --- | --- |
| `db/pgtap/dbops/test-vw-email-da-guardare.sql` | 8 | owner (retrodata `email_log`, rilegge le righe di sistema) |
| `db/pgtap/dbops/test-vw-fatture-stampa-coda-da-guardare.sql` | 6 | owner (spegne l'audit trigger nella transazione); `skip()` senza 4 fatture libere |
| `db/pgtap/dbops/test-fn-guardiano-digest.sql` | 9 | owner (scrive `job_run_log`, cambia `coda_lavori_tipi.attivo`) |
| `db/pgtap/dbops/test-vw-processi-programmazione.sql` | 13 → **19** | owner (già) — test 7 riscritto in due, cinque nuovi (14..18) |

E il **test 2 di `test-catalogo-presidi-v1`** deve restare verde: le due viste
nuove sono in `dbops` e a catalogo.

---

# 11. 🔵 Lato backend — esecuzione del §10.7 (2026-09-11)

> **Chi scrive:** backend (`dev/backend-tid`). Il DB ha chiuso; qui c'è la
> lettura critica di ciò che è cambiato rispetto alla proposta (§11.1), una
> scelta di Tid che il piano non registrava (§11.2) e il log dei sei punti.

## 11.1 Che cosa è cambiato rispetto alla proposta — in una riga ciascuno

| Proposta (§1–§9) | Deciso/consegnato (§10) | Effetto BE |
| --- | --- | --- |
| presidio stampa in `vendite.` | in `dbops.` — il catalogo legge il perimetro per schema | nessuno |
| email: `PENDING`/`RETRY` | predicato sbagliato (ometteva i `FAILED` ripescabili); definizione **una sola volta** in `config.vw_email_in_coda`, presidio in `dbops.vw_email_da_guardare` | il cron legge la vista (§10.7-1) |
| D5 «tolleranza è modello» | sì, ma per un'altra ragione: **il lettore che serve sta nel DB**. Tolleranza = contratto del processo; cadenza = come il deploy lo onora, e può violarlo | catalogo al posto del JSON (§10.7-2) + test contratto ≤ deploy (§10.7-3) |
| §6 «il BE non può fare niente» | premessa sbagliata, conclusione giusta (il pannello è PULL): costruito il **push** — guardiano pgAgent → `NOTIFICA_DIGEST_MUTO` su `coda_lavori`, tipo spento fino all'handler | handler (§10.7-5) |
| D6 battito **o** timestamp | terza forma a costo zero: la **sessione** in `pg_stat_activity` | `application_name` (§10.7-4). ⚠️ Fino ad allora `listen_cambio_reparto` è `MUTO` nel panorama, e finisce nel digest |
| §3 «§11.5 si chiude per effetto» | si chiude **dal DB**, direttamente: `MAI_PARTITO` su un `COMMAND` con contratto | nessuno |

## 11.2 ⚠️ Un limite accettato: il contratto ha la grana del PROCESSO, il giornale quella della CORSIA

Il giornale registra `<codice>:<corsia>` (`digest_presidi:giornaliera` e
`:settimanale` sono due righe); il catalogo ha **una** `tolleranza_minuti` per
processo. ⇒ Il panorama dice `MUTO` solo quando **tutte** le corsie tacciono
oltre l'unica tolleranza, e il battito del digest giudica ogni corsia contro
quel numero: la giornaliera è «ferma» dopo 8 giorni (11520), non dopo 26 ore.

**Per chi morde:** solo per i processi con **più di una sveglia** — oggi
`digest_presidi` (2 corsie attive, cadenze 24h/7g) e `run_fatturazione_batch`
(2 corsie spente, tolleranza `NULL`, niente da presidiare). Gli altri quattro
sono 1 processo = 1 unit = 1 jobname: nessuna perdita. Il giorno in cui un
altro processo prende una seconda corsia, il limite si ripresenta lì.

**Non è una perdita nuova nel comportamento — è una perdita nell'opzione.** Il
codice collassava già a processo (`sveglie.tolleranza_minuti()` = `max` fra le
corsie: «basta che una abbia girato»); il JSON però **portava il dato per
unit** (1560 e 11520), e nessuno lo leggeva a quella grana. Con D5 il secondo
numero sparisce dal modello: per tornare a giudicare la giornaliera da sola non
basterebbe più un `for` nel backend.

⭐ Resta intero, per corsia, il segnale più forte dei due: **«mai girata»**
(nessuna riga nel giornale) non ha bisogno di una tolleranza, e il battito lo
mostra già. Fatto datato: il 2026-09-11 `digest_presidi:settimanale` non ha
corse negli ultimi 30 giorni, e il battito lo dice così.

✅ **Deciso da Tid, 2026-09-11: il limite si accetta.** Se un giorno servirà la
giornaliera sulla sua cadenza, la sede è il modello a DB — un contratto a grana
corsia (`dbops.processi_corsie`, stessa convenzione `<codice>:<corsia>` del
giornale), **non** una tolleranza per unit rimessa nel deploy: sarebbe la
seconda sede che il §10.2 ha appena tolto. Scritto qui, accanto al limite su
`abilita` (§10.2), perché non si legga come una dimenticanza.

## 11.3 ✅ Fatto lato backend — 2026-09-11, sera

Tutti e sei i punti del §10.7. **4670 test verdi** (dopo la revisione §11.4), `ruff` pulito. Ogni
punto è provato dove si può provare: sul DB vero in transazione ritirata dove
la prova è un binding, con un test senza database dove è una regola.

| § | Cosa | Dove | Prova |
| --- | --- | --- | --- |
| 10.7-4 | `application_name = PROCESSO_LISTEN_CAMBIO_REPARTO` nella conninfo del listener — il nome è la **costante**, non un letterale | `anagrafiche/services/notify_listener.py` | `test_conninfo_porta_il_codice_del_processo_come_application_name` legge la stringa che psycopg costruisce davvero. ⚠️ **Il servizio va riavviato** (`zeroerp-listen-cambio-reparto`, `sudo`): finché gira il processo vecchio, la connessione non porta il nome e il panorama resta `MUTO` |
| 10.7-1 | `send_pending_emails` legge `config.vw_email_in_coda`: **nessuna `WHERE` sullo stato** nel command | `core/management/commands/send_pending_emails.py` | `--dry-run` reale → 0 in coda (= `fn_conta_presidio`); `test_send_pending_emails_predicato_in_una_sede` vieta che il predicato ricompaia nel sorgente (`FROM config.email_log`, `stato IN (`, `tentativi < max_tentativi`, `prossimo_tentativo`) |
| 10.7-2 | Tolleranza dal catalogo: `ProcessiRepository.contratti_liveness(codici)` / `.tolleranza_minuti(codice)`; `_liveness_worker` e `_leggi_battito` la leggono da lì; `sveglie.tolleranza_minuti` **non esiste più**; il campo è **uscito** dalle 8 voci di `sveglie.json` e `carica_sveglie` **rifiuta** il file se ricompare (anche a `null`: la chiave stessa è la seconda sede) | `core/db/processi_repository.py`, `core/services/sveglie.py`, `deploy/sveglie.json`, `coda_lavori/gestione_service.py`, `presidi_digest.py` | Repository provato sul dbdev (10 / 10 / 30 / 11520 / `SESSIONE` senza tolleranza / `ignoto` assente); `test_sveglie` 5 (rifiuto) e 9 (i drainer hanno un contratto **nel seed**); `test_presidi_digest` 13 inietta il catalogo finto e verifica che il battito chieda `digest_presidi` |
| 10.7-3 | `test_contratto_liveness_vs_deploy`: per ogni timer con contratto, `intervallo_massimo(OnCalendar) ≤ tolleranza` **dal seed `processi.csv`**, non dal DB; più `SESSIONE ⇔ servizio`, «ogni `COMMAND` con contratto ha una sveglia accesa», «il parser conosce ogni `OnCalendar` in uso» (solleva su forma ignota). Supporto in `core/tests/_contratto_processi.py` | `core/tests/services/test_contratto_liveness_vs_deploy.py` | 1 ≤ 10 · 2 ≤ 10 · 5 ≤ 30 · 1440 ≤ 11520 · 10080 ≤ 11520; le due corsie di fatturazione saltano (nessun contratto), il listener è `SESSIONE`/`servizio`. Anti verde-per-sottrazione: fallisce se **nessun** timer arriva al confronto |
| 10.7-5 | Handler `notifica_digest_muto_default` (`coda_lavori/notifica_digest_muto_handler.py`), registrato in `CoreConfig.ready()`; `separa_destinatari` **salita** dal command a `presidi_digest` (secondo lettore); senza destinatario → `E_CONFIG_MANCANTE` **terminale**, non un `FATTO` vuoto | `core/services/coda_lavori/notifica_digest_muto_handler.py`, `core/apps.py`, `presidi_digest.py` | 6 test senza DB; il guardrail del binding (`test_coda_lavori_tipi_handler_guardrail`, DB vero) è verde: l'handler è a catalogo e non è orfano; **prova end-to-end in transazione ritirata**: handler → `fn_accoda_email_sistema` (id 537) → la riga è **visibile all'identità tecnica di `send_pending_emails` attraverso `config.vw_email_in_coda`**, e invisibile a `zeroerp_app` nudo — la cecità RLS di [[feedback_rls_conteggio_zero_non_e_un_dato]], vista di persona prima di leggere col ruolo giusto |
| 10.7-6 | niente per §4 e §5 | — | il pannello legge il catalogo |

Documentazione allineata: catalogo BB backend (riga `sveglie` riscritta — la
frase «non va su `dbops.processi`» era giusta per la cadenza e sbagliata per
la tolleranza; righe nuove per `contratti_liveness`, `separa_destinatari`,
l'handler), header di `install-timers.sh`, `_contratto` in `sveglie.json`.

### ✅ Che cosa restava, e com'è finita

* ~~Riavviare `zeroerp-listen-cambio-reparto`~~ — **fatto da Tid** il
  2026-09-11 alle 20:06: la sessione porta `application_name`, il panorama dà
  `OK`, `da_guardare = false`. gunicorn ricaricato (`kill -HUP`).
* ~~`NOTIFICA_DIGEST_MUTO` `attivo = true`~~ — acceso **sul dbdev** alle 20:11
  (`titodb`), ⚠️ **ma non nel seed**: vedi il residuo dichiarato in testa al
  documento. Finché il CSV dice `false`, ogni migrate lo rispegne.
* Il brief va in `work-done` con quel residuo scritto in testa.
* **Derivata** (domanda di Tid, stessa sera): il riavvio dei processi da
  interfaccia — [analisi-riavvio-processi-da-interfaccia.md](../work-in-progress/analisi-riavvio-processi-da-interfaccia.md).
  Non è di questo brief: lo cita perché nasce dal suo ultimo anello umano.

### ⚠️ Una cosa vista facendo, da non perdere

**Il BE e il DB calcolano lo stesso predicato in due posti.** Il badge code
(`_liveness_worker` → `job_liveness`) e il panorama
(`vw_processi_programmazione`) confrontano entrambi `ultimo run` con la
tolleranza — ora **lo stesso numero, dallo stesso catalogo, col clock del
database**, quindi non divergono; ma sono due lettori dello stesso fatto. Il
giorno in cui il badge dovesse mostrare *`MUTO`/`MAI_PARTITO`* e non un
booleano, la strada è leggere `stato` dal panorama, non riscriverlo. Non è di
questo brief.

## 11.4 🔍 Revisione critica del codice scritto — 2026-09-11, sera (su richiesta di Tid)

Cercato: bug, codice fragile, duplicazioni, valori scritti a mano. Trovato e
corretto, tutto con **4670 test verdi** e `ruff` pulito a valle:

| Che cosa | Dov'era | Perché contava | Rimedio |
| --- | --- | --- | --- |
| 🔴 **Bug** nel parser `OnCalendar`: `*:0/N` restituiva `N` anche per `N ≥ 60` | `_contratto_processi.intervallo_massimo_minuti` | in systemd `*:0/90` combacia **solo il minuto 0** → il timer gira ogni ORA, non ogni 90 minuti: il presidio avrebbe accettato un contratto di 90 su un timer che promette 60, cioè il contrario di ciò che presidia | `min(N, 60)`; test 5 sui casi che ingannano |
| 🔴 **Bug** gemello: `*-*-DD` accettava `29`..`31` e rispondeva «31 giorni» | idem | systemd **salta** i mesi senza quel giorno: l'intervallo non è più «un mese» | il parser **rifiuta** `DD > 28` — meglio non capire che stimare |
| 🟠 Fragile: il test statico del cron vietava la parola `prossimo_tentativo` **ovunque** nel sorgente | `test_send_pending_emails_predicato_in_una_sede` | una scrittura legittima del backoff (`SET prossimo_tentativo`) l'avrebbe fatto scattare, e un cancello che boccia il caso giusto viene spento | ristretto al **predicato di lettura** (`IS NULL` / `<=`) |
| 🟠 **Duplicato**: la chiamata a `insert_log` con otto argomenti, identica nel command del digest e nell'handler del guardiano | `digest_presidi._invia`, `notifica_digest_muto_handler` | due copie del «come si scrive alla persona dei presidi» divergono alla prima modifica (un `cc` in più, un contesto in meno) | estratta `presidi_digest.accoda_email_presidi(...)` → `EmailPresidiAccodata | None`; il command mappa `None` su `NON_CONFIGURATO`, l'handler lo fa fallire terminale |
| 🟠 **Scritto a mano**: i nomi delle due unit del digest e il percorso di `manage.py` nel testo della mail | `componi_avviso_digest_muto` | seconda sede di `sveglie.json`: una corsia rinominata e la mail manda a guardare l'unit sbagliata alle sette di mattina | le unit si **leggono** da `sveglie_di_processo(processo)`; il comando suggerito è `bin/run-command.sh` (il wrapper di systemd, con l'env vero) |
| 🟠 **Duplicato** preesistente, aggravato: `_repo_root()` era in **sette** file di test e la mia `_contratto_processi.py` era l'ottava copia (più un nono lettore che la importava da un modulo di test) | `apps/core/tests/*` | regola del 2 superata da un pezzo | `apps/core/tests/_repo.py` (`repo_root`), nove file ripuntati, `Path` inutilizzati tolti |
| 🟡 Letterale `"COMMAND"` in un test | `test_contratto_liveness_vs_deploy` | vocabolario del CHECK ricopiato | `CANALE_COMMAND` accanto a `SEGNO_*` nell'helper |
| 🟡 Il mio stesso primo ritocco al parser catturava il giorno della settimana come gruppo → `int('Mon')` | idem | trovato dalla prova a mano prima del test | gruppo non catturante; è il caso 5 del test |

**Lasciato com'è, e dichiarato**: `_PROCESSO_GUARDIANO = "guardiano_digest"`
nell'handler è un **mirror dichiarato** di `coda_lavori_tipi.processo_codice`
— non sta in `processi.py` perché quel modulo elenca solo i processi che il
backend avvia, e questo lo avvia pgAgent. Serve a una riga di `contesto_json`,
non a una decisione: se il nome cambia, cambia lì e nel CSV insieme, e nel
frattempo non si rompe niente.

*Brief del 2026-09-11. Le misure sono letture di `backend-dev` e del dbdev di
quel giorno: valgono come controesempio, non come motivo. Il motivo sta sul
modello, ed è che un processo che non parte non lascia una riga da nessuna
parte — e una riga che manca non si vede, se non contro l'elenco di ciò che ci
si aspettava.*
