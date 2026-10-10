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
> **Stato (2026-10-09):** ✅ **lato DB chiuso.** `20261009-32…37` applicati da
> Tid (i `−32…−35` alle 15:20, i `−36/−37` dopo), pgTAP eseguiti da Tid: nessuna
> regressione. Tocca al **team BE/FE** (§5.4).
>
> 🔴 **URGENTE per il BE — da fare subito, prima del resto del §5.4.** Su dbdev
> `dbops.presidi_testi` porta già le otto righe di causa del presidio dei processi.
> `presidi_repository._TESTO_PER_LINGUA` cerca il testo con
> `WHERE pt.vista = p.vista AND pt.lingua IN (…) ORDER BY … LIMIT 1`: per
> `dbops.vw_processi_programmazione_da_guardare` ora trova **nove** righe per
> lingua e ne restituisce **una qualsiasi**, quindi pannello e digest possono
> mostrare il rimedio di una causa a caso come testo del presidio. Rimedio di una
> riga: aggiungere `AND pt.variante IS NULL` (il testo del presidio). Vale per
> ogni presidio, non solo per questo.
>
> ✅ **2026-10-10, BE:** il rimedio urgente è fatto (§6.1). 🔵 **Al team DB: R-2, il
> conteggio per causa (§6.2)**, che serve al digest per raggruppare per chi agisce. Il
> testo per causa nel pannello e nel digest si fa intanto (§6.3).
>
> ✅ **2026-10-10, DB: R-2 applicato da Tid, pgTAP verdi** — compresi i due di `vendite`
> «senza veste», che provano come app il percorso INVOKER → DEFINER (§7). **Lato DB chiuso.**
> ⏳ Resta al **team BE/FE**: il giro del §6.4 (conteggio per causa, digest per chi agisce
> della causa, conteggio nel pannello), poi il collaudo a video di Tid e l'archivio.
>
> **Da leggere per primo:** §6.4, con la lettura in §7.4.

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

## 5. Consegna DB (2026-10-09)

### 5.1 Che cosa è stato scritto

| changeSet / file | Che cosa fa |
| --- | --- |
| `00_schema/dbops/20261009-32-alter-presidi-add-colonna-variante` | `dbops.presidi.colonna_variante text NULL` + `chk_presidi_colonna_variante_non_vuota` |
| `00_schema/dbops/20261009-33-alter-presidi-testi-add-variante` | `dbops.presidi_testi.variante text NULL` + `chk_presidi_testi_variante_non_vuota`; la chiave passa da `uq_presidi_testi_vista_lingua` a `uq_presidi_testi_vista_lingua_variante` **NULLS NOT DISTINCT** |
| `20_code/dbops/20261009-34-update-vw-processi-programmazione-causa` | il panorama porta `causa` in coda; ogni ramo del CASE consegna la coppia `[stato, causa]`; `da_guardare` = `causa IS NOT NULL` |
| `20_code/dbops/20261009-35-update-vw-processi-programmazione-da-guardare-causa` | il presidio proietta `causa` in coda |
| `80_data/sql/dbops/presidi.csv` + mirror `20260910-35` | `colonna_variante = causa` sul presidio dei processi, `NULL` altrove |
| `80_data/sql/dbops/presidi_testi.csv` + mirror `20261006-06` | colonna `variante`, chiave `vista,lingua,variante`; le otto cause coi testi del §3; il testo generico del presidio riscritto **neutro** (non dà più un rimedio: «per ogni processo segui il rimedio indicato accanto alla sua causa») |
| `db/pgtap/dbops/test-presidio-processi-testo-per-causa-v1.sql` (nuovo, 15 test) | censimento delle cause dalla **definizione** del panorama; ogni causa ha il suo testo `it`; nessun testo per una causa ritirata; ogni causa ha una costruzione; le otto cause **costruite** una per una; i tre sani senza causa |
| `db/pgtap/dbops/test-presidi-testi-v1.sql` (7 → 14 test) | il test 2 pretende il testo **generico**; 8-14: la colonna della variante esiste nella vista, varianti solo dove il catalogo le chiede, ripiego per lingua dentro la stessa variante, NULLS NOT DISTINCT (clausola e comportamento), vuoti rifiutati |
| doc manuale | `presidi_testi`, `presidi`, `vw_processi_programmazione`, `vw_processi_programmazione_da_guardare` |

