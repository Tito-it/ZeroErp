# Brief DB — Quali processi sono accesi: per ambiente, a mano, e quelli che non si spengono

## ⏭️ Chi riparte — aggiornato al 2026-10-17

**Riparte: il team DB, col lotto 4 della 2b-1 (il fornitore, §5-ter.2). Lotti 1-3 applicati su dbdev,
pgTAP verdi (2026-10-17).**

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | Tid | ✅ decisioni A-1…A-5, P-1…P-3, R-1…R-4 (2026-10-15/16) | §4, §4-bis, §4-ter | — |
| 2 | team DB | ✅ giro 1 scritto e provato sullo scratch (2026-10-16): `20261016-15` … `-32` | §5-bis | — |
| 3 | Tid | ✅ apply del giro 1, fase `post` su dbdev (`SVILUPPO`, 2026-10-16 14:20), pgTAP verdi | §5-bis.4 | — |
| 4 | sessione BE/FE | ✅ punti 1-6 del §6.0, pushati (`f811719d1`, 2026-10-17); codici d'errore nel commit `843166c88` | §6.1 | — |
| 4-ter | Tid | ✅ sveglie reinstallate su dbdev (`sudo backend/bin/install-timers.sh`, 2026-10-17) | §6.1 | — |
| 5 | sessione BE | ✅ che cosa crea il provisioning di sviluppo: l'elenco è in [brief-be-utenti-di-sviluppo §7](brief-be-utenti-di-sviluppo.md) (2026-10-16), decisioni di Tid del §7.4 prese (emittenti nuovi dal verbo, niente `dev.shop` per ora, portale senza contratto) | §5-ter | — |
| 6 | Tid | ✅ decisioni S-1 (storia delle scelte, R-BE-2) e S-2 (smoke, §6.0 punto 7): proposte del team DB accolte (2026-10-17) | §6.2 | — |
| 7 | Tid | ✅ il via allo sviluppo del giro DB 2 (2026-10-17) | — | — |
| 8 | team DB | ✅ giro 2a scritto e provato sullo scratch: R-BE-1, R-BE-3, S-1 (`20261017-02` … `-04`) | §6.3 | — |
| 8-ter | Tid | ✅ apply del giro 2a su dbdev, automazioni, pgTAP verdi (2026-10-17) | §6.3 | — |
| 9-bis | Tid | ✅ strada (b), prima i building block (2026-10-17); resta **il via** alla 2b-1 | §5-ter.1 | — |
| 9 | team DB | 🔨 2b-1: i sette BB nel DB e i builder pgTAP che diventano involucri. ✅ lotto 1 (emittente, più i due BB della scrittura da jsonb) scritto e provato: `20261017-05` … `-10`. ✅ lotti 2 (indirizzi del ruolo, `-11`, `-12`) e 3 (contatto, `-13` … `-17`) scritti, provati e applicati. Prossimo: lotto 4, il fornitore | §5-ter.2 | — |
| 9-quinquies | Tid | ✅ apply del lotto 1, pgTAP verdi (2026-10-17) | §5-ter.2 | — |
| 9-sexies | Tid | ✅ apply dei lotti 2 e 3 (`-11` … `-17`), pgTAP verdi (2026-10-17) | §5-ter.2 | — |
| 9-ter | sessione BE | 2b-2: il backend passa ai BB, le sue copie si ritirano | §5-ter.1 | 9 |
| 9-quater | team DB | 2b-3: etichette, verbo di sviluppo, presidio (R-4) | §5-ter.1 | 9 |
| 10 | sessione BE | con S-2: il valore della tolleranza di `smoke_notturno` in sviluppo; il ritiro di `SMOKE_NOTTURNO_CONSENTITO` dal command e dalla unit | §6.2 | — |
| 11 | chi chiude | archiviazione, riga di PROJECT_CONTEXT | — | 8-ter, 9, 10 |

Decisioni aperte di Tid: nessuna. Da committare: i lotti 1-3 della 2b-1 (`20261017-05` … `-17`, i
codici 1351-1354 nei due CSV, quattro pgTAP, cinque pagine manual), il giro 2a (tre changeSet,
quattro CSV, un pgTAP, due pagine manual) e questo brief. ⚠️ `codici_errore.csv`,
`messaggi_errore.csv` e `processi.csv` li tocca anche la sessione del brief del presidio dei job.

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

### 5-ter.1 Disegno del giro 2b (team DB, 2026-10-17) — ⏳ una decisione di Tid prima del codice

> L'elenco è arrivato ([brief-be-utenti-di-sviluppo §7](brief-be-utenti-di-sviluppo.md)). Ricognizione
> dei building block fatta il 2026-10-17 sulla doc auto-gen e sul backend.

**Il nodo: sette pezzi su dieci non hanno un verbo DB.** Il verbo deve creare questi pezzi:

