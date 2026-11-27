# Brief DB — lo schema `storico` scrivibile dall'app

> **⏭️ Chi riparte — aggiornato al 2026-11-27**
>
> **Riparte: Tid, con R-1 … R-4 della revisione critica (§5.8), poi il via del giro 1 (§5.1).** Il brief l'ha aperto D-AL **a** (Tid,
> 2026-11-27) del giro 10-quater di [brief-db-porte-aperte-dalla-sola-guc](../work-done/2026/brief-db-porte-aperte-dalla-sola-guc.md) §15.4.
> L'analisi è partita lo stesso giorno: le cinque decisioni sul **perimetro e sul flag `storicizza`** sono prese
> (D-S-1 … D-S-5, §4.1), e sono un cambio di modello; poi D-S-6 … D-S-9 e il censimento (§6).
>
> | # | Chi | Che cosa | Dove | Aspetta |
> | --- | --- | --- | --- | --- |
> | 1 | Tid | ✅ il perimetro e le classi di storicizzazione (D-S-1 … D-S-5, 2026-11-27) | §4.1 | — |
> | 2 | Tid | ✅ chi scrive lo storico e la nota (D-S-6, D-S-9, 2026-11-27); ✅ `user_insert` = l'operatore, `ruolo_sessione` = la porta (D-S-7); ✅ si ritira `fn_grant_storico_shadows` (D-S-8) | §4.1, §4.2 | — |
> | 3 | team DB | ✅ il censimento delle tabelle storicizzate, letto sulla struttura (2026-11-27) | §6 | 1 |
> | 4 | Tid | ✅ D-S-10, D-S-11 **b**, D-S-12, D-S-13 e la rilettura delle classi (2026-11-27) | §6 | 3 |
> | 5 | team DB | ✅ il piano dei giri, con «Garanzie ritirate» e le richieste al BE/FE (2026-11-27) | §5 | 4 |
> | 5b | Tid | R-1 … R-4 della revisione critica (R-5 … R-9 si chiudono nei loro giri) | §5.8 | 5 |
> | 6 | Tid | il via del giro 1 | §5.1 | 5b |
> | 7 | team DB | giri 1-5, ciascuno col suo via | §5 | 6 |
>
> Decisioni aperte di Tid: R-1 … R-4 (§5.8), poi il via del giro 1, e al via le due conseguenze del §5.1: il valore di `storicizza` sulla
> riga non si legge più; il ripiego del trigger di audit passa da `CURRENT_USER` a `session_user` (D-S-7). Da
> committare: questo file e la riga del cantiere in `.codex/PROJECT_CONTEXT.md`.
>
> **Brief vicini verificati** (2026-11-27, ricerca su `storico`, `trgfn_storico_generic`, `fn_ensure_storico_table`,
> `storico_set_storicizza` in `work-in-progress/`):
> * `brief-db-porte-aperte-dalla-sola-guc`: chiude le tabelle dei permessi in sola lettura per l'app, non lo storico;
>   da lì nasce questo brief (D-AL **a**). Non basta: il tema è di tutto lo schema.
> * `brief-db-revisione-anagrafiche` (§18, giro 1): ha reso continuo lo storico di indirizzi, civici e vie, e lascia
>   un debito «per la revisione di quello schema»: le pagine `storico/manual/indirizzi.md`, `indirizzi_dettaglio.md`,
>   `stradario.md` sono nel formato vecchio e dicono cose non vere (il trigger solleva l'eccezione, non la logga).
>   Quel debito è di questo schema: si riprende qui quando il brief parte. Il brief è di un'altra sessione e non si tocca.
> * `valutazione-modello-di-dominio-db`: il tipo di `data_insert` delle shadow, già chiuso (`20260920-03`, `20260921-01`).
>   Non riguarda i privilegi.
> * `integrazione-ai-sviluppo-v2`: un campo `ai_initiated` nelle tabelle `storico.*`, sviluppo futuro. Non riguarda i
>   privilegi, ma tocca le stesse tabelle: si rilegge all'analisi.
> * Aggiunti al censimento (2026-11-27): `brief-db-utility-gestite-dall-emittente` (D-U-10: la matrice
>   `config.utilities_tipi_ruolo` è di seed, quindi N per D-S-12; nessun conflitto); `brief-db-revisione-anagrafiche`
>   (documenta i titoli IVA, il loro accumulatore e `trgfn_stiva_movimenti_guard_annullo`: lo storno di T-1, §5.2, si
>   costruisce qui ma si confronta con quelle righe al giro 2).
>
> **Guide verificate** (`scripts/guide_coinvolte.py --oggetti script.trgfn_storico_generic dbops.fn_ensure_storico_table
> config.storico_set_storicizza`, 2026-11-27). Esito preliminare, da confermare all'analisi:
> * `storicizzazione-tabelle`: dice che l'applicazione non cancella mai una versione, «è un privilegio, non una
>   convenzione» (manca il `DELETE`: **coerente**). Sull'`UPDATE` non dice niente: da rileggere.
> * nota di dominio `dbzero/storico/_tabelle-storico`: «append-only per destinazione d'uso. Le righe non si
>   aggiornano e non si cancellano». L'`UPDATE` concesso all'app rende l'archivio riscrivibile: la nota descrive l'uso,
>   il privilegio non lo garantisce. **Da decidere** se è la nota che va corretta o il privilegio.
> * `audit-e-tracciabilita`, `automazione-db`, `catasto-delle-istanze`, `generazione-cliente`: nominano il trigger o
>   il registro; si rileggono all'analisi.
>
> Riletture del 2026-11-27, con le decisioni D-S-1 … D-S-5:
> * `storicizzazione-tabelle` §«La colonna `storicizza`»: descrive come scelta la storicizzazione «one-shot» delle
>   tabelle non registrate e l'esclusione per singolo record. **Contraddetta**: è il cambio di modello di D-S-3 e
>   D-S-4, deciso da Tid; la guida si riscrive nel giro che lo costruisce.
> * `gestione-degli-indirizzi` (righe 495 e 776): la normalizzazione e gli import «passano `storicizza = false`».
>   **Contraddetta** da D-S-4: l'eccezione passa dal DB, non dall'UPDATE dell'app. Si riscrive nello stesso giro.
> * `architettura-permessi-e-autorizzazioni` §13.2: l'audit degli override legge lo storico; il «chi» lo prende dalla
>   riga, che scrive il backend. **Coerente** col limite del modello (§1).
> * nota `dbzero/storico/_tabelle-storico`: «le righe non si aggiornano» è falso già sull'uso, perché il trigger chiude
>   `valid_to` della versione aperta (§2). **Guida indietro**: la forma della correzione è D-S-9.

## 1. Il problema, sul modello

Lo storico è l'archivio delle versioni precedenti: vale come prova di chi ha cambiato cosa e quando, e l'audit dei
permessi lo legge (`architettura-permessi-e-autorizzazioni` §13.2). Un archivio che chi lo produce può riscrivere non
prova niente.

Oggi lo scrive il trigger generico `script.trgfn_storico_generic`, agganciato a ogni tabella madre. Il trigger è
`INVOKER`: scrive coi privilegi di chi modifica la tabella madre, cioè quasi sempre l'app. Per questo l'app ha
`INSERT` e `UPDATE` sulle tabelle di `storico`: senza, la modifica della tabella madre si fermerebbe. Con quei
privilegi, però, l'app può anche scrivere nello storico **direttamente**, senza il trigger: aggiungere una versione
che non c'è stata, o cambiarne una vera.

Il modello «una scrittura = un verbo» chiude le tabelle che danno poteri. Lo storico non dà poteri, ma è la traccia
su cui si controllano: è un caso diverso, e non si chiude con la regola dei giri delle porte.

⚠️ **Il limite, come nel resto del modello (Tid, 2026-11-27, D-S-1).** Lo storico si protegge da un backend che
**sbaglia**, non da uno **manomesso**. Il «chi» di una versione lo dichiara il backend (`user_update` della riga,
la GUC di sessione), e `user_insert = current_user` dice il ruolo DB, non la persona. Chiudere i privilegi serve a
far rifiutare dal DB la scrittura sbagliata (un ORM che scrive nello storico, un UPDATE su una versione vecchia, un
flag lasciato spento), non a fare dello storico una prova contro chi controlla l'app.

Il buco più grande non sono i privilegi sullo storico, ma il flag della madre: con `UPDATE … SET storicizza = false`
l'app modifica una riga senza lasciare versione, anche con lo storico chiuso. Per questo il brief tiene insieme i
due temi.

## 2. Fatti datati

* 2026-11-26 (catalogo di dbdev, analisi del giro 10-quater): l'app ha `INSERT` e `UPDATE` su **116 tabelle di
  `storico` su 116**, nessun `DELETE`. Fra queste lo storico di override, profili, legami e scope (otto tabelle
  dell'accesso).
* `script.trgfn_storico_generic` è `INVOKER`.

Struttura, letta il 2026-11-27 dalla doc auto-generata (corpo della funzione, commenti, changeSet dei grant):

* Il trigger è `BEFORE UPDATE OR DELETE`: all'INSERT non scrive niente. Alla prima modifica scrive due versioni,
  quella «iniziale» (lo stato di prima, `valid_from = 1950-01-01`) e quella nuova.
* Esce senza scrivere se `NEW.storicizza` (UPDATE) o `OLD.storicizza` (DELETE) è falso.
* Fa sempre un `UPDATE` sullo storico: chiude la versione aperta (`SET valid_to = … WHERE valid_to IS NULL`).
  L'`UPDATE` è quindi legittimo per costruzione.
* Sulle tabelle non registrate in `config.storico_set_storicizza` rimette il flag a `false` dopo ogni UPDATE (la
  storicizzazione «one-shot»). La sync settimanale registra le tabelle con DEFAULT `true`: oggi la classe di una
  tabella la decide il default della colonna (`true` continuo, `false` storico vuoto finché qualcuno non accende il
  flag; esempi di `false`: `vendite.fatture_righe`, `magazzino.movimenti`).
* `vendite.fatture` è continua anche in bozza di lotto: la pipeline la ricalcola, il reset la cancella, e ogni DELETE
  lascia una versione.
* I privilegi dell'app sullo storico hanno **due fonti**: il loop dei grant (`20260205-41`, schema `storico` fra
  quelli senza `DELETE`) e `dbops.fn_grant_storico_shadows` (90_end, runAlways), che concede `SELECT, INSERT, UPDATE`
  sulla shadow a **ogni** ruolo non superuser con `INSERT` o `UPDATE` sulla madre (oggi il solo `zeroerp_app`: i ruoli
  batch non esistono più dal 2026-10-15), e non revoca mai. Per questo i privilegi restano anche sulle shadow delle madri già chiuse in sola lettura.

## 3. L'analisi da fare

* Chi deve poter scrivere lo storico: solo il trigger? Anche altri (backfill, `fn_storico_backfill_scope`, la sync di
  `storico_set_storicizza`, i lavori notturni)?
* Con quale privilegio scrive il trigger, se l'app non ha più `INSERT`/`UPDATE`: una funzione DEFINER chiamata dal
  trigger, il trigger stesso DEFINER, o un'altra strada. Che cosa resta vero di `user_insert = CURRENT_USER` (la
  colonna che dice chi ha generato la versione) quando scrive il proprietario.
