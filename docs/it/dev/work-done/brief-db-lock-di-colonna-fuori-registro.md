# Brief DB — i lock di colonna fuori dal registro: il giro notturno li cancella

> **Perimetro:** DB (`dev/db-tid`). Nessuna azione chiesta a BE né FE (§6).
> **Aperto:** 2026-09-26.
> **Origine:** la domanda lasciata aperta in §7 di
> [brief-db-codici-ritirati-negli-argomenti-dei-trigger.md](brief-db-codici-ritirati-negli-argomenti-dei-trigger.md):
> *«dbdev ha perso dei trigger di lock che il DB da zero ha»* (`config.iva`,
> `config.iva_stati`, `vendite.fatture`), più la convergenza «trigger vivo =
> registro» che il runner non fa.
>
> **Stato:** ✅ **APPLICATO, VERDE, NESSUNA REGRESSIONE — 2026-09-26.** I sette
> changeSet `20260926-01…07` sono `EXECUTED` su dbdev (11:49) e su `zeroerp_ci`
> (11:53); pgTAP rilanciati da Tid, verdi, nessuna regressione. Letto dopo
> l'apply sul catalogo vivo di entrambi: **zero divergenze**, zero trigger di
> lock fuori template, `fatture.natura_doc_id` bloccata, `user_emittenti_fiscali`
> sul codice dedicato. La causa è confermata dal log dei job per tutti e tre i
> casi (§3).
> ✅ **CHIUSO il 2026-09-26 e spostato in `work-done/`.** Tid ha confermato il
> codice dedicato su `user_emittenti_fiscali` (§5). D4 continua in
> [brief-db-job-notturni-in-ci.md](brief-db-job-notturni-in-ci.md).
>
> **In una riga.** Il giro notturno `fn_run_automations_drop_lock_trg` decide
> che una tabella «non ha niente da bloccare» leggendo **solo il registro**, ma
> poi cancella i trigger di lock cercandoli **per funzione**. Così cancella anche
> quelli scritti a mano, che il registro non conosce. Su CI non succede perché lì
> il job non esiste.

---

## 1. Il difetto, sul modello

Due runner lavorano sugli stessi trigger (`script.trgfn_lock_columns`) e li
riconoscono in due modi diversi:

| | Come decide | Come riconosce il trigger |
| --- | --- | --- |
| `fn_run_automations_lock_columns` (crea) | colonne da `codice_interno` + registro `dbops.automation_lock_columns` | `existence_strategy = BOTH`: per **nome da template** *oppure* per **funzione**. Se ne trova uno, **non fa niente** |
| `fn_run_automations_drop_lock_trg` (cancella) | se la tabella non ha `codice_interno` **né** righe attive nel registro, non c'è niente da bloccare | ancora `BOTH`: droppa il trigger col nome da template **e ogni altro trigger su `trgfn_lock_columns`** di quella tabella |

⇒ Un trigger di lock scritto a mano in `20_code` su una tabella che il registro
non nomina ha due destini:

* per il runner che crea **esiste già**, quindi non viene mai riallineato (è il
  §1 del brief dei codici ritirati);
* per il runner che cancella **è superfluo**, quindi sparisce alle 21:10.

Nessuno dei due sbaglia rispetto alla propria regola. Il difetto sta nel
presupposto che condividono: *«un lock di colonna è una riga del registro»*. Il
repository non lo garantisce, perché si può ancora scrivere a mano un
`CREATE TRIGGER … EXECUTE FUNCTION script.trgfn_lock_columns(...)`.

### Perché dev e CI dissentono

Il runner che cancella gira **solo** nel job pgAgent delle 21:10
(`maintenance.proc_automations_lock_columns_job`, creato dal `85_pgagent/20260905-08`).
In CI `85_pgagent` è `MARK_RAN`: il job non esiste e quel runner non parte mai.
È l'**R-11** di
[brief-db-processi-automatici-identita-e-perimetro.md](brief-db-processi-automatici-identita-e-perimetro.md).