Vocabolario delle cause: quello proposto nel §3, invariato (`TIMER_FERMO`,
`TIMER_NON_INSTALLATO`, `SERVIZIO_GIU`, `NON_PROGRAMMATO`, `JOB_ASSENTE`,
`JOB_SPENTO`, `JOB_MAI_PARTITO`, `GIRA_E_NON_REGISTRA`). I testi sono quelli del §3.

### 5.2 Scelte di forma fatte qui

* **Stato e causa in una coppia.** Il CASE consegna `ARRAY['MUTO', 'SERVIZIO_GIU']`
  e le colonne la proiettano: un ramo, due fatti, nessun secondo CASE.
* **`da_guardare` = «ha una causa».** Il vecchio `stato NOT IN ('OK',
  'FUORI_PORTATA', 'SU_RICHIESTA')` era un secondo elenco degli stati sani
  accanto al CASE. Ora il guasto è *definito* dall'avere una causa: una riga da
  guardare senza rimedio non può esistere (test 14-15 del file nuovo). Il
  risultato è identico ramo per ramo.
* ⭐ Il test di completezza **non dipende dalle righe di oggi né da pgAgent**:
  l'elenco delle cause si legge da `pg_get_viewdef`, quindi in CI (zero
  processi guasti, pgAgent assente) è lo stesso. Le tre cause pgAgent si
  costruiscono con un job finto in `pgagent.pga_job` dove si può, e si
  dichiarano con `skip()` altrove.

### 5.3 Prova (sessione DB, 2026-10-09)

Su `zeroerp_ci` (migrato fino al `20261009-61`, nessuno dei changeSet sopra),
come `zeroerp`, in transazioni annullate: SQL **estratto** dai quattro
changeSet + i due mirror resi con `updateSQL` offline + un pgTAP per
transazione, con il log via dblink spento.

| File | Esito |
| --- | --- |
| `test-presidio-processi-testo-per-causa-v1` | 15/15 (pgAgent costruito: anche 11-13 veri) |
| `test-presidi-testi-v1` | 14/14 |
| `test-vw-processi-programmazione` | 21/21 |
| `test-vw-processi-programmazione-da-guardare` | 7/7 |
| `test-catalogo-presidi-v1` | 11/11 |
| file nuovo **senza** le modifiche | rosso al test 1, poi si ferma (colonna assente) |
| mutazione: tolto il testo di `SERVIZIO_GIU` | rosso il test 3, che nomina `SERVIZIO_GIU` |
| mutazione: chiave senza NULLS NOT DISTINCT | rossi i test 11 e 12 |
| mirror dei testi rilanciato due volte | 51 righe, nessun doppione (Liquibase cerca la riga generica con `variante is NULL`) |

⚠️ Non provato: l'apply vero (preConditions comprese), la corsa dal runner, la
baseline. Sono di Tid.

### 5.4 Ricaduta BE/FE — precisa

1. 🔴 **URGENTE — l'apply è già avvenuto (vedi intestazione).** `presidi_repository._TESTO_PER_LINGUA` legge il
   testo con `WHERE pt.vista = p.vista AND pt.lingua IN (…) … LIMIT 1`: appena il
   seed porta le varianti, quella LATERAL pesca **una riga qualsiasi** fra il
   generico e le otto cause. Serve `AND pt.variante IS NULL` (il testo del
   presidio). Prima dell'apply la colonna non esiste: le due cose vanno nello
   stesso giro.
2. Il testo **per riga**: quando `dbops.presidi.colonna_variante` non è NULL, il
   repository legge quella colonna dalla vista e cerca il testo con
   `variante = <valore>`, lingua richiesta poi `it` **della stessa variante**.
   ⛔ Mai ripiegare sul generico (`variante IS NULL`) per una causa senza
   testo: i pgTAP garantiscono che non succeda, e un ripiego silenzioso rifarebbe
   il difetto di oggi.
