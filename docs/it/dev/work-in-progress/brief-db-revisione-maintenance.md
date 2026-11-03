# Brief DB — Revisione dello schema `maintenance`: i difetti di codice e i metadati

## ⏭️ Chi riparte — aggiornato al 2026-11-03

**Riparte: Tid**, col via allo sviluppo. Le decisioni sono prese (§4, Tid 2026-11-03): il lavoro è
tutto del team DB, e parte quando Tid lo dice.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ sessione DB | Revisione delle pagine `maintenance/manual/` allo standard, doc fuori schema corretta | — | — |
| 2 | ✅ Tid | Le decisioni D4, D5, D7, D8, D9, D10 | §4 | 1 |
| 3 | **Tid** ⏭️ | Il via allo sviluppo | — | 2 |
| 4 | team DB | D1, D2, D3, D6: changeSet nuovi, pgTAP, scheda `manual/` aggiornata | §2 | 3 |
| 5 | team DB | D4, D5, D7, D8, D9, D10 come decisi | §2, §4 | 3 |
| 6 | team DB | I metadati: COMMENT, CSV, descrizioni pgAgent, intestazioni pgTAP | §3 | 3 |
| 7 | team DB | Le due verifiche aperte | §5 | 3 |
| 8 | team BE/FE | Niente: nessuna ricaduta (§6) | — | — |

**Decisioni aperte di Tid:** nessuna. **Da committare:** le pagine `manual/` riscritte, la doc
corretta e questo brief, della sessione del 2026-11-03.

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-11-03. **A chi:** team DB e Tid.
> **Origine:** verifica delle 24 pagine `docs/it/dbzero/maintenance/manual/` contro lo standard e contro
> il modello, chiesta da Tid. Le pagine sono state riscritte e ne sono nate 5 nuove; nel confronto col
> codice sono emersi i difetti qui sotto. Tid, 2026-11-03: un brief per i difetti di codice e i
> metadati, la doc fuori schema corretta subito.
> **Brief vicini verificati:**
> [framework-automazione-db-migliorie](framework-automazione-db-migliorie.md) tocca gli stessi runner
> delle automazioni (D3, D4, D6), ma su temi diversi: recupero da esecuzione parziale, naming,
> conflitto fra trigger manuali e generati. Nessuno dei punti di questo brief vi compare. Nessun altro
> brief aperto tocca `fn_run_and_log`, le `proc_bump_*`, il giornale dei job o la storicizzazione.

⚠️ Il DDL e il corpo di ogni oggetto si prendono dalla doc auto-generata
(`docs/it/dbzero/<schema>/funzioni/…`), non dagli YAML citati qui: i riferimenti `file:riga` servono a
trovare il punto, non a ripartire da lì.

## 1. Il perimetro

Sono i difetti del **codice** e dei **metadati** dello schema `maintenance` e dei runner che le sue
procedure chiamano. La documentazione è già allineata: le pagine `manual/` descrivono il
comportamento di oggi, difetti compresi, e vanno aggiornate quando un difetto si chiude.

## 2. I difetti di codice

Per ogni difetto: il fatto, perché il modello non lo ammette, la correzione proposta e il presidio.
✔︎ = ricontrollato sul codice dalla sessione che scrive.

### D1 ✔︎ — `proc_bump_toponomastica` accende il flag e non lo spegne mai

* **Fatto.** `20_code/maintenance/20260102-06-proc-bump-toponomastica-mctit.yaml:36`:
  `set_config('zeroerp.maintenance_toponomastica', 'on', true)` e nessuna riga lo rimette a `off`. Il
  commento (riga 35) e il `comment:` (righe 17-19) dicono «per la sessione corrente», ma il terzo
  argomento `true` lo lega alla transazione.
* **Perché è un difetto.** Il flag è una porta che deve restare aperta solo per la scrittura della
  procedura. Dentro una transazione più grande, ogni UPDATE successivo su `config.toponomastica` passa
  senza `trgfn_toponomastica_protect_update`. La gemella `proc_bump_indirizzi_dettaglio` ha già la
  forma giusta: spegne il flag prima di uscire, anche in caso di errore.
* **Correzione.** Stessa forma della gemella: flag a `off` dopo l'UPDATE e nel gestore d'eccezione,
  con rilancio. COMMENT corretto («transazione», non «sessione»).
* **Presidio.** In `db/pgtap/config/test-toponomastica-stradario-generale.sql`: dopo la `CALL`, nella
  stessa transazione, un cambio a mano della descrizione di un toponimo in uso viene ancora rifiutato
  (`E_COLONNA_NON_MODIFICABILE`). È lo stesso test che la gemella ha già.

