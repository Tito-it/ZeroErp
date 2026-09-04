# Analisi DB+BE — nessun processo senza operatore: identità e perimetro dei job

> **Che cos'è questo documento.** L'**analisi** e le **decisioni** su chi esegue i
> processi automatici e dentro quale emittente. ⇒ Il piano operativo lato database vive
> in [brief-db-processi-automatici-identita-e-perimetro.md](brief-db-processi-automatici-identita-e-perimetro.md):
> qui c'è **il perché**, lì **il cosa si scrive**.
>
> **Destinatario:** team DB (`dev/db-tid`) e backend (`dev/backend-tid`).
>
> **Origine.** Decisione di Tid, 2026-09-04: *«i processi non possono girare senza
> operatore, anche a costo di creare utenti tecnici — non voglio che nessuno faccia
> girare attività libere: si deve poter conoscere chi ha eseguito l'attività
> sempre»*.
>
> **Perché adesso, e non dopo.** Tid: *«prima di iniziare col magazzino preferisco
> sistemare i processi, così quello di magazzino nasce pulito e allineato — non ho
> produzione, posso farlo subito»*. ⭐ È la condizione migliore: si tocca un
> meccanismo mentre **non c'è ancora il consumatore** che erediterebbe il difetto.
>
> **Stato:** ✅ **ANALISI CHIUSA** — decisioni prese; il disegno DB è passato al brief.
> Nessun changeSet, niente applicato.
>
> ⚠️ **Perimetro:** *chi* esegue un processo automatico e *dentro quale emittente*.
> ⛔ **Non** è di questo brief cosa fanno i processi, né la coda in sé.
>
> **Decisioni chiuse** (tutte 2026-09-04, di Tid): **D-1, D-2, D-4, D-5, D-6, D-8,
> D-9, D-10** — tabella in §9. **Aperte:** **D-0** (il registro: da progettare, vincoli
> completi) e un dettaglio di **D-3** (accanto al codice del processo, si registra
> anche l'`auth_user_id` quando c'è?).
>
> **Terza stesura, 2026-09-04.** Le stesure precedenti sono state verificate contro il
> codice e la doc auto-gen; ciò che non reggeva è corretto nel corpo e registrato in
> §16 (storia delle revisioni), così il testo si legge senza dover leggere gli errori.

---

## 0. In due parole, senza tecnicismi

Un programma può girare in due modi: perché **una persona ha premuto un pulsante**,
oppure **da solo** — di notte, a orario, o perché qualcosa l'ha messo in coda.

Nel primo caso si sa sempre chi è stato: c'è l'utente collegato. Nel secondo no — e
la richiesta è che si sappia **comunque**, sempre.

**Che cosa si è deciso, in parole normali:**

1. **I programmi automatici non sono tutti uguali.** Alcuni fanno *manutenzione del
   database* (sistemano indici, tabelle di servizio): non toccano il lavoro di nessuna
   azienda. Altri fanno *il lavoro dell'azienda* (fatturare, stampare, chiudere
   scadenze). Ai primi basta lasciare **il nome** di chi è girato. I secondi devono
   lavorare **un'azienda emittente alla volta**, con un **utente vero** che dice chi
   sono e dove possono guardare.
2. **Ogni programma automatico dichiara che cosa è**, in un registro. Non lo si
   indovina dal codice: lo si scrive, e il database controlla che la dichiarazione sia
   coerente con le tabelle che quel programma tocca.
3. **Chi fa il lavoro dell'azienda ha un proprio utente tecnico** — *uno per
   programma*, non uno per azienda, e non un «doppione» di una persona vera. Quando
   qualcuno chiede *«chi ha fatturato?»* la risposta è *«il programma di
   fatturazione»*, e *«per quale azienda?»* è una domanda separata.
4. **Si toglie il permesso speciale** che oggi fa vedere a un programma i dati di
   tutte le aziende insieme. Tid: *«altrimenti siamo da capo: qualcuno lo attiva e fa
   casino»*. Senza quel permesso, un programma che sbaglia **non fa danni**: al massimo
   non fa niente.
5. **La fatturazione notturna non gira più «tutta insieme»**: mette in coda un lavoro
   per ogni azienda, e i lavori possono girare in parallelo. Se uno fallisce, gli altri
   vanno avanti.
6. **Quando nasce un'azienda emittente nuova, una persona la aggiunge** alla lista
   di ogni programma che deve servirla. Il sistema non lo fa da solo, ma **segnala**
   se manca.

⭐ **La buona notizia è che il progetto ha già quasi tutto.** La coda dei lavori fa già
la cosa giusta; c'è da completarla e da portare gli altri programmi sullo stesso
binario.

---

## 1. Che cosa è stato letto

Letto il **2026-09-04** sul database vivo (`dbops.coda_lavori`,
`maintenance.job_run_log`, `script.fn_job_run_start`, `maintenance.fn_run_and_log`,
`script.fn_check_user_emittente_scope`, `script.trgfn_guard_emittente_scope`,
`anagrafiche.identita_digitali`, `pg_roles`), sui changeSet di `85_pgagent`, sul
catalogo dei building block backend e sui file che usano il canale di sistema.

⚠️ Sono **letture di struttura**: colonne, `CHECK`, commenti di colonna, corpi di
funzione, policy RLS, e chi chiama che cosa. Nessun conteggio di righe di dati decide
niente qui. ⛔ E **nessuna lettura su `magazzino` e `acquisti`**: sono in
ristrutturazione, e un cantiere aperto non si misura.

---

## 2. ⭐⭐ Le tre classi di processo

**Decisione di Tid, 2026-09-04:** *«bisogna fare una distinzione tra lavori automatici
che servono alla manutenzione del db — generatori di indici, automazioni — e le
attività specifiche che eseguono processi dell'applicazione, come fatturazione o
magazzino»*.

### 2.1 Le classi sono TRE, e chiedono cose diverse

