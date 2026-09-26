# Brief DB — i job notturni che la CI non esegue mai

> **Perimetro:** DB (`dev/db-tid`), più il workflow di CI (`.github/workflows/`).
> Nessuna ricaduta su BE né FE.
> **Aperto:** 2026-09-26.
> **Origine:** D4 di
> [brief-db-lock-di-colonna-fuori-registro.md](brief-db-lock-di-colonna-fuori-registro.md),
> approvata da Tid il 2026-09-26, e l'**R-11** di
> [brief-db-processi-automatici-identita-e-perimetro.md](brief-db-processi-automatici-identita-e-perimetro.md).
>
> **Stato:** ✅ **CHIUSO il 2026-09-26 — applicato, verde, nessuna regressione.**
> `20260926-08`, `-09`, `-10` `EXECUTED` su dbdev e su `zeroerp_ci`; pgTAP
> rilanciati da Tid, verdi, compresi i due corretti in §6-bis. Letto dopo l'apply
> sul catalogo vivo di entrambi: `chk_processi_convergenza_ci` convalidato, zero
> job pgAgent senza dichiarazione, gli 11 job in elenco hanno tutti una riga
> riuscita (non di salto) nel giornale dei run.
>
> **In una riga.** In CI `85_pgagent` è `MARK_RAN`: i job notturni non esistono,
> e le procedure che eseguono non girano mai. Tutto ciò che solo un job fa è un
> comportamento che la CI non vede. Il 26-09 questo ha prodotto per due giorni
> una diagnosi rovesciata («dev fuori modello»).

---

## 1. Il difetto, sul modello

Una automazione di `dbops` ha **due** vie per arrivare su un database:

| Via | Dove gira | Che cosa esegue |
| --- | --- | --- |
| `90_end/ci_apply/20250627-31` | CI, a ogni migrazione (seconda invocazione, `--contexts=ci_apply`) | un **elenco scritto a mano** di chiamate `fn_run_automations_*('CI', …)` |
| job pgAgent → `maintenance.proc_*_job()` | solo dove esiste pgAgent (dbdev, domani produzione) | il **corpo della procedura** (`p_sql` di `fn_run_and_log`), con `'SCHEDULED'` |

Sono due copie della stessa domanda, *«che cosa fa girare questa famiglia di
automazioni?»*, e nessuno le tiene allineate. ⇒ Quando la procedura fa qualcosa
che l'elenco di `ci_apply` non fa, quel qualcosa:

* **non è mai collaudato in CI**, né dalla migrazione né dai pgTAP, che girano
  dopo;
* **gira solo su dev**, e una divergenza dev/CI viene letta come «dev sporco»,
  perché la CI ricostruita da zero passa per il metro.

⭐ **Il caso che l'ha mostrato.** `proc_automations_lock_columns_job` chiamava anche
`fn_run_automations_drop_lock_trg`, che `ci_apply` non chiamava. Su dev cancellava
ogni sera i lock di colonna scritti a mano; in CI c'erano ancora. Ritirata il 26-09,
ma il meccanismo che l'ha resa invisibile è ancora lì.

## 2. La fotografia (2026-09-26 — fatto datato, non un motivo)

Le procedure della famiglia `automations_*` a confronto con `ci_apply`, lette sui
corpi vivi di dbdev e sul file di `ci_apply`:

| Procedura | Che cosa esegue | In `ci_apply`? |
| --- | --- | --- |
| `proc_automations_audit_update_job` | `fn_run_automations_audit_update` | ✅ |
| `proc_automations_storico_provision_job` | `fn_run_automations_storico_provision` | ✅ |
| `proc_automations_storico_job` | `fn_run_automations_storico` | ✅ |
| `proc_automations_tx_id_job` | `fn_run_automations_tx_id` | ✅ |
| `proc_automations_attivo_job` | `fn_run_automations_attivo` | ✅ |
| `proc_automations_lock_columns_job` | `fn_run_automations_lock_columns` + **`fn_run_automations_date_validita`** | lock ✅; date di validità ⚠️ solo dal `runAlways` `90_end/20260923-47`, non da `ci_apply` |
| `proc_automations_delete_block_job` | `fn_run_automations_delete_block` | ✅ |
| `proc_automations_overlap_job` | **`fn_apply_automazione_overlap`** | ❌ nessun giro di migrazione |
| `proc_automations_cleanup_job` | **`fn_run_automations_cleanup('SCHEDULED', ARRAY['dbops'])`** | ❌ nessun giro di migrazione |

