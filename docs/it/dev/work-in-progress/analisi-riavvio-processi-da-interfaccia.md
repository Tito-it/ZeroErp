# Analisi — Riavviare (o far partire) un processo dall'interfaccia

> **Tipo**: analisi preliminare (nessuna riga di codice scritta) · **Data**: 2026-09-11 ·
> **Owner**: Tid · **Stato**: 🟠 **DA APPROFONDIRE** — le decisioni sono in §7, e la
> prima (l'host) viene prima di tutte le altre.
>
> **Origine.** Domanda di Tid del 2026-09-11, subito dopo aver riavviato a mano il
> listener (`sudo systemctl restart zeroerp-listen-cambio-reparto`) per spegnere la
> riga `MUTO` del panorama: *«questi comandi di riavvio potranno mai essere messi su
> interfaccia, per un riavvio da parte di un super admin o di un tecnico
> autorizzato?»*
>
> **Risposta breve.** Sì — ma **non** nella forma «il web chiama `systemctl`». La
> forma che regge è la stessa del guardiano del digest
> ([brief-db-quattro-processi-senza-presidio.md §10.2](../work-done/brief-db-quattro-processi-senza-presidio.md)):
> **la UI dichiara una richiesta, un agente sull'host la esegue**. L'agente esiste
> già (`draina_coda_lavori`); ciò che manca è piccolo lato codice e **grande lato
> modello**: il sistema oggi non sa che cosa sia un *host*.
>
> **Documenti correlati**: [brief-db-quattro-processi-senza-presidio.md](../work-done/brief-db-quattro-processi-senza-presidio.md)
> (§9 «niente interfaccia verso systemd», §10.2 il guardiano e il limite su
> `abilita`, §11.2 il limite processo/corsia) ·
> [brief-db-un-destinatario-per-i-presidi.md](brief-db-un-destinatario-per-i-presidi.md) ·
> [brief-db-sveglia-dei-processi.md](../work-done/brief-db-sveglia-dei-processi.md) ·
> [piano-be-fe-processi-automatici-identita-e-perimetro.md](../work-done/piano-be-fe-processi-automatici-identita-e-perimetro.md).

---

## 1. La domanda, e il fatto che la rende viva

Da oggi il panorama (`dbops.vw_processi_programmazione`) dice **`MUTO`** su un
processo che ha smesso di lasciare un segno di vita, il pannello dei processi lo
mostra e il digest lo scrive a una persona. Il cerchio si chiude con un gesto —
riavviare l'unit, o farla partire adesso — e **quel gesto oggi è una riga di
shell con `sudo`, su un host, da parte di chi ha la password**.

Non è un difetto: è l'ultimo anello lasciato umano di proposito. Ma è anche
l'anello che una persona *autorizzata ma senza shell* non può chiudere, e il
pannello glielo mostra senza dargli il modo di agire. La domanda è se e come
quel modo possa stare a video.

## 2. Che cosa c'è già (verificato sul repo e sul dbdev il 2026-09-11)

| Pezzo | Dove | Che cosa dà |
| --- | --- | --- |
| 15 unit systemd (7 timer + relativi `.service`, 1 servizio sempre acceso) | `backend/deploy/systemd/`, rese da `install-timers.sh` | `User=__APP_USER__`, `ExecStart=run-command.sh <command>`: **i processi girano come l'utente applicativo, non come root** |
| Il dichiarato di deploy | `backend/deploy/sveglie.json` + `apps.core.services.sveglie` | **la whitelist delle unit** (chiave `unit`, regex `_UNIT_AMMESSA` già presidiata), la forma `timer`/`servizio`, `abilita` |
| La coda generica | `dbops.coda_lavori`, `fn_accoda_lavoro` (idempotente, guard di classe), `draina_coda_lavori` ogni minuto, `handler_registry`, `run_as` `OPERATORE`/`SISTEMA` | **l'agente sull'host**: sveglio, presidiato (`vw_coda_lavori_da_guardare`), con un run per lavoro e un handler per tipo |
| Il giornale | `maintenance.job_run_log` (`auth_user_id`, `origine`, `agent_host`) | l'audit «chi, quando, con che esito». ⚠️ `agent_host` è `inet_client_addr()`: **osservato dal DB**, non dichiarato dall'host |
| Il contratto e il panorama | `dbops.processi.tolleranza_minuti`/`segno_di_vita`, `vw_processi_programmazione` | lo **stato** accanto al pulsante: `OK`/`MUTO`/`MAI_PARTITO`/`FUORI_PORTATA` |
| Il permesso tecnico | area `strumenti` (13) + azione `code_manage` (28) | il **precedente**: un'azione cross-utente su strumenti tecnici, assegnata a un profilo, con bypass super admin |
| La UI | `ProcessiAutomaticiListView.vue`, `ProcessoDrawer.vue`, `PresidiProcessiPanel.vue`; API `amm_software/processi/*` | il posto dove il pulsante starebbe: **il drawer del processo**, che ha già il tab «Ultimi run» |

**Che cosa NON c'è**: un `sudoers` o una regola polkit nel repo (l'utente
applicativo non può toccare systemd); una **dimensione host** nel modello
(né su `coda_lavori`, né a catalogo); un'azione di processo per il riavvio.

