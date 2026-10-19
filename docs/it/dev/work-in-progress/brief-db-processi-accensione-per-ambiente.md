# Brief DB — Quali processi sono accesi: per ambiente, a mano, e quelli che non si spengono

## ⏭️ Chi riparte — aggiornato al 2026-10-19

**Riparte: Tid, col commit della R-BE-15 (riga 9-ter-bis-17, §6.17.2: applicata il 2026-10-19, pgTAP verdi su dbdev); poi il BE con R-DB-17a. Poi chi chiude, con l'archiviazione (riga 11).** ✅ Il lavoro BE di R-DB-14a, R-DB-11a, R-DB-16a, R-DB-16b è fatto e committato (`615281b6c`, 2026-10-19). ✅ Il collaudo finale (riga 9-decies) è fatto. ✅ 2b-1, 2b-3 e la loro ricaduta BE/FE sono fatte (§6.9). ✅ La 2b-2 è
fatta (2026-10-18, §6.10): il backend crea emittente, fornitore, cliente, veste portale, magazzino, profilo,
legame SUPER_ADMIN, override, emittente attivo e accende la veste dalle madri del DB; restano due scritture
che le madri non coprono. ✅ La riga 10 del BE è fatta (§6.8): l'accensione è chiusa.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | Tid | ✅ decisioni A-1…A-5, P-1…P-3, R-1…R-4 (2026-10-15/16) | §4, §4-bis, §4-ter | — |
| 2 | team DB | ✅ giro 1 scritto e provato sullo scratch (2026-10-16): `20261016-15` … `-32` | §5-bis | — |
| 3 | Tid | ✅ apply del giro 1, fase `post` su dbdev (`SVILUPPO`, 2026-10-16 14:20), pgTAP verdi | §5-bis.4 | — |
| 4 | sessione BE/FE | ✅ punti 1-6 del §6.0, pushati (`f811719d1`, 2026-10-17); codici d'errore nel commit `843166c88`. ✅ Dopo l'incidente delle 23:45, i tetti di rete e delle sveglie (2026-10-17, `295737a90`) | §6.1, §6.4 | — |
| 4-bis | team DB | le richieste del BE: ✅ R-BE-1 e R-BE-3 (giro 2a, §6.3), ✅ R-BE-2 sciolta da S-1 (§6.2); ✅ R-BE-4, la tolleranza di `smoke_notturno` = 1560 in `processi.csv`, applicata (§6.0 punto 7) | §6.2, §6.3, §6.5 | — |
| 4-ter | Tid | ✅ sveglie reinstallate su dbdev (`sudo backend/bin/install-timers.sh`, 2026-10-17): le unit installate hanno i tetti `TimeoutStartSec` del §6.4 | §6.1, §6.4 | — |
| 5 | sessione BE | ✅ che cosa crea il provisioning di sviluppo: l'elenco è in [brief-be-utenti-di-sviluppo §7](brief-be-utenti-di-sviluppo.md) (2026-10-16), decisioni di Tid del §7.4 prese (emittenti nuovi dal verbo, niente `dev.shop` per ora, portale senza contratto) | §5-ter | — |
| 6 | Tid | ✅ decisioni S-1 (storia delle scelte, R-BE-2) e S-2 (smoke, §6.0 punto 7): proposte del team DB accolte (2026-10-17) | §6.2 | — |
| 7 | Tid | ✅ il via allo sviluppo del giro DB 2 (2026-10-17) | — | — |
| 8 | team DB | ✅ giro 2a scritto e provato sullo scratch: R-BE-1, R-BE-3, S-1 (`20261017-02` … `-04`) | §6.3 | — |
| 8-ter | Tid | ✅ apply del giro 2a su dbdev, automazioni, pgTAP verdi (2026-10-17) | §6.3 | — |
| 9-bis | Tid | ✅ strada (b), prima i building block (2026-10-17); resta **il via** alla 2b-1 | §5-ter.1 | — |
| 9 | team DB | 🔨 2b-1: i sette BB nel DB e i builder pgTAP che diventano involucri. ✅ lotto 1 (emittente, più i due BB della scrittura da jsonb) scritto e provato: `20261017-05` … `-10`. ✅ lotti 2 (indirizzi del ruolo, `-11`, `-12`) e 3 (contatto, `-13` … `-17`) scritti, provati e applicati. ✅ lotti 4-9 scritti (2026-10-18): fornitore `20261018-30`, BA e cliente `-34` … `-38`, veste dei portali `-39`, magazzino `-40`, `-41`, profilo e legame `-42` … `-45`, override ed emittente attivo `-46`, `-47`. ✅ anche le copie del binding d'identità nei pgTAP (lotto 8) | §5-ter.2 | — |
| 9-septies | Tid | ✅ apply dei lotti 4-9 su dbdev e sullo scratch (2026-10-18 14:26), pgTAP verdi | §5-ter.2 | — |
| 9-quinquies | Tid | ✅ apply del lotto 1, pgTAP verdi (2026-10-17) | §5-ter.2 | — |
| 9-sexies | Tid | ✅ apply dei lotti 2 e 3 (`-11` … `-17`), pgTAP verdi (2026-10-17) | §5-ter.2 | — |
| 9-ter | sessione BE | ✅ (2026-10-18) 2b-2: il backend passa ai BB, le sue copie si ritirano | §6.10 | — |
| 9-ter-bis-11 | team DB, poi Tid, poi BE | ✅ R-BE-11: `20261019-16` (lettore `config.fn_profilo_super_admin_id`) e `-17` (la madre lo usa), applicati su dbdev (2026-10-18 23:59), pgTAP verdi, committati. ✅ R-DB-11a (2026-10-19): il BE ritira la sua query | §6.15 | — |
| 9-ter-bis | team DB | ✅ (2026-10-19) R-BE-6, R-BE-7, R-BE-12: decisioni D-16a … D-16c di Tid col via allo sviluppo; `20261019-33` … `-39` scritti e provati sullo scratch, due pgTAP nuovi. R-BE-11 ha la sua riga (9-ter-bis-11) | §6.10, §6.16 | — |
| 9-ter-bis-16 | Tid | ✅ apply di `20261019-33` … `-39` su dbdev (2026-10-19 00:26), pgTAP verdi compreso `test-fn-provisiona-dati-di-sviluppo-v1` corretto; committati | §6.16 | — |
| 9-ter-bis-16-be | sessione BE | ✅ (2026-10-19) R-DB-16a (i legami di profilo dalle madri) e R-DB-16b (gli indirizzi dalle madri, ritirati la INSERT e la procedura); committato `615281b6c` | §6.16 | — |
| 9-ter-bis-17 | team DB, poi Tid, poi BE | ✅ **R-BE-15** (D-17a … D-17d, via di Tid): `20261019-80` … `-86`, tre codici, il lock; applicati da Tid su dbdev e sullo scratch (2026-10-19 11:10), pgTAP verdi su dbdev. Restano: il commit (Tid), **R-DB-17a** al BE (i tre codici) | §6.17.2 | — |
| 9-ter-ter | team DB | ✅ (2026-10-18, D-1 … D-4 di Tid, `20261018-80` … `-99`, `20261019-01` … `-04`, applicati) l'indirizzo libero: R-BE-8 (lo stato proposto, `script.fn_stato_proposto_id`), R-BE-9 (il guard `trgfn_indirizzi_guard_forma_libera` col codice e il campo), R-BE-10 (la forma estera nella madre del soggetto, `fn_crea_indirizzo_soggetto(soggetto, jsonb)`); la regione alleggerita (`-82`: forma estera = località sola) | §6.11, §6.12 | — |
| 9-ter-quater | sessione BE/FE | ✅ (2026-10-18) firma jsonb della madre del soggetto, `postal_code`, tendina degli stati, form in due forme, codici; provato sul DB vero dopo l'apply | §6.12 | — |
| 9-ter-quinquies | Tid | ✅ apply di `20261018-80 … -99` e `20261019-01 … -04` su dbdev, pgTAP verdi (2026-10-18) | §6.12 | — |
| 9-ter-sexies | team DB, poi Tid | ✅ R-BE-13: `fn_stato_proposto_id` non applicava l'override per utente (né per gruppo ed emittente). D-13a e D-13b di Tid; `20261019-05` (BB `fn_get_parameter_di_sessione`) e `-06` scritti e provati, applicati su dbdev (2026-10-18 22:45), pgTAP verdi; resta il commit | §6.12, §6.13 | — |
| 9-ter-septies | team DB, poi Tid | R-BE-14: l'emittente di prova del provisioning non è attrezzato per lavorare. Tre pezzi (§6.12): ✅ **registri** in questo brief; **template di default** in [brief-db-modelli-documento-standard](brief-db-modelli-documento-standard.md), D-1 … D-3 di Tid aperte; ✅ **giacenza** nello smoke (BE). Registri: ✅ (2026-10-18) D-14a … D-14d prese, via allo sviluppo dato; `20261019-07` … `-12`, codice `E_REGISTRO_COPPIA_GIA_COPERTA`, pgTAP nuovo e `test-registri-motore-trasloco` adeguato, scritti e provati sullo scratch | §6.12, §6.14 | — |
| 9-ter-octies | Tid | ✅ apply di `20261019-07` … `-12` e dei due CSV dei codici su dbdev (2026-10-18 23:35), pgTAP verdi, compreso `test-numero-prefisso-registro-v1` corretto; resta il commit | §6.14 | — |
| 9-ter-nonies | sessione BE | ✅ (2026-10-19) R-DB-14a: ripiego e policy del codice `E_REGISTRO_COPPIA_GIA_COPERTA`; committato `615281b6c` | §6.14 | — |
| 9-quater | team DB | ✅ 2b-3 scritta e provata (2026-10-18): etichette, guard, verbo, presidio, `fn_accendi_veste` (`20261018-55` … `-64`) | §5-ter.3 | — |
| 9-octies | Tid | ✅ (2026-10-18, pgTAP verdi) apply della 2b-3 (`20261018-55` … `-64`, i due CSV dei codici, `presidi.csv`, `presidi_testi.csv`, il loop `20260205-41`); pgTAP `dbops/test-etichette-di-prova-v1`, `anagrafiche/test-fn-provisiona-dati-di-sviluppo-v1`, chi usa `fn_pgtap_crea_operatore_umano`, i presidi trasversali | §5-ter.3 | — |
| 9-novies | sessione BE | ✅ (2026-10-18) ricaduta della 2b-3: codici, command `provision_utenti_sviluppo`, lista Operatori (BE e FE), smoke e run-book | §6.9 | — |
| 9-decies | Tid | ✅ collaudo (2026-10-18): command su dbdev, `env.sh` a `dev.smoke`, `smoke` disattivato. Il giro degli smoke ha aperto T-7 e il brief dei modelli di documento standard, fuori da questo brief | brief BE §9 | — |
| 10-bis | Tid | ✅ contraddizione su `SMOKE_NOTTURNO_CONSENTITO` sciolta (2026-10-18): il divieto entra nel modello, poi il consenso si ritira | §6.6 | — |
| 10-ter | team DB | ✅ **R-BE-5** scritto e provato sullo scratch (2026-10-18): `accendibile_in_produzione` nel catalogo, il predicato, la regola e il guard, `E_PROCESSO_NON_ACCENDIBILE_IN_PRODUZIONE` (1355) | §6.7 | — |
| 10-quater | Tid | ✅ apply di R-BE-5 (`20261018-10` … `-14`) su dbdev, pgTAP senza regressioni (2026-10-18) | §6.7.4 | — |
| 10 | sessione BE | ✅ (2026-10-18) codice nuovo e ripiego, capability di «Accendi» dal predicato del guard, consenso ritirato da command, test, unit e `sveglie.json`, nota della tolleranza riscritta | §6.8 | — |
| 10-bis-env | Tid | ✅ tolta la riga `SMOKE_NOTTURNO_CONSENTITO` da `backend/.env.systemd` di backend-dev (2026-10-18) | §6.8 | — |
| 11 | chi chiude | archiviazione, riga di PROJECT_CONTEXT | — | 9-ter-bis-17 (R-DB-17a compresa) |

