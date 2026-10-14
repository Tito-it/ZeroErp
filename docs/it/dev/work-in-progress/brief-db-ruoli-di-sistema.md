# Brief DB — I ruoli di sistema: nomi fissi, un provisioning solo, uguali ovunque

## ⏭️ Chi riparte — aggiornato al 2026-10-14

**Riparte: Tid — apply della fase 1-bis (§8) e la corsa delle 21:00. Poi il team DB con la fase 1, che
ha bisogno di un superuser per la prova.**

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ **Tid** | Decisioni D-1 … D-5 | §7 | — |
| 2 | ✅ **team DB** | Fase 1-bis: le 16 procedure dei job `DEFINER` (`20261014-55`), presidio `maintenance/test-proc-job-definer-v1`, provato sullo scratch | §8 | — |
| 3 | ✅ **Tid** | Tolta a mano la firma orfana `proc_apply_fk_index_policy_job()`; `-55` applicato su dbdev | §8.3 | — |
| 3-bis | **Tid** | Apply del `20261014-56` (il `search_path` nella forma di casa) e corsa pgTAP | §8.4 | niente |
| 4 | **Tid** | La sera dopo l'apply: le automazioni delle 21:00 nel giornale, riuscite (primo giro come `titodb` invece di `postgres`) | §8.3 | 3 |
| 5 | ✅ **team DB** | Fase 1: `scripts/sql/provision_zeroerp.sql` e `ci-local.sh` (default dal 2026-10-15; il modo vecchio con `--classico`), scritti e provati per quanto si può senza superuser | §9 | — |
| 5-bis | ✅ **Tid** | `scripts/ci-local.sh --fresh --ci-apply`: completato il 2026-10-14 (al secondo giro, §9.4) | §9.3 | — |
| 5-ter | ✅ **team DB** | Verifiche sullo scratch `zeroerp_ruoli`: postura dei ruoli, un owner solo, due presidi mirati | §9.4 | — |
| 5-ter-bis | ✅ **Tid** | La suite pgTAP intera su `zeroerp_ruoli`: **nessuna regressione** rispetto alla baseline di `zeroerp_ci` (2026-10-15) | §9.4 | — |
| 5-ter-ter | **Tid** | La baseline dello scratch rifatta su `zeroerp_ruoli` (`--update`), dopo aver guardato i rientrati | §10 | niente |
| 5-quater | **team DB** + **Tid** | Il presidio D-5: due changeSet (uno nel contesto `provision`, da superuser) | §7 D-5 | 5-ter |
| 6 | 🔨 **team DB** | Fase 2: i due workflow di GitHub sul modello, scritti (§11); prova sul cluster usa-e-getta | §11 | — |
| 6-bis | **Tid** | Push e prima corsa vera su GitHub; la baseline della CI va guardata | §11.4 | 6 |
| 7 | **Tid** | Fase 3: allineare dbdev (owner, `titodb` membro con `SET role`, pgAgent come `zeroerp_job`, Liquibase) — da superuser, in una finestra | §6 | 4, 6 |
| 8 | **team DB** | Fase 4: documentazione d'installazione e ritiro dei vecchi script e ruoli | §6 | 7 |

**Decisioni aperte di Tid: nessuna.** Prese il 2026-10-14: owner `zeroerp_owner`; D-1 … D-5 come
proposte, con la precisazione di Tid su D-5 (si controlla la membership, non il nome) e la sua
ricaduta su D-1 (§7).
⬜ Da committare: questo documento, `20261014-55`, `20261014-56`, `db/pgtap/maintenance/test-proc-job-definer-v1.sql`,
`scripts/sql/provision_zeroerp.sql`, `scripts/ci-local.sh`.

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-10-14. **A chi:** Tid, poi il team DB.
> **Origine:** il cantiere delle statistiche
> ([brief-db-statistiche-tabelle-job-notturno](brief-db-statistiche-tabelle-job-notturno.md) §7.2-§7.3):
> il job ha trovato in CI tabelle create da `postgres` che `zeroerp` non poteva analizzare. Proposta
> di Tid: dare ruoli standard «di sistema», da non riconfigurare a ogni installazione.
> **Stato:** 🔨 fase 1-bis scritta e provata (§8, 2026-10-14); il resto da fare.
> **Ricadute BE/FE:** nessuna sul codice (il backend resta `zeroerp_app`). Ricadute su documentazione
> d'installazione e configurazione dei server.

## 1. La regola

ZeroERP porta con sé un **modello di ruoli fisso**: nomi, attributi e diritti sono parte del
prodotto, come le tabelle. Un solo script idempotente li crea e li allinea, e lo stesso script
costruisce la CI, il database di prova e un'installazione nuova.

* **I nomi sono di sistema e non si configurano.** Il database li nomina: `zeroerp_app` compare
  scritto **863** volte fra changeSet, script e workflow (grant, policy, presidi; conteggio del
  2026-10-14). Un nome diverso darebbe un database che si rompe in silenzio.
* **Le password non hanno default.** Le chiede o le genera chi installa; non stanno nel repo.
* **Chi vuole personalizzare aggiunge, non rinomina.** Un utente suo (`mario_dba`) diventa membro
  del ruolo di sistema (`GRANT zeroerp_app TO mario_dba`): il modello resta intatto.