| Classe | Che cosa fa | Esempi | Attore | Perimetro emittente |
| --- | --- | --- | --- | --- |
| **MANUTENZIONE** | tiene in piedi il database: trigger, indici, storicizzazione, pulizie | i dieci job `automations_*`, `apply_fk_index_policy`, `apply_storicizza` | **il nome** del processo | ⛔ no — non c'è niente da restringere |
| **AMMINISTRAZIONE** | tocca dati dell'applicazione che **non appartengono a un emittente** | `sync_auth_user_expired`, invio email di sistema | **il nome** del processo | ⛔ no |
| **DOMINIO** | fa il lavoro dell'azienda, dentro il perimetro di un emittente | fatturazione, stampe, invio fatture via email, cessazione contratti, chiusura versioni di listino, ricalcolo giacenza | **un utente tecnico** (§6) | ✅ sì — **un emittente alla volta** |

### 2.2 ⭐ Chi ha eseguito e dove sono due domande separate

La richiesta di Tid — *«conoscere chi ha eseguito l'attività **sempre**»* — vale per
**tutte e tre** le classi. L'iterazione per emittente vale **solo per la terza**.

⇒ L'attore sul registro dei run (D-3) è **incondizionato** e non aspetta nessuna
classificazione; la classe decide soltanto *chi itera*.

### 2.3 ✅ D-8 — L'attore è sempre un NOME; l'utente c'è in più dove serve

**Decisione di Tid, 2026-09-04 (risposta A).** I processi di manutenzione girano
**dentro il database** (pgAgent), di notte, senza il backend: non c'è nessuno che possa
«entrare» come utente. Il loro attore è **il codice del processo** nel registro.

⇒ Regola unica: **l'attore di un run è il codice del processo, sempre.** Per i processi
di dominio c'è **in più** l'utente tecnico (§6), che serve al perimetro, non
all'attribuzione. ⚠️ Il presidio *«flag e registro in disaccordo»* (§13) vale quindi
**solo per i processi dichiarati DOMINIO**: gli altri non hanno un'identità da avere.

### 2.4 ⛔ La classe è una DICHIARAZIONE, e il database la verifica in un verso solo

**Il criterio non si deriva dalla presenza della RLS.** Sembrerebbe comodo — *«è di
dominio se la tabella su cui scrive ha una policy `rls_*_ef_whitelist`»* — ma
riconoscerebbe una **difesa**, non la **natura del dato**: una tabella che *dovrebbe*
avere la RLS e non ce l'ha ancora risulterebbe «non di dominio». È come dire che una
casa è abitata se ha l'allarme.

⚠️ E nel momento in cui serve — **il progetto** — la RLS non c'è ancora: arriva dopo,
come conseguenza. Un criterio che funziona solo a cose fatte non serve a chi le sta
facendo. Controesempio in casa: `send_pending_emails` scrive su `config.email_outbox`,
che non porta l'emittente, e spedisce **fatture ai clienti** — è dominio, e un
criterio sulla RLS lo direbbe amministrazione.

⭐ **Il verso giusto:** chi progetta il processo **dichiara** la classe nel registro
(D-0). Il database verifica **una direzione sola**: *dichiarato DOMINIO ma senza
percorso verso un emittente* → riga rossa in una vista che deve restare vuota (§13).
⇒ La dichiarazione **tira il progetto** nella direzione giusta: *«il ricalcolo giacenza
è di dominio»* ⇒ *«allora le sue tabelle devono portare l'emittente»*, mentre si
progetta. È così che magazzino e acquisti, in ristrutturazione, nascono conformi (§11).

⛔ **Il verso opposto non lo prende nessun automatismo**: *«dovrebbe essere DOMINIO ma
è dichiarato manutenzione»* resta un errore umano, e va scritto che è così (§13.1).

⚠️ **«Percorso verso un emittente» include i padri.** `vendite.listini_versioni` non ha
una colonna emittente, ma `listino_id → vendite.listini.emittente_soggetto_ruolo_id`
(`NOT NULL`) ce l'ha: è dominio, come `fatture_righe` lo è attraverso `fatture`. Il
progetto ha già gli adapter `fn_scope_ef_whitelist_via_*` per questi casi. ⛔ Guardare
la sola colonna della figlia è l'errore che questa stesura ha fatto **due volte** (§16):
la classe si giudica dalla natura del dato, e il percorso si segue fino in fondo.

### 2.5 ✅ D-10 — Nei framework guidati da configurazione la classe sta sul BERSAGLIO

**Decisione di Tid, 2026-09-04 (risposta C).** `chiusura_scadenze_daily` non ha un
elenco di tabelle nel codice: lo legge da `dbops.automazione_chiusura_scadenze`. ⇒ La
sua classe **non è una proprietà del job**: è una proprietà di ogni riga di
configurazione, e una riga in più nel CSV ne cambierebbe la natura senza che nessuno
riapra la domanda.

⇒ Per i framework guidati da tabella la classe è **una colonna della riga di
configurazione**, e il job la rispetta bersaglio per bersaglio.

⚠️ Oggi le due righe sono **entrambe di dominio** — `vendite.contratti` direttamente,
`vendite.listini_versioni` attraverso il listino (§2.4) — quindi il job migra intero
(§8.2). La regola serve lo stesso: è la riga **prossima** che deve dichiararsi, non
quelle di oggi.

---

## 3. Com'è oggi: tre strade, una sola sa per conto di chi lavora

| Come parte | Chi è | Perimetro emittente | Registrazione |
| --- | --- | --- | --- |
| ⭐ **`dbops.coda_lavori`** | `run_as` = `SISTEMA` \| `OPERATORE`; per l'operatore uno `scope` **catturato all'enqueue** | ✅ lo `scope` porta `{auth_user_id, username, identita_id, emittente_attivo_id}` | ✅ `job_run_id` verso il log |
| **management command** | ⛔ quando usa il canale di sistema, la connessione passa a un ruolo **`BYPASSRLS`** | ⛔ attraversa gli emittenti per costruzione | ⚠️ parziale — §5.2 |
| **pgAgent** (12 job SQL) | ⛔ nessun utente: pgAgent apre la sua connessione e bypassa la RLS **per ruolo** | ⛔ no | ✅ `job_run_log`, senza attore |

### 3.1 La coda è il modello — con un limite preciso

