# Brief DB — Revisione dello schema `maintenance`: i difetti di codice e i metadati

## ⏭️ Chi riparte — aggiornato al 2026-11-03

**Brief chiuso**: tutti i giri applicati e verdi (Tid, 2026-11-03). Spostato in `work-done/` il 2026-11-03.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ sessione DB | Revisione delle pagine `maintenance/manual/` allo standard, doc fuori schema corretta | — | — |
| 2 | ✅ Tid | Le decisioni D4, D5, D7, D8, D9, D10 | §4 | 1 |
| 3 | ✅ sessione DB / Tid | Giro 1 (`-54 … -63`) applicato e verde | §8 | 2 |
| 4 | ✅ sessione DB / Tid | Giro 2 (`-64`, §5, doc) applicato e verde | §9 | 3 |
| 5 | ✅ Tid | Le decisioni M17, M9, D11 (2026-11-03) | §9.3 | 4 |
| 6 | ✅ sessione DB / Tid | Giro 3 (`-66`, `-67`, `-68`) applicato e verde, doc rigenerata | §10 | 5 |
| 7 | ✅ sessione DB | Giro 4: R1, R2 scritti; R3 chiuso senza modifiche | §11 | 6 |
| 8 | ✅ Tid | Apply di `-69`, `dbops/test-storico-nome-funzione-ritirato-v1` verde | §11 | 7 |
| 9 | ✅ Tid | Decisione su R4 e R5: come raccomandato (2026-11-03) | §11.4 | — |
| 10 | ✅ sessione DB | Giro 5: R4, R5; preCondition del `-66` corretta | §12 | 9 |
| 11 | ✅ Tid | Apply di `-70`, `-71`, i pgTAP di §12.2 verdi | §12 | 10 |
| 12 | ✅ sessione DB / Tid | Brief in `work-done/`; commit del lavoro del 2026-11-03 (Tid) | §7 | 11 |
| 13 | team BE/FE | Niente: nessuna ricaduta (§6) | — | — |

**Decisioni aperte di Tid:** nessuna. **Da committare:** tutto il lavoro del 2026-11-03 (lo fa Tid).

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-11-03. **A chi:** team DB e Tid.
> **Origine:** verifica delle 24 pagine `docs/it/dbzero/maintenance/manual/` contro lo standard e contro
> il modello, chiesta da Tid. Le pagine sono state riscritte e ne sono nate 5 nuove; nel confronto col
> codice sono emersi i difetti qui sotto. Tid, 2026-11-03: un brief per i difetti di codice e i
> metadati, la doc fuori schema corretta subito.
> **Brief vicini verificati:**
> [framework-automazione-db-migliorie](../work-in-progress/framework-automazione-db-migliorie.md) tocca gli stessi runner
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
  restituito da `p_sql` e rende la riga rossa **senza** annullare il lavoro. Fissato nel giro 1
  (§8.1): il valore va in `job_run_log.meta`, chiave `esito` (`message` resta breve), e «rossa» è
  `ok = false` con `error_code = E_JOB_ESITO_CON_SCARTI`, cioè una corsa fallita come le altre per
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

## 8. Giro 1 — 2026-11-03

### 8.1 Che cosa è stato scritto

