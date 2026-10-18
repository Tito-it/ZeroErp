# Brief DB — Il presidio dei job falliti manda tutto al sistemista

## ⏭️ Chi riparte — aggiornato al 2026-10-16

**Riparte: team BE** (tramite Tid): §4.2 e D9 (§10.3). Lato DB il codice di D9 è nel
registro (2026-10-17, §11.3): si applica col mirror dei due CSV, ed è da committare. ✅ Giro 1 (§8) e giro 2 (§11) applicati, pgTAP senza
regressioni.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | Tid | ✅ via allo sviluppo e D1–D6 (2026-10-16) | §6 | — |
| 2 | team DB | ✅ changeSet `20261016-34…43`, CSV, pgTAP, doc (2026-10-16) | §8 | — |
| 3 | Tid | ✅ provision-post e migrate applicati, pgTAP senza regressioni (2026-10-16) | §8.3, §8.4 | — |
| 4 | team BE | `registered_job`: SQLSTATE al nono argomento e codice `E_` dei P0001 in `error_code` | §4.2 | — |
| 5 | team DB | ✅ censimento D7 scritto (2026-10-16); Tid lo fa confermare al BE | §9 | — |
| 5b | Tid | ✅ D8 in questo brief, D9 proposta accettata (2026-10-16) | §9.4 | — |
| 7 | Tid | ✅ via allo sviluppo del giro 2 (2026-10-16) | §10 | — |
| 8 | team DB | ✅ giro 2 D8 scritto e provato (`20261016-44…53`); codice di D9 in attesa del nome dal BE | §11 | — |
| 8b | Tid | ✅ migrate del giro 2 applicato, pgTAP senza regressioni (2026-10-16) | §11 | — |
| 10 | team DB | ✅ codice di D9 nel registro (+ messaggio), nome dal BE: `E_JOB_ELEMENTI_NON_COMPLETATI` (2026-10-17) | §11.3 | — |
| 11 | Tid | ✅ collaudo lato DB (2026-10-17); resta il digest stampato e le fasi dopo BE; poi archiviazione | §5 | 4, 9, 10 |
| 9 | team BE | D9: una corsa con elementi falliti senza registro chiude rossa | §10.3 | 8 |
| 6 | Tid | collaudo: digest `--secco` con un rosso per causa | §5 | 3, 4 |

Decisioni aperte di Tid: nessuna. Lavoro da committare: il giro 2 (§11) e il §10-§11
di questo brief.
Debito noto, non in questo brief: il `%TYPE` mancato del giro 1 (§10.1-bis). Lavoro fatto: tutto
committato (`2793096a6`, 2026-10-16).

---

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-10-16. **A chi:** Tid; ricaduta al
> team BE al §4.2.
> **Origine:** analisi del 2026-10-16 su `maintenance.vw_job_run_da_guardare`.
> **Filone:** è lo stesso difetto che `work-done/brief-db-presidio-processi-testo-per-causa.md`
> ha chiuso per `dbops.vw_processi_programmazione_da_guardare`. Si usa lo stesso
> meccanismo, e non se ne costruisce uno nuovo.

## 1. Il difetto

In `dbops.presidi` il presidio `maintenance.vw_job_run_da_guardare` ha
`chi_agisce = SISTEMISTA` e `colonna_variante = NULL`, cioè **un solo destinatario
per tutte le righe**. Le righe della vista però sono guasti di natura diversa:

| Un job fallisce perché… | A chi tocca davvero |
| --- | --- |
| il disco è pieno, la connessione è caduta, Postgres è stato riavviato | chi gestisce il server |
| il processo è stato ucciso (OOM, riavvio) e la corsa è rimasta aperta | chi gestisce il server |
| a un ruolo manca un diritto (es. `E_STATISTICHE_MANCANTI`: il rimedio è `pg_maintain` al ruolo del job) | chi gestisce il database |
| lo smoke notturno trova regressioni (`SMOKE_REGRESSIONI`) | lo sviluppo |
| un errore di logica in una funzione | lo sviluppo |

Con `SISTEMISTA` fisso, il digest manda al sistemista anche i guasti dello
sviluppo. Il testo del presidio (`presidi_testi`, variante NULL) prova a
rimediare a parole («se riguarda il server avvisa il sistemista, altrimenti lo
sviluppo»), ma il **gruppo** in cui il digest mette la voce resta sbagliato.

## 2. Perché non basta dichiararlo per processo

Una prima idea (2026-10-16) era: «lo stesso processo, se fallisce, va sempre alla
stessa persona: lo si dichiara in `dbops.processi` e la vista lo espone come
causa». **Sul modello non regge da solo.** Un disco pieno o una connessione
caduta possono far fallire **qualunque** processo, compreso `smoke_notturno`. Se
il destinatario dipendesse solo dal processo, lo smoke caduto per il disco pieno
andrebbe allo sviluppo: l'errore cambierebbe solo riga.

A chi tocca dipende da **due cose, in quest'ordine**:

1. **la natura del guasto**: se è dell'ambiente (server, connessione, risorse), il
   processo non conta;
2. **di chi è il processo**, solo quando il guasto non è dell'ambiente.

⛔ Scartato anche il destinatario **per codice d'errore** preso uno per uno: è un
vocabolario aperto, e un codice nuovo senza destinatario finirebbe in «Senza
indicazione di chi agisce». Il §3.2 usa invece le **classi** SQLSTATE, che sono
un vocabolario chiuso e standard.

## 3. I segnali che il modello già offre

### 3.1 La corsa rimasta aperta

Il motivo «presa e mai chiusa» vuol dire che il processo è morto senza arrivare
al gestore d'eccezione: kill, OOM, riavvio. È un guasto **dell'ambiente per
natura**, qualunque sia il processo.

### 3.2 Lo SQLSTATE — ✅ verificato il 2026-10-16: c'è solo per i job del database

* **Job pgAgent** (`maintenance.fn_run_and_log`): `error_code` è lo SQLSTATE
  (`GET STACKED DIAGNOSTICS … RETURNED_SQLSTATE`). Le classi dell'ambiente sono
  standard: `08` connessione, `53` risorse insufficienti (disco, memoria), `57`
  intervento dell'operatore (shutdown), `58` errore di sistema.
* **Command del backend** (`backend/apps/core/services/job_run.py`,
  `registered_job`): `error_code = str(getattr(exc, "code", type(exc).__name__))`.
  Quindi:
  * con un `ServiceError` o un'eccezione che porta un `code` (es. `GiroSmokeFallito`)
    si ha il **codice applicativo** (`SMOKE_REGRESSIONI`, `SMOKE_GIRO_FALLITO`);
  * con un errore del database si ha il **nome della classe Python** del wrapper
    Django (`OperationalError`, `InterfaceError`…). **Lo SQLSTATE si perde**: un
    disco pieno e una connessione caduta lato command non si distinguono da
    `error_code`;
  * con un errore di sistema non-DB (`OSError`, `ConnectionError`,
    `TimeoutError`…) si ha il nome della classe Python.
