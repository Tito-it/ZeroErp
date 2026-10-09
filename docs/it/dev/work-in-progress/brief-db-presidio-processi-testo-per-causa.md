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
> **Da leggere per primo:** §5.4.

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