* ✅ Perché serve l'`UPDATE`: risolto dalla struttura (§2), il trigger chiude sempre la versione aperta. Fra le
  strade c'è anche l'`UPDATE (valid_to)` di colonna.
* Le tabelle che la madre ha già chiuse in sola lettura (giri 10-bis e 10-quater): i verbi DEFINER scrivono già come
  proprietario, quindi lì l'app non ha bisogno dei privilegi sullo storico. Le due fonti dei grant (§2) però li
  lasciano: la chiusura passa dal loop dei grant (§11.8 di linee-guida-sql) e da `fn_grant_storico_shadows`.
* La nota di dominio e la guida: che cosa promettono, e se lo promettono come privilegio o come uso.
* **Il censimento delle tabelle storicizzate** (D-S-1 … D-S-5), letto sulla struttura: per ognuna chi la scrive
  (persona da un verbo, processo, tutti e due), se la versione precedente si ricostruisce altrove, e la classe che ne
  segue (continua, nessuna, continua dall'emissione). Comprende le madri con DEFAULT `false` e quelle senza registro.
* I lettori lato DB che oggi scrivono lo storico o spengono il flag girando come app (backfill, sync, job, verbi
  INVOKER): la sezione «Garanzie ritirate» del piano.
* Il debito di `brief-db-revisione-anagrafiche` sulle tre pagine `manual/` delle shadow: è debito documentale, giro
  a sé.

## 4. Le decisioni

### 4.1 Decise da Tid il 2026-11-27

Cambio di modello: revoca la storicizzazione «one-shot» e l'esclusione per record scritte come scelta nella guida
`storicizzazione-tabelle` §«La colonna `storicizza`», e l'uso di `storicizza = false` dall'app descritto in
`gestione-degli-indirizzi`.

* **D-S-1 — Che cosa garantisce lo storico.** Protegge da un backend che sbaglia, non da uno manomesso, come il
  resto del modello (§1). Il criterio della classe è il **significato del dato**, non il volume: lo storico risponde
  a «com'era prima che qualcuno lo cambiasse», e vale solo se la versione precedente non si ricostruisce altrove.
  * **dato deciso** (anagrafiche, parametri, permessi, prezzi, documenti emessi) → storico **continuo**;
  * **dato calcolato o di lavoro** (righe di fattura in un lotto DRAFT, totali ricalcolati, righe che un reset
    cancella e rigenera) → **nessuno**: la sua storia è il lotto (stato, `tx_id`, log della pipeline);
  * **dato che è già un registro append-only** (`magazzino.movimenti`, `documenti_eventi`) → **nessuno**.
* **D-S-2 — «Nessuno storico» vuol dire nessuna colonna.** Una tabella senza storico non ha `storicizza`, quindi non
  ha shadow né trigger. Il DEFAULT `false` come classe si ritira.
* **D-S-3 — La storicizzazione «one-shot» si ritira.** Il trigger non spegne più il flag dopo un UPDATE: una
  tabella storicizzata lo è sempre.
* **D-S-4 — L'eccezione per un'operazione la concede solo il DB.** L'app (interfaccia **e** processi del backend: al
  DB sono lo stesso ruolo) non spegne mai il flag. Un'operazione che riscrive dati decisi senza lasciare storia
  (migrazione, import, normalizzazione massiva) la fanno il migratore o il proprietario, compresi i job notturni,
  con il trigger sospeso come già fanno `20260805-14` e `20261123-38`. Se un giorno servirà dall'interfaccia, sarà
  un verbo DEFINER che concede l'eccezione e registra chi l'ha chiesta. I processi di calcolo non hanno bisogno
  dell'eccezione: scrivono su tabelle senza storico (D-S-1, D-S-2) o su documenti non ancora emessi (D-S-5).