`dbops.coda_lavori` ha tre colonne che dicono ciò che serve: **`run_as`**, **`scope`**
(l'identità completa catturata all'enqueue), **`origine`** (chi ha accodato: `API` |
`CRON` | `COMMAND` | `TRIGGER`). Il `CHECK` `chk_coda_lavori_run_as_scope` impone
*scope presente se e solo se `run_as = OPERATORE`*.

⚠️ **Il `CHECK` garantisce la coerenza fra `run_as` e `scope`, non che un job di
dominio abbia un operatore.** `dbops.fn_accoda_lavoro` accetta un `p_run_as` che
**sovrascrive** il `run_as_default` del tipo: un tipo di dominio accodato con
`p_run_as => 'SISTEMA'` passa tutti i cancelli. Si chiude in §10.2 (ridefinizione di
`run_as`).

⭐ Fatto che conta, 2026-09-04: i tipi seedati in `dbops/coda_lavori_tipi.csv` sono
**due** (`FATTURAZIONE_GIRO`, `FATTURAZIONE_NUMERA`), entrambi `OPERATORE`. Nessun job
`SISTEMA` è mai esistito: la ridefinizione tocca **il contratto, non una popolazione**.

---

## 4. ⛔ Dov'è davvero la porta aperta

Non è la regola 1 di `script.fn_check_user_emittente_scope` (*«utente NULL → true»*),
per due ragioni verificate:

* **i job pgAgent non passano da lì** — bypassano per ruolo, con la propria
  connessione;
* **in lettura quel ramo è irraggiungibile**: ogni policy `rls_*_ef_whitelist` mette
  in AND `current_setting('app.ruolo_applicativo', true) = 'OPERATORE'` **prima**
  dell'adapter. Una connessione senza GUC ⇒ policy falsa ⇒ **zero righe**. ⭐ Sulle
  tabelle che hanno la RLS, la lettura è già fail-closed.

**La porta viva è in SCRITTURA**, in `script.trgfn_guard_emittente_scope`, due righe
prima di arrivare alla canonica:

```sql
v_auth_user_id := NULLIF(current_setting('app.current_user_id', true), '')::integer;
IF v_auth_user_id IS NULL THEN
  RETURN NEW;  -- batch job, nessun filtro
END IF;
```

⇒ Un processo senza utente **non viene mai controllato in scrittura**. È peggio di una
lettura: lascia **entrare righe**. Ed è lo stesso trigger del difetto 2026-08-22 (*«il
guard si spegneva esattamente nel caso che esiste per coprire»*), in un altro ramo.

### 4.1 ✅ D-4 — La porta si chiude rispecchiando il bypass della RLS

**Decisione di Tid, 2026-09-04.** Il ramo *«utente NULL → passa»* diventa: **«se
questa sessione bypasserebbe la RLS, salta; altrimenti, senza utente → errore»**.

**Chi scrive senza utente, e legittimamente** (verificato 04-09):

| Chi | Perché | Con la porta chiusa «secca» | Con il rispecchiamento |
| --- | --- | --- | --- |
| **le migrazioni** (Liquibase, proprietario `titodb`) | i backfill correggono il pregresso — **18 changeSet** fanno `UPDATE` su tabelle col guard | ⛔ ogni backfill futuro sulle **15 tabelle** col guard fallisce | ✅ passano, come già passano dalla RLS |
| **pgAgent** (superuser) | manutenzione | ⛔ idem | ✅ passa |
| **i pgTAP** | contesto operatore obbligatorio | ✅ | ✅ |
| **un processo applicativo senza utente** | ⛔ non è mai legittimo, dopo D-2/b | ✅ si ferma | ✅ **si ferma** — nessun ruolo applicativo ha più il bypass |

⇒ Il guard **spara esattamente dove spara la policy**: un criterio solo, quello che
PostgreSQL applica già, senza un secondo elenco da mantenere.

⚠️ **È una deroga dichiarata.** Le linee guida (§10.4) vietano alle funzioni di *scope*
di guardare il ruolo del database, perché l'utente applicativo non coincide col ruolo.
Qui non si identifica l'utente: si **rispecchia** la regola di bypass che PostgreSQL
applica già alla RLS. ⛔ L'alternativa — una GUC che una migrazione imposta per dire
«sono io» — è un cartello, non un cancello: chiunque può impostarla. È la stessa
ragione per cui il progetto ha già scartato il «sentinel applicativo» del canale di
sistema (Opzione B, `system_context.py`).

**Quando:** dopo tutto il resto — passo 7 del §12. Non è una decisione, è una
conseguenza: prima che i processi abbiano un'identità, chiuderla li fermerebbe.

---

## 5. Che cosa manca alle altre due strade

### 5.1 I comandi che usano il canale girano come sistema, e bypassano

Il building block lo dichiara: *«ripunta la connessione alle credenziali del ruolo di
sistema … la RLS è **bypassata dal ruolo**»*. Non è una svista: è un disegno con un suo
brief, e va cambiato sapendo che si cambia un disegno.

I call-site reali sono **tre**: `run_fatturazione_batch.py:107`,
`draina_coda_stampa.py:67`, `coda_lavori/drainer_service.py:60`.

⚠️ E c'è codice che **si rompe apposta se il bypass NON c'è**:
`document_generation_service._guard_canale_sistema` solleva se la connessione non è
`BYPASSRLS` quando genera senza emittente. È una difesa scritta bene per il mondo di
oggi, e nel mondo nuovo va **riscritta**, non aggirata (passo 6-bis).

### 5.2 `job_run_log` non registra CHI — e tre processi non ci scrivono affatto

`maintenance.job_run_log` non ha una colonna per l'attore, e né
`script.fn_job_run_start` né `maintenance.fn_run_and_log` hanno un parametro per
riceverlo (⇒ D-3 tocca **due** funzioni).

⛔ Tre comandi headless **non si registrano per niente**: `sync_auth_user_active`,
`send_pending_emails`, `listen_cambio_reparto`. Nessuno usa `registered_job`: girano
come `zeroerp_app`, senza identità e senza riga di run. ⇒ Un presidio costruito su
`job_run_log` **è cieco su di loro**: misura solo chi già si registra.