3. Il digest raggruppa per causa; `PresidiProcessiPanel` mostra il rimedio accanto
   alla riga. Il nome della colonna (`causa`) **non** va scritto nel codice: si
   legge da `colonna_variante`.
4. (dal §5.6) **A chi tocca, per riga**: per un presidio con `colonna_variante`,
   `chi_agisce` della riga si legge da `dbops.presidi_cause` (`vista`, `causa` =
   valore della colonna), non da `dbops.presidi.chi_agisce`. Il digest raggruppa
   per quel valore: le righe `NON_PROGRAMMATO` e `GIRA_E_NON_REGISTRA` vanno allo
   **sviluppo**, le altre sei al sistemista. `dbops.presidi.chi_agisce` resta il
   valore del presidio nel suo insieme (intestazione, conteggi).

### 5.5 ✅ Decisione di Tid (2026-10-09): (b) — chi agisce, per causa

`dbops.presidi.chi_agisce` dice, per presidio, a chi tocca spegnerlo; il suo
COMMENT lo vuole un **dato** «perché il pannello deve poter distinguere *tocca a
te* da *inoltra* e il digest deve poter raggruppare». Il presidio dei processi è
`SISTEMISTA`, ma due cause su otto (`NON_PROGRAMMATO`, `GIRA_E_NON_REGISTRA`)
toccano allo **sviluppo**: oggi lo dice solo la frase («Avvisa lo sviluppo»), e il
digest le raggruppa sotto il sistemista. È lo stesso difetto del §1 un livello
sopra — un valore unico per righe diverse.

* **(a) Lasciare così** — l'azione dice a chi inoltrare; il raggruppamento del
  digest resta per presidio.
* **(b) ⭐ consigliata — un catalogo delle cause**: `dbops.presidi_cause (vista,
  causa, chi_agisce)`, con FK da `presidi_testi (vista, variante)`. La causa
  diventa un'entità con il suo «chi agisce»; i testi restano figli per lingua.
  È additivo su quanto scritto oggi (nessuna colonna da rifare), e il
  censimento del pgTAP confronterebbe la vista con il catalogo invece che con i
  testi.

Non l'ho fatta: la forma B decisa non la prevede, e cambia ciò che il BE legge.
⇒ **Tid ha scelto (b)** lo stesso giorno: §5.6.

### 5.6 Il catalogo delle cause (2026-10-09, ✅ applicato da Tid, pgTAP senza regressioni)

| changeSet / file | Che cosa fa |
| --- | --- |
| `00_schema/dbops/20261009-36-create-presidi-cause` | `dbops.presidi_cause (vista, causa, chi_agisce)`, UNIQUE `(vista, causa)`, FK `vista` → `dbops.presidi`, CHECK di dominio su `chi_agisce` (stesso di `chk_presidi_chi_agisce`); FK **NOT VALID** `fk_presidi_testi_presidi_cause` da `presidi_testi (vista, variante)`; `GRANT SELECT` a `zeroerp_app` |
| `90_end/20261009-37-validate-fk-presidi-testi-presidi-cause` | convalida la FK dopo il seed |
| `80_data/sql/dbops/presidi_cause.csv` (nuovo) | le otto cause: sei `SISTEMISTA`, `NON_PROGRAMMATO` e `GIRA_E_NON_REGISTRA` `SVILUPPO` |
| mirror `80_data/20261006-06` | carica **prima** le cause, **poi** i testi (due `loadUpdateData`, un changeSet) |
| pgTAP `test-presidi-testi-v1` (14 → 19) | 9 ora sulle cause; 15 dominio `chi_agisce` identico nei due CHECK; 16 ogni causa ha il testo `it`; 17 chi dichiara `colonna_variante` ha cause; 18 FK convalidata; 19 GRANT |
| pgTAP `test-presidio-processi-testo-per-causa-v1` (15 → 16) | 3-4: le cause della vista **coincidono** col catalogo; 16: ognuna ha il testo |
| doc manuale | nuova `presidi_cause`; aggiornate `presidi_testi`, `presidi`, `vw_processi_programmazione` |