* **D-S-5 — I documenti generati dai lotti si storicizzano dall'emissione.** Una fattura in bozza di lotto è un
  dato di lavoro: la pipeline la crea e la ricalcola, il reset la cancella, senza versioni. Lo storico parte quando
  il documento è emesso, e la condizione la guarda il DB (lo stato del documento), non un flag scritto dall'app.
  Il censimento (§3) dice quali altri documenti nascono da un processo e seguono la stessa regola.

* **D-S-6 — Lo storico lo scrive solo il trigger, come proprietario (strada a).** La scrittura nella shadow
  (l'`INSERT` delle versioni e l'`UPDATE` che chiude `valid_to`) gira `SECURITY DEFINER` del proprietario, nel
  trigger o in una funzione che il trigger chiama (la forma la sceglie il piano dei giri). L'app perde `INSERT` e
  `UPDATE` su tutto lo schema `storico` e tiene il `SELECT`. Scartate: (b) `INSERT` più `UPDATE (valid_to)` di
  colonna, che lascia all'app inventare versioni; (c) la chiusura sulle sole madri già in sola lettura, che ricrea
  l'asimmetria scartata da D-AL.
* **D-S-9 — La nota `_tabelle-storico`.** Si corregge nel primo giro: «le versioni non si riscrivono; il trigger
  chiude solo `valid_to` della versione aperta», e con D-S-6 la garanzia è il privilegio, non l'uso.

* **D-S-7 — `user_insert` scrive l'operatore, `ruolo_sessione` la porta del database.** ⚠️ Rivista due volte il
  2026-11-27 su osservazione di Tid (la decisione finale è in fondo a questa voce). Prima correzione: la colonna non scrive
  «il ruolo DB» in astratto, scrive l'**utente corrente** (`current_user`), che di norma **coincide con l'utente di
  connessione**: Django si collega come `zeroerp_app`, chi migra col proprio nome. Le due cose si separano in due
  casi, dentro una funzione DEFINER (l'utente corrente diventa il proprietario) e con il `SET role` dell'utente
  personale (`provisioning-db-roles`, «Un utente personale che lavora come proprietario»). Fatto datato (dbdev,
  2026-11-27, sola lettura): in `storico.soggetti`, `storico.fatture` e `storico.user_override_oggetti` compaiono
  `zeroerp_app`, `titodb`, `postgres` e anche `zeroerp_owner`, cioè versioni in cui l'utente di connessione è già
  perso. Con D-S-6 l'utente corrente sarebbe **sempre** il proprietario, e la colonna non direbbe più niente.
  ⚠️ Prima decisione, superata: la colonna scrive `session_user`, l'utente di connessione, che non cambia né con
  una DEFINER né col `SET role`.

  Seconda osservazione (Tid): nella **madre** `user_insert` e `user_update` le scrive `trgfn_audit_data_user_generic`
  con l'**operatore dell'app** (la GUC `app.jwt_user`, con ripiego su `CURRENT_USER`); nella **shadow** `user_insert`
  la scrive il trigger dello storico con `current_user`, senza leggere la GUC. Fatto datato (dbdev, 2026-11-27):
  una versione di `storico.soggetti` porta `user_insert = zeroerp_app` e nello snapshot `user_update = tid`. Lo stesso
  nome dice due cose diverse.

  **Deciso (Tid, 2026-11-27, strada b):**
  * `user_insert` della shadow scrive l'**operatore**, con la stessa regola della madre: la GUC `app.jwt_user`, e
    senza GUC l'utente di connessione (`session_user`, non `current_user`: dentro il trigger DEFINER l'utente
    corrente è sempre il proprietario). Il valore è dichiarato dal backend (D-S-1), come nella madre;
  * una colonna nuova, **`ruolo_sessione`** (`session_user`, come `maintenance.job_run_log.ruolo_sessione`), dice la
    porta del database: `zeroerp_app`, il migratore, un utente PostgreSQL;
  * la regola «l'operatore, dalla GUC o dalla connessione» sta ora in due trigger, quindi si estrae in un building
    block di `script` (regola del 2) che il trigger di audit e il trigger dello storico chiamano entrambi. Il ripiego
    del trigger di audit passa da `CURRENT_USER` a `session_user`: dentro un verbo DEFINER senza GUC oggi scrive
    `zeroerp_owner`, dopo scrive l'utente di connessione. È un cambio di comportamento della madre: si conferma al
    via del giro 1 (§5.1).

