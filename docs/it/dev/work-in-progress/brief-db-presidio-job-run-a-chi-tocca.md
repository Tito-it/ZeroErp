# Brief DB — Il presidio dei job falliti manda tutto al sistemista

## ⏭️ Chi riparte — aggiornato al 2026-10-16

**Riparte: Tid**, quando decide di aprire lo sviluppo. D1, D2 e D3 sono prese
(D1 = variante B). La ricognizione per lo sviluppo è al §4.4. Tid ha chiesto di
**non** iniziare lo sviluppo (2026-10-16).

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | Tid | dà il via allo sviluppo e chiude D4–D6 | §4.4, §6 | — |
| 2 | team DB | changeSet: giornale, tre funzioni, `processi`, `codici_errore`, vista, CSV, pgTAP | §4.1, §4.3, §4.4 | 1 |
| 3 | Tid | applica (provision-post compreso) e lancia i pgTAP | — | 2 |
| 4 | team BE | lo SQLSTATE nella colonna nuova del giornale | §4.2, §4.3 | 2 |
| 5 | Tid | collaudo: digest `--secco` con un rosso per causa | §5 | 3, 4 |

Decisioni aperte di Tid: **D4, D5, D6** (§6). Lavoro fatto da committare: solo questo brief.

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

**In `dbops.processi`** una colonna nuova, **NOT NULL**, con CHECK sul
vocabolario: «di che natura sono i miei fallimenti quando l'ambiente è sano». Un
processo nuovo non può nascere senza dichiararla. Esempio sul modello:
`analyze_statistiche` dichiara `AMBIENTE` (il suo errore proprio chiede un diritto
al ruolo), `smoke_notturno` dichiara `PROGRAMMA`.

⚠️ La colonna **non** nasce come FK verso `presidi_cause`, che è chiavata
`(vista, causa)`. La coerenza la tiene un pgTAP: ogni valore dichiarato in
`processi` è una causa del presidio.

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

### 4.2 Lato BE — richiesta, se D2 = sì

In `registered_job`, quando l'eccezione è un errore del database, scrivere in
`error_code` lo **SQLSTATE** (psycopg 3: `exc.__cause__.sqlstate`) invece del nome
della classe Django. Senza questo, per i command il §3.2 non vede mai l'ambiente
e la regola cade sul processo.

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
SQLSTATE `53100`, un rosso applicativo di `smoke_notturno`. Ognuno deve finire nel
gruppo del suo destinatario e con il suo testo.

## 6. Decisioni aperte di Tid

* ✅ **D1 — `CONFIGURAZIONE` / `AMMINISTRATORE` entra, variante B (§4.3)**: Tid,
  2026-10-16, dopo la stima del costo.
* **D4 — Il vocabolario delle cause.** (a) Una tabella-vocabolario con le FK dalle
  due colonne. È pulita, ma una tabella nuova si porta dietro i suoi registri
  (`storico_scope_policy.csv`, perimetro RLS). (b) Due `CHECK` più un pgTAP che
  le confronta con `presidi_cause`. **Proposta: (a).**
* **D5 — Il significato di `error_code`.** «Il codice più preciso che chi scrive
  ha»: dominio, backend o, in mancanza, SQLSTATE/classe. È la forma del §4.4 e
  non tocca i lettori. In alternativa, «solo il codice applicativo, NULL
  altrimenti», più pura ma da adeguare nel pannello. **Proposta: la prima.**
* **D6 — Quando si tocca `codici_errore.csv`**: dopo il commit del cantiere
  listino (§4.4).
* ✅ **D2 — Il BE scrive lo SQLSTATE nel giornale dei command (§4.2): sì** (Tid,
  2026-10-16). In quale colonna dipende da D1.
* ✅ **D3 — I nomi: accettati quelli proposti** (Tid, 2026-10-16). Le cause sono
  `AMBIENTE` (SISTEMISTA), `PROGRAMMA` (SVILUPPO) e, con D1, `CONFIGURAZIONE`
  (AMMINISTRATORE). La colonna nuova di `dbops.processi` si chiama
  `causa_fallimento`.

## 7. Fuori da questo brief

* Il **job che non parte affatto**: lo vede il presidio dei processi
  (`vw_processi_programmazione_da_guardare`), non questo.
* I processi ritirati che restano nella vista (residuo D10 di
  `migliorie-generali-da-test-valutazione.md`).