* **Sviluppo, CI e installazione usano lo stesso modello.** Un diritto mancante si vede in CI, non
  la prima notte su un server.

## 2. Che cosa c'è oggi (fatti datati 2026-10-14)

### 2.1 I ruoli nel cluster di sviluppo

| Ruolo | Superuser | Login | BYPASSRLS | Membro di | Che cosa fa |
| --- | --- | --- | --- | --- | --- |
| `postgres` | ✅ | ✅ | ✅ | — | provisioning; **pgAgent** (`pgagent.service`: `user=postgres dbname=zeroerp`) |
| `titodb` | — | ✅ | — | — | **owner** degli oggetti e del database `zeroerp`; Liquibase (`db/liquibase.properties`) |
| `zeroerp` | — | ✅ | — | `pg_maintain` | owner sullo scratch `zeroerp_ci`; il migratore della CI |
| `zeroerp_app` | — | ✅ | — | — | il backend |
| `zeroerp_log` | — | ✅ | — | — | il canale di log via `dblink` |
| `zeroerp_batch_fatturazione` | — | ✅ | ✅ | — | **in ritiro**: il backend non lo usa più dal 2026-09-05 |
| `pgagent` | — | ✅ | — | — | **nessuno**: pgAgent si collega come `postgres` |

### 2.2 Dove nascono

| Pezzo | Sede | Nota |
| --- | --- | --- |
| `zeroerp_app` | `scripts/sql/provision_db_roles.sql` | il nome è una variabile (`-v app_role`), ma il database lo pretende letterale: **configurabilità finta** |
| il migratore | nessuna: «il ruolo con cui si crea il database» | `migrator_role` ha default **`titodb`**, cioè l'utente di sviluppo, in `provision_db_roles.sql` e `provision_dblink_log_channel.sql` |
| `zeroerp_log` | `scripts/sql/provision_dblink_log_channel.sql` | |
| il batch | `scripts/sql/provision_db_role_batch_fatturazione.sql` (+ `retire_…`, `check_…`) | da ritirare (`provisioning-db-roles.md` §«in ritiro») |
| lo scope delle shadow | `scripts/sql/provision_storico_scope.sql` | esiste **perché** pgAgent crea shadow come `postgres` (68 su 121 al 2026-09-11) e va riassegnato a mano |
| diritti ad hoc | `.github/workflows/ci.yaml`, `ci-validate.yaml`, `scripts/ci-local.sh` | ognuno ha il suo passo di bootstrap con i suoi `GRANT` (le tabelle di Liquibase, `pg_maintain`, `CREATE` su `public`…) |

Documentazione: [provisioning-db-roles.md](../backend/provisioning-db-roles.md),
[liquibase-setup-workflow.md](../../liquibase-setup-workflow.md) §2.

### 2.3 Tre ambienti, non due

| | dbdev (`zeroerp`) | scratch (`zeroerp_ci`, `scripts/ci-local.sh`) | CI GitHub |
| --- | --- | --- | --- |
| Estensione pgAgent | sì | **sì** | no |
| ChangeSet di `85_pgagent` | eseguiti | **eseguiti**: 16 job creati | `MARK_RAN` |
| Chi esegue i job | il demone (`pgagent.service`, `dbname=zeroerp`) | **nessuno**: il demone serve solo `zeroerp`; il lavoro lo fa la convergenza di `ci_apply` | la convergenza di `ci_apply` |
| Owner degli oggetti | `titodb` | `zeroerp` (il database è di `postgres`) | `zeroerp` |

⚠️ Sullo scratch il panorama dei processi dice `MAI_PARTITO` per i job la cui corsa è passata (11 su 16
il 2026-10-14): è vero, nessuno li fa partire. ⭐ Ed è l'unico ambiente costruito da zero **con**
pgAgent: il banco di prova di D-2 da capo a fondo, con un **secondo demone** pgAgent collegato a
`zeroerp_ci` come `zeroerp_job`, senza toccare dbdev (fase 1-bis).

### 2.4 Dove il modello si spezza

* **Due owner.** `titodb` su dbdev, `zeroerp` in CI. Una funzione `SECURITY DEFINER` gira come
  il suo proprietario, quindi la stessa funzione ha due identità in due ambienti.
* **Tre migratori in CI.** Il provision-pre gira come `postgres` e crea `databasechangelog`,
  `databasechangeloglock`, `internal.project_metadata`, `version_info`; il resto di Liquibase e
  `manage.py migrate` come `zeroerp`. Da qui i `GRANT` di raccordo in ogni workflow, e il
  `pg_maintain` del 14-10.
* **pgAgent superuser.** I lavori di manutenzione fanno DDL (shadow di storico, trigger, indici
  delle FK): girando come `postgres` creano oggetti che non sono del migratore. Da qui
  `provision_storico_scope.sql`, che li riassegna a posteriori.
* **Privilegi dati a mano.** Il caso tipico è stato `django.auth_user` per `zeroerp_app`: esisteva
  solo su dev (linee-guida-sql §11.9).

## 3. Il modello proposto