* **D-S-8 — `fn_grant_storico_shadows` si ritira, `storico` è in sola lettura per l'app.** ⚠️ Riformulata il 2026-11-27: la domanda «i ruoli
  batch» partiva da un'ipotesi falsa. I ruoli batch non esistono più dal 2026-10-15 (linee-guida-sql §11.6): un
  processo automatico gira come `zeroerp_app`. Fatto datato (catalogo di dbdev, 2026-11-27): sulle 116 shadow hanno
  privilegi solo `zeroerp_owner` (tutti) e `zeroerp_app` (`SELECT, INSERT, UPDATE`). `fn_grant_storico_shadows` è
  scritta per qualunque ruolo con `INSERT`/`UPDATE` sulla madre, ma oggi ne serve uno solo, l'app. La regola «lo
  storico dell'app è senza `DELETE`» sta in **tre** sedi: il loop `20260205-41` (`v_schemi_senza_delete`),
  `scripts/sql/provision_zeroerp.sql` (`REVOKE DELETE … IN SCHEMA storico`) e `fn_grant_storico_shadows`.
  Deciso: con D-S-6 il motivo di `fn_grant_storico_shadows` («il trigger è INVOKER, senza i privilegi fallisce
  l'UPDATE della madre») cade, e la funzione si **ritira** con il suo changeSet `runAlways` del 90_end; `storico`
  diventa uno schema in **sola lettura** per l'app nel loop dei grant e nel provisioning (le due sedi che restano,
  cambiate insieme, §11.8). Chi scrive lo storico oltre al trigger lo dice il censimento (§3): backfill, sync e job
  girano come proprietario e non hanno bisogno di grant.

### 4.2 Aperte

Nessuna sul modello: D-S-10 … D-S-13, nate dal censimento, sono decise (§6), e le classi rilette.

## 5. Il piano dei giri

Scritto il 2026-11-27, dopo D-S-1 … D-S-13 e la rilettura delle classi (§6). Ogni giro ha il suo via; i numeri dei
changeSet si prendono con `scripts/prossimo_changeset.py` al momento di scriverli. L'ordine va dal motore alle
tabelle: prima il trigger e i privilegi, poi le classi.

### 5.1 Giro 1 — il trigger scrive come proprietario, l'app legge soltanto (D-S-3, D-S-4, D-S-6 … D-S-9)

* Una revisione di `script.trgfn_storico_generic` (il corpo dalla doc auto-generata, o da `pg_get_functiondef` se un
  changeSet è più recente):
  * la scrittura nella shadow gira `SECURITY DEFINER` del proprietario, con `search_path` fissato (la forma, trigger
    DEFINER o funzione DEFINER chiamata dal trigger, la sceglie il giro, con `linee-guida-trigger`);
  * `user_insert` scrive l'operatore (GUC `app.jwt_user`, ripiego `session_user`) e la colonna nuova
    `ruolo_sessione` scrive `session_user` (D-S-7); il building block dell'operatore lo usano anche il trigger di
    audit delle madri e i default delle colonne; colonne e default cambiano su tutte le shadow:
    `dbops.fn_ensure_storico_table` per quelle che nasceranno, un changeSet per quelle che esistono;
  * il reset del flag dopo l'UPDATE si toglie (D-S-3);
  * il valore di `storicizza` sulla riga non si legge più: la colonna resta il **marcatore della classe** (D-S-2),
    e un'eccezione passa solo dal trigger sospeso dal proprietario (D-S-4). Conseguenza da confermare al via del
    giro.
* I privilegi (D-S-6, D-S-8): `storico` diventa uno schema in sola lettura per l'app nel loop dei grant
  (`20260205-41`, il `REVOKE` sta lì, §11.8) e in `scripts/sql/provision_zeroerp.sql`, cambiati insieme; si
  ritirano `dbops.fn_grant_storico_shadows` e il suo `runAlways` del 90_end (`20260902-10`).
* `dbops.fn_admin_merge_comune` e `fn_admin_merge_stradario` scrivono i due registri delle fusioni
  (`storico.comune_trasformazioni`, `storico.stradario_trasformazioni`, che non sono shadow): sono strumenti DBA e
  girano come proprietario; il giro verifica che nessun percorso dell'app li chiami.
* pgTAP: l'app non scrive nessuna shadow (postura), l'UPDATE della madre fatto dall'app lascia la versione con
  `user_insert` = l'operatore della GUC e `ruolo_sessione = zeroerp_app`, un UPDATE che porta `storicizza = false` lascia comunque la versione, il trigger
  sospeso dal proprietario non la lascia.
* Doc: la nota `_tabelle-storico` (D-S-9), la guida `storicizzazione-tabelle` (§«La colonna `storicizza`»,
  §«Di chi è»), `gestione-degli-indirizzi` (righe 495 e 776), `provisioning-db-roles` (§«Scope congelato delle
  shadow»).

### 5.2 Giro 2 — la classe N: la colonna si toglie (D-S-1, D-S-2, T-1)

* Le tabelle N del §6 perdono `storicizza`, il trigger e la riga del registro. Le shadow **restano** con le versioni
  già scritte («lo storico sopravvive alla fonte»). ⚠️ Il trigger è generato dall'automazione: il giro verifica come
  esce (§11.5 di linee-guida-sql vieta il DDL sui trigger generati da `ci_apply`).
* T-1: `anagrafiche.soggetti_titoli_iva_movimenti` è un registro, quindi l'annullo non può restare un `UPDATE`
  della riga: `anagrafiche.fn_annulla_movimento_titolo_iva` scrive un movimento di storno. Il giro legge prima
  l'accumulatore (`trgfn_soggetti_titoli_iva_movimenti_accumulatore`) e i lettori del campo d'annullo; se è un cambio
  di comportamento per il BE, entra nelle richieste (§5.7).

### 5.3 Giro 3 — la classe E: lo storico parte dall'emissione (D-S-5, D-S-10)

* Un attributo dello stato nei vocabolari degli stati dei documenti (`config.stati_doc_*` e gli stati di magazzino,
  template, ricevute) dice «da qui il documento è emesso»; il trigger lo legge tramite un registro (tabella → colonna
  di stato → vocabolario), non da un elenco di codici. Le righe seguono la loro testata, risalendo al padre come fa
  già `fn_storico_risolvi_scope`.
* Il giro dice che cosa succede al passaggio bozza → emesso: la prima versione si scrive alla prima modifica dopo
  l'emissione, come oggi per l'INSERT.

### 5.4 Giro 4 — le colonne di processo (D-S-11)