* ⚠️ `SMOKE_GIRO_FALLITO` copre sia il tetto di tempo sia lo script uscito con
  codice 2. Può essere un guasto dell'ambiente come un difetto: da solo non decide.

### 3.3 Il motivo «intermittente» guarda la riga sbagliata

Per gli intermittenti l'ultima corsa è **verde** e il suo `error_code` è NULL. La
natura del guasto si legge dall'**ultimo rosso** del job, che oggi la vista non
espone.

### 3.4 `processo_codice` può mancare

`maintenance.job_run_log.processo_codice` è nullable. Senza un ripiego dichiarato
la riga darebbe causa NULL, e il digest direbbe «la riga non dice la sua causa».

## 4. La proposta

### 4.1 Lato DB

**Cause** a vocabolario chiuso, in `presidi_cause.csv`, ognuna col suo testo in
`presidi_testi.csv` (nomi definitivi: D3):

| Causa | `chi_agisce` | Quando |
| --- | --- | --- |
| `AMBIENTE` | `SISTEMISTA` | corsa rimasta aperta; oppure SQLSTATE di classe `08`/`53`/`57`/`58` |
| `PROGRAMMA` | `SVILUPPO` | tutto il resto, se il processo dichiara così (ed è il ripiego senza processo) |
| `CONFIGURAZIONE` | `AMMINISTRATORE` | solo se D1 = sì |

**Regola nella vista**, nell'ordine:

1. «presa e mai chiusa» → `AMBIENTE`;
2. `error_code` dell'**ultimo rosso** con classe SQLSTATE dell'ambiente → `AMBIENTE`;
3. altrimenti → la causa che **il processo dichiara** per i suoi fallimenti;
4. riga senza processo → `PROGRAMMA`: un job che scrive nel giornale senza un
   codice di catalogo è già una lacuna del programma.

**In `dbops.processi`** una colonna nuova, **NOT NULL**, con FK verso il
vocabolario (D4): «di che natura sono i miei fallimenti quando l'ambiente è
sano». Un processo nuovo non può nascere senza dichiararla.
⚠️ *Rev 2026-10-16, in sviluppo:* l'esempio di `analyze_statistiche` («dichiara
`AMBIENTE`») si è spostato sul **codice**: `E_STATISTICHE_MANCANTI` dichiara
`AMBIENTE` in `config.codici_errore`, perché è quell'errore a chiedere un diritto
al ruolo. Un difetto della funzione di analisi resta `PROGRAMMA`, come il
processo.

⚠️ La colonna **non** è una FK verso `presidi_cause`, che è chiavata
`(vista, causa)`. La coerenza fra vocabolario e cause del presidio la tiene un
pgTAP.

**In `presidi.csv`**: `colonna_variante = causa`. `chi_agisce` del presidio resta
valorizzata, perché `chk_presidi_chi_agisce_se_allarma` la vuole; diventa il
destinatario del testo generale, come per il presidio dei processi. La nota
del presidio va riscritta: oggi spiega perché `colonna_stato` è NULL, e quella
ragione resta valida.

**pgTAP**, sul modello di `test-presidio-processi-testo-per-causa-v1.sql`:

* le cause a catalogo sono **esattamente** quelle che la vista può produrre;
* ogni valore della colonna nuova di `processi` è una causa del presidio;
* i quattro rami della regola, **costruiti** con righe di giornale fabbricate
  nel test, non pescati dal giornale di dbdev (regola zero, corollario sui test);
* l'intermittente prende la causa dall'ultimo rosso, non dall'ultima corsa.

Prima di scrivere si censiscono i lettori della vista (`vw_job_run_da_guardare`):
la colonna nuova va **in coda** per non rompere chi legge per posizione.

### 4.2 Lato BE — richiesta (D2 = sì; forma aggiornata dalla variante B)

In `registered_job` (`backend/apps/core/services/job_run.py`), quando l'eccezione
è un errore del database:

1. passare lo **SQLSTATE** (psycopg 3: lo porta la causa dell'eccezione Django,
   `exc.__cause__.sqlstate`) come **nono argomento** `p_sqlstate` di
   `script.fn_job_run_end` (`20261016-40`). Senza, per i command il §3.2 non vede
   mai l'ambiente e la regola cade sul codice o sul processo;
2. *(aggiunto dal censimento del §9, 2026-10-16)* per un `P0001` scrivere in
   `error_code` il **codice `E_`** e non `InternalError`. È la stessa regola che
   `fn_run_and_log` applica dal `-38` (D5), e il BB c'è già:
   `apps/core/services/db_error_fields.structured_db_error_code`. Senza, un errore
   di dominio sollevato dal database dentro un command arriva al giornale come
   nome di classe, e `config.codici_errore.causa_fallimento` non lo vede.
⚠️ La chiamata a otto argomenti continua a funzionare (default `NULL`): il BE può
arrivare dopo l'apply senza rompere niente.

Resta aperto, e lo decide il BE: gli errori di sistema non-DB (`OSError`,
`ConnectionError`). Si possono riconoscere per classe Python, ma è una tassonomia
loro.

Il digest **non** dovrebbe richiedere modifiche: `_voci_per_causa` e il raggruppamento
per `chi_agisce` sono già generici. Da confermare sul pannello prima di dirlo chiuso.

### 4.3 Quanto costa l'amministratore (stima del 2026-10-16)

**Il punto.** Un guasto «da amministratore» si riconosce dall'**errore**, non dal
processo: `send_pending_emails` può fallire per una password sbagliata nelle
impostazioni (amministratore) o per un difetto (sviluppo). Serve quindi un segnale
**per codice d'errore**. Oggi il giornale non lo conserva, e lo perde in due modi
opposti:

| Chi scrive la corsa | Cosa finisce in `error_code` | Cosa si perde |
| --- | --- | --- |
| job del database (`maintenance.fn_run_and_log`) | lo SQLSTATE: per un errore di dominio è sempre `P0001` | il **codice di dominio**, che `script.fn_log_and_raise_error` mette nel canale `CONSTRAINT` dell'eccezione e che `GET STACKED DIAGNOSTICS` non legge |
| command del backend (`registered_job`) | il codice applicativo, oppure il nome della classe Python | lo **SQLSTATE** (§3.2) |