### 5.3 ⛔ Non esiste un registro dei processi

`job_run_log.jobname` è testo libero; `dbops.domini_task` e `pipeline_task_registry`
catalogano **step di pipeline**; `dbops.coda_lavori_tipi` solo i tipi della coda.
⇒ Non c'è un posto in cui sia scritto **quali processi esistono e di che classe sono**.
Senza, la classe del §2 è una convenzione a mano e nessun presidio del §13 è
costruibile. **È il passo 0 (D-0).**

---

## 6. L'utente tecnico: uno per processo

### 6.1 ⛔ Non per emittente, e non un alias di una persona

**Non `automatico_<emittente>`**: moltiplica le identità per un dato che il contesto
già porta, e alla domanda *«chi ha ricalcolato?»* risponderebbe con dieci nomi per un
solo programma.

**Non un alias derivato da una persona** (*«Mario fa derivare Mario_tecnico»*):

1. ⛔ **l'audit direbbe una bugia** — le colonne scrivono lo username, e un nome
   sbagliato è peggio di uno mancante perché sembra completo;
2. ⛔ **il processo morirebbe con la persona** — `sync_auth_user_expired_daily` disattiva
   gli utenti scaduti, e `coda_lavori/context.py` si ferma con
   `E_CODA_IDENTITA_NON_ATTIVA` se l'identità non è più attiva. La notte in cui Mario
   esce, si ferma la fatturazione;
3. ⛔ **la struttura non lo permette** — `uq_identita_digitali_auth_user_ruolo_attivo`:
   un solo ruolo applicativo attivo per `auth_user`;
4. ⛔ **non risparmia configurazione** — con D-1 il processo serve tutti gli emittenti,
   Mario uno: la whitelist andrebbe riscritta comunque;
5. ⚠️ **il perimetro slitterebbe** con la carriera di Mario, senza che nessuno decida.

⭐ **Il risparmio che l'alias prometteva si ottiene puntando al profilo del reparto**
(`config.profili_accesso_bindings`): i permessi seguono il *ruolo*, non la *persona*.

### 6.2 ✅ D-6 — La forma

**Decisione di Tid:** un **flag dichiarato** (non una convenzione di nome), agganciato a
un **soggetto «sistema» dedicato** (non all'azienda emittente: un processo che serve
tutti non può essere il dipendente di uno).

| Pezzo | Dove | Seed |
| --- | --- | --- |
| il soggetto «sistema» | `anagrafiche.soggetti` (+ `tipo_soggetto_dettaglio`) | 🔧 macchina |
| il tipo ruolo dei processi | `config.tipi_ruoli` — riga nuova | 📚 catalogo |
| il `soggetto_ruolo` di ogni processo | `anagrafiche.soggetti_ruoli` | 🔧 macchina |
| l'identità del processo | `anagrafiche.identita_digitali`, con il **flag** | 🔧 macchina |
| il profilo | **puntato** a quello del reparto, non copiato | 🔧 macchina |
| la whitelist emittenti | `config.user_emittenti_fiscali`, **tutti** gli emittenti | 🔧 macchina |

⚠️ **Il tipo ruolo nuovo e la matrice delle nature**: il guard
`trgfn_soggetti_ruoli_guard_natura_ammessa` applica *«matrice assente = nature
libere»*. Va **dichiarato** — o la riga in `config.tipi_ruoli_nature_ammesse`, o
scritto che è libero e perché.

⭐ **Conseguenza sul registro (D-0)**: ha una parte di **catalogo** (codice, classe,
canale — identica ovunque) e una di **macchina** (quale utente, quali emittenti), perché
quest'ultima valorizza FK verso `anagrafiche.*`. Vanno separate, o la parte macchina
marcata `context: dati_macchina`.

### 6.3 ⛔ Due trappole da chiudere nello stesso passo

1. **L'identità tecnica DEVE essere `OPERATORE`**: ogni policy lo pretende in AND. Con
   un altro ruolo applicativo il processo vedrebbe zero righe, in silenzio.
2. **⛔⛔ Un utente tecnico NON è mai super admin.** La scorciatoia per «serve tutti gli
   emittenti» è `SUPER_ADMIN`, che in `fn_check_user_emittente_scope` bypassa lo scope
   **prima** della whitelist: riaprirebbe la porta con un nome rassicurante. Il
   perimetro si scrive **riga per riga**.

### 6.4 ✅ D-9 — L'emittente nuovo lo aggiunge una PERSONA, e il sistema segnala

**Decisione di Tid, 2026-09-04 (risposta B).** Quando nasce un emittente, la riga in
`config.user_emittenti_fiscali` per ogni processo di dominio la scrive una persona.
Il sistema **non** concede permessi da solo.

⛔ **Il pericolo che questo copre è silenzioso**: senza la riga, il comando accoda
comunque il lavoro per il nuovo emittente; il lavoro parte, la RLS gli mostra **zero
righe**, e finisce con «FATTO, 0 elaborate». **Nessun errore.** Quell'emittente non
viene fatturato, e nessuno lo sa.

⇒ Presidio obbligatorio (§13): *«emittente attivo assente dalla whitelist di un
processo DOMINIO»* — deve restare vuoto.

---

## 7. Difetti del meccanismo esistente

Nessuno è bloccante da solo; tre cambiano il piano.

* **A. ⛔ Un job di dominio può essere accodato come `SISTEMA`** (§3.1). Si chiude con
  la classe su `coda_lavori_tipi` + guard in `fn_accoda_lavoro`. ⚠️ Toccando la
  funzione, il codice `E_PARAMETRO_INVALIDO` che solleva oggi è **debito, non sede**: si
  conia quello nuovo.
* **B. ⛔ D-3 tocca DUE funzioni** — `script.fn_job_run_start` e
  `maintenance.fn_run_and_log`. Una colonna attore `NOT NULL` subito fermerebbe i 12 job
  pgAgent al primo giro: *un `NOT NULL` va dove il dato si può fornire*.