### D2 ✔︎ — `fn_run_and_log`: il lock può restare preso

* **Fatto.** `20_code/maintenance/20261016-38-update-fn-run-and-log-sqlstate-e-codice-mctit.yaml`:
  `pg_try_advisory_lock(p_lock_key)` (riga 115) prende un lock **di sessione**. L'INSERT di apertura
  della corsa (riga 137) sta **fuori** dal blocco `BEGIN … EXCEPTION` (riga 143), che è l'unico punto
  in cui il lock si rilascia.
* **Perché è un difetto.** Se quell'INSERT fallisce — e il modello lo ammette: il CHECK
  `chk_job_run_log_processo_dichiarato` e la FK `fk_job_run_log_processi` possono respingerla — la
  funzione esce con l'errore e il lock resta preso per tutta la vita della connessione. Le corse
  successive dello stesso job sulla stessa connessione risultano tutte «saltate».
* **Correzione.** Rilascio garantito su ogni uscita dopo l'acquisizione: l'INSERT di apertura entra in
  un blocco con gestore che rilascia il lock e rilancia. In alternativa si può prendere il lock *dopo*
  l'INSERT, ma così la riga di una corsa saltata cambierebbe forma: da valutare.
* **Presidio.** pgTAP: con un `p_jobname` senza processo e un `p_lock_key`, la chiamata fallisce
  (23514) e subito dopo `pg_try_advisory_lock` sulla stessa chiave riesce.

### D3 ✔︎ — `fn_run_automations_storico` cerca una funzione ritirata

* **Fatto.** `20_code/dbops/20261016-48-update-fn-run-automations-storico-ambiente-rilancia-mctit.yaml:172,174`:
  il controllo di esistenza per funzione cerca `script.trgfn_upd_dlt_storico_generic`. La funzione viva
  è `script.trgfn_storico_generic`.
* **Perché è un difetto.** Con la strategia `BY_FUNCTION` il trigger non viene mai riconosciuto come
  presente (il runner lo ricrea a ogni giro); con `BOTH` il ramo per funzione è inerte e decide solo il
  nome.
* **Correzione.** Il nome vivo nei due punti. Il censimento si fa per significato: grep di
  `trgfn_upd_dlt_storico_generic` su `db/changelog/migrations_v2/20_code` e `90_end`, perché altri
  lettori con lo stesso nome ritirato avrebbero lo stesso difetto.
* **Presidio.** pgTAP del runner storico con `exist_strat = 'BY_FUNCTION'` su una tabella che ha già il
  trigger: nessuna azione `CREA`.

### D4 ✔︎ — `proc_automations_cleanup_job` pulisce solo lo schema `dbops`

* **Fatto.** `20_code/maintenance/20260207-12-proc-automations-cleanup-job-mctit.yaml:28` passa
  `ARRAY['dbops']`. Le regole `CLEANUP_AT` del seed su `vendite.*` e `config.*`
  (`automation_rules_tbl.csv`) e la `CLEANUP_PURGE` su tutto non le esegue né il giro della domenica né
  la convergenza in CI, e non c'è un altro chiamante.
* **Perché è un difetto.** Una regola dichiarata nel registro che nessuno esegue è una promessa senza
  esecutore: le righe scadute di quelle tabelle non vengono mai cancellate.
* **Decisione** (Tid, 2026-11-03): il job **legge l'ambito dal registro**. Una regola attiva ha un
  esecutore, o non sta nel registro. ⚠️ Prima si verifica che `dbops.fn_run_automations_cleanup`
  ammetta «tutti gli schemi» (ambito NULL o vuoto) e che cosa fa con la `CLEANUP_PURGE` su `*all`.
* **Presidio.** Qualunque sia la scelta: un pgTAP o un presidio che non lasci una regola `CLEANUP_*`
  attiva fuori dall'ambito di ogni chiamante.

### D5 — Una corsa con errori interni risulta verde

* **Fatto.** `maintenance.fn_run_and_log` fa `EXECUTE p_sql` e scarta il risultato: scrive solo
  `rows_affected` = ROW_COUNT e `message = 'done'`. `dbops.fn_accoda_chiusura_scadenze` dichiara il
  contrario: «un riepilogo finisce nel giornale mentre un'eccezione si perde»
  (`20_code/dbops/20261009-46-update-oggi-dal-fuso-aziendale-dbops-mctit.yaml:210` e `:1315`).