⇒ Oggi **due** automazioni (OVERLAP, CLEANUP) non girano mai in CI. ⚠️ I 12
vincoli `EXCLUDE` coincidono comunque fra dev e CI (confrontati per nome, il
26-09): non è un argomento per lasciar stare. Vuol dire che oggi i vincoli
nascono anche per altre vie, e che il giorno in cui una riga nuova di
`dbops.automazione_overlap` dipenderà solo dal job, la CI non l'avrà.

Fuori dalla famiglia `automations_*` i job sono **operativi**: agiscono sui dati e
sul tempo, non sulla struttura (`send_pending_emails`, `draina_coda_*`,
`guardiano_digest`, `digest_presidi:*`, `chiusura_scadenze_daily`,
`sync_auth_user_expired_daily`, `listen_cambio_reparto`, `apply_storicizza_weekly`,
`sync_storico_set_storicizza`, `apply_fk_index_policy`). Vedi D2.

## 3. Proposta — rivista il 2026-09-26 dopo la domanda di Tid («serve l'elenco»)

⭐ **Tid ha ragione: un elenco serve**, e non è una copia. Porta due informazioni
che nessuna procedura ha:

* **quali** job sono strutturali (vanno eseguiti su ogni database, CI compresa) e
  quali operativi;
* **in che ordine**: `storico_provision` prima di `storico`, il lock dopo `attivo`.
  pgAgent l'ordine non lo dà (i job della famiglia partono tutti alle 21:00).

La copia da togliere non è l'elenco: sono i **corpi**. L'elenco deve **nominare le
procedure**, non ripetere quello che fanno.

⛔ **Correzione della prima versione di questo brief**: «ritirare l'elenco di
`20250627-31`» non si può. È un changeSet già mergiato, e su un database da zero
gira comunque. Resta com'è, ed è anche l'unico posto che esercita il modo `'CI'`
(oggi nessuna riga dei registri lo usa: 19 regole e 44 lock, tutte `AUTO`).

### D1 — L'elenco sta nel catalogo dei processi, e un `ci_apply` lo esegue

`dbops.processi` è già il registro di **tutti** i job, con `classe` e `canale`.
L'elenco va lì, così lo leggono sia il changeSet sia il presidio:

* due colonne nuove in `dbops.processi`:
  * `ci_ordine integer`: la posizione nella convergenza strutturale; `NULL` vuol
    dire fuori;
  * `ci_procedura text`: la procedura da chiamare, **scritta per esteso**. Non si
    deriva dal codice: `apply_storicizza_weekly` non segue la forma
    `proc_<codice>_job` (verificato il 26-09);
* un changeSet `90_end/ci_apply` nuovo, `runAlways`, che fa `CALL` delle procedure
  con `ci_ordine` valorizzato, in quell'ordine. Dopo le `CALL` verifica che ogni
  job abbia una riga `ok` in `maintenance.job_run_log` **che non sia uno skip**
  (§5).

### D2 — Il confine sta nella riga del catalogo, non in una regola a parole

Proposta di valori, per i processi `MANUTENZIONE` / `PGAGENT`:

| Processo | `ci_ordine` | Perché |
| --- | --- | --- |
| `automations_audit_update`, `_storico_provision`, `_storico`, `_tx_id`, `_attivo`, `_lock_columns`, `_delete_block` | 10…70 | l'ordine di `ci_apply` |
| `automations_overlap`, `automations_cleanup` | 80, 90 | oggi non girano mai in CI (§2) |
| `sync_storico_set_storicizza` → `apply_storicizza_weekly` | 100, 110 | strutturali (il `DEFAULT` di `storicizza`); il secondo consuma l'insieme del primo |
| `apply_fk_index_policy` | 120 | ha già un `runAlways` suo (`20250626-31`), che resta: due giri idempotenti, ma un elenco solo |
| `guardiano_digest` | fuori | operativo |
| `COMMAND`, `CODA`, `CODA_AUTOMATICA`, `sync_auth_user_expired_daily` | fuori | operativi: agiscono su dati e orologio |

### D3 — Il presidio legge lo stesso catalogo

Un pgTAP, che gira dopo `ci_apply`:

