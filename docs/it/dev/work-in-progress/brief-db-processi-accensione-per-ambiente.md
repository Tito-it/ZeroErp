# Brief DB — Quali processi sono accesi: per ambiente, a mano, e quelli che non si spengono

## ⏭️ Chi riparte — aggiornato al 2026-10-16

**Riparte: la sessione BE/FE (§6). Il giro 1 è applicato e verde (2026-10-16). Il giro 2 (R-4, i
dati di sviluppo) aspetta che il BE dica che cosa crea il provisioning di sviluppo.**

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | Tid | ✅ decisioni A-1…A-5, P-1…P-3, R-1…R-4 (2026-10-15/16) | §4, §4-bis, §4-ter | — |
| 2 | team DB | ✅ giro 1 scritto e provato sullo scratch (2026-10-16): `20261016-15` … `-32` | §5-bis | — |
| 3 | Tid | ✅ apply del giro 1, fase `post` su dbdev (`SVILUPPO`, 2026-10-16 14:20), pgTAP verdi | §5-bis.4 | — |
| 4 | sessione BE/FE | 🔨 punti 1-6 del §6.0 fatti e verdi (2026-10-16, §6.1); dopo l'incidente delle 23:45 i tetti di rete e delle sveglie (2026-10-17, §6.2). Punto 7 deciso (§6.3): resta la richiesta R-BE-4 al team DB, e la reinstallazione delle sveglie su dbdev | §6.1, §6.2 | — |
| 4-bis | team DB | le richieste del BE (R-BE-1 … R-BE-3 al §6.1, R-BE-4 al §6.3) | §6.1, §6.3 | — |
| 5 | sessione BE | ✅ che cosa crea il provisioning di sviluppo: l'elenco è in [brief-be-utenti-di-sviluppo §7](brief-be-utenti-di-sviluppo.md) (2026-10-16), decisioni di Tid del §7.4 prese (emittenti nuovi dal verbo, niente `dev.shop` per ora, portale senza contratto) | §5-ter | — |
| 6 | team DB | giro 2 (R-4): etichette, verbo del provisioning di sviluppo, presidio | §5-ter | 5 |
| 7 | chi chiude | archiviazione, riga di PROJECT_CONTEXT | — | 4, 6 |

Decisioni aperte di Tid: nessuna. Lavoro DB del giro 1 da committare.

> ✅ **Giro 1 applicato** il 2026-10-16 su dbdev e sullo scratch, ambiente `SVILUPPO` dichiarato su
> tutti e due; corsa pgTAP di Tid verde. In corsa si è corretto un difetto del test (§5-bis.5).

> **Chi scrive:** team DB (`dev/db-tid`), 2026-10-15. **A chi:** Tid, poi il team DB e la sessione BE/FE.
> **Origine:** domanda di Tid del 2026-10-15: lo smoke notturno è acceso solo in sviluppo; estendere
> la stessa idea agli altri processi, deciderne l'accensione anche da interfaccia, e stabilire quali non
> si possono mai spegnere.
> **Ricadute BE/FE:** sì (§6).
> **Stato:** 📝 decisioni prese, proposte da confermare, codice non iniziato.

## 1. Il caso

Un processo automatico oggi si accende in tre posti diversi, e in nessuno dipende dall'installazione:

| Sveglia | Dove si decide se è acceso | Per ambiente? |
| --- | --- | --- |
| Timer o servizio systemd | `abilita` in `backend/deploy/sveglie.json`, letto da `backend/bin/install-timers.sh` | no: un booleano uguale su ogni host |
| Job pgAgent | i changeSet di `85_pgagent`, tutti con `jobenabled = true` | no |
| Processi `CODA` | nessuno: li avvia una persona o il drenatore | non serve |

Lo smoke notturno è «solo sviluppo» per due accorgimenti, non per una regola: `abilita: false` (la
sveglia si accende a mano su dbdev) e il consenso `SMOKE_NOTTURNO_CONSENTITO=1` nell'ambiente del
comando. Il modello non sa che cosa sia un'installazione di sviluppo.

E manca la domanda opposta: niente dice che certi processi **non** si possono spegnere. Oggi chi
spegne `listen_permessi` lascia agli utenti i diritti tolti, senza che nessuno se ne accorga.

## 2. Perché è un difetto del modello

* **Il default è del processo**, non del deploy: «gli smoke scrivono dati di prova» è vero su ogni
  macchina. Sta quindi nel catalogo `dbops.processi`, come il contratto di liveness
  (`tolleranza_minuti`, `segno_di_vita`), che `sveglie.json` già non ripete (`_contratto`).
* **La scelta di una macchina** («qui il batch delle stampe lo spengo») è un dato di macchina, come
  `dbops.processi_identita`: non sta nel seed.
* **Il panorama non distingue spento da morto**: per questo lo smoke ha tolleranza NULL (decisione del
  2026-10-13), col prezzo dichiarato che un timer fermo su sviluppo non lo vede nessuno.

## 3. I fatti di struttura (2026-10-15)

* `dbops.processi`: 28 righe nel CSV `80_data/sql/dbops/processi.csv`, 26 vive e 2 ritirate
  (`sync_auth_user_active`, `listen_cambio_reparto`). Canali: 16 `PGAGENT` (compreso
  `chiusura_scadenze_daily`, `CODA_AUTOMATICA` svegliato da pgAgent), 7 `COMMAND` vivi su 9 unit
  systemd, 3 `CODA`.
* `config.parameters`: `code`, `default_value`, seminato dal CSV `parameters_sistema.csv`
  (`loadUpdateData`: il CSV riscrive il valore a ogni migrate). `config.parameter_overrides` scavalca
  per utente, sessione, gruppo, emittente: non per installazione.
* La convergenza strutturale non dipende dai job notturni dove si migra col contesto `ci_apply`:
  `90_end/ci_apply/20260926-10` chiama in ordine le procedure dei job strutturali (`ci_ordine`), e lo
  fa ogni installazione (passo 6 di `installazione.md`). Su dbdev il migrate normale non passa da lì: le
  fanno i job.
* Il panorama `dbops.vw_processi_programmazione` conosce `MAI_PARTITO`, `IN_ATTESA`,
  `JOB_IN_RITARDO`; nessuno stato «spento».
* Le sveglie calendariali hanno già un cancello all'avvio: `ExecCondition=… e_dovuto <unit>` (esce 1,
  systemd salta senza errore).

## 4. Decisioni di Tid (2026-10-15)

