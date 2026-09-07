# Brief — chi sveglia i processi, e perché di otto non lo sappiamo

> **Destinatari:** backend e team DB (`dev/db-tid`).
>
> **Che cos'è.** Le due code rimaste dal filo delle email, che con le email non
> c'entravano niente. Erano il §6-bis e l'ultimo punto del §10 di
> [brief-db-email-perimetro-e-invio-di-sistema.md](../work-done/brief-db-email-perimetro-e-invio-di-sistema.md)
> (ora in `work-done/`): un cantiere a sé, dentro un documento chiuso.
>
> **Stato:** 🔵 aperto, non urgente. ⛔ **Non blocca niente**, e proprio per
> questo va scritto: è il genere di cosa che resta scoperta finché qualcuno non
> la nomina.
>
> ✅ **La metà backend è chiusa il 2026-09-06** (§3.1 e §5), e non come proponeva
> questo documento: leggere la correzione in cima al §2 e l'esito del §3.1 prima
> di usarlo per decidere. Resta aperto ciò che è del team DB: la terza guardia
> `IGNOTO` (§3.2), la vista-presidio (§6) e le due righe di catalogo per lo
> stesso lavoro (§7).
>
> 🔵 **Risposta del team DB: §8** (2026-09-06) — piano, decisioni prese, e **un
> guasto trovato rileggendo**: `apply_storicizza_weekly` non è un residuo che si
> toglie alla prossima corsa, è **R-12 ancora vivo** (§8.1). Leggere quello prima
> del §1.
> ✅ **Lavorato e applicato il 2026-09-07: §9.** Il §6 e il §3.2 sono chiusi lato
> DB, il §7 pure — resta al backend togliere l'unit e la costante (§9.5), e resta
> **sabato 12-09** per `apply_storicizza_weekly`.
>
> ⚠️ **Nessuno dei due punti è un guasto.** Sono due posti in cui un presidio
> **non guarda** — e un presidio cieco non si nota, per definizione.
> ⛔ **Tranne uno, e si è visto solo guardando**: vedi §8.1.

---

## 1. Il panorama, misurato il 2026-09-06

`dbops.vw_processi_programmazione` confronta due fonti — chi dovrebbe svegliare
un processo e quando ha girato davvero:

| stato | n | |
| --- | --- | --- |
| `OK` | **12** | pgAgent lo sveglia e il giornale lo registra |
| `FUORI_PORTATA` | **8** | ⛔ la sveglia vive **fuori** dal database |
| `GIRA_E_NON_REGISTRA` | **2** | `apply_storicizza_weekly`, `chiusura_scadenze_daily` — i wrapper ci sono, si tolgono alla prossima corsa |

⭐ Il DB si ferma dove deve: chiama `FUORI_PORTATA` ciò che non può vedere,
invece di darlo per buono. **È tutto quello che può onestamente fare.**

---

## 2. 🔴 Gli otto scoperti, e sono quasi tutti nostri

| processo | classe | canale | chi lo sveglia |
| --- | --- | --- | --- |
| `run_fatturazione_batch` | DOMINIO | COMMAND | cron/systemd |
| `send_pending_emails` | DOMINIO | COMMAND | cron/systemd |
| `draina_coda_stampa` | DOMINIO | COMMAND | worker systemd |
| `draina_coda_lavori` | MANUTENZIONE | COMMAND | worker systemd |
| `sync_auth_user_active` | AMMINISTRAZIONE | COMMAND | cron/systemd |
| `listen_cambio_reparto` | AMMINISTRAZIONE | COMMAND | servizio in ascolto |
| `FATTURAZIONE_GIRO` | DOMINIO | CODA | lo accoda un operatore |
| `FATTURAZIONE_NUMERA` | DOMINIO | CODA | lo accoda un operatore |

⛔ **Sei su otto sono comandi del backend**, e la loro cadenza vive in unit
systemd e crontab — cioè **fuori dal repository**, invisibili ai test. È lo
stesso difetto che il cantiere dei processi automatici ha già nominato una volta
per `85_pgagent`, solo spostato di lato.