| # | ChangeSet / file | Che cosa |
| --- | --- | --- |
| D8 | `20_code/maintenance/20261103-54-update-proc-bump-indirizzi-dettaglio-senza-flag` | Niente flag: l'aggiornamento è neutro |
| D1, D9 | `20_code/maintenance/20261103-55-update-proc-bump-toponomastica-spegne-flag-e-cascata` | Flag spento anche in errore; cascata via `proc_bump_indirizzi_dettaglio` per ogni via del toponimo |
| D2, D5, M7 | `20_code/maintenance/20261103-56-update-fn-run-and-log-lock-ed-esito` | Lock rilasciato se l'apertura fallisce; esito di una SELECT sola in `meta.esito`; `_falliti` > 0 → rossa con `E_JOB_ESITO_CON_SCARTI`, lavoro non annullato. CALL e stringhe con più istruzioni (lock_columns, fk policy) restano un `EXECUTE` semplice |
| D3 | `20_code/dbops/20261103-57-update-fn-run-automations-storico-funzione-viva` | Controllo per funzione su `script.trgfn_storico_generic` |
| D4 | `20_code/maintenance/20261103-58-update-proc-automations-cleanup-job-ambito-dal-registro` | Ambito NULL = registro. Non accorcia nessun log: con `apply_on_update` falso la scadenza si scrive solo dove manca, e la regola della tabella (priorità 190) precede la generica (200) |
| D6 | `20_code/dbops/20261103-59-update-fn-apply-automazione-overlap-tabella-sparita` | `to_regclass`, salto dichiarato `TABLE_NOT_FOUND` |
| D10, M10 | `20_code/maintenance/20261103-60-update-vw-job-run-da-guardare-corse-distinte` | `falliti_ultimi_7_giorni` conta i `run_uuid` distinti. Censimento: è l'unico conteggio di righe rosse fra i lettori di `job_run_log` |
| D7, M1, M2, M6 | `85_pgagent/20261103-61-update-pgagent-storicizza-sync-prima-dell-apply` | Sync sabato 07:00, apply 07:05; step pgAgent con lo stesso nome del giornale; descrizioni corrette |
| M8, M9 | `00_schema/maintenance/20261103-62-comment-job-run-log-processo-origine` | COMMENT di `processo_codice` e `origine` |
| M12–M14 | `20_code/maintenance/20261103-63-comment-procedure-maintenance-allineati` | COMMENT di `fn_sveglia_accesa`, sync/apply della storicizzazione, sei wrapper |
| D5 | `80_data/sql/config/codici_errore.csv`, `messaggi_errore.csv` (id 1432) | `E_JOB_ESITO_CON_SCARTI` |
| M3, M4, M11 | `80_data/sql/dbops/processi.csv`, `presidi.csv`, riga `E_STATISTICHE_MANCANTI` dei due CSV di config | Descrizioni e note allineate |
| M5, M15, M16 | intestazioni `#` di `85_pgagent/20261014-53`, `90_end/ci_apply/20260926-10`; testate di due pgTAP | Solo commenti, fuori dal checksum |

pgTAP nuovi: `maintenance/test-bump-toponomastica-v1` (8), `maintenance/test-fn-run-and-log-lock-ed-esito-v1`
(9), `maintenance/test-cleanup-job-ambito-registro-v1` (3), `maintenance/test-vw-job-run-da-guardare-corse-distinte-v1`
(2), `dbops/test-storico-nome-funzione-ritirato-v1` (2), `dbops/test-overlap-tabella-sparita-v1` (2),
`dbops/test-pgagent-storicizza-ordine-v1` (1, skip motivato senza pgAgent).

### 8.2 Le prove fatte (scratch `zeroerp_ruoli`, SQL estratto, `BEGIN … ROLLBACK`)

* Ogni pgTAP nuovo **senza** il suo changeSet è rosso proprio sui test che il changeSet corregge (bump:
  3, 4, 6, 7; fn_run_and_log: 2, 3, 4, 5, 7; storico, cleanup, overlap, vista, pgAgent: il test di D);
  **con** il changeSet è verde. Tutti e dieci i changeSet nella stessa transazione: 27/27.
* Regressione, senza e con il changeSet, identica: i pgTAP che chiamano `fn_run_and_log` o i wrapper
  (`maintenance/*job-run*`, `test-fn-analyze-statistiche-v1`, `dbops/test-processi-jobname-wrapper`, due di
  `vendite`), quelli della vista (`test-vw-job-run-da-guardare*`), dello storico, dell'overlap, della
  toponomastica e della riclassificazione, della convergenza CI e dell'installazione.
* `proc_automations_cleanup_job` col nuovo ambito, eseguito per davvero e annullato: corsa verde, 39
  operazioni OK nell'audit.
