# Brief DB — gli otto residui che il backend chiede per chiudere i processi automatici

> **Destinatario:** team DB (`dev/db-tid`).
>
> **Origine.** Il lavoro DB del cantiere «nessun processo senza operatore» è **chiuso e
> pushato** ([brief-db-processi-automatici-identita-e-perimetro.md](brief-db-processi-automatici-identita-e-perimetro.md),
> merge `e09a4c2cf`). Il backend lo sta ora consumando, secondo
> [piano-be-fe-processi-automatici-identita-e-perimetro.md](piano-be-fe-processi-automatici-identita-e-perimetro.md).
> Leggendo il contratto — e provando a scrivere il primo presidio — sono emerse **otto
> cose che il BE non può darsi da solo**.
>
> **Stato:** 🔵 **RICHIESTA — niente scritto, niente applicato.**
>
> ⛔ **Questo brief dice che cosa serve e perché, non come farlo.** Forma, DDL, numerazione
> dei changeSet, seed e test sono decisioni di chi scrive: se il *cosa* qui sotto si
> ottiene meglio in un altro modo, il modo giusto è il vostro.
>
> ⚠️ **Nessuna delle otto è urgente allo stesso modo.** Tre bloccano qualcosa del piano
> BE, due sono debiti già vostri che il BE **eredita** e che vale la pena datare, due non
> bloccano niente. La colonna «blocca» lo dice riga per riga.

---

## 0. In due parole

Il registro dei processi funziona: il backend adesso sa nominare i processi, il giornale
dei run ha l'attore, la coda rifiuta un lavoro di dominio senza operatore.

Restano sette cose. Una serve a far **migrare la chiusura scadenze** sulla coda; una perché
un presidio **non nasca già rumoroso**; due sono debiti del vostro registro che adesso hanno un consumatore
che ci sbatte contro — uno è `email_outbox`, l'altro **non era quello che credevo**
(§DB-4); una è la **stretta finale** su una colonna, da fare quando il BE avrà finito il
suo pezzo. L'ultima è un **buco piccolo nella fabbrica** degli utenti tecnici, trovato
provando a usarla, e la settima e' un disallineamento di nomi
che impedisce a un presidio di arrivare a zero — trovata guardando il presidio.

---

## 1. Il quadro: chi aspetta chi

| # | Serve a | Blocca | Chi va per primo |
| --- | --- | --- | --- |
| **DB-1** | far diventare la chiusura scadenze un lavoro di coda | ⛔ sì, il lotto 4 del piano BE | **DB** |
| **DB-2** | rendere leggibile il presidio «dominio senza emittente» | ⚠️ non blocca, ma peggiora ogni giorno che passa | **DB** |
| **DB-3** | dare un perimetro a `send_pending_emails` | ⛔ sì, per la parte «un emittente alla volta» | **DB** |
| **DB-4** | ⚠️ *riscritta* — il **write-guard** su `vendite.fatture_stampa_coda`, ultima riga del livello 2 | ⚠️ no | **DB** |
| **DB-5** | rendere obbligatorio l'attore sui run | — | **BE**, poi DB |
| **DB-6** | poter rifare l'utente tecnico di un processo ritirato male | ⚠️ no — ma il caso oggi esce con un errore che non parla | **DB** |
| **DB-7** | 🔴 far coincidere i nomi dei job pgAgent col registro: **quattro non si dichiareranno mai** | ⛔ sì, impedisce a `vw_run_senza_attore` di arrivare a zero (DB-5) | **DB** |
| **DB-8** | un codice errore per «processo non trovato nel registro» | ⚠️ no — c'è un ripiego dichiarato | **DB** |

---

## DB-1 — La chiusura scadenze ha bisogno di una casa nella coda

**Che cosa serve.** Un tipo di lavoro della coda con cui il backend possa accodare
*«chiudi le scadenze di questo emittente»*, e il processo registrato a cui quel tipo
appartiene.

