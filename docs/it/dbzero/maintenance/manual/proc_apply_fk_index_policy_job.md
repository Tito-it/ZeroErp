## 📘 Documentazione Concettuale – Procedura `maintenance.proc_apply_fk_index_policy_job`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — il processo `apply_fk_index_policy`: job pgAgent, procedura e perché resta fuori dalla convergenza del rilascio
> * [maintenance.job_run_log](/dbzero/maintenance/tabelle/job_run_log) — il giornale in cui ogni corsa lascia la sua riga
> * [dbops.fk_index_policy](/dbzero/dbops/tabelle/fk_index_policy) — la politica: una riga per chiave esterna, con la decisione e il comando
>
> Approfondimento viste:
>
> * [dbops.vw_processi_programmazione](/dbzero/dbops/views/vw_processi_programmazione) — il calendario vivo e lo stato del processo
> * [maintenance.vw_job_run_da_guardare](/dbzero/maintenance/views/vw_job_run_da_guardare) — dove una corsa fallita diventa una cosa da guardare
> * [dbops.vw_fk_senza_indice](/dbzero/dbops/views/vw_fk_senza_indice) — le chiavi esterne senza un indice che le copra: quelle senza riga il populate le registra
>
> Approfondimento funzioni:
>
> * [dbops.apply_fk_index_policy](/dbzero/dbops/funzioni/apply_fk_index_policy) — il lavoro vero: crea o toglie gli indici secondo le decisioni
> * [dbops.fn_populate_fk_index_policy](/dbzero/dbops/funzioni/fn_populate_fk_index_policy) — registra le chiavi esterne nuove, come `DA_DECIDERE`
> * [maintenance.fn_run_and_log](/dbzero/maintenance/funzioni/fn_run_and_log) — il giornale da cui passa la chiamata, col lock e il verbale del fallimento
> * [maintenance.fn_sveglia_accesa](/dbzero/maintenance/funzioni/fn_sveglia_accesa) — il cancello dello step pgAgent
>
> Guide:
>
> * [Framework di Automazione DB, §6](/guide/automazione-db#6-policy-indici-fk) — la policy degli indici FK
> * [Framework di Automazione DB, §9](/guide/automazione-db#9-quando-girano-le-automazioni) — quando girano le automazioni

---

### 🎯 Scopo Principale

Il wrapper del processo `apply_fk_index_policy`: esegue `dbops.apply_fk_index_policy`, preceduta a richiesta da
`dbops.fn_populate_fk_index_policy`, passando dal giornale delle esecuzioni sotto il codice del
processo.

La procedura non aggiunge logica: delega a `maintenance.fn_run_and_log`, che apre la riga
della corsa in `maintenance.job_run_log`, esegue il lavoro e chiude la riga con l'esito.

---

### Un solo parametro: registrare prima di applicare

* **Con `p_populate` vero** la corsa esegue prima `dbops.fn_populate_fk_index_policy`, che
  registra in `dbops.fk_index_policy` le chiavi esterne senza indice e ancora senza riga, e toglie
  quelle da decidere che non sono più scoperte; poi `dbops.apply_fk_index_policy`. È la chiamata
  del job pgAgent.
* **Senza argomento**, o con `p_populate` falso, esegue solo l'applicazione.

⛔ Registrare non è indicizzare. Una riga nuova nasce `DA_DECIDERE`, e finché resta così
l'applicazione non crea e non toglie niente. L'indice nasce quando il seed decide `CON_INDICE`. Il
giro settimanale tiene il registro completo, non decide quali indici servono.

---

### ⭐ Il job della domenica, non la convergenza

| Dove | Chi la chiama | Quando |
| --- | --- | --- |
| dbdev e installazioni con pgAgent | il job `automations_apply_fk_indexes_policy`, step `run_apply_fk_index_policy`, con `p_populate` vero | al giro del suo calendario |
| ogni migrazione, anche in CI | **non** questa procedura: due changeSet `runAlways` di `90_end` chiamano direttamente `dbops.apply_fk_index_policy` e `dbops.fn_populate_fk_index_policy` | a ogni migrazione |

A differenza delle altre procedure della famiglia, questa non sta nella convergenza del rilascio:
il processo dichiara in `dbops.processi` l'esclusione, perché l'applicazione e la scoperta girano
già a ogni migrazione, e nell'elenco girerebbero due volte. Ne seguono due cose:

* alla migrazione l'applicazione e la scoperta non passano dal giornale: lasciano solo i loro avvisi;
* in CI il job non esiste (`85_pgagent` finisce `MARK_RAN`), ma il registro ha comunque le chiavi
  esterne nuove, perché le registra la migrazione.

Lo step pgAgent chiama la procedura solo se `maintenance.fn_sveglia_accesa('apply_fk_index_policy')`
è vero: a processo spento il giro settimanale non parte e il giornale non scrive niente; la
migrazione applica la politica lo stesso. Il calendario dei job è in
[Job pgAgent](/dbzero/maintenance/job_pgagent), quello vivo di un'installazione in
`dbops.vw_processi_programmazione`.

---

### ⭐ Una corsa, una riga nel giornale

Il meccanismo è quello di `maintenance.fn_run_and_log`, e la sua scheda lo racconta per intero.
Per chi legge il giornale di questo processo:

* **Il nome della corsa è il codice del processo**, `apply_fk_index_policy`: così il giornale
  risale alla riga di `dbops.processi`, e il panorama dei processi la legge.
  ⚠️ Il job pgAgent si chiama invece `automations_apply_fk_indexes_policy`: il legame fra i due nomi lo tiene
  la colonna `jobname_pgagent` del processo.
* **Una corsa alla volta.** La procedura passa come chiave un advisory lock sull'hash del
  codice. Se una corsa dello stesso processo è già in giro, la seconda non esegue niente e
  lascia una riga **saltata**: `saltata` vero, `ok` vuoto, già chiusa. Un salto non è una
  corsa riuscita.
* **Un fallimento si propaga, e il verbale resta.** Se il runner fallisce, `fn_run_and_log`
  scrive il verbale **fuori transazione**, con `maintenance.fn_job_run_log_failure`, e poi
  rilancia l'errore: lo step pgAgent fallisce, e la transazione si
  annulla con tutto il DDL del giro. La riga rossa porta in `error_code` il codice di dominio
  del runner (`E_…`) o, in mancanza, lo SQLSTATE, che sta anche in `sqlstate`. Questo runner
  non passa dal registro errori: in `dbops.error_log` non resta niente. Da lì la corsa compare in
  `maintenance.vw_job_run_da_guardare`.
* **Gira come il proprietario.** La procedura è `SECURITY DEFINER`, con `search_path` fissato,
  e appartiene a `zeroerp_owner`: chi la chiama è `zeroerp_job`, ma
  il DDL gira come `zeroerp_owner`, e gli indici nascono suoi. Il giornale registra come ruolo
  della sessione chi si è collegato.

---

### ⚠️ I rifiuti della guardia non arrivano al giornale

L'applicazione ha due guardie: con `CON_INDICE` crea l'indice solo se la chiave esterna è
ancora scoperta, e con `SENZA_INDICE` **rifiuta** di togliere un indice che regge un vincolo
(chiave primaria, unicità, `REPLICA IDENTITY`). Il rifiuto è un `WARNING`, e il conto di creati,
saltati, tolti, rifiutati, da decidere e fuori ambito un `NOTICE`: nessuno dei due è un errore, la corsa finisce riuscita
(`done`), e il giornale non li registra.

---

### Nessun modo, nessun ambito, nessuna simulazione

L'applicazione non ha parametri: scorre tutte le righe della politica, e fa il DDL di quelle decise.
Il modo `SCHEDULED` e l'ambito delle altre procedure della famiglia qui non esistono; gli schemi li
delimita la politica stessa, per schema, con
[dbops.fn_indici_schema_nell_ambito](/dbzero/dbops/funzioni/fn_indici_schema_nell_ambito): una riga
fuori da quegli schemi non produce niente.

---

### Codici errore

La procedura non ne solleva di suoi, e il lavoro non ha codici di dominio: un errore del DDL
arriva col suo SQLSTATE, e `error_code` del giornale riporta quello.

---

### Test

* `db/pgtap/maintenance/test-proc-job-definer-v1.sql` — per ogni `maintenance.proc_*_job`:
  `SECURITY DEFINER`, `search_path` fissato, proprietario dello schema, nessun `EXECUTE` a
  `PUBLIC` né a `zeroerp_app`.
* `db/pgtap/dbops/test-processi-jobname-wrapper.sql` — il nome che il wrapper passa al giornale
  esiste in `dbops.processi`.
* `db/pgtap/dbops/test-processi-convergenza-ci.sql` — ogni job pgAgent dichiara la sua posizione
  nella convergenza o la sua esclusione: questo processo dichiara l'esclusione.

---

### Note di migrazione

* 2026-01-16 — nasce col job settimanale.
* 2026-09-05 — il processo a catalogo prende il nome che il wrapper passa al giornale,
  `apply_fk_index_policy`; prima portava quello del job pgAgent
  (`brief-db-processi-automatici-residui-be`).
* 2026-09-26 — resta fuori dalla convergenza del rilascio, con l'esclusione dichiarata
  (`brief-db-job-notturni-in-ci`).
* 2026-10-14 — diventa `SECURITY DEFINER`, come tutte le `maintenance.proc_*_job`
  (`brief-db-ruoli-di-sistema`).
* 2026-10-16 — lo step pgAgent passa dal cancello `maintenance.fn_sveglia_accesa`
  (`brief-db-processi-accensione-per-ambiente`).
* 2026-11-03 — pagina riscritta: la versione precedente nominava il job pgAgent col codice del
  processo, lo mostrava chiamato senza il populate, e proponeva orari e un `cron` d'esempio.
* 2026-11-09 — la scoperta gira anche a ogni migrazione, con un suo changeSet `runAlways` di
  `90_end`, e scrive `DA_DECIDERE` al posto del flag spento (`20261110-48`, `-54`;
  brief-db-revisione-dbops, giro 10d). Prima solo questo giro registrava le chiavi esterne nuove, e
  in CI nessuno.

---

{% include-markdown "signature-core.md" %}