| Ruolo | Login | Attributi | Chi lo usa | Diritti |
| --- | --- | --- | --- | --- |
| **`zeroerp_owner`** | ✅ | non superuser, `NOBYPASSRLS` | Liquibase (tutte le passate tranne quella da superuser), `manage.py migrate` | proprietario di **tutti** gli oggetti del progetto **tranne le funzioni che `dbops.sec_functions_owner` vuole di un superuser** (§9.2), compreso lo schema `django` e le tabelle di Liquibase; `pg_maintain` non serve, perché possiede tutto; il DML su `pgagent` per i changeSet di `85_pgagent` |
| **`zeroerp_job`** | ✅ | non superuser, `NOBYPASSRLS`, **non possiede niente** | il demone **pgAgent** (D-2) | il DML sulle tabelle di `pgagent` che servono al demone; `EXECUTE` **solo** sulle procedure dei job (`maintenance.proc_*_job`), che girano come `zeroerp_owner` (§3.1) |
| **`zeroerp_app`** | ✅ | `NOBYPASSRLS`, non owner | il backend | quelli di oggi, da `provision_db_roles.sql` |
| **`zeroerp_log`** | ✅ | — | il canale di log via `dblink` | solo `INSERT` su `dbops.error_log` |
| `postgres` | — | superuser | **solo** il provisioning | — |

* **`COMMENT ON ROLE zeroerp_owner`**: «Proprietario degli oggetti di ZeroERP — progetto di Tid
  (Michele Carlo Titini)». La firma sta lì, e nel copyright di ogni file.
* **Spariscono** `zeroerp_batch_fatturazione` (il ritiro già scritto) e `pgagent` (inutilizzato,
  D-4).
* **Il superuser non lavora**: crea i ruoli, le estensioni e il database, poi passa la mano. Ciò
  che oggi fa da superuser per necessità (i `GRANT` sulle tabelle di Liquibase, lo scope delle
  shadow) non serve più, perché un owner solo possiede tutto.

### 3.1 I job: `zeroerp_job` chiama, il lavoro gira come owner

pgAgent si collega come `zeroerp_job`, che può **solo chiamare** le procedure dei job. Le
procedure (`maintenance.proc_*_job`) sono `SECURITY DEFINER` di proprietà di `zeroerp_owner`:
quando partono girano come il proprietario, e ciò che creano (shadow di storico, trigger, indici
delle FK) nasce di `zeroerp_owner`.

| | pgAgent come `postgres` (oggi) | pgAgent come `zeroerp_owner` | **`zeroerp_job` + procedure `DEFINER`** |
| --- | --- | --- | --- |
| Chi possiede ciò che i job creano | `postgres` (da riassegnare) | `zeroerp_owner` | `zeroerp_owner` |
| Che cosa può fare uno step scritto a mano | tutto | tutto sul progetto | solo chiamare le procedure dichiarate |
| Il giornale distingue la corsa notturna da una a mano | no | no | sì: `session_user` = `zeroerp_job` |
| Il login dell'owner serve anche a pgAgent | — | sì | no: solo ai migratori |

⚠️ **Il prezzo, dichiarato:**

* le procedure dei job sono **16** (2026-10-14, nessuna `DEFINER` oggi), e ognuna va convertita
  con un changeSet suo, preso dal corpo vivo;
* ⛔ **il `search_path`** di una `DEFINER` va fissato (igiene di sicurezza), ma uno troppo stretto
  **acceca le funzioni `INVOKER` chiamate dentro**, che risolvono i nomi col `search_path` del
  chiamante (è già successo in questo progetto). Si sceglie procedura per procedura, e ognuna si
  prova con la corsa pgTAP che la attraversa: non è una modifica meccanica;
* una `DEFINER` non può fare `COMMIT`: oggi nessuna procedura dei job lo fa, e la convergenza in
  CI ci conta già;
* `proc_apply_fk_index_policy_job` esiste in **due** firme su dbdev (`()` e `(p_populate boolean)`):
  il job chiama la seconda. ✅ **La prima è un residuo**: nessun changelog la crea, e lo scratch
  costruito da zero non ce l'ha (§8.3).
  ⚠️ La doc auto-generata ne mostra **una sola**, quella senza argomenti: il generatore fa una
  pagina per nome, e con due firme una sparisce. Il corpo della firma che il job chiama si prende
  dal database (`pg_get_functiondef`), non dalla doc;
* ✅ **gli step dei job, letti sul vivo** (2026-10-14, dalla pagina generata
  `dbzero/maintenance/job_pgagent.md`): tutti e **16** sono `CALL maintenance.proc_*_job()`, e quello
  degli indici FK chiama la firma `(true)`. Con `zeroerp_job` nessuno step si rompe. Nei changeSet
  storici di `85_pgagent` compaiono anche `SELECT` dirette: sono versioni sostituite, non il vivo.

## 4. Il provisioning unico

Un punto d'ingresso solo, idempotente, da superuser, in due fasi perché alcune cose esistono solo
dopo le migrazioni:

1. **Prima delle migrazioni**: crea i ruoli (password chieste o passate, mai di default), il
   database con owner `zeroerp_owner`, le estensioni; dà a `zeroerp_owner` e a `zeroerp_job` ciò
   che serve sullo schema `pgagent`.
2. **Dopo le migrazioni** (Liquibase e `manage.py migrate`): la postura di `zeroerp_app`
   (l'attuale `provision_db_roles.sql`, senza più variabili sui nomi), il canale di log, e
   l'`EXECUTE` di `zeroerp_job` sulle procedure dei job (⚠️ in un changeSet no: è un ruolo di
   sistema, ma il grant a un ruolo che nasce fuori da Liquibase segue la regola di
   linee-guida-sql §11.6 — da confermare in scrittura se `zeroerp_job` la ricade).

