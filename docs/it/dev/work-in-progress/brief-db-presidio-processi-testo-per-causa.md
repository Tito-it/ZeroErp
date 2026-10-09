# Brief DB — Il presidio dei processi dà un solo rimedio a guasti diversi

> **Chi scrive:** sessione backend (`dev/backend-tid`), 2026-10-09. **A chi:** team
> DB (`dev/db-tid`), tramite Tid.
> **Origine:** avviso del 2026-10-09 sul pannello Processi automatici:
> `listen_permessi` `MUTO`, con il testo «il programmatore dei processi, o il timer
> di quel processo, non sta girando… lancialo a mano con «Esegui ora»». Il
> processo è un **servizio sempre acceso**: non ha timer, e «Esegui ora» per lui
> non esiste. Il guasto vero era la connessione persa dopo il riavvio di Postgres
> sul dbdev, sanato lato BE lo stesso giorno (battito nel listener,
> `notify_listener.py`).
> **Decisione di Tid (2026-10-09):** **forma B** (§3) — il testo lo sceglie la
> causa della riga.
> **Stato:** ⏳ tocca al team DB (R-1, forma B). Nessuna riga scritta lato DB.
> Dopo l'apply, BE/FE (§3, «Ricaduta BE/FE»).

## 1. Il difetto

`dbops.presidi_testi` ha **un** testo per presidio e lingua: `significato` e
`azione` valgono per **tutte** le righe della vista. Per
`dbops.vw_processi_programmazione_da_guardare` non basta, perché le righe di
quella vista sono guasti **diversi**, con rimedi diversi e spesso con persone
diverse che devono intervenire. Gli stati che entrano nel presidio (`da_guardare`,
letto dal CASE di `dbops.vw_processi_programmazione`):

| Stato | Quando (canale, segno di vita) | Che cosa è successo | Rimedio giusto | Lo dice il testo di oggi? |
| --- | --- | --- | --- | --- |
| `MUTO` | `COMMAND`, `GIORNALE` | il timer non gira più | riaccendere il timer; intanto «Esegui ora», **se** la sveglia lo ammette | ⚠️ in parte: «Esegui ora» non esiste per le sveglie con `avvio_manuale = false` (il drenatore della coda lavori, che è anche chi esegue «Esegui ora») |
| `MAI_PARTITO` | `COMMAND`, `GIORNALE` | il timer è dichiarato ma non è mai stato installato | `install-timers.sh` sul server | ⚠️ in parte («non sta girando»); «Esegui ora» su un'unit assente fallisce |
| `MUTO` | `COMMAND`, `SESSIONE` | il servizio è spento, oppure acceso ma senza connessione al DB | riavviare il servizio | ⛔ parla di timer e di «Esegui ora» |
| `NON_PROGRAMMATO` | `PGAGENT` | il catalogo non nomina il job che sveglia il processo | sviluppo DB: completare `dbops.processi` | ⛔ manda al server un difetto di catalogo |
| `JOB_ASSENTE` | `PGAGENT` | il catalogo nomina un job che in pgAgent non c'è | chi gestisce il database: installare il job | ⚠️ generico («programmatore dei processi») |
| `JOB_SPENTO` | `PGAGENT` | il job c'è ma è disabilitato | chi gestisce il database: riaccenderlo, o capire chi l'ha spento | ⚠️ generico |
| `MAI_PARTITO` | `PGAGENT` | il job è acceso ma non è mai girato | chi gestisce il database: il programmatore pgAgent non gira | ⚠️ generico; «Esegui ora» non c'entra |
| `GIRA_E_NON_REGISTRA` | `PGAGENT` | pgAgent dice che il job è girato, il giornale no | sviluppo | ✅ («avvisa anche lo sviluppo») |

Il testo di oggi è scritto per il primo caso. Per gli altri dà indicazioni
**sbagliate**: dice a chi deve intervenire di cercare un timer che non esiste, o di
premere un pulsante che non c'è. Gli stati sono sei, ma le cause otto: `MUTO` e
`MAI_PARTITO` cambiano significato secondo il canale e il segno di vita. Nessun
testo unico, per quanto lungo, risponde bene a tutte.

⚠️ Non è un difetto di questo solo presidio, ma del **modello** dei testi: quando
le righe di una vista hanno cause diverse, un testo unico è sbagliato per alcune
di loro. Questo è il primo caso che lo mostra, e la soluzione va pensata per tutti.

## 2. Cosa si chiede

| # | Cosa | Tipo | Bloccante per il BE/FE |
| --- | --- | --- | --- |
| R-1 | Un testo (`significato`, `azione`) **per causa** delle righe del presidio dei processi, dove la causa la sa il database | modello (forma B, §3) + seed `80_data` | sì: pannello e digest leggono il testo per riga |

## 3. Le due forme

### A — Un testo unico che elenca i casi (⛔ scartata da Tid, 2026-10-09)

Si riscrive la riga 5 di `presidi_testi.csv`: `azione` dice cosa fare **per
ciascuno stato**, e chi legge cerca nell'elenco quello della sua riga.

* Costo: una cella di CSV, nessun cambio al modello, al BE o al FE.
* Limite: a decidere quale rimedio vale è chi legge, non il sistema. Il database
  conosce già la causa e non la usa. Il testo diventa lungo, e il collaudo del
  19-09 (`presidi_testi.md` §Scopo) ha già mostrato che un testo lungo non viene letto.
* ⛔ È la soluzione che va bene solo per i dati di oggi: al prossimo presidio
  con più cause si riscrive di nuovo un elenco.

