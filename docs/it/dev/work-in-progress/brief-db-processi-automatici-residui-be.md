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
> **Stato:** 🟢 **IN CORSO — 5 su 8 APPLICATE, DB-5 scritta, DB-2/DB-3 in
> lavorazione.** Lo stato per riga è nel **§1-quinquies**.
> ✅ **Le tre domande aperte sono chiuse**: le decisioni e il perché stanno nel
> **§1-quater**.
>
> La risposta del team DB è nel **§1-bis** (e corregge l'ordine del §1); la
> **risposta del backend, misurata dopo quel push**, è nel **§1-ter**.
>
> 🔴 **Una cosa da sapere subito:** `apply_storicizza_weekly` fallisce da sei
> mesi, e non c'entra con questo cantiere — ma è **la sola cosa che separa
> `vw_run_senza_attore` dallo zero**, cioè dal vostro criterio per DB-5.
> Dettagli nel §1-quinquies.
> 🔴 **DB-6, DB-7 e DB-8 non erano nella versione che il team DB ha letto** — sono
> arrivate con la PR #1507, dopo la loro risposta: §1-ter, ultimo punto.
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

### ✅ DB-6 — FATTA E APPLICATA (2026-09-05)

> Il residuo che non era nel vostro elenco. `vendite.fatture_stampa_coda` aveva
> la policy ma non il write-guard: changeSet `20260905-07`.
>
> ⭐ **`dbops.vw_processi_dominio_senza_difesa` è VUOTA.** È il primo presidio di
> questo cantiere ad arrivare davvero a zero.

**Perché serviva anche con la policy in piedi.** Sull'`INSERT` il `WITH CHECK`
si valuta **dopo** i trigger `BEFORE ROW`. Misurato prima di applicare:

```
senza guard →  42501 | «la nuova riga viola la regola di sicurezza per riga»
con guard   →  P0001 | «Utente N non autorizzato per emittente M su vendite.fatture_stampa_coda»
```

⇒ La riga si fermava già; quello che mancava era **poter dire perché**.

⚠️ **Un assunto che ora è presidiato.** La tabella porta `sorgente_tipo_id` e
`sorgente_uid`, cioè la forma delle sorgenti **polimorfe** — dove il portante
può essere l'`uid` e puntare `sorgente_id` a una tabella sola sarebbe sbagliato.
Qui è lecito **solo** perché una FK dura fissa `sorgente_id` a `vendite.fatture`.
⛔ Se quella FK cadesse, guard **e** policy assumerebbero entrambi una cosa
falsa, e nessuno dei due se ne accorgerebbe: il test 3 di
`db/pgtap/rls/test-rls-fatture-stampa-coda-write-guard.sql` la tiene ferma.

**Verifica:** quel file — **6/6**, ed era **3 rossi su 6** prima della migrazione.

---

### ⭐ R-D. C'è un sesto residuo, e non era nell'elenco — ✅ risolta

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
| **DB-6** | ✅ **FATTA** il 2026-09-05 | changeSet `20260905-07`, pgTAP 6/6 — il presidio livello 2 è a ZERO |

---

## 1-ter. Risposta del BE (2026-09-05) — misurata dopo il vostro push

> ⚠️ Tutto ciò che segue è **letto dal database dopo il merge `6fd2266ed`**, non
> dedotto dal testo. Dove c'è un numero, viene da una query.

### Che cosa si è sbloccato per il backend: **niente** — ed è corretto così

DB-4 era il prerequisito di **DB-1**, non di un lotto BE: ha fatto un passo nella
vostra catena, non nella nostra. Il **lotto 4** resta fermo dov'era.

| Misurato | Valore |
| --- | --- |
| `dbops.coda_lavori_tipi` | due tipi: `FATTURAZIONE_GIRO`, `FATTURAZIONE_NUMERA` — nessuna casa per la chiusura scadenze |
| `chiusura_scadenze_daily` | ancora `DOMINIO / PGAGENT` |
| `vw_processi_dominio_senza_difesa` | **una riga**: `draina_coda_stampa · vendite.fatture_stampa_coda · write-guard` |
| `vw_processi_dominio_senza_emittente` | **una riga**: `send_pending_emails · config.email_outbox` |
| `config.codici_errore` | nessun `E_PROCESSO_NON_TROVATO` — il ripiego dichiarato di DB-8 resta in piedi |
| `vendite.listini` / `listini_versioni` | RLS accesa, **1 policy** ciascuna, write-guard presente — stessa forma di `vendite.contratti` |

### ✅ La metà BE di DB-5 è chiusa, e adesso si vede dalla vista

`dbops.vw_run_senza_attore` è passata da **sette righe a quattro**, e le due del
backend — `run_fatturazione_batch:immediata` e `:differita` — **non ci sono più**.
Restano:

| jobname | `processo_registrato` | |
| --- | --- | --- |
| `apply_fk_index_policy` | `false` | DB-7 |
| `automations_cleanup` | `false` | DB-7 |
| `automations_lock_columns` | `false` | DB-7 |
| `apply_storicizza_weekly` | `true` | si toglie da sé — ⚠️ ma l'ultima corsa è del **2026-02-21** |

⇒ **Nessuna delle quattro è del backend.** La parte che vi avevo promesso di
segnalare («vi scrivo io quando la vista è vuota») è fatta per la nostra metà.

### 🔵 R-B, prima domanda — la risposta è: **il suffisso non va strappato**

`registered_job` ha `processo_codice` **keyword-only e senza default**: un comando
che non lo dichiara non parte. Tutti e sei i comandi headless lo passano esplicito,
e le due cose sono separate **per costruzione**:

* `run_fatturazione_batch:immediata` è il **jobname** — porta la corsia, che è la
  chiave dell'anti-overlap: due corsie devono poter girare insieme;
* `run_fatturazione_batch` è il **processo** — la corsia non c'entra niente.

⇒ ⛔ **Non derivate il codice dal jobname per i comandi del backend, e non
insegnate alla derivazione a strappare un suffisso**: la derivazione è il ripiego
per chi non sa dichiararsi, e chi si dichiara ha già dato la risposta giusta.
Strappare il suffisso farebbe *sembrare* dichiarato anche chi non lo è.
⇒ **Un `NOT NULL` su `job_run_log.processo_codice` non pianta nessun comando
Django.** Quello che resta fra voi e il vincolo è DB-7, che è tutto di là.

### 🔵 R-B, seconda domanda — `automations_lock_columns` non è del backend

Cercati i quattro nomi in tutto `backend/`: **nessuna occorrenza**, in nessun file
Python. Non sono nominati né dai comandi né dai service: vivono in pgAgent e nei
wrapper `maintenance.proc_*_job`. ⇒ La domanda *«di quale processo sono, o sono
passi e non job»* resta vostra, e il BE non ha un'opinione da opporre.

### ⚠️ R-E — la decisione è di Tid, ma il BE non è indifferente

Fra le due strade, quella che al backend **non costa niente di nuovo** è la **A**
(il processo resta `COMMAND` e produce, un secondo processo `CODA` esegue): è
esattamente la forma di `run_fatturazione_batch`, che è già scritta, provata e in
piedi da ieri — produttore che legge il roster, un lavoro per azienda, l'identità
tecnica nello scope.

⛔ **Non è un argomento per scegliere A**: che una strada sia già lastricata non
dice che sia quella giusta. La **B** cambia il *modello* dei presidi — «un processo
di coda accodato da una macchina vuole comunque l'identità» — e se il modello è
quello, va cambiato il modello, non aggirato con un secondo processo.
⇒ Lo mettiamo davanti a Tid così: **A costa poco e lascia il modello com'è; B costa
di più e dice la verità su chi accoda.**

### ✅ R-F verificata contro il codice del backend: **non lo tocca**

La regola *«padre e figlia non nella stessa istruzione»* è stata cercata nel
backend, non data per buona:

* **nessuna CTE di scrittura** su `vendite.listini*` in `listini_repository.py`;
* `create_listino` e `create_versione` sono **due metodi**, quindi due istruzioni:
  il padre è già committato nello snapshot quando la figlia viene scritta;
* nessun cambio di attore fra la scrittura e il commit ⇒ il caso dei **vincoli
  differiti** non si presenta.

⇒ Niente da correggere lato BE. ⭐ La regola però **vale in avanti**: è annotata
fra le trappole del piano, perché il giorno in cui qualcuno scriverà padre e figlia
in una `WITH` il messaggio parlerà di sicurezza per riga e sembrerà un problema di
permessi.

### 🔴 Tre richieste non erano nella versione che avete letto

La vostra risposta parla di **cinque richieste**, ed è esatto per il commit su cui
avete lavorato: `a4fe59b4f^` conteneva DB-1…DB-5. **DB-6, DB-7 e DB-8 — e la
riscrittura di DB-4 — sono arrivate con la PR #1507**, mergiata *dopo* la vostra.
Sono nel documento che state leggendo adesso, e nessuna è persa:

| | |
| --- | --- |
| **DB-7** | ⭐ l'avete trovata da soli, ed è il vostro **R-B**: stessa cosa, due nomi |
| **DB-6** (fabbrica dell'utente tecnico) | **mai vista** — è il `23505` sullo username deterministico |
| **DB-8** (codice errore) | **mai vista** — non blocca, c'è un ripiego dichiarato |

⛔ **E c'è una collisione di numeri da sciogliere prima che costi un'ora**: il
vostro §1-bis registra il write-guard su `fatture_stampa_coda` come «**DB-6**»
(R-D), mentre in questo brief **DB-6 è un'altra cosa** — la fabbrica dell'utente
tecnico. Nel vostro registro dei residui quella riga è **R-10**, che è un nome
libero e non ambiguo.
⇒ Proposta: **si usa R-10**, e «DB-6» resta la fabbrica. Il numero lo scegliete
voi; l'importante è che due cose diverse non si chiamino allo stesso modo, perché è
così che una delle due sparisce.

⚠️ E la vostra tabella **«L'ordine reale» si ferma a DB-6**: DB-7 e DB-8 non ci
sono. DB-7 è la sola cosa che separa DB-5 dall'essere fattibile.

---

## 1-quater. Decisioni prese (2026-09-05, Tid) — e cosa cambia per voi

> ⭐ Le tre domande aperte sono chiuse. Qui c'è **cosa si è deciso e perché**;
> il come lo trovate nei changeSet.

### ⚠️ Prima: una vostra misura è superata di un'ora

`dbops.vw_processi_dominio_senza_difesa` per voi ha **una riga**
(`fatture_stampa_coda`). Avete misurato dopo il merge `6fd2266ed`, cioè **prima**
del changeSet `20260905-07`. ⇒ Adesso è **VUOTA**. È il primo presidio del
cantiere ad arrivare a zero.

✅ **Numerazione**: accettata la vostra proposta. Il write-guard su
`fatture_stampa_coda` si chiama **R-10**, e **DB-6 resta la fabbrica**.

---

### ✅ R-E → **strada B**: si corregge il modello, non si spacca il processo

Resta **una voce sola** nel registro per la chiusura scadenze, e si cambia la
regola dei presidi:

> Un processo di coda **accodato da una macchina** vuole comunque un'identità
> tecnica.

⛔ La strada A (produttore `COMMAND` + esecutore `CODA`) è stata scartata pur
essendo già lastricata, e la ragione è quella che avete scritto voi: *«che una
strada sia già lastricata non dice che sia quella giusta»*.

⭐ **Il motivo di fondo**: il presidio che assume «coda ⇒ c'è una persona» è
nostro, ed è **lui** a sbagliare. Spaccare un lavoro in due per far quadrare un
controllo scritto da noi significa piegare la realtà allo strumento — e fra sei
mesi qualcuno chiederebbe perché la chiusura scadenze è a catalogo due volte.

⇒ **Per il backend non cambia niente rispetto ad A**: l'utente tecnico serve
comunque, e lo scope si riempie allo stesso modo. Cambia che il registro dice la
verità su chi accoda.

---

### ✅ R-B seconda domanda → `lock_columns` e `delete_block` sono una DIMENTICANZA

Misurato: **non sono abbandonate.** Girano a ogni migrazione, dentro
`ci_apply`, insieme alle altre cinque automazioni — e hanno **31** e **8**
configurazioni attive.

⛔ Quello che manca è il **giro notturno**:

| automazione | alla migrazione | di notte |
| --- | --- | --- |
| audit, storico, tx_id, attivo, … | ✅ | ✅ |
| `lock_columns`, `delete_block` | ✅ | ⛔ **no** |

⇒ Una tabella creata **fra due migrazioni** riceve le altre cinque protezioni la
notte stessa, e queste due solo alla migrazione dopo: nel frattempo quelle
colonne non hanno lucchetto e quelle righe si possono cancellare.

**Decisione: si creano i due job notturni mancanti**, e i due processi si
registrano come gli altri.

⚠️ **E c'è un motivo pratico oltre a quello di merito**: se li avessimo
*ritirati*, `dbops.vw_run_senza_attore` non sarebbe arrivata a zero lo stesso.
`automations_lock_columns` ha **tre corse storiche** senza attore, l'ultima del
4 giugno; la vista guarda l'ultima corsa di ogni job, e un job ritirato **non
gira più**, quindi non si dichiara mai e non sparisce mai. Sarebbe stato di
nuovo un presidio incapace di arrivare a zero. Registrandoli, la riga si toglie
da sé alla prima corsa notturna.

---

### ✅ DB-7 → si **allineano i nomi**, e si aggiunge il presidio che mancava

⛔ **Non** si passa il codice esplicito ai 13 wrapper, che era la nostra prima
proposta. Misurato il costo reale, la proposta era sbagliata:

| | |
| --- | --- |
| rinominare i 2 codici | ⭐ **solo il CSV** — nessuno li referenzia, né `job_run_log` né i tipi di coda |
| codice esplicito | **13 wrapper** da riscrivere |

⚠️ **E l'argomento a favore del codice esplicito non morde qui.** È vero che
jobname e codice del processo sono due fatti diversi — lo prova il vostro
`run_fatturazione_batch:immediata`, dove il jobname porta la **corsia**. Ma i
jobname dei wrapper di manutenzione **non portano nessuna corsia**: lì i due
fatti coincidono. Applicare quell'argomento a questo caso era simmetria col
backend, non un ragionamento sul modello.

⭐ **E soprattutto: entrambe le strade lasciano lo stesso buco.** Col codice
esplicito, un wrapper nuovo che si dimentica di dichiararsi ricade sulla
derivazione — e se il nome non combacia resta senza attore, esattamente come
adesso. ⇒ Il presidio serve comunque; e se la garanzia è la stessa, vince la
strada che costa una riga di CSV.

**Cosa si fa:**

| # | |
| --- | --- |
| 1 | `automations_cleanup_weekly` → **`automations_cleanup`** — *weekly* è schedulazione, non il nome di un processo |
| 2 | `automations_apply_fk_indexes_policy` → **`apply_fk_index_policy`** — pura deriva di nome |
| 3 | due righe nuove: `automations_lock_columns`, `automations_delete_block` |
| 4 | ⭐ **il presidio**: ogni `jobname` che un wrapper `maintenance.proc_*_job` passa a `fn_run_and_log` **esiste** in `dbops.processi` |

⭐ Il presidio si legge dal **codice vivo** delle funzioni, e il suo perimetro non
è un elenco scritto a mano: è `proname LIKE 'proc_%_job'`. Un wrapper nuovo ci
finisce dentro da solo. **È il presidio che oggi manca**, ed è la ragione per cui
questo difetto è arrivato fino a voi.

---

### ✅ R-B prima domanda → **il suffisso non si strappa**, come dite voi

Accettato senza riserve, e la ragione che date è quella giusta: *«la derivazione
è il ripiego per chi non sa dichiararsi, e chi si dichiara ha già dato la
risposta giusta»*. Strappare il suffisso farebbe **sembrare** dichiarato chi non
lo è.

---

### ✅ DB-6 → confermato PROVANDOLO, ed è un difetto nostro

Non creduto sulla parola: riprodotto in transazione.

```
legame disattivato  →  fn_crea_utente_tecnico(...)  →  23505 auth_user_username_key
```

⇒ Avete ragione su tutto: lo username è `processo@emittente`, il `UNIQUE` è
incondizionato, e disattivare il legame libera il nostro guard 4 lasciando in
piedi il muro. **La via che il nostro §12.7 documenta non è percorribile.**

⛔ **Non la ripareremo riusando l'utente in silenzio.** Riattivare un utente che
qualcuno aveva ritirato *per un motivo* è peggio di un `23505`. ⇒ Un errore con
un codice registrato che dice *«esiste già un utente per questa coppia: riattiva
il legame invece di rifarlo»*, e il verbo «riattiva il legame» reso possibile.

⚠️ **Una cosa che sospettavamo e abbiamo verificato essere falsa**: i quattro
utenti senza emittente rimasti dal vecchio modello (`chiusura_scadenze_daily`,
`draina_coda_stampa`, …) **non** sono un residuo scoperto — hanno identità
inattiva e nessun perimetro, e il presidio ha ragione a non nominarli.

---

### ✅ DB-8 → accettato

`E_PROCESSO_NON_TROVATO`, classe `NON_TROVATO`. La vostra ragione per non
riusare `E_JOB_NON_TROVATO` è corretta e la sottoscriviamo: *un codice usato per
due cose si spezza a monte, non si rimappa a valle.*

---

### ⚠️ Un debito che la decisione sui job notturni CREA, e va detto subito

I due job pgAgent nuovi vivono in `85_pgagent`, e quella fase in CI è
**`MARK_RAN`**: viene segnata come eseguita **senza essere eseguita**.

⇒ I due job nasceranno su dbdev, ma su un ambiente ricostruito da zero **non
esisterebbero**, e nessun test lo direbbe. Non è un motivo per non farli: è un
motivo per non scoprirlo fra sei mesi. Registrato fra i residui.

---

## 1-quinquies. Stato dei lavori DB (2026-09-05, fine giornata)

| # | Stato | changeSet |
| --- | --- | --- |
| **DB-4** | ✅ applicata — RLS + write-guard sulla famiglia listino | `20260905-02`…`-06` |
| **R-10** (era «DB-6» nel nostro §1-bis) | ✅ applicata — write-guard su `fatture_stampa_coda`. ⭐ `vw_processi_dominio_senza_difesa` è **VUOTA** | `20260905-07` |
| **R-E** | ✅ applicata — **strada B**: il canale `CODA_AUTOMATICA`, e i tre presidi che assumevano «coda ⇒ persona» | `20260905-09`…`-12` |
| **DB-7** | ✅ applicata — 2 rinomine, 2 righe nuove, **i due job notturni mancanti**, e il presidio che chiude il buco per sempre | CSV + `20260905-08` |
| **DB-6** + **DB-8** | ✅ applicate — i due rifiuti parlano, e `fn_riattiva_utente_tecnico` è il verbo che mancava | `20260905-13`…`-15` |
| **DB-5** | ✅ applicata — `CHECK … NOT VALID` sull'attore dei run | `20260905-16` |
| **DB-2** + **DB-3** | ✅ applicate — il debito si **dichiara**, e l'email sa di chi è | `20260905-17`…`-20` |
| **DB-1** | ✅ applicata e collaudata — pgAgent **sveglia e non lavora** | `20260905-21`…`-25` + CSV |

> ⭐ **Sviluppo DB chiuso** per questo cantiere. Baseline pgTAP su 581 file:
> **nessuna regressione** (19 rossi, tutti già noti). Tutti i guardrail verdi.

---

### ✅ DB-1 — risposta alla vostra domanda aperta: **pgAgent, ma sveglia e non lavora**

Nel §DB-1 chiedevate chi accoda: *«il job pgAgent di stasera, che smetterebbe di
eseguire e comincerebbe a produrre, oppure un comando Django su cron?»*

⭐ **Il job pgAgent**, e la decisione è più larga della domanda. La regola presa
il 2026-09-05 è:

> ⛔ **Nessun processo di classe `DOMINIO` su pgAgent.**

⚠️ Non «gli applicativi via da pgAgent», che è vago: è il **perimetro emittente**
a fare la differenza, e la classe già lo dice. `sync_auth_user_expired_daily`
resta dov'è — è applicativo in senso lato, ma non ha un emittente.

⇒ Su un processo di dominio **pgAgent sveglia e non lavora**: il job chiama
`fn_accoda_lavoro` e basta. Se muore non ha toccato nessun documento, e il
lavoro vero resta tracciato nella coda.

⛔ **Perché non cron/systemd**: avrebbe lo stesso problema di visibilità di
`85_pgagent` — configurazione fuori dal repo, invisibile ai test — solo spostato.

**L'argomento è sperimentale, ed è il vostro stesso R-12 al contrario:**
`apply_storicizza_weekly` è morto per sei mesi perché pgAgent non racconta i
propri fallimenti. Un lavoro di coda che fallisce lascia `ultimo_errore` e
`tentativi` in una tabella che voi mostrate.

⚠️ **Ma abbiamo cambiato l'ordine**, e vale la pena dirlo: il silenzio si
**trasferisce** se il worker è giù. Misurato: la coda aveva **4 lavori in
`ERRORE`** e **nessuna vista** che li nominasse. ⇒ `dbops.vw_coda_lavori_da_guardare`
viene **prima** della migrazione — falliti, presi e mai chiusi (worker morto),
mai presi (⛔ worker spento). Senza, staremmo comprando una visibilità non
ancora costruita.

---

#### ✅ Fatto — e che cosa trovate adesso nel database

| Oggetto | A che cosa vi serve |
| --- | --- |
| `dbops.vw_coda_lavori_da_guardare` | ⭐ **il presidio da mettere a video**: falliti, presi e mai chiusi, **mai presi** (worker spento). Porta `motivo` e `da_quanto` già pronti |
| `dbops.vw_processi_dominio_su_pgagent` | la regola, verificabile. Oggi **0 righe** |
| `dbops.vw_processi_roster` | ⚠️ **è la vostra query**: `processi_repository.roster_processo` può diventare un `SELECT … WHERE processo_codice = %s`. Finché restano due copie, sono due copie |
| `dbops.fn_accoda_chiusura_scadenze()` | il produttore. La chiama il job notturno; a voi non serve chiamarla |

**Che cosa cambia a runtime, e va detto chiaro:** dalla notte in cui questo è
attivo, la chiusura scadenze **non avviene più dentro il job**. Avviene nel
drenatore, minuti dopo. ⇒ **Se `draina_coda_lavori` non gira, le scadenze non
si chiudono** — ed è esattamente il caso che `vw_coda_lavori_da_guardare` è
stata scritta per nominare (riga `PENDING` da oltre un'ora, motivo *«mai preso:
il worker non sta girando»*).

⚠️ **Il lavoro arriva con `run_as = OPERATORE`** e lo scope pieno: `auth_user_id`,
`username`, `identita_id` e l'**emittente congelato** all'accodamento. Il vostro
handler non deve risolverlo: deve **usarlo**.

⚠️ **R-11 vale anche qui**: `85_pgagent` è `MARK_RAN` in CI. Su un ambiente
ricostruito da zero il job resterebbe alla forma vecchia — **eseguirebbe invece
di accodare** — e nessun test lo direbbe.

---

### 🔴 DB-3, seconda metà — la policy è decisa ma **non la scriviamo**, e vi riguarda

**Decisione di Tid (2026-09-05):** le email di ambito `SISTEMA` le legge **solo
il super admin**. Non appartengono a nessuna azienda e il loro contenuto vale
quanto una credenziale. Le altre seguono la whitelist emittente, come tutta la
famiglia.

⛔ **Ma la policy non è stata scritta, e il motivo è vostro.**

`send_pending_emails` è un **management command**: le GUC `app.current_user_id`
e `app.ruolo_applicativo` le imposta l'autenticazione JWT, quindi lì **non ci
sono**. E `zeroerp_app` non ha `BYPASSRLS` (ce l'hanno solo `postgres` e
`zeroerp_batch_fatturazione`, in ritiro).

> ⇒ Abilitando la RLS oggi, **chi spedisce vedrebbe zero righe**. E non se ne
> accorgerebbe nessuno: una coda vuota è indistinguibile da «niente da fare».
> Il command girerebbe verde, il giornale direbbe «0 processate», e le email di
> **reset password non partirebbero più**.
>
> ⭐ È la forma esatta di R-12 — un guasto che si manifesta come **assenza** —
> introdotto da noi, dentro il cantiere che esiste per toglierla.

⚠️ Il commento nel vostro command lo diceva già: *«questo processo è di DOMINIO
e non ha un perimetro … gli si dà l'ATTORE e basta»*. Con DB-3 la colonna adesso
c'è. **Chi la usa, no.**

#### Che cosa serve da voi

| | |
| --- | --- |
| 1 | `send_pending_emails` **dice chi è anche al database**: `app.current_user_id` + `app.ruolo_applicativo` con l'identità tecnica del processo — che **esiste già**, la trovate in `dbops.vw_processi_roster` (`send_pending_emails@<azienda>`) |
| 2 | ⚠️ **Per le email `SISTEMA` serve una decisione**, non un'implementazione: o l'identità tecnica porta il profilo super admin, o la policy nomina esplicitamente il processo. Chi spedisce un reset password lo può **leggere** — è una scelta di sicurezza, ditecela |

⭐ Quando i due punti ci sono, la policy è **già scritta e pronta**: la trovate in
`brief-db-processi-automatici-identita-e-perimetro` §12.15.

#### ⛔ E la scorciatoia che non abbiamo preso, perché vi riguarda leggere il perché

Si poteva scrivere la policy **senza abilitare la RLS**: il presidio sarebbe
andato a zero e l'invio avrebbe continuato a funzionare. ⛔ Ma PostgreSQL
**conserva** le policy di una tabella con la row level security disabilitata e
**non le applica**: la tabella sarebbe rimasta aperta a tutti, col presidio che
diceva di no.

⇒ Abbiamo invece **irrigidito il presidio** (`20260905-26`): una policy conta
solo se la RLS è **attiva**. ⭐ Misurato: nessun bersaglio era in quello stato,
quindi non cambia una riga. Non nasce da un dato — nasce dal fatto che la
domanda posta era la domanda sbagliata.

---

### ⚠️ DB-5: il vincolo c'è, ma il VOSTRO criterio non è ancora soddisfatto

Il vincolo è scritto, ed è **un `CHECK … NOT VALID`, non un `SET NOT NULL`**.
Il motivo è un numero misurato: `maintenance.job_run_log` ha **99.775 righe
senza attore** su 100.738 — il giornale di ieri, scritto prima che la colonna
esistesse.

> ⛔ Riempirle «per far passare il vincolo» sarebbe **inventare un attore per
> corse che non l'avevano**.

⇒ Il `CHECK` vale su ciò che si scrive **da adesso**, e lascia la storia dov'è.
✅ Verificato che i due scrittori veri continuano a funzionare: `fn_run_and_log`
(derivazione) e `fn_job_run_start` (codice esplicito, come lo passate voi).

⛔ **Ma `dbops.vw_run_senza_attore` non si svuoterà a breve, e non è colpa del
cantiere.**

---

### 🔴 Il guasto che abbiamo trovato guardando la vostra vista

**`apply_storicizza_weekly` fallisce ogni settimana dal 21 febbraio 2026.**

Il job pgAgent è acceso e gira — verificato su `pgagent.pga_joblog`, ultima
corsa oggi — e muore sempre allo stesso punto:

```
ERRORE: la relazione "vendite.attivita_fatturabili_lotti" non esiste
```

⚠️ **Muore prima di scrivere**, quindi non lascia traccia: la sua ultima riga in
`job_run_log` è di febbraio. Un guasto che dura da sei mesi e che nessun log
racconta.

**La causa**: `config.storico_set_storicizza` ha **tre** righe che puntano a
tabelle sparite (`vendite.attivita_fatturabili_lotti`,
`config.profili_reparto_aree`, `config.profili_reparto_azioni`). Il job muore
sulla prima, quindi le altre due non si vedono nemmeno.

⭐ **Come è saltato fuori**: non da un allarme, ma chiedendosi **perché una riga
della vista non se ne andava**. La vista diceva «questo job non si è ancora
dichiarato»; la risposta vera era «questo job non gira da sei mesi».

⇒ Registrato come **R-12** nel nostro registro dei residui. È di un altro
cantiere e non lo progettiamo qui, ma lo diciamo subito perché è **la sola cosa
che separa la vostra vista dallo zero**.

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

> 🔴 **Riscritta due volte, e la prima riscrittura era sbagliata.** Diceva
> «`vendite.listini_versioni` la policy ce l'ha, R-8 per quel bersaglio è chiuso»,
> e diceva di averlo letto dal presidio. ⛔ **Non reggeva:** la misura del team DB
> (§1-bis, R-A) dice `RLS no · policy 0 · write-guard 0`, e i changeSet
> `20260905-04`/`-05` **accendono** la RLS su quelle due tabelle — cosa che non si
> fa dove è già accesa. La loro misura è quella giusta, e R-8 era aperto.
> ⭐ Il presidio si interroga invece di fidarsi di un elenco scritto — ma una
> lettura del presidio va **riportata per intero**, altrimenti diventa essa stessa
> l'elenco che invecchia.
> ⇒ **Quello che resta di questa richiesta è il bersaglio giusto**, ed è l'unica
> riga oggi viva nel livello 2: il write-guard su `vendite.fatture_stampa_coda`.
> Il team DB l'ha registrata come **R-10** nel proprio registro dei residui, e come
> «DB-6» nel §1-bis — ⚠️ vedere la collisione di numerazione nel §1-ter.

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
