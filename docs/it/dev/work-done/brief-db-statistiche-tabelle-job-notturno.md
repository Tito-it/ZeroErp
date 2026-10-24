# Brief DB — Le statistiche delle tabelle: un job notturno che le tiene aggiornate

## ✅ Chiuso il 2026-10-15

**Archiviato da Tid il 2026-10-15. D15 è chiusa.** Nessun debito residuo: le decisioni D-1 … D-4
sono state prese il 2026-10-14 (§6), il codice è nel commit `5e8d5094d`.

| # | Chi | Che cosa | Dove | Esito |
| --- | --- | --- | --- | --- |
| 1 | ✅ **Tid** | `GRANT pg_maintain TO zeroerp` sul cluster (ruolo poi ritirato col modello dei ruoli di sistema) | §7.3 | — |
| 2 | ✅ **Tid** | Apply su dbdev di `-50…-53`; prima corsa riuscita alle 17:49 (da `ci_apply`) | §7.4 | — |
| 3 | ✅ **Tid** | Apply del `-54` e dei CSV dei presidi, corsa pgTAP: **verdi** (2026-10-14) | §7.4, §8 | — |
| 4 | ✅ **Tid** | Corse di pgAgent riuscite in `maintenance.job_run_log` (vedi sotto) | §5.6 | — |
| 5 | ✅ **Tid** | Archiviazione in `work-done/` e chiusura di D15 | — | 2026-10-15 |

**La prova del §5.6, su dbdev** (fatti datati 2026-10-15):

* **02:30**, la prima corsa notturna: `ok = true`, `done`, 2,8 s; pgAgent `jlgstatus = s`. Il
  demone si collegava ancora col ruolo vecchio, poi ritirato dal
  [brief dei ruoli di sistema](brief-db-ruoli-di-sistema.md).
* **19:28**, «Esegui ora» da pgAdmin: la stessa corsa col ruolo nuovo, `ruolo_sessione = zeroerp_job`,
  `ok = true`, 2,4 s. La procedura è `SECURITY DEFINER` di `zeroerp_owner`, che è proprietario di
  tutte le tabelle del perimetro. Il job poi si è riprogrammato da solo per il 16-10 alle 02:30.
* `maintenance.vw_statistiche_mancanti` vuota; nel panorama `dbops.vw_processi_programmazione` il
  processo è `OK` e `da_guardare = false`.

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-10-14. **A chi:** Tid, poi il team DB.
> **Origine:** **D15** di [migliorie-generali-da-test-valutazione](../work-in-progress/migliorie-generali-da-test-valutazione.md),
> emersa il 2026-09-22 chiudendo D14 ([brief della partita di merce](brief-db-partita-merce-per-documento.md)
> §15). Nel registro D15 resta come voce che rimanda qui.
> **Stato:** ✅ chiuso il 2026-10-15: applicato su dbdev, pgTAP verdi, job notturno provato.
> **Ricadute BE/FE:** nessuna. **Ricaduta di provisioning:** il ruolo con cui gira pgAgent (§4.4).

## 1. La regola

Il planner sceglie un piano **stimando** quante righe escono da ogni passaggio. Le stime le prende
dalle statistiche che scrive `ANALYZE`: righe della tabella, valori più frequenti, istogrammi,
frazione di `NULL`. È una **fotografia dei dati**, non una memoria delle esecuzioni, e va rifatta
perché i dati cambiano.

⇒ **Il database deve avere un posto che tiene aggiornate le statistiche di tutte le sue tabelle, e
che dice quando non ci riesce.** Oggi questo posto non esiste.

## 2. Perché l'autovacuum non basta — sul modello

L'autovacuum non è quel posto, e non per un fatto di volume: per come è fatto.

* **La soglia è relativa.** Una tabella si rianalizza quando cambiano `50 + 10%` delle sue righe
  (`autovacuum_analyze_threshold`, `autovacuum_analyze_scale_factor`). Una tabella di catalogo o di
  configurazione che non cambia mai non viene mai analizzata, e il planner la stima coi default.