* Guardrail statici verdi (letterali, runOnChange, preambolo pgTAP, preCondition, v1, timestamp, DDL
  su trigger, GRANT).

### 8.3 Per Tid

* Apply dei `20261103-54 … -63` e dei CSV; poi i sette pgTAP nuovi e la regressione dei file di §8.2.
* ⚠️ `-61` è in `85_pgagent`: su un database senza pgAgent va in `MARK_RAN`, come gli altri.
* ✅ 2026-11-03 — migrazione applicata e verde (Tid). Alla prima corsa `dbops/test-pgagent-storicizza-ordine-v1`
  era rosso per «permesso negato per lo schema pgagent»: il runner gira come applicazione, che su
  `pgagent` non ha USAGE, e la prova pre-apply girava da owner e non poteva vederlo. Aggiunto il
  marcatore `pgtap-runner: owner` con il motivo (solo il file di test, nessun changeSet). Gli altri due
  pgTAP nuovi senza marcatore, provati come applicazione dopo l'apply: verdi (8/8, 2/2).

### 8.4 Residuo

* M13: il commento **nel corpo** di `proc_sync_storico_set_storicizza` («il riepilogo finisce nel log
  del server») resta: si corregge solo ridefinendo la procedura, alla prossima occasione che la tocca.
* M9: la colonna `origine` non distingue la convergenza CI da pgAgent: corretto il COMMENT, la domanda
  se debba distinguerle resta aperta.
* M17 (**domanda nuova per Tid**): `job_run_log.agent_host` ha due significati — il default è
  `inet_client_addr()`, il verbale fuori transazione scrive `cluster_name`. Uno dei due va scelto.
* Restano nomi di brief e id di changeSet in alcune note di `presidi.csv` e nella `ci_esclusione` di
  `apply_fk_index_policy` in `processi.csv`: debito di stile, non errori.
* Le due verifiche di §5.

## 9. Giro 2 — il residuo, 2026-11-03

### 9.1 Che cosa è stato scritto

* `20_code/maintenance/20261103-64-update-fn-run-and-log-esito-vuoto-e-prima-riga` — due difetti del
  giro 1 (D5), visti allineando la doc: le automazioni sono `void`, e ogni loro corsa scriveva
  `meta.esito = ""`; e la lettura raccoglieva tutte le righe con `array_agg` per tenerne la prima. Ora
  l'esito vuoto non si scrive, e il conteggio è una finestra con `LIMIT 1` (zero righe → 0).
  `test-fn-run-and-log-lock-ed-esito-v1` passa a plan 11 (test 10: void senza esito, rosso senza il
  changeSet; test 11: zero righe). Regressione dei `test-job-run-*`, `test-fn-analyze-statistiche-v1`,
  `test-processi-jobname-wrapper`: invariata.
* §5, primo punto, **chiuso**: sullo scratch costruito da zero `django.auth_user` è di `zeroerp_owner`,
  lo stesso proprietario della procedura DEFINER `proc_sync_auth_user_expired_job`: l'UPDATE c'è.
* §5, secondo punto, **chiuso**: `test-app-postura-job-run-log-v1` passa a plan 11, il test 11 pinna
  che `zeroerp_app` non ha privilegi su `maintenance.test_pgagent_log` (verde come app).
  ⚠️ Su dbdev è **rosso** (Tid, 2026-11-03), ed è il test che fa il suo lavoro: dbdev ha
  `zeroerp_app=r` su quella tabella, dato a mano (la coda §3.3 di `brief-db-privilegio-app-job-run-log`);
  lo scratch costruito da zero non ce l'ha (ACL vuota), quindi nessun changeSet né il provisioning lo
  concede. Il rimedio è a mano su dbdev, come owner — `REVOKE ALL ON maintenance.test_pgagent_log FROM
  zeroerp_app;` — non un changeSet (§11.8 delle linee guida SQL: niente `REVOKE` a `zeroerp_app`
  fuori dal loop dei grant). Lo lancia Tid.