* ✅ **A-1 — l'ambiente è un dato del DB**, interrogabile da chiunque ne abbia bisogno (oggi i
  processi, domani altre attività): valori `SVILUPPO` / `PRODUZIONE`. `SVILUPPO` per sbaglio mai.
  ⚠️ Rivista il 2026-10-16 (R-2): **nessun default**, l'ambiente si sceglie come parametro
  all'installazione. Un default scritto dal changeSet avrebbe fatto di dbdev, già esistente, un
  `PRODUZIONE` per sempre. Lo scopo di A-1 resta: `SVILUPPO` non capita per caso, va scritto.
* ✅ **A-2 — il default per ambiente sta in `dbops.processi`**, e `abilita` di `sveglie.json` si ritira
  (doppione). In più **la scelta a mano da interfaccia**: un operatore autorizzato spegne o riaccende
  un processo su questa installazione. **Alcuni processi non si spengono mai.**
* ✅ **A-3 — i dodici strutturali restano accesi di default anche in produzione**, spegnibili. In
  produzione convergono già al rilascio, ma nel dubbio (tabelle di guida cambiate a runtime) si
  tengono accesi.
* ✅ **A-4 — `send_pending_emails` è acceso anche in sviluppo**: serve già a provare gli utenti.
* ✅ **A-5 — i non spegnibili**: un processo non si spegne quando, spento, si rompe la sicurezza o la
  correttezza dei dati senza che nessuno se ne accorga. Sono sette (tabella di §5.1).

## 4-bis. Proposte del team DB

* ✅ **P-1 — dove sta il valore di macchina dell'ambiente**: assorbita da §4-ter (R-3). Non in
  `config.parameters`: il CSV lo riscriverebbe a ogni migrate, e l'app lo potrebbe cambiare.
* ✅ **P-2 — «Esegui ora» su un processo spento NON si può** (Tid, 2026-10-15; la proposta del team
  DB era il sì): prima lo si riaccende. Spento vuol dire spento, anche a mano. Il verbo che accoda
  `ESEGUI_PROCESSO` rifiuta un processo spento (codice d'errore registrato) e l'handler lo ricontrolla
  quando parte; il drawer mostra il pulsante disabilitato col motivo. `avvio_manuale` resta la sede di
  «il pulsante ha senso», lo stato effettivo si aggiunge come seconda condizione.
* ✅ **P-3 — il cancello vale solo per la sveglia** (Tid, 2026-10-16). La convergenza del rilascio
  (`20260926-10`, contesto `ci_apply`) chiama le procedure strutturali **sempre**, anche se il processo
  è spento: spegnere il job notturno non deve lasciare una struttura a metà dopo un rilascio.

## 4-ter. Richieste del BE (2026-10-15)

> Arrivate dalla sessione BE, che userà l'ambiente anche fuori dai processi (un command che deve
> girare solo in sviluppo). Il team DB le accoglie tutte; R-4 è stata completata il 2026-10-16 col
> requisito dell'etichetta portato dal BE e le decisioni di Tid.

* **R-1 — il lettore valida e non ripiega.** Come `script.fn_fuso_operativo()`: niente cascata di
  override (un ambiente per utente o per emittente non ha senso), niente ripiego. Valore assente o
  diverso da `SVILUPPO`/`PRODUZIONE` → `E_CONFIG_MANCANTE` (già a catalogo, `TECNICO`). Il lettore è
  `script.fn_ambiente_installazione()`, l'unico punto da cui si chiede.
  ⚠️ Conseguenza da scrivere: lo stato effettivo di un processo **non spegnibile** non legge
  l'ambiente (è acceso e basta), così un'installazione rotta non ferma anche i sette processi che non
  devono fermarsi mai.
* ✅ **R-2 — l'ambiente si sceglie all'installazione, come parametro; nessun default** (osservazione
  del BE e decisione di Tid, 2026-10-16):
  * il changeSet crea la tabella **vuota**: non scrive niente, perché troverebbe database già esistenti
    (dbdev, lo scratch, la CI) e li dichiarerebbe al posto di chi li conosce;
  * lo scrive la **fase `post` di `scripts/sql/provision_zeroerp.sql`** (gira dopo le migrazioni) con
    `-v ambiente=SVILUPPO|PRODUZIONE`, come le password. Riga assente e parametro mancante → lo script
    si ferma e chiede di scegliere. Riga presente → il parametro è facoltativo, ma se c'è deve
    coincidere (immutabile);
  * chi dichiara che cosa:

    | Database | Chi lo dichiara | Valore |
    | --- | --- | --- |
    | dbdev | Tid, fase `post` subito dopo l'apply | `SVILUPPO` |
    | scratch `zeroerp_ruoli` | `scripts/ci-local.sh` | `SVILUPPO` |
    | CI di GitHub | il workflow, nel bootstrap | `SVILUPPO` |
    | installazione nuova | `installazione.md` (l'esempio porta `PRODUZIONE`) | scelto da chi installa |

  * fra l'apply e la dichiarazione il lettore dà `E_CONFIG_MANCANTE` (R-1): il verbo di sviluppo non
    parte e i job spegnibili falliscono, visibili; i sette non spegnibili non leggono l'ambiente e
    continuano.
* ✅ **L'ambiente è immutabile** (Tid, 2026-10-16): si scrive una volta, alla nascita, e non cambia
  più, in nessuna delle due direzioni. Un guard sulla tabella rifiuta l'`UPDATE` del valore (e il
  `DELETE` della riga).
  * `SVILUPPO` → `PRODUZIONE` mai: un database di sviluppo contiene dati nati fuori dal verbo (gli
    smoke scrivono dalle API normali e creano soggetti senza etichetta né radice), e nessuna regola
    può certificarlo pulito. Una produzione nasce dal provisioning, vuota.
  * `PRODUZIONE` → `SVILUPPO` mai: protegge dall'errore (un DBA sul database sbagliato). Una copia
    della produzione per fare prove **resta `PRODUZIONE`**: lì smoke e provisioning di sviluppo non
    partono, ed è giusto, perché contiene dati veri. Un ambiente di sviluppo si costruisce da zero.
  * Contro un DBA malevolo nessun guard regge (può aggirarli tutti): quella difesa sono i ruoli, e il
    caso pericoloso indicato dal BE (un amministratore dalla UI) è chiuso da R-3.
