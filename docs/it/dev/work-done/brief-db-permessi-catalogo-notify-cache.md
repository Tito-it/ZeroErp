# Brief DB — Un cambio del catalogo permessi svuota la cache del backend

> **Chi scrive:** sessione BE/FE (`dev/backend-tid`), 2026-10-04. **A chi:** team DB
> (`dev/db-tid`); poi BE (§5), che **attende** la consegna DB.
> **Origine:** [brief-db-permessi-tetto-area.md](brief-db-permessi-tetto-area.md) §6.5 e §10:
> `livello_minimo_area` cambia solo a DB (seed al migrate), e il backend non lo sa.
> **Decisione:** di Tid, 2026-10-04: soluzione LISTEN/NOTIFY, sul meccanismo che già esiste per
> il cambio di reparto.
> **Stato:** ✅ **CHIUSO il 2026-10-05.** DB: `20261004-87 → -89` + mirror `processi`, applicati su dbdev e `zeroerp_ci` il 2026-10-04, pgTAP verdi. BE: listener su due canali e rinomino `listen_permessi` (§8), installer che ritira le sveglie non più dichiarate (§8.4, con l'incidente gunicorn). Passaggio sull'host dbdev fatto da Tid il 2026-10-05 (§8.5).

## 1. Il problema

Il backend tiene in cache, per utente e contesto di sessione, i permessi risolti dalle funzioni DB
(`apps/core/services/permissions_cache.py`, Redis). La cache si svuota quando **l'applicazione**
scrive qualcosa che li cambia: un override (`invalidate_user`), il profilo di un reparto
(`invalidate_department`), un cambio di reparto (trigger DB → `NOTIFY cambio_reparto` → listener →
`invalidate_user`).

Chi scrive il **catalogo** dei permessi **fuori dall'applicazione** non svuota niente:

| Tabella | Chi la scrive | Cosa cambia per gli utenti |
| --- | --- | --- |
| `config.azioni_processo` | seed CSV al migrate | `livello_minimo_area` (tetto d'area), azioni nuove o spente |
| `config.aree_funzionali` | seed CSV al migrate | aree nuove o spente |
| `config.area_model_overrides` | seed CSV al migrate | a quale area appartiene un oggetto ⇒ quale tetto lo limita |
| `config.profili_accesso`, `config.profili_accesso_aree`, `config.profili_accesso_azioni`, `config.profili_accesso_bindings` | app (solo il PUT del profilo di **reparto**, che invalida il reparto), seed, interventi a mano | tutto l'ereditato di chi ha quel profilo, anche `AD_HOC` e `PORTALE`, che l'app non invalida |

Fino alla scadenza della voce (`PERMISSIONS_CACHE_TTL`, 300 s) gli utenti lavorano coi permessi
vecchi: un'azione appena chiusa dal tetto resta eseguibile. ⚠️ Il team DB applica i migrate per
conto suo, indipendentemente dal deploy del backend: svuotare la cache dallo script di deploy
**non** chiuderebbe il buco, e nemmeno una correzione fatta in `psql`.

## 2. La regola

**Ogni scrittura che cambia il catalogo o i profili dei permessi, da qualunque scrittore, avvisa il
backend al commit.** Il backend svuota la cache di tutti (`invalidate_all`, invalidazione per
generazione: costa un ricalcolo per utente alla richiesta successiva).

È lo stesso schema del cambio di reparto (`anagrafiche.trgfn_risorse_umane_notify_cambio_reparto`
→ `anagrafiche.fn_notify_cambio_reparto` → canale `cambio_reparto`), con una differenza: qui la
notifica non riguarda un utente, ma tutti.

## 3. Richiesta

| # | Cosa |
| --- | --- |
| R1 | Una funzione `script.fn_notify_permessi_catalogo(p_tabella text)` che emette `pg_notify('permessi_catalogo', json_build_object('tabella', p_tabella)::text)`. Sede unica del nome del canale lato DB. Forma e guard come `fn_notify_cambio_reparto`. |
| R2 | Una trigger function generica (`script.trgfn_notify_permessi_catalogo()`, argomento: il nome della tabella, oppure `TG_TABLE_SCHEMA.TG_TABLE_NAME`) che chiama R1 e restituisce `NULL`. |
| R3 | Un trigger **`AFTER INSERT OR UPDATE OR DELETE … FOR EACH STATEMENT`** (non per riga: un mirror CSV tocca decine di righe e basta un avviso) su ognuna delle **sette** tabelle di §1, prefisso `z90_` come quello del cambio di reparto. ⭐ `NOTIFY` è transazionale: parte al commit, non parte su rollback, e PostgreSQL scarta i payload identici nella stessa transazione. Valutare anche `TRUNCATE`. |
| R4 | Verificare che il mirror dei CSV (`80_data`, `loadUpdateData`) faccia `INSERT`/`UPDATE` normali e quindi **accenda** i trigger: è il caso per cui il brief esiste. Se un passo li disattiva (`session_replication_role`, `ALTER TABLE … DISABLE TRIGGER`), dirlo nella consegna. |
| R5 | pgTAP: per ogni tabella, una scrittura in transazione produce **una** notifica sul canale col nome della tabella (`LISTEN` + `pg_notification_queue_usage` non basta: usare il metodo dei test del cambio di reparto, se esiste, o dichiarare come si prova). Una scrittura annullata non ne produce. |
| R6 | Doc `manual/` delle due funzioni e una riga nella guida di architettura dei permessi (§ cache), che oggi non dice chi svuota la cache al cambio di catalogo. |

ℹ️ **Fuori:** `config.user_override_*`. Le scrive il pannello, che invalida già l'utente
(`invalidate_user`). Un avviso per utente su scritture fuori dall'app è un'altra cosa (payload per
utente, come il cambio di reparto) e non serve per chiudere questo buco.

## 4. Il processo che ascolta si rinomina `listen_permessi` (✅ Tid, 2026-10-04)

Il listener oggi si chiama `listen_cambio_reparto` (`dbops.processi.codice`, `sveglie.json`,
unità systemd `zeroerp-listen-cambio-reparto`, `application_name` della sessione, che
`dbops.vw_processi_programmazione` legge per dire se il processo è vivo). Col canale nuovo fa due
cose, e il nome non lo direbbe più. Decisione: **un solo processo**, che ascolta entrambi i canali,
rinominato **`listen_permessi`**. Due processi separati non servono: stessa connessione, stesso
destinatario.

| # | Cosa (DB) |
| --- | --- |
| R7 | `dbops.processi`: il codice `listen_cambio_reparto` diventa `listen_permessi` (dal seed CSV, mai con `UPDATE`, linee-guida-sql §11.2), con descrizione aggiornata: «invalida la cache permessi al cambio di reparto di un utente e al cambio del catalogo o dei profili dei permessi». Verificare chi altro legge quel codice (viste di presidio, `job_run_log`, pgTAP) e allinearlo nello stesso giro. ⚠️ Le righe storiche di `maintenance.job_run_log` col codice vecchio: dire nella consegna se restano (storia) o se una FK le lega al catalogo. |

⛔ **Ordine**: il codice cambia a DB e nel BE **insieme**. Col DB avanti, il listener si presenterebbe
con un `application_name` che il catalogo non conosce più, e il presidio lo darebbe «muto» pur vivo;
col BE avanti, il contrario. Il BE si allinea appena il DB consegna (§5), prima del riavvio del
servizio.

## 5. Lato BE, a consegna DB fatta

* `apps/anagrafiche/services/notify_listener.py`: `LISTEN` anche su `permessi_catalogo`;
  `_handle_notification` smista per canale: `cambio_reparto` → `invalidate_user` (come oggi),
  `permessi_catalogo` → `invalidate_all` (che oggi esiste e non chiama nessuno).
* ⭐ **All'avvio e a ogni riconnessione** del listener, un `invalidate_all`: una notifica emessa
  mentre il processo era giù è persa (LISTEN/NOTIFY non accoda), e il migrate fatto con il
  listener spento è esattamente il caso da coprire.
* Il nome del canale in **una** costante, accanto a `CHANNEL`.
* Test in `anagrafiche/tests/services/test_notify_listener.py`: smistamento per canale, payload
  non valido ignorato, `invalidate_all` all'avvio.
* Il rinomino di §4: costante `PROCESSO_LISTEN_CAMBIO_REPARTO` → `PROCESSO_LISTEN_PERMESSI` in
  `core/services/processi.py`, command `listen_permessi` (ritirato `listen_cambio_reparto`), unità
  systemd `zeroerp-listen-permessi` (`backend/deploy/systemd/`, poi `install-timers.sh` sugli host:
  la vecchia unità va disabilitata), `sveglie.json`, il test `core/tests/services/test_sveglie.py`
  e i commenti che citano il nome vecchio, nello stesso giro.

## 6. Analisi del team DB (2026-10-04) — prima di scrivere

> Letta la catena dalla doc auto-gen e il giro BE/FE del tetto (`b8ac544fe`). Il giro BE/FE
> **non** chiede altro al DB: legge `fn_get_permessi_effettivi_azioni/_oggetti` con le colonne
> consegnate, e `/me/` cambia solo nella descrizione OpenAPI. Il solo lavoro DB che resta del
> cantiere del tetto è questo brief.

### 6.1 Le sette tabelle sono quelle giuste

Lette dai corpi (`fn_get_permessi_effettivi_*`, `fn_get_permessi_ereditati_*`,
`fn_get_profili_accesso_applicabili`, `fn_resolve_livello_area`, `fn_area_di_oggetto`): la parte
**di catalogo** che la catena legge è esattamente quella di §1. Il resto che legge è **per
utente** (`user_override_*`, `identita_digitali`, `risorse_umane.unita_organizzativa_id`) e resta
fuori, come dice §3.

⚠️ **Residuo dichiarato, non di questo brief:** una scrittura fuori dall'app su
`identita_digitali` (veste spenta, identità revocata) non svuota la cache fino al TTL. È lo
stesso buco, ma per utente. La leva manuale è R1 (§6.4).

### 6.2 ⛔ R7 così com'è rompe il migrate fuori dalla CI

Il command `listen_cambio_reparto` apre un `registered_job(..., processo_codice=…)`: scrive in
`maintenance.job_run_log.processo_codice`, che ha la FK `fk_job_run_log_processi` verso
`dbops.processi(codice)`, **senza** `ON UPDATE`. Cambiare il codice della riga 24 nel CSV fa un
`UPDATE` della chiave referenziata ⇒ il mirror `80_data/20260904-13` fallisce su **ogni database
dove il listener è partito almeno una volta** (dbdev, ogni installazione). In CI, ricostruita da
zero, non ci sono righe di giornale: **verde in CI, rosso su dbdev**.

**Proposta:** non si rinomina, si **sostituisce** — è il meccanismo di deprecazione del catalogo:

* riga nuova `46,listen_permessi,…` (stessi `classe`/`canale`/`segno_di_vita` della 24);
* la riga 24 resta, con `attivo = f` e `obsoleto_dal = 2026-10-04`: la storia del giornale
  resta legata al codice con cui è stata scritta, e `vw_processi_programmazione` la esclude già
  (`attivo AND obsoleto_dal IS NULL`). Nessun guard di disattivazione su `dbops.processi`.

Effetto collaterale buono: l'ordine di §4 si ammorbidisce. Col DB avanti, il listener vecchio
scrive ancora nel giornale (la riga c'è) e il panorama segna `listen_permessi` MUTO fino al
riavvio col nome nuovo: un rosso vero e transitorio, non un migrate fallito.

✅ **Tid, 2026-10-04: rinomino confermato**, eseguito con la riga nuova + ritiro (§7.1).

### 6.3 Il trigger: tre precisazioni

* **Per istruzione, anche a zero righe.** Un trigger `FOR EACH STATEMENT` scatta anche su un
  `UPDATE … WHERE false`: un avviso in più, cioè un `invalidate_all` innocuo. Non si filtra
  (servirebbero le transition table); è anche ciò che rende il pgTAP pulito (§6.5).
* **Il mirror li accende.** Nessun mirror delle sette tabelle usa `session_replication_role` o
  `DISABLE TRIGGER` (cercato nei changelog: compaiono solo in changeSet di altre tabelle).
  `loadUpdateData` fa un'istruzione per riga ⇒ N chiamate al trigger, **una** notifica per
  tabella per transazione (payload identici fusi da PostgreSQL).
* **Nome e TRUNCATE.** `trg_profili_accesso_bindings_z90_notify_permessi_catalogo_ins_upd_dlt`
  supera i 63 caratteri (nome troncato, linee-guida-trigger). Si usa
  `trg_<tabella>_z90_notify_permessi_ins_upd_dlt` (60 sulla più lunga). `TRUNCATE` sì, nello
  stesso trigger e dichiarato nel `COMMENT`: un suffisso `_trn` sforerebbe di nuovo.

### 6.4 R1 e R2: due funzioni, e la seconda copia c'è

R1 ha due consumatori, non uno: il trigger (R2) e la **leva manuale**
`SELECT script.fn_notify_permessi_catalogo('manuale')` dopo una correzione fuori dall'app su
tabelle che il trigger non copre (§6.1). Va scritto nel `COMMENT` di R1.

### 6.5 R5 si prova davvero, senza sporcare

Il pgTAP del cambio di reparto prova solo `lives_ok`: la consegna non la vede. Qui si può fare
meglio con due sessioni `dblink`, come `test-vw-processi-programmazione`:

1. sessione A: `LISTEN permessi_catalogo`;
2. sessione B, in autocommit, per ognuna delle sette tabelle un `UPDATE … SET id = id WHERE
   false`: **committa senza cambiare una riga** (lo statement trigger scatta, gli audit `BEFORE
   ROW` no);
3. `dblink_get_notify('A')`: una notifica per tabella, col nome giusto nel payload;
4. B: `BEGIN; UPDATE … WHERE false; ROLLBACK;` ⇒ nessuna notifica.

⚠️ B deve poter scrivere sul catalogo (`zeroerp_app` può non avere `UPDATE` su queste
tabelle: il privilegio si controlla prima del trigger). Se `dblink` non si apre o B non ha il
privilegio, `skip()` motivato, come il precedente. In più, sul catalogo: i sette trigger
esistono, sono `AFTER`, per istruzione, sui quattro eventi (`pg_trigger.tgtype`).

### 6.6 Piano

| # | Cosa |
| --- | --- |
| `20_code/script` | R1 `fn_notify_permessi_catalogo(p_tabella text)` + R2 `trgfn_notify_permessi_catalogo()` |
| `20_code/config` | i sette trigger `z90`, un changeSet |
| `80_data` CSV `processi` | riga 46 `listen_permessi`, riga 24 ritirata (§6.2), se Tid conferma il rinomino |
| pgTAP | `config/test-notify-permessi-catalogo-v1` (§6.5) |
| doc | `manual/` delle due funzioni, guida architettura permessi § cache |

## 7. Consegna DB (2026-10-04) — ✅ applicata su dbdev e `zeroerp_ci`, pgTAP verdi

### 7.1 ChangeSet e dati

| # | File | Cosa |
| --- | --- | --- |
| `-87` | `20_code/script/…-create-fn-notify-permessi-catalogo` | R1: `pg_notify('permessi_catalogo', {"tabella": …})`; `p_tabella` NULL o vuoto → `E_PARAMETRO_INVALIDO`. VOLATILE, INVOKER, `GRANT EXECUTE` a `zeroerp_app` |
| `-88` | `20_code/script/…-create-trgfn-notify-permessi-catalogo` | R2: chiama R1 con `TG_TABLE_SCHEMA.TG_TABLE_NAME`, nessun argomento di trigger |
| `-89` | `20_code/config/…-create-trg-notify-permessi-catalogo` | R3: sette trigger `trg_<tabella>_z90_notify_permessi_ins_upd_dlt`, `AFTER INSERT OR UPDATE OR DELETE OR TRUNCATE … FOR EACH STATEMENT` |
| CSV | `80_data/sql/dbops/processi.csv` (mirror `20260904-13`) | R7: riga **46** `listen_permessi` (`AMMINISTRAZIONE`/`COMMAND`/`SESSIONE`); riga 24 `listen_cambio_reparto` → `attivo = f`, `obsoleto_dal = 2026-10-04`, descrizione che rimanda alla 46 |

📌 *Fatto datato:* il 2026-10-04 su dbdev `maintenance.job_run_log` ha 14 righe con
`processo_codice = 'listen_cambio_reparto'`: il rinomino diretto sarebbe morto sulla FK (§6.2). Il
CSV, a parte le due righe, coincide con dbdev e con `zeroerp_ci` (confronto colonna per colonna):
risvegliare il mirror non riscrive nient'altro.

R4: nessun mirror delle sette tabelle spegne i trigger (§6.3). R6: `manual/` delle due funzioni,
guida architettura permessi §6.1 («La cache fra una richiesta e l'altra», tabella di chi svuota
cosa) e «Vedi anche»; `dbops/manual/processi.md` e la guida `processi-automatici-classe-e-identita`
col nome nuovo.

### 7.2 pgTAP — `db/pgtap/script/test-notify-permessi-catalogo-v1.sql` (15)

1-4 la funzione (esiste, leva manuale, i due rifiuti); 5-11 i sette trigger cercati per
**funzione** e tabella (`tgtype = 60`: AFTER, per istruzione, I/U/D/TRUNCATE; abilitato); 12 il
trigger scatta come app; **13-15 la consegna vera**, con due sessioni `dblink` (§6.5): una notifica
per tabella col nome giusto; nessuna su `ROLLBACK`; una sola per due istruzioni nella stessa
transazione. Niente attese a tempo: ogni fase si chiude con una sentinella. Dove la seconda
sessione non si apre, o un lock la ferma (`lock_timeout` 5 s: senza, la prova pre-apply resta
appesa nello stallo fra le due sessioni), 13-15 vanno in `skip()` col motivo.

### 7.3 Prove (2026-10-04)

* **`zeroerp_ci`, da owner, in transazione annullata**: SQL estratto di `-87 → -89` con le loro
  `preConditions` (attese 1, avute 1), mirror reso da `updateSQL` offline, poi il pgTAP. 1-12
  verdi; 13-15 in skip per lock, come previsto: la DDL non committata tiene la tabella.
  `plpgsql_check` a zero sulle due funzioni. Il panorama vede `listen_permessi` `MUTO` (nessuna
  sessione lo porta ancora) e non vede più `listen_cambio_reparto`. DB lasciato com'era.
* **Cluster PG18 usa-e-getta** (stub minimi per tabelle ed errore, SQL estratto, pgTAP
  invariato): **15/15**. Ha trovato un difetto del test, non del codice: `dblink_exec` rifiuta un
  `SELECT` (2F003), la sentinella non partiva e 13-15 andavano **sempre** in skip. Corretto (la
  sentinella va in un `DO`).
* **Mutazioni** sul cluster: trigger tolto su una tabella → rossi 6 e 13; trigger per riga → 7,
  13, 15; payload senza nome tabella → 13, 15.
* Guardrail statici verdi (preambolo pgTAP, `runOnChange`, preCondition/seed, DDL su trigger
  generati, letterali SQL, GRANT batch, v1 congelato).
* ⚠️ **Non provato qui:** l'apply, la corsa come app su dbdev (lì il DSN dblink è `service=`:
  13-15 andranno in skip col motivo) e la CI da zero, dove il DSN è quello del proprietario e
  13-15 girano davvero. È la corsa di Tid.

### 7.3-bis Prima corsa di Tid su dbdev (2026-10-04) — test 12 rosso, corretto

`42501 permesso negato per la tabella aree_funzionali`. Il difetto era **del test**, non del
codice: per contratto (GRANT, uguale su dbdev e CI) l'app scrive sei tabelle su sette, e
`config.aree_funzionali` per lei è in sola lettura (la scrivono il seed e il migratore). Il
test pretendeva che l'app le scrivesse tutte e sette. La mia prova non lo vedeva perché girava da
owner (§7.3). Ora il 12 prova le tabelle che il GRANT dà in scrittura a
chi esegue (`has_table_privilege`), e se non ce n'è nessuna va rosso con `fail()`.
`aree_funzionali` resta coperta dal 13, dove B scrive col DSN del proprietario. Cluster di nuovo
15/15, prove con codice alterato invariate. ⏳ Da rilanciare (Tid).

### 7.3-ter Apply e corsa (2026-10-04 sera)

* Su dbdev (`zeroerp`) il `databasechangelog` registra `-87`, `-88`, `-89` `EXECUTED` alle 23:55 e
  il mirror `20260904-13` `RERAN`; `dbops.processi`: riga 24 `listen_cambio_reparto` ritirata,
  riga 46 `listen_permessi` attiva.
* Corsa pgTAP di Tid: **verde**, test 12 compreso dopo la correzione di §7.3-bis.
* Su `zeroerp_ci` il `databasechangelog` registra `-87`, `-88`, `-89` `EXECUTED` alle 23:55:30.

### 7.4 Al BE — ⏳ si può partire (DB applicato)

§5 resta valido, con due precisazioni:

* l'**ordine** di §4 non è più stretto: col DB avanti il listener vecchio continua a scrivere il
  suo run di avvio (la riga 24 c'è ancora) e il panorama segna `listen_permessi` `MUTO` finché il
  servizio non riparte col nome nuovo. È il segnale atteso, non un guasto;
* da allineare anche la guida `risorse-umane-e-accessi.md` (§ cambio di reparto e tabella dei
  componenti: `listen_cambio_reparto`, `CambioRepartoListener`) e
  `play-book-operativo-backend.md` (unità `zeroerp-listen-cambio-reparto`), che parlano di
  oggetti del BE.

### 7.5 Per Tid

1. ~~Apply e corsa pgTAP~~ — ✅ fatti il 2026-10-04 (§7.3-ter).
2. Dopo l'apply, finché il BE non riparte, il digest dei presidi conterà `listen_permessi` `MUTO`.

## 8. Consegna BE (2026-10-05)

### 8.1 Il listener

`apps/anagrafiche/services/notify_listener.py`, classe rinominata `PermessiListener` (era
`CambioRepartoListener`):

* `LISTEN` su `cambio_reparto` e `permessi_catalogo`, nomi in due costanti
  (`CANALE_CAMBIO_REPARTO`, `CANALE_PERMESSI_CATALOGO`) e nella tupla `CANALI`; `CHANNEL` ritirata;
* `_handle_notification` smista per canale: `cambio_reparto` → `invalidate_user` (come prima),
  `permessi_catalogo` → `invalidate_all`, canale sconosciuto → warning e niente;
* ⭐ sul canale del catalogo **un payload malformato invalida lo stesso**. Il segnale è la
  notifica; `{"tabella": …}` serve solo al log. Scartare l'avviso perché la didascalia è rotta
  lascerebbe i permessi vecchi fino al TTL. Questo si discosta dalla lettera di §5 («payload non
  valido ignorato»), che resta vera per il canale del reparto, dove il payload porta il destinatario;
* ⭐ `invalidate_all` **a ogni connessione** (avvio e riconnessione), **dopo** i `LISTEN`.
  Nell'ordine inverso, una scrittura committata fra l'invalidazione e il `LISTEN` non svuoterebbe
  niente e non arriverebbe come notifica.

### 8.2 Il rinomino (§4)

| Cosa | Prima | Ora |
| --- | --- | --- |
| costante (`core/services/processi.py`) | `PROCESSO_LISTEN_CAMBIO_REPARTO` | `PROCESSO_LISTEN_PERMESSI` = `listen_permessi` |
| command | `listen_cambio_reparto` | `listen_permessi` (`git mv`, il vecchio non esiste più) |
| unità systemd | `zeroerp-listen-cambio-reparto.service` | `zeroerp-listen-permessi.service` |
| `deploy/sveglie.json` | voce `listen_cambio_reparto` | `unit`, `processo_codice`, `comando` col nome nuovo |
| `application_name` della sessione | `listen_cambio_reparto` | `listen_permessi` (dalla costante: è ciò che la riga 46 cerca) |

`test_sveglie.py` non chiedeva modifiche: legge `sveglie.json` e i template, e il rinomino li ha
portati insieme. In `scripts/tests/test-install-timers.sh` i test 2 e 4 avevano il nome
dell'unità **scritto a mano**, cioè una seconda copia del dichiarato, che lo stesso file vieta in
`attesi()`. Ora leggono i servizi sempre accesi da `sveglie.json`, e con nessun servizio
dichiarato vanno **rossi** invece che verdi per sottrazione.

I commenti che raccontano il difetto del 2026-09-06 (`install-timers.sh`, `ci-validate.yaml`,
`sveglie_processi.md`, `test_sveglie.py`) citano il nome vecchio **come storia** e restano così.

### 8.3 Test e doc

* `anagrafiche/tests/services/test_notify_listener.py`: 13 test (9 aggiornati, 4 nuovi). Il
  catalogo invalida tutti; un payload malformato sul catalogo invalida lo stesso; un canale
  sconosciuto non invalida niente; l'ordine `LISTEN`, `LISTEN`, `invalidate_all` si ripete a ogni
  connessione (avvio e riconnessione). Il test 1 prova anche che un cambio di reparto **non** svuota tutti.
* Corse del 2026-10-05: `apps.core.tests.services`, `apps.anagrafiche.tests.services` e i due test
  API dei processi → 1194 OK; `test-install-timers.sh` OK; ruff verde.
* Doc: guida architettura permessi §6.1 (lo svuotamento alla riconnessione),
  `risorse-umane-e-accessi.md` (tre punti), play-book §16.1-16.2 (tabella e nome nuovo),
  catalogo BB backend (consumer di `registered_job`; chi chiama `invalidate_all`),
  `PROJECT_CONTEXT.md`.

### 8.4 Il ritiro degli unit non più dichiarati (✅ Tid, 2026-10-05)

Prima `install-timers.sh` solo aggiungeva, e col rinomino l'unità vecchia sarebbe rimasta
accesa accanto alla nuova. Ora l'installer **spegne e toglie** le sveglie presenti sull'host e
non più dichiarate in `sveglie.json`: è lo specchio sull'host di `test_nessun_template_orfano`.
Una sveglia è un `zeroerp-*.service` che lancia `bin/run-command.sh`, la firma di ogni template.

🔴 **Incidente del 2026-10-05.** La prima versione guardava il solo prefisso `zeroerp-`, e al
primo giro di Tid sul dbdev ha spento e cancellato **`zeroerp-gunicorn.service`**. È `zeroerp-`
ma non è una sveglia: lo installa il play-book §8. Effetto: backend giù, sessione persa, unità
ricreata a mano dal §8 (il drop-in `override.conf` era sopravvissuto). Il test 8 non lo vedeva
perché seminava solo un orfano e un file non `zeroerp-`, non un `zeroerp-` estraneo. Ora la firma
decide, gli estranei si stampano come `ESTRANEO` e non si toccano, e il test 8 semina proprio
`zeroerp-gunicorn`. La mutazione che torna al solo prefisso fa diventare il test rosso, e la
simulazione sull'assetto reale del dbdev ritira la sola `zeroerp-listen-cambio-reparto`. Prima i timer, poi i servizi, prima del `daemon-reload`; se uno
spegnimento fallisce l'installer si ferma senza cancellare il file. Il piano li stampa come
`RITIRA`. Test 8 di `test-install-timers.sh` (orfano seminato, file non `zeroerp-` e unit
dichiarato intatti); una mutazione sull'ordine timer/servizio lo fa diventare rosso. Doc:
play-book §16.3-bis, `sveglie_processi.md`.

#### 8.4-bis Revisione critica (2026-10-05, dopo il commit `87205cbfa`)

* **Firma fragile**: `grep -F` cercava il wrapper in tutto il file, quindi un unit estraneo che lo
  citava in un commento sarebbe stato ritirato. Ora si legge la sola riga `ExecStart=`, dall'inizio
  (`e_una_sveglia`).
* **Timer orfano di una sveglia dichiarata**: una voce passata da `timer` a `servizio` lasciava
  il `.timer` vecchio acceso, e questo continuava a rilanciare il servizio. Ora un `.timer` non
  dichiarato si ritira se il suo `.service` è una sveglia, dichiarata o no.
* **Prefisso cablato senza contratto**: nessuna regola obbliga una sveglia a chiamarsi `zeroerp-*`.
  Ora decide solo la firma, su tutti i `.service` della destinazione. Il prefisso resta come
  etichetta `ESTRANEO` nel piano.
* **Letterali**: il messaggio `ESTRANEO` usa `$WRAPPER`, e l'help di `listen_permessi` usa `CANALI`.
* Test 8 esteso, con tre casi nuovi seminati. Tre mutazioni, una per correzione, lo fanno diventare
  rosso. Simulazione sull'intera `/etc/systemd/system` del dbdev (17 file): nessun `RITIRA`.
* ℹ️ Non corretto, dichiarato: `invalidate_all` / `invalidate_user` ingoiano un errore di Redis
  (warning). Un'invalidazione persa così dura al massimo `PERMISSIONS_CACHE_TTL`: è il
  comportamento del BB, non nasce qui.

### 8.5 Sull'host dbdev (✅ Tid, 2026-10-05)

* `sudo backend/bin/install-timers.sh`, primo giro: ritirata `zeroerp-listen-cambio-reparto` e,
  per il difetto di §8.4, anche `zeroerp-gunicorn`. Gunicorn ricreato dal play-book §8.
* Secondo giro, con l'installer corretto: piano con 6 `ACCENDI`, 2 `SPENTO` (le fatturazioni),
  `ESTRANEO zeroerp-gunicorn.service`, nessun `RITIRA`. Dopo il giro `zeroerp-gunicorn` e
  `zeroerp-listen-permessi` sono `active`.
* Pannello dei processi: `listen_permessi` `OK` (Tid).

Su un host nuovo o non ancora aggiornato basta il deploy e `sudo backend/bin/install-timers.sh`.