* Un registro (tabella, colonna) delle colonne che scrive un processo, sulla forma dei registri di
  `automazione-db`; il trigger non scrive la versione quando un UPDATE cambia solo quelle. Prime righe:
  `vendite.commesse_attivita` (lo stato di fatturazione), `anagrafiche.soggetti_titoli_iva` (il contatore del
  plafond). Il giro censisce le altre leggendo i verbi dei processi.

### 5.5 Giro 5 — le tabelle C che oggi non hanno storico (D-S-12, D-S-13)

* Le 55 tabelle del pannello prendono `storicizza` DEFAULT `true` e la riga di `dbops.storico_scope_policy`
  (`NESSUNO` per i cataloghi globali); le 8 senza `user_update` prendono prima le colonne di audit.
* Le madri C che oggi hanno DEFAULT `false` (`config.forme_giuridiche`, `stati_pdp`, `magazzino.assets`,
  `causali`, `pratiche.sospensioni`) passano a DEFAULT `true`, con le righe esistenti accese a trigger sospeso, come
  `20261123-38`.

### 5.6 Garanzie ritirate

Censimento lato DB sul catalogo di dbdev, 2026-11-27 (ricerca sul corpo delle funzioni e sulle viste; l'SQL
dinamico non si vede, e il giro lo rilegge).

| Garanzia che si ritira | Lettori lato DB | Esito |
| --- | --- | --- |
| «chi scrive la madre scrive anche lo storico» (INVOKER, D-S-6) | l'unica funzione che scrive una shadow è il trigger; i due `fn_admin_merge_*` scrivono i registri delle fusioni come proprietario; `dbops.fn_storico_backfill_scope` aggiorna le shadow con SQL dinamico ed è INVOKER | il backfill gira nel migrate, come proprietario: non ne dipende. Da riverificare al giro 1 |
| «`user_insert` della shadow è l'utente corrente del DB» (D-S-7) | `dbops.vw_storico_scope_da_dichiarare` legge lo storico; `fn_storico_risolvi_scope` e `script.fn_get_vie_discendenti` leggono le shadow | nessuno dei tre legge `user_insert`: da confermare al giro 1 |
| «l'app può spegnere lo storico di una riga» (D-S-4) | nessuna funzione DB scrive `storicizza = false` (oltre al trigger) | lato DB nessun lettore; la guida degli indirizzi lo descrive, e si riscrive |
| «una tabella con DEFAULT `false` ha uno storico a richiesta» (D-S-2) | nessuno | — |
| «una fattura in bozza lascia versioni» (D-S-5) | chi legge `storico.fatture` (audit, ristampa) | da censire al giro 3, con il BE |

### 5.7 Le richieste al team BE/FE

Da mandare al via del giro 1, tutte insieme:

* **«Censisci le scritture che passano `storicizza`»**: dopo il giro 1 il valore non conta più; chi lo scrive per
  saltare lo storico (import, normalizzazioni, script) perde l'effetto, e il DB non lo dice. Il caso noto è la guida
  degli indirizzi; non è un elenco chiuso.
* **«Censisci chi scrive in `storico.*`, e chi legge `user_insert`»**: dopo il giro 1 l'app non scrive più nessuna
  shadow, `user_insert` dice l'operatore (come nella madre) e la porta del DB passa in `ruolo_sessione`. L'app `storico` è uno scheletro, ma l'ORM o l'SQL grezzo
  altrove non si escludono da qui.
* **«Censisci chi legge lo storico di un documento in bozza»** (giro 3), e l'eventuale ricaduta di T-1 sui movimenti
  del titolo IVA (giro 2).

### 5.8 Revisione critica del piano — 2026-11-27

Riletto il piano sul corpo di `script.trgfn_storico_generic`, `dbops.fn_run_automations_storico`,
`fn_run_automations_storico_provision`, `fn_ensure_storico_table` e `fn_storico_arma_scope` (doc auto-generata) e sulla
regola `STORICO` di `dbops.automation_rules_tbl`. Le decisioni D-S-1 … D-S-13 reggono; i punti sotto sono difetti o
buchi del **piano dei giri**, e R-1 … R-4 vanno decisi prima del via del giro 1.

* **R-1 — Il giro 2 si rompe da solo.** `fn_run_automations_storico` monta il trigger su ogni madre che ha la
  **gemella** in `storico` (`has_sto`), non su quelle che hanno `storicizza`: la colonna la guarda solo il
  provisioning della shadow. Il giro 2 toglie la colonna e lascia la shadow («lo storico sopravvive alla fonte»), quindi
  il `ci_apply` successivo rimonta il trigger, e il trigger muore sulla prima riga (`NEW.storicizza` non esiste, fuori
  da ogni blocco `EXCEPTION`): ogni UPDATE della madre si ferma. Oggi la classe ha già **due marcatori** che possono
  divergere (la colonna per la shadow, la shadow per il trigger). Proposta: un marcatore solo, letto dalle due
  automazioni e dal trigger. Il candidato è il registro `config.storico_set_storicizza`, che esiste già e oggi serve
  solo al reset «one-shot» che D-S-3 ritira: «la madre è storicizzata» = «è nel registro», con una classe (C/E) per
  riga.
* **R-2 — La colonna che non si legge più tace.** Al giro 1 `storicizza` resta ma il suo valore non conta: un
  `UPDATE … SET storicizza = false` dell'app passa e non fa niente, e il §5.7 lo ammette («il DB non lo dice»). Il
  limite di D-S-1 chiede il contrario: il DB **rifiuta** la scrittura sbagliata. Strade: (a) un `CHECK (storicizza)`
  sulle madri, che fa rompere subito chi la scrive (le rotture del BE sono ammesse); (b) con R-1, la colonna si
  **toglie** da tutte le madri e la classe sta nel registro. La (b) chiude anche D-S-2 senza eccezioni: nessuna madre
  ha più la colonna.
* **R-3 — L'ordine dei giri apre una finestra.** Il giro 1 toglie il reset e smette di leggere il flag; le tabelle N
  (giro 2) ed E (giro 3) restano col trigger. Fra i due giri, le 17 madri che oggi hanno DEFAULT `false` (fra cui
  `vendite.fatture_righe` e `magazzino.movimenti`) passano da «una versione, poi silenzio» a una versione per ogni
  UPDATE, e le righe ricalcolate dalla pipeline dei lotti scrivono versioni a ogni giro. Proposta: il giro 1 fa il
  trigger DEFINER e i privilegi, e la lettura del flag si toglie **insieme** al giro 2, o dopo, che stacca il trigger
  dalle N. Il giro 3 (E) va prima di togliere la lettura del flag sulle righe dei documenti.