Lo stesso ingresso lo usano `ci.yaml`, `ci-validate.yaml`, `scripts/ci-local.sh` e
l'installazione. I passi di bootstrap con i `GRANT` sparsi nei workflow spariscono.

## 5. I presidi

* **Postura per ruolo** — un pgTAP per ruolo che dice che ha **esattamente** gli attributi e i
  diritti del modello, sul calco di `rls/test-role-batch-fatturazione-postura.sql`.
* **Un owner solo** — nessun oggetto del progetto (tabelle, viste, funzioni, sequenze, schemi;
  esclusi gli oggetti delle estensioni e gli schemi che le ospitano) posseduto da un ruolo diverso
  da `zeroerp_owner`, **tranne le funzioni dichiarate in `dbops.sec_functions_owner`** (§9.2). È il
  presidio che avrebbe visto le shadow di `postgres` e le tabelle di Liquibase in CI. Oggi è la
  verifica finale di `provision_zeroerp.sql` (fase `post`).
* **Le procedure dei job girano come owner** — ogni `maintenance.proc_*_job` è `SECURITY
  DEFINER`, di `zeroerp_owner`, con `search_path` fissato; `zeroerp_job` ha `EXECUTE` su quelle e
  su nient'altro del progetto. Il perimetro è il nome (`proc_%_job`), come per il presidio dei
  jobname, così una procedura nuova ci entra da sola.
* **Nessun superuser al lavoro** — il giornale registra con che ruolo è girata ogni corsa; una
  vista di presidio pretende che l'ultima corsa `PGAGENT` di ogni processo sia di un ruolo **membro**
  di `zeroerp_job`, non superuser e non membro di `zeroerp_owner` (D-5: la membership, non il nome).

## 6. Le fasi

1. **Il provisioning unico e i presidi**, provati su uno scratch costruito da zero
   (`ci-local.sh` su un database nuovo).
1-bis. **Le procedure dei job `DEFINER`** (§3.1): un changeSet per procedura, dal corpo vivo, col
   `search_path` scelto e provato; il presidio sulle procedure. Funziona già con l'owner di oggi,
   quindi può precedere le fasi 2 e 3. La prova da capo a fondo sullo scratch: un secondo demone
   pgAgent su `zeroerp_ci` come `zeroerp_job` (§2.3), una notte di corse, il giornale.