⭐ **Perché la FK nasce NOT VALID e il seed sta nel mirror vecchio.** Su dbdev le
otto varianti esistono già (apply delle 15:20) e il catalogo delle cause è vuoto:
una FK convalidata subito fallirebbe. E in `80_data` l'ordine è il nome del file:
un mirror delle cause numerato oggi girerebbe **dopo** `20261006-06`, e la prossima
causa aggiunta ai due CSV insieme farebbe fallire la FK nel mirror dei testi. Con
le cause caricate come primo passo dello stesso changeSet, l'ordine è giusto sempre.

**Prova** (scratch `zeroerp_ci`, che ha già `−32…−35` come dbdev; SQL estratto +
mirror reso con `updateSQL` offline, transazioni annullate):

| Percorso | `test-presidi-testi-v1` | `…-testo-per-causa-v1` | `test-catalogo-presidi-v1` | `…-da-guardare` |
| --- | --- | --- | --- | --- |
| dbdev (varianti già presenti) | 19/19 | 16/16 | 11/11 | 7/7 |
| da zero (varianti assenti prima del mirror) | 19/19 | 16/16 | 11/11 | 7/7 |

Mutazioni: tolta la causa `SERVIZIO_GIU` (e il suo testo) → rossi i test 3 e 16, che
la nominano; un testo con una causa inventata → rifiutato dalla FK già NOT VALID.
Guardrail statici verdi. ⚠️ Non provati: apply vero, runner, baseline (di Tid).

## 6. Giro BE/FE (sessione backend, 2026-10-10)

### 6.1 Fatto

* ✅ §5.4.1, il rimedio urgente: `presidi_repository._TESTO_PER_LINGUA` legge il testo
  del presidio con `pt.variante IS NULL`. Prove: il test 9 di `test_presidi_repository`
  legge l'SQL (mutazione senza filtro: rosso); `test_presidi_catalogo` 9-bis confronta,
  sul database vero, il testo consegnato con la riga generica del seed. ⚠️ Il 9-bis è un
  presidio della giuntura, non la prova del filtro: senza filtro il `LIMIT 1` sceglie per
  ordine fisico, e sul dbdev il 2026-10-10 pescava proprio il generico (mutazione: verde).

### 6.2 🔵 Richiesta al team DB — R-2: il conteggio per causa

**Perché serve.** Il §5.4.3-4 chiede che il digest raggruppi per causa e per chi agisce
della causa. Il BE però ha un solo numero per presidio (`dbops.fn_conta_presidio`) e un
**campione** di righe: 5 nel digest, 20 nel pannello. Raggruppare il campione darebbe
conteggi per causa sbagliati appena le righe sono più del campione, e una causa
`SVILUPPO` oltre la quinta riga non arriverebbe mai al gruppo dello sviluppo: è lo stesso
difetto del §1, spostato sul conteggio. Il conteggio, per la regola del repository, non
si fa nel BE (il filtro `colonna_stato` e la RLS stanno nella funzione). ⇒ Decisione di
Tid, 2026-10-10: lo dà il DB.

| # | Cosa | Tipo | Bloccante per il BE |
| --- | --- | --- | --- |
| R-2 | `dbops.fn_conta_presidio_per_variante(p_vista text) RETURNS TABLE (variante text, conteggio bigint)` | funzione `20_code` | sì: il raggruppamento del digest per chi agisce e i conteggi per causa nel pannello |

Contratto proposto (la forma la fissa il team DB):

1. **Stesso perimetro e stesso filtro di `fn_conta_presidio`**: `SECURITY DEFINER`, vista
   a catalogo attiva oppure `E_PRESIDIO_NON_A_CATALOGO`, `colonna_stato IS DISTINCT FROM
   stato_atteso` quando c'è. ⭐ Meglio se le due funzioni condividono la costruzione del
   `FROM … WHERE`: due copie del filtro divergono.