⛔ **Quindi dev non è fuori modello**: è l'unico ambiente in cui il modello gira
per intero. La CI è verde perché le manca un pezzo. Qualsiasi ambiente col job
attivo, da qui in avanti, perderebbe gli stessi lock alla prima notte.
Il §5-ter del brief chiuso diceva il contrario ed è stato corretto il 26-09.

## 2. La fotografia (fatto datato, non un motivo)

Letta sui **file** il 2026-09-26, poi confermata sul catalogo vivo di dbdev
(come `zeroerp_app`, sola lettura) e di `zeroerp_ci` (come owner, in rollback).

| Tabella | Lock scritto a mano | `codice_interno` | Righe attive nel registro prima del 23-09 | Spiegato dal runner che cancella? |
| --- | --- | --- | --- | --- |
| `config.iva_stati` | `20251006-21` | no | nessuna | ✅ sì |
| `vendite.fatture` | `20260818-28` (`natura_doc_id`, `E_COLONNA_NON_MODIFICABILE`) | no | solo `numero`, **`enabled = f`** | ✅ sì |
| `config.iva` | `20251006-12` (poi `trg_iva_a10_protect_columns_upd`) | **sì** | `aliquota_iva`, `natura_iva_id` (dal 30-08) | ❌ **no**: con `codice_interno` il runner salta la tabella |

⚠️ **`config.iva`: un'ipotesi compatibile, non una prova.** Nessun changeSet
cancella `trg_iva_a10_protect_columns_upd` (il `00_schema/20260829-43` toglie solo
il nome da template). Però la chiamata a `drop_lock_trg` sta nella procedura del
job **dal 2026-02-09** (`20260209-06`), e **prima del 29-08** `config.iva` non
aveva né `codice_interno` (arriva col `20260829-43`) né righe nel registro
(arrivano il 30-08). ⇒ Un qualunque giro della procedura in quella finestra,
anche lanciato **a mano** (il job notturno esiste solo dal 05-09), lo toglieva.
Tid può dire se la procedura è stata lanciata a mano prima del 29-08.

**Oggi:**

* `config.iva` e `config.iva_stati` sono coperte dal registro dal 23-09, quindi
  sono al sicuro dal job;
* **`vendite.fatture.natura_doc_id` non è nel registro.** Su dev manca, e se lo
  si rimettesse a mano il job lo toglierebbe di nuovo la notte stessa. Su CI c'è,
  ma solo finché il job non esiste;
* gli altri lock scritti a mano censiti dai changelog (§5-ter del brief chiuso)
  sono al sicuro: `stati_fornitore` e `stati_commessa` hanno `codice_interno`,
  mentre `user_emittenti_fiscali` e `fatture_fondi_fattura_source` hanno righe
  attive nel registro. ⚠️ Sono al sicuro **per come stanno oggi i dati**, non per
  una regola: basta disattivare una riga del registro e il job li toglie.

## 3. Le verifiche sul catalogo vivo

Servono a confermare la causa. Non decidono il rimedio: quello discende dal §1.

1. ✅ **Confermata il 26-09 su `zeroerp_ci`**, in `BEGIN … ROLLBACK`: fatta girare
   **davvero** `fn_run_automations_drop_lock_trg('SCHEDULED', NULL, false)` sul
   database ricostruito da zero, toglie **esattamente un** trigger su 91:
   `vendite.fatture → trg_fatture_a10_lock_natura_doc_upd`. È il lock che su dev
   manca.
2. ✅ **Confermata il 26-09 da `maintenance.job_run_log`** (il log che
   `fn_run_and_log` scrive a ogni giro, leggibile come `zeroerp_app`, mentre lo
   schema `pgagent` non lo è). Il lock di `fatture` nasce il 18-08; il primo giro
   di `automations_lock_columns` dopo quella data è il **2026-09-05 alle 21:10**,
   la prima sera del job notturno. Da lì il lock non c'era più.