* **C. ✅ [chiuso 04-09 — non si fa] Le due funzioni di run usano forme diverse di
  advisory lock.** Allinearle **accoppierebbe** due canali oggi indipendenti per
  costruzione: le due forme stanno in spazi di lock **distinti**, quindi un job
  pgAgent e un comando headless non si bloccano a vicenda. Motivo esteso nel brief DB §3.4.
* **D. ⚠️ `system_process_context` scambia le credenziali in un dict condiviso dal
  processo** ⇒ mai parallelizzare in thread *finché il canale esiste*. ⭐ **Decade con
  D-2/b** (§10.4): i lavori `OPERATORE` non usano quel canale.
* **E. ⚠️ Il canale di sistema si chiama `zeroerp_batch_fatturazione`** e serve tre
  processi non imparentati: nome di dominio per un canale di sistema. Si ritira con
  D-2/b.
* **F. ⚠️ L'attore del run e l'attore dell'item sono cose diverse**: `draina_coda_lavori`
  registra **un** run (il worker) ed esegue N item, ognuno col suo operatore nello
  `scope`. La colonna di D-3 registra il worker; l'attribuzione per-item è già in
  `coda_lavori.scope`. La vista di presidio deve saperlo.

---

## 8. Il censimento

### 8.1 I job pgAgent sono dodici

`85_pgagent`, dopo la sostituzione del 20260426-06 (che cancella
`listini_versioni_close_scadute_daily`):

| Job | Classe | Attore (D-8) |
| --- | --- | --- |
| `automations_attivo`, `automations_audit_update`, `automations_storico`, `automations_storico_provision`, `automations_tx_id`, `automations_overlap`, `automations_cleanup_weekly`, `automations_apply_fk_indexes_policy`, `apply_storicizza_weekly`, `sync_storico_set_storicizza` | MANUTENZIONE | il nome |
| `sync_auth_user_expired_daily` | AMMINISTRAZIONE | il nome |
| `chiusura_scadenze_daily` | **DOMINIO** (entrambi i bersagli; classe per bersaglio, D-10) — §8.2 | utente tecnico |

⇒ Dieci su dodici sono manutenzione pura: hanno bisogno di un attore, non di un
perimetro. È ciò che rende il cantiere piccolo.

### 8.2 ✅ D-5 — `chiusura_scadenze_daily` è di dominio ed esce da pgAgent

È l'unico job pgAgent che cambia lo **stato gestionale** di righe applicative, ogni
notte alle 00:05, senza attore, con `user_update = CURRENT_USER`. Per D-10 la classe sta
sulla riga di `dbops.automazione_chiusura_scadenze`, e oggi entrambe sono di dominio:

| Bersaglio | Percorso verso l'emittente | Difese oggi |
| --- | --- | --- |
| `vendite.contratti` (ATTIVO → CESSATO) | colonna diretta | ✅ `rls_contratti_ef_whitelist` |
| `vendite.listini_versioni` (ATTIVA → CHIUSA) | `listino_id → listini.emittente_soggetto_ruolo_id` (`NOT NULL`) | ⛔ **nessuna policy, nessun guard** su `listini*` |

⇒ Il job **migra intero**: diventa un lavoro di coda `OPERATORE`, un emittente alla
volta, con l'utente tecnico. `fn_apply_chiusura_scadenze` lavora **solo i bersagli
della classe con cui viene chiamata**, e il cancello sta **dentro la funzione**, non
nell'elenco dei job: una riga nuova nel CSV deve dichiarare la propria classe o non
viene lavorata.

⚠️ **Il listino è il primo caso del secondo livello del presidio** (§13): ha il
percorso, non ha la policy. Finché è così, su di lui il Caso A del §13.1 (*«si ferma da
solo»*) **non vale**: un filtro dimenticato passerebbe. È un debito da far calare, non
un blocco di questo brief.

⚠️ Con questo, **D-5 è chiusa per conseguenza di D-8 e D-10**: i dieci di manutenzione
restano tecnici con il nome come attore; `chiusura_scadenze` migra sulla coda.

### 8.3 I management command

| Comando | Canale oggi | Registrato? | Classe |
| --- | --- | --- | --- |
| `run_fatturazione_batch` | sistema (BYPASSRLS) | ✅ con lock | DOMINIO |
| `draina_coda_stampa` | sistema (BYPASSRLS) | ✅ con lock | DOMINIO |
| `draina_coda_lavori` | ruolo web; sistema per item `SISTEMA` | ✅ senza lock | infrastruttura (§7-F) |
| ⛔ `send_pending_emails` | ruolo web, nessuna identità | ⛔ no | **DOMINIO** — ⚠️ e la sua tabella `config.email_outbox` **non porta l'emittente**: è il Caso B del §13.1, in casa |
| ⛔ `sync_auth_user_active` | ruolo web, nessuna identità | ⛔ no | AMMINISTRAZIONE |
| ⛔ `listen_cambio_reparto` | ruolo web, nessuna identità | ⛔ no | AMMINISTRAZIONE |

(`copertura_doc_api` e `genera_error_policies` sono strumenti di sviluppo.)

---

## 9. Le decisioni