* **R-4 — Le policy di scrittura delle shadow.** `fn_storico_arma_scope` crea su ogni shadow protetta
  `rls_sto_<tab>_trg_ins` e `_trg_upd` con `true`, «perché la shadow la scrive il trigger», cioè l'app. Con D-S-6 le
  scrive il proprietario, che non passa dalla RLS (non c'è `FORCE`): le due policy restano lì senza servire a niente.
  La funzione è «forward-only, non disarma mai», quindi le rimette a ogni convergenza. Il piano non le nomina: vanno
  nel giro 1, nella funzione e sulle shadow esistenti.
* **R-5 — La classe E non dice su quale stato decide.** Il §5.3 non dice se conta lo stato di `OLD` o di `NEW`, e
  i due casi diversi sono tre: l'emissione (OLD in bozza, NEW emesso: nessuna versione, la prima arriva alla modifica
  successiva), il ritorno in bozza (un annullo dell'emissione, OLD emesso: deve lasciare la versione), il `DELETE` di
  un documento emesso. Le righe «risalgono al padre»: nel `DELETE` in cascata la testata può non esserci più, e serve
  un ripiego dichiarato, come quello che `fn_storico_risolvi_scope` ha già per lo scope.
* **R-6 — Le colonne di processo cambiano il significato della versione** (D-S-11). Una versione dice «la riga era
  così da `valid_from` a `valid_to`». Se il trigger salta gli UPDATE di sole colonne di processo, quelle colonne nello
  snapshot valgono al momento in cui la versione è stata scritta, non per tutto l'intervallo. Lo deve dire la nota
  `_tabelle-storico`, e il giro 4 decide se le colonne di processo si tolgono dallo snapshot. Nello stesso punto: un
  UPDATE che non cambia niente oggi lascia una versione. Il confronto OLD/NEW del giro 4 lo copre, se lo si dichiara.
* **R-7 — `tx_id` della shadow non lo scrive nessuno.** La colonna nasce in ogni shadow (`fn_ensure_storico_table`),
  e nessuno dei due `INSERT` del trigger la valorizza. D-S-1 dice che la storia di un dato di lavoro è il lotto
  («stato, `tx_id`, log della pipeline»). Il giro 1 riscrive proprio quegli `INSERT`: o le versioni portano il
  `tx_id`, o la colonna si dichiara inutilizzata. Lo decide Tid, ed è facoltativo.
* **R-8 — Il giro 2 tocca un oggetto di un'altra sessione.** `config.utilities_tipi_ruolo` (N per D-S-12) ha
  modifiche non committate di `brief-db-utility-gestite-dall-emittente` (CSV, guard, pgTAP, 2026-11-27). Il giro 2
  parte dopo il suo commit.
* **R-9 — La sospensione del trigger da un job.** D-S-4 ammette i job notturni del proprietario fra chi sospende il
  trigger. Il modo di `20261123-38` è un `ALTER TABLE … DISABLE TRIGGER`, cioè DDL con lucchetto esclusivo sulla madre
  per tutta la transazione: va bene in un migrate, su una tabella viva blocca l'app. Il giro 1 lo scrive nella guida
  come vincolo di D-S-4, o dice un'altra forma.
* Guida indietro, fuori dal brief: `.codex/PROJECT_CONTEXT.md` dice ancora di `storico` «nessuna decisione presa»
  (albero dei moduli) e «resta senza decisione» (perimetro). Si corregge col commit di questo file.

## 6. Il censimento delle tabelle storicizzate — 2026-11-27

Letto sul catalogo di dbdev, in sola lettura: le madri che portano il trigger `trgfn_storico_generic`, il default di
`storicizza`, la riga nel registro, i privilegi diretti dell'app sulla madre, le funzioni che la scrivono (ricerca
sul corpo, `I:` INVOKER, `D:` DEFINER: trova l'SQL statico, non quello dinamico, ed è un punto di partenza, non un
elenco chiuso). È struttura, non popolazione: la classe la dà D-S-1 sul significato del dato.

**Fatti di struttura emersi:**

* 119 madri, 116 shadow. Cinque shadow sono condivise da due madri omonime (`acquisti`/`vendite`: `ddt`,
  `ddt_righe`, `ordini`, `ordini_righe`, `ordini_righe_fulfillment`); il commento del trigger dice «sei».
* ⚠️ Corretto il 2026-11-27: `storico.comune_trasformazioni` e `storico.stradario_trasformazioni` non sono shadow
  rimaste senza madre, sono i **registri delle fusioni** di comuni e vie, scritti da `dbops.fn_admin_merge_comune` e
  `fn_admin_merge_stradario`. Le shadow vere sono quindi 114 su 116 tabelle dello schema.
* Le madri con DEFAULT `false` (classe «a richiesta», da ritirare con D-S-2) sono 17: `config.comuni`,
  `forme_giuridiche`, `stati_pdp`, `tipi_ruoli_nature_ammesse`, `tipi_ruolo_tipi_indirizzo`,
  `tipi_soggetto_dettaglio_tipi_indirizzo`, `utilities_tipi_ruolo`; `magazzino.assets`, `causali`, `eventi_assets`,
  `movimenti`, `movimenti_attesi`; `pratiche.sospensioni`; `vendite.fatture_atti`, `fatture_indirizzi`,
  `fatture_riepiloghi_iva`, `fatture_righe`. Tutte le altre hanno DEFAULT `true` e sono nel registro.
* L'app scrive direttamente (`INSERT`/`UPDATE`/`DELETE`) su quasi tutte le madri; non ce l'ha su `dati_societari`,
  i profili e i legami d'accesso, gli override, `user_emittenti_fiscali` e tutto `magazzino`, dove scrivono solo i
  verbi DEFINER; su `identita_digitali` ha il solo `INSERT`.
* Il criterio di D-S-1 ha già un precedente scritto: il commento di `vendite.fatture_atti` («si rifà a ogni
  rigenerazione del lotto e si congela con la fattura, quindi la sua storia sarebbe rumore»).
* All'opposto, molte tabelle del pannello (`config.tabelle_gestibili`) sono dati decisi **senza** storico:
  `termini_pagamento`, `modalita_pagamento`, `valute`, `utilities`, gli `stati_doc_*`, i `tipi_*`, e altre. Il
  censimento le vede solo da qui: non hanno la colonna (D-S-13).