**Variante A: solo la causa, decisa per processo.** Costa quasi niente: un
valore in più nel vocabolario, una riga in `presidi_cause.csv` e una in
`presidi_testi.csv`. ⛔ Però sbaglia proprio il caso per cui esiste: un processo
che fallisce **anche** per difetti non può dichiararsi «da amministratore». È
una causa che di fatto nessuno potrebbe dichiarare. **Sconsigliata.**

**Variante B: il segnale per codice.** Sono quattro pezzi:

1. **Il giornale tiene i due segnali separati.** `maintenance.job_run_log`
   riceve una colonna nuova per lo SQLSTATE, e `error_code` resta il codice di
   dominio o applicativo. Si toccano così:
   * `maintenance.fn_run_and_log`, che legge anche `CONSTRAINT_NAME`;
   * `maintenance.fn_job_run_log_failure` e `script.fn_job_run_end`, ciascuna
     con un parametro **in coda**.

   Censiti il 2026-10-16: 12 file nominano `fn_job_run_end`, 9 nominano
   `fn_job_run_log_failure`, 25 nominano `fn_run_and_log` (funzioni e pgTAP).
   Vanno censiti i pgTAP che leggono `error_code` aspettandosi lo SQLSTATE.
2. **Il registro dei codici dice chi rimedia.** `config.codici_errore` riceve una
   colonna **nullable** e vocabolario chiuso: «quando questo errore ferma un
   lavoro automatico, a chi tocca». È NULL di proposito: vuol dire «decide il
   processo». Si valorizza solo sui codici che lo richiedono. Le `classi_errore`
   non bastano, perché descrivono l'errore per chi ha fatto la richiesta:
   `TECNICO` mescola server, difetto e configurazione mancante.
3. **La vista** aggiunge un passo alla regola, fra il 2 e il 3: il codice
   dell'ultimo rosso con un destinatario dichiarato decide lui. Un codice non
   registrato (es. `SMOKE_*`) o senza destinatario passa al processo, quindi
   **niente «Senza indicazione»**.
4. **Il BE**: la richiesta del §4.2 cambia colonna. Lo SQLSTATE va nella colonna
   nuova, non sovrascrive `error_code`.

**Ordine di grandezza.** La base del §4.1 sta sui 6-7 changeSet. La variante B
ne aggiunge circa 5: colonna del giornale, tre funzioni, colonna sul registro
dei codici. Poi c'è il CSV dei codici da valorizzare, il cambio nel BE e i pgTAP
dei tre scrittori.

⭐ **Perché conviene farla adesso, se «prima o poi servirà».** D2 tocca già
`registered_job`, e la base tocca già la vista. Farla dopo vorrebbe dire rimettere
mano al giornale, alle sue funzioni e al BE una seconda volta. In più, se lo
SQLSTATE dei command finisse dentro `error_code` come chiede oggi il §4.2, i
valori scritti fino ad allora mescolerebbero due vocabolari nella stessa
colonna.

### 4.4 Ricognizione per lo sviluppo (2026-10-16, niente scritto)

**Il verbale dei fallimenti è di un superuser.** `maintenance.fn_job_run_log_failure`
è nel registro `dbops.sec_functions_owner`. Il parametro nuovo (lo SQLSTATE, in
coda con `DEFAULT NULL`) comporta quindi:

* `DROP` della firma vecchia + `CREATE` in un changeSet `context: provision`,
  incluso in `db/changelog/changelog-provision-post.yaml` (precedente:
  `20261015-03`);
* la riga 6 di `80_data/sql/dbops/sec_functions_owner.csv` con la firma nuova.

Ordine: in CI il provision-post gira **prima** di `ci_apply`, quindi i job di
convergenza trovano la firma nuova. Su dbdev il provision-post va lanciato
prima del migrate. Il prezzo da dichiarare: nella sola passata principale da
zero, un fallimento dentro `fn_run_and_log` (versione nuova) troverebbe la firma
vecchia, e l'errore originale sarebbe coperto da «la funzione non esiste».

**Gli scrittori del giornale sono tre**: `maintenance.fn_run_and_log`,
`maintenance.fn_job_run_log_failure`, `script.fn_job_run_start`/`fn_job_run_end`
(per il backend). La colonna nuova si censisce su tutti.

**Cosa scrive `fn_run_and_log`:** lo SQLSTATE nella colonna nuova. In `error_code`
va il codice di dominio **solo** con il contratto di `script.fn_log_and_raise_error`
(«`P0001` + `CONSTRAINT` valorizzato»), negli altri casi lo SQLSTATE. Per un
`23505` il `CONSTRAINT` è il nome di un vincolo, non un codice.

**Le righe già nel giornale**: quelle di `fn_run_and_log` hanno lo SQLSTATE in
`error_code`. La colonna nuova si riempie per conversione sul posto
(`ADD COLUMN` + `ALTER … TYPE … USING`, nessun trigger), dove `error_code` ha la
forma di uno SQLSTATE.

**Lettori di `error_code`**: `backend/apps/core/db/maintenance_repository.py:154`
(giornale) e `processi_repository.py:413` (lo mostrano e basta),
`db/pgtap/maintenance/test-vw-job-run-da-guardare.sql` (fixture). Il pannello
continua a mostrare un codice. Per un errore di dominio di un job DB mostrerà
`E_…` invece di `P0001`: è un miglioramento.

**Il vocabolario delle cause sta in tre posti**: `processi.causa_fallimento`,
`codici_errore.causa_fallimento` e le righe di `presidi_cause` della vista. Con
due `CHECK IN (…)` più il CSV sarebbe una copia (regola del 2). Vedi D4.

**Ordine da zero**: le due colonne nascono nullable in `00_schema`. Il valore
arriva dai CSV in `80_data`. `NOT NULL` su `processi` e le FK verso il vocabolario
vanno in `90_end`. Stessa forma di `chk_processi_accensione`
(`20261016-20`/`-31`).

**Due CSV che altri cantieri stanno toccando (2026-10-16):**

* `80_data/sql/dbops/processi.csv`: il brief `brief-db-processi-accensione-per-ambiente`
  è al giro 1, appena committato. La colonna in coda tocca ogni riga.
* `80_data/sql/config/codici_errore.csv`: ha modifiche **non committate** del
  cantiere listino (`brief-db-coerenza-listino-della-riga-di-commessa`). La
  colonna in coda tocca tutte le ~1090 righe: va fatta **dopo** il loro commit,
  o sarà un conflitto su ogni riga. Vedi D6.

## 5. Collaudo