| # | Decisione | Stato |
| --- | --- | --- |
| **D-0** | **Il registro dei processi**: codice, classe (per bersaglio dove il perimetro è configurazione, D-10), canale, attore = codice; parte catalogo e parte macchina separate (§6.2); criterio di disegno in §2.4 e §13.1 | 🔵 **aperta — da progettare**, vincoli completi |
| **D-1** | Tutti i processi di dominio iterano per emittente, **senza eccezioni**. La ragione è l'isolamento (§10), non il perimetro | ✅ chiusa 04-09 |
| **D-2** | **(a)** il comando **accoda N lavori**, uno per emittente; **(b)** il **`BYPASSRLS` applicativo sparisce**; **(c)** più emittenti girano **insieme**. Conseguenze in §10 | ✅ chiusa 04-09 |
| **D-3** | L'attore su `job_run_log`: **il codice del processo** (D-8), in **entrambe** le funzioni, colonna facoltativa finché la vista di presidio non è vuota, poi `NOT NULL`. ⚠️ Resta da decidere se accanto al codice si registra anche l'`auth_user_id` quando c'è | 🔵 quasi chiusa |
| **D-4** | La porta di `trgfn_guard_emittente_scope` si chiude **rispecchiando il bypass della RLS**: chi bypasserebbe la policy (proprietario, superuser) salta il guard; un processo applicativo senza utente si ferma (§4.1). Quando: passo 7, per conseguenza | ✅ chiusa 04-09 |
| **D-5** | I 12 job pgAgent: dieci restano tecnici con il nome; `sync_auth_user_expired` idem; `chiusura_scadenze_daily` è di dominio e **migra intero sulla coda** (§8.2) | ✅ chiusa per conseguenza di D-8 + D-10 |
| **D-6** | Un utente tecnico **per processo**, **flag** dichiarato, **soggetto «sistema»** dedicato, profilo **puntato** al reparto; ⛔ né per emittente, né alias, né super admin | ✅ chiusa 04-09 |
| **D-7** | Il vincolo `run_as` per tipo di coda | ✅ assorbita dal passo 6 (§10.2) |
| **D-8** | **L'attore è sempre un nome**; l'utente tecnico c'è in più solo per il DOMINIO (§2.3) | ✅ chiusa 04-09 |
| **D-9** | L'emittente nuovo lo aggiunge **una persona**; il sistema **segnala** il mancante (§6.4) | ✅ chiusa 04-09 |
| **D-10** | Nei framework guidati da configurazione la classe sta **sul bersaglio** (§2.5) | ✅ chiusa 04-09 |

---

## 10. La fatturazione: come si costruisce il giro

Il batch oggi gira **una volta**, attraversa tutti gli emittenti, con un ruolo che
bypassa la RLS. Con D-1 e D-2 diventa un **produttore di lavori**.

| | Oggi | Dopo |
| --- | --- | --- |
| corse | 1 | N lavori in coda, uno per emittente, in parallelo |
| perimetro | ⛔ nessuno | ✅ quello dell'emittente, catturato all'enqueue |
| chi ha fatto | `app.jwt_user` solo nelle righe | ✅ codice del processo nel run **e** utente tecnico nelle righe |
| se un emittente fallisce | ⚠️ può fermare la corsa di tutti | ⭐ fallisce da solo, ritenta con backoff |

⭐ Il mattone «un giro per un emittente solo» **esiste già**: è `--emittente-id` del
comando. Quello che mancava era chi lo chiama N volte e con quale identità — ed è la
coda, che ha già ritentativi, backoff, isolamento per riga e scope.

### 10.1 ⛔ La sola cosa da disegnare bene: la chiave di idempotenza

Emittenti diversi non si incontrano (commesse e registri di numerazione sono separati a
monte; e `fn_get_next_progressivo` serializza comunque con `FOR UPDATE` sul registro).
Le due corsie dello stesso emittente si sovrappongono **già oggi** (il lucchetto è per
corsia). ⇒ Il parallelismo non apre buchi nuovi. Resta **una** cosa:

| Chiave di idempotenza | Effetto |
| --- | --- |
| assente | ⛔ due cron ravvicinati accodano due volte lo stesso emittente → doppio lotto |
| troppo grossa (solo `job_type`) | ⛔ **silenzioso**: il secondo emittente sembra un doppione del primo e viene scartato → emittenti **mai fatturati**, senza errore |
| ⭐ `emittente + corsia + competenza` | un solo giro vivo per terna; gli altri passano |

Il lucchetto anti-sovrapposizione si sposta dal **lavoro** all'**accodamento**.

### 10.2 🔴 `run_as` cambia significato, e con lui un `CHECK`

`SISTEMA` oggi **è** il bypass. Togliendolo, resta senza canale; e con D-8 anche un
processo di manutenzione ha un attore. ⇒ `run_as` smette di significare *«con o senza
bypass»* e significa **«con o senza emittente»**:

| Valore | Dopo |
| --- | --- |
| `SISTEMA` | attore = codice del processo, **nessun emittente** (manutenzione, amministrazione) |
| `OPERATORE` | identità + emittente — invariato |

⚠️ **[corretto in sede di progetto] I punti sono QUATTRO, e il `CHECK` non è fra
questi.** `chk_coda_lavori_run_as_scope` dice *«`OPERATORE` ⇒ scope non nullo; `SISTEMA`
⇒ scope nullo»*: dopo la ridefinizione un job `SISTEMA` continua a non avere emittente,
quindi continua ad avere `scope` nullo. La condizione è **già quella giusta** — cambia
il significato di `SISTEMA`, non la sua forma. Restano: il **commento** della colonna
(che cita il canale `BYPASSRLS`), `fn_accoda_lavoro`, il legame tipo→processo (⇒ chiude
anche §7-A) e `drainer_service._dispatch_item`. Dettaglio nel brief DB §5.1.

### 10.3 ⚠️ «Il bypass sparisce» ha un perimetro preciso

pgAgent gira come superuser e Liquibase come `titodb`, il proprietario: bypassano per
superuser e per proprietà, e devono (fanno DDL). La frase corretta è **«nessun processo
*applicativo* bypassa»**. ⭐ Verificato: `zeroerp_app` **non** è il proprietario, quindi
la RLS su di lui è già efficace senza `FORCE ROW LEVEL SECURITY` — togliere il ruolo
chiude davvero il buco.

### 10.4 ⭐ Il vincolo «mai in thread» decade con il bypass

I lavori `OPERATORE` usano `operator_identity_context`, che tocca solo le variabili di
sessione della propria connessione, non `system_process_context`. E il claim
(`FOR UPDATE SKIP LOCKED`) dà N worker paralleli senza coordinamento. ⇒ Le tre
decisioni di D-2 rendono il parallelismo **sicuro per costruzione**. Il §7-D resta vero
finché il canale esiste, e decade il giorno in cui viene ritirato.

---

## 11. Magazzino e acquisti nascono con la dichiarazione, prima della RLS

