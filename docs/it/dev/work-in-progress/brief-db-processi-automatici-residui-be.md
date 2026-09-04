# Brief DB — i cinque residui che il backend chiede per chiudere i processi automatici

> **Destinatario:** team DB (`dev/db-tid`).
>
> **Origine.** Il lavoro DB del cantiere «nessun processo senza operatore» è **chiuso e
> pushato** ([brief-db-processi-automatici-identita-e-perimetro.md](brief-db-processi-automatici-identita-e-perimetro.md),
> merge `e09a4c2cf`). Il backend lo sta ora consumando, secondo
> [piano-be-fe-processi-automatici-identita-e-perimetro.md](piano-be-fe-processi-automatici-identita-e-perimetro.md).
> Leggendo il contratto sono emerse **cinque cose che il BE non può darsi da solo**.
>
> **Stato:** 🔵 **RICHIESTA — niente scritto, niente applicato.**
>
> ⛔ **Questo brief dice che cosa serve e perché, non come farlo.** Forma, DDL, numerazione
> dei changeSet, seed e test sono decisioni di chi scrive: se il *cosa* qui sotto si
> ottiene meglio in un altro modo, il modo giusto è il vostro.
>
> ⚠️ **Nessuna delle cinque è urgente allo stesso modo.** Tre bloccano un lotto del piano
> BE, due sono debiti già vostri che il BE **eredita** e che vale la pena datare. La
> colonna «blocca» lo dice riga per riga.

---

## 0. In due parole

Il registro dei processi funziona: il backend adesso sa nominare i processi, il giornale
dei run ha l'attore, la coda rifiuta un lavoro di dominio senza operatore.

Restano cinque cose. Una serve a far **migrare la chiusura scadenze** sulla coda; una
serve perché un presidio **non nasca già rumoroso**; due sono i debiti che il vostro
brief ha fatto emergere (`email_outbox` e `listini*`) e che adesso hanno un consumatore
che ci sbatte contro; l'ultima è la **stretta finale** su una colonna, da fare quando il
BE avrà finito il suo pezzo.

---

## 1. Il quadro: chi aspetta chi

| # | Serve a | Blocca | Chi va per primo |
| --- | --- | --- | --- |
| **DB-1** | far diventare la chiusura scadenze un lavoro di coda | ⛔ sì, il lotto 4 del piano BE | **DB** |
| **DB-2** | rendere leggibile il presidio «dominio senza emittente» | ⚠️ non blocca, ma peggiora ogni giorno che passa | **DB** |
| **DB-3** | dare un perimetro a `send_pending_emails` | ⛔ sì, per la parte «un emittente alla volta» | **DB** |
| **DB-4** | far valere davvero il perimetro sui listini | ⚠️ non blocca il codice, blocca la **dichiarazione** che il lotto 4 è chiuso | **DB** |
| **DB-5** | rendere obbligatorio l'attore sui run | — | **BE**, poi DB |

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

## DB-4 — I listini hanno il percorso ma nessuno lo applica (R-8)

**Che cosa serve.** Che il perimetro emittente valga davvero su `vendite.listini*`.

**Perché.** Il percorso all'emittente **c'è** — `listini_versioni.listino_id →
listini.emittente_soggetto_ruolo_id`, che è `NOT NULL` — ed è la ragione per cui la
chiusura scadenze è stata dichiarata di dominio anche su quel bersaglio. Ma nessuna difesa
lo applica: né in lettura né in scrittura.

⇒ Quando la chiusura scadenze girerà per emittente (DB-1), sul bersaglio *contratti* il
perimetro sarà garantito dal database; sul bersaglio *listini* lo garantirà **soltanto la
query**. È la differenza fra il Caso A e il Caso B: lì un filtro dimenticato non si ferma
da solo.

⛔ **Non blocca il codice, blocca la dichiarazione.** Il lotto si può scrivere e girare;
quello che non si può fare è dire che il perimetro della chiusura scadenze è applicato,
perché su metà dei suoi bersagli non lo è. Preferisco scriverlo adesso che scoprirlo dopo.

⚠️ Anche questo è già registrato da voi come **R-8**.

**Come si vede che è chiuso.** `dbops.vw_processi_dominio_senza_difesa` non nomina più
`vendite.listini*`.

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