* **Perché è un difetto.** Una corsa in cui un'azienda fallisce (`_falliti > 0`) risulta verde in
  `vw_job_run_da_guardare`: il presidio tace proprio quando serve. Vale anche, meno grave, per l'esito
  testuale di `fn_guardiano_digest` e per il conteggio di `fn_sync_auth_user_expired`.
* **Decisione** (Tid, 2026-11-03): l'esito **si porta nel giornale**, senza sollevare. Sollevare
  annullerebbe anche il lavoro delle aziende riuscite, che è proprio ciò che l'isolamento per azienda
  protegge. Nasce un contratto «riuscita con scarti»: `fn_run_and_log` registra in `message` il valore
  restituito da `p_sql` e rende la riga rossa **senza** annullare il lavoro. Da fissare nel disegno: se
  «rossa» è `ok = false` con un `error_code` dedicato o uno stato a parte, e come lo legge
  `vw_job_run_da_guardare`. Si applica a `fn_accoda_chiusura_scadenze`, `fn_guardiano_digest`,
  `fn_sync_auth_user_expired`.

### D6 — Overlap: una tabella sparita ferma tutta la corsa

* **Fatto.** `20_code/dbops/20260602-09-update-fn-apply-automazione-overlap-key-expressions-mctit.yaml:81`
  usa `::regclass` senza `to_regclass`.
* **Perché è un difetto.** Una riga di `dbops.automazione_overlap` che punta a una tabella non più
  esistente solleva 42P01 e ferma il giro intero, con lo SQLSTATE grezzo: le altre tabelle restano
  senza vincolo. Il modello ammette quel caso (il registro non ha FK verso il catalogo).
* **Correzione.** `to_regclass` e una riga di esito `SKIP` con motivo, come fanno gli altri runner.
* **Presidio.** pgTAP: una riga del registro su una tabella inesistente non impedisce il vincolo su
  un'altra.

### D7 — Sync e apply della storicizzazione girano in ordine opposto fra CI e pgAgent

* **Fatto.** In CI la convergenza chiama prima il sync (`ci_ordine` 100) e poi l'apply (110), e
  `db/pgtap/dbops/test-processi-convergenza-ci.sql:89` lo pretende. Su pgAgent l'apply parte il sabato
  alle 07:00 e il sync alle 07:05.
* **Perché è un difetto.** Su pgAgent l'apply lavora sempre sull'insieme che il sync ha preparato la
  settimana prima: una tabella nuova riceve il DEFAULT con una settimana di ritardo.
* **Decisione** (Tid, 2026-11-03): **si inverte il calendario pgAgent**: sync il sabato alle 07:00,
  apply alle 07:05. L'ordine è uno solo, quello già dichiarato e presidiato dalla convergenza.
  ChangeSet nuovo in `85_pgagent` per i due job (insieme a M1 e M2).

### D8 — Il flag di `proc_bump_indirizzi_dettaglio` non serve, e manca il verbo che servirebbe

* **Fatto.** L'UPDATE della procedura è `SET stradario_id = stradario_id`
  (`20_code/maintenance/20260806-20-…yaml:96`). Il guard
  (`20_code/anagrafiche/20260102-03-guard-indirizzi-dettaglio-mctit.yaml:34`) blocca solo se
  `NEW.stradario_id IS DISTINCT FROM OLD.stradario_id`: passerebbe anche a flag spento.
* **Perché è un difetto.** Il flag apre una porta che la procedura non attraversa. Il passo che la
  guida *Riclassificazione vie* descrive — puntare gli indirizzi a una via nuova — non ha una
  procedura: il guard lo blocca e nessun verbo lo fa.
* **Decisione** (Tid, 2026-11-03): **si toglie il flag dalla procedura**; il verbo di
  riclassificazione **non si costruisce ora**, nasce quando servirà davvero. Il guard continua a
  riconoscere il flag, pronto per quel verbo. La guida *Riclassificazione vie* dichiara già il limite
  («il passo 2 oggi non ha una procedura»).

### D9 — Cambiare un toponimo non aggiorna gli indirizzi di dettaglio

* **Fatto.** `proc_bump_toponomastica` rinormalizza solo `config.stradario_generale`. `via_norm` e
  `indirizzo_normalizzato` di `anagrafiche.indirizzi_dettaglio` si calcolano solo quando la riga viene
  scritta (`fn_build_indirizzo_normalizzato` legge il toponimo da `vw_indirizzo_completo`).
* **Perché è un difetto.** Dopo la correzione di un toponimo, gli indirizzi su quelle vie restano con
  la descrizione vecchia: non c'è una cascata e non c'è un presidio che lo segnali.