3. ✅ **`config.iva`, confermata dallo stesso log.** Prima del 29-08 i giri sono
   tre: due l'11-01 e uno il **2026-06-04**. Quello di giugno cade dopo il
   `20260209-06`, che ha messo `drop_lock_trg` nella procedura, e prima del
   `20260829-43`, che ha dato `codice_interno` a `config.iva`. ⇒ In quel giro
   `config.iva` non aveva niente da bloccare per il registro, e il lock scritto a
   mano è stato tolto. Tid conferma di aver lanciato la procedura a mano in quel
   periodo. `config.iva_stati` è stata tolta nello stesso giro o in uno
   successivo: fino al 23-09 non aveva nessuna riga nel registro.

⚠️ `origine` nel log vale `PGAGENT` anche per un giro lanciato a mano con
`CALL maintenance.proc_automations_lock_columns_job()`: è il default della
colonna. Il log dice **quando** un giro è partito, non **chi** l'ha lanciato.

## 4. Decisioni — ✅ approvate da Tid il 2026-09-26

### D1 — Il registro è l'unica sede di un lock di colonna

* `vendite.fatture.natura_doc_id` entra in `automation_lock_columns.csv` con
  `E_COLONNA_NON_MODIFICABILE`, lo stesso codice del trigger a mano;
* ⛔ **Da qui in avanti niente `CREATE TRIGGER` scritto a mano su
  `trgfn_lock_columns`.** I trigger a mano che restano vengono riassorbiti dalla
  convergenza di D2 e cambiano nome. Il pgTAP `vendite/test-documento-lineage-v1`
  nomina `trg_fatture_lock_natura_doc` **solo in un commento**, quindi nessuna
  asserzione pinna il nome. Il censimento dei nomi va comunque rifatto al
  momento di scrivere.

### D2 — Un runner che converge, invece di due che si ignorano

Per ogni tabella nel perimetro il runner calcola il lock **atteso** (colonne e
codice, da `codice_interno` + registro) e lo confronta con i trigger vivi su
`trgfn_lock_columns`:

| Stato vivo | Azione |
| --- | --- |
| uguale all'atteso, un solo trigger, nome da template | niente |
| argomenti diversi, più di un trigger, o nome non da template | drop e rigenera |
| atteso vuoto | drop: è il lavoro di oggi di `drop_lock_trg` |
| manca | crea: è il lavoro di oggi di `lock_columns` |

⇒ `fn_run_automations_drop_lock_trg` diventa un ramo del runner e **si ritira
nello stesso giro**, con la sua pagina `manual/` e i due chiamanti (il job e il
suo wrapper). Due runner che si contraddicono sullo stesso oggetto sono proprio
la copia da ritirare.

⚠️ **Precedente da leggere prima, non da copiare alla cieca.** La regola
`ATTIVO` ha già `reconcile_on_change`, ma secondo la sua doc serve a togliere i
**doppioni** con gli stessi argomenti, non a confrontarli con una sede. Va
verificato se `dbops.fn_trigger_exists_block_by_args` o un'altra primitiva di
`dbops` legge già gli argomenti di un trigger. Se sì, la convergenza la riusa.
Il confronto su `tgargs` ha una trappola nota (§5-bis del brief chiuso):
`encode(tgargs,'escape')` finisce con `\000`.
✅ **Letto il 26-09.** `fn_trigger_exists_block_by_args` confronta con `ILIKE` su
`pg_get_triggerdef`, quindi non legge gli argomenti. `fn_ritira_attivo_eccezioni`
(20260925-47) invece li decodifica sul posto: la convergenza sarebbe stata la
**seconda copia**. ⇒ Si è estratto il building block `dbops.fn_trigger_argomenti`
(§7). Scrivendolo è emerso che la forma in uso aveva **due difetti latenti**, e il
§5-bis del brief chiuso ne aveva visto solo un terzo, il `\000` in coda.

⭐ **Il controllo (b) del `20260923-02` entra nel runner.** Il controllo (b) è
«nessuna colonna che era bloccata resta scoperta». Senza, la convergenza
cancellerebbe in silenzio ogni lock scritto a mano che il registro non conosce,
cioè lo stesso difetto di oggi, solo più veloce. Se una colonna bloccata dal vivo
non è nell'atteso, il runner **si ferma e la nomina**, non la droppa. Su un DB
nuovo questo controllo è quello che parla alla prima migrate, perché lì i
trigger a mano di `20_code` esistono.