Digest `--secco` con un rosso per causa: una corsa lasciata aperta, un rosso con
SQLSTATE `53100`, un rosso applicativo, un rosso con un codice che dichiara
`CONFIGURAZIONE`. Ognuno deve finire nel gruppo del suo destinatario e col suo testo.

**Script (2026-10-17)**, in `allegati/`:
1. `collaudo-presidio-job-run-prepara.sql`: mette le quattro corse
   (`COLLAUDO-CAUSA-*`), un processo `COLLAUDO-CAUSA` di canale CODA (non tocca il
   pannello dei processi) e un codice `E_COLLAUDO_CAUSA_CONFIGURAZIONE`. Controlla
   nel database causa e destinatario; se uno non torna si ferma senza lasciare
   niente. Provato sullo scratch con `ROLLBACK`: quattro su quattro.
2. `source backend/.venv/bin/activate` e `python backend/manage.py digest_presidi --cadenza giornaliera --secco` (dalla radice): i gruppi attesi sono sistemista
   (APPESA, DISCO), sviluppo (PROGRAMMA), amministratore (CONFIGURAZIONE).
3. `collaudo-presidio-job-run-pulisci.sql`: toglie tutto. ⚠️ Va lanciato lo stesso
   giorno: il digest delle 7 vedrebbe le corse di prova.

✅ **Esito su dbdev, lato DB (Tid, 2026-10-17).** Con le quattro corse di collaudo,
`dbops.fn_conta_presidio_per_variante('maintenance.vw_job_run_da_guardare')` (la
funzione da cui il digest prende i conteggi) dà `AMBIENTE` 2 → SISTEMISTA,
`PROGRAMMA` 2 → SVILUPPO (la corsa di collaudo più quella vera di
`smoke_notturno:completo`, `SMOKE_REGRESSIONI` del 14 e 15 ottobre: un caso reale
instradato giusto), `CONFIGURAZIONE` 1 → AMMINISTRATORE. Ognuna col suo testo. Il
digest stampato dal backend (`--secco`) resta da vedere: è del BE.
⚠️ Prima prova persa: il paginatore di `psql` teneva aperta la transazione, e
uscendone si annullava prima del `COMMIT`. Ora gli script hanno `\pset pager off`.

**Fasi:** ora quello che è applicato (i quattro casi qui sopra). Dopo il §4.2 del BE,
un errore del database dentro un command (va al sistemista) e un `P0001` col suo
codice `E_`. Dopo D9, un'azienda non accodata che chiude rossa la corsa.

## 6. Decisioni aperte di Tid

* ✅ **D1 — `CONFIGURAZIONE` / `AMMINISTRATORE` entra, variante B (§4.3)**: Tid,
  2026-10-16, dopo la stima del costo.
* ✅ **D4 — Il vocabolario delle cause: (a), tabella-vocabolario** (Tid, 2026-10-16).
  Testo della scelta: (a) Una tabella-vocabolario con le FK dalle
  due colonne. È pulita, ma una tabella nuova si porta dietro i suoi registri
  (`storico_scope_policy.csv`, perimetro RLS). (b) Due `CHECK` più un pgTAP che
  le confronta con `presidi_cause`. **Proposta: (a).**
* ✅ **D5 — `error_code` = «il codice più preciso che chi scrive ha»** (Tid,
  2026-10-16). Testo della scelta: «Il codice più preciso che chi scrive
  ha»: dominio, backend o, in mancanza, SQLSTATE/classe. È la forma del §4.4 e
  non tocca i lettori. In alternativa, «solo il codice applicativo, NULL
  altrimenti», più pura ma da adeguare nel pannello. **Proposta: la prima.**
* ✅ **D6 — `codici_errore.csv`**: il cantiere listino ha committato (Tid,
  2026-10-16), il file si può toccare.
* ✅ **D2 — Il BE scrive lo SQLSTATE nel giornale dei command (§4.2): sì** (Tid,
  2026-10-16). In quale colonna dipende da D1.
* ✅ **D3 — I nomi: accettati quelli proposti** (Tid, 2026-10-16). Le cause sono
  `AMBIENTE` (SISTEMISTA), `PROGRAMMA` (SVILUPPO) e, con D1, `CONFIGURAZIONE`
  (AMMINISTRATORE). La colonna nuova di `dbops.processi` si chiama
  `causa_fallimento`.
* ✅ **D7 — Quali codici d'errore dichiarano `CONFIGURAZIONE`?** Proposta concordata da
  Tid il 2026-10-16: il censimento lo anticipa il team DB anche per il lato BE, e Tid
  lo fa confermare al BE (§9).
  Il meccanismo è in servizio, ma un codice va scelto conoscendo il suo
  significato, non per somiglianza del nome. `E_CONFIG_MANCANTE`, per esempio, lo
  solleva anche il guardiano del digest per un tipo di lavoro non a catalogo, e
  lì è `PROGRAMMA`. Il caso che ha aperto D1, la password SMTP sbagliata, oggi non
  ha un codice: `send_pending_emails` registra la classe dell'eccezione Python.
  Serve prima un codice dal BE. **Proposta:** un censimento corto dei codici che i
  lavori automatici possono sollevare (pipeline di fatturazione, coda stampa, coda
  email), fatto col BE, e i valori nel CSV in un giro successivo.

## 7. Fuori da questo brief

* Il **job che non parte affatto**: lo vede il presidio dei processi
  (`vw_processi_programmazione_da_guardare`), non questo.
* I processi ritirati che restano nella vista (residuo D10 di
  `migliorie-generali-da-test-valutazione.md`).

## 8. Consegna DB (2026-10-16) — ✅ applicata, pgTAP senza regressioni

### 8.1 Che cosa è stato scritto

| ChangeSet | Cosa |
| --- | --- |
| `00_schema/dbops/20261016-34` | `dbops.cause_fallimento` (vocabolario, D4) |
| `00_schema/maintenance/20261016-35` | `job_run_log.sqlstate` + CHECK di forma; righe di prima convertite sul posto dalla forma di `error_code` |
| `00_schema/dbops/20261016-36` | `dbops.processi.causa_fallimento` (nullable fino al `-43`) |
| `00_schema/config/20261016-37` | `config.codici_errore.causa_fallimento` (NULL = decide il processo) |
| `20_code/maintenance/20261016-38` | `fn_run_and_log`: `error_code` = codice di dominio col contratto P0001 + CONSTRAINT, SQLSTATE nella colonna nuova |
| `20_code/maintenance/20261016-39` | ⚠️ **context provision**: `fn_job_run_log_failure` + `p_sqlstate` in coda (DROP + CREATE), incluso in `changelog-provision-post.yaml` |
| `20_code/script/20261016-40` | `fn_job_run_end` + `p_sqlstate` in coda (DROP + CREATE, REVOKE PUBLIC, GRANT app) |
| `20_code/maintenance/20261016-41` | la vista: colonne in coda `sqlstate`, `causa`, `ultimo_rosso_job_run_id`; «presa e mai chiusa» solo oltre l'ora |
| `80_data/20261016-42` | mirror di `cause_fallimento.csv` |
| `90_end/20261016-43` | `processi.causa_fallimento` NOT NULL + due FK verso il vocabolario |