Sono **in ristrutturazione**: questo brief non li misura e non li progetta. Quello che
dà loro è l'ordine giusto delle cose: si **dichiara** che un processo è di dominio (D-0)
⇒ il presidio pretende che le sue tabelle portino l'emittente ⇒ la RLS arriva come
conseguenza del progetto, non come cerotto dopo.

⚠️ Vincolo ereditato dall'analisi carico e scarico: `valore_giacenza` è una copia
ricostruibile, e il ricalcolo scrive alla grana **articolo × magazzino**. Un aggregato
«per articolo» dentro un batch romperebbe il confine in silenzio. ⛔ Che quella grana
porti l'emittente è un'affermazione **dell'altro documento**, e lì va verificata.

⛔ «Nasce conforme» ha due prerequisiti: il **registro** (passo 0) e l'**utente
tecnico** (passo 2). Senza, il job di magazzino nasce conforme a un elenco che nessuno
rilegge.

---

## 12. L'ordine in cui conviene procedere

| # | Passo | Perché prima di quello dopo |
| --- | --- | --- |
| **0** ⭐ | **Il registro dei processi** (D-0) | senza, la classe è prosa e nessun presidio esiste. È anche la colonna che serve al passo 6 |
| **1** | **L'attore sul registro dei run** (D-3): codice del processo, entrambe le funzioni, colonna facoltativa | indipendente e utile da subito, anche ai dieci job di manutenzione |
| **2** | **Gli utenti tecnici** dei processi di dominio (§6.2), con le due trappole di §6.3 chiuse nello stesso passo | prerequisito per smettere di bypassare |
| **3** | I **tre comandi orfani** entrano in `registered_job` (§5.2) | costo quasi nullo; senza, i presidi nascono ciechi |
| **4** | ⭐ **Primo caso di dominio: `draina_coda_stampa`** — ogni item è una fattura di un emittente, il worker ha già il motore di coda, usa il bypass e contiene il guard da riscrivere (§5.1). È la fatturazione **in piccolo, sullo stesso binario** | ci si misura il meccanismo prima del caso grande. ⚠️ `chiusura_scadenze` **non** lo è: gira in pgAgent e ha un bersaglio senza emittente (§8.2) |
| **5** | **La fatturazione** diventa un produttore di lavori (D-2/a), con la chiave `emittente + corsia + competenza` (§10.1) | il caso grande, quando il binario ha già girato |
| **5-bis** | **`chiusura_scadenze`** migra intero sulla coda (§8.2), con la classe per bersaglio dentro `fn_apply_chiusura_scadenze` | stesso binario del passo 5 |
| **6** | **Ridefinizione di `run_as`** (§10.2): i cinque punti insieme | o la coda resta incoerente a metà |
| **6-bis** | ⛔ **Ritiro del ruolo `BYPASSRLS` applicativo** e del canale; riscrittura di `_guard_canale_sistema` (§5.1) | finché un processo lo usa, toglierlo lo ferma. Da qui il §7-D decade |
| **7** | ⛔ **Chiudere la porta** di `trgfn_guard_emittente_scope` rispecchiando il bypass della RLS (D-4, §4.1) | ultimo: prima fermerebbe i job. ⚠️ Con un pgTAP che **costruisce** i tre casi: proprietario passa, operatore fuori perimetro si ferma, sessione applicativa senza utente si ferma |

---

## 13. I presidi

Lo stampo è quello delle viste `dbops` che **devono restare vuote**
(`vw_riferimenti_morti_da_sanare`, `vw_codici_errore_da_dichiarare`,
`vw_operatori_senza_emittente`, `vw_liste_multi_emittente_non_certificate`…).

| Vista | Che cosa elenca | Dipende da |
| --- | --- | --- |
| *processi non dichiarati* | job comparsi su `job_run_log` che non stanno nel registro | passo 0 |
| *dominio senza emittente* — **livello 1** | processi (o bersagli, D-10) dichiarati DOMINIO che scrivono dove **non c'è percorso** verso un emittente, padri compresi — prende l'omissione **prima** che il processo giri (§2.4) ⇒ deve restare vuota | passo 0 |
| *dominio senza difesa* — **livello 2** | bersagli DOMINIO con il percorso ma **senza policy RLS né guard**: lì il Caso A del §13.1 non vale ⇒ è un **debito**, deve calare. Prima riga oggi: `vendite.listini*` (§8.2) | passo 0 |
| *flag e registro in disaccordo* | **solo per il DOMINIO** (D-8): identità col flag senza processo, e processi DOMINIO senza identità col flag | passo 0 + 2 |
| *emittente non servito* | emittente attivo assente dalla whitelist di un processo DOMINIO (D-9) — copre il «FATTO, 0 elaborate» silenzioso | passo 2 |
| *run senza attore* | righe di `job_run_log` senza codice del processo | passo 1 |
| *processi che bypassano* | ruoli applicativi con `BYPASSRLS` fuori dall'elenco dichiarato (oggi uno: `zeroerp_batch_fatturazione`; a regime: **zero**) | costruibile subito |

⚠️ La prima è la condizione delle altre: senza registro, una vista su `job_run_log`
può solo dire «le righe arrivate non hanno attore», non «un processo è girato e non si
è registrato».

⚠️ E finché il passo 7 non è fatto, la porta del §4 **resta aperta e va registrata
come tale**: la decisione è presa (§4.1), la chiusura arriva per ultima.

### 13.1 ⭐⭐ Che cosa un presidio può fare, e che cosa no

**Tid:** *«un lavoro batch sarebbe in grado di bloccare un processo impostato male a
monte? Io non credo»*. **Ha ragione**: un meccanismo a runtime non può far rispettare
una distinzione che **nei dati non esiste**. Ma «progettato male» sono due cose:

* **Caso A — la separazione c'è nel modello, il processo si dimentica di usarla**
  (la tabella porta l'emittente, la policy c'è, la query dimentica il filtro).
  ✅ **Si ferma da solo**: le righe degli altri emittenti non ci sono; in scrittura il
  guard solleva. È ciò che D-2/b rende vero, ed è la forma più comune di errore reale.