* **Le tabelle partizionate non le analizza mai.** L'autovacuum lavora sulle partizioni e non
  sulla madre: le statistiche della madre esistono solo se qualcuno lancia `ANALYZE` su di lei.
  Nel modello ci sono tabelle partizionate.
* **Un database appena costruito non ha statistiche.** In CI il database rinasce a ogni corsa, e i
  pgTAP girano subito dopo il caricamento: ogni pgTAP che guarda la forma di un piano la guarda
  costruita su stime di default.
* **Quando scatta, scatta in un momento qualunque.** Le stime cambiano a metà giornata e con loro
  il piano: è il «si ribalta da solo» di D15.

E le **forme** curate da D26-2 (piano generico, CTE `MATERIALIZED`, cardinalità dichiarata) non
coprono questo punto: correggono ciò che le statistiche non possono sapere. Il resto delle
scelte del planner (ordine dei join, indice o scansione, tipo di join) resta appoggiato alle stime.

## 3. Fatti datati

Entrano come **fatti**, non come motivi: il §2 sta in piedi anche senza.

* **2026-09-22** (brief della partita di merce §15): in `vendite` 82 tabelle su 87 mai analizzate.
  Lo stesso corpo misurava 63 ms alle 16:12 e 95–104 ms alle 17:19.
* **2026-10-12**: un autoanalyze di `pg_proc`, scattato su `zeroerp_ci` un minuto dopo un apply, ha
  fatto diventare rosso un pgTAP di costo stimato. La cura di quel caso è stata dichiarare la
  cardinalità (`20261012-25/-26`), non le statistiche.
* **2026-10-14** (dbdev, `pg_stat_user_tables` e `pg_class`): mai analizzate 69 tabelle su 89 in
  `vendite`, 25 su 25 in `magazzino`, 9 su 9 in `acquisti`; 121 tabelle su 535 negli schemi di
  progetto con `reltuples = -1`. Soglie di autovacuum ai default, nessuna `reloptions`, nessun job.
  Database 812 MB, `default_statistics_target = 100`.
* **2026-10-14**, prova in transazione annullata su PostgreSQL 18.6: `EXECUTE 'ANALYZE …'` dentro un
  blocco plpgsql funziona, e porta `reltuples` da `-1` a un valore vero anche per una tabella
  **vuota** (0) e per una **partizionata**. È ciò che rende possibile l'autoverifica del §4.2.

⚠️ Tid, 2026-10-14: la maggior parte delle righe di dbdev sono log. Non cambia il disegno:
`ANALYZE` legge un **campione** (al più `300 × default_statistics_target` righe per tabella), quindi
il suo costo non cresce con la dimensione delle tabelle.

## 4. Il disegno

Si usa ciò che c'è: il giornale dei job (`maintenance.fn_run_and_log`), il catalogo dei processi
(`dbops.processi`), la convergenza in CI (`90_end/ci_apply/20260926-10`), il panorama dei processi e
i presidi. Non nasce nessun meccanismo nuovo.

### 4.1 Il verbo e il job

* **Verbo** `maintenance.fn_analyze_statistiche()` (nome da confermare in scrittura): lancia
  `ANALYZE` sul database, poi fa l'autoverifica del §4.2. È la sola sede del lavoro.
* **Procedura** `maintenance.proc_analyze_statistiche_job()`: passa dal giornale, come
  `proc_guardiano_digest_job`:
  `fn_run_and_log(p_jobname := '<codice>', p_stepname := 'analyze', p_sql := 'SELECT maintenance.fn_analyze_statistiche();')`.