## 3. ⛔ Perché non la forma diretta — il web che chiama `systemctl`

Sono le ragioni del §9 del brief dei quattro processi, scritte per la lettura e
valide identiche per l'azione, più una:

1. **Privilegi.** gunicorn gira come l'utente applicativo. Una richiesta HTTP
   che arriva a `sudo systemctl` è il perimetro peggiore possibile: chi trova
   una strada verso quell'endpoint ha un comando root su un host. E un `sudo`
   *dentro il processo web* è un `sudo` che ogni endpoint può raggiungere.
2. **L'host.** `systemctl` risponde **solo per la macchina che serve la
   richiesta**: con due backend dietro un bilanciatore il pulsante riavvia «un
   host a caso»; in un container systemd non esiste.
3. **Il guasto che si vuole curare.** Se a essere morto è il processo web, il
   pulsante non c'è. Chi esegue il riavvio dev'essere qualcuno che *non muore
   insieme* a ciò che riavvia.

## 4. La forma che regge: la UI dichiara, l'host esegue

È il disegno del guardiano applicato a un gesto umano: **il web scrive una
richiesta su `dbops.coda_lavori`**, il drenatore dell'host giusto la prende e
fa `systemctl`. Nessun privilegio nel processo web, nessun `systemctl` fuori
dall'host, e se l'esecutore è morto la richiesta resta «mai presa» — cioè
**visibile** in `vw_coda_lavori_da_guardare`, non persa.

### 4.1 Il gesto — due verbi, non uno

| Verbo | Per chi | Che cosa fa | Perché |
| --- | --- | --- | --- |
| **Riavvia** | `forma = servizio` (oggi: `listen_cambio_reparto`) | `systemctl restart <unit>.service` | un servizio sempre acceso che è morto |
| **Esegui ora** | `forma = timer` (drenatori, email, digest, fatturazione) | `systemctl start <unit>.service` — **una corsa adesso**, il timer tiene il suo orario | un digest in ritardo, una coda da svuotare subito: più utile del riavvio, e non tocca la programmazione |