**Le classi proposte.** C = continuo; E = continuo dall'emissione (la bozza è lavoro, D-S-5 e D-S-10);
N = nessuno, la colonna si toglie (D-S-2); ⚠️ = dipende da una decisione aperta.

| Schema | C — continuo | E — dall'emissione | N — nessuno |
| --- | --- | --- | --- |
| `anagrafiche` | 23 madri su 24 (soggetti, clienti, fornitori, indirizzi, civici, conti, billing account, emittenti, PDP, PSP, reseller, risorse umane, vettori, catasto, dati societari, vesti, titoli IVA e ambiti); `soggetti_titoli_iva`, con il contatore del plafond fra le colonne di processo (D-S-11) | — | `soggetti_titoli_iva_movimenti`: un registro, l'annullo diventa uno storno (T-1) |
| `catalogo` | `articoli`, `articoli_componenti`, `articoli_uom_operativa` | — | — |
| `config` | parametri e override, IVA (`iva`, `_assoggettamenti`, `_natura`, `_stati`), listini tipologie, `note_stili`, `scope_policy`, `stradario`, profili, legami e override d'accesso, emittenti dell'utente; dal pannello `forme_giuridiche`, `stati_pdp` (oggi `false`) | — | i cataloghi solo di seed (`comuni`, le tre matrici `tipi_*`, `utilities_tipi_ruolo`: D-S-12) |
| `dbops` | `processi_accensione` | — | — |
| `documenti` | `template_asset`, `template_documenti` | `template_documenti_versioni` (dalla pubblicazione) | — |
| `magazzino` | `lotti`, `magazzini`, `assets`, `causali` (le ultime due oggi `false`) | `inventari`, `rettifiche`, `trasferimenti` con le righe (dalla postatura) | `movimenti`, `eventi_assets` (registri), `movimenti_attesi` (i blocchi, lavoro) |
| `pagamenti` | `sepa_mandati` | — | — |
| `pratiche` | definizioni (`template_flussi`, `regole_generazione`, `competenze_flussi`, `tipi_prestazione`), istanze (`pratiche`, `flussi`), note, `pratiche_sorgenti`, `sospensioni` (oggi `false`) | — | — |
| `shop` | — | `ricevute` | — |
| `vendite` | `articolo_regole_fatturazione`, `registri_fatturazione`, `commesse`, `commesse_sorgenti`, `attivita_consumi`, `fatturazione_lotti` (è la traccia del processo), `commesse_attivita` con lo stato di fatturazione fra le colonne di processo (D-S-11) | `fatture`, `fatture_scadenze` (D-S-5); `preventivi`, `ordini`, `ordini_righe`, `ddt`, `ddt_righe`, `ddt_righe_prelievi`, `resi`, `resi_righe`, `resi_righe_accrediti`, `resi_righe_rientri`, `resi_righe_rinunce` (D-S-10) | `attivita_fatturabili` (nasce dalla commessa, la consuma il lotto), `fatturazione_lotti_fatture`, `fatturazione_lotti_gruppi`, `fatturazione_lotti_esiti` (lavoro e registro del lotto), `fatture_righe`, `fatture_atti`, `fatture_indirizzi`, `fatture_riepiloghi_iva` (calcolate, congelate con la fattura), `ordini_righe_fulfillment`, `resi_righe_riconsegne` (derivate dai DDT) |
| `acquisti` | — | `ordini`, `ordini_righe`, `ddt`, `ddt_righe` (D-S-10) | `ordini_righe_fulfillment` |

**I punti della rilettura (Tid).** ✅ Riletti il 2026-11-27: T-1 **N**, gli altri come proposti. Le classi della tabella sono una proposta del team DB, fatta dal nome, dalla
struttura e dalle funzioni che scrivono: questi sono i punti dove la proposta è meno sicura.

