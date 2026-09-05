# Brief DB — i cinque residui che il backend chiede per chiudere i processi automatici

> **Destinatario:** team DB (`dev/db-tid`).
>
> **Origine.** Il lavoro DB del cantiere «nessun processo senza operatore» è **chiuso e
> pushato** ([brief-db-processi-automatici-identita-e-perimetro.md](brief-db-processi-automatici-identita-e-perimetro.md),
> merge `e09a4c2cf`). Il backend lo sta ora consumando, secondo
> [piano-be-fe-processi-automatici-identita-e-perimetro.md](piano-be-fe-processi-automatici-identita-e-perimetro.md).
> Leggendo il contratto sono emerse **cinque cose che il BE non può darsi da solo**.
>
> **Stato:** 🟢 **IN CORSO — 1 su 6 fatta.** ✅ **DB-4 applicata il 2026-09-05**
> (era il prerequisito di DB-1). La risposta del team DB è nel **§1-bis**, e
> corregge l'ordine del §1.
> ⛔ Due punti vanno decisi insieme prima che uno dei due lati scriva (R-B e R-E).
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

⛔ **Questa tabella è stata corretta dal team DB il 2026-09-05** — l'ordine reale è nel
§1-bis qui sotto: **DB-4 non è parallela a DB-1, è il suo prerequisito**, e DB-5 non
dipende solo dal BE.

---

## 1-bis. Risposta del team DB (2026-09-05)

> **Le cinque richieste sono legittime e ben argomentate**, e tre premesse su cinque sono
> state verificate corrette. ⛔ Le altre non reggono alla misura, e ne manca una sesta.
>
> ⚠️ Tutto ciò che segue è **misurato sul database**, non dedotto dal testo: dove c'è un
> numero, viene da una query.

### ✅ Quello che il brief ha visto giusto

* **DB-1** — `chiusura_scadenze_daily` è davvero l'**unico** processo `DOMINIO` su
  pgAgent.
* **DB-2** — la contraddizione **esiste**, e le due frasi sono entrambe nel codice. ⭐ E il
  precedente citato è esatto: `vw_processi_che_bypassano` porta una colonna `stato` con
  `DEBITO_DICHIARATO` e la nota di chiusura. Applicarlo alle due viste sorelle è la strada
  giusta.
* **DB-3 / DB-4** — le premesse sono corrette: `config.email_outbox` non porta l'emittente,
  e `vendite.listini*` non ha **nessuna** difesa.

---

### ✅ DB-4 — FATTA E APPLICATA (2026-09-05)

> Era il prerequisito di DB-1, quindi è partita per prima. `vendite.listini` e
> `vendite.listini_versioni` hanno ora **policy RLS + write-guard**, come la
> famiglia dei documenti.
>
> ⭐ `dbops.vw_processi_dominio_senza_difesa` **non nomina più la famiglia
> listino**: da due righe è scesa a una, ed è DB-6.

| changeSet | Che cosa fa |
| --- | --- |
| `20260905-02` | `script.fn_scope_ef_whitelist_via_listino` — l'adapter per la figlia, che delega alla canonica invece di riscrivere la regola |
| `20260905-03` | il modo `listino` in `fn_resolve_emittente_fiscale_id` — serve al **guard di scrittura**, che è `SECURITY INVOKER` e non può leggere sotto la RLS appena accesa |
| `20260905-04` | policy + `ENABLE ROW LEVEL SECURITY` su `vendite.listini` |
| `20260905-05` | idem su `vendite.listini_versioni`, col perimetro preso **dal listino padre** |
| `20260905-06` | i due write-guard: la policy nasconde, il guard rifiuta **e spiega** |

**Verifica:** `db/pgtap/rls/test-rls-listini-ef-whitelist-write.sql` — **8/8**.

⚠️ **Da sapere applicandolo altrove:** su dbdev tutti i listini erano di un
emittente solo, quindi nessuno ha perso visibilità. Su un database con più
aziende popolate l'effetto è reale e voluto: chi prima vedeva tutti i listini
vedrà i propri.