### B — Il testo scelto dalla causa della riga (✅ decisa da Tid, 2026-10-09)

1. **La causa è una colonna della vista.** `dbops.vw_processi_programmazione`
   (e quindi la vista `da_guardare`, che la proietta) dichiara `causa`, più fine
   di `stato` dove lo stato non basta: **una causa per riga della tabella del
   §1**. Dove lo stato identifica già la causa, la causa è lo stato
   (`NON_PROGRAMMATO`, `JOB_ASSENTE`, `JOB_SPENTO`, `GIRA_E_NON_REGISTRA`); si
   separano solo i due stati ambigui: `MUTO` → `TIMER_FERMO` / `SERVIZIO_GIU`,
   `MAI_PARTITO` → `TIMER_NON_INSTALLATO` / `JOB_MAI_PARTITO`. ⛔ Non si
   accorpano cause con rimedi diversi sotto una sola etichetta: sarebbe lo stesso
   difetto di oggi, spostato di un livello. Il vocabolario finale lo fissa il
   team DB: è il team che conosce il CASE.
   ⭐ Va calcolata **nello stesso CASE** che produce `stato`: un secondo CASE
   farebbe due elenchi degli stessi casi, e prima o poi i due elenchi divergono
   (stesso motivo per cui `da_guardare` sta accanto al CASE).
2. **`presidi_testi` può avere una variante.** Una colonna `variante text NULL`
   entra nella chiave (`vista`, `lingua`, `variante`). `NULL` è il testo del
   presidio, come oggi; una variante valorizzata è il testo per le righe con
   quella causa.
3. **Il catalogo dice da quale colonna si legge la variante.**
   `dbops.presidi.colonna_variante text NULL` (qui `causa`). Così la regola vale
   per qualsiasi presidio, non solo per questo, e il BE non ha un nome di
   colonna scritto nel codice.
4. **Completezza, sul modello dei test esistenti** (`test-presidi-testi-v1.sql`):
   un presidio con `colonna_variante` ha la riga italiana **per ogni causa**
   che la vista può produrre. ⛔ Il testo generico (`NULL`) **non** fa da ripiego
   per una causa senza testo: tornerebbe a dare il rimedio sbagliato, cioè il
   difetto di oggi, e in silenzio. Una causa senza testo è un test rosso. Il
   pgTAP **costruisce** ogni causa e verifica che abbia il suo testo: non basta
   confrontare con le righe di oggi, perché su un database ricostruito da zero
   (in CI) non ce n'è nessuna. Il ripiego per lingua resta com'è (una lingua
   che manca ripiega sull'italiano **della stessa causa**).

Ricaduta BE/FE (la segnalo qui, la fa il team BE): `presidi_repository`
consegna il testo **per riga** quando il presidio ha una variante, il digest
raggruppa per causa, e `PresidiProcessiPanel` mostra il rimedio accanto alla riga
invece che una volta sola in testa.

### Testi proposti per la forma B (da rivedere col team DB)

| Causa | `significato` | `azione` |
| --- | --- | --- |
| `TIMER_FERMO` | Un processo automatico non è partito quando doveva. | Avvisa chi gestisce il server: il timer di questo processo non sta girando. Se in Processi automatici il processo ha «Esegui ora», intanto puoi lanciarlo a mano. |
| `TIMER_NON_INSTALLATO` | Un processo automatico non è mai partito su questo server: il suo timer non è stato installato. | Avvisa chi gestisce il server: va lanciata l'installazione dei timer. «Esegui ora» non funziona finché il timer non è installato. |
| `SERVIZIO_GIU` | Un servizio che deve restare sempre acceso non è collegato al database: è spento, oppure ha perso la connessione. | Avvisa chi gestisce il server: il servizio va riavviato. |
| `NON_PROGRAMMATO` | Un processo che dovrebbe partire da solo nel database non ha un lavoro programmato che lo faccia partire. | Avvisa lo sviluppo: il catalogo dei processi non dice quale lavoro lo sveglia. |
| `JOB_ASSENTE` | Il lavoro programmato che deve far partire un processo non esiste nel database. | Avvisa chi gestisce il database: il lavoro va installato. |
| `JOB_SPENTO` | Il lavoro programmato che fa partire un processo è stato spento. | Avvisa chi gestisce il database: va riacceso, oppure va chiarito chi l'ha spento e perché. |
| `JOB_MAI_PARTITO` | Un lavoro programmato nel database è acceso ma non è mai partito. | Avvisa chi gestisce il database: il programmatore dei lavori del database non sta girando. |
| `GIRA_E_NON_REGISTRA` | Un lavoro programmato è partito, ma non ha lasciato traccia della sua corsa. | Avvisa lo sviluppo: il lavoro si interrompe prima di riuscire a registrare l'esito. |

⚠️ I testi sono scritti per la **causa**, non per il processo che oggi la
produce: `SERVIZIO_GIU` non nomina la cache dei permessi anche se oggi l'unico
servizio è il listener dei permessi. Un testo che dipende da chi c'è oggi
diventa sbagliato al secondo servizio.

## 4. Fuori da questo brief

* Il pulsante «Riavvia» per i servizi: è il secondo pezzo di
  `work-done/analisi-riavvio-processi-da-interfaccia.md`, fermo sulla decisione
  **D1** (l'host). Quando ci sarà, l'`azione` di `SERVIZIO_GIU` potrà indicarlo.
* Il listener che non si accorgeva della connessione persa: sanato lato BE il
  2026-10-09, non richiede niente al DB.