2. `GROUP BY` la colonna nominata da `dbops.presidi.colonna_variante` (`%I`). Una riga per
   valore presente; i valori a zero non si restituiscono.
3. Presidio **senza** `colonna_variante`: una riga sola, `variante = NULL`, conteggio
   uguale a `fn_conta_presidio`. Così non serve un codice d'errore nuovo, e il BE ha una
   lettura sola.
4. Una riga con la colonna della variante a `NULL`, in un presidio che la dichiara, esce
   come gruppo `NULL`: il modello lo ammette anche se la vista dei processi oggi non lo
   produce. Il BE lo mostra come «causa non indicata», **senza** ripiegare sul testo
   generico (§5.4.2).
5. `GRANT EXECUTE` a `zeroerp_app`, come `fn_conta_presidio`.
6. pgTAP: la somma dei conteggi è uguale a `fn_conta_presidio` per ogni presidio a
   catalogo; casi **costruiti**, cioè due cause con conteggi diversi, il filtro di stato che
   esclude e il presidio senza variante.

### 6.3 Il BE/FE nell'attesa di R-2

Si fa ora quello che non dipende dai conteggi: il testo **per causa** delle righe lette
(`presidi_cause` + `presidi_testi`, lingua richiesta poi `it` della stessa causa, nessun
ripiego sul generico), consegnato per gruppo di causa nel pannello e nel digest. Il
raggruppamento del digest per chi agisce della causa e i conteggi per causa si chiudono
con R-2.

✅ **Fatto il 2026-10-10** (non committato):

| Dove | Che cosa |
| --- | --- |
| `presidi_repository` | la scelta della lingua in una sede sola (`_testo_per_lingua`), con due lettori: il testo del presidio (`variante IS NULL`) e quello della causa (`variante = c.causa`); `colonna_variante` letta dal catalogo; `testi_delle_cause(vista)` (`presidi_cause` + `presidi_testi`); `cause_delle_righe(riga, righe)`, unica sede del raggruppamento, con il nome della colonna dal catalogo. Una causa senza testo, o assente dal catalogo, arriva con i campi a `None` e non eredita il testo del presidio |
| pannello (`stato_presidi` → `PresidiProcessiPanel`) | campo `cause`; a video ogni gruppo di righe ha sopra la causa, il badge del suo «chi agisce», l'azione e il significato; una causa senza testo lo dice |
| digest | `VocePresidio.cause`; testo e HTML rendono ogni causa con «causa — a chi tocca», il rimedio e le sue righe. La voce resta nel gruppo del presidio: lo spostamento per causa aspetta R-2 |
| doc | `api_amm_software.md` §presidi: `significato`, `azione`, `chi_agisce` (mancavano già) e `cause` |

Prove: `test_presidi_repository` 12-13, `test_presidi_digest` 27-28, `test_presidi_catalogo`
9-ter (e2e: ogni causa del catalogo arriva col suo testo; mutazione sul join: rosso),
`PresidiProcessiPanel.spec` 5-7. Ruff, mypy (baseline) e `check_i18n_keys` verdi.
⏳ Restano: R-2 (DB) e poi il giro BE che ne segue (§6.4); il collaudo a video dopo il
`kill -HUP` del backend.

### 6.4 Il giro BE dopo R-2 (da fare)

1. `PresidiRepository.conta_per_variante(riga)` su `dbops.fn_conta_presidio_per_variante`.
2. `cause_delle_righe` parte dai **conteggi** (tutte le cause accese, anche senza righe nel
   campione) e aggiunge a ciascuna le righe del campione; ogni causa porta il suo
   `conteggio`.
3. Digest: una voce per (presidio, causa) nel gruppo del «chi agisce» della causa, così
   le righe `NON_PROGRAMMATO` e `GIRA_E_NON_REGISTRA` vanno allo sviluppo (§5.4.4).
   L'intestazione e il conteggio del presidio restano su `dbops.presidi.chi_agisce`.