⇒ Con D2 i sei changeSet `90_end/*provision-lock*` degli ultimi due mesi
(`20260818-23`, `20260821-07`, `20260901-21`, `20260905-40`, `20260923-02`,
`20260923-03`) smettono di essere un pattern: ognuno era una convergenza fatta a
mano su un perimetro fisso. Restano come storia e non si toccano.

### D3 — Un presidio sul lock vivo

Ogni trigger su `trgfn_lock_columns` deve avere il nome da template e gli
argomenti uguali all'atteso. Da decidere dove metterlo: o accanto al controllo
(H) di `scripts/sql/guardrail_codice_errore_strutturato.sql`, che già legge il
registro, o in un pgTAP. ⚠️ **Il criterio deve stare in un posto solo.** Il
calcolo dell'atteso va esposto **una volta** dal runner (per esempio come
funzione di sola lettura) e il presidio lo chiama; non lo ricalcola.

### D4 — La CI che non ha i job notturni (R-11)

Non si risolve qui, ma va detto. Finché `85_pgagent` è `MARK_RAN`, **ogni**
automazione che gira anche di notte ha su CI un pezzo di comportamento in meno
che su dev. Questo brief è il primo caso in cui quella differenza ha prodotto un
falso «dev fuori modello». Si propone di riaprire R-11 con questo esempio:
almeno i **corpi** dei job si possono lanciare una volta in CI dopo `ci_apply`,
anche senza pgAgent.

## 5. Come si è arrivati al disegno, e che cosa è cambiato strada facendo

* **D3 sta in un pgTAP, e il criterio in una funzione.** Il confronto fra atteso e
  vivo è `dbops.fn_lock_columns_divergenze`, di sola lettura. La chiamano il
  runner, che esegue le azioni, il pgTAP `dbops/test-lock-columns-convergenza`,
  che ne pretende zero, e il `90_end/20260926-07`, che ne pretende zero dopo la
  convergenza. Nessuno dei tre la ricalcola. Il guardrail dei codici resta sul
  suo mestiere, i codici.
* **«Ignota» e «disattivata» non sono la stessa cosa.** Una colonna bloccata dal
  vivo che il registro **non nomina affatto** ferma il runner. Una colonna con una
  riga `enabled = false` è una decisione, e la convergenza la toglie senza
  fermarsi. È l'unico modo di togliere un lock che resta dichiarato.
* **`exec_mode` dice quando un lock nasce, non quando esiste.** Una riga di un
  altro modo resta attesa se la colonna è già bloccata. Senza questa regola il
  giro `SCHEDULED` toglierebbe ogni notte quello che il giro `CI` ha messo. Oggi
  tutte le righe sono `AUTO`: è un caso che il modello ammette, e il pgTAP lo
  costruisce (test 21-22).
* **Il runner si ferma PRIMA di qualunque DDL, su tutte le tabelle insieme.** La
  prima versione si fermava sulla prima tabella con colonne perse, dopo aver già
  rigenerato le precedenti (annullate dal rollback, ma il messaggio ne nominava
  una sola). Ora un solo errore le elenca tutte.
* ⭐ **Una seconda divergenza vera, trovata dalla convergenza stessa.** Il registro
  dava `E_CODICE_NON_MODIFICABILE` a `config.user_emittenti_fiscali.emittente_fiscale_id`
  (riga del 18-08), mentre il trigger scritto a mano del `20260408-16`, vivo su un
  DB ricostruito da zero, solleva `E_EMITTENTE_NON_MODIFICABILE`. Su dev c'era il
  generico, su CI il dedicato: **due codici per la stessa regola**. Il pgTAP
  `config/test-user-emittenti-fiscali-immutable` passava su entrambi perché
  cercava `'%emittente%'` e il **nome della colonna** contiene «emittente».
  ⇒ Corretta la riga del registro sul codice **dedicato**: ha il suo messaggio col
  rimedio per l'operatore e il BE lo dichiara (`apps/anagrafiche/error_codes.py`).
  Il pgTAP ora cerca la frase del codice dedicato; per mutazione (registro col
  codice generico) va rosso.
  ✅ Scelta presa scrivendo, **confermata da Tid il 2026-09-26**.