**Perché.** `chiusura_scadenze_daily` è oggi l'**unico** processo di classe `DOMINIO` che
gira in pgAgent: cambia lo stato gestionale di righe applicative ogni notte, senza attore
e senza perimetro. La vostra analisi (§8.2) ha già deciso che *migra intero* sulla coda,
un emittente alla volta, con l'utente tecnico. Il backend ha già il motore, l'handler e i
produttori: gli manca il **vocabolario**, cioè un tipo che possa nominare.

⚠️ **Il vincolo se lo è dato il cantiere stesso**: un tipo di coda pretende un processo
registrato (la FK c'è già), e un processo di dominio non può essere accodato se non come
`OPERATORE`. Sono entrambe cose giuste: le nomino perché il tipo nuovo ci nasce dentro,
non perché vadano cambiate.

**🔵 Un punto da concordare, non una richiesta.** Chi **accoda** i lavori: il job pgAgent
di stasera, che smetterebbe di eseguire e comincerebbe a produrre, oppure un comando
Django su cron come per la fatturazione? Tocca tutti e due i lati, e la risposta cambia
poco al DB e parecchio al BE. Ne parliamo prima che uno dei due scriva.

**Come si vede che è chiuso.** Il backend riesce ad accodare un lavoro di chiusura
scadenze per un emittente, e `dbops.vw_processi_dominio_senza_emittente` resta vuota.

---

## DB-2 — Un presidio che non sarà mai vuoto smette di essere letto

**Che cosa serve.** Che `dbops.vw_processi_dominio_senza_emittente` sappia distinguere una
riga **attesa** da una riga **nuova**.

**Perché — ed è una contraddizione nel contratto, non un'opinione.** La descrizione della
vista dice:

> *«DEVE restare VUOTA»*

e il seed di `dbops.processi_bersagli` dice, sulla riga di `config.email_outbox`:

> *«DEBITO DICHIARATO … Riga attesa in `vw_processi_dominio_senza_emittente` finché il
> cantiere email non chiude»*

Le due frasi non possono essere vere insieme. E la conseguenza non è formale: **un
presidio che è sempre acceso viene ignorato**, e il giorno in cui comparirà una riga vera
— un processo nuovo dichiarato di dominio e progettato senza percorso all'emittente —
nessuno la distinguerà dal rumore di fondo. È esattamente il difetto che quella vista
esiste per prendere *mentre si progetta*.

⭐ **Il progetto ha già risolto questo problema una volta**, nello stesso cantiere:
`dbops.vw_processi_che_bypassano` porta il proprio debito **dichiarato dentro di sé**, con
lo stato e la fase in cui si chiude. Lo cito come precedente, non come prescrizione: la
forma la decidete voi.

⚠️ **La stessa domanda vale per la vista sorella** `vw_processi_dominio_senza_difesa`, che
nasce dichiarata *«registro di debito, deve calare»* e oggi ha righe. Lì la natura è già
scritta nella descrizione, quindi il caso è meno grave — ma le due viste sono della stessa
famiglia e sarebbe bene che raccontassero il debito **allo stesso modo**. Il frontend deve
mostrarle in un pannello solo: se una dice «zero o allarme» e l'altra «cala», deve poterlo
leggere dal dato, non da una tabella di eccezioni scritta a mano nel codice.

**Come si vede che è chiuso.** Chi guarda le sei viste può rispondere a *«c'è qualcosa di
nuovo?»* senza sapere a memoria quali righe erano previste.

---

## DB-3 — `config.email_outbox` non sa a chi appartiene (R-7)

**Che cosa serve.** Che una riga di `config.email_outbox` porti l'emittente per cui è
stata scritta.

**Perché.** `send_pending_emails` è classificato **DOMINIO** — e correttamente: spedisce
fatture ai clienti. Ma la sua tabella non porta l'emittente, quindi è un processo di
dominio **senza percorso al perimetro**: il Caso B del vostro §13.1, quello che a runtime
non si può recuperare.

⇒ Il backend può dargli l'**attore** (lo fa nel lotto 1), ma **non può** fargli lavorare
un emittente alla volta: non c'è niente su cui filtrare. Finché è così, quel processo resta
l'unico di dominio che attraversa tutte le aziende, e la frase *«nessun processo
applicativo lavora fuori dal perimetro»* ha un'eccezione.

⚠️ Il debito è già registrato come **R-7** nel vostro brief: qui non aggiungo una
richiesta nuova, aggiungo **il consumatore** che ci sbatte contro e una data.

**Come si vede che è chiuso.** `dbops.vw_processi_dominio_senza_emittente` non nomina più
`send_pending_emails`.

---

## DB-4 — ⚠️ *Riscritta*: il write-guard manca su `vendite.fatture_stampa_coda`

> 🔴 **Questa richiesta diceva un'altra cosa, ed era sbagliata.** Diceva «le policy
> mancano su `vendite.listini*` (R-8)», copiando il vostro registro dei residui.
> **Interrogato il presidio il 2026-09-05: `vendite.listini_versioni` la policy ce
> l'ha**, e non compare in `dbops.vw_processi_dominio_senza_difesa`. R-8, per quel
> bersaglio, **è chiuso**.
> ⭐ È la ragione per cui un presidio si interroga invece di fidarsi di un elenco
> scritto: l'elenco invecchia, la vista no.

**Che cosa serve.** Il **write-guard** `script.trgfn_guard_emittente_scope` su
`vendite.fatture_stampa_coda`.

**Perché.** È l'unica riga rimasta nel livello 2 del presidio, e dice
*«write-guard (scrittura scoperta)»*. La tabella ha la policy RLS — armata il
2026-09-04 — quindi in **lettura** il perimetro c'è; in **scrittura** l'unico
presidio è la policy stessa.

⚠️ **E adesso ha un consumatore.** Dal 2026-09-05 il worker della coda stampa gira
con l'identità dell'utente tecnico di **un** emittente e marca l'esito su quelle
righe. Il perimetro regge — la policy filtra anche l'`UPDATE` — ma il livello 2 del
vostro presidio esiste apposta per dire che lì il «Caso A» non è completo: manca la
metà che si ferma da sola in scrittura.

⛔ **Non è urgente e non blocca**: lo segnalo perché è l'ultima riga di quel
registro, e un registro a una riga sola è a un passo dall'essere vuoto.

**Come si vede che è chiuso.** `dbops.vw_processi_dominio_senza_difesa` **vuota**.

---

## DB-5 — L'attore sui run diventa obbligatorio (a BE finito)

**Che cosa serve.** Che `maintenance.job_run_log.processo_codice` smetta di ammettere
l'assenza dell'attore.

**Perché.** La colonna è nata facoltativa **di proposito**, e la ragione era giusta: un
vincolo obbligatorio prima che i chiamanti sapessero passare il dato avrebbe fermato i
dodici job pgAgent al primo giro. *Un `NOT NULL` va dove il dato si può fornire.*

⇒ Adesso il backend lo fornisce: il lotto 1 del piano fa dichiarare il processo a tutti e
sei i comandi headless, compresi i tre che finora non si registravano affatto. Quando
`dbops.vw_run_senza_attore` sarà vuota, il ripiego non serve più — e finché la colonna
resta facoltativa, il prossimo processo potrà nascere senza attore senza che niente lo
dica.

⚠️ **Questa è l'unica delle cinque in cui il BE va per primo.** Ve la segnalo adesso
perché è la chiusura del cerchio e non voglio che resti a nessuno in fondo a un elenco: vi
scrivo io quando la vista è vuota.

⚠️ **E il criterio della vista è l'ULTIMA corsa**, non «esiste una corsa senza attore»: le
righe storiche resteranno `NULL` per sempre — sono giornale di ieri — ed è la scelta che vi
permette di arrivare davvero a zero. Lo scrivo perché è la cosa che, rileggendo fra sei
mesi, sembra un errore e non lo è.

**Come si vede che è chiuso.** Un run scritto senza attore viene rifiutato.

---

## DB-6 — Rifare l'utente tecnico di un processo: oggi si sbatte su un 23505

**Che cosa serve.** Che il caso *«questo processo ha un utente tecnico sbagliato o
ritirato male, se ne rifà uno»* si concluda con un rifiuto **che dice quale regola è**,
oppure funzioni.

**Perché.** `script.fn_crea_utente_tecnico` ha un guard esplicito sul duplicato — il
vostro guard 4 — e il commento dice bene perché esiste:

> *«Ci si ferma prima dell'unique: un 23505 nudo non direbbe quale regola.»*

⚠️ **Ma quel guard guarda `processi_identita.attivo`, e lo username no.** Lo username è
deterministico (`processo@emittente`) ed è `UNIQUE` senza condizioni. ⇒ Disattivare il
legame — che è **la via che voi stessi indicate** per sostituire l'utente di un processo
(«si disattiva la riga esistente e se ne crea una nuova») — libera il guard 4 e lascia in
piedi il muro: `auth_user_username_key`.

**Come l'ho trovato.** Non leggendo: **provando**. Scrivendo il presidio che tiene gli
utenti tecnici fuori dalle liste di persone di Amm. Software, la fixture doveva
fabbricarsi il proprio soggetto con la fabbrica vera — che è la forma giusta di un test.
Non ci è riuscita, e il test ora **dichiara** perché
(`apps/amm_software/tests/db/test_operatori_senza_utenti_tecnici.py`), invece di
nascondere il limite dietro un `skip` senza motivo.

⭐ **Il difetto non è nel test: è che la strada di sostituzione documentata non è
percorribile.** Finché è così, la §12.7 del vostro brief descrive un rimedio che non
funziona — ed è il tipo di frase che qualcuno seguirà fra sei mesi, di fretta, su un
processo che non fattura.

⚠️ **Non blocca niente** oggi: nessuno deve rifare un utente tecnico. Lo segnalo perché è
piccolo adesso e diventa un'ora persa il giorno in cui serve davvero.

**Come si vede che è chiuso.** Disattivare il legame di una coppia (processo, emittente) e
richiamare la fabbrica per la stessa coppia produce o un utente nuovo, o un errore con un
codice di dominio registrato.

---

## DB-7 — 🔴 Quattro job pgAgent non si dichiareranno mai: il registro usa nomi diversi

**Che cosa serve.** Che i nomi con cui i job pgAgent si presentano al giornale dei run
esistano in `dbops.processi`.

**Perché — sono due vocabolari, e si è dato per scontato che fossero uno.** La §3.3 del
vostro brief promette che *«i dodici job diventano conformi senza una riga in
`85_pgagent`»*, perché `fn_run_and_log` deriva il codice dal jobname quando quel jobname
corrisponde a un processo registrato. ⭐ Il meccanismo funziona. ⛔ Ma il registro è stato
seminato con i nomi dei **job di pgAgent**, mentre la funzione riceve il `p_jobname` che
gli passano i **wrapper `maintenance.proc_*_job`** — e i due insiemi non coincidono:

| Il wrapper passa | Il registro contiene |
| --- | --- |
| `apply_fk_index_policy` | `automations_apply_fk_indexes_policy` |
| `automations_cleanup` | `automations_cleanup_weekly` |
| `automations_lock_columns` | — (nessuna riga) |
| `automations_delete_block` | — (nessuna riga) |

⇒ Per quei nomi la derivazione non aggancia niente, l'attore resta `NULL`, e la riga
resta in `dbops.vw_run_senza_attore` **per sempre**: non c'è nessuna corsa futura che la
tolga.

**Fatto datato, 2026-09-05** (contesto, non la ragione): la vista ha sette righe. Due
(`apply_storicizza_weekly`, `sync_storico_set_storicizza`) hanno `processo_registrato =
true` e si toglieranno da sole alla prossima corsa notturna — la derivazione lì funziona.
Tre hanno `processo_registrato = false` e non si toglieranno mai. Le ultime due sono del
backend e le chiude il piano BE.

⚠️ **La conseguenza è su DB-5**, ed è per questo che lo segnalo qui invece di lasciarlo
scoprire: finché quei nomi non combaciano, `vw_run_senza_attore` **non può arrivare a
zero**, quindi `job_run_log.processo_codice` non può diventare obbligatorio, quindi la
stretta finale del cantiere resta aperta per un disallineamento di quattro stringhe.

🔵 **Non so quale dei due lati sia quello giusto**, e non è una mia decisione: `…_lock_columns`
e `…_delete_block` potrebbero essere **passi** di un job e non job — nel qual caso la
domanda non è «aggiungere due righe» ma «il registro cataloga job o unità di lavoro?». Ve
la giro così com'è.

**Come si vede che è chiuso.** Ogni jobname che compare in `maintenance.job_run_log` con
origine `PGAGENT` ha una riga in `dbops.processi`, e `vw_run_senza_attore` può svuotarsi
dopo un giro notturno.

---

## DB-8 — Un codice per «questo processo non esiste»

**Che cosa serve.** Un codice errore di classe `NON_TROVATO` per il caso *«il codice
processo indicato non è nel registro»* — es. `E_PROCESSO_NON_TROVATO`.

**Perché.** La schermata dei processi automatici ha un dettaglio per codice
(`GET /amm-software/processi/<codice>/`). Un codice inesistente è un 404, e a catalogo
quel codice non c'è.

⛔ **Non si riusa `E_JOB_NON_TROVATO`**, che è la tentazione ovvia: quello dice «il
LAVORO in coda 42 non esiste». Un processo e un lavoro sono due cose diverse, e un
messaggio che parla del secondo manda a cercare nel posto sbagliato. *Un codice usato per
due cose si spezza a monte, non si rimappa a valle.*

⚠️ **Non blocca**: nel frattempo l'endpoint risponde **400** con la frase esatta («Il
processo indicato non esiste nel registro»), dichiarato in un commento nel service. È il
denominatore sicuro — a quell'indirizzo ci si arriva solo digitandolo a mano — e il
giorno in cui il codice esiste qui si cambia una riga.