**Seed:** `processi.csv` (colonna in coda, `PROGRAMMA` su tutti e 28), `codici_errore.csv`
(colonna in coda, `NULL` su tutti tranne `E_STATISTICHE_MANCANTI` = `AMBIENTE`),
`presidi.csv` (`colonna_variante = causa`, nota), `presidi_cause.csv` (tre righe),
`presidi_testi.csv` (tre testi di causa + testo generale riscritto),
`sec_functions_owner.csv` (riga 6, firma nuova). Mirror di `processi` e
`codici_errore` con la colonna nell'elenco.

**pgTAP nuovi:** `maintenance/test-vw-job-run-da-guardare-causa-v1.sql` (14: la
regola ramo per ramo, costruita), `maintenance/test-job-run-sqlstate-e-codice-v1.sql`
(9: le tre porte di scrittura; i test 7-9 sono presidi sul testo, dichiarati).
**Adeguati:** 17 file che fabbricano processi (28 `INSERT INTO dbops.processi`,
ora con `causa_fallimento`), e `test-job-run-registrazione.sql` test 21 (la firma
di `fn_job_run_end` cercata per nome, come il test 20 accanto).

**Doc `manual/`:** `cause_fallimento` (nuova), `vw_job_run_da_guardare`,
`job_run_log`, `processi`, `codici_errore`, `presidi_cause`, e le tre funzioni.

### 8.2 Scelte fatte in sviluppo

* **Il motivo «presa e mai chiusa» aveva un difetto, chiuso nello stesso giro.**
  Diceva morta OGNI ultima corsa aperta, anche quella partita cinque minuti fa di
  un job con rossi recenti, che entra per il ramo intermittente. Con la causa
  sarebbe diventata `AMBIENTE` a torto. Ora «appesa» vale solo oltre l'ora, e
  la corsa in corso ha il suo motivo: «in corso adesso, ma ha fallito di recente:
  intermittente». I valori di motivo esistenti non cambiano.
* **Tutti i processi dichiarano `PROGRAMMA`.** Nessun processo del catalogo fallisce,
  per natura, per l'ambiente o per la configurazione quando l'ambiente è sano: i casi
  d'ambiente li prendono i rami 1-2, quelli di un errore preciso il codice.
* **Codici con causa: uno solo** (`E_STATISTICHE_MANCANTI` = `AMBIENTE`, che la sua
  nota già diceva). Quali codici dichiarano `CONFIGURAZIONE` è D7: il meccanismo
  c'è e il pgTAP lo prova con un codice fabbricato, ma oggi nessun codice vero
  porta l'amministratore.
* **Il ramo «nessun processo → PROGRAMMA» non è costruibile in un test**:
  `chk_job_run_log_processo_dichiarato` (NOT VALID) vieta una corsa nuova senza
  processo. Vale per le righe di prima; lo presidia il test 13 (nessuna causa NULL).

### 8.3 Ordine di apply su dbdev

1. **provision-post da superuser** (`changelog-provision-post.yaml`): il `-39`
   sostituisce `fn_job_run_log_failure`. ⚠️ Fino al migrate la funzione scrive una
   colonna che non c'è: un fallimento in quei minuti lascia solo un WARNING, non
   la riga rossa. E `fn_sync_functions_owner` dice «non trovata» la firma del
   registro: WARNING, non un guasto.
2. **migrate**: `-34…-38`, `-40…-43`, e i mirror risvegliati (`processi`,
   `codici_errore`, `presidi`, `presidi_testi`/`presidi_cause`, `sec_functions_owner`).

### 8.4 Prova (sessione DB, 2026-10-16, scratch `zeroerp_ruoli` come `zeroerp_owner`)

SQL estratto dai changeSet + seed simulati, in una transazione annullata
(verificato dopo: niente persistito). Il `-39` **escluso**: la funzione è di un
superuser e l'owner non può sostituirla.

* l'intero estratto passa, compresi `NOT NULL` e FK del `-43` sulle 28 righe;
* **upsert completo** dei cinque CSV toccati (dopo le FK): passa, zero processi
  senza causa;
* `test-vw-job-run-da-guardare-causa-v1`: **14/14**;
* `test-job-run-sqlstate-e-codice-v1`: **7/9**. I due rossi (6, 7) sono il `-39`
  non applicato, attesi: dimostrano che i test se ne accorgono. Verdi dopo il
  provision-post;
* i 17 file con le fixture adeguate, più `test-vw-job-run-da-guardare`,
  `test-job-run-log-failure-out-of-tx`, `test-presidi-testi-v1`,
  `test-job-run-registrazione`: verdi, **tranne tre rossi che ci sono identici
  sullo scratch senza queste modifiche** (provati sul file di `HEAD`):
  `test-identita-tecnica` e `test-fn-crea-utente-tecnico` (fixture: «Il soggetto
  non ha contatti validi»), `test-app-postura-job-run-log-v1` test 9 (da owner il
  vincolo del processo parla prima del privilegio: è un test da app).
* guardrail statici (`guardrail_*.py`): tutti verdi.

Non provato qui: la corsa come app, il provision-post, e la corsa pgTAP completa.
Sono di Tid.

## 9. Censimento D7 — i codici che possono far fallire un lavoro automatico (2026-10-16)

> Fatto dal team DB anche per il lato BE (decisione di Tid del 2026-10-16), **da far
> confermare al BE**. Due ricerche in sola lettura: i job pgAgent dentro
> `maintenance.fn_run_and_log`, e i command del backend dentro `registered_job`.
> Nessun file toccato.

### 9.1 La risposta corta: oggi nessun codice dichiara `CONFIGURAZIONE`, ed è giusto

Nessun errore che **fa fallire una corsa**, né nel database né nel backend, si
sistema con un gesto dell'amministratore nelle impostazioni dell'app.

**Il caso che aveva aperto D1, la password SMTP sbagliata, non arriva a questo
presidio.** Verificato in `email_service._send_smtp`: `SMTPAuthenticationError`,
host o porta sbagliati (`OSError`), chiave non decifrabile (`ValueError`), account
mancante e password vuota sono **tutti catturati per email**. La singola email va
in `FAILED`, viene ritentata fino a `max_tentativi`, e la corsa di
`send_pending_emails` resta `ok = true` con `error_code` NULL. Quel guasto lo vede
il presidio delle email, `dbops.vw_email_da_guardare`, non quello dei lavori.

