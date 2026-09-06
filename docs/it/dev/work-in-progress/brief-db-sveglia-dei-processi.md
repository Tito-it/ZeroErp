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
> ⚠️ **Nessuno dei due punti è un guasto.** Sono due posti in cui un presidio
> **non guarda** — e un presidio cieco non si nota, per definizione.

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
