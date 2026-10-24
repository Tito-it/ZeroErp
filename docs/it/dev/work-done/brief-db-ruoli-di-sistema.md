# Brief DB — I ruoli di sistema: nomi fissi, un provisioning solo, uguali ovunque

## ✅ Chiuso il 2026-10-15

**Il modello è in vigore ovunque** — CI di GitHub (verde), scratch `zeroerp_ruoli`, dbdev convertito
con pgAgent come `zeroerp_job` — e i ruoli dismessi sono fuori dal cluster. Fasi 1, 1-bis, 2, 3, 4,
D-5 e i rientri dopo la conversione (§19) sono committati e uniti (ultima: PR #1866).

**Debito residuo**, chiuso lo stesso giorno → [brief-db-zeroerp-log-nella-fase-ruoli](brief-db-zeroerp-log-nella-fase-ruoli.md)
(D35): `zeroerp_log` creato dalla fase `ruoli` invece che a mano; i vecchi privilegi di default di
`titodb` (facoltativo); una corsa di `ci-local.sh` dopo la fase 4.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ **Tid** | Decisioni D-1 … D-5 (2026-10-14), D-6 (2026-10-15) | §7, §19.2 | — |
| 2 | ✅ **team DB** + **Tid** | Fase 1-bis: le 16 procedure dei job `DEFINER` (`20261014-55`, `-56`), applicate su dbdev | §8 | — |
| 3 | ✅ **team DB** + **Tid** | Fase 1: `provision_zeroerp.sql`, lo scratch `zeroerp_ruoli`, baseline rifatta senza regressioni | §9, §10 | — |
| 4 | ✅ **team DB** + **Tid** | Fase 2: i due workflow di GitHub sul modello; prima corsa vera con i pgTAP verdi | §11 | — |
| 5 | ✅ **team DB** + **Tid** | D-5: il ruolo di ogni corsa (`20261015-01…-05`) e il presidio «nessun superuser al lavoro», applicati; presidio vuoto | §14, §17 | — |
| 6 | ✅ **team DB** + **Tid** | Fase 3: dbdev convertito con `converti_db_al_modello_ruoli.sql`; pgAgent come `zeroerp_job` | §16 | — |
| 7 | ✅ **team DB** + **Tid** | Fase 4: nel repo (via `--classico`, un solo provisioning, ruolo batch) e sul cluster (`zeroerp_batch_fatturazione`, `pgagent`, `zeroerp` con `zeroerp_ci`) | §18 | — |
| 8 | ✅ **team DB** + **Tid** | Dopo la conversione: la guard di scope (`20261015-06`) e `pg_read_all_stats` a `zeroerp_owner` (D-6), applicati; i 19 rossi nuovi rientrati | §19 | — |
| 9 | **Tid** | La baseline completa su dbdev (in corsa): conferma che non resta niente della conversione | §19 | niente |
| 10 | ✅ **Tid** | Fase 4, `-06` e D-6 committati e uniti (PR #1866, 2026-10-15). La CI della PR prova i due workflow cambiati | §18, §19 | — |
| 10-bis | ✅ **team DB** | Le guide allineate al modello, senza riferimenti storici: permessi (§7.6 «Chi si collega al database»), pgAgent («Con che utente girano i lavori»), RLS, dblink, Liquibase, statistiche, storicizzazione, GUC, audit, tracciamento, installazione | — | — |
| 11 | → D35 | `scripts/ci-local.sh --ci-apply` dopo la fase 4: nel brief del debito residuo | — | — |
| 12 | → D35 | I 48 vecchi privilegi di default di `titodb`: nel brief del debito residuo | — | — |
| 12-bis | → D35 | `zeroerp_log` dentro la fase `ruoli`: nel brief del debito residuo | — | — |
| 13 | ✅ **team DB** | Chiusura (2026-10-15): brief in `work-done/`, guide allineate, `PROJECT_CONTEXT.md`, memoria, D35 | — | — |

**Decisioni aperte di Tid: nessuna.**
⬜ Da committare (2026-10-15): fase 4 nel repo (§18), `20261015-06`, il test 8 di
`script/test-guard-emittente-senza-utente`, D-6 in `provision_zeroerp.sql`, la documentazione, questo
documento. Committati e pushati: fasi 1, 1-bis, 2; committati e non pushati dopo l'ultima PR: niente
(D-5, fase 3 e `-42` sono nella PR del 2026-10-15).

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-10-14. **A chi:** Tid, poi il team DB.
> **Origine:** il cantiere delle statistiche
> ([brief-db-statistiche-tabelle-job-notturno](brief-db-statistiche-tabelle-job-notturno.md) §7.2-§7.3):
> il job ha trovato in CI tabelle create da `postgres` che `zeroerp` non poteva analizzare. Proposta
> di Tid: dare ruoli standard «di sistema», da non riconfigurare a ogni installazione.
> **Stato:** ✅ chiuso il 2026-10-15. Debito residuo (D35) chiuso lo stesso giorno: `work-done/brief-db-zeroerp-log-nella-fase-ruoli`.
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
* **Un changeSet scriveva `titodb` alla lettera**: `90_end/20260205-42` impostava il canale di log
  per `titodb` e `zeroerp_app`. Era `context: disabled` (non girava mai): ✅ ritirato il 2026-10-15
  (§15), la sede è lo script `provision_dblink_log_channel.sql`.
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

### 11.2 La prova sul cluster usa-e-getta (2026-10-15)

I passi DB di `ci-validate.yaml` su un PostgreSQL 18 vergine, senza ruoli preesistenti (come il container
di GitHub; `manage.py migrate` sostituito dalla copia del DDL di `django`, come in `ci-local.sh`):
fase `ruoli` (tre ruoli creati), provision-pre, fase `pre`, passata principale come `zeroerp_owner`,
provision-post, `ci_apply`, ruolo batch, `provision_db_roles`, fase `post`: **«un owner solo:
verificato»**; 705 relazioni del progetto tutte di `zeroerp_owner`. pgTAP mirati, nessun rosso e nessuno
skip: procedure dei job 7, `search_path` delle DEFINER 5, statistiche 10, verbale fuori transazione 6,
convergenza in CI 8, catalogo presidi 11, postura del ruolo batch 19, riferimenti morti 9, postura di
`django` 11, registri append-only 24. ⚠️ Il cluster era in `trust`: le password dei workflow le prova
solo la prima corsa su GitHub.

### 11.3 Le PR

PR 1 (#1861, mergiata il 2026-10-15): tutto tranne la fase 2, con i workflow nella sola versione
«`pg_maintain`». PR 2: i due workflow della fase 2 — la prima corsa del modello su GitHub. Dopo, la
baseline della CI (`baseline-rossi-ci.tsv`) va guardata.

## 12. Documentazione anticipata dalla fase 4 (2026-10-15)

La sede del modello è [provisioning-db-roles.md](../backend/provisioning-db-roles.md): i ruoli di
sistema, le regole (nomi fissi, membership, password, un owner solo e il registro, job `DEFINER`,
membership e non nome, il superuser non lavora), **dove il modello è in vigore** (scratch e CI sì,
sviluppo no fino alla fase 3) e `provision_zeroerp.sql` fase per fase. Rimandano lì, e non lo
contraddicono più: `liquibase-setup-workflow.md` §2 (`pgagent`, `pg_maintain`), `postgresql/pgAgent.md`
(«Permessi consigliati»: era `maintenance_executor` e pgAgent come `postgres`), `postgresql/dblink.md`,
`guide/storicizzazione-tabelle.md`, `guide/statistiche-del-planner.md`, `play-book-operativo-backend.md`.
Lo scratch nei commenti d'uso di `testpgtap.sh` e `pgtap-baseline.sh` è `zeroerp_ruoli`. Restano per la
fase 4: unificare gli script (`\quit 1` compreso) e ritirare `--classico`, `zeroerp_ci`, `internal.ci.env`.

## 13. pgAgent come `zeroerp_job`, da capo a fondo (2026-10-15)

Prova sul cluster usa-e-getta, database costruito come in CI, con il **demone pgAgent vero** (4.2.3)
avviato con `user=zeroerp_job` e tre job programmati per partire subito:

| Job | Esito pgAgent | Giornale | Che cosa dimostra |
| --- | --- | --- | --- |
| `CALL maintenance.proc_analyze_statistiche_job()` | riuscito | `analyze_statistiche` ok | la procedura gira come proprietario: `zeroerp_job` da solo non analizzerebbe niente |
| `CALL maintenance.proc_guardiano_digest_job()` | riuscito | `guardiano_digest` ok | un secondo job reale passa dal giornale |
| step libero (`CREATE TABLE public…; SELECT … FROM vendite.ddt`) | **fallito** | — | «permesso negato per lo schema public»: `zeroerp_job` può solo chiamare le procedure; nessuna tabella creata |

Nessun errore di permesso del demone sulle tabelle di `pgagent` (i diritti della fase `pre` bastano);
`zeroerp_job` non è superuser né membro di `zeroerp_owner`.

⚠️ **Da sapere per la fase 3**: `ANALYZE` come `zeroerp_owner` salta i **cataloghi condivisi** del cluster
(`pg_authid`, `pg_database`, …), che solo un superuser analizza: è la D-1 (catalogo fuori
dall'autoverifica), quindi il job riesce. Su dbdev oggi pgAgent è superuser e li analizza; dopo la fase 3
li lascerà all'autovacuum.
⚠️ Il giornale scrive `origine = PGAGENT` anche per le corse di `ci_apply` (è il default della
colonna): è il motivo per cui D-5 deve leggere il **ruolo** della corsa, non l'origine.

## 14. D-5 — il ruolo di ogni corsa e il presidio «nessun superuser al lavoro» (2026-10-15)

### 14.1 Che cosa c'è

| Pezzo | Dove |
| --- | --- |
| `maintenance.job_run_log.ruolo_sessione`: chi si è collegato (`session_user`), **senza default** | `00_schema/maintenance/20261015-01` |
| `maintenance.fn_run_and_log` lo scrive nella corsa e nella riga saltata | `20_code/maintenance/20261015-02` |
| `maintenance.fn_job_run_log_failure` lo scrive nel verbale di un fallimento, letto nella sessione del job; `search_path` nella forma di casa | `20_code/maintenance/20261015-03`, **`context: provision`**, incluso in `changelog-provision-post.yaml` (la funzione è di un superuser: registro `sec_functions_owner`) |
| La vista `maintenance.vw_job_run_da_superuser`, presidio `ZERO` (chi agisce: sistemista), con il testo | `20_code/maintenance/20261015-04`; `presidi.csv`, `presidi_testi.csv` |
| pgTAP (plan 8) | `db/pgtap/maintenance/test-job-run-ruolo-sessione-v1.sql` |
| Rubinetto D6-bis del `search_path`: 5 → 4 | `db/pgtap/dbops/test-security-definer-search-path-v1.sql` |
| Il canale di log anche per `zeroerp_job` | `scripts/sql/provision_dblink_log_channel.sql` |

**Una semplificazione rispetto alla D-5, sul modello.** Il presidio guarda «superuser» e non «membro
di `zeroerp_job`»: dal `-55` le procedure dei job le possono chiamare solo proprietario, `zeroerp_job`
e superuser, e il giornale non distingue pgAgent da `ci_apply` (origine `PGAGENT` di default; pgAgent
non imposta `application_name`). Si giudica da `rolsuper`, mai dal nome.

**Una lacuna trovata provando, e chiusa.** Il verbale di un fallimento apre il canale `dblink` col
parametro `myapp.dblink_log_connection` della **sessione**, cioè di `zeroerp_job` sotto pgAgent: i
workflow e gli script lo impostavano solo per migratore e app. Su dbdev non mordeva (il parametro è
impostato per tutto il database), su un'installazione nuova sì: un job fallito sotto pgAgent non
avrebbe lasciato il verbale. `provision_dblink_log_channel.sql` ora lo imposta anche per
`zeroerp_job` (riga gemella delle due vicine; non lanciata, perché lo script riscrive la password di
`zeroerp_log`, che è di cluster).

### 14.2 La prova (cluster usa-e-getta, database come in CI, 98 s)

* il `-03` si applica dal provision-post: la funzione resta di `postgres`, `search_path=pg_catalog,
  public, pg_temp`, il corpo scrive il ruolo;
* pgTAP verdi: il file nuovo 8 (test 3 in skip **d'ambiente**: il cluster è in `trust`, e `dblink` da
  un non-superuser vuole una password — lo stesso skip di `test-job-run-saltata-v1`; in CI gira),
  `search_path` 5 con la soglia a 4, catalogo presidi 11, testi 19, verbale fuori transazione 6,
  giornale 21 + 11 + 12, procedure dei job 7, riferimenti morti 9, guardiano 9;
* **da capo a fondo**, chiamate come `zeroerp_job`: `guardiano_digest` riuscita con ruolo
  `zeroerp_job`; una procedura `DEFINER` che fallisce → riga **fallita scritta fuori transazione con
  ruolo `zeroerp_job`**; `analyze_statistiche` lanciata da `postgres` → il presidio la nomina, e solo
  lei.

### 14.3 L'apply su dbdev, e che cosa aspettarsi

⛔ **Su dbdev l'ordine è rovesciato: prima il provision-post, poi il migrate.** Il migrate di dbdev
gira **senza** `--contexts`, e Liquibase senza contexts esegue anche i changeSet `context: provision`:
il `-03` (che l'autogen raccoglie da `20_code`) lo prova il migratore e fallisce con «bisogna essere
proprietari della funzione fn_job_run_log_failure» (successo il 2026-10-15: `-01` e `-02` applicati, il
migrate fermo al `-03`, `-04` e CSV non ancora). Se il provision-post lo ha già registrato, il migrate
lo trova fatto e passa — è la strada su cui passò il `20260912-41`. In CI e in `ci-local.sh` la
passata principale esclude `provision`, e l'ordine scritto sotto vale com'è.

1. migrate: `20261015-01`, `-02`, `-04` e i due CSV dei presidi;
2. ⚠️ **provision-post da superuser** per il `-03` (la funzione è di `postgres`):
   `scripts/liquibase5.sh --url=… --username=postgres --password=… --changeLogFile=db/changelog/changelog-provision-post.yaml update --contexts=provision`.
   Finché non passa, `test-security-definer-search-path-v1` test 5 è **rosso** (la soglia è già 4) e le
   righe dei fallimenti hanno `ruolo_sessione` NULL;
3. ⚠️ **il presidio si accende su dbdev** alla prima corsa notturna: pgAgent si collega ancora come
   `postgres`. Dice il vero; si spegne con la fase 3.

## 15. Fase 4 — la parte anticipata (2026-10-15)

* ✅ **`\quit 1` → errore vero** in cinque script (`check_db_role_access`, `provision_db_roles`,
  `provision_dblink_log_channel`, `provision_db_role_batch_fatturazione`,
  `retire_db_role_batch_fatturazione`): un fermo usciva con 0, ora con 3 (provato su ognuno).
* ✅ Il canale di log per `zeroerp_job` (§14.1).
* ✅ **`90_end/20260205-42` ritirato** (decisione di Tid, 2026-10-15): impostava il canale per `titodb`
  alla lettera, ma era `context: disabled` e non girava mai. Una seconda copia del provisioning del canale,
  morta: la sede è `scripts/sql/provision_dblink_log_channel.sql`, che segue il modello (migratore, app,
  `zeroerp_job`). Su dbdev la riga in `databasechangelog` resta (RERAN del 2026-02-05): Liquibase non
  protesta per un changeSet registrato il cui file non c'è più.
* ⬜ **Distruttivi, da superuser sul cluster vero, con Tid**: ritiro di `zeroerp_batch_fatturazione`
  (script pronto), di `pgagent`, di `zeroerp_ci` con `internal.ci.env` e `--classico` (dopo che la CI
  col modello ha fatto girare anche i pgTAP).
* ⬜ **Unificare gli script** in un ingresso solo: dopo la fase 3, quando non serve più il migratore
  come variabile.

## 16. Fase 3 — dbdev si converte al modello (2026-10-15)

### 16.1 Lo script

`scripts/sql/converti_db_al_modello_ruoli.sql`, da superuser, sul database da convertire, con
`-v utente_personale=titodb`. **Generico**: serve a qualunque database nato prima del modello, non
solo a dbdev. **Una transazione sola**: o tutto o niente. Con `-v solo_prova=1` fa tutto, verifica
tutto e annulla.

1. fase `ruoli` di `provision_zeroerp.sql`: postura dei ruoli di sistema, database a `zeroerp_owner`,
   `CONNECT` a `zeroerp_job` e `zeroerp_app`;
2. `REASSIGN OWNED BY titodb TO zeroerp_owner`. ⚠️ Prende anche gli oggetti **condivisi**: gli altri
   database di `titodb` (su dbdev `zeroerp_b2_test`) gli vengono restituiti;
3. i 48 privilegi di default di `titodb` **ricopiati** per `zeroerp_owner`, con gli stessi destinatari
   (anche `zeroerp_batch_fatturazione`, che si ritira con la fase 4). Quelli di `titodb` restano: non
   crea più niente a nome suo;
4. `GRANT zeroerp_owner TO titodb` e `ALTER ROLE titodb IN DATABASE zeroerp SET role = zeroerp_owner`
   (D-1). `db/liquibase.properties` e `db/internal.env` **non cambiano**: Liquibase, il runner pgTAP e
   una psql di Tid lavorano come proprietario. `SET ROLE NONE` torna a `titodb`, `RESET ROLE` al
   proprietario;
5. fasi `pre` e `post` di `provision_zeroerp.sql`: `pgagent`, `EXECUTE` di `zeroerp_job` sulle 16
   procedure, **verifica «un owner solo»**;
6. verifica che `titodb` non possieda più niente in `zeroerp`.

Fatti datati (dbdev, 2026-10-15): `titodb` possiede 1213 relazioni, 1151 funzioni, 20 schemi, 15 tipi;
`postgres` solo le funzioni del registro; nessun oggetto del progetto di `postgres` fuori registro.

### 16.2 La prova (cluster usa-e-getta, struttura di dbdev, 2026-10-15)

Struttura di dbdev (`pg_dump -s` come `titodb`) più le 5 righe del registro `sec_functions_owner`,
restore senza errori, stessa tabella dei lock di dbdev (64 × 50):

* prova a vuoto: tutto verificato, ROLLBACK, proprietari invariati;
* conversione: **0,35 s**; 1213 relazioni a `zeroerp_owner`; restano di `postgres` solo le 5 funzioni
  del registro e `fn_sync_functions_owner`; `zeroerp_b2_test` resta di `titodb`; 48 default per
  `zeroerp_owner`;
* una sessione di `titodb`: `session_user=titodb`, `current_user=zeroerp_owner`; tabella e funzione
  nuove nascono di `zeroerp_owner` e `zeroerp_app` le usa; su `zeroerp_b2_test` `titodb` resta se stesso;
* `zeroerp_job`: `EXECUTE` su 16 procedure su 16, `pgagent` leggibile e scrivibile;
* rilancio: idempotente.

⚠️ **I lock**: `REASSIGN OWNED` ne prende **4036** in una transazione, oltre i 3200 nominali di dbdev.
Sul cluster di prova è bastato; se su dbdev la conversione si fermasse con «out of shared memory», si
alza `max_locks_per_transaction` (riavvio) e si rilancia: non resta niente a metà.
⛔ La prova ha trovato un trucco: senza le righe del registro (copia della sola struttura) la conversione
dà a `zeroerp_owner` anche le funzioni che devono restare di un superuser. Su dbdev il registro c'è.

### 16.3 I passi di Tid, in una finestra

1. `sudo systemctl stop pgagent` (lo script si rifiuta se vede una sessione al lavoro su `pgagent`);
   nessun lavoro lungo del backend in corso (lo script blocca ogni tabella, per un istante);
2. prova a vuoto, poi la vera:
   ```
   PGPASSWORD="$PGPASSWORD_POSTGRES" psql -h localhost -U postgres -d zeroerp \
     -v utente_personale=titodb -v solo_prova=1 -f scripts/sql/converti_db_al_modello_ruoli.sql
   PGPASSWORD="$PGPASSWORD_POSTGRES" psql -h localhost -U postgres -d zeroerp \
     -v utente_personale=titodb -f scripts/sql/converti_db_al_modello_ruoli.sql
   ```
3. pgAgent come `zeroerp_job`: nell'override dell'unità (`sudo systemctl edit pgagent`)
   ```
   ExecStart=
   ExecStart=/usr/bin/pgagent -f -l 1 "host=127.0.0.1 dbname=zeroerp user=zeroerp_job"
   ```
   e in `/var/lib/postgresql/.pgpass` (proprietario `postgres`, `0600`) **una riga in più**
   `127.0.0.1:5432:zeroerp:zeroerp_job:<password di zeroerp_job>`. ⚠️ libpq confronta l'host **come
   testo**: `localhost` e `127.0.0.1` sono due righe diverse, quindi l'host della riga è lo stesso della
   connessione. ⛔ Le altre righe non si toccano ora: quella di `zeroerp_log` serve al canale di log (il
   `service=zeroerp_log` di `/var/lib/postgresql/.pg_service.conf` prende la password da qui, perché
   `dblink` si collega dal processo del server, utente di sistema `postgres`); quelle di `pgagent` e
   `loguser` (ruolo che non esiste più) si tolgono con i ritiri della fase 4. Poi
   `sudo systemctl daemon-reload && sudo systemctl start pgagent`. ⚠️ Su socket (`host=/var/run/…`)
   l'autenticazione `peer` rifiuterebbe `zeroerp_job` (utente di sistema `postgres`): per questo TCP;
4. controllo: `journalctl -u pgagent -n 20` senza errori di autenticazione; dopo la prima corsa
   notturna `maintenance.job_run_log.ruolo_sessione = 'zeroerp_job'` e il presidio
   `maintenance.vw_job_run_da_superuser` **vuoto**;
5. baseline pgTAP completa (cambia il proprietario di ogni funzione `SECURITY DEFINER`).

Tornare indietro, se servisse: ⛔ **non** `REASSIGN OWNED BY zeroerp_owner TO titodb`: prenderebbe anche
il database `zeroerp_ruoli`, che è di `zeroerp_owner`. Si fa con lo stesso schema dello script, a
parti invertite e con la restituzione degli altri database.

## 17. Il terzo scrittore del giornale — `20261015-05` (2026-10-15)

Dopo l'apply della D-5 il giornale di dbdev aveva ancora righe con `ruolo_sessione` NULL ogni minuto:
`draina_coda_lavori`, `draina_coda_stampa`, `send_pending_emails`, origine `CRON`. Le scrive
`script.fn_job_run_start`, l'apertura delle corse **headless** del backend (management command, cron,
systemd): un terzo scrittore che la D-5 (§7, §14) non aveva censito.

Al presidio non sfuggiva niente di oggi (quelle corse girano come `zeroerp_app`), ma una corsa headless
lanciata da un amministratore sarebbe passata invisibile.

* `20_code/script/20261015-05`: le due `INSERT` (corsa e riga saltata) scrivono
  `ruolo_sessione = session_user`; corpo dal `20261010-21`, identico al vivo (confrontato su dbdev);
  firma, `SECURITY DEFINER` e `search_path` invariati. Aggiorna anche il `COMMENT` della colonna (tre
  scrittori). Funzione del proprietario: **passata normale**, niente provision-post;
* pgTAP `maintenance/test-job-run-ruolo-sessione-v1`: plan 8 → 10 (test 9 la corsa, test 10 la riga
  saltata, con lo stesso skip d'ambiente del test 3).

**Prova** (dbdev, SQL estratto in transazione annullata, 2026-10-15): con il `-05` 8 verdi e 2 skip
d'ambiente; **senza** il `-05` il test 9 è rosso (il test misura). Il ramo della riga saltata provato a
parte con due sessioni vere (una tiene il lock): `acquired = false`, `saltata = true`,
`ruolo_sessione = titodb`.

## 18. Fase 4 — il ritiro (2026-10-15)

### 18.1 Nel repo

1. **Il modo classico.** `ci-local.sh` non ha più `--classico`: un modo solo, il modello, su
   `zeroerp_ruoli`. Commenti di `testpgtap.sh`, `pgtap-baseline.sh` e due pagine allineati.
2. **Un solo script di provisioning.** La postura di `zeroerp_app` (era
   `scripts/sql/provision_db_roles.sql`, con `app_role`, `app_password` e `migrator_role` di default
   `titodb`) è la fase `post` di `provision_zeroerp.sql`: nomi di sistema, e la password di
   `zeroerp_app` non si tocca più (la crea la fase `ruoli`). Il passo «Privilegi del ruolo applicativo»
   di `ci-validate.yaml` e il passo 3 di `ci-local.sh` sono assorbiti dalla fase `post`, che sta già
   dopo entrambi i migratori. ⚠️ Unificato e non incluso con `\ir`: `ci-local.sh` passa gli script
   dallo standard input (`postgres` non attraversa `/home/tid`), e lì `\ir` cercherebbe nella
   cartella corrente.
   `provision_dblink_log_channel.sql` (nomi di sistema; la password di `zeroerp_log` solo per crearlo),
   `provision_storico_scope.sql` (migratore `zeroerp_owner`: col default `titodb` oggi avrebbe ridato
   le shadow a un utente personale), `check_db_role_access.sql` (default `zeroerp_app`).
   I riferimenti attivi puntano alla fase `post`; quelli nei changeSet applicati restano (fatti datati).
3. **Il ruolo batch.** Via il provisioning, il controllo, il vecchio script di ritiro, il passo dei due
   workflow, il ponte di `ci-local.sh` e il pgTAP `rls/test-role-batch-fatturazione-postura`. Il test 11
   di `rls/test-rls-fondi-fattura-source-functional` è **rovesciato**: pretendeva che il batch avesse
   `BYPASSRLS`, ora pretende che nessun ruolo `zeroerp_*` ce l'abbia (il giro notturno gira con un
   utente tecnico per azienda dal 2026-09-05). Il guardrail sui `GRANT` ai ruoli batch resta.
4. **`scripts/ritira_ruoli_dismessi.sh`**: ritira ruoli dal **cluster**. Gira su ogni database
   (`DROP OWNED` lavora su quello a cui si è collegati), si ferma se un ruolo **possiede** qualcosa,
   cancella un database solo se lo si nomina con `--cancella-database`, rifiuta i ruoli di sistema e il
   database di sviluppo. Senza `--esegui` è una prova a vuoto (ogni `DROP OWNED` provato e annullato).
   Sostituisce `retire_db_role_batch_fatturazione.sql`, che non sarebbe partito (variabili psql dentro
   blocchi `DO`) e lavorava su un database solo.

### 18.2 Le prove

* **Postura di `zeroerp_app`** (struttura di dbdev senza privilegi, cluster usa-e-getta piccolo — la
  memoria del server non regge un build da zero): i privilegi dati dalla fase `post` sono **identici** a
  quelli del vecchio script, nei due versi (vecchio sopra il nuovo non aggiunge niente; vecchio da solo
  dà esattamente gli stessi). Rilanci: password di `zeroerp_app` e `zeroerp_log` invariate. Canale di
  log senza `zeroerp_log` e senza password: si ferma (rc=3); con la password lo crea. La conversione
  della fase 3 con la nuova fase `post`: verde.
* **`ritira_ruoli_dismessi.sh`** (cluster usa-e-getta con ruoli e privilegi sparsi su più database):
  ruolo di sistema e database di sviluppo rifiutati; prova a vuoto; un ruolo che possiede una funzione
  si ferma e la nomina; batch e `pgagent` ritirati da tutti i database; `zeroerp` si ferma finché
  `zeroerp_ci` esiste e passa con `--cancella-database zeroerp_ci`; rilancio idempotente.
* ⚠️ Non provati qui: `ci-local.sh` (vuole `sudo`) e i workflow (li prova la prossima PR).

### 18.3 I passi di Tid, sul cluster

Fatti datati (2026-10-15, da `pg_shdepend`): `zeroerp_batch_fatturazione` ha privilegi in `zeroerp`,
`zeroerp_ruoli`, `zeroerp_ci` e un'impostazione di cluster; `pgagent` in `postgres` e `zeroerp`;
`zeroerp` possiede tutto `zeroerp_ci`.

1. prova a vuoto, poi il ritiro dei due ruoli senza proprietà:
   ```
   PGPASSWORD="$PGPASSWORD_POSTGRES" scripts/ritira_ruoli_dismessi.sh zeroerp_batch_fatturazione pgagent
   PGPASSWORD="$PGPASSWORD_POSTGRES" scripts/ritira_ruoli_dismessi.sh --esegui zeroerp_batch_fatturazione pgagent
   ```
   ⚠️ **prima** del prossimo `ci-local.sh --fresh`: col ruolo nel cluster lo scratch nuovo si ferma
   sulla `preCondition` di `20260729-05` (ora `ci-local.sh` lo dice subito). Fino al ritiro il test 11
   di `rls/test-rls-fondi-fattura-source-functional` è rosso su dbdev e sullo scratch: dice il vero;
2. ⛔ **irreversibile**: `zeroerp_ci` e il suo ruolo (lo scratch classico, fermo dal 2026-10-14):
   ```
   PGPASSWORD="$PGPASSWORD_POSTGRES" scripts/ritira_ruoli_dismessi.sh --cancella-database zeroerp_ci zeroerp
   PGPASSWORD="$PGPASSWORD_POSTGRES" scripts/ritira_ruoli_dismessi.sh --esegui --cancella-database zeroerp_ci zeroerp
   ```
   poi a mano `db/internal.ci.env` (fuori da git: non si recupera) e, se non serve più,
   `db/pgtap/baseline-rossi-scratch.tsv` resta: è la baseline di `zeroerp_ruoli`;
3. i vecchi privilegi di default di `titodb` su `zeroerp` (non crea più niente a nome suo), da superuser:
   ```
   psql -h localhost -U postgres -d zeroerp -c "SELECT format('ALTER DEFAULT PRIVILEGES FOR ROLE titodb%s REVOKE ALL ON %s FROM %I',
       CASE WHEN d.defaclnamespace = 0 THEN '' ELSE ' IN SCHEMA ' || quote_ident(d.defaclnamespace::regnamespace::text) END,
       CASE d.defaclobjtype WHEN 'r' THEN 'TABLES' WHEN 'S' THEN 'SEQUENCES' WHEN 'f' THEN 'FUNCTIONS' WHEN 'T' THEN 'TYPES' WHEN 'n' THEN 'SCHEMAS' END,
       pg_get_userbyid(a.grantee))
     FROM pg_default_acl d CROSS JOIN LATERAL aclexplode(d.defaclacl) a
    WHERE d.defaclrole = 'titodb'::regrole AND a.grantee <> 0" -At | psql -h localhost -U postgres -d zeroerp
   ```
   (dopo il punto 1: tra i destinatari c'è anche il ruolo batch);
4. `/var/lib/postgresql/.pgpass`: via le righe di `pgagent` e le due di `loguser`; quella di
   `zeroerp_log` e quella di `zeroerp_job` restano.

## 19. Dopo la conversione: due regressioni del «lavoro come proprietario» (2026-10-15)

La baseline di Tid su dbdev (`config dbops magazzino maintenance rls`) dopo la fase 3: **19 rossi nuovi**.
Tutti hanno la stessa radice: `titodb` si collega col suo nome e lavora come `zeroerp_owner`
(`SET role`, D-1), quindi `session_user` (titodb) e `current_user` (zeroerp_owner) sono diversi anche
fuori da ogni `SECURITY DEFINER`. In CI il runner si collega come `zeroerp_owner` e i due coincidono.

### 19.1 La guard di scope prendeva il proprietario per una DEFINER — `20261015-06`

18 pgTAP `pgtap-runner: owner` (i satelliti RLS, il magazzino) in `ERRORE_FIXTURE` con
`E_SCOPE_SENZA_UTENTE`. `script.trgfn_guard_emittente_scope`, ramo «utente NULL», riconosceva «sono
dentro una DEFINER» da `current_user <> session_user` (rev 18-09, `20260918-13`).

* **Rimedio**: si confronta col ruolo di **sessione**, il parametro `role` (`none` → `session_user`).
  Una DEFINER cambia `current_user` ma non `role` (provato su dbdev). Per chi si collega col proprio
  nome (CI, l'app) l'espressione è **identica** a prima.
* **Censimento**: il confronto `current_user <> session_user` c'era solo qui. Le altre letture di
  `session_user` lo **registrano** (il giornale dei job: voluto il login) o controllano la
  **membership** (`dbops.fn_sessione_del_migratore`: già giusta).
* **Prova** (dbdev, SQL estratto in transazione annullata): `rls/test-rls-ddt-satelliti` 10/10,
  `rls/test-rls-magazzino-perimetro-v1` 12/12, `rls/test-rls-fondi-fattura-source-functional` 11/11
  (compreso il test 11 rovesciato: nessun ruolo con BYPASSRLS). Il ramo DEFINER resta chiuso: una
  DEFINER del proprietario chiamata da `titodb` con `SET ROLE NONE`, senza utente, su una riga con
  padrone → **fermata**; la stessa scrittura da `titodb` che lavora come proprietario → passa (è lui).
* `script/test-guard-emittente-senza-utente` test 8 pinnava il testo del corpo: aggiornato al nuovo
  criterio, verde col `-06`.

### 19.2 L'orario di una sessione si vede solo dallo stesso ruolo — ✅ D-6 (a), Tid 2026-10-15

`dbops/test-vw-processi-programmazione` test 17: `ultimo_segno_di_vita` NULL. È
`min(backend_start)` da `pg_stat_activity`, che PostgreSQL **maschera** a chi legge con un ruolo diverso
da quello della sessione (memoria «pg_stat_activity maschera», 2026-09-14): la sessione è di `titodb`,
legge `zeroerp_owner`. Il verdetto (`OK`) è giusto, perché usa il conteggio, che non è mascherato; è vuoto solo l'orario.

**D-6, per Tid:**

* **(a) consigliata**: `GRANT pg_read_all_stats TO zeroerp_owner`, nella fase `ruoli` di
  `provision_zeroerp.sql` (un ruolo di cluster: mai in un changeSet). Chi legge come proprietario — il
  digest (`fn_conta_presidio`, DEFINER del proprietario), una psql di Tid — vede l'orario di **ogni**
  sessione, comprese quelle di `zeroerp_app` che oggi gli arrivano vuote. È un ruolo di sola lettura
  delle statistiche.
* (b) il test 17 misura «la vista dice ciò che chi legge può vedere» (confronto con
  `pg_stat_activity` della propria sessione): resta verde ovunque, ma l'orario resta mascherato al digest.
