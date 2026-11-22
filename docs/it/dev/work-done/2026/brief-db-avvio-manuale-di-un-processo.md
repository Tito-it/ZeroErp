# Brief DB — Avviare un processo dall'interfaccia: il lavoro di coda che lo chiede

> ✅ **CHIUSO il 2026-09-15 (sera): collaudato in-app da Tid** — due «Esegui
> ora» sul digest settimanale, lavori `FATTO`, run con `origine = COMMAND` e
> l'utente di chi ha premuto, email `SENT` e ricevute. Spostato in
> `work-done/` insieme al piano BE/FE, dove sta il resoconto del collaudo
> (§4.4 e §7.5 del piano).
>
> **Da leggere per primo: §11 — il terzo giro (15-09): il tipo
> `ESEGUI_PROCESSO` è **ACCESO nel CSV** (una cella, nessun changeSet, prova
> verde in transazione annullata), il pgTAP resta com'è per scelta; il
> migrate su dbdev va fatto **DOPO** il deploy + `kill -HUP` del BE (§11.4).
> Poi §10 — la risposta del BE (15-09, sera): stato di
> ogni pezzo e le decisioni prese nel piano BE/FE. Poi §9 — il secondo giro
> (15-09): i cinque codici errore del verbo sono **a catalogo e in git**
> (CSV, id 1067–1071, PR #1591 su Tito-dev), con una classe diversa da quella
> chiesta su uno solo (§9.2). Poi §8 — la risposta del DB (14-09, sera): le
> tre righe reggono e sono **APPLICATE** (pgTAP verde — §8.4); tre cose del
> brief no (§8.2). Le due domande a Tid (§8.5) sono decise — solo
> `SUPER_ADMIN`; «Esegui ora» solo su comandi brevi.**
> Gemello BE/FE: [piano-be-fe-avvio-manuale-di-un-processo.md](piano-be-fe-avvio-manuale-di-un-processo.md)
> — passi, test e decisioni per esteso; qui solo ciò che tocca il DB.
> Chi scrive: backend (`dev/backend-tid`), 2026-09-14. Decisione di Tid del
> 14-09, dopo aver rilanciato a mano le due cadenze del digest.
> Origine: [analisi-riavvio-processi-da-interfaccia.md](analisi-riavvio-processi-da-interfaccia.md)
> §4.1-bis (addendum 14-09) — il verbo **«Esegui ora»** si stacca da «Riavvia»
> e parte per primo, **senza host**: un timer è un orario attorno a un
> comando, e il comando si lancia da solo.
>
> **In una riga:** un tipo di coda, un processo di classe `MANUTENZIONE` e
> canale `CODA` sotto cui metterlo, un'azione di processo. Nessuna colonna
> nuova, nessun host, `attivo = false` fino alla release del backend.

---

## 1. Il gesto, e perché passa dalla coda

Una persona autorizzata, dal drawer del processo in *Amministrazione →
Processi automatici*, preme «Esegui ora» sulla sveglia
`zeroerp-digest-presidi-settimanale`. Il web **non esegue niente**: scrive un
lavoro su `dbops.coda_lavori`, il drenatore dell'host lo prende e lancia
`bin/run-command.sh digest_presidi --cadenza settimanale` come sottoprocesso —
la stessa riga che il timer esegue, meno l'orario. Il comando si registra sul
giornale sotto **il suo** processo (`digest_presidi:settimanale`, origine
`COMMAND`, `auth_user_id` di chi ha premuto); il lavoro di coda si registra
sotto il processo di questo brief: è l'audit del **gesto**, distinto
dall'audit dell'**esecuzione**. Due righe, due domande, nessuna tabella nuova.
⚠️ **La seconda riga non sta dove questa frase la mette** — vedi §8.2.1: il
drenatore non apre nessun run per lavoro; l'audit del gesto è la riga di
`dbops.coda_lavori`, non una riga di `job_run_log` sotto `avvio_manuale`.

È il disegno del §4 dell'analisi («la UI dichiara, l'host esegue»), con una
differenza sola: niente `systemctl`, niente `sudoers`, niente host. Il §3
dell'analisi resta vero per «Riavvia», che è un altro cantiere.

## 2. Che cosa NON si chiede, e perché

* ⛔ **Nessuna colonna `host`** su `coda_lavori`, nessun registro degli host
  (analisi §5, D1): un comando che parla col DB gira uguale da qualunque host
  con il checkout. La domanda dell'host arriva con «Riavvia», non prima.
* ⛔ **Niente `abilita` a catalogo**: resta un fatto di deploy in
  `sveglie.json` (brief dei quattro processi, §10.2). Un timer spento su
  questa installazione ha il pulsante spento, con il motivo (analisi D-A).
* ⛔ **Il comando NON sta nel database.** Il client manda il `processo_codice`
  e la `unit`; il backend risolve il comando dalla whitelist di deploy
  (`sveglie.json`, campo `comando`, che è la stessa riga resa nel template
  systemd). Un comando letto da una tabella sarebbe un comando che una
  scrittura sbagliata può cambiare.
* ⛔ **Nessun ritentativo automatico** (`max_tentativi_default = 1`): un
  processo partito e caduto a metà non è idempotente per natura — chi vuole
  ripetere, preme di nuovo, e il giornale porta due righe.

## 3. Il precedente, riga per riga

`NOTIFICA_DIGEST_MUTO` / `guardiano_digest` (brief-db-quattro-processi-senza-presidio,
§10.2): tipo nato `attivo = false` e acceso dal DB a release BE avvenuta —
**la regola del binding** — sotto un processo `MANUTENZIONE` che non tocca i
dati di nessuna azienda. Qui vale identica, con una differenza di canale: là
`PGAGENT` (lo accoda una macchina), qui **`CODA`** (lo accoda una persona, e
l'identità è la sua — `run_as = OPERATORE`, `auth_user_id` gratis dallo
`scope`, come già scritto in `processi_repository.py` per il canale `CODA`).

## 4. Cosa si chiede — tre righe di catalogo

### 4.1 `dbops.processi` (seed `80_data/sql/dbops/processi.csv`)

| campo | valore | perché |
| --- | --- | --- |
| `codice` | `avvio_manuale` | il gesto, non l'unit: domani ospiterà anche «Riavvia» |
| `descrizione` | *Avvio manuale di un processo dall'interfaccia: una persona autorizzata preme «Esegui ora» su una sveglia, il web accoda un lavoro `ESEGUI_PROCESSO`, il drenatore lancia il comando del timer come sottoprocesso. MANUTENZIONE perché non tocca i dati di nessuna azienda; CODA perché lo accoda una persona e l'identità è la sua. Il run di questo processo è l'audit del gesto; il comando lanciato registra il suo run sotto il processo eseguito.* | |
| `classe` | `MANUTENZIONE` | niente utente tecnico, niente emittente |
| `canale` | `CODA` | lo accoda una persona |
| `tolleranza_minuti` / `segno_di_vita` | `NULL` / `GIORNALE` | non ha una cadenza: gira quando qualcuno preme. ⚠️ Se il panorama pretende una tolleranza per ogni processo `attivo`, ditelo: è un processo che «sta bene» anche se non gira per mesi |
| `jobname_pgagent` | `NULL` | |