---

### ⚠️ R-F. Una conseguenza di DB-4 che tocca il VOSTRO codice

> **Da leggere prima di toccare i listini.** Non era deducibile dal contratto, e
> l'abbiamo trovata solo perché ha rotto un test.

⛔ **Scrivere un listino e la sua prima versione nella STESSA istruzione non
funziona più.**

```sql
-- ⛔ Da oggi fallisce
WITH lst AS (
    INSERT INTO vendite.listini (...) RETURNING id
),
lst_v AS (
    INSERT INTO vendite.listini_versioni (listino_id, ...)
    SELECT id FROM lst RETURNING id
)
SELECT ...;
```

**Perché.** La policy di `listini_versioni` risolve il perimetro passando dal
listino padre, e legge `vendite.listini` con **lo snapshot dell'istruzione** —
che non contiene la riga appena scritta dalla CTE sorella. Padre invisibile →
perimetro `NULL` → *«la nuova riga viola la regola di sicurezza per riga»*.

⇒ **Due istruzioni separate.** Il padre prima, la figlia poi.

⚠️ **Non è un difetto della policy, e non si aggira**: è la regola generale
`RLS + CTE` del progetto, e vale per qualunque coppia padre-figlio su una
famiglia protetta — non solo per i listini.

⭐ E c'è un secondo caso, che abbiamo incontrato scrivendo il collaudo: i
**vincoli differiti** (`trgfn_child_requires_active_parent`) non scattano
all'`INSERT` ma alla verifica dei vincoli, e lì leggono **col contesto attivo in
quel momento**. Se il vostro codice cambia utente fra la scrittura e il commit,
il padre può diventare invisibile e il guard alza *«Padre non attivo»* su una
riga perfettamente attiva. ⇒ I vincoli differiti si chiudono **nei panni di chi
ha scritto**.

---

### 🔴 R-A. DB-4 non è parallela a DB-1: **è il suo prerequisito** — ✅ risolta

Il brief la classifica *«non blocca il codice, blocca la dichiarazione»*. È il contrario.

⭐ **Buona notizia prima**: `dbops.fn_apply_chiusura_scadenze` è **`SECURITY INVOKER`**.
Il perimetro non ha quindi bisogno di nessun parametro nuovo — se il lavoro gira con
l'utente tecnico dell'azienda X, **la RLS filtra da sola**. È già così su
`vendite.contratti`.

⛔ **Ma non su tutti i bersagli:**

| Bersaglio | RLS | policy | write-guard |
| --- | --- | --- | --- |
| `vendite.contratti` | ✅ | 1 | 1 |
| `vendite.listini_versioni` | ⛔ **no** | **0** | **0** |

⇒ Girando «per l'azienda X», la metà *contratti* verrebbe filtrata e la metà *listini*
**no**: il lavoro direbbe X e toccherebbe i listini di tutti. Non manca la dichiarazione —
**è il codice a non poter fare ciò che dice**.

⇒ **DB-4 va prima di DB-1.**

---

### 🔴 R-B. DB-5 non è sicura nemmeno dopo il lotto 1 del BE

Misurato su `maintenance.job_run_log`: **quattro jobname vivi non hanno un processo
omonimo**. La vista lo dice già da sé, con la colonna `processo_registrato`:

| jobname | run | perché la derivazione non aggancia |
| --- | --- | --- |
| `run_fatturazione_batch:immediata` · `:differita` | 4 · 25 | ⭐ il nome porta un **suffisso**: `codice = jobname` non combacerà mai |
| `apply_fk_index_policy` | 45 | il job pgAgent si chiama `automations_apply_fk_indexes_policy` |
| `automations_cleanup` | 35 | il job pgAgent si chiama `automations_cleanup_weekly` |
| `automations_lock_columns` | 3 | ⚠️ **non esiste** un job pgAgent con quel nome |