⛔ Non c'è un terzo verbo «accendi il timer» (`systemctl enable/start
<unit>.timer`): è **`abilita`**, cioè un fatto di deploy che il DB ha
dichiarato fuori dal catalogo (§10.2 del brief). Accenderlo da video vorrebbe
dire avere quella decisione a catalogo, per host — vedi §5.

### 4.2 La richiesta — un tipo di coda, un processo a catalogo

* **Tipo** `dbops.coda_lavori_tipi`: `RIAVVIA_UNIT` (e `ESEGUI_UNIT`, o un tipo
  solo con il verbo nel payload — D3). `handler_code` proprio, `attivo = false`
  fino alla release dell'handler (regola del binding, come `NOTIFICA_DIGEST_MUTO`).
* **Processo** `dbops.processi`: la FK `processo_codice` è `NOT NULL`, quindi il
  tipo vuole un processo. Uno nuovo — `riavvio_unit` (o `gestione_unit`) —
  classe **`MANUTENZIONE`**, canale **`CODA`**: *lo accoda una persona, e
  l'identità è la sua* (è la lettura di `CODA` già scritta in
  `processi_repository.py`). Niente utente tecnico, niente emittente.
* **Payload**: `{unit, verbo, host, processo_codice}` — l'unit **presa dalla
  whitelist di `sveglie.json`**, mai dalla richiesta libera (il service la
  risolve dal `processo_codice` e dalla forma; il client manda il processo,
  non l'unit).
* **`run_as`**: `OPERATORE`, così `scope` porta l'identità di chi ha chiesto e
  il run sul giornale ha `auth_user_id` **gratis** (D4). L'handler non tocca
  nessuna tabella con RLS: l'identità serve all'audit, non al perimetro.
* **Idempotenza**: `idempotency_key = f"{verbo}:{unit}:{host}"` sui job vivi —
  due click non fanno due riavvii; il secondo trova il primo `PENDING`.

### 4.3 L'esecutore — un handler nel drenatore

`apps/core/services/coda_lavori/riavvia_unit_handler.py`, registrato in
`CoreConfig.ready()`, e fa **quattro cose sole**:

1. ricontrolla che `unit` sia **una di `sveglie.json`** e passi `_UNIT_AMMESSA`
   (difesa in profondità: il produttore l'ha già fatto, ma la whitelist è la
   sede e si rilegge dove si esegue);
2. verifica che `host` sia **questo host** (§5) — altrimenti non tocca niente e
   solleva un errore parlante (ma vedi §5: il claim non dovrebbe nemmeno
   arrivargli);
3. esegue `["sudo", "-n", "/usr/bin/systemctl", verbo, f"{unit}.service"]` come
   **lista di argomenti, senza shell**, con timeout; `-n` = non interattivo:
   senza regola `sudoers` fallisce **rumorosamente** (`E_CONFIG_MANCANTE`,
   terminale), non aspetta una password che nessuno darà;
4. rilegge `systemctl is-active <unit>` e lo mette nel `result` del job: l'esito
   è **lo stato dell'unit dopo**, non «il comando è tornato 0».

⛔ Nessun `restart` sul drenatore stesso (`zeroerp-coda-lavori`): è un timer
oneshot, ogni corsa è un processo nuovo — «riavviarlo» non significa niente, e
se il suo *timer* è spento la richiesta non viene presa da nessuno (§6).

### 4.4 Il privilegio — un `sudoers` per host, reso dal dichiarato

L'utente applicativo può fare **solo** i comandi elencati, **unit per unit,
senza wildcard**:

```text
# /etc/sudoers.d/zeroerp-unit   (0440, validato con `visudo -cf`)
Cmnd_Alias ZEROERP_RESTART = /usr/bin/systemctl restart zeroerp-listen-cambio-reparto.service
Cmnd_Alias ZEROERP_START   = /usr/bin/systemctl start zeroerp-digest-presidi-giornaliero.service, \
                             /usr/bin/systemctl start zeroerp-digest-presidi-settimanale.service, \
                             /usr/bin/systemctl start zeroerp-send-pending-emails.service, \
                             /usr/bin/systemctl start zeroerp-coda-stampa.service