1. ogni processo `MANUTENZIONE` / `PGAGENT` attivo ha `ci_ordine` **oppure** una
   **esclusione dichiarata**. ⚠️ Serve distinguere «fuori apposta» da
   «dimenticato»: `NULL` da solo non lo fa. Quindi una terza colonna,
   `ci_esclusione text`, e un `CHECK`: esattamente una fra `ci_ordine` e
   `ci_esclusione`, per quella classe e quel canale;
2. ogni `ci_procedura` esiste (`to_regprocedure`);
3. ogni processo con `ci_ordine` ha nel `job_run_log` di questo database una
   riga `ok` che non è uno skip.

⇒ Un job strutturale nuovo senza giro in CI fa rosso al punto 1, senza un
secondo elenco da tenere nel pgTAP.

## 4. Decisioni — ✅ Tid, 2026-09-26

| | Decisione |
| --- | --- |
| D1 | ✅ l'elenco in `dbops.processi` (`ci_ordine`, `ci_procedura`), eseguito da un `ci_apply` `runAlways` nuovo; `20250627-31` resta |
| D2 | ✅ dentro. ⭐ `apply_fk_index_policy` però **fuori dall'elenco**, con esclusione dichiarata: gira già in CI e a ogni migrazione dal `runAlways` `90_end/20250626-31`, con la stessa chiamata (`dbops.apply_fk_index_policy`). Nell'elenco girerebbe due volte, e quel changeSet non si può togliere perché è mergiato. In CI c'è, una volta sola |
| D3 | ✅ `ci_esclusione` + `CHECK` + pgTAP |

**Il perimetro è più largo della prima proposta**: non i soli `MANUTENZIONE` /
`PGAGENT`, ma **ogni processo con un job pgAgent** (`jobname_pgagent`
valorizzato). Il difetto è «ciò che solo pgAgent esegue», qualunque classe
abbia. Sono 15 righe: 11 in elenco e 4 escluse (`apply_fk_index_policy`,
`guardiano_digest`, `sync_auth_user_expired_daily`, `chiusura_scadenze_daily`).

## 5. Rischi già noti

* **Due passate per lo storico** (nota di memoria del 15-09): su dev
  `automations_storico` parte prima di `automations_storico_provision`, e una
  madre nuova ha lo storico il giorno dopo. Con D1 l'ordine lo decide il
  changeSet, quindi in CI il problema non c'è; su dev resta. Da dire, non da
  risolvere qui.
* **`runAlways` in `90_end` gira prima di `ci_apply`** (memoria): il changeSet di
  D1 va nel contesto `ci_apply`, altrimenti nella prima passata troverebbe tabelle
  senza i trigger che le procedure presuppongono.
* **`fn_run_and_log` salta in silenzio** se l'advisory lock del job è già preso
  (`RETURN` con la riga «skip: another run in progress», `ok = true`). In CI non
  c'è un altro giro concorrente, quindi non dovrebbe succedere; ma un salto
  risulterebbe **verde**. Il changeSet di D1 può verificare, dopo le `CALL`, che
  ogni job abbia una riga `ok` **senza** quel messaggio.

## 6. Che cosa è stato scritto (2026-09-26)

| File | Che cosa fa |
| --- | --- |
| `00_schema/dbops/20260926-08-alter-processi-add-convergenza-ci` | tre colonne, `UNIQUE (ci_ordine)`, `chk_processi_convergenza_ci` **NOT VALID**: su dev le righe esistono e i valori arrivano dal CSV, dopo |
| `80_data/sql/dbops/processi.csv` | le tre colonne su 25 righe; le 10 colonne originali verificate identiche byte per byte |
| `90_end/20260926-09-validate-chk-processi-convergenza-ci` | `VALIDATE CONSTRAINT`, dopo il CSV |
| `90_end/ci_apply/20260926-10-run-processi-strutturali-in-ordine` | `runAlways`, contesto `ci_apply`: `CALL` delle procedure in ordine, poi pretende una riga ok **non di salto** in `maintenance.job_run_log` per ognuna |
| `db/pgtap/dbops/test-processi-convergenza-ci.sql` | 8 test, gira come app: colonne, vincolo convalidato, nessun job «dimenticato», procedure esistenti, ogni job in elenco ha girato su questo DB, ordine delle dipendenze |
| `docs/it/dbzero/dbops/manual/processi.md` | sezione «La convergenza in CI» e il passo nuovo in «Come si registra un processo» |

Il loader `80_data/changelog/20260904-13` **non si tocca**: elenca solo sette
colonne, e Liquibase carica le altre deducendo il tipo dal CSV, come fa già per
`jobname_pgagent`, `tolleranza_minuti` e `segno_di_vita`.