* Doc: il nome ritirato `trgfn_upd_dlt_storico_generic` corretto in nove pagine `manual/` di `storico`,
  `dbops`, `anagrafiche`; il salto `TABLE_NOT_FOUND` nella pagina dbops del runner overlap; la pagina
  di `fn_run_and_log` allineata al `-64`. Le pagine `manual/` toccate dal giro 1 sono allineate ai
  changeSet (15 di `maintenance`, tre guide).

### 9.2 Valutato e non fatto

* La cascata di D9 sotto RLS: non c'è il caso, `anagrafiche.indirizzi_dettaglio` non ha RLS.
* D3 ha un presidio sul testo (nessuna funzione nomina il nome ritirato), non una prova di
  comportamento con `BY_FUNCTION`: il seed usa solo `BOTH`. Debito dichiarato.
* Le note di `presidi.csv` e la `ci_esclusione` di `apply_fk_index_policy` con nomi di brief e id:
  debito di stile, resta.

### 9.3 Le decisioni di Tid

| # | Domanda | Raccomandazione |
| --- | --- | --- |
| M17 | `job_run_log.agent_host` ha due significati: il default e `script.fn_job_run_start` scrivono l'indirizzo del client (`inet_client_addr()`), `fn_job_run_log_failure` il nome del cluster. Il backend la mostra | Un solo significato, l'indirizzo del client: `fn_job_run_log_failure` legge `inet_client_addr()` nella sessione originale, prima del dblink. Le righe già scritte restano |
| M9 | `origine` non distingue la convergenza in CI da pgAgent | Chiudere senza modifiche: lo dice `ruolo_sessione` (`zeroerp_job` contro il migratore), e il COMMENT ora lo spiega |
| D11 | `proc_apply_storicizza_defaults` isola le righe fallite (WARNING) e chiude «done»: una corsa con righe non applicate è **verde**. È D5 su una procedura: il job la chiama con `CALL`, e il contratto «riuscita con scarti» non la vede | Diventa una funzione che restituisce il riepilogo (`_applicate`, `_saltate`, `_falliti`), chiamata dal wrapper con una `SELECT`: la corsa con righe fallite è rossa con `E_JOB_ESITO_CON_SCARTI`. Nello stesso giro si correggono i commenti nel corpo di sync e apply (M13), che oggi restano stantii |

**Decisioni (Tid, 2026-11-03):** M17 come raccomandato; M9 chiuso senza modifiche (lo dice
`ruolo_sessione`); D11 come raccomandato, con M13 nello stesso giro.

## 10. Giro 3 — M17, D11, M13, 2026-11-03

### 10.1 Che cosa è stato scritto

| # | ChangeSet / file | Che cosa |
| --- | --- | --- |
| M17 | `20_code/maintenance/20261103-66-update-fn-job-run-log-failure-agent-host` | Il verbale di un fallimento scrive in `agent_host` l'indirizzo del client della sessione del job (`inet_client_addr()`), non il nome del cluster. La funzione è di `postgres`: proprietà in prestito via `dbops.fn_sync_functions_owner()` con verifica e restituzione, la forma di `20260807-19` (non `context: provision`). Le righe già scritte restano |
| D11 | `20_code/maintenance/20261103-67-create-fn-apply-storicizza-defaults-esito` | Nasce `maintenance.fn_apply_storicizza_defaults()`: stessa logica per riga, restituisce `_applicate`, `_saltate`, `_saltate_manuali`, `_falliti`, `_dettaglio`. Il wrapper la chiama con una `SELECT`: una tabella fallita rende la corsa rossa (`E_JOB_ESITO_CON_SCARTI`). La procedura `proc_apply_storicizza_defaults` si ritira (chiamanti: il wrapper e un pgTAP) |
| M13 | `20_code/maintenance/20261103-68-update-proc-sync-storico-set-storicizza-commento-riepilogo` | Solo il commento nel corpo: il riepilogo è un NOTICE per chi la lancia a mano |
| — | numero `-65` | preso da un'altra sessione (vendite): il giro salta da `-64` a `-66` |