**Come si vede che è chiuso.** `E_PROCESSO_NON_TROVATO` è a catalogo con classe
`NON_TROVATO`, e il service smette di ripiegare sul 400.

---

## 2. Che cosa il backend NON chiede

* **niente sul canale di sistema**: il ritiro del ruolo `zeroerp_batch_fatturazione` è
  provisioning e backend, e lo fa il BE (R-2). Il presidio che lo verifica ce l'avete già
  acceso;
* **niente sulle sei viste di presidio** oltre a DB-2: sono leggibili da `zeroerp_app`, e
  il frontend le mostra così come sono;
* **nessuna azione di processo nuova** per il verbo «crea utente tecnico»: la schermata
  vive in `amm-software`, che è già super-admin-only — un secondo cancello sopra il primo
  sarebbe una seconda sede della stessa decisione;
* **nessuna modifica a `fn_crea_utente_tecnico`**: la firma va bene così, e il fatto che
  l'emittente sia obbligatorio è il punto, non un attrito.

---

## 3. Riferimenti

* [brief-db-processi-automatici-identita-e-perimetro.md](brief-db-processi-automatici-identita-e-perimetro.md)
  — il cantiere DB chiuso, e il **registro dei residui** (§12) da cui nascono DB-3 e DB-4
* [analisi-db-be-processi-automatici-identita-e-perimetro.md](analisi-db-be-processi-automatici-identita-e-perimetro.md)
  — le decisioni: §8.2 (la chiusura scadenze migra), §13.1 (Caso A e Caso B)
* [piano-be-fe-processi-automatici-identita-e-perimetro.md](piano-be-fe-processi-automatici-identita-e-perimetro.md)
  — che cosa fa il backend, e in quale ordine: §6 elenca queste cinque richieste dal lato
  di chi le aspetta