> 🔴 **CORREZIONE (2026-09-06): il paragrafo qui sopra è sbagliato, e va letto
> prima di progettarci sopra.** Gli unit **erano già nel repository** —
> `backend/deploy/systemd/`, template versionati e reviewabili in PR — e la CI
> **li validava** (`ci-validate.yaml`, `--render-only` + `systemd-analyze
> verify`). Non per tutti: per **tre processi su sei**.
>
> ⚠️ E «invisibili ai test» era vero in un senso più stretto e più importante di
> come è scritto: `systemd-analyze verify` è un cancello di **sintassi** —
> verifica che un unit scritto sia scritto bene, e non ha nessun modo di
> accorgersi di un unit che **non è stato scritto**. È il difetto classico: il
> presidio guardava ciò che c'era.
>
> 🔴 **Il buco vero era un altro, e peggiore**: `send_pending_emails`,
> `sync_auth_user_active` e `listen_cambio_reparto` non avevano **nessun**
> artefatto di deploy. Non una cadenza scritta altrove — **niente**. ⭐ E il
> primo dei tre è proprio quello che il paragrafo qui sotto usa come esempio
> dello spavento: le tre cause che elenca («unit disattivata, timer sbagliato,
> macchina spenta») presuppongono tutte che un unit **esista**.
>
> ✅ **Chiuso il 2026-09-06** dal lato backend: i sei processi hanno tutti il
> loro unit, il dichiarato ha una sede unica (`backend/deploy/sveglie.json`,
> letta dall'installer **e** dal backend), e il presidio che mancava esiste —
> `test_ogni_processo_del_backend_ha_una_sveglia` fallisce se un processo che il
> backend dichiara di eseguire non ha niente che lo faccia partire.
> ⇒ Ne discende che il **§3.1 qui sotto è superato**: leggerlo per il
> ragionamento, non per la strada.

### Che cosa vuol dire davvero

> Se stanotte `send_pending_emails` non parte — unit disattivata, timer
> sbagliato, macchina spenta — **nessuna vista se ne accorge**. Il processo non
> ha fallito: non è mai partito. E l'unico segno sarebbe una coda che si allunga,
> che è di nuovo un guasto che si manifesta come **assenza**.

⚠️ I due `CODA` sono un caso diverso e sano: li sveglia una persona, quindi non
esiste una cadenza da dichiarare. Restano `FUORI_PORTATA` a ragione — ma varrebbe
la pena che il panorama li distinguesse dagli altri sei, o «otto scoperti» conta
insieme cose diverse.

---

## 3. Che cosa serve, e da chi

### 3.1 ✅ Backend — dire quando siamo programmati *(chiuso 2026-09-06)*

> **Esito:** fatto, ma **non con la strada proposta qui sotto** — e il perché
> vale più della soluzione.
>
> ⛔ **La promessa scritta dal processo è cieca proprio sul caso da chiudere.**
> *«Il comando, al primo giro, dichiara la propria cadenza attesa»* funziona per
> *«girava e ha smesso»* (che è R-12, già coperto). Ma **una promessa esiste solo
> se il processo gira**: un processo mai partito non promette niente, e non
> produrrebbe una riga rossa — produrrebbe **nessuna riga**, indistinguibile da
> un processo appena registrato a catalogo. Cioè di nuovo un guasto che si
> manifesta come assenza, che è ciò che questo brief esiste per togliere.
> ⇒ **La seconda fonte non può essere il processo**: dev'essere qualcosa che
> esiste *a prescindere* dal fatto che il processo giri.
>
> ⛔ **E sarebbe stata una TERZA scrittura.** Lo stesso fatto era già in due
> posti: l'`OnCalendar` dentro `install-timers.sh` e
> `WORKER_ATTIVO_SOGLIA_MINUTI = 10` in `coda_lavori/gestione_service.py` (due
> processi su sei, margine 10× e 5×, senza il perché scritto da nessuna parte).
> È esattamente l'argomento che il §6-bis del brief email usa per rifiutare la
> cadenza su `dbops.processi` — *«due scritture prima o poi dissentono»* — e che
> questa proposta stava per infrangere dall'altro lato.
>
> ✅ **Quello che si è fatto**: il dichiarato di deploy ha una **sede unica**,
> `backend/deploy/sveglie.json`, letta dall'installer degli unit **e** dal
> backend (`apps.core.services.sveglie`). Non è una promessa del processo: è il
> **deploy che dichiara**, e il giornale dei run che verifica. Playbook §17.
>
> ⬇️ Il ragionamento originale resta agli atti — è il precedente di come si
> decide, e la strada scartata è la parte che insegna di più.

Il database non ha modo di sapere la cadenza di un comando su systemd. ⇒ Deve
dirgliela chi ce l'ha: **noi**.

⚠️ **Non è "una colonna con un cron string"**, ed è il punto da decidere insieme:
una cadenza *dichiarata* che nessuno verifica è una promessa, e una promessa in
una tabella invecchia come tutte. Il valore sta nel **confronto** fra due fonti —
esattamente ciò che la vista già fa per pgAgent. ⇒ La domanda giusta non è «dove
scriviamo la cadenza» ma **«quale seconda fonte possiamo confrontare?»**.

🔵 Una strada possibile, da valutare: il comando stesso, al primo giro, dichiara
la propria cadenza attesa — e da lì in poi il confronto è fra *quando ha detto
che sarebbe tornato* e *quando è tornato davvero*. Non serve conoscere systemd:
serve che il processo prometta e che qualcuno controlli la promessa.

### 3.2 🔵 DB — la terza guardia che la misura non sa leggere

Il rubinetto degli accumulatori (`scripts/codici-errore-baseline.sh`) classifica
un punto d'errore leggendo la **riga di guardia**. In
`config.fn_chiudi_email_sistema` la terza è:

```sql
IF v_ambito <> 'SISTEMA' THEN
```

⇒ Nessuna regola la riconosce: risulta `IGNOTO`.

⛔ Ed è **il caso pericoloso** — quello che il vostro stesso commento dice avere
«parole sue» perché è l'unico momento in cui si nota che qualcuno sta usando la
porta di sistema per l'email di un'azienda. Il presidio che dovrebbe accorgersi
se quel codice si allarga, lì **non sta guardando**.

⚠️ Non è urgente e non è un guasto: è un presidio con un punto cieco, e i punti
ciechi si nominano quando si vedono.

---

## 4. Come si vede che è chiuso

* ✅ **ogni processo che il backend sveglia ha un artefatto di deploy**, e se un
  giorno ne nascesse uno senza, la CI lo dice per nome
  (`test_ogni_processo_del_backend_ha_una_sveglia`) — 2026-09-06;
* 🔵 `dbops.vw_processi_programmazione` continua a chiamarli `FUORI_PORTATA`, ed
  è **corretto**: il database non può vedere systemd, e dirlo `OK` sarebbe una
  bugia rassicurante. ⇒ La riga di chiusura originale — *«non ha più righe
  `FUORI_PORTATA`»* — chiedeva alla vista una cosa che non può fare: quello
  stato non è un debito da azzerare, è un confine dichiarato. Chi presidia di là
  dal confine è il backend, e adesso presidia;
* 🔵 il **panorama si vede in-app**: serve la vista-presidio filtrata al team DB
  (§6);
* 🔵 `dbops.processi` non ha più **due righe attive per lo stesso lavoro**
  (`sync_auth_user_active` / `sync_auth_user_expired_daily`) — §7. Finché non è
  deciso, l'unit di quel processo resta scritto e spento;
* 🔵 nessun punto d'errore di `fn_chiudi_email_sistema` resta `IGNOTO` (§3.2).

---

## 5. ✅ Che cosa ha fatto il backend (2026-09-06)

I sei processi su canale `COMMAND` hanno ora **tutti** un artefatto di deploy
versionato, e il dichiarato («chi sveglia cosa, ogni quanto») ha una **sede
unica** — `backend/deploy/sveglie.json` — letta sia dall'installer degli unit
(`backend/bin/install-timers.sh`) sia dal backend
(`apps.core.services.sveglie`). Playbook §17.

| Unit | Processo | Forma | Cadenza | Acceso |
| --- | --- | --- | --- | --- |
| `zeroerp-coda-lavori` | `draina_coda_lavori` | timer | `*:0/1` | ✅ |
| `zeroerp-coda-stampa` | `draina_coda_stampa` | timer | `*:0/2` | ✅ |
| `zeroerp-fatturazione-immediata` | `run_fatturazione_batch` | timer | `*:0/2` | ⛔ emette documenti |
| `zeroerp-fatturazione-differita` | `run_fatturazione_batch` | timer | `*-*-01 02:00` | ⛔ idem |
| **`zeroerp-send-pending-emails`** | `send_pending_emails` | timer | `*:0/5` | ✅ |
| **`zeroerp-sync-auth-user-active`** | `sync_auth_user_active` | timer | `*-*-* 03:00` | 🔴 vedi §7 |
| **`zeroerp-listen-cambio-reparto`** | `listen_cambio_reparto` | **servizio** | — | ✅ |

🔴 **I tre in grassetto non esistevano.** Erano processi a catalogo, che si
registravano su `maintenance.job_run_log` dal 2026-09-05, e che **nessun
artefatto di deploy faceva partire**: su un host nuovo non partivano mai.

⭐ E c'è un presidio nuovo dal nostro lato, che è il pezzo che vale:
`test_ogni_processo_del_backend_ha_una_sveglia` fallisce — **nominando il
processo** — se un processo che il backend dichiara di eseguire non ha nessun
unit che lo faccia partire. ⇒ **Adesso chi può saperlo guarda.** Il verso
opposto, «il database dichiara di non poter vedere», resta vostro ed è il §6.

### 5.1 🔴 Un difetto trovato rileggendo, e dove si nascondeva

Scrivendo il presidio è emerso che `install-timers.sh` leggeva i campi con
`IFS=$'\t'`. Il TAB è **IFS-whitespace**, quindi `read` collassa i delimitatori
consecutivi: un campo **vuoto** sparisce e tutti quelli dopo slittano di uno.
`oncalendar` vuoto è il caso **normale** di un servizio sempre acceso ⇒
`zeroerp-listen-cambio-reparto` leggeva `abilita` = il testo della nota, finiva
fra gli spenti e **veniva installato senza essere mai avviato**.

⛔ **E la prova non poteva vederlo**, che è la parte che vale più del bug: la CI
lanciava `install-timers.sh --render-only`, che esce **prima** del ramo che
accende. Sette unit renderizzati correttamente, e nessuno in grado di accorgersi
che uno non sarebbe partito. *Il difetto viveva esattamente dove la prova non
arrivava* — la stessa forma del guasto che questo cantiere esiste per togliere.

✅ Corretto (separatore `\x1f`, non-whitespace: i campi vuoti sopravvivono) e —
soprattutto — **il ramo cieco è stato aperto alla prova**:
`backend/scripts/tests/test-install-timers.sh` mette un `systemctl` finto in
testa al `PATH` e sposta la destinazione con `ZEROERP_SYSTEMD_DIR`, così esegue
**le righe vere** e verifica che si accendano esattamente gli unit dichiarati.
Gira in CI accanto a `systemd-analyze verify`, e le due coprono metà a testa:
*gli unit sono validi* e *si accendono quelli giusti*.

⛔ Non è un `--dry-run`: quello avrebbe provato il ramo che **non** accende,
cioè proprio quello che non interessa. Verificato che il test diventa rosso
rimettendo il TAB — nomina l'unit mancante.

### 5.2 🔵 Che cosa resta scoperto, dichiarato

* **`systemctl enable` che fallisce**: lo stub esce sempre `0`, quindi la
  reazione a un `enable` rifiutato non è provata. Vuole uno stub parametrico ed
  è un test suo.
* **`sync_auth_user_active` è installato e spento** in attesa del §7.
* ⚠️ **Che gli unit siano davvero attivi su un host** non lo dice nessun test, e
  non può: è una proprietà della macchina, non del repository. La sede giusta è
  il panorama del §6.

⚠️ **`listen_cambio_reparto` non ha un timer**, e non è una dimenticanza: è un
listener `LISTEN/NOTIFY` sempre acceso, `Type=simple` + `Restart=always`. Non ha
una cadenza da dichiarare, e la sua tolleranza di liveness è `null` — scrive
**un solo run**, quello di avvio (decisione di Tid, 2026-09-05), quindi
presidiarne la vitalità sull'ultimo run direbbe «fermo» su un listener sano
partito tre settimane fa. ⇒ Il §2 lo contava fra gli otto scoperti insieme ai
timer: è di natura diversa, come i due `CODA`.

---

## 6. 🔵 Richiesta al team DB — il panorama ha bisogno della sua vista-presidio

`dbops.vw_processi_programmazione` dichiara la propria natura nel suo stesso
commento, e ha ragione:

> *«È un **panorama**, non un presidio: elenca anche i sani, perché senza sapere
> quanti sono i sani un guasto sembra la norma. Il presidio è
> `WHERE stato NOT IN (OK, FUORI_PORTATA)`.»*

⛔ **Ed è esattamente il motivo per cui non possiamo cablarla dove sarebbe
naturale.** Il pannello dei presidi della schermata «Processi automatici»
(`PresidiProcessiPanel.vue`) ha un contratto: ogni vista che ci compare o **deve
restare vuota**, o è **un registro di debito che deve calare** — e la natura la
dichiarate voi, nel commento della vista, che il backend legge con
`obj_description`. Metterci dentro un panorama con **12 righe `OK`**
insegnerebbe a leggere il verde come debito, cioè a ignorare l'avviso. È il modo
più efficace di spegnere un presidio, ed è la ragione per cui il pannello quel
filtro non ce l'ha e non deve averlo.

**Che cosa serve.** La vista che il vostro commento già nomina, come oggetto
suo, con il commento che ne dichiari la natura («deve restare vuota»):

```sql
-- il presidio, non il panorama
SELECT * FROM dbops.vw_processi_programmazione
 WHERE stato NOT IN ('OK', 'FUORI_PORTATA');
```

⭐ **La forma e il nome sono vostri.** Da parte nostra il cablaggio è **una riga**
in `PRESIDI_PROCESSI` (`apps/core/db/processi_repository.py`) e **zero** nel
frontend: il pannello legge le colonne che trova e la descrizione dal database.

⚠️ **E vale la pena che sia una VISTA, non un filtro che scriviamo noi.** Il
criterio «quali stati sono un guasto» è del modello e cambierà (oggi tre valori,
domani forse `MAI_PARTITO` si sdoppia): scritto nel backend sarebbe la seconda
sede, e la seconda diverge. Il panorama resta dov'è per chi vuole vedere anche i
sani.

---

## 7. 🔴 E un difetto del catalogo, che è la cosa più importante di questa coda

`dbops.processi` ha **due righe per lo stesso lavoro**:

| id | codice | classe | canale | jobname_pgagent |
| --- | --- | --- | --- | --- |
| 11 | `sync_auth_user_expired_daily` | AMMINISTRAZIONE | `PGAGENT` | `sync_auth_user_expired_daily` |
| 23 | `sync_auth_user_active` | AMMINISTRAZIONE | `COMMAND` | `NULL` |

Entrambe disattivano gli utenti la cui finestra temporale è scaduta. L'header del
management command lo dice da sempre — *«Alternativa a pgAgent job
`sync_auth_user_expired_daily`»* — ma **«alternativa» non è uno stato del
mondo**: il modello ammette benissimo che siano **accesi tutti e due**, e nulla
nel database lo impedisce né lo segnala.

⚠️ **Oggi non fa danno**, e non è un argomento: `fn_sync_auth_user_expired` è
idempotente, quindi il secondo giro non trova più nessuno da disattivare. Quello
che si perde è la **leggibilità del giornale** — due attori diversi per lo stesso
fatto — e la possibilità di presidiare: `vw_processi_programmazione` mostrerebbe
uno dei due `OK` e l'altro fermo, **senza che ci sia niente di rotto**. Un
presidio che segnala il sano è un presidio che si impara a ignorare.

⛔ **Per questo non abbiamo acceso il timer.** L'unit
`zeroerp-sync-auth-user-active` è **scritto e spento**, con la ragione nel suo
template: accenderlo senza ritirare il gemello farebbe girare il lavoro due
volte. E la scelta di quale dei due tenere **non è del deploy** — è del modello,
ed è vostra:

* si tiene il `COMMAND` → `obsoleto_dal` sulla riga 11, e noi accendiamo il timer;
* si tiene il `PGAGENT` → `obsoleto_dal` sulla riga 23, e noi cancelliamo unit e
  voce dal dichiarato.

⭐ **Non proponiamo quale.** Ma qualunque sia, il caso generale merita una
domanda: *un processo può avere due righe di catalogo per lo stesso lavoro, su
canali diversi?* Se la risposta è no, è un vincolo; se è sì, è una colonna che
dice quale delle due è quella viva. Oggi non è né l'uno né l'altro — è una
coincidenza di nomi che regge finché qualcuno se la ricorda.

---

## 8. 🔵 Risposta del team DB — il piano, e un guasto trovato rileggendo

> Rilettura del 2026-09-06, dopo il push del backend (`990996575`).

### Prima: la metà backend regge, e in tre punti va oltre il contratto

* il presidio del §5 legge le costanti `PROCESSO_*` **da `processi.py`** invece di
  riscriverle: niente terza sede, e un command nuovo lo vede da sé;
* il **test 0** protegge i test 2 e 4 — senza, una cartella spostata li avrebbe
  fatti passare trovando zero file, cioè smettere di verificare senza diventare
  rossi. È la stessa forma di guasto che questo cantiere esiste per togliere,
  vista in anticipo;
* `abilita` obbligatorio, con la ragione scritta: *«il default sicuro è quello
  che nasconde meglio la dimenticanza»*.

⭐ E il §5.1 è il pezzo che vale più della correzione: non «ho sistemato l'IFS»,
ma *«la prova non poteva vederlo, e ho aperto il ramo cieco alla prova»*.

---

### 8.1 🔴 Il §1 dice una cosa che non regge, e riguarda R-12

Il §1 archivia i due `GIRA_E_NON_REGISTRA` come *«i wrapper ci sono, si tolgono
alla prossima corsa»*. **Per uno dei due è una previsione, e per l'altro è
falsa.** Letto su dbdev il 2026-09-06:

| processo | pgAgent ultima corsa | giornale ultima corsa |
| --- | --- | --- |
| `chiusura_scadenze_daily` | 2026-09-06 00:05 | **mai** |
| `apply_storicizza_weekly` | 2026-09-05 07:00 | **2026-02-21** |

Il primo si spiega e si chiuderà da solo: il wrapper è stato installato alle
**00:39**, cioè *dopo* la corsa delle 00:05 (`20260906-06` e `-07`, entrambi
`EXECUTED`). Alla prossima registra.

⛔ **Il secondo no, e non è un residuo.**
`maintenance.proc_apply_storicizza_defaults_job` esiste **dal 2025-08-08** e
chiama `fn_run_and_log`: il wrapper c'era già. Da sei mesi e mezzo quel job gira
e non lascia traccia. ⭐ **È R-12, ancora vivo** — la stessa firma, sullo stesso
processo che l'ha resa famosa.

⭐ La causa più probabile è esattamente quella corretta il 2026-09-05 alle 22:49
(`20260905-35`/`-36`, «il verbale sopravvive»): prima, il `RAISE` annullava la
riga rossa, quindi un job che falliva non lasciava **niente**, non un rosso. La
corsa del 05-09 alle 07:00 precede il fix di quindici ore.
⇒ **La prima prova onesta di quel fix è sabato 2026-09-12 alle 07:00.** E se il
job sta fallendo, ciò che comparirà non sarà silenzio: sarà una riga rossa in
`maintenance.vw_job_run_da_guardare`.
⚠️ In `dbops.error_log` non c'è nulla, il che è coerente: l'errore non passa da
`script.fn_log_and_raise_error`.

⚠️ **Conseguenza diretta sul §6**, e va detta prima di cablare: la vista-presidio
**nasce non vuota**, e resta tale almeno fino al 12-09. Non è un difetto della
vista — è la prima cosa che quella vista ha da dire.

---

### 8.2 🔵 §6 — la vista si fa, ma il criterio si scrive UNA volta sola

La richiesta è giusta e il ragionamento pure: *«il criterio quali stati sono un
guasto è del modello e cambierà; scritto nel backend sarebbe la seconda sede»*.

⛔ **Ma una vista-presidio che ripete `stato NOT IN ('OK','FUORI_PORTATA')` è la
stessa duplicazione in miniatura**, spostata di un metro. Il vocabolario degli
stati sarebbe enumerato in **due** posti, e il giorno in cui `MAI_PARTITO` si
sdoppia — l'esempio è vostro — qualcuno deve *ricordarsi* di decidere da che
parte cade il valore nuovo. Un allineamento affidato alla memoria è quello che
manca per primo.

✅ **La forma che facciamo**: il panorama guadagna una colonna **`da_guardare`**,
calcolata nella stessa vista a partire dallo **stesso** `CASE` (via CTE: gli
stati sani si nominano una volta, sotto il `CASE` che li produce). La
vista-presidio è `WHERE da_guardare`. ⇒ Uno stato nuovo obbliga a decidere sul
posto, dove la decisione si vede.

Nome: **`dbops.vw_processi_programmazione_da_guardare`**, in linea con
`vw_coda_lavori_da_guardare` e `vw_job_run_da_guardare`.

Due dettagli che sembrano forma e non lo sono:

* ⚠️ **`CREATE OR REPLACE VIEW` sa solo AGGIUNGERE colonne in coda.** `stato` è
  oggi l'ultima, quindi `da_guardare` le va dietro. Ordine e tipi delle altre
  restano intoccati.
* ⛔ **La vista-presidio non si scrive `SELECT *`.** L'asterisco viene espanso e
  **congelato** alla creazione: una colonna aggiunta domani al panorama non
  arriverebbe mai al pannello, e non lo direbbe nessuno. Colonne enumerate.
  `da_guardare` **non** entra: in un presidio sarebbe una colonna sempre vera.

Il `COMMENT` dichiara la natura, come chiedete — è quello che il backend legge
con `obj_description` e che `PresidiProcessiPanel.vue` rende. Vi dichiara anche
la riga dell'§8.1: una vista che nasce con una riga dentro deve dire **perché**,
o al primo sguardo sembra rumore di fondo.

---

### 8.3 ⛔ E un vocabolario chiuso, enumerato in due posti — è quello che morderà

`chk_processi_canale` ammette **quattro** canali (`PGAGENT`, `COMMAND`, `CODA`,
`CODA_AUTOMATICA`). Il `CASE` di `vw_processi_programmazione` ne nomina **due**
nel ramo `FUORI_PORTATA` e lascia cadere gli altri sui rami di pgAgent.

⚠️ **Oggi funziona per coincidenza**: sia i `PGAGENT` sia l'unico
`CODA_AUTOMATICA` portano un `jobname_pgagent`. Ma il modello ammette benissimo
un `CODA_AUTOMATICA` accodato da un trigger o da un altro processo: nessun
jobname → `NON_PROGRAMMATO` → e con il §6 finisce nel presidio come **falso
allarme su un processo sano**. Che è esattamente il difetto contro cui il vostro
§7 mette in guardia, arrivato dalla porta di servizio.

⭐ Il rimedio non è un ramo in più adesso: è un **pgTAP** che tiene i due
vocabolari legati — *«ogni canale ammesso dal CHECK ha un ramo dichiarato nel
CASE»*. Un canale nuovo domani fa rosso il test, non un allarme in produzione.
⚠️ Non una `preCondition`: quella guarda ciò che viene prima, un invariante si
asserisce in pgTAP (linee-guida-sql §11.5).

---

### 8.4 🔵 §3.2 — il buco non è di una funzione, è una forma che l'asse non nomina

Il §4 chiede *«nessun punto d'errore di `fn_chiudi_email_sistema` resta
IGNOTO»*. ⛔ **È il criterio di chiusura di una toppa**, e chiude una funzione
sola dentro un'area cieca che al **2026-09-06** vale **357 codici su 453** (era
269 su 344 all'08-08: il buco **cresce**).

La domanda sul modello è un'altra: **l'asse "forma della condizione" ha una forma
che non nomina?** Sì. Le quattro famiglie leggono un'eccezione, una riga
mancante, un parametro, un insieme. Manca *«il valore letto non è quello
ammesso»* — `x <> 'LETTERALE'` — che è la forma di **ogni** guardia di stato o di
perimetro del progetto. Non è un caso di nicchia: è una famiglia intera.

⇒ Allargare l'asse per **quella** ragione chiude la terza guardia di
`fn_chiudi_email_sistema` come **conseguenza**, non come bersaglio.

⭐ **E la posta in gioco è quella che dite voi, verificata.** Oggi
`E_VALIDAZIONE` legge `famiglie = {IGNOTO, PARAMETRO}`, `n_famiglie_note = 1` —
quindi **non compare nella query (1) dei candidati**, che filtra `> 1`. Con la
famiglia nuova diventa 2 e affiora. *Il rubinetto è cieco su qualunque codice la
cui seconda forma sia una che il classificatore non sa leggere*, e questa era una
delle due.

⚠️ **Famiglia NUOVA, non `ENUM` allargato.** Le letture di quella vista sono
datate e si confrontano nel tempo: cambiare che cosa significa `ENUM` renderebbe
la lettura del 2026-08-08 incomparabile con la prossima, **in silenzio**. Il
nome nuovo dice esattamente che cosa si è reso visibile e quando.

Fatto datato (2026-09-06, provato in sola lettura sulla stessa query della
vista): l'allargamento sposta **73 punti / 60 codici** da `IGNOTO`.

⚠️ **L'imprecisione si dichiara nel commento**, non si scopre dopo: la forma
prende anche del normale control-flow che capita prima di un `RAISE` — `IF TG_OP
= 'DELETE'`, `IF v_id_type = 'uuid'`. Sta dentro la natura già dichiarata dalla
vista (*«è una MISURA, non un cancello»*, *«una lista DA GUARDARE, non una lista
di difetti»*), ma va scritto.

---

### 8.5 ✅ §7 — si tiene il `PGAGENT`, e la domanda generale ha una risposta

**Decisione di Tid, 2026-09-06: si tiene la riga 11 (`PGAGENT`),
`obsoleto_dal` sulla riga 23 (`sync_auth_user_active`).**

Le due righe **non fanno lo stesso lavoro**, e il vostro §7 lo sottovaluta: il
command invalida anche la cache Redis dei permessi (`invalidate_user`), che
pgAgent strutturalmente non può fare. ⚠️ Ma quella differenza è più piccola di
come sembra: `PERMISSIONS_CACHE_TTL` è **300 secondi**, e `is_active` è imposto
in **autenticazione** da `JwtAuditAuthentication` → `JWTAuthentication.get_user()`,
che legge dal database. ⇒ è un'ottimizzazione con orizzonte di cinque minuti,
**non un confine di sicurezza**.

Dall'altro lato il lavoro vero (`anagrafiche.fn_sync_auth_user_expired`) sta
tutto nel database, ha il suo wrapper di giornale dal 2026-09-06, ed è l'**unica**
delle due righe che il confronto a due fonti riesca a vedere. ⭐ Ritirare quella
visibile per tenere l'invisibile toglierebbe presidio a un processo il cui unico
valore è non essere dimenticato.

**Cosa vi chiediamo**, come dice il vostro §7 secondo ramo: cancellare i due
template `zeroerp-sync-auth-user-active.*`, la voce da `sveglie.json` e la
costante `PROCESSO_SYNC_AUTH_USER_ACTIVE` da `processi.py`. ⚠️ Vanno insieme:
lasciarne una fa dissentire `test_ogni_processo_del_backend_ha_una_sveglia` e
`test_nessun_template_orfano`, che guardano lo stesso fatto dai due versi.
⚠️ Se il command resta come attrezzo a mano, non può più registrare un run sotto
un processo ritirato: o smette di registrare, o registra sotto il codice
superstite.

#### ⭐ *«Un processo può avere due righe di catalogo per lo stesso lavoro?»*

**No — e non è un vincolo che il database possa imporre.** «Stesso lavoro» non è
una proprietà leggibile: è esattamente la situazione della `classe`, che il
manuale di `dbops.processi` già dichiara *«una dichiarazione, verificata in un
verso solo»*. Un vincolo che pretendesse di riconoscerla dedurrebbe, e una
deduzione sbagliata non si vede.

⭐ **Quello che il modello può fare è non avere bisogno della domanda: l'unità
del catalogo è il LAVORO, e chi lo sveglia non fa parte della sua identità.** La
prova che la forma regge sta dall'altra parte del confine — `sveglie.json` è
chiavato sull'**unit**, non sul processo, proprio perché `run_fatturazione_batch`
ne ha due. E `maintenance.job_run_log.origine` (CHECK: `PGAGENT` / `CRON` /
`COMMAND`) dice già **quale attore** è girato. ⇒ Una riga, due attori, `origine`
a distinguerli. **Nessuna colonna nuova, e nessun vincolo.**

⚠️ Il costo è vero e va scritto: `canale` resterebbe monovalore su un lavoro che
ha due sveglie, e quella colonna oggi decide se il processo vuole un'identità
tecnica e come lo legge il panorama. È un cantiere suo. ⛔ La decisione di oggi
non ci dipende, e non va usata per aprirlo di straforo.

---

### 8.6 ✅ §2 — i due `CODA` si distinguono, il listener no

Avete ragione che *«otto scoperti» conta insieme cose diverse*. Il panorama si
divide, **ma solo su ciò che sa leggere**:

* i due `CODA` prendono uno stato loro (**`SU_RICHIESTA`**): lì una cadenza non
  esiste proprio, ed è un fatto **permanente** — diverso dal confine
  `FUORI_PORTATA`, che è un limite di vista e che adesso qualcuno presidia
  dall'altro lato. Il canale lo dice, quindi la vista lo può derivare;
* ⛔ **`listen_cambio_reparto` resta coi `COMMAND`**, e non è pigrizia: che sia
  un listener il database **non lo sa**. Nessuna colonna di `dbops.processi` lo
  dice, e dedurlo dal nome sarebbe una coincidenza travestita da regola. Uno
  stato che il modello non sa produrre sarebbe una parola scritta a mano.
  ⇒ Se serve, è una colonna — cioè un pezzo di modello, non un ramo di `CASE`.

⚠️ Il **test 7** di `db/pgtap/dbops/test-vw-processi-programmazione.sql`
(«`COMMAND` e `CODA` sono `FUORI_PORTATA`») va aggiornato **nello stesso
changeSet**: altrimenti diventa rosso, e un rosso atteso insegna a non guardare
i rossi.

---

### 8.7 L'ordine dei lavori

| # | Cosa | Dove |
| --- | --- | --- |
| **DB-1** | `da_guardare` + `SU_RICHIESTA` sul panorama (`CREATE OR REPLACE`, colonna **in coda**) | `20_code/dbops` |
| **DB-2** | `dbops.vw_processi_programmazione_da_guardare` — colonne enumerate, `COMMENT` che dichiara la natura, `GRANT SELECT` a `zeroerp_app` in `DO` col check del ruolo | `20_code/dbops` |
| **DB-3** | pgTAP: la vista-presidio, il test 7 aggiornato, e **il vocabolario chiuso dei canali** (§8.3) | `db/pgtap/dbops` |
| **DB-4** | Famiglia nuova in `dbops.vw_codici_errore_forme_condizione`, **dopo** `PARAMETRO` per non toccare la precedenza; commento con la lettura datata e l'imprecisione dichiarata | `20_code/dbops` |
| **DB-5** | pgTAP: la terza guardia di `fn_chiudi_email_sistema` non è più `IGNOTO` — **e il verso opposto**, senza cui il test passerebbe anche se la famiglia dicesse sempre sé stessa | `db/pgtap/dbops` |
| **DB-6** | `obsoleto_dal` sulla riga 23, **editando `processi.csv`** | `80_data/sql/dbops` |
| **DB-7** | 🔴 `apply_storicizza_weekly`: guardare sabato **12-09** e capire perché sei mesi di corse non hanno lasciato traccia | — |

⚠️ **DB-6 si fa dal CSV, mai con un `UPDATE` SQL**: il mirror è `runOnChange` e
riallinea, quindi le due sorgenti divergerebbero fra sviluppo e CI
(linee-guida-sql §11.2).
⭐ E si scrive `obsoleto_dal`, **non `attivo = false`**: la vista filtra su
entrambi, e la prima non sveglia nessun guard di disattivazione con figlie —
quella riga ha un giornale dietro.

---

### 8.8 Come si vede che è chiuso, lato DB

* 🔵 `dbops.vw_processi_programmazione` distingue `SU_RICHIESTA` da
  `FUORI_PORTATA`, e porta `da_guardare`: **il criterio del guasto è scritto una
  volta sola**, nella stessa vista che produce gli stati;
* 🔵 la vista-presidio esiste, il pannello la mostra, e il suo commento dice se
  deve restare vuota o calare. ⚠️ **Oggi non è vuota**, e il perché è l'§8.1 —
  non un difetto della vista, la prima cosa che ha da dire;
* 🔵 un canale ammesso dal `CHECK` senza ramo nel `CASE` fa **rosso un pgTAP**,
  non un falso allarme in produzione;
* 🔵 `E_VALIDAZIONE` compare fra i candidati della query (1) — cioè il rubinetto
  vede la seconda forma che prima non sapeva leggere;
* 🔵 `dbops.processi` non ha più due righe attive per lo stesso lavoro;
* 🔴 `apply_storicizza_weekly` lascia una traccia — **verde o rossa**, ma una.
  ⛔ Finché non l'ha lasciata, «i wrapper ci sono» non è una risposta.

---

## 9. ✅ Lavorato — che cosa è entrato, e che cosa resta

> 2026-09-07. Numerazione: il cantiere ha usato `20260907-01..03`; da `-11` in
> avanti è di un altro lavoro.

### 9.1 I changeSet

| # | Oggetto | Stato |
| --- | --- | --- |
| `20260907-01` | `dbops.vw_processi_programmazione`: colonna **`da_guardare`** + stato **`SU_RICHIESTA`** | ✅ applicato |
| `20260907-02` | `dbops.vw_processi_programmazione_da_guardare` — la vista-presidio del §6 | ✅ applicato |
| `20260907-03` | `dbops.vw_codici_errore_forme_condizione`: famiglia **`VALORE_ATTESO`** | ✅ applicato |
| `80_data` | `processi.csv`: `obsoleto_dal = 2026-09-07` sulla riga 23 | ✅ applicato (mirror `runOnChange`) |

⚠️ Il seed **non** ha avuto bisogno di un changeSet nuovo: la sede del dato è il
CSV, e il mirror `20260904-13` è `runOnChange` — l'edit del file lo risveglia da
sé. ⭐ Prima di toccarlo è stato verificato che fosse **risvegliabile**: tutte e
22 le righe ricaricate in una temp table e ri-upsertate in una transazione
annullata, perché quel loader rilegge **tutto** il file e una riga di qualcun
altro che un guard entrato dopo non accetta più sarebbe una mina armata.

### 9.2 I pgTAP

| File | Cosa |
| --- | --- |
| `test-vw-processi-programmazione.sql` | plan 7 → **10**: il 7 riscritto sui soli `COMMAND`, l'8 nuovo sui `CODA`, il **9 e il 10** sul vocabolario chiuso dei canali |
| `test-vw-processi-programmazione-da-guardare.sql` | **nuovo**, plan 6 — fra cui il 5, che impedisce alla vista-presidio di riscriversi un criterio suo |
| `test-vw-codici-errore-valore-atteso.sql` | **nuovo**, plan 6 — quattro forme costruite, quattro risposte attese |
| `test-processi-registro.sql` | plan 14 → **15**: di due righe di catalogo per lo stesso lavoro ne vive al massimo una |

⭐ **Ognuno è stato provato anche al contrario**, perché un presidio verde non
dice niente finché non si sa che cosa lo farebbe diventare rosso:

| si rompe… | diventa rosso |
| --- | --- |
| un canale nel `CHECK` senza verdetto dichiarato | 9 |
| il panorama torna a tenere `COMMAND` e `CODA` sotto una parola sola | 8 |
| la vista-presidio si riscrive un `WHERE` suo | 5 (presidio) |
| la vista-presidio elenca anche i sani | 3 e 5 (presidio) |
| il classificatore torna alle quattro famiglie | 1, 5, 6 (valore atteso) |
| la riga 23 torna viva | 15 (registro) |

⚠️ E i test 2, 3, 4 del file sul classificatore **restano verdi** con la vista
vecchia, ed è voluto: provano i rami che *non* sono cambiati. Un test che
diventasse rosso anche lì starebbe misurando il proprio codice, non il
comportamento.

### 9.3 ⭐ Le decisioni, in una riga ciascuna

* **`da_guardare` sta nel panorama, non nel presidio.** La vista-presidio
  proietta. Il criterio del guasto è scritto una volta sola, accanto al `CASE`
  che produce gli stati: uno stato nuovo non ha un default in cui cadere.
* **`SU_RICHIESTA` è uno stato, non una nota.** I due `CODA` non hanno una
  cadenza da confrontare — è la loro natura, non un limite di vista.
  ⛔ `listen_cambio_reparto` resta fra i `COMMAND`: che sia un listener il
  database **non lo sa**, e dedurlo dal nome sarebbe una coincidenza travestita
  da regola.
* **`VALORE_ATTESO` è una famiglia nuova, non `ENUM` allargato.** Le letture di
  quella vista sono datate e si confrontano nel tempo.
* **Il §7 si chiude con `obsoleto_dal`, non con `attivo = false`.** Il panorama
  filtra su entrambi, e `obsoleto_dal` non sveglia nessun guard di
  disattivazione con figlie — quella riga ha **124 run** di giornale dietro.

### 9.4 Le misure, datate

Lette su dbdev il **2026-09-06/07**. Sono fatti, non ragioni: il perché di ogni
scelta sta nel §8.

| | prima | dopo |
| --- | ---: | ---: |
| stati del panorama | 6 | **7** (`SU_RICHIESTA`) |
| righe nel presidio | — | **2** (§8.1) |
| codici classificati (su 453) | 96 | **148** |
| codici invisibili | 357 | **305** |
| candidati della query (1) | 6 | **10** |

⭐ E il caso che il backend aveva segnalato: `E_VALIDAZIONE` passa da
`famiglie = {IGNOTO, PARAMETRO}` con `n_famiglie_note = 1` — **fuori** dalla
query dei candidati — a `{PARAMETRO, VALORE_ATTESO}` con `n_famiglie_note = 2`.
Non gli resta nemmeno un punto `IGNOTO`.

### 9.5 🔴 Che cosa resta, e a chi

* **Al backend** (§8.5): togliere insieme la costante
  `PROCESSO_SYNC_AUTH_USER_ACTIVE`, i due template
  `zeroerp-sync-auth-user-active.*` e la voce in `sveglie.json`. ⚠️ Vanno
  insieme: `test_ogni_processo_del_backend_ha_una_sveglia` e
  `test_nessun_template_orfano` guardano lo stesso fatto dai due versi, e
  lasciarne una li fa dissentire.
  ⚠️ Se il command resta come attrezzo a mano, non può più registrare un run
  sotto un processo ritirato: o smette di registrare, o registra sotto
  `sync_auth_user_expired_daily` con `origine = 'CRON'` — che è la forma che il
  `CHECK` di `job_run_log` già ammette.
  ⭐ E i 124 run storici restano dove sono: la FK punta a una riga che esiste
  ancora, e `maintenance.vw_job_run_da_guardare` si auto-pulisce dopo sette
  giorni senza corse.
* **Una riga in `PRESIDI_PROCESSI`** (`apps/core/db/processi_repository.py`):
  `dbops.vw_processi_programmazione_da_guardare`. Nel frontend zero.
* **A noi**: niente. I tre changeSet sono applicati, la suite `dbops` è **31 su
  31 verde** (`scripts/pgtap-baseline.sh dbops`, 2026-09-07) e la documentazione
  è scritta: i manual di `dbops.vw_processi_programmazione`,
  `dbops.vw_processi_programmazione_da_guardare` e
  `dbops.vw_codici_errore_forme_condizione`.
* 🔴 **A nessuno, ed è il punto**: `apply_storicizza_weekly`. Sabato
  **2026-09-12 alle 07:00** quel job gira. È la prima corsa dopo il
  `20260905-36`, e sarà la prima volta in sei mesi e mezzo che lascia una
  traccia — verde o rossa. ⛔ Se non ne lascia nessuna, il difetto non è nel
  verbale: è nel job, e va aperto un cantiere suo.

### 9.6 ⚠️ Una piccola divergenza vista di passaggio, non sanata

`test-processi-registro.sql` test 8 («ogni canale dichiarato dal `CHECK` è usato
da almeno un processo») legge il solo `attivo`; il panorama legge `attivo AND
obsoleto_dal IS NULL`. Sono due nozioni di «vivo» sullo stesso catalogo.
⚠️ Oggi non fa danno — i `COMMAND` restano cinque — ma un canale il cui ultimo
processo fosse ritirato con `obsoleto_dal` terrebbe quel test verde mentre il
panorama non lo mostra più. È scritto qui perché non si perda, non perché vada
fatto adesso.

---

## 10. ⚠️ Un cantiere nato di traverso da questo, il 2026-09-07

Toccando `dbops.vw_codici_errore_forme_condizione` per il §3.2 sono usciti rossi
due pgTAP che con questo brief non c'entravano — e che **non avevano niente di
rotto**: confrontavano la *grafia* di una reloption booleana invece della
proprietà, e diventavano rossi su una vista sana riscritta con l'altra parola.

Tirando quel filo: la proprietà più delicata delle nostre viste — *«questa vista
gira col perimetro di chi legge»* — era presidiata in **quattro posti, tutti a
elenco**, e una vista era scoperta da due mesi.

⇒ È un cantiere suo e ha un brief suo:
[brief-db-viste-security-invoker-criterio.md](brief-db-viste-security-invoker-criterio.md).

⭐ Sta scritto qui perché è il precedente più utile di questa giornata, e vale
per entrambi i cantieri: **un presidio che elenca copre ciò che qualcuno si è
ricordato di scriverci.** È lo stesso identico argomento con cui il §8.3 chiede
un pgTAP che tenga legati i canali del `CHECK` ai rami del `CASE`, e con cui il
§8.2 rifiuta di ripetere l'elenco degli stati nella vista di presidio. Tre volte
in un giorno, su tre oggetti diversi.