### 4.2 `dbops.coda_lavori_tipi` (seed `coda_lavori_tipi.csv`)

| campo | valore |
| --- | --- |
| `codice` | `ESEGUI_PROCESSO` |
| `handler_code` | `esegui_processo_default` |
| `descrizione` | *Esegue adesso, una volta, il comando di una sveglia di deploy (`sveglie.json`, forma `timer`): lo accoda l'endpoint `processi/<codice>/esegui-ora/` con l'identità di chi preme, lo esegue il drenatore come sottoprocesso `run-command.sh <comando>`, senza `sudo` e senza systemd. Payload: `processo_codice`, `unit`. Nato `attivo=false` (regola del binding: seed spento fino alla release BE).* |
| `run_as_default` | `OPERATORE` |
| `max_tentativi_default` | **`1`** (§2) |
| `attivo` | **`false`** |
| `processo_codice` | `avvio_manuale` |

### 4.3 `config.azioni_processo` (seed `config/azioni_processo.csv`)

| campo | valore | perché |
| --- | --- | --- |
| `area_id` | `13` (`strumenti`) | accanto a `code_manage` (id 28) |
| `permission_codename` | `processo_avvia` | **non** `code_manage`: chi può requeue-are un lavoro non è per questo chi può avviare un giro di fatturazione — due fiducie, due decisioni di profilo (analisi D8, D-C) |
| `descrizione` | *Avvio manuale di un processo dall'interfaccia («Esegui ora» su una sveglia)* | |
| `pericolosa` | **`t`** | un click avvia un giro di fatturazione; la conferma a video è il minimo (D-D) |

## 5. Cosa fa il backend, per chi rilegge