## 6. Ricadute

* **BE/FE:** nessuna azione. `fatture.natura_doc_id` risponde con lo stesso
  `E_COLONNA_NON_MODIFICABILE` di prima (su CI), e i nomi dei trigger riassorbiti
  non compaiono in `backend/` né in `frontend/` (grep del 26-09). ⚠️ Su **dbdev**
  cambia la risposta di un `UPDATE` su `config.user_emittenti_fiscali.emittente_fiscale_id`:
  dal messaggio generico a quello dedicato, che il BE conosce già. Il BE non fa mai
  quell'`UPDATE` (la porta di dominio fa DELETE + INSERT, nota della riga nel CSV);
* **pgTAP:** nessuno chiama il runner o `drop_lock_trg`. I due che leggevano
  `tgargs` o dipendevano dal codice sono stati aggiornati (§7). ⚠️ Il fatto che
  nessun test chiamasse `drop_lock_trg` vuol dire anche che **nessun test la
  misurava**;
* **guardrail:** `scripts/sql/guardrail_codice_errore_strutturato.sql` ora chiama
  `dbops.fn_trigger_argomenti`, quindi ha bisogno che il `20260926-01` sia
  applicato. In CI gira dopo la migrate Liquibase (`ci-validate.yaml`), quindi lo
  trova. Su dev va lanciato dopo l'apply.

## 7. Che cosa è stato scritto (2026-09-26)

| File | Che cosa fa |
| --- | --- |
| `20_code/dbops/20260926-01-create-fn-trigger-argomenti` | **building block**: gli argomenti di un trigger come `text[]`, tagliati sui byte `NUL`. La forma `rtrim(encode(tgargs,'escape'),'\000')` toglie l'**insieme** `{\, 0}`: `'col','E_X10'` → `{col,E_X1}`. E `'escape'` storpia i non ASCII (`città` → `citt\303\240`). Provato sul DB |
| `20_code/dbops/20260926-02-update-fn-ritira-attivo-eccezioni-argomenti-dal-bb` | ritiro della prima copia: cambia **una** riga rispetto al corpo vivo (verificato con un diff) |
| `20_code/dbops/20260926-03-create-fn-lock-columns-divergenze` | il criterio: atteso contro vivo, azione e colonne perse. `VOLATILE` perché chiama helper `VOLATILE` (`plpgsql_check`) |
| `20_code/dbops/20260926-04-update-fn-run-automations-lock-columns-converge` | il runner converge: `CREA` / `RIGENERA` / `TOGLIE`; si ferma con `E_LOCK_COLUMNS` prima di qualunque DDL se ci sono colonne perse |
| `20_code/maintenance/20260926-05-update-proc-automations-lock-columns-job-senza-drop` | il job notturno non chiama più `drop_lock_trg` |
| `20_code/dbops/20260926-06-drop-fn-run-automations-drop-lock-trg` | ritiro; la `preCondition` pretende che nessun corpo vivo la **chiami** |
| `90_end/20260926-07-converge-lock-columns` | una convergenza alla migrate, non alle 21:10; pretende zero divergenze dopo |
| `80_data/sql/dbops/automation_lock_columns.csv` | D1: riga nuova `vendite.fatture.natura_doc_id`; riga `user_emittenti_fiscali` corretta sul codice dedicato (§5) |
| `db/pgtap/dbops/test-lock-columns-convergenza.sql` | **nuovo**, 22 test, da owner (fa DDL). Test 4 = il presidio D3 su tutto il DB; il resto costruisce uno schema di prova con lock scritti a mano, righe ignote, disattivate e di un altro `exec_mode` |
| `db/pgtap/catalogo/test-articoli-seed-uom-base-lock.sql` | legge `tgargs` dal building block (il filtro `a <> ''` non serve più) |
| `db/pgtap/config/test-user-emittenti-fiscali-immutable.sql` | test 1 sulla frase del codice dedicato |
| `scripts/sql/guardrail_codice_errore_strutturato.sql` | controllo (D) sugli argomenti dal building block |
| doc | `manual/` del runner, del registro, di `automation_rules_tbl` e del job riscritti; nuovi `manual/` delle due funzioni; tolto quello di `drop_lock_trg`; guida `automazione-db.md` e tutorial aggiornati; nota R-11 nel brief dei processi automatici (D4) |