* **Decisione** (Tid, 2026-11-03): **cascata**. La procedura è il gesto di manutenzione e lo
  completa: per ogni via di `config.stradario_generale` toccata chiama
  `proc_bump_indirizzi_dettaglio`, nella stessa transazione. Il pgTAP prova che, corretto un toponimo,
  l'`indirizzo_normalizzato` di un indirizzo di dettaglio su quella via contiene la descrizione nuova.

### D10 — Un fallimento può essere contato due volte

* **Fatto.** Se il chiamante di `fn_run_and_log` cattura l'eccezione, restano due righe rosse con lo
  stesso `run_uuid`: quella aggiornata in transazione e quella scritta fuori transazione da
  `fn_job_run_log_failure`. Non c'è un vincolo unico su `run_uuid`. Il COMMENT dice il contrario: «o
  l'una o l'altra, mai due» (`20261016-38-…:234`).
* **Perché è un difetto.** `falliti_ultimi_7_giorni` di `vw_job_run_da_guardare` conta quel
  fallimento due volte.
* **Decisione** (Tid, 2026-11-03): **le viste contano per corsa distinta** (`run_uuid`). ⛔ Niente
  vincolo unico: il verbale fuori transazione nasce via dblink mentre la riga in transazione non è
  ancora committata, e con un indice unico la seconda connessione **aspetterebbe la transazione che la
  sta chiamando**: la corsa si bloccherebbe invece di fallire. Si censiscono i lettori di
  `job_run_log` che contano righe rosse (almeno `vw_job_run_da_guardare`, `vw_job_run_da_superuser`)
  e si corregge il COMMENT (M7).

## 3. I metadati

Nessuno cambia il comportamento, ma ognuno dice una cosa falsa a chi legge.

| # | Dove | Che cosa |
| --- | --- | --- |
| M1 | `85_pgagent/20250811-02-create-pgagent-job-sync_storico_set_storicizza-weekly-mctit.yml:59,86` | Descrizione del job sync e nome dello step copiati dall'apply («Setta DEFAULT=true…», `run_apply_storicizza`) |
| M2 | step pgAgent e `p_stepname` | Lo stesso step ha due nomi: apply `run_apply_storicizza` / `run_proc_apply_storicizza`, sync `run_apply_storicizza` / `run_sync_storico_set_storicizza` |
| M3 | `80_data/sql/dbops/processi.csv` | `automations_cleanup` (riga 8) descritto come «pulizia degli oggetti generati», ma cancella righe scadute; `automations_attivo` (riga 2) «propaga la colonna attivo», ma crea i trigger di blocco e di requisito; il sync (riga 11) «tabelle shadow», ma allinea `config.storico_set_storicizza`; la `ci_esclusione` della fk policy (riga 9) «la stessa chiamata», ma il job fa anche il populate; `guardiano_digest` (riga 25) «compone il digest», ma lo guarda; `analyze_statistiche` (riga 29) ha nome di brief e id di changeSet nella descrizione |
| M4 | `80_data/sql/config/codici_errore.csv:1082`, `messaggi_errore.csv:1080` | Il rimedio di `E_STATISTICHE_MANCANTI` è ancora «`pg_maintain` nel provisioning»; oggi è la proprietà al migratore |
| M5 | `85_pgagent/20261014-53-create-pgagent-job-analyze-statistiche-mctit.yaml:26-31` | Il diritto «del ruolo con cui si collega pgAgent» e `pg_maintain` (la procedura è DEFINER, conta il proprietario); «lontano dal job delle 00:05 e delle 06:00», job che non esistono |
| M6 | `85_pgagent/20260302-04-create-pgagent-job-sync-auth-user-expired-daily-mctit.yaml:64` e corpo di `anagrafiche.fn_sync_auth_user_expired` | «Giornaliero ore 06:00», «batch notturno»: il job gira ogni ora al minuto 10 |
| M7 | COMMENT di `maintenance.fn_run_and_log` (`20261016-38-…:234`) | «Mai due righe» (falso, D10), «dodici job», marcatori `Rev …` e nomi di brief |
| M8 | COMMENT di `job_run_log.processo_codice` (`00_schema/maintenance/20260904-16-…:81-82`) | «Diventerà NOT NULL»: oggi la regola è un CHECK `NOT VALID` |
| M9 | COMMENT di `job_run_log.origine` (`00_schema/maintenance/20260618-01-…:59-62`) | «`PGAGENT` = job DB pgAgent»: è il default anche per le corse della convergenza CI e per quelle a mano. Da valutare se la colonna debba distinguerle |
| M10 | COMMENT di `vw_job_run_da_guardare` (`20_code/maintenance/20261018-02-…:205`) | «`dbops.processi` non ce l'ha» (la cadenza: `tolleranza_minuti` esiste); elenca le classi 08/53/57/58 superate |
| M11 | `80_data/sql/dbops/presidi.csv:34` | Classi 08/53/57/58 senza 42501 e 55P03; «in maintenance c'è questa sola vista» |
| M12 | COMMENT di `maintenance.fn_sveglia_accesa` | Fra i casi di `E_CONFIG_MANCANTE` manca la scelta a mano non ammessa |
| M13 | COMMENT di sync e apply della storicizzazione (`20_code/maintenance/20260905-28-…:150`, `20260905-29-…:148,154`) | Il riepilogo `RAISE NOTICE` «finisce nel log del server» (con `log_min_messages` di default non ci arriva); «un'eccezione cancellava anche il proprio verbale», superato dal verbale fuori transazione |
| M14 | Procedure senza COMMENT | `proc_automations_attivo_job`, `_audit_update_job`, `_storico_job`, `_storico_provision_job`, `_tx_id_job`. Il COMMENT di `proc_automations_lock_columns_job` ha ancora marcatori `Rev …` |
| M15 | `90_end/ci_apply/20260926-10-run-processi-strutturali-in-ordine-mctit.yaml:30` | Il commento dice che il salto scrive `ok = true`: oggi è `saltata = TRUE`, `ok` vuoto |
| M16 | Intestazioni pgTAP | `db/pgtap/maintenance/test-job-run-attore.sql:23,31-32` («resta senza attore», ma il test 8 prova il rifiuto 23514); `db/pgtap/maintenance/test-proc-job-definer-v1.sql:33-34` («zeroerp in CI», ma la CI migra come `zeroerp_owner`) |
| M17 | `maintenance.job_run_log.agent_host` (`20_code/maintenance/20261016-39-…:106`) | Il verbale fuori transazione scrive `cluster_name`, il default della colonna è `inet_client_addr()`: due significati nella stessa colonna |