⇒ **Nessuna modifica a `codici_errore.csv`.** `CONFIGURAZIONE` resta nel
vocabolario e nel presidio, pronta per il primo codice che fermi davvero una corsa
per un'impostazione dell'app. Il pgTAP la prova già con un codice fabbricato.
`E_STATISTICHE_MANCANTI` = `AMBIENTE` resta l'unico valore.

### 9.2 Lato database (job pgAgent)

* Nessun job pgAgent arriva alla fatturazione o alla chiusura vera.
  `chiusura_scadenze_daily` accoda soltanto; la chiusura gira nel drenatore,
  fuori da `fn_run_and_log`.
* **Codici raggiungibili e la loro natura.** Tutti sono già classificati bene dal
  ripiego del processo (`PROGRAMMA`), tranne quelli del §9.4:
  * `E_STATISTICHE_MANCANTI`: `AMBIENTE`, già dichiarato;
  * i codici del cablaggio job/catalogo (`E_PROCESSO_NON_TROVATO`,
    `E_PROCESSO_SENZA_SVEGLIA`, `E_JOB_TYPE_*`), quelli strutturali dello storico
    (`E_STORICO_FK_COL_ASSENTE`, `E_STORICO_PARENT_PK_NOT_FOUND`) e i guard di
    chiamata (`E_PARAMETRO_INVALIDO`): `PROGRAMMA`.
* **`E_CONFIG_MANCANTE` è ambiguo** (classe TECNICO, quattro sedi):
  * ambiente dell'installazione non dichiarato: provisioning;
  * `SYSTEM_FUSO_ORARIO` mancante: seed; l'app scrive solo gli override;
  * colonne di accensione mancanti in `dbops.processi`: catalogo;
  * `digest_presidi` assente per il guardiano: catalogo.

  Nessuna delle quattro è `CONFIGURAZIONE`. Resta **NULL** (decide il processo).
  Le due sedi della sveglia (`fn_sveglia_accesa`) girano comunque **prima** di
  `fn_run_and_log`: un loro rosso è solo in pgAgent, e lo vede il presidio dei
  processi.
* `automations_overlap` può fallire con un `23P01` grezzo (righe già
  sovrapposte): nessun codice `E_`, cade su `PROGRAMMA`. Si sistema correggendo i
  dati. Annotato, non urgente.

### 9.3 Lato backend (command)

* Escono dalla corsa, cioè arrivano al giornale, solo gli errori **di
  infrastruttura della corsa stessa**:
  * le letture e scritture della coda o del roster (`OperationalError`,
    `InterfaceError`: `AMBIENTE`, una volta passato lo SQLSTATE del §4.2);
  * gli errori di funzione DB (`InternalError`: oggi il codice `E_` si perde, da
    cui il punto 2 del §4.2);
  * lo smoke (`SMOKE_REGRESSIONI`: `PROGRAMMA`; `SMOKE_GIRO_FALLITO`: ambiguo, sotto).
* **Tutto ciò che riguarda il singolo elemento è catturato.** Una email, un item
  della coda lavori, un emittente della coda stampa, un'azienda della fatturazione
  o del badge: finisce in `meta` o nel proprio registro, e la corsa resta verde.
* **Restano fuori dal giornale** per costruzione:
  * il database giù già all'apertura della corsa: nessuna riga;
  * il database giù alla chiusura: riga aperta, che dopo un'ora diventa «presa
    e mai chiusa», cioè `AMBIENTE`;
  * la morte del listener `listen_permessi`, che ha per segno di vita la sessione.
* `SMOKE_*` non sono a registro: cadono su `smoke_notturno` = `PROGRAMMA`. Per
  `SMOKE_GIRO_FALLITO` è giusto per lo script rotto, non per il tetto di tempo
  superato. Una separazione (es. un codice per il tetto) la decide il BE.

### 9.4 Due buchi del modello emersi dal censimento (decisioni per Tid)

* **D8 — Gli involucri `WHEN others` nascondono l'ambiente.** `E_ATTIVO_*`,
  `E_AUDIT_UPDATE`, `E_TX_ID`, `E_STORICO_UD`, `E_STORICO_PROVISION`,
  `E_LOCK_COLUMNS` (ramo DDL), `E_DATE_VALIDITA` ed `E_DELETE_BLOCK` catturano
  qualunque errore della DDL generata e lo rilanciano come `P0001` col proprio
  codice. Un `42501` (manca un diritto) o un `55P03` (lock) dentro un'automazione
  arriva al giornale come `P0001` + codice dell'involucro, e la causa diventa
  `PROGRAMMA` invece di `AMBIENTE`. L'errore originale c'è, ma solo nel contesto
  dell'eccezione. *Strade:* (a) l'involucro rilancia così com'è quando lo
  SQLSTATE originale è di classe `08`/`42501`/`53`/`55`/`57`/`58`; (b) lo si
  accetta e lo si dichiara. **Proposta: (a)**, in un brief suo: tocca otto
  funzioni del framework automazioni.
* **D9 — Un lavoro che fallisce su tutti gli elementi resta verde.** Se tutte le
  email, tutte le aziende o tutti gli emittenti falliscono, la corsa è `ok`. Il
  presidio dei lavori non lo vede, e lo vedono solo i presidi dei singoli
  registri (email, coda lavori, coda stampa), quando ci sono. È il confine
  dichiarato di questo presidio, non un suo difetto: il fallimento di un elemento
  appartiene al registro dell'elemento. **Proposta:** verificarlo sulla
  struttura. Ogni registro in cui un command isola i fallimenti per elemento
  (`config.email_log`, `dbops.coda_lavori`, `vendite.fatture_stampa_coda`, il
  `meta` della fatturazione e dei badge) deve avere un presidio a catalogo. Quello
  che non ce l'ha è il buco da chiudere. Il `meta` della fatturazione e dei badge
  oggi non ha presidio: è il primo candidato.

* ✅ **Decisioni di Tid (2026-10-16):** D8 si fa **in questo brief** (giro 2, §10);
  D9: proposta accettata, cioè la verifica sulla struttura, il cui esito è al §10.3.

## 10. Giro 2 — D8 e D9 (ricognizione del 2026-10-16, niente scritto)

### 10.1 D8: i nove gestori `WHEN others`