4. Pannello: il conteggio accanto a ogni causa.

## 7. Consegna DB di R-2 (2026-10-10)

### 7.1 Che cosa è stato scritto

| changeSet / file | Che cosa fa |
| --- | --- |
| `20_code/dbops/20261010-41-create-fn-conta-presidio-per-variante` | `dbops.fn_conta_presidio_per_variante(p_vista) RETURNS TABLE (variante, conteggio bigint)`, `SECURITY DEFINER` del proprietario, `search_path` pinnato come `fn_conta_presidio`, `GRANT EXECUTE` a `zeroerp_app` |
| `20_code/dbops/20261010-42-update-fn-conta-presidio-somma-per-variante` | `dbops.fn_conta_presidio` = `coalesce(sum(conteggio), 0)` della funzione sopra; passa a `SECURITY INVOKER`. Firma e risposta invariate |
| `db/pgtap/dbops/test-conta-presidio-per-variante-v1.sql` (nuovo, 13 test) | rifiuto fuori catalogo e su NULL; senza variante una riga anche a zero; caso **costruito** con due cause a conteggi diversi, filtro di stato, causa sana assente, gruppo NULL, stato nuovo che conta; somma; zero gruppi → `fn_conta_presidio` = 0 e non NULL; `fn_conta_presidio` non contiene più il filtro (sorgente); DEFINER/INVOKER; `search_path`; GRANT; i presidi veri con variante rispondono |
| `db/pgtap/dbops/test-catalogo-presidi-v1.sql`, test 11 | risale al proprietario della **sede** (`fn_conta_presidio_per_variante`): è lei la DEFINER che legge le viste |
| doc manuale | nuova `fn_conta_presidio_per_variante`; aggiornate `fn_conta_presidio` e `presidi` |

Il contratto del §6.2 è rispettato punto per punto: perimetro e filtro uguali (sono
gli stessi, §7.2), `GROUP BY` della colonna nominata dal catalogo con `%I`, una riga per
valore presente, presidio senza variante = una riga con `variante NULL` (anche a zero),
il NULL come gruppo a sé, `GRANT` all'app, pgTAP sui casi costruiti.

### 7.2 Scelte di forma fatte qui

* ⭐ **La sede è il conteggio per variante, e `fn_conta_presidio` ne è la somma.** Il
  §6.2.1 chiedeva di condividere il `FROM … WHERE`. Il conteggio per gruppi contiene il
  conteggio intero, il contrario no: quindi una sede sola, e la copia ritirata nello
  stesso giro (regola del 2). Le due risposte **non possono** divergere, invece di
  provare che oggi coincidono.
* **Il pgTAP prova il sorgente, non l'uguaglianza.** Il §6.2.6 chiedeva «la somma è
  uguale a `fn_conta_presidio` per ogni presidio»: dal `-42` è vero per costruzione e non
  proverebbe niente. Il test 9 pretende invece che `fn_conta_presidio` non legga il
  catalogo né applichi un filtro, e chiami la sede (linee-guida-sql §12.5.2). Il test 13
  esegue la sede sui presidi **veri** con variante, perché lì può rompersi (colonna
  rinominata, tipo): e se il catalogo non ne dichiara nessuno è rosso, non vuoto.
* **`fn_conta_presidio` diventa `SECURITY INVOKER`.** Non legge più niente da sé; la
  RLS la attraversa la sede, che è DEFINER. Lasciarla DEFINER sarebbe un privilegio senza
  motivo.
* **Ordine dei gruppi**: per valore, il NULL in coda. Stabile, il BE può leggerlo così.
* **Il valore esce come testo** (`::text`): la colonna della vista può avere un tipo
  suo, la variante a catalogo è testo.
* ⚠️ **Non toccati**: le descrizioni di `E_PRESIDIO_NON_A_CATALOGO` in
  `codici_errore.csv` e `messaggi_errore.csv` nominano `dbops.fn_conta_presidio`. Restano
  vere (chi chiama il conteggio intero riceve quel codice), e svegliare due mirror per
  una frase descrittiva non comprava niente. Il contesto del log ora nomina
  `fn_conta_presidio_per_variante`, che è il sito che solleva.