* **Caso B — la separazione nel modello non c'è** (la tabella non sa a chi appartiene).
  ⛔ **A runtime non c'è niente da fare.** Si prende **prima**: il processo dichiara la
  classe (D-0) e la vista *dominio senza emittente* confronta la dichiarazione con la
  struttura. L'omissione diventa una riga rossa **mentre si progetta**.

⚠️ **Il limite, dichiarato come lo dichiara il precedente
`vw_liste_multi_emittente_non_certificate`**: prova che la struttura c'è, non che il
codice la usi bene; e non prende il verso «dovrebbe essere DOMINIO ma è dichiarato
manutenzione» (§2.4). Quel residuo lo coprono un pgTAP sul caso specifico e una persona
che legge il registro.

⚠️ **E «zero righe» non è un allarme.** Togliere il bypass trasforma un danno
silenzioso in un *niente* silenzioso: molto meglio, ma «non è successo niente» lo nota
solo chi si aspettava qualcosa. Per questo esistono la vista *emittente non servito*
(D-9) e il confronto fra lavoro atteso e lavoro fatto — non il fail-closed da solo.

---

## 14. Che cosa NON è di questo brief

* **che cosa fanno** i processi: qui si decide *chi* li esegue e *dentro quale
  perimetro*;
* **la coda in sé** — è il modello; resta di questo brief solo ciò che riguarda
  l'identità (§10.2);
* **magazzino e acquisti** — in ristrutturazione, con i loro documenti;
* **i permessi degli operatori umani**: la whitelist emittenti non si tocca;
* la **colonna emittente su `config.email_outbox`** (Caso B, §8.3): è un cantiere suo,
  che questo brief **nomina** e non progetta.

---

## 15. Riferimenti

* [analisi-db-magazzino-carico-e-scarico.md](analisi-db-magazzino-carico-e-scarico.md)
  — §7-sexies e §7-ter: da dove nasce la richiesta, e il vincolo sul ricalcolo
* Building block dei processi headless: `apps/core/services/system_context.py`,
  `apps/core/services/job_run.py` — e la loro scheda nel catalogo backend
* `apps/core/services/coda_lavori/` — `drainer_service.py`, `context.py`,
  `repository.py`: il modello già in esercizio
* `apps/documenti/services/document_generation_service.py` — `_guard_canale_sistema`,
  da riscrivere al passo 6-bis
* `dbops.coda_lavori`, `dbops.coda_lavori_tipi`, `dbops.fn_accoda_lavoro`
* `script.trgfn_guard_emittente_scope` — ⛔ la porta vera (§4)
* `script.fn_check_user_emittente_scope` — la canonica dello scope
* `maintenance.fn_run_and_log`, `script.fn_job_run_start` / `fn_job_run_end` — i due
  canali del registro dei run
* `dbops.automazione_chiusura_scadenze` + `dbops.fn_apply_chiusura_scadenze` — il
  framework a classe per bersaglio (§8.2)
* `dbops.vw_liste_multi_emittente_non_certificate` — lo stampo del presidio «dichiarato
  ma non esposto»

---

## 16. Storia delle revisioni

Tutte del 2026-09-04. Ogni riga: che cosa diceva la stesura precedente → che cosa è
stato verificato.

| Diceva | Verificato |
| --- | --- |
| «lo usano 17 file» (canale di sistema) | i call-site reali sono **3**; 17 era la conta grep con test e commenti |
| «9 job pgAgent» | sono **12** vivi; `listini_versioni_close_scadute_daily` è cancellato dal 20260426-06 |
| «la porta è la regola 1 di `fn_check_user_emittente_scope`, attraversata dai job pgAgent» | i job pgAgent bypassano per ruolo; in lettura quel ramo è irraggiungibile (AND su `ruolo_applicativo`); la porta viva è in **scrittura**, in `trgfn_guard_emittente_scope` (§4) |
| «scadenze» fra i job tecnici | `chiusura_scadenze_daily` cambia lo stato di `vendite.contratti`, che ha la RLS: è **dominio** (per bersaglio, §8.2) |
| il `CHECK` della coda «impone che un job di dominio abbia un operatore» | impone la coerenza `run_as`↔`scope`; `p_run_as` sovrascrive il default (§3.1) |
| «la classe si deriva dalla presenza della RLS, verificabile dal catalogo» | riconosce una difesa, non la natura del dato; la classe è una **dichiarazione** verificata in un verso solo (§2.4) |
| `send_pending_emails` classificato AMMINISTRAZIONE | spedisce fatture ai clienti: **DOMINIO**, con tabella senza emittente (Caso B) |
| `chiusura_scadenze_daily` come «primo caso piccolo» | gira in pgAgent e ha un bersaglio senza emittente; il primo caso è `draina_coda_stampa` (§12) |
| «zero righe: si vede» (§13.1) | zero righe è silenzioso; serve il presidio *emittente non servito* (D-9) |
| il parallelismo «fa nascere» la sovrapposizione fra corsie dello stesso emittente | già possibile oggi (lucchetto per corsia); la novità è stessa corsia, emittenti diversi, ed è sicura (§10.1) |
| «misurare il costo prima di generalizzare» | con D-1 senza eccezioni la misura non può decidere nulla: **tolta** |
| numeri su RLS in `magazzino`/`acquisti` | cantieri in ristrutturazione: **non si misurano** (§1, §11) |
| la ridefinizione di `run_as` «tocca cinque punti, fra cui il `CHECK`» | il `CHECK` **resta valido**: `SISTEMA` continua a non avere emittente ⇒ `scope` nullo. I punti sono **quattro**, e uno solo non è DB (§10.2, brief DB §5.1) |
| `listini_versioni` classificato AMMINISTRAZIONE «perché non porta l'emittente» (Tid, rileggendo: *«il listino andrebbe legato all'emittente»*) | **lo è già**: `vendite.listini.emittente_soggetto_ruolo_id NOT NULL`, e la versione lo raggiunge via `listino_id`. È **DOMINIO**; `chiusura_scadenze` migra intero (§8.2). ⚠️ Stesso errore di `send_pending_emails`: giudicare la colonna della figlia invece di seguire il percorso (§2.4). E il listino non ha policy né guard: primo caso del livello 2 del presidio (§13) |