* **Job pgAgent** in `85_pgagent`, ricalcato su `20260911-17` (classe `Routine Maintenance`,
  idempotente col `DELETE` per nome, step `CALL` della procedura, `MARK_RAN` dove pgAgent non c'è).
  Una volta per notte, a un orario lontano dalle automazioni delle 21 e dai job di mezzanotte e
  delle sei (D-2).

⚠️ **Una transazione sola.** La CI chiama la procedura dentro la transazione del changeSet (nessuna
procedura del catalogo fa `COMMIT`), quindi il verbo non può fare `COMMIT` fra una tabella e
l'altra. Conseguenza da sapere: `ANALYZE` tiene un lock `SHARE UPDATE EXCLUSIVE` su ogni tabella
fino alla fine della transazione. Non blocca letture né scritture; blocca DDL, un altro `ANALYZE` e
l'autovacuum sulla stessa tabella. È il motivo dell'orario lontano dagli altri job.

### 4.2 L'autoverifica — il job dice quando non ci è riuscito

`ANALYZE` **non fallisce** su una tabella che non può analizzare: la salta con un `WARNING`. Senza
un controllo, un job che salta metà delle tabelle scrive «done» nel giornale.

Subito dopo `ANALYZE`, nella stessa transazione, il verbo cerca le tabelle del perimetro (§4.3)
ancora senza statistiche e, se ce n'è anche una sola, **solleva** con un codice registrato
(`E_STATISTICHE_MANCANTI`, da aggiungere al catalogo dei messaggi) che le nomina.
`fn_run_and_log` scrive la riga rossa fuori transazione, e da lì la vedono il panorama e il digest
come ogni altro job fallito.

Il criterio è **strutturale**, e per questo non dipende dall'orologio:

* `pg_class.reltuples < 0` — la tabella non ha mai avuto un `ANALYZE` né un `VACUUM`. Sta nel
  catalogo, quindi sopravvive a un crash (i contatori di `pg_stat_*` no);
* `NOT has_table_privilege(oid, 'MAINTAIN')` per il ruolo che esegue — la tabella che il job
  **salterebbe**. Questo copre anche la tabella già analizzata in passato, che `reltuples` non
  distingue.

⭐ La verifica sta **nel job** e non in una vista guardata dal digest, perché lì ha un senso preciso:
subito dopo `ANALYZE`, una tabella senza statistiche è un errore. Guardata in un'ora qualunque, la
stessa riga sarebbe anche la tabella creata da una migrazione di oggi pomeriggio: un falso allarme
fino alla notte, cioè un presidio che dipende dal calendario (la classe di D16).

### 4.3 Il perimetro

Tutte le tabelle ordinarie e partizionate del database, **tranne**:

* gli schemi di sistema (`pg_catalog`, `information_schema`, `pg_toast`) e quelli temporanei;
* gli oggetti che appartengono a un'**estensione** (`pg_depend.deptype = 'e'`): `pgagent`, `pgtap`,
  PostGIS. Si escludono **per struttura**, non con un elenco di nomi da tenere aggiornato.

Il catalogo di sistema (`pg_proc` & co.) è D-1.

### 4.4 Chi esegue, e con che diritti

`ANALYZE` su una tabella richiede di esserne proprietari o di avere il privilegio `MAINTAIN`
(PostgreSQL 17+; il ruolo predefinito `pg_maintain` lo dà su tutte). Le tabelle sono del migratore
(`titodb` su dbdev, un altro ruolo in produzione), e pgAgent si collega col ruolo che ha la sua
configurazione.

⛔ Il diritto **non** si dà in un changeSet: un `GRANT` a un ruolo batch è vietato
(linee-guida-sql §11.6). Va nel provisioning, accanto al `USAGE` su `pgagent` già scritto in
[liquibase-setup-workflow.md](../../liquibase-setup-workflow.md) §2. Se il ruolo non ha il diritto,
l'autoverifica (§4.2) lo dice la prima notte, nominando le tabelle.

### 4.5 In CI — la convergenza che c'è già

La riga in `dbops.processi` dichiara `ci_ordine` + `ci_procedura`. Così `20260926-10` chiama la
procedura in `ci_apply`, dopo il caricamento e prima dei pgTAP, e pretende nel giornale una riga
riuscita di quel giro. Il `ci_ordine` è **l'ultimo** del catalogo: si analizza dopo che le
automazioni hanno creato le tabelle di storico.

⇒ In CI i pgTAP partono da statistiche reali, e l'autoverifica gira anche lì: un ruolo senza
diritti o una tabella saltata fermano la migrazione invece di passare in silenzio.

### 4.6 La riga del catalogo

`dbops.processi` (dal CSV di `80_data`, append): codice = `jobname_pgagent`, classe `MANUTENZIONE`,
canale `PGAGENT`, `segno_di_vita = GIORNALE`, `tolleranza_minuti` **`NULL`** (corretto in scrittura:
il CHECK `chk_processi_contratto_solo_command` la ammette solo per i `COMMAND`; per un job pgAgent
la cadenza il panorama la legge da pgAgent), `ci_ordine` ultimo, `ci_procedura` con la firma per esteso.
Il panorama la guarda da solo: `JOB_ASSENTE`, `JOB_SPENTO`, `MAI_PARTITO`, `GIRA_E_NON_REGISTRA`.
Controllare in scrittura se il codice vuole anche righe in `dbops.presidi`/`presidi_testi` per il
nuovo codice d'errore.

## 5. Il lavoro (team DB)

1. **Verbo** `maintenance.fn_analyze_statistiche()` col perimetro del §4.3 e l'autoverifica del
   §4.2; COMMENT che dice perché la verifica sta nel job.
2. **Codice d'errore** `E_STATISTICHE_MANCANTI` nel catalogo dei messaggi, con le tabelle nel
   dettaglio (format a segnaposto, attenzione ai `%`).
3. **Procedura** `maintenance.proc_analyze_statistiche_job()` che passa dal giornale.
4. **Riga in `dbops.processi`** (CSV, append) col §4.6; `test-processi-convergenza-ci` la pretende.
5. **Job** in `85_pgagent`, ricalcato su `20260911-17`.
6. **pgTAP** `maintenance/test-fn-analyze-statistiche-v1` che si costruisce il caso: una tabella
   nuova in uno schema di progetto, dentro la transazione del test, risulta senza statistiche;
   dopo il verbo non più; una tabella senza `MAINTAIN` per il ruolo fa sollevare il verbo col suo
   codice. ⚠️ Il verbo analizza tutto il database: misurare quanto ci mette in CI, col tetto dei
   90 s per file; se serve, il verbo prende un perimetro facoltativo **in coda** alla firma, che il
   test usa per restringere.
7. **Pagine `manual/`** del verbo e della procedura; riga nella pagina `manual/` di `processi` se
   l'elenco dei job sta lì.
8. **Provisioning**: la riga del diritto `MAINTAIN` (o `pg_maintain`) per il ruolo di pgAgent in
   `liquibase-setup-workflow.md` §2.

### 5.6 La prova dopo l'apply (Tid)

* corsa pgTAP: verdi, e `test-processi-convergenza-ci` verde;
* su dbdev, il giorno dopo: la riga del job in `maintenance.job_run_log` riuscita; nessuna tabella
  del perimetro con `reltuples < 0`;
* su `zeroerp_ci`: la riga del job nel giornale del giro `ci_apply`.

## 6. Decisioni — ✅ prese da Tid il 2026-10-14, tutte come proposte

Il ruolo di pgAgent su dbdev: Tid non lo ricorda; dalle connessioni attive è con ogni probabilità
`postgres` (superuser). L'autoverifica lo conferma o lo smentisce la prima notte. Produzione: non c'è.

* **D-1 — Il catalogo di sistema.** `ANALYZE` lanciato dal proprietario del database analizza anche
  i cataloghi; un altro ruolo li salta. Lo stimatore di `pg_proc` ha già fatto un falso rosso
  (12-10). Proposta: dentro il perimetro **se** il ruolo del job è il proprietario del database,
  ma fuori dall'autoverifica, perché i diritti sui cataloghi non sono nostri da dare.
* **D-2 — L'orario.** Proposta: 02:30, lontano dalle automazioni delle 21, dal job delle 00:05 e
  da quello delle 06:00.
* **D-3 — Il ruolo di pgAgent e il diritto.** `pg_maintain` (tutte le tabelle, comprese le
  future) o `MAINTAIN` tabella per tabella (da rifare a ogni tabella nuova). Proposta:
  `pg_maintain`, nel provisioning. Dipende dalla risposta del passo 2 della tabella in cima.
* **D-4 — Anche la freschezza?** L'autoverifica copre «mai analizzata» e «non analizzabile». Non
  copre «il job non è girato da una settimana»: quello lo copre già il panorama dalla tolleranza
  del processo. Proposta: niente presidio in più.

## 7. Il lavoro fatto (2026-10-14, sessione DB)

### 7.1 Che cosa c'è

| Pezzo | Dove |
| --- | --- |
| Vista del perimetro e della prova: `maintenance.vw_statistiche_mancanti` | `20_code/maintenance/20261014-50` |
| Verbo con autoverifica: `maintenance.fn_analyze_statistiche(p_tabelle regclass[] DEFAULT NULL)` | `20_code/maintenance/20261014-51` |
| Wrapper dal giornale: `maintenance.proc_analyze_statistiche_job()` | `20_code/maintenance/20261014-52` |
| Job pgAgent `analyze_statistiche`, ogni notte alle 02:30 | `85_pgagent/20261014-53` |
| Processo 48 `analyze_statistiche`, `ci_ordine` 900 | `80_data/sql/dbops/processi.csv` |
| `E_STATISTICHE_MANCANTI` (`TECNICO`), messaggio id 1320 | `config/codici_errore.csv`, `config/messaggi_errore.csv` |
| pgTAP (plan 10) | `db/pgtap/maintenance/test-fn-analyze-statistiche-v1.sql` |
| Pagine `manual/` | `maintenance/manual/{fn_analyze_statistiche,vw_statistiche_mancanti,proc_analyze_statistiche_job}.md` |
| La vista nel catalogo dei presidi: `CANCELLO` (il cancello è il job stesso), `chi_agisce` `SISTEMISTA`, testo generico italiano — trovato dalla corsa pgTAP di Tid, `test-catalogo-presidi-v1` test 2 | `80_data/sql/dbops/presidi.csv`, `presidi_testi.csv` |
| Provisioning | `liquibase-setup-workflow.md` §2 |
| Guida | `guide/statistiche-del-planner.md` (nuova, in `mkdocs.yml`, `mkdocs.zensical.yml`, `readme.md`); il panorama pgAgent in `guide/processi-automatici-classe-e-identita.md` §4-bis |

Scelte fatte scrivendo, sul modello:

* il perimetro sta in **una** vista, letta sia dal verbo sia dal pgTAP: un predicato solo;
* la **partizionata senza partizioni** è fuori: non ha dati da descrivere, e dopo `ANALYZE` resta a
  `reltuples = -1` (provato su PG 18.6). Dentro, il job fallirebbe per sempre;
* le **temporanee della sessione corrente** sono dentro: è ciò che lascia al pgTAP, che gira come
  `zeroerp_app` e non può creare tabelle di progetto, costruire il suo caso;
* numeri `-50…-53` invece di `-21`: l'altra sessione stava scrivendo `-08…-20` in parallelo.

### 7.2 Una ricaduta trovata provando: il diritto in CI

Provando sul percorso vero (`CALL` → giornale → verbo, scratch `zeroerp_ci`, transazione annullata)
l'autoverifica ha fatto il suo mestiere: `ANALYZE` come `zeroerp` ha saltato con un `WARNING`
`databasechangelog`, `databasechangeloglock` e `internal.project_metadata` (più `version_info` nella
corsa vera), che il **provision-pre crea come `postgres`**. In CI `ci_apply` gira come `zeroerp`:
senza un diritto in più la CI sarebbe rossa.

È D-3 applicata alla CI: `GRANT pg_maintain TO zeroerp` nel passo di bootstrap che già concede le
tabelle di Liquibase, in **tre** posti che devono restare gemelli: `.github/workflows/ci.yaml`
(«Grant CREATE on public»), `.github/workflows/ci-validate.yaml` («Grant Liquibase tables to
zeroerp»), `scripts/ci-local.sh` («grant post-provision»).

### 7.3 ⚠️ Lo scratch, alle 17:47

Mentre scrivevo, `zeroerp_ci` è stato ricostruito e ha preso i changeSet `-50…-53`, che erano
già nell'albero. Il `ci_apply` di quella corsa ha chiamato il job e il job è **fallito**: riga
`ok = false` in `maintenance.job_run_log` alle 17:47:31, con le quattro tabelle nominate. Il presidio
funziona; manca il diritto. ⇒ passo 1 della tabella in cima, poi si rilancia il `ci_apply`.
⚠️ I file `-50…-53` sono applicati sullo scratch: da qui non si modificano più (checksum).

### 7.4 Le prove

* **SQL estratto** dagli YAML, `zeroerp_ci`, transazione annullata, come owner: il pgTAP **10/10**
  (6 e 7 sono `skip` dichiarati: come owner il caso negativo non si costruisce);
  `plpgsql_check` pulito sul verbo e sulla procedura.
* **Caso negativo come `zeroerp_app`** su dbdev, con copie in `pg_temp`: `maintenance.job_run_log`
  è `NON_ANALIZZABILE` e il verbo solleva `E_STATISTICHE_MANCANTI` (P0001, codice nel canale
  `CONSTRAINT`); su una temporanea propria ritorna 0.
* **Tempo**: `ANALYZE` di tutto lo scratch (66 MB) 110 ms. Fatto datato, non un motivo.
* ⚠️ **Non provati da me**: i presidi trasversali (`test-processi-convergenza-ci`,
  `-jobname-wrapper`, `-registro`, `test-catalogo-messaggi-errore-completo`, `test-riferimenti-morti-v1`,
  `test-rubinetto-primo-motivo-v1`): lo scratch era a metà ricostruzione e rompeva anche la corsa
  senza il mio lavoro. Restano alla corsa di Tid (passo 2).

## 8. Trovato al primo giorno: il presidio di pgAgent (2026-10-14, sera)

**Il fatto.** Alle 22 il pannello dei presidi mostrava `analyze_statistiche` come `MAI_PARTITO /
JOB_MAI_PARTITO`, «il programmatore dei lavori del database non sta girando». Falso: pgAgent era vivo
(gli altri 14 job `OK`, `guardiano_digest` alle 21:20), e il job era solo in attesa della prima corsa
delle 02:30.

**Il difetto, sul modello.** `dbops.vw_processi_programmazione` deduceva «il demone non gira» da «il
job non ha mai girato». Falso allarme su ogni job nuovo fino alla prima corsa, e **silenzio** sul
demone fermo per ogni job che aveva già girato: il caso per cui il testo esiste non si vedeva mai.

**La cura** (decisione di Tid, 2026-10-14): il segnale è la **corsa dovuta e non fatta**,
`jobnextrun` passato da più di un'ora.

| Pezzo | Dove |
| --- | --- |
| La vista: `MAI_PARTITO` solo se in ritardo, `IN_ATTESA` (senza causa), `IN_RITARDO` / `JOB_IN_RITARDO` | `20_code/dbops/20261014-54` |
| Causa `JOB_IN_RITARDO`: chi agisce `SISTEMISTA`, testo italiano | `80_data/sql/dbops/presidi_cause.csv`, `presidi_testi.csv` |
| pgTAP: plan 16 → 18, ricetta per `JOB_IN_RITARDO`, costruzioni con `jobnextrun` esplicito | `db/pgtap/dbops/test-presidio-processi-testo-per-causa-v1.sql` |
| Pagina `manual/` | `dbops/manual/vw_processi_programmazione.md` |

⚠️ La regola resta nel `CASE` e **non** in una funzione pura, come avevo proposto: il pgTAP del
presidio fa il censimento delle cause leggendo `pg_get_viewdef`, e spostarla lo renderebbe cieco
proprio su questi rami.

**Prove** (SQL estratto, `zeroerp_ci` come `zeroerp`, che lì può scrivere `pgagent.pga_job`;
transazione annullata). Prima (corpo vivo): test 17 rosso (il demone fermo resta fuori dal presidio)
e 18 rosso (`MAI_PARTITO/JOB_MAI_PARTITO/true`: il falso allarme del 14-10). Dopo: **18/18**, nessuno
skip. Invariati prima e dopo: `test-vw-processi-programmazione` (21 + 6 skip), `test-fn-guardiano-digest`
(9), `test-presidi-testi-v1` (19). ⚠️ Su un ambiente dove il runner non può scrivere `pga_job` (la CI)
i test 11, 12, 13, 17 e 18 sono `skip` dichiarati, come prima.

Dopo l'apply la riga di stasera diventa `IN_ATTESA` ed esce dal presidio; dopo le 02:30, `OK`.