### Come è stato provato

SQL **estratto** dai changeSet con uno script (non ricopiato), eseguito su
`zeroerp_ci` come owner in `BEGIN … ROLLBACK`, con il registro modificato come
lo lascia `80_data`. Dopo ogni prova è stato verificato che niente sia rimasto
(`fn_lock_columns_divergenze` assente, `drop_lock_trg` presente, nessuno schema
di prova).

* **Percorso vero**: 91 lock prima e dopo; i tre scritti a mano (`fatture`,
  `user_emittenti_fiscali`, `fatture_fondi_fattura_source`) prendono il nome da
  template con colonne e codici giusti; zero trigger di lock fuori template;
  zero divergenze anche in un secondo giro con `'CI'`.
* **pgTAP nuovo 22/22**, con l'SQL estratto in testa nella sua transazione.
* **Tre prove per mutazione, tutte rosse dove devono:**
  1. registro senza la riga D1 → il runner si ferma e nomina
     `vendite.fatture (natura_doc_id)`, e il lock scritto a mano resta;
  2. senza il `90_end/20260926-07` → il test 4 del pgTAP va rosso e nomina le tre
     tabelle;
  3. registro col codice generico su `user_emittenti_fiscali` → il pgTAP
     `test-user-emittenti-fiscali-immutable` va rosso al test 1.
* `config/test-user-emittenti-fiscali-immutable` **3/3** sul percorso nuovo.
* Guardrail dei codici sul percorso nuovo: pulito, «nessun codice ritirato … né
  nei corpi né negli argomenti dei 2140 trigger».
* `plpgsql_check` sulle quattro funzioni toccate: zero righe.
* Guardrail statici del repository (runOnChange, preCondition/seed, DDL su
  trigger di automazione, GRANT batch, letterali, timestamp, preambolo pgTAP):
  tutti verdi.
* **dbdev, previsione in sola lettura** (come `zeroerp_app`, con le due funzioni
  caricate in `pg_temp` e una copia temporanea del registro corretto): il 07
  **crea** il lock di `fatture.natura_doc_id` e **rigenera** quello di
  `user_emittenti_fiscali` (codice dedicato). Zero colonne perse: **non si ferma**.

### Che cosa NON prova

* **Non è un database ricostruito da zero**: è `zeroerp_ci` con i changeSet
  eseguiti sopra il suo stato. Il percorso «da zero» (07 nella prima passata,
  poi `ci_apply`) è ragionato, non corso;
* **niente come applicazione**: le prove girano da owner. Il pgTAP nuovo gira da
  owner per scelta (fa DDL); gli altri li misura la corsa di Tid;
* **il job notturno** non è stato fatto girare: `fn_run_and_log` è provato solo
  per sostituzione del testo della chiamata.

## 8. Che cosa resta

| | Chi | Che cosa |
| --- | --- | --- |
| ✅ | Tid | apply su dbdev e su `zeroerp_ci`, 26-09 |
| ✅ | Tid | pgTAP verdi, nessuna regressione, 26-09 |
| ✅ | — | §3.2 e §3.3 chiusi dal log dei job |
| ✅ | Tid | codice dedicato su `user_emittenti_fiscali` confermato, 26-09 (§5) |
| ✅ | — | D4 aperto il 26-09: [brief-db-job-notturni-in-ci.md](brief-db-job-notturni-in-ci.md) |