⚠️ In D11 una riga **saltata** (non risolve a niente) non rende rossa la corsa: è il caso che il sync
pota, e una manuale si conta a parte in `_saltate_manuali` perché si veda nell'esito.

### 10.2 Le prove fatte (scratch, SQL estratto, `BEGIN … ROLLBACK`)

* `-66`: la NOTIFICA della sync mostra `postgres -> zeroerp_owner -> postgres`;
  `test-job-run-log-failure-out-of-tx` passa a plan 7 (test 7, presidio sul testo: rosso senza, verde
  con), 7/7.
* `-67`: `maintenance/test-apply-storicizza-esito-v1` (nuovo, 6/6; senza il changeSet si ferma: la
  funzione non c'è); `test-storicizza-set-potatura` (aggiornato a chiamare la funzione) 7/7.
  Presidi trasversali invariati: `dbops/test-riferimenti-morti-v1` 9/9 (plpgsql_check su ogni
  funzione), `dbops/test-processi-convergenza-ci` 8/8, `maintenance/test-proc-job-definer-v1` 7/7.
* `-66 … -68` insieme: i test di sopra verdi. Guardrail statici verdi.

### 10.3 Doc

* `maintenance/manual/proc_apply_storicizza_defaults.md` **cancellata** (oggetto ritirato), nasce
  `maintenance/manual/fn_apply_storicizza_defaults.md`; rimandi ripuntati in
  `proc_apply_storicizza_defaults_job`, `proc_sync_storico_set_storicizza`,
  `config/manual/storico_set_storicizza` e nella guida *Storicizzazione delle tabelle*.
  ⚠️ La scheda auto-generata `funzioni/fn_apply_storicizza_defaults` nasce con la prossima
  `gen_db_docs.py`: fino ad allora quei quattro link non risolvono.
* `maintenance/manual/fn_job_run_log_failure.md` allineata a M17.

### 10.4 Esito

Tid, 2026-11-03: `-66`, `-67`, `-68` applicati, i pgTAP di §10.2 verdi, doc rigenerata (la scheda
`funzioni/fn_apply_storicizza_defaults` c'è: i quattro link di §10.3 risolvono).

### 10.5 Residuo

| # | Che cosa | Proposta |
| --- | --- | --- |
| R1 | Il COMMENT di `maintenance.proc_sync_storico_set_storicizza` (dal `20261103-63`) dice «il caso transitorio che `maintenance.proc_apply_storicizza_defaults` ripara»: nomina la procedura ritirata dal `-67`. Sfuggito al censimento dei chiamanti, che guardava i corpi e non i COMMENT | Un changeSet `COMMENT ON` solo (`20261103-69`), che nomina `maintenance.fn_apply_storicizza_defaults` |
| R2 | D3: il presidio è sul testo, nessuna prova di comportamento con `BY_FUNCTION` (§9.2) | Un pgTAP che fabbrica una regola `BY_FUNCTION` e verifica che il runner trovi `trgfn_storico_generic` |
| R3 | Nomi di brief e id di changeSet nelle note di `presidi.csv` e nella `ci_esclusione` di `apply_fk_index_policy` in `processi.csv` (§9.2) | Pulizia di stile nel CSV, senza effetti sul comportamento |

ℹ️ La chiave del lock del wrapper resta `hashtext('proc_apply_storicizza_defaults')`: è un'etichetta,
non un riferimento all'oggetto, e cambiarla aprirebbe una finestra in cui due corse non si escludono.

Tid, 2026-11-03: R1, R2, R3 da fare tutti e tre (§11).

## 11. Giro 4 — il residuo di §10.5, 2026-11-03

### 11.1 Che cosa è stato scritto

| # | ChangeSet / file | Che cosa |
| --- | --- | --- |
| R1 | `20_code/maintenance/20261103-69-comment-proc-sync-storico-set-storicizza-consumatore` | Il COMMENT di `proc_sync_storico_set_storicizza` riscritto intero, identico salvo il consumatore: `maintenance.fn_apply_storicizza_defaults`. Nessun'altra descrizione nel database nomina la procedura ritirata (censimento sulla doc auto-generata di tutti gli schemi) |
| R2 | `db/pgtap/dbops/test-storico-nome-funzione-ritirato-v1.sql` (plan 2 → 5, marcatore `pgtap-runner: owner`) | Prova di comportamento di D3: una madre col trigger generico montato a mano con un altro nome non ne riceve un secondo, con `BY_FUNCTION` (test 3) e con `BOTH`, la strategia del seed (test 4); senza trigger, `BY_FUNCTION` lo monta (test 5, perché 3-4 non passino a vuoto) |
| R3 | — | **Chiuso senza modifiche**: la regola vieta il *percorso* di un brief, non il nome (le note di `presidi.csv` e `processi.csv` citano i brief per nome, come tutto il catalogo). L'id `20250626-31` nella `ci_esclusione` di `apply_fk_index_policy` punta a un changeSet `runAlways` vivo: è il motivo dell'esclusione. Il debito dichiarato in §8.4 e §9.2 era una lettura sbagliata |

Doc: `maintenance/manual/proc_automations_storico_job.md`, sezione Test, allineata a R2.

### 11.2 Le prove fatte (scratch, `BEGIN … ROLLBACK`)

* `-69`: il COMMENT si applica; le due preCondition valgono 1.
* R2: 5/5 col runner vivo. Col runner **mutato** a cercare il nome ritirato (il difetto di D3): test 2
  rosso, e il runner muore al test 3 — non per il trigger doppio, ma per R4 qui sotto.

### 11.3 Esito

Tid, 2026-11-03: `-69` applicato, `dbops/test-storico-nome-funzione-ritirato-v1` verde.

### 11.4 Difetti nuovi — decisione di Tid

| # | Difetto | Raccomandazione |
| --- | --- | --- |
| R4 | `dbops.fn_run_automations_storico`, ramo `duplicate_object` del `CREATE TRIGGER`: scrive in `dbops.audit_log` lo status `SKIP_EXISTS`, che `chk_audit_status` (`START`, `OK`, `ERROR`, `DRYRUN`, `WARN`) rifiuta. Il ramo che doveva saltare un trigger già presente **ferma il runner** con 23514. Ci si arriva quando il controllo di esistenza dice «assente» e il nome del template è già preso: con `BY_FUNCTION`, una madre che ha un trigger col nome del template su un'altra funzione | Lo status diventa `WARN` (il salto è un fatto da vedere, non un errore), `SKIP_EXISTS` resta nel `message`/`params` come azione. Un pgTAP che passa dal ramo. Il vocabolario del vincolo non si allarga: `SKIP_EXISTS` è un'azione, non un esito |
| R5 | `dbops.fn_apply_chiusura_scadenze` scrive l'audit con status `INFO`, fuori dal vincolo; l'eccezione la inghiotte un `WHEN OTHERS THEN NULL`: l'audit di quella funzione **non si scrive mai**, in silenzio. Fuori dal perimetro `maintenance` | Status `OK`; nello stesso changeSet nessun'altra modifica. Il `WHEN OTHERS` best-effort resta (è voluto), ma è quello che ha nascosto il difetto |

⚠️ Il censimento: fra le chiamate a `fn_audit_log_once` con status letterale nella doc auto-generata,
`SKIP_EXISTS` e `INFO` sono le sole fuori dal vincolo.

**Decisione (Tid, 2026-11-03):** R4 e R5 come raccomandato (§12).

## 12. Giro 5 — R4, R5, 2026-11-03

### 12.1 Che cosa è stato scritto

| # | ChangeSet / file | Che cosa |
| --- | --- | --- |
| R4 | `20_code/dbops/20261103-70-update-fn-run-automations-storico-salto-in-audit` | Ramo `duplicate_object`: status `WARN`, `action: SKIP_EXISTS` nei `params` (come `DRYRUN_CREATE_TRIGGER_UD` nel ramo del dry run). Corpo dalla doc auto-generata (= `-57`), cambia solo quella chiamata |
| R4 | `db/pgtap/dbops/test-storico-salto-trigger-presente-v1.sql` (nuovo, plan 3, owner) | Una madre col nome del template preso da un trigger su un'altra funzione, regola `BY_FUNCTION`: il runner vive, l'audit ha `WARN` + `SKIP_EXISTS` con la tabella, nessun trigger di storico nasce |
| R5 | `20_code/dbops/20261103-71-update-fn-apply-chiusura-scadenze-audit-scritto` | Status `OK` invece di `INFO`. Il `WHEN OTHERS` best-effort resta. Corpo dalla doc auto-generata (= `20261028-14`) |
| R5 | `db/pgtap/dbops/test-chiusura-scadenze-audit-v1.sql` (nuovo, plan 2, app) | Un giro senza righe attive scrive una riga di audit `OK` con il riepilogo restituito |
| — | `20_code/maintenance/20261103-66-…` (**già applicato**) | ⛔ La preCondition leggeva la voce di `dbops.sec_functions_owner`, che arriva con `80_data`: su un database da zero il migrate si sarebbe fermato lì. L'ha trovato `guardrail_precondition_seed`. Ora controlla la funzione in `pg_proc`, come `20260807-19`. Le preCondition non entrano nel checksum: dbdev non vede la modifica. Da zero il corpo regge senza la voce (il prestito non trova righe, la funzione è già del migratore; la firma è già quella del `20261016-39`, che senza contesti gira prima) |

Doc: le guide *Automazione DB* e *Messaggi audit*, il tutorial del framework e le pagine
`dbops/manual/fn_run_automations_storico` e `fn_apply_chiusura_scadenze` davano `SKIP_EXISTS` (o
`INFO`) come status: allineate. ⚠️ Le due pagine `dbops/manual/` non sono allo standard (cornice,
«Vedi anche»): fuori dal perimetro di questo brief, toccate solo nel punto.

### 12.2 Le prove fatte (scratch, SQL estratto, `BEGIN … ROLLBACK`)

* `-70`: `dbops/test-storico-salto-trigger-presente-v1` 3/3; senza il changeSet 1/3 (test 1-2 rossi).
  Regressione: `test-storico-nome-funzione-ritirato-v1` 5/5, `test-storico-automazione-colonna-fk-v1`
  7/7.
* `-71`: `dbops/test-chiusura-scadenze-audit-v1` 2/2 da owner; senza il changeSet 0/2, anche come app
  (il test gira come app senza errori di permesso: con l'apply di dbdev va lanciato così).
  Regressione: `test-fn-apply-chiusura-scadenze-v1` 8/8.
* Guardrail statici sui changeSet del 2026-11-03: `sql_letterali`, `timestamp_senza_fuso`,
  `run_on_change`, `precondition_seed` (dopo la correzione del `-66`), `pgtap_preambolo` verdi.

### 12.3 Esito

Tid, 2026-11-03: `-70` e `-71` applicati, `dbops/test-storico-salto-trigger-presente-v1` e
`dbops/test-chiusura-scadenze-audit-v1` verdi.

## 13. Chiusura

Tutti i punti del brief sono chiusi: D1–D11 e i metadati M1–M17 corretti o chiusi con una decisione
(M9 senza modifiche), il residuo R1–R5 fatto (R3 chiuso senza modifiche, §11.1). Le pagine di §7 sono
allineate ai changeSet. Debito che resta, fuori perimetro e senza brief: le pagine
`dbops/manual/fn_run_automations_storico` e `fn_apply_chiusura_scadenze` non sono allo standard
(§12.1).