Letti dal doc auto-generato: `fn_run_automations_attivo` (due, `E_ATTIVO_REQUIRE` ed
`E_ATTIVO_BLOCK`), `_audit_update` (`E_AUDIT_UPDATE`), `_tx_id` (`E_TX_ID`), `_storico`
(`E_STORICO_UD`), `fn_ensure_storico_table` (`E_STORICO_PROVISION`), `_lock_columns`
(`E_LOCK_COLUMNS`, ramo DDL), `_date_validita` (`E_DATE_VALIDITA`) e `_delete_block`
(`E_DELETE_BLOCK`). Tutti hanno la stessa forma: `EXCEPTION WHEN others THEN PERFORM
script.fn_log_and_raise_error(…, 'E_…', jsonb_build_object(…, 'error', SQLERRM), …)`.
Lo SQLSTATE originale si perde e il giornale riceve `P0001`.

**La forma proposta:** in ogni gestore, prima dell'involucro,
`IF <lo SQLSTATE è dell'ambiente> THEN RAISE; END IF;`. `RAISE;` senza argomenti
rilancia l'eccezione originale, col suo SQLSTATE: `fn_run_and_log` la scrive in
`sqlstate`, e la vista la classifica `AMBIENTE`. Il resto, cioè i difetti di
struttura, continua a uscire col codice dell'involucro (`PROGRAMMA`).

⭐ **Regola del 2: «quali SQLSTATE sono dell'ambiente» diventa una funzione sola.**
Oggi la lista `08`/`53`/`57`/`58` sta nel CASE della vista (`-41`). Con i nove
gestori sarebbero dieci copie. Si estrae un predicato (nome da decidere, es.
`dbops.fn_sqlstate_di_ambiente(text) RETURNS boolean`, IMMUTABLE). Lo chiamano la
vista e i nove gestori, e la vista si riscrive per usarlo nello stesso giro.

**La lista, sul modello:** quello che rimedia chi gestisce il server o il database.
* `08` connessione, `53` risorse, `57` intervento dell'operatore, `58` sistema: già oggi;
* **`42501` (privilegio mancante)**: un diritto al ruolo è provisioning, come
  `E_STATISTICHE_MANCANTI`. Le altre `42xxx` (sintassi, oggetto inesistente)
  restano `PROGRAMMA`;
* **`55P03` (lock non ottenuto entro `lock_timeout`)**: contesa con un'altra
  sessione, è un fatto d'esercizio. Vedi D10.

⚠️ Un `42501` in un job DB **senza** involucro oggi esce `PROGRAMMA`; con la lista
nuova esce `AMBIENTE`. È lo stesso difetto visto dal lato diretto, e si chiude
insieme.

⚠️ **Il registro degli errori.** L'involucro, oltre a sollevare, scrive in
`dbops.error_log` (via `fn_log_and_raise_error`). Col `RAISE;` diretto quella riga
non si scrive più per i casi d'ambiente. Il giornale dei job resta (codice,
SQLSTATE, messaggio), ma il contesto (tabella, trigger) sta solo nel messaggio
originale. Vedi D11.

Dove si prova: pgTAP che provoca un `42501` dentro un'automazione. Si fa
**costruendo** un ruolo senza diritto, se lo scratch lo consente; altrimenti un
presidio sul testo dei nove corpi, dichiarato tale.

### 10.1-bis ⛔ Il `%TYPE` mancato nel giro 1: debito noto, non si riscrive (Tid, 2026-10-16)

Regola: `%TYPE` nella **firma**, nel `RETURNS TABLE` e nel `DECLARE`, e anche nelle
firme di `COMMENT ON FUNCTION`, `DROP FUNCTION`, `GRANT`/`REVOKE EXECUTE`. Il tipo
nudo si mette solo dove non c'è una colonna di cui il valore è il riflesso, e
allora si scrive perché.

Nel giro 1, già applicato e committato:
* `p_sqlstate text` in `script.fn_job_run_end` (`-40`) e in
  `maintenance.fn_job_run_log_failure` (`-39`), con le firme di `COMMENT`, `DROP`,
  `REVOKE`/`GRANT`: andava `maintenance.job_run_log.sqlstate%TYPE`;
* `v_vincolo text` in `fn_run_and_log` (`-38`): qui il tipo nudo è giusto, perché
  `CONSTRAINT_NAME` è un dato diagnostico senza colonna di cui sia riflesso. Il
  valore finisce in `error_code` solo attraverso `v_codice`, che è ancorato. Manca
  però il commento che lo dice.

**Decisione di Tid (2026-10-16): le funzioni già scritte non si riscrivono per il
`%TYPE`.** Si sistemeranno in futuro, insieme ad altre modifiche a quelle
funzioni. Il giro 2 applica la regola solo al codice **nuovo**: il predicato del
§10.1 nasce `p_sqlstate maintenance.job_run_log.sqlstate%TYPE`, e ogni variabile o
parametro nuovo nei corpi toccati per D8 è ancorato.

### 10.2 Costo stimato

Un changeSet per il predicato, otto per le funzioni (una per file, corpo dal doc
auto-generato), uno per la vista, i pgTAP. Nessuna firma cambia. Le automazioni
girano in `ci_apply`: in CI un fallimento d'ambiente lì mostrerà il messaggio
originale invece di quello dell'involucro.

### 10.3 D9: l'esito della verifica sulla struttura

| Dove un command isola i fallimenti per elemento | Registro con presidio? |
| --- | --- |
| email (`send_pending_emails`) | ✅ `config.email_log` → `dbops.vw_email_da_guardare` |
| item della coda lavori (`draina_coda_lavori`) | ✅ `dbops.coda_lavori` → `dbops.vw_coda_lavori_da_guardare` |
| emittenti della coda stampa (`draina_coda_stampa`) | ✅ `vendite.fatture_stampa_coda` → `dbops.vw_fatture_stampa_coda_da_guardare` |
| aziende non accodate da `run_fatturazione_batch` (`meta.falliti`) | ⛔ **nessun registro**: il lavoro non è mai entrato in coda |
| badge falliti di `send_pending_emails` (`meta.badge_falliti`) | ⛔ **nessun registro** |

**I due buchi hanno la stessa forma:** l'elemento fallito non lascia una riga da
nessuna parte, salvo il `meta` della corsa. **Proposta:** quando un elemento senza
registro fallisce, la corsa chiude **rossa** dopo aver finito gli altri, con un
codice registrato. Il lavoro sugli altri elementi resta fatto. La corsa rossa la
vede questo presidio, e la causa la decide il codice o il processo come per ogni
altro rosso.
* Lato DB: il codice nel registro (nome da decidere, es.
  `E_JOB_ELEMENTI_NON_COMPLETATI`, classe TECNICO, `causa_fallimento` NULL perché
  decide il processo) e il suo messaggio.