⇒ Con il `NOT NULL` quei run **falliscono l'INSERT, e il job si pianta**. Un'etichetta
mancante diventerebbe un'interruzione — e su `run_fatturazione_batch:immediata` è la
fatturazione on-demand.

⛔ **Due decisioni prima del vincolo**, e non sono del solo DB:

1. la derivazione **strappa il suffisso** `:variante`, oppure quei command passano il
   codice esplicito?
2. `automations_lock_columns` **di quale processo è**? Non ha nemmeno un job pgAgent —
   potrebbe essere un passo interno, o un residuo da ritirare.

---

### ⚠️ R-C. DB-3 non può essere una colonna obbligatoria

`config.email_outbox.ambito` è `NOT NULL`, e **tutte** le righe di oggi sono `SISTEMA`.
Un'email di sistema — reset password, alert — non ha un emittente e non può averlo.

⇒ Colonna **nullable** con un CHECK legato ad `ambito`, non un `NOT NULL`: *un `NOT NULL`
va dove il dato si può fornire.*

⚠️ **E il presidio va insegnato a non contare le righe `SISTEMA`**, o resta rosso per
sempre — che è **esattamente il difetto di DB-2, ripetuto sulla soluzione di DB-3**.
⇒ I due si progettano insieme, o il secondo ricrea il primo.

---

### ⭐ R-D. C'è un sesto residuo, e non era nell'elenco

`dbops.vw_processi_dominio_senza_difesa` nomina **due** righe, non una:

```text
chiusura_scadenze_daily | vendite.listini_versioni    | policy RLS e write-guard          <- DB-4
draina_coda_stampa      | vendite.fatture_stampa_coda | write-guard (scrittura scoperta)  <- nuovo
```

La seconda ha la stessa forma di DB-4 — e `draina_coda_stampa` è **uno dei processi a cui
il lotto 1 sta per dare un'identità tecnica**. Dargli l'identità senza la difesa produce
lo stesso mezzo-perimetro dei listini.

⇒ Lo registriamo come **DB-6**.

---

### ⭐ R-E. DB-1 nasconde una domanda di MODELLO, non solo «chi accoda»

Un processo ha **un** canale. Se `chiusura_scadenze_daily` diventa `CODA`:

* i presidi **escludono** i processi di coda dal bisogno di utente tecnico — l'assunto è
  *«chi accoda è una persona»*;
* ma qui chi accoda è una **macchina**, e `dbops.fn_accoda_lavoro` pretende
  `run_as = OPERATORE` **con scope**, cioè un `auth_user_id` da metterci dentro.

⇒ L'utente tecnico serve **comunque**, ma per riempire lo scope invece che per eseguire.
Il modello di oggi non prevede questo caso.

⛔ Quindi la domanda *«chi accoda»* **non è simmetrica**: non cambia «poco al DB e parecchio
al BE» — cambia il modello dei processi. Le due strade:

| | |
| --- | --- |
| **A** | il processo resta su `COMMAND` (produttore) e ne nasce un **secondo** su `CODA` (esecutore) |
| **B** | si allarga il presidio: un processo di coda **accodato da una macchina** vuole comunque l'identità |

⇒ È la prima cosa da decidere insieme, prima che uno dei due lati scriva.

---

### L'ordine reale

| # | Blocca | Quando |
| --- | --- | --- |
| **DB-2** | non blocca, ma è la più economica | ⭐ **prima**, e progettata **insieme a DB-3** |
| **DB-4** | ✅ **FATTA** il 2026-09-05 | changeSet `20260905-02`…`-06`, pgTAP 8/8 |
| **DB-1** | blocca il lotto 4 BE | dopo DB-4, e dopo la decisione R-E |
| **DB-3** | blocca «un emittente alla volta» | indipendente, con la forma di R-C |
| **DB-5** | — | ⛔ non basta il lotto 1: prima le due decisioni di R-B |
| **DB-6** | — | nuovo (R-D), stessa forma di DB-4 |

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