2. **CI e `ci-local.sh`** passano a `zeroerp_owner`: un cambio di utente nei workflow (Liquibase,
   `manage.py migrate`, l'env file del runner pgTAP), e l'ingresso unico al posto dei bootstrap.
3. **dbdev si allinea**, da superuser e in una finestra concordata:
   `REASSIGN OWNED BY titodb TO zeroerp_owner` per ciò che è di `titodb`; per gli oggetti del
   progetto posseduti da `postgres` un `ALTER … OWNER TO` **oggetto per oggetto**, letto dal
   presidio «un owner solo» (⛔ mai `REASSIGN OWNED BY postgres`: prenderebbe anche il sistema); le
   `ALTER DEFAULT PRIVILEGES` rifatte per il nuovo owner, `db/liquibase.properties`,
   `pgagent.service` (`user=zeroerp_job`, con la sua password in `.pgpass`), il registro
   `sec_functions_owner` riallineato.
   ⚠️ È il passo delicato: cambia il proprietario di ogni funzione `SECURITY DEFINER`, quindi va
   seguito dalla corsa pgTAP completa.
4. **Documentazione e ritiro**: `provisioning-db-roles.md` e la guida d'installazione riscritte
   sul modello; ritirati i vecchi script e le loro variabili; ritirati il ruolo batch e `pgagent`.

## 7. Decisioni — ✅ tutte prese da Tid il 2026-10-14

* ✅ **D-1 — Il nome `titodb` su dbdev** (Tid, 2026-10-14): dbdev si allinea al modello (fase 3) e
  `titodb` resta l'utente **personale** di Tid, membro di `zeroerp_owner`
  (`GRANT zeroerp_owner TO titodb`): il «chi personalizza aggiunge» del §1.
  ⚠️ **La membership da sola non basta**: un oggetto creato da una sessione di `titodb` nasce di
  `titodb`, non dell'owner, e «un owner solo» si romperebbe al primo changeSet. Quindi
  `ALTER ROLE titodb SET role = zeroerp_owner` (ogni sessione di `titodb` lavora come proprietario),
  oppure Liquibase si collega direttamente come `zeroerp_owner`. Il presidio «un owner solo» (§5)
  se ne accorge comunque. Vale per qualunque utente personale membro di un ruolo di sistema che
  crea oggetti.
* ✅ **D-2 — Con chi gira pgAgent** (Tid, 2026-10-14): **`zeroerp_job`**, che può solo chiamare
  le procedure dei job; le procedure sono `SECURITY DEFINER` di `zeroerp_owner`, quindi il lavoro
  gira come il proprietario (§3.1). Scartati `postgres` (crea oggetti col padrone sbagliato) e
  `zeroerp_owner` (uno step scritto a mano potrebbe fare qualunque cosa sul progetto).
* ✅ **D-3 — Le password** (Tid, 2026-10-14): lo script le prende da variabili o da un file fuori dal repo, e
  se mancano si ferma; in CI restano i letterali di oggi, che sono di un database usa e getta.
* ✅ **D-4 — I ruoli da ritirare** (Tid, 2026-10-14): `zeroerp_batch_fatturazione` col suo script di ritiro
  (già pronto) nella fase 4, e `pgagent` nello stesso giro.
* ✅ **D-5 — Dove si presidia «nessun superuser al lavoro»** (Tid, 2026-10-14, con una correzione
  sua). Il giornale registra con che ruolo è girata ogni corsa (`session_user` in
  `maintenance.job_run_log`). ⛔ **Si controlla che cosa può fare il ruolo, non come si chiama**:
  chi installa può far girare pgAgent con un suo utente membro di `zeroerp_job`, e un controllo sul
  nome darebbe un falso rosso. Una corsa `PGAGENT` è in regola se il suo ruolo
  * è membro di `zeroerp_job` (`pg_has_role(…, 'zeroerp_job', 'MEMBER')`, vero anche per
    `zeroerp_job` stesso);
  * non è superuser (`pg_roles.rolsuper`);
  * non è membro di `zeroerp_owner` (lavorerebbe come proprietario senza passare dalle procedure).

  La forma: una **vista di presidio** di natura `ZERO` sull'ultima corsa `PGAGENT` di ogni processo
  (guarda il database vero, entra nel digest) e un **pgTAP che costruisce** i due casi (un ruolo
  membro di `zeroerp_job` passa, un superuser no). ⛔ Non un pgTAP che legge le corse esistenti: in
  CI non ce ne sono, e passerebbe per sottrazione. Una corsa lanciata a mano porta il nome di chi
  l'ha lanciata e non è un guasto (non è di origine `PGAGENT`).

  ⚠️ **Come si scrive il ruolo nel giornale** (trovato scrivendo la fase 1, 2026-10-14). Una corsa
  riuscita la scrive `maintenance.fn_run_and_log` nella sessione del job; una **fallita** la scrive
  `maintenance.fn_job_run_log_failure` via `dblink`, cioè in un'**altra** sessione (quella del canale
  di log). Quindi:
  * la colonna nuova **non** ha default `session_user` (nella riga del fallimento direbbe il ruolo
    del canale di log): la valorizzano le due funzioni;
  * `fn_job_run_log_failure` legge `session_user` nella sessione del job — è `DEFINER`, e
    `session_user` resta chi si è collegato — e lo passa nella `INSERT` via `dblink`;
  * ⛔ `fn_job_run_log_failure` è nel registro `dbops.sec_functions_owner`: è di un **superuser**
    in ogni ambiente (il provision-post la riassegna). Un changeSet della passata principale non
    può modificarla: il suo changeSet va nel contesto `provision`, come `90_end/20251123-12`.

## 8. Fase 1-bis — le procedure dei job `DEFINER` (2026-10-14, sessione DB)

### 8.1 Che cosa c'è

| Pezzo | Dove |
| --- | --- |
| Le 16 procedure `maintenance.proc_*_job`: `SECURITY DEFINER`, `search_path = public, topology, pg_temp`, `EXECUTE` tolto a `PUBLIC` | `20_code/maintenance/20261014-55` (`ALTER PROCEDURE`: i corpi restano quelli vivi) |
| Presidio: perimetro per nome (`proc_%_job`); `DEFINER`, `search_path` fissato, proprietario = proprietario dello schema, niente `EXECUTE` a `PUBLIC` né a `zeroerp_app`; `EXECUTE` a `zeroerp_job` dove il ruolo esiste (oggi skip dichiarato) | `db/pgtap/maintenance/test-proc-job-definer-v1.sql` (plan 7, come app) |

### 8.2 Le scelte, sul modello

* **Il `search_path`** è quello con cui i job girano **oggi**: il default del database
  (`"$user", public, topology`, da `pg_db_role_setting`; né pgAgent né `ci_apply` ne hanno uno
  loro). `"$user"` cade, `pg_temp` in coda. Nessuna funzione chiamata dentro vede un percorso
  diverso da prima.
* **`EXECUTE` tolto a `PUBLIC`**: con `DEFINER` chiunque lancerebbe le automazioni come
  proprietario. Censito: nessuna funzione del database e nessun punto del backend chiama le
  procedure; i pgTAP le nominano solo nei commenti; `maintenance` è fuori dal loop dei grant di
  `ci_apply` e dalla whitelist di `provision_db_roles.sql`, quindi il `REVOKE` non viene riaperto.
  L'`EXECUTE` a `zeroerp_job` lo darà il provisioning (§4).
* **`ALTER` e non `CREATE OR REPLACE`**: cambiano gli attributi, nessun corpo ricopiato.

### 8.3 Che cosa cambia su dbdev, e la prova

⭐ **Il lavoro notturno cambia identità**: oggi gira come `postgres` (il demone), dopo il `-55` come
`titodb` (il proprietario delle procedure). Censito il 2026-10-14: tabelle, viste, sequenze e
schemi del progetto sono tutti di `titodb`; di `postgres` restano sei funzioni `DEFINER` volute
(log via `dblink`, `tx_id`, verbale fuori transazione, registro degli owner), che `titodb` chiama
come oggi. Due effetti:

* gli oggetti che le automazioni creano nascono di `titodb`, non di `postgres`;
* le primitive delle automazioni che agiscono solo dove `current_user` è il proprietario
  (`fn_storico_arma_scope` & co.) di notte **saltavano** con un WARN; ora lavorano, come già in CI.

**Prove** (SQL estratto del `-55`, `zeroerp_ci` come `zeroerp`, transazione annullata):

* presidio: **prima** 4 rossi (2, 3, 5, 6), **dopo** 6 verdi + lo skip dichiarato del 7;
* la convergenza vera di `ci_apply` (`20260926-10`) dopo il `-55`: **12 job strutturali su 12
  riusciti**; i tre non strutturali (`guardiano_digest`, `sync_auth_user_expired`,
  `accoda_chiusura_scadenze`) chiamati uno per uno: «done»;
* invariati prima e dopo: `test-job-run-registrazione` (21), `-saltata-v1` (11), `-attore` (12),
  `-log-failure-out-of-tx` (6), `test-fn-analyze-statistiche-v1` (10), `test-processi-convergenza-ci`
  (8), `test-processi-jobname-wrapper` (4), `test-riferimenti-morti-v1` (9).

⚠️ **Il limite della prova**: sullo scratch chi esegue è già il proprietario, quindi il cambio
d'identità di dbdev non si riproduce lì. La prova vera è **la corsa delle 21:00** dopo l'apply
(passo 4 della tabella in cima).

⚠️ **L'orfano da togliere a mano, prima dell'apply** (passo 3): su dbdev esiste
`maintenance.proc_apply_fk_index_policy_job()`, senza argomenti, che nessun changelog crea e nessuno
chiama (il job chiama `(boolean)`). Il presidio la nominerebbe (non `DEFINER`, `EXECUTE` a `PUBLIC`).
Da titodb:

```sql
DROP PROCEDURE maintenance.proc_apply_fk_index_policy_job();
```

## 9. Fase 1 — il provisioning unico (2026-10-14, sessione DB)

### 9.1 Che cosa c'è

| Pezzo | Dove |
| --- | --- |
| Lo script del modello, tre fasi (`ruoli`, `pre`, `post`), da superuser, idempotente | `scripts/sql/provision_zeroerp.sql` |
| Il modello dei ruoli in `ci-local.sh` (default dal 2026-10-15; il modo vecchio con `--classico`): scratch `zeroerp_ruoli`, migratore `zeroerp_owner`, password da un file fuori dal repo; il modo classico resta identico (il migratore è una variabile, default `zeroerp`/`secret`) | `scripts/ci-local.sh` |

* **`ruoli`** (sul database `postgres`): crea `zeroerp_owner`, `zeroerp_job`, `zeroerp_app` se
  mancano (password obbligatoria solo per crearli; di un ruolo che esiste non la tocca, perché i
  ruoli sono di cluster); controlla la postura (né superuser, né `BYPASSRLS`, né `CREATEROLE`,
  con login) e la segnala invece di correggerla; il commento con la firma; il database con owner
  `zeroerp_owner`; `CONNECT` a job e app.
* **`pre`** (dopo il provision-pre di Liquibase): passa a `zeroerp_owner` schemi, relazioni e
  funzioni che il superuser ha creato; i diritti su `pgagent` per owner e job.
* **`post`** (alla fine): `EXECUTE` di `zeroerp_job` sulle procedure dei job; ripassa la
  proprietà; **verifica «un owner solo»** e, se trova un oggetto non suo, si ferma nominandolo.

La postura di `zeroerp_app` resta a `provision_db_roles.sql`, chiamato con
`-v migrator_role=zeroerp_owner`: l'unificazione dei file è la fase 4.

### 9.2 Che cosa ha corretto nel modello

* ⭐ **Le funzioni del registro `dbops.sec_functions_owner` sono di un superuser per scelta**, in
  ogni ambiente (il provision-post le riassegna): il canale `dblink` rifiuta la connessione senza
  password a chi non è superuser. Sono cinque, più `dbops.fn_sync_functions_owner` che le applica:
  le sei funzioni di `postgres` censite su dbdev nel §8.3. Il modello dice quindi «`zeroerp_owner`
  possiede tutto **tranne ciò che quel registro dichiara**».