* Lato BE: i due command sollevano quel codice in fondo, quando `falliti` o
  `badge_falliti` non è vuoto.

⛔ Scartato: un presidio che legge il `meta` delle corse. Il `meta` non ha una
forma comune (`falliti`, `badge_falliti`, `emittenti_falliti`, `fallite`), e un
presidio su chiavi libere si spegne in silenzio al primo nome nuovo.

### 10.4 Decisioni per il giro 2

* ✅ **D10 — `55P03` (lock non ottenuto) è `AMBIENTE`: sì, proposta accettata da Tid (2026-10-16).** Sì se lo si legge come
  contesa d'esercizio (un'altra sessione tiene la tabella); no se lo si legge come
  difetto di ordine dei lavori. **Proposta: sì.** Il deadlock (`40P01`) resta
  fuori: lì due lavori si contendono in un ordine sbagliato, ed è programma.
* ✅ **D11 — (a), proposta accettata da Tid (2026-10-16).** Per i casi d'ambiente l'involucro deve ancora scrivere in
  `dbops.error_log` prima di rilanciare?** (a) Sì: `fn_log_error_only` col contesto,
  poi `RAISE;`. (b) No: basta il giornale. **Proposta: (a)**. Il contesto (quale
  tabella, quale trigger) serve a chi rimedia, e il messaggio originale non sempre
  lo dice.

## 11. Consegna DB del giro 2 — D8 (2026-10-16) — ✅ applicata, pgTAP senza regressioni

### 11.1 Che cosa è stato scritto

| ChangeSet | Cosa |
| --- | --- |
| `20_code/script/20261016-44` | `script.fn_sqlstate_di_ambiente(p_sqlstate maintenance.job_run_log.sqlstate%TYPE)`: `08`, `53`, `57`, `58`, `42501`, `55P03` (D10). `LANGUAGE sql`, IMMUTABLE, NULL → false |
| `20_code/dbops/20261016-45…-52` | i nove gestori `WHEN others` in otto funzioni (`fn_run_automations_attivo` ×2, `_audit_update`, `_tx_id`, `_storico`, `fn_ensure_storico_table`, `_lock_columns`, `_date_validita`, `_delete_block`). Per un guasto d'ambiente: `fn_log_error_only` con lo stesso codice e contesto (D11), poi `RAISE;` dell'originale. Altrimenti l'involucro di prima. Il contesto si costruisce una volta in `v_ctx_errore dbops.error_log.context%TYPE` |
| `20_code/maintenance/20261016-53` | la vista: il ramo `AMBIENTE` della causa chiama il predicato (regola del 2). Effetto anche sui job senza involucro: un `42501` diretto ora è `AMBIENTE` |

**pgTAP:** nuovo `dbops/test-automazioni-guasto-ambiente-rilanciato-v1.sql` (6). I test
1-3 sono la tabella di verità del predicato; i 4-6 sono presidi sul testo,
dichiarati: provocare un `42501` o un `55P03` dentro un'automazione non è
costruibile dall'owner in una transazione di prova. `test-vw-job-run-da-guardare-causa-v1`
cresce a 15 (caso `42501`).

**Doc `manual/`:** `script/fn_sqlstate_di_ambiente` (nuova), `vw_job_run_da_guardare`.

⚠️ **Il rilancio non si estrae**: `RAISE;` vive solo dentro il gestore. La decisione
sì, ed è il predicato. Le nove copie del blocco le tiene allineate il test 5-6.

⚠️ **Il codice di D9 non è scritto.** Il nome del codice registrato
(es. `E_JOB_ELEMENTI_NON_COMPLETATI`) va concordato col BE, che lo solleva. Un
codice a registro senza nessuno che lo sollevi sarebbe un riferimento morto.
✅ Scritto il 2026-10-17, col nome dato dal BE: §11.3.

### 11.2 Prova (sessione DB, 2026-10-16, scratch `zeroerp_ruoli`, transazione annullata)

* SQL estratto `-44…-53`: passa. Scratch verificato intatto dopo.
* `test-automazioni-guasto-ambiente-rilanciato-v1`: **6/6**. Mutazione (predicato
  presente, gestori vecchi): il test 4 è rosso e nomina tutte le otto funzioni.
* `test-vw-job-run-da-guardare-causa-v1`: **15/15**.
* Regressione sui pgTAP che chiamano le otto funzioni (`test-lock-columns-convergenza`
  22, `test-storico-automazione-colonna-fk-v1` 7, `test-trgfn-guard-date-validita-v1` 12,
  `test-storico-scope-congelato-v1` 23) e sui presidi trasversali
  (`test-catalogo-messaggi-errore-completo` 7, `test-riferimenti-morti-v1` 9, che
  compila ogni plpgsql, `test-vw-codici-errore-motivo-nominato` 8): tutti verdi.
* Guardrail statici: verdi.

**Apply:** solo migrate, nessun provision-post (nessuna funzione del registro dei
superuser).

### 11.3 Il codice di D9 (2026-10-17)

Nome dal BE: **`E_JOB_ELEMENTI_NON_COMPLETATI`**. Due righe, nessun changeSet: le carica il mirror
dei due CSV, come `E_JOB_RUN_SALTATA_NON_CHIUDIBILE`, il precedente citato dal BE.

| CSV | Riga |
| --- | --- |
| `codici_errore.csv` | classe `TECNICO`, `causa_fallimento` NULL (la causa la decide il processo, oggi `PROGRAMMA`) |
| `messaggi_errore.csv` (id 1350) | «Il lavoro automatico è finito, ma alcuni elementi non sono stati completati.» |

⚠️ **La frase è chiusa, senza `%s`: uno scostamento dalla proposta del BE, voluto.** Il BE
proponeva di passarle `jobname` e `falliti`. Ma il codice lo solleva il **backend**, che scrive la
sua frase in `maintenance.job_run_log.message` e non riempie i segnaposto del catalogo: un `%s` a
catalogo uscirebbe grezzo dovunque la frase del catalogo venga mostrata. È la forma dei diciannove
`*_VALIDATION`, tutti chiusi perché li solleva il BE. La corsa e il numero di elementi falliti
stanno dove li legge chi guarda: nel `message` della corsa (il BE li mette nella sua frase) e nel
`meta` (`falliti`, `badge_falliti`). Causa e soluzione a catalogo dicono dove guardarli.

Provato sullo scratch (`zeroerp_ruoli`, transazione annullata): le due righe entrano nelle tabelle,
coi loro vincoli. Per il BE: rigenerare `error_policies_generated.py` e, se serve, il ripiego in
`error_messages_fallback.py`.