Decisioni aperte di Tid: nessuna. ✅ D-17a … D-17d prese e sviluppate il 2026-10-19 (R-BE-15, §6.17.2); ⚠️ il lavoro DB è **da committare** su `dev/db-tid`. D-14a … D-14d e la nota di debito sul registro standard prese il 2026-10-18 (§6.14). L'ultimo «trovato, non toccato» è diventato R-BE-15 (§6.17, riga 9-ter-bis-17). ✅ `count_admin_attivi` (§6.15) ritirato il 2026-10-19, ok di Tid. ✅ Il lavoro BE del 2026-10-19 (R-DB-14a, R-DB-11a, R-DB-16a, R-DB-16b) è committato su `dev/backend-tid` (`615281b6c`), da pushare. La 10-bis è presa il 2026-10-18 (§6.6). ✅ La ricaduta BE/FE della 2b-3 (§6.9), la
2b-2 (§6.10) e le richieste R-BE-11, R-BE-12 sono committate su `dev/backend-tid` (`08cc15a61`, 2026-10-18,
mergiato in `Tito-dev` con la PR #1881). ✅ La ricaduta BE/FE delle due forme dell'indirizzo libero (§6.12) è
committata (`bd7946224`, mergiata in `Tito-dev` con la PR #1884). ✅ Committati su `dev/db-tid` (2026-10-19): R-BE-13 lato DB (§6.13), R-BE-14 (§6.14), R-BE-11 (§6.15) e R-BE-6, R-BE-7, R-BE-12 (§6.16). ✅ Il lavoro
DB del cantiere è committato e pushato su `dev/db-tid` (2026-10-18): 2b-1 lotti 1-9, 2b-3, giro 2a, R-BE-5,
le copie del binding nei pgTAP e questo brief. ⚠️ `codici_errore.csv`, `messaggi_errore.csv` e
`processi.csv` li tocca anche la sessione del brief del presidio dei job.

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

#### Lotto 4 — il fornitore (scritto e provato, 2026-10-18)

| changeSet | Che cosa |
| --- | --- |
| `20_code/anagrafiche/20261018-30` | **`anagrafiche.fn_crea_fornitore(soggetto, campi, contatto, indirizzi)`**: ruolo FO (get_or_create), riga di `fornitori` nello stato iniziale `VE`, contatto del ruolo (`fn_crea_contatto`, se c'è) e indirizzi del ruolo (`fn_crea_indirizzi_ruolo`); ritorna `(fornitore_id, soggetto_ruolo_id)` |
| pgTAP | nuovo `anagrafiche/test-fn-crea-fornitore-v1` (16); `script/test-search-regola-unica-visibile-v1`: l'`INSERT` diretto del fornitore passa alla madre (poi un `UPDATE` allo stato `AT`) |
| manual | `fn_crea_fornitore` |

Scelte dichiarate:

* **i campi sono quelli del backend** (`_CREATE_ALLOWED` meno ruolo e stato); una chiave a null vale
  assente (`jsonb_strip_nulls`: è lo `skip_none` del backend), così il codice generato resta attivo;
* **lo stato non è un campo**: un fornitore nasce `VE` («in verifica»), come nel backend; un altro stato
  è un `UPDATE` dopo;
* **contatto `NULL` = nessun contatto**: la classificazione EMPTY/PARTIAL/VALID resta del backend (decide
  *se* chiamare), come al lotto 3;
* nessun codice d'errore nuovo.

**Prova** (scratch, SQL estratto, owner, transazione annullata): il pgTAP nuovo **16/16**;
`test-search-regola-unica-visibile-v1` **17/17** prima e dopo; `riferimenti-morti`,
`catalogo-messaggi-errore-completo`, `security-definer-search-path` verdi.

**Ricaduta BE (2b-2):** `FornitoriService.crea_fornitore` diventa una chiamata a
`anagrafiche.fn_crea_fornitore(soggetto, campi, contatto, indirizzi)`; si ritirano
`transaction.atomic`, `get_or_create_ruolo_fornitore`, `create_fornitore` (e `_CREATE_ALLOWED`), il passo
del contatto e quello degli indirizzi. Restano la traduzione dei vincoli per nome
(`uq_fornitori_soggetto_ruolo_id`, `uq_fornitori_codice`) e la classificazione del contatto inline.

#### Lotto 5 — il cliente con il BA (scritto e provato, 2026-10-18)

Il censimento ha trovato **due BB, non uno**: il builder `fn_pgtap_crea_cliente_ba` (133 pgTAP, più
`fn_pgtap_crea_mondo_cliente`) si ferma al billing account, senza la riga del cliente. Un BA senza
cliente è un mondo legittimo (l'istanza vuole un satellite: BA, dato precontrattuale o cliente), quindi
il BA è un BB a sé e la madre del cliente lo usa.

| changeSet | Che cosa |
| --- | --- |
| `20_code/script/20261018-34` | `script.fn_scrivi_riga_da_jsonb` prende **`p_rileggi_per`** (text[], in coda, default NULL): la INSERT senza `RETURNING` e la riga **riletta a istruzione finita** per quelle colonne. DROP della firma a tre + CREATE: i chiamanti di oggi restano identici |
| `20_code/anagrafiche/20261018-35` | **`anagrafiche.fn_crea_billing_account(ruolo, utility, campi, istanza esistente, istanza nuova, emittente)`**: l'istanza fittizia se non indicata, il BA riletto per `(istanza_utility_id, utility_id)`, il legame all'emittente se chiesto |
| `20_code/anagrafiche/20261018-36` | **`anagrafiche.fn_crea_cliente(soggetto, utility, campi, ba, contatto, indirizzi, ba esistente, istanza esistente, istanza nuova, emittente)`**: ruolo CL, BA (nuovo dal BB o esistente), riga di `clienti` riletta per `billing_account_id`, contatto e indirizzi |
| `20_code/dbops/20261018-37` | il builder `fn_pgtap_crea_cliente_ba` passa al BB del BA (firma, ritorno e codice `PGTAPBAnnnnn` invariati) |
| `20_code/dbops/20261018-38` | il builder `fn_pgtap_crea_cliente` passa alla madre (lo stato e le date restano scelte della fixture) |
| pgTAP | nuovo `anagrafiche/test-fn-crea-cliente-v1` (25, runner owner); `script/test-fn-scrivi-riga-da-jsonb-v1` 22 → 27 (la firma nuova al test 1; la rilettura ai test 23-27, col caso costruito di una policy che non lascia vedere la riga) |
| manual | `fn_crea_billing_account`, `fn_crea_cliente`, `fn_scrivi_riga_da_jsonb` |

Scelte dichiarate:

* **perché la rilettura.** BA e cliente sono in RLS e la policy di lettura passa dal legame BA → emittente,
  che scrive un trigger AFTER (`z90_link_ef`): un `RETURNING` guarda la riga prima che quel legame esista.
  I builder rileggevano a istruzione finita da `20260912-38`; i due BB nuovi sono la seconda copia, quindi
  la forma va nel BB di scrittura. ⚠️ Fatto datato, non un motivo: il 2026-10-18 sullo scratch, con le
  policy di quel giorno (che la sessione plancache sta riscrivendo), il `RETURNING` diretto passa anche con
  un operatore di un'altra azienda sotto `FORCE ROW LEVEL SECURITY`;
* **lo stato di nascita del cliente.** Senza stato nasce `AT` con la data operativa (la regola del backend);
  con uno stato indicato le date sono di chi chiama, e le pretende `trgfn_clienti_guard_stato_date`. I
  builder fanno nascere clienti anche `PR` e `CH`, e il grafo degli stati non ammette `AT → PR`: la madre
  deve accettare lo stato. ⚠️ **Il modello non dice in quali stati un cliente può nascere**: è lo stesso
  buco di D32 ([brief-db-documento-nasce-nello-stato-iniziale](brief-db-documento-nasce-nello-stato-iniziale.md),
  decisione N aperta). La madre non lo allarga né lo chiude: lo rende visibile in un punto solo;
* **il legame all'emittente**: con un operatore in sessione lo scrive `z90`; senza sessione (provisioning,
  owner) lo scrive il BB. Un legame discorde è una chiamata sbagliata: `E_SCRIPT_CHIAMATA_NON_VALIDA`, nessun
  codice nuovo;
* ⚠️ **un limite del modello di oggi, trovato scrivendo**: il guard `z95` dell'istanza («un'istanza ha i BA
  di una sola azienda») è un AFTER INSERT del BA e scatta *prima* che il BB scriva il legame chiesto. Con
  la sessione il legame lo scrive `z90`, che viene prima: nessun problema. Senza sessione, un secondo BA su
  un'istanza esistente con un emittente esplicito diverso dal default muore sul guard. Il builder non lo
  faceva (un BA per istanza) e il provisioning crea istanze nuove: dichiarato nel BB, non corretto;
* **la utility che richiede il PDP**: il backend la controlla come pre-check, ma il rifiuto c'è già nel DB
  (`trgfn_clienti_sync_pdp`, trovato dal pgTAP). La madre non aggiunge niente;
* restano al backend il permesso, il caso amministratore globale (lo dice anche il guard del BA) e le
  validazioni read-only di BA e istanza esistenti (il rifiuto lo danno FK composte e guard).

**Prova** (scratch, SQL estratto `-30` e `-34` … `-38`, owner, transazione annullata):

* i pgTAP nuovi: `test-fn-crea-cliente-v1` **25/25**, `test-fn-scrivi-riga-da-jsonb-v1` **27/27**;
* **370 pgTAP prima e dopo**: tutti quelli che passano dai builder del cliente, da `mondo_cliente`, dal
  pannello, dalla madre del contratto o che leggono BA e clienti, più i presidi trasversali
  (`riferimenti-morti`, `catalogo-messaggi-errore-completo`, `rubinetto-primo-motivo`,
  `security-definer-search-path`). **Nessuna differenza** se non nei due file nuovi. Già rossi sullo
  scratch, identici prima e dopo: una trentina di file di `vendite` che muoiono nella fixture su «l'azienda
  indicata non è quella del cliente» (il codice casuale del documento cambia a ogni corsa, l'errore no);
* sotto `FORCE ROW LEVEL SECURITY` su `billing_account` e `clienti`, con l'operatore pgTAP e con un
  operatore di un'altra azienda in sessione: i due builder riscritti passano.

⚠️ Non provato: la corsa come app (la prova gira da owner; la RLS è provata col `FORCE`).

**Ricaduta BE (2b-2):** `ClientiService._execute_creazione` diventa una chiamata a
`anagrafiche.fn_crea_cliente`: si ritirano `create_istanza_fittizia`, `create_billing_account`,
`create_cliente` (e `_CLIENTE_CREATE_ALLOWED`), i passi del contatto e degli indirizzi. Restano i pre-check
(`_guard_can_create_ba`, `_validate_istanza`, `_validate_billing_account`, la utility col PDP) per il
messaggio, e la traduzione dei vincoli per nome (`uq_billing_instance_utility`, `uq_clienti_billing_account`).

#### Lotto 6 — la veste dei portali (scritto e provato, 2026-10-18)

| changeSet | Che cosa |
| --- | --- |
| `20_code/anagrafiche/20261018-39` | **`anagrafiche.fn_crea_veste_portale(credenziale, ruolo, veste, attivo)`**: la riga di `identita_digitali` di una veste esterna (`CLIENTE_PORTALE`, `FORNITORE_PORTALE`, `SHOP_CUSTOMER`), spenta o accesa; ritorna l'id |
| pgTAP | nuovo `anagrafiche/test-fn-crea-veste-portale-v1` (9); **sedici file** con le fixture riscritte sul BB (sotto) |
| manual | `fn_crea_veste_portale` |

Scelte dichiarate:

* **solo le tre vesti esterne**: la veste `OPERATORE` ha le sue madri (`fn_crea_operatore_v2`,
  `fn_crea_utente_tecnico`), che portano perimetro e risorsa umana; `API_CLIENT` e `DISABILITATO` non nascono
  da un invito. Fuori elenco: `E_SCRIPT_CHIAMATA_NON_VALIDA`;
* **`attivo` obbligatorio, senza default**: l'invito crea la veste spenta, lo shop accesa; il DEFAULT della
  colonna (`true`) è sbagliato per l'invito;
* **le copie nei pgTAP, per significato** (regola del 2): sono copie le fixture che *creano una veste per
  avere una veste*. Ventinove `INSERT` in sedici file passano al BB:
  `test-fn-sync-auth-user-is-active-or`, `test-sync-auth-user-is-active-multi-role`,
  `test-fn-scope-ba-ownership-ruolo-aware`, `test-rls-clienti`, `test-rls-fatture-residuo`,
  `test-fn-get-permessi-ereditati-v1`, `test-fn-get-profili-accesso-applicabili`,
  `test-fn-get-user-profile-guc-aware`, `test-fn-is-super-admin-operatore-only`,
  `test-fn-scope-ba-ownership-via-fattura`, `test-fn-scope-ba-ownership`, `test-fn-scope-cliente-ownership`,
  `test-fn-scope-fornitore-ownership`, `test-fn-veste-utilizzabile-v1`, `test-fn-resolve-dashboard-config`,
  `test-fn-resolve-lista-config`. **Restano a mano**, apposta, le scritture il cui soggetto è la tabella:
  i test dei guard di coerenza, unicità e natura della credenziale (`test-identita-digitali-guard-coerenza`,
  `test-identita-digitali-unique-multi-veste`, i rifiuti di `test-area-accessi-v1`), le vesti `API_CLIENT`
  e `DISABILITATO`, e le copie di righe `OPERATORE` storicizzate (`test-fn-check-operatore-invitabile`,
  `test-fn-get-operatore-detail`). `test-area-accessi-v1` resta tutto: il suo helper crea anche una
  `API_CLIENT`.

**Prova** (scratch, SQL estratto fino al `-39`): il pgTAP nuovo **9/9**; i sedici file, **originale senza il
BB contro riscritto col BB**: identici; i sei file dei guard rimasti a mano e `riferimenti-morti`: identici
prima e dopo. Già rossi sullo scratch, identici: `test-fn-sync-auth-user-is-active-or` (1),
`test-sync-auth-user-is-active-multi-role` (1), `test-identita-digitali-guard-coerenza` (5),
`test-identita-digitali-unique-multi-veste` (1), fixture che pescano dai dati.

**Ricaduta BE (2b-2):** `PortaleRepository.create_identita_portale` diventa una chiamata a
`anagrafiche.fn_crea_veste_portale(auth_user, ruolo, veste, attivo)` (due chiamanti: l'invito e lo shop).

✅ **Lotti 4-9 applicati su dbdev e sullo scratch (Tid, 2026-10-18 14:26-14:27), pgTAP verdi.**

#### Lotto 7 — il magazzino (scritto, provato e applicato, 2026-10-18)

| changeSet | Che cosa |
| --- | --- |
| `20_code/magazzino/20261018-40` | **`magazzino.fn_crea_magazzino(codice, descrizione, indirizzo, campi, emittente)`**: la riga di `magazzini`; campi `usa_ubicazioni`, `predefinito`, `meta`; emittente NULL = quello della sessione (lo mette `trgfn_default_emittente_fiscale('SOLLEVA')`) |
| `20_code/dbops/20261018-41` | il builder `fn_pgtap_crea_magazzino` passa al BB (firma invariata) |
| pgTAP | nuovo `magazzino/test-fn-crea-magazzino-v1` (9); sei `INSERT` delle fixture passano al BB in `test-movimenti-vincoli-v2`, `test-movimenti-attesi-forma-v1`, `test-valore-giacenza-forma-v1`, `rls/test-rls-magazzino-perimetro-v1`. Resta a mano, apposta, `script/test-trgfn-default-emittente-fiscale-v1`, che prova il trigger del default |
| manual | `fn_crea_magazzino` |

⚠️ **Trovato scrivendo, per la 2b-3**: il guard `trgfn_guard_emittente_scope` della tabella, dentro una
SECURITY DEFINER senza un operatore in sessione, **ferma una riga che ha un padrone** (rev 2026-09-18). Il
verbo di sviluppo, che il §5-ter.1 voleva DEFINER, non può quindi scrivere un magazzino (né, per lo stesso
guard, le altre tabelle di dominio con l'emittente) senza agire per conto di un operatore dell'emittente di
prova. È una scelta di forma del verbo: si risolve scrivendo la 2b-3.

**Prova**: il pgTAP nuovo **9/9**; le quattro fixture, originale contro riscritta, identiche; i 28 pgTAP
che usano il builder o la tabella, identici prima e dopo.

**Ricaduta BE (2b-2):** `AnagraficheMagazzinoRepository.create_magazzino` diventa una chiamata al BB.

#### Lotto 8 — il profilo di accesso e il suo legame (scritto e applicato, 2026-10-18)

**Il censimento corregge la tabella del §5-ter.1.** Un profilo AD_HOC oggi non lo scrive nessuno: nel backend
`put_profilo_*` esiste solo per il reparto, e `_set_super_admin_binding` è un binding, non un profilo. Le
due cose che si ripetono davvero sono due BB:

| changeSet | Che cosa |
| --- | --- |
| `20_code/config/20261018-42` | **`config.fn_scrivi_profilo_accesso(tipo, codice, descrizione, aree, azioni, campi)`**: il profilo per codice, creato o aggiornato; aree e azioni sostituite (NULL = invariate). Copia: i passi del profilo di `put_profilo_reparto` (backend); seconda occorrenza: i profili `DEV_*` del verbo |
| `20_code/config/20261018-43` | **`config.fn_lega_profilo_identita(profilo, identità)`**: il binding di un'identità, idempotente sullo stesso profilo; un altro profilo già legato lo rifiuta `uq_profili_accesso_bindings_identita` |
| `20_code/script/20261018-44`, `20_code/anagrafiche/20261018-45` | `fn_crea_utente_tecnico` (passo 6) e `fn_crea_risorsa_umana_v2` (binding SUPER_ADMIN) passano al BB del legame |
| pgTAP | nuovo `config/test-fn-scrivi-profilo-accesso-v1` (15) |
| manual | `fn_scrivi_profilo_accesso`, `fn_lega_profilo_identita` |

⚠️ **Un fatto per la 2b-2**: `_set_super_admin_binding` scrive con `ON CONFLICT DO NOTHING`. Se l'identità ha
già un altro profilo, il SUPER_ADMIN chiesto **non arriva e nessuno lo dice**. Col BB quel caso diventa
l'errore del vincolo: il BE decide che cosa mostrare.

✅ **Le copie del binding nei pgTAP (2026-10-18)**: ventitré `INSERT` di binding d'identità in ventun file
passano a `config.fn_lega_profilo_identita`; originale contro riscritto, identici. Restano a mano,
apposta: i test del guard di coerenza dei binding (`test-profili-accesso-bindings-guard-coerenza`), i
binding di reparto e di veste, e `test-permessi-funzioni-risoluzione`, che scrive con `ON CONFLICT DO
NOTHING` (la semantica di `_set_super_admin_binding`, non quella del BB).

#### Lotto 9 — gli override e l'emittente attivo (scritto e applicato, 2026-10-18)

| changeSet | Che cosa |
| --- | --- |
| `20_code/config/20261018-46` | **`config.fn_imposta_override_oggetti(utente, oggetti)`**: gli override sostituiti dall'elenco (vuoto = nessuno). Copia: `put_override_oggetti` |
| `20_code/config/20261018-47` | **`config.fn_imposta_emittente_attivo(utente, emittente)`**: UPSERT della preferenza; l'UPDATE tocca la riga anche a valore invariato (la storia registra la conferma, come il backend). Copia: `set_preferenza` |
| pgTAP | nuovo `config/test-fn-imposta-override-emittente-attivo-v1` (13) |
| manual | `fn_imposta_override_oggetti`, `fn_imposta_emittente_attivo` |

Scelte e debito dichiarati:

* gli `INSERT` di override nei pgTAP (otto file) **non sono copie**: aggiungono una riga, il BB sostituisce
  tutto. Restano;
* ⚠️ **override, `valido_dal`**: una chiave assente prende il DEFAULT (la data operativa), una chiave a null
  scrive NULL (senza inizio). Il backend oggi passa sempre la chiave: nella 2b-2 deve continuare a farlo
  per tenere lo stesso significato;
* ⚠️ **debito, come la partita IVA del lotto 1**: che l'utente possa lavorare nell'emittente attivo lo
  controlla solo il backend (`is_scelta_valida`, sulla canonica `fn_check_user_emittente_scope`). Una regola
  senza un guard sulla tabella.

**Prova dei lotti 8-9** (scratch, prima dell'apply): i due pgTAP nuovi **15/15** e **13/13**; tutti i
changeSet `-40` … `-47` compilano in una transazione annullata. La regressione dei pgTAP che creano
operatori (`fn_crea_risorsa_umana_v2` e `fn_crea_utente_tecnico` riscritte) non è partita prima dell'apply:
l'ha data la corsa di Tid, verde (2026-10-18).

⚠️ **Le prove di tutti i lotti girano su uno scratch che aveva già i changeSet `-16` … `-29` della sessione
plancache** (policy `ef_whitelist` e funzioni di scope). Nessun file di questi lotti dipende dai loro; le
policy che i guard e la RLS chiamano a runtime erano le loro versioni nuove.

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

### 5-ter.3 La 2b-3 scritta e provata (team DB, 2026-10-18)

| changeSet / file | Che cosa |
| --- | --- |
| `00_schema/dbops/20261018-55`, `-56` | `dbops.credenziali_di_prova` (auth_user_id, chiave = username alla nascita) e `dbops.soggetti_di_prova` (soggetto_id, chiave = codice di prova), solo audit di nascita |
| `20_code/dbops/20261018-57` | `dbops.fn_dati_di_sviluppo_ammessi_su_valori(ambiente)`: la regola, pura sul valore (§5.5) |
| `20_code/dbops/20261018-58`, `-59` | il guard delle etichette: `INSERT` solo in SVILUPPO (`E_DATI_DI_SVILUPPO_IN_PRODUZIONE`), `UPDATE`/`DELETE`/`TRUNCATE` mai (`E_ETICHETTA_DI_PROVA_IMMUTABILE`) |
| `20_code/anagrafiche/20261018-60` | **il verbo `anagrafiche.fn_provisiona_dati_di_sviluppo(p_password_hash jsonb)`**, SECURITY DEFINER |
| `90_end/20261018-61` + loop `20260205-41` + fase `post` di `provision_zeroerp.sql` | le due tabelle in sola lettura per l'app (tre sedi, §11.8) |
| `20_code/dbops/20261018-62` + `presidi.csv`, `presidi_testi.csv` | il presidio `dbops.vw_radici_di_prova_in_produzione` |
| `20_code/anagrafiche/20261018-63` | BB **`anagrafiche.fn_accendi_veste(identità, credenziale, vesti)`** (regola del 2, sotto) |
| `20_code/dbops/20261018-64` | il builder `fn_pgtap_crea_operatore_umano` accende la veste dal BB |
| `codici_errore.csv`, `messaggi_errore.csv` | `E_DATI_DI_SVILUPPO_IN_PRODUZIONE` (NON_ESEGUIBILE, 1356), `E_ETICHETTA_DI_PROVA_IMMUTABILE` (TECNICO, 1357), `E_RADICE_DI_PROVA_SENZA_ETICHETTA` (CONFLITTO_STATO, 1358) |
| pgTAP | nuovi `dbops/test-etichette-di-prova-v1` (16, runner owner) e `anagrafiche/test-fn-provisiona-dati-di-sviluppo-v1` (20, runner owner) |
| manual | le due tabelle, la regola, il presidio, il verbo, `fn_accendi_veste` |

**Scelte di forma, dichiarate:**

* **Le etichette in `dbops`, non in `anagrafiche`** (il disegno del §5-ter.2 diceva anagrafiche). Sono un
  dato di macchina del provisioning, come `dbops.installazione` e `dbops.processi_identita`; le automazioni
  di `ci_apply` coprono `anagrafiche` per intero e su righe che non cambiano mai monterebbero audit,
  `tx_id` e storico inerti.
* **Un codice per la regola**: il guard delle etichette e il verbo dicono la stessa cosa
  (`E_DATI_DI_SVILUPPO_IN_PRODUZIONE`), e leggono la stessa funzione pura.
* **Il verbo nasce solo sopra madri e BB** (strada b): `fn_crea_soggetto_pg`, `fn_crea_indirizzo_soggetto`,
  `fn_create_indirizzo`, `fn_crea_emittente_fiscale`, `fn_crea_magazzino`, `fn_crea_cliente`,
  `fn_crea_fornitore`, `fn_crea_operatore_v2`, `fn_crea_auth_user`, `fn_crea_veste_portale`,
  `fn_accendi_veste`, `fn_scrivi_profilo_accesso`, `fn_lega_profilo_identita`,
  `fn_change_user_emittenti_scope`, `fn_imposta_override_oggetti`, `fn_imposta_emittente_attivo`. Dai
  builder pgTAP prende solo i generatori puri di CF e P.IVA (ammessi dal §7.1 del brief BE). Scrive da sé
  solo le etichette (ne è l'unico scrittore) e la password di una credenziale riallineata (prima
  occorrenza nel DB).
* **Regola del 2, trovata scrivendo**: accendere una veste era un `UPDATE` in due punti (backend
  `attiva_identita`, builder `fn_pgtap_crea_operatore_umano`); il verbo sarebbe stato il terzo. Nasce
  `fn_accendi_veste`, il builder passa a lui nello stesso giro (`-64`), il backend nella 2b-2.
* **Le GUC di sessione le governa il verbo**, e le rimette com'erano: vuote mentre nascono i BA (il legame
  BA → emittente lo scrive il BB verso l'emittente chiesto, non `z90` verso quello di chi chiama);
  `dev.smoke` dentro l'emittente del magazzino mentre nasce il magazzino (il guard di scope, dentro una
  DEFINER senza operatore, ferma una riga che ha un padrone: lotto 7).
* **I profili `DEV_*` non sono radici** (risposta al brief BE §7.3): configurazione legata alle sole
  identità etichettate, riscritta a ogni corsa su tutte le aree presenti.
* **Le persone**: per gli operatori il PF lo crea `fn_crea_operatore_v2` e il verbo lo etichetta
  (`DEV-PERSONA-<NOME>`); le credenziali dei portali non hanno una persona, perché la loro veste sta sul ruolo
  del cliente o del fornitore. Un PF senza legame sarebbe una radice senza scopo.
* ⚠️ **Uno scostamento dall'elenco del brief BE, imposto dal modello**: un ruolo cliente ha una sola veste
  portale attiva (`uq_identita_digitali_sr_ruolo_attivo`), quindi `dev.multiveste` non può stare sul
  cliente 1 insieme a `dev.portale1`. Ha un cliente suo, **`DEV-CLIENTE-3`** su A (venti radici in tutto).
* **Password**: hash Django per username; assente alla nascita = password inutilizzabile (`!…`), assente dopo
  = invariata.
* Restano fuori, apposta: il ritiro dell'utente `smoke` (lo disattiva il BE dopo aver spostato gli
  smoke), il secondo fattore (il BE dopo il verbo; la colonna `secondo_fattore` dice chi), una funzione
  `script.fn_credenziale_di_prova` (T-4: la lista Operatori fa `LEFT JOIN dbops.credenziali_di_prova`, una
  funzione per una colonna non serve).

**Prova** (scratch, SQL estratto `-55` … `-64` più le righe nuove dei CSV, owner, transazione annullata):

* il verbo in due corse: **20 radici `creata`, poi 20 `riallineata`**, 8 credenziali e 12 soggetti
  etichettati, nessuna etichetta nuova alla seconda; vincoli differiti rispettati; GUC rimesse com'erano;
* `test-etichette-di-prova-v1` **16/16** (SVILUPPO, PRODUZIONE e non dichiarato costruiti);
  `test-fn-provisiona-dati-di-sviluppo-v1` **20/20**; nel mondo CI simulato (senza `django.auth_user`) 2
  verdi e 18 `skip()` motivati;
* **62 pgTAP prima e dopo** (i presidi trasversali, `test-installazione-ambiente-v1`,
  `test-processi-accensione-produzione-v1` e chi usa `fn_pgtap_crea_operatore_umano`): identici. Il
  rubinetto del primo motivo era rosso per un falso positivo di forma (`->> 'codice'` dentro la chiamata
  che solleva), corretto nel verbo prima della consegna.

⚠️ Non provato: la corsa come app (il verbo è DEFINER; l'app lo chiama e basta); la fase `post` del
provisioning con le due righe nuove (serve un superuser: alla prima corsa di `ci-local.sh` o in CI).

✅ **Applicata su dbdev e sullo scratch, pgTAP verdi (Tid, 2026-10-18).** Il primo apply si era fermato
sulla preCondition del `-60`, che contava anche `fn_accendi_veste` (nasce nel `-63`, dopo): il `-60` non era
entrato, il file è stato corretto (la funzione esce dalla preCondition, il corpo plpgsql la risolve alla
prima chiamata) e il migrate è ripartito.

**Ricaduta BE (2b-3, T-1 … T-6 del brief BE):**

1. **codici d'errore**: rigenerare la policy e i ripieghi per `E_DATI_DI_SVILUPPO_IN_PRODUZIONE`,
   `E_ETICHETTA_DI_PROVA_IMMUTABILE`, `E_RADICE_DI_PROVA_SENZA_ETICHETTA`;
2. **il command** chiama `SELECT * FROM anagrafiche.fn_provisiona_dati_di_sviluppo(%s::jsonb)` con
   `{username: hash Django}` e stampa le righe; poi configura il secondo fattore per le righe con
   `secondo_fattore = true` (oggi `dev.smoke`);
3. **la lista Operatori**: `LEFT JOIN dbops.credenziali_di_prova cp ON cp.auth_user_id = …`, colonna
   `cp.auth_user_id IS NOT NULL AS di_prova` (filtro di default e badge);
4. **gli smoke** passano a `dev.smoke`, poi `smoke` si disattiva;
5. ⚠️ **`dev.multiveste` è sul cliente 3**, non sul cliente 1 (sopra).

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

> ⚠️ **Superata per la parte del consenso** dal §6.6 (Tid, 2026-10-18): il consenso si ritira, ma
> **dopo** che il divieto di accensione in produzione è entrato nel modello (R-BE-5). Il §6.5 diceva
> il contrario alla stessa data: la contraddizione è emersa al merge del 2026-10-18.

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

### 6.4 L'incidente del 2026-10-16 23:45, e le due reti aggiunte (sessione BE, 2026-10-17)

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

### 6.5 Punto 7 — lo smoke notturno: decisioni di Tid (2026-10-17)

* ✅ **Una tolleranza vera in sviluppo.** Il 2026-10-13 la tolleranza dello smoke era stata lasciata
  NULL perche' il panorama non distingueva spento da morto: in produzione, dove lo smoke non gira,
  avrebbe suonato ogni giorno. Con lo stato `SPENTO` quel motivo cade: in produzione lo smoke e'
  spento (default a catalogo), non morto. Senza tolleranza, invece, un giro notturno che smette di
  partire su sviluppo non lo vede nessuno.
* ⚠️ **Superato dal §6.6 (Tid, 2026-10-18).** S-2 al §6.2 diceva il contrario alla stessa data.
  Il fatto qui sotto resta vero ed è quello che ha deciso: il consenso si ritira, ma dopo R-BE-5.
* ~~✅ **`SMOKE_NOTTURNO_CONSENTITO` resta** come seconda serratura:~~ lo smoke e' spegnibile, quindi in
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

### 6.6 Il consenso dello smoke: la decisione (Tid, 2026-10-18)

**La contraddizione.** Lo stesso giorno (2026-10-17) S-2 (§6.2, team DB) diceva «il consenso
`SMOKE_NOTTURNO_CONSENTITO` si ritira» e il §6.5 (sessione BE) diceva «resta». È emersa al merge
del 2026-10-18.

**Avevano ragione tutti e due, ciascuno su una metà.**

* **Il fatto (BE):** in produzione lo smoke è spento di default, ma `fn_imposta_accensione_processo`
  con `p_acceso = true` lo accende «qualunque cosa dica il default». `smoke_notturno` ha
  `spegnibile = t`, quindi nessun guard lo ferma: un click e un motivo dal drawer bastano.
  Oggi a fermarlo è solo la riga che manca in `.env.systemd`. Togliere il consenso adesso aprirebbe
  la strada a documenti di prova su una base vera (numerazione fiscale compresa, che non torna
  indietro).
* **Il principio (DB):** una protezione in un `.env` di una macchina non sta nel modello. Il drawer
  non la vede, non ha storia né autore, e la si perde in silenzio copiando il file da sviluppo.
* L'argomento «in produzione `dev.smoke` non esiste» non regge: R-4 non c'è ancora, e uno smoke
  che si ferma perché mancano gli utenti è una coincidenza, non una regola.

**Il difetto vero è un'asimmetria del modello.** Il catalogo sa dire «questo processo non si può
**spegnere**» (`spegnibile`). Non sa dire «questo processo non si può **accendere** a mano in
questo ambiente». Il consenso nel `.env` copre proprio quel concetto che manca: non è un doppione
del DB.

**Decisione.** Il divieto entra nel modello, e poi il consenso si ritira, in quest'ordine:

1. **R-BE-5 — al team DB.** Il gemello di `spegnibile`: un processo «non accendibile a mano in
   `PRODUZIONE`». Il guard di `dbops.processi_accensione` rifiuta `acceso = true` per quel processo
   quando l'ambiente dichiarato è `PRODUZIONE`, con un codice d'errore suo (+ messaggio e ripiego).
   `smoke_notturno` è il primo a usarlo. Il guard deve valere anche se la riga a mano esiste già
   (una scelta fatta prima della regola) e, da verificare scrivendo, anche se l'ambiente si
   dichiara dopo la scelta. Forma (colonna nel catalogo, nome, codice) a scelta del team DB, dentro
   la regola del 2: si appoggia al guard che c'è già, non ne nasce un secondo.
2. **Lato BE, dopo l'apply di R-BE-5:** via `SMOKE_NOTTURNO_CONSENTITO` dal command
   (`smoke_notturno.py`, `ENV_CONSENTITO` e test), dalla unit, da `.env.systemd` di dbdev e dalla nota
   in `sveglie.json`, nello stesso giro della nota sulla tolleranza (riga 10). Il drawer mostra il
   gesto come non disponibile, come per i non spegnibili. Codice d'errore nuovo: policy rigenerate
   e ripiego.

Non è un tampone: il consenso c'è già, e ritirarlo prima del guard aprirebbe il buco che oggi copre.

### 6.7 R-BE-5 scritto (team DB, 2026-10-18)

#### 6.7.1 I changeSet

| changeSet / file | Che cosa |
| --- | --- |
| `00_schema/dbops/20261018-10` | `dbops.processi.accendibile_in_produzione`; `chk_processi_accensione` riscritto (NULL senza sveglia, obbligatoria con la sveglia, e un non accendibile è spento di default in produzione), rinasce NOT VALID |
| `20_code/dbops/20261018-11` | `dbops.fn_accensione_a_mano_ammessa_su_valori(acceso, accendibile_in_produzione, ambiente)`: il divieto, puro sui valori (IMMUTABLE, sql) |
| `20_code/dbops/20261018-12` | `dbops.fn_processo_acceso_su_valori` col parametro in coda (DROP della firma a sette + CREATE): la scelta a mano decide solo se il divieto la ammette; `fn_processo_acceso_dichiarato` gliela passa |
| `20_code/dbops/20261018-13` | il guard di `processi_accensione`: il terzo rifiuto, `E_PROCESSO_NON_ACCENDIBILE_IN_PRODUZIONE`; ambiente non dichiarato → `E_CONFIG_MANCANTE` |
| `90_end/20261018-14` | convalida del CHECK riscritto (su un database nuovo la fa già `20261016-31`) |
| `processi.csv` + mirror `20260904-13` | colonna in coda: `f` per `smoke_notturno`, `t` per gli altri con sveglia, `NULL` per CODA e ritirati |
| `codici_errore.csv`, `messaggi_errore.csv` | `E_PROCESSO_NON_ACCENDIBILE_IN_PRODUZIONE` (NON_ESEGUIBILE, 1355) |
| pgTAP | `test-processi-accensione-v1` (35 → 47: predicato, regola, catalogo, CHECK), **nuovo** `test-processi-accensione-produzione-v1` (12, runner owner); 13 file con le fixture adeguate (sotto) |
| manual | `processi`, `processi_accensione`, `fn_imposta_accensione_processo` |

#### 6.7.2 Scelte di forma, dichiarate

* **Una colonna «in produzione», non «per ambiente».** In sviluppo accendere a mano è sempre
  lecito: una colonna per l'altro ambiente non avrebbe un caso.
* **Un predicato, tre lettori.** La condizione sta in `fn_accensione_a_mano_ammessa_su_valori` e la
  leggono il guard (rifiuta il gesto nuovo), la regola dello stato effettivo (ignora una riga accesa
  già scritta: i due casi del §6.6, «la riga esiste già» e «l'ambiente si dichiara dopo») e il
  backend per il pulsante. Pura sui valori come la regola (§5.5).
* **Il parametro nuovo della regola è senza default**: il default che rifà il comportamento di prima
  è il buco chiuso qui. L'unico chiamante (`fn_processo_acceso_dichiarato`) si riscrive nello stesso
  changeSet; il backend non chiama la regola.
* **Il guard chiede l'ambiente solo quando serve** (accendere un non accendibile). Con l'ambiente
  non dichiarato quel gesto si ferma (`E_CONFIG_MANCANTE`); spegnere e tornare al default no.
* **Il CHECK si riscrive, non se ne aggiunge un secondo**: è il contratto dell'accensione, e «senza
  sveglia, colonne NULL» resta scritto una volta. Il prezzo: i pgTAP che creano processi finti con
  una sveglia dichiarano la colonna. Censiti per `spegnibile, causa_fallimento)` e per la coda
  `'PROGRAMMA')`: **43 tuple in 12 file**, adeguate col valore di `spegnibile` della stessa tupla
  (`true` con la sveglia, `NULL` sui CODA, il `CASE` del ciclo dei canali), più il ritiro finto di
  `digest_presidi` in `test-fn-guardiano-digest`.
* **La prova del ramo PRODUZIONE sul dato**: il §5.5 la voleva solo sui valori. Il file nuovo la
  costruisce davvero, come `test-installazione-ambiente-v1` costruisce l'ambiente non dichiarato:
  runner owner, trigger di immutabilità spento dentro la transazione, `ROLLBACK`.

#### 6.7.3 Ricaduta BE (riga 10)

1. **Codice d'errore nuovo**: rigenerare `error_policies_generated.py` e il ripiego in
   `error_messages_fallback.py` per `E_PROCESSO_NON_ACCENDIBILE_IN_PRODUZIONE`. Finché non si fa, il
   guardrail dei codici del backend è rosso.
2. **La capability del drawer** («Accendi» disabilitato col motivo, come per i non spegnibili):
   `_con_capability_accensione` oggi la deriva da `spegnibile`. Per il gesto «accendi» il DB espone
   il predicato: nella lettura dell'accensione (`ProcessiRepository.accensione_processo`)
   `dbops.fn_accensione_a_mano_ammessa_su_valori(true, p.accendibile_in_produzione,
   script.fn_ambiente_dichiarato())`: `false` → motivo `E_PROCESSO_NON_ACCENDIBILE_IN_PRODUZIONE`,
   `NULL` → `E_CONFIG_MANCANTE`. ⛔ Non ricalcolare la condizione in Python (§12.1 delle
   linee-guida SQL: il predicato è lo stesso del guard). Spegnere e tornare al default restano
   ammessi.
3. **Dopo l'apply**: il ritiro di `SMOKE_NOTTURNO_CONSENTITO` (command, unit, `.env.systemd` di dbdev,
   nota in `sveglie.json`), come deciso al §6.6.

#### 6.7.4 La prova (scratch `zeroerp_ruoli`, 2026-10-18)

SQL estratto dei cinque changeSet + upsert **completo** di `processi.csv` (28 righe, nessuna
rifiutata) + le due righe dei codici, in una transazione annullata, come `zeroerp_owner`:

* `test-processi-accensione-v1` **47/47**, `test-processi-accensione-produzione-v1` **12/12**;
* il file nuovo **vede il difetto**: senza `-12` e `-13` sono rossi 3, 4, 5, 6, 7 e 11;
* **37 pgTAP identici prima e dopo** (prima: la versione committata, senza il prefisso; dopo: il
  working tree, col prefisso): tutti quelli che scrivono o leggono `dbops.processi`,
  `processi_accensione`, la sveglia, l'installazione, più i presidi trasversali (`riferimenti-morti`,
  `catalogo-messaggi-errore-completo`, `rubinetto-primo-motivo`, `security-definer-search-path`,
  `stati-check-scrittori`, `catalogo-presidi`, `vw-codici-errore-*`, `storico-scope-policy`). Già
  rossi sullo scratch, identici prima e dopo: `test-identita-tecnica` e `test-fn-crea-utente-tecnico`
  («il soggetto non ha contatti validi», §5-ter.2 lotto 3), `test-rls-email-log-ambito` (2 su 6).
  `maintenance/test-vw-job-run-da-guardare` nel working tree è dell'altro cantiere e vuole la sua
  colonna (`corsa_verdetto_completo`), non applicata sullo scratch;
* cancelli statici: verdi. Il preambolo segnala `test-automazioni-guasto-ambiente-rilanciato-v1`,
  già committato da `brief-db-presidio-job-run-a-chi-tocca`, non di questo giro.

⚠️ Non provato: la corsa come app (la prova gira da owner).

✅ **Applicato su dbdev il 2026-10-18 (Tid), pgTAP senza regressioni.**

**Per Tid, l'apply** (fatto). ⚠️ `processi.csv` e il mirror `20260904-13` portano anche la colonna
`corsa_verdetto_completo` di `brief-db-intermittente-e-verdetto-completo` (`00_schema/20261018-01`,
non ancora applicato): il mirror carica le due colonne insieme, quindi i due giri si applicano
**insieme**. Poi i pgTAP: `dbops/test-processi-accensione-v1`,
`dbops/test-processi-accensione-produzione-v1` (owner), e i 13 file adeguati.

### 6.8 Riga 10 fatta (sessione BE, 2026-10-18)

* **Codice nuovo:** `E_PROCESSO_NON_ACCENDIBILE_IN_PRODUZIONE` in `error_policies_generated.py`
  (NON_ESEGUIBILE, nessuna classe cambiata) e il ripiego, senza `%s`, in `error_messages_fallback.py`.
* **La capability di «Accendi».** `ProcessiRepository.accensione_processo` legge
  `dbops.fn_accensione_a_mano_ammessa_su_valori(true, p.accendibile_in_produzione,
  script.fn_ambiente_dichiarato())`; `_con_capability_accensione` ne fa la terna `can_accendere`,
  `_reason`, `_reason_key` (`false` → `E_PROCESSO_NON_ACCENDIBILE_IN_PRODUZIONE`, `NULL` →
  `E_CONFIG_MANCANTE`), e il dato grezzo non arriva al client. «Spegni» e «Torna al default» restano
  sotto `can_imposta_accensione`. Il drawer mostra «Accendi» spento col motivo nel tooltip
  (`bloccoAttivo`/`motivoBloccoRiga`, come «Esegui ora»; chiavi `accendi_blocco.*`).
* **Consenso ritirato:** `ENV_CONSENTITO` e il suo rifiuto via dal command `smoke_notturno`, il test
  3 ritirato, il test 8 prova il passaggio dell'ambiente con una variabile qualsiasi; commenti della
  unit e nota di `sveglie.json` riscritti (divieto a catalogo, tolleranza 1560, la spia finché un
  giro non torna verde).
* **Test:** `test_processi_accensione` 6 (la terna dai cinque casi), `test_processi_accensione_db` 5
  (binding del predicato sul DB vero, smoke notturno e coda stampa). Corretto anche il test 1 dello
  stesso file, rosso dal giro 2a: «torna al default» ora vuole il motivo.
* **La scelta «accendi» non ammessa** (revisione del 2026-10-18): una riga accesa a mano scritta
  prima del divieto, o prima che l'ambiente fosse dichiarato, resta nella tabella ma la regola la
  ignora (§6.6). Il drawer avrebbe mostrato «Spento» sopra «Scelta a mano: …». Ora la scelta viaggia
  con `ammessa` (la risposta dello stesso predicato; una scelta che non accende è sempre ammessa) e
  il drawer dice «Scelta a mano non applicata … "Torna al default" la toglie». Test 7 del service.
* ⚠️ Il ramo PRODUZIONE sul DB vero non si prova dal backend (l'ambiente è immutabile e la CI è
  SVILUPPO): lo prova il pgTAP sui valori; qui la terna è provata coi tre valori del predicato.

### 6.9 Ricaduta della 2b-3 fatta (sessione BE, 2026-10-18)

Il dettaglio sta nel [brief BE §8](brief-be-utenti-di-sviluppo.md). In breve:

* **codici**: i tre della 2b-3 nella policy generata e nei ripieghi;
* **il command** `manage.py provision_utenti_sviluppo [--nuove-password]` chiama
  `anagrafiche.fn_provisiona_dati_di_sviluppo`: prima senza password, poi (stessa transazione) con l'hash
  Django delle password nuove, per le credenziali appena create o per tutte. Il secondo fattore di chi lo deve
  avere lo configura `SecondoFattoreService.configura_confermato` dentro il contesto della credenziale (i verbi
  `fn_totp_*` chiedono `fn_guard_utente_stesso`). Ambiente letto a ogni corsa da `fn_ambiente_dichiarato`;
* **la lista Operatori**: `LEFT JOIN dbops.credenziali_di_prova`, colonna `di_prova`, parametro
  `includi_di_prova` (assente = nascosti); FE con l'interruttore e il badge;
* **smoke e run-book**: commenti a `dev.smoke`, lo smoke RLS con `dev.emittente`, run-book §11 riscritto.

Prova del binding sul DB vero: `anagrafiche/tests/db/test_provisioning_sviluppo_db` gira il command intero (il
verbo crea o riallinea le venti radici) in una transazione annullata. ⚠️ Non provato: il command su dbdev
fuori dai test (il collaudo di Tid).

### 6.10 La 2b-2 fatta (sessione BE, 2026-10-18)

Il backend crea dalle madri del DB, e le sue copie sono ritirate nello stesso giro:

| Lotto | Il backend chiama | Ritirato |
| --- | --- | --- |
| 1 emittente | `fn_crea_emittente_fiscale` (`EmittentiFiscaliRepository.crea_emittente_fiscale`) | `transaction.atomic`, `get_or_create_ruolo_emittente`, `create_emittente`, `_CREATE_COLS`, l'UPDATE di conferma del regime |
| 2 indirizzi del ruolo | `fn_crea_indirizzi_ruolo` (`SoggettiService.create_indirizzi_ruolo`, i tre chiamanti) | la saga Python (matrice, auto-clone, skip), `get_existing_tipo_indirizzo_ids`, `_create_stradario_da_generale`, `IndirizziRepository.get_or_create_stradario` e `create_indirizzo_dettaglio`: la via la risolve `fn_create_indirizzo`, anche per gli indirizzi di soggetto (`GeoService.crea_dettaglio_indirizzo`) |
| 3 contatto | `fn_crea_contatto` (`SoggettiRepository.crea_contatto`) | l'INSERT |
| 4 fornitore | `fn_crea_fornitore` | i quattro passi del service, `get_or_create_ruolo_fornitore`, `create_fornitore`, `_CREATE_ALLOWED` |
| 5 cliente | `fn_crea_cliente` (istanza e BA nuovi, o quelli indicati) | i sei passi, `get_or_create_ruolo_cliente`, `create_istanza_fittizia`, `create_billing_account`, `create_cliente`, `_CLIENTE_CREATE_ALLOWED` |
| 6 veste portale | `fn_crea_veste_portale` (`PortaleRepository.create_identita_portale`) | l'INSERT |
| 7 magazzino | `magazzino.fn_crea_magazzino` | l'INSERT del BB di scrittura |
| 8 profilo e legame | `fn_scrivi_profilo_accesso` (profilo di reparto), `fn_lega_profilo_identita` (SUPER_ADMIN) | UPSERT del profilo, DELETE+INSERT di aree e azioni, la INSERT `ON CONFLICT DO NOTHING` del legame |
| 9 override, emittente attivo | `fn_imposta_override_oggetti` (le sei chiavi sempre: `valido_dal` null = senza inizio), `fn_imposta_emittente_attivo` | DELETE+INSERT, UPSERT |
| accensione della veste | `fn_accendi_veste` (`AuthRepository.attiva_identita`) | l'UPDATE |

Con loro escono anche il BB `get_or_create_soggetto_ruolo` (senza più chiamanti) e
`crea_contatto_inline_se_valido`: il contatto inline lo classifica `contatto_inline_per_madre` (decide SE c'è un
contatto), lo scrive la madre. Gli indirizzi arrivano alle madri da `indirizzi_per_madre`, coi pre-check per
l'operatore (non oggetto, via nuova incompleta).

**Due comportamenti cambiano, ed è il modello:**

* SUPER_ADMIN chiesto su un accesso che ha già un altro profilo: prima la richiesta spariva (`ON CONFLICT DO
  NOTHING`, il salvataggio rispondeva ok), ora `uq_profili_accesso_bindings_identita` lo rifiuta e il service
  risponde 400 `E_AMM_VALIDAZIONE` sul campo `is_super_admin`;
* un indirizzo di ruolo in forma libera porta anche `locality`, `postal_box`, `administrative_area`,
  `sublocality`: il backend li scartava.

**Richieste al team DB** (due scritture che le madri non coprono, oggi del backend):

* **R-BE-6 — l'indirizzo di ruolo per istanza.** `POST …/ruoli/<id>/indirizzi/` crea UN indirizzo, anche per
  un'istanza (`istanza_utility_id`), e ne restituisce l'id. `fn_crea_indirizzi_ruolo` non conosce l'istanza e
  torna un conteggio: `SoggettiRepository.crea_indirizzo_ruolo` resta una INSERT del backend (la via passa già
  dalla madre `fn_create_indirizzo`). Proposta: l'istanza fra le chiavi ammesse, o un BB dell'indirizzo singolo
  che la madre degli indirizzi usa.
* **R-BE-7 — il legame di reparto.** `put_profilo_reparto` scrive il profilo dalla madre, ma il legame
  profilo → unità organizzativa resta un UPSERT del backend: `fn_lega_profilo_identita` lega identità. Proposta:
  il legame di reparto nella stessa forma (o il ramo del reparto nella madre del legame). Anche lo slegare
  SUPER_ADMIN (DELETE) è del backend: non ha una madre.
* **R-BE-11 — il profilo SUPER_ADMIN si risolve in una sede** (regola del 2, ok Tid 2026-10-18). La regola
  «per `tipo`, fra i profili **attivi**, esattamente uno, altrimenti `E_CONFIG_MANCANTE`» è scritta dentro
  `fn_crea_risorsa_umana_v2` e, dal 2026-10-18, anche in `AmmSoftwareRepository._set_super_admin_binding`. Fino a
  quel giorno il backend cercava il profilo con una sottoquery per il solo `tipo`: con due profili di quel tipo (il
  modello non lo vieta) era un 500, e legava anche un profilo spento. Proposta: un lettore
  `config.fn_profilo_super_admin()` (o nome a scelta del team) che risolve o solleva, usato dalla madre della
  risorsa umana e dal backend; il backend ritira la sua copia nello stesso giro. Presidio BE già scritto:
  `test_operatore_altre_vesti_db` 3b (due profili attivi → `E_CONFIG_MANCANTE`, nessun legame).
* **R-BE-12 — la madre plurale degli indirizzi di SOGGETTO.** `fn_crea_indirizzi_ruolo` scrive gli indirizzi
  di un ruolo con l'auto-clone dei tipi obbligatori; per il soggetto c'è solo la madre singolare
  `fn_crea_indirizzo_soggetto`, e l'auto-clone dalla matrice `tipi_soggetto_dettaglio` (col flag `auto_clone`
  del payload) resta una saga del backend: `SoggettiService._apply_auto_clone` + `_create_indirizzi_batch`. È
  un'asimmetria fra i due livelli. Proposta: `fn_crea_indirizzi_soggetto(p_soggetto_id, p_indirizzi,
  p_auto_clone)` gemella di quella del ruolo (le stesse tre forme dell'indirizzo, la forma estera di R-BE-10
  compresa); il backend ritira la saga nello stesso giro. Nel frattempo (2026-10-18) è sanato lato BE il
  difetto della saga: il primo dettaglio si riusava per ogni indirizzo successivo senza dettaglio, anche per
  una via diversa (lo stesso già trovato sul ruolo); ora ogni indirizzo risolve il suo.

**Decisioni di Tid su R-BE-6, R-BE-7, R-BE-12 (2026-10-19), col via allo sviluppo** (risposta del team DB nel
§6.16):

* **D-16a — indirizzi, singolare + plurale per entrambi i livelli.** Ogni livello ha due madri: la singolare
  crea UN indirizzo e restituisce l'id (quella del ruolo ammette anche l'istanza), la plurale ne crea più d'uno
  con la copia automatica degli obbligatori e usa la singolare. Nascono `fn_crea_indirizzo_ruolo` (R-BE-6) e
  `fn_crea_indirizzi_soggetto` (R-BE-12); il backend ritira la sua INSERT e la sua procedura.
* **D-16b — il legame profilo → reparto in una madre gemella:** `fn_lega_profilo_reparto(profilo, unità
  organizzativa)`, sulla forma di `fn_lega_profilo_identita`.
* **D-16c — lo slegare in questo giro:** le madri che slegano un profilo dall'identità e dal reparto; il
  backend non scrive più sui legami.

**Trovato, da decidere (non toccato):** la forma «libera» dell'indirizzo nel frontend
(`useIndirizzoSoggettoForm._buildPayload`) manda testo, stato e località; `chk_indirizzi_free_requirements` vuole
anche comune + CAP, oppure casella postale e area/sottolocalità. Un indirizzo libero dal drawer non può nascere.

**Prova:** sul DB vero, in transazione annullata, `anagrafiche/tests/db/test_creazioni_dalle_madri_db` (6:
emittente e duplicati tradotti per nome attraverso la madre, indirizzi del ruolo con l'auto-clone e il guard
differito, veste portale, emittente attivo, override con `valido_dal` null), `test_clienti_fornitori_scrittura_db`
riscritto sui service, `test_regime_fiscale_conferma_db`, `test_contatti_creazione_db`,
`test_anagrafiche_magazzino_db`, `test_operatore_altre_vesti_db` (con il nuovo rifiuto del legame),
`test_profilo_reparto_secondo_fattore_db`. Il test della divergenza dei codici era rosso su dbdev perché il
catalogo era avanti rispetto al branch (`E_DOC_EMITTENTE_IMMUTABILE`, `E_DOC_UTILITY_IMMUTABILE`,
`E_ARTICOLO_STRUTTURA_RIGHE_APERTE`, di altri cantieri). ✅ Rigenerato il 2026-10-18, dopo aver verificato che i tre
codici sono a catalogo in git (`Tito-dev`, PR #1880) e che la differenza era solo quella; ripieghi senza `%s`.

### 6.11 L'indirizzo libero non può nascere (sessione BE, 2026-10-18)

**Il caso.** Nei drawer di soggetto, cliente e fornitore l'indirizzo «libero» (testo e stato, per le vie fuori
stradario e per l'estero) non si salva mai. I vincoli gemelli `chk_indirizzi_free_requirements` (ruolo) e
`chk_indirizzi_soggetti_free_requirements` (soggetto) vogliono, oltre a testo e stato, **comune + CAP** oppure
**località + codice postale + regione o sotto-località**; il form chiede testo, stato e località facoltativa.
L'operatore riceve `E_DATABASE`, «Errore durante l'operazione database», senza sapere quale campo manca.

**Chi ha ragione: il modello** (Tid, 2026-10-18). Il form si allinea, in due varianti: lo stato di sistema con
comune e CAP, l'estero con località, codice postale e regione.

**Fatto lato BE (2026-10-18):** l'indirizzo libero del soggetto passa alla madre `fn_crea_indirizzo_soggetto`
anche comune e CAP, che lei pretende e il backend buttava (prima nemmeno la forma italiana poteva nascere). Gli
indirizzi di ruolo li portavano già tutti dalla 2b-2 (`indirizzi_per_madre`). Prova sul DB vero:
`test_creazioni_dalle_madri_db` 7.

**Richieste al team DB:**

* **R-BE-8 — lo stato di sistema.** Il form sceglie la variante dallo stato: serve sapere qual è lo stato
  dell'installazione, come il fuso (`SYSTEM_FUSO_ORARIO` + `script.fn_fuso_operativo()`: un valore di sistema,
  senza override, letto da un lettore che valida e non ripiega, `E_CONFIG_MANCANTE`). Oggi c'è
  `soggetto_default_stato_iso2 = IT`, che però dice «lo stato proposto creando un soggetto»: decidere se è la
  stessa cosa (un parametro solo, regola del 2) o due. Da censire anche le `'IT'` scritte nel corpo delle
  funzioni: `config.fn_sigla_provincia_ammessa` e il ripiego di `vendite.fn_resolve_iva_riga` parlano dello stato
  di casa; il dispatch di CF e P.IVA (`trgfn_soggetti_valida_cf_piva_dispatch`) applica regole italiane e
  resta `'IT'`.
* **R-BE-9 — il rifiuto col codice e il campo.** Oggi l'indirizzo libero incompleto è solo un CHECK, che arriva
  come `E_DATABASE`. Un guard sulle due tabelle con un codice suo (per esempio `E_INDIRIZZO_LIBERO_INCOMPLETO`,
  DATO_ERRATO) e il primo campo mancante nel canale `COLUMN`; il CHECK resta come rete.
* **R-BE-10 — la forma estera nella madre del soggetto.** `fn_crea_indirizzo_soggetto` pretende comune e CAP
  per ogni indirizzo libero e non ha i parametri `locality`, `postal_box`, `administrative_area`,
  `sublocality`: la forma estera, che la tabella ammette, non passa. È un'asimmetria con
  `fn_crea_indirizzi_ruolo`, che la scrive. I suoi rifiuti usano `E_ADMIN_VALIDAZIONE` col solo `parametro`.
* **Da valutare (Tid d'accordo):** alleggerire la regione nella forma estera (oggi regione **o** sotto-località
  obbligatoria): località e codice postale sono ciò che serve a spedire e alla fattura elettronica.

**Dopo il DB, BE/FE (riga 9-ter-quater):** il form dell'indirizzo libero in due varianti scelte dallo stato
(stato di sistema dal lettore R-BE-8), la validazione del form sulla stessa regola, e il backend che passa la
forma estera anche per il soggetto.

### 6.12 Ricaduta BE/FE delle due forme dell'indirizzo libero (sessione BE, 2026-10-18)

> Risposta del team DB al §6.11: commit `42ae92188` (D-1 … D-4 di Tid). Scritta sul codice vero (changeSet e
> doc auto-generata), **prima dell'apply**: le prove sul DB vero si fanno dopo (riga 9-ter-quinquies).

| Che cosa | Dove |
| --- | --- |
| l'indirizzo del soggetto con la firma nuova `fn_crea_indirizzo_soggetto(soggetto, indirizzo jsonb)`: un oggetto, la stessa grammatica del ruolo (`indirizzo_per_madre`, estratto da `indirizzi_per_madre`); la forma estera passa anche per il soggetto. Ritirati il percorso posizionale e `_create_indirizzo_libero` | `SoggettiRepository.crea_indirizzo_soggetto`, `SoggettiService._create_indirizzo` |
| `postal_box` → `postal_code` nelle colonne scrivibili degli indirizzi di ruolo | `soggetti_repository.py` |
| la tendina degli stati porta `catalogo_comuni_completo` (la forma) e `proposto` (da `script.fn_stato_proposto_id`) | `GeoRepository.list_stati_lookup` |
| i due smoke scrivono l'indirizzo nella forma che decide lo stato, coi campi dell'helper `dbops.fn_pgtap_indirizzo_libero_forma` e lo stato proposto (non più `codice_iso2 = 'IT'`, che non è univoco) | `smoke-indirizzi-documento-catena.py`, `smoke-fattura-indirizzi-snapshot.py` |
| il form dell'indirizzo libero in due forme dal flag dello stato scelto: comune e CAP (il blocco del form normalizzato, uno solo) oppure località obbligatoria, codice postale, regione; sotto-località in tutte e due; lo stato proposto preselezionato; validazione e payload in un modulo solo (`indirizzoLibero.js`), che non manda i campi dell'altra forma | `IndirizzoSoggettoForm.vue`, `useIndirizzoSoggettoForm`, `useIndirizzoMultiTipo` |
| i ripieghi dei cinque codici nuovi | `error_messages_fallback.py` |

Prove: unitari backend di `anagrafiche` 577, frontend 897 (spec nuovo `indirizzoLibero.spec.js`), lint, guard,
mypy. ✅ **Dopo l'apply (2026-10-18):** policy dei codici rigenerata (i cinque codici nuovi, nessun altro); suite
backend completa sul DB vero **6716 verdi**, `test_creazioni_dalle_madri_db` 10/10 (forma estera del soggetto, il
guard col campo `locality`, la tendina e lo stato proposto); `smoke-indirizzi-documento-catena` verde.
`smoke-fattura-indirizzi-snapshot` si ferma prima dell'indirizzo, ma **non** per mancanza di materia: su dbdev le
attività fatturabili ci sono (63 sull'emittente 32, 2026-10-18). Lo smoke apre il contesto con
`config.user_emittenti_fiscali LIMIT 1`, senza ordine: da quando ci sono gli utenti `dev.*` pesca `dev.lettura`, che
vede solo l'emittente di prova (vuoto), e la RLS gli dà zero righe. Stesso frammento in dieci smoke Python: vedi la
revisione qui sotto. La sua `INSERT` riscritta è provata a parte, in transazione annullata, e passa il guard.

**Revisione prima del commit (sessione BE, 2026-10-18).** Corretti:

* il form non indovina la forma: uno stato scelto la cui riga la tendina non porta (non ancora caricata,
  o fallita) ferma la validazione sullo stato, invece di chiedere la località a un indirizzo italiano
  (`validaLibero`, spec 4);
* `formaCatalogo` esportato dal composable e mai letto (il componente ha la sua): tolto;
* la tendina e il test 10 chiedono lo stato proposto con lo stesso `p_chi` (`CHI_STATI_LOOKUP`): finché
  vale R-BE-13 quel valore pesa sull'override per funzione, e il test confrontava due chiamate diverse;
* i ripieghi dei codici nuovi in ordine, e il commento di `E_INDIRIZZO_DOC_NON_DEL_CLIENTE` di nuovo sopra
  la sua voce.

* ✅ regola del 2 (ok di Tid, 2026-10-18): l'`INSERT` dell'indirizzo libero di ruolo, scritta tre volte in
  due smoke, è il BB degli smoke `scripts/tests/_smoke_indirizzo.py` (`crea_indirizzo_libero_ruolo`, sul
  modello di `_smoke_commessa.py`); le tre copie ritirate;
* `smoke-indirizzi-documento-catena` si **costruisce** il cliente (`dbops.fn_pgtap_crea_cliente_ba`, due
  volte per l'altra istanza) invece di prendere il primo BA di dbdev e cancellarne gli indirizzi: un
  contratto annullato che li usava lo fermava col lock delle righe (`E_DOC_*` fuori bozza), cioè l'esito
  dipendeva dai dati. Rieseguito: 1-6 verdi, nessuno skip, niente resta sul DB.

* ✅ regola del 2 (ok di Tid, 2026-10-18): il **contesto operatore** dei dieci smoke Python (la copia
  `config.user_emittenti_fiscali LIMIT 1`) è il BB `scripts/tests/_smoke_contesto.py`:
  `apri_contesto_smoke` apre il contesto su **`dev.smoke`** (decisione di Tid: l'utente degli smoke, mai uno
  personale; il nome da `UTENTE_SMOKE` del command), e si ferma se non è di prova, super admin e con la veste
  OPERATORE; `seleziona_emittente_di_prova` sceglie l'emittente di prova (dall'etichetta, non dalla sigla) per chi
  costruisce un BA. La catena lo usa. Esito dei dieci, 2026-10-18: verdi `catena` (1-6), `fattura-indirizzi-snapshot`
  (9, prima si fermava), `fattura-contatore-note`, `fattura-scadenze`, `fattura-aggregazione-termini`,
  `ritorno-lotto-a-draft`, `fatturazione-aggregazione-righe`. Riallineati al codice lo stesso giro (erano
  rossi anche con un operatore vero, provato a parte sull'emittente 32), ora verdi:
  * `fatturazione-render-stampa` (10/10): il template della fattura si risolve per l'EMITTENTE della fattura
    (`find_template_applicabile`, come il generatore; prima `WHERE codice = 'Fattura'` e una riga qualsiasi, ma i
    template sono per emittente); le righe di primo livello si separano da quelle `row-componente` (dalla forma 3 i
    componenti stanno dentro il kit: il confronto per posizione era sfasato) e un caso nuovo, 4b, prova i
    componenti; il PDF col risolutore degli asset del generatore (`risolvi_asset`); il caso 9 su una fattura
    pre-fiscale sua, e se ha già il piano ne verifica i valori;
  * `nota-credito-resi` (16 OK, 14 e 15 saltati per materia come prima): il piano rate prima del numero, come il
    giro vero (dalla rev 2026-09-17, P-5, il guard lo chiede a ogni totale diverso da zero), e un caso nuovo, 11-bis,
    che prova la P-5 (una rata negativa uguale al totale).
  Rosso **per il contesto**: `push-termine-documento-commessa`, che prende «l'ordine più recente» e ora cade su
  `DEVA` (R-BE-14).

**R-BE-14 — al team DB: l'emittente di prova non è attrezzato per lavorare.** Gli smoke girano su `dev.smoke`
(via HTTP e in-process), e via HTTP lavorano sul suo emittente attivo, `DEVA` (41194). Il giro di baseline di Tid
del 2026-10-18 (23:08) ha **sette** non-verdi con la stessa causa, nessuno per un difetto di codice:

| Manca a `DEVA` | Codice | Smoke |
| --- | --- | --- |
| il registro della fattura (tipo 1, natura 1) | `E_CONFIG_MANCANTE` «registro non risolto» | `push-termine-documento-commessa` |
| il template di default dei preventivi (sorgente 2) | `E_DOCUMENTI_NOT_FOUND` | `preventivi` (SENZA_MATERIA), `preventivi-smistamento-ordine`, `pratica-preventivi-bivio` |
| il template di default dei contratti (sorgente 4) | `E_DOCUMENTI_NOT_FOUND` | `listini-v5` (SENZA_MATERIA), `contratti-addebito-standard` |
| il template di default delle bolle | `E_DOCUMENTI_NOT_FOUND` | `resi-vendita` (non conclusivo, dopo il carico: vedi sotto) |
| ~~la giacenza nel magazzino `DEVA-MAG`~~ | `E_MAG_GIACENZA_INSUFFICIENTE` | `resi-vendita`: ✅ sistemato nello smoke (2026-10-18) |

Verificato: `vendite.fn_get_registro_id(1, NULL, NULL, <sr di DEVA>)` solleva, sull'emittente 32 risponde; i template
sono per emittente (`uq_template_documenti_emittente_sorgente_codice`) e `DEVA` non ne ha.

Proposta, in due pezzi diversi:
* **configurazione** (registri, template di default per sorgente): è ciò senza cui un emittente non lavora, quindi
  la deve avere ogni emittente che nasce — da valutare se è della madre `fn_crea_emittente_fiscale` (e allora vale
  anche per gli emittenti veri) o del verbo del provisioning; un pgTAP lo prova costruendo preventivo, contratto e
  fattura su un emittente appena nato;
* **giacenza**: non è configurazione, è materia dello smoke. ✅ (2026-10-18) `resi-vendita` si carica la merce che
  spedisce: una rettifica di magazzino sul magazzino del DDT (testata, riga `qta_delta`, CONFIRM, registra),
  `carica_merce_ddt` nello smoke (prima occorrenza: resta lì). Rieseguito: il carico passa (11 OK), poi lo smoke
  si dichiara non conclusivo sul template delle bolle di `DEVA`, cioè su R-BE-14.

➡️ **Dove va ciascun pezzo** (team DB, 2026-10-19):

* **registri**: risposta e consegna nel §6.14, ✅ applicati su dbdev il 2026-10-18 (23:35). Lo smoke
  `push-termine-documento-commessa` deve tornare a fatturare su `DEVA`: da confermare al prossimo giro di smoke;
* **template di default**: non si apre una sede nuova. È il difetto di
  [brief-db-modelli-documento-standard](brief-db-modelli-documento-standard.md) (un emittente nasce senza
  modelli), che ha già la sua decisione aperta (D-1 … D-3 di Tid, §5) e la ricaduta sugli smoke (§7). I sei
  smoke della tabella che si fermano su `E_DOCUMENTI_NOT_FOUND` aspettano quel brief;
* **giacenza**: ✅ nello smoke, come sopra.

⚠️ Finché il brief dei modelli standard non è fatto, `scripts/smoke-baseline.sh --update` non va lanciato:
registrerebbe in baseline come «noti» i rossi dell'emittente di prova (sei, se il registro ha chiuso il settimo).

**R-BE-13 — al team DB: l'override per utente dello stato proposto non scatta.** `script.fn_stato_proposto_id`
chiama `fn_get_parameter_full('STATO_PROPOSTO_ISO2', NULL, NULL, NULL, session_key, p_chi)`: l'utente
(`p_django_user_id`) è sempre NULL, e `p_chi` finisce nel posto della **funzione** (`p_function_name`). Così vale
l'override per sessione e per nome di funzione, non quello per utente o per gruppo che la pagina manual promette
(«un utente che lavora con clienti tedeschi può avere DE»). Proposta: l'utente dalla GUC `app.current_user_id`
(e i suoi gruppi), come gli altri lettori dei parametri; `p_chi` resta per il contesto dell'errore. Il backend
legge già da quel lettore (la tendina degli stati), quindi corretto il DB vale anche per il form.

### 6.13 Risposta del team DB a R-BE-13: lo stato proposto ignora l'utente (2026-10-18)

**La segnalazione** è nel §6.12 (R-BE-13), arrivata prima in chat. Il lettore BE è
`GeoRepository.list_stati_lookup` (la tendina degli stati), che chiama `fn_stato_proposto_id` con
`p_chi = CHI_STATI_LOOKUP`: passa dal lettore del DB, quindi la correzione vale anche per il form.

**Ricognizione del team DB (2026-10-18).**

* **Il difetto è vero.** `20261018-83` chiama `script.fn_get_parameter_full('STATO_PROPOSTO_ISO2', NULL, NULL,
  NULL::integer[], current_setting('app.session_key', true), p_chi)`. Dei sette livelli della cascata (utente,
  categoria cliente, gruppo, emittente, sessione, funzione, default) restano vivi solo sessione, funzione e
  default: **utente, gruppo ed emittente sono spenti**, non solo l'utente.
* **Metà della segnalazione non è un difetto.** `p_chi` nel posto di `p_function_name` è voluto: è il livello
  «function» della cascata (un override per il trigger o la funzione che chiede), detto nel commento e nella
  COMMENT. Resta così (D-13a, sotto): la proposta del BE di usarlo solo per il contesto dell'errore non è
  accolta. Conseguenza da sapere: un override per funzione su `anagrafiche.stati_lookup` vale per la
  tendina e non per i trigger normalize, che chiedono col loro nome; è il senso di quel livello.
* **Perché solo il DB.** Quando legge un parametro, il backend passa lui utente, gruppi ed emittente
  (`ParameterRepository._SQL_RESOLVE`). I trigger normalize, che sono i lettori principali di
  `fn_stato_proposto_id`, non ricevono nulla: il contesto lo devono ricavare dalla sessione. Nel DB oggi
  **nessuno** lo fa: `fn_get_default_by_param`, l'unico altro lettore della cascata lato DB, passava gli stessi
  NULL ed è stata ritirata con `-93`.
* **Da dove si ricava il contesto:**
  * **utente**: `app.current_user_id`, che contiene `auth_user.id`, cioè lo stesso id di
    `parameter_overrides.django_user_id` (`jwt_audit_authentication.py`, `JWT_IDENTITY_GUCS`). Vuota nei job,
    nel provisioning e nelle sessioni senza utente: lì il livello salta da solo, come oggi;
  * **gruppi**: `django.auth_user_groups` dell'utente. Si possono leggere solo da `plpgsql`, mai con `%TYPE`
    sulle colonne di `django` (precedente: `fn_crea_operatore_v2`). In CI e su un'installazione nuova la
    tabella non esiste quando gira Liquibase: la lettura passa da `to_regclass` e, se la tabella manca, il
    livello gruppo resta spento. Qui è giusto non fermarsi (fail-open), perché lo stato proposto è una
    proposta e non apre nessun accesso;
  * **emittente**: `app.current_emittente_id`, cioè l'emittente attivo scelto nel token. Vuota quando non c'è
    una scelta: il livello salta;
  * **categoria cliente**: non fa parte del contesto di sessione (dipende dal BA del documento), resta NULL per
    natura.

**Proposta.** Leggere un parametro con la cascata **del contesto della sessione** è un concetto generale, non
dello stato proposto: si scrive come building block, e `fn_stato_proposto_id` è il suo primo lettore.

* **BB nuovo `script.fn_get_parameter_di_sessione(p_code text, p_chi text DEFAULT NULL)`**, `plpgsql`,
  `STABLE`, `SECURITY INVOKER`. Ricava utente, gruppi, emittente e session key come sopra e chiama
  `fn_get_parameter_full` con `p_chi` come funzione. Ha gli stessi errori di `fn_get_parameter_full`, nessuna
  validazione del valore: quella resta al lettore specifico.
* **`fn_stato_proposto_id`** chiama il BB al posto di `fn_get_parameter_full`; la validazione (E_CONFIG_MANCANTE,
  E_DEFAULT_ERRATO, E_STATO_ISO2_AMBIGUO) non cambia.
* **Manual**: `fn_stato_proposto_id.md` dice quali livelli valgono e da dove arrivano; manual nuova del BB.
* **pgTAP**: un override utente a `DE`, letto dal trigger normalize di un indirizzo, propone DE a quell'utente
  e IT a un altro. Poi il gruppo (nel mondo con `django.auth_user_groups`; nel mondo CI il livello deve
  risultare spento), l'emittente attivo, e una sessione senza utente che legge il default.

**Decisioni di Tid (2026-10-18): accolta la proposta, col via allo sviluppo.**

* **D-13a** ✅ BB generale, `fn_stato_proposto_id` è il suo primo lettore.
* **D-13b** ✅ tutti e tre i livelli: utente, gruppo, emittente.

**Fatto (team DB, 2026-10-18), da applicare:**

| ChangeSet | Che cosa |
| --- | --- |
| `20_code/script/20261019-05-create-fn-get-parameter-di-sessione` | il BB `script.fn_get_parameter_di_sessione(p_code, p_chi)`: utente da `app.current_user_id`, gruppi da `django.auth_user_groups` (cercata per OID nel catalogo, letta solo se esiste e il ruolo ha `USAGE` + `SELECT`), emittente da `app.current_emittente_id`, session key da `app.session_key`, funzione da `p_chi` |
| `20_code/script/20261019-06-update-fn-stato-proposto-id-contesto-di-sessione` | `fn_stato_proposto_id` legge dal BB; corpo, firma e validazione del `-83` invariati (md5 del corpo del `-83` = `prosrc` vivo su dbdev e sullo scratch, `a943999f…`) |

* **pgTAP nuovo** `db/pgtap/script/test-fn-get-parameter-di-sessione-v1.sql` (plan 15): ogni livello costruito
  (gli override di oggi si cancellano nella transazione), più il percorso del BE: override utente a `DE` → il
  normalize di un indirizzo senza stato scrive la Germania (test 6).
* **Doc**: manual nuova `script/manual/fn_get_parameter_di_sessione.md`; `fn_stato_proposto_id.md` (i livelli
  e da dove arrivano); rimando da `fn_get_parameter_full.md`; la guida `gestione-degli-indirizzi` (R8: «per
  utente, gruppo, azienda attiva o sessione»).

**Prova prima dell'apply** (scratch `zeroerp_ruoli`, come `zeroerp_owner`, SQL estratto dagli YAML dentro
`BEGIN … ROLLBACK`, `ON_ERROR_STOP`; dopo ogni corsa lo scratch è risultato intatto: BB assente, md5 di
`fn_stato_proposto_id` invariato, nessun gruppo pgTAP rimasto):

* pgTAP nuovo con i due changeSet: **15/15**;
* controprova col solo `-05` (il `fn_stato_proposto_id` di oggi): **test 5 rosso**, cioè il test riconosce il
  difetto R-BE-13;
* `anagrafiche/test-indirizzo-libero-due-forme-v1` con i due changeSet: **28/28**;
* `plpgsql_check`: `-05` pulito; `-06` solo i due warning «STABLE ma VOLATILE» su
  `fn_log_and_raise_error`, che erano già nel `-83`;
* il ramo «gruppi non leggibili»: con `django.auth_user_groups` rinominata nella transazione il BB risponde il
  default, senza errore. Il ramo «ruolo senza privilegio» (`zeroerp_job`: niente `USAGE` su `django`,
  verificato) non si prova da owner, che non è membro di `zeroerp_job`: passa dallo stesso controllo per OID
  (`has_schema_privilege`/`has_table_privilege` su OID non sollevano). Il pgTAP lo dichiara in testa.

**Applicato** (Tid, 2026-10-18 22:45, dbdev): `20261019-05` e `-06`, pgTAP verdi. Da committare.
Ricaduta BE: nessuna da scrivere; alla sessione BE va riportato che il posto di `p_chi` era voluto.

**Trovati strada facendo (non toccati, fuori perimetro):**

* `fn_get_parameter_full` passa i due segnaposto di `E_ERRORE_PARAMETRI_TABELLA` invertiti: il messaggio dice
  «Parametro: config.parameters non trovato nella tabella: `PGTAP_…`». Il test 15 asserisce solo il codice del
  parametro, per non pinnare il difetto.
* la manual `script/manual/fn_get_parameter_full.md` descrive ancora i due overload, ritirati il 2026-07-27.

**Dopo il DB, BE:** niente da cambiare. La tendina legge da `fn_stato_proposto_id`, che ora sente utente,
gruppo ed emittente attivo dalle GUC che il backend già scrive (`JwtAuditAuthentication`): tendina e
trigger propongono lo stesso stato allo stesso utente, salvo un override per funzione voluto.

### 6.14 Risposta del team DB a R-BE-14: un emittente nasce senza registro delle fatture (2026-10-18)

> Questo paragrafo risponde al pezzo **registri** di R-BE-14. I template di default stanno in
> [brief-db-modelli-documento-standard](brief-db-modelli-documento-standard.md) (§6.12, «Dove va ciascun pezzo»).

**La richiesta** è nel §6.12 (R-BE-14): su `DEVA` `vendite.fn_get_registro_id(1, NULL, NULL, <sr>)` solleva
`E_CONFIG_MANCANTE` «registro non risolto per tipo_doc 1 e natura 1». Il BE propone che il verbo del
provisioning, oppure la madre dell'emittente, lasci l'emittente di prova completo per fatturare.

**Il caso, sul modello.** Il difetto non è dell'emittente di prova: **nessun emittente nasce col registro delle
fatture**, quello di un'installazione nuova compreso. È lo stesso difetto che
[brief-db-modelli-documento-standard](brief-db-modelli-documento-standard.md) §2 descrive per i modelli («un
emittente è un'identità completa solo se può emettere»), su un'altra configurazione. Quel brief chiede al team
DB il censimento di ciò che serve per emettere: i registri sono questa voce.

**Ricognizione (struttura, doc `dbzero`, 2026-10-18).**

| Pezzo | Com'è | Che cosa c'entra |
| --- | --- | --- |
| `vendite.fn_get_registro_id` → `fn_lookup_registro_id` | cerca in `tipi_doc_fiscale_registri` per (tipo documento, natura), registro dell'emittente con `=` puro, utility esatta o NULL; nessun ripiego (dal 30-08 il registro «di nessuno» non esiste) | senza una riga per la coppia, l'emittente non fattura |
| `vendite.fn_provision_registri` (primitiva) + `trg_emittenti_fiscali_z90_provision_registri_ins_upd` | all'INSERT (e alla riaccensione) di un emittente crea un registro per ogni famiglia attiva, **tranne `FATTURA`**, esclusa con un letterale: «il suo registro dipende da (tipo documento, natura)» | il meccanismo per far nascere i registri con l'emittente **c'è già**; manca la fattura |
| `vendite.fn_provision_registri_famiglia` | una famiglia nuova crea il suo registro per ogni emittente | il gemello per le coppie nuove esiste per le famiglie, non per tipo documento e natura |
| `vendite.tipi_doc_fiscale_registri` | UNIQUE su (tipo, natura, registro); **nessun vincolo per emittente** | due registri dello stesso emittente sulla stessa coppia sono ammessi, e il lookup sceglie il primo per `id` (`ORDER BY …, r.id LIMIT 1`): un'ambiguità del modello risolta da un id |
| `config.tipi_doc_fiscale`, `config.nature_doc_fiscale` | due cataloghi: il tipo documento ha semantica aperta per azienda (front/back office è un esempio), le nature sono fattura, nota di credito, nota di debito | la riga che serve è per ogni coppia (tipo attivo × natura attiva) |
| `vendite.registri_fatturazione` | default `famiglia_documento = 'FATTURA'`, `politica_data_documento = 'OGGI'`, `limite_emissione_giorni` NULL = il limite di default (non «nessun limite»); `famiglie_documento.FATTURA` porta `lunghezza_default = 7`, `prefisso_default` NULL | lo standard si costruisce coi default del catalogo, come le altre famiglie |
| `fn_provisiona_dati_di_sviluppo` | non tocca i registri | il verbo non è la sede: il difetto c'è anche in produzione |

Fatto datato, non motivo (2026-10-18, dbdev): l'emittente 32, configurato a mano, ha un registro per tipo
documento sulla natura fattura e uno per le note di credito, condiviso dai due tipi; nessuna riga per la nota
di debito.

**Proposta.**

1. **Il registro delle fatture nasce con l'emittente**, dallo stesso meccanismo degli altri: la primitiva
   `fn_provision_registri` smette di escludere `FATTURA` e, per l'emittente, crea **un registro delle fatture
   standard** (codice e descrizione con la regola della primitiva, i default della famiglia `FATTURA`) e una
   riga di `tipi_doc_fiscale_registri` per **ogni coppia mancante** (tipo documento attivo × natura attiva) che
   punta a quel registro. L'operatore lo divide poi dal CRUD dei registri, come fa oggi.
2. **Le coppie nuove**: quando nasce (o si riaccende) un tipo documento o una natura, la coppia mancante di ogni
   emittente si collega al suo registro standard, come `fn_provision_registri_famiglia` fa per le famiglie. Un
   emittente configurato a mano senza registro standard riceve il registro standard solo per le coppie che non
   ha: oggi l'emittente 32 lo riceverebbe per la nota di debito.
3. **Gli emittenti di oggi**: un changeSet chiama la primitiva per tutti gli emittenti attivi (le coppie
   mancanti, idempotente): copre `DEVA` e gli altri.
4. **L'ambiguità del collegamento**: un guard su `tipi_doc_fiscale_registri` che rifiuta una seconda riga dello
   stesso emittente sulla stessa coppia (e utility), con un codice suo. Il lookup smette di decidere per `id`.

**Decisioni di Tid (2026-10-18): tutte come da proposta.** Il via allo sviluppo è dato (2026-10-18).

* **D-14a** ✅ il registro delle fatture nasce **con l'emittente**, anche in produzione; non nel verbo di
  sviluppo.
* **D-14b** ✅ **un registro** standard per tutte le coppie; il CRUD dei registri lo divide quando serve.
* **D-14c** ✅ le coppie mancanti di un emittente configurato a mano si collegano al registro standard.
* **D-14d** ✅ il guard sull'ambiguità (punto 4) entra in questo giro.

**Da censire nello sviluppo** (regole già note):

* i 56 pgTAP che usano `script.fn_pgtap_registro_fattura`: il builder restituisce il primo registro `FATTURA`
  dell'emittente. Su un emittente costruito dalla fixture troverebbe quello standard, col limite di emissione
  **di default**, invece di crearne uno suo con `limite_emissione_giorni = 9999`; le fixture che datano i
  documenti nel passato cadrebbero sul presidio del limite. Il builder diventa un involucro che restituisce
  il registro standard e ne apre il limite, oppure resta com'è e cerca solo il suo: da decidere sul codice;
* i pgTAP che contano i registri creati dalla primitiva (`vendite/test-registri-motore-trasloco-v1`,
  `test-famiglie-documento-crud-v1`, `test-numero-prefisso-registro-v1`) e quelli che asseriscono «registro
  non risolto» su un emittente nuovo;
* il COMMENT e la manual della primitiva, che dichiarano l'esclusione della fattura.

**Decisione di Tid durante lo sviluppo (2026-10-18): la nota di debito va sul registro standard.** Fino ad
allora era volutamente senza registro («nessuno ha deciso su quale registro numerarla»,
brief-design-note-credito-resi §20.5 punto 4, e la manual di `tipi_doc_fiscale_registri`). D-14b e D-14c,
applicate alla lettera, la chiudevano; Tid conferma. Per un emittente nuovo è numerata con le fatture; agli
emittenti già configurati a mano (su dbdev EMITEST e PGTAPEF202) lo standard nasce apposta.

**Fatto (team DB, 2026-10-18), da applicare:**

| ChangeSet | Che cosa |
| --- | --- |
| `20_code/vendite/20261019-07-create-fn-coppie-fattura-scoperte` | lettore `vendite.fn_coppie_fattura_scoperte(emittente)`: le coppie (tipo attivo × natura attiva) che `fn_lookup_registro_id` non risolve con utility NULL, per gli emittenti attivi. Chiama il lookup, non lo riscrive |
| `20_code/vendite/20261019-08-update-fn-provision-registri-fattura-standard` | la primitiva non esclude più la FATTURA: **un solo `INSERT`** per tutte le famiglie (il registro standard `FAT-<sr>` nasce con la regola degli altri), poi i collegamenti delle coppie scoperte allo standard acceso. La regola del codice esce in `vendite.fn_codice_registro_provisionato` (serviva tre volte). Firma, DEFINER, `search_path` invariati; corpo di partenza = vivo = doc auto-generata |
| `20_code/vendite/20261019-09-create-trgfn-coppie-fattura-provision-registri` | trigger su `config.tipi_doc_fiscale` e `config.nature_doc_fiscale`: all'INSERT attivo e al passaggio a attivo (non a ogni `UPDATE OF attivo`: il loader dei CSV riscrive la colonna) chiama `fn_provision_registri_famiglia('FATTURA')` |
| `20_code/vendite/20261019-10-create-guard-coppia-registro-fattura-unica` | lettore `vendite.fn_registro_che_copre_coppia` e due guard (sul collegamento; sul registro, `UPDATE OF` emittente e utility), lock consultivo per emittente, codice nuovo `E_REGISTRO_COPPIA_GIA_COPERTA` (CONFLITTO_STATO, messaggio 1367, in coda ai due CSV) |
| `80_data/changelog/20261019-11-seed-registro-fattura-standard-per-emittente` | la sistemazione degli emittenti esistenti: `fn_provision_registri_famiglia('FATTURA')`, idempotente, `runOnChange` come `20260915-34` |
| `20_code/script/20261019-12-update-fn-pgtap-registro-fattura-ignora-standard` | il builder pgTAP salta lo standard: le 56 fixture tengono il loro registro col limite a 9999; sugli emittenti di oggi restituisce lo stesso registro di prima |

* **pgTAP nuovo** `db/pgtap/vendite/test-registro-fattura-nasce-con-emittente-v1.sql` (plan 16): emittente che
  nasce (standard, nessuna coppia scoperta, `fn_get_registro_id` risolve ogni coppia, registri delle famiglie
  come prima), natura nuova e riaccesa, `UPDATE` che non accende, emittente configurato a mano, guard (stessa
  utility rifiutato, utility diversa ammessa, registro portato a «tutte» rifiutato, no-op), builder, standard
  spento, idempotenza.
* **pgTAP adeguato** `vendite/test-registri-motore-trasloco-v1`: la fixture spegneva **tutti** i registri del
  terzo emittente, ora c'è anche lo standard con i suoi collegamenti, che `trgfn_prevent_deactivate_if_children`
  non lascia spegnere. Spegne solo il DDT, che è quello che i test 6 e 7 chiedono.
* **Doc**: manual nuova `vendite/manual/fn_coppie_fattura_scoperte.md`; rev in `fn_provision_registri.md`,
  `fn_provision_registri_emittente.md` (il «non crea registri per le fatture» superato), `tipi_doc_fiscale_registri.md`
  (provisioning, guard, nota di debito).

**Prova prima dell'apply** (scratch `zeroerp_ruoli`, ricostruito da zero: nessun emittente, nessun registro;
come `zeroerp_owner`, SQL estratto dai sei YAML dentro `BEGIN … ROLLBACK`, il codice d'errore inserito nella
transazione; dopo ogni corsa scratch intatto: md5 delle funzioni, zero registri, funzioni nuove assenti):

* pgTAP nuovo: **16/16**. Controprova senza il `-10`: rossi il 10 e il 12;
* regressione, ogni file senza e con l'estratto, esiti **identici**: `test-famiglie-documento-crud-v1` 28/28,
  `test-registro-documento-previsto-v1` 11/11, `test-registri-progressivi` 14/14, `test-limite-emissione-v1`
  19/19, `script/test-fn-check-registro-disattivabile-v1` 9/9, `test-registri-motore-trasloco-v1` 9/9 (dopo
  l'adeguamento; prima della correzione 0, fermo sullo spegnimento). Rossi uguali nei due casi, quindi dello
  scratch e non di questo giro: `test-numero-prefisso-registro-v1` (3 ko), `test-registri-per-emittente-v1`,
  `test-fatture-guard-registro-emittente`, `test-fattura-guard-uscita-draft-v1`,
  `test-snapshot-intestazione-fattura-v1`;
* `plpgsql_check` sulle sette funzioni nuove o cambiate (tre trigger con la loro tabella): **nessun errore né
  warning**;
* **dbdev, come owner, in transazione annullata** (fatto datato, 2026-10-18): la sistemazione crea 4 registri
  standard e 16 collegamenti; DEVA e DEVB ricevono le sei coppie, EMITEST e PGTAPEF202 la sola nota di debito;
  nessuna coppia resta scoperta; DEVA risolve tipo 1 natura 1. Dopo, dbdev identico (26 registri, 8
  collegamenti, md5 invariati).

**Per Tid:** apply di `20261019-07` … `-12` e dei due CSV dei codici (`codici_errore.csv`,
`messaggi_errore.csv`); pgTAP `vendite/test-registro-fattura-nasce-con-emittente-v1`,
`vendite/test-registri-motore-trasloco-v1`, i file della regressione qui sopra, chi usa
`script.fn_pgtap_registro_fattura`, e i presidi trasversali `dbops/test-riferimenti-morti-v1` (sette funzioni
plpgsql nuove o cambiate) e `script/test-catalogo-messaggi-errore-completo` (codice nuovo). Da committare.
⚠️ Nell'albero ci sono modifiche non di questo giro a `config/sorgenti.csv` e `config/tipi_entita.csv`.

✅ **Applicato** da Tid su dbdev il 2026-10-18 alle 23:35 (`20261019-07` … `-12` e i due CSV dei codici),
**pgTAP verdi**. Da committare.

**Collaudo, rosso non di R-BE-14 (2026-10-18):** `vendite/test-numero-prefisso-registro-v1` test 4 su dbdev,
«ORDINE/ORD-134419/2026: contatore 9 < max 20260000009». Il contatore è giusto (nove ordini di DEVA dagli
smoke di `dev.smoke`, ORD2026-0000001 … -0000009): il test teneva **tutte** le cifre del numero, e su un
registro con `anno_nel_numero` contava anche l'anno. Corretto il test: toglie dal numero prefisso, anno con
trattino e suffisso che il registro dichiara, poi tiene le cifre; un numero senza il prefisso (il pregresso)
si legge come prima. Provato come `SELECT` in sola lettura su dbdev: i cinque registri con documenti risultano
allineati (ORD-134419 9 = 9; gli altri quattro con gli stessi valori di prima). ✅ Rilanciato da Tid: verde.

**Dopo il DB, BE (richieste):**

* **R-DB-14a** — il codice nuovo `E_REGISTRO_COPPIA_GIA_COPERTA` (CONFLITTO_STATO, 409): ripiego in
  `error_messages_fallback.py` e rigenerazione di `error_policies_generated.py`. Contesto: `campo`
  (`registro_id` sul collegamento, `utility_id` o `emittente_soggetto_ruolo_id` sul registro),
  `registro_occupante_id`;
* niente nel verbo di sviluppo; lo smoke `push-termine-documento-commessa` torna a fatturare su `DEVA` dopo
  l'apply (la sistemazione `-11` copre gli emittenti già creati).

✅ **Fatto (sessione BE, 2026-10-19):** R-DB-14a. Ripiego senza segnaposto in `error_messages_fallback.py`;
`error_policies_generated.py` rigenerato (una voce in più, `CONFLITTO_STATO`, nessuna classe spostata; `--check`
pulito). Il campo del contesto arriva al client dalla traduzione generica: nessuna mappa per codice. Da committare.

### 6.15 Risposta del team DB a R-BE-11: il profilo SUPER_ADMIN si risolve in una sede (2026-10-18)

**La richiesta** è nel §6.10 (R-BE-11, regola del 2, ok Tid 2026-10-18): la regola «per `tipo`, fra i profili
**attivi**, esattamente uno, altrimenti `E_CONFIG_MANCANTE`» era scritta due volte, in
`anagrafiche.fn_crea_risorsa_umana_v2` (dal `20260923-10`) e in `AmmSoftwareRepository._set_super_admin_binding`.
Via allo sviluppo di Tid: 2026-10-18.

**Censimento (2026-10-18).** Nel DB la regola la scriveva solo la madre della risorsa umana: il verbo di
sviluppo le passa il flag; i guard «ultimo super admin» e `script.fn_is_super_admin*` usano il tipo per
**controllare** un utente, non per scegliere un profilo. Nel backend il tipo compare anche in
`count_admin_attivi`, che conta i super admin attivi: è un'altra regola, fuori da R-BE-11 (vedi sotto).

**Fatto (team DB, 2026-10-18), da applicare:**

| ChangeSet | Che cosa |
| --- | --- |
| `20_code/config/20261019-16-create-fn-profilo-super-admin-id` | lettore `config.fn_profilo_super_admin_id()`: l'id dell'unico profilo attivo di tipo SUPER_ADMIN, o `E_CONFIG_MANCANTE` con il numero dei profili trovati; `GRANT` all'app |
| `20_code/anagrafiche/20261019-17-update-fn-crea-risorsa-umana-v2-profilo-dal-lettore` | la madre chiama il lettore al posto della sua ricerca, nello stesso punto (prima di ogni scrittura); la firma si ancora con `%TYPE` (ogni ancora risolve al tipo di prima: una versione sola, stessa firma, verificato). Corpo di partenza `20261018-45` = vivo (md5 `e21d2f29…`). ⚠️ Nessuna `preCondition` sul lettore: `20_code/anagrafiche` gira prima di `20_code/config` |

* **pgTAP nuovo** `db/pgtap/config/test-fn-profilo-super-admin-id-v1.sql` (plan 5): firma, STABLE e INVOKER,
  un secondo profilo SUPER_ADMIN spento non conta, due attivi → `E_CONFIG_MANCANTE` «trovati 2», la madre si
  ferma sullo stesso codice prima di scrivere. Non provato: zero profili attivi (il profilo del seed non si
  spegne finché ha legami); è lo stesso ramo del caso dei due.
* **Doc**: manual nuova `config/manual/fn_profilo_super_admin_id.md`; `anagrafiche/manual/fn_crea_risorsa_umana_v2.md`
  corretta anche nei passaggi rimasti al profilo cablato 9100 e all'`INSERT` del legame (stantii da due
  revisioni).

**Prova prima dell'apply** (scratch `zeroerp_ruoli`, come `zeroerp_owner`, SQL estratto dai due YAML dentro
`BEGIN … ROLLBACK`; scratch intatto dopo ogni corsa):

* pgTAP nuovo: **5/5**; senza il lettore il file si ferma al test 1;
* nella transazione: la madre ha **una sola versione**, stessa firma e stesso ritorno, chiama il lettore, la
  ricerca sua non c'è più;
* `plpgsql_check`: madre pulita; il lettore ha il solo warning «STABLE ma VOLATILE» sul
  `fn_log_and_raise_error`, come `script.fn_stato_proposto_id`;
* regressione, senza e con l'estratto, esiti **identici**: `config/test-fn-scrivi-profilo-accesso-v1` 15/15,
  `test-credenziale-blocco-admin-v1` 16/16, `test-totp-obbligo-v1` 15/15,
  `anagrafiche/test-istanza-ba-gestore-globale-v1` 8/8, `test-fn-provisiona-dati-di-sviluppo-v1` 20/20,
  `config/test-credenziali-porta-v1` 10 ok e 3 ko in tutti e due i casi (dello scratch, non di questo giro).

✅ **Applicato** da Tid su dbdev (2026-10-18 23:59, `20261019-16` e `-17`), pgTAP verdi; committato il 2026-10-19.

**Dopo il DB, BE (richiesta):**

* **R-DB-11a** — `AmmSoftwareRepository._set_super_admin_binding` chiama `config.fn_profilo_super_admin_id()` e
  ritira la sua query (righe ~391-409): l'errore e il messaggio sono gli stessi (`E_CONFIG_MANCANTE`, «trovati
  N»). Il presidio BE c'è già: `test_operatore_altre_vesti_db` 3b.

✅ **Fatto (sessione BE, 2026-10-19):** R-DB-11a. `_set_super_admin_binding` chiede il profilo a
`config.fn_profilo_super_admin_id()`, in tutti e due i rami (legare e slegare, R-DB-16a), prima di cercare la veste:
una configurazione rotta si dice anche a chi non ha una veste operatore. L'errore ora sale dal DB come
`DatabaseError` e lo traduce il middleware (era un `ServiceError` del backend): il test 3b lo legge così.

**Trovato (chiuso il 2026-10-19: ritirato, era codice morto, §6.16 revisione critica):** `AmmSoftwareRepository.count_admin_attivi` conta i super admin attivi con
una query sua; nel DB c'è `script.fn_check_almeno_un_super_admin_attivo`. Se dicono la stessa cosa sono due
copie (regola del 2); va confrontato il significato, non il testo.

### 6.16 Risposta del team DB a R-BE-6, R-BE-7, R-BE-12: indirizzi e legami dalle madri (2026-10-19)

**Le richieste** sono nel §6.10; le decisioni D-16a … D-16c di Tid (2026-10-19), col via allo sviluppo, sono
scritte lì. Progressivi da Tid: dal `20261019-33`.

**Ricognizione (corpo vivo, 2026-10-19).**

* **indirizzi:** per il soggetto c'era solo la singolare (`fn_crea_indirizzo_soggetto`, l'id), per il ruolo solo la
  plurale (`fn_crea_indirizzi_ruolo`, un conteggio, senza istanza). La regola «copia il primo per gli obbligatori
  che mancano» stava nella plurale del ruolo e nella procedura del backend del soggetto, con due matrici
  diverse (`config.tipi_ruolo_tipi_indirizzo`, `config.tipi_soggetto_dettaglio_tipi_indirizzo`);
* **un difetto della plurale del ruolo:** saltava un tipo se il ruolo ne aveva **un qualsiasi** indirizzo, anche di
  un'istanza; la chiave vera è `uq_indirizzi_ruolo_tipo_no_istanza` (ruolo + tipo senza istanza): l'indirizzo del
  ruolo non nasceva;
* **legami:** `config.profili_accesso_bindings` ha tre bersagli (reparto, identità, ruolo applicativo), uno per
  riga, al più un legame per reparto e per identità; la madre c'era solo per legare un'identità. Il backend legava
  il reparto con un `UPSERT` (che sostituiva il profilo) e slegava il SUPER_ADMIN con un `DELETE`.

**Fatto (team DB, 2026-10-19), da applicare:**

| ChangeSet | Che cosa |
| --- | --- |
| `20_code/config/20261019-33-create-fn-lega-profilo-reparto` | `config.fn_lega_profilo_reparto(profilo, reparto)`, gemella di `fn_lega_profilo_identita`: idempotente sullo stesso profilo, un altro profilo lo rifiuta `uq_profili_accesso_bindings_uo` (non sostituisce: in pratica è lo stesso, il profilo di un reparto ha sempre lo stesso codice e quindi lo stesso id) |
| `20_code/config/20261019-34-create-fn-slega-profilo-identita` | `config.fn_slega_profilo_identita(profilo, identità)`: toglie il legame solo verso quel profilo, ritorna 0 o 1; l'ultimo super admin lo protegge il trigger della tabella |
| `20_code/config/20261019-35-create-fn-slega-profilo-reparto` | `config.fn_slega_profilo_reparto(profilo, reparto)`, la gemella per il reparto |
| `20_code/anagrafiche/20261019-36-create-fn-crea-indirizzo-ruolo` | la singolare del ruolo: UN indirizzo, anche di un'istanza (la legge la madre: la grammatica `fn_indirizzo_elemento` è comune al soggetto e resta senza istanza), ritorna l'id |
| `20_code/anagrafiche/20261019-37-create-fn-indirizzi-con-obbligatori` | il BB puro della copia del primo per i tipi obbligatori che mancano, comune alle due plurali (regola del 2) |
| `20_code/anagrafiche/20261019-38-update-fn-crea-indirizzi-ruolo-dalla-singolare` | la plurale del ruolo: la copia dal BB, ogni riga dalla singolare, il salto solo sugli indirizzi senza istanza. Corpo di partenza `20261018-95` = vivo (md5 `3dad0435…`), generato da script, firma e ritorno invariati |
| `20_code/anagrafiche/20261019-39-create-fn-crea-indirizzi-soggetto` | la plurale del soggetto, gemella: matrice del tipo di soggetto, copia attiva di default (`p_copia_obbligatori`, il flag `auto_clone` del backend), salto dei tipi presenti, righe dalla singolare; `E_SOGGETTO_NOT_FOUND` |

* **pgTAP nuovi:** `config/test-legami-profilo-lega-e-slega-v1.sql` (plan 11) e
  `anagrafiche/test-indirizzi-singolare-e-plurale-v1.sql` (plan 14: il BB, la singolare con l'istanza, la plurale
  che non salta più per un'istanza, la plurale del soggetto con e senza copia, dentro una finestra dei differiti).
  Non provato: l'ultimo super admin slegato (lo protegge il trigger della tabella, coi suoi test).
* **Doc:** manual nuove `anagrafiche/manual/fn_crea_indirizzo_ruolo.md`, `fn_crea_indirizzi_soggetto.md`,
  `config/manual/fn_lega_profilo_reparto.md` (le tre madri dei legami); note di revisione in
  `fn_crea_indirizzi_ruolo.md`, `fn_crea_indirizzo_soggetto.md`, `fn_lega_profilo_identita.md`.

**Prova prima dell'apply** (scratch `zeroerp_ruoli`, come `zeroerp_owner`, SQL estratto dai YAML dentro
`BEGIN … ROLLBACK`; scratch intatto dopo ogni corsa):

* pgTAP nuovi: **11/11** e **14/14**. Controprova senza il `-38`: rosso il test 8 (il salto per un'istanza);
* con i sette changeSet: **una versione** per ognuna delle sette funzioni; `plpgsql_check` **pulito** su tutte e sei
  le plpgsql;
* regressione, senza e con l'estratto degli indirizzi, esiti **identici**: `anagrafiche/test-fn-crea-indirizzi-ruolo-v1`
  18/18, `test-indirizzo-libero-due-forme-v1` 28/28, `test-fn-provisiona-dati-di-sviluppo-v1` 20/20,
  `test-fn-crea-fornitore-v1` 16/16, `test-fn-crea-cliente-v1` 25/25, `test-istanza-cliente-chain` 26/26,
  `test-crea-operatore-riusa-credenziale-v1` 20/20.

✅ **Applicato** da Tid su dbdev (2026-10-19 00:26, `20261019-33` … `-39`), pgTAP verdi; committato il 2026-10-19.

**Dopo il DB, BE (richieste):**

* **R-DB-16a — i legami di profilo dalle madri.** `AmmSoftwareRepository.put_profilo_reparto` lega con
  `config.fn_lega_profilo_reparto` al posto del suo `UPSERT`; `_set_super_admin_binding` (ramo `enabled = false`)
  slega con `config.fn_slega_profilo_identita(config.fn_profilo_super_admin_id(), <veste>)` al posto del suo
  `DELETE`. Un profilo diverso su un reparto già legato ora è un errore (`uq_profili_accesso_bindings_uo`), non una
  sostituzione: il percorso del backend non lo produce;
* **R-DB-16b — gli indirizzi dalle madri.** `SoggettiRepository.crea_indirizzo_ruolo` chiama
  `anagrafiche.fn_crea_indirizzo_ruolo(ruolo, indirizzo jsonb)` (l'istanza nella chiave `istanza_utility_id`; la
  grammatica di `indirizzo_per_madre`, forma estera e via compresa) al posto della sua INSERT; `create_soggetto`
  chiama `anagrafiche.fn_crea_indirizzi_soggetto(soggetto, indirizzi, auto_clone)` e ritira
  `_apply_auto_clone` e `_create_indirizzi_batch`. Il tipo già presente ora si **salta** (come per il ruolo),
  invece del duplicato tradotto da `create_with_dedup`.

✅ **Fatto (sessione BE, 2026-10-19), da committare:**

* **R-DB-16a.** `put_profilo_reparto` lega con `config.fn_lega_profilo_reparto` (ritirato l'`UPSERT`);
  `_set_super_admin_binding` slega con `config.fn_slega_profilo_identita` sul profilo del lettore (ritirato il
  `DELETE`, che toglieva i legami verso **ogni** profilo SUPER_ADMIN, spenti compresi). Ripetere lo slegare non è un
  errore (la madre ritorna 0).
* **R-DB-16b.** `SoggettiRepository.crea_indirizzo_ruolo(ruolo, indirizzo)` chiama
  `anagrafiche.fn_crea_indirizzo_ruolo` e rilegge la riga per id **in un'istruzione a parte** (la riga scritta
  dalla funzione non è visibile allo snapshot dell'istruzione che la chiama). La view `RuoloIndirizziView.post` non
  risolve più tipo e via: passa da `SoggettiService.create_indirizzo_ruolo`, con gli stessi pre-check dell'indirizzo
  di soggetto (`indirizzo_per_madre`) e il duplicato tradotto da `create_with_dedup`; il contratto della risposta
  (la riga) è invariato. `create_soggetto` chiama `SoggettiRepository.crea_indirizzi_soggetto` →
  `anagrafiche.fn_crea_indirizzi_soggetto(soggetto, indirizzi, auto_clone)`. Ritirati `_apply_auto_clone`,
  `_create_indirizzi_batch`, `_resolve_indirizzo_dettaglio`, `resolve_tipo_indirizzo_id` e la dipendenza del
  service da `LookupRepository`. Il FE non cambia: il drawer manda già la grammatica della madre.
* **Test.** Unitari: la suite intera verde (6287). Sul DB vero (`ZEROERP_TEST_DB_E2E=1`, dbdev, transazioni
  annullate): `test_creazioni_dalle_madri_db` 3b (singolare del ruolo: forma estera, la riga, il duplicato), 3c e
  3d (plurale del soggetto con e senza copia, guard differito che passa), `test_operatore_altre_vesti_db` 3-bis
  (slegare, due volte) e 3b adeguato; `test_profilo_reparto_secondo_fattore_db` passa dalla madre del reparto (tre
  `PUT` sullo stesso reparto: l'idempotenza). `apps.anagrafiche`, `apps.amm_software`, `apps.core` e2e verdi;
  mypy a cricchetto e ruff puliti. Worker gunicorn di dev ricaricati.
* **Catalogo BB backend**: voci di `create_indirizzi_ruolo` e di `GeoService.crea_dettaglio_indirizzo` aggiornate.
* **Revisione critica (2026-10-19, stessa sessione):** la plurale del soggetto e quella del ruolo passano da
  `create_with_dedup` (una FK o un CHECK violati dentro la madre erano un 500 `E_DATABASE`; prima della madre ogni
  indirizzo del soggetto era tradotto); `auto_clone` letto come booleano (`"false"` stringa accendeva la copia); gli
  indirizzi della creazione validati **prima** di scrivere e senza scarti silenziosi (`indirizzi_per_madre`); la
  rilettura dell'indirizzo di ruolo restituisce anche i campi della forma estera (colonne dalla whitelist
  dell'update); pre-check delle singolari in `indirizzo_singolo_per_madre`; schema OpenAPI della grammatica in
  `campi_indirizzo_madre` (cinque endpoint). ✅ Ritirato (ok di Tid) `AmmSoftwareRepository.count_admin_attivi`:
  nessun chiamante, nemmeno nei test (codice morto), e contava i super admin «attivi» dove la regola del DB
  (`script.fn_check_almeno_un_super_admin_attivo`) chiede «senza scadenza».

**Collaudo, rosso non di questo giro (2026-10-19):** `anagrafiche/test-fn-provisiona-dati-di-sviluppo-v1` test 3
su dbdev, «have 20|0, want 20|20». Il verbo è giusto: su dbdev le 20 radici di prova esistono dal command del
collaudo (2026-10-18 20:37), e rilanciato le **riallinea**. Il test pretendeva «tutte create», cioè un database
senza dati di sviluppo. Corretto il test: conta le radici già presenti prima della prima corsa e pretende il conto
esatto (create le mancanti, riallineate le presenti): su un database nuovo `20|20|0`, su dbdev `20|0|20`. Provato
sullo scratch (nessuna radice): 20/20. ✅ Rilanciato da Tid su dbdev: verde.

**Trovato, non toccato** (→ R-BE-15, §6.17): nessun controllo verifica che l'istanza di un indirizzo di ruolo sia dello stesso soggetto
del ruolo (`istanze_utilities.soggetto_id` contro `soggetti_ruoli.soggetto_id`). È una regola della tabella, che
vale anche per l'`UPDATE`: andrebbe in un guard su `anagrafiche.indirizzi`, non nella madre.

### 6.17 R-BE-15: l'istanza di un indirizzo di ruolo è di un altro soggetto (sessione BE, 2026-10-19)

**Il difetto** (trovato dal team DB in §6.16): `anagrafiche.indirizzi` lega un indirizzo a un ruolo
(`soggetto_ruolo_id`) e, facoltativamente, a un'istanza (`istanza_utility_id`). Niente verifica che l'istanza
appartenga allo **stesso soggetto** del ruolo (`istanze_utilities.soggetto_id` contro `soggetti_ruoli.soggetto_id`).
Un indirizzo può quindi stare sul ruolo di un soggetto ed essere l'indirizzo dell'istanza di un altro: la catena di
risoluzione degli indirizzi (istanza → ruolo → soggetto) restituirebbe a un soggetto l'indirizzo di un altro.

**Che cosa serve:**

* la regola vale per **ogni scrittore** e per l'`UPDATE` (cambio del ruolo o dell'istanza), non solo per le madri
  che creano: oggi scrivono la tabella `fn_crea_indirizzo_ruolo`, `fn_crea_indirizzi_ruolo` e l'`UPDATE` del backend
  (`update_indirizzo_ruolo`, whitelist con `istanza_utility_id`);
* un rifiuto con un **codice registrato**, che dica il campo (`istanza_utility_id`), così che il backend lo mostri
  sul form senza una traduzione sua;
* il pgTAP che lo provi costruendo il caso (istanza di un altro soggetto, in creazione e in modifica) e il caso
  ammesso (istanza dello stesso soggetto, nessuna istanza);
* se il dato esistente lo viola, dirlo: va deciso prima che il controllo entri.

**Ricaduta BE attesa:** ripiego del codice nuovo e policy rigenerate; nessun pre-check nel backend.

#### 6.17.1 Risposta del team DB: ricognizione e proposta (2026-10-19)

**Ricognizione (struttura, doc auto-generata e codice del BE, 2026-10-19).** La regola «il soggetto del ruolo è il
soggetto dell'istanza» vale per **ogni** riga che porta tutti e due; oggi:

| Tabella | Ruolo + istanza | La regola c'è? |
| --- | --- | --- |
| `billing_account` | NOT NULL tutti e due | ✅ `trgfn_billing_account_guard_soggetto_coerenza_istanza` (fascia `a20`, `E_BA_SOGGETTO_INCOERENTE_ISTANZA`, campo `istanza_utility_id`) |
| `clienti` | NOT NULL tutti e due | ✅ per costruzione: FK composte sul BA (`billing_account_id, istanza_utility_id` e `billing_account_id, soggetto_ruolo_id, utility_id`), colonne bloccate |
| `pratiche.pratiche` | facoltativi | ✅ regola 4 di `trgfn_pratiche_guard_contesto` (istanza del `soggetto_id` della pratica) |
| **`indirizzi`** | ruolo NOT NULL, istanza facoltativa | ❌ **R-BE-15**. Scrittori in `UPDATE`: il backend (`soggetti_repository.py`, whitelist con `istanza_utility_id`) |
| **`contatti`** | `soggetto_id` NOT NULL, ruolo e istanza facoltativi | ❌ né istanza↔soggetto, né ruolo↔soggetto (`soggetto_id` della riga) |
| **`soggetti_ruoli_conti_bancari`** | ruolo NOT NULL, istanza facoltativa | ❌ il guard della tabella guarda solo il conto attivo. Il backend scrive `istanza_utility_id` in `UPDATE` (`LEGAME_RUOLO_UPDATE_COLS`, `conti_bancari_repository.py`) |

E le **due porte** dall'altro lato della regola:

* `istanze_utilities.soggetto_id` è bloccato (`E_ISTANZA_SOGGETTO_IMMUTABILE`, D-7 del 2026-10-09): ✅;
* ⚠️ **`soggetti_ruoli.soggetto_id` non è bloccato.** Un `UPDATE` del soggetto di un ruolo porta su un altro
  soggetto i suoi indirizzi e contatti d'istanza, i conti, **e i BA**: il guard del BA scatta solo su
  `billing_account`, quindi anche la regola che c'è ha la porta aperta. Nessuno lo scrive oggi (né il backend né
  una funzione del DB), ma il modello lo ammette.

**Dati (fatto datato, non motivo):** dbdev, 2026-10-19 10:40, **nessuna riga viola** la regola in nessuna delle tre
tabelle (indirizzi con istanza 4, contatti con istanza 3, contatti con ruolo 10, conti con istanza 2). Non c'è
niente da bonificare prima del controllo, e quindi niente da decidere su questo punto.

**Proposta del team DB.** ✅ **Decisa da Tid il 2026-10-19: accolte tutte e quattro** (D-17a (B) tre tabelle, D-17b BB comune col BA nello stesso giro, D-17c codice condiviso, D-17d lock del soggetto del ruolo). Resta il via allo sviluppo, coi progressivi.

* **D-17a — il perimetro.** (A) Solo `indirizzi`, come chiede la R-BE-15. (B, **proposta**) `indirizzi`,
  `contatti` e `soggetti_ruoli_conti_bancari` nello stesso giro: è la stessa regola sulla stessa coppia di colonne,
  e il difetto è identico. Con (A) le altre due restano un debito noto, da scrivere in un brief
  prima di archiviare questo.
* **D-17b — un BB, regola del 2.** Il guard del BA è la prima copia, gli indirizzi la seconda: si estrae
  `anagrafiche.fn_guard_istanza_del_soggetto(istanza, soggetto, codice, contesto)` (confronta
  `istanze_utilities.soggetto_id` col soggetto dato; istanza NULL = niente da dire) e il guard del BA lo chiama
  **nello stesso giro**, col suo codice di oggi (il BE lo consuma: `error_ui_overrides`, il ripiego). Ogni tabella
  ha il suo guard sottile, che risolve il soggetto (dal ruolo, o da `soggetto_id` per i contatti) e chiama il BB.
  Fascia `a10`, `INSERT` e `UPDATE`; in `UPDATE` esce se ruolo, istanza (e `soggetto_id` dei contatti) non sono
  cambiati, come `guard_forma_libera`. Nessun trigger `BEFORE` delle tre tabelle scrive quelle colonne.
* **D-17c — il codice.** Un codice solo per le tabelle nuove: `E_ISTANZA_ALTRO_SOGGETTO`, `DATO_ERRATO`, contesto
  `campo = istanza_utility_id` e `tabella`, così il BE lo mostra sul form senza tradurlo. Il BA tiene il suo. Per i
  contatti serve anche il ruolo di un altro soggetto (`campo = soggetto_ruolo_id`): `E_RUOLO_ALTRO_SOGGETTO`, solo
  se (B).
* **D-17d — la porta del ruolo.** Bloccare `soggetti_ruoli.soggetto_id` con una riga di
  `dbops.automation_lock_columns` (`E_SOGGETTO_RUOLO_SOGGETTO_IMMUTABILE`, `CONFLITTO_STATO`, come l'istanza): un
  ruolo è «il ruolo X del soggetto S» (`uq_soggetto_ruolo`), e il ruolo creato sul soggetto sbagliato si ritira e si
  ricrea. Chiude la porta per le tre tabelle e per il BA. Senza, il guard delle righe va messo anche su
  `soggetti_ruoli` (un `UPDATE` del soggetto che rilegge tutte le figlie): più caro, per un caso che il modello non
  vuole.

**pgTAP previsto:** `anagrafiche/test-istanza-dello-stesso-soggetto-v1.sql`, che fabbrica due soggetti con le loro
istanze: per ogni tabella del perimetro, rifiutati l'`INSERT` e l'`UPDATE` (ruolo e istanza, separatamente) con
l'istanza dell'altro soggetto, col codice e il campo; ammessi la stessa istanza, nessuna istanza, e l'`UPDATE` che
non tocca le due colonne; il BA che rifiuta come prima (regressione dal BB); con D-17d, l'`UPDATE` del soggetto di
un ruolo rifiutato. Regressione: i pgTAP di indirizzi, contatti, conti e BA.

**Ricaduta BE (dopo l'apply):** il codice nuovo in `error_policies_generated` (dal CSV), il ripiego in
`error_messages_fallback` e `highlight_form_fields` in `error_ui_overrides`, come per
`E_BA_SOGGETTO_INCOERENTE_ISTANZA`; con D-17d, il codice del lock. Nessun cambio di contratto degli endpoint.

#### 6.17.2 Fatto (team DB, 2026-10-19), applicato da Tid

Via allo sviluppo di Tid (2026-10-19), progressivi dal `20261019-80`.

| ChangeSet | Che cosa |
| --- | --- |
| `20_code/anagrafiche/20261019-80-create-fn-istanza-di-altro-soggetto` | BB `anagrafiche.fn_istanza_di_altro_soggetto(istanza, soggetto)`: il soggetto dell'istanza quando non è quello dato, `NULL` altrimenti (anche senza istanza o soggetto, o con un'istanza che non esiste: la rifiuta la FK). Un predicato: il rifiuto resta nel chiamante, col suo codice e il campo scritti nella chiamata (il presidio del canale li legge lì) |
| `20_code/anagrafiche/20261019-81-create-fn-ruolo-di-altro-soggetto` | il gemello per il ruolo |
| `20_code/anagrafiche/20261019-82-create-trgfn-guard-istanza-del-ruolo` | un guard per `indirizzi` e `soggetti_ruoli_conti_bancari` (a10, `INSERT` e `UPDATE`, esce se ruolo e istanza non cambiano): `E_ISTANZA_ALTRO_SOGGETTO`, campo `istanza_utility_id` |
| `20_code/anagrafiche/20261019-83-create-trgfn-contatti-guard-contesto-soggetto` | il guard dei contatti: prima il ruolo (`E_RUOLO_ALTRO_SOGGETTO`, campo `soggetto_ruolo_id`), poi l'istanza (`E_ISTANZA_ALTRO_SOGGETTO`), tutti e due contro `soggetto_id` della riga |
| `20_code/anagrafiche/20261019-84-update-trgfn-billing-account-guard-coerenza-istanza-dal-bb` | il guard del BA passa dal BB (regola del 2); codice, contesto e frase invariati |
| `20_code/pratiche/20261019-85-update-trgfn-pratiche-guard-contesto-dai-bb` | regole 3 e 4 delle pratiche dai due BB: era la terza copia, trovata scrivendo, ritirata nello stesso giro. ⚠️ Un ruolo o un'istanza che **non esistono** non sono più «non coerenti»: li rifiuta la FK, che dice la causa giusta (nessun pgTAP lo provava) |
| `90_end/20261019-86-provision-lock-soggetti-ruoli-soggetto` | chiama il runner dei lock sullo schema `anagrafiche`: monta subito `trg_soggetti_ruoli_a10_lock_columns_upd` (su dbdev il ci_apply non rigira le automazioni). Il 2026-10-19 il runner non aveva altre divergenze su `anagrafiche` |
| CSV | `codici_errore.csv` e `messaggi_errore.csv` (id 1368 … 1370): `E_ISTANZA_ALTRO_SOGGETTO` e `E_RUOLO_ALTRO_SOGGETTO` (`DATO_ERRATO`), `E_SOGGETTO_RUOLO_SOGGETTO_IMMUTABILE` (`CONFLITTO_STATO`); `automation_lock_columns.csv`, la riga di `soggetti_ruoli.soggetto_id` |

Firme e `RETURNS` dei due BB ancorati con `%TYPE` (anche in `COMMENT` e `DROP`); `SECURITY INVOKER`
esplicito su tutti e sei: `istanze_utilities` e `soggetti_ruoli` non hanno RLS (2026-10-19), la lettura
risponde sempre.

* **pgTAP nuovo:** `anagrafiche/test-istanza-dello-stesso-soggetto-v1.sql` (plan 17): i due BB, i guard
  montati, indirizzi (madre e `UPDATE` di istanza e di ruolo, rifiutati e ammessi), conti del ruolo,
  contatti (ruolo e istanza d'altri, `UPDATE` del soggetto), il lock del ruolo. Asserisce il codice (canale
  `CONSTRAINT`) e il campo (canale `COLUMN`), non un `P0001` qualsiasi.
* **pgTAP corretto:** `vendite/test-indirizzi-documento-seguono-cliente-v1.sql` costruiva proprio il
  difetto: per far diventare d'altri una riga del preventivo spostava in anagrafica un indirizzo del ruolo di
  A sulla fornitura di B. Ora lo sposta su una **seconda fornitura di A** (dalla madre
  `fn_crea_billing_account`, nella finestra dei differiti): il predicato risponde `ALTRA_FORNITURA` come prima,
  la check ha lo stesso motivo. 18/18.
* **Doc:** manual nuove `fn_istanza_di_altro_soggetto`, `fn_ruolo_di_altro_soggetto`,
  `trgfn_guard_istanza_del_ruolo`, `trgfn_contatti_guard_contesto_soggetto`; note in `fn_crea_indirizzo_ruolo`
  (il ⚠️ «non controlla» è chiuso), nel guard del BA e nel contesto delle pratiche.

**Prova (scratch `zeroerp_ruoli`, come `zeroerp_owner`).** Il test nuovo con l'SQL estratto: 17/17.
Regressione su 79 file (i pgTAP che scrivono indirizzi, contatti, conti del ruolo, pratiche o i due guard
rivisti, più i presidi `test-catalogo-messaggi-errore-completo`, `test-vw-codici-errore-motivo-nominato`,
`test-punti-canale-campo-v1`, `test-riferimenti-morti-v1`, `test-lock-columns-convergenza`): la corsa
«con l'estratto» è stata invalidata a metà dall'apply di Tid sullo scratch (11:10), quindi il confronto vero
è **prima dell'apply (11:09-11:10) contro dopo l'apply**: due file cambiano, il test nuovo (rosso → 17/17) e
`test-indirizzi-documento-seguono-cliente-v1` (18/18 → 12/18, il fixture del difetto, corretto come sopra).
Gli altri rossi dello scratch sono identici prima e dopo, non di questo giro. `plpgsql_check` pulito sui
cinque montaggi (i due guard nuovi sulle loro tabelle, BA, pratiche).

⚠️ **Regressione trovata da Tid su dbdev (2026-10-19), sfuggita alla prova:**
`anagrafiche/test-conto-incasso-un-solo-soggetto.sql` test 4, `E_ISTANZA_ALTRO_SOGGETTO`. La fixture
**pescava** «il primo ruolo» e «la prima istanza» del database, senza legame fra loro: il test metteva sul
ruolo di un soggetto l'istanza di un altro, cioè la riga che il guard ora rifiuta. Sullo scratch il file
moriva già al test 1 (la pesca non trova la filiale), prima e dopo: lo stesso esito ha nascosto la
regressione nel confronto. Corretto: due clienti e la filiale costruiti dai builder, l'istanza è quella del
soggetto del primo ruolo; 10/10 sullo scratch. Poi riletti uno per uno gli altri rossi preesistenti dello
scratch che scrivono un'istanza (`test-pratiche-sorgenti-flusso`, `test-proiezione-stato-sorgente`,
`test-vw-dash-competenza-gruppi-cliente-v1`, `test-esecutivi-ba-coppia-v1`, i due `test-snapshot-indirizzi-*`,
`test-guard-contesto-pratica`): coppie coerenti o pratiche col solo soggetto, nessun altro caso.

✅ **Applicato** da Tid su dbdev (11:10:21) e sullo scratch (11:10:44): due BB, tre guard, il lock montato
su tutti e due. ✅ **pgTAP verdi su dbdev** (Tid, 2026-10-19): il test nuovo e i due corretti (`test-indirizzi-documento-seguono-cliente-v1`, `test-conto-incasso-un-solo-soggetto`). **Resta a Tid:** il commit.

**Dopo il DB, BE (richiesta):**

* **R-DB-17a — i tre codici nuovi.** `E_ISTANZA_ALTRO_SOGGETTO` e `E_RUOLO_ALTRO_SOGGETTO` (`DATO_ERRATO`,
  col campo nel canale `COLUMN`): policy rigenerate dal CSV, ripiego in `error_messages_fallback`,
  `highlight_form_fields` in `error_ui_overrides`, come per `E_BA_SOGGETTO_INCOERENTE_ISTANZA`.
  `E_SOGGETTO_RUOLO_SOGGETTO_IMMUTABILE` (`CONFLITTO_STATO`, il lock): policy e ripiego. Nessun pre-check nel
  backend, nessun cambio di contratto degli endpoint. Da sapere: anche la modifica di un **contatto** e di
  un **conto del ruolo** ora può rifiutare l'istanza (o il ruolo) di un altro soggetto.