* **R-3 — chi lo scrive: solo il provisioning, mai l'app.** Il controllo regge solo se l'app non lo
  cambia, altrimenti un amministratore lo mette a `SVILUPPO`, lancia il command e lo rimette a posto.
  Quindi:
  * sede di macchina **fuori** da `config.parameters` (né pagina di configurazione né loader CSV): una
    tabella di una riga sola, scritta dalla fase `post` del provisioning (R-2), mai da un changeSet;
  * l'app la **legge** e non la scrive. ⚠️ Un `REVOKE` a `zeroerp_app` fuori dal loop dei grant di
    `ci_apply` viene annullato (linee-guida-sql §11.8): la difesa sta nel loop (esclusione dichiarata)
    o in un guard che rifiuta chi non è membro di `zeroerp_owner` (per membership, mai per nome); la
    scelta è del team DB scrivendo, col pgTAP di postura che la prova;
  * la riga dice chi l'ha scritta e quando (audit); un cambio non esiste (immutabile).
* ✅ **R-4 — gli utenti e i dati di sviluppo non stanno in un database `PRODUZIONE`** (requisito del
  BE e decisioni di Tid, 2026-10-16). Lato BE: [brief-be-utenti-di-sviluppo](brief-be-utenti-di-sviluppo.md). Gli utenti `dev.*` sono in preparazione: non ne esiste ancora
  nessuno, e il segno si sceglie prima che nascano.
  * **Un'etichetta, non il nome.** Il prefisso `dev.` si sbaglia a mano in tutti e due i versi
    (`dev_mario` sfugge, una persona vera `dev.qualcosa` suona per niente): resta una convenzione di
    lettura, il presidio guarda l'etichetta.
  * **Sulla credenziale**, in una tabella satellite di una riga per credenziale (come
    `processi_identita`): non su `anagrafiche.identita_digitali`, che ha una riga per veste (due
    vesti, due etichette che possono dissentire), e non su `auth_user`, che è di Django.
  * **La mette solo il provisioning di sviluppo**, mai l'app: l'app la legge.
  * **Non si toglie**: togliendola si nasconderebbe l'utente al presidio.
  * **In `PRODUZIONE` un guard rifiuta di crearla**: impedire prima, non segnalare dopo.
  * **Nessuna quarta categoria, e la categoria non cambia** (Tid, 2026-10-16):
    `script.fn_categoria_accesso` resta `SISTEMA` / `OPERATORE` / `ALTRO` e non legge l'etichetta. La
    categoria dice *che cos'è* una credenziale, l'etichetta *perché esiste*. ⚠️ La categoria non è solo
    il tab: è il cancello della porta degli operatori (`AmmSoftwareService.get_operatore`, 404 se non
    `OPERATORE`). Un operatore di prova messo in `ALTRO` non si aprirebbe né si comanderebbe più come
    operatore, cioè non servirebbe più a provare la gestione degli operatori. Scartate anche le due
    strade di mezzo: una categoria `ALTRO` per gli etichettati (stesso difetto) e la stessa credenziale
    in due tab (cade la partizione A-2 dell'area Accessi).
  * **Nell'area Accessi** (Tid, 2026-10-16, strada b): il tab «Operatori» ha un **filtro, attivo di
    default, che nasconde gli utenti di prova**; togliendolo si vedono, col badge «di prova». La
    lista degli operatori veri resta pulita e quelli di prova funzionano in tutto. Il DB espone
    l'etichetta nella lettura che il BE già usa per le liste (una colonna, non un'altra vista).
  * **I dati di prova** (soggetti, clienti, BA, contratti degli utenti portale) non si etichettano riga
    per riga (Tid): una colonna in decine di tabelle si dimentica alla prima tabella nuova. Tre pezzi:
    1. **la porta**: il provisioning di sviluppo passa da un verbo del DB che rifiuta di partire in
       `PRODUZIONE` (legge `fn_ambiente_installazione()`). Tutti i dati di prova nascono da lì: un
       controllo copre anche le tabelle future;
    2. **le radici**: è radice **ogni credenziale e ogni soggetto creato dal verbo**, non solo la
       persona dietro una credenziale: anche i clienti di prova degli utenti portale e l'emittente di
       prova (oggi `EMITEST`). Il verbo mette l'etichetta mentre li crea, nella stessa transazione:
       l'etichetta è la sua firma. Stesse regole (solo dal verbo, non si toglie, rifiutata in
       `PRODUZIONE`). Contratti, BA e documenti si ritrovano dalla radice a cui sono legati (un
       contratto di prova dal suo cliente, un documento su `EMITEST` dall'emittente);
    3. **niente passaggio a `PRODUZIONE`**: l'ambiente è immutabile (sopra). I soggetti creati dagli
       smoke via API, senza etichetta e senza radice, non sono quindi un problema: nascono solo in un
       database che resta `SVILUPPO`. (Sostituisce la regola del 2026-10-16 «non si passa finché
       esistono radici etichettate», che non vedeva quei soggetti: osservazione del BE.)
  * **L'utente `smoke` di oggi** (Tid, 2026-10-16): non è nato dal verbo, quindi non ha l'etichetta.
    Si crea `dev.smoke` dal verbo e `smoke` si **ritira disattivandolo**, non cancellandolo: le sue
    corse, i documenti e le righe di log lo nominano. Gli script smoke passano a `dev.smoke` (BE).
  * **Il presidio** (vista `dbops` in `dbops.presidi`) resta come ultima rete, per ciò che i guard non
    vedono (un dump di sviluppo ripristinato su un server di produzione con l'ambiente riscritto a
    mano): le radici etichettate in un database `PRODUZIONE`. La vista
    legge `django.auth_user`, che in CI non ha le FK del mondo Django: va scritta in modo che lì sia
    vuota, non rotta.

## 5. Consegna DB

### 5.1 Il catalogo

Due proprietà nuove per processo in `dbops.processi` (CSV), NULL per i processi `CODA` (non hanno una
sveglia) con un CHECK che lo lega al canale:

* il default per ambiente (acceso in sviluppo, acceso in produzione);
* **spegnibile**. CHECK: un non spegnibile è acceso di default in tutti e due gli ambienti.

| Processo | Sviluppo | Produzione | Spegnibile |
| --- | --- | --- | --- |
| `listen_permessi` | acceso | acceso | ⛔ mai: la cache dei permessi resterebbe vecchia |
| `sync_auth_user_expired_daily` | acceso | acceso | ⛔ mai: un utente scaduto resterebbe attivo |
| `chiusura_scadenze_daily` | acceso | acceso | ⛔ mai: gli stati per scadenza resterebbero aperti |
| `draina_coda_lavori` | acceso | acceso | ⛔ mai: ci passano i lavori di tutti, anche «Esegui ora» |
| `guardiano_digest`, `digest_presidi` | acceso | acceso | ⛔ mai: guardano gli altri |
| `send_pending_emails` | acceso | acceso | ⛔ mai (A-5) |
| `draina_coda_stampa` | acceso | acceso | sì |
| `analyze_statistiche` | acceso | acceso | sì: danno di prestazioni, non di dati |
| i dodici strutturali (`automations_*` ×9, `apply_storicizza_weekly`, `sync_storico_set_storicizza`, `apply_fk_index_policy`) | acceso | acceso | sì (A-3) |
| `smoke_notturno` | acceso | **spento** | sì |
| `run_fatturazione_batch` | spento | spento | sì: si accende a mano quando l'installazione è pronta per SDI |
| `FATTURAZIONE_GIRO`, `FATTURAZIONE_NUMERA`, `avvio_manuale` | — | — | — (canale `CODA`) |

### 5.2 La scelta a mano

Tabella di macchina accanto a `processi_identita`: processo, acceso sì/no, motivo; audit e storico
come le altre. Guard: un processo non spegnibile non si spegne (codice d'errore registrato). Chi la
scrive passa da un verbo, con la stessa autorizzazione del drawer dei processi.

### 5.3 Lo stato effettivo

Una funzione sola risponde «questo processo è acceso qui?»: la scelta a mano se c'è, altrimenti il
default per `fn_ambiente_installazione()` (solo per gli spegnibili, R-1). La leggono il cancello di pgAgent, il cancello delle sveglie
systemd (§6) e il panorama.

* **pgAgent:** il passo del job non lancia la procedura se il processo è spento (P-3: solo la sveglia,
  non la convergenza del rilascio), senza scrivere una corsa nel giornale.
* **Panorama:** uno stato `SPENTO` prima di `MAI_PARTITO`. Allora lo smoke può avere una tolleranza
  vera in sviluppo, e il prezzo dichiarato il 2026-10-13 sparisce.

### 5.4 L'ambiente (§4-ter)

La tabella di macchina, il lettore `script.fn_ambiente_installazione()` (R-1), la scrittura nel
fase `post` di `provision_zeroerp.sql` col parametro `ambiente` (R-2) e il suo uso in
`ci-local.sh` e nel workflow della CI, la protezione dall'app (R-3). Per R-4: le due etichette (credenziale, soggetto)
coi loro guard (solo dal provisioning, non si tolgono, rifiutate in `PRODUZIONE`), il verbo del
provisioning di sviluppo che in `PRODUZIONE` non parte (crea credenziali e soggetti di prova e li
etichetta), il guard che rende l'ambiente immutabile, la vista del presidio in `dbops.presidi`.

### 5.5 pgTAP

⚠️ La CI è `SVILUPPO` e l'ambiente non cambia nemmeno dentro un test: il ramo `PRODUZIONE` non si
prova cambiando l'ambiente. Ogni decisione che dipende dall'ambiente (il verbo che parte o no,
l'etichetta ammessa o no, il default di un processo) si scrive come **funzione pura sul valore**, che
riceve l'ambiente come parametro; i pgTAP la chiamano con tutti e due i valori, e il lettore le passa
quello vero.

Il lettore: `SVILUPPO`, `PRODUZIONE`, assente e valore estraneo → `E_CONFIG_MANCANTE`; l'app non scrive
l'ambiente (postura). R-4: l'etichetta rifiutata in `PRODUZIONE`, non scrivibile dall'app, non
cancellabile; il verbo del provisioning di sviluppo rifiutato in `PRODUZIONE`; ogni soggetto creato
dal verbo esce etichettato; l'ambiente non cambia in nessuna delle due direzioni; il presidio vede una radice etichettata (costruita
prima del guard) in `PRODUZIONE` e non in `SVILUPPO`; `fn_categoria_accesso` dà `OPERATORE` a un
operatore etichettato. Il default per ambiente dei processi (sviluppo e produzione); la scelta a mano
scavalca il default; un non spegnibile rifiutato; il CHECK sui `CODA`; il panorama dice `SPENTO`; la
convergenza del rilascio chiama anche un processo spento; il presidio che ogni processo non `CODA`
dichiari le due proprietà.

## 5-bis. Giro 1 scritto (team DB, 2026-10-16): l'ambiente e l'accensione dei processi

### 5-bis.1 I changeSet

| changeSet | Che cosa |
| --- | --- |
| `00_schema/dbops/20261016-15` | nasce `dbops.installazione`, vuota (una riga, `SVILUPPO`/`PRODUZIONE`) |
| `20_code/dbops/20261016-16`, `-17` | il guard dell'ambiente immutabile: UPDATE, DELETE e TRUNCATE rifiutati (`E_AMBIENTE_IMMUTABILE`) |
| `20_code/script/20261016-18` | `script.fn_ambiente_dichiarato()`: il valore o NULL, per chi descrive |
| `20_code/script/20261016-19` | `script.fn_ambiente_installazione()`: il valore o `E_CONFIG_MANCANTE`, per chi decide (R-1) |
| `00_schema/dbops/20261016-20` | `dbops.processi`: `acceso_in_sviluppo`, `acceso_in_produzione`, `spegnibile`; `chk_processi_accensione` NOT VALID |
| `00_schema/dbops/20261016-21` | nasce `dbops.processi_accensione`, la scelta a mano (dato di macchina, motivo obbligatorio) |
| `20_code/dbops/20261016-22`, `-23` | il guard della scelta a mano: senza sveglia, non spegnibile, motivo |
| `20_code/dbops/20261016-24` | `dbops.fn_processo_acceso_su_valori`: **la regola**, pura sui valori (IMMUTABLE, sql) |
| `20_code/dbops/20261016-25` | `dbops.fn_processo_acceso_dichiarato(codice)`: lo stato su questa installazione, senza sollevare |
| `20_code/maintenance/20261016-26` | `maintenance.fn_sveglia_accesa(codice)`: true/false o un errore; DEFINER per `zeroerp_job` |
| `20_code/dbops/20261016-27` | `dbops.fn_imposta_accensione_processo(codice, acceso, motivo)`: il verbo (NULL = torna al default) |
| `20_code/dbops/20261016-28` | panorama: stato `SPENTO` (senza causa, non da guardare), colonna `acceso` in coda |
| `20_code/dbops/20261016-29` | presidio `dbops.vw_ambiente_non_dichiarato` |
| `85_pgagent/20261016-30` | il passo di ogni job di processo avvolto nel cancello `maintenance.fn_sveglia_accesa` |
| `90_end/20261016-31` | convalida di `chk_processi_accensione` dopo il CSV |
| `90_end/20261016-32` | `dbops.installazione` in sola lettura per l'app (forward) |

Fuori dai changeSet: `processi.csv` (tre colonne in coda) e il suo mirror `20260904-13`;
`codici_errore.csv` / `messaggi_errore.csv` (id 1340-1343: `E_AMBIENTE_IMMUTABILE`,
`E_PROCESSO_NON_SPEGNIBILE`, `E_PROCESSO_SENZA_SVEGLIA`, `E_PROCESSO_ACCENSIONE_MOTIVO_OBBLIGATORIO`;
l'ambiente mancante usa `E_CONFIG_MANCANTE`); `presidi.csv` / `presidi_testi.csv` (il presidio
nuovo); il loop dei grant `20260205-41` (`v_tabelle_sola_lettura_app`); `provision_zeroerp.sql`
(fase `post`: il parametro `ambiente` e la postura); `ci-local.sh`, `ci.yaml`, `ci-validate.yaml`
(`-v ambiente=SVILUPPO`); la guida `installazione.md`; le pagine `manual/` dei sei oggetti nuovi e di
`dbops.processi`.

### 5-bis.2 Scelte di forma, dichiarate

* **Il cancello sta nel passo pgAgent**, non nella procedura né in `fn_run_and_log`: la convergenza
  del rilascio chiama le stesse procedure e deve chiamarle sempre (P-3). Il passo esistente si
  **avvolge**, non si riscrive. Un job nuovo di un processo nasce già avvolto (lo presidia il pgTAP).
* **Due lettori dell'ambiente**: chi decide (`fn_ambiente_installazione`, solleva) e chi descrive
  (`fn_ambiente_dichiarato`, NULL). Il panorama non muore su un'installazione non dichiarata: lo dice
  il presidio, una volta.
* **Un non spegnibile non legge l'ambiente**: un'installazione non dichiarata non ferma i sette
  processi che non devono fermarsi (R-1).
* ⚠️ **Le automazioni di `ci_apply` non coprono `dbops`** (`automation_scope.csv`: solo
  `sessioni_utente`). Le due tabelle nuove non hanno storico né `tx_id`: `dbops.installazione` non
  cambia mai; di `dbops.processi_accensione` resta l'ultima scelta (chi, quando, perché), e
  `data_update`/`user_update` li scrive il verbo. Una storia delle scelte è un cantiere a parte.
* **Il CHECK è rigido**: un processo con una sveglia dichiara le tre colonne. Censiti gli scrittori
  di `dbops.processi` nei pgTAP: **22 inserimenti in 15 file** creavano processi finti con una sveglia
  senza le colonne; adeguati con `true, true, true` (acceso ovunque, spegnibile), che non cambiano
  ciò che quei test provano. In tre (`test-processi-registro` 1-3, `test-processi-coda-automatica` 2,
  `test-vw-processi-programmazione` 2-3) il test misura **quale** vincolo scatta: senza le colonne
  sarebbe scattato il CHECK nuovo, rosso o verde per il vincolo sbagliato. Più
  `test-fn-guardiano-digest` (ritira per finta `digest_presidi`: le tre colonne a NULL) e
  `test-vw-processi-programmazione` test 7 (un COMMAND senza contratto può essere anche `SPENTO`).

### 5-bis.3 La prova (scratch `zeroerp_ruoli`, 2026-10-16)

SQL estratto dai changeSet + l'upsert completo di `processi.csv` + le righe nuove dei codici e dei
presidi + `90_end` + `85_pgagent` (pgAgent c'è, sullo scratch) + la dichiarazione `SVILUPPO`, in una
transazione annullata, come `zeroerp_owner`:

* i 16 passi pgAgent avvolti **compilano tutti** (eseguiti con la condizione resa falsa); ripassare il
  changeSet non riavvolge niente; il passo di un processo spento eseguito **non** scrive nel giornale,
  quello di un processo acceso sì (controllo a mano su `guardiano_digest`);
* il panorama: `run_fatturazione_batch` è `SPENTO`, gli altri come prima;
* pgTAP nuovi: `dbops/test-processi-accensione-v1` **31/31**, `dbops/test-installazione-ambiente-v1`
  **23/23** (i test dei passi pgAgent girano davvero, non in skip);
* i 15 pgTAP con le fixture adeguate: identici prima e dopo;
* 42 pgTAP che leggono processi, presidi, giornale e codici d'errore, presidi trasversali compresi
  (`riferimenti-morti`, `catalogo-messaggi-errore-completo`, `rubinetto-primo-motivo`,
  `storico-scope-policy`, `stati-check-scrittori`, `catalogo-presidi`, `processi-convergenza-ci`,
  `vw-codici-errore-*`, `security-definer-search-path`): **identici prima e dopo**; i rossi sono gli
  stessi sei di partenza;
* cancelli statici della CI (runOnChange, letterali, preCondition, DDL su trigger generati, GRANT
  batch, timestamp, v1, preambolo pgTAP): verdi.

⚠️ Non provato prima dell'apply: la corsa **come app** (la prova gira da owner); la fase `post` del
provisioning (serve un superuser: si prova alla prima corsa di `ci-local.sh` o in CI).

### 5-bis.4 Per Tid: l'apply e la dichiarazione di dbdev

1. apply (Liquibase) del giro 1;
2. **subito dopo**, su dbdev: `provision_zeroerp.sql` fase `post` con `-v ambiente=SVILUPPO`. Finché
   non lo fai, `dbops.vw_ambiente_non_dichiarato` ha una riga e le sveglie spegnibili falliscono con
   `E_CONFIG_MANCANTE` (i sette non spegnibili continuano);
3. pgTAP: i due nuovi più i 15 adeguati. `dbops/test-installazione-ambiente-v1` test 4 è rosso su un
   database non ancora dichiarato: è ciò che deve dire.
4. sullo scratch: `ci-local.sh` dichiara `SVILUPPO` da solo alla prima corsa.

### 5-bis.5 Dopo l'apply (2026-10-16)

Prima della fase `post`, su dbdev `dbops/test-installazione-ambiente-v1` si fermava al test 5: il
lettore che decide era chiamato senza protezione, e su un database non dichiarato l'eccezione
interrompeva il file (20 test su 23 non giravano). Ora passa da `pg_temp.codice_errore`: un database
non dichiarato dà rossi puliti (4, 5, 6, 7, 8, 10), e dichiarato 23/23. Dichiarato dbdev, tutto verde.

## 5-ter. Giro 2 (R-4): i dati di sviluppo — da scrivere

> Il lato BE (il command, gli smoke, la lista Operatori) e l'elenco di che cosa crea il verbo stanno
> in [brief-be-utenti-di-sviluppo](brief-be-utenti-di-sviluppo.md).

Le etichette (credenziale, soggetto) coi loro guard, il verbo del provisioning di sviluppo che in
`PRODUZIONE` non parte, il presidio delle radici etichettate in un database `PRODUZIONE`, la colonna
dell'etichetta nella lettura della lista operatori (§4-ter, R-4). Il verbo crea ciò che il BE sta
disegnando: **serve dal BE l'elenco** di che cosa crea (gli utenti `dev.*` e le loro vesti, le persone,
i clienti di prova degli utenti portale con i loro contratti, `EMITEST`, `dev.smoke`), con quali dati.
Prima di quell'elenco il verbo sarebbe una forma vuota.

## 6. Ricaduta BE/FE

### 6.0 ⭐ Al BE, dal giro 1 applicato (team DB, 2026-10-16)

> Il giro 1 è applicato su dbdev e sullo scratch (`20261016-15` … `-32`), con l'ambiente
> `SVILUPPO` dichiarato su tutti e due, e pgTAP verdi. Le richieste qui sotto sono in ordine: la
> prima rompe un vostro guardrail finché non la fate. Il dettaglio di ogni punto è nell'elenco che
> segue (§6).

| # | Che cosa | Con che cosa, dal DB |
| --- | --- | --- |
| 1 | **Rigenerare i codici d'errore**: `error_policies_generated.py` e i ripieghi di `error_messages_fallback.py`. Finché non si fa, il guardrail dei codici del backend è rosso | `E_AMBIENTE_IMMUTABILE` (TECNICO), `E_PROCESSO_NON_SPEGNIBILE`, `E_PROCESSO_SENZA_SVEGLIA` (NON_ESEGUIBILE), `E_PROCESSO_ACCENSIONE_MOTIVO_OBBLIGATORIO` (DATO_ERRATO); l'ambiente mancante usa `E_CONFIG_MANCANTE` |
| 2 | **La sveglia systemd chiede al DB** se partire: un `ExecCondition` accanto a `e_dovuto`. Da spento systemd salta senza errore | `SELECT maintenance.fn_sveglia_accesa('<processo_codice>')`: `true`/`false`, oppure un errore (`E_PROCESSO_NON_TROVATO`, `E_PROCESSO_SENZA_SVEGLIA`, `E_CONFIG_MANCANTE`) |
| 3 | **«Esegui ora» su un processo spento è rifiutato** (P-2): il motivo 2 di `motivi_esegui_ora` legge la stessa funzione invece di `abilita` | come al punto 2. Se tenete `E_PROCESSO_SVEGLIA_NON_ABILITATA`, la sua nota nel CSV la aggiorniamo noi: ditecelo |
| 4 | **Si ritira `abilita`** da `sveglie.json`, dai test e da `install-timers.sh`: l'installer installa tutte le sveglie, decide il DB | il default per ambiente è in `dbops.processi` (`acceso_in_sviluppo`, `acceso_in_produzione`, `spegnibile`) |
| 5 | **Il drawer dei processi**: lo stato effettivo e da dove viene (default dell'ambiente o scelta a mano: chi, quando, perché); l'interruttore, assente sui non spegnibili; «Esegui ora» disabilitato su un processo spento; l'ambiente dell'installazione in testa | verbo `dbops.fn_imposta_accensione_processo(codice, acceso, motivo)` (`acceso` NULL = torna al default; restituisce lo stato effettivo); la scelta in `dbops.processi_accensione`; l'ambiente da `script.fn_ambiente_dichiarato()`. Il permesso è vostro, come per «Esegui ora». Togliere una scelta non lascia traccia nella tabella: registratela nel vostro registro delle operazioni |
| 6 | **Il panorama ha lo stato `SPENTO`** (non da guardare) e la colonna `acceso` in coda: un'etichetta nel FE | `dbops.vw_processi_programmazione` |
| 7 | **Lo smoke**: decidere la tolleranza in sviluppo (ora che spento non è morto) e se il consenso `SMOKE_NOTTURNO_CONSENTITO` resta come seconda serratura | la tolleranza la scriviamo noi nel catalogo, su vostra indicazione |

⭐ **E una domanda, che apre il giro 2 (R-4, §5-ter).** Il verbo del provisioning di sviluppo crea
ciò che state disegnando, e prima di scriverlo ci serve **l'elenco di che cosa crea**, con i dati di
ciascuno:

* gli utenti `dev.*`: quali, con quali vesti (operatore, portale, shop…), quale azienda e quale
  profilo;
* le persone dietro di loro;
* i clienti di prova degli utenti portale, con i loro BA e contratti;
* l'emittente di prova (`EMITEST`, oggi creato a mano);
* `dev.smoke`, che prende il posto di `smoke`.

Con quell'elenco il team DB scrive le etichette (credenziale e soggetto), il verbo che in
`PRODUZIONE` non parte, il presidio e la colonna dell'etichetta nella lista degli operatori.


* **Cancello delle sveglie:** un `ExecCondition` che chiede al DB lo stato effettivo, accanto a
  `e_dovuto` dove c'è; da spento systemd salta senza errore. L'installer installa **tutte** le
  sveglie: `abilita` si ritira da `sveglie.json`, dai test e da `install-timers.sh`.
* **Smoke:** il consenso `SMOKE_NOTTURNO_CONSENTITO` diventa la lettura di `SVILUPPO`, oppure resta
  come seconda serratura: da decidere col giro BE.
* **Drawer dei processi:** lo stato effettivo e da dove viene (default dell'ambiente o scelta a mano,
  con chi e quando); l'interruttore, assente sui non spegnibili; «Esegui ora» disabilitato su un
  processo spento (P-2); l'ambiente dell'installazione in testa.
* **Provisioning di sviluppo (R-4):** il command che crea gli utenti `dev.*` e i loro dati passa dal
  verbo del DB (che in `PRODUZIONE` non parte) e non scrive le etichette per conto suo.
* **Utente smoke (R-4):** gli script passano da `smoke` a `dev.smoke`, creato dal verbo; poi `smoke`
  si disattiva (non si cancella).
* **Installazione:** `installazione.md` porta `-v ambiente=…` nel comando della fase `post` (esempio
  `PRODUZIONE`) e dice che dopo non si cambia. `ci-local.sh` e il workflow della CI passano
  `SVILUPPO` (sono script di DB, li aggiorna il team DB col changeSet).
* **Codici d'errore:** quattro nuovi (`E_AMBIENTE_IMMUTABILE`, `E_PROCESSO_NON_SPEGNIBILE`,
  `E_PROCESSO_SENZA_SVEGLIA`, `E_PROCESSO_ACCENSIONE_MOTIVO_OBBLIGATORIO`): `error_policies_generated.py`
  si rigenera, i ripieghi in `error_messages_fallback.py`. Finché non si rigenera, il guardrail dei
  codici del backend è rosso.
* **La domanda della sveglia** per le sveglie systemd e per «Esegui ora» è
  `SELECT maintenance.fn_sveglia_accesa(<processo_codice>)` (P-2: da spento «Esegui ora» è rifiutato).
  Il motivo 2 di `motivi_esegui_ora` oggi legge `abilita` di `sveglie.json`
  (`E_PROCESSO_SVEGLIA_NON_ABILITATA`): passa a leggere questa. Se il codice resta, la sua nota in
  `codici_errore.csv` va aggiornata (la scrive il team DB, su richiesta).
* **Il verbo della scelta a mano** è `dbops.fn_imposta_accensione_processo(codice, acceso, motivo)`:
  restituisce lo stato effettivo. Togliere la scelta (`acceso` NULL) non lascia traccia nella
  tabella: il BE la registra nel suo registro delle operazioni.
* **Panorama:** stato nuovo `SPENTO` (non da guardare) e colonna `acceso` in coda: il FE gli dà
  un'etichetta.
* **Smoke:** con `SPENTO` il panorama distingue spento da morto, quindi `smoke_notturno` potrebbe avere
  una tolleranza vera in sviluppo (oggi NULL per la decisione del 2026-10-13). Da decidere col giro BE,
  insieme al consenso `SMOKE_NOTTURNO_CONSENTITO`.
* **Area Accessi (R-4):** i tre tab non cambiano. Nel tab «Operatori» un filtro, attivo di default,
  nasconde gli utenti di prova; togliendolo si vedono col badge «di prova». Il dettaglio e i comandi
  dell'operatore funzionano su di loro come su ogni operatore.

### 6.1 Risposta del BE (sessione BE, 2026-10-16)

| # del §6.0 | Stato | Dove |
| --- | --- | --- |
| 1 codici d'errore | ✅ rigenerati nel working tree (modulo generato e ripieghi dei quattro codici), ⚠️ **non da questa sessione** e **non ancora committati**: li ha scritti la sessione che lavora in parallelo su brief-db-coerenza-listino-della-riga-di-commessa, insieme ai suoi codici. `genera_error_policies --check` pulito. Vanno nello stesso commit del resto, o il guardrail torna rosso | `error_policies_generated.py`, `error_messages_fallback.py` |
| 2 sveglie systemd | ✅ **un comando solo**, `e_dovuto`, invece di un secondo `ExecCondition` accanto: per prima cosa chiede `maintenance.fn_sveglia_accesa` (spento → 1, systemd salta; errore del DB, ambiente non dichiarato compreso → 255, unit fallita), poi il periodo per le calendariali. «Dovuto adesso?» comprende «acceso?», e il recinto delle uscite (il 255 che un'eccezione non deve perdere) resta scritto una volta. L'`ExecCondition` sta ora su **ogni** template, anche dei non spegnibili: è il catalogo a dire chi si spegne | `e_dovuto.py`, `MaintenanceRepository.sveglia_accesa`, `deploy/systemd/*.service` |
| 3 «Esegui ora» | ✅ il motivo 2 legge lo stato effettivo dal DB (`dbops.fn_processo_acceso_dichiarato`, passato al predicato dal chiamante, uguale per capability, rifiuto e ricontrollo dell'handler). `E_PROCESSO_SVEGLIA_NON_ABILITATA` **resta**, col significato «processo spento»: vedi R-BE-3. `acceso` NULL (ambiente non dichiarato) è un motivo a sé, `E_CONFIG_MANCANTE` | `avvio_manuale.py`, `processi_service.py`, `esegui_processo_handler.py` |
| 4 `abilita` ritirato | ✅ da `sveglie.json`, da `Sveglia`, dall'installer (accende tutto) e dai test; `carica_sveglie` lo **rifiuta** se ricompare | `sveglie.py`, `install-timers.sh` |
| 5 drawer | ✅ in testa l'ambiente, lo stato (acceso / spento / non decidibile) e da dove viene (non si spegne mai, scelta a mano con motivo e data, default dell'ambiente); «Spegni» / «Accendi» / «Torna al default» col motivo obbligatorio (`MotivoDialog`), solo se `can_imposta_accensione`. Endpoint `POST amm-software/processi/<codice>/accensione/` (`AdminAPIView`, come «Esegui ora»). Tolta la colonna «Su questa installazione» dalle sveglie | `ProcessoDrawer.vue`, `ProcessiAccensioneView` |
| 6 panorama `SPENTO` | ✅ nessun lavoro: il FE non mostra gli stati del panorama (solo i presidi «da guardare», coi testi dal DB), e `SPENTO` non è da guardare | — |
| 7 smoke | ⏳ **decisione di Tid**: tolleranza in sviluppo, e se `SMOKE_NOTTURNO_CONSENTITO` resta come seconda serratura | — |

Prove: backend `apps.core` + `apps.amm_software` 1860 test verdi; `test_processi_accensione_db` (3) sul DB vero; `test-install-timers.sh` verde; frontend 886 test, lint. ⚠️ Su dbdev le sveglie vanno **reinstallate** (`sudo backend/bin/install-timers.sh`): fino ad allora girano i template vecchi, senza il cancello sui cinque che non l'avevano, e i due di fatturazione e lo smoke restano spenti dall'installer vecchio.
⚠️ Fatto da sapere, non un motivo: l'`ExecCondition` su ogni sveglia fa partire un processo Python in più a ogni sveglia (il drenatore dei lavori ogni minuto).

**Richieste al team DB:**

* **R-BE-1 — «chi» nella scelta a mano è il ruolo, non la persona.** `dbops.processi_accensione` ha
  `user_insert`/`user_update` a `CURRENT_USER` e il verbo scrive `user_update = CURRENT_USER`: dal
  backend è sempre `zeroerp_app`. Il drawer deve dire chi ha spento (§6.0 punto 5). Le tabelle
  coperte dall'audit usano `app.jwt_user` (`script.trgfn_audit_data_user_generic`), che il backend
  imposta a ogni richiesta. Il backend mostra già `user_update`: corretto il DB, non cambia niente
  di qua.
* **R-BE-2 — il «registro delle operazioni del backend» non esiste.** §6 e la pagina manual di
  `fn_imposta_accensione_processo` dicono che la traccia di «torna al default» (che cancella la
  riga) la tiene quel registro: nel backend non c'è nessun registro dei gesti amministrativi. Oggi
  il gesto si scrive nel log applicativo (chi, processo, gesto, motivo): è una traccia, non una
  storia interrogabile. La storia delle scelte (che il §5-bis.2 rimanda a «un cantiere a parte») è
  la soluzione sul modello: da decidere con Tid.
* **R-BE-3 — la nota di `E_PROCESSO_SVEGLIA_NON_ABILITATA` in `codici_errore.csv`.** Il codice resta
  (stessa classe `NON_DISPONIBILE`, stesso gesto rifiutato); la nota va riscritta: non più
  «`abilita = false` in `sveglie.json`», ma «il processo è spento su questa installazione
  (`dbops.fn_processo_acceso_dichiarato`)». Il ripiego nel backend è già aggiornato.

### 6.2 L'incidente del 2026-10-16 23:45, e le due reti aggiunte (sessione BE, 2026-10-17)

**Fatto.** Il presidio `vw_processi_programmazione_da_guardare` ha detto `TIMER_FERMO` su
`draina_coda_lavori` e `send_pending_emails`. Le due corse delle 23:45:08 erano «in avvio» da oltre
un'ora: TCP aperto verso dbdev, nessuna sessione nel DB, nessuna CPU. Verso le 23:45 la rete fra il
backend e dbdev (Tailscale) si era interrotta (il listener dei permessi ha riaperto la sessione alle
23:46; alle 01:04 dbdev era di nuovo irraggiungibile per qualche minuto: porta 5432 e `tailscale
ping` muti). Il cancello di questo brief non c'entrava: su dbdev giravano ancora i template vecchi.
Sbloccate terminando i due processi (ok di Tid), le sveglie sono ripartite da sole.

**Il difetto, che c'era gia'.** La connessione al DB del backend non aveva tetti di rete
(`connect_timeout`, `tcp_user_timeout`, keepalive) e le unit `oneshot` non avevano
`TimeoutStartSec` (lo smoke a parte): un'interruzione di rete durante l'apertura teneva il processo
in attesa per sempre, e il timer non ripartiva. Il cancello `e_dovuto` su ogni sveglia raddoppia le
connessioni aperte, e quindi le occasioni.

**Le due reti** (BE, non tamponi: il guasto di rete resta possibile, cambia che diventa un errore):

1. `settings.DATABASES["default"]["OPTIONS"]`: `connect_timeout` 10 s, `tcp_user_timeout` 30 s,
   keepalive TCP (30 s di riposo, sonda ogni 10 s, 3 tentativi). Una connessione morta diventa un
   errore in secondi. Vale per sveglie, gunicorn e comandi (gunicorn al prossimo riavvio).
2. `TimeoutStartSec` su ogni sveglia `oneshot`, sotto la tolleranza del processo e sotto l'ora della
   corsa «presa e mai chiusa»; il drenatore sopra il tetto di «Esegui ora» che aspetta. Presidio
   `test_sveglie` 22.

✅ **Regola del 2 (ok Tid, 2026-10-17).** Gli stessi tetti di rete li aveva gia' il listener dei
permessi, in due costanti sue: ora la sede unica e' `settings.DB_TETTI_DI_RETE`, letta da
`DATABASES` e dal listener (`notify_listener._get_conninfo`); le costanti del listener sono ritirate
nello stesso giro.
⚠️ Su dbdev le sveglie vanno reinstallate (`sudo backend/bin/install-timers.sh`) perche' i tetti
entrino negli unit.

### 6.3 Punto 7 — lo smoke notturno: decisioni di Tid (2026-10-17)

* ✅ **Una tolleranza vera in sviluppo.** Il 2026-10-13 la tolleranza dello smoke era stata lasciata
  NULL perche' il panorama non distingueva spento da morto: in produzione, dove lo smoke non gira,
  avrebbe suonato ogni giorno. Con lo stato `SPENTO` quel motivo cade: in produzione lo smoke e'
  spento (default a catalogo), non morto. Senza tolleranza, invece, un giro notturno che smette di
  partire su sviluppo non lo vede nessuno.
* ✅ **`SMOKE_NOTTURNO_CONSENTITO` resta** come seconda serratura: lo smoke e' spegnibile, quindi in
  produzione si puo' accendere a mano dal drawer; la riga che manca in `.env.systemd` lo ferma
  comunque. Due serrature indipendenti su un comando che scrive dati di prova.

**R-BE-4 — al team DB:** in `80_data/sql/dbops/processi.csv`, riga `smoke_notturno`,
`tolleranza_minuti` da NULL a **1560** (26 ore). Perche' 1560: la sveglia e' calendariale (ogni
giorno dalle 02:30 aziendali, sveglia oraria), quindi fra due corse passano al massimo un giorno
piu' il passo della sveglia, 25 ore (`test_contratto_liveness_vs_deploy` test 1, che con la
tolleranza valorizzata lo controlla anche sullo smoke); un'ora di margine sopra. Il tetto della
corsa (`TimeoutStartSec=55min`) sta gia' sotto.
⚠️ La stessa riga del CSV la tocca anche `brief-db-presidio-job-run-a-chi-tocca` (colonna
`causa_fallimento`, lavoro in corso nel working tree il 2026-10-17): coordinarsi per non
sovrascriversi.
Dopo il CSV, lato BE: la nota della voce in `backend/deploy/sveglie.json` («Tolleranza NULL a
catalogo … nessuno se ne accorge») va riscritta. Nessun codice cambia.