__APP_USER__ ALL=(root) NOPASSWD: ZEROERP_RESTART, ZEROERP_START
```

⭐ **Questo file è un RENDER di `sveglie.json`, come gli unit**: lo scrive
`install-timers.sh` dalla stessa lista (`forma = servizio` → `restart`,
`forma = timer` con `abilita` → `start`). Una sede sola: una sveglia nuova
compare nel `sudoers` alla prossima installazione, e una tolta sparisce. ⛔ Un
file scritto a mano sarebbe la seconda sede della whitelist, quella che resta
indietro — e qui «indietro» vuol dire un'unit che il pulsante non può più
toccare, oppure una che può toccare e non dovrebbe.

Alternativa: una regola **polkit** (`org.freedesktop.systemd1.manage-units`
filtrata per nome unit) — più precisa, ma per-distro e meno leggibile in un
audit. `sudoers` è la forma che un tecnico sa leggere (D5).

### 4.5 Il permesso — un'azione di processo

`unit_riavvia` (nome da decidere) sull'area **`strumenti`**, accanto a
`code_manage`: il super admin passa, il tecnico la riceve dal profilo. È il
modello permessi v1 che c'è già; il service fa `check_azione` come
`gestione_service`. ⚠️ **Non** è `code_manage`: chi può requeue-are un job non
è per questo chi può riavviare un servizio sull'host — due azioni, due
decisioni di profilo.

### 4.6 L'audit — viene dal giornale, non da una tabella nuova

Il lavoro registra un run (`registered_job` dentro il drenatore, come ogni
handler): `auth_user_id` di chi ha chiesto (dallo `scope`), `origine`, l'host
che ha eseguito, l'esito con `is-active` dopo. Il drawer del processo ha già il
tab «Ultimi run»: il riavvio compare lì, sotto il processo riavviato, senza
schermate nuove — **se** il run si registra sotto il `processo_codice`
dell'unit riavviata e non sotto `riavvio_unit` (D6: è la stessa domanda
della corsia, «chi è l'attore del run?»).

### 4.7 La UI — un pulsante dove già si guarda

Nel **drawer del processo**, accanto allo stato del panorama: «Riavvia» se la
forma è `servizio`, «Esegui ora» se è `timer` — con `useConfirmAction` e il
motivo dell'azione spenta secondo il pattern delle capability di riga
(`api.md` §«Capability di riga»): spenta con *«nessun host dichiarato»*,
*«unit non abilitata su questo host»*, *«già in coda»*. Dopo il click il
processo mostra «richiesta in coda» e lo stato si aggiorna da solo alla corsa
successiva del panorama — **non** si aspetta il `systemctl` in linea: il gesto
è asincrono per costruzione (§4), e la UI lo dice.

## 5. ⛔ L'host — la domanda che viene prima di tutte

Un riavvio **deve nominare l'host**, e ogni drenatore deve prendere **solo le
richieste sue**. Oggi nel modello l'host non esiste:

* `dbops.coda_lavori` non ha una colonna host, e il claim
  (`FOR UPDATE SKIP LOCKED` su `stato = 'PENDING'`) prende **qualunque** riga;
* `job_run_log.agent_host` è `inet_client_addr()`: dice da che IP è arrivata
  la connessione, cioè un fatto **osservato**, non un nome che un utente possa
  scegliere in un menu;
* il catalogo non sa quali processi sono accesi su quale host — è il limite
  su `abilita` che il DB ha **dichiarato** in §10.2 del brief, rimandando «un
  registro per host a database» al giorno in cui servirà.

**Quel giorno è questo.** Un pulsante «riavvia» costruito senza host su una
installazione a un host solo funziona; alla seconda macchina riavvia quella
sbagliata **in silenzio** — è il caso di scuola della regola zero: *si
sviluppa sul modello, non sulle righe di oggi*. Il fatto datato «oggi un
host» entra qui come contesto, mai come motivo per lasciare l'host `NULL`.

Le forme, dalla minima alla piena:

| Forma | Che cosa | Costo | Che cosa non risolve |
| --- | --- | --- | --- |
| **A — host dichiarato + claim filtrato** | ogni host dichiara il proprio nome (`ZEROERP_HOST` in `env.sh`, letto da `run-command.sh` — dichiarato, non `gethostname()`); la richiesta porta `host` **obbligatorio**; il **claim** del drenatore prende solo `payload->>'host' = <me>` (o una colonna dedicata) | una colonna/campo + il claim + una riga di env per host | l'elenco degli host da offrire a video (si deduce dal giornale: gli host visti negli ultimi N giorni — osservato, non dichiarato) |
| **B — registro degli host a catalogo** | `dbops.host` (nome, descrizione, attivo, ultimo battito) + `dbops.host_unit` (quale unit è accesa dove) — cioè `abilita` **per host** a database, che è ciò che il DB ha rimandato | un modello nuovo, un brief DB, il battito degli host | — |

⭐ **A non preclude B**, e B è dove il §10.2 del brief dice di andare. La
scelta minima onesta è **A con l'host obbligatorio dal primo giorno**, e B quando
`abilita` per host diventa una domanda vera (secondo host, container). Ma è la
decisione D1, e va presa **prima** di scrivere il tipo di coda: il payload e il
claim dipendono da lei.

## 6. Che cosa non può fare, e va detto a video

* **Installare un timer mancante** (`MAI_PARTITO` con unit assente): serve root
  e il checkout — resta `install-timers.sh` a mano. Il pulsante «Esegui ora» su
  un'unit non installata fallisce con `systemctl` che non la trova: esito
  parlante, non silenzio.
* **Riavviare l'esecutore.** Se il timer del drenatore è spento, la richiesta
  resta `PENDING` «mai presa» → `vw_coda_lavori_da_guardare` → pannello e
  digest → una persona con una shell. È **giusto così**: l'ultimo anello è
  umano, e questo disegno lo lascia visibile invece di fingere di chiuderlo.
* **Riavviare gunicorn** (il web stesso): fuori scope per lo stesso motivo —
  chi lo chiede sta parlando col processo che vuole riavviare.
* **Il riavvio automatico** (il guardiano che accoda un `RIAVVIA` su `MUTO`) è
  tecnicamente lo stesso pezzo, ma un riavvio in loop su un processo che muore
  per un bug **nasconde il bug**. Se un giorno si vuole, va tenuto a *una volta
  al giorno* con la stessa idempotenza del guardiano, e va deciso a parte (D7).

## 7. 🟠 Decisioni per Tid — in quest'ordine

| # | Domanda | Raccomandazione | Perché |
| --- | --- | --- | --- |
| **D1** | **L'host**: forma A (dichiarato + claim filtrato) o B (registro a catalogo)? E l'elenco a video da dove viene? | **A subito, con `host` obbligatorio**; B è la direzione già scritta nel §10.2 del brief | senza D1 non si può scrivere né il payload né il claim; A non preclude B |
| D2 | Il **claim per host** è una colonna su `coda_lavori` o un filtro sul payload? | colonna (`host_target text NULL`; `NULL` = qualunque host, com'è oggi per tutti gli altri tipi) | un filtro su `payload->>'host'` è una convenzione che ogni tipo dovrebbe ricordare; una colonna la vede il claim di tutti |
| D3 | **Un tipo con il verbo nel payload** o **due tipi** (`RIAVVIA_UNIT`, `ESEGUI_UNIT`)? | due tipi | il `sudoers` distingue `restart` da `start` per unit; due tipi rendono la distinzione visibile anche nella coda e nel presidio |
| D4 | `run_as = OPERATORE` (identità nello `scope`, audit gratis) o `SISTEMA` + `auth_user_id` nel payload? | **`OPERATORE`** | «lo accoda una persona, l'identità è la sua» è la semantica di `CODA` già scritta nel repository; e il run porta `auth_user_id` senza una riga in più |
| D5 | Privilegio: **`sudoers` reso da `sveglie.json`** o regola polkit? | `sudoers` reso | una sede sola (il dichiarato), leggibile in audit, per-distro-indipendente |
| D6 | Il run del riavvio si registra sotto **il processo riavviato** o sotto `riavvio_unit`? | sotto il processo riavviato, `stepname = 'riavvio'` (o `'esegui_ora'`) | compare nel tab «Ultimi run» del processo giusto senza una schermata nuova. ⚠️ Ma un run «riavvio» sotto `listen_cambio_reparto` **sposta `giornale_ultima_corsa`** del processo: per un `SESSIONE` non conta (il segno è la sessione), per un timer con contratto **farebbe sembrare vivo** un processo che si è solo provato a far partire — è lo stesso rilevatore R-12 protetto in `processi.py`. ⇒ Se D6 = «sotto il processo», il panorama deve **escludere** quell'origine/stepname dal segno di vita; altrimenti `riavvio_unit` |
| D7 | Riavvio **automatico** dal guardiano su `MUTO`? | **no**, per ora | nasconde il bug che ha ucciso il processo; se mai, una volta al giorno e a parte |
| D8 | Nome dell'azione di processo e chi la riceve nei profili | `unit_riavvia` su `strumenti`; profili: da decidere in-app | è una decisione di profilo, non di codice |

## 8. Rischi, e come si contengono

| Rischio | Contenimento |
| --- | --- |
| **Iniezione** nel nome dell'unit | l'unit non arriva mai dal client: il service la risolve dal `processo_codice` + forma via `sveglie.json`; l'handler la ricontrolla contro la stessa whitelist e `_UNIT_AMMESSA`; `subprocess` a lista, mai shell; il `sudoers` elenca i comandi completi |
| **`sudo` che aspetta una password** (regola assente) | `sudo -n`: fallisce subito, `E_CONFIG_MANCANTE` terminale, visibile nel presidio della coda |
| **Doppio click / due tecnici** | `idempotency_key` sui job vivi: il secondo trova il primo |
| **Host sbagliato** | D1/D2: host obbligatorio, claim filtrato; un host che riceve una richiesta non sua **non la esegue** e lo dice |
| **Falso «vivo»** dopo un tentativo di avvio | D6: il run del riavvio non è un segno di vita del processo riavviato |
| **Un tecnico che riavvia a raffica** | la coda è un giornale: ogni gesto ha un run con chi/quando; se serve, `run_after` con un minimo fra due riavvii della stessa unit — è una riga nell'handler, non un rate limit a parte |
| **Il file `sudoers` reso male** | `install-timers.sh` lo scrive in un temporaneo e lo valida con `visudo -cf` **prima** di copiarlo; un `sudoers` rotto blocca `sudo` per tutti, ed è l'unico modo per non scoprirlo dopo |

## 9. Sequenza, se si fa

1. **D1 + D2** (l'host): brief DB — colonna `host_target` su `coda_lavori` e
   claim filtrato (o il registro, se B). È il pezzo che decide tutto il resto.
2. **DB**: processo `riavvio_unit` (MANUTENZIONE, CODA), i tipi (`attivo = false`),
   l'azione `unit_riavvia` su `strumenti`; pgTAP sul claim per host.
3. **Deploy**: `ZEROERP_HOST` in `env.sh` per host; `install-timers.sh` rende
   anche `/etc/sudoers.d/zeroerp-unit` e lo valida; `test-install-timers.sh`
   prova il render (come già prova gli unit).
4. **BE**: handler + registrazione; endpoint
   `POST /api/v1/amm-software/processi/<codice>/riavvia/` e `/esegui-ora/`
   (verbo come ultimo segmento, `handle_post_json`, `Idempotency-Key`,
   `check_azione`); il service risolve unit e host e accoda.
5. **FE**: i due pulsanti nel drawer, con il motivo dell'azione spenta.
6. **Team DB**: `attivo = true` sui tipi, a release BE avvenuta.

## 10. Fuori scope, dichiarato

* Accendere/spegnere i **timer** (`enable`/`disable`): è `abilita` per host,
  cioè la forma B di §5 — non prima di quella.
* Riavviare **gunicorn** o il **drenatore**: §6.
* Vedere lo **stato di systemd** a video (`is-active`, `journalctl`): il §9 del
  brief l'ha scartato per la lettura, e resta scartato — lo stato lo dà il
  panorama dall'**effetto**, non dallo schedulatore. L'unica lettura ammessa è
  l'`is-active` **dopo** un riavvio, nel `result` del job.

---

*Analisi del 2026-09-11. I fatti sono letti dal repo e dal dbdev di quel
giorno: le unit, la coda, il giornale, il panorama e il pannello esistono come
descritti; l'host non esiste nel modello, e questo è il punto.*