⚠️ M1, M5 e M6 stanno in changeSet di `85_pgagent` già applicati: si correggono con un changeSet
nuovo, mai riscrivendo quello esistente.

## 4. Le decisioni di Tid — prese il 2026-11-03

Tid ha accolto le raccomandazioni della sessione DB. Il dettaglio sta nella sezione di ogni difetto.

| # | Domanda | Decisione |
| --- | --- | --- |
| D4 | Il cleanup su `dbops` soltanto è voluto? | No: l'ambito si legge dal registro |
| D5 | Come arriva al giornale un esito parziale? | `fn_run_and_log` registra il valore restituito e rende rossa la riga, senza annullare il lavoro |
| D7 | Ordine sync → apply anche su pgAgent? | Sì: calendario pgAgent invertito |
| D8 | Flag degli indirizzi di dettaglio | Si toglie dalla procedura; il verbo di riclassificazione non si costruisce ora |
| D9 | Toponimo corretto → indirizzi di dettaglio | Cascata da `proc_bump_toponomastica` |
| D10 | Fallimento contato due volte | Le viste contano per `run_uuid` distinto; niente vincolo unico |

## 5. Da verificare

* Su un'installazione nuova, il proprietario sotto cui gira `proc_sync_auth_user_expired_job`
  (`SECURITY DEFINER`) ha `UPDATE` su `django.auth_user`? Il provisioning
  (`scripts/sql/provision_zeroerp.sql`, whitelist `django`) parla di `zeroerp_app`.
* `docs/it/dev/work-done/brief-db-privilegio-app-job-run-log.md` §3.3 proponeva un pgTAP che blocchi il
  `SELECT = false` di `zeroerp_app` su `maintenance.test_pgagent_log`: non esiste.

## 6. Ricadute su BE e FE

Nessuna: tutti i punti stanno nel database. Se D5 cambia il contenuto di `message` nel giornale, il
pannello che legge `vw_job_run_da_guardare` lo mostra senza modifiche.

## 7. Alla chiusura

Ogni difetto chiuso aggiorna la sua pagina `docs/it/dbzero/maintenance/manual/` (o `dbops/manual/`),
che oggi descrive il comportamento difettoso: in particolare `proc_bump_toponomastica` (D1, D9),
`fn_run_and_log` (D2, D5, D10), `proc_automations_storico_job` (D3), `proc_automations_cleanup_job`
(D4), `proc_automations_overlap_job` (D6), `proc_apply_storicizza_defaults` e
`proc_sync_storico_set_storicizza` (D7), `proc_bump_indirizzi_dettaglio` (D8), e la guida
*Riclassificazione vie* (D8, D9).