* **T-1** `anagrafiche.soggetti_titoli_iva_movimenti`: N se è un registro (l'annullo diventa una riga nuova), C se
  l'annullo resta un `UPDATE` della riga. ✅ **N** (Tid, 2026-11-27): l'annullo diventa uno storno (§5.2).
* **T-2** `vendite.attivita_consumi` in C: i consumi li correggono le persone, o arrivano solo da un import?
* **T-3** `vendite.attivita_fatturabili` in N: nasce dalla commessa, la consuma il lotto.
* **T-4** `vendite.fatturazione_lotti` in C (la traccia del processo), con `_fatture`, `_gruppi`, `_esiti` in N.
* **T-5** le righe del reso: `resi_righe_accrediti`, `_rientri`, `_rinunce` in E (le decide chi conferma il reso),
  `resi_righe_riconsegne` in N (deriva dal DDT di riconsegna); `ddt_righe_prelievi` in E con il DDT;
  `ordini_righe_fulfillment` in N (deriva dai DDT).
* **T-6** `pratiche.pratiche` e `pratiche.flussi` in C: un'istanza di workflow non ha una bozza, e i cambi di stato
  sono fatti, anche quando li fa un trigger. `pratiche.sospensioni` in C (oggi DEFAULT `false`).
* **T-7** `magazzino.assets` in C (oggi DEFAULT `false`), `eventi_assets` in N (è il registro degli eventi).
* **T-8** `config.comuni` in N: è un catalogo di seed e ha già il suo modello nel tempo (le trasformazioni dei comuni).
* **T-9** `shop.ricevute` in E: se una ricevuta nasce già emessa, E coincide con C.
* **T-10** `config.utilities_tipi_ruolo` in N: è di seed per D-U-10 di
  `brief-db-utility-gestite-dall-emittente` (brief vicino, stessi oggetti).

**Le decisioni che il censimento apre (Tid):**

* **D-S-10 — «Dall'emissione» vale per tutti i documenti, non solo per quelli dei lotti.** ✅ Deciso da Tid il
  2026-11-27, come proposto. La bozza di un ordine,
  di un DDT, di un reso, di un inventario è lavoro come la bozza di una fattura: le righe si correggono, i totali si
  ricalcolano. Proposta: **sì**. Lo storico parte quando il documento esce dalla bozza; la condizione la dà lo stato
  del documento (un attributo dello stato nel vocabolario, non un elenco di codici nel trigger). Il preventivo ha già
  le sue revisioni (`fn_crea_revisione_preventivo`): il censimento non le tocca. Le righe ⚠️ di D-S-10 nella
  tabella sopra passano in E.
* **D-S-11 — Le colonne scritte da un processo su una riga decisa.** ✅ Deciso da Tid il 2026-11-27: strada **b**. `commesse_attivita` (lo stato di
  fatturazione, scritto da emissione e liberazione del lotto), `soggetti_titoli_iva` (l'accumulatore del plafond):
  oggi ogni scrittura del processo lascia una versione della riga. (a) va bene così; (b) un registro delle colonne di
  processo, e il trigger non scrive la versione quando cambiano solo quelle. Proposta: **b**, sulla forma dei
  registri di `automazione-db` («si scrive nei registri ciò che la struttura non dice»). Nello stesso punto:
  `soggetti_titoli_iva_movimenti` è un registro (N) se l'annullo diventa una riga nuova, C se resta un `UPDATE`.
* **D-S-12 — I cataloghi di seed.** ✅ Deciso da Tid il 2026-11-27, come proposto. Un catalogo che cambia solo con una migrazione ha la storia nel repository (il
  CSV e i suoi commit): N. Uno che l'utente modifica dal pannello è un dato deciso: C. Proposta: questa regola, e la
  stessa vale per le tabelle che nasceranno.
* **D-S-13 — Il censimento al contrario.** ✅ Deciso da Tid il 2026-11-27, come proposto: le 55 tabelle del
  pannello senza storico entrano in questo brief (C), le 8 senza `user_update` prendono prima le colonne di audit. Le tabelle di dati decisi che oggi **non** hanno storico (le tabelle del
  pannello sopra, e quelle di altri domini). Proposta: in questo brief le tabelle del pannello, che hanno già un
  elenco (`config.tabelle_gestibili`); le altre si guardano dominio per dominio quando un cantiere le tocca.

  Fatto di struttura (catalogo di dbdev, 2026-11-27): `config.tabelle_gestibili` ha 64 tabelle modificabili dal
  pannello (`pannello = true`); **55 non hanno `storicizza`**, 9 sì (`forme_giuridiche`, `iva`,
  `iva_assoggettamenti`, `iva_natura`, `note_stili`, `stati_pdp`, `magazzino.causali`, `pratiche.template_flussi`,
  `pratiche.tipi_prestazione`). Delle 55, **8 non hanno nemmeno `user_update`** (`config.categoria_accisa`,
  `classi_utenze`, `modalita_addebito_trasporto`, `stati_doc_fiscale`, `stati_doc_ordini`, `stati_sdi`,
  `tipi_utenze`, `vendite.stati_commessa`): una versione direbbe che cosa è cambiato, non chi. Le altre 31 righe del
  registro sono `pannello = false` (solo tendina): per D-S-12 sono N se cambiano solo con una migrazione. Fuori dal
  pannello, un esempio di dato deciso senza storico: `vendite.listini`.

## Piano

- [x] Quando partire (Tid): l'analisi parte il 2026-11-27
- [x] Il perimetro e il flag `storicizza`, D-S-1 … D-S-5 (Tid, 2026-11-27)
- [x] D-S-6 strada a, D-S-9 come proposta (Tid, 2026-11-27)
- [x] D-S-7: `user_insert` l'operatore, `ruolo_sessione` la porta (Tid, 2026-11-27, strada b)
- [x] D-S-8, si ritira `fn_grant_storico_shadows` (Tid, 2026-11-27)
- [x] Il censimento delle tabelle storicizzate, letto sulla struttura (§6, 2026-11-27)
- [x] D-S-10 e D-S-12 come proposte (Tid, 2026-11-27)
- [x] D-S-11 strada b (Tid, 2026-11-27)
- [x] D-S-13 come proposta (Tid, 2026-11-27)
- [x] La rilettura delle classi: T-1 N, le altre come proposte (Tid, 2026-11-27)
- [x] Il piano dei giri, con «Garanzie ritirate» e le richieste al BE/FE (§5, 2026-11-27)
- [x] La revisione critica del piano (§5.8, 2026-11-27)
- [ ] R-1 … R-4 (Tid)
- [ ] Il via del giro 1 (Tid)
- [ ] Giro 1 — il trigger come proprietario, `storico` in sola lettura per l'app (§5.1)
- [ ] Giro 2 — la classe N (§5.2)
- [ ] Giro 3 — la classe E (§5.3)
- [ ] Giro 4 — le colonne di processo (§5.4)
- [ ] Giro 5 — le tabelle C senza storico (§5.5)

## Registro

| Data | Chi | Che cosa |
| --- | --- | --- |
| 2026-11-27 | DB | Brief aperto, non iniziato, da D-AL **a** (Tid) del giro 10-quater di `brief-db-porte-aperte-dalla-sola-guc` |
| 2026-11-27 | DB + Tid | Analisi avviata: struttura letta (§2), limite del modello (§1), D-S-1 … D-S-5 decise (§4.1), aperte D-S-6 … D-S-9 |
| 2026-11-27 | DB + Tid | D-S-6 **a** e D-S-9 decise; D-S-7 corretta su osservazione di Tid e riverificata su dbdev (utente corrente = di norma utente di connessione), proposta `session_user`; D-S-8 da rivedere |
| 2026-11-27 | DB + Tid | D-S-7 decisa (`session_user`); D-S-8 riformulata: i ruoli batch non esistono più, sulle shadow scrivono solo app e proprietario; proposta: si ritira `fn_grant_storico_shadows`, `storico` in sola lettura per l'app |
| 2026-11-27 | DB + Tid | D-S-8 decisa: si ritira `fn_grant_storico_shadows`, `storico` in sola lettura per l'app. Parte il censimento |
| 2026-11-27 | DB | Censimento delle 119 madri storicizzate (§6): classi proposte, aperte D-S-10 … D-S-13 |
| 2026-11-27 | DB + Tid | D-S-10 e D-S-12 decise come proposte; D-S-11 da rispiegare |
| 2026-11-27 | DB + Tid | D-S-11 decisa: strada b, il registro delle colonne di processo |
| 2026-11-27 | DB + Tid | D-S-13 decisa: le 55 tabelle del pannello prendono lo storico; tabella delle classi aggiornata con D-S-10 … D-S-13 |
| 2026-11-27 | DB + Tid | Classi rilette (T-1 N); corretto il §6 sui due registri delle fusioni; scritto il piano dei giri (§5) con «Garanzie ritirate» e le richieste al BE/FE |
| 2026-11-27 | DB + Tid | D-S-7 rivista (strada b): `user_insert` della shadow = l'operatore come nella madre, `ruolo_sessione` nuova = `session_user`; la regola dell'operatore diventa un BB usato anche dall'audit |
| 2026-11-27 | DB | Revisione critica del piano sul corpo di trigger e automazioni (§5.8): R-1 … R-9; R-1 … R-4 da decidere prima del via del giro 1 |