### Come è stato provato

SQL estratto dai changeSet, su `zeroerp_ci` come owner, in una transazione
annullata; il CSV simulato con `UPDATE` generati dal CSV stesso. Dopo, nessun
residuo.

* Il `CHECK` `NOT VALID` blocca già le scritture: un `UPDATE` di una riga senza
  valori va in errore 23514. Col CSV applicato la convalida passa.
* Il `ci_apply` 10: **11 job in ordine, 0,74 s**, una riga `done` per ognuno nel
  giornale. ⭐ **Una differenza vera, vista subito**: su `zeroerp_ci`
  `sync_storico_set_storicizza` ha trovato **2 tabelle** mancanti dall'insieme
  della storicizzazione. Era una delle cose che la CI non eseguiva mai.
* pgTAP **8/8** dopo l'SQL estratto.
* **Mutazione A**: `guardiano_digest` senza esclusione, rifiutata dal `CHECK`
  già all'`UPDATE`.
* **Mutazione B**: `automations_overlap` puntato alla procedura del cleanup
  (che registra sotto un altro codice); il 10 si ferma con «non ha lasciato una
  riga riuscita».
* Guardrail statici del repository e del preambolo pgTAP: verdi.

### Che cosa NON prova

* il **salto** per advisory lock non è stato provocato: servirebbero due
  sessioni. Il controllo che lo intercetta è lo stesso della mutazione B;
* il percorso **da zero** (00_schema prima della tabella piena, 80_data, poi le
  due invocazioni) è ragionato, non corso;
* il pgTAP gira come **app** nella corsa di Tid; qui è girato da owner.

## 6-bis. ⚠️ La ricaduta dell'apply: pgTAP che seminano processi

Dopo l'apply, `dbops/test-vw-processi-programmazione-da-guardare` è andato
**rosso** (corsa di Tid, 26-09): la fixture del test 4 semina un processo con un
job pgAgent finto e senza `ci_*`, e il `CHECK` nuovo la rifiuta.

⛔ **È un buco del censimento, e va dichiarato.** Prima di aggiungere il vincolo
non ho cercato i pgTAP che scrivono in `dbops.processi`. Sono 14 file; 5 punti
valorizzano `jobname_pgagent`, e 3 di questi erano colpiti, in tre modi diversi:

| Test | Effetto del `CHECK` nuovo | Rimedio |
| --- | --- | --- |
| `-da-guardare`, test 4 (fixture) | rosso: riga rifiutata | la riga dichiara `ci_esclusione` |
| `programmazione`, test 2 (`23505`, job doppio) | rosso: il `CHECK` scatta **prima** dell'`UNIQUE`, `23514` | la riga dichiara `ci_esclusione`, e l'`UNIQUE` torna a parlare |
| `programmazione`, test 3 (`23514`, nome vuoto) | ⭐ **verde per coincidenza**: il `23514` era del vincolo nuovo, non di `chk_processi_jobname_pgagent_non_vuoto` | riga con `ci_esclusione` **e** `throws_like` sul **nome** del vincolo misurato |

Il rimedio sta nelle fixture, non nel vincolo: un processo con un job pgAgent
dichiara se gira in CI, anche quando è seminato da un test. Riprovati su
`zeroerp_ci` dopo la correzione: `programmazione` **21/21**, `-da-guardare`
**7/7**. Gli altri 9 punti non valorizzano `jobname_pgagent` e non sono toccati.

## 7. Chiusura

| | Che cosa |
| --- | --- |
| ✅ | apply su dbdev e `zeroerp_ci` (`20260926-08`, `-09`, CSV, `-10`), 26-09 |
| ✅ | pgTAP verdi, nessuna regressione, 26-09 (corsa di Tid) |
| ✅ | stato vivo verificato su entrambi i database (vedi Stato) |

**Fuori da questo brief, e non lo tengono aperto:**

* su **dbdev** l'ordine dei job notturni resta quello di pgAgent, che li lancia
  tutti alle 21:00 senza un ordine fra loro (§5): una madre nuova può avere lo
  storico il giorno dopo. La CI ora li esegue in ordine; dev no. Se serve, è un
  cantiere a parte (un job unico che fa le `CALL` dall'elenco di `dbops.processi`);
* `20250627-31` (elenco `'CI'` scritto a mano) resta: è mergiato, ed è l'unico
  che esercita il modo `'CI'`.