Nell'ordine, dopo l'apply (tutto in `analisi-riavvio-processi-da-interfaccia.md`
§9-bis): `comando` in `sveglie.json` e `__COMANDO__` nei template systemd (una
sede); `job_run()` che legge origine e attore dall'ambiente; l'handler
`esegui_processo_default` (whitelist, `abilita`, sottoprocesso a lista con
timeout, esito dall'exit code); l'endpoint con `post_permission =
"processo_avvia"` e `Idempotency-Key` (⚠️ **non su `AdminAPIView`**, che il
`post_permission` non lo legge — §8.2.2); la capability di riga sulle sveglie nel
dettaglio del processo; il pulsante nel drawer. ⚠️ Finché il tipo è
`attivo = false`, `fn_accoda_lavoro` rifiuta: è il cancello giusto, e il
backend chiede l'accensione quando l'handler è in servizio.

## 6. Come si verifica che è arrivato

```sql
SELECT codice, classe, canale, tolleranza_minuti FROM dbops.processi WHERE codice = 'avvio_manuale';
SELECT codice, handler_code, run_as_default, max_tentativi_default, attivo, processo_codice
  FROM dbops.coda_lavori_tipi WHERE codice = 'ESEGUI_PROCESSO';
SELECT permission_codename, area_id, pericolosa FROM config.azioni_processo WHERE permission_codename = 'processo_avvia';
```

Lato backend, le tre righe attese saranno dichiarate in un registro **a
ritiro**, sul modello di `_IN_ATTESA_DI_CATALOGO` in `presidi_repository.py`
(test `test_il_debito_delle_viste_in_attesa_e_rientrato`, diventato rosso in
CI il giorno dell'apply di `dbops.presidi` nominando la riga da togliere):
stesso verso, stessa prova.

## 7. Domande al DB

1. `tolleranza_minuti = NULL` su un processo `attivo` di canale `CODA`: il
   panorama lo tratta come «senza contratto» (come gli altri di coda) o
   pretende un numero?
2. Il guard di classe di `fn_accoda_lavoro` (un lavoro di dominio non si accoda
   come `SISTEMA`) ha qualcosa da dire su `MANUTENZIONE` + `OPERATORE`? Il
   precedente `NOTIFICA_DIGEST_MUTO` è `SISTEMA`: qui l'identità serve
   all'audit, non al perimetro.
3. pgTAP: basta il presidio esistente sui tipi (handler/processo/classe), o
   volete un test che il tipo sia sotto un processo `CODA` e non `PGAGENT`?

*Scritto il 2026-09-14. Nessuna riga di codice applicativo scritta; il
backend parte dopo l'apply, e chiede l'accensione del tipo a handler in
servizio.*

*Aggiornamento 14-09 (sera): il solo pezzo di **deploy** — `comando` in
`sveglie.json` e `__COMANDO__` nei template, §9-bis punto 2 dell'analisi — è
fatto, perché non dipende dalle tre righe. Handler, endpoint e pulsante restano
in attesa dell'apply.*

---

## 8. Risposta del DB — 2026-09-14, sera

> Chi scrive: DB (`dev/db-tid`). Tutto ciò che segue è letto dal **modello**
> (CHECK, funzioni, viste, pgTAP, codice del drenatore), non dalle righe di
> oggi; dove compare un numero è un fatto datato, e sta scritto come tale.

### 8.1 Che cosa regge — le tre domande del §7 hanno già una risposta a DB

**Domanda 1 — `tolleranza_minuti = NULL` su un `CODA`.** Il panorama non lo
«tratta»: lo **impone**. `chk_processi_contratto_solo_command` dice
`canale = 'COMMAND' OR (tolleranza_minuti IS NULL AND segno_di_vita = 'GIORNALE')`,
quindi su `CODA` un numero è un `23514`, non un'opinione. E
`vw_processi_programmazione` mette ogni `CODA` a **`SU_RICHIESTA`** con
`da_guardare = false` (primo ramo del `CASE`, prima ancora di guardare il
contratto), presidiato da `test-vw-processi-programmazione.sql` test 8 e da
`…-da-guardare.sql`. Un processo che «sta bene anche se non gira per mesi» è
esattamente ciò che quel ramo descrive: nessuna riga in più, nessun allarme.

**Domanda 2 — il guard di classe su `MANUTENZIONE` + `OPERATORE`.** Non ha
niente da dire: in `fn_accoda_lavoro` scatta **solo** su
`v_classe = 'DOMINIO' AND v_run_as <> 'OPERATORE'`, e il pgTAP
`test-coda-accoda-classe.sql` test 6 fissa proprio che la manutenzione resta
libera («altrimenti il guard sarebbe una tassa su tutta la coda»). ⚠️ Quello
che invece **morde** è l'altro guard, tre righe sotto: `OPERATORE ⇒ p_scope
NOT NULL` (con il `CHECK chk_coda_lavori_run_as_scope` dietro). E il drenatore
pretende di più del `NOT NULL`: `operator_identity_context` esige la **terna
completa** `auth_user_id` + `username` + `identita_id`, e rilegge che la coppia
(utente, identità) sia **ancora attiva** all'esecuzione
(`E_CODA_SCOPE_OPERATORE_INVALIDO`, `E_CODA_IDENTITA_NON_ATTIVA`). ⇒ Un
superuser Django senza identità `OPERATORE` non può premere il pulsante: il
lavoro nascerebbe e morirebbe in `ERRORE` un minuto dopo. Il rifiuto va
**prima** di accodare, nell'endpoint — è la stessa regola scritta per i giri
di fatturazione. La semantica di `CODA` («lo accoda una persona, l'identità è
la sua») è confermata in tre sedi indipendenti: `vw_processi_dominio_senza_identita`,
`processi_repository._CANALI_CON_IDENTITA` e `test-processi-coda-automatica.sql`
test 6, che rifiuta `CODA` alla fabbrica di identità tecniche.

**Domanda 3 — il pgTAP.** Sì, ma non quello proposto. «`ESEGUI_PROCESSO` sta
sotto un `CODA` e non un `PGAGENT`» pinnerebbe **una riga**; quello che si
presidia è l'**invariante da cui quella riga discende**, e vale per tutti i
tipi presenti e futuri (§8.3). Il presidio esistente sui tipi
(`test-coda-accoda-classe.sql` test 7) guarda solo che il processo ci sia.

**La regola del binding, verificata sul codice e non sul precedente.** Un tipo
`attivo = true` senza handler **non** resta `PENDING`: il drenatore lo claima,
`get_handler` solleva `E_CODA_HANDLER_NON_REGISTRATO`, il lavoro va in
`ERRORE` (con `max_tentativi = 1`, al primo colpo). ⚠️ La doc manuale di
`coda_lavori_tipi` diceva il contrario («può nascere `attivo=true`: i job
restano `PENDING` finché il worker non atterra») — era vera prima che il
drenatore esistesse, ed è corretta in questo cantiere. E l'**ordine** lo fissa
un guardrail del backend, non una convenzione: `test_nessun_handler_orfano`
diventa rosso se il BE registra `esegui_processo_default` **prima** che il tipo
sia a catalogo, `test_ogni_tipo_attivo_ha_un_handler` se il DB lo accende
prima che l'handler ci sia. DB (spento) → BE → DB (acceso): non c'è altro
ordine possibile.

**Le tre righe, provate.** Non solo lette: eseguito in transazione annullata
l'**upsert completo** dei tre CSV come lo farebbe il mirror (§11.2 delle linee
guida, le due specie di mina) più le tre righe nuove — 62 righe esistenti
riscritte senza rifiuti, zero divergenze CSV ↔ DB, le tre nuove accettate da
CHECK, FK e trigger; il panorama risponde `avvio_manuale | CODA | SU_RICHIESTA
| f`; `fn_accoda_lavoro('ESEGUI_PROCESSO', …)` rifiuta con
`E_JOB_TYPE_NON_ATTIVO`, che è il cancello su cui il §5 conta.

### 8.2 ⛔ Tre cose del brief che non reggono

**1. «Il lavoro di coda si registra sotto il processo di questo brief» (§1,
descrizione del §4.1; analisi §4.1-bis e §4.6 «come ogni handler»).** Nessun
handler apre un run, e il drenatore nemmeno *per lavoro*: `draina_coda_lavori`
apre **un** run per **corsa** sotto il proprio processo (origine `CRON`) e
timbra `job_run_id` sui lavori claimati. `FATTURAZIONE_GIRO` e
`FATTURAZIONE_NUMERA` — i due `CODA` in servizio da luglio — hanno **zero**
righe in `job_run_log` (letto il 14-09; i run `PGAGENT` di `guardiano_digest` e
`chiusura_scadenze_daily` sono quelli del *wrapper* pgAgent, non del lavoro).
⇒ L'audit del gesto **esiste**, ma sta in `dbops.coda_lavori`: `scope ->>
'auth_user_id'`, `payload`, `data_insert`, `result`, `job_run_id` della corsa
che l'ha eseguito — leggibile in *Strumenti → Code di lavoro* (con
`?ambito=tutti` per chi ha `code_manage`). Il tab «Ultimi run» di
`avvio_manuale` resterà vuoto, come per i due giri di fatturazione: non è un
difetto, è dove sta l'audit dei lavori di coda. Se un giorno lo si vorrà nel
giornale è una decisione a parte, e va detto che `chk_job_run_log_origine`
ammette `PGAGENT | CRON | COMMAND` — «una persona da API» esiste solo su
`coda_lavori`. La **descrizione** di `avvio_manuale` è riscritta per non
promettere ciò che nessuno scrive.

**2. `AdminAPIView` + `post_permission = "processo_avvia"` (§5; analisi §9-bis
punto 3).** `AdminAPIView` monta `IsAdminZeroERP`, che risponde
SUPER_ADMIN-o-niente e **non legge mai** `post_permission`: con quella base
view l'azione `processo_avvia` è una riga che nessuna porta valuta, e «due
fiducie» (D8, D-C) resta un argomento scritto e non applicato. Il precedente
che il brief cita — `code_manage` — sta su `DomainAPIView(area_funzionale =
"strumenti")`, ed è così che l'azione **conta**. ⚠️ E non è solo il verbo:
`ProcessiListView`, `ProcessiDetailView`, `ProcessiRunView` sono tutte
`AdminAPIView`, quindi un tecnico con `processo_avvia` e senza `SUPER_ADMIN`
non arriva nemmeno al drawer in cui il pulsante starebbe. Il DB semina l'azione
**comunque**: è la sede della fiducia, e `code_manage` fu seminato prima delle
sue view («fino all'apply, fail-closed = solo SUPER_ADMIN»). Ma la scelta va
scritta, ed è di Tid — §8.5.

**3. Il sottoprocesso sincrono e il contratto del drenatore (D-B).** Il
drenatore è un timer oneshot ogni minuto con `tolleranza_minuti = 10` a
catalogo; l'handler aspetta il sottoprocesso fino a 30 minuti. systemd non fa
partire un oneshot mentre l'istanza precedente è attiva ⇒ per tutta la durata
del comando **nessun altro lavoro** viene drenato (fatturazione, avviso del
guardiano), il badge in topbar segna il worker fermo e il panorama dice
`MUTO` su `draina_coda_lavori` — un allarme *vero* su un sistema che sta
facendo quello che gli è stato chiesto. Oggi non morde: i cinque timer con
`abilita = true` finiscono in secondi e i due di fatturazione sono spenti. Ma
il modello lo ammette e il brief stesso scrive «un click avvia un giro di
fatturazione». Da dichiarare nel brief BE, in una delle due forme: o il tetto è
dell'ordine del minuto e un comando lungo **non è un candidato** a «Esegui
ora»; o l'handler non aspetta, e l'esito lo racconta il giornale del comando
(che già lo scrive, con `auth_user_id`). ⚠️ E `STALE_MINUTI_DEFAULT = 30` del
reaper coincide col default di D-B: con `max_tentativi = 1` un lavoro
riconosciuto stantìo va **direttamente** in `ERRORE` mentre il comando magari
sta ancora finendo — un allineamento da scrivere, non da lasciare al caso.
Nota minore, stessa famiglia: la whitelist di `sveglie.json` contiene
`zeroerp-coda-lavori` — «Esegui ora» sul drenatore *dal* drenatore. Da
escludere per forma, come il §4.3 dell'analisi esclude «Riavvia».

### 8.3 Le decisioni del DB, in una riga ciascuna

* **`id`**: `45` per `avvio_manuale` (prossimo libero nel blocco `4x`, dove
  sono atterrati anche `42`–`44`), `35` per `processo_avvia`. Il codice resta
  `snake_case` come `digest_presidi` e `guardiano_digest`: i due `CODA` in
  maiuscolo (`FATTURAZIONE_*`) lo sono perché **nati** come tipi di coda con lo
  stesso nome, e qui il processo non coincide col tipo.
* **Descrizioni** riscritte nella forma dei tre CSV — ASCII, senza apostrofi
  né virgolette tipografiche né backtick — e quella di `avvio_manuale` senza la
  promessa del run (§8.2.1); quella di `ESEGUI_PROCESSO` senza il path
  dell'endpoint, che è la cosa più volatile che si possa scrivere in un
  catalogo (il precedente nomina un *setting*, non una URL).
* **`attivo`**: `false` sul tipo (regola del binding, ora verificata); `t`
  sull'azione — non è un binding, è «assegnabile a un profilo», e
  `test-permessi-strutture-base.sql` conta le attive.
* **`max_tentativi_default = 1`**: accolto, con la conseguenza detta in
  §8.2.3 sul reaper.
* **pgTAP** — `db/pgtap/dbops/test-coda-tipi-canale-e-run-as.sql`, nuovo:
  `CODA ⇒ run_as_default = OPERATORE` (è la *definizione* del canale);
  `PGAGENT ⇒ SISTEMA` (una macchina non ha un nome da prestare: se le serve,
  il canale è `CODA_AUTOMATICA` — è la correzione R-E); `COMMAND` non ospita
  tipi (lo esegue systemd, non il drenatore — ed è la ragione per cui si conia
  `avvio_manuale` invece di appendere il tipo a `draina_coda_lavori`); più la
  terna di questo brief come seed pin, **senza `attivo`**, che si accende e
  un test che lo pinnasse sarebbe rosso sulla riparazione.
* **Nessun guard nuovo** in `fn_accoda_lavoro` per `CODA` + `SISTEMA`: la
  posta è l'audit, non il perimetro come per `DOMINIO`; il seed lo presidia il
  pgTAP e l'enqueue lo scrive il BE con il suo test. Se servirà, ha la stessa
  forma del guard di classe.
* **Nessuna validazione del payload a DB** (`processo_codice`, `unit`): la
  whitelist è del deploy e il DB non conosce le unit — §2 del brief, accolto.
  ⚠️ Vale anche come limite dichiarato: un `processo_codice` inesistente nel
  payload lo scopre l'handler, non un vincolo.

### 8.4 ✅ Fatto e APPLICATO — 2026-09-14, sera

> **Migrazione applicata da Tid e pgTAP verde** (`test-coda-tipi-canale-e-run-as.sql`,
> 6/6 come `zeroerp_app`). Le tre righe sono a catalogo sul dbdev; il tipo
> `ESEGUI_PROCESSO` è **spento** e lo resta finché il backend non dichiara
> l'handler in servizio. Lato DB il cantiere è **chiuso**, salvo l'accensione.
> ⚠️ **Non del tutto (15-09)**: il BE ha chiesto i codici errore del verbo, che
> questo brief non aveva previsto — §9.

* Le tre righe nei CSV: `80_data/sql/dbops/processi.csv` (id 45),
  `80_data/sql/dbops/coda_lavori_tipi.csv` (`ESEGUI_PROCESSO`),
  `80_data/sql/config/azioni_processo.csv` (id 35). **Nessun changeSet**: i
  tre mirror (`20260904-13`, `20260905-01`, `20260228-18`) sono `runOnChange`
  e rileggono il file al prossimo migrate.
* `db/pgtap/dbops/test-coda-tipi-canale-e-run-as.sql` (plan 6), runner `app`: verde pre-apply concatenato all'SQL reso dai tre mirror in transazione annullata, e **mutazione fatta** — tre difetti costruiti (tipo `SISTEMA` sotto un `CODA`, `OPERATORE` sotto un `PGAGENT`, tipo sotto un `COMMAND`), tre rossi che nominano la riga.
* Doc manuali: `dbops/manual/coda_lavori_tipi.md` (tabella dei tipi completa —
  ne elencava due su quattro — e la frase falsa su `attivo=true`),
  `dbops/manual/processi.md` (`avvio_manuale` e il quarto canale
  `CODA_AUTOMATICA`, che il CHECK ammette dal 05-09 e la tabella «I tre
  canali» non nominava), `config/manual/azioni_processo.md`.
* Le tre `SELECT` del §6 (più `SELECT stato, da_guardare FROM
  dbops.vw_processi_programmazione WHERE processo_codice = 'avvio_manuale'`
  → `SU_RICHIESTA | f`) tornano le righe attese: provate sull'SQL reso prima
  dell'apply (§8.1), e il pgTAP le fissa sul vivo (test 5 e 6).

**Che cosa resta, e di chi è:**

| Passo | Di chi | Stato |
| --- | --- | --- |
| handler `esegui_processo_default`, endpoint su `AdminAPIView` (§8.5.1), tetto basso nel sottoprocesso (§8.5.2), capability sulle sveglie | BE | ✅ 15-09 sera (§10.1) — in attesa del deploy sul backend di sviluppo |
| pulsante «Esegui ora» nel drawer del processo (tab «Sveglie») | FE | ✅ 15-09 sera (piano §4.3), scritto sul contratto della capability |
| `registered_job()` (⚠️ il nome vero, non `job_run()`) che legge `ZEROERP_JOB_ORIGINE` / `ZEROERP_JOB_AUTH_USER_ID` (analisi §9-bis punto 3) | BE | ✅ 15-09 (`job_run.py::origine_e_attore_dall_ambiente`, fail-loud sul valore) |
| `attivo = true` su `ESEGUI_PROCESSO`, **dal CSV**, su richiesta del BE a handler in servizio (come `NOTIFICA_DIGEST_MUTO` l'11-09) | DB | ✅ 15-09 **nel CSV** (§11.1, prova verde) — migrate di Tid **dopo** deploy + HUP del BE (§11.4) |
| i cinque codici errore del verbo, nei due CSV del catalogo (§9) | DB | ✅ 15-09, applicati sul dbdev e **in git** (commit `5dd7013fd`, PR #1591 su Tito-dev) |
| `genera_error_policies` + le cinque frasi di ripiego in `error_messages_fallback.py` | BE | ✅ 15-09 sera — il file porta il catalogo **di git**; i due `E_MAG_*` del dbdev sono di un altro cantiere (§10.3) |
| commit di `dev/db-tid` (3 CSV, pgTAP, 3 doc manuali, brief e analisi) | Tid | ✅ 15-09 (`53d5ca923`, PR #1590; codici: PR #1591) |
| a cantiere chiuso: brief in `work-done/` e una riga nel changelog della mappa concentrica (tema «processi automatici») | DB | ⏳ |

### 8.5 ✅ Due domande a Tid — entrambe decise il 14-09, sera

1. ✅ **La porta del verbo** (§8.2.2) — **decisione di Tid, 14-09 sera: (a),
   v1 solo `SUPER_ADMIN`.** Il pannello resta in *Amministrazione*, il verbo
   nasce su `AdminAPIView` come le sue sorelle, e l'azione `processo_avvia`
   è la **sede della fiducia** per il giorno in cui il verbo passerà a
   `strumenti` — non un cancello che oggi qualcuno attraversa. Si semina lo
   stesso (precedente `code_manage`), e questa riga dice perché: chi la
   trovasse a catalogo senza una view che la valuti non deve cercare un
   difetto. ⚠️ Per il BE: `post_permission = "processo_avvia"` sulla view
   admin è **decorativo** e va commentato come tale, o omesso — non deve
   sembrare il presidio. Scartata (b): `DomainAPIView(area_funzionale =
   "strumenti")` per il verbo **e** per il dettaglio che espone le sveglie.
2. ✅ **Comandi lunghi** (§8.2.3) — **decisione di Tid, 14-09 sera: (a),
   solo comandi brevi.** Riformulata qui sotto, perché la prima stesura non
   si capiva. Il pulsante mette un biglietto in coda; il drenatore passa ogni
   minuto, prende il biglietto, lancia il comando e **resta ad aspettare che
   finisca** (fino a 30 minuti, D-B) per leggerne l'esito. Finché aspetta, la
   corsa del minuto dopo non parte: nessun altro biglietto viene lavorato
   (un giro di fatturazione dal cockpit, l'avviso del guardiano), dopo 10
   minuti il badge dice «worker fermo» e il panorama segna il drenatore
   `MUTO` — un allarme su un sistema che sta facendo ciò che gli è stato
   chiesto. Oggi non si nota: i comandi accesi finiscono in secondi. Due
   uscite:
   * **(a) solo comandi brevi** — tetto basso e dichiarato nell'handler
     (pochi minuti); un comando lungo non è candidato a «Esegui ora», e il
     pulsante non compare per lui. ⭐ **Consigliata**: coerente con la 1 e
     con i due timer di fatturazione spenti; zero deploy;
   * **(b) il drenatore non aspetta** — lancia e se ne va, l'esito lo dice il
     giornale del comando (che già lo scrive, con `auth_user_id`). ⚠️ **Non è
     gratis**: `zeroerp-coda-lavori.service` è `Type=oneshot` senza
     `KillMode`, quindi al termine della corsa systemd **uccide i processi
     figli rimasti** (default `control-group`). Servono `KillMode=process`
     nel template più il distacco del figlio (`start_new_session`): un
     cantiere di deploy suo, per il giorno in cui un giro di fatturazione si
     vorrà lanciare dal pulsante.

   ⇒ **Conseguenze per il BE, dalla (a)**: il tetto del sottoprocesso è
   **basso e scritto nell'handler** (pochi minuti, non 30) e un comando che lo
   supera va in `ERRORE` con un messaggio che dice *«troppo lungo per «Esegui
   ora»»*, non in silenzio; con `max_tentativi = 1` l'`ERRORE` è terminale
   e si legge in `vw_coda_lavori_da_guardare`. La capability di riga sulle
   sveglie spegne il pulsante sui comandi che per natura non sono brevi —
   oggi i due di fatturazione, già `abilita = false` (D-A), e il drenatore
   stesso (`zeroerp-coda-lavori`: «Esegui ora» dal drenatore, §8.2.3). La
   (b) resta scritta come strada per quando servirà, con il suo costo di
   deploy. `timeout_minuti` in `sveglie.json` **non rientra**: con un tetto
   unico basso non ha un lettore che lo distingua dal default.

### 8.6 Per il backend, a valle dell'apply

* Lo `scope` di `ESEGUI_PROCESSO` porta la terna completa o l'endpoint risponde
  400 **prima** di `fn_accoda_lavoro` (§8.1, domanda 2); `p_origine = 'API'`
  (default del CHECK di `coda_lavori`).
* ⛔ **Non** aggiungere `PROCESSO_AVVIO_MANUALE` a `apps/core/services/processi.py`:
  `test_ogni_processo_del_backend_ha_una_sveglia` pretende un unit per ogni
  costante di quel modulo, e `avvio_manuale` per definizione non ne ha — e
  non serve, perché nessun run va scritto sotto quel processo (§8.2.1).
* L'accensione è una riga del CSV (`attivo = true` su `ESEGUI_PROCESSO`), a
  carico del DB su richiesta, come per `NOTIFICA_DIGEST_MUTO` l'11-09.
* Fuori da questo brief, ma visto facendo: non esiste un presidio «ogni
  azione di `config.azioni_processo` è valutata da almeno una view» — il
  gemello, per le capability, è la regola *«verificare che il client la
  LEGGA»* di `api.md`. È così che una riga come `processo_avvia` può restare
  decorativa senza che niente lo dica.

---

## 9. Secondo giro — i cinque codici errore di «Esegui ora»

> Richiesta del backend, 2026-09-15 (dal
> [piano BE/FE](piano-be-fe-avvio-manuale-di-un-processo.md) §3.1: *«ogni
> codice nominato in Python deve esistere in `error_policies_generated.py`,
> che è generato dal catalogo»*). Risposta del DB lo stesso giorno, §9.2.

### 9.1 La richiesta, in sintesi

Il predicato *«questa sveglia si può lanciare a mano?»* vive in **Python**
(la whitelist è `sveglie.json`, il DB non conosce le unit — §2 di questo
brief) e lo leggono **tre** consumatori: la capability `can_esegui_ora` nel
dettaglio del processo, il rifiuto dell'endpoint `esegui-ora/`, il ricontrollo
dell'handler `esegui_processo_default`. I primi tre codici sono i **motivi**
di quel predicato; gli ultimi due sono gli **esiti dell'handler**, che non
attraversano HTTP: finiscono in `coda_lavori.ultimo_errore` (terminali,
`max_tentativi = 1`) e si leggono in `vw_coda_lavori_da_guardare`.

| # | Codice | Classe chiesta | Chi lo solleva | `%s` |
| --- | --- | --- | --- | --- |
| 1 | `E_PROCESSO_SVEGLIA_NON_AVVIABILE_A_MANO` | `NON_ESEGUIBILE` (422) | capability · endpoint · handler | unit |
| 2 | `E_PROCESSO_SVEGLIA_NON_ABILITATA` | `NON_ESEGUIBILE` (422) | capability · endpoint · handler | unit |
| 3 | `E_PROCESSO_AVVIO_GIA_IN_CODA` | `CONFLITTO_STATO` (409) | capability · endpoint | unit, id del lavoro |
| 4 | `E_PROCESSO_AVVIO_TROPPO_LUNGO` | `NON_ESEGUIBILE` | handler | unit, secondi del tetto |
| 5 | `E_PROCESSO_AVVIO_FALLITO` | `TECNICO` | handler | unit, exit code |

Condizioni: (1) `forma = servizio` oppure `avvio_manuale = false` nel
dichiarato — vale per il drenatore stesso e per i comandi lunghi per natura,
perché il drenatore aspetta il sottoprocesso (§8.5, decisione 2a); (2)
`abilita = false` su questa installazione (D-A); (3) un lavoro
`ESEGUI_PROCESSO` vivo — `PENDING`/`IN_CORSO`, la definizione di
`uq_coda_lavori_vivo_idem` — con chiave `esegui:<unit>`, incontrato su una
schermata invecchiata (sotto resta la dedup di `fn_accoda_lavoro` per la corsa
fra due click); (4) il sottoprocesso ha superato il tetto dell'handler (300 s)
ed è stato ucciso; (5) `run-command.sh <comando>` è uscito con exit ≠ 0, e la
diagnosi sta nel run del comando (origine `COMMAND`, con l'utente di chi ha
premuto), non qui.

Si **riusano**, perché la condizione è la stessa: `E_VALIDATION_INPUT` (unit
assente o non fra le sveglie del processo, `campo = unit`),
`E_CODA_SCOPE_OPERATORE_INVALIDO` (terna incompleta, detta **prima** di
accodare), `E_CONFIG_MANCANTE` (`run-command.sh` assente),
`E_PROCESSO_NON_TROVATO`, `E_JOB_TYPE_NON_ATTIVO`.

### 9.2 ✅ Risposta del DB — seminati, 2026-09-15

**Cinque righe in ciascuno dei due CSV del catalogo, nessun changeSet**: il
mirror `20260614-08` è `runOnChange` + `validCheckSums: ANY` e rilegge i file al
prossimo migrate. `config/codici_errore.csv` porta identità, classe e la
`note` per chi legge `error_policies_generated.py` (dove quella nota diventa
il commento sopra la voce); `config/messaggi_errore.csv` porta frase, causa e
soluzione con **id 1067–1071**, in quest'ordine.

| # | Codice | Classe a catalogo | id msg | `%s` |
| --- | --- | --- | --- | --- |
| 1 | `E_PROCESSO_SVEGLIA_NON_AVVIABILE_A_MANO` | `NON_ESEGUIBILE` (422) | 1067 | 1 |
| 2 | `E_PROCESSO_SVEGLIA_NON_ABILITATA` | ⛔ **`NON_DISPONIBILE` (501)** — non `NON_ESEGUIBILE` | 1068 | 1 |
| 3 | `E_PROCESSO_AVVIO_GIA_IN_CODA` | `CONFLITTO_STATO` (409) | 1069 | 2 |
| 4 | `E_PROCESSO_AVVIO_TROPPO_LUNGO` | `NON_ESEGUIBILE` (422) | 1070 | 2 |
| 5 | `E_PROCESSO_AVVIO_FALLITO` | `TECNICO` (500) | 1071 | 2 |

**La sola divergenza, ed è di classe: il 2 nasce `NON_DISPONIBILE`.** Il
catalogo delle classi (`classi_errore.csv`) definisce `NON_DISPONIBILE` come
*«la funzione esiste ma non è servita: è spenta»* e `NON_ESEGUIBILE` come *«la
richiesta si capisce ma non si può eseguire: una configurazione che non regge
a quella data»*. `abilita = false` è la prima cosa, non la seconda: la sveglia è
nel dichiarato, il comando esiste, su questa installazione **non lo serve
nessuno** — né il timer né a mano — e la configurazione non «non regge», è
spenta di proposito. È la famiglia di `E_JOB_TYPE_NON_ATTIVO` (tipo di coda
spento dal seed, la cui nota dice *«funzione presente ma non servita»*),
`E_AI_DISABLED`, `E_SHOP_NON_DISPONIBILE` — e il rimedio è **lo stesso** di
`E_JOB_TYPE_NON_ATTIVO`, che sullo stesso endpoint risponde già 501: una
release, non un click. Il 1 invece resta `NON_ESEGUIBILE`: non è spento, è *per
natura* non candidato — un limite dichiarato dell'attrezzo, che nessuna
release accende senza cambiare una decisione di progetto. ⚠️ Per il BE e il FE
non cambia niente: `ui_action` è `show_error_banner` in entrambe le classi, il
tooltip legge la `reason_key`, la classe arriva dal file generato. Cambia
**solo** lo status del rifiuto (501 invece di 422). Se Tid preferisce la
classe chiesta, è una cella del CSV e una rigenerazione — ma allora andrebbe
riletto anche `E_JOB_TYPE_NON_ATTIVO`, che sullo stesso verbo dice l'altra cosa.

**Le frasi.** Scritte per chi le legge — in v1 un `SUPER_ADMIN` nel drawer del
processo o nel pannello delle code — nella forma del catalogo: messaggio con i
`%s` che il BE riempie (unit; unit e id del lavoro; unit e secondi; unit e exit
code), `causa` che dice da dove viene il fatto, `soluzione` che dice cosa fare
adesso — e per i due esiti dell'handler *dove andare a leggere* (il run del
comando nel tab «Ultimi run» del processo eseguito). ⚠️ Nella `causa` del 2
*«oggi i due timer di fatturazione, spenti perché l'invio SDI è sospeso»* è un
fatto datato al 15-09, scritto come esempio e non come regola. ⚠️ Il termine
«reaper» non compare nelle frasi (soluzione del 3: *«se resta fermo troppo a
lungo il sistema lo chiude da solo come stantio»*): è il nome del meccanismo,
non una cosa che la persona vede.

**Che cosa è provato, e come.** Non un pgTAP: nessuna funzione del database
solleva questi codici, quindi i test 2, 4 e 5 di
`test-catalogo-messaggi-errore-completo.sql` (che leggono `pg_proc`) non li
vedono **per costruzione**, e il test 3 (nessun doppione per `(codice,
lingua)`) li copre come tutti gli altri. La prova è quella prescritta per un
mirror CSV (linee-guida-sql §11.2): l'SQL del mirror `20260614-08` reso
**offline** (`updateSQL`, su una copia senza `preConditions`) ed eseguito su
dbdev in una transazione annullata — upsert completo dei tre CSV, **864 codici
e 859 messaggi** riscritti senza rifiuti, le cinque righe nuove accettate da
FK (`classe`), CHECK (`note` su una riga) e PK; dopo il `ROLLBACK` zero righe
sul vivo e nessuna sessione appesa in `DblinkGetResult` (la trappola
dell'upsert completo vale solo con un pgTAP nella stessa transazione — qui non
c'è). Segnaposto passati al setaccio (ogni `%` seguito da `s`), conteggio dei
`%s` = arità dichiarata dal BE (1/1/2/2/2), id unici, `git diff --numstat` =
sole righe appese (niente CRLF, niente ri-quotatura).

**Che cosa resta, e di chi è** (anche nella tabella di §8.4):

| Passo | Di chi |
| --- | --- |
| migrate dei CSV su dbdev (il mirror rilegge da sé) e commit di `dev/db-tid` | Tid |
| `manage.py genera_error_policies` + cinque frasi **senza segnaposto** in `error_messages_fallback.py` (`test_ogni_codice_vivo_ha_un_messaggio_di_ripiego`) — e finché non è fatto, a migrate avvenuto `test_error_policies_divergenza_db` (CI, `ZEROERP_TEST_DB_E2E=1`; a mano `genera_error_policies --check`) è rosso perché il file committato non è più quello che `config.vw_codici_errore_identita` produce, e `test_error_codes_declared_guardrail` (AST, senza DB) rifiuta i cinque codici appena nominati in Python finché il file non li porta: è il verso giusto, non un difetto. ⚠️ `dbops.vw_codici_errore_da_dichiarare` **non** li vede e non deve: legge i corpi plpgsql, e questi codici a database non li solleva nessuno | BE |
| ⚠️ nel `VARIADIC`/nei valori entrano **unit, id, secondi, exit code** — mai il nome di un parametro (AGENTS.md §«tre canali, tre destinatari») | BE |
| `attivo = true` su `ESEGUI_PROCESSO`, dal CSV, a handler in servizio (§8.6) | DB, su richiesta |

---

## 10. Risposta del BE — 2026-09-15, sera

> Chi scrive: backend (`dev/backend-tid`). Il dettaglio passo per passo, i
> test e le decisioni per esteso stanno nel
> [piano BE/FE](piano-be-fe-avvio-manuale-di-un-processo.md) (§0-bis per lo
> stato, §3 per le decisioni). Qui c'è ciò che il DB deve sapere per chiudere
> il suo lato.

### 10.1 Stato, in una riga per pezzo

| Pezzo | Stato |
| --- | --- |
| `registered_job` legge origine e attore dall'ambiente (`ZEROERP_JOB_ORIGINE`, `ZEROERP_JOB_AUTH_USER_ID`), fail-loud su un valore fuori vocabolario | ✅ |
| `avvio_manuale` **obbligatorio** in `sveglie.json` (§10.2, decisione 1) | ✅ |
| `lavori_vivi_per_chiave` nel repository della coda (`STATI_VIVI` sede unica) | ✅ |
| BB `scope_operatore_da_request` (§10.2, decisione 4) | ✅ |
| costanti e tetto (`avvio_manuale.py`, 300 s pinnati ai due limiti del repo) | ✅ |
| predicato `motivi_esegui_ora`, handler `esegui_processo_default` (registrato in `CoreConfig.ready()`), verbo `POST processi/<codice>/esegui-ora/`, capability `sveglie[]` nel dettaglio, policy rigenerate + cinque ripieghi, test (unit, API, DB provvisto) | ✅ 15-09 sera — 1607/1609 verdi, i due rossi sono i due `E_MAG_*` di §10.3 |
| FE: tab «Sveglie» nel drawer del processo, pulsante, conferma, toast, i18n | ✅ |
| accensione di `ESEGUI_PROCESSO` | ⏳ la chiede il BE a handler in servizio (§10.4) |

### 10.2 Le decisioni del piano che toccano anche il DB

1. **«Non candidato» ha una sede, ed è il dichiarato di deploy.** La
   decisione 2a di §8.5 («solo comandi brevi») aveva bisogno di un posto in
   cui *«questa sveglia non si lancia a mano»* fosse scritto: `abilita = false`
   copriva i due timer di fatturazione **per coincidenza**, e il giorno in cui
   si accendono il pulsante si sarebbe acceso con loro. Da qui `avvio_manuale`
   obbligatorio su ogni voce di `sveglie.json` (`false` sul drenatore, sui due
   di fatturazione e sul listener; `true` su digest ×2, email, coda stampa).
   ⚠️ Non tocca `dbops.processi`: è un fatto del deploy, come la cadenza.
2. **Il «registro a ritiro» del §6 non serve più**: l'apply è avvenuto, e il
   verso di ritiro che il DB stesso ha nominato (`test_nessun_handler_orfano`)
   esiste già. Resta un test **su DB provvisto** che fissa le tre righe come le
   legge il backend (piano §5.4).
3. **`post_permission = "processo_avvia"` non si scrive sulla view** (decisione
   1 di §8.5: v1 solo `SUPER_ADMIN`). Si scrive il **commento** che dice dov'è
   la sede della fiducia: un attributo che sembra un cancello e non lo è
   sarebbe peggio di nessun attributo. `processo_avvia` resta per scelta la
   prima riga «decorativa» di `config.azioni_processo`; il presidio «ogni
   azione è valutata da almeno una view» è un cantiere suo (§8.6).
4. **«Già in coda»: entrambi, con ruoli diversi.** La capability spegne il
   pulsante e l'endpoint rifiuta con 409 su una schermata invecchiata;
   `fn_accoda_lavoro` resta la rete per la corsa fra due click. Un endpoint che
   assorbisse in silenzio direbbe «accodato» a chi non ha accodato niente.
5. **Il BB dello scope operatore** (`scope_operatore_da_request`) è stato
   estratto da `_accoda_job_fatturazione` alla seconda occorrenza (ok Tid).
   ⚠️ Effetto collaterale dichiarato: su un percorso **vivo** (il giro di
   fatturazione dal cockpit) la terna mancante risponde ora
   `E_CODA_SCOPE_OPERATORE_INVALIDO` e non più `E_VALIDATION_INPUT` — stesso
   400, codice che dice *di che cosa*.
6. **Le `reason_key` le ha fissate il FE** (piano §2.5), nella forma già in uso
   per le check del DB: `amministrazione.processi.esegui_ora_blocco.{non_avviabile_a_mano,
   non_abilitata, gia_in_coda}`; la terza porta `{job_id}` nel `dettaglio`.
7. Il nome vero della registrazione run è **`registered_job`**, non `job_run()`
   (analisi §9-bis punto 3): corretto nelle righe di §8.4.

### 10.3 La rigenerazione, e i due codici che non sono di questo cantiere

I cinque codici sono in git dal 15-09 (PR #1591) e il file generato li porta.
⚠️ **Fatto datato, 15-09 sera**: sul dbdev `config.vw_codici_errore_identita`
porta anche `E_MAG_MOVIMENTO_VERSO_INCOERENTE` e
`E_MAG_TRASFERIMENTO_EMITTENTI_DIVERSI` (seminati lo stesso giorno da `titodb`,
sollevati da due trigger di `magazzino`), che **non sono in nessun branch**.
Rigenerare «come viene» avrebbe agganciato il ramo BE a un seed non mergiato —
e la CI, che ricostruisce il DB da git, avrebbe visto il file **avanti** —
quindi il file generato porta il catalogo **di git**, cioè senza quelle due
righe. Finché il cantiere magazzino non le committa, sul dbdev
`genera_error_policies --check` e `test_error_policies_divergenza_db` restano
rossi **per quei due**, e questo è il verso giusto: il primo commit di
`dev/db-tid` con i due CSV li fa rientrare da soli. Non è una richiesta al DB:
è un promemoria di dove sta la divergenza, perché il rosso non venga letto
come un difetto di questo cantiere.

> ⚠️ **Aggiornamento DB, 15-09 (dopo la PR #1593)**: i due codici **sono in
> git** — `dev/db-tid` e `Tito-dev`. Il rosso si chiude con la prossima
> rigenerazione BE, non con un commit DB: §11.3.

### 10.4 Chiusura — cosa chiede il BE, e quando

> ✅ Fatto il 15-09: accensione applicata dal DB (§11), collaudo in-app la
> sera stessa — il resoconto è nel piano, §4.4.

A handler in servizio sul backend di sviluppo (deploy + `kill -HUP` al master:
gunicorn dev non ricarica da sé): **`attivo = true` su `ESEGUI_PROCESSO` dal
CSV**, come per `NOTIFICA_DIGEST_MUTO` l'11-09. Poi il collaudo in-app (piano
§4.4.2) su `zeroerp-digest-presidi-giornaliero`: lavoro `FATTO` in *Code di
lavoro*, run `digest_presidi:giornaliera` con `origine = COMMAND` e lo username
di chi ha premuto, panorama `avvio_manuale | SU_RICHIESTA | f`.

---

## 11. Terzo giro — l'accensione (2026-09-15)

> Chi scrive: DB (`dev/db-tid`). Il BE è su `Tito-dev` dalla PR #1592
> (commit `337c255fb`) e chiede l'accensione (§10.4). Qui il lato DB: la
> cella del CSV, la prova, che cosa **non** cambia, i due fatti che il BE ha
> lasciato al DB, e che cosa resta a Tid — nell'**ordine** in cui va fatto.

### 11.1 ✅ Acceso nel CSV — una cella, nessun changeSet

* `80_data/sql/dbops/coda_lavori_tipi.csv`: `attivo` `false → true` su
  `ESEGUI_PROCESSO`, e la descrizione registra data e motivo nella forma di
  `NOTIFICA_DIGEST_MUTO` dell'11-09 — *«Nato attivo=false (…) e ACCESO il
  2026-09-15 su richiesta del backend, che dichiara l handler
  esegui_processo_default registrato in CoreConfig.ready() (…); se l handler
  non fosse registrato nel backend in servizio, il lavoro finirebbe in ERRORE
  al primo claim (un solo tentativo) e lo direbbe vw_coda_lavori_da_guardare»*.
  Il mirror `20260905-01` è `runOnChange` e rilegge il file al migrate.
* Letto sul **modello** prima di toccare: sulla tabella ci sono solo i trigger
  di audit e `tx_id` e i due CHECK (`max_tentativi`, `run_as_default`) —
  nessun guard sull'attivazione. Il cancello che l'accensione apre è **uno**,
  `IF NOT v_tipo.attivo` in `fn_accoda_lavoro` (`E_JOB_TYPE_NON_ATTIVO`,
  §8.1). Che l'handler sia registrato in `CoreConfig.ready()` è letto dal
  codice arrivato con la PR (`apps/core/apps.py`), non dal messaggio.
* **Prova** (linee-guida-sql §11.2): SQL del mirror **reso** offline
  (`updateSQL`, copia senza `preConditions`) ed eseguito su dbdev in
  transazione annullata — `ESEGUI_PROCESSO` `f → t` (descrizione 760 → 1182
  char), le altre quattro righe identiche, cinque righe in tutto, nessun tipo
  spento; dopo il `ROLLBACK` il vivo è ancora `f`. ⚠️ **Senza** chiamare
  `fn_accoda_lavoro` nella prova: un rifiuto passa da
  `fn_log_and_raise_error` → `dblink` e lascerebbe una riga in
  `dbops.error_log` anche dopo il rollback.

### 11.2 Che cosa NON cambia, e perché

* `db/pgtap/dbops/test-coda-tipi-canale-e-run-as.sql`: **intatto**. I test
  5 e 6 pinnano handler, `run_as`, tentativi e processo **senza `attivo`** —
  scelta scritta nell'intestazione del file il 14-09 proprio per questo
  giorno (*«un test che lo pinnasse sarebbe rosso sulla riparazione»*).
  Niente da aggiornare nello stesso commit, e niente da rieseguire per
  questa modifica.
* Doc manuale `dbops/manual/coda_lavori_tipi.md`: il precedente e la riga in
  tabella dicono ora «nato spento il 14-09, acceso il 15-09», e la regola del
  binding porta l'ordine DB (spento) → BE → DB (acceso) con la nota che
  l'accensione è **una cella**, da applicare **dopo** il deploy.
* `processi.md`, `azioni_processo.md`, `processi.csv`,
  `azioni_processo.csv`: niente — l'accensione non li tocca.

### 11.3 Due fatti lasciati dal BE, letti dal DB

**I cinque codici (id 1067–1071) li solleva Python, non
`fn_log_and_raise_error`.** Identità, classi e `%s` (1/1/2/2/2) sono quelli
che il BE usa: niente da rifare. ⚠️ Ma il BE compone la frase **con i valori
dentro** (unit, id del lavoro, secondi, exit code) e il client legge la
`reason_key`: **il testo a catalogo e la `soluzione` non li rende nessuno a
runtime** — un `ServiceError` Python non porta `hint`, e il canale `HINT`
esiste solo per un errore nato in PL/pgSQL (api.md §Envelope). Per questi
cinque il catalogo è quindi **la sede dell'identità e della classe** (da cui
il file generato deriva status e `ui_action`) e **la doc per chi legge
`dbops.error_log`** — non il messaggio a video. ⭐ È lo stato di ogni codice
«sollevato in Python» già a catalogo (la `note` di ciascuno dei cinque lo
dichiara), e la §9.2 lo diceva in negativo (*«nessuna funzione del database
solleva questi codici»*): qui sta scritto in positivo, perché chi rilegge la
`soluzione` dei cinque non cerchi dove compaia a video. Se un giorno il BE
vorrà rendere la `soluzione` anche sui codici nati in Python, la sede è il
traduttore (una lettura dal catalogo, per codice), non una copia in Python —
la stessa ragione per cui `hint` è arrivato all'envelope il 18-08. Fuori da
questo cantiere.

**I due `E_MAG_*` — correzione datata del §10.3.**
`E_MAG_MOVIMENTO_VERSO_INCOERENTE` e `E_MAG_TRASFERIMENTO_EMITTENTI_DIVERSI`
**sono in git**: `dev/db-tid` dal commit `937acd83a` (15-09, cantiere
magazzino lotto 1) e `Tito-dev` dalla PR #1593, mergiata **dopo** la #1592
del BE. `error_policies_generated.py` su `Tito-dev` non li porta ancora (zero
occorrenze, letto il 15-09): il rosso di `genera_error_policies --check` /
`test_error_policies_divergenza_db` si chiude con la **prossima rigenerazione
BE**, non con un commit DB — come il §10.3 stesso prevedeva. Nessuna azione
lato DB.

### 11.4 Che cosa resta, e di chi è — nell'ordine

| # | Passo | Di chi | Stato |
| --- | --- | --- | --- |
| 1 | deploy del BE sul backend di sviluppo + `kill -HUP` al master (gunicorn dev non ricarica da sé, §10.4) | Tid | ⏳ **prima** del 2 |
| 2 | `make db-migrate` su dbdev: il mirror `20260905-01` rilegge il CSV e accende il tipo. Verifica: `SELECT codice, attivo FROM dbops.coda_lavori_tipi WHERE codice = 'ESEGUI_PROCESSO'` → `t` | Tid | ⏳ **dopo** l'1 — invertiti, `test_ogni_tipo_attivo_ha_un_handler` è rosso nel verso sbagliato (§8.1) |
| 3 | pgTAP `test-coda-tipi-canale-e-run-as.sql` (6/6, invariato) | Tid | ⏳ |
| 4 | collaudo in-app (piano §4.4.2) su `zeroerp-digest-presidi-giornaliero`: lavoro `FATTO` in *Code di lavoro*, run `digest_presidi:giornaliera` con `origine = COMMAND` e lo username di chi ha premuto, panorama `avvio_manuale \| SU_RICHIESTA \| f` | BE / Tid | ⏳ |
| 5 | commit di `dev/db-tid` (CSV, doc manuale, brief) | Tid | ⏳ |
| 6 | a collaudo fatto: brief in `work-done/` e una riga nel changelog della mappa concentrica (tema «processi automatici») | DB | ⏳ |

*Scritto il 2026-09-15. Lato DB il cantiere è chiuso: ciò che resta è
l'apply nell'ordine detto, il collaudo e l'archiviazione.*