### 7.3 Prova (sessione DB, 2026-10-10)

Su `zeroerp_ci` (migrato fino al `20261010-40`), come `zeroerp`, in transazioni
annullate: SQL **estratto** dai due changeSet + un pgTAP per transazione, log via
dblink spento.

| File | senza | con |
| --- | --- | --- |
| `test-conta-presidio-per-variante-v1` | rosso (la funzione non esiste) | 13/13 |
| `test-catalogo-presidi-v1` | 11/11 | 11/11 |
| `test-presidi-testi-v1` | 19/19 | 19/19 |
| `test-presidio-processi-testo-per-causa-v1` | 16/16 | 16/16 |
| `test-vw-processi-programmazione` / `…-da-guardare` | 21/21, 7/7 | 21/21, 7/7 |
| `test-vw-email-da-guardare`, `test-sorgenti-orfane-v1`, `test-articoli-a-magazzino-prontezza-v1`, `magazzino/test-valore-giacenza-divergenza-owner-v1` | verdi | verdi |
| `vendite/test-lotti-fermi-verdetto-a-db-v1` | 20/21 | 20/21 |
| `vendite/test-annullamento-chiude-la-vita-v1` | 16/17 | 16/17 |
| `test-riferimenti-morti-v1` (plpgsql_check su ogni funzione) | — | 9/9 |
| `test-catalogo-messaggi-errore-completo`, `test-codici-errore-identita`, `-obsoleto-dal` | — | verdi |

⚠️ I due rossi di `vendite` (18 e 16, «senza veste la vista risponde zero») sono
**identici prima e dopo**: da owner la RLS non c'è, quindi sono rossi per costruzione e
verdi come app. Sono però i test che provano il percorso **app → `fn_conta_presidio`
(ora INVOKER) → sede DEFINER**: la proprietà l'ho provata a parte su un cluster PG18
usa-e-getta con ruoli di login veri (tabella in RLS con policy sulla GUC, vista
`security_invoker`, la stessa coppia di funzioni): come app, la vista diretta senza GUC
dà 0, la somma 3, i gruppi `A|2`, `B|1`.

Mutazioni sul file nuovo: solo `-41` senza `-42` (la copia del filtro resta) → rossi 9 e
10; `coalesce` tolto → rosso 8; gruppo NULL scartato → rossi 5 e 6.
`plpgsql_check`: `fn_conta_presidio` pulita; la sede ha due `warning extra` (variabili
OUT con `RETURN QUERY EXECUTE`), che il presidio dei riferimenti morti non conta.
Guardrail statici (letterali, `runOnChange`, preCondition, timestamp, grant batch,
trigger di automazione, v1, preambolo pgTAP) verdi.

✅ **Apply e corsa pgTAP di Tid, 2026-10-10: verdi**, compresi `vendite/test-lotti-fermi-verdetto-a-db-v1`
(18) e `vendite/test-annullamento-chiude-la-vita-v1` (16) come app: il percorso app →
`fn_conta_presidio` (INVOKER) → sede (DEFINER) attraversa la RLS anche dal runner.

### 7.4 Per il giro BE (§6.4)

* La lettura è `SELECT variante, conteggio FROM dbops.fn_conta_presidio_per_variante(%s)`
  — ⛔ non `SELECT dbops.fn_…(…)`, che consegna la tupla in un campo solo.
* Un presidio senza variante dà **una** riga `(NULL, n)`: per il conteggio del presidio
  resta `fn_conta_presidio`, invariata.
* Un presidio con variante e niente da guardare dà **zero** righe.
* Un gruppo `variante = NULL` in un presidio con variante è «causa non indicata»
  (§6.2.4): non eredita il testo generico (§5.4.2).
* Nessun codice d'errore nuovo: fuori catalogo resta `E_PRESIDIO_NON_A_CATALOGO`.