| Pezzo | Verbo DB di produzione | Chi lo scrive oggi |
| --- | --- | --- |
| credenziale + persona + veste OPERATORE (anche SUPER_ADMIN) | ✅ `anagrafiche.fn_crea_operatore_v2` (crea la veste spenta: l'accensione è un `UPDATE`, come il builder) | — |
| soggetto PF / PG | ✅ `fn_crea_soggetto_pf`, `fn_crea_soggetto_pg` | — |
| emittente (ruolo EF + `emittenti_fiscali`; i registri nascono da sé) | ❌ | builder `fn_pgtap_crea_emittente` (SQL diretto); la UI |
| magazzino predefinito dell'emittente | ❌ | backend; builder `fn_pgtap_crea_magazzino` (vuole un contesto operatore) |
| cliente + BA (`anagrafiche.clienti`, istanza utility, billing account) | ❌ | backend; builder `fn_pgtap_crea_cliente` |
| fornitore | ❌ | backend; nei pgTAP SQL diretto (nessun builder) |
| veste portale (CLIENTE_PORTALE, FORNITORE_PORTALE) | ❌ | backend, `portale_repository.create_identita_portale` (SQL diretto) |
| profilo AD_HOC + aree + binding all'identità | ❌ (solo dentro `fn_crea_utente_tecnico`) | backend, `amm_software_repository.put_profilo_*` |
| `user_override_oggetti` (BLOCCATO su `vendite.contratto`) | ❌ | backend, `put_override_oggetti` |
| emittente attivo (`config.user_emittente_attivo`) | ❌ | backend, `EmittenteAttivoRepository.set_preferenza` |
| whitelist emittente | ✅ `script.fn_change_user_emittenti_scope` | — |

Un verbo che scrive quei sette pezzi con `INSERT` diretti diventa la terza copia di ciascuno, dopo il
backend e i builder pgTAP. Le tre copie prima o poi divergono: un guard nuovo sul cliente lo vede
il backend, e il verbo di sviluppo resta indietro senza che nessun test se ne accorga. Le strade:

* **(a) Il verbo scrive tutto da sé.** È il giro più corto, ma sono sette copie nuove; si dichiarano
  come debito.
* **(b) Prima i building block.** Un verbo DB per ognuno dei sette pezzi; i builder pgTAP e il
  verbo di sviluppo li chiamano; le copie del backend si ritirano nello stesso giro. È il cantiere
  giusto sul modello, ma è grande e tocca il BE in cinque punti.
* **(c) A metà, proposta del team DB.** Il giro 2b estrae nel DB **solo** i building block che hanno
  già una copia DB, cioè la logica dei builder pgTAP: emittente, cliente+BA, fornitore e veste
  portale. I builder diventano involucri sottili sopra quei BB, e il verbo di sviluppo li chiama.
  Per profilo AD_HOC, override ed emittente attivo, che oggi hanno una sola sede (il backend), il
  verbo scrive le righe e il debito si dichiara (`Dnn` in un brief nuovo): il ritiro delle copie
  del backend su tutti e sette i pezzi è un cantiere a parte.

✅ **Deciso (Tid, 2026-10-17): strada (b), prima i building block.** Il giro 2b si divide in tre parti,
in quest'ordine. Il verbo di sviluppo nasce **solo** sopra i BB; nessun suo pezzo scrive tabelle di
dominio con `INSERT` diretti.

| Parte | Chi | Che cosa |
| --- | --- | --- |
| **2b-1** | team DB | i sette BB nel DB (tabella sotto), ognuno col suo pgTAP; i builder pgTAP che ne hanno una copia (`fn_pgtap_crea_emittente`, `fn_pgtap_crea_cliente`/`_cliente_ba`, `fn_pgtap_crea_magazzino`, e gli `INSERT` diretti di fornitore e veste portale nei pgTAP che li ripetono) diventano involucri sopra il BB **nello stesso giro**. Registrati nella doc del catalogo DB |
| **2b-2** | sessione BE | il backend chiama i BB al posto delle sue copie, che si ritirano nello stesso cantiere (regola del 2): cinque punti, elencati sotto. Senza questa parte la (b) diventa la (a) con un BB in più |
| **2b-3** | team DB | etichette, verbo di sviluppo, presidio (il disegno qui sotto) |

**I sette BB** (nomi e forma da confermare scrivendo, sul corpo vivo dei builder e del backend):

| BB | Sostituisce | Copie da ritirare |
| --- | --- | --- |
| `anagrafiche.fn_crea_emittente_fiscale` (ruolo EF + `emittenti_fiscali`, sigla, valuta) | `fn_pgtap_crea_emittente` (SQL diretto) | builder; la creazione dalla UI, se il BE scrive SQL suo |
| `magazzino.fn_crea_magazzino` (con `predefinito`, emittente esplicito, senza contesto operatore) | `fn_pgtap_crea_magazzino` | builder; il backend del magazzino |
| `anagrafiche.fn_crea_cliente` (ruolo CL, `clienti`, istanza utility, billing account, legame all'emittente) | `fn_pgtap_crea_cliente`, `fn_pgtap_crea_cliente_ba` | due builder; il backend dei clienti |
| `anagrafiche.fn_crea_fornitore` (ruolo FO, `fornitori`) | `INSERT` diretti nei pgTAP | i pgTAP che lo ripetono; il backend dei fornitori |
| `anagrafiche.fn_crea_veste_portale` (identità CLIENTE_PORTALE / FORNITORE_PORTALE, spenta o accesa) | — | `portale_repository.create_identita_portale` |
| `config.fn_imposta_profilo_ad_hoc` (profilo, aree, binding all'identità) | dentro `fn_crea_utente_tecnico` | `amm_software_repository.put_profilo_*`, `_set_super_admin_binding`; il ramo AD_HOC di `fn_crea_utente_tecnico` |
| `config.fn_imposta_override_oggetti`, `config.fn_imposta_emittente_attivo` | — | `put_override_oggetti`, `EmittenteAttivoRepository.set_preferenza` |

⚠️ Da sapere prima di cominciare:

* il BE va **censito** punto per punto all'inizio della 2b-1: l'elenco qui sopra viene dalla
  ricognizione del 2026-10-17, non da un censimento completo dei chiamanti;
* i BB nascono **INVOKER**, come le madri: RLS e scope restano quelli di chi chiama. Fanno
  eccezione i pezzi che il verbo di sviluppo deve scrivere da **DEFINER**, e lì l'interazione con
  i guard che leggono il contesto di sessione si prova scrivendo;
* la 2b-2 è lavoro BE in un perimetro che il team DB non tocca: lo scrive il brief BE, su questa
  tabella.

### 5-ter.2 La 2b-1, lotto per lotto (team DB, dal 2026-10-17)

La 2b-1 si consegna **un BB per lotto**, ciascuno applicabile da solo. Ordine: 1 emittente,
2 fornitore, 3 cliente con BA, 4 veste portale, 5 magazzino, 6 profilo AD_HOC, 7 override ed
emittente attivo.

**Due scelte che valgono per tutti i lotti** (team DB):

* **I BB di `anagrafiche` sono madri INVOKER senza guard di permesso**, come `fn_crea_operatore_v2`
  e `fn_crea_soggetto_pg`. Il dominio `anagrafiche` lascia il permesso al backend: è il
  precedente B-5 deciso da Tid (brief-db-dati-fiscali-e-societari-del-soggetto). Con un
  `fn_guard_livello` ogni builder pgTAP morirebbe su `E_PERMESSO_NEGATO`, perché l'operatore
  pgTAP è BLOCCATO su anagrafiche;
* **i campi facoltativi viaggiano come oggetto jsonb**, come nelle madri di casa
  (`fn_update_cliente`, `fn_create_contratto`). Una chiave estranea si **rifiuta** col suo nome
  (`E_CAMPO_NON_AMMESSO`, sul canale `COLUMN`), non si scarta.

#### Lotto 1 — l'emittente (scritto e provato, 2026-10-17)

Il censimento ha trovato una **regola del 2 a monte**. La scrittura «solo le colonne del payload,
convertite da `jsonb_populate_record`» era scritta a mano in tre punti: `config.fn_pannello_scrivi`
(passo 3) e due volte in `vendite.fn_create_contratto` (testata e fornitura). I BB di questa
2b-1 l'avrebbero ripetuta altre quattro volte. Si estrae prima lei.

| changeSet | Che cosa |
| --- | --- |
| `20_code/script/20261017-05` | BB `script.fn_scrivi_riga_da_jsonb(tabella, dati, dove)`: INSERT o UPDATE delle sole chiavi; INVOKER. Le chiavi le sceglie chi chiama |
| `20_code/script/20261017-06` | BB `script.fn_prima_chiave_estranea(dati, ammesse)`: pura, la regola «la chiave estranea si rifiuta» del pannello |
| `20_code/config/20261017-07` | il pannello passa ai due BB (passi 2 e 3); firma, codici e comportamento invariati |
| `20_code/vendite/20261017-08` | la madre del contratto passa al BB per testata e fornitura; il **filtro** delle chiavi (che scarta, non rifiuta) resta suo |
| `20_code/anagrafiche/20261017-09` | **`anagrafiche.fn_crea_emittente_fiscale(soggetto, codice, campi)`**: ruolo EF + riga; un regime indicato è confermato; ritorna `(emittente_fiscale_id, soggetto_ruolo_id)` |
| `20_code/dbops/20261017-10` | il builder `fn_pgtap_crea_emittente` passa dal verbo (firma invariata) |
| `codici_errore.csv` / `messaggi_errore.csv` | `E_SCRIPT_CHIAMATA_NON_VALIDA` (TECNICO, 1351), `E_CAMPO_NON_AMMESSO` (DATO_ERRATO, 1352) |
| pgTAP | `script/test-fn-scrivi-riga-da-jsonb-v1` (22), `anagrafiche/test-fn-crea-emittente-fiscale-v1` (14) |
| manual | le tre funzioni nuove |

**Prova** (scratch `zeroerp_ruoli`, come `zeroerp_owner`, transazione annullata, SQL estratto più
l'upsert completo dei CSV dei codici):

* i due pgTAP nuovi: **22/22** e **14/14**;
* **38 pgTAP identici prima e dopo**. Sono quelli che usano pannello, madre del contratto o builder
  dell'emittente, più 15 file a campione fra i 205 che passano dai builder `mondo_cliente` /
  `emittente_operatore`, più i presidi trasversali (`riferimenti-morti` con `plpgsql_check`,
  `catalogo-messaggi-errore-completo`, `rubinetto-primo-motivo`, `vw-codici-errore-*`,
  `security-definer-search-path`). Tre di loro sono già rossi sullo scratch, identici prima e dopo:
  `test-fn-create-contratto-v1` si ferma al test 6 sul vincolo di esclusione dei contratti (il
  file costruisce un secondo contratto sovrapposto al primo); `test-fatture-atti-v1` e
  `test-registri-per-emittente-v1` muoiono nella fixture. Il ramo riscritto della fornitura del
  contratto (UPDATE della scheda) è esercitato da `test-fornitura-documento-segue-cliente-v1`,
  17/17;
* cancelli statici verdi, compreso il preambolo pgTAP per i due file nuovi.

⚠️ Non provato: la corsa come app.

**Debito dichiarato dal lotto 1:**

* **la partita IVA dell'emittente** la controlla solo il backend, come pre-check (§5b). È una regola
  di dominio senza un guard sulla tabella: ogni altro chiamante del verbo la salta. Il posto
  giusto è un guard su `emittenti_fiscali`, come `trgfn_gestori_guard` per i gestori. È un
  cantiere suo, che va censito sui dati prima di scriverlo;
* `E_RUOLO_RICHIEDE_PIVA`, il codice che quel guard userebbe, ha un messaggio con gli id dentro
  (`Soggetto_id %s , Soggetto_ruolo_id %s`): va riscritto quando si scrive il guard.

**Ricaduta BE (2b-2, per il lotto 1)**:

* `EmittentiFiscaliService.crea_emittente` chiama `anagrafiche.fn_crea_emittente_fiscale(soggetto,
  codice, campi)` con i campi facoltativi. Si ritirano `transaction.atomic`,
  `get_or_create_ruolo_emittente`, `create_emittente`, l'UPDATE di conferma del regime e
  `_CREATE_COLS`. Restano il pre-check della partita IVA e la traduzione dei vincoli per nome
  (`uq_emittenti_fiscali_ruolo`, `uq:codice`, FK del regime): escono identici;
* rigenerare la policy dei codici e i ripieghi per `E_SCRIPT_CHIAMATA_NON_VALIDA` ed
  `E_CAMPO_NON_AMMESSO`. Finché non si fa, il guardrail dei codici del backend è rosso.

✅ **Lotto 1 applicato su dbdev, pgTAP verdi (Tid, 2026-10-17).**

#### Lotto 2 — il fornitore: il censimento allarga il lotto (2026-10-17)

✅ **Deciso (Tid, 2026-10-17): proposta accettata.** La 2b-1 si allarga ai due BB; ordine dei lotti
qui sotto.

`FornitoriService.crea_fornitore`, e allo stesso modo `ClientiService` per il cliente, non è «ruolo
più una riga». È una **saga di quattro passi** dentro `transaction.atomic`: il ruolo, la riga, il
contatto del ruolo (validato EMPTY / PARTIAL / VALID) e gli indirizzi del ruolo. Gli indirizzi
sono obbligatori: per FO servono FATT e SEDELEG, e il guard differito li pretende al commit.
Gli indirizzi del ruolo li scrive `SoggettiService.create_indirizzi_ruolo`, che porta due cose da
sapere:

* **una regola di dominio in Python, l'auto-clone**: i tipi obbligatori della matrice del ruolo che
  il payload non porta si clonano dal primo indirizzo; i tipi già presenti sul ruolo si saltano.
  La usano fornitore, cliente e il ramo ruoli della creazione del soggetto (tre chiamanti);
* **una copia Python di una madre DB che c'è già.** `_resolve_indirizzo_dettaglio` e
  `_create_stradario_da_generale` rifanno a mano `anagrafiche.fn_create_indirizzo` (stradario
  get_or_create più dettaglio, «fix #13», che `geo_service` usa già). È la regola del 2 violata
  oggi, nel backend.

Il gemello DB per il livello soggetto esiste (`anagrafiche.fn_crea_indirizzo_soggetto`), quello per
il ruolo no: il backend fa un `INSERT` diretto. Anche il contatto è un `INSERT` diretto
(`SoggettiRepository.crea_contatto`).

**Che cosa vuol dire per la (b).** Una madre DB del fornitore che non porti indirizzi e contatto non
sostituisce la saga del backend: la lascerebbe in Python con un passo in meno, e il verbo di
sviluppo dovrebbe scrivere gli indirizzi del ruolo con `INSERT` diretti, cioè una copia nuova. Per
avere madri vere servono **due BB in più** prima del fornitore:

| BB | Che cosa | Copie da ritirare |
| --- | --- | --- |
| `anagrafiche.fn_crea_indirizzi_ruolo(soggetto_ruolo, indirizzi jsonb)` | gli indirizzi di un ruolo, con l'auto-clone dei tipi obbligatori e lo skip dei tipi presenti; ogni indirizzo normalizzato passa da `fn_create_indirizzo` | `SoggettiService.create_indirizzi_ruolo` (tre chiamanti), `_resolve_indirizzo_dettaglio`, `_create_stradario_da_generale`, `crea_indirizzo_ruolo`; nel DB l'`INSERT` di `fn_pgtap_crea_soggetto_ruolo` |
| `anagrafiche.fn_crea_contatto(soggetto, ruolo, campi jsonb)` | un contatto di soggetto o di ruolo, con la regola «nominativo + tipo, o niente» | `crea_contatto`, la classificazione EMPTY/PARTIAL/VALID di `contatti_service` (resta il pre-check del messaggio, il rifiuto lo dà il DB); nel DB gli `INSERT` dei builder |

Poi il fornitore (lotto 4) e il cliente (lotto 5) sono madri sottili sopra questi due BB e sopra il
ruolo.

**La proposta del team DB:** allargare la 2b-1 con i due BB, in quest'ordine: **lotto 2**
indirizzi del ruolo, **lotto 3** contatto, **lotto 4** fornitore, **lotto 5** cliente con BA, poi
veste portale, magazzino, profilo, override ed emittente attivo. È la stessa strada (b) applicata
fino in fondo. Il costo è più BE nella 2b-2: tre chiamanti degli indirizzi e due del contatto.

L'alternativa è tenere il perimetro di prima: fornitore e cliente come «ruolo più riga», e la saga
resta in Python. Il verbo di sviluppo scriverebbe allora indirizzi e contatti con `INSERT`
diretti, dichiarati come debito, cioè la strada (a) sui due pezzi.

#### Lotto 2 — gli indirizzi del ruolo (applicato, pgTAP verdi, 2026-10-17)

| changeSet | Che cosa |
| --- | --- |
| `20_code/anagrafiche/20261017-11` | **`anagrafiche.fn_crea_indirizzi_ruolo(soggetto_ruolo, indirizzi jsonb)`**: array di indirizzi (tipo per id o codice interno; forma libera, dettaglio risolto o via da risolvere con `fn_create_indirizzo`); **auto-clone** dei tipi obbligatori dal primo; skip dei tipi presenti; ritorna quanti ne scrive |
| `20_code/dbops/20261017-12` | il builder `fn_pgtap_crea_soggetto_ruolo` passa al BB: gli passa il primo tipo obbligatorio, gli altri li clona il verbo |
| codici | `E_TIPO_INDIRIZZO_NON_TROVATO` (DATO_ERRATO, 1353), `E_SOGGETTO_RUOLO_NON_TROVATO` (NON_TROVATO, 1354) |
| pgTAP, manual | `anagrafiche/test-fn-crea-indirizzi-ruolo-v1` (18); manual del BB |

Differenze dal backend, dichiarate (sono il modello, non un adattamento):

* **un difetto del backend non si porta nel DB**: `create_indirizzi_ruolo` riusava il primo
  dettaglio risolto per *ogni* indirizzo successivo senza dettaglio, non solo per i cloni. Due
  indirizzi nuovi su vie diverse finivano sullo stesso dettaglio. Qui ognuno si risolve da sé
  (`fn_create_indirizzo` è idempotente: il clone ritrova lo stesso dettaglio). Lo prova il test 9;
* il tipo del ruolo si legge dal ruolo, non da un parametro (il backend lo riceveva, default `FO`);
* un elemento che non è un oggetto si rifiuta (il backend lo saltava), una chiave estranea pure;
* i campi di una via nuova restano pre-check del backend, come per `fn_create_indirizzo`.

**Prova** (scratch, SQL estratto `-05` … `-12`): il pgTAP nuovo **18/18**; **178 pgTAP identici
prima e dopo**. Sono tutti quelli che toccano il builder del ruolo, `anagrafiche.indirizzi` e i
builder dei clienti, più un campione dei builder `mondo_cliente` / `emittente_operatore` e i presidi
trasversali. Due sono già rossi, con lo stesso errore prima e dopo:
`test-soggetti-ruoli-indirizzi-required` (codice fiscale duplicato nella fixture) e
`test-proiezione-stato-sorgente` (chiave sorgente mancante).

**Ricaduta BE (2b-2):** `SoggettiService.create_indirizzi_ruolo` (fornitore, cliente, ruoli del
soggetto) diventa una chiamata al BB, e si ritirano `_resolve_indirizzo_dettaglio`,
`_create_stradario_da_generale`, `crea_indirizzo_ruolo` e `get_existing_tipo_indirizzo_ids`. Resta il
pre-check dei campi della via nuova. Il payload va filtrato sulle chiavi del BB: una chiave in più
ora è un rifiuto.

#### Lotto 3 — il contatto (applicato, pgTAP verdi, 2026-10-17)

| changeSet | Che cosa |
| --- | --- |
| `20_code/anagrafiche/20261017-13` | **`anagrafiche.fn_crea_contatto(soggetto, ruolo, campi jsonb)`**: contatto di soggetto o di ruolo, nominativo e tipo obbligatori (`E_CONTATTO_INCOMPLETO`, già a catalogo, col campo); scrive con `fn_scrivi_riga_da_jsonb` |
| `-14`, `-15`, `-16`, `-17` | le quattro copie DB passano al BB: `fn_crea_soggetto_pf`, `fn_crea_soggetto_pg`, `script.fn_crea_utente_tecnico`, il builder `fn_pgtap_crea_soggetto_pg` |
| pgTAP, manual | `anagrafiche/test-fn-crea-contatto-v1` (13); manual del BB |

La classificazione «vuoto / parziale / valido» di un contatto **facoltativo** in un form
(`contatti_service`, gemella del composable frontend) resta dov'è: decide *se* chiamare, il DB decide
*come* si scrive.

**Prova** (scratch, SQL estratto `-05` … `-17`): il pgTAP nuovo **13/13**. **106 pgTAP identici prima
e dopo**: tutti quelli che toccano le quattro funzioni riscritte, `anagrafiche.contatti`,
`fn_crea_operatore_v2` e il builder dell'operatore, più i presidi trasversali. Il 107° è
`test-fn-crea-indirizzi-ruolo-v1` del lotto 2, che prima non poteva girare. Già rossi sullo
scratch, con lo stesso errore prima e dopo: `test-identita-tecnica` e `test-fn-crea-utente-tecnico`
(«il soggetto non ha contatti validi»), `test-identita-digitali-guard-coerenza`,
`test-soggetti-indirizzi-required`, `test-soggetti-ruoli-indirizzi-required` (fixture). Cancelli
statici verdi.

**Ricaduta BE (2b-2):** `SoggettiRepository.crea_contatto` diventa una chiamata al BB.

**Il resto del disegno (team DB, nessuna decisione aperta), parte 2b-3:**

* **Due etichette, due tabelle satellite in `anagrafiche`**:
  * `credenziali_di_prova`: una riga per `auth_user_id`, con la chiave di prova (lo username alla
    nascita) `UNIQUE`; un utente rinominato resta di prova;
  * `soggetti_di_prova`: una riga per `soggetto_id`, con la chiave (`DEVA`, `DEV-CLIENTE-1`…)
    `UNIQUE`.
  * Le chiavi servono anche all'idempotenza: una seconda corsa ritrova le radici dall'etichetta,
    non dal nome. Niente FK verso `django.auth_user`, come `processi_identita`: in CI lo schema
    `django` nasce dopo Liquibase.
* **«Solo dal verbo»**: le due tabelle sono in sola lettura per l'app (tre sedi:
  `v_tabelle_sola_lettura_app`, fase `post` del provisioning, `90_end` forward, col pgTAP di
  postura), come `dbops.installazione`. Il verbo è **SECURITY DEFINER**, perché è l'unico che le
  scrive. Guard sulle tabelle: rifiutano `INSERT` in `PRODUZIONE` (decisione pura sul valore,
  provata con tutti e due i valori), `UPDATE` e `DELETE` sempre ("non si toglie").
* **Il verbo**: `anagrafiche.fn_provisiona_dati_di_sviluppo(p_password_hash jsonb)` (username →
  hash Django; una chiave assente o NULL = password invariata). Per prima cosa
  `fn_ambiente_installazione()`, poi un rifiuto se l'ambiente non è `SVILUPPO` (codice nuovo).
  Crea o riallinea l'elenco del §7, e un omonimo senza etichetta è un errore (codice nuovo).
  Restituisce una riga per radice (tipo, chiave, id, `creata`/`riallineata`, secondo fattore
  sì/no). L'elenco è scritto nel corpo del verbo, perché è il contratto del software, non un dato
  di macchina.
* **I profili `DEV_LETTURA` / `DEV_OPERATIVO`** non sono radici (risposta al brief BE §7.3). Sono
  configurazione legata alle sole identità etichettate da un binding AD_HOC per identità; si
  ritrovano da lì.
* **Email**: `<username>@sviluppo.invalid` (dominio riservato, RFC 2606): nessuna email esce
  davvero.
* **Il presidio** `dbops.vw_radici_di_prova_in_produzione`: le righe dei due registri quando
  l'ambiente dichiarato è `PRODUZIONE`. Legge solo le tabelle di `anagrafiche`, quindi in CI non è
  rotta.
* **La lista Operatori** è SQL in linea nel backend (`list_operatori`), non una vista DB. Il BE
  fa `LEFT JOIN anagrafiche.credenziali_di_prova`, oppure chiama una funzione
  `script.fn_credenziale_di_prova(auth_user_id)`: la sceglie il BE (T-4).

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
| 7 ✅ | **BE-4, 2026-10-17: tolleranza di `smoke_notturno` = 1560 minuti** (26 ore: sveglia ogni ora, lavoro una volta al giorno, quindi al massimo 25 ore fra due corse, più un'ora di margine). Scritta dal team DB in `processi.csv` (riga 47, con la descrizione aggiornata); si applica col mirror. Provato il 2026-10-17: su dbdev il panorama dice `OK`, sullo scratch `MAI_PARTITO`/`TIMER_NON_INSTALLATO` come ogni comando con contratto dove non ci sono timer | `test_contratto_liveness_vs_deploy` ora controlla anche lo smoke |

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

> ✅ Aggiornamento del 2026-10-17 (team DB): il push del BE è `f811719d1`; il ⚠️ del punto 1 è
> chiuso, i quattro codici sono nel modulo generato e nei ripieghi dal commit `843166c88`.

### 6.2 Risposta del team DB alle richieste del BE (2026-10-17)

* ✅ **R-BE-1 — accolta, ed è un difetto del giro 1.** Verificato sul corpo vivo (doc auto-gen):
  `fn_imposta_accensione_processo` scrive `user_update = CURRENT_USER` e la tabella ha
  `user_insert`/`user_update` a `DEFAULT CURRENT_USER`, quindi dal backend è sempre `zeroerp_app`.
  La regola «chi è l'utente» esiste già, una volta sola: `script.trgfn_audit_data_user_generic`
  (`app.jwt_user`, ripiego su `CURRENT_USER`). Non si ricopia nel verbo (regola del 2): la tabella
  prende quel trigger e il verbo smette di scrivere `data_update`/`user_update`. Come lo prende
  dipende da S-1.
* ✅ **R-BE-3 — accolta**: la nota di `E_PROCESSO_SVEGLIA_NON_ABILITATA` in `codici_errore.csv` si
  riscrive nel giro 2 (motivo 2 = processo spento su questa installazione, letto da
  `dbops.fn_processo_acceso_dichiarato`; il rimedio non è più una release ma un click nel drawer, o
  il default del catalogo). Va rivista anche la frase sul gemello
  `E_PROCESSO_SVEGLIA_NON_AVVIABILE_A_MANO`, che oppone i due rimedi «release contro decisione di
  progetto».
* **R-BE-2 — da decidere (S-1).** Il BE ha ragione: il registro a cui il giro 1 rimandava non
  esiste, e «torna al default» cancella la riga, cioè cancella chi e perché. È un buco del modello,
  non del BE: chiunque guardi il drawer dopo un «torna al default» non sa più che cosa è successo.

**S-1 — la storia delle scelte a mano.** ✅ **Deciso (Tid, 2026-10-17): proposta accolta.** In due
pezzi:

1. **«Torna al default» non cancella la riga**: la riscrive con `acceso = NULL` e il motivo. La
   riga dice sempre l'ultimo gesto (chi, quando, perché); `acceso` NULL = «segue il default
   dell'ambiente». Assenza della riga = nessuno l'ha mai toccata. Il guard ammette NULL anche sui non
   spegnibili (tornare al default non spegne niente); `fn_processo_acceso_dichiarato` legge NULL
   come assenza.
2. **La storia la tiene la macchina che c'è già**: `dbops.processi_accensione` entra in
   `automation_scope.csv` (audit con `app.jwt_user` e `tx_id`, che chiude anche R-BE-1 senza un
   trigger scritto a mano) e in `storico_set_storicizza.csv` (gemella `storico.processi_accensione`,
   una versione per ogni gesto). Più la riga di `storico_scope_policy.csv` (modo `NESSUNO`: la tabella
   non ha RLS né asse emittente).

   Da verificare scrivendo, non a priori: che le automazioni di `ci_apply` sulla tabella non
   urtino il guard della scelta a mano (ordine dei BEFORE ROW) e che il verbo, INVOKER, regga sotto
   la gemella con i grant del loop.

Alternativa scartata: una tabella di storia scritta a mano da un trigger AFTER. Sarebbe una seconda
storicizzazione accanto a quella generica, cioè una copia della stessa regola.

Ricaduta BE con S-1: nessuna sul verbo (stessa firma, stesso ritorno); il drawer, se vuole, legge
lo storico. Il log applicativo del gesto diventa ridondante.

**S-2 — lo smoke (§6.0 punto 7).** ✅ **Deciso (Tid, 2026-10-17): proposta accolta**, il consenso
`SMOKE_NOTTURNO_CONSENTITO` si ritira; il valore della tolleranza lo dà il BE e lo scrive il team DB
nel catalogo. Ora che `SPENTO` non è morto: (a) una tolleranza
vera per `smoke_notturno` in sviluppo, che il team DB scrive nel catalogo sul valore che dà il BE;
(b) se `SMOKE_NOTTURNO_CONSENTITO` resta. Proposta del team DB per (b): **si ritira**. Lo smoke
in produzione è già spento di default e non si accende per sbaglio (lo dice il catalogo, e la
scelta a mano ha motivo e autore); quando R-4 arriva, gli smoke girano con `dev.smoke`, che in
`PRODUZIONE` non esiste. Una seconda serratura che dice la stessa cosa del DB è un doppione con il
rischio di divergere.

**Per il giro 2, dal brief BE §7.3:** la domanda «i profili `DEV_LETTURA` / `DEV_OPERATIVO` sono
radici?» la scioglie il team DB scrivendo il giro 2, e la risposta torna nel brief BE.

### 6.3 Giro 2a scritto (team DB, 2026-10-17): R-BE-1, R-BE-3, S-1

Il giro 2 si consegna in due parti: **2a** (questa: la storia della scelta a mano e la nota del
codice) e **2b** (R-4, i dati di sviluppo, §5-ter). La 2a si applica da sola.

| changeSet / file | Che cosa |
| --- | --- |
| `00_schema/dbops/20261017-02` | `dbops.processi_accensione`: `acceso` nullable (NULL = tornato al default), `storicizza`, `tx_id` |
| `20_code/dbops/20261017-03` | il verbo: «torna al default» scrive la riga con `acceso` NULL e il motivo (niente `DELETE`); non scrive più `data_update`/`user_update`. Firma e ritorno invariati |
| `80_data/changelog/20261017-04` | la tabella in `config.storico_set_storicizza` (storico permanente; forma di `20260804-16`) |
| `automation_scope.csv` | `dbops,processi_accensione`: audit (`app.jwt_user`), `tx_id`, storico da `ci_apply` |
| `storico_scope_policy.csv` | riga 125, `NESSUNO` (niente RLS né emittente) |
| `codici_errore.csv`, `messaggi_errore.csv` | R-BE-3: nota, messaggio, causa e rimedio di `E_PROCESSO_SVEGLIA_NON_ABILITATA` = «spento su questa installazione», rimedio un gesto dal drawer; ritoccata la frase del gemello `E_PROCESSO_SVEGLIA_NON_AVVIABILE_A_MANO` |
| `test-processi-accensione-v1` | plan 31 → 35: il 25 passa il motivo, il 25-bis vede la riga con `acceso` NULL; nuovi 31 (nullable), 32 (motivo anche per il default), 33 (chi = `app.jwt_user`), 34 (tre gesti, tre versioni) |
| manual | `processi_accensione`, `fn_imposta_accensione_processo` |

Scelte dichiarate:

* **Il guard non cambia**: `NOT NEW.acceso` con `acceso` NULL è NULL, quindi il ramo «non
  spegnibile» non scatta; il motivo resta obbligatorio per tutti e tre i gesti (il drawer lo
  chiede già). Neanche la regola cambia: `fn_processo_acceso_su_valori` legge già NULL come
  «nessuna scelta».
* **Il verbo smette di scrivere l'audit** invece di copiare la regola di
  `trgfn_audit_data_user_generic` (regola del 2). Il prezzo: fino al primo giro delle automazioni su
  un database, l'UPDATE non tocca `data_update`/`user_update`.
* **Il registro dello storico per SQL**, non per CSV: `storico_set_storicizza.csv` non ha un mirror
  (il CSV esiste ma nessun changeSet lo carica). Precedente: `20260804-16`.

**La prova** (scratch `zeroerp_ruoli`, come `zeroerp_owner`, transazione annullata): SQL estratto
dei tre changeSet + upsert **completo** dei quattro CSV (1090 codici, 1086 messaggi, 123 righe della
mappa: nessuna rifiutata) + le sette automazioni di `ci_apply` ristrette a `dbops`, nell'ordine di
`20250627-31` (nascono `…_audit_data_user_upd`, `…_gen_tx_id_ins_upd`, `…_z90_storico_upd_dlt` e
`storico.processi_accensione`):

* `test-processi-accensione-v1` **35/35**; senza automazioni (lo stato di dbdev subito dopo il
  migrate) rossi puliti **solo** il 33 e il 34, il file arriva in fondo;
* identici prima e dopo, tutti verdi: i dodici pgTAP che leggono gli oggetti toccati (processi,
  registro, coda automatica, convergenza, panorama, guardiano, installazione, cleanup, storico
  colonna FK, scope congelato, potatura dello storico, legacy risorse umane, documenti schema
  base) e i presidi trasversali (`storico-scope-policy`, `riferimenti-morti`, `vw-codici-errore-*`,
  `security-definer-search-path`, `catalogo-presidi`, `stati-check-scrittori`,
  `catalogo-messaggi-errore-completo`, `rubinetto-primo-motivo`);
* `test-storico-scope-policy-v1` senza automazioni: rossi il 5 e il 33 (riga della mappa senza
  trigger), che si chiudono col giro delle automazioni;
* cancelli statici (runOnChange, letterali, preCondition, DDL su trigger generati, GRANT batch,
  timestamp, v1): verdi.

⚠️ Non provato: la corsa **come app** (la prova gira da owner; l'app ha i grant sulla gemella dal
loop dei grant e da `fn_grant_storico_shadows`, in CI).

**Per Tid, dopo l'apply su dbdev**: le automazioni di dbdev sono i job notturni, e lo storico ne
vuole due passate. Per chiudere subito la finestra, nell'ordine della CI:

```sql
CALL maintenance.proc_automations_audit_update_job();
CALL maintenance.proc_automations_storico_provision_job();
CALL maintenance.proc_automations_storico_job();
CALL maintenance.proc_automations_tx_id_job();
CALL maintenance.proc_automations_attivo_job();
CALL maintenance.proc_automations_lock_columns_job();
CALL maintenance.proc_automations_delete_block_job();
```

Poi i pgTAP: `dbops/test-processi-accensione-v1` e `dbops/test-storico-scope-policy-v1`.

**Ricaduta BE** (nessuna obbligatoria):

* il lettore del drawer (`ProcessiRepository.accensione_processo`) tratta già `acceso` NULL come
  «nessuna scelta» e mostra il default: invariato. Se vuole, può dire «rimesso al default da X il …»
  leggendo la riga, e mostrare la storia da `storico.processi_accensione`;
* la riga di log applicativo del gesto (`processi_service.imposta_accensione`) è ora ridondante;
* il ripiego di `E_PROCESSO_SVEGLIA_NON_ABILITATA` in `error_messages_fallback.py` dice già
  «spento»: il messaggio del DB ora porta il nome del processo (`%s`) e dice lo stesso.