* **Gli schemi che ospitano un'estensione** (`pgagent`, `topology`) non ne sono membri in
  `pg_depend` (`pgagent` lo crea un changeSet prima dell'estensione): si escludono per
  `pg_extension.extnamespace`, o lo script se ne prenderebbe la proprietà.
* **Il provision-pre crea anche una funzione da superuser**, `internal.trgfn_block_project_metadata`:
  il passaggio di proprietà copre anche le funzioni, registro escluso.
* ⛔ **`\quit 1` non fallisce**: psql ignora il codice ed esce con **0**. Nello script nuovo ogni
  fermo è un errore vero (codice 3). ⚠️ Lo stesso difetto è in `provision_db_roles.sql` e
  `provision_dblink_log_channel.sql` (variabili obbligatorie mancanti): da correggere con la fase 4,
  quando si unificano.
* **Un changeSet scrive `titodb` alla lettera**: `90_end/20260205-42` imposta il canale di log per
  `titodb` e `zeroerp_app` (gira solo quando gli si passa la password del canale). Va sostituito
  nella fase 3.
* Il canale `dblink` del migratore, sullo scratch del modello, resta **vuoto** come in CI: la stringa
  con la password finirebbe in `pg_db_role_setting`, che ogni ruolo può leggere.

### 9.3 Le prove, e quella che serve a Tid

**Fatte senza superuser** (scratch `zeroerp_ci`): i tre fermi escono con codice 3 (fase mancante,
sconosciuta, non superuser); le tre selezioni del passaggio di proprietà, a secco, prendono
esattamente lo schema `internal`, `databasechangelog`, `databasechangeloglock`,
`internal.project_metadata` (la sua sequenza segue la tabella) e
`internal.trgfn_block_project_metadata()`, lasciando fuori registro ed estensioni; la verifica «un
owner solo», a secco, trova gli stessi oggetti; `bash -n` su `ci-local.sh`.

**Quella che serve a Tid**, da superuser:

1. Il file delle password, fuori dal repo:
   ```bash
   mkdir -p ~/.config/zeroerp
   printf 'ZEROERP_OWNER_PASSWORD=%s\nZEROERP_JOB_PASSWORD=%s\n' '<pwd owner>' '<pwd job>' > ~/.config/zeroerp/ruoli-sviluppo.env
   chmod 600 ~/.config/zeroerp/ruoli-sviluppo.env
   ```
2. La corsa (chiede `sudo`; serve anche la password TCP del superuser, come oggi per lo scratch):
   ```bash
   PGPASSWORD_POSTGRES='<password di postgres>' scripts/ci-local.sh --fresh --ci-apply
   ```
   Crea i ruoli `zeroerp_owner` e `zeroerp_job` nel cluster (inerti finché nessuno li usa) e il
   database `zeroerp_ruoli`. Lo scratch `zeroerp_ci` e dbdev non si toccano (il testimone su dbdev
   resta).
3. Dire com'è finita. L'ultima riga attesa del provisioning è «un owner solo: verificato».

Poi il team DB verifica su `zeroerp_ruoli`: la postura dei ruoli, il presidio delle procedure dei
job (il test 7 non più in skip), la suite pgTAP.

### 8.4 Il `search_path` nella forma di casa — `20261014-56`

Rosso trovato da Tid il 2026-10-14 sulla corsa di `zeroerp_ruoli`:
`dbops/test-security-definer-search-path-v1`, test 5 — le `DEFINER` con `public` **prima** di
`pg_catalog` sono un debito (D6-bis) a soglia che può solo calare, e il `-55` lo aveva portato da 5 a
**21** scrivendo `public, topology, pg_temp`. La risoluzione era giusta (PostgreSQL cerca
`pg_catalog` per primo quando non è elencato), la forma no. ⚠️ La prova pre-apply del `-55` non aveva
lanciato quel presidio: è il presidio trasversale da lanciare per ogni `DEFINER` nuova o modificata.

Cura: `20261014-56`, `ALTER PROCEDURE … SET search_path = pg_catalog, public, topology, pg_temp` sulle
16 procedure (il `-55` è già applicato su dbdev, quindi non si modifica). Prova su `zeroerp_ruoli`, SQL
estratto, transazione annullata: test 5 **rosso prima, verde dopo** (5/5); il presidio delle procedure
dei job 7/7 prima e dopo; la convergenza di `ci_apply` 12 job su 12 riusciti.

### 9.4 La corsa di Tid e le verifiche (2026-10-14)

**Primo giro fermo alla fase `pre`**, per due difetti dello script: un apostrofo in una riga
`\echo` («stringa tra virgolette non terminata») e il registro `dbops.sec_functions_owner` letto
con un riferimento statico, che fallisce quando la tabella non esiste ancora anche dietro un
`to_regclass(…) IS NOT NULL`. Corretti (lettura dinamica) e provati **nello stato della fase**
(tabella nascosta in una transazione annullata). **Secondo giro: completato.**

**Verifiche su `zeroerp_ruoli`:**

* i tre ruoli di sistema hanno la postura del modello (né superuser, né `BYPASSRLS`, né
  `CREATEROLE`, con login) e il commento; quello di `zeroerp_owner` porta la firma;
* il database è di `zeroerp_owner`; degli oggetti del progetto **2376 sono di `zeroerp_owner`** e
  **6 di `postgres`**: le cinque funzioni del registro e `fn_sync_functions_owner`, nient'altro;
* ⭐ il job delle statistiche è passato due volte in `ci_apply` **senza `pg_maintain`**: con un owner
  solo il diritto in più non serve (quello dato a `zeroerp` nel modo classico si ritira con la fase 2);
* `maintenance/test-proc-job-definer-v1`: **7/7, nessuno skip** (il test 7, l'`EXECUTE` di
  `zeroerp_job`, ora si esercita); `maintenance/test-fn-analyze-statistiche-v1`: **10/10** (come app,
  caso negativo compreso). Lanciati via `psql` in transazione, non col runner.

**La suite la lancia Tid**, col suo comando abituale puntato sullo scratch del modello. Serve un env
file (gitignorato da `internal*.env`), sul calco di `db/internal.ci.env`, con `PGUSER=zeroerp_owner`,
la sua password e `PGDATABASE=zeroerp_ruoli`; la riga di `~/.pgpass` per `zeroerp_app` su
`zeroerp_ruoli` c'è già (aggiunta il 2026-10-14). Senza `--update`, così nessuna baseline cambia:

```bash
PGTAP_ENV_FILE=db/internal.ruoli.env PGTAP_BASELINE=db/pgtap/baseline-rossi-scratch.tsv \
  scripts/pgtap-baseline.sh dbops maintenance
```

Il confronto che conta è con la stessa corsa su `zeroerp_ci` (owner `zeroerp`): ciò che cambia fra i
due è solo il modello dei ruoli.

⚠️ **Incidente del 2026-10-14, dichiarato.** Un comando della sessione DB (uno script con un heredoc
annidato) si è rotto e la shell ha eseguito come comandi le righe di istruzioni pensate per questo
paragrafo: è partito `pgtap-baseline.sh` con `PGTAP_ENV_FILE=db/internal.ruoli.env`, che **non
esisteva**, quindi tutte le 833 chiamate si sono fermate al controllo del file, **senza collegarsi a
nessun database**; nessuna baseline modificata. Unico effetto: la riga di `~/.pgpass` per
`zeroerp_ruoli`, che serviva comunque.

## 10. Lo scratch è `zeroerp_ruoli` (decisione di Tid, 2026-10-14)

Da oggi lo scratch curato è `zeroerp_ruoli` (`ci-local.sh`, default dal 2026-10-15; il modo vecchio con `--classico`); `zeroerp_ci` resta fermo,
come specchio locale della CI di GitHub, finché la fase 2 non porta i workflow sul modello, poi si
cancella con il suo env file e il modo classico di `ci-local.sh`. Due conseguenze:

* **fino alla fase 2** un rosso che compare solo in CI può essere di modello (owner `zeroerp`, tre
  migratori, `pg_maintain`), non del lavoro: la fase 2 diventa la prossima;
* **la baseline dello scratch** (`baseline-rossi-scratch.tsv`, misurata su `zeroerp_ci`) si rifà su
  `zeroerp_ruoli` in tre passi: ricostruzione col `-56`; corsa completa **senza** `--update` e ogni
  differenza spiegata (modello, regressione, rosso già noto); solo dopo la corsa con `--update`.

**2026-10-15** — corsa completa della suite su `zeroerp_ruoli` (Tid): **nessuna regressione** rispetto
a `baseline-rossi-scratch.tsv` di `zeroerp_ci`. Il modello dei ruoli non cambia niente di ciò che i
test vedono. Resta il terzo passo: rifare la baseline sul nuovo scratch.

## 11. Fase 2 — la CI di GitHub sul modello (2026-10-15, sessione DB)

### 11.1 Che cosa cambia

| Workflow | Prima | Dopo |
| --- | --- | --- |
| `ci.yaml` «Set custom GUCs for CI role» | `CREATE ROLE zeroerp`, GUC su `zeroerp` | `provision_zeroerp.sql` fase `ruoli` (owner, job, app; il database passa a `zeroerp_owner`); GUC su `zeroerp_owner` |
| `ci.yaml` «Grant CREATE on public (CI bootstrap)» | `GRANT` su `public` e sulle tabelle di Liquibase, `pg_maintain` | «Proprieta' a zeroerp_owner»: fase `pre` |
| `ci-validate.yaml` «DB bootstrap (roles + grants)» | `CREATE ROLE zeroerp LOGIN CREATEDB`, `zeroerp_app`, `GRANT` su `public` | fase `ruoli` |
| `ci-validate.yaml` «Grant Liquibase tables to zeroerp» | `GRANT` sulle tabelle di Liquibase, `pg_maintain` | fase `pre` |
| Liquibase (passata principale, `ci_apply`) | `--username=zeroerp` | `--username=zeroerp_owner` |
| `manage.py migrate`, `check`, mypy (`env.DB_USER` del job) | `zeroerp` | `zeroerp_owner`: le tabelle di `django` nascono sue |
| Ruolo batch, `provision_db_roles.sql` | `migrator_role=zeroerp` | `migrator_role=zeroerp_owner` |
| — | — | **nuovo**: «Ruoli di sistema - fase post e verifica «un owner solo»» (in `ci-validate` dopo `provision_db_roles`, in `ci.yaml` dopo `ci_apply`) |
| Env file del runner pgTAP | `PGUSER=zeroerp` | `PGUSER=zeroerp_owner` |
| Doc DB (`ci.yaml`) | `user=zeroerp` | `user=zeroerp_owner` (il generatore vuole il proprietario) |

Password letterali di CI (D-3): `secret-owner`, `secret-job`, `secret-app` (quest'ultima esisteva).

* ⚠️ **`CREATEDB` non passa a `zeroerp_owner`**: il vecchio `zeroerp` lo aveva, ma i test Django girano
  sul database configurato e non ne creano uno (`backend/zeroerp_backend/test_runner.py`).
* ⚠️ **Fuori perimetro, dichiarato**: lo smoke test del container (`ci.yaml`, job `docker`) passa
  `DB_USER=zeroerp` all'immagine senza un database: non tocca il modello, si guarda con la fase 4.
* In `ci.yaml` `zeroerp_app` ora esiste (prima no): i `GRANT` dei changeSet scritti «salta se il
  ruolo manca» si applicano anche li', come gia' in `ci-validate`.
